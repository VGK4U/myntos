from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, case
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
from typing import Optional, List
import pytz

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.staff_tasks import (
    StaffTask, StaffTaskPhase, StaffTaskAssignee,
    StaffDayPlan, StaffDayPlanItem,
    log_task_activity, get_indian_time
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter()


def get_indian_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def _compute_days_pending(created_at):
    if not created_at:
        return 0
    today = get_indian_date()
    if hasattr(created_at, 'date'):
        created_date = created_at.date()
    else:
        created_date = created_at
    return max(0, (today - created_date).days)


def _get_times_planned_counts(db, task_ids=None, phase_ids=None):
    task_counts = {}
    phase_counts = {}
    if task_ids:
        rows = db.query(
            StaffDayPlanItem.task_id,
            func.count(func.distinct(StaffDayPlan.plan_date))
        ).join(StaffDayPlan, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
        ).filter(
            StaffDayPlanItem.task_id.in_(task_ids),
            StaffDayPlanItem.item_type == 'task'
        ).group_by(StaffDayPlanItem.task_id).all()
        task_counts = {r[0]: r[1] for r in rows}
    if phase_ids:
        rows = db.query(
            StaffDayPlanItem.phase_id,
            func.count(func.distinct(StaffDayPlan.plan_date))
        ).join(StaffDayPlan, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
        ).filter(
            StaffDayPlanItem.phase_id.in_(phase_ids),
            StaffDayPlanItem.item_type == 'phase'
        ).group_by(StaffDayPlanItem.phase_id).all()
        phase_counts = {r[0]: r[1] for r in rows}
    return task_counts, phase_counts


def _recalc_plan_stats(plan):
    items = plan.items or []
    plan.total_planned = len(items)
    plan.total_completed = sum(1 for i in items if (i.eod_status or i.planned_status) == 'completed')
    plan.total_in_progress = sum(1 for i in items if (i.eod_status or i.planned_status) == 'in_progress')
    plan.total_pending = plan.total_planned - plan.total_completed - plan.total_in_progress


@router.get("/today", summary="Get today's day plan for current user")
def get_today_plan(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    today = get_indian_date()
    plan = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.primary_assignee),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.creator),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.phase),
    ).filter(
        StaffDayPlan.employee_id == current_user.id,
        StaffDayPlan.plan_date == today
    ).first()

    plan_data = plan.to_dict() if plan else None
    if plan_data and plan_data.get("items"):
        task_ids = [i["task_id"] for i in plan_data["items"] if i.get("item_type") == "task" and i.get("task_id")]
        phase_ids = [i["phase_id"] for i in plan_data["items"] if i.get("item_type") == "phase" and i.get("phase_id")]
        task_counts, phase_counts = _get_times_planned_counts(db, task_ids or None, phase_ids or None)
        task_dates = {}
        phase_dates = {}
        if task_ids:
            rows = db.query(StaffTask.id, StaffTask.created_at).filter(StaffTask.id.in_(task_ids)).all()
            task_dates = {r[0]: r[1] for r in rows}
        if phase_ids:
            rows = db.query(StaffTaskPhase.id, StaffTaskPhase.created_at).filter(StaffTaskPhase.id.in_(phase_ids)).all()
            phase_dates = {r[0]: r[1] for r in rows}
        for item in plan_data["items"]:
            if item.get("item_type") == "phase" and item.get("phase_id"):
                item["days_pending"] = _compute_days_pending(phase_dates.get(item["phase_id"]))
                item["times_planned"] = phase_counts.get(item["phase_id"], 0)
            else:
                item["days_pending"] = _compute_days_pending(task_dates.get(item.get("task_id")))
                item["times_planned"] = task_counts.get(item.get("task_id"), 0)

    return {"plan": plan_data, "plan_date": today.isoformat()}


@router.get("/by-date", summary="Get day plan by specific date")
def get_plan_by_date(
    plan_date: str,
    employee_id: Optional[int] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    try:
        target_date = date.fromisoformat(plan_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    target_emp_id = employee_id if employee_id else current_user.id

    if employee_id and employee_id != current_user.id:
        if not _is_admin_user(current_user):
            from app.utils.staff_hierarchy import get_recursive_downline
            downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=False)
            if employee_id not in downline_ids:
                raise HTTPException(status_code=403, detail="You can only view day plans of your downline team members")

    plan = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.primary_assignee),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.creator),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.phase),
    ).filter(
        StaffDayPlan.employee_id == target_emp_id,
        StaffDayPlan.plan_date == target_date
    ).first()

    plan_data = plan.to_dict() if plan else None
    if plan_data and plan_data.get("items"):
        task_ids = [i["task_id"] for i in plan_data["items"] if i.get("item_type") == "task" and i.get("task_id")]
        phase_ids = [i["phase_id"] for i in plan_data["items"] if i.get("item_type") == "phase" and i.get("phase_id")]
        task_counts, phase_counts = _get_times_planned_counts(db, task_ids or None, phase_ids or None)
        task_dates = {}
        phase_dates = {}
        if task_ids:
            rows = db.query(StaffTask.id, StaffTask.created_at).filter(StaffTask.id.in_(task_ids)).all()
            task_dates = {r[0]: r[1] for r in rows}
        if phase_ids:
            rows = db.query(StaffTaskPhase.id, StaffTaskPhase.created_at).filter(StaffTaskPhase.id.in_(phase_ids)).all()
            phase_dates = {r[0]: r[1] for r in rows}
        for item in plan_data["items"]:
            if item.get("item_type") == "phase" and item.get("phase_id"):
                item["days_pending"] = _compute_days_pending(phase_dates.get(item["phase_id"]))
                item["times_planned"] = phase_counts.get(item["phase_id"], 0)
            else:
                item["days_pending"] = _compute_days_pending(task_dates.get(item.get("task_id")))
                item["times_planned"] = task_counts.get(item.get("task_id"), 0)

    return {"plan": plan_data, "plan_date": target_date.isoformat()}


@router.get("/available-tasks", summary="Get all tasks/phases available for day planning")
def get_available_tasks(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(StaffTask).options(
        joinedload(StaffTask.primary_assignee),
        joinedload(StaffTask.creator),
        joinedload(StaffTask.phases).joinedload(StaffTaskPhase.assignee),
    ).filter(
        StaffTask.is_deleted == False,
        StaffTask.status.in_(['pending', 'in_progress', 'on_hold', 'under_review']),
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(
                db.query(StaffTaskAssignee.task_id).filter(
                    StaffTaskAssignee.employee_id == current_user.id
                )
            )
        )
    ).order_by(StaffTask.priority.desc(), StaffTask.due_date.asc()).all()

    all_task_ids = [t.id for t in tasks]
    all_phase_ids = []
    for task in tasks:
        active_phases = [p for p in (task.phases or []) if not p.is_deleted and p.phase_status in ('pending', 'in_progress', 'on_hold')]
        all_phase_ids.extend([p.id for p in active_phases])

    task_counts, phase_counts = _get_times_planned_counts(
        db, all_task_ids or None, all_phase_ids or None
    )

    result = []
    for task in tasks:
        task_data = {
            "id": task.id,
            "task_code": task.task_code,
            "title": task.title,
            "description": task.description,
            "category": task.category,
            "priority": task.priority,
            "status": task.status,
            "progress": task.progress,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "days_pending": _compute_days_pending(task.created_at),
            "times_planned": task_counts.get(task.id, 0),
            "assignee_name": task.primary_assignee.full_name if task.primary_assignee else None,
            "creator_name": task.creator.full_name if task.creator else None,
            "item_type": "task",
            "phases": []
        }
        active_phases = [p for p in (task.phases or []) if not p.is_deleted and p.phase_status in ('pending', 'in_progress', 'on_hold')]
        for phase in sorted(active_phases, key=lambda p: p.phase_number):
            task_data["phases"].append({
                "id": phase.id,
                "phase_number": phase.phase_number,
                "phase_title": phase.phase_title,
                "phase_status": phase.phase_status,
                "target_date": phase.target_date.isoformat() if phase.target_date else None,
                "created_at": phase.created_at.isoformat() if phase.created_at else None,
                "days_pending": _compute_days_pending(phase.created_at),
                "times_planned": phase_counts.get(phase.id, 0),
                "assignee_name": phase.assignee.full_name if phase.assignee else None,
                "task_id": task.id,
                "task_code": task.task_code,
                "task_title": task.title,
                "item_type": "phase"
            })
        result.append(task_data)

    return {"tasks": result, "total": len(result)}


