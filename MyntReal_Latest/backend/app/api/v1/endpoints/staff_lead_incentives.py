"""
Staff Lead Incentive Endpoints (DC Protocol Apr 2026)
VGK-rate-based incentives for staff sourcing CRM leads.

Routes:
  GET  /lead-incentives/my-earnings        — staff sees own earnings, month-wise
  GET  /lead-incentives/my-tier-status     — tier progress + escalation info
  GET  /lead-incentives/admin/list         — admin: all staff, filterable
  POST /lead-incentives/admin/clear        — admin: clear monthly payout
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_admin(emp: StaffEmployee) -> bool:
    st = (emp.staff_type or "").upper()
    return "VGK" in st or "SUPREME" in st or "ADMIN" in st or "FINANCE" in st or "HR" in st


@router.get("/lead-incentives/my-earnings")
def my_lead_incentive_earnings(
    year: int = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff sees own earnings broken down by month."""
    from datetime import date
    yr = year or date.today().year

    q = """
        SELECT
            lie.id,
            lie.lead_id,
            lie.transaction_id,
            lie.revenue_amount,
            lie.vgk_base_rate_pct,
            lie.multiplier,
            lie.incentive_amount,
            lie.status,
            lie.earned_month,
            lie.created_at,
            lie.cleared_at,
            COALESCE(cl.name, 'Lead #'||lie.lead_id::text) AS lead_name,
            COALESCE(sc.name, '') AS category_name
        FROM staff_lead_incentive_earnings lie
        LEFT JOIN crm_leads cl ON cl.id = lie.lead_id
        LEFT JOIN signup_categories sc ON sc.id = lie.category_id
        WHERE lie.employee_id = :eid
          AND EXTRACT(YEAR FROM lie.earned_month) = :yr
    """
    params = {"eid": me.id, "yr": yr}
    if status:
        q += " AND lie.status = :st"
        params["st"] = status
    q += " ORDER BY lie.earned_month DESC, lie.id DESC"

    rows = db.execute(text(q), params).fetchall()

    months = {}
    total_earned = 0.0
    total_pending = 0.0
    total_cleared = 0.0

    for r in rows:
        inc = float(r[6] or 0)
        st = r[7]
        mon_key = r[8].strftime("%Y-%m") if r[8] else "unknown"
        mon_label = r[8].strftime("%B %Y") if r[8] else "Unknown"
        if mon_key not in months:
            months[mon_key] = {"month_key": mon_key, "month_label": mon_label,
                                "total": 0.0, "pending": 0.0, "cleared": 0.0, "entries": []}
        months[mon_key]["total"] += inc
        if st == "pending":
            months[mon_key]["pending"] += inc
            total_pending += inc
        elif st == "cleared":
            months[mon_key]["cleared"] += inc
            total_cleared += inc
        total_earned += inc
        months[mon_key]["entries"].append({
            "id": r[0], "lead_id": r[1], "transaction_id": r[2],
            "lead_name": r[11], "category": r[12],
            "revenue": float(r[3] or 0),
            "vgk_rate_pct": float(r[4] or 0),
            "multiplier": float(r[5] or 1.0),
            "incentive_amount": inc,
            "status": st,
            "earned_month": r[8].isoformat() if r[8] else None,
            "created_at": r[9].isoformat() if r[9] else None,
            "cleared_at": r[10].isoformat() if r[10] else None,
        })

    return {
        "success": True,
        "year": yr,
        "summary": {
            "total_earned": round(total_earned, 2),
            "total_pending": round(total_pending, 2),
            "total_cleared": round(total_cleared, 2),
            "entry_count": len(rows),
        },
        "months": sorted(months.values(), key=lambda x: x["month_key"], reverse=True),
    }


