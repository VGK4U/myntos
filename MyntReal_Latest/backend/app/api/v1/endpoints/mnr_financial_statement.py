"""
MNR Financial Statement API
DC Protocol: Read-only financial overview for Staff Portal
Shows Revenue, Payouts, and Liabilities from Feb 12, 2026 onwards
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, or_, case, desc, cast, Date
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
import logging

from app.core.database import get_db
from app.core.security import get_current_rvz_user_hybrid
from app.models.user import User
from app.models.transaction import Transaction, PendingIncome
from app.models.withdrawal import WithdrawalRequest
from app.models.coupon import PINPurchaseRequest
from app.models.awards import (
    DirectAwardTier, MatchingAwardTier,
    UserAwardProgress, UserMatchingAwardProgress
)
from app.models.bonanza import DynamicBonanza, DynamicBonanzaHistory, DynamicBonanzaReward
from app.models.myntreal_incentive import MNRAccidentalInsurance
from app.constants.award_statuses import AwardStatus
from app.models.staff_accounts import IncomeEntry, ExpenseEntry, AssociatedCompany, EmployeeFundLedger
from app.models.staff import StaffEmployee
from app.models.expense_category import ExpenseMainCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rvz/financial-statement", tags=["MNR Financial Statement"])

FINANCIAL_START_DATE = date(2026, 2, 12)
PRODUCTION_START_DATE = date(2025, 10, 21)
INSURANCE_ELIGIBILITY_DATE = datetime(2026, 2, 3, 0, 0, 0)
INSURANCE_PREMIUM_PER_USER = 500
REQUIRED_REFERRALS_FOR_OLD_USERS = 2


VGK_SUPREME_EMP_CODE = 'MR10001'

def _staff_only_check(current_user):
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access only")
    if getattr(current_user, 'emp_code', None) != VGK_SUPREME_EMP_CODE:
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme only")
    return current_user


def _safe_float(val):
    if val is None:
        return 0.0
    return float(val)


def _cost_priority(*values):
    """Return the first non-None value (0 is valid). Falls back to 0.0."""
    for v in values:
        if v is not None:
            return float(v)
    return 0.0


def _parse_dates(date_from, date_to):
    start_date = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else FINANCIAL_START_DATE
    end_date = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else date.today()
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    return start_date, end_date, start_dt, end_dt


@router.get("/data")
async def get_financial_statement(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="Filter: pin_revenue, income, withdrawal, award, bonanza, insurance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    _staff_only_check(current_user)

    start_date, end_date, start_dt, end_dt = _parse_dates(date_from, date_to)

    date_rows = {}

    if not category or category == "pin_revenue":
        _aggregate_pin_revenue(db, start_dt, end_dt, date_rows)

    if not category or category == "income":
        _aggregate_income(db, start_dt, end_dt, date_rows)

    if not category or category == "withdrawal":
        _aggregate_withdrawals(db, start_date, end_date, date_rows)

    if not category or category == "award":
        _aggregate_awards(db, start_dt, end_dt, date_rows)

    if not category or category == "bonanza":
        _aggregate_bonanza(db, start_dt, end_dt, date_rows)

    if not category or category == "insurance":
        _aggregate_insurance(db, date_rows, start_dt, end_dt)

    entries = sorted(date_rows.values(), key=lambda x: x["sort_key"], reverse=True)

    total_revenue = sum(e["revenue"] for e in entries)
    total_admin_charges = sum(e["admin_charges_received"] for e in entries)
    total_tds = sum(e["tds_received"] for e in entries)
    total_payouts = sum(e["payout"] for e in entries)
    total_liabilities = sum(e["liability"] for e in entries)
    total_insurance = sum(e["insurance"] for e in entries)
    total_awards = sum(e["awards_amount"] for e in entries)
    total_payable = total_payouts + total_liabilities
    net_position = total_revenue - total_payable

    total_entries = len(entries)
    offset = (page - 1) * page_size
    paginated = entries[offset:offset + page_size]

    return {
        "success": True,
        "summary": {
            "total_revenue": total_revenue,
            "total_admin_charges": total_admin_charges,
            "total_tds": total_tds,
            "total_payouts": total_payouts,
            "total_liabilities": total_liabilities,
            "total_insurance": total_insurance,
            "total_awards": total_awards,
            "total_payable": total_payable,
            "net_position": net_position,
        },
        "entries": paginated,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_entries": total_entries,
            "total_pages": max(1, (total_entries + page_size - 1) // page_size)
        },
        "filters": {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "category": category
        }
    }


@router.get("/data/detail")
async def get_financial_detail(
    detail_date: str = Query(..., description="Date YYYY-MM-DD"),
    detail_type: str = Query(..., description="revenue or payable"),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    _staff_only_check(current_user)

    try:
        target_date = datetime.strptime(detail_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    if detail_type == "revenue":
        return _get_revenue_detail(db, target_date, day_start, day_end)
    elif detail_type == "payable":
        return _get_payable_detail(db, target_date, day_start, day_end)
    else:
        raise HTTPException(status_code=400, detail="detail_type must be 'revenue' or 'payable'")


@router.get("/summary")
async def get_financial_summary(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="Filter: pin_revenue, income, withdrawal, award, bonanza, insurance"),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    _staff_only_check(current_user)

    start_date, end_date, start_dt, end_dt = _parse_dates(date_from, date_to)

    pin_revenue = 0
    if not category or category == "pin_revenue":
        pin_revenue = db.query(func.coalesce(func.sum(PINPurchaseRequest.total_amount), 0))\
            .filter(
                PINPurchaseRequest.status.in_(['Approved', 'Fulfilled']),
                PINPurchaseRequest.request_date >= start_dt,
                PINPurchaseRequest.request_date <= end_dt
            ).scalar() or 0

    income_totals = []
    income_admin_retained = 0.0
    income_tds_retained = 0.0
    income_guru_dakshina = 0.0
    if not category or category == "income":
        income_totals = db.query(
            PendingIncome.income_type,
            func.coalesce(func.sum(PendingIncome.gross_amount - PendingIncome.admin_deduction), 0)
        ).filter(
            PendingIncome.business_date >= start_dt,
            PendingIncome.business_date <= end_dt,
            PendingIncome.verification_status != 'Rejected'
        ).group_by(PendingIncome.income_type).all()

        income_deductions = db.query(
            func.coalesce(func.sum(PendingIncome.admin_deduction), 0),
            func.coalesce(func.sum(PendingIncome.tds_deduction), 0),
            func.coalesce(func.sum(PendingIncome.gurudakshina_deduction), 0)
        ).filter(
            PendingIncome.business_date >= start_dt,
            PendingIncome.business_date <= end_dt,
            PendingIncome.verification_status != 'Rejected'
        ).first()

        income_admin_retained = _safe_float(income_deductions[0]) if income_deductions else 0.0
        income_tds_retained = _safe_float(income_deductions[1]) if income_deductions else 0.0
        income_guru_dakshina = _safe_float(income_deductions[2]) if income_deductions else 0.0

    withdrawal_total = 0
    total_admin_charges = 0.0
    total_tds = 0.0
    if not category or category == "withdrawal":
        withdrawal_data = db.query(
            func.coalesce(func.sum(WithdrawalRequest.final_payout), 0),
            func.coalesce(func.sum(WithdrawalRequest.admin_charges), 0),
            func.coalesce(func.sum(WithdrawalRequest.tds_amount), 0)
        ).filter(
            WithdrawalRequest.status.in_(['Approved', 'Paid', 'Completed']),
            WithdrawalRequest.request_date >= start_date,
            WithdrawalRequest.request_date <= end_date
        ).first()

        withdrawal_total = withdrawal_data[0] if withdrawal_data else 0
        total_admin_charges = _safe_float(withdrawal_data[1]) if withdrawal_data else 0.0
        total_tds = _safe_float(withdrawal_data[2]) if withdrawal_data else 0.0

    awards_liability = 0.0
    if not category or category == "award":
        awards_liability = _calculate_awards_liability_total(db, start_dt, end_dt)

    bonanza_liability = 0.0
    if not category or category == "bonanza":
        bonanza_liability = _calculate_bonanza_liability_total(db, start_dt, end_dt)

    insurance_data = {"total_cost": 0, "eligible_count": 0}
    if not category or category == "insurance":
        insurance_data = _calculate_insurance_liability(db, start_dt, end_dt)

    total_income = sum(_safe_float(t[1]) for t in income_totals)
    total_payouts = total_income + _safe_float(withdrawal_total)
    total_liabilities = awards_liability + bonanza_liability + insurance_data["total_cost"]
    total_payable = total_payouts + total_liabilities
    net_position = _safe_float(pin_revenue) - total_payable

    return {
        "success": True,
        "summary": {
            "total_revenue": _safe_float(pin_revenue),
            "total_admin_charges": total_admin_charges,
            "total_tds": total_tds,
            "income_admin_retained": income_admin_retained,
            "income_tds_retained": income_tds_retained,
            "income_guru_dakshina": income_guru_dakshina,
            "income_company_retained": income_admin_retained + income_tds_retained,
            "income_breakdown": {t[0]: _safe_float(t[1]) for t in income_totals},
            "total_income_paid": total_income,
            "total_withdrawals": _safe_float(withdrawal_total),
            "total_payouts": total_payouts,
            "awards_liability": awards_liability,
            "bonanza_liability": bonanza_liability,
            "insurance_liability": insurance_data["total_cost"],
            "insurance_eligible_count": insurance_data["eligible_count"],
            "total_liabilities": total_liabilities,
            "total_payable": total_payable,
            "net_position": net_position
        }
    }


def _ensure_date_row(date_rows, date_key, date_display):
    if date_key not in date_rows:
        date_rows[date_key] = {
            "sort_key": date_key,
            "date": date_display,
            "date_key": date_key,
            "revenue": 0.0,
            "revenue_count": 0,
            "admin_charges_received": 0.0,
            "tds_received": 0.0,
            "income_admin_retained": 0.0,
            "income_tds_retained": 0.0,
            "income_guru_dakshina": 0.0,
            "payout": 0.0,
            "payout_count": 0,
            "liability": 0.0,
            "liability_count": 0,
            "insurance": 0.0,
            "awards_amount": 0.0,
            "payable": 0.0,
            "categories": []
        }
    return date_rows[date_key]


def _aggregate_pin_revenue(db, start_dt, end_dt, date_rows):
    results = db.query(
        cast(PINPurchaseRequest.request_date, Date).label('day'),
        func.count(PINPurchaseRequest.id),
        func.coalesce(func.sum(PINPurchaseRequest.total_amount), 0)
    ).filter(
        PINPurchaseRequest.status.in_(['Approved', 'Fulfilled']),
        PINPurchaseRequest.request_date >= start_dt,
        PINPurchaseRequest.request_date <= end_dt
    ).group_by('day').all()

    for day, count, total in results:
        if day is None:
            continue
        dk = day.isoformat()
        dd = day.strftime("%d %b %Y")
        row = _ensure_date_row(date_rows, dk, dd)
        row["revenue"] += _safe_float(total)
        row["revenue_count"] += count
        if "PIN Revenue" not in row["categories"]:
            row["categories"].append("PIN Revenue")


def _aggregate_income(db, start_dt, end_dt, date_rows):
    results = db.query(
        cast(PendingIncome.business_date, Date).label('day'),
        func.count(PendingIncome.id),
        func.coalesce(func.sum(PendingIncome.gross_amount), 0),
        func.coalesce(func.sum(PendingIncome.admin_deduction), 0),
        func.coalesce(func.sum(PendingIncome.tds_deduction), 0),
        func.coalesce(func.sum(PendingIncome.gurudakshina_deduction), 0)
    ).filter(
        PendingIncome.business_date >= start_dt,
        PendingIncome.business_date <= end_dt,
        PendingIncome.verification_status != 'Rejected'
    ).group_by('day').all()

    for day, count, gross_total, admin_ded, tds_ded, guru_ded in results:
        if day is None:
            continue
        dk = day.isoformat()
        dd = day.strftime("%d %b %Y")
        row = _ensure_date_row(date_rows, dk, dd)
        payout_amt = _safe_float(gross_total) - _safe_float(admin_ded)
        row["payout"] += payout_amt
        row["payout_count"] += count
        row["payable"] += payout_amt
        row["income_admin_retained"] += _safe_float(admin_ded)
        row["income_tds_retained"] += _safe_float(tds_ded)
        row["income_guru_dakshina"] += _safe_float(guru_ded)
        if "Income" not in row["categories"]:
            row["categories"].append("Income")


def _aggregate_withdrawals(db, start_date, end_date, date_rows):
    results = db.query(
        WithdrawalRequest.request_date,
        func.count(WithdrawalRequest.id),
        func.coalesce(func.sum(WithdrawalRequest.final_payout), 0),
        func.coalesce(func.sum(WithdrawalRequest.admin_charges), 0),
        func.coalesce(func.sum(WithdrawalRequest.tds_amount), 0)
    ).filter(
        WithdrawalRequest.status.in_(['Approved', 'Paid', 'Completed']),
        WithdrawalRequest.request_date >= start_date,
        WithdrawalRequest.request_date <= end_date
    ).group_by(WithdrawalRequest.request_date).all()

    for day, count, total, admin_charges, tds in results:
        if day is None:
            continue
        dk = day.isoformat()
        dd = day.strftime("%d %b %Y")
        row = _ensure_date_row(date_rows, dk, dd)
        amt = _safe_float(total)
        row["payout"] += amt
        row["payout_count"] += count
        row["payable"] += amt
        row["admin_charges_received"] += _safe_float(admin_charges)
        row["tds_received"] += _safe_float(tds)
        if "Withdrawal" not in row["categories"]:
            row["categories"].append("Withdrawal")


def _aggregate_awards(db, start_dt, end_dt, date_rows):
    direct_results = db.query(UserAwardProgress, DirectAwardTier)\
        .outerjoin(DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id)\
        .filter(
            UserAwardProgress.achievement_date.isnot(None),
            UserAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            UserAwardProgress.achievement_date >= start_dt,
            UserAwardProgress.achievement_date <= end_dt,
            UserAwardProgress.processed_status != AwardStatus.REJECTED.value
        ).all()

    for prog, tier in direct_results:
        cost = _cost_priority(prog.actual_cost_paid, prog.budgeted_amount, tier.actual_price if tier else None)
        dk = prog.achievement_date.strftime("%Y-%m-%d")
        dd = prog.achievement_date.strftime("%d %b %Y")
        row = _ensure_date_row(date_rows, dk, dd)
        row["awards_amount"] += cost
        row["liability"] += cost
        row["liability_count"] += 1
        row["payable"] += cost
        if "Award" not in row["categories"]:
            row["categories"].append("Award")

    matching_results = db.query(UserMatchingAwardProgress, MatchingAwardTier)\
        .outerjoin(MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id)\
        .filter(
            UserMatchingAwardProgress.achievement_date.isnot(None),
            UserMatchingAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            UserMatchingAwardProgress.achievement_date >= start_dt,
            UserMatchingAwardProgress.achievement_date <= end_dt,
            UserMatchingAwardProgress.processed_status != AwardStatus.REJECTED.value
        ).all()

    for prog, tier in matching_results:
        cost = _cost_priority(prog.actual_cost_paid, prog.budgeted_amount, tier.actual_price if tier else None)
        dk = prog.achievement_date.strftime("%Y-%m-%d")
        dd = prog.achievement_date.strftime("%d %b %Y")
        row = _ensure_date_row(date_rows, dk, dd)
        row["awards_amount"] += cost
        row["liability"] += cost
        row["liability_count"] += 1
        row["payable"] += cost
        if "Award" not in row["categories"]:
            row["categories"].append("Award")


def _aggregate_bonanza(db, start_dt, end_dt, date_rows):
    results = db.query(DynamicBonanzaHistory)\
        .filter(
            DynamicBonanzaHistory.claimed_at >= start_dt,
            DynamicBonanzaHistory.claimed_at <= end_dt,
            DynamicBonanzaHistory.processed_status != AwardStatus.REJECTED.value
        ).all()

    for hist in results:
        cost = _cost_priority(hist.actual_cost_paid, hist.budgeted_amount, hist.reward_value_claimed)
        if hist.claimed_at:
            dk = hist.claimed_at.strftime("%Y-%m-%d")
            dd = hist.claimed_at.strftime("%d %b %Y")
        else:
            dk = "0000-00-00"
            dd = "Undated"
        row = _ensure_date_row(date_rows, dk, dd)
        row["liability"] += cost
        row["liability_count"] += 1
        row["payable"] += cost
        if "Bonanza" not in row["categories"]:
            row["categories"].append("Bonanza")


def _aggregate_insurance(db, date_rows, start_dt=None, end_dt=None):
    already_issued_ids = set(
        r[0] for r in db.query(MNRAccidentalInsurance.user_id).filter(
            MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
        ).all()
    )

    new_users_q = db.query(User.id, User.activation_date, User.coupon_status_changed_at).filter(
        User.coupon_status.in_(['Active', 'Activated']),
        ~User.id.in_(already_issued_ids) if already_issued_ids else True,
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date.is_(None),
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    )
    if start_dt:
        new_users_q = new_users_q.filter(
            or_(
                User.activation_date >= start_dt,
                and_(User.activation_date.is_(None), User.coupon_status_changed_at >= start_dt)
            )
        )
    if end_dt:
        new_users_q = new_users_q.filter(
            or_(
                User.activation_date <= end_dt,
                and_(User.activation_date.is_(None), User.coupon_status_changed_at <= end_dt)
            )
        )
    new_users = new_users_q.all()

    Referrer = aliased(User)
    Referral = aliased(User)
    old_user_refs_q = db.query(
        Referrer.id,
        Referrer.activation_date,
        Referrer.coupon_status_changed_at,
        func.count(Referral.id).label('ref_count')
    ).outerjoin(
        Referral,
        and_(
            Referral.referrer_id == Referrer.id,
            Referral.coupon_status.in_(['Active', 'Activated']),
            or_(
                Referral.activation_date >= INSURANCE_ELIGIBILITY_DATE,
                and_(
                    Referral.activation_date.is_(None),
                    Referral.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
                )
            )
        )
    ).filter(
        Referrer.coupon_status.in_(['Active', 'Activated']),
        ~Referrer.id.in_(already_issued_ids) if already_issued_ids else True,
        or_(
            Referrer.activation_date < INSURANCE_ELIGIBILITY_DATE,
            and_(
                Referrer.activation_date.is_(None),
                or_(
                    Referrer.coupon_status_changed_at < INSURANCE_ELIGIBILITY_DATE,
                    Referrer.coupon_status_changed_at.is_(None)
                )
            )
        )
    ).group_by(Referrer.id, Referrer.activation_date, Referrer.coupon_status_changed_at)\
     .having(func.count(Referral.id) >= REQUIRED_REFERRALS_FOR_OLD_USERS)

    old_user_refs = old_user_refs_q.all()

    start_date_obj = start_dt.date() if start_dt else None
    end_date_obj = end_dt.date() if end_dt else None

    seen_ids = set()
    date_map = {}

    for uid, act_date, status_date in new_users:
        if uid in seen_ids:
            continue
        seen_ids.add(uid)
        d = act_date or status_date
        if d:
            dk = d.strftime("%Y-%m-%d")
            dd = d.strftime("%d %b %Y")
        else:
            dk = "0000-00-00"
            dd = "Undated"
        if dk not in date_map:
            date_map[dk] = {"display": dd, "count": 0}
        date_map[dk]["count"] += 1

    for uid, act_date, status_date, _ in old_user_refs:
        if uid in seen_ids:
            continue
        seen_ids.add(uid)
        d = act_date or status_date
        if d:
            d_date = d.date() if hasattr(d, 'date') else d
            if start_date_obj and d_date < start_date_obj:
                continue
            if end_date_obj and d_date > end_date_obj:
                continue
            dk = d.strftime("%Y-%m-%d")
            dd = d.strftime("%d %b %Y")
        else:
            dk = "0000-00-00"
            dd = "Undated"
        if dk not in date_map:
            date_map[dk] = {"display": dd, "count": 0}
        date_map[dk]["count"] += 1

    for dk, info in date_map.items():
        row = _ensure_date_row(date_rows, dk, info["display"])
        cost = info["count"] * INSURANCE_PREMIUM_PER_USER
        row["insurance"] += cost
        row["liability"] += cost
        row["liability_count"] += info["count"]
        row["payable"] += cost
        if "Insurance" not in row["categories"]:
            row["categories"].append("Insurance")


def _get_revenue_detail(db, target_date, day_start, day_end):
    results = db.query(PINPurchaseRequest, User)\
        .outerjoin(User, PINPurchaseRequest.user_id == User.id)\
        .filter(
            PINPurchaseRequest.status.in_(['Approved', 'Fulfilled']),
            PINPurchaseRequest.request_date >= day_start,
            PINPurchaseRequest.request_date <= day_end
        ).order_by(desc(PINPurchaseRequest.request_date)).all()

    entries = []
    for pin, user in results:
        entries.append({
            "user_id": pin.user_id,
            "user_name": user.name if user else "-",
            "description": f"PIN Purchase ({pin.quantity} x {pin.package_value:,})",
            "amount": _safe_float(pin.total_amount),
            "status": pin.status,
            "time": pin.request_date.strftime("%H:%M") if pin.request_date else "-"
        })

    return {
        "success": True,
        "date": target_date.strftime("%d %b %Y"),
        "type": "revenue",
        "total": sum(e["amount"] for e in entries),
        "count": len(entries),
        "entries": entries
    }


def _get_payable_detail(db, target_date, day_start, day_end):
    sections = []

    income_results = db.query(PendingIncome, User)\
        .outerjoin(User, PendingIncome.user_id == User.id)\
        .filter(
            PendingIncome.business_date >= day_start,
            PendingIncome.business_date <= day_end,
            PendingIncome.verification_status != 'Rejected'
        ).order_by(desc(PendingIncome.business_date)).all()

    if income_results:
        income_entries = []
        for pi, user in income_results:
            gross = _safe_float(pi.gross_amount)
            admin_ded = _safe_float(pi.admin_deduction)
            tds_ded = _safe_float(pi.tds_deduction)
            guru_ded = _safe_float(pi.gurudakshina_deduction)
            net_payout = gross - admin_ded
            income_entries.append({
                "user_id": pi.user_id,
                "user_name": user.name if user else "-",
                "description": pi.income_type,
                "amount_gross": gross,
                "amount": net_payout,
                "admin_deduction": admin_ded,
                "tds_deduction": tds_ded,
                "guru_dakshina": guru_ded,
                "net_amount": _safe_float(pi.net_amount),
                "status": pi.verification_status or "Pending",
                "time": pi.business_date.strftime("%H:%M") if pi.business_date else "-"
            })
        total_gross = sum(e["amount_gross"] for e in income_entries)
        total_admin = sum(e["admin_deduction"] for e in income_entries)
        total_net_payout = sum(e["amount"] for e in income_entries)
        sections.append({
            "title": "Income Payouts",
            "icon": "fas fa-hand-holding-usd",
            "color": "#f97316",
            "total": total_net_payout,
            "total_gross": total_gross,
            "total_admin_deduction": total_admin,
            "count": len(income_entries),
            "entries": income_entries,
            "link": "/staff/mnr/income-unified",
            "has_breakdown": True
        })

    wr_results = db.query(WithdrawalRequest, User)\
        .outerjoin(User, WithdrawalRequest.user_id == User.id)\
        .filter(
            WithdrawalRequest.status.in_(['Approved', 'Paid', 'Completed']),
            WithdrawalRequest.request_date == target_date
        ).order_by(desc(WithdrawalRequest.request_date)).all()

    if wr_results:
        wr_entries = []
        for wr, user in wr_results:
            wr_entries.append({
                "user_id": wr.user_id,
                "user_name": user.name if user else "-",
                "description": f"Gross: {wr.withdrawal_amount:,}, Charges: {wr.admin_charges:,}, TDS: {wr.tds_amount:,}",
                "amount": _safe_float(wr.final_payout),
                "status": wr.status,
                "time": "-"
            })
        sections.append({
            "title": "Withdrawals",
            "icon": "fas fa-money-bill-transfer",
            "color": "#ef4444",
            "total": sum(e["amount"] for e in wr_entries),
            "count": len(wr_entries),
            "entries": wr_entries,
            "link": "/staff/mnr/income-unified"
        })

    direct_awards = db.query(UserAwardProgress, User, DirectAwardTier)\
        .outerjoin(User, UserAwardProgress.user_id == User.id)\
        .outerjoin(DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id)\
        .filter(
            UserAwardProgress.achievement_date.isnot(None),
            UserAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            UserAwardProgress.achievement_date >= day_start,
            UserAwardProgress.achievement_date <= day_end,
            UserAwardProgress.processed_status != AwardStatus.REJECTED.value
        ).all()

    matching_awards = db.query(UserMatchingAwardProgress, User, MatchingAwardTier)\
        .outerjoin(User, UserMatchingAwardProgress.user_id == User.id)\
        .outerjoin(MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id)\
        .filter(
            UserMatchingAwardProgress.achievement_date.isnot(None),
            UserMatchingAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            UserMatchingAwardProgress.achievement_date >= day_start,
            UserMatchingAwardProgress.achievement_date <= day_end,
            UserMatchingAwardProgress.processed_status != AwardStatus.REJECTED.value
        ).all()

    award_entries = []
    for prog, user, tier in direct_awards:
        cost = _cost_priority(prog.actual_cost_paid, prog.budgeted_amount, tier.actual_price if tier else None)
        award_entries.append({
            "user_id": prog.user_id,
            "user_name": user.name if user else "-",
            "description": f"Direct: {tier.award_name if tier else 'Award'}",
            "amount": cost,
            "status": prog.processed_status,
            "time": prog.achievement_date.strftime("%H:%M") if prog.achievement_date else "-"
        })
    for prog, user, tier in matching_awards:
        cost = _cost_priority(prog.actual_cost_paid, prog.budgeted_amount, tier.actual_price if tier else None)
        award_entries.append({
            "user_id": prog.user_id,
            "user_name": user.name if user else "-",
            "description": f"Matching: {tier.award_name if tier else 'Award'}",
            "amount": cost,
            "status": prog.processed_status,
            "time": prog.achievement_date.strftime("%H:%M") if prog.achievement_date else "-"
        })

    if award_entries:
        sections.append({
            "title": "Award Liabilities",
            "icon": "fas fa-trophy",
            "color": "#eab308",
            "total": sum(e["amount"] for e in award_entries),
            "count": len(award_entries),
            "entries": award_entries,
            "link": "/staff/mnr/awards-management"
        })

    bonanza_results = db.query(DynamicBonanzaHistory, User, DynamicBonanza)\
        .outerjoin(User, DynamicBonanzaHistory.user_id == User.id)\
        .outerjoin(DynamicBonanza, DynamicBonanzaHistory.bonanza_id == DynamicBonanza.id)\
        .filter(
            DynamicBonanzaHistory.claimed_at >= day_start,
            DynamicBonanzaHistory.claimed_at <= day_end,
            DynamicBonanzaHistory.processed_status != AwardStatus.REJECTED.value
        ).all()

    if bonanza_results:
        bonanza_entries = []
        for hist, user, bonanza in bonanza_results:
            cost = _cost_priority(hist.actual_cost_paid, hist.budgeted_amount, hist.reward_value_claimed)
            bonanza_entries.append({
                "user_id": hist.user_id,
                "user_name": user.name if user else "-",
                "description": f"{bonanza.title if bonanza else 'Bonanza'} - {hist.award_name or hist.reward_type or ''}",
                "amount": cost,
                "status": hist.processed_status,
                "time": hist.claimed_at.strftime("%H:%M") if hist.claimed_at else "-"
            })
        sections.append({
            "title": "Bonanza Liabilities",
            "icon": "fas fa-gift",
            "color": "#3b82f6",
            "total": sum(e["amount"] for e in bonanza_entries),
            "count": len(bonanza_entries),
            "entries": bonanza_entries,
            "link": "/staff/mnr/awards-management"
        })

    insurance_entries = _get_insurance_detail_for_date(db, target_date, day_start, day_end)
    if insurance_entries:
        sections.append({
            "title": "Insurance Liabilities",
            "icon": "fas fa-shield-halved",
            "color": "#a855f7",
            "total": sum(e["amount"] for e in insurance_entries),
            "count": len(insurance_entries),
            "entries": insurance_entries,
            "link": "/staff/incentives/points"
        })

    grand_total = sum(s["total"] for s in sections)

    return {
        "success": True,
        "date": target_date.strftime("%d %b %Y"),
        "type": "payable",
        "total": grand_total,
        "sections": sections
    }


def _get_insurance_detail_for_date(db, target_date, day_start, day_end):
    new_users = db.query(User).filter(
        User.coupon_status.in_(['Active', 'Activated']),
        or_(
            and_(
                User.activation_date >= day_start,
                User.activation_date <= day_end
            ),
            and_(
                User.activation_date.is_(None),
                User.coupon_status_changed_at >= day_start,
                User.coupon_status_changed_at <= day_end
            )
        ),
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date.is_(None),
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    ).all()

    already_issued_ids = set(
        r[0] for r in db.query(MNRAccidentalInsurance.user_id).filter(
            MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
        ).all()
    )

    entries = []
    seen_ids = set()
    for u in new_users:
        if u.id in seen_ids or u.id in already_issued_ids:
            continue
        seen_ids.add(u.id)
        act_date = u.activation_date or u.coupon_status_changed_at
        entries.append({
            "user_id": u.id,
            "user_name": u.name or "-",
            "description": "Insurance Premium - Eligible",
            "amount": INSURANCE_PREMIUM_PER_USER,
            "status": "Eligible",
            "time": act_date.strftime("%H:%M") if act_date else "-"
        })

    return entries


def _calculate_awards_liability_total(db, start_dt, end_dt):
    total = 0
    direct_results = db.query(UserAwardProgress, DirectAwardTier)\
        .outerjoin(DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id)\
        .filter(
            UserAwardProgress.achievement_date.isnot(None),
            UserAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            UserAwardProgress.achievement_date >= start_dt,
            UserAwardProgress.achievement_date <= end_dt,
            UserAwardProgress.processed_status != AwardStatus.REJECTED.value
        ).all()
    for prog, tier in direct_results:
        cost = _cost_priority(prog.actual_cost_paid, prog.budgeted_amount, tier.actual_price if tier else None)
        total += cost

    matching_results = db.query(UserMatchingAwardProgress, MatchingAwardTier)\
        .outerjoin(MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id)\
        .filter(
            UserMatchingAwardProgress.achievement_date.isnot(None),
            UserMatchingAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            UserMatchingAwardProgress.achievement_date >= start_dt,
            UserMatchingAwardProgress.achievement_date <= end_dt,
            UserMatchingAwardProgress.processed_status != AwardStatus.REJECTED.value
        ).all()
    for prog, tier in matching_results:
        cost = _cost_priority(prog.actual_cost_paid, prog.budgeted_amount, tier.actual_price if tier else None)
        total += cost
    return total


def _calculate_bonanza_liability_total(db, start_dt, end_dt):
    results = db.query(DynamicBonanzaHistory)\
        .filter(
            DynamicBonanzaHistory.claimed_at >= start_dt,
            DynamicBonanzaHistory.claimed_at <= end_dt,
            DynamicBonanzaHistory.processed_status != AwardStatus.REJECTED.value
        ).all()
    total = 0
    for hist in results:
        cost = _cost_priority(hist.actual_cost_paid, hist.budgeted_amount, hist.reward_value_claimed)
        total += cost
    return total


def _calculate_insurance_liability(db, start_dt=None, end_dt=None):
    already_issued_ids = set(
        r[0] for r in db.query(MNRAccidentalInsurance.user_id).filter(
            MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
        ).all()
    )

    new_q = db.query(func.count(User.id)).filter(
        User.coupon_status.in_(['Active', 'Activated']),
        ~User.id.in_(already_issued_ids) if already_issued_ids else True,
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date.is_(None),
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    )
    if start_dt:
        new_q = new_q.filter(
            or_(
                User.activation_date >= start_dt,
                and_(User.activation_date.is_(None), User.coupon_status_changed_at >= start_dt)
            )
        )
    if end_dt:
        new_q = new_q.filter(
            or_(
                User.activation_date <= end_dt,
                and_(User.activation_date.is_(None), User.coupon_status_changed_at <= end_dt)
            )
        )
    new_eligible = new_q.scalar() or 0

    Referrer = aliased(User)
    Referral = aliased(User)
    old_q = db.query(Referrer.id, Referrer.activation_date, Referrer.coupon_status_changed_at)\
        .outerjoin(
            Referral,
            and_(
                Referral.referrer_id == Referrer.id,
                Referral.coupon_status.in_(['Active', 'Activated']),
                or_(
                    Referral.activation_date >= INSURANCE_ELIGIBILITY_DATE,
                    and_(
                        Referral.activation_date.is_(None),
                        Referral.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
                    )
                )
            )
        ).filter(
            Referrer.coupon_status.in_(['Active', 'Activated']),
            ~Referrer.id.in_(already_issued_ids) if already_issued_ids else True,
            or_(
                Referrer.activation_date < INSURANCE_ELIGIBILITY_DATE,
                and_(
                    Referrer.activation_date.is_(None),
                    or_(
                        Referrer.coupon_status_changed_at < INSURANCE_ELIGIBILITY_DATE,
                        Referrer.coupon_status_changed_at.is_(None)
                    )
                )
            )
        ).group_by(Referrer.id, Referrer.activation_date, Referrer.coupon_status_changed_at)\
         .having(func.count(Referral.id) >= REQUIRED_REFERRALS_FOR_OLD_USERS).all()

    start_date_obj = start_dt.date() if start_dt else None
    end_date_obj = end_dt.date() if end_dt else None
    old_eligible = 0
    for uid, act_date, status_date in old_q:
        d = act_date or status_date
        if d:
            d_date = d.date() if hasattr(d, 'date') else d
            if start_date_obj and d_date < start_date_obj:
                continue
            if end_date_obj and d_date > end_date_obj:
                continue
        old_eligible += 1

    eligible_count = new_eligible + old_eligible
    already_issued = len(already_issued_ids)
    return {
        "eligible_count": eligible_count,
        "issued_count": already_issued,
        "total_eligible": new_eligible + old_eligible,
        "total_cost": eligible_count * INSURANCE_PREMIUM_PER_USER
    }


# ==================== NEW ACCOUNTS MODULE TABS (Expenses, P&L, Cash Holding) ====================

@router.get("/expenses")
async def get_expenses_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Executive view of company-wise expense entries.
    Restricted to VGK Supreme (same as other financial statement tabs).
    Shows breakdown by status: APPROVED, SUBMITTED, DRAFT.
    """
    _staff_only_check(current_user)
    start_date, end_date, start_dt, end_dt = _parse_dates(date_from, date_to)

    q = db.query(
        ExpenseEntry.company_id,
        ExpenseEntry.main_category_id,
        ExpenseEntry.status,
        func.count(ExpenseEntry.id).label('count'),
        func.coalesce(func.sum(ExpenseEntry.amount), 0).label('total')
    ).filter(
        ExpenseEntry.expense_date >= start_date,
        ExpenseEntry.expense_date <= end_date
    )
    if company_id:
        q = q.filter(ExpenseEntry.company_id == company_id)
    rows = q.group_by(ExpenseEntry.company_id, ExpenseEntry.main_category_id, ExpenseEntry.status).all()

    companies = db.query(AssociatedCompany).all()
    company_map = {c.id: c.company_name for c in companies}

    categories = db.query(ExpenseMainCategory).all()
    cat_map = {c.id: c.name for c in categories}

    summary = {}
    for row in rows:
        cid = row.company_id
        if cid not in summary:
            summary[cid] = {
                "company_id": cid,
                "company_name": company_map.get(cid, f"Company {cid}"),
                "approved": 0.0,
                "submitted": 0.0,
                "draft": 0.0,
                "total": 0.0,
                "approved_count": 0,
                "categories": {}
            }
        amt = float(row.total)
        status_lower = (row.status or '').lower()
        if status_lower == 'approved':
            summary[cid]['approved'] += amt
            summary[cid]['approved_count'] += row.count
        elif status_lower == 'submitted':
            summary[cid]['submitted'] += amt
        elif status_lower == 'draft':
            summary[cid]['draft'] += amt
        summary[cid]['total'] += amt

        cat_name = cat_map.get(row.main_category_id, 'Uncategorized')
        if cat_name not in summary[cid]['categories']:
            summary[cid]['categories'][cat_name] = {'approved': 0.0, 'submitted': 0.0, 'draft': 0.0, 'total': 0.0}
        summary[cid]['categories'][cat_name][status_lower if status_lower in ('approved','submitted','draft') else 'draft'] += amt
        summary[cid]['categories'][cat_name]['total'] += amt

    for cid in summary:
        summary[cid]['categories'] = [
            {"category": k, **v} for k, v in summary[cid]['categories'].items()
        ]

    totals = {
        "total_approved": round(sum(v['approved'] for v in summary.values()), 2),
        "total_submitted": round(sum(v['submitted'] for v in summary.values()), 2),
        "total_draft": round(sum(v['draft'] for v in summary.values()), 2),
        "total_all": round(sum(v['total'] for v in summary.values()), 2)
    }

    return {
        "success": True,
        "date_from": str(start_date),
        "date_to": str(end_date),
        "company_breakdown": list(summary.values()),
        "totals": totals
    }