@router.post("/", summary="Create or update day plan")
def create_or_update_plan(
    request: Request,
    data: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    plan_date_str = data.get("plan_date")
    items_data = data.get("items", [])
    notes = data.get("notes")
    append_mode = bool(data.get("append", False))

    if plan_date_str:
        try:
            target_date = date.fromisoformat(plan_date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = get_indian_date()

    plan = db.query(StaffDayPlan).filter(
        StaffDayPlan.employee_id == current_user.id,
        StaffDayPlan.plan_date == target_date
    ).first()

    if plan:
        if not append_mode:
            db.query(StaffDayPlanItem).filter(StaffDayPlanItem.day_plan_id == plan.id).delete()
        if notes is not None:
            plan.notes = notes
    else:
        plan = StaffDayPlan(
            employee_id=current_user.id,
            plan_date=target_date,
            notes=notes
        )
        db.add(plan)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            # DC_P6: Concurrent request already inserted this plan — re-fetch and continue
            plan = db.query(StaffDayPlan).filter(
                StaffDayPlan.employee_id == current_user.id,
                StaffDayPlan.plan_date == target_date
            ).first()
            if not plan:
                raise

    existing_keys: set = set()
    if append_mode and plan.id:
        for ei in db.query(StaffDayPlanItem).filter(StaffDayPlanItem.day_plan_id == plan.id).all():
            existing_keys.add((ei.task_id, ei.phase_id if ei.item_type == "phase" else None))

    seen_keys: set = set()
    for idx, item in enumerate(items_data):
        task_id = item.get("task_id")
        phase_id = item.get("phase_id")
        item_type = item.get("item_type", "task")
        priority = item.get("priority_order", idx + 1)

        dedup_key = (task_id, phase_id if item_type == "phase" else None)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if append_mode and dedup_key in existing_keys:
            continue

        task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
        if not task:
            continue

        if item_type == "phase" and phase_id:
            phase = db.query(StaffTaskPhase).filter(StaffTaskPhase.id == phase_id).first()
            if not phase:
                continue

        plan_item = StaffDayPlanItem(
            day_plan_id=plan.id,
            item_type=item_type,
            task_id=task_id,
            phase_id=phase_id if item_type == "phase" else None,
            priority_order=priority,
            planned_status=item.get("planned_status", task.status),
            is_carried_forward=item.get("is_carried_forward", False),
            carried_from_date=date.fromisoformat(item["carried_from_date"]) if item.get("carried_from_date") else None
        )
        db.add(plan_item)

    db.flush()

    plan = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.primary_assignee),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.creator),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.phase),
    ).filter(StaffDayPlan.id == plan.id).first()

    _recalc_plan_stats(plan)
    db.commit()

    return {"plan": plan.to_dict(), "message": "Day plan saved successfully"}


