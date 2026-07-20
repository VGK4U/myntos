"""
Staff Performance Config & Report API
DC Protocol: company_id filtering in report. Config is system-wide (no company scope).
Access: VGK Supreme (MR10001) + EA for config writes; both for report reads.
WVV: Config saves validate weightage sum = 100% before commit.
Per-employee KPI targets: month=0/year=0 = global default for that employee.
March 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, text
from typing import Optional
from datetime import datetime, date, timedelta
import calendar
import pytz
import logging
import json

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffRole
from app.models.staff_tasks import StaffDayPlan
from app.models.staff_attendance import StaffAttendance
from app.models.staff_kra import StaffKRADailyInstance, StaffKRAAssignment
from app.models.staff_timesheet import StaffTimesheetEntry
from app.models.ticket import ServiceTicket
from app.models.crm import CRMLead, CRMLeadTransaction
from app.models.marketplace import MarketplaceProcurementRequest, MarketplacePurchaseOrder
from app.utils.staff_hierarchy import get_recursive_downline, HIDDEN_FROM_TEAM_CODES
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter()
logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')

KPI_ORDER = [
    'attendance', 'day_plan', 'kra', 'timesheet',
    'talk_time', 'service_tickets', 'crm_revenue', 'procurement'
]

KPI_DEFAULTS = {
    'attendance':      {'kpi_label': 'Attendance',       'target_value': 90,     'target_unit': '%'},
    'day_plan':        {'kpi_label': 'Day Plan',         'target_value': 80,     'target_unit': '%'},
    'kra':             {'kpi_label': 'KRA Completion',   'target_value': 80,     'target_unit': '%'},
    'timesheet':       {'kpi_label': 'Timesheet',        'target_value': 90,     'target_unit': '%'},
    'talk_time':       {'kpi_label': 'Talk Time',        'target_value': 30,     'target_unit': 'min/day'},
    'service_tickets': {'kpi_label': 'Service Tickets',  'target_value': 20,     'target_unit': 'tickets/month'},
    'crm_revenue':     {'kpi_label': 'CRM Revenue',      'target_value': 100000, 'target_unit': '₹/month'},
    'procurement':     {'kpi_label': 'Procurement',      'target_value': 80,     'target_unit': '%'},
}


def _is_vgk_or_ea(emp: StaffEmployee) -> bool:
    rc = (emp.role.role_code or '').lower() if emp.role else ''
    rn = (emp.role.role_name or '').lower() if emp.role else ''
    st = (getattr(emp, 'staff_type', '') or '').lower()
    ec = (emp.emp_code or '')
    return (
        ec == 'MR10001' or
        rc in ('vgk4u', 'vgk4u_supreme') or
        rn in ('ea', 'executive assistant', 'vgk4u supreme') or
        st in ('ea', 'vgk4u', 'vgk4u_supreme')
    )


def _load_config(db: Session) -> list:
    rows = db.execute(text(
        "SELECT kpi_code, kpi_label, is_enabled, target_value, target_unit, "
        "weightage_pct, sub_config, COALESCE(is_custom, FALSE) "
        "FROM staff_performance_config ORDER BY id"
    )).fetchall()
    result = []
    for r in rows:
        result.append({
            'kpi_code': r[0],
            'kpi_label': r[1],
            'is_enabled': bool(r[2]),
            'target_value': float(r[3] or 0),
            'target_unit': r[4] or '',
            'weightage_pct': float(r[5] or 0),
            'sub_config': r[6] or {},
            'is_custom': bool(r[7]),
        })
    if not result:
        result = [
            {**{'kpi_code': k, 'is_enabled': False, 'weightage_pct': 0, 'is_custom': False}, **v}
            for k, v in KPI_DEFAULTS.items()
        ]
    return result


def _load_employee_targets_raw(db: Session, employee_ids: list, month: int = 0, year: int = 0) -> dict:
    """
    Returns {employee_id: {kpi_code: {target_value, is_enabled, weightage_pct}}}
    Priority: (month, year) specific row → (0, 0) default row → None
    """
    if not employee_ids:
        return {}
    rows = db.execute(text("""
        SELECT employee_id, kpi_code, target_value, is_enabled, weightage_pct, month, year
        FROM staff_performance_employee_kpi
        WHERE employee_id = ANY(:ids)
          AND (
            (month = :month AND year = :year)
            OR (month = 0 AND year = 0)
          )
        ORDER BY employee_id, kpi_code,
                 CASE WHEN month = :month AND year = :year THEN 0 ELSE 1 END
    """), {'ids': employee_ids, 'month': month, 'year': year}).fetchall()

    result = {}
    for r in rows:
        emp_id, kpi_code = r[0], r[1]
        if emp_id not in result:
            result[emp_id] = {}
        # Only set if not already set by a more-specific row (month/year specific wins)
        if kpi_code not in result[emp_id]:
            result[emp_id][kpi_code] = {
                'target_value': float(r[2] or 0),
                'is_enabled': r[3],
                'weightage_pct': float(r[4]) if r[4] is not None else None,
                'month': r[5],
                'year': r[6],
                'is_month_specific': (r[5] == month and r[6] == year and month != 0),
            }
    return result


# ── GET /performance/config ───────────────────────────────────────────────────

@router.get("/performance/config", summary="Get Performance KPI Configuration")
def get_performance_config(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")
    config = _load_config(db)
    total_weight = sum(c['weightage_pct'] for c in config if c['is_enabled'])
    return {
        'success': True,
        'config': config,
        'total_weightage': round(total_weight, 2),
        'is_valid': abs(total_weight - 100) < 0.01 or total_weight == 0,
    }


# ── PUT /performance/config ───────────────────────────────────────────────────

@router.put("/performance/config", summary="Save Performance KPI Configuration")
def save_performance_config(
    payload: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")

    items = payload.get('config', [])
    if not items:
        raise HTTPException(status_code=400, detail="config list is required")

    enabled_weight = sum(float(item.get('weightage_pct', 0)) for item in items if item.get('is_enabled'))
    if enabled_weight > 0 and abs(enabled_weight - 100) > 0.5:
        raise HTTPException(
            status_code=400,
            detail=f"Enabled KPI weightages must total 100%. Current total: {round(enabled_weight, 2)}%"
        )

    now = datetime.utcnow()
    for item in items:
        kpi_code = item.get('kpi_code', '').strip()
        if not kpi_code:
            continue
        sub_config = item.get('sub_config', {}) or {}
        db.execute(text("""
            UPDATE staff_performance_config
            SET is_enabled    = :is_enabled,
                target_value  = :target_value,
                target_unit   = :target_unit,
                weightage_pct = :weightage_pct,
                sub_config    = CAST(:sub_config AS jsonb),
                changed_by    = :changed_by,
                changed_at    = :changed_at
            WHERE kpi_code = :kpi_code
        """), {
            'kpi_code': kpi_code,
            'is_enabled': bool(item.get('is_enabled', False)),
            'target_value': float(item.get('target_value', 0)),
            'target_unit': item.get('target_unit', ''),
            'weightage_pct': float(item.get('weightage_pct', 0)),
            'sub_config': json.dumps(sub_config) if sub_config else '{}',
            'changed_by': current_user.id,
            'changed_at': now,
        })

    db.commit()
    config = _load_config(db)
    total_weight = sum(c['weightage_pct'] for c in config if c['is_enabled'])
    return {
        'success': True,
        'message': 'Performance configuration saved successfully',
        'config': config,
        'total_weightage': round(total_weight, 2),
    }


# ── POST /performance/config/custom ──────────────────────────────────────────

@router.post("/performance/config/custom", summary="Create a custom KPI metric")
def create_custom_kpi(
    payload: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")

    label = (payload.get('kpi_label') or '').strip()
    unit  = (payload.get('target_unit') or '').strip()
    target_value  = float(payload.get('target_value', 0))
    weightage_pct = float(payload.get('weightage_pct', 0))
    is_enabled    = bool(payload.get('is_enabled', True))

    if not label:
        raise HTTPException(status_code=400, detail="kpi_label is required")
    if not unit:
        raise HTTPException(status_code=400, detail="target_unit is required")

    import re
    kpi_code = 'custom_' + re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')[:30]

    existing = db.execute(text(
        "SELECT kpi_code FROM staff_performance_config WHERE kpi_code = :kc"
    ), {'kc': kpi_code}).fetchone()
    if existing:
        suffix = db.execute(text(
            "SELECT COUNT(*) FROM staff_performance_config WHERE kpi_code LIKE :pat"
        ), {'pat': kpi_code + '%'}).scalar() or 0
        kpi_code = f"{kpi_code}_{int(suffix) + 1}"

    db.execute(text("""
        INSERT INTO staff_performance_config
            (kpi_code, kpi_label, is_enabled, target_value, target_unit, weightage_pct, sub_config, is_custom, changed_by, changed_at)
        VALUES
            (:kpi_code, :kpi_label, :is_enabled, :target_value, :target_unit, :weightage_pct, '{}', TRUE, :changed_by, NOW())
    """), {
        'kpi_code': kpi_code,
        'kpi_label': label,
        'is_enabled': is_enabled,
        'target_value': target_value,
        'target_unit': unit,
        'weightage_pct': weightage_pct,
        'changed_by': current_user.id,
    })
    db.commit()

    config = _load_config(db)
    return {
        'success': True,
        'message': f'Custom KPI "{label}" created successfully',
        'kpi_code': kpi_code,
        'config': config,
    }


# ── DELETE /performance/config/custom/{kpi_code} ──────────────────────────────

@router.delete("/performance/config/custom/{kpi_code}", summary="Delete a custom KPI metric")
def delete_custom_kpi(
    kpi_code: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")

    row = db.execute(text(
        "SELECT kpi_code, is_custom FROM staff_performance_config WHERE kpi_code = :kc"
    ), {'kc': kpi_code}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"KPI '{kpi_code}' not found")
    if not row[1]:
        raise HTTPException(status_code=400, detail="Only custom KPIs can be deleted")

    db.execute(text(
        "DELETE FROM staff_performance_employee_kpi WHERE kpi_code = :kc"
    ), {'kc': kpi_code})
    db.execute(text(
        "DELETE FROM staff_performance_config WHERE kpi_code = :kc"
    ), {'kc': kpi_code})
    db.commit()

    config = _load_config(db)
    return {
        'success': True,
        'message': f'Custom KPI "{kpi_code}" deleted',
        'config': config,
    }


# ── GET /performance/employee-targets ────────────────────────────────────────

@router.get("/performance/employee-targets", summary="Get per-employee KPI targets")
def get_employee_targets(
    month: int = Query(0, ge=0, le=12),
    year: int = Query(0, ge=0),
    company_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")

    config = _load_config(db)
    global_cfg = {c['kpi_code']: c for c in config}

    emp_q = (
        db.query(StaffEmployee)
        .options(joinedload(StaffEmployee.department), joinedload(StaffEmployee.role))
        .filter(StaffEmployee.status == 'active', StaffEmployee.emp_code.isnot(None))
    )
    if company_id:
        emp_q = emp_q.filter(StaffEmployee.base_company_id == company_id)
    if department_id:
        emp_q = emp_q.filter(StaffEmployee.department_id == department_id)

    emps = emp_q.order_by(StaffEmployee.role_id, StaffEmployee.full_name).all()
    emp_ids = [e.id for e in emps]
    raw_targets = _load_employee_targets_raw(db, emp_ids, month, year)

    employees = []
    for emp in emps:
        personal = raw_targets.get(emp.id, {})
        kpi_targets = {}
        total_weight = 0.0

        for kpi_code, gcfg in global_cfg.items():
            row = personal.get(kpi_code)
            # is_enabled: per-employee override if set, else global
            is_enabled = row['is_enabled'] if (row and row['is_enabled'] is not None) else gcfg['is_enabled']
            # target: per-employee if set, else global
            target_value = row['target_value'] if row else gcfg['target_value']
            # weightage: per-employee if set, else global
            weightage_pct = row['weightage_pct'] if (row and row['weightage_pct'] is not None) else gcfg['weightage_pct']
            is_month_specific = row['is_month_specific'] if row else False

            kpi_targets[kpi_code] = {
                'is_enabled': is_enabled,
                'target_value': target_value,
                'weightage_pct': weightage_pct,
                'global_target': gcfg['target_value'],
                'global_weight': gcfg['weightage_pct'],
                'global_enabled': gcfg['is_enabled'],
                'is_custom': row is not None,
                'is_month_specific': is_month_specific,
            }
            if is_enabled:
                total_weight += weightage_pct

        employees.append({
            'employee_id': emp.id,
            'emp_code': emp.emp_code,
            'name': emp.full_name,
            'role': emp.role.role_name if emp.role else '—',
            'role_id': emp.role_id,
            'department': emp.department.name if emp.department else '—',
            'department_id': emp.department_id,
            'kpi_targets': kpi_targets,
            'total_weight': round(total_weight, 2),
        })

    return {
        'success': True,
        'employees': employees,
        'config': config,
        'total': len(employees),
        'month': month,
        'year': year,
    }


# ── PUT /performance/employee-targets ────────────────────────────────────────

@router.put("/performance/employee-targets", summary="Save per-employee KPI targets")
def save_employee_targets(
    payload: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")

    rows = payload.get('targets', [])
    month = int(payload.get('month', 0))
    year = int(payload.get('year', 0))

    if not rows:
        raise HTTPException(status_code=400, detail="targets list is required")

    now = datetime.utcnow()
    saved = 0
    for row in rows:
        emp_id = row.get('employee_id')
        kpi_code = row.get('kpi_code', '').strip()
        if not emp_id or not kpi_code:
            continue
        target_value = row.get('target_value', 0)
        is_enabled = row.get('is_enabled')
        weightage_pct = row.get('weightage_pct')

        db.execute(text("""
            INSERT INTO staff_performance_employee_kpi
                (employee_id, kpi_code, target_value, is_enabled, weightage_pct,
                 month, year, updated_at, updated_by)
            VALUES
                (:emp_id, :kpi_code, :target_value, :is_enabled, :weightage_pct,
                 :month, :year, :now, :by)
            ON CONFLICT ON CONSTRAINT staff_perf_emp_kpi_unique
            DO UPDATE SET
                target_value  = EXCLUDED.target_value,
                is_enabled    = EXCLUDED.is_enabled,
                weightage_pct = EXCLUDED.weightage_pct,
                updated_at    = EXCLUDED.updated_at,
                updated_by    = EXCLUDED.updated_by
        """), {
            'emp_id': emp_id,
            'kpi_code': kpi_code,
            'target_value': float(target_value) if target_value is not None else 0,
            'is_enabled': is_enabled,
            'weightage_pct': float(weightage_pct) if weightage_pct is not None else None,
            'month': month,
            'year': year,
            'now': now,
            'by': current_user.id,
        })
        saved += 1

    db.commit()
    return {'success': True, 'message': f'{saved} target(s) saved for {month}/{year}', 'saved': saved}


# ── GET /performance/employee-kpis ───────────────────────────────────────────

@router.get("/performance/employee-kpis", summary="KPI actuals + config for self/downline employee")
def get_employee_kpi_summary(
    employee_id: Optional[int] = Query(None, description="Target employee ID (default: self)"),
    date_from: date = Query(..., description="Period start date"),
    date_to: date = Query(..., description="Period end date"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """DC Protocol: Read-only. Self / manager downline / VGK-EA access.
    Returns per-KPI: monthly_target, prorated_target, period_actual, mtd_actual, period_score, mtd_score, weightage."""
    import traceback, calendar as _cal
    try:
        today = datetime.now(IST).date()
        if date_from > date_to:
            raise HTTPException(status_code=400, detail="date_from must be <= date_to")

        target_id = employee_id or current_user.id
        if target_id != current_user.id:
            if _is_vgk_or_ea(current_user):
                pass
            else:
                from app.utils.staff_hierarchy import get_downline_employee_ids
                dl = get_downline_employee_ids(db, current_user.id, recursive=True)
                if target_id not in dl:
                    raise HTTPException(status_code=403, detail="Employee not in your downline")

        _emp_q = db.query(StaffEmployee).options(
            joinedload(StaffEmployee.department),
            joinedload(StaffEmployee.role)
        ).filter(StaffEmployee.id == target_id)
        if not _is_vgk_or_ea(current_user):
            _emp_q = _emp_q.filter(StaffEmployee.base_company_id == current_user.base_company_id)
        target_emp = _emp_q.first()
        if not target_emp:
            raise HTTPException(status_code=404, detail="Employee not found")

        config = _load_config(db)
        rpt_month, rpt_year = date_from.month, date_from.year
        emp_targets_map = _load_employee_targets_raw(db, [target_id], rpt_month, rpt_year)
        emp_tgt = emp_targets_map.get(target_id, {})

        def _eff(kpi_code: str, gcfg: dict):
            row = emp_tgt.get(kpi_code)
            is_en = row['is_enabled'] if (row and row['is_enabled'] is not None) else gcfg['is_enabled']
            tgt = float(row['target_value'] if row and row.get('target_value') is not None else gcfg['target_value']) or 1.0
            wt = float(row['weightage_pct'] if row and row.get('weightage_pct') is not None else gcfg['weightage_pct'])
            return is_en, tgt, wt

        period_days = (date_to - date_from).days + 1
        days_in_month = _cal.monthrange(rpt_year, rpt_month)[1]
        mtd_start = date_from.replace(day=1)
        mtd_end = min(date_to, today)
        BONUS_CAP = 120.0

        def _compute_actuals(d_from: date, d_to: date, emp_id: int) -> dict:
            n_days = (d_to - d_from).days + 1
            from app.utils.leave_utils import get_employee_leave_dates as _glv
            _ind_leave_map = _glv(db, [emp_id], d_from, d_to)
            leave_days_count = len(_ind_leave_map.get(emp_id, set()))
            eff_days = max(1, n_days - leave_days_count)
            actuals: dict = {}
            att_count = db.query(func.count(StaffAttendance.id)).filter(
                StaffAttendance.employee_id == emp_id,
                StaffAttendance.date.between(d_from, d_to),
                StaffAttendance.status.in_(['present', 'half_day'])
            ).scalar() or 0
            actuals['attendance'] = round((att_count / eff_days) * 100, 1)
            dp_plans = db.query(StaffDayPlan).options(joinedload(StaffDayPlan.items)).filter(
                StaffDayPlan.employee_id == emp_id,
                StaffDayPlan.plan_date.between(d_from, d_to)
            ).all()
            dp_total = sum(len(p.items) for p in dp_plans)
            dp_done = sum(sum(1 for i in p.items if i.eod_status == 'delivered') for p in dp_plans)
            actuals['day_plan'] = round((dp_done / dp_total) * 100, 1) if dp_total > 0 else 0.0
            kra_assign_ids = [r[0] for r in db.query(StaffKRAAssignment.id).filter(
                StaffKRAAssignment.employee_id == emp_id
            ).all()]
            if kra_assign_ids:
                kra_total = db.query(func.count(StaffKRADailyInstance.id)).filter(
                    StaffKRADailyInstance.kra_assignment_id.in_(kra_assign_ids),
                    StaffKRADailyInstance.instance_date.between(d_from, d_to),
                    StaffKRADailyInstance.completion_status.notin_(['na', 'skipped']),
                ).scalar() or 0
                kra_done = db.query(func.count(StaffKRADailyInstance.id)).filter(
                    StaffKRADailyInstance.kra_assignment_id.in_(kra_assign_ids),
                    StaffKRADailyInstance.instance_date.between(d_from, d_to),
                    StaffKRADailyInstance.completion_status == 'completed'
                ).scalar() or 0
                actuals['kra'] = round((kra_done / kra_total) * 100, 1) if kra_total > 0 else 0.0
            else:
                actuals['kra'] = 0.0
            ts_dates = db.query(func.date(StaffTimesheetEntry.date)).filter(
                StaffTimesheetEntry.employee_id == emp_id,
                func.date(StaffTimesheetEntry.date).between(d_from, d_to)
            ).distinct().count()
            actuals['timesheet'] = round((ts_dates / eff_days) * 100, 1)
            from app.models.call_tracking import StaffCallLog
            call_secs = int(db.query(func.sum(StaffCallLog.duration_seconds)).filter(
                StaffCallLog.staff_id == emp_id,
                StaffCallLog.call_date.between(str(d_from), str(d_to))
            ).scalar() or 0)
            days_p = max(att_count, 1)
            actuals['talk_time'] = round(call_secs / 60 / days_p, 1)
            # DC Protocol: Revenue source by role:
            #   EA / Key Leadership / VGK → company-wide revenue
            #   Manager with downline     → team (downline) revenue
            #   Others                    → personal revenue
            from app.utils.staff_hierarchy import get_downline_employee_ids as _get_dl_ids_perf
            _emp_dl = list(_get_dl_ids_perf(db, emp_id, recursive=True))

            _crm_viewer_is_self = (emp_id == current_user.id)
            _crm_unrestricted = _is_vgk_or_ea(current_user) if _crm_viewer_is_self else False

            if _crm_unrestricted:
                # EA / Key Leadership / VGK: org-wide revenue (same company)
                _all_co_ids = [r[0] for r in db.query(StaffEmployee.id).filter(
                    StaffEmployee.base_company_id == current_user.base_company_id,
                    StaffEmployee.status == 'active',
                    StaffEmployee.is_deleted == False
                ).all()]
                crm_rev = float(db.query(func.coalesce(func.sum(CRMLeadTransaction.amount), 0)).filter(
                    CRMLeadTransaction.collected_by_id.in_(_all_co_ids),
                    func.date(CRMLeadTransaction.transaction_date).between(d_from, d_to),
                    CRMLeadTransaction.validation_status != 'rejected'
                ).scalar() or 0)
                actuals['crm_revenue'] = crm_rev
                actuals['crm_revenue_is_team'] = True
                actuals['crm_revenue_scope'] = 'org'
                actuals['crm_revenue_downline_count'] = len(_all_co_ids)
            elif _emp_dl:
                # Manager with reporting chain: team (downline) revenue
                crm_rev = float(db.query(func.coalesce(func.sum(CRMLeadTransaction.amount), 0)).filter(
                    CRMLeadTransaction.collected_by_id.in_(_emp_dl),
                    func.date(CRMLeadTransaction.transaction_date).between(d_from, d_to),
                    CRMLeadTransaction.validation_status != 'rejected'
                ).scalar() or 0)
                actuals['crm_revenue'] = crm_rev
                actuals['crm_revenue_is_team'] = True
                actuals['crm_revenue_downline_count'] = len(_emp_dl)
            else:
                # Individual contributor: own revenue
                crm_rev = float(db.query(func.coalesce(func.sum(CRMLeadTransaction.amount), 0)).filter(
                    CRMLeadTransaction.collected_by_id == emp_id,
                    func.date(CRMLeadTransaction.transaction_date).between(d_from, d_to)
                ).scalar() or 0)
                actuals['crm_revenue'] = crm_rev
                actuals['crm_revenue_is_team'] = False
                actuals['crm_revenue_downline_count'] = 0
            svc_q = db.query(
                func.count(ServiceTicket.id).label('total'),
                func.sum(case((ServiceTicket.status.in_(['Resolved', 'Closed', 'resolved', 'closed']), 1), else_=0)).label('resolved'),
                func.sum(case((ServiceTicket.sla_status == 'Within SLA', 1), else_=0)).label('within_tat')
            ).filter(
                ServiceTicket.service_technician_id == emp_id,
                func.date(ServiceTicket.created_date).between(d_from, d_to)
            ).one()
            svc_total = int(svc_q.total or 0)
            if svc_total > 0:
                res_pct = round(int(svc_q.resolved or 0) / svc_total * 100, 1)
                tat_pct = round(int(svc_q.within_tat or 0) / svc_total * 100, 1)
                actuals['service_tickets'] = (res_pct + tat_pct) / 2
            else:
                actuals['service_tickets'] = 0.0
            proc_row = db.execute(text("""
                SELECT COALESCE(SUM(ordered_qty),0), COALESCE(SUM(received_qty),0),
                       COALESCE(SUM(CASE WHEN status='cancelled' THEN ordered_qty ELSE 0 END),0)
                FROM marketplace_procurement_requests
                WHERE store_manager_id = :eid AND created_at::date BETWEEN :df AND :dt
            """), {'eid': emp_id, 'df': d_from, 'dt': d_to}).fetchone()
            p_denom = float(proc_row[0] or 0) - float(proc_row[2] or 0)
            actuals['procurement'] = round(float(proc_row[1] or 0) / p_denom * 100, 1) if p_denom > 0 else 0.0
            po_row = db.execute(text("""
                SELECT COUNT(*) AS total,
                    SUM(CASE WHEN status IN ('payment_received','dispatched','completed')
                             AND completed_at IS NOT NULL
                             AND EXTRACT(EPOCH FROM (completed_at - created_at)) <= 172800
                        THEN 1 ELSE 0 END) AS within_tat
                FROM marketplace_purchase_orders
                WHERE store_manager_id = :eid AND status NOT IN ('cancelled','hold')
                  AND created_at::date BETWEEN :df AND :dt
            """), {'eid': emp_id, 'df': d_from, 'dt': d_to}).fetchone()
            po_total = int(po_row[0] or 0)
            actuals['po_handling'] = round(int(po_row[1] or 0) / po_total * 100, 1) if po_total > 0 else None
            prh_row = db.execute(text("""
                SELECT COUNT(*) AS total,
                    SUM(CASE WHEN status IN ('quality_confirmed','added_to_stock')
                             AND EXTRACT(EPOCH FROM (updated_at - created_at)) <= 172800
                        THEN 1 ELSE 0 END) AS within_tat
                FROM marketplace_procurement_requests
                WHERE store_manager_id = :eid AND status NOT IN ('cancelled','hold')
                  AND created_at::date BETWEEN :df AND :dt
            """), {'eid': emp_id, 'df': d_from, 'dt': d_to}).fetchone()
            prh_total = int(prh_row[0] or 0)
            actuals['procurement_handling'] = round(int(prh_row[1] or 0) / prh_total * 100, 1) if prh_total > 0 else None
            actuals['team_revenue'] = None
            actuals['team_performance'] = None
            return actuals

        period_actuals = _compute_actuals(date_from, date_to, target_id)
        mtd_actuals = _compute_actuals(mtd_start, mtd_end, target_id)

        kpi_results = []
        total_weight = 0.0
        for gcfg in config:
            kpi_code = gcfg['kpi_code']
            is_enabled, monthly_target, weightage = _eff(kpi_code, gcfg)
            if not is_enabled:
                continue
            prorated_target = round(monthly_target * period_days / days_in_month, 2)
            period_actual = period_actuals.get(kpi_code)
            mtd_actual = mtd_actuals.get(kpi_code)
            is_custom = gcfg.get('is_custom', False)
            if period_actual is not None and not is_custom:
                pt = prorated_target if prorated_target > 0 else 1.0
                period_score = round(min((period_actual / pt) * 100, BONUS_CAP), 1)
            else:
                period_score = None
            if mtd_actual is not None and not is_custom:
                period_score_mtd = round(min((mtd_actual / monthly_target) * 100, BONUS_CAP), 1) if monthly_target > 0 else 0.0
            else:
                period_score_mtd = None
            kpi_results.append({
                'kpi_code': kpi_code,
                'kpi_label': gcfg['kpi_label'],
                'target_unit': gcfg['target_unit'],
                'weightage_pct': weightage,
                'monthly_target': monthly_target,
                'prorated_target': prorated_target,
                'period_actual': period_actual,
                'mtd_actual': mtd_actual,
                'period_score': period_score,
                'mtd_score': period_score_mtd,
                'is_custom': is_custom,
                'is_na': period_actual is None,
                # DC Protocol: crm_revenue flag — is this tracking team/org/personal revenue?
                'is_team_metric': period_actuals.get('crm_revenue_is_team', False) if kpi_code == 'crm_revenue' else False,
                'team_member_count': period_actuals.get('crm_revenue_downline_count', 0) if kpi_code == 'crm_revenue' else 0,
                'revenue_scope': period_actuals.get('crm_revenue_scope', 'personal') if kpi_code == 'crm_revenue' else None,
            })
            if period_score is not None:
                total_weight += weightage

        overall_period, overall_mtd = 0.0, 0.0
        if total_weight > 0:
            for k in kpi_results:
                if k['period_score'] is not None:
                    overall_period += k['period_score'] * (k['weightage_pct'] / total_weight)
                if k['mtd_score'] is not None:
                    overall_mtd += k['mtd_score'] * (k['weightage_pct'] / total_weight)

        return {
            'success': True,
            'employee': {
                'id': target_emp.id,
                'emp_code': target_emp.emp_code or '',
                'name': target_emp.full_name or '',
                'department': target_emp.department.name if target_emp.department else '',
                'role': target_emp.role.role_name if target_emp.role else '',
            },
            'date_range': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'days_in_range': period_days,
                'days_in_month': days_in_month,
                'month': rpt_month,
                'year': rpt_year,
                'mtd_start': mtd_start.isoformat(),
                'mtd_end': mtd_end.isoformat(),
            },
            'kpi_config': kpi_results,
            'overall': {
                'period_score': round(overall_period, 1),
                'mtd_score': round(overall_mtd, 1),
                'total_weight': round(total_weight, 2),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EMPLOYEE-KPIS] Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"KPI summary error: {str(e)}")


# ── GET /performance/report ───────────────────────────────────────────────────

@router.get("/performance/report", summary="Performance Report — VGK Supreme & EA only")
def get_performance_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    department_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    include_self: bool = Query(False),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    if not _is_vgk_or_ea(current_user):
        raise HTTPException(status_code=403, detail="Access restricted to VGK Supreme and EA")

    if (date_to - date_from).days > 62:
        date_from = date_to - timedelta(days=61)
    total_days = (date_to - date_from).days + 1
    # Derive month/year from date_from for target lookup
    rpt_month = date_from.month
    rpt_year = date_from.year

    config = _load_config(db)
    global_enabled = {c['kpi_code']: c for c in config if c['is_enabled']}

    from app.models.staff import StaffDepartment
    from app.models.staff_accounts import AssociatedCompany
    from app.models.call_tracking import StaffCallLog

    emp_q = (
        db.query(StaffEmployee)
        .options(joinedload(StaffEmployee.department), joinedload(StaffEmployee.role))
        .filter(StaffEmployee.status == 'active', StaffEmployee.emp_code.isnot(None))
    )
    if company_id:
        emp_q = emp_q.filter(StaffEmployee.base_company_id == company_id)
    if department_id:
        emp_q = emp_q.filter(StaffEmployee.department_id == department_id)
    if not include_self:
        hidden = HIDDEN_FROM_TEAM_CODES or []
        if hidden:
            emp_q = emp_q.filter(~StaffEmployee.emp_code.in_(hidden))
    all_emps = emp_q.all()
    all_ids = [e.id for e in all_emps]

    if not all_ids:
        return {'success': True, 'data': [], 'total': 0, 'config': config,
                'date_range': {'from': date_from.isoformat(), 'to': date_to.isoformat()}}

    # Per-employee targets for this month
    emp_targets = _load_employee_targets_raw(db, all_ids, rpt_month, rpt_year)

    # ── Per-employee effective days (total_days minus leave days) ─────────────
    from app.utils.leave_utils import get_employee_leave_dates as _get_leave_dates
    _leave_map = _get_leave_dates(db, all_ids, date_from, date_to)
    effective_days_map = {
        emp_id: max(1, total_days - len(_leave_map.get(emp_id, set())))
        for emp_id in all_ids
    }

    # ── Data queries ──────────────────────────────────────────────────────────
    att_rows = db.query(
        StaffAttendance.employee_id,
        func.sum(case((StaffAttendance.status == 'present', 1), else_=0)).label('days_present'),
        func.sum(func.coalesce(StaffAttendance.worked_minutes, 0)).label('worked_minutes'),
    ).filter(
        StaffAttendance.employee_id.in_(all_ids),
        StaffAttendance.date.between(date_from, date_to),
    ).group_by(StaffAttendance.employee_id).all()
    att_map = {r.employee_id: {'days_present': int(r.days_present or 0),
                                'worked_minutes': int(r.worked_minutes or 0)} for r in att_rows}

    dp_rows = db.query(
        StaffDayPlan.employee_id,
        func.count(StaffDayPlan.id).label('plans'),
        func.sum(StaffDayPlan.total_planned).label('total_planned'),
        func.sum(StaffDayPlan.total_completed).label('total_completed'),
    ).filter(
        StaffDayPlan.employee_id.in_(all_ids),
        StaffDayPlan.plan_date.between(date_from, date_to),
    ).group_by(StaffDayPlan.employee_id).all()
    dp_map = {r.employee_id: {
        'plans': int(r.plans or 0),
        'pct': round((int(r.total_completed or 0) / int(r.total_planned or 1)) * 100)
               if int(r.total_planned or 0) > 0 else 0
    } for r in dp_rows}

    kra_rows = db.query(
        StaffKRADailyInstance.employee_id,
        func.count(StaffKRADailyInstance.id).label('total'),
        func.sum(case((StaffKRADailyInstance.completion_status == 'completed', 1), else_=0)).label('completed'),
    ).filter(
        StaffKRADailyInstance.employee_id.in_(all_ids),
        StaffKRADailyInstance.instance_date.between(date_from, date_to),
        StaffKRADailyInstance.completion_status.notin_(['na', 'skipped']),
    ).group_by(StaffKRADailyInstance.employee_id).all()
    kra_map = {r.employee_id: {'total': int(r.total or 0), 'completed': int(r.completed or 0)} for r in kra_rows}

    ts_rows = db.query(
        StaffTimesheetEntry.employee_id,
        func.count(func.distinct(func.date(StaffTimesheetEntry.date))).label('days_submitted'),
    ).filter(
        StaffTimesheetEntry.employee_id.in_(all_ids),
        func.date(StaffTimesheetEntry.date).between(date_from, date_to),
    ).group_by(StaffTimesheetEntry.employee_id).all()
    ts_map = {r.employee_id: int(r.days_submitted or 0) for r in ts_rows}

    svc_rows = db.query(
        ServiceTicket.service_technician_id,
        func.count(ServiceTicket.id).label('total'),
        func.sum(case((ServiceTicket.status.in_(['Resolved', 'Closed']), 1), else_=0)).label('resolved'),
        func.sum(case((ServiceTicket.sla_status == 'Within SLA', 1), else_=0)).label('within_tat'),
    ).filter(
        ServiceTicket.service_technician_id.in_(all_ids),
        func.date(ServiceTicket.created_date).between(date_from, date_to),
    ).group_by(ServiceTicket.service_technician_id).all()
    svc_map = {r.service_technician_id: {
        'total': int(r.total or 0), 'resolved': int(r.resolved or 0), 'within_tat': int(r.within_tat or 0)
    } for r in svc_rows}

    txn_rows = db.query(
        CRMLeadTransaction.collected_by_id,
        func.coalesce(func.sum(CRMLeadTransaction.amount), 0).label('txn_revenue'),
    ).filter(
        CRMLeadTransaction.collected_by_id.in_(all_ids),
        func.date(CRMLeadTransaction.transaction_date).between(date_from, date_to),
    ).group_by(CRMLeadTransaction.collected_by_id).all()
    txn_map = {r.collected_by_id: float(r.txn_revenue or 0) for r in txn_rows}

    call_rows = db.query(
        StaffCallLog.staff_id,
        func.sum(StaffCallLog.duration_seconds).label('total_seconds'),
    ).filter(
        StaffCallLog.staff_id.in_(all_ids),
        StaffCallLog.call_date.between(str(date_from), str(date_to)),
    ).group_by(StaffCallLog.staff_id).all()
    call_map = {r.staff_id: int(r.total_seconds or 0) for r in call_rows}

    proc_rows = db.execute(text("""
        SELECT CAST(actioned_by AS INTEGER) AS staff_id,
               SUM(ordered_qty) AS total_ordered,
               SUM(CASE WHEN status='cancelled' THEN ordered_qty ELSE 0 END) AS cancelled_qty,
               SUM(received_qty) AS total_received
        FROM marketplace_procurement_requests
        WHERE actioned_by ~ '^[0-9]+$'
          AND actioned_at::date BETWEEN :d_from AND :d_to
        GROUP BY CAST(actioned_by AS INTEGER)
    """), {'d_from': date_from, 'd_to': date_to}).fetchall()
    proc_map = {}
    for r in proc_rows:
        sid, total_ordered = r[0], int(r[1] or 0)
        cancelled, received = int(r[2] or 0), int(r[3] or 0)
        effective = total_ordered - cancelled
        proc_map[sid] = {
            'total_ordered': total_ordered, 'cancelled_qty': cancelled,
            'received_qty': received, 'effective_qty': effective,
            'pct': round((received / effective) * 100) if effective > 0 else 0,
        }

    # ── New KPI data queries (March 2026) ─────────────────────────────────────
    # Build a Python children map for downline traversal (all active employees)
    _all_rpts = db.query(
        StaffEmployee.id,
        StaffEmployee.reporting_manager_id,
    ).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.reporting_manager_id.isnot(None),
    ).all()
    _children_map: dict = {}
    for _eid, _mid in _all_rpts:
        _children_map.setdefault(_mid, []).append(_eid)

    def _get_downline_ids(mgr_id: int, max_depth: int = 10) -> set:
        result, queue = set(), [(mgr_id, 0)]
        while queue:
            cur, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for child in _children_map.get(cur, []):
                if child not in result:
                    result.add(child)
                    queue.append((child, depth + 1))
        return result

    # team_revenue: sum CRM transactions for entire downline
    _all_txn_rows = db.execute(text("""
        SELECT collected_by_id, COALESCE(SUM(amount), 0) AS rev
        FROM crm_lead_transactions
        WHERE collected_by_id IS NOT NULL
          AND transaction_date::date BETWEEN :d_from AND :d_to
        GROUP BY collected_by_id
    """), {'d_from': date_from, 'd_to': date_to}).fetchall()
    _all_txn_map = {r[0]: float(r[1] or 0) for r in _all_txn_rows}

    team_revenue_map: dict = {}
    for _eid in all_ids:
        _dl = _get_downline_ids(_eid)
        if not _dl:
            team_revenue_map[_eid] = None
        else:
            team_revenue_map[_eid] = sum(_all_txn_map.get(d, 0.0) for d in _dl)

    # po_handling: POs assigned via store_manager_id — 48h TAT rate
    po_h_rows = db.execute(text("""
        SELECT store_manager_id,
               COUNT(*) AS total,
               SUM(CASE
                   WHEN status IN ('payment_received','dispatched','completed')
                    AND completed_at IS NOT NULL
                    AND EXTRACT(EPOCH FROM (completed_at - created_at)) <= 172800
                   THEN 1 ELSE 0 END) AS within_tat
        FROM marketplace_purchase_orders
        WHERE store_manager_id = ANY(:mgr_ids)
          AND status NOT IN ('cancelled','hold')
          AND created_at::date BETWEEN :d_from AND :d_to
        GROUP BY store_manager_id
    """), {'mgr_ids': all_ids, 'd_from': date_from, 'd_to': date_to}).fetchall()
    po_handling_map: dict = {}
    for r in po_h_rows:
        total, within_tat = int(r[1] or 0), int(r[2] or 0)
        po_handling_map[r[0]] = {
            'total': total, 'within_tat': within_tat,
            'pct': round((within_tat / total) * 100, 1) if total > 0 else 0,
        }

    # procurement_handling: procurements assigned via store_manager_id — 48h TAT rate
    proc_h_rows = db.execute(text("""
        SELECT store_manager_id,
               COUNT(*) AS total,
               SUM(CASE
                   WHEN status IN ('quality_confirmed','added_to_stock')
                    AND EXTRACT(EPOCH FROM (updated_at - created_at)) <= 172800
                   THEN 1 ELSE 0 END) AS within_tat
        FROM marketplace_procurement_requests
        WHERE store_manager_id = ANY(:mgr_ids)
          AND status NOT IN ('cancelled','hold')
          AND created_at::date BETWEEN :d_from AND :d_to
        GROUP BY store_manager_id
    """), {'mgr_ids': all_ids, 'd_from': date_from, 'd_to': date_to}).fetchall()
    procurement_handling_map: dict = {}
    for r in proc_h_rows:
        total, within_tat = int(r[1] or 0), int(r[2] or 0)
        procurement_handling_map[r[0]] = {
            'total': total, 'within_tat': within_tat,
            'pct': round((within_tat / total) * 100, 1) if total > 0 else 0,
        }

    # team_performance: computed in a second pass after individual scores are assembled
    _individual_scores: dict = {}  # emp_id -> overall_score (populated in first pass)

    # ── Per-employee scoring ──────────────────────────────────────────────────
    BONUS_CAP = 120.0

    def _resolve_kpi_settings(kpi_code: str, emp_id: int, gcfg: dict):
        """Returns (is_enabled, target, weightage) using per-employee override where set."""
        row = emp_targets.get(emp_id, {}).get(kpi_code)
        is_enabled = row['is_enabled'] if (row and row['is_enabled'] is not None) else gcfg['is_enabled']
        target = float(row['target_value'] if row else gcfg['target_value']) or 1.0
        weightage = float(row['weightage_pct'] if (row and row['weightage_pct'] is not None) else gcfg['weightage_pct'])
        return is_enabled, target, weightage

    def _kpi_actual(kpi_code: str, emp_id: int, cfg: dict) -> tuple:
        sub = cfg.get('sub_config') or {}
        actual, display = 0.0, {}

        if kpi_code == 'attendance':
            dp = att_map.get(emp_id, {}).get('days_present', 0)
            eff = effective_days_map.get(emp_id, total_days)
            actual = round((dp / eff) * 100, 1)
            display = {'days_present': dp, 'working_days': eff}

        elif kpi_code == 'day_plan':
            actual = float(dp_map.get(emp_id, {}).get('pct', 0))
            display = {'plans': dp_map.get(emp_id, {}).get('plans', 0)}

        elif kpi_code == 'kra':
            k = kra_map.get(emp_id, {'total': 0, 'completed': 0})
            actual = round((k['completed'] / k['total']) * 100, 1) if k['total'] > 0 else 0
            display = k

        elif kpi_code == 'timesheet':
            ds = ts_map.get(emp_id, 0)
            eff = effective_days_map.get(emp_id, total_days)
            actual = round((ds / eff) * 100, 1)
            display = {'days_submitted': ds, 'working_days': eff}

        elif kpi_code == 'talk_time':
            secs = call_map.get(emp_id, 0)
            days_p = max(att_map.get(emp_id, {}).get('days_present', 1), 1)
            avg_min = round(secs / 60 / days_p, 1)
            actual = avg_min
            display = {'avg_min_per_day': avg_min, 'total_seconds': secs}

        elif kpi_code == 'service_tickets':
            sv = svc_map.get(emp_id, {'total': 0, 'resolved': 0, 'within_tat': 0})
            total_t = sv['total']
            min_t = int(sub.get('min_tickets', 0))
            tat_t = float(sub.get('tat_pct', 0))
            if total_t < min_t:
                actual = 0
                display = {**sv, 'below_min_threshold': True}
            else:
                res_pct = round((sv['resolved'] / total_t) * 100, 1) if total_t > 0 else 0
                tat_pct = round((sv['within_tat'] / total_t) * 100, 1) if total_t > 0 else 0
                actual = (res_pct + tat_pct) / 2 if tat_t > 0 else res_pct
                display = {**sv, 'resolution_pct': res_pct, 'tat_pct': tat_pct}

        elif kpi_code == 'crm_revenue':
            actual = txn_map.get(emp_id, 0.0)
            display = {'revenue': actual}

        elif kpi_code == 'procurement':
            pm = proc_map.get(emp_id, {})
            actual = float(pm.get('pct', 0))
            display = pm

        elif kpi_code == 'team_revenue':
            val = team_revenue_map.get(emp_id)
            if val is None:
                return None, {'note': 'no_direct_reports'}
            actual = float(val)
            display = {'team_revenue': actual}

        elif kpi_code == 'po_handling':
            pm = po_handling_map.get(emp_id)
            if pm is None:
                return None, {'note': 'no_pos_assigned'}
            actual = float(pm.get('pct', 0))
            display = pm

        elif kpi_code == 'procurement_handling':
            pm = procurement_handling_map.get(emp_id)
            if pm is None:
                return None, {'note': 'no_procurement_assigned'}
            actual = float(pm.get('pct', 0))
            display = pm

        elif kpi_code == 'team_performance':
            # team_performance is resolved in the second pass; skip here
            return None, {'note': 'pending_second_pass'}

        elif cfg.get('is_custom'):
            # Custom KPIs have no automated data source — excluded from score
            return None, {'note': 'custom_kpi_no_data'}

        return actual, display

    results = []
    for emp in all_emps:
        kpi_scores = {}
        overall = 0.0
        total_w = 0.0

        # Determine which KPIs apply to this employee
        for kpi_code, gcfg in global_enabled.items():
            is_enabled, target, weightage = _resolve_kpi_settings(kpi_code, emp.id, gcfg)
            if not is_enabled:
                continue
            actual, display = _kpi_actual(kpi_code, emp.id, gcfg)
            if actual is None:
                # Custom KPI — show in results but exclude from score
                row = emp_targets.get(emp.id, {}).get(kpi_code)
                kpi_scores[kpi_code] = {
                    'actual': None, 'target': target, 'weightage': weightage,
                    'global_target': gcfg['target_value'],
                    'score': None, 'display': display,
                    'is_custom': True,
                    'is_custom_target': row is not None,
                }
                continue
            raw_score = min((actual / target) * 100, BONUS_CAP) if target > 0 else 0
            score = round(raw_score, 1)
            row = emp_targets.get(emp.id, {}).get(kpi_code)
            kpi_scores[kpi_code] = {
                'actual': actual, 'target': target, 'weightage': weightage,
                'global_target': gcfg['target_value'],
                'is_custom_target': row is not None and row['target_value'] != gcfg['target_value'],
                'is_custom_weight': row is not None and row['weightage_pct'] is not None,
                'score': score, 'bonus': score > 100, 'display': display,
            }
            total_w += weightage

        # Overall weighted score (skip None — custom KPIs excluded from auto-score)
        if total_w > 0:
            for kpi_code, ks in kpi_scores.items():
                if ks.get('score') is not None:
                    overall += ks['score'] * (ks['weightage'] / total_w)

        result_entry = {
            'employee_id': emp.id,
            'emp_code': emp.emp_code or '',
            'name': emp.full_name or '',
            'department': emp.department.name if emp.department else '—',
            'department_id': emp.department_id,
            'role': emp.role.role_name if emp.role else '—',
            'role_id': emp.role_id,
            'days_present': att_map.get(emp.id, {}).get('days_present', 0),
            'overall_score': round(overall, 1),
            'total_weight': round(total_w, 2),
            'kpi_scores': kpi_scores,
        }
        _individual_scores[emp.id] = round(overall, 1)
        results.append(result_entry)

    # ── Second pass: team_performance KPI ────────────────────────────────────
    if 'team_performance' in global_enabled:
        gcfg_tp = global_enabled['team_performance']
        for result_entry in results:
            emp_id = result_entry['employee_id']
            is_enabled, target, weightage = _resolve_kpi_settings('team_performance', emp_id, gcfg_tp)
            if not is_enabled:
                continue
            downline_ids = _get_downline_ids(emp_id)
            scores_in_downline = [_individual_scores[d] for d in downline_ids if d in _individual_scores]
            if not scores_in_downline:
                result_entry['kpi_scores']['team_performance'] = {
                    'actual': None, 'target': target, 'weightage': weightage,
                    'global_target': gcfg_tp['target_value'],
                    'score': None, 'display': {'note': 'no_direct_reports'},
                    'is_custom': True, 'is_custom_target': False,
                }
                continue
            avg_team_score = round(sum(scores_in_downline) / len(scores_in_downline), 1)
            raw_score_tp = min((avg_team_score / target) * 100, BONUS_CAP) if target > 0 else 0
            score_tp = round(raw_score_tp, 1)
            row_tp = emp_targets.get(emp_id, {}).get('team_performance')
            result_entry['kpi_scores']['team_performance'] = {
                'actual': avg_team_score, 'target': target, 'weightage': weightage,
                'global_target': gcfg_tp['target_value'],
                'is_custom_target': row_tp is not None and row_tp['target_value'] != gcfg_tp['target_value'],
                'is_custom_weight': row_tp is not None and row_tp['weightage_pct'] is not None,
                'score': score_tp, 'bonus': score_tp > 100,
                'display': {'avg_team_score': avg_team_score, 'member_count': len(scores_in_downline)},
            }
            # Recompute overall_score to include team_performance
            total_w_new = 0.0
            overall_new = 0.0
            for kc, ks in result_entry['kpi_scores'].items():
                if ks.get('score') is not None:
                    total_w_new += ks['weightage']
            if total_w_new > 0:
                for kc, ks in result_entry['kpi_scores'].items():
                    if ks.get('score') is not None:
                        overall_new += ks['score'] * (ks['weightage'] / total_w_new)
            result_entry['overall_score'] = round(overall_new, 1)
            result_entry['total_weight'] = round(total_w_new, 2)

    results.sort(key=lambda x: x['overall_score'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    dept_ids = list({e.department_id for e in all_emps if e.department_id})
    from app.models.staff import StaffDepartment
    dept_objs = db.query(StaffDepartment).filter(StaffDepartment.id.in_(dept_ids)).all() if dept_ids else []
    co_ids = list({e.base_company_id for e in all_emps if e.base_company_id})
    from app.models.staff_accounts import AssociatedCompany
    co_objs = db.query(AssociatedCompany).filter(AssociatedCompany.id.in_(co_ids)).all() if co_ids else []

    return {
        'success': True,
        'data': results,
        'total': len(results),
        'config': config,
        'enabled_kpis': list(global_enabled.keys()),
        'departments': [{'id': d.id, 'name': d.name} for d in dept_objs],
        'companies': [{'id': c.id, 'name': c.company_name, 'code': c.company_code} for c in co_objs],
        'date_range': {'from': date_from.isoformat(), 'to': date_to.isoformat()},
    }


# ══════════════════════════════════════════════════════════════════════════════
# STAFF INCENTIVE CONFIG — DC_STAFF_INCFG_001
# ══════════════════════════════════════════════════════════════════════════════
from pydantic import BaseModel


class IncentiveConfigRow(BaseModel):
    company_id: int = 1
    month: int
    year: int
    category_slug: str
    category_label: str
    min_target_value: float
    min_target_unit: str = 'amount'          # 'count' | 'amount'
    incentive_rate_without_support: float
    incentive_rate_with_support: float
    incentive_rate_direct_work: float = 0.0  # DC-INCENTIVE-LEAD-TYPE-003
    incentive_type: str = 'percentage'       # 'percentage' | 'fixed_per_unit'
    bonus_trigger_value: Optional[float] = None
    bonus_multiplier: float = 1.20
    is_active: bool = True


def _incfg_row(r) -> dict:
    return {
        'id': r[0], 'company_id': r[1], 'month': r[2], 'year': r[3],
        'category_slug': r[4], 'category_label': r[5],
        'min_target_value': float(r[6] or 0),
        'min_target_unit': r[7] or 'amount',
        'incentive_rate_without_support': float(r[8] or 0),
        'incentive_rate_with_support': float(r[9] or 0),
        'incentive_rate_direct_work': float(r[10] or 0),
        'incentive_type': r[11] or 'percentage',
        'bonus_trigger_value': float(r[12]) if r[12] is not None else None,
        'bonus_multiplier': float(r[13] or 1.2),
        'is_active': bool(r[14]),
    }


@router.get("/incentive-config/access-check", summary="Check incentive access level")
def incentive_access_check(
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    """Returns access level: 'admin' | 'read' | 'denied'"""
    dept_name = (me.department.name or '').lower() if me.department else ''
    role_name = (me.role.role_name or '').lower() if me.role else ''
    emp_code = me.emp_code or ''
    is_admin = _is_vgk_or_ea(me) or 'key leadership' in role_name or 'leadership' in role_name
    is_sales = 'sales' in dept_name
    # Check if manager with sales downline
    has_sales_downline = False
    if not is_sales and not is_admin:
        from app.utils.staff_hierarchy import get_recursive_downline
        try:
            downline = get_recursive_downline(db, emp_code, include_self=False) if emp_code else []
            from app.models.staff import StaffEmployee as _SE, StaffDepartment as _SD
            for _dl_emp in db.query(_SE).filter(_SE.emp_code.in_(downline)).all():
                _dl_dept = (_dl_emp.department.name or '').lower() if _dl_emp.department else ''
                if 'sales' in _dl_dept:
                    has_sales_downline = True
                    break
        except Exception:
            pass
    if is_admin:
        level = 'admin'
    elif is_sales or has_sales_downline:
        level = 'read'
    else:
        level = 'denied'
    return {
        'success': True,
        'access_level': level,
        'is_admin': is_admin,
        'is_sales': is_sales,
        'employee_id': me.id,
        'emp_code': emp_code,
    }


@router.get("/incentive-config", summary="Get incentive config table")
def get_incentive_config(
    company_id: int = Query(1),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    where = ["company_id = :co"]
    params: dict = {"co": company_id}
    if month:
        where.append("month = :mo"); params["mo"] = month
    if year:
        where.append("year = :yr"); params["yr"] = year
    rows = db.execute(text(
        "SELECT id, company_id, month, year, category_slug, category_label, "
        "min_target_value, min_target_unit, incentive_rate_without_support, "
        "incentive_rate_with_support, incentive_rate_direct_work, incentive_type, bonus_trigger_value, "
        "bonus_multiplier, is_active "
        f"FROM staff_incentive_config WHERE {' AND '.join(where)} "
        "ORDER BY year DESC, month DESC, id"
    ), params).fetchall()
    return {'success': True, 'config': [_incfg_row(r) for r in rows]}


@router.post("/incentive-config", summary="Create incentive config row (admin only)")
def create_incentive_config(
    payload: IncentiveConfigRow,
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    if not _is_vgk_or_ea(me) and 'leadership' not in (me.role.role_name or '').lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        row = db.execute(text("""
            INSERT INTO staff_incentive_config
                (company_id, month, year, category_slug, category_label, min_target_value, min_target_unit,
                 incentive_rate_without_support, incentive_rate_with_support, incentive_rate_direct_work,
                 incentive_type, bonus_trigger_value, bonus_multiplier, is_active, created_by, updated_at)
            VALUES (:co, :mo, :yr, :slug, :lbl, :min_v, :min_u, :r_no, :r_wi, :r_dw, :itype, :btrig, :bmul, :act, :by, NOW())
            RETURNING id
        """), dict(co=payload.company_id, mo=payload.month, yr=payload.year,
                   slug=payload.category_slug, lbl=payload.category_label,
                   min_v=payload.min_target_value, min_u=payload.min_target_unit,
                   r_no=payload.incentive_rate_without_support, r_wi=payload.incentive_rate_with_support,
                   r_dw=payload.incentive_rate_direct_work,
                   itype=payload.incentive_type, btrig=payload.bonus_trigger_value,
                   bmul=payload.bonus_multiplier, act=payload.is_active, by=me.emp_code or me.id)).fetchone()
        db.commit()
        return {'success': True, 'id': row[0]}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/incentive-config/{row_id}", summary="Update incentive config row (admin only)")
def update_incentive_config(
    row_id: int,
    payload: IncentiveConfigRow,
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    if not _is_vgk_or_ea(me) and 'leadership' not in (me.role.role_name or '').lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    db.execute(text("""
        UPDATE staff_incentive_config SET
            category_label=:lbl, min_target_value=:min_v, min_target_unit=:min_u,
            incentive_rate_without_support=:r_no, incentive_rate_with_support=:r_wi,
            incentive_rate_direct_work=:r_dw,
            incentive_type=:itype, bonus_trigger_value=:btrig, bonus_multiplier=:bmul,
            is_active=:act, updated_at=NOW()
        WHERE id=:rid
    """), dict(rid=row_id, lbl=payload.category_label, min_v=payload.min_target_value,
               min_u=payload.min_target_unit, r_no=payload.incentive_rate_without_support,
               r_wi=payload.incentive_rate_with_support, r_dw=payload.incentive_rate_direct_work,
               itype=payload.incentive_type, btrig=payload.bonus_trigger_value,
               bmul=payload.bonus_multiplier, act=payload.is_active))
    db.commit()
    return {'success': True}


@router.delete("/incentive-config/{row_id}", summary="Delete incentive config row (admin only)")
def delete_incentive_config(
    row_id: int,
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    if not _is_vgk_or_ea(me) and 'leadership' not in (me.role.role_name or '').lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    db.execute(text("DELETE FROM staff_incentive_config WHERE id=:rid"), {'rid': row_id})
    db.commit()
    return {'success': True}


@router.post("/incentive-config/copy-month", summary="Copy incentive config to next month")
def copy_incentive_month(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    """Copy all active config rows from source month/year to the following month.
    Idempotent: returns error message if target month already has rows."""
    if not _is_vgk_or_ea(me) and 'leadership' not in (me.role.role_name or '').lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    import calendar as _c
    src_month  = int(payload.get('month', 1))
    src_year   = int(payload.get('year', 2026))
    company_id = int(payload.get('company_id') or 0)  # 0 = all companies
    all_companies = (company_id == 0)
    next_month = src_month + 1
    next_year  = src_year
    if next_month > 12:
        next_month = 1
        next_year += 1
    # Check for existing rows in target month
    if all_companies:
        existing = db.execute(text(
            "SELECT COUNT(*) FROM staff_incentive_config "
            "WHERE month=:mo AND year=:yr"
        ), {'mo': next_month, 'yr': next_year}).scalar()
    else:
        existing = db.execute(text(
            "SELECT COUNT(*) FROM staff_incentive_config "
            "WHERE company_id=:co AND month=:mo AND year=:yr"
        ), {'co': company_id, 'mo': next_month, 'yr': next_year}).scalar()
    if existing:
        scope = "All companies" if all_companies else f"Company {company_id}"
        return {'success': False,
                'message': f'{scope}: config already exists for {_c.month_abbr[next_month]} {next_year}. '
                           f'Delete existing rows first to overwrite.',
                'target_month': next_month, 'target_year': next_year}
    # Copy rows — preserve each row's own company_id when copying all companies
    if all_companies:
        result = db.execute(text("""
            INSERT INTO staff_incentive_config
                (company_id, month, year, category_slug, category_label,
                 min_target_value, min_target_unit, incentive_rate_without_support,
                 incentive_rate_with_support, incentive_rate_direct_work, incentive_type,
                 bonus_trigger_value, bonus_multiplier, is_active, created_by, updated_at)
            SELECT company_id, :nm, :ny, category_slug, category_label,
                   min_target_value, min_target_unit, incentive_rate_without_support,
                   incentive_rate_with_support, incentive_rate_direct_work, incentive_type,
                   bonus_trigger_value, bonus_multiplier, is_active, :by, NOW()
            FROM staff_incentive_config
            WHERE month=:mo AND year=:yr AND is_active=TRUE
        """), {'nm': next_month, 'ny': next_year,
               'mo': src_month, 'yr': src_year,
               'by': me.emp_code or str(me.id)})
    else:
        result = db.execute(text("""
            INSERT INTO staff_incentive_config
                (company_id, month, year, category_slug, category_label,
                 min_target_value, min_target_unit, incentive_rate_without_support,
                 incentive_rate_with_support, incentive_rate_direct_work, incentive_type,
                 bonus_trigger_value, bonus_multiplier, is_active, created_by, updated_at)
            SELECT :co, :nm, :ny, category_slug, category_label,
                   min_target_value, min_target_unit, incentive_rate_without_support,
                   incentive_rate_with_support, incentive_rate_direct_work, incentive_type,
                   bonus_trigger_value, bonus_multiplier, is_active, :by, NOW()
            FROM staff_incentive_config
            WHERE company_id=:src_co AND month=:mo AND year=:yr AND is_active=TRUE
        """), {'co': company_id, 'nm': next_month, 'ny': next_year,
               'src_co': company_id, 'mo': src_month, 'yr': src_year,
               'by': me.emp_code or str(me.id)})
    db.commit()
    count = result.rowcount
    scope = "All companies" if all_companies else f"Company {company_id}"
    return {'success': True,
            'message': f'Copied {count} row(s) to {_c.month_abbr[next_month]} {next_year} ({scope})',
            'target_month': next_month, 'target_year': next_year, 'rows_copied': count}


@router.get("/incentive-achievements", summary="Live incentive achievement calculation")
def get_incentive_achievements(
    company_id: Optional[int] = Query(None),
    month: int = Query(...),
    year: int = Query(...),
    employee_id: Optional[str] = Query(None),
    show_all: bool = Query(False, description="Include all active employees, even those with 0 achievements"),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Calculates achieved deals per category and computes incentive for each employee.
    company_id=None or 0 = all companies (uses company_id=1 as reference config).
    DC-INCENTIVE-TELE-FIELD-ONLY-001: telecaller_id + field_staff_id each receive 1x credit
    per lead. handler_id is excluded — incentives are earned only via explicit assignment.
    DISTINCT ON (lead_id, emp_key) prevents double-counting same employee.
    """
    import calendar as _cal

    all_companies = not company_id or company_id == 0
    cfg_company_id = 1 if all_companies else company_id

    # Date range for target month
    _last_day = _cal.monthrange(year, month)[1]
    date_from = datetime(year, month, 1)
    date_to = datetime(year, month, _last_day, 23, 59, 59)

    # Load incentive config (use cfg_company_id as reference rates)
    cfg_rows = db.execute(text(
        "SELECT category_slug, min_target_value, min_target_unit, "
        "incentive_rate_without_support, incentive_rate_with_support, "
        "incentive_rate_direct_work, incentive_type, "
        "bonus_trigger_value, bonus_multiplier "
        "FROM staff_incentive_config "
        "WHERE company_id=:co AND month=:mo AND year=:yr AND is_active=TRUE"
    ), {'co': cfg_company_id, 'mo': month, 'yr': year}).fetchall()

    if not cfg_rows:
        return {'success': True, 'data': [], 'note': 'No incentive config for this month/company'}

    cfg_by_slug = {r[0]: {
        'min_target_value': float(r[1]), 'min_target_unit': r[2],
        'rate_no': float(r[3]), 'rate_wi': float(r[4]),
        'rate_dw': float(r[5] or 0),  # DC-INCENTIVE-LEAD-TYPE-003: Direct Work rate
        'itype': r[6], 'bonus_trigger': float(r[7]) if r[7] else None,
        'bonus_mul': float(r[8] or 1.2)
    } for r in cfg_rows}

    # Category slug → ILIKE patterns
    CAT_PATTERNS = {
        'solar':       ['%solar%'],
        'ev_b2c':      ['%ev%b2c%', '%ev b2c%', '%ev-b2c%'],
        'ev_b2b':      ['%ev%b2b%', '%ev b2b%', '%ev-b2b%'],
        'training':    ['%training%', '%etc%'],
        'insurance':   ['%insurance%'],
        'real_estate': ['%real%estate%', '%real dream%', '%property%'],
    }

    # DC-CAT-ALL-001: When all_companies=True, fetch categories from ALL companies so
    # cross-company leads (e.g. ETC Training id=42 for co=2, id=30 for co=1) match correctly.
    if all_companies:
        all_cats = db.execute(text("SELECT id, name FROM signup_categories")).fetchall()
    else:
        all_cats = db.execute(text(
            "SELECT id, name FROM signup_categories WHERE company_id=:co"
        ), {'co': cfg_company_id}).fetchall()
    slug_to_cat_ids: dict = {s: [] for s in CAT_PATTERNS}
    for cat_id, cat_name in all_cats:
        cn = (cat_name or '').lower()
        for slug, patterns in CAT_PATTERNS.items():
            for pat in patterns:
                pat_clean = pat.replace('%', '')
                if pat_clean and all(p in cn for p in pat_clean.split() if p):
                    slug_to_cat_ids[slug].append(cat_id)
                    break

    # DC Protocol: telecaller_id + field_staff_id each get 1x credit per lead.
    # handler_id is EXCLUDED — incentives are only earned via explicit tele/field assignment
    # (DC-INCENTIVE-TELE-FIELD-ONLY-001). Lead owner / handler do NOT earn incentive credit.
    # DISTINCT ON (lead_id, emp_key) prevents same employee getting same lead twice.
    # DC-INCENTIVE-COMPANY-SRC-002: ONLY source='Self Lead' → self (rate_no, no bonus).
    # Every other source (Website, Referral, MNR, VGK4U, Walk-In, NULL, etc.) → company rate.
    # ETC Students are always company via DC-ETC-ALWAYS-COMPANY-001 post-processing override.
    # DC-LEAD-TYPE-PRESENCE-001: Company = lead has at least one MNR/VGK4U reference ID.
    # Self = source 'Self Lead'. Direct = everything else (no MNR/VGK4U link, not self).
    # Replaces confirmation-gate (DC-HANDLER-CONFIRM-GATE-001) for incentive classification.
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
    _co_clause = "" if all_companies else "AND l.company_id = :co"

    # DC-COMPLETED-001: Mirror _completed_exprs() from crm.py — three completion signals:
    #   Solar  → solar_pipeline_status='completed' (date: actual_close_date)
    #   B2B    → ev_b2b_stage='completed'          (date: actual_close_date)
    #   Others → status='completed' with both sub-status cols NULL (date: actual_close_date)
    #   ETC    → etc_students.training_completed_date in period (date: training_completed_date)
    # DC-CLOSE-DATE-001: Use actual close date (not updated_at) so edits to a lead's fields
    # after completion don't smuggle it into a later month's incentive period.
    # All CRM leads (including solar) use actual_close_date; ETC uses training_completed_date
    # via the EXISTS subquery below.
    _close_date_expr = "COALESCE(l.actual_close_date, l.updated_at)"
    _comp_where = f"""(
        (
            l.solar_pipeline_status = 'completed'
            OR l.ev_b2b_stage = 'completed'
            OR (l.status = 'completed'
                AND l.solar_pipeline_status IS NULL
                AND l.ev_b2b_stage IS NULL)
        ) AND ({_close_date_expr}) BETWEEN :df AND :dt
        OR EXISTS (
            SELECT 1 FROM etc_students s
            WHERE s.crm_lead_id = l.id
            AND s.training_completed_date IS NOT NULL
            AND s.training_completed_date BETWEEN :df_d AND :dt_d
            AND s.is_active = TRUE
        )
    )"""

    lead_q = text(f"""
        SELECT emp_key, category_id, dvr, has_support, partner_id, is_direct_work FROM (
            SELECT DISTINCT ON (lead_id, emp_key) lead_id, emp_key, category_id, dvr, has_support, partner_id, is_direct_work
            FROM (
                SELECT l.id                                                             AS lead_id,
                       l.telecaller_id::TEXT                                            AS emp_key,
                       l.category_id                                                    AS category_id,
                       COALESCE(NULLIF(l.deal_value_received,0), l.deal_value, 0)      AS dvr,
                       {_sup}                                                           AS has_support,
                       l.associated_partner_id                                          AS partner_id,
                       CASE WHEN (
                           (l.source IS NULL OR l.source != 'Self Lead')
                           AND l.guru_id IS NULL
                           AND l.z_guru_id IS NULL
                           AND l.adi_guru_id IS NULL
                           AND (l.mnr_handler_id IS NULL OR l.mnr_handler_id = '')
                           AND (
                               l.associated_partner_id IS NULL
                               OR (
                                   -- DC-DIRECT-WORK-VGK-001 (Jun 2026): VGK lead where all active
                                   -- VCI entries share the same partner (no diverse upline chain).
                                   -- Staff handled it as direct work despite VGK partner assignment.
                                   l.associated_partner_id IS NOT NULL
                                   AND (
                                       SELECT COUNT(DISTINCT vci.partner_id)
                                       FROM vgk_cash_income_entries vci
                                       WHERE vci.source_lead_id = l.id
                                         AND vci.status NOT IN ('CANCELLED')
                                   ) = 1
                               )
                           )
                       ) THEN TRUE ELSE FALSE END                                       AS is_direct_work
                FROM crm_leads l
                WHERE {_comp_where}
                  {_co_clause} AND l.telecaller_id IS NOT NULL
                UNION ALL
                SELECT l.id                                                             AS lead_id,
                       l.field_staff_id::TEXT                                           AS emp_key,
                       l.category_id                                                    AS category_id,
                       COALESCE(NULLIF(l.deal_value_received,0), l.deal_value, 0)      AS dvr,
                       {_sup}                                                           AS has_support,
                       l.associated_partner_id                                          AS partner_id,
                       CASE WHEN (
                           (l.source IS NULL OR l.source != 'Self Lead')
                           AND l.guru_id IS NULL
                           AND l.z_guru_id IS NULL
                           AND l.adi_guru_id IS NULL
                           AND (l.mnr_handler_id IS NULL OR l.mnr_handler_id = '')
                           AND (
                               l.associated_partner_id IS NULL
                               OR (
                                   -- DC-DIRECT-WORK-VGK-001 (Jun 2026): VGK lead where all active
                                   -- VCI entries share the same partner (no diverse upline chain).
                                   l.associated_partner_id IS NOT NULL
                                   AND (
                                       SELECT COUNT(DISTINCT vci.partner_id)
                                       FROM vgk_cash_income_entries vci
                                       WHERE vci.source_lead_id = l.id
                                         AND vci.status NOT IN ('CANCELLED')
                                   ) = 1
                               )
                           )
                       ) THEN TRUE ELSE FALSE END                                       AS is_direct_work
                FROM crm_leads l
                WHERE {_comp_where}
                  {_co_clause} AND l.field_staff_id IS NOT NULL
            ) raw
            ORDER BY lead_id, emp_key
        ) deduped
    """ + (" WHERE emp_key = :eid" if employee_id else ""))

    from datetime import date as _date_cls
    params_lead: dict = {
        'df': date_from, 'dt': date_to,
        'df_d': _date_cls(year, month, 1),
        'dt_d': _date_cls(year, month, _last_day),
    }
    if not all_companies:
        params_lead['co'] = company_id
    if employee_id:
        params_lead['eid'] = employee_id

    lead_rows = db.execute(lead_q, params_lead).fetchall()

    # DC-ETC-ALWAYS-COMPANY-001: ETC/Training leads are ALWAYS company leads —
    # the training programme is a company activity; self-source never applies.
    _etc_cat_ids = set(slug_to_cat_ids.get('training', []))
    if _etc_cat_ids:
        lead_rows = [
            (ek, cid, dvr, 1 if cid in _etc_cat_ids else hs, pid, idw)
            for ek, cid, dvr, hs, pid, idw in lead_rows
        ]

    # DC-ETC-DIRECT-001: Pre-fetch direct ETC students (crm_lead_id IS NULL) for processing
    # AFTER emp_data is initialised. Query also captures deal_value_received so percentage
    # incentive is calculated correctly using the 7.5% direct-work rate (DC-ETC-DW-AMOUNT-001).
    _training_slug = 'training' if 'training' in slug_to_cat_ids else None
    _etc_direct_rows: list = []
    if _training_slug:
        _co_etc = "AND es.company_id = :co" if not all_companies else ""
        _etc_direct_q = text(f"""
            SELECT se.id::TEXT AS emp_key,
                   COALESCE(es.deal_value_received, 0) AS dvr
            FROM etc_students es
            JOIN staff_employees se ON se.emp_code = es.telecaller_emp_code
            WHERE es.training_completed_date IS NOT NULL
              AND es.training_completed_date BETWEEN :df_d AND :dt_d
              AND es.crm_lead_id IS NULL AND es.is_active = TRUE {_co_etc}
              {"AND se.id::TEXT = :eid" if employee_id else ""}
            UNION ALL
            SELECT se.id::TEXT AS emp_key,
                   COALESCE(es.deal_value_received, 0) AS dvr
            FROM etc_students es
            JOIN staff_employees se ON se.emp_code = es.field_staff_emp_code
            WHERE es.training_completed_date IS NOT NULL
              AND es.training_completed_date BETWEEN :df_d AND :dt_d
              AND es.crm_lead_id IS NULL AND es.is_active = TRUE {_co_etc}
              {"AND se.id::TEXT = :eid" if employee_id else ""}
        """)
        _etc_direct_params: dict = {'df_d': params_lead['df_d'], 'dt_d': params_lead['dt_d']}
        if not all_companies:
            _etc_direct_params['co'] = company_id
        if employee_id:
            _etc_direct_params['eid'] = employee_id
        _etc_direct_rows = db.execute(_etc_direct_q, _etc_direct_params).fetchall()

    # Build per-employee per-slug achievements
    # DC-BONUS-COMPANY-ONLY-001: Track self vs company leads separately.
    # Self-source (has_support=False) → rate_no, flat, NO bonus multiplier.
    # Company leads (has_support=True) → rate_wi, bonus trigger applies.
    # DC-B2B-SPLIT-001: When ev_b2b_new + ev_b2b_existing both in config,
    # intercept B2B leads and route by partner history (new = first ever deal).
    use_b2b_split = ('ev_b2b_new' in cfg_by_slug and 'ev_b2b_existing' in cfg_by_slug)
    b2b_cat_ids = set(slug_to_cat_ids.get('ev_b2b', []))
    b2b_pending: list = []  # (emp_key, partner_id, dvr, has_sup)

    emp_data: dict = {}
    for emp_key, cat_id, dvr, has_sup, partner_id, is_direct in lead_rows:
        if not emp_key:
            continue
        if emp_key not in emp_data:
            emp_data[emp_key] = {}
        if use_b2b_split and cat_id in b2b_cat_ids:
            b2b_pending.append((emp_key, partner_id, float(dvr), bool(has_sup), bool(is_direct)))
            continue
        for slug, cat_ids in slug_to_cat_ids.items():
            if cat_id in cat_ids:
                if slug not in emp_data[emp_key]:
                    emp_data[emp_key][slug] = {
                        'self_count': 0, 'self_amount': 0.0,
                        'company_count': 0, 'company_amount': 0.0,
                        'direct_count': 0, 'direct_amount': 0.0,
                    }
                # DC-INCENTIVE-LEAD-TYPE-003: Direct Work (no MNR/VGK4U user_id) takes
                # priority over Self/Company classification.
                if bool(is_direct):
                    emp_data[emp_key][slug]['direct_count'] += 1
                    emp_data[emp_key][slug]['direct_amount'] += float(dvr)
                elif has_sup:
                    emp_data[emp_key][slug]['company_count'] += 1
                    emp_data[emp_key][slug]['company_amount'] += float(dvr)
                else:
                    emp_data[emp_key][slug]['self_count'] += 1
                    emp_data[emp_key][slug]['self_amount'] += float(dvr)
                break

    # DC-B2B-SPLIT-001: Route B2B leads to ev_b2b_new or ev_b2b_existing.
    # New partner = associated_partner_id has NO prior completed B2B lead before this period.
    if use_b2b_split and b2b_pending:
        _b2b_pids = list({p for _, p, _, _ in b2b_pending if p is not None})
        _existing_pids: set = set()
        if _b2b_pids and b2b_cat_ids:
            _prior = db.execute(text("""
                SELECT DISTINCT l.associated_partner_id
                FROM crm_leads l
                WHERE l.associated_partner_id = ANY(:pids)
                  AND l.category_id = ANY(:cids)
                  AND l.updated_at < :cutoff
                  AND (
                    l.ev_b2b_stage = 'completed'
                    OR (l.status = 'completed'
                        AND l.solar_pipeline_status IS NULL
                        AND l.ev_b2b_stage IS NULL)
                  )
            """), {'pids': _b2b_pids, 'cids': list(b2b_cat_ids), 'cutoff': date_from}).fetchall()
            _existing_pids = {r[0] for r in _prior}
        def _empty_b2b():
            return {'self_count': 0, 'self_amount': 0.0, 'company_count': 0, 'company_amount': 0.0,
                    'direct_count': 0, 'direct_amount': 0.0}
        for _ek, _pid, _dvr, _hs, _is_direct in b2b_pending:
            _aslug = 'ev_b2b_existing' if _pid in _existing_pids else 'ev_b2b_new'
            if _ek not in emp_data:
                emp_data[_ek] = {}
            if _aslug not in emp_data[_ek]:
                emp_data[_ek][_aslug] = _empty_b2b()
            if _is_direct:
                emp_data[_ek][_aslug]['direct_count'] += 1
                emp_data[_ek][_aslug]['direct_amount'] += _dvr
            elif _hs:
                emp_data[_ek][_aslug]['company_count'] += 1
                emp_data[_ek][_aslug]['company_amount'] += _dvr
            else:
                emp_data[_ek][_aslug]['self_count'] += 1
                emp_data[_ek][_aslug]['self_amount'] += _dvr

    # DC-ETC-DIRECT-001 (loop) / DC-ETC-DW-AMOUNT-001:
    # Direct ETC students (no CRM link) are classified as Direct Work because there is
    # no external referral or handler — the telecaller/field_staff sourced them personally.
    # Their deal_value_received is used as the amount base so the 7.5% direct-work rate
    # produces a meaningful non-zero incentive (previously bucketed as company with ₹0).
    if _training_slug and _etc_direct_rows:
        for (_ek, _dvr_etc) in _etc_direct_rows:
            if not _ek:
                continue
            if _ek not in emp_data:
                emp_data[_ek] = {}
            if _training_slug not in emp_data[_ek]:
                emp_data[_ek][_training_slug] = {
                    'self_count': 0, 'self_amount': 0.0,
                    'company_count': 0, 'company_amount': 0.0,
                    'direct_count': 0, 'direct_amount': 0.0,
                }
            emp_data[_ek][_training_slug]['direct_count'] += 1
            emp_data[_ek][_training_slug]['direct_amount'] += float(_dvr_etc or 0)

    # Build employee map — start from leads, then merge all active staff if show_all
    emp_ids_from_leads = list(emp_data.keys())
    emp_map = {}

    if show_all or (not employee_id and not emp_ids_from_leads):
        # Fetch ALL active staff employees (filtered by company if specified)
        all_emp_q = (
            "SELECT id, emp_code, COALESCE(full_name, emp_code) as name, department_id "
            "FROM staff_employees WHERE status = 'active'"
            + (" AND base_company_id = :co" if not all_companies else "")
            + " ORDER BY full_name, emp_code"
        )
        all_emp_params: dict = {}
        if not all_companies:
            all_emp_params['co'] = company_id
        all_emps = db.execute(text(all_emp_q), all_emp_params).fetchall()
        emp_map = {str(r[0]): {'emp_code': r[1], 'name': r[2], 'dept_id': r[3]} for r in all_emps}
        # Ensure every employee exists in emp_data (with empty slug data)
        for eid in emp_map:
            if eid not in emp_data:
                emp_data[eid] = {}
    else:
        # Only resolve names for employees found in lead data
        int_ids = [int(x) for x in emp_ids_from_leads if str(x).isdigit()]
        if int_ids:
            emps = db.execute(text(
                "SELECT id, emp_code, COALESCE(full_name, emp_code) as name, department_id "
                "FROM staff_employees WHERE id = ANY(:ids)"
            ), {'ids': int_ids}).fetchall()
            emp_map = {str(r[0]): {'emp_code': r[1], 'name': r[2], 'dept_id': r[3]} for r in emps}

    # DC-INCENTIVE-EMP-TARGETS-001: Load per-employee incentive min-targets for this month.
    # Keyed as {emp_id_str: {category_slug: min_target_float}}. Default = 2.0 when not set.
    _inc_target_map: dict = {}
    _INC_DEFAULT_TARGET = 2.0
    _all_emp_int_ids = [int(k) for k in emp_map.keys() if str(k).isdigit()]
    if _all_emp_int_ids:
        _eit_rows = db.execute(text(
            "SELECT employee_id::TEXT, category_slug, min_target "
            "FROM staff_incentive_employee_targets "
            "WHERE month=:mo AND year=:yr AND employee_id=ANY(:eids)"
        ), {'mo': month, 'yr': year, 'eids': _all_emp_int_ids}).fetchall()
        for _eit_eid, _eit_slug, _eit_mt in _eit_rows:
            if _eit_eid not in _inc_target_map:
                _inc_target_map[_eit_eid] = {}
            _inc_target_map[_eit_eid][_eit_slug] = float(_eit_mt if _eit_mt is not None else _INC_DEFAULT_TARGET)

    def _calc_employee(emp_id: str, slug_data: dict) -> dict:
        emp_info = emp_map.get(str(emp_id), {'emp_code': emp_id, 'name': emp_id, 'dept_id': None})
        cat_results = []
        total_earned = 0.0
        _empty = {'self_count': 0, 'self_amount': 0.0, 'company_count': 0, 'company_amount': 0.0,
                  'direct_count': 0, 'direct_amount': 0.0}
        for slug, cfg in cfg_by_slug.items():
            ach = slug_data.get(slug, _empty)

            self_count     = ach.get('self_count', 0)
            self_amount    = ach.get('self_amount', 0.0)
            company_count  = ach.get('company_count', 0)
            company_amount = ach.get('company_amount', 0.0)
            direct_count   = ach.get('direct_count', 0)
            direct_amount  = ach.get('direct_amount', 0.0)
            total_count    = self_count + company_count + direct_count
            total_amount   = self_amount + company_amount + direct_amount

            rate_no  = cfg['rate_no']
            rate_wi  = cfg['rate_wi']
            rate_dw  = cfg.get('rate_dw', 0.0)

            # DC-INCENTIVE-EMP-TARGETS-001: Per-employee min target gate.
            # Total (self+company+direct) must meet emp_min_target before ANY incentive is paid.
            # If emp_min_target = 0 → pay from deal 1. Default = 2.
            emp_min_target = _inc_target_map.get(str(emp_id), {}).get(slug, _INC_DEFAULT_TARGET)
            total_gate_val = total_count if cfg['min_target_unit'] == 'count' else total_amount
            target_met = (emp_min_target == 0) or (total_gate_val >= emp_min_target)
            gap = max(0.0, emp_min_target - total_gate_val) if emp_min_target > 0 else 0.0

            # DC-INCENTIVE-SPLITVAL-001: fixed_per_unit uses count; percentage uses amount.
            # DC-BONUS-COMPANY-ONLY-001: Self leads → flat rate_no, NO bonus multiplier.
            # DC-INCENTIVE-LEAD-TYPE-003: Direct Work → rate_dw, shares bonus trigger.
            if cfg['itype'] == 'fixed_per_unit':
                self_base    = self_count    * rate_no
                company_base = company_count * rate_wi
                direct_base  = direct_count  * rate_dw
            else:
                self_base    = (self_amount    * rate_no) / 100.0
                company_base = (company_amount * rate_wi) / 100.0
                direct_base  = (direct_amount  * rate_dw) / 100.0

            # If target not met → hold all incentives at ₹0
            if not target_met:
                self_base = company_base = direct_base = 0.0

            # Bonus trigger — on company AND direct leads combined (only when target met)
            company_target_val = company_count + direct_count if cfg['min_target_unit'] == 'count' \
                                 else company_amount + direct_amount
            bonus_applied = False
            final_company = company_base
            final_direct  = direct_base
            if target_met and cfg['bonus_trigger'] and company_target_val >= cfg['bonus_trigger'] \
                    and (company_base + direct_base) > 0:
                final_company = company_base * cfg['bonus_mul']
                final_direct  = direct_base  * cfg['bonus_mul']
                bonus_applied = True

            final_incentive = self_base + final_company + final_direct
            total_earned   += final_incentive

            cat_results.append({
                'slug': slug,
                'achieved_count': total_count, 'achieved_amount': total_amount,
                'self_count': self_count,      'self_amount': self_amount,
                'company_count': company_count, 'company_amount': company_amount,
                'direct_count': direct_count,  'direct_amount': direct_amount,
                'achieved_value': total_gate_val,
                'min_target': emp_min_target,
                'min_target_unit': cfg['min_target_unit'],
                'target_met': target_met,
                'gap': round(gap, 2),
                'rate_self': rate_no, 'rate_company': rate_wi, 'rate_direct': rate_dw,
                'rate_applied': rate_wi if company_count > 0 else (rate_dw if direct_count > 0 else rate_no),
                'has_support': company_count > 0,
                'self_incentive': round(self_base, 2),
                'company_incentive_base': round(company_base, 2),
                'direct_incentive_base': round(direct_base, 2),
                'base_incentive': round(self_base + company_base + direct_base, 2),
                'bonus_applied': bonus_applied,
                'bonus_multiplier': cfg['bonus_mul'] if bonus_applied else None,
                'incentive_earned': round(final_incentive, 2),
            })
        return {
            'employee_id': emp_id, 'emp_code': emp_info['emp_code'], 'name': emp_info['name'],
            'dept_id': emp_info['dept_id'], 'categories': cat_results,
            'total_incentive_earned': round(total_earned, 2),
        }

    results = [_calc_employee(eid, sd) for eid, sd in emp_data.items()]
    results.sort(key=lambda x: (-x['total_incentive_earned'], (x['name'] or '').lower()))
    return {'success': True, 'data': results, 'month': month, 'year': year}


