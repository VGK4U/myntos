"""
Staff Lead Incentive Service (DC Protocol Apr 2026)
VGK-rate-based incentive for staff who source CRM leads (field_staff_id).

Tier Logic (per employee, permanent escalation once triggered):
  Default : multiplier = 1.0 (100% of VGK L1 rate)
  Tier 1  : cumulative earned >= 5x monthly CTC → multiplier = 1.2 (120%)

Trigger  : CRM transaction validated AND lead.field_staff_id is set
Wallet   : entry lands in staff_incentive_payouts as status='pending'
           (same table used by sales-performance system — monthly rollup)
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


def _now_ist():
    return datetime.now(IST).replace(tzinfo=None)


def _get_employee_monthly_salary(db, employee_id: int) -> Decimal:
    """Fetch latest ctc_monthly from staff_payroll_profile for this employee."""
    from sqlalchemy import text
    try:
        row = db.execute(text(
            "SELECT ctc_monthly FROM staff_payroll_profile "
            "WHERE employee_id = :eid AND is_active = true "
            "ORDER BY effective_from DESC NULLS LAST, id DESC LIMIT 1"
        ), {"eid": employee_id}).fetchone()
        if row and row[0]:
            return Decimal(str(row[0]))
    except Exception:
        pass
    return Decimal("0")


def _get_or_create_tier_tracker(db, employee_id: int) -> dict:
    """Fetch tier tracker row; insert default if absent."""
    from sqlalchemy import text
    row = db.execute(text(
        "SELECT id, cumulative_earned, monthly_salary_snapshot, is_escalated "
        "FROM staff_incentive_tier_tracker WHERE employee_id = :eid"
    ), {"eid": employee_id}).fetchone()
    if row:
        return {"id": row[0], "cumulative_earned": Decimal(str(row[1] or 0)),
                "monthly_salary_snapshot": Decimal(str(row[2] or 0)),
                "is_escalated": bool(row[3])}
    salary = _get_employee_monthly_salary(db, employee_id)
    db.execute(text(
        "INSERT INTO staff_incentive_tier_tracker "
        "(employee_id, cumulative_earned, monthly_salary_snapshot, is_escalated) "
        "VALUES (:eid, 0, :sal, FALSE)"
    ), {"eid": employee_id, "sal": float(salary)})
    db.flush()
    row2 = db.execute(text(
        "SELECT id, cumulative_earned, monthly_salary_snapshot, is_escalated "
        "FROM staff_incentive_tier_tracker WHERE employee_id = :eid"
    ), {"eid": employee_id}).fetchone()
    return {"id": row2[0], "cumulative_earned": Decimal("0"),
            "monthly_salary_snapshot": salary, "is_escalated": False}


def _get_vgk_l1_rate(db, category_id: int, company_id: int) -> Decimal:
    """Get VGK L1 paid commission rate for this category; fall back to 5%."""
    from sqlalchemy import text
    row = db.execute(text(
        "SELECT level1_pct, level1_type, level1_amt FROM vgk_team_commission_config "
        "WHERE category_id = :cat AND is_paid_member = TRUE AND is_active = TRUE "
        "AND company_id = :co LIMIT 1"
    ), {"cat": category_id, "co": company_id}).fetchone()
    if not row:
        row = db.execute(text(
            "SELECT level1_pct, level1_type, level1_amt FROM vgk_team_commission_config "
            "WHERE category_id = :cat AND is_active = TRUE LIMIT 1"
        ), {"cat": category_id}).fetchone()
    if row:
        l1_type = (row[1] or "PCT").upper()
        if l1_type == "PCT":
            return Decimal(str(row[0] or 5))
        return None
    return Decimal("5")


def _upsert_monthly_payout(db, employee_id: int, company_id: int,
                           month: int, year: int, incentive_amount: Decimal) -> None:
    """Upsert staff_incentive_payouts to keep monthly wallet total current."""
    from sqlalchemy import text
    existing = db.execute(text(
        "SELECT id, total_incentive FROM staff_incentive_payouts "
        "WHERE employee_id=:eid AND company_id=:co AND month=:mo AND year=:yr"
    ), {"eid": employee_id, "co": company_id, "mo": month, "yr": year}).fetchone()
    if existing:
        new_total = Decimal(str(existing[1] or 0)) + incentive_amount
        db.execute(text(
            "UPDATE staff_incentive_payouts SET total_incentive=:tot, updated_at=NOW() "
            "WHERE id=:pid"
        ), {"tot": float(new_total), "pid": existing[0]})
    else:
        from datetime import date
        next_mo = month + 1
        next_yr = year
        if next_mo > 12:
            next_mo = 1
            next_yr += 1
        due = date(next_yr, next_mo, 15)
        db.execute(text(
            "INSERT INTO staff_incentive_payouts "
            "(employee_id, company_id, month, year, total_incentive, payout_status, due_date) "
            "VALUES (:eid, :co, :mo, :yr, :tot, 'pending', :dd)"
        ), {"eid": employee_id, "co": company_id, "mo": month, "yr": year,
            "tot": float(incentive_amount), "dd": due})


def trigger_staff_lead_incentive(db, lead, transaction, company_id: int,
                                  validated_by_id: int,
                                  override_employee_id: int = None) -> dict:
    """
    Main entry point — called from CRM validate_transaction after existing incentive hooks.
    Returns dict with success, message, and incentive_amount.
    DC-MULTI-STAFF-INCV-001: override_employee_id allows triggering for support_staff /
    technical_staff1 / technical_id roles independently. Same employee in multiple roles
    earns separate incentive per role (no dedup by person).
    """
    from sqlalchemy import text

    employee_id = override_employee_id or getattr(lead, "field_staff_id", None)
    if not employee_id:
        return {"success": False, "message": "No employee_id — skipped"}

    category_id = getattr(lead, "category_id", None)
    revenue = Decimal(str(getattr(transaction, "amount", 0) or 0))
    if revenue <= 0:
        return {"success": False, "message": "Zero revenue — skipped"}

    vgk_rate = _get_vgk_l1_rate(db, category_id, company_id) if category_id else Decimal("5")
    if vgk_rate is None:
        return {"success": False, "message": "VGK L1 uses flat amount — not percentage, skipped"}

    now = _now_ist()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Monthly tier: calculate this month's existing sum to decide multiplier
    salary = _get_employee_monthly_salary(db, employee_id)
    threshold = salary * Decimal("5")
    month_sum_row = db.execute(text("""
        SELECT COALESCE(SUM(incentive_amount), 0)
        FROM staff_lead_incentive_earnings
        WHERE employee_id = :eid
          AND EXTRACT(MONTH FROM earned_month) = :m
          AND EXTRACT(YEAR  FROM earned_month) = :y
          AND status != 'cancelled'
    """), {"eid": employee_id, "m": now.month, "y": now.year}).fetchone()
    month_sum = Decimal(str(month_sum_row[0] or 0))

    # If this month's sum already >= 5× CTC → 1.2× rate
    is_escalated = (threshold > 0) and (month_sum >= threshold)
    multiplier = Decimal("1.2") if is_escalated else Decimal("1.0")

    incentive = (revenue * vgk_rate / Decimal("100") * multiplier).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)

    if incentive <= 0:
        return {"success": False, "message": "Calculated incentive is zero — skipped"}

    # Check if this new entry would push the employee past the threshold (newly escalated)
    newly_escalated = (not is_escalated) and (threshold > 0) and ((month_sum + incentive) >= threshold)

    db.execute(text("""
        INSERT INTO staff_lead_incentive_earnings
          (employee_id, lead_id, transaction_id, company_id, category_id,
           revenue_amount, vgk_base_rate_pct, multiplier, incentive_amount,
           status, earned_month, created_by, created_at, updated_at)
        VALUES
          (:eid, :lid, :tid, :co, :cat,
           :rev, :rate, :mul, :inc,
           'pending', :emon, :cb, NOW(), NOW())
    """), {
        "eid": employee_id, "lid": lead.id, "tid": transaction.id,
        "co": company_id, "cat": category_id,
        "rev": float(revenue), "rate": float(vgk_rate), "mul": float(multiplier),
        "inc": float(incentive), "emon": month_start.date(), "cb": validated_by_id
    })

    _upsert_monthly_payout(db, employee_id, company_id, now.month, now.year, incentive)

    msg = (f"Staff incentive ₹{incentive:.2f} @ {vgk_rate}% × {multiplier} "
           f"for employee #{employee_id}")
    if newly_escalated:
        msg += " | 🎯 Tier 1 (120%) UNLOCKED"
    logger.info(f"[STAFF-INCV] {msg} lead={lead.id} txn={transaction.id}")
    return {"success": True, "message": msg, "incentive_amount": float(incentive),
            "multiplier": float(multiplier), "newly_escalated": newly_escalated}
