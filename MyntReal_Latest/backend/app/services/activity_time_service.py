"""
Unified Activity Time Service (DC Protocol Compliant)
Central service for logging activity time from KRA, Tasks, DayPlan, Leads, Tickets, Journeys

Created: Feb 24, 2026
DC Protocol: Insert-only ledger, auto-sync to attendance
WVV Protocol: Minutes validation (>0, <=1440), source validation

Summary provides Total/Planned/Completed/Pending counts (like Task Planner tabs)
plus Required Time/Planned Time/Completed Time per category.
"""

from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models.staff_attendance import StaffAttendance, StaffActivityTimeLog, get_indian_time, get_indian_date


VALID_SOURCE_TYPES = ('kra', 'task', 'dayplan', 'lead', 'ticket', 'journey', 'custom')

SOURCE_FIELD_MAP = {
    'kra': 'kra_minutes',
    'task': 'task_minutes',
    'dayplan': 'dayplan_minutes',
    'lead': 'lead_minutes',
    'ticket': 'ticket_minutes',
    'journey': 'journey_minutes',
    'custom': 'custom_minutes',
}


def log_activity_time(
    db: Session,
    employee_id: int,
    source_type: str,
    completed_minutes: int,
    target_date: date = None,
    source_id: int = None,
    source_title: str = None,
    source_code: str = None,
    required_minutes: int = 0,
    planned_minutes: int = 0,
    description: str = None,
    ip_address: str = None,
    user_agent: str = None,
    created_by: int = None
) -> StaffActivityTimeLog:
    """
    Log an activity time entry and update attendance record.
    DC Protocol: Immutable insert into activity ledger + attendance sync.
    """
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(f"Invalid source_type: {source_type}. Must be one of {VALID_SOURCE_TYPES}")
    
    if completed_minutes < 1 or completed_minutes > 1440:
        raise ValueError(f"completed_minutes must be between 1 and 1440, got {completed_minutes}")
    
    if target_date is None:
        target_date = get_indian_date()
    
    if created_by is None:
        created_by = employee_id
    
    attendance = upsert_attendance(db, employee_id, target_date)
    
    entry = StaffActivityTimeLog(
        employee_id=employee_id,
        date=target_date,
        source_type=source_type,
        source_id=source_id,
        source_title=source_title,
        source_code=source_code,
        required_minutes=required_minutes,
        planned_minutes=planned_minutes,
        completed_minutes=completed_minutes,
        description=description,
        attendance_id=attendance.id if attendance else None,
        ip_address=ip_address,
        user_agent=user_agent,
        created_by=created_by
    )
    db.add(entry)
    db.flush()
    
    recalculate_attendance_activity(db, employee_id, target_date)
    
    return entry


def upsert_attendance(db: Session, employee_id: int, target_date: date) -> StaffAttendance:
    """
    Get or create attendance record for employee on given date.
    DC Protocol: Creates minimal attendance record if none exists.
    """
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == employee_id,
        StaffAttendance.date == target_date
    ).first()
    
    if not attendance:
        attendance = StaffAttendance(
            employee_id=employee_id,
            date=target_date,
            status='absent',
            approval_status='pending'
        )
        db.add(attendance)
        db.flush()
    
    return attendance


def recalculate_attendance_activity(db: Session, employee_id: int, target_date: date):
    """
    Recalculate activity minutes on attendance record from activity log.
    DC Protocol: Sum entries by source type, respecting approval status.
    - approved: uses approved_minutes (supervisor-adjusted)
    - submitted/resubmitted: uses completed_minutes (pending approval)
    - rejected: excluded from totals
    """
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == employee_id,
        StaffAttendance.date == target_date
    ).first()
    
    if not attendance:
        return
    
    entries = db.query(StaffActivityTimeLog).filter(
        StaffActivityTimeLog.employee_id == employee_id,
        StaffActivityTimeLog.date == target_date
    ).all()
    
    totals = {}
    for entry in entries:
        status = entry.approval_status or 'submitted'
        if status == 'rejected':
            continue
        
        if status == 'approved' and entry.approved_minutes is not None:
            mins = entry.approved_minutes
        else:
            mins = entry.completed_minutes
        
        st = entry.source_type
        totals[st] = totals.get(st, 0) + mins
    
    attendance.kra_minutes = totals.get('kra', 0)
    attendance.task_minutes = totals.get('task', 0)
    attendance.dayplan_minutes = totals.get('dayplan', 0)
    attendance.lead_minutes = totals.get('lead', 0)
    attendance.ticket_minutes = totals.get('ticket', 0)
    attendance.journey_minutes = totals.get('journey', 0)
    attendance.custom_minutes = totals.get('custom', 0)
    attendance.activity_minutes_total = sum(totals.values())