@router.get("/incentive-achievements/drilldown", summary="Source leads/students for a given employee+category+period")
def incentive_achievements_drilldown(
    month:       int            = Query(...),
    year:        int            = Query(...),
    employee_id: str            = Query(...),
    category_slug: str          = Query(...),
    company_id:  Optional[int]  = Query(None),
    db:          Session        = Depends(get_db),
    me:          StaffEmployee  = Depends(get_current_staff_user),
):
    """Returns the actual leads/students that were counted for a specific
    employee + category + month, so users can verify the calculation."""
    import calendar as _cal
    from datetime import date as _date_cls

    all_companies = not company_id or company_id == 0
    _last_day = _cal.monthrange(year, month)[1]
    date_from = datetime(year, month, 1)
    date_to   = datetime(year, month, _last_day, 23, 59, 59)
    df_d = _date_cls(year, month, 1)
    dt_d = _date_cls(year, month, _last_day)

    # Resolve employee
    emp_row = db.execute(text(
        "SELECT id, emp_code, COALESCE(full_name, emp_code) AS name "
        "FROM staff_employees WHERE id = :eid"
    ), {'eid': int(employee_id)}).fetchone()
    if not emp_row:
        return {'success': False, 'data': [], 'message': 'Employee not found'}
    emp_db_id, emp_code, emp_name = emp_row

    # Map slug → category IDs
    CAT_PATTERNS = {
        'solar':           ['%solar%'],
        'ev_b2c':          ['%ev%b2c%', '%ev b2c%', '%ev-b2c%'],
        'ev_b2b':          ['%ev%b2b%', '%ev b2b%', '%ev-b2b%'],
        'ev_b2b_new':      ['%ev%b2b%', '%ev b2b%', '%ev-b2b%'],
        'ev_b2b_existing': ['%ev%b2b%', '%ev b2b%', '%ev-b2b%'],
        'training':        ['%training%', '%etc%'],
        'insurance':       ['%insurance%'],
        'real_estate':     ['%real%estate%', '%real dream%', '%property%'],
    }
    patterns = CAT_PATTERNS.get(category_slug, [])
    if not patterns:
        return {'success': False, 'data': [], 'message': f'Unknown category slug: {category_slug}'}

    if all_companies:
        all_cats = db.execute(text("SELECT id, name FROM signup_categories")).fetchall()
    else:
        all_cats = db.execute(text(
            "SELECT id, name FROM signup_categories WHERE company_id=:co"
        ), {'co': company_id}).fetchall()

    cat_ids = []
    for cid, cname in all_cats:
        cn = (cname or '').lower()
        for pat in patterns:
            pc = pat.replace('%', '')
            if pc and all(p in cn for p in pc.split() if p):
                cat_ids.append(cid)
                break
    if not cat_ids:
        return {'success': True, 'data': [], 'count': 0, 'employee': emp_name,
                'employee_id': emp_db_id, 'category_slug': category_slug,
                'month': month, 'year': year, 'message': 'No matching categories'}

    _co_clause = "" if all_companies else "AND l.company_id = :co"
    results = []

    if category_slug == 'training':
        # ── CRM-linked ETC — use SAME _comp_where as main endpoint ────────
        # DC-ETC-DRILLDOWN-001: match exactly what the main achievement
        # endpoint counts: either standard completion OR etc_students link.
        # DC-CLOSE-DATE-001: use actual close date, not updated_at.
        _drl_close = "COALESCE(l.actual_close_date, l.updated_at)"
        _etc_comp = f"""(
            (
                l.solar_pipeline_status = 'completed'
                OR l.ev_b2b_stage = 'completed'
                OR (l.status = 'completed'
                    AND l.solar_pipeline_status IS NULL
                    AND l.ev_b2b_stage IS NULL)
            ) AND ({_drl_close}) BETWEEN :df AND :dt
            OR EXISTS (
                SELECT 1 FROM etc_students s
                WHERE s.crm_lead_id = l.id
                AND s.training_completed_date IS NOT NULL
                AND s.training_completed_date BETWEEN :df_d AND :dt_d
                AND s.is_active = TRUE
            )
        )"""
        crm_q = text(f"""
            SELECT DISTINCT ON (l.id)
                l.id,
                COALESCE(l.name, '—')   AS cname,
                COALESCE(l.phone, '—') AS cphone,
                l.source,
                COALESCE(NULLIF(l.deal_value_received,0), l.deal_value, 0) AS dv,
                COALESCE(
                    (SELECT es2.training_completed_date::text
                     FROM etc_students es2
                     WHERE es2.crm_lead_id = l.id
                       AND es2.training_completed_date IS NOT NULL
                       AND es2.is_active = TRUE
                     ORDER BY es2.training_completed_date LIMIT 1),
                    COALESCE(l.actual_close_date, l.updated_at)::text
                ) AS comp_date,
                sc.name AS cat_name,
                CASE
                    WHEN l.source = 'Self Lead' THEN 'Self'
                    WHEN (l.guru_id IS NOT NULL OR l.z_guru_id IS NOT NULL
                          OR l.adi_guru_id IS NOT NULL
                          OR (l.mnr_handler_id IS NOT NULL AND l.mnr_handler_id != '')
                          OR l.associated_partner_id IS NOT NULL) THEN 'Company'
                    ELSE 'Direct'
                END AS ltype,
                ARRAY_REMOVE(ARRAY[
                    CASE WHEN l.telecaller_id::text = :emp_id   THEN 'Telecaller'  END,
                    CASE WHEN l.field_staff_id::text = :emp_id  THEN 'Field Staff' END
                ], NULL) AS roles
            FROM crm_leads l
            JOIN signup_categories sc ON sc.id = l.category_id
            WHERE l.category_id = ANY(:cat_ids)
              AND {_etc_comp}
              AND (
                  l.telecaller_id::text = :emp_id
                  OR l.field_staff_id::text = :emp_id
              ) {_co_clause}
            ORDER BY l.id, l.updated_at DESC
        """)
        p = {'cat_ids': cat_ids, 'df': date_from, 'dt': date_to,
             'df_d': df_d, 'dt_d': dt_d,
             'emp_code': emp_code, 'emp_id': str(emp_db_id)}
        if not all_companies:
            p['co'] = company_id
        for r in db.execute(crm_q, p).fetchall():
            results.append({
                'id': r[0], 'name': r[1], 'phone': r[2], 'source': r[3],
                'deal_value': float(r[4]) if r[4] else 0,
                'completion_date': str(r[5])[:10] if r[5] else None,
                'category': r[6], 'lead_type': r[7],
                'roles': list(r[8]) if r[8] else ['Handler'],
                'record_type': 'crm_lead',
                'incentive_count': 1,
            })
        # ── Direct ETC students (no crm_lead_id) ──────────────────────────
        # DC-ETC-DIRECT-ROLECOUNT-001: main endpoint counts per-role via UNION ALL
        # (no dedup). Return one row per student but include incentive_count = number
        # of roles this employee holds for that student — so source total matches.
        _co_etc = "AND es.company_id = :co" if not all_companies else ""
        dir_q = text(f"""
            SELECT
                es.id,
                COALESCE(es.name, '—') AS cname,
                COALESCE(es.phone, '—') AS cphone,
                'Direct ETC' AS source,
                COALESCE(es.deal_value_received, 0) AS dv,
                es.training_completed_date::text AS comp_date,
                'ETC Students' AS cat_name,
                'Direct' AS ltype,
                ARRAY_REMOVE(ARRAY[
                    CASE WHEN es.telecaller_emp_code = :emp_code THEN 'Telecaller'  END,
                    CASE WHEN es.field_staff_emp_code= :emp_code THEN 'Field Staff' END
                ], NULL) AS roles,
                (CASE WHEN es.telecaller_emp_code  = :emp_code THEN 1 ELSE 0 END
                 + CASE WHEN es.field_staff_emp_code = :emp_code THEN 1 ELSE 0 END
                ) AS incentive_count
            FROM etc_students es
            WHERE es.training_completed_date BETWEEN :df_d AND :dt_d
              AND es.crm_lead_id IS NULL
              AND es.is_active = TRUE
              AND (
                  es.telecaller_emp_code  = :emp_code
                  OR es.field_staff_emp_code = :emp_code
              ) {_co_etc}
        """)
        dp = {'df_d': df_d, 'dt_d': dt_d, 'emp_code': emp_code}
        if not all_companies:
            dp['co'] = company_id
        for r in db.execute(dir_q, dp).fetchall():
            results.append({
                'id': r[0], 'name': r[1], 'phone': r[2], 'source': r[3],
                'deal_value': float(r[4]) if r[4] else 0,
                'completion_date': str(r[5])[:10] if r[5] else None,
                'category': r[6], 'lead_type': r[7],
                'roles': list(r[8]) if r[8] else ['Handler'],
                'record_type': 'etc_student',
                'incentive_count': int(r[9]) if r[9] else 1,
            })
    else:
        # ── Standard CRM path ─────────────────────────────────────────────
        # DC-CLOSE-DATE-001: use actual close date, not updated_at.
        _drl_close2 = "COALESCE(l.actual_close_date, l.updated_at)"
        _comp_where = f"""(
            l.solar_pipeline_status = 'completed'
            OR l.ev_b2b_stage       = 'completed'
            OR (l.status = 'completed'
                AND l.solar_pipeline_status IS NULL
                AND l.ev_b2b_stage IS NULL)
        ) AND ({_drl_close2}) BETWEEN :df AND :dt"""
        crm_q = text(f"""
            SELECT DISTINCT ON (l.id)
                l.id,
                COALESCE(l.name, '—')   AS cname,
                COALESCE(l.phone, '—') AS cphone,
                l.source,
                COALESCE(NULLIF(l.deal_value_received,0), l.deal_value, 0) AS dv,
                COALESCE(l.actual_close_date, l.updated_at)::text AS comp_date,
                sc.name AS cat_name,
                CASE
                    WHEN l.source = 'Self Lead' THEN 'Self'
                    WHEN (l.guru_id IS NOT NULL OR l.z_guru_id IS NOT NULL
                          OR l.adi_guru_id IS NOT NULL
                          OR (l.mnr_handler_id IS NOT NULL AND l.mnr_handler_id != '')
                          OR l.associated_partner_id IS NOT NULL) THEN 'Company'
                    ELSE 'Direct'
                END AS ltype,
                ARRAY_REMOVE(ARRAY[
                    CASE WHEN l.telecaller_id::text = :emp_id   THEN 'Telecaller'  END,
                    CASE WHEN l.field_staff_id::text = :emp_id  THEN 'Field Staff' END
                ], NULL) AS roles
            FROM crm_leads l
            JOIN signup_categories sc ON sc.id = l.category_id
            WHERE l.category_id = ANY(:cat_ids)
              AND {_comp_where}
              AND (
                  l.telecaller_id::text = :emp_id
                  OR l.field_staff_id::text = :emp_id
              ) {_co_clause}
            ORDER BY l.id, l.updated_at DESC
        """)
        p = {'cat_ids': cat_ids, 'df': date_from, 'dt': date_to,
             'emp_code': emp_code, 'emp_id': str(emp_db_id)}
        if not all_companies:
            p['co'] = company_id
        for r in db.execute(crm_q, p).fetchall():
            results.append({
                'id': r[0], 'name': r[1], 'phone': r[2], 'source': r[3],
                'deal_value': float(r[4]) if r[4] else 0,
                'completion_date': str(r[5])[:10] if r[5] else None,
                'category': r[6], 'lead_type': r[7],
                'roles': list(r[8]) if r[8] else ['Handler'],
                'record_type': 'crm_lead',
                'incentive_count': 1,
            })

    incentive_total = sum(r.get('incentive_count', 1) for r in results)
    return {
        'success': True, 'data': results, 'count': len(results),
        'incentive_total': incentive_total,
        'employee': emp_name, 'employee_id': emp_db_id,
        'emp_code': emp_code,
        'category_slug': category_slug, 'month': month, 'year': year,
    }


