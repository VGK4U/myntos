"""
DC Protocol — Leave Date Utility
Returns per-employee sets of leave dates in a given range.

Sources (all checked, union of results):
  1. staff_attendance_sheets — HR-marked attendance with leave/holiday/weekend/half_day status
  2. staff_leave_request_days — APPROVED leave request per-day rows
  3. Calendar Sundays — default non-working, UNLESS HR explicitly marks the employee
     as present/half_day/on_duty/work_from_home on that date.

Key distinctions:
  - Full leave (sick, approved, casual, unpaid, holiday, weekend) → excluded from KRA denominator
  - Unmarked Sunday → excluded by default; overridden to working if HR marks a working status
  - Half-day → prorated at 0.5 in KRA denominator (not fully excluded)
  - Retroactive HR marking is fully dynamic: all calculations query live DB each call

Usage:
    from app.utils.leave_utils import get_employee_leave_dates, get_employee_nonworking_data

    # Simple: get full leave dates only
    leave_map = get_employee_leave_dates(db, employee_ids, date_from, date_to)

    # Full: get full leaves + half-day dates separately (for prorating)
    leave_map, half_day_map = get_employee_nonworking_data(db, employee_ids, date_from, date_to)
    # leave_map[emp_id]    = {date(2026,3,1), ...}  — fully excluded days
    # half_day_map[emp_id] = {date(2026,3,5), ...}  — count as 0.5 in denominator
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Set, Tuple

from sqlalchemy.orm import Session


LEAVE_ATTENDANCE_STATUSES = {
    'sick_leave', 'approved_leave', 'casual_leave',
    'unpaid_leave', 'holiday', 'weekend',
}

HALF_DAY_STATUS = 'half_day'

# HR statuses that make a day (including a Sunday) explicitly a working day
WORKING_ATTENDANCE_STATUSES = {'present', 'on_duty', 'work_from_home'}


def _build_sunday_set(date_from: date, date_to: date) -> Set[date]:
    """Return the set of all Sundays (weekday==6) in [date_from, date_to]."""
    sundays: Set[date] = set()
    current = date_from
    while current <= date_to:
        if current.weekday() == 6:
            sundays.add(current)
        current += timedelta(days=1)
    return sundays


def get_employee_nonworking_data(
    db: Session,
    employee_ids: List[int],
    date_from: date,
    date_to: date,
) -> Tuple[Dict[int, Set[date]], Dict[int, Set[date]]]:
    """
    Returns two maps:
      leave_map    — fully non-working days per employee.
                     Includes: HR-marked leave/holiday/weekend, approved leave requests,
                     AND calendar Sundays unless HR explicitly marks the employee as
                     present/half_day/on_duty/work_from_home on that Sunday.
      half_day_map — half-day dates per employee.
                     These count as 0.5 in KRA denominator rather than being fully excluded.
                     A half_day on a Sunday overrides the default Sunday non-working status.

    Dynamic: any retroactive HR attendance marking is automatically picked up on next API call
    because this function queries the live DB every time.
    """
    if not employee_ids:
        return {}, {}

    from app.models.staff_attendance_sheet import (
        StaffAttendanceSheet,
        StaffLeaveRequest,
        StaffLeaveRequestDay,
        LeaveRequestStatus,
    )

    leave_map: Dict[int, Set[date]] = defaultdict(set)
    half_day_map: Dict[int, Set[date]] = defaultdict(set)

    # ── Source 1: HR-marked attendance sheets ────────────────────────────────
    sheets = (
        db.query(
            StaffAttendanceSheet.employee_id,
            StaffAttendanceSheet.date,
            StaffAttendanceSheet.attendance_status,
        )
        .filter(
            StaffAttendanceSheet.employee_id.in_(employee_ids),
            StaffAttendanceSheet.date >= date_from,
            StaffAttendanceSheet.date <= date_to,
        )
        .all()
    )

    # Track which (emp_id, date) combos have an explicit working HR status.
    # Used below to decide whether to add a Sunday to leave_map.
    hr_working_dates: Dict[int, Set[date]] = defaultdict(set)

    for s in sheets:
        status_val = (
            s.attendance_status.value
            if hasattr(s.attendance_status, 'value')
            else str(s.attendance_status)
        )
        if status_val in LEAVE_ATTENDANCE_STATUSES:
            leave_map[s.employee_id].add(s.date)
            half_day_map[s.employee_id].discard(s.date)
        elif status_val == HALF_DAY_STATUS:
            # Half-day overrides default Sunday non-working (employee worked on Sunday)
            leave_map[s.employee_id].discard(s.date)
            if s.date not in leave_map[s.employee_id]:
                half_day_map[s.employee_id].add(s.date)
            hr_working_dates[s.employee_id].add(s.date)
        elif status_val in WORKING_ATTENDANCE_STATUSES:
            # Explicit working status (present, on_duty, wfh) — marks day as working
            hr_working_dates[s.employee_id].add(s.date)

    # ── Auto-Sundays: non-working by default unless HR marks employee as working ──
    sundays = _build_sunday_set(date_from, date_to)
    for emp_id in employee_ids:
        emp_working = hr_working_dates.get(emp_id, set())
        for sunday in sundays:
            if sunday not in emp_working:
                leave_map[emp_id].add(sunday)

    # ── Source 2: Approved leave request days ─────────────────────────────────
    leave_days = (
        db.query(
            StaffLeaveRequest.employee_id,
            StaffLeaveRequestDay.date,
        )
        .join(StaffLeaveRequestDay, StaffLeaveRequestDay.leave_request_id == StaffLeaveRequest.id)
        .filter(
            StaffLeaveRequest.employee_id.in_(employee_ids),
            StaffLeaveRequest.status == LeaveRequestStatus.APPROVED,
            StaffLeaveRequestDay.date >= date_from,
            StaffLeaveRequestDay.date <= date_to,
        )
        .all()
    )
    for emp_id, leave_date in leave_days:
        leave_map[emp_id].add(leave_date)
        half_day_map[emp_id].discard(leave_date)

    return dict(leave_map), dict(half_day_map)


def get_employee_leave_dates(
    db: Session,
    employee_ids: List[int],
    date_from: date,
    date_to: date,
) -> Dict[int, Set[date]]:
    """
    Backward-compatible wrapper.
    Returns {employee_id: {leave_date, ...}} for all fully non-working days in [date_from, date_to].
    Includes: HR-marked leaves/holidays/weekends, approved leave requests,
    AND calendar Sundays unless HR explicitly marks the employee as working on that Sunday.
    Half-days are NOT included here (use get_employee_nonworking_data for full split).
    """
    leave_map, _ = get_employee_nonworking_data(db, employee_ids, date_from, date_to)
    return leave_map