def _get_kra_counts(db: Session, employee_id: int, target_date: date) -> dict:
    """Get KRA instance counts for date: total/planned/completed/pending/in_progress"""
    from app.models.staff_kra import StaffKRADailyInstance
    instances = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.employee_id == employee_id,
        StaffKRADailyInstance.instance_date == target_date
    ).all()
    
    total = len(instances)
    completed = sum(1 for i in instances if i.completion_status == 'completed')
    in_progress = sum(1 for i in instances if i.completion_status == 'in_progress')
    partial = sum(1 for i in instances if i.completion_status == 'partial')
    pending = sum(1 for i in instances if i.completion_status == 'pending')
    skipped = sum(1 for i in instances if i.completion_status in ('skipped', 'na'))
    
    required_mins = sum(i.kra_template.estimated_time_minutes or 0 for i in instances if i.kra_template)
    completed_mins = sum(i.time_spent_minutes or 0 for i in instances)
    
    items = []
    for i in instances:
        items.append({
            "id": i.id,
            "source_id": i.id,
            "title": i.kra_template.title if i.kra_template else f"KRA #{i.kra_template_id}",
            "code": i.kra_template.kra_code if i.kra_template else None,
            "status": i.completion_status,
            "completion_percentage": i.completion_percentage,
            "time_spent_minutes": i.time_spent_minutes or 0,
            "required_minutes": i.kra_template.estimated_time_minutes if i.kra_template else 0,
            "updated_at": i.updated_at.isoformat() if i.updated_at else None,
        })
    
    return {
        "total": total, "completed": completed, "in_progress": in_progress + partial,
        "pending": pending, "skipped": skipped,
        "required_minutes": required_mins, "completed_minutes": completed_mins,
        "items": items
    }


def _get_task_counts(db: Session, employee_id: int, target_date: date) -> dict:
    """Get task counts assigned to employee: total/completed/in_progress/pending"""
    from app.models.staff_tasks import StaffTask, StaffTaskAssignee
    
    primary_tasks = db.query(StaffTask).filter(
        StaffTask.primary_assignee_id == employee_id,
        StaffTask.is_deleted == False,
        or_(
            StaffTask.due_date == target_date,
            and_(StaffTask.due_date >= target_date, StaffTask.created_at <= datetime.combine(target_date, datetime.max.time())),
            StaffTask.status.in_(['in_progress', 'on_hold', 'under_review'])
        )
    ).all()
    
    primary_ids = {t.id for t in primary_tasks}
    
    secondary_ids_q = db.query(StaffTaskAssignee.task_id).filter(
        StaffTaskAssignee.employee_id == employee_id
    ).all()
    secondary_ids = {r.task_id for r in secondary_ids_q} - primary_ids
    
    secondary_tasks = []
    if secondary_ids:
        secondary_tasks = db.query(StaffTask).filter(
            StaffTask.id.in_(secondary_ids),
            StaffTask.is_deleted == False,
            or_(
                StaffTask.due_date == target_date,
                StaffTask.status.in_(['in_progress', 'on_hold', 'under_review'])
            )
        ).all()
    
    all_tasks = primary_tasks + secondary_tasks
    total = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.status == 'completed')
    in_progress = sum(1 for t in all_tasks if t.status in ('in_progress', 'on_hold', 'under_review'))
    pending = sum(1 for t in all_tasks if t.status == 'pending')
    
    items = []
    for t in all_tasks:
        items.append({
            "id": t.id,
            "source_id": t.id,
            "title": t.title,
            "code": t.task_code,
            "status": t.status,
            "priority": t.priority,
            "progress": t.progress,
            "category": t.category,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "estimated_hours": t.estimated_hours,
            "required_minutes": int((t.estimated_hours or 0) * 60),
        })
    
    required_mins = sum(int((t.estimated_hours or 0) * 60) for t in all_tasks)
    
    return {
        "total": total, "completed": completed, "in_progress": in_progress,
        "pending": pending, "skipped": 0,
        "required_minutes": required_mins, "completed_minutes": 0,
        "items": items
    }