@router.get("/performance/my-incentive-achievements", summary="Current employee's live incentive achievement")
def my_incentive_achievements(
    month: int = Query(...),
    year:  int = Query(...),
    db:    Session = Depends(get_db),
    me:    StaffEmployee = Depends(get_current_staff_user),
):
    """Returns live incentive achievement breakdown for the currently logged-in employee.
    Uses all companies scope so telecaller/handler/field roles across companies are captured.
    DC-LIVE-ACH-SELF-001: show_all=False so only this employee is in d.data → d.data[0] is
    always the logged-in employee (or empty list when no leads exist).
    """
    return get_incentive_achievements(
        company_id=None,
        month=month,
        year=year,
        employee_id=str(me.id),
        show_all=False,
        db=db,
        me=me,
    )


# ── Payout Management Endpoints ────────────────────────────────────────────────

def _can_clear_payout(emp: StaffEmployee) -> bool:
    """Accounts / HR / VGK Mentor / Admin can mark payouts cleared."""
    rc  = (emp.role.role_code if emp.role else '') or ''
    rn  = (emp.role.role_name if emp.role else '') or ''
    ec  = emp.emp_code or ''
    rn_l = rn.lower()
    rc_l = rc.lower()
    return (
        ec == 'MR10001' or
        'accounts' in rn_l or 'account' in rc_l or
        'hr' in rn_l or rn_l == 'hr' or rc_l in ('hr', 'hr_manager') or
        'vgk_mentor' in rc_l or 'vgk mentor' in rn_l or
        _is_vgk_or_ea(emp)
    )