@router.patch("/items/{item_id}", summary="Update single day plan item status/progress")
def update_plan_item(
    item_id: int,
    data: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    item = db.query(StaffDayPlanItem).options(
        joinedload(StaffDayPlanItem.day_plan)
    ).filter(StaffDayPlanItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Plan item not found")
    if item.day_plan.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own day plan items")

    if "eod_status" in data:
        item.eod_status = data["eod_status"]
    if "eod_progress" in data:
        item.eod_progress = data["eod_progress"]
    if "eod_notes" in data:
        item.eod_notes = data["eod_notes"]
    if "priority_order" in data:
        item.priority_order = data["priority_order"]
    if "time_spent_minutes" in data and data["time_spent_minutes"]:
        time_val = int(data["time_spent_minutes"])
        if 1 <= time_val <= 1440:
            item.time_spent_minutes = time_val

    # DC Protocol: propagate eod_status back to the source task/phase so that
    # available-tasks and carried-forward queries stay consistent.
    # (Without this, completed tasks reappear in available-tasks the next day.)
    if "eod_status" in data and data["eod_status"]:
        _new_status = data["eod_status"]
        _notes = data.get("eod_notes")
        if item.item_type == "task" and item.task_id:
            _task = db.query(StaffTask).filter(StaffTask.id == item.task_id).first()
            if _task and _new_status != _task.status:
                _old = _task.status
                _task.status = _new_status
                if _new_status == "completed":
                    _task.completed_at = get_indian_time()
                    _task.completion_notes = _notes
                try:
                    log_task_activity(
                        db, _task.id, current_user.id, "status_change",
                        "status", _old, _new_status,
                        "Updated via Day Planner item status update",
                    )
                except Exception as _e:
                    print(f"[DC-WARN] log_task_activity failed for task {_task.id}: {_e}")
        elif item.item_type == "phase" and item.phase_id:
            _phase = db.query(StaffTaskPhase).filter(StaffTaskPhase.id == item.phase_id).first()
            _VALID_PHASE = {'pending', 'in_progress', 'on_hold', 'completed', 'cancelled'}
            _safe_new = _new_status if _new_status in _VALID_PHASE else (
                'in_progress' if _new_status == 'under_review' else _new_status
            )
            if _phase and _safe_new != _phase.phase_status and _safe_new in _VALID_PHASE:
                _old_ph = _phase.phase_status
                _phase.phase_status = _safe_new
                if _safe_new == "completed":
                    _phase.completed_at = get_indian_time()
                    _phase.completion_notes = _notes
                if _phase.parent_task_id:
                    try:
                        log_task_activity(
                            db, _phase.parent_task_id, current_user.id, "phase_status_change",
                            f"phase_{_phase.phase_number}_status", _old_ph, _new_status,
                            f"Phase '{_phase.phase_title}' updated via Day Planner item status update",
                        )
                    except Exception as _e:
                        print(f"[DC-WARN] log_task_activity failed for phase {_phase.id}: {_e}")

    _recalc_plan_stats(item.day_plan)
    
    if "time_spent_minutes" in data and data["time_spent_minutes"] and int(data["time_spent_minutes"]) >= 1:
        from app.services.activity_time_service import log_activity_time
        try:
            log_activity_time(
                db=db,
                employee_id=current_user.id,
                source_type='dayplan',
                completed_minutes=int(data["time_spent_minutes"]),
                target_date=item.day_plan.plan_date,
                source_id=item.id,
                source_title=getattr(item.task, 'title', None) or f"Day Plan Item #{item.id}",
                description=f"Day plan item update: {item.eod_status or 'in progress'}",
                created_by=current_user.id
            )
        except Exception as e:
            print(f"[DC-WARN] Activity time log failed for day plan item {item.id}: {e}")

        # DC Protocol (Mar 2026): Auto-capture task time into timesheet (task-wise, per item)
        try:
            from app.services.timesheet_auto_service import auto_upsert_timesheet_entry
            task_title = getattr(item.task, 'title', None) or f"Task #{item.task_id}"
            auto_upsert_timesheet_entry(
                db=db,
                employee_id=current_user.id,
                entry_date=item.day_plan.plan_date,
                time_spent_minutes=int(data["time_spent_minutes"]),
                entry_type='task',
                auto_source='day_plan',
                comments=f"[Auto from Day Plan] {task_title}",
                task_id=item.task_id,
                created_by=current_user.id,
            )
        except Exception as e:
            print(f"[DC-WARN] Auto timesheet entry failed for day plan item {item.id}: {e}")

    db.commit()

    return {"item": item.to_dict(), "message": "Item updated"}


@router.post("/finalize", summary="Finalize day plan and apply updates to original tasks/phases")
def finalize_plan(
    request: Request,
    data: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    plan_date_str = data.get("plan_date")
    item_updates = data.get("items", [])

    if plan_date_str:
        try:
            target_date = date.fromisoformat(plan_date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = get_indian_date()

    plan = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.items)
    ).filter(
        StaffDayPlan.employee_id == current_user.id,
        StaffDayPlan.plan_date == target_date
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="No day plan found for this date")

    client_ip = request.client.host if request.client else None
    updates_applied = 0

    for update in item_updates:
        item_id = update.get("item_id") or update.get("id")
        eod_status = update.get("eod_status")
        eod_progress = update.get("eod_progress")
        eod_notes = update.get("eod_notes")
        time_spent = update.get("time_spent_minutes")

        item = db.query(StaffDayPlanItem).filter(
            StaffDayPlanItem.id == item_id,
            StaffDayPlanItem.day_plan_id == plan.id
        ).first()
        if not item:
            continue

        item.eod_status = eod_status
        item.eod_progress = eod_progress
        item.eod_notes = eod_notes
        if time_spent and int(time_spent) >= 1 and int(time_spent) <= 1440:
            item.time_spent_minutes = int(time_spent)
            from app.services.activity_time_service import log_activity_time
            try:
                log_activity_time(
                    db=db,
                    employee_id=current_user.id,
                    source_type='dayplan',
                    completed_minutes=int(time_spent),
                    target_date=target_date,
                    source_id=item.id,
                    source_title=item.title or f"Day Plan Item #{item.id}",
                    description=f"Day plan finalize: {eod_status or 'finalized'}",
                    ip_address=client_ip,
                    created_by=current_user.id
                )
            except Exception as e:
                print(f"[DC-WARN] Activity time log failed for day plan finalize item {item.id}: {e}")

        if item.item_type == "task" and item.task_id:
            task = db.query(StaffTask).filter(StaffTask.id == item.task_id).first()
            if task:
                old_status = task.status
                if eod_status and eod_status != old_status:
                    task.status = eod_status
                    if eod_status == 'completed':
                        task.completed_at = get_indian_time()
                        task.completion_notes = eod_notes
                    try:
                        log_task_activity(
                            db, task.id, current_user.id, "status_change",
                            "status", old_status, eod_status,
                            "Updated via Day Planner EOD finalization",
                            ip_address=client_ip
                        )
                    except Exception as _e:
                        print(f"[DC-WARN] log_task_activity (status) failed for task {task.id}: {_e}")
                if eod_progress is not None:
                    old_progress = task.progress
                    task.progress = int(eod_progress)
                    if old_progress != eod_progress:
                        try:
                            log_task_activity(
                                db, task.id, current_user.id, "progress_update",
                                "progress", str(old_progress), str(eod_progress),
                                "Updated via Day Planner EOD finalization",
                                ip_address=client_ip
                            )
                        except Exception as _e:
                            print(f"[DC-WARN] log_task_activity (progress) failed for task {task.id}: {_e}")
                updates_applied += 1

        elif item.item_type == "phase" and item.phase_id:
            phase = db.query(StaffTaskPhase).filter(StaffTaskPhase.id == item.phase_id).first()
            if phase:
                old_phase_status = phase.phase_status
                VALID_PHASE_STATUSES = {'pending', 'in_progress', 'on_hold', 'completed', 'cancelled'}
                safe_phase_status = eod_status if eod_status in VALID_PHASE_STATUSES else (
                    'in_progress' if eod_status == 'under_review' else old_phase_status
                )
                if safe_phase_status and safe_phase_status != old_phase_status:
                    phase.phase_status = safe_phase_status
                    if safe_phase_status == 'completed':
                        phase.completed_at = get_indian_time()
                        phase.completion_notes = eod_notes
                    if phase.parent_task_id:
                        try:
                            log_task_activity(
                                db, phase.parent_task_id, current_user.id, "phase_status_change",
                                f"phase_{phase.phase_number}_status", old_phase_status, safe_phase_status,
                                f"Phase '{phase.phase_title}' updated via Day Planner EOD",
                                ip_address=client_ip
                            )
                        except Exception as _e:
                            print(f"[DC-WARN] log_task_activity (phase) failed for phase {phase.id}: {_e}")
                updates_applied += 1

    plan.status = "finalized"
    plan.finalized_at = get_indian_time()
    plan.finalized_by = current_user.id
    _recalc_plan_stats(plan)
    db.commit()

    plan = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.primary_assignee),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.creator),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.phase),
    ).filter(StaffDayPlan.id == plan.id).first()

    return {
        "plan": plan.to_dict(),
        "updates_applied": updates_applied,
        "message": f"Day plan finalized. {updates_applied} task/phase updates applied."
    }