def _get_dayplan_counts(db: Session, employee_id: int, target_date: date) -> dict:
    """Get day plan item counts for date"""
    from app.models.staff_tasks import StaffDayPlan, StaffDayPlanItem
    
    plan = db.query(StaffDayPlan).filter(
        StaffDayPlan.employee_id == employee_id,
        StaffDayPlan.plan_date == target_date
    ).first()
    
    if not plan:
        return {
            "total": 0, "completed": 0, "in_progress": 0, "pending": 0, "skipped": 0,
            "required_minutes": 0, "completed_minutes": 0, "items": []
        }
    
    items_list = plan.items or []
    total = len(items_list)
    completed = sum(1 for i in items_list if (i.eod_status or i.planned_status) == 'completed')
    in_progress = sum(1 for i in items_list if (i.eod_status or i.planned_status) == 'in_progress')
    pending = total - completed - in_progress
    completed_mins = sum(i.time_spent_minutes or 0 for i in items_list)
    
    items = []
    for i in items_list:
        items.append({
            "id": i.id,
            "source_id": i.id,
            "title": i.task.title if i.task else f"Item #{i.id}",
            "code": i.task.task_code if i.task else None,
            "status": i.eod_status or i.planned_status or 'pending',
            "progress": i.eod_progress,
            "time_spent_minutes": i.time_spent_minutes or 0,
            "priority_order": i.priority_order,
        })
    
    return {
        "total": total, "completed": completed, "in_progress": in_progress,
        "pending": pending, "skipped": 0,
        "required_minutes": 0, "completed_minutes": completed_mins,
        "items": items
    }


def _get_journey_counts(db: Session, employee_id: int, target_date: date) -> dict:
    """Get journey counts for date (auto-calculated from system)"""
    from app.models.staff_journey import StaffJourney
    
    journeys = db.query(StaffJourney).filter(
        StaffJourney.employee_id == employee_id,
        func.date(StaffJourney.start_time) == target_date
    ).all()
    
    total = len(journeys)
    def _jstatus(j):
        return j.status.value if hasattr(j.status, 'value') else str(j.status)
    completed = sum(1 for j in journeys if _jstatus(j) == 'completed')
    in_progress = sum(1 for j in journeys if _jstatus(j) == 'in_progress')
    pending = total - completed - in_progress
    
    completed_mins = 0
    items = []
    for j in journeys:
        duration = j.calculate_duration() if hasattr(j, 'calculate_duration') else 0
        completed_mins += duration or 0
        status_val = j.status.value if hasattr(j.status, 'value') else str(j.status)
        items.append({
            "id": j.id,
            "source_id": j.id,
            "title": j.purpose.value if hasattr(j.purpose, 'value') else str(j.purpose or ''),
            "code": None,
            "status": status_val,
            "duration_minutes": duration or 0,
            "distance_km": round(float(j.total_distance_km or 0), 2) if j.total_distance_km else 0,
            "start_time": j.start_time.isoformat() if j.start_time else None,
            "end_time": j.end_time.isoformat() if j.end_time else None,
        })
    
    return {
        "total": total, "completed": completed, "in_progress": in_progress,
        "pending": pending, "skipped": 0,
        "required_minutes": 0, "completed_minutes": completed_mins,
        "items": items
    }


