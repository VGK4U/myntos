"""
Staff Operations Snapshot API — DC Protocol Compliant
Single endpoint that returns all operational metrics per employee for the
management overview page.

Modules covered: Tasks, KRA, CRM, Timesheet, Service Tickets, PO, PR,
                 Call Logs (Talk Time), CRM Deal Value, Attendance (Hrs Worked)

Access: Key Leadership only (VGK4U, Key Leadership, EA, Executive Admin)
DC Protocol: Read-only, batch SQL, no N+1, no schema changes.
Created: March 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case, text
from typing import Optional, List
from datetime import datetime, date, timedelta
import pytz
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffRole, StaffDepartment
from app.models.staff_tasks import StaffTask, StaffTaskAssignee, StaffDayPlan
from app.models.staff_kra import StaffKRADailyInstance
from app.models.staff_timesheet import StaffTimesheetEntry
from app.models.crm import CRMLead
from app.models.ticket import ServiceTicket
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter()
logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')


def _get_indian_date() -> date:
    return datetime.now(IST).date()


def _is_key_leadership(employee: StaffEmployee) -> bool:
    """DC Protocol: exact role check for snapshot page access."""
    if not employee.role:
        return False
    rc = (employee.role.role_code if hasattr(employee.role, 'role_code') else '').lower().strip()
    rn = (employee.role.role_name if hasattr(employee.role, 'role_name') else '').upper().strip()
    ok_codes = {'vgk4u', 'vgk4u_supreme', 'key_leadership', 'ea', 'executive_admin'}
    ok_names = {'VGK4U', 'VGK4U SUPREME', 'VGK MENTOR', 'KEY LEADERSHIP', 'EA', 'EXECUTIVE ADMIN'}
    return rc in ok_codes or 'vgk4u' in rc or rn in ok_names


def _get_downline_ids(db: Session, manager_id: int) -> List[int]:
    """BFS downline traversal — DC Protocol: no recursion, explicit queue."""
    all_ids: List[int] = []
    queue = [manager_id]
    visited: set = set()
    while queue:
        cur = queue.pop(0)
        if cur in visited:
            continue
        visited.add(cur)
        rows = db.query(StaffEmployee.id).filter(
            StaffEmployee.reporting_manager_id == cur,
            StaffEmployee.status == 'active'
        ).all()
        for r in rows:
            if r.id not in visited:
                all_ids.append(r.id)
                queue.append(r.id)
    return all_ids


@router.get("/overview", summary="Staff Operations Snapshot — all metrics per employee")
def get_ops_snapshot(
    from_date: Optional[date] = Query(None, description="Start date (ISO). Omit for overall mode."),
    to_date: Optional[date] = Query(None, description="End date (ISO). Omit for overall mode."),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Returns per-employee operational metrics across all modules.
    Access restricted to Key Leadership. Returns downline only (or all for VGK4U Supreme).
    DC Protocol: batch queries, no N+1, read-only.
    """
    if not _is_key_leadership(current_user):
        raise HTTPException(status_code=403, detail="Key Leadership access required for Operations Snapshot.")

    today = _get_indian_date()
    is_range = from_date is not None and to_date is not None

    rc = (current_user.role.role_code if current_user.role else '').lower()
    is_supreme = 'vgk4u' in rc or rc in {'vgk4u_supreme', 'key_leadership', 'ea', 'executive_admin'}

    if is_supreme:
        emp_rows = db.query(
            StaffEmployee.id,
            StaffEmployee.emp_code,
            StaffEmployee.full_name,
            StaffEmployee.department_id,
            StaffEmployee.reporting_manager_id,
            StaffEmployee.base_company_id,
        ).filter(StaffEmployee.status == 'active').all()
    else:
        dl_ids = _get_downline_ids(db, current_user.id)
        if not dl_ids:
            return []
        emp_rows = db.query(
            StaffEmployee.id,
            StaffEmployee.emp_code,
            StaffEmployee.full_name,
            StaffEmployee.department_id,
            StaffEmployee.reporting_manager_id,
            StaffEmployee.base_company_id,
        ).filter(
            StaffEmployee.id.in_(dl_ids),
            StaffEmployee.status == 'active'
        ).all()

    if not emp_rows:
        return []

    emp_ids = [r.id for r in emp_rows]

    dept_rows = db.query(StaffDepartment.id, StaffDepartment.name).all()
    dept_map = {d.id: d.name for d in dept_rows}

    mgr_rows = db.query(StaffEmployee.id, StaffEmployee.full_name).filter(
        StaffEmployee.id.in_([r.reporting_manager_id for r in emp_rows if r.reporting_manager_id])
    ).all()
    mgr_map = {m.id: m.full_name for m in mgr_rows}

    # Company names
    company_ids = list(set(r.base_company_id for r in emp_rows if r.base_company_id))
    company_map = {}
    if company_ids:
        try:
            from app.models.staff_accounts import AssociatedCompany
            co_rows = db.query(AssociatedCompany.id, AssociatedCompany.company_name).filter(
                AssociatedCompany.id.in_(company_ids)
            ).all()
            company_map = {c.id: c.company_name for c in co_rows}
        except Exception as e:
            logger.warning("[SNAPSHOT] Company query failed: %s", e)

    # ── 1. TASKS — batch query per primary_assignee_id ────────────────────────
    task_cols = db.query(
        StaffTask.primary_assignee_id,
        func.count(StaffTask.id).label('total'),
        func.count(case((StaffTask.status == 'completed', 1))).label('handled'),
        func.count(case((
            StaffTask.status.in_(['pending', 'in_progress', 'on_hold', 'under_review']),
            1
        ))).label('pending'),
        func.count(case((
            and_(
                StaffTask.due_date < today,
                StaffTask.status.notin_(['completed', 'cancelled'])
            ), 1
        ))).label('overdue'),
    ).filter(
        StaffTask.primary_assignee_id.in_(emp_ids),
        StaffTask.status != 'cancelled',
        *(([StaffTask.created_at >= datetime.combine(from_date, datetime.min.time()),
            StaffTask.created_at <= datetime.combine(to_date, datetime.max.time())])
          if is_range else [])
    ).group_by(StaffTask.primary_assignee_id).all()
    tasks_by_assignee = {r.primary_assignee_id: r for r in task_cols}

    task_cols_creator = db.query(
        StaffTask.created_by,
        func.count(StaffTask.id).label('total'),
        func.count(case((StaffTask.status == 'completed', 1))).label('handled'),
        func.count(case((
            StaffTask.status.in_(['pending', 'in_progress', 'on_hold', 'under_review']),
            1
        ))).label('pending'),
        func.count(case((
            and_(
                StaffTask.due_date < today,
                StaffTask.status.notin_(['completed', 'cancelled'])
            ), 1
        ))).label('overdue'),
    ).filter(
        StaffTask.created_by.in_(emp_ids),
        StaffTask.status != 'cancelled',
        *(([StaffTask.created_at >= datetime.combine(from_date, datetime.min.time()),
            StaffTask.created_at <= datetime.combine(to_date, datetime.max.time())])
          if is_range else [])
    ).group_by(StaffTask.created_by).all()
    tasks_by_creator = {r.created_by: r for r in task_cols_creator}

    # ── 2. KRA — batch query per employee_id ─────────────────────────────────
    kra_filters = [StaffKRADailyInstance.employee_id.in_(emp_ids)]
    if is_range:
        kra_filters += [
            StaffKRADailyInstance.instance_date >= from_date,
            StaffKRADailyInstance.instance_date <= to_date,
        ]
    kra_cols = db.query(
        StaffKRADailyInstance.employee_id,
        func.count(StaffKRADailyInstance.id).label('total'),
        func.count(case((StaffKRADailyInstance.completion_status == 'completed', 1))).label('handled'),
        func.count(case((
            StaffKRADailyInstance.completion_status.in_(['pending', 'in_progress', 'partial']),
            1
        ))).label('pending'),
        func.count(case((
            StaffKRADailyInstance.completion_status.in_(['skipped', 'na']),
            1
        ))).label('skipped'),
    ).filter(*kra_filters).group_by(StaffKRADailyInstance.employee_id).all()
    kra_map = {r.employee_id: r for r in kra_cols}

    # ── 3. CRM — batch query per primary_owner_id ────────────────────────────
    not_handled_threshold = today - timedelta(days=3)
    crm_filters = [CRMLead.primary_owner_id.in_(emp_ids)]
    if is_range:
        crm_filters += [
            func.date(CRMLead.created_at) >= from_date,
            func.date(CRMLead.created_at) <= to_date,
        ]
    crm_cols = db.query(
        CRMLead.primary_owner_id,
        func.count(CRMLead.id).label('total'),
        func.count(case((CRMLead.status == 'new', 1))).label('new_leads'),
        func.count(case((CRMLead.status == 'won', 1))).label('deals_closed'),
        func.count(case((
            and_(
                CRMLead.status == 'new',
                func.date(CRMLead.created_at) <= not_handled_threshold
            ), 1
        ))).label('not_handled'),
        func.count(case((
            and_(
                CRMLead.status.notin_(['won', 'lost', 'cancelled', 'completed']),
                func.date(CRMLead.created_at) <= not_handled_threshold
            ), 1
        ))).label('overdue'),
    ).filter(*crm_filters).group_by(CRMLead.primary_owner_id).all()
    crm_map = {r.primary_owner_id: r for r in crm_cols}

    # ── 4. TIMESHEET — batch query per employee_id ───────────────────────────
    ts_filters = [StaffTimesheetEntry.employee_id.in_(emp_ids)]
    if is_range:
        ts_filters += [
            StaffTimesheetEntry.date >= from_date,
            StaffTimesheetEntry.date <= to_date,
        ]
    ts_cols = db.query(
        StaffTimesheetEntry.employee_id,
        func.count(StaffTimesheetEntry.id).label('applied'),
        func.count(case((StaffTimesheetEntry.status == 'approved', 1))).label('approved'),
        func.count(case((
            StaffTimesheetEntry.status.in_(['rejected', 'pending_edit']),
            1
        ))).label('exceptions'),
        func.count(case((
            StaffTimesheetEntry.status.in_(['submitted', 'resubmitted']),
            1
        ))).label('pending'),
        func.coalesce(func.sum(case(
            (StaffTimesheetEntry.status.in_(['submitted', 'resubmitted', 'approved']),
             StaffTimesheetEntry.duration_minutes),
            else_=0
        )), 0).label('submitted_total_mins'),
        func.coalesce(func.sum(case(
            (StaffTimesheetEntry.status == 'approved',
             StaffTimesheetEntry.duration_minutes),
            else_=0
        )), 0).label('approved_total_mins'),
    ).filter(*ts_filters).group_by(StaffTimesheetEntry.employee_id).all()
    ts_map = {r.employee_id: r for r in ts_cols}

    # ── 5. SERVICE TICKETS — batch query per service_technician_id ───────────
    try:
        tkt_filters = [ServiceTicket.service_technician_id.in_(emp_ids)]
        if is_range:
            tkt_filters += [
                func.date(ServiceTicket.created_at) >= from_date,
                func.date(ServiceTicket.created_at) <= to_date,
            ]
        tkt_cols = db.query(
            ServiceTicket.service_technician_id,
            func.count(ServiceTicket.id).label('raised'),
            func.count(case((
                ServiceTicket.status.in_(['Resolved', 'Closed']),
                1
            ))).label('handled'),
            func.count(case((
                ServiceTicket.status.in_(['Open', 'In Progress']),
                1
            ))).label('pending'),
            func.count(case((
                ServiceTicket.sla_status == 'Within SLA',
                1
            ))).label('in_time'),
        ).filter(*tkt_filters).group_by(ServiceTicket.service_technician_id).all()
        tkt_map = {r.service_technician_id: r for r in tkt_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] Ticket query failed: %s", e)
        tkt_map = {}

    # ── 6. PO — batch query per store_manager_id ─────────────────────────────
    try:
        from app.models.marketplace import MarketplacePurchaseOrder
        po_filters = [MarketplacePurchaseOrder.store_manager_id.in_(emp_ids)]
        if is_range:
            po_filters += [
                func.date(MarketplacePurchaseOrder.created_at) >= from_date,
                func.date(MarketplacePurchaseOrder.created_at) <= to_date,
            ]
        po_cols = db.query(
            MarketplacePurchaseOrder.store_manager_id,
            func.count(MarketplacePurchaseOrder.id).label('total'),
            func.count(case((
                MarketplacePurchaseOrder.status.in_(['confirmed', 'accepted', 'in_progress', 'under_procurement']),
                1
            ))).label('in_queue'),
            func.count(case((
                MarketplacePurchaseOrder.status.in_(['received', 'payment_received', 'payment_pending', 'dispatched']),
                1
            ))).label('completed'),
            func.count(case((
                MarketplacePurchaseOrder.status.in_(['hold']),
                1
            ))).label('pending'),
            func.count(case((
                MarketplacePurchaseOrder.status == 'cancelled',
                1
            ))).label('cancelled'),
        ).filter(*po_filters).group_by(MarketplacePurchaseOrder.store_manager_id).all()
        po_map = {r.store_manager_id: r for r in po_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] PO query failed: %s", e)
        po_map = {}

    # ── 7. PR — batch query per store_manager_id ─────────────────────────────
    try:
        from app.models.marketplace import MarketplaceProcurementRequest
        pr_filters = [MarketplaceProcurementRequest.store_manager_id.in_(emp_ids)]
        if is_range:
            pr_filters += [
                func.date(MarketplaceProcurementRequest.created_at) >= from_date,
                func.date(MarketplaceProcurementRequest.created_at) <= to_date,
            ]
        pr_cols = db.query(
            MarketplaceProcurementRequest.store_manager_id,
            func.count(MarketplaceProcurementRequest.id).label('total'),
            func.count(case((
                MarketplaceProcurementRequest.status == 'ordered',
                1
            ))).label('in_queue'),
            func.count(case((
                MarketplaceProcurementRequest.status.in_(['received', 'completed']),
                1
            ))).label('completed'),
            func.count(case((
                MarketplaceProcurementRequest.status.in_(['pending', 'confirmed', 'payment_received', 'procurement']),
                1
            ))).label('pending'),
        ).filter(*pr_filters).group_by(MarketplaceProcurementRequest.store_manager_id).all()
        pr_map = {r.store_manager_id: r for r in pr_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] PR query failed: %s", e)
        pr_map = {}

    # ── 8. CALL LOGS — talk time per staff_id ────────────────────────────────
    call_map = {}
    try:
        from app.models.call_tracking import StaffCallLog
        call_filters = [StaffCallLog.staff_id.in_(emp_ids)]
        if is_range:
            call_filters += [
                StaffCallLog.call_date >= from_date.isoformat(),
                StaffCallLog.call_date <= to_date.isoformat(),
            ]
        call_cols = db.query(
            StaffCallLog.staff_id,
            func.count(StaffCallLog.id).label('total_calls'),
            func.coalesce(func.sum(StaffCallLog.duration_seconds), 0).label('total_secs'),
            func.count(func.distinct(StaffCallLog.call_date)).label('call_days'),
        ).filter(*call_filters).group_by(StaffCallLog.staff_id).all()
        call_map = {r.staff_id: r for r in call_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] Call log query failed: %s", e)

    # ── 9. CRM DEAL VALUE — won deals per primary_owner_id ───────────────────
    crm_deal_map = {}
    try:
        deal_filters = [
            CRMLead.primary_owner_id.in_(emp_ids),
            CRMLead.status == 'won',
        ]
        if is_range:
            deal_filters += [
                func.date(CRMLead.updated_at) >= from_date,
                func.date(CRMLead.updated_at) <= to_date,
            ]
        deal_cols = db.query(
            CRMLead.primary_owner_id,
            func.count(CRMLead.id).label('deals_count'),
            func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('deal_value_total'),
            func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('deal_value_received'),
            func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('deal_value_balance'),
        ).filter(*deal_filters).group_by(CRMLead.primary_owner_id).all()
        crm_deal_map = {r.primary_owner_id: r for r in deal_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] CRM deal value query failed: %s", e)

    # ── 10. ATTENDANCE — worked hours per employee_id ─────────────────────────
    att_map = {}
    try:
        from app.models.staff_attendance import StaffAttendance
        att_filters = [
            StaffAttendance.employee_id.in_(emp_ids),
            StaffAttendance.clock_in.isnot(None),
        ]
        if is_range:
            att_filters += [
                StaffAttendance.date >= from_date,
                StaffAttendance.date <= to_date,
            ]
        att_cols = db.query(
            StaffAttendance.employee_id,
            func.count(StaffAttendance.id).label('days_present'),
            func.coalesce(func.sum(StaffAttendance.worked_minutes), 0).label('total_worked_minutes'),
        ).filter(*att_filters).group_by(StaffAttendance.employee_id).all()
        att_map = {r.employee_id: r for r in att_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] Attendance query failed: %s", e)

    # ── 11. ATTENDANCE — not logged out (clock_in set, clock_out NULL) ────────
    nlo_map = {}
    try:
        from app.models.staff_attendance import StaffAttendance as _SAtt2
        nlo_filters = [
            _SAtt2.employee_id.in_(emp_ids),
            _SAtt2.clock_in.isnot(None),
            _SAtt2.clock_out.is_(None),
        ]
        if is_range:
            nlo_filters += [_SAtt2.date >= from_date, _SAtt2.date <= to_date]
        nlo_cols = db.query(
            _SAtt2.employee_id,
            func.count(_SAtt2.id).label('cnt'),
        ).filter(*nlo_filters).group_by(_SAtt2.employee_id).all()
        nlo_map = {r.employee_id: r.cnt for r in nlo_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] NLO query failed: %s", e)

    # ── 12. HR FINAL ATTENDANCE — from attendance sheet (raw SQL) ────────────
    hr_att_map = {}
    try:
        emp_ids_csv = ','.join(str(i) for i in emp_ids)
        hr_date_clause = ""
        hr_params: dict = {}
        if is_range:
            hr_date_clause = "AND date BETWEEN :d_from AND :d_to"
            hr_params = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        hr_sql = text(f"""
            SELECT employee_id,
                   COUNT(*) FILTER (WHERE attendance_status::text IN ('present','half_day','on_duty')) AS hr_present
            FROM staff_attendance_sheets
            WHERE employee_id IN ({emp_ids_csv})
            {hr_date_clause}
            GROUP BY employee_id
        """)
        hr_rows = db.execute(hr_sql, hr_params).fetchall()
        hr_att_map = {r.employee_id: int(r.hr_present or 0) for r in hr_rows}
    except Exception as e:
        logger.warning("[SNAPSHOT] HR att query failed: %s", e)

    # ── 13. DIALER SESSIONS — session count + paused secs per staff ──────────
    dialer_sess_map: dict = {}
    try:
        emp_ids_csv = ','.join(str(i) for i in emp_ids)
        user_refs_csv = ','.join("'" + str(i) + "'" for i in emp_ids)
        ds_date_clause = ""
        ds_params: dict = {}
        if is_range:
            ds_date_clause = "AND DATE(created_at AT TIME ZONE 'Asia/Kolkata') BETWEEN :d_from AND :d_to"
            ds_params = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        ds_sql = text(f"""
            SELECT
                CAST(user_ref AS INTEGER) AS staff_id,
                COUNT(id) AS session_count,
                COALESCE(SUM(
                    CASE
                        WHEN status != 'paused' AND paused_at IS NOT NULL
                             AND last_active_at IS NOT NULL AND last_active_at > paused_at
                        THEN EXTRACT(EPOCH FROM (last_active_at - paused_at))
                        WHEN status = 'paused' AND paused_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'UTC' - paused_at))
                        ELSE 0
                    END
                ), 0) AS paused_secs,
                COALESCE(SUM(
                    EXTRACT(EPOCH FROM (
                        COALESCE(closed_at, NOW() AT TIME ZONE 'UTC') - started_at
                    ))
                ), 0) AS total_session_secs
            FROM crm_dialer_sessions
            WHERE user_ref IN ({user_refs_csv})
              AND user_ref ~ '^[0-9]+$'
            {ds_date_clause}
            GROUP BY user_ref
        """)
        ds_rows = db.execute(ds_sql, ds_params).fetchall()
        dialer_sess_map = {
            r.staff_id: {
                'session_count':    int(r.session_count or 0),
                'paused_secs':      int(r.paused_secs or 0),
                'total_session_secs': int(r.total_session_secs or 0),
            }
            for r in ds_rows
        }
    except Exception as e:
        logger.warning("[SNAPSHOT] Dialer session query failed: %s", e)

    # ── 14. DIALER ATTEMPTS — skipped count per staff ────────────────────────
    dialer_att_map: dict = {}
    try:
        user_refs_csv = ','.join("'" + str(i) + "'" for i in emp_ids)
        da_date_clause = ""
        da_params: dict = {}
        if is_range:
            da_date_clause = "AND DATE(ds.created_at AT TIME ZONE 'Asia/Kolkata') BETWEEN :d_from AND :d_to"
            da_params = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        da_sql = text(f"""
            SELECT
                CAST(ds.user_ref AS INTEGER) AS staff_id,
                COUNT(da.id) AS total_attempts,
                SUM(CASE WHEN da.call_outcome IN ('skipped','skip') THEN 1 ELSE 0 END) AS skipped_count
            FROM crm_dialer_attempts da
            JOIN crm_dialer_sessions ds ON ds.id = da.session_id
            WHERE ds.user_ref IN ({user_refs_csv})
              AND ds.user_ref ~ '^[0-9]+$'
            {da_date_clause}
            GROUP BY ds.user_ref
        """)
        da_rows = db.execute(da_sql, da_params).fetchall()
        dialer_att_map = {
            r.staff_id: {
                'total_attempts': int(r.total_attempts or 0),
                'skipped_count':  int(r.skipped_count or 0),
            }
            for r in da_rows
        }
    except Exception as e:
        logger.warning("[SNAPSHOT] Dialer attempts query failed: %s", e)

    # ── 15. DAY PLAN — planned vs finalized days per employee ─────────────────
    dayplan_map: dict = {}
    try:
        dp_filters = [StaffDayPlan.employee_id.in_(emp_ids)]
        if is_range:
            dp_filters += [StaffDayPlan.plan_date >= from_date, StaffDayPlan.plan_date <= to_date]
        dp_cols = db.query(
            StaffDayPlan.employee_id,
            func.count(StaffDayPlan.id).label('days_planned'),
            func.count(case((StaffDayPlan.finalized_at.isnot(None), 1))).label('days_finished'),
        ).filter(*dp_filters).group_by(StaffDayPlan.employee_id).all()
        dayplan_map = {r.employee_id: r for r in dp_cols}
    except Exception as e:
        logger.warning("[SNAPSHOT] Day plan query failed: %s", e)

    # ── Assemble result rows ──────────────────────────────────────────────────
    results = []
    for emp in emp_rows:
        eid = emp.id

        ta  = tasks_by_assignee.get(eid)
        tc  = tasks_by_creator.get(eid)
        k   = kra_map.get(eid)
        c   = crm_map.get(eid)
        ts  = ts_map.get(eid)
        tkt = tkt_map.get(eid)
        po  = po_map.get(eid)
        pr  = pr_map.get(eid)
        cl  = call_map.get(eid)
        dv  = crm_deal_map.get(eid)
        at  = att_map.get(eid)
        dp  = dayplan_map.get(eid)

        def _pct(num, den):
            return round(num / den * 100, 1) if den and den > 0 else None

        # Talk time averages
        cl_total_secs  = int(cl.total_secs) if cl and cl.total_secs else 0
        cl_call_days   = int(cl.call_days)  if cl and cl.call_days  else 0
        cl_total_calls = int(cl.total_calls) if cl else 0
        cl_avg_secs    = round(cl_total_secs / cl_call_days) if cl_call_days > 0 else 0
        cl_avg_calls_per_day = round(cl_total_calls / cl_call_days) if cl_call_days > 0 else 0

        # Attendance averages
        at_days    = int(at.days_present)        if at and at.days_present else 0
        at_mins    = int(at.total_worked_minutes) if at else 0
        at_avg_min = round(at_mins / at_days)    if at_days > 0 else 0
        at_nlo     = nlo_map.get(eid, 0)
        at_hr_pres = hr_att_map.get(eid, 0)

        # Dialer data
        ds = dialer_sess_map.get(eid, {})
        da = dialer_att_map.get(eid, {})
        ds_sessions     = ds.get('session_count', 0)
        ds_paused_secs  = ds.get('paused_secs', 0)
        ds_total_secs   = ds.get('total_session_secs', 0)
        ds_inactive_secs = max(0, ds_total_secs - cl_total_secs - ds_paused_secs)
        da_skipped      = da.get('skipped_count', 0)

        # Day plan data
        dp_planned  = int(dp.days_planned)  if dp and dp.days_planned  else 0
        dp_finished = int(dp.days_finished) if dp and dp.days_finished else 0
        dp_diff     = dp_planned - dp_finished

        # Timesheet minutes
        ts_sub_mins = int(ts.submitted_total_mins) if ts and ts.submitted_total_mins else 0
        ts_app_mins = int(ts.approved_total_mins)  if ts and ts.approved_total_mins  else 0
        ts_sub_avg  = round(ts_sub_mins / at_days) if at_days > 0 else 0
        ts_app_avg  = round(ts_app_mins / at_days) if at_days > 0 else 0

        results.append({
            "employee_id": eid,
            "emp_code": emp.emp_code or '',
            "name": emp.full_name or '',
            "department": dept_map.get(emp.department_id, '—'),
            "department_id": emp.department_id,
            "company_id": emp.base_company_id,
            "company_name": company_map.get(emp.base_company_id, '—') if emp.base_company_id else '—',
            "reporting_manager_id": emp.reporting_manager_id,
            "reporting_manager_name": mgr_map.get(emp.reporting_manager_id, '—') if emp.reporting_manager_id else '—',

            "tasks_assignee": {
                "total":       int(ta.total)   if ta else 0,
                "handled":     int(ta.handled) if ta else 0,
                "pending":     int(ta.pending) if ta else 0,
                "overdue":     int(ta.overdue) if ta else 0,
                "overdue_pct": _pct(int(ta.overdue), int(ta.total)) if ta and ta.total else None,
            },
            "tasks_creator": {
                "total":       int(tc.total)   if tc else 0,
                "handled":     int(tc.handled) if tc else 0,
                "pending":     int(tc.pending) if tc else 0,
                "overdue":     int(tc.overdue) if tc else 0,
                "overdue_pct": _pct(int(tc.overdue), int(tc.total)) if tc and tc.total else None,
            },
            "day_plan": {
                "days_planned":  dp_planned,
                "days_finished": dp_finished,
                "diff":          dp_diff,
            },

            "kra": {
                "assigned":       int(k.total)   if k else 0,
                "handled":        int(k.handled) if k else 0,
                "pending":        int(k.pending) if k else 0,
                "skipped":        int(k.skipped) if k else 0,
                "completion_pct": _pct(int(k.handled), int(k.total)) if k and k.total else None,
            },

            "crm": {
                "total":        int(c.total)        if c else 0,
                "new_leads":    int(c.new_leads)    if c else 0,
                "deals_closed": int(c.deals_closed) if c else 0,
                "not_handled":  int(c.not_handled)  if c else 0,
                "overdue":      int(c.overdue)      if c else 0,
            },

            "tickets": {
                "raised":    int(tkt.raised)   if tkt else 0,
                "handled":   int(tkt.handled)  if tkt else 0,
                "pending":   int(tkt.pending)  if tkt else 0,
                "in_time":   int(tkt.in_time)  if tkt else 0,
                "in_time_pct": _pct(int(tkt.in_time), int(tkt.raised)) if tkt and tkt.raised else None,
            },

            "po": {
                "total":          int(po.total)     if po else 0,
                "in_queue":       int(po.in_queue)  if po else 0,
                "completed":      int(po.completed) if po else 0,
                "pending":        int(po.pending)   if po else 0,
                "cancelled":      int(po.cancelled) if po else 0,
                "completion_pct": _pct(int(po.completed), int(po.total)) if po and po.total else None,
            },

            "pr": {
                "total":          int(pr.total)     if pr else 0,
                "in_queue":       int(pr.in_queue)  if pr else 0,
                "completed":      int(pr.completed) if pr else 0,
                "pending":        int(pr.pending)   if pr else 0,
                "completion_pct": _pct(int(pr.completed), int(pr.total)) if pr and pr.total else None,
            },

            "calls": {
                "total_calls":        cl_total_calls,
                "total_secs":         cl_total_secs,
                "call_days":          cl_call_days,
                "avg_secs_per_day":   cl_avg_secs,
                "avg_calls_per_day":  cl_avg_calls_per_day,
            },

            "dialer": {
                "sessions":      ds_sessions,
                "paused_secs":   ds_paused_secs,
                "inactive_secs": ds_inactive_secs,
                "skipped":       da_skipped,
            },

            "deal": {
                "deals_won":           int(dv.deals_count)       if dv else 0,
                "deal_value_total":    float(dv.deal_value_total)    if dv else 0.0,
                "deal_value_received": float(dv.deal_value_received) if dv else 0.0,
                "deal_value_balance":  float(dv.deal_value_balance)  if dv else 0.0,
            },

            "attendance": {
                "days_present":         at_days,
                "hr_final_present":     at_hr_pres,
                "not_logged_out":       at_nlo,
                "total_worked_minutes": at_mins,
                "avg_mins_per_day":     at_avg_min,
            },

            "timesheet": {
                "applied":           int(ts.applied)            if ts else 0,
                "approved":          int(ts.approved)           if ts else 0,
                "exceptions":        int(ts.exceptions)         if ts else 0,
                "pending":           int(ts.pending)            if ts else 0,
                "submitted_avg_min": ts_sub_avg,
                "approved_avg_min":  ts_app_avg,
            },
        })

    results.sort(key=lambda x: (x['department'] or ''), )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# My Team Summary helpers — DC Protocol: no N+1, batch queries, read-only