@router.delete("/items/{item_id}", summary="Remove item from day plan")
def remove_plan_item(
    item_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    item = db.query(StaffDayPlanItem).options(
        joinedload(StaffDayPlanItem.day_plan)
    ).filter(StaffDayPlanItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Plan item not found")
    if item.day_plan.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only modify your own day plan")

    plan = item.day_plan
    db.delete(item)
    db.flush()
    _recalc_plan_stats(plan)
    db.commit()

    return {"message": "Item removed from day plan"}


def _is_admin_user(user):
    if getattr(user, 'staff_type', None) in ['VGK4U', 'VGK4U Supreme']:
        return True
    role = getattr(user, 'role', None)
    if role:
        if getattr(role, 'role_code', None) in ['hr', 'ea', 'key_leadership']:
            return True
        if getattr(role, 'hierarchy_level', 0) and role.hierarchy_level >= 100:
            return True
    return False


@router.get("/team", summary="Get team day plans for managers")
def get_team_day_plans(
    plan_date: Optional[str] = None,
    employee_id: Optional[int] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    if plan_date:
        try:
            target_date = date.fromisoformat(plan_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = get_indian_date()

    is_admin = _is_admin_user(current_user)

    reporting_manager_id_col = getattr(StaffEmployee, 'reporting_manager_id', None)
    if reporting_manager_id_col is None and not is_admin:
        raise HTTPException(status_code=500, detail="Reporting manager field not found")

    query = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.employee),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.primary_assignee),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task).joinedload(StaffTask.creator),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.phase),
    ).filter(StaffDayPlan.plan_date == target_date)

    if employee_id:
        query = query.filter(StaffDayPlan.employee_id == employee_id)
    elif is_admin:
        from app.utils.staff_hierarchy import get_team_member_ids
        team_ids = get_team_member_ids(current_user, db, StaffEmployee)
        if team_ids:
            query = query.filter(StaffDayPlan.employee_id.in_(team_ids))
    else:
        from app.utils.staff_hierarchy import get_team_member_ids
        team_ids = get_team_member_ids(current_user, db, StaffEmployee)
        if not team_ids:
            return {"plans": [], "plan_date": target_date.isoformat(), "total": 0, "is_admin_view": False}
        query = query.filter(StaffDayPlan.employee_id.in_(team_ids))

    plans = query.order_by(StaffDayPlan.employee_id).all()

    plans_data = [p.to_dict() for p in plans]

    all_task_ids = []
    all_phase_ids = []
    task_dates = {}
    phase_dates = {}
    for pd in plans_data:
        for item in (pd.get("items") or []):
            if item.get("item_type") == "phase" and item.get("phase_id"):
                all_phase_ids.append(item["phase_id"])
            elif item.get("task_id"):
                all_task_ids.append(item["task_id"])

    if all_task_ids:
        from app.models.staff_tasks import StaffTask as ST
        rows = db.query(ST.id, ST.created_at).filter(ST.id.in_(all_task_ids)).all()
        task_dates = {r[0]: r[1] for r in rows}
    if all_phase_ids:
        from app.models.staff_tasks import StaffTaskPhase as STP
        rows = db.query(STP.id, STP.created_at).filter(STP.id.in_(all_phase_ids)).all()
        phase_dates = {r[0]: r[1] for r in rows}

    task_counts, phase_counts = _get_times_planned_counts(
        db, all_task_ids or None, all_phase_ids or None
    )

    for pd in plans_data:
        for item in (pd.get("items") or []):
            if item.get("item_type") == "phase" and item.get("phase_id"):
                item["days_pending"] = _compute_days_pending(phase_dates.get(item["phase_id"]))
                item["times_planned"] = phase_counts.get(item["phase_id"], 0)
            else:
                item["days_pending"] = _compute_days_pending(task_dates.get(item.get("task_id")))
                item["times_planned"] = task_counts.get(item.get("task_id"), 0)

    emp_ids_in_plans = list(set(p.get("employee_id") for p in plans_data if p.get("employee_id")))

    all_team_ids = []
    if employee_id:
        all_team_ids = [employee_id]
    elif is_admin:
        from app.utils.staff_hierarchy import get_team_member_ids as gtm2
        all_team_ids = gtm2(current_user, db, StaffEmployee)
    else:
        from app.utils.staff_hierarchy import get_team_member_ids as gtm2
        all_team_ids = gtm2(current_user, db, StaffEmployee) or []

    all_bucket_ids = list(set(emp_ids_in_plans + all_team_ids))
    activity_buckets = {}
    if all_bucket_ids:
        active_tasks_primary = db.query(
            StaffTask.primary_assignee_id,
            StaffTask.id,
            StaffTask.created_at
        ).filter(
            StaffTask.primary_assignee_id.in_(all_bucket_ids),
            StaffTask.status.notin_(['completed', 'cancelled', 'deleted']),
            StaffTask.created_at.isnot(None)
        ).all()

        active_tasks_secondary = db.query(
            StaffTaskAssignee.employee_id,
            StaffTask.id,
            StaffTask.created_at
        ).join(StaffTask, StaffTaskAssignee.task_id == StaffTask.id
        ).filter(
            StaffTaskAssignee.employee_id.in_(all_bucket_ids),
            StaffTask.status.notin_(['completed', 'cancelled', 'deleted']),
            StaffTask.created_at.isnot(None)
        ).all()

        active_phases = db.query(
            StaffTaskPhase.phase_assignee_id,
            StaffTaskPhase.id,
            StaffTaskPhase.created_at
        ).filter(
            StaffTaskPhase.phase_assignee_id.in_(all_bucket_ids),
            StaffTaskPhase.phase_status.notin_(['completed', 'cancelled']),
            StaffTaskPhase.is_deleted == False,
            StaffTaskPhase.created_at.isnot(None)
        ).all()

        activity_items = {}
        for eid in all_bucket_ids:
            activity_items[eid] = {}

        for r in active_tasks_primary:
            if r[0] in activity_items:
                activity_items[r[0]][('task', r[1])] = r[2]
        for r in active_tasks_secondary:
            if r[0] in activity_items:
                activity_items[r[0]][('task', r[1])] = r[2]
        for r in active_phases:
            if r[0] in activity_items:
                activity_items[r[0]][('phase', r[1])] = r[2]

        for eid, items in activity_items.items():
            buckets = {"0_1": 0, "2_3": 0, "4_7": 0, "8_14": 0, "15_plus": 0, "total": 0}
            for key, created_at in items.items():
                if not created_at:
                    continue
                buckets["total"] += 1
                days = _compute_days_pending(created_at)
                if days <= 1:
                    buckets["0_1"] += 1
                elif days <= 3:
                    buckets["2_3"] += 1
                elif days <= 7:
                    buckets["4_7"] += 1
                elif days <= 14:
                    buckets["8_14"] += 1
                else:
                    buckets["15_plus"] += 1
            activity_buckets[eid] = buckets

    for pd in plans_data:
        eid = pd.get("employee_id")
        pd["activity_buckets"] = activity_buckets.get(eid, {"0_1": 0, "2_3": 0, "4_7": 0, "8_14": 0, "15_plus": 0, "total": 0})

    no_plan_buckets = {}
    plan_ids_set = set(emp_ids_in_plans)
    for eid in all_team_ids:
        if eid not in plan_ids_set:
            no_plan_buckets[str(eid)] = activity_buckets.get(eid, {"0_1": 0, "2_3": 0, "4_7": 0, "8_14": 0, "15_plus": 0, "total": 0})

    return {
        "plans": plans_data,
        "plan_date": target_date.isoformat(),
        "total": len(plans),
        "is_admin_view": is_admin,
        "no_plan_activity_buckets": no_plan_buckets
    }