def _get_lead_counts(db: Session, employee_id: int, target_date: date) -> dict:
    """Get CRM lead activity counts for the date — shows ALL active leads, not date-filtered."""
    from app.models.crm import CRMLead
    from app.models.staff import StaffEmployee
    
    emp = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not emp:
        return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "skipped": 0,
                "required_minutes": 0, "completed_minutes": 0, "items": []}
    
    emp_id_str = str(employee_id)
    leads = db.query(CRMLead).filter(
        or_(
            CRMLead.handler_id == emp_id_str,
            CRMLead.telecaller_id == employee_id,
            CRMLead.field_staff_id == employee_id,
        ),
        CRMLead.status.notin_(['lost', 'closed_won', 'closed_lost', 'duplicate'])
    ).limit(50).all()
    
    total = len(leads)
    completed = sum(1 for l in leads if l.status in ('won', 'closed_won', 'converted'))
    hot = sum(1 for l in leads if l.status == 'hot')
    pending = sum(1 for l in leads if l.status in ('new', 'contacted', 'warm'))
    in_progress = total - completed - pending
    
    items = []
    for l in leads:
        items.append({
            "id": l.id,
            "source_id": l.id,
            "title": l.name,
            "code": None,
            "status": l.status,
            "priority": l.priority,
            "category": l.category_id,
            "phone": l.phone,
            "company_id": l.company_id,
            "tat_due_at": l.next_followup_date.isoformat() if l.next_followup_date else None,
        })
    
    return {
        "total": total, "completed": completed, "in_progress": in_progress,
        "pending": pending, "skipped": 0,
        "required_minutes": 0, "completed_minutes": 0,
        "items": items
    }


def _get_overdue_lead_counts(db: Session, employee_id: int) -> dict:
    """Get overdue CRM leads: past TAT, not closed — cross-date, not restricted to selected day."""
    from app.models.crm import CRMLead
    from app.models.staff import StaffEmployee

    emp = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not emp:
        return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "skipped": 0,
                "required_minutes": 0, "completed_minutes": 0, "items": []}

    today = get_indian_date()
    emp_id_str = str(employee_id)
    leads = db.query(CRMLead).filter(
        or_(
            CRMLead.handler_id == emp_id_str,
            CRMLead.telecaller_id == employee_id,
            CRMLead.field_staff_id == employee_id,
        ),
        CRMLead.next_followup_date.isnot(None),
        CRMLead.next_followup_date < today,
        CRMLead.status.notin_(['won', 'lost', 'dropped', 'closed_won', 'closed_lost', 'converted', 'duplicate'])
    ).limit(50).all()

    total = len(leads)
    items = []
    for l in leads:
        items.append({
            "id": l.id,
            "source_id": l.id,
            "title": l.name,
            "code": None,
            "status": l.status,
            "priority": l.priority,
            "phone": l.phone,
            "company_id": l.company_id,
            "tat_due_at": l.next_followup_date.isoformat() if l.next_followup_date else None,
        })

    return {
        "total": total, "completed": 0, "in_progress": 0,
        "pending": total, "skipped": 0,
        "required_minutes": 0, "completed_minutes": 0,
        "items": items
    }


def _get_ticket_counts(db: Session, employee_id: int, target_date: date) -> dict:
    """Get service ticket counts assigned to employee"""
    from app.models.ticket import ServiceTicket
    
    tickets = db.query(ServiceTicket).filter(
        or_(
            ServiceTicket.service_manager_id == employee_id,
            ServiceTicket.service_technician_id == employee_id,
        ),
        ServiceTicket.status.notin_(['Closed', 'Cancelled'])
    ).limit(50).all()
    
    total = len(tickets)
    completed = sum(1 for t in tickets if t.status == 'Resolved')
    in_progress = sum(1 for t in tickets if t.status == 'In Progress')
    pending = sum(1 for t in tickets if t.status in ('Open', 'Assigned'))
    
    items = []
    for t in tickets:
        items.append({
            "id": t.id,
            "source_id": t.id,
            "title": t.issue_category,
            "code": t.ticket_id,
            "status": t.status,
            "sub_status": t.sub_status or 'new',
            "priority": t.priority,
            "ticket_str_id": t.ticket_id,
        })
    
    return {
        "total": total, "completed": completed, "in_progress": in_progress,
        "pending": pending, "skipped": 0,
        "required_minutes": 0, "completed_minutes": 0,
        "items": items
    }