@router.get("/pnl")
async def get_profit_and_loss(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Profit & Loss statement.
    Revenue: PIN purchases + income entries (CONFIRMED/TALLY_DONE) + MNR income (PendingIncome).
    Expenses: ExpenseEntry (APPROVED only, as per DC rules).
    Net P&L = Total Revenue - Total Approved Expenses.
    Company filter available.
    """
    _staff_only_check(current_user)
    start_date, end_date, start_dt, end_dt = _parse_dates(date_from, date_to)

    # Revenue 1: PIN purchases (platform-wide, not company-specific)
    pin_revenue = 0.0
    if not company_id:
        pin_revenue = float(db.query(
            func.coalesce(func.sum(PINPurchaseRequest.total_amount), 0)
        ).filter(
            PINPurchaseRequest.status.in_(['Approved', 'Fulfilled']),
            PINPurchaseRequest.request_date >= start_dt,
            PINPurchaseRequest.request_date <= end_dt
        ).scalar() or 0)

    # Revenue 2: MNR income distributions (PendingIncome)
    mnr_income_total = 0.0
    if not company_id:
        mnr_income_total = float(db.query(
            func.coalesce(func.sum(PendingIncome.gross_amount), 0)
        ).filter(
            PendingIncome.business_date >= start_dt,
            PendingIncome.business_date <= end_dt,
            PendingIncome.verification_status != 'Rejected'
        ).scalar() or 0)

    # Revenue 3: Accounts module income entries (CONFIRMED or TALLY_DONE)
    ie_q = db.query(
        IncomeEntry.company_id,
        func.coalesce(func.sum(IncomeEntry.amount), 0).label('total')
    ).filter(
        IncomeEntry.income_date >= start_date,
        IncomeEntry.income_date <= end_date,
        IncomeEntry.status.in_(['CONFIRMED', 'TALLY_DONE', 'EXCEPTION_TALLY'])
    )
    if company_id:
        ie_q = ie_q.filter(IncomeEntry.company_id == company_id)
    ie_rows = ie_q.group_by(IncomeEntry.company_id).all()
    income_by_company = {r.company_id: float(r.total) for r in ie_rows}

    # Expenses: Only APPROVED expense entries count
    exp_q = db.query(
        ExpenseEntry.company_id,
        func.coalesce(func.sum(ExpenseEntry.amount), 0).label('total')
    ).filter(
        ExpenseEntry.expense_date >= start_date,
        ExpenseEntry.expense_date <= end_date,
        ExpenseEntry.status == 'APPROVED'
    )
    if company_id:
        exp_q = exp_q.filter(ExpenseEntry.company_id == company_id)
    exp_rows = exp_q.group_by(ExpenseEntry.company_id).all()
    expenses_by_company = {r.company_id: float(r.total) for r in exp_rows}

    # Pending expenses (not yet approved) — informational
    pending_q = db.query(
        ExpenseEntry.company_id,
        func.coalesce(func.sum(ExpenseEntry.amount), 0).label('total')
    ).filter(
        ExpenseEntry.expense_date >= start_date,
        ExpenseEntry.expense_date <= end_date,
        ExpenseEntry.status.in_(['SUBMITTED', 'DRAFT'])
    )
    if company_id:
        pending_q = pending_q.filter(ExpenseEntry.company_id == company_id)
    pending_rows = pending_q.group_by(ExpenseEntry.company_id).all()
    pending_by_company = {r.company_id: float(r.total) for r in pending_rows}

    companies = db.query(AssociatedCompany).all()
    company_map = {c.id: c.company_name for c in companies}

    all_company_ids = set(income_by_company.keys()) | set(expenses_by_company.keys())
    if company_id:
        all_company_ids.add(company_id)

    company_pnl = []
    total_income_entries = 0.0
    total_expenses = 0.0
    total_pending_expenses = 0.0

    for cid in all_company_ids:
        inc = income_by_company.get(cid, 0.0)
        exp = expenses_by_company.get(cid, 0.0)
        pend = pending_by_company.get(cid, 0.0)
        net = round(inc - exp, 2)
        net_after_pending = round(inc - exp - pend, 2)
        total_income_entries += inc
        total_expenses += exp
        total_pending_expenses += pend
        company_pnl.append({
            "company_id": cid,
            "company_name": company_map.get(cid, f"Company {cid}"),
            "revenue_income_entries": round(inc, 2),
            "expenses_approved": round(exp, 2),
            "expenses_pending": round(pend, 2),
            "net_pnl": net,
            "net_pnl_worst_case": net_after_pending
        })

    total_revenue = pin_revenue + mnr_income_total + total_income_entries
    total_net_pnl = round(total_revenue - total_expenses, 2)
    total_net_worst = round(total_revenue - total_expenses - total_pending_expenses, 2)

    return {
        "success": True,
        "date_from": str(start_date),
        "date_to": str(end_date),
        "company_id_filter": company_id,
        "revenue": {
            "pin_revenue": round(pin_revenue, 2),
            "mnr_income_distributions": round(mnr_income_total, 2),
            "accounts_income_entries": round(total_income_entries, 2),
            "total_revenue": round(total_revenue, 2)
        },
        "expenses": {
            "total_approved": round(total_expenses, 2),
            "total_pending": round(total_pending_expenses, 2),
            "total_all": round(total_expenses + total_pending_expenses, 2)
        },
        "net_pnl": total_net_pnl,
        "net_pnl_worst_case": total_net_worst,
        "company_breakdown": company_pnl
    }


@router.get("/cash-holding")
async def get_cash_holding(
    company_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Search by employee name"),
    include_company_accounts: bool = Query(True),
    include_employee_accounts: bool = Query(True),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Cash holding summary - employee-wise and company-wise.
    Shows for each holder: available_balance, approved_expenses, pending_submitted, pending_draft.
    Restricted to VGK Supreme executive access.
    """
    _staff_only_check(current_user)

    from sqlalchemy import text as _text, or_ as _or

    result = {"success": True, "employee_holdings": [], "company_holdings": []}

    if include_employee_accounts:
        # Get all employees with their latest ledger balance
        ledger_sub = db.query(
            EmployeeFundLedger.employee_id,
            func.max(EmployeeFundLedger.id).label('last_id')
        ).group_by(EmployeeFundLedger.employee_id).subquery()

        latest_entries = db.query(EmployeeFundLedger).join(
            ledger_sub,
            and_(
                EmployeeFundLedger.employee_id == ledger_sub.c.employee_id,
                EmployeeFundLedger.id == ledger_sub.c.last_id
            )
        ).all()

        emp_ids = [e.employee_id for e in latest_entries]
        emps = db.query(StaffEmployee).filter(StaffEmployee.id.in_(emp_ids)).all()
        emp_map = {e.id: e for e in emps}

        from app.models.staff_accounts import ExpenseEntry as _EE, FundAllocation as _FA

        emp_holdings = []
        for le in latest_entries:
            emp = emp_map.get(le.employee_id)
            if not emp:
                continue
            emp_name = f"{getattr(emp, 'first_name', '')} {getattr(emp, 'last_name', '')}".strip()
            if search and search.lower() not in emp_name.lower():
                continue

            def _exp_sum(st):
                q = db.query(func.coalesce(func.sum(_EE.amount), 0)).join(
                    _FA, _EE.fund_allocation_id == _FA.id, isouter=True
                ).filter(
                    _or(
                        _FA.to_employee_id == le.employee_id,
                        _EE.created_by_id == le.employee_id
                    ),
                    _EE.status == st
                )
                if company_id:
                    q = q.filter(_EE.company_id == company_id)
                return float(q.scalar() or 0)

            approved_exp = _exp_sum('APPROVED')
            submitted_exp = _exp_sum('SUBMITTED')
            draft_exp = _exp_sum('DRAFT')
            available_bal = float(le.balance)

            emp_holdings.append({
                "employee_id": le.employee_id,
                "employee_name": emp_name,
                "emp_code": getattr(emp, 'emp_code', ''),
                "available_balance": available_bal,
                "total_approved_expenses": approved_exp,
                "pending_submitted": submitted_exp,
                "pending_draft": draft_exp,
                "effective_balance": round(available_bal - submitted_exp, 2),
                "worst_case_balance": round(available_bal - submitted_exp - draft_exp, 2)
            })

        emp_holdings.sort(key=lambda x: abs(x['available_balance']), reverse=True)
        result["employee_holdings"] = emp_holdings
        result["employee_totals"] = {
            "total_available": round(sum(h['available_balance'] for h in emp_holdings), 2),
            "total_approved_expenses": round(sum(h['total_approved_expenses'] for h in emp_holdings), 2),
            "total_pending_submitted": round(sum(h['pending_submitted'] for h in emp_holdings), 2),
            "total_pending_draft": round(sum(h['pending_draft'] for h in emp_holdings), 2)
        }

    if include_company_accounts:
        company_ledger_rows = db.execute(_text("""
            SELECT
                cal.company_id,
                ac.company_name,
                MAX(cal.id) as last_id,
                (SELECT balance FROM company_account_ledger WHERE id = MAX(cal.id)) as balance,
                SUM(cal.credit_amount) as total_credits,
                SUM(cal.debit_amount) as total_debits
            FROM company_account_ledger cal
            JOIN associated_companies ac ON ac.id = cal.company_id
            GROUP BY cal.company_id, ac.company_name
            ORDER BY balance DESC
        """)).fetchall()

        company_holdings = []
        for row in company_ledger_rows:
            if company_id and row.company_id != company_id:
                continue
            company_holdings.append({
                "company_id": row.company_id,
                "company_name": row.company_name,
                "available_balance": float(row.balance or 0),
                "total_credits": float(row.total_credits or 0),
                "total_debits": float(row.total_debits or 0)
            })

        result["company_holdings"] = company_holdings
        result["company_totals"] = {
            "total_available": round(sum(h['available_balance'] for h in company_holdings), 2),
            "total_credits": round(sum(h['total_credits'] for h in company_holdings), 2),
            "total_debits": round(sum(h['total_debits'] for h in company_holdings), 2)
        }

    return result


# ─────────────────────────────────────────────────────────────────────────────
# VGK4U Partner Commissions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/vgk-commissions")
def get_vgk_commissions(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    level: Optional[int] = Query(None, description="1, 2, 3, or 4"),
    status: Optional[str] = Query(None, description="PENDING, CONFIRMED, CANCELLED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user=Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """VGK4U partner commission entries — consolidated with company/category/level filters."""
    _staff_only_check(current_user)
    from app.models.staff_accounts import VGKTeamIncomeEntry, OfficialPartner
    from app.models.signup_category import SignupCategory

    start_date, end_date, start_dt, end_dt = _parse_dates(date_from, date_to)

    q = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.created_at >= start_dt,
        VGKTeamIncomeEntry.created_at <= end_dt
    )
    if company_id:
        q = q.filter(VGKTeamIncomeEntry.company_id == company_id)
    if category_id:
        q = q.filter(VGKTeamIncomeEntry.category_id == category_id)
    if level is not None:
        q = q.filter(VGKTeamIncomeEntry.level == level)
    if status:
        q = q.filter(VGKTeamIncomeEntry.status == status.upper())

    entries = q.order_by(VGKTeamIncomeEntry.created_at.desc()).all()

    partner_ids = list({e.partner_id for e in entries if e.partner_id})
    partners = db.query(OfficialPartner).filter(OfficialPartner.id.in_(partner_ids)).all() if partner_ids else []
    partner_map = {p.id: {"code": p.partner_code, "name": p.partner_name} for p in partners}

    cat_ids = list({e.category_id for e in entries if e.category_id})
    categories_q = db.query(SignupCategory).filter(SignupCategory.id.in_(cat_ids)).all() if cat_ids else []
    cat_map = {c.id: c.name for c in categories_q}

    companies_all = db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
    company_map = {c.id: {"id": c.id, "name": c.company_name, "code": c.company_code} for c in companies_all}

    total_pending = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.status == 'PENDING')
    total_confirmed = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.status == 'CONFIRMED')
    total_cancelled = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.status == 'CANCELLED')
    l1_total = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.level == 1 and e.status != 'CANCELLED')
    l2_total = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.level == 2 and e.status != 'CANCELLED')
    l3_total = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.level == 3 and e.status != 'CANCELLED')
    l4_total = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.level == 4 and e.status != 'CANCELLED')
    total_bonus = sum(_safe_float(e.bonus_amount) for e in entries if e.status != 'CANCELLED')
    total_active = sum(_safe_float(e.commission_amount) + _safe_float(e.bonus_amount) for e in entries if e.status != 'CANCELLED')

    company_totals = {}
    for e in entries:
        if e.status == 'CANCELLED':
            continue
        cid = e.company_id
        if cid not in company_totals:
            info = company_map.get(cid, {"id": cid, "name": "Company " + str(cid), "code": ""})
            company_totals[cid] = {**info, "total": 0.0, "pending": 0.0, "confirmed": 0.0, "l1": 0.0, "l2": 0.0, "l3": 0.0, "l4": 0.0}
        amt = _safe_float(e.commission_amount) + _safe_float(e.bonus_amount)
        company_totals[cid]["total"] += amt
        if e.status == 'PENDING':
            company_totals[cid]["pending"] += amt
        elif e.status == 'CONFIRMED':
            company_totals[cid]["confirmed"] += amt
        if e.level == 1:
            company_totals[cid]["l1"] += amt
        elif e.level == 2:
            company_totals[cid]["l2"] += amt
        elif e.level == 3:
            company_totals[cid]["l3"] += amt
        elif e.level == 4:
            company_totals[cid]["l4"] += amt

    total_count = len(entries)
    offset = (page - 1) * page_size
    paginated = entries[offset:offset + page_size]

    rows = []
    for e in paginated:
        p_info = partner_map.get(e.partner_id, {"code": "\u2014", "name": "\u2014"}) if e.partner_id else {"code": "\u2014", "name": "\u2014"}
        rows.append({
            "id": e.id,
            "entry_number": e.entry_number,
            "company_id": e.company_id,
            "company_name": company_map.get(e.company_id, {}).get("name", ""),
            "partner_code": p_info["code"],
            "partner_name": p_info["name"],
            "category": cat_map.get(e.category_id, "\u2014") if e.category_id else "\u2014",
            "level": e.level,
            "revenue_amount": _safe_float(e.revenue_amount),
            "commission_pct": _safe_float(e.commission_pct),
            "commission_amount": _safe_float(e.commission_amount),
            "bonus_amount": _safe_float(e.bonus_amount),
            "total_payable": _safe_float(e.commission_amount) + _safe_float(e.bonus_amount),
            "status": e.status,
            "notes": e.notes or "",
            "created_at": e.created_at.strftime("%d %b %Y %H:%M") if e.created_at else "\u2014",
            "confirmed_at": e.confirmed_at.strftime("%d %b %Y %H:%M") if e.confirmed_at else None,
        })

    all_cats = db.query(SignupCategory).filter(SignupCategory.is_active == True).order_by(SignupCategory.company_id, SignupCategory.name).all()

    return {
        "success": True,
        "summary": {
            "total_pending": round(total_pending, 2),
            "total_confirmed": round(total_confirmed, 2),
            "total_cancelled": round(total_cancelled, 2),
            "total_active": round(total_active, 2),
            "l1_total": round(l1_total, 2),
            "l2_total": round(l2_total, 2),
            "l3_total": round(l3_total, 2),
            "l4_total": round(l4_total, 2),
            "total_bonus": round(total_bonus, 2),
            "total_entries": total_count,
        },
        "company_breakdown": [
            {**v, "total": round(v["total"], 2), "pending": round(v["pending"], 2),
             "confirmed": round(v["confirmed"], 2), "l1": round(v["l1"], 2),
             "l2": round(v["l2"], 2), "l3": round(v["l3"], 2),
             "l4": round(v["l4"], 2)}
            for v in company_totals.values()
        ],
        "entries": rows,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_entries": total_count,
            "total_pages": max(1, (total_count + page_size - 1) // page_size)
        },
        "filters": {
            "date_from": str(start_date),
            "date_to": str(end_date),
            "company_id": company_id,
            "category_id": category_id,
            "level": level,
            "status": status
        },
        "companies": [{"id": c.id, "name": c.company_name, "code": c.company_code} for c in companies_all],
        "categories": [{"id": c.id, "name": c.name, "company_id": c.company_id} for c in all_cats],
    }


# ─────────────────────────────────────────────────────────────────────────────
# DAR — Daily Account Reporting
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/dar/opening-balance")
def set_dar_opening_balance(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_rvz_user_hybrid)
):
    """Set or update company opening balance in company_account_ledger."""
    _staff_only_check(current_user)
    from sqlalchemy import text as _text
    company_id = payload.get("company_id")
    amount = payload.get("amount", 0)
    narration = payload.get("narration", "Opening Balance")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id required")
    ob_date = payload.get("date", str(date.today()))
    existing = db.execute(_text(
        "SELECT id FROM company_account_ledger WHERE company_id=:cid AND entry_type='OPENING' LIMIT 1"
    ), {"cid": company_id}).fetchone()
    if existing:
        db.execute(_text("""
            UPDATE company_account_ledger
            SET credit_amount=:amt, balance=:amt, narration=:nar, transaction_date=:dt, updated_at=NOW()
            WHERE id=:eid
        """), {"amt": amount, "nar": narration, "dt": ob_date, "eid": existing.id})
    else:
        db.execute(_text("""
            INSERT INTO company_account_ledger
            (company_id, transaction_date, entry_type, reference_type, credit_amount, debit_amount, balance, narration, created_by_id)
            VALUES (:cid, :dt, 'OPENING', 'MANUAL', :amt, 0, :amt, :nar, :uid)
        """), {"cid": company_id, "dt": ob_date, "amt": amount, "nar": narration, "uid": getattr(current_user, 'id', None)})
    db.commit()
    return {"status": "ok", "company_id": company_id, "amount": float(amount)}


@router.get("/dar")
def get_dar(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_rvz_user_hybrid)
):
    """DAR — Daily Account Reporting: date-wise IN/OUT per company & category."""
    _staff_only_check(current_user)
    from sqlalchemy import text as _text
    import calendar as _cal

    today = date.today()

    fd = None
    td = None
    if from_date:
        try:
            fd = date.fromisoformat(from_date)
        except Exception:
            pass
    if to_date:
        try:
            td = date.fromisoformat(to_date)
        except Exception:
            pass

    # ── Companies ──────────────────────────────────────────────────────────
    companies_rows = db.execute(_text(
        "SELECT id, company_name, company_code FROM associated_companies WHERE is_active=true ORDER BY company_name"
    )).fetchall()
    company_ids = [r.id for r in companies_rows]
    company_map = {r.id: {"id": r.id, "name": r.company_name, "code": r.company_code} for r in companies_rows}

    # ── Dynamic IN categories per company (signup_categories used in income_entries) ──
    in_cats_rows = db.execute(_text("""
        SELECT DISTINCT ie.company_id,
               COALESCE(ie.revenue_category_id, 0) AS cat_id,
               COALESCE(sc.name, 'Uncategorized') AS cat_name
        FROM income_entries ie
        LEFT JOIN signup_categories sc ON sc.id = ie.revenue_category_id
        WHERE ie.status NOT IN ('REJECTED', 'ESTIMATED')
        ORDER BY ie.company_id, cat_name
    """)).fetchall()

    # ── Dynamic OUT categories per company (expense_main_category) ──
    out_cats_rows = db.execute(_text("""
        SELECT DISTINCT ee.company_id,
               COALESCE(ee.main_category_id, 0) AS cat_id,
               COALESCE(emc.name, 'Uncategorized') AS cat_name
        FROM expense_entries ee
        LEFT JOIN expense_main_category emc ON emc.id = ee.main_category_id
        WHERE ee.status = 'APPROVED'
        ORDER BY ee.company_id, cat_name
    """)).fetchall()

    in_cat_map = {}
    for r in in_cats_rows:
        if r.company_id not in in_cat_map:
            in_cat_map[r.company_id] = []
        if not any(c["id"] == r.cat_id for c in in_cat_map[r.company_id]):
            in_cat_map[r.company_id].append({"id": r.cat_id, "name": r.cat_name})

    out_cat_map = {}
    for r in out_cats_rows:
        if r.company_id not in out_cat_map:
            out_cat_map[r.company_id] = []
        if not any(c["id"] == r.cat_id for c in out_cat_map[r.company_id]):
            out_cat_map[r.company_id].append({"id": r.cat_id, "name": r.cat_name})

    companies_list = []
    for cid in company_ids:
        c = company_map[cid]
        companies_list.append({
            "id": c["id"],
            "name": c["name"],
            "code": c["code"],
            "in_categories": in_cat_map.get(cid, []),
            "out_categories": out_cat_map.get(cid, [])
        })

    # ── Monthly Summary: last 3 months + current ──────────────────────────
    monthly_summary = []
    for i in range(3, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        ms = date(y, m, 1)
        me = date(y, m, _cal.monthrange(y, m)[1]) if i > 0 else today
        label = (ms.strftime("%b %Y") + (" (Current)" if i == 0 else ""))

        tot_in = float(db.execute(_text(
            "SELECT COALESCE(SUM(amount),0) FROM income_entries WHERE income_date>=:s AND income_date<=:e AND status NOT IN ('REJECTED','ESTIMATED')"
        ), {"s": ms, "e": me}).scalar() or 0)
        tot_out = float(db.execute(_text(
            "SELECT COALESCE(SUM(amount),0) FROM expense_entries WHERE status='APPROVED' AND expense_date>=:s AND expense_date<=:e"
        ), {"s": ms, "e": me}).scalar() or 0)

        comp_in_rows = db.execute(_text("""
            SELECT ie.company_id, ac.company_name, COALESCE(SUM(ie.amount),0) AS total_in
            FROM income_entries ie JOIN associated_companies ac ON ac.id=ie.company_id
            WHERE ie.income_date>=:s AND ie.income_date<=:e AND ie.status NOT IN ('REJECTED','ESTIMATED')
            GROUP BY ie.company_id, ac.company_name
        """), {"s": ms, "e": me}).fetchall()
        comp_out_rows = db.execute(_text("""
            SELECT ee.company_id, COALESCE(SUM(ee.amount),0) AS total_out
            FROM expense_entries ee
            WHERE ee.status='APPROVED' AND ee.expense_date>=:s AND ee.expense_date<=:e
            GROUP BY ee.company_id
        """), {"s": ms, "e": me}).fetchall()
        comp_out_dict = {r.company_id: float(r.total_out) for r in comp_out_rows}

        company_wise = []
        for r in comp_in_rows:
            ci = float(r.total_in)
            co = comp_out_dict.get(r.company_id, 0.0)
            company_wise.append({"company_id": r.company_id, "company_name": r.company_name,
                                  "total_in": ci, "total_out": co, "balance": ci - co})

        monthly_summary.append({"label": label, "total_in": tot_in, "total_out": tot_out,
                                 "balance": tot_in - tot_out, "company_wise": company_wise})

    # ── Company opening balances ──────────────────────────────────────────
    ob_rows = db.execute(_text("""
        SELECT company_id, SUM(credit_amount - debit_amount) AS ob
        FROM company_account_ledger WHERE entry_type='OPENING'
        GROUP BY company_id
    """)).fetchall()
    company_ob = {r.company_id: float(r.ob or 0) for r in ob_rows}
    total_ob = sum(company_ob.values())

    # ── Opening balance for filtered range ────────────────────────────────
    if fd:
        pre_in = float(db.execute(_text(
            "SELECT COALESCE(SUM(amount),0) FROM income_entries WHERE income_date < :fd AND status NOT IN ('REJECTED','ESTIMATED')"
        ), {"fd": fd}).scalar() or 0)
        pre_out = float(db.execute(_text(
            "SELECT COALESCE(SUM(amount),0) FROM expense_entries WHERE status='APPROVED' AND expense_date < :fd"
        ), {"fd": fd}).scalar() or 0)
        opening_balance = total_ob + pre_in - pre_out

        comp_pre_in = db.execute(_text("""
            SELECT company_id, COALESCE(SUM(amount),0) AS tot
            FROM income_entries WHERE income_date < :fd AND status NOT IN ('REJECTED','ESTIMATED') GROUP BY company_id
        """), {"fd": fd}).fetchall()
        comp_pre_out = db.execute(_text("""
            SELECT company_id, COALESCE(SUM(amount),0) AS tot
            FROM expense_entries WHERE status='APPROVED' AND expense_date < :fd GROUP BY company_id
        """), {"fd": fd}).fetchall()
        comp_pre_out_d = {r.company_id: float(r.tot or 0) for r in comp_pre_out}
        company_opening = {}
        for r in comp_pre_in:
            company_opening[r.company_id] = (company_ob.get(r.company_id, 0.0)
                                             + float(r.tot or 0)
                                             - comp_pre_out_d.get(r.company_id, 0.0))
        for cid in company_ids:
            if cid not in company_opening:
                company_opening[cid] = company_ob.get(cid, 0.0)
    else:
        opening_balance = total_ob
        company_opening = {cid: company_ob.get(cid, 0.0) for cid in company_ids}

    # ── Date-wise raw data ────────────────────────────────────────────────
    in_filter = ""
    out_filter = ""
    params_in = {}
    params_out = {}
    if fd:
        in_filter += " AND ie.income_date >= :fd"
        out_filter += " AND ee.expense_date >= :fd"
        params_in["fd"] = fd
        params_out["fd"] = fd
    if td:
        in_filter += " AND ie.income_date <= :td"
        out_filter += " AND ee.expense_date <= :td"
        params_in["td"] = td
        params_out["td"] = td

    in_data = db.execute(_text(
        "SELECT ie.income_date AS txn_date, ie.company_id,"
        " COALESCE(ie.revenue_category_id,0) AS cat_id,"
        " COALESCE(sc.name,'Uncategorized') AS cat_name,"
        " SUM(ie.amount) AS total"
        " FROM income_entries ie"
        " LEFT JOIN signup_categories sc ON sc.id=ie.revenue_category_id"
        " WHERE ie.status NOT IN ('REJECTED','ESTIMATED')" + in_filter +
        " GROUP BY ie.income_date, ie.company_id, ie.revenue_category_id, sc.name"
        " ORDER BY ie.income_date"
    ), params_in).fetchall()

    out_data = db.execute(_text(
        "SELECT ee.expense_date AS txn_date, ee.company_id,"
        " COALESCE(ee.main_category_id,0) AS cat_id,"
        " COALESCE(emc.name,'Uncategorized') AS cat_name,"
        " SUM(ee.amount) AS total"
        " FROM expense_entries ee"
        " LEFT JOIN expense_main_category emc ON emc.id=ee.main_category_id"
        " WHERE ee.status='APPROVED'" + out_filter +
        " GROUP BY ee.expense_date, ee.company_id, ee.main_category_id, emc.name"
        " ORDER BY ee.expense_date"
    ), params_out).fetchall()

    # ── Build lookup dicts ────────────────────────────────────────────────
    in_lookup = {}
    for r in in_data:
        d = str(r.txn_date)
        if d not in in_lookup:
            in_lookup[d] = {}
        if r.company_id not in in_lookup[d]:
            in_lookup[d][r.company_id] = {}
        in_lookup[d][r.company_id][r.cat_id] = float(r.total or 0)

    out_lookup = {}
    for r in out_data:
        d = str(r.txn_date)
        if d not in out_lookup:
            out_lookup[d] = {}
        if r.company_id not in out_lookup[d]:
            out_lookup[d][r.company_id] = {}
        out_lookup[d][r.company_id][r.cat_id] = float(r.total or 0)

    all_dates = sorted(set(list(in_lookup.keys()) + list(out_lookup.keys())))

    # ── Build rows with running balance ───────────────────────────────────
    running_balance = opening_balance
    company_running = dict(company_opening)
    rows = []
    for sno, d in enumerate(all_dates, 1):
        day_in_data = in_lookup.get(d, {})
        day_out_data = out_lookup.get(d, {})

        total_in_day = sum(
            sum(cats.values()) for cats in day_in_data.values()
        )
        total_out_day = sum(
            sum(cats.values()) for cats in day_out_data.values()
        )
        running_balance = running_balance + total_in_day - total_out_day

        comp_balances = {}
        for cid in company_ids:
            c_in = sum(day_in_data.get(cid, {}).values())
            c_out = sum(day_out_data.get(cid, {}).values())
            company_running[cid] = company_running.get(cid, 0.0) + c_in - c_out
            comp_balances[cid] = round(company_running[cid], 2)

        rows.append({
            "sno": sno,
            "date": d,
            "total_in": round(total_in_day, 2),
            "total_out": round(total_out_day, 2),
            "for_day": round(total_in_day - total_out_day, 2),
            "running_balance": round(running_balance, 2),
            "in_data": {str(k): {str(ck): cv for ck, cv in v.items()} for k, v in day_in_data.items()},
            "out_data": {str(k): {str(ck): cv for ck, cv in v.items()} for k, v in day_out_data.items()},
            "company_running_balances": {str(k): v for k, v in comp_balances.items()}
        })

    return {
        "companies": companies_list,
        "monthly_summary": monthly_summary,
        "opening_balance": round(opening_balance, 2),
        "company_opening_balances": {str(k): round(v, 2) for k, v in company_opening.items()},
        "company_ob_set": {str(k): round(v, 2) for k, v in company_ob.items()},
        "rows": rows,
        "total_rows": len(rows)
    }


@router.get("/dar/staff-view")
def get_dar_staff_view(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_rvz_user_hybrid)
):
    """DAR staff view — employee-wise IN collected and OUT approved expenses."""
    _staff_only_check(current_user)
    from sqlalchemy import text as _text

    fd = None
    td = None
    if from_date:
        try:
            fd = date.fromisoformat(from_date)
        except Exception:
            pass
    if to_date:
        try:
            td = date.fromisoformat(to_date)
        except Exception:
            pass

    in_filter = ""
    out_filter = ""
    params_in = {}
    params_out = {}
    if fd:
        in_filter += " AND ie.income_date >= :fd"
        out_filter += " AND ee.expense_date >= :fd"
        params_in["fd"] = fd
        params_out["fd"] = fd
    if td:
        in_filter += " AND ie.income_date <= :td"
        out_filter += " AND ee.expense_date <= :td"
        params_in["td"] = td
        params_out["td"] = td

    staff_in = db.execute(_text(
        "SELECT ie.collected_by_id AS emp_id,"
        " se.full_name, se.emp_code,"
        " COALESCE(SUM(ie.amount),0) AS total_in"
        " FROM income_entries ie"
        " JOIN staff_employees se ON se.id=ie.collected_by_id"
        " WHERE ie.collected_by_id IS NOT NULL AND ie.status NOT IN ('REJECTED','ESTIMATED')" + in_filter +
        " GROUP BY ie.collected_by_id, se.full_name, se.emp_code"
        " ORDER BY total_in DESC"
    ), params_in).fetchall()

    staff_out = db.execute(_text(
        "SELECT ee.created_by_id AS emp_id,"
        " se.full_name, se.emp_code,"
        " COALESCE(SUM(ee.amount),0) AS total_out"
        " FROM expense_entries ee"
        " JOIN staff_employees se ON se.id=ee.created_by_id"
        " WHERE ee.status='APPROVED' AND ee.created_by_id IS NOT NULL" + out_filter +
        " GROUP BY ee.created_by_id, se.full_name, se.emp_code"
        " ORDER BY total_out DESC"
    ), params_out).fetchall()

    out_dict = {r.emp_id: {"name": r.full_name, "code": r.emp_code, "total_out": float(r.total_out or 0)}
                for r in staff_out}
    in_dict = {r.emp_id: {"name": r.full_name, "code": r.emp_code, "total_in": float(r.total_in or 0)}
               for r in staff_in}

    all_emp_ids = sorted(set(list(in_dict.keys()) + list(out_dict.keys())))
    staff_rows = []
    for emp_id in all_emp_ids:
        name = (in_dict.get(emp_id) or out_dict.get(emp_id, {})).get("name", "Unknown")
        code = (in_dict.get(emp_id) or out_dict.get(emp_id, {})).get("code", "")
        ti = in_dict.get(emp_id, {}).get("total_in", 0.0)
        to_ = out_dict.get(emp_id, {}).get("total_out", 0.0)
        staff_rows.append({"emp_id": emp_id, "name": name, "code": code,
                           "total_in": round(ti, 2), "total_out": round(to_, 2),
                           "net": round(ti - to_, 2)})

    return {
        "staff": staff_rows,
        "totals": {
            "total_in": round(sum(r["total_in"] for r in staff_rows), 2),
            "total_out": round(sum(r["total_out"] for r in staff_rows), 2),
            "net": round(sum(r["net"] for r in staff_rows), 2)
        }
    }
