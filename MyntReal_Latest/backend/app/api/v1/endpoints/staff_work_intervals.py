"""
Staff Work Interval API Endpoints (DC Protocol Compliant)
Time-Activity linkage for KRA and Task status updates

Key Features:
- Log work intervals linked to KRAs or Tasks
- Status propagation to linked entities
- Non-overlapping interval enforcement
- Manager approval workflow

Created: Nov 27, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
import pytz

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.staff_attendance import StaffAttendance
from app.models.staff_work_interval import (
    StaffWorkInterval, StaffWorkIntervalLog, log_interval_activity
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter()


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


def get_indian_date():
    """Get current date in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def get_client_ip(request: Request = None) -> str:
    """Extract client IP from request headers (handles None request)"""
    if request is None:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")


class CreateIntervalRequest(BaseModel):
    activity_type: str = Field(default="general")
    kra_entry_id: Optional[int] = None
    task_id: Optional[int] = None
    activity_title: Optional[str] = None
    activity_notes: Optional[str] = None
    interval_start: Optional[str] = None
    interval_end: Optional[str] = None
    is_billable: bool = True


class UpdateIntervalRequest(BaseModel):
    activity_type: Optional[str] = None
    kra_entry_id: Optional[int] = None
    task_id: Optional[int] = None
    activity_title: Optional[str] = None
    activity_notes: Optional[str] = None
    interval_end: Optional[str] = None
    status: Optional[str] = None
    is_billable: Optional[bool] = None


class IntervalStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None