def sync_source_to_activity_log(db: Session, employee_id: int, target_date: date):
    """
    Auto-sync source system time entries into StaffActivityTimeLog.
    DC Protocol: Idempotent - only creates entries that don't exist yet (by source_type + source_id + date).
    Creates log entries from KRA instances, tasks, day plan items etc. that have time > 0.
    """
    existing = db.query(
        StaffActivityTimeLog.source_type,
        StaffActivityTimeLog.source_id
    ).filter(
        StaffActivityTimeLog.employee_id == employee_id,
        StaffActivityTimeLog.date == target_date,
        StaffActivityTimeLog.source_id.isnot(None)
    ).all()
    existing_keys = {(r.source_type, r.source_id) for r in existing}

    synced = 0
    attendance = upsert_attendance(db, employee_id, target_date)
    att_id = attendance.id if attendance else None

    from app.models.staff_kra import StaffKRADailyInstance
    kra_instances = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.employee_id == employee_id,
        StaffKRADailyInstance.instance_date == target_date
    ).all()
    for inst in kra_instances:
        mins = inst.time_spent_minutes or 0
        if mins <= 0:
            continue
        if ('kra', inst.id) in existing_keys:
            continue
        entry = StaffActivityTimeLog(
            employee_id=employee_id, date=target_date,
            source_type='kra', source_id=inst.id,
            source_title=inst.kra_template.title if inst.kra_template else f"KRA #{inst.kra_template_id}",
            source_code=inst.kra_template.kra_code if inst.kra_template else None,
            required_minutes=inst.kra_template.estimated_time_minutes if inst.kra_template else 0,
            completed_minutes=mins, attendance_id=att_id,
            created_by=employee_id
        )
        db.add(entry)
        synced += 1

    from app.models.staff_tasks import StaffTask, StaffTaskAssignee, StaffDayPlan, StaffDayPlanItem
    primary_tasks = db.query(StaffTask).filter(
        StaffTask.primary_assignee_id == employee_id,
        StaffTask.is_deleted == False,
        StaffTask.status == 'completed',
        or_(
            StaffTask.due_date == target_date,
            and_(StaffTask.completed_at.isnot(None),
                 func.date(StaffTask.completed_at) == target_date)
        )
    ).all()
    for t in primary_tasks:
        hrs = t.estimated_hours or 0
        mins = int(hrs * 60)
        if mins <= 0:
            continue
        if ('task', t.id) in existing_keys:
            continue
        entry = StaffActivityTimeLog(
            employee_id=employee_id, date=target_date,
            source_type='task', source_id=t.id,
            source_title=t.title, source_code=t.task_code,
            required_minutes=mins, completed_minutes=mins,
            attendance_id=att_id, created_by=employee_id
        )
        db.add(entry)
        synced += 1

    plan = db.query(StaffDayPlan).filter(
        StaffDayPlan.employee_id == employee_id,
        StaffDayPlan.plan_date == target_date
    ).first()
    if plan:
        for item in (plan.items or []):
            mins = item.time_spent_minutes or 0
            if mins <= 0:
                continue
            status = item.eod_status or item.planned_status
            if status != 'completed':
                continue
            if ('dayplan', item.id) in existing_keys:
                continue
            item_title = 'Day Plan Item'
            if hasattr(item, 'task') and item.task:
                item_title = item.task.title or item_title
            entry = StaffActivityTimeLog(
                employee_id=employee_id, date=target_date,
                source_type='dayplan', source_id=item.id,
                source_title=item_title,
                required_minutes=0,
                completed_minutes=mins, attendance_id=att_id,
                created_by=employee_id
            )
            db.add(entry)
            synced += 1

    if synced > 0:
        db.flush()
        recalculate_attendance_activity(db, employee_id, target_date)

    return synced