@router.get("/lead-incentives/my-tier-status")
def my_tier_status(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Monthly tier status — calculated fresh from staff_lead_incentive_earnings.
    Each month is independent: if this month's incentives >= 5× monthly CTC → 1.2× rate.
    """
    from datetime import date
    from app.services.staff_lead_incentive_service import _get_employee_monthly_salary

    today = date.today()
    m = month or today.month
    y = year or today.year

    sal = float(_get_employee_monthly_salary(db, me.id))
    threshold = sal * 5

    # Sum all non-cancelled incentives earned in this month
    sum_row = db.execute(text("""
        SELECT COALESCE(SUM(incentive_amount), 0)
        FROM staff_lead_incentive_earnings
        WHERE employee_id = :eid
          AND EXTRACT(MONTH FROM earned_month) = :m
          AND EXTRACT(YEAR  FROM earned_month) = :y
          AND status != 'cancelled'
    """), {"eid": me.id, "m": m, "y": y}).fetchone()

    cumulative = float(sum_row[0] or 0)
    is_escalated = (threshold > 0) and (cumulative >= threshold)
    multiplier = 1.2 if is_escalated else 1.0
    progress = min(100.0, (cumulative / threshold * 100) if threshold > 0 else 0.0)

    import calendar
    month_label = f"{calendar.month_name[m]} {y}"

    return {
        "success": True,
        "month": m,
        "year": y,
        "month_label": month_label,
        "multiplier": multiplier,
        "cumulative_earned": round(cumulative, 2),
        "monthly_salary": round(sal, 2),
        "threshold_5x": round(threshold, 2),
        "progress_pct": round(progress, 1),
        "is_escalated": is_escalated,
    }


@router.get("/lead-incentives/my-earning-capacity")
def my_earning_capacity(
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Returns THIS MONTH's staff incentive config rates (from staff_incentive_config,
    company_id=1 as master) as the earning capacity for the logged-in staff member.
    Falls back to the most recent available month if no config exists for the current month.
    Incentive config is set at MyntReal level (company_id=1) and applies to all staff
    irrespective of which company they belong to.
    """
    from datetime import date as _date
    from app.services.staff_lead_incentive_service import _get_employee_monthly_salary

    today = _date.today()

    # Multiplier: same tier-escalation logic as my-tier-status
    sal = float(_get_employee_monthly_salary(db, me.id))
    threshold = sal * 5
    sum_row = db.execute(text("""
        SELECT COALESCE(SUM(incentive_amount), 0)
        FROM staff_lead_incentive_earnings
        WHERE employee_id = :eid
          AND EXTRACT(MONTH FROM earned_month) = :m
          AND EXTRACT(YEAR  FROM earned_month) = :y
          AND status != 'cancelled'
    """), {"eid": me.id, "m": today.month, "y": today.year}).fetchone()
    month_sum = float(sum_row[0] or 0)
    is_esc = (threshold > 0) and (month_sum >= threshold)
    multiplier = 1.2 if is_esc else 1.0

    # Fetch staff incentive config from company_id=1 (MyntReal — master config).
    # Try current month first; fall back to the most recent month available.
    cfg_rows = db.execute(text("""
        SELECT category_slug, category_label,
               min_target_value, min_target_unit,
               incentive_rate_without_support, incentive_rate_with_support,
               incentive_rate_direct_work,
               incentive_type, bonus_trigger_value, bonus_multiplier
        FROM staff_incentive_config
        WHERE company_id = 1
          AND month = :mo AND year = :yr
          AND is_active = TRUE
        ORDER BY category_slug
    """), {"mo": today.month, "yr": today.year}).fetchall()

    if not cfg_rows:
        # Fallback: most recent active config for company_id=1
        cfg_rows = db.execute(text("""
            SELECT category_slug, category_label,
                   min_target_value, min_target_unit,
                   incentive_rate_without_support, incentive_rate_with_support,
                   incentive_rate_direct_work,
                   incentive_type, bonus_trigger_value, bonus_multiplier
            FROM staff_incentive_config
            WHERE company_id = 1 AND is_active = TRUE
            ORDER BY year DESC, month DESC, category_slug
        """)).fetchall()

    # Build config map keyed by slug
    # Indices: 0=slug,1=label,2=min_tgt_val,3=min_tgt_unit,4=rate_no,5=rate_wi,
    #          6=rate_dw,7=itype,8=bonus_trigger,9=bonus_mul
    cfg_map: dict = {}
    seen: set = set()
    for r in cfg_rows:
        slug = r[0]
        if slug in seen:
            continue
        seen.add(slug)
        cfg_map[slug] = {
            "category_name":    r[1] or slug,
            "min_target_value": float(r[2] or 0),
            "min_target_unit":  r[3] or "count",
            "rate_no_support":  float(r[4] or 0),
            "rate_with_support": float(r[5] or 0),
            "rate_direct_work": float(r[6] or 0),
            "incentive_type":   r[7] or "percentage",
            "bonus_trigger":    float(r[8]) if r[8] else None,
            "bonus_multiplier": float(r[9] or 1.0),
        }

    # ── Achievement calculation for THIS employee in THIS month ──────────────
    import calendar as _cal
    from datetime import datetime as _dt
    _last_day = _cal.monthrange(today.year, today.month)[1]
    date_from = _dt(today.year, today.month, 1)
    date_to   = _dt(today.year, today.month, _last_day, 23, 59, 59)

    # category_slug → list of matching signup_category ids (company_id=1 as reference)
    CAT_PATTERNS = {
        'solar':       ['%solar%'],
        'ev_b2c':      ['%ev%b2c%', '%ev b2c%', '%ev-b2c%'],
        'ev_b2b':      ['%ev%b2b%', '%ev b2b%', '%ev-b2b%'],
        'training':    ['%training%', '%etc%'],
        'insurance':   ['%insurance%'],
        'real_estate': ['%real%estate%', '%real dream%', '%property%'],
    }
    all_cats = db.execute(text(
        "SELECT id, name FROM signup_categories WHERE company_id=1"
    )).fetchall()
    slug_to_cat_ids: dict = {s: [] for s in CAT_PATTERNS}
    for cat_id, cat_name in all_cats:
        cn = (cat_name or '').lower()
        for slug, patterns in CAT_PATTERNS.items():
            for pat in patterns:
                pat_clean = pat.replace('%', '')
                if pat_clean and all(p in cn for p in pat_clean.split() if p):
                    slug_to_cat_ids[slug].append(cat_id)
                    break

    # DC-CLOSE-DATE-001: Use actual_close_date (not updated_at) to avoid smuggling
    # field-edits into a later month's incentive window.
    # DC-INCENTIVE-TELE-FIELD-ONLY-001: Only telecaller_id + field_staff_id earn incentive
    # credit; handler_id (VARCHAR, not a systematic FK) is excluded.
    # DC-INCENTIVE-LEAD-TYPE-003: Direct Work = no MNR/VGK4U ref + not Self Lead.
    _sup = """CASE
        WHEN l.source = 'Self Lead' THEN 0
        WHEN (
            l.guru_id IS NOT NULL
            OR l.z_guru_id IS NOT NULL
            OR l.adi_guru_id IS NOT NULL
            OR (l.mnr_handler_id IS NOT NULL AND l.mnr_handler_id != '')
            OR l.associated_partner_id IS NOT NULL
        ) THEN 1
        ELSE 0
    END"""
    _close_dt = "COALESCE(l.actual_close_date, l.updated_at)"
    _is_direct = """CASE WHEN (
        (l.source IS NULL OR l.source != 'Self Lead')
        AND l.guru_id IS NULL AND l.z_guru_id IS NULL
        AND l.adi_guru_id IS NULL
        AND (l.mnr_handler_id IS NULL OR l.mnr_handler_id = '')
        AND l.associated_partner_id IS NULL
    ) THEN TRUE ELSE FALSE END"""
    _comp_where = f"""(
        (
            l.solar_pipeline_status = 'completed'
            OR l.ev_b2b_stage = 'completed'
            OR (l.status = 'completed'
                AND l.solar_pipeline_status IS NULL
                AND l.ev_b2b_stage IS NULL)
        ) AND ({_close_dt}) BETWEEN :df AND :dt
        OR EXISTS (
            SELECT 1 FROM etc_students s
            WHERE s.crm_lead_id = l.id
              AND s.training_completed_date IS NOT NULL
              AND s.training_completed_date BETWEEN :df_d AND :dt_d
              AND s.is_active = TRUE
        )
    )"""
    lead_rows = db.execute(text(f"""
        SELECT category_id, dvr, has_support, is_direct FROM (
            SELECT DISTINCT ON (lead_id)
                   lead_id, category_id,
                   COALESCE(deal_value_received, 0) AS dvr, has_support, is_direct
            FROM (
                SELECT l.id                                                        AS lead_id,
                       l.category_id,
                       COALESCE(NULLIF(l.deal_value_received,0), l.deal_value, 0) AS deal_value_received,
                       {_sup}                                                      AS has_support,
                       {_is_direct}                                                AS is_direct
                FROM crm_leads l
                WHERE {_comp_where}
                  AND l.telecaller_id::TEXT = :eid
                UNION ALL
                SELECT l.id,
                       l.category_id,
                       COALESCE(NULLIF(l.deal_value_received,0), l.deal_value, 0),
                       {_sup},
                       {_is_direct}
                FROM crm_leads l
                WHERE {_comp_where}
                  AND l.field_staff_id::TEXT = :eid
            ) raw
            ORDER BY lead_id
        ) deduped
    """), {
        "df":   date_from,
        "dt":   date_to,
        "df_d": _date(today.year, today.month, 1),
        "dt_d": _date(today.year, today.month, _last_day),
        "eid":  str(me.id),
    }).fetchall()

    # DC-ETC-DIRECT-001: Direct ETC students (crm_lead_id IS NULL) — always direct_count.
    # Join via emp_code since etc_students stores telecaller_emp_code / field_staff_emp_code.
    _training_slug = 'training' if 'training' in slug_to_cat_ids else None
    _etc_direct_rows: list = []
    if _training_slug:
        _erow = db.execute(text(
            "SELECT emp_code FROM staff_employees WHERE id = :eid"
        ), {"eid": me.id}).fetchone()
        if _erow and _erow[0]:
            _etc_direct_rows = db.execute(text("""
                SELECT COALESCE(es.deal_value_received, 0) AS dvr
                FROM etc_students es
                WHERE es.training_completed_date IS NOT NULL
                  AND es.training_completed_date BETWEEN :df_d AND :dt_d
                  AND es.crm_lead_id IS NULL AND es.is_active = TRUE
                  AND (es.telecaller_emp_code = :ec OR es.field_staff_emp_code = :ec)
            """), {
                "df_d": _date(today.year, today.month, 1),
                "dt_d": _date(today.year, today.month, _last_day),
                "ec":   _erow[0],
            }).fetchall()

    # DC-ETC-ALWAYS-COMPANY-001: ETC/Training CRM leads → force has_support=1 (company).
    _training_cat_ids = set(slug_to_cat_ids.get('training', []))
    lead_rows_clean = [
        (cid, dvr, 1, False) if cid in _training_cat_ids else (cid, dvr, hs, bool(isd))
        for cid, dvr, hs, isd in lead_rows
    ]

    # Aggregate per slug: self / company / direct
    _empty_ach = lambda: {"self_count": 0, "self_amount": 0.0,
                          "company_count": 0, "company_amount": 0.0,
                          "direct_count": 0, "direct_amount": 0.0}
    ach: dict = {slug: _empty_ach() for slug in cfg_map}
    for cat_id, dvr, has_sup, is_direct in lead_rows_clean:
        for slug, cat_ids in slug_to_cat_ids.items():
            if slug in cfg_map and cat_id in cat_ids:
                if is_direct:
                    ach[slug]["direct_count"]  += 1
                    ach[slug]["direct_amount"] += float(dvr)
                elif has_sup:
                    ach[slug]["company_count"]  += 1
                    ach[slug]["company_amount"] += float(dvr)
                else:
                    ach[slug]["self_count"]  += 1
                    ach[slug]["self_amount"] += float(dvr)
                break
    for (_dvr_etc,) in _etc_direct_rows:
        if _training_slug in ach:
            ach[_training_slug]["direct_count"]  += 1
            ach[_training_slug]["direct_amount"] += float(_dvr_etc or 0)

    # ── Build final categories list ──────────────────────────────────────────
    DISPLAY_ORDER = ['training', 'solar', 'ev_b2c', 'ev_b2b', 'insurance', 'real_estate']
    ordered_slugs = [s for s in DISPLAY_ORDER if s in cfg_map] + \
                    [s for s in cfg_map if s not in DISPLAY_ORDER]

    categories = []
    for slug in ordered_slugs:
        cfg = cfg_map[slug]
        a   = ach.get(slug, _empty_ach())
        itype = cfg["incentive_type"]
        unit  = cfg["min_target_unit"]

        self_count    = a["self_count"]
        self_amount   = a["self_amount"]
        company_count = a["company_count"]
        company_amount= a["company_amount"]
        direct_count  = a["direct_count"]
        direct_amount = a["direct_amount"]
        total_count   = self_count + company_count + direct_count
        total_amount  = self_amount + company_amount + direct_amount

        achieved_val = total_count if unit == "count" else total_amount
        target_met   = achieved_val >= cfg["min_target_value"]

        rate_no = cfg["rate_no_support"]
        rate_wi = cfg["rate_with_support"]
        rate_dw = cfg.get("rate_direct_work", 0.0)

        if itype == "fixed_per_unit":
            self_base    = self_count    * rate_no
            company_base = company_count * rate_wi
            direct_base  = direct_count  * rate_dw
        elif itype == "percentage":
            self_base    = (self_amount    * rate_no) / 100.0
            company_base = (company_amount * rate_wi) / 100.0
            direct_base  = (direct_amount  * rate_dw) / 100.0
        else:  # fixed_amount
            self_base = company_base = direct_base = rate_no if (total_count > 0 or total_amount > 0) else 0.0

        if not target_met:
            self_base = company_base = direct_base = 0.0

        company_tgt = (company_count + direct_count) if unit == "count" \
                      else (company_amount + direct_amount)
        bonus_applied = False
        if target_met and cfg["bonus_trigger"] and company_tgt >= cfg["bonus_trigger"] \
                and (company_base + direct_base) > 0:
            company_base *= cfg["bonus_multiplier"]
            direct_base  *= cfg["bonus_multiplier"]
            bonus_applied = True

        earned = self_base + company_base + direct_base

        categories.append({
            "category_slug":              slug,
            "category_name":              cfg["category_name"],
            "min_target_value":           cfg["min_target_value"],
            "min_target_unit":            cfg["min_target_unit"],
            "rate_no_support":            rate_no,
            "rate_with_support":          rate_wi,
            "incentive_rate_direct_work": rate_dw,
            "incentive_type":             itype,
            "bonus_trigger":              cfg["bonus_trigger"],
            "bonus_multiplier":           cfg["bonus_multiplier"],
            "achieved_count":             total_count,
            "achieved_amount":            round(total_amount, 2),
            "achieved_value":             round(achieved_val, 2),
            "target_met":                 target_met,
            "earned_amount":              round(earned, 2),
            "self_count":                 self_count,
            "company_count":              company_count,
            "direct_count":               direct_count,
        })

    return {
        "success":      True,
        "multiplier":   multiplier,
        "is_escalated": bool(is_esc),
        "month":        today.month,
        "year":         today.year,
        "categories":   categories,
    }


@router.get("/lead-incentives/admin/list")
def admin_list_incentives(
    employee_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """Admin: list all staff lead incentive entries with filters."""
    if not _is_admin(me):
        raise HTTPException(status_code=403, detail="Admin access required")

    q = """
        SELECT
            lie.id, lie.employee_id, lie.lead_id, lie.company_id,
            lie.revenue_amount, lie.vgk_base_rate_pct, lie.multiplier,
            lie.incentive_amount, lie.status, lie.earned_month, lie.created_at, lie.cleared_at,
            COALESCE(e.full_name, e.emp_code) AS emp_name, e.emp_code,
            COALESCE(cl.name, 'Lead #'||lie.lead_id::text) AS lead_name,
            COALESCE(sc.name,'') AS category_name
        FROM staff_lead_incentive_earnings lie
        JOIN staff_employees e ON e.id = lie.employee_id
        LEFT JOIN crm_leads cl ON cl.id = lie.lead_id
        LEFT JOIN signup_categories sc ON sc.id = lie.category_id
        WHERE 1=1
    """
    params = {}
    if employee_id:
        q += " AND lie.employee_id = :eid"; params["eid"] = employee_id
    if company_id:
        q += " AND lie.company_id = :co"; params["co"] = company_id
    if month:
        q += " AND EXTRACT(MONTH FROM lie.earned_month) = :mo"; params["mo"] = month
    if year:
        q += " AND EXTRACT(YEAR FROM lie.earned_month) = :yr"; params["yr"] = year
    if status:
        q += " AND lie.status = :st"; params["st"] = status

    total = db.execute(text(q.replace(
        "SELECT\n            lie.id, lie.employee_id", "SELECT COUNT(*)"
    ).split("FROM")[0] + " FROM" + q.split("FROM", 1)[1]), params).scalar() or 0

    q += f" ORDER BY lie.earned_month DESC, lie.id DESC LIMIT {page_size} OFFSET {(page-1)*page_size}"
    rows = db.execute(text(q), params).fetchall()

    data = []
    for r in rows:
        data.append({
            "id": r[0], "employee_id": r[1], "lead_id": r[2], "company_id": r[3],
            "revenue": float(r[4] or 0), "vgk_rate_pct": float(r[5] or 0),
            "multiplier": float(r[6] or 1.0), "incentive_amount": float(r[7] or 0),
            "status": r[8],
            "earned_month": r[9].isoformat() if r[9] else None,
            "created_at": r[10].isoformat() if r[10] else None,
            "cleared_at": r[11].isoformat() if r[11] else None,
            "employee_name": r[12], "emp_code": r[13],
            "lead_name": r[14], "category": r[15],
        })

    return {"success": True, "data": data, "total": total, "page": page, "page_size": page_size}


@router.post("/lead-incentives/admin/clear")
def admin_clear_incentives(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Admin: clear pending incentive entries for an employee's month.
    Marks individual entries + monthly payout row as cleared.
    """
    if not _is_admin(me):
        raise HTTPException(status_code=403, detail="Admin access required")

    employee_id = int(payload.get("employee_id", 0))
    month = int(payload.get("month", 0))
    year = int(payload.get("year", 0))
    company_id = int(payload.get("company_id", 1))
    notes = payload.get("notes", "")

    if not all([employee_id, month, year]):
        raise HTTPException(status_code=400, detail="employee_id, month, year required")

    updated = db.execute(text(
        "UPDATE staff_lead_incentive_earnings "
        "SET status='cleared', cleared_at=NOW(), cleared_by=:cb, updated_at=NOW() "
        "WHERE employee_id=:eid AND status='pending' "
        "AND EXTRACT(MONTH FROM earned_month)=:mo AND EXTRACT(YEAR FROM earned_month)=:yr "
        "RETURNING id"
    ), {"cb": me.id, "eid": employee_id, "mo": month, "yr": year}).fetchall()
    count = len(updated)

    db.execute(text(
        "UPDATE staff_incentive_payouts "
        "SET payout_status='cleared', cleared_by=:cb, cleared_at=NOW(), notes=:notes, updated_at=NOW() "
        "WHERE employee_id=:eid AND company_id=:co AND month=:mo AND year=:yr "
        "AND payout_status != 'cleared'"
    ), {"cb": str(me.emp_code), "eid": employee_id, "co": company_id,
        "mo": month, "yr": year, "notes": notes})

    db.commit()
    return {"success": True, "message": f"{count} entries cleared", "cleared_count": count}