# ─────────────────────────────────────────────────────────────────────────────

def _ops_metrics_for_ids(db: Session, emp_ids: List[int], is_range: bool,
                          from_date, to_date, today) -> dict:
    """Batch-query all operational metrics for a list of employee IDs.
    Returns dict[employee_id -> metrics_dict]. DC Protocol: read-only, no N+1."""
    if not emp_ids:
        return {}

    def _r(x): return x if x is not None else 0
    def _pct(n, d): return round(n / d * 100, 1) if d else None

    # 1. Tasks as assignee
    ta_rows = db.query(
        StaffTask.primary_assignee_id,
        func.count(StaffTask.id).label('total'),
        func.count(case((StaffTask.status == 'completed', 1))).label('handled'),
        func.count(case((StaffTask.status.in_(['pending','in_progress','on_hold','under_review']), 1))).label('pending'),
        func.count(case((and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed','cancelled'])), 1))).label('overdue'),
    ).filter(
        StaffTask.primary_assignee_id.in_(emp_ids), StaffTask.status != 'cancelled',
        *(([StaffTask.created_at >= datetime.combine(from_date, datetime.min.time()),
            StaffTask.created_at <= datetime.combine(to_date, datetime.max.time())]) if is_range else [])
    ).group_by(StaffTask.primary_assignee_id).all()
    ta_map = {r.primary_assignee_id: r for r in ta_rows}

    # 2. Tasks as creator
    tc_rows = db.query(
        StaffTask.created_by,
        func.count(StaffTask.id).label('total'),
        func.count(case((StaffTask.status == 'completed', 1))).label('handled'),
        func.count(case((StaffTask.status.in_(['pending','in_progress','on_hold','under_review']), 1))).label('pending'),
        func.count(case((and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed','cancelled'])), 1))).label('overdue'),
    ).filter(
        StaffTask.created_by.in_(emp_ids), StaffTask.status != 'cancelled',
        *(([StaffTask.created_at >= datetime.combine(from_date, datetime.min.time()),
            StaffTask.created_at <= datetime.combine(to_date, datetime.max.time())]) if is_range else [])
    ).group_by(StaffTask.created_by).all()
    tc_map = {r.created_by: r for r in tc_rows}

    # 3. KRA
    kf = [StaffKRADailyInstance.employee_id.in_(emp_ids)]
    if is_range:
        kf += [StaffKRADailyInstance.instance_date >= from_date, StaffKRADailyInstance.instance_date <= to_date]
    kra_rows = db.query(
        StaffKRADailyInstance.employee_id,
        func.count(StaffKRADailyInstance.id).label('total'),
        func.count(case((StaffKRADailyInstance.completion_status == 'completed', 1))).label('handled'),
        func.count(case((StaffKRADailyInstance.completion_status.in_(['pending','in_progress','partial']), 1))).label('pending'),
        func.count(case((StaffKRADailyInstance.completion_status.in_(['skipped','na']), 1))).label('skipped'),
    ).filter(*kf).group_by(StaffKRADailyInstance.employee_id).all()
    kra_map = {r.employee_id: r for r in kra_rows}

    # 4. CRM leads
    not_h = today - timedelta(days=3)
    cf = [CRMLead.primary_owner_id.in_(emp_ids)]
    if is_range:
        cf += [func.date(CRMLead.created_at) >= from_date, func.date(CRMLead.created_at) <= to_date]
    crm_rows = db.query(
        CRMLead.primary_owner_id,
        func.count(CRMLead.id).label('total'),
        func.count(case((CRMLead.status == 'new', 1))).label('new_leads'),
        func.count(case((CRMLead.status == 'won', 1))).label('deals_closed'),
        func.count(case((and_(CRMLead.status == 'new', func.date(CRMLead.created_at) <= not_h), 1))).label('not_handled'),
        func.count(case((and_(CRMLead.status.notin_(['won','lost','cancelled','completed']),
                              func.date(CRMLead.created_at) <= not_h), 1))).label('overdue'),
    ).filter(*cf).group_by(CRMLead.primary_owner_id).all()
    crm_map = {r.primary_owner_id: r for r in crm_rows}

    # 5. Timesheet
    tsf = [StaffTimesheetEntry.employee_id.in_(emp_ids)]
    if is_range:
        tsf += [StaffTimesheetEntry.date >= from_date, StaffTimesheetEntry.date <= to_date]
    ts_rows = db.query(
        StaffTimesheetEntry.employee_id,
        func.count(StaffTimesheetEntry.id).label('applied'),
        func.count(case((StaffTimesheetEntry.status == 'approved', 1))).label('approved'),
        func.count(case((StaffTimesheetEntry.status.in_(['rejected','pending_edit']), 1))).label('exceptions'),
        func.count(case((StaffTimesheetEntry.status.in_(['submitted','resubmitted']), 1))).label('pending'),
        func.coalesce(func.sum(case((StaffTimesheetEntry.status.in_(['submitted','resubmitted','approved']),
                                     StaffTimesheetEntry.duration_minutes), else_=0)), 0).label('sub_total_mins'),
        func.coalesce(func.sum(case((StaffTimesheetEntry.status == 'approved',
                                     StaffTimesheetEntry.duration_minutes), else_=0)), 0).label('app_total_mins'),
    ).filter(*tsf).group_by(StaffTimesheetEntry.employee_id).all()
    ts_map = {r.employee_id: r for r in ts_rows}

    # 6. Service tickets
    tkt_map = {}
    try:
        tkf = [ServiceTicket.service_technician_id.in_(emp_ids)]
        if is_range:
            tkf += [func.date(ServiceTicket.created_date) >= from_date, func.date(ServiceTicket.created_date) <= to_date]
        tkt_rows = db.query(
            ServiceTicket.service_technician_id,
            func.count(ServiceTicket.id).label('raised'),
            func.count(case((ServiceTicket.status.in_(['Resolved','Closed']), 1))).label('handled'),
            func.count(case((ServiceTicket.status.in_(['Open','In Progress']), 1))).label('pending'),
            func.count(case((ServiceTicket.sla_status == 'Within SLA', 1))).label('in_time'),
        ).filter(*tkf).group_by(ServiceTicket.service_technician_id).all()
        tkt_map = {r.service_technician_id: r for r in tkt_rows}
    except Exception as e:
        logger.warning('[MY_TEAM] Ticket query: %s', e)
        try: db.rollback()
        except: pass

    # 7. PO — count all POs raised by team (created_by) or assigned (store_manager_id)
    po_map = {}
    try:
        from app.models.marketplace import MarketplacePurchaseOrder
        ids_csv_po = ','.join(str(i) for i in emp_ids)
        po_dc = ""; po_p: dict = {}
        if is_range:
            po_dc = "WHERE DATE(created_at) BETWEEN :d_from AND :d_to"
            po_p = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        po_sql = text(f"""
            SELECT emp_id,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status IN ('confirmed','accepted','in_progress','under_procurement')) AS in_queue,
                COUNT(*) FILTER (WHERE status IN ('received','payment_received','payment_pending','dispatched')) AS completed,
                COUNT(*) FILTER (WHERE status = 'hold') AS pending
            FROM (
                SELECT id, status, store_manager_id AS emp_id, created_at FROM marketplace_purchase_orders
                WHERE store_manager_id IN ({ids_csv_po})
                UNION ALL
                SELECT id, status,
                    CAST(created_by AS INTEGER) AS emp_id, created_at
                FROM marketplace_purchase_orders
                WHERE created_by ~ '^[0-9]+$'
                    AND CAST(created_by AS INTEGER) IN ({ids_csv_po})
                    AND (store_manager_id IS NULL OR store_manager_id NOT IN ({ids_csv_po}))
            ) sub
            {po_dc}
            GROUP BY emp_id
        """)
        po_rows2 = db.execute(po_sql, po_p).fetchall()
        po_map = {r.emp_id: r for r in po_rows2}
    except Exception as e:
        logger.warning('[MY_TEAM] PO query: %s', e)
        try: db.rollback()
        except: pass

    # 8. PR — count all PRs raised by team (created_by) or assigned (store_manager_id)
    pr_map = {}
    try:
        from app.models.marketplace import MarketplaceProcurementRequest
        ids_csv_pr = ','.join(str(i) for i in emp_ids)
        pr_dc = ""; pr_p: dict = {}
        if is_range:
            pr_dc = "WHERE DATE(created_at) BETWEEN :d_from AND :d_to"
            pr_p = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        pr_sql = text(f"""
            SELECT emp_id,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'ordered') AS in_queue,
                COUNT(*) FILTER (WHERE status IN ('received','completed')) AS completed,
                COUNT(*) FILTER (WHERE status IN ('pending','confirmed','payment_received','procurement')) AS pending
            FROM (
                SELECT id, status, store_manager_id AS emp_id, created_at FROM marketplace_procurement_requests
                WHERE store_manager_id IN ({ids_csv_pr})
                UNION ALL
                SELECT id, status,
                    CAST(created_by AS INTEGER) AS emp_id, created_at
                FROM marketplace_procurement_requests
                WHERE created_by ~ '^[0-9]+$'
                    AND CAST(created_by AS INTEGER) IN ({ids_csv_pr})
                    AND (store_manager_id IS NULL OR store_manager_id NOT IN ({ids_csv_pr}))
            ) sub
            {pr_dc}
            GROUP BY emp_id
        """)
        pr_rows2 = db.execute(pr_sql, pr_p).fetchall()
        pr_map = {r.emp_id: r for r in pr_rows2}
    except Exception as e:
        logger.warning('[MY_TEAM] PR query: %s', e)
        try: db.rollback()
        except: pass

    # 9. Call logs
    call_map = {}
    try:
        from app.models.call_tracking import StaffCallLog
        clf = [StaffCallLog.staff_id.in_(emp_ids)]
        if is_range:
            clf += [StaffCallLog.call_date >= from_date.isoformat(), StaffCallLog.call_date <= to_date.isoformat()]
        cl_rows = db.query(
            StaffCallLog.staff_id,
            func.count(StaffCallLog.id).label('total_calls'),
            func.coalesce(func.sum(StaffCallLog.duration_seconds), 0).label('total_secs'),
            func.count(func.distinct(StaffCallLog.call_date)).label('call_days'),
        ).filter(*clf).group_by(StaffCallLog.staff_id).all()
        call_map = {r.staff_id: r for r in cl_rows}
    except Exception as e:
        logger.warning('[MY_TEAM] Call log query: %s', e)
        try: db.rollback()
        except: pass

    # 10. CRM Deal value (won deals)
    deal_map = {}
    try:
        df = [CRMLead.primary_owner_id.in_(emp_ids), CRMLead.status == 'won']
        if is_range:
            df += [func.date(CRMLead.updated_at) >= from_date, func.date(CRMLead.updated_at) <= to_date]
        dv_rows = db.query(
            CRMLead.primary_owner_id,
            func.count(CRMLead.id).label('deals_count'),
            func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('deal_value_total'),
            func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('deal_value_received'),
            func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('deal_value_balance'),
        ).filter(*df).group_by(CRMLead.primary_owner_id).all()
        deal_map = {r.primary_owner_id: r for r in dv_rows}
    except Exception as e:
        logger.warning('[MY_TEAM] Deal value query: %s', e)
        try: db.rollback()
        except: pass

    # 10b. CRM Deal transactions (submitted = payment_pending, confirmed = deal_value_received > 0)
    deal_txn_map = {}
    try:
        from app.models.crm import CRMLeadDeal
        dtxn_f = [CRMLeadDeal.created_by_id.in_(emp_ids)]
        if is_range:
            dtxn_f += [func.date(CRMLeadDeal.deal_date) >= from_date, func.date(CRMLeadDeal.deal_date) <= to_date]
        dtxn_rows = db.query(
            CRMLeadDeal.created_by_id,
            func.count(case((CRMLeadDeal.status.in_(['payment_pending', 'submitted']), 1))).label('submitted_count'),
            func.coalesce(func.sum(case((CRMLeadDeal.status.in_(['payment_pending', 'submitted']),
                                         CRMLeadDeal.deal_value_total), else_=0)), 0).label('submitted_value'),
            func.count(case((CRMLeadDeal.deal_value_received > 0, 1))).label('confirmed_count'),
            func.coalesce(func.sum(case((CRMLeadDeal.deal_value_received > 0,
                                         CRMLeadDeal.deal_value_received), else_=0)), 0).label('confirmed_value'),
        ).filter(*dtxn_f).group_by(CRMLeadDeal.created_by_id).all()
        deal_txn_map = {r.created_by_id: r for r in dtxn_rows}
    except Exception as e:
        logger.warning('[MY_TEAM] Deal txn query: %s', e)
        try: db.rollback()
        except: pass

    # 11. Attendance (clock-in based)
    att_map = {}
    nlo_map = {}
    try:
        from app.models.staff_attendance import StaffAttendance
        af = [StaffAttendance.employee_id.in_(emp_ids), StaffAttendance.clock_in.isnot(None)]
        if is_range:
            af += [StaffAttendance.date >= from_date, StaffAttendance.date <= to_date]
        att_rows = db.query(
            StaffAttendance.employee_id,
            func.count(StaffAttendance.id).label('days_present'),
            func.coalesce(func.sum(StaffAttendance.worked_minutes), 0).label('total_worked_minutes'),
        ).filter(*af).group_by(StaffAttendance.employee_id).all()
        att_map = {r.employee_id: r for r in att_rows}

        nf = [StaffAttendance.employee_id.in_(emp_ids), StaffAttendance.clock_in.isnot(None),
              StaffAttendance.clock_out.is_(None)]
        if is_range:
            nf += [StaffAttendance.date >= from_date, StaffAttendance.date <= to_date]
        nlo_rows = db.query(StaffAttendance.employee_id, func.count(StaffAttendance.id).label('cnt')).filter(*nf).group_by(StaffAttendance.employee_id).all()
        nlo_map = {r.employee_id: r.cnt for r in nlo_rows}
    except Exception as e:
        logger.warning('[MY_TEAM] Attendance query: %s', e)
        try: db.rollback()
        except: pass

    # 12. HR final attendance (raw SQL)
    hr_att_map = {}
    try:
        ids_csv = ','.join(str(i) for i in emp_ids)
        hr_dc = ""; hr_p: dict = {}
        if is_range:
            hr_dc = "AND date BETWEEN :d_from AND :d_to"
            hr_p = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        hr_sql = text(f"""SELECT employee_id,
                   COUNT(*) FILTER (WHERE attendance_status::text IN ('present','half_day','on_duty')) AS hr_present
            FROM staff_attendance_sheets WHERE employee_id IN ({ids_csv}) {hr_dc} GROUP BY employee_id""")
        hr_att_map = {r.employee_id: int(r.hr_present or 0) for r in db.execute(hr_sql, hr_p).fetchall()}
    except Exception as e:
        logger.warning('[MY_TEAM] HR att query: %s', e)
        try: db.rollback()
        except: pass

    # 13. Dialer sessions (raw SQL)
    dialer_sess_map: dict = {}
    try:
        urefs = ','.join("'" + str(i) + "'" for i in emp_ids)
        ds_dc = ""; ds_p: dict = {}
        if is_range:
            ds_dc = "AND DATE(started_at AT TIME ZONE 'Asia/Kolkata') BETWEEN :d_from AND :d_to"
            ds_p = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        ds_sql = text(f"""SELECT CAST(user_ref AS INTEGER) AS staff_id,
            COUNT(id) AS session_count,
            COALESCE(SUM(CASE WHEN status != 'paused' AND paused_at IS NOT NULL AND last_active_at IS NOT NULL AND last_active_at > paused_at
                THEN EXTRACT(EPOCH FROM (last_active_at - paused_at))
                WHEN status = 'paused' AND paused_at IS NOT NULL
                THEN EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'UTC' - paused_at)) ELSE 0 END), 0) AS paused_secs,
            COALESCE(SUM(EXTRACT(EPOCH FROM (COALESCE(closed_at, NOW() AT TIME ZONE 'UTC') - started_at))), 0) AS total_session_secs
            FROM crm_dialer_sessions WHERE user_ref IN ({urefs}) AND user_ref ~ '^[0-9]+$' {ds_dc} GROUP BY user_ref""")
        dialer_sess_map = {r.staff_id: {'session_count': int(r.session_count or 0),
            'paused_secs': int(r.paused_secs or 0), 'total_session_secs': int(r.total_session_secs or 0)}
            for r in db.execute(ds_sql, ds_p).fetchall()}
    except Exception as e:
        logger.warning('[MY_TEAM] Dialer session query: %s', e)
        try: db.rollback()
        except: pass

    # 14. Dialer attempts — skipped (raw SQL)
    dialer_att_map: dict = {}
    try:
        urefs = ','.join("'" + str(i) + "'" for i in emp_ids)
        da_dc = ""; da_p: dict = {}
        if is_range:
            da_dc = "AND DATE(ds.started_at AT TIME ZONE 'Asia/Kolkata') BETWEEN :d_from AND :d_to"
            da_p = {"d_from": from_date.isoformat(), "d_to": to_date.isoformat()}
        da_sql = text(f"""SELECT CAST(ds.user_ref AS INTEGER) AS staff_id,
            SUM(CASE WHEN da.call_outcome IN ('skipped','skip') THEN 1 ELSE 0 END) AS skipped_count
            FROM crm_dialer_attempts da JOIN crm_dialer_sessions ds ON ds.id = da.session_id
            WHERE ds.user_ref IN ({urefs}) AND ds.user_ref ~ '^[0-9]+$' {da_dc} GROUP BY ds.user_ref""")
        dialer_att_map = {r.staff_id: int(r.skipped_count or 0) for r in db.execute(da_sql, da_p).fetchall()}
    except Exception as e:
        logger.warning('[MY_TEAM] Dialer attempts query: %s', e)
        try: db.rollback()
        except: pass

    # 15. Day plan
    dayplan_map: dict = {}
    try:
        dpf = [StaffDayPlan.employee_id.in_(emp_ids)]
        if is_range:
            dpf += [StaffDayPlan.plan_date >= from_date, StaffDayPlan.plan_date <= to_date]
        dp_rows = db.query(
            StaffDayPlan.employee_id,
            func.count(StaffDayPlan.id).label('days_planned'),
            func.count(case((StaffDayPlan.finalized_at.isnot(None), 1))).label('days_finished'),
        ).filter(*dpf).group_by(StaffDayPlan.employee_id).all()
        dayplan_map = {r.employee_id: r for r in dp_rows}
    except Exception as e:
        logger.warning('[MY_TEAM] Day plan query: %s', e)
        try: db.rollback()
        except: pass

    # Assemble per-employee result dicts
    results = {}
    for eid in emp_ids:
        ta = ta_map.get(eid); tc = tc_map.get(eid); k = kra_map.get(eid)
        c  = crm_map.get(eid); ts = ts_map.get(eid); tkt = tkt_map.get(eid)
        po = po_map.get(eid);  pr = pr_map.get(eid); cl = call_map.get(eid)
        dv = deal_map.get(eid); dtxn = deal_txn_map.get(eid)
        at = att_map.get(eid); dp = dayplan_map.get(eid)
        ds = dialer_sess_map.get(eid, {}); da_sk = dialer_att_map.get(eid, 0)

        at_days = int(at.days_present) if at else 0
        at_mins = int(at.total_worked_minutes) if at else 0
        cl_secs = int(cl.total_secs) if cl else 0; cl_days = int(cl.call_days) if cl else 0
        cl_calls = int(cl.total_calls) if cl else 0
        ds_total = ds.get('total_session_secs', 0); ds_paused = ds.get('paused_secs', 0)
        ds_inactive = max(0, ds_total - cl_secs - ds_paused)
        ds_active = max(0, ds_total - ds_paused - ds_inactive)
        ts_sub_m = int(ts.sub_total_mins) if ts else 0; ts_app_m = int(ts.app_total_mins) if ts else 0

        results[eid] = {
            "tasks_assignee": {
                "total": _r(ta.total if ta else 0), "handled": _r(ta.handled if ta else 0),
                "pending": _r(ta.pending if ta else 0), "overdue": _r(ta.overdue if ta else 0),
                "overdue_pct": _pct(_r(ta.overdue if ta else 0), _r(ta.total if ta else 0)),
            },
            "tasks_creator": {
                "total": _r(tc.total if tc else 0), "handled": _r(tc.handled if tc else 0),
                "pending": _r(tc.pending if tc else 0), "overdue": _r(tc.overdue if tc else 0),
            },
            "day_plan": {
                "days_planned": _r(dp.days_planned if dp else 0),
                "days_finished": _r(dp.days_finished if dp else 0),
                "diff": _r(dp.days_planned if dp else 0) - _r(dp.days_finished if dp else 0),
            },
            "kra": {
                "assigned": _r(k.total if k else 0), "handled": _r(k.handled if k else 0),
                "pending": _r(k.pending if k else 0), "skipped": _r(k.skipped if k else 0),
                "completion_pct": _pct(_r(k.handled if k else 0), _r(k.total if k else 0)),
            },
            "crm": {
                "total": _r(c.total if c else 0), "new_leads": _r(c.new_leads if c else 0),
                "deals_closed": _r(c.deals_closed if c else 0),
                "not_handled": _r(c.not_handled if c else 0), "overdue": _r(c.overdue if c else 0),
            },
            "calls": {
                "total_calls": cl_calls, "total_secs": cl_secs, "call_days": cl_days,
                "avg_secs_per_day": round(cl_secs / cl_days) if cl_days else 0,
                "avg_calls_per_day": round(cl_calls / cl_days) if cl_days else 0,
            },
            "dialer": {
                "sessions": ds.get('session_count', 0), "paused_secs": ds_paused,
                "inactive_secs": ds_inactive,
                "active_secs": ds_active,
                "skipped": da_sk,
            },
            "deal": {
                "deals_won": _r(dv.deals_count if dv else 0),
                "deal_value_total": float(dv.deal_value_total if dv else 0),
                "deal_value_received": float(dv.deal_value_received if dv else 0),
                "deal_value_balance": float(dv.deal_value_balance if dv else 0),
                "deals_submitted_count": int(dtxn.submitted_count if dtxn else 0),
                "deals_submitted_value": float(dtxn.submitted_value if dtxn else 0),
                "deals_confirmed_count": int(dtxn.confirmed_count if dtxn else 0),
                "deals_confirmed_value": float(dtxn.confirmed_value if dtxn else 0),
            },
            "attendance": {
                "days_present": at_days, "hr_final_present": hr_att_map.get(eid, 0),
                "not_logged_out": nlo_map.get(eid, 0),
                "total_worked_minutes": at_mins,
                "avg_mins_per_day": round(at_mins / at_days) if at_days else 0,
            },
            "timesheet": {
                "applied": _r(ts.applied if ts else 0), "approved": _r(ts.approved if ts else 0),
                "exceptions": _r(ts.exceptions if ts else 0), "pending": _r(ts.pending if ts else 0),
                "submitted_avg_min": round(ts_sub_m / at_days) if at_days else 0,
                "approved_avg_min":  round(ts_app_m / at_days) if at_days else 0,
                "_sub_total_mins": ts_sub_m, "_app_total_mins": ts_app_m,
            },
            "tickets": {
                "raised": _r(tkt.raised if tkt else 0), "handled": _r(tkt.handled if tkt else 0),
                "pending": _r(tkt.pending if tkt else 0), "in_time": _r(tkt.in_time if tkt else 0),
                "in_time_pct": _pct(_r(tkt.in_time if tkt else 0), _r(tkt.raised if tkt else 0)),
            },
            "po": {
                "total": _r(po.total if po else 0), "in_queue": _r(po.in_queue if po else 0),
                "completed": _r(po.completed if po else 0), "pending": _r(po.pending if po else 0),
                "completion_pct": _pct(_r(po.completed if po else 0), _r(po.total if po else 0)),
            },
            "pr": {
                "total": _r(pr.total if pr else 0), "in_queue": _r(pr.in_queue if pr else 0),
                "completed": _r(pr.completed if pr else 0), "pending": _r(pr.pending if pr else 0),
                "completion_pct": _pct(_r(pr.completed if pr else 0), _r(pr.total if pr else 0)),
            },
        }
    return results


def _aggregate_ops(rows: List[dict]) -> dict:
    """Sum all raw metrics across a list of employee metric dicts, recompute derived fields."""
    if not rows:
        return {}
    skip = {'overdue_pct','completion_pct','in_time_pct','avg_mins_per_day',
            'avg_secs_per_day','avg_calls_per_day','submitted_avg_min','approved_avg_min','diff'}
    total: dict = {}
    for section in rows[0]:
        total[section] = {}
        for key, val in rows[0][section].items():
            if key in skip:
                total[section][key] = 0
            else:
                total[section][key] = sum(r[section].get(key, 0) or 0 for r in rows)

    def _p(n, d): return round(n / d * 100, 1) if d else None

    ta = total['tasks_assignee']
    ta['overdue_pct'] = _p(ta['overdue'], ta['total'])
    k = total['kra']
    k['completion_pct'] = _p(k['handled'], k['assigned'])
    tkt = total['tickets']
    tkt['in_time_pct'] = _p(tkt['in_time'], tkt['raised'])
    po = total['po']
    po['completion_pct'] = _p(po['completed'], po['total'])
    pr = total['pr']
    pr['completion_pct'] = _p(pr['completed'], pr['total'])
    dp = total['day_plan']
    dp['diff'] = dp['days_planned'] - dp['days_finished']
    att = total['attendance']
    att['avg_mins_per_day'] = round(att['total_worked_minutes'] / att['days_present']) if att['days_present'] else 0
    cl = total['calls']
    cl['avg_secs_per_day']  = round(cl['total_secs']   / cl['call_days']) if cl['call_days'] else 0
    cl['avg_calls_per_day'] = round(cl['total_calls']   / cl['call_days']) if cl['call_days'] else 0
    ts = total['timesheet']
    n = len(rows)
    ts['submitted_avg_min'] = round(ts['_sub_total_mins'] / att['days_present']) if att['days_present'] else 0
    ts['approved_avg_min']  = round(ts['_app_total_mins'] / att['days_present']) if att['days_present'] else 0
    return total


def _team_avg(total: dict, count: int) -> dict:
    """Per-member average from aggregated total dict. Preserves derived/rate fields as-is."""
    if not count:
        return {}
    preserve = {'overdue_pct','completion_pct','in_time_pct','avg_mins_per_day',
                'avg_secs_per_day','avg_calls_per_day','submitted_avg_min','approved_avg_min','diff'}
    avg: dict = {}
    for section, vals in total.items():
        avg[section] = {}
        for key, val in vals.items():
            if key.startswith('_'):
                continue
            if key in preserve:
                avg[section][key] = val
            else:
                avg[section][key] = round(val / count, 1)
    return avg


@router.get("/my-team-summary", summary="Self vs Team performance summary for Progress page")
def get_my_team_summary(
    emp_id: Optional[int] = Query(None, description="Employee to view (defaults to self)"),
    from_date: Optional[date] = Query(None),
    to_date:   Optional[date] = Query(None),
    prev_date_from: Optional[date] = Query(None, description="Previous period start date for comparison"),
    prev_date_to:   Optional[date] = Query(None, description="Previous period end date for comparison"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Returns self metrics + full-downline team metrics for the given employee.
    Any authenticated staff can call this for themselves.
    Managers/key-leadership can specify emp_id to view another employee.
    DC Protocol: read-only, batch queries, no N+1.
    Supports optional prev_date_from/prev_date_to for previous period comparison.
    """
    today = _get_indian_date()
    is_range = from_date is not None and to_date is not None
    has_prev = prev_date_from is not None and prev_date_to is not None

    target_id = emp_id if emp_id else current_user.id

    # Security: key-leadership can view anyone; others can only view self or their own downline
    if target_id != current_user.id:
        if _is_key_leadership(current_user):
            pass  # allowed
        else:
            my_dl = _get_downline_ids(db, current_user.id)
            if target_id not in my_dl:
                raise HTTPException(status_code=403, detail="Access denied.")

    target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == target_id).first()
    if not target_emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    dept_map = {d.id: d.name for d in db.query(StaffDepartment.id, StaffDepartment.name).all()}

    # Self metrics
    self_metrics_map = _ops_metrics_for_ids(db, [target_id], is_range, from_date, to_date, today)
    self_metrics = self_metrics_map.get(target_id, {})

    # Full downline team (excluding self)
    team_ids = _get_downline_ids(db, target_id)
    team_rows_map: dict = {}
    team_members_info: List[dict] = []
    if team_ids:
        team_rows_map = _ops_metrics_for_ids(db, team_ids, is_range, from_date, to_date, today)
        emp_info_rows = db.query(
            StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code,
            StaffEmployee.department_id, StaffEmployee.reporting_manager_id,
            StaffEmployee.designation,
        ).filter(StaffEmployee.id.in_(team_ids)).all()
        mgr_ids = [r.reporting_manager_id for r in emp_info_rows if r.reporting_manager_id]
        mgr_map = {}
        if mgr_ids:
            mgr_map = {m.id: m.full_name for m in db.query(StaffEmployee.id, StaffEmployee.full_name).filter(StaffEmployee.id.in_(mgr_ids)).all()}
        for e in emp_info_rows:
            team_members_info.append({
                "id": e.id, "emp_code": e.emp_code or '', "name": e.full_name or '',
                "department": dept_map.get(e.department_id, '—'),
                "designation": e.designation or '—',
                "reporting_manager": mgr_map.get(e.reporting_manager_id, '—'),
                **team_rows_map.get(e.id, {}),
            })
        team_members_info.sort(key=lambda x: x.get('department', ''))

    team_rows_list = [team_rows_map[i] for i in team_ids if i in team_rows_map]
    team_total = _aggregate_ops(team_rows_list) if team_rows_list else {}
    team_avg   = _team_avg(team_total, len(team_ids)) if team_total else {}

    # Previous period comparison (optional)
    prev_self: dict = {}
    prev_team_total: dict = {}
    prev_team_avg: dict = {}
    if has_prev:
        try:
            prev_self_map = _ops_metrics_for_ids(db, [target_id], True, prev_date_from, prev_date_to, today)
            prev_self = prev_self_map.get(target_id, {})
            if team_ids:
                prev_team_map = _ops_metrics_for_ids(db, team_ids, True, prev_date_from, prev_date_to, today)
                prev_team_list = [prev_team_map[i] for i in team_ids if i in prev_team_map]
                prev_team_total = _aggregate_ops(prev_team_list) if prev_team_list else {}
                prev_team_avg   = _team_avg(prev_team_total, len(team_ids)) if prev_team_total else {}
        except Exception as e:
            logger.warning('[MY_TEAM] Prev period query failed: %s', e)

    return {
        "target_emp": {
            "id": target_emp.id,
            "emp_code": target_emp.emp_code or '',
            "name": target_emp.full_name or '',
            "department": dept_map.get(target_emp.department_id, '—'),
        },
        "period": {
            "from_date": from_date.isoformat() if from_date else None,
            "to_date":   to_date.isoformat()   if to_date   else None,
            "is_range":  is_range,
            "prev_from": prev_date_from.isoformat() if prev_date_from else None,
            "prev_to":   prev_date_to.isoformat()   if prev_date_to   else None,
        },
        "self": self_metrics,
        "team_count": len(team_ids),
        "team_total": team_total,
        "team_avg":   team_avg,
        "team_members": team_members_info,
        "prev_self":       prev_self,
        "prev_team_total": prev_team_total,
        "prev_team_avg":   prev_team_avg,
    }