def _detect_dept_type(db: Session, department_ids: list) -> str:
    """Detect department type from department IDs. Returns 'sales'|'service'|'procurement'|'other'."""
    if not department_ids:
        return 'other'
    try:
        from app.models.staff import StaffDepartment
        depts = db.query(StaffDepartment).filter(StaffDepartment.id.in_(department_ids)).all()
        for d in depts:
            n = (d.name or '').lower()
            if 'sales' in n or 'crm' in n:
                return 'sales'
            if 'service' in n:
                return 'service'
            if 'procurement' in n or 'purchase' in n:
                return 'procurement'
    except Exception:
        pass
    return 'other'


def get_daily_activity_summary(db: Session, employee_id: int, target_date: date, department_ids: list = None) -> dict:
    """
    Get category-wise activity summary for timesheet page.
    Returns Total/Planned/Completed/Pending counts (like Task Planner tabs)
    plus Required Time/Planned Time/Completed Time + Approved Time per category.
    
    Auto-syncs source system time into activity log before computing.
    dept_type is returned so frontend can render overdue/dept-specific rows.
    """
    sync_source_to_activity_log(db, employee_id, target_date)

    dept_type = _detect_dept_type(db, department_ids)

    time_entries = db.query(StaffActivityTimeLog).filter(
        StaffActivityTimeLog.employee_id == employee_id,
        StaffActivityTimeLog.date == target_date
    ).order_by(StaffActivityTimeLog.created_at.desc()).all()
    
    time_by_source = {}
    for entry in time_entries:
        st = entry.source_type
        if st not in time_by_source:
            time_by_source[st] = {"required_minutes": 0, "planned_minutes": 0, "completed_minutes": 0, "approved_minutes": 0, "pending_count": 0, "approved_count": 0, "rejected_count": 0, "entries": []}
        time_by_source[st]["required_minutes"] += entry.required_minutes or 0
        time_by_source[st]["planned_minutes"] += entry.planned_minutes or 0
        time_by_source[st]["completed_minutes"] += entry.completed_minutes
        status = entry.approval_status or 'submitted'
        if status == 'approved' and entry.approved_minutes is not None:
            time_by_source[st]["approved_minutes"] += entry.approved_minutes
            time_by_source[st]["approved_count"] += 1
        elif status == 'rejected':
            time_by_source[st]["rejected_count"] += 1
        else:
            time_by_source[st]["pending_count"] += 1
        time_by_source[st]["entries"].append(entry.to_dict())
    
    kra_data = _get_kra_counts(db, employee_id, target_date)
    task_data = _get_task_counts(db, employee_id, target_date)
    dayplan_data = _get_dayplan_counts(db, employee_id, target_date)
    journey_data = _get_journey_counts(db, employee_id, target_date)
    
    lead_data = _get_lead_counts(db, employee_id, target_date)
    ticket_data = _get_ticket_counts(db, employee_id, target_date)
    
    all_categories = [
        _build_category('kra', 'KRA Activities', kra_data, time_by_source.get('kra')),
        _build_category('task', 'Tasks', task_data, time_by_source.get('task')),
        _build_category('dayplan', 'Task Planner', dayplan_data, time_by_source.get('dayplan')),
        _build_category('journey', 'Journeys', journey_data, time_by_source.get('journey')),
        _build_category('lead', 'Leads / CRM', lead_data, time_by_source.get('lead')),
        _build_category('ticket', 'Service Tickets', ticket_data, time_by_source.get('ticket')),
    ]

    if dept_type == 'sales':
        overdue_data = _get_overdue_lead_counts(db, employee_id)
        all_categories.append(_build_category('overdue_leads', 'Overdue Follow-ups', overdue_data, None))
    
    custom_time = time_by_source.get('custom')
    custom_count = len(custom_time["entries"]) if custom_time else 0
    all_categories.append({
        "source_type": "custom",
        "label": "Custom / Other",
        "total": custom_count,
        "planned": 0,
        "completed": custom_count,
        "in_progress": 0,
        "pending": 0,
        "skipped": 0,
        "required_minutes": custom_time["required_minutes"] if custom_time else 0,
        "planned_minutes": custom_time["planned_minutes"] if custom_time else 0,
        "completed_minutes": custom_time["completed_minutes"] if custom_time else 0,
        "approved_minutes": custom_time["approved_minutes"] if custom_time else 0,
        "pending_count": custom_time["pending_count"] if custom_time else 0,
        "approved_count": custom_time["approved_count"] if custom_time else 0,
        "rejected_count": custom_time["rejected_count"] if custom_time else 0,
        "time_entries": custom_time["entries"] if custom_time else [],
        "items": [],
    })
    
    for st, tdata in time_by_source.items():
        if st not in [c["source_type"] for c in all_categories]:
            all_categories.append({
                "source_type": st,
                "label": _get_source_label(st),
                "total": len(tdata["entries"]),
                "planned": 0,
                "completed": len(tdata["entries"]),
                "in_progress": 0,
                "pending": 0,
                "skipped": 0,
                "required_minutes": tdata["required_minutes"],
                "planned_minutes": tdata["planned_minutes"],
                "completed_minutes": tdata["completed_minutes"],
                "approved_minutes": tdata["approved_minutes"],
                "pending_count": tdata["pending_count"],
                "approved_count": tdata["approved_count"],
                "rejected_count": tdata["rejected_count"],
                "time_entries": tdata["entries"],
                "items": [],
            })
    
    totals = {
        "total": sum(c["total"] for c in all_categories),
        "planned": sum(c.get("planned", c["total"]) for c in all_categories),
        "completed": sum(c["completed"] for c in all_categories),
        "in_progress": sum(c["in_progress"] for c in all_categories),
        "pending": sum(c["pending"] for c in all_categories),
        "required_minutes": sum(c["required_minutes"] for c in all_categories),
        "planned_minutes": sum(c["planned_minutes"] for c in all_categories),
        "completed_minutes": sum(c["completed_minutes"] for c in all_categories),
        "approved_minutes": sum(c.get("approved_minutes", 0) for c in all_categories),
        "pending_count": sum(c.get("pending_count", 0) for c in all_categories),
        "approved_count": sum(c.get("approved_count", 0) for c in all_categories),
        "rejected_count": sum(c.get("rejected_count", 0) for c in all_categories),
    }
    
    return {
        "date": target_date.isoformat(),
        "employee_id": employee_id,
        "dept_type": dept_type,
        "categories": all_categories,
        "totals": totals
    }