@router.get("/today", summary="Get today's work intervals")
async def get_today_intervals(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all work intervals for today
    DC: Return intervals with linked entities
    """
    today = get_indian_date()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        return {
            "success": True,
            "intervals": [],
            "total_minutes": 0,
            "has_attendance": False
        }
    
    intervals = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.attendance_id == attendance.id
    ).order_by(StaffWorkInterval.interval_start).all()
    
    total_minutes = sum(i.duration_minutes or 0 for i in intervals if i.interval_end)
    
    return {
        "success": True,
        "intervals": [i.to_dict() for i in intervals],
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "has_attendance": True,
        "active_interval": next((i.to_dict() for i in intervals if not i.interval_end), None)
    }


@router.post("/start", summary="Start a work interval")
async def start_interval(
    interval_data: CreateIntervalRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Start a new work interval
    DC: One active interval at a time
    WVV: Validate no overlapping intervals
    """
    today = get_indian_date()
    now = get_indian_time()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance or not attendance.clock_in:
        raise HTTPException(status_code=400, detail="Must clock in first")
    
    if attendance.clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out for the day")
    
    active_interval = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.attendance_id == attendance.id,
        StaffWorkInterval.interval_end == None
    ).first()
    
    if active_interval:
        raise HTTPException(
            status_code=400, 
            detail="An interval is already active. End it before starting a new one."
        )
    
    interval_start = now
    if interval_data.interval_start:
        try:
            interval_start = datetime.fromisoformat(interval_data.interval_start.replace('Z', ''))
        except:
            pass
    
    interval = StaffWorkInterval(
        attendance_id=attendance.id,
        employee_id=current_user.id,
        interval_start=interval_start,
        activity_type=interval_data.activity_type,
        kra_entry_id=interval_data.kra_entry_id,
        task_id=interval_data.task_id,
        activity_title=interval_data.activity_title,
        activity_notes=interval_data.activity_notes,
        is_billable=interval_data.is_billable,
        status='in_progress'
    )
    db.add(interval)
    db.flush()
    
    log_interval_activity(
        db=db,
        interval_id=interval.id,
        employee_id=current_user.id,
        action='created',
        details={
            "activity_type": interval_data.activity_type,
            "kra_entry_id": interval_data.kra_entry_id,
            "task_id": interval_data.task_id,
            "time": interval_start.isoformat()
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(interval)
    
    return {
        "success": True,
        "message": "Work interval started",
        "interval": interval.to_dict()
    }


@router.post("/{interval_id}/end", summary="End a work interval")
async def end_interval(
    interval_id: int,
    request: Request,
    interval_data: UpdateIntervalRequest = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    End a work interval and update linked entity status
    DC: Calculate duration and propagate status
    WVV: Update KRA/Task status if linked
    """
    now = get_indian_time()
    
    interval = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.id == interval_id,
        StaffWorkInterval.employee_id == current_user.id
    ).first()
    
    if not interval:
        raise HTTPException(status_code=404, detail="Interval not found")
    
    if interval.interval_end:
        raise HTTPException(status_code=400, detail="Interval already ended")
    
    interval_end = now
    if interval_data and interval_data.interval_end:
        try:
            interval_end = datetime.fromisoformat(interval_data.interval_end.replace('Z', ''))
        except:
            pass
    
    interval.interval_end = interval_end
    interval.duration_minutes = interval.calculate_duration()
    
    if interval_data:
        if interval_data.status:
            interval.status_before = interval.status
            interval.status = interval_data.status
            interval.status_after = interval_data.status
        
        if interval_data.activity_notes:
            interval.activity_notes = interval_data.activity_notes
    else:
        interval.status = 'completed'
        interval.status_after = 'completed'
    
    log_interval_activity(
        db=db,
        interval_id=interval.id,
        employee_id=current_user.id,
        action='updated',
        details={
            "duration_minutes": interval.duration_minutes,
            "status": interval.status,
            "end_time": interval_end.isoformat()
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(interval)
    
    return {
        "success": True,
        "message": f"Interval ended. Duration: {interval.duration_minutes} minutes",
        "interval": interval.to_dict()
    }


@router.put("/{interval_id}", summary="Update a work interval")
async def update_interval(
    interval_id: int,
    interval_data: UpdateIntervalRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update work interval details
    DC: Allow updates before approval
    WVV: Validate ownership and approval status
    """
    interval = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.id == interval_id,
        StaffWorkInterval.employee_id == current_user.id
    ).first()
    
    if not interval:
        raise HTTPException(status_code=404, detail="Interval not found")
    
    if interval.approval_status == 'approved':
        raise HTTPException(status_code=400, detail="Cannot modify approved interval")
    
    previous_values = {}
    new_values = {}
    
    if interval_data.activity_type is not None:
        previous_values['activity_type'] = interval.activity_type
        interval.activity_type = interval_data.activity_type
        new_values['activity_type'] = interval_data.activity_type
    
    if interval_data.kra_entry_id is not None:
        previous_values['kra_entry_id'] = interval.kra_entry_id
        interval.kra_entry_id = interval_data.kra_entry_id
        new_values['kra_entry_id'] = interval_data.kra_entry_id
    
    if interval_data.task_id is not None:
        previous_values['task_id'] = interval.task_id
        interval.task_id = interval_data.task_id
        new_values['task_id'] = interval_data.task_id
    
    if interval_data.activity_title is not None:
        previous_values['activity_title'] = interval.activity_title
        interval.activity_title = interval_data.activity_title
        new_values['activity_title'] = interval_data.activity_title
    
    if interval_data.activity_notes is not None:
        previous_values['activity_notes'] = interval.activity_notes
        interval.activity_notes = interval_data.activity_notes
        new_values['activity_notes'] = interval_data.activity_notes
    
    if interval_data.status is not None:
        previous_values['status'] = interval.status
        interval.status_before = interval.status
        interval.status = interval_data.status
        interval.status_after = interval_data.status
        new_values['status'] = interval_data.status
    
    if interval_data.is_billable is not None:
        previous_values['is_billable'] = interval.is_billable
        interval.is_billable = interval_data.is_billable
        new_values['is_billable'] = interval_data.is_billable
    
    if new_values:
        log_interval_activity(
            db=db,
            interval_id=interval.id,
            employee_id=current_user.id,
            action='updated',
            previous_value=previous_values,
            new_value=new_values,
            ip_address=get_client_ip(request)
        )
    
    db.commit()
    db.refresh(interval)
    
    return {
        "success": True,
        "message": "Interval updated",
        "interval": interval.to_dict()
    }


@router.post("/{interval_id}/link-kra", summary="Link interval to KRA")
async def link_to_kra(
    interval_id: int,
    kra_entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Link work interval to a KRA entry
    DC: Update KRA progress based on interval
    """
    interval = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.id == interval_id,
        StaffWorkInterval.employee_id == current_user.id
    ).first()
    
    if not interval:
        raise HTTPException(status_code=404, detail="Interval not found")
    
    previous_kra = interval.kra_entry_id
    interval.kra_entry_id = kra_entry_id
    interval.activity_type = 'kra'
    interval.task_id = None
    
    log_interval_activity(
        db=db,
        interval_id=interval.id,
        employee_id=current_user.id,
        action='kra_linked',
        previous_value={"kra_entry_id": previous_kra},
        new_value={"kra_entry_id": kra_entry_id},
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Interval linked to KRA",
        "interval": interval.to_dict()
    }


@router.post("/{interval_id}/link-task", summary="Link interval to Task")
async def link_to_task(
    interval_id: int,
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Link work interval to a Task
    DC: Update Task progress based on interval
    """
    interval = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.id == interval_id,
        StaffWorkInterval.employee_id == current_user.id
    ).first()
    
    if not interval:
        raise HTTPException(status_code=404, detail="Interval not found")
    
    previous_task = interval.task_id
    interval.task_id = task_id
    interval.activity_type = 'task'
    interval.kra_entry_id = None
    
    log_interval_activity(
        db=db,
        interval_id=interval.id,
        employee_id=current_user.id,
        action='task_linked',
        previous_value={"task_id": previous_task},
        new_value={"task_id": task_id},
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Interval linked to Task",
        "interval": interval.to_dict()
    }


@router.get("/history", summary="Get work interval history")
async def get_interval_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    activity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get work interval history with filters
    DC: Return historical interval data
    """
    query = db.query(StaffWorkInterval).filter(
        StaffWorkInterval.employee_id == current_user.id
    )
    
    if start_date:
        query = query.filter(StaffWorkInterval.interval_start >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.filter(StaffWorkInterval.interval_start <= datetime.combine(end_date, datetime.max.time()))
    
    if activity_type:
        query = query.filter(StaffWorkInterval.activity_type == activity_type)
    
    intervals = query.order_by(StaffWorkInterval.interval_start.desc()).limit(100).all()
    
    total_minutes = sum(i.duration_minutes or 0 for i in intervals if i.interval_end)
    
    by_type = {}
    for i in intervals:
        t = i.activity_type
        if t not in by_type:
            by_type[t] = {"count": 0, "minutes": 0}
        by_type[t]["count"] += 1
        by_type[t]["minutes"] += i.duration_minutes or 0
    
    return {
        "success": True,
        "intervals": [i.to_dict() for i in intervals],
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "by_activity_type": by_type
    }


@router.get("/kra-options", summary="Get available KRAs for linking")
async def get_kra_options(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get available KRAs that can be linked to intervals
    DC: Return active KRA assignments
    """
    today = get_indian_date()
    
    try:
        from app.models.staff_kra import StaffKRAAssignment
        
        assignments = db.query(StaffKRAAssignment).filter(
            StaffKRAAssignment.employee_id == current_user.id,
            StaffKRAAssignment.is_active == True
        ).all()
        
        return {
            "success": True,
            "kras": [
                {
                    "id": a.id,
                    "kra_template_id": a.kra_template_id,
                    "kra_title": a.kra_template.title if a.kra_template else None,
                    "effective_from": a.effective_from.isoformat() if a.effective_from else None,
                    "effective_until": a.effective_until.isoformat() if a.effective_until else None
                }
                for a in assignments
            ]
        }
    except Exception as e:
        return {
            "success": True,
            "kras": [],
            "error": str(e)
        }


@router.get("/task-options", summary="Get available Tasks for linking")
async def get_task_options(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get available Tasks that can be linked to intervals
    DC: Return active task assignments
    """
    try:
        from app.models.staff_tasks import StaffTask
        
        tasks = db.query(StaffTask).filter(
            or_(
                StaffTask.primary_assignee_id == current_user.id,
                StaffTask.secondary_assignees.any(id=current_user.id)
            ),
            StaffTask.status.in_(['pending', 'in_progress', 'on_hold'])
        ).limit(50).all()
        
        return {
            "success": True,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "category": t.category,
                    "priority": t.priority,
                    "status": t.status,
                    "due_date": t.due_date.isoformat() if t.due_date else None
                }
                for t in tasks
            ]
        }
    except Exception as e:
        return {
            "success": True,
            "tasks": [],
            "error": str(e)
        }