def _due_date_str(month: int, year: int) -> str:
    """Returns 'Due: 15 Apr 2026' format for the FOLLOWING month after month/year."""
    import calendar as _cal
    next_month = month + 1
    next_year  = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_name = _cal.month_abbr[next_month]
    return f"Due: 15 {month_name} {next_year}"


def _derive_payout_status(month: int, year: int, db_status: str) -> str:
    """Return effective status: if DB says cleared → cleared.
    If current calendar month → in_progress. Else → pending."""
    if db_status == 'cleared':
        return 'cleared'
    now = datetime.now(IST)
    if now.year == year and now.month == month:
        return 'in_progress'
    return 'pending'


@router.get('/incentive-payouts/list')
def list_incentive_payouts(
    month:       int            = Query(...),
    year:        int            = Query(...),
    company_id:  Optional[int]  = Query(None),
    employee_id: Optional[int]  = Query(None),
    status:      Optional[str]  = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """List incentive payout rows for month/year. company_id=None means all companies."""
    q = """
        SELECT p.id, p.employee_id, p.company_id, p.month, p.year,
               p.total_incentive, p.payout_status, p.cleared_by, p.cleared_at,
               p.due_date, p.notes, p.created_at, p.updated_at,
               COALESCE(e.full_name, e.emp_code) AS employee_name,
               e.emp_code
        FROM staff_incentive_payouts p
        JOIN staff_employees e ON e.id = p.employee_id
        WHERE p.month = :mo AND p.year = :yr
    """
    params = {'mo': month, 'yr': year}
    if company_id:
        q += " AND p.company_id = :co"
        params['co'] = company_id
    if employee_id:
        q += " AND p.employee_id = :eid"
        params['eid'] = employee_id
    if status:
        q += " AND p.payout_status = :st"
        params['st'] = status
    q += " ORDER BY employee_name"
    rows = db.execute(text(q), params).fetchall()
    data = []
    for r in rows:
        eff_status = _derive_payout_status(r[3], r[4], r[6])
        data.append({
            'id': r[0], 'employee_id': r[1], 'company_id': r[2],
            'month': r[3], 'year': r[4], 'total_incentive': float(r[5] or 0),
            'payout_status': eff_status, 'cleared_by': r[7],
            'cleared_at': r[8].isoformat() if r[8] else None,
            'due_date': r[9].isoformat() if r[9] else None,
            'due_date_label': _due_date_str(r[3], r[4]),
            'notes': r[10],
            'employee_name': r[13], 'emp_code': r[14],
        })
    return {'success': True, 'data': data, 'month': month, 'year': year}


@router.post('/incentive-payouts/upsert')
def upsert_incentive_payout(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Upsert a payout row after achievement calculation. Called from frontend after Calculate."""
    employee_id    = int(payload['employee_id'])
    company_id     = int(payload.get('company_id', 1))
    month          = int(payload['month'])
    year           = int(payload['year'])
    total_incentive = float(payload.get('total_incentive', 0))
    # Derive due_date: 15th of month+1
    next_month = month + 1
    next_year  = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    due_date_val = date(next_year, next_month, 15)
    # Determine payout_status: if existing row is 'cleared' — do NOT overwrite
    existing = db.execute(text("""
        SELECT id, payout_status FROM staff_incentive_payouts
        WHERE employee_id=:eid AND company_id=:co AND month=:mo AND year=:yr
    """), {'eid': employee_id, 'co': company_id, 'mo': month, 'yr': year}).fetchone()
    if existing and existing[1] == 'cleared':
        return {'success': True, 'message': 'Already cleared — not overwritten', 'id': existing[0]}
    # Derive status from calendar
    eff_status = _derive_payout_status(month, year, 'in_progress')
    db.execute(text("""
        INSERT INTO staff_incentive_payouts
            (employee_id, company_id, month, year, total_incentive, payout_status, due_date, updated_at)
        VALUES (:eid, :co, :mo, :yr, :amt, :st, :dd, NOW())
        ON CONFLICT (employee_id, company_id, month, year)
        DO UPDATE SET
            total_incentive = EXCLUDED.total_incentive,
            payout_status   = CASE WHEN staff_incentive_payouts.payout_status = 'cleared'
                                   THEN 'cleared'
                                   ELSE EXCLUDED.payout_status END,
            due_date        = EXCLUDED.due_date,
            updated_at      = NOW()
    """), {'eid': employee_id, 'co': company_id, 'mo': month, 'yr': year,
           'amt': total_incentive, 'st': eff_status, 'dd': due_date_val})
    db.commit()
    return {'success': True, 'message': 'Payout row upserted'}


@router.put('/incentive-payouts/{payout_id}/mark-cleared')
def mark_payout_cleared(
    payout_id: int,
    payload:   dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Mark a payout as cleared. Role-gated: Accounts / HR / VGK Mentor / Admin only."""
    if not _can_clear_payout(current_user):
        raise HTTPException(status_code=403, detail='Only Accounts, HR, or VGK Mentor can clear payouts.')
    row = db.execute(text(
        "SELECT id, payout_status FROM staff_incentive_payouts WHERE id=:pid"
    ), {'pid': payout_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Payout row not found.')
    if row[1] == 'cleared':
        return {'success': True, 'message': 'Already cleared.'}
    now_ist = datetime.now(IST)
    notes   = payload.get('notes', '')
    db.execute(text("""
        UPDATE staff_incentive_payouts
        SET payout_status = 'cleared',
            cleared_by    = :cb,
            cleared_at    = :ca,
            notes         = COALESCE(NULLIF(:notes,''), notes),
            updated_at    = NOW()
        WHERE id = :pid
    """), {'cb': current_user.emp_code, 'ca': now_ist, 'notes': notes, 'pid': payout_id})
    db.commit()
    return {'success': True, 'message': 'Payout marked as cleared.'}


@router.get('/incentive-payouts/my-summary', summary="My performance incentive payouts summary")
def my_incentive_payouts_summary(
    year: int = Query(...),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """Get logged-in employee's performance-based incentive payouts by month for the year."""
    rows = db.execute(text("""
        SELECT p.month, p.year, p.total_incentive, p.payout_status,
               p.due_date, p.cleared_at, p.company_id,
               ac.company_name
        FROM staff_incentive_payouts p
        LEFT JOIN associated_companies ac ON ac.id = p.company_id
        WHERE p.employee_id = :eid AND p.year = :yr
        ORDER BY p.month DESC
    """), {'eid': me.id, 'yr': year}).fetchall()
    data = []
    for r in rows:
        eff_status = _derive_payout_status(r[0], r[1], r[3])
        data.append({
            'month': r[0], 'year': r[1], 'total_incentive': float(r[2] or 0),
            'payout_status': eff_status,
            'due_date': r[4].isoformat() if r[4] else None,
            'cleared_at': r[5].isoformat() if r[5] else None,
            'company_name': r[7] or f'Company {r[6]}',
        })
    total   = sum(d['total_incentive'] for d in data)
    pending = sum(d['total_incentive'] for d in data if d['payout_status'] != 'cleared')
    cleared = sum(d['total_incentive'] for d in data if d['payout_status'] == 'cleared')
    return {'success': True, 'data': data,
            'summary': {'total': total, 'pending': pending, 'cleared': cleared}}


@router.get('/outgoing-expenses')
def list_outgoing_expenses(
    month:      int            = Query(...),
    year:       int            = Query(...),
    company_id: int            = Query(1),
    employee_id: Optional[int] = Query(None),
    status:     Optional[str]  = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Unified outgoing expenses: expense table + field work reimbursements + journey reimbursements."""
    params = {'mo': month, 'yr': year, 'co': company_id}
    emp_filter = " AND src.employee_id = :eid" if employee_id else ""
    if employee_id:
        params['eid'] = employee_id

    # Source A: General expense table (created_by_id links to user.id — show by creator name)
    expense_q = """
        SELECT
            'expense' AS source_type,
            ex.id AS source_id,
            ex.expense_date AS entry_date,
            COALESCE(u.name, ex.created_by_id::TEXT) AS employee_name,
            NULL AS emp_code,
            ex.category AS category,
            ex.description AS description,
            ex.amount AS amount,
            ex.status AS status,
            ex.payment_mode AS payment_mode,
            ex.reference_no AS reference_no
        FROM expense ex
        LEFT JOIN "user" u ON u.id = ex.created_by_id
        WHERE EXTRACT(MONTH FROM ex.expense_date) = :mo
          AND EXTRACT(YEAR  FROM ex.expense_date) = :yr
          AND ex.is_deleted = FALSE
    """

    # Source B: Journey reimbursements
    journey_q = """
        SELECT
            'journey' AS source_type,
            sj.id AS source_id,
            sj.date AS entry_date,
            COALESCE(e.full_name, e.emp_code) AS employee_name,
            e.emp_code AS emp_code,
            'Travel Reimbursement' AS category,
            'Journey reimbursement' AS description,
            sj.reimbursement_amount AS amount,
            sj.approval_status::TEXT AS status,
            NULL AS payment_mode,
            NULL AS reference_no
        FROM staff_journeys sj
        JOIN staff_employees e ON e.id = sj.employee_id
        WHERE EXTRACT(MONTH FROM sj.date) = :mo
          AND EXTRACT(YEAR  FROM sj.date) = :yr
          AND sj.reimbursement_amount > 0
    """
    if employee_id:
        journey_q += " AND sj.employee_id = :eid"

    # Source C: Field work session reimbursements
    fieldwork_q = """
        SELECT
            'field_work' AS source_type,
            sfw.id AS source_id,
            DATE(sfw.session_start) AS entry_date,
            COALESCE(e.full_name, e.emp_code) AS employee_name,
            e.emp_code AS emp_code,
            'Field Work Reimbursement' AS category,
            'Field work reimbursement' AS description,
            sfw.reimbursement_amount AS amount,
            sfw.status AS status,
            NULL AS payment_mode,
            NULL AS reference_no
        FROM staff_field_work_sessions sfw
        JOIN staff_employees e ON e.id = sfw.employee_id
        WHERE EXTRACT(MONTH FROM sfw.session_start) = :mo
          AND EXTRACT(YEAR  FROM sfw.session_start) = :yr
          AND sfw.reimbursement_amount > 0
    """
    if employee_id:
        fieldwork_q += " AND sfw.employee_id = :eid"

    union_q = f"({expense_q}) UNION ALL ({journey_q}) UNION ALL ({fieldwork_q}) ORDER BY entry_date DESC"

    rows = db.execute(text(union_q), params).fetchall()
    data = []
    for r in rows:
        st = (r[8] or '').lower()
        if status and st != status.lower():
            continue
        data.append({
            'source_type': r[0], 'source_id': r[1],
            'entry_date': r[2].isoformat() if r[2] else None,
            'employee_name': r[3], 'emp_code': r[4],
            'category': r[5], 'description': r[6],
            'amount': float(r[7] or 0),
            'status': r[8], 'payment_mode': r[9], 'reference_no': r[10],
        })
    return {'success': True, 'data': data, 'month': month, 'year': year, 'total': len(data)}


# ──────────────────────────────────────────────────────────────────────────────
# DC-INCENTIVE-EMP-TARGETS-001: Per-employee incentive min-target CRUD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/incentive-employee-targets")
def get_incentive_employee_targets(
    month:      int = Query(...),
    year:       int = Query(...),
    company_id: int = Query(0),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """Return all active employees + their saved min targets for the given month/year."""
    all_companies = (company_id == 0)
    # Build employee query — skip company filter when "All Companies" selected
    emp_q = (
        "SELECT id, COALESCE(full_name, emp_code) AS name, emp_code "
        "FROM staff_employees WHERE status='active'"
        + ("" if all_companies else " AND base_company_id=:cid")
        + " ORDER BY full_name, emp_code"
    )
    emp_params: dict = {} if all_companies else {'cid': company_id}
    emps = db.execute(text(emp_q), emp_params).fetchall()

    # Load saved targets — skip company filter when all companies
    tgt_q = (
        "SELECT id, employee_id, category_slug, min_target "
        "FROM staff_incentive_employee_targets "
        "WHERE month=:mo AND year=:yr"
        + ("" if all_companies else " AND company_id=:cid")
    )
    tgt_params: dict = {'mo': month, 'yr': year}
    if not all_companies:
        tgt_params['cid'] = company_id
    tgts = db.execute(text(tgt_q), tgt_params).fetchall()

    return {
        'success': True,
        'employees': [{'id': r[0], 'name': r[1], 'emp_code': r[2]} for r in emps],
        'targets':   [{'id': t[0], 'employee_id': t[1], 'category_slug': t[2],
                        'min_target': float(t[3] or 2)} for t in tgts],
    }


class IncEmpTargetUpsertItem(BaseModel):
    employee_id:   int
    company_id:    int = 1
    month:         int
    year:          int
    category_slug: str
    min_target:    float = 2.0


class IncEmpTargetBulkPayload(BaseModel):
    targets: list[IncEmpTargetUpsertItem]


@router.post("/incentive-employee-targets/bulk-upsert")
def bulk_upsert_incentive_employee_targets(
    payload: IncEmpTargetBulkPayload = Body(...),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """Upsert min-targets in bulk (one row per employee+slug)."""
    saved = 0
    for item in payload.targets:
        db.execute(text(
            "INSERT INTO staff_incentive_employee_targets "
            "(employee_id, company_id, month, year, category_slug, min_target, updated_at) "
            "VALUES (:eid, :cid, :mo, :yr, :slug, :mt, NOW()) "
            "ON CONFLICT (employee_id, month, year, category_slug) "
            "DO UPDATE SET min_target=EXCLUDED.min_target, company_id=EXCLUDED.company_id, updated_at=NOW()"
        ), {
            'eid': item.employee_id, 'cid': item.company_id or 1,
            'mo': item.month, 'yr': item.year,
            'slug': item.category_slug, 'mt': item.min_target,
        })
        saved += 1
    db.commit()
    return {'success': True, 'saved': saved}


class IncEmpTargetCopyPayload(BaseModel):
    month:      int
    year:       int
    company_id: int = 1


@router.post("/incentive-employee-targets/copy-to-next-month")
def copy_incentive_employee_targets_to_next_month(
    payload: IncEmpTargetCopyPayload = Body(...),
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    """Copy all employee targets from month/year to the next month."""
    next_month = payload.month + 1 if payload.month < 12 else 1
    next_year  = payload.year  if payload.month < 12 else payload.year + 1
    cid        = payload.company_id or 1

    existing = db.execute(text(
        "SELECT employee_id, category_slug, min_target "
        "FROM staff_incentive_employee_targets "
        "WHERE month=:mo AND year=:yr AND company_id=:cid"
    ), {'mo': payload.month, 'yr': payload.year, 'cid': cid}).fetchall()

    if not existing:
        return {'success': False, 'message': 'No targets found for the selected month to copy'}

    copied = 0
    for eid, slug, mt in existing:
        db.execute(text(
            "INSERT INTO staff_incentive_employee_targets "
            "(employee_id, company_id, month, year, category_slug, min_target, updated_at) "
            "VALUES (:eid, :cid, :mo, :yr, :slug, :mt, NOW()) "
            "ON CONFLICT (employee_id, month, year, category_slug) "
            "DO UPDATE SET min_target=EXCLUDED.min_target, updated_at=NOW()"
        ), {'eid': eid, 'cid': cid, 'mo': next_month, 'yr': next_year, 'slug': slug, 'mt': mt})
        copied += 1
    db.commit()
    return {
        'success': True,
        'message': f'Copied {copied} target(s) to {next_month}/{next_year}',
        'copied': copied,
    }


@router.delete("/incentive-employee-targets/{target_id}")
def delete_incentive_employee_target(
    target_id: int,
    db: Session = Depends(get_db),
    me: StaffEmployee = Depends(get_current_staff_user),
):
    result = db.execute(text(
        "DELETE FROM staff_incentive_employee_targets WHERE id=:tid RETURNING id"
    ), {'tid': target_id}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Target not found")
    db.commit()
    return {'success': True, 'deleted_id': target_id}