def _build_category(source_type: str, label: str, source_data: dict, time_data: dict = None) -> dict:
    """
    Build a category entry merging source system counts with activity time log data.
    source_data: from _get_kra_counts, _get_task_counts, etc. (Total/Completed/InProgress/Pending + items)
    time_data: from activity time log (required/planned/completed/approved minutes + entries)
    """
    completed_mins_from_source = source_data.get("completed_minutes", 0)
    completed_mins_from_log = time_data["completed_minutes"] if time_data else 0
    final_completed_mins = max(completed_mins_from_source, completed_mins_from_log)
    
    return {
        "source_type": source_type,
        "label": label,
        "total": source_data["total"],
        "planned": source_data["total"],
        "completed": source_data["completed"],
        "in_progress": source_data["in_progress"],
        "pending": source_data["pending"],
        "skipped": source_data.get("skipped", 0),
        "required_minutes": source_data.get("required_minutes", 0),
        "planned_minutes": time_data["planned_minutes"] if time_data else 0,
        "completed_minutes": final_completed_mins,
        "approved_minutes": time_data["approved_minutes"] if time_data else 0,
        "pending_count": time_data["pending_count"] if time_data else 0,
        "approved_count": time_data["approved_count"] if time_data else 0,
        "rejected_count": time_data["rejected_count"] if time_data else 0,
        "time_entries": time_data["entries"] if time_data else [],
        "items": source_data.get("items", []),
    }