@router.get("/team/pending-activities", summary="Get full pending activity detail for an employee")
def get_pending_activities(
    employee_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin_user(current_user)

    if not is_admin and current_user.id != employee_id:
        from app.utils.staff_hierarchy import get_team_member_ids
        team_ids = get_team_member_ids(current_user, db, StaffEmployee)
        if employee_id not in team_ids:
            raise HTTPException(status_code=403, detail="Not authorized to view this employee's activities")

    INACTIVE = ['completed', 'cancelled', 'deleted']

    primary_tasks = db.query(StaffTask).options(
        joinedload(StaffTask.creator),
        joinedload(StaffTask.secondary_assignees).joinedload(StaffTaskAssignee.employee)
    ).filter(
        StaffTask.primary_assignee_id == employee_id,
        StaffTask.is_deleted == False,
        StaffTask.status.notin_(INACTIVE)
    ).all()

    secondary_task_ids = [
        r[0] for r in db.query(StaffTaskAssignee.task_id).filter(
            StaffTaskAssignee.employee_id == employee_id
        ).all()
    ]
    primary_ids = {t.id for t in primary_tasks}
    secondary_tasks = []
    if secondary_task_ids:
        secondary_tasks = db.query(StaffTask).options(
            joinedload(StaffTask.creator),
            joinedload(StaffTask.secondary_assignees).joinedload(StaffTaskAssignee.employee)
        ).filter(
            StaffTask.id.in_(secondary_task_ids),
            StaffTask.id.notin_(primary_ids),
            StaffTask.is_deleted == False,
            StaffTask.status.notin_(INACTIVE)
        ).all()

    phases = db.query(StaffTaskPhase).options(
        joinedload(StaffTaskPhase.parent_task).joinedload(StaffTask.creator)
    ).filter(
        StaffTaskPhase.phase_assignee_id == employee_id,
        StaffTaskPhase.is_deleted == False,
        StaffTaskPhase.phase_status.notin_(['completed', 'cancelled'])
    ).all()

    all_task_ids = [t.id for t in primary_tasks] + [t.id for t in secondary_tasks]
    all_phase_ids = [p.id for p in phases]
    task_counts, phase_counts = _get_times_planned_counts(
        db, all_task_ids or None, all_phase_ids or None
    )

    def _bucket(days):
        if days <= 1:
            return '0-1d'
        if days <= 3:
            return '2-3d'
        if days <= 7:
            return '4-7d'
        if days <= 14:
            return '8-14d'
        return '15+d'

    items = []

    today = get_indian_date()
    today_plan = db.query(StaffDayPlan).filter(
        StaffDayPlan.employee_id == employee_id,
        StaffDayPlan.plan_date == today
    ).first()
    planned_task_ids: set = set()
    planned_phase_ids: set = set()
    if today_plan:
        for pi in db.query(StaffDayPlanItem).filter(StaffDayPlanItem.day_plan_id == today_plan.id).all():
            if pi.item_type == "phase" and pi.phase_id:
                planned_phase_ids.add(pi.phase_id)
            elif pi.task_id:
                planned_task_ids.add(pi.task_id)

    for task in primary_tasks + secondary_tasks:
        days = _compute_days_pending(task.created_at)
        assoc_names = [
            sa.employee.full_name
            for sa in (task.secondary_assignees or [])
            if sa.employee and sa.employee_id != employee_id
        ]
        items.append({
            'id': task.id,
            'task_id': task.id,
            'phase_id': None,
            'type': 'task',
            'title': task.title,
            'parent_task': None,
            'category': task.category or 'general',
            'priority': task.priority or 'medium',
            'status': task.status,
            'assigned_by': task.creator.full_name if task.creator else '—',
            'associated_people': ', '.join(assoc_names) if assoc_names else '—',
            'days_pending': days,
            'bucket': _bucket(days),
            'times_planned': task_counts.get(task.id, 0),
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'in_today_plan': task.id in planned_task_ids,
        })

    for phase in phases:
        days = _compute_days_pending(phase.created_at)
        parent = phase.parent_task
        creator_name = parent.creator.full_name if (parent and parent.creator) else '—'
        items.append({
            'id': phase.id,
            'task_id': parent.id if parent else None,
            'phase_id': phase.id,
            'type': 'phase',
            'title': phase.phase_title,
            'parent_task': parent.title if parent else '—',
            'category': parent.category if parent else 'general',
            'priority': parent.priority if parent else 'medium',
            'status': phase.phase_status,
            'assigned_by': creator_name,
            'associated_people': '—',
            'days_pending': days,
            'bucket': _bucket(days),
            'times_planned': phase_counts.get(phase.id, 0),
            'due_date': None,
            'in_today_plan': phase.id in planned_phase_ids,
        })

    items.sort(key=lambda x: x['days_pending'], reverse=True)

    return {
        'success': True,
        'employee_id': employee_id,
        'total': len(items),
        'items': items,
    }


@router.post("/team/push-item", summary="Manager pushes an activity to a team member's day plan")
def push_item_to_team_plan(
    data: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func as sqlfunc
    employee_id = data.get("employee_id")
    task_id = data.get("task_id")
    item_type = data.get("item_type", "task")
    phase_id = data.get("phase_id")

    if not employee_id or not task_id:
        raise HTTPException(status_code=400, detail="employee_id and task_id are required")

    is_admin = _is_admin_user(current_user)
    if not is_admin and current_user.id != employee_id:
        from app.utils.staff_hierarchy import get_team_member_ids
        team_ids = get_team_member_ids(current_user, db, StaffEmployee)
        if employee_id not in team_ids:
            raise HTTPException(status_code=403, detail="Not authorized to manage this employee's day plan")

    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if item_type == "phase" and phase_id:
        phase = db.query(StaffTaskPhase).filter(StaffTaskPhase.id == phase_id).first()
        if not phase:
            raise HTTPException(status_code=404, detail="Phase not found")

    today = get_indian_date()
    plan = db.query(StaffDayPlan).filter(
        StaffDayPlan.employee_id == employee_id,
        StaffDayPlan.plan_date == today
    ).first()

    if not plan:
        plan = StaffDayPlan(employee_id=employee_id, plan_date=today)
        db.add(plan)
        db.flush()

    existing_q = db.query(StaffDayPlanItem).filter(
        StaffDayPlanItem.day_plan_id == plan.id,
        StaffDayPlanItem.task_id == task_id,
        StaffDayPlanItem.item_type == item_type
    )
    if item_type == "phase" and phase_id:
        existing_q = existing_q.filter(StaffDayPlanItem.phase_id == phase_id)
    if existing_q.first():
        return {"success": True, "message": "Activity already in day plan", "already_planned": True}

    max_priority = db.query(sqlfunc.max(StaffDayPlanItem.priority_order)).filter(
        StaffDayPlanItem.day_plan_id == plan.id
    ).scalar() or 0

    plan_item = StaffDayPlanItem(
        day_plan_id=plan.id,
        item_type=item_type,
        task_id=task_id,
        phase_id=phase_id if item_type == "phase" else None,
        priority_order=max_priority + 1,
        planned_status=task.status
    )
    db.add(plan_item)
    _recalc_plan_stats(plan)
    db.commit()

    return {"success": True, "message": "Activity added to day plan", "already_planned": False}


@router.get("/team/members", summary="Get team members for manager filter")
def get_team_members(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin_user(current_user)

    from app.utils.staff_hierarchy import get_team_member_ids
    team_ids = get_team_member_ids(current_user, db, StaffEmployee)
    if not team_ids:
        return {"members": [], "is_admin_view": is_admin}

    members = db.query(StaffEmployee).filter(
        StaffEmployee.id.in_(team_ids),
        StaffEmployee.status == 'active'
    ).order_by(StaffEmployee.full_name).all()

    return {
        "members": [
            {"id": s.id, "full_name": s.full_name, "emp_code": s.emp_code}
            for s in members
        ],
        "is_admin_view": is_admin
    }


@router.get("/carried-forward", summary="Get incomplete items from previous day for carry-forward")
def get_carried_forward(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    today = get_indian_date()

    recent_plans = db.query(StaffDayPlan).options(
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.task),
        joinedload(StaffDayPlan.items).joinedload(StaffDayPlanItem.phase),
    ).filter(
        StaffDayPlan.employee_id == current_user.id,
        StaffDayPlan.plan_date < today
    ).order_by(StaffDayPlan.plan_date.desc()).limit(1).all()

    carried = []
    for plan in recent_plans:
        for item in (plan.items or []):
            effective_status = item.eod_status or item.planned_status or ''
            if effective_status not in ('completed', 'cancelled'):
                if item.task and item.task.status not in ('completed', 'cancelled'):
                    carried.append({
                        **item.to_dict(),
                        "carried_from_date": plan.plan_date.isoformat(),
                        "is_carried_forward": True
                    })

    return {"carried_items": carried, "total": len(carried)}


@router.get("/day-progress", summary="Get daily progress tracker for self and team")
def get_day_progress(
    plan_date: Optional[str] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.models.staff_attendance import StaffAttendance
    from app.models.staff_kra import StaffKRADailyInstance
    from app.models.staff_timesheet import StaffTimesheetEntry
    from app.models.staff_attendance_sheet import StaffAttendanceSheet, StaffLeaveRequest, LeaveRequestStatus

    target_date = get_indian_date()
    if plan_date:
        try:
            target_date = date.fromisoformat(plan_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    is_admin = _is_admin_user(current_user)

    from app.utils.staff_hierarchy import get_team_member_ids
    team_member_ids = get_team_member_ids(current_user, db, StaffEmployee)
    all_emp_ids = [current_user.id] + list(team_member_ids)

    team_members = []
    if team_member_ids:
        team_members = db.query(
            StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code
        ).filter(
            StaffEmployee.id.in_(team_member_ids),
            StaffEmployee.status == 'active'
        ).order_by(StaffEmployee.full_name).all()

    attendance_rows = db.query(
        StaffAttendance.employee_id,
        StaffAttendance.clock_in,
        StaffAttendance.clock_out,
        StaffAttendance.status
    ).filter(
        StaffAttendance.employee_id.in_(all_emp_ids),
        StaffAttendance.date == target_date
    ).all()
    att_map = {}
    for r in attendance_rows:
        ci_time = None
        co_time = None
        if r.clock_in:
            try:
                ci_time = r.clock_in.strftime("%I:%M %p")
            except Exception:
                ci_time = str(r.clock_in)
        if r.clock_out:
            try:
                co_time = r.clock_out.strftime("%I:%M %p")
            except Exception:
                co_time = str(r.clock_out)
        att_map[r.employee_id] = {"clock_in": r.clock_in is not None, "clock_out": r.clock_out is not None, "clock_in_time": ci_time, "clock_out_time": co_time}

    hr_sheet_rows = db.query(
        StaffAttendanceSheet.employee_id,
        StaffAttendanceSheet.attendance_status,
        StaffAttendanceSheet.approval_status
    ).filter(
        StaffAttendanceSheet.employee_id.in_(all_emp_ids),
        StaffAttendanceSheet.date == target_date
    ).all()
    hr_sheet_map = {}
    for r in hr_sheet_rows:
        hr_sheet_map[r.employee_id] = {
            "attendance_status": r.attendance_status.value if r.attendance_status else None,
            "approval_status": r.approval_status.value if r.approval_status else "pending"
        }

    LEAVE_STATUSES = {'sick_leave', 'casual_leave', 'approved_leave', 'unpaid_leave', 'holiday', 'weekend'}

    leave_request_rows = db.query(
        StaffLeaveRequest.employee_id,
        StaffLeaveRequest.status
    ).filter(
        StaffLeaveRequest.employee_id.in_(all_emp_ids),
        StaffLeaveRequest.start_date <= target_date,
        StaffLeaveRequest.end_date >= target_date,
        StaffLeaveRequest.status.in_([
            LeaveRequestStatus.APPROVED,
            LeaveRequestStatus.PENDING_MANAGER,
            LeaveRequestStatus.PENDING_HR
        ])
    ).all()
    leave_request_map = {}
    for r in leave_request_rows:
        leave_request_map[r.employee_id] = r.status.value if r.status else "pending_manager"

    def is_employee_on_leave(emp_id):
        hr_data = hr_sheet_map.get(emp_id)
        if hr_data and hr_data.get("attendance_status") in LEAVE_STATUSES:
            return True
        if emp_id in leave_request_map:
            return True
        return False

    def get_leave_display(emp_id):
        hr_data = hr_sheet_map.get(emp_id)
        hr_status = hr_data.get("attendance_status") if hr_data else None
        leave_req_status = leave_request_map.get(emp_id)

        STATUS_LABELS = {
            'sick_leave': 'Sick Leave',
            'casual_leave': 'Casual Leave',
            'approved_leave': 'Approved Leave',
            'unpaid_leave': 'Unpaid Leave',
            'holiday': 'Holiday',
            'weekend': 'Weekend'
        }

        if hr_status and hr_status in LEAVE_STATUSES:
            return STATUS_LABELS.get(hr_status, hr_status.replace('_', ' ').title())

        if leave_req_status:
            REQ_LABELS = {
                'approved': 'Leave (Approved)',
                'pending_manager': 'Leave (Pending Manager)',
                'pending_hr': 'Leave (Pending HR)'
            }
            return REQ_LABELS.get(leave_req_status, 'On Leave')

        return 'On Leave'

    plan_rows = db.query(
        StaffDayPlan.employee_id,
        StaffDayPlan.status,
        StaffDayPlan.finalized_at,
        func.count(StaffDayPlanItem.id).label('item_count')
    ).outerjoin(StaffDayPlanItem, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
    ).filter(
        StaffDayPlan.employee_id.in_(all_emp_ids),
        StaffDayPlan.plan_date == target_date
    ).group_by(StaffDayPlan.employee_id, StaffDayPlan.status, StaffDayPlan.finalized_at).all()
    plan_map = {}
    for r in plan_rows:
        plan_map[r.employee_id] = {
            "has_plan": r.item_count > 0,
            "is_finalized": r.finalized_at is not None,
            "item_count": r.item_count
        }

    plan_eod_rows = db.query(
        StaffDayPlan.employee_id,
        func.count(StaffDayPlanItem.id).label('total_items'),
        func.count(func.nullif(
            func.coalesce(StaffDayPlanItem.eod_status, ''), 'completed'
        )).label('not_completed'),
        func.sum(case(
            (func.coalesce(StaffDayPlanItem.eod_status, StaffDayPlanItem.planned_status) == 'completed', 1),
            else_=0
        )).label('delivered_count'),
        func.sum(case(
            (StaffDayPlanItem.eod_status.isnot(None), 1),
            else_=0
        )).label('eod_filled_count'),
        func.sum(case(
            (and_(
                StaffDayPlanItem.eod_status.is_(None),
                func.coalesce(StaffDayPlanItem.eod_status, StaffDayPlanItem.planned_status) != 'completed'
            ), 1),
            else_=0
        )).label('left_count')
    ).join(StaffDayPlanItem, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
    ).filter(
        StaffDayPlan.employee_id.in_(all_emp_ids),
        StaffDayPlan.plan_date == target_date
    ).group_by(StaffDayPlan.employee_id).all()
    plan_eod_map = {}
    for r in plan_eod_rows:
        plan_eod_map[r.employee_id] = {
            "total_planned": r.total_items or 0,
            "delivered": r.delivered_count or 0,
            "eod_filled": r.eod_filled_count or 0,
            "left": r.left_count or 0
        }

    plan_item_task_ids = {}
    plan_item_rows = db.query(
        StaffDayPlan.employee_id,
        StaffDayPlanItem.task_id
    ).join(StaffDayPlanItem, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
    ).filter(
        StaffDayPlan.employee_id.in_(all_emp_ids),
        StaffDayPlan.plan_date == target_date
    ).all()
    for r in plan_item_rows:
        if r.employee_id not in plan_item_task_ids:
            plan_item_task_ids[r.employee_id] = set()
        plan_item_task_ids[r.employee_id].add(r.task_id)

    all_plan_task_ids = set()
    for tids in plan_item_task_ids.values():
        all_plan_task_ids.update(tids)

    worked_task_ids = set()
    if all_plan_task_ids:
        from app.models.staff_tasks import StaffTaskActivityLog
        target_start = datetime.combine(target_date, datetime.min.time())
        target_end = datetime.combine(target_date, datetime.max.time())
        activity_rows = db.query(
            StaffTaskActivityLog.task_id
        ).filter(
            StaffTaskActivityLog.task_id.in_(list(all_plan_task_ids)),
            StaffTaskActivityLog.created_at >= target_start,
            StaffTaskActivityLog.created_at <= target_end,
            StaffTaskActivityLog.action.in_([
                'status_changed', 'status_change', 'progress_update',
                'completed', 'updated', 'phase_status_change'
            ])
        ).distinct().all()
        worked_task_ids = {r.task_id for r in activity_rows}

    worked_map = {}
    for emp_id, task_ids in plan_item_task_ids.items():
        worked_map[emp_id] = len(task_ids & worked_task_ids)

    overall_tasks_primary = db.query(
        StaffTask.primary_assignee_id.label('emp_id'),
        StaffTask.id
    ).filter(
        StaffTask.primary_assignee_id.in_(all_emp_ids),
        StaffTask.status.in_(['pending', 'in_progress', 'on_hold', 'under_review']),
        StaffTask.is_deleted == False
    ).all()

    overall_tasks_secondary = db.query(
        StaffTaskAssignee.employee_id.label('emp_id'),
        StaffTask.id
    ).join(StaffTask, StaffTaskAssignee.task_id == StaffTask.id
    ).filter(
        StaffTaskAssignee.employee_id.in_(all_emp_ids),
        StaffTask.status.in_(['pending', 'in_progress', 'on_hold', 'under_review']),
        StaffTask.is_deleted == False
    ).all()

    overall_phases = db.query(
        StaffTaskPhase.phase_assignee_id.label('emp_id'),
        StaffTaskPhase.id
    ).filter(
        StaffTaskPhase.phase_assignee_id.in_(all_emp_ids),
        StaffTaskPhase.phase_status.in_(['pending', 'in_progress', 'on_hold']),
        StaffTaskPhase.is_deleted == False
    ).all()

    overall_map = {}
    for r in overall_tasks_primary:
        overall_map[r.emp_id] = overall_map.get(r.emp_id, set())
        overall_map[r.emp_id].add(('task', r.id))
    for r in overall_tasks_secondary:
        overall_map[r.emp_id] = overall_map.get(r.emp_id, set())
        overall_map[r.emp_id].add(('task', r.id))
    for r in overall_phases:
        overall_map[r.emp_id] = overall_map.get(r.emp_id, set())
        overall_map[r.emp_id].add(('phase', r.id))

    kra_instances = db.query(
        StaffKRADailyInstance
    ).options(
        joinedload(StaffKRADailyInstance.kra_template)
    ).filter(
        StaffKRADailyInstance.employee_id.in_(all_emp_ids),
        StaffKRADailyInstance.instance_date == target_date,
        StaffKRADailyInstance.completion_status != 'na'
    ).all()
    
    from app.api.v1.endpoints.staff_kra import _check_kra_delayed
    kra_map = {}
    for inst in kra_instances:
        emp_id = inst.employee_id
        if emp_id not in kra_map:
            kra_map[emp_id] = {"total": 0, "completed": 0, "delayed_completed": 0, "pending_or_skipped": 0, "status": "incomplete"}
        kra_map[emp_id]["total"] += 1
        if inst.completion_status == 'completed':
            kra_map[emp_id]["completed"] += 1
            if _check_kra_delayed(inst, inst.kra_template):
                kra_map[emp_id]["delayed_completed"] += 1
        else:
            kra_map[emp_id]["pending_or_skipped"] += 1
    for emp_id, kra in kra_map.items():
        kra["status"] = "completed" if kra["completed"] >= kra["total"] else "incomplete"

    ts_rows = db.query(
        StaffTimesheetEntry.employee_id,
        func.count(StaffTimesheetEntry.id).label('entry_count'),
        func.sum(StaffTimesheetEntry.duration_minutes).label('total_minutes'),
        func.sum(
            case(
                (StaffTimesheetEntry.status == 'approved',
                 func.coalesce(StaffTimesheetEntry.approved_minutes, StaffTimesheetEntry.duration_minutes)),
                else_=0
            )
        ).label('approved_minutes'),
        func.count(
            case(
                (StaffTimesheetEntry.status == 'approved', StaffTimesheetEntry.id),
                else_=None
            )
        ).label('approved_count'),
        # DC Protocol (Mar 2026): Granular status flags for yellow=submitted / green=approved color logic
        func.bool_or(StaffTimesheetEntry.status == 'submitted').label('any_submitted'),
        func.bool_and(StaffTimesheetEntry.status == 'approved').label('all_approved')
    ).filter(
        StaffTimesheetEntry.employee_id.in_(all_emp_ids),
        StaffTimesheetEntry.date == target_date
    ).group_by(StaffTimesheetEntry.employee_id).all()
    ts_map = {}
    for r in ts_rows:
        total_mins = r.total_minutes or 0
        approved_mins = r.approved_minutes or 0
        hours = total_mins // 60
        mins = total_mins % 60
        ap_hours = approved_mins // 60
        ap_mins = approved_mins % 60
        has_entries = r.entry_count > 0
        # DC Protocol (Mar 2026): all_approved is True only when entries exist AND all are approved
        all_ok = bool(r.all_approved) and has_entries
        ts_map[r.employee_id] = {
            "has_entries": has_entries,
            "all_approved": all_ok,
            "any_submitted": bool(r.any_submitted),
            "total_hours": f"{hours}h {mins}m" if total_mins > 0 else None,
            "entry_count": r.entry_count,
            "total_minutes_updated": total_mins,
            "total_minutes_approved": approved_mins,
            "total_time_updated": f"{hours}h {mins}m" if total_mins > 0 else "0h 0m",
            "total_time_approved": f"{ap_hours}h {ap_mins}m" if approved_mins > 0 else "0h 0m",
            "approved_count": r.approved_count or 0
        }

    def build_progress(emp_id, emp_name, emp_code):
        on_leave = is_employee_on_leave(emp_id)
        leave_display = get_leave_display(emp_id) if on_leave else None

        att = att_map.get(emp_id, {})
        plan = plan_map.get(emp_id, {})
        kra = kra_map.get(emp_id, None)
        ts = ts_map.get(emp_id, {})
        eod = plan_eod_map.get(emp_id, {})
        overall_count = len(overall_map.get(emp_id, set()))
        planned_count = plan.get("item_count", 0)
        overall_pending = max(0, overall_count - planned_count)

        if emp_id not in plan_map and overall_count == 0:
            planner_status = "na"
            planner_detail = None
        elif emp_id not in plan_map and overall_count > 0:
            planner_status = "pending"
            planner_detail = f"0/{overall_count}"
        elif planned_count > 0:
            planner_status = "done"
            planner_detail = f"{planned_count}/{overall_count}"
        else:
            planner_status = "pending"
            planner_detail = f"0/{overall_count}"

        total_planned_eod = eod.get('total_planned', 0)
        closed_count = eod.get('delivered', 0)
        left_count = eod.get('left', 0)
        worked_count = worked_map.get(emp_id, 0)
        eod_filled = eod.get('eod_filled', 0)
        worked_combined = max(eod_filled, worked_count)

        if emp_id not in plan_map:
            closure_status = "na"
            closure_detail = None
        elif plan.get("is_finalized"):
            closure_status = "completed"
            closure_detail = f"{closed_count}/{total_planned_eod}"
        else:
            closure_status = "pending"
            closure_detail = f"{closed_count}/{total_planned_eod}"

        return {
            "employee_id": emp_id,
            "full_name": emp_name,
            "emp_code": emp_code,
            "is_on_leave": on_leave,
            "leave_display": leave_display,
            "clock_in": "done" if att.get("clock_in") else "pending",
            "clock_in_time": att.get("clock_in_time"),
            "day_planner": planner_status,
            "day_planner_detail": planner_detail,
            "planner_overall": overall_count,
            "planner_overall_pending": overall_pending,
            "planner_overall_planned": planned_count,
            "kra_status": kra["status"] if kra else "na",
            "kra_detail": f"{kra['completed']}/{kra['total']}" if kra else None,
            "kra_total": kra["total"] if kra else 0,
            "kra_completed": kra["completed"] if kra else 0,
            "kra_delayed_completed": kra["delayed_completed"] if kra else 0,
            "kra_pending_or_skipped": kra["pending_or_skipped"] if kra else 0,
            "day_closure": closure_status,
            "day_closure_detail": closure_detail,
            "closure_planned": total_planned_eod,
            "closure_closed": closed_count,
            "closure_left": left_count,
            "closure_worked": worked_combined,
            # DC Protocol (Mar 2026): Return granular status: approved=green, submitted=yellow, pending=red
            "timesheet": "approved" if ts.get("all_approved") else ("submitted" if ts.get("has_entries") else "pending"),
            "timesheet_detail": ts.get("total_hours"),
            "ts_total_time_updated": ts.get("total_time_updated", "0h 0m"),
            "ts_total_time_approved": ts.get("total_time_approved", "0h 0m"),
            "ts_entry_count": ts.get("entry_count", 0),
            "ts_approved_count": ts.get("approved_count", 0),
            "clock_out": "done" if att.get("clock_out") else "pending",
            "clock_out_time": att.get("clock_out_time"),
            "hr_attendance": hr_sheet_map[emp_id]["attendance_status"] if emp_id in hr_sheet_map else "na",
            "hr_approval": hr_sheet_map[emp_id]["approval_status"] if emp_id in hr_sheet_map else "na"
        }

    self_progress = build_progress(current_user.id, current_user.full_name, current_user.emp_code)

    # ── Department KPI for self ──────────────────────────────────────────────
    from app.api.v1.endpoints.staff_progress import get_procurement_kpi_summary
    _self_dn = (current_user.department.name or '').lower() if current_user.department else ''
    _self_is_sales = 'sales' in _self_dn or 'crm' in _self_dn
    _self_is_service = 'service' in _self_dn
    _self_is_proc = 'procurement' in _self_dn or 'purchase' in _self_dn
    self_progress['dept_type'] = 'sales' if _self_is_sales else ('service' if _self_is_service else ('procurement' if _self_is_proc else 'other'))
    _self_dept_kpi = {}
    if _self_is_sales:
        from app.models.call_tracking import StaffCallLog
        from app.models.crm import CRMLead
        _call_secs = int(db.query(func.sum(StaffCallLog.duration_seconds)).filter(
            StaffCallLog.staff_id == current_user.id,
            StaffCallLog.call_date == target_date.isoformat()
        ).scalar() or 0)
        _talk_h = _call_secs // 3600
        _talk_m = (_call_secs % 3600) // 60
        _overdue = int(db.query(func.count(CRMLead.id)).filter(
            or_(CRMLead.telecaller_id == current_user.id, CRMLead.field_staff_id == current_user.id),
            func.date(CRMLead.next_followup_date) < target_date,
            CRMLead.status.notin_(['won', 'lost', 'dropped', 'completed'])
        ).scalar() or 0)
        _handled = int(db.query(func.count(CRMLead.id)).filter(
            or_(CRMLead.telecaller_id == current_user.id, CRMLead.field_staff_id == current_user.id),
            func.date(CRMLead.last_contact_date) == target_date
        ).scalar() or 0)
        _self_dept_kpi = {'talk_time_secs': _call_secs, 'talk_time_formatted': f"{_talk_h}h {_talk_m}m",
                          'leads_handled_today': _handled, 'overdue_leads': _overdue}
    elif _self_is_service:
        from app.models.ticket import ServiceTicket
        _base_f = or_(ServiceTicket.service_manager_id == current_user.id, ServiceTicket.service_technician_id == current_user.id)
        _new_t = int(db.query(func.count(ServiceTicket.id)).filter(_base_f, func.date(ServiceTicket.created_date) == target_date).scalar() or 0)
        _closed_t = int(db.query(func.count(ServiceTicket.id)).filter(_base_f, ServiceTicket.status == 'Closed', func.date(ServiceTicket.closed_date) == target_date).scalar() or 0)
        _within_tat = int(db.query(func.count(ServiceTicket.id)).filter(_base_f, ServiceTicket.status == 'Closed', func.date(ServiceTicket.closed_date) == target_date, ServiceTicket.tat_due_at.isnot(None), ServiceTicket.closed_date <= ServiceTicket.tat_due_at).scalar() or 0)
        _tat_pct = round((_within_tat / _closed_t) * 100) if _closed_t > 0 else 0
        _self_dept_kpi = {'tickets_handled': _new_t, 'tickets_resolved': _closed_t, 'within_tat_count': _within_tat, 'within_tat_pct': _tat_pct, 'above_tat_count': max(0, _closed_t - _within_tat)}
    elif _self_is_proc:
        _self_dept_kpi = get_procurement_kpi_summary(db, current_user.id, target_date)
    self_progress['dept_kpi'] = _self_dept_kpi

    # ── Dept type/KPI for team members (batch lookup) ───────────────────────────
    _team_dept_map = {}
    _team_kpi_map = {}
    if team_member_ids:
        _emp_dept_rows = db.query(StaffEmployee.id, StaffEmployee.department_id).filter(StaffEmployee.id.in_(team_member_ids)).all()
        _dept_ids = list({r.department_id for r in _emp_dept_rows if r.department_id})
        if _dept_ids:
            from app.models.staff import StaffDepartment
            _dept_name_rows = db.query(StaffDepartment.id, StaffDepartment.name).filter(StaffDepartment.id.in_(_dept_ids)).all()
            _dn_map = {d.id: (d.name or '').lower() for d in _dept_name_rows}
            for r in _emp_dept_rows:
                _dn = _dn_map.get(r.department_id, '')
                dtype = 'sales' if ('sales' in _dn or 'crm' in _dn) else ('service' if 'service' in _dn else ('procurement' if ('procurement' in _dn or 'purchase' in _dn) else 'other'))
                _team_dept_map[r.id] = dtype
                
                # Fetch KPI for team member if applicable
                if dtype == 'sales':
                    from app.models.call_tracking import StaffCallLog
                    from app.models.crm import CRMLead
                    __call_secs = int(db.query(func.sum(StaffCallLog.duration_seconds)).filter(StaffCallLog.staff_id == r.id, StaffCallLog.call_date == target_date.isoformat()).scalar() or 0)
                    __talk_h = __call_secs // 3600
                    __talk_m = (__call_secs % 3600) // 60
                    __overdue = int(db.query(func.count(CRMLead.id)).filter(or_(CRMLead.telecaller_id == r.id, CRMLead.field_staff_id == r.id), func.date(CRMLead.next_followup_date) < target_date, CRMLead.status.notin_(['won', 'lost', 'dropped', 'completed'])).scalar() or 0)
                    __handled = int(db.query(func.count(CRMLead.id)).filter(or_(CRMLead.telecaller_id == r.id, CRMLead.field_staff_id == r.id), func.date(CRMLead.last_contact_date) == target_date).scalar() or 0)
                    _team_kpi_map[r.id] = {'talk_time_secs': __call_secs, 'talk_time_formatted': f"{__talk_h}h {__talk_m}m", 'leads_handled_today': __handled, 'overdue_leads': __overdue}
                elif dtype == 'service':
                    from app.models.ticket import ServiceTicket
                    __base_f = or_(ServiceTicket.service_manager_id == r.id, ServiceTicket.service_technician_id == r.id)
                    __new_t = int(db.query(func.count(ServiceTicket.id)).filter(__base_f, func.date(ServiceTicket.created_date) == target_date).scalar() or 0)
                    __closed_t = int(db.query(func.count(ServiceTicket.id)).filter(__base_f, ServiceTicket.status == 'Closed', func.date(ServiceTicket.closed_date) == target_date).scalar() or 0)
                    __within_tat = int(db.query(func.count(ServiceTicket.id)).filter(__base_f, ServiceTicket.status == 'Closed', func.date(ServiceTicket.closed_date) == target_date, ServiceTicket.tat_due_at.isnot(None), ServiceTicket.closed_date <= ServiceTicket.tat_due_at).scalar() or 0)
                    __tat_pct = round((__within_tat / __closed_t) * 100) if __closed_t > 0 else 0
                    _team_kpi_map[r.id] = {'tickets_handled': __new_t, 'tickets_resolved': __closed_t, 'within_tat_count': __within_tat, 'within_tat_pct': __tat_pct, 'above_tat_count': max(0, __closed_t - __within_tat)}
                elif dtype == 'procurement':
                    _team_kpi_map[r.id] = get_procurement_kpi_summary(db, r.id, target_date)

    team_progress = []
    team_on_leave = []
    for m in team_members:
        p = build_progress(m.id, m.full_name, m.emp_code)
        p['dept_type'] = _team_dept_map.get(m.id, 'other')
        p['dept_kpi'] = _team_kpi_map.get(m.id, {})
        if p.get("is_on_leave"):
            team_on_leave.append(p)
        else:
            team_progress.append(p)

    return {
        "date": target_date.isoformat(),
        "self": self_progress,
        "team": team_progress,
        "team_on_leave": team_on_leave,
        "has_team": len(team_progress) + len(team_on_leave) > 0
    }