def get_activity_detail(db: Session, employee_id: int, target_date: date, source_type: str) -> dict:
    """
    Get detailed activity entries for a specific category on a date.
    Returns both source system items and time log entries.
    Auto-syncs source time before fetching.
    overdue_leads: cross-date query (not restricted to target_date).
    Time entries for overdue_leads use source_type='lead' since they are leads.
    """
    sync_source_to_activity_log(db, employee_id, target_date)

    log_source_type = 'lead' if source_type == 'overdue_leads' else source_type
    time_entries = db.query(StaffActivityTimeLog).filter(
        StaffActivityTimeLog.employee_id == employee_id,
        StaffActivityTimeLog.date == target_date,
        StaffActivityTimeLog.source_type == log_source_type
    ).order_by(StaffActivityTimeLog.created_at.desc()).all()
    
    source_items = []
    if source_type == 'kra':
        source_items = _get_kra_counts(db, employee_id, target_date).get("items", [])
    elif source_type == 'task':
        source_items = _get_task_counts(db, employee_id, target_date).get("items", [])
    elif source_type == 'dayplan':
        source_items = _get_dayplan_counts(db, employee_id, target_date).get("items", [])
    elif source_type == 'journey':
        source_items = _get_journey_counts(db, employee_id, target_date).get("items", [])
    elif source_type in ('lead', 'overdue_leads'):
        if source_type == 'overdue_leads':
            source_items = _get_overdue_lead_counts(db, employee_id).get("items", [])
        else:
            source_items = _get_lead_counts(db, employee_id, target_date).get("items", [])
        # Batch-fetch call durations per lead for target_date (single query — no N+1)
        lead_ids = [item["id"] for item in source_items if item.get("id")]
        if lead_ids:
            from app.models.call_tracking import StaffCallLog
            call_rows = db.query(
                StaffCallLog.matched_lead_id,
                func.sum(StaffCallLog.duration_seconds).label("total_secs")
            ).filter(
                StaffCallLog.staff_id == employee_id,
                StaffCallLog.call_date == target_date.isoformat(),
                StaffCallLog.matched_lead_id.in_(lead_ids)
            ).group_by(StaffCallLog.matched_lead_id).all()
            call_map = {row.matched_lead_id: int(row.total_secs or 0) for row in call_rows}
        else:
            call_map = {}
        for item in source_items:
            secs = call_map.get(item.get("id"), 0)
            mins = secs // 60
            rem_secs = secs % 60
            item["call_time_seconds"] = secs
            item["call_time_minutes"] = mins
            item["call_time_formatted"] = f"{mins}m {rem_secs}s" if secs > 0 else ""
    elif source_type == 'ticket':
        source_items = _get_ticket_counts(db, employee_id, target_date).get("items", [])
    
    return {
        "source_type": source_type,
        "label": _get_source_label(source_type),
        "date": target_date.isoformat(),
        "source_items": source_items,
        "time_entries": [e.to_dict() for e in time_entries],
        "total_completed_minutes": sum(e.completed_minutes for e in time_entries)
    }


def get_activity_history(db: Session, employee_id: int, source_type: str, days: int = 7) -> list:
    """
    Get historical activity entries for a category over N days.
    """
    today = get_indian_date()
    start_date = today - timedelta(days=days)
    
    entries = db.query(StaffActivityTimeLog).filter(
        StaffActivityTimeLog.employee_id == employee_id,
        StaffActivityTimeLog.source_type == source_type,
        StaffActivityTimeLog.date >= start_date,
        StaffActivityTimeLog.date <= today
    ).order_by(StaffActivityTimeLog.date.desc(), StaffActivityTimeLog.created_at.desc()).all()
    
    date_groups = {}
    for e in entries:
        d = e.date.isoformat()
        if d not in date_groups:
            date_groups[d] = {"date": d, "entries": [], "total_minutes": 0}
        date_groups[d]["entries"].append(e.to_dict())
        date_groups[d]["total_minutes"] += e.completed_minutes
    
    return list(date_groups.values())


def _get_source_label(source_type: str) -> str:
    labels = {
        'kra': 'KRA Activities',
        'task': 'Tasks',
        'dayplan': 'Task Planner',
        'lead': 'Leads / CRM',
        'ticket': 'Service Tickets',
        'journey': 'Journeys',
        'custom': 'Custom / Other',
        'overdue_leads': 'Overdue Follow-ups',
    }
    return labels.get(source_type, source_type.title())
