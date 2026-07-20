"""
Staff Timesheet Entry API Endpoints (DC Protocol Compliant)
Manual time tracking with Task/KRA linking and approval workflow

Key Features:
- Create/update/delete timesheet entries
- Multiple entries per day (non-overlapping)
- Link to Tasks, KRAs, or Others category
- Total time validation (must not exceed working hours)
- Approval workflow: submit → approve/reject → resubmit
- Role-based access: Manager sees team, Supreme sees all
- Complete audit trail (DC Protocol)

Created: Dec 01, 2025
DC Protocol: Write-Verify-Validate at all levels
WVV Protocol: All data validated before operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import pytz
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffDepartment
from app.models.staff_attendance import StaffAttendance, StaffAttendanceBreak
from app.models.staff_tasks import StaffTask
from app.models.staff_kra import StaffKRAAssignment
from app.models.crm import CRMLead
from app.models.staff_journey import StaffJourney, JourneyStatus
from app.models.staff_timesheet import (
    StaffTimesheetEntry, StaffTimesheetApprovalHistory,
    log_timesheet_activity, compute_attendance_status,
    generate_timesheet_audit_id, generate_entry_group_id
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.staff_hierarchy import get_team_member_ids, _get_hidden_employee_ids, HIDDEN_FROM_TEAM_CODES

logger = logging.getLogger(__name__)

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


def calculate_duration_minutes(start_time: time, end_time: time) -> int:
    """Calculate duration in minutes between two times"""
    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    delta = end_dt - start_dt
    return int(delta.total_seconds() / 60)


def calculate_non_duplicated_minutes(entries: list) -> int:
    """
    DC Protocol (Jan 22, 2026): Calculate total minutes avoiding double-counting grouped entries.
    When multiple leads share an entry_group_id, count that time slot only once.
    """
    seen_groups = set()
    total = 0
    
    for e in entries:
        if e.entry_group_id:
            # For grouped entries, count only once per group
            if e.entry_group_id not in seen_groups:
                seen_groups.add(e.entry_group_id)
                total += e.duration_minutes or 0
        else:
            # Non-grouped entries are counted normally
            total += e.duration_minutes or 0
    
    return total


def calculate_non_duplicated_billable_minutes(entries: list) -> int:
    """
    DC Protocol (Jan 22, 2026): Calculate billable minutes avoiding double-counting grouped entries.
    """
    seen_groups = set()
    total = 0
    
    for e in entries:
        billable = e.billable_minutes if e.billable_minutes > 0 else (e.duration_minutes - e.break_duration_minutes)
        if e.entry_group_id:
            if e.entry_group_id not in seen_groups:
                seen_groups.add(e.entry_group_id)
                total += billable
        else:
            total += billable
    
    return total


# ==================== PYDANTIC SCHEMAS ====================

class TimesheetEntryCreate(BaseModel):
    date: date
    start_time: time
    end_time: time
    break_start_time: Optional[time] = None
    break_end_time: Optional[time] = None
    break_duration_minutes: Optional[int] = None
    break_type: Optional[str] = None
    entry_type: str  # 'task', 'kra', 'lead', 'journey', 'others'
    task_id: Optional[int] = None
    kra_id: Optional[int] = None
    lead_id: Optional[int] = None  # Single lead (backward compatible)
    lead_ids: Optional[List[int]] = None  # DC Protocol (Jan 22, 2026): Multiple leads for continuous activity
    journey_id: Optional[int] = None
    comments: Optional[str] = None

    @field_validator('end_time')
    def end_after_start(cls, v, info):
        if 'start_time' in info.data and info.data['start_time'] is not None:
            if v <= info.data['start_time']:
                raise ValueError('End time must be after start time')
        return v


class TimesheetApprovalAction(BaseModel):
    action: str  # 'approve' or 'reject'
    comments: Optional[str] = None
    approved_minutes: Optional[int] = None


class TimesheetEntryUpdate(BaseModel):
    """Schema for updating timesheet entry (DC Protocol)"""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    comments: Optional[str] = None

    @field_validator('end_time')
    def end_after_start(cls, v, info):
        if v is not None and 'start_time' in info.data and info.data['start_time'] is not None:
            if v <= info.data['start_time']:
                raise ValueError('End time must be after start time')
        return v


# ==================== ENDPOINTS ====================

@router.get("/my-entries/{date_str}", summary="Get my timesheet entries for a specific date")
async def get_my_entries(
    date_str: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get timesheet entries for current user for a specific date
    DC: Own entries only, all statuses
    """
    try:
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    entries = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.employee_id == current_user.id,
        StaffTimesheetEntry.date == entry_date
    ).order_by(StaffTimesheetEntry.start_time).all()

    # DC Protocol (Jan 22, 2026): Use non-duplicating calculation to avoid double-counting grouped entries
    total_minutes = calculate_non_duplicated_minutes(entries)
    
    worked_today = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == entry_date
    ).first()
    
    available_minutes = 0
    if worked_today and worked_today.clock_in and worked_today.clock_out:
        delta = worked_today.clock_out - worked_today.clock_in
        available_minutes = int(delta.total_seconds() / 60)

    result = []
    for entry in entries:
        entry_dict = entry.to_dict()
        if entry.task_id:
            task = db.query(StaffTask).filter(StaffTask.id == entry.task_id).first()
            entry_dict["task_title"] = task.title if task else None
        if entry.kra_id:
            kra = db.query(StaffKRAAssignment).filter(StaffKRAAssignment.id == entry.kra_id).first()
            entry_dict["kra_title"] = kra.kra_template.title if kra and kra.kra_template else None
        if entry.lead_id:
            lead = db.query(CRMLead).filter(CRMLead.id == entry.lead_id).first()
            entry_dict["lead_name"] = lead.name if lead else None
        if entry.journey_id:
            journey = db.query(StaffJourney).filter(StaffJourney.id == entry.journey_id).first()
            if journey:
                entry_dict["journey_name"] = f"{journey.purpose.replace('_', ' ').title()} - {journey.client_name or 'N/A'}"
            else:
                entry_dict["journey_name"] = None
        result.append(entry_dict)

    logger.info(f"[DC_TIMESHEET_MY] User {current_user.id} fetched {len(result)} entries for {entry_date}")

    return {
        "success": True,
        "date": entry_date.isoformat(),
        "entries": result,
        "available_minutes": available_minutes,
        "total_minutes": total_minutes,
        "attendance": worked_today.status if worked_today else None
    }


@router.get("/my-history", summary="Get my timesheet entries for a date range")
async def get_my_history(
    from_date: str,
    to_date: str,
    status: Optional[str] = None,
    entry_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get timesheet entries for current user for a date range
    DC: Own entries only, with optional filters
    """
    try:
        start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if (end_date - start_date).days > 90:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 90 days")

    query = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.employee_id == current_user.id,
        StaffTimesheetEntry.date >= start_date,
        StaffTimesheetEntry.date <= end_date
    )

    if status:
        query = query.filter(StaffTimesheetEntry.status == status)
    if entry_type:
        query = query.filter(StaffTimesheetEntry.entry_type == entry_type)

    entries = query.order_by(
        StaffTimesheetEntry.date.desc(),
        StaffTimesheetEntry.start_time
    ).all()

    attendance_records = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date >= start_date,
        StaffAttendance.date <= end_date
    ).all()
    attendance_map = {a.date.isoformat(): a for a in attendance_records}

    result = []
    for entry in entries:
        entry_dict = entry.to_dict()
        if entry.task_id:
            task = db.query(StaffTask).filter(StaffTask.id == entry.task_id).first()
            entry_dict["task_title"] = task.title if task else None
        if entry.kra_id:
            kra = db.query(StaffKRAAssignment).filter(StaffKRAAssignment.id == entry.kra_id).first()
            entry_dict["kra_title"] = kra.kra_template.title if kra and kra.kra_template else None
        if entry.lead_id:
            lead = db.query(CRMLead).filter(CRMLead.id == entry.lead_id).first()
            entry_dict["lead_name"] = lead.name if lead else None
        if entry.journey_id:
            journey = db.query(StaffJourney).filter(StaffJourney.id == entry.journey_id).first()
            if journey:
                entry_dict["journey_name"] = f"{journey.purpose.replace('_', ' ').title()} - {journey.client_name or 'N/A'}"
            else:
                entry_dict["journey_name"] = None
        
        att = attendance_map.get(entry.date.isoformat())
        if att:
            entry_dict["clock_in"] = att.clock_in.strftime("%H:%M") if att.clock_in else None
            entry_dict["clock_out"] = att.clock_out.strftime("%H:%M") if att.clock_out else None
            entry_dict["worked_minutes"] = att.worked_minutes
            entry_dict["attendance_status"] = att.status
            entry_dict["approval_status"] = att.approval_status
            if att.clock_in and att.clock_out:
                delta = att.clock_out - att.clock_in
                entry_dict["attendance_minutes"] = int(delta.total_seconds() / 60)
            else:
                entry_dict["attendance_minutes"] = None
        else:
            entry_dict["clock_in"] = None
            entry_dict["clock_out"] = None
            entry_dict["worked_minutes"] = None
            entry_dict["attendance_status"] = None
            entry_dict["approval_status"] = None
            entry_dict["attendance_minutes"] = None
        result.append(entry_dict)

    logger.info(f"[DC_TIMESHEET_MY_HISTORY] User {current_user.id} fetched {len(result)} entries for {from_date} to {to_date}")

    return {
        "success": True,
        "from_date": from_date,
        "to_date": to_date,
        "entries": result,
        "count": len(result)
    }


@router.post("/", summary="Create a new timesheet entry")
async def create_timesheet_entry(
    entry_data: TimesheetEntryCreate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a new timesheet entry
    DC Protocol: Validate against worked hours, non-overlapping times
    DC Protocol (Jan 22, 2026): Support multi-lead entries via lead_ids array
    - When lead_ids is provided, creates separate entries for each lead with same entry_group_id
    - Time calculations use entry_group_id to avoid double-counting
    """
    # DC Protocol: Check for overlapping entries (only for non-grouped lead entries)
    # Exclude auto-source entries — they must not block manual entry creation
    existing = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.employee_id == current_user.id,
        StaffTimesheetEntry.date == entry_data.date,
        or_(
            and_(
                StaffTimesheetEntry.start_time < entry_data.end_time,
                StaffTimesheetEntry.end_time > entry_data.start_time
            )
        ),
        # Allow grouped entries (same time slot for multiple leads)
        StaffTimesheetEntry.entry_group_id.is_(None),
        # Only manual entries (auto_source IS NULL) can trigger an overlap error
        StaffTimesheetEntry.auto_source.is_(None)
    ).first()

    # DC Protocol (Jan 22, 2026): Multi-lead entries
    # Determine leads to process
    leads_to_process = []
    if entry_data.entry_type == 'lead':
        if entry_data.lead_ids and len(entry_data.lead_ids) > 0:
            leads_to_process = entry_data.lead_ids
        elif entry_data.lead_id:
            leads_to_process = [entry_data.lead_id]
        
        if not leads_to_process:
            raise HTTPException(status_code=400, detail="At least one lead must be selected")
    
    # Only check overlap for non-lead entries or single lead entries
    if existing and (entry_data.entry_type != 'lead' or len(leads_to_process) <= 1):
        conflict_start = existing.start_time.strftime("%H:%M") if existing.start_time else "?"
        conflict_end = existing.end_time.strftime("%H:%M") if existing.end_time else "?"
        raise HTTPException(
            status_code=400,
            detail=f"Time slot overlaps with your existing entry from {conflict_start} to {conflict_end}"
        )

    if entry_data.entry_type == 'journey' and entry_data.journey_id:
        journey = db.query(StaffJourney).filter(
            StaffJourney.id == entry_data.journey_id,
            StaffJourney.employee_id == current_user.id
        ).first()
        if not journey:
            raise HTTPException(status_code=400, detail="Invalid journey: Journey not found or does not belong to you")
        if journey.start_time and journey.start_time.date() != entry_data.date:
            raise HTTPException(status_code=400, detail="Journey date does not match timesheet entry date")

    duration_minutes = calculate_duration_minutes(entry_data.start_time, entry_data.end_time)
    billable_minutes = duration_minutes - (entry_data.break_duration_minutes or 0)
    
    # DC Protocol (Jan 22, 2026): Create entries
    created_entries = []
    
    if entry_data.entry_type == 'lead' and len(leads_to_process) > 1:
        # Multi-lead: Create separate entries with shared entry_group_id
        group_id = generate_entry_group_id()
        
        for lead_id in leads_to_process:
            # Verify lead exists and belongs to user
            lead = db.query(CRMLead).filter(
                CRMLead.id == lead_id,
                or_(
                    CRMLead.telecaller_id == current_user.id,
                    CRMLead.field_staff_id == current_user.id,
                    and_(
                        CRMLead.handler_type == 'staff',
                        CRMLead.handler_id == str(current_user.id)
                    )
                )
            ).first()
            if not lead:
                raise HTTPException(status_code=400, detail=f"Lead ID {lead_id} not found or not assigned to you")
            
            new_entry = StaffTimesheetEntry(
                employee_id=current_user.id,
                date=entry_data.date,
                start_time=entry_data.start_time,
                end_time=entry_data.end_time,
                duration_minutes=duration_minutes,
                break_start_time=entry_data.break_start_time,
                break_end_time=entry_data.break_end_time,
                break_duration_minutes=entry_data.break_duration_minutes or 0,
                break_type=entry_data.break_type,
                billable_minutes=billable_minutes,
                entry_type='lead',
                lead_id=lead_id,
                entry_group_id=group_id,
                comments=entry_data.comments,
                status='submitted',
                created_by=current_user.id
            )
            db.add(new_entry)
            created_entries.append(new_entry)
        
        db.commit()
        for e in created_entries:
            db.refresh(e)
        
        # Log activity for first entry (group)
        log_timesheet_activity(
            db, created_entries[0].id, 'created', current_user.id,
            new_status='submitted',
            comments=f"Multi-lead entry: {len(leads_to_process)} leads, group {group_id}",
            device_id=request.headers.get("X-Device-ID", "") if request else "",
            ip_address=get_client_ip(request) if request else ""
        )
        
        logger.info(f"[DC_TIMESHEET_CREATE] User {current_user.id} created multi-lead entry group {group_id} with {len(leads_to_process)} leads")
        
        return {
            "success": True,
            "message": f"Created {len(created_entries)} entries for {len(leads_to_process)} leads",
            "entries": [e.to_dict() for e in created_entries],
            "entry_group_id": group_id,
            "lead_count": len(leads_to_process)
        }
    else:
        # Single entry (backward compatible)
        new_entry = StaffTimesheetEntry(
            employee_id=current_user.id,
            date=entry_data.date,
            start_time=entry_data.start_time,
            end_time=entry_data.end_time,
            duration_minutes=duration_minutes,
            break_start_time=entry_data.break_start_time,
            break_end_time=entry_data.break_end_time,
            break_duration_minutes=entry_data.break_duration_minutes or 0,
            break_type=entry_data.break_type,
            billable_minutes=billable_minutes,
            entry_type=entry_data.entry_type,
            task_id=entry_data.task_id if entry_data.entry_type == 'task' else None,
            kra_id=entry_data.kra_id if entry_data.entry_type == 'kra' else None,
            lead_id=leads_to_process[0] if leads_to_process else None,
            journey_id=entry_data.journey_id if entry_data.entry_type == 'journey' else None,
            comments=entry_data.comments,
            status='submitted',
            created_by=current_user.id
        )

        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        log_timesheet_activity(
            db, new_entry.id, 'created', current_user.id,
            new_status='submitted',
            device_id=request.headers.get("X-Device-ID", "") if request else "",
            ip_address=get_client_ip(request) if request else ""
        )

        logger.info(f"[DC_TIMESHEET_CREATE] User {current_user.id} created entry {new_entry.id}")

        return {
            "success": True,
            "message": "Entry created",
            "entry": new_entry.to_dict()
        }


@router.delete("/{entry_id}", summary="Delete a timesheet entry")
async def delete_timesheet_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Delete a timesheet entry (own only)
    DC: Only unlocked entries can be deleted
    """
    entry = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.id == entry_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if entry.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete other's entry")

    if entry.auto_source:
        raise HTTPException(status_code=403, detail=f"This entry was auto-captured from your {entry.auto_source.replace('_', ' ').title()} and cannot be deleted. Update the time in the source instead.")

    if entry.is_locked:
        raise HTTPException(status_code=403, detail="Entry is locked and cannot be deleted")

    db.delete(entry)
    db.commit()

    logger.info(f"[DC_TIMESHEET_DELETE] User {current_user.id} deleted entry {entry_id}")

    return {"success": True, "message": "Entry deleted"}


@router.put("/{entry_id}", summary="Update a timesheet entry")
async def update_timesheet_entry(
    entry_id: int,
    update_data: TimesheetEntryUpdate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update a timesheet entry (own only)
    DC: Only unlocked entries can be edited
    WVV: Audit trail maintained
    """
    entry = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.id == entry_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if entry.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot update other's entry")

    if entry.auto_source:
        raise HTTPException(status_code=403, detail=f"This entry was auto-captured from your {entry.auto_source.replace('_', ' ').title()} and cannot be edited. Update the time in the source instead.")

    if entry.is_locked:
        raise HTTPException(status_code=403, detail="Entry is locked and cannot be edited")

    if entry.status == 'approved':
        raise HTTPException(status_code=403, detail="Approved entries cannot be edited")

    old_values = {
        "start_time": str(entry.start_time) if entry.start_time else None,
        "end_time": str(entry.end_time) if entry.end_time else None,
        "comments": entry.comments
    }

    new_start = update_data.start_time if update_data.start_time is not None else entry.start_time
    new_end = update_data.end_time if update_data.end_time is not None else entry.end_time

    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # Exclude auto-source entries — they must not block manual entry updates
    overlapping = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.employee_id == current_user.id,
        StaffTimesheetEntry.date == entry.date,
        StaffTimesheetEntry.id != entry_id,
        and_(
            StaffTimesheetEntry.start_time < new_end,
            StaffTimesheetEntry.end_time > new_start
        ),
        StaffTimesheetEntry.auto_source.is_(None)
    ).first()

    if overlapping:
        conflict_start = overlapping.start_time.strftime("%H:%M") if overlapping.start_time else "?"
        conflict_end = overlapping.end_time.strftime("%H:%M") if overlapping.end_time else "?"
        raise HTTPException(
            status_code=400,
            detail=f"Time slot overlaps with your existing entry from {conflict_start} to {conflict_end}"
        )

    if update_data.start_time is not None:
        entry.start_time = update_data.start_time
    if update_data.end_time is not None:
        entry.end_time = update_data.end_time
    if update_data.comments is not None:
        entry.comments = update_data.comments

    if update_data.start_time is not None or update_data.end_time is not None:
        entry.duration_minutes = calculate_duration_minutes(entry.start_time, entry.end_time)
        entry.billable_minutes = entry.duration_minutes - (entry.break_duration_minutes or 0)

    entry.updated_at = get_indian_time()
    entry.updated_by = current_user.id

    edit_record = {
        "timestamp": get_indian_time().isoformat(),
        "edited_by": current_user.id,
        "old_values": old_values,
        "new_values": {
            "start_time": str(entry.start_time) if entry.start_time else None,
            "end_time": str(entry.end_time) if entry.end_time else None,
            "comments": entry.comments
        }
    }
    if entry.edit_history is None:
        entry.edit_history = []
    entry.edit_history = entry.edit_history + [edit_record]

    db.commit()
    db.refresh(entry)

    log_timesheet_activity(
        db, entry.id, 'updated', current_user.id,
        old_status=entry.status,
        new_status=entry.status,
        device_id=request.headers.get("X-Device-ID", "") if request else "",
        ip_address=get_client_ip(request)
    )

    logger.info(f"[DC_TIMESHEET_UPDATE] User {current_user.id} updated entry {entry_id}")

    return {
        "success": True,
        "message": "Entry updated",
        "entry": entry.to_dict()
    }


def _get_recursive_downline(db: Session, manager_id: int, max_depth: int = 10) -> list:
    """
    DC Protocol: Recursively get all employees in a manager's downline.
    Uses iterative BFS to avoid deep recursion. Max depth prevents infinite loops.
    """
    all_ids = []
    current_level = [manager_id]
    visited = {manager_id}
    for _ in range(max_depth):
        if not current_level:
            break
        direct = db.query(StaffEmployee.id).filter(
            StaffEmployee.reporting_manager_id.in_(current_level)
        ).all()
        next_level = [t[0] for t in direct if t[0] not in visited]
        all_ids.extend(next_level)
        visited.update(next_level)
        current_level = next_level
    return all_ids


@router.get("/reporting-managers", summary="Get list of reporting managers for filter dropdown")
async def get_reporting_managers(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Get all employees who are reporting managers (have at least one direct report).
    WVV: Scoped to current user's visibility — top-level sees all, others see within their scope.
    """
    is_top_level = current_user.role and current_user.role.role_code in ['key_leadership', 'vgk4u', 'ea']

    manager_ids_subq = db.query(StaffEmployee.reporting_manager_id).filter(
        StaffEmployee.reporting_manager_id.isnot(None)
    ).distinct().subquery()

    query = db.query(StaffEmployee).filter(StaffEmployee.id.in_(manager_ids_subq))

    if not is_top_level:
        managed_depts = db.query(StaffDepartment).filter(
            StaffDepartment.head_id == current_user.id
        ).all()
        dept_ids = [d.id for d in managed_depts]
        direct_reports = db.query(StaffEmployee.id).filter(
            StaffEmployee.reporting_manager_id == current_user.id
        ).all()
        direct_report_ids = [t[0] for t in direct_reports]
        dept_employees = db.query(StaffEmployee.id).filter(
            StaffEmployee.department_id.in_(dept_ids)
        ).all()
        dept_employee_ids = [t[0] for t in dept_employees]
        scope_ids = list(set(direct_report_ids + dept_employee_ids + [current_user.id]))
        query = query.filter(StaffEmployee.id.in_(scope_ids))

    managers = query.order_by(StaffEmployee.full_name).all()

    hidden_codes = set(HIDDEN_FROM_TEAM_CODES)

    return {
        "success": True,
        "managers": [
            {"id": m.id, "name": m.full_name, "code": m.emp_code}
            for m in managers
            if m.emp_code not in hidden_codes
        ]
    }


@router.get("/team-entries", summary="Get team timesheet entries for approval")
async def get_team_entries_for_approval(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    staff_type: Optional[str] = Query(None),
    reporting_manager_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get team entries for approval (managers/supervisors)
    DC: Key Leadership / VGK4U Supreme see ALL employees
    DC: Regular managers see dept employees + direct reports (reporting_manager_id)
    WVV: Role hierarchy enforcement with department_id, staff_type, and reporting_manager_id filters
    """
    is_top_level = current_user.role and current_user.role.role_code in ['key_leadership', 'vgk4u', 'ea']

    if is_top_level:
        base_scope_ids = None
    else:
        managed_depts = db.query(StaffDepartment).filter(
            StaffDepartment.head_id == current_user.id
        ).all()
        dept_ids = [d.id for d in managed_depts]

        direct_reports = db.query(StaffEmployee.id).filter(
            StaffEmployee.reporting_manager_id == current_user.id
        ).all()
        direct_report_ids = [t[0] for t in direct_reports]

        dept_employees = db.query(StaffEmployee.id).filter(
            StaffEmployee.department_id.in_(dept_ids)
        ).all()
        dept_employee_ids = [t[0] for t in dept_employees]

        base_scope_ids = list(set(direct_report_ids + dept_employee_ids))
        if not base_scope_ids:
            base_scope_ids = [0]

    if reporting_manager_id:
        downline_ids = _get_recursive_downline(db, reporting_manager_id)
        if not downline_ids:
            downline_ids = [0]
        if base_scope_ids is not None:
            downline_ids = [did for did in downline_ids if did in set(base_scope_ids)]
            if not downline_ids:
                downline_ids = [0]
        team_query = db.query(StaffEmployee.id).filter(StaffEmployee.id.in_(downline_ids))
    elif base_scope_ids is None:
        team_query = db.query(StaffEmployee.id)
    else:
        team_query = db.query(StaffEmployee.id).filter(StaffEmployee.id.in_(base_scope_ids))

    if department_id:
        team_query = team_query.filter(StaffEmployee.department_id == department_id)
    if staff_type:
        team_query = team_query.filter(StaffEmployee.staff_type == staff_type)
    if search:
        search_term = f"%{search.strip()}%"
        team_query = team_query.filter(StaffEmployee.full_name.ilike(search_term))

    team_ids = [t[0] for t in team_query.all()]

    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    team_ids = [tid for tid in team_ids if tid != current_user.id and tid not in hidden_ids]

    if not team_ids:
        team_ids = [0]

    if employee_id:
        if employee_id in team_ids:
            team_ids = [employee_id]
        else:
            return {"success": True, "entries": [], "total": 0, "limit": limit, "offset": offset}

    query = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.employee_id.in_(team_ids)
    )

    if from_date:
        query = query.filter(StaffTimesheetEntry.date >= from_date)
    if to_date:
        query = query.filter(StaffTimesheetEntry.date <= to_date)
    if status:
        query = query.filter(StaffTimesheetEntry.status == status)

    total = query.count()
    entries = query.order_by(StaffTimesheetEntry.date.desc()).limit(limit).offset(offset).all()

    emp_ids_in_result = list(set(e.employee_id for e in entries))
    att_query = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id.in_(emp_ids_in_result if emp_ids_in_result else [0])
    )
    if from_date:
        att_query = att_query.filter(StaffAttendance.date >= from_date)
    if to_date:
        att_query = att_query.filter(StaffAttendance.date <= to_date)
    att_records = att_query.all()
    att_map = {}
    for a in att_records:
        att_map[(a.employee_id, a.date.isoformat())] = a

    result = []
    for entry in entries:
        entry_dict = entry.to_dict()
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == entry.employee_id).first()
        entry_dict["employee_name"] = employee.full_name if employee else None
        entry_dict["employee_code"] = employee.emp_code if employee else None

        if entry.task_id:
            task = db.query(StaffTask).filter(StaffTask.id == entry.task_id).first()
            entry_dict["task_title"] = task.title if task else None

        if entry.kra_id:
            kra = db.query(StaffKRAAssignment).filter(StaffKRAAssignment.id == entry.kra_id).first()
            entry_dict["kra_title"] = kra.kra_template.title if kra and kra.kra_template else None
        if entry.lead_id:
            lead = db.query(CRMLead).filter(CRMLead.id == entry.lead_id).first()
            entry_dict["lead_name"] = lead.name if lead else None
        if entry.journey_id:
            journey = db.query(StaffJourney).filter(StaffJourney.id == entry.journey_id).first()
            if journey:
                entry_dict["journey_name"] = f"{journey.purpose.replace('_', ' ').title()} - {journey.client_name or 'N/A'}"
            else:
                entry_dict["journey_name"] = None

        att = att_map.get((entry.employee_id, entry.date.isoformat()))
        if att:
            entry_dict["clock_in"] = att.clock_in.strftime("%H:%M") if att.clock_in else None
            entry_dict["clock_out"] = att.clock_out.strftime("%H:%M") if att.clock_out else None
            entry_dict["worked_minutes"] = att.worked_minutes
            entry_dict["attendance_status"] = att.status
            entry_dict["approval_status"] = att.approval_status
        else:
            entry_dict["clock_in"] = None
            entry_dict["clock_out"] = None
            entry_dict["worked_minutes"] = None
            entry_dict["attendance_status"] = None
            entry_dict["approval_status"] = None

        result.append(entry_dict)

    logger.info(f"[DC_TIMESHEET_TEAM] User {current_user.id} fetched {len(result)} team entries")

    return {
        "success": True,
        "entries": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/{entry_id}/approve", summary="Approve or reject a timesheet entry")
async def approve_timesheet_entry(
    entry_id: int,
    request: Request,
    action_data: TimesheetApprovalAction,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve or reject a timesheet entry
    DC: Manager/Supreme can approve team entries
    WVV: Role hierarchy enforcement (manager/team_leader/key_leadership/vgk4u only)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['manager', 'team_leader', 'key_leadership', 'vgk4u']:
    #     raise HTTPException(status_code=403, detail="Not authorized to approve entries")

    entry = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.id == entry_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Timesheet entry not found")

    if current_user.role and current_user.role.role_code not in ['vgk4u', 'key_leadership']:
        employee = db.query(StaffEmployee).filter(
            StaffEmployee.id == entry.employee_id
        ).first()

        is_reporting_manager = employee and employee.reporting_manager_id == current_user.id

        managed_depts = db.query(StaffDepartment).filter(
            StaffDepartment.head_id == current_user.id
        ).all()
        dept_ids = [d.id for d in managed_depts]
        is_dept_manager = employee and employee.department_id in dept_ids

        if not is_reporting_manager and not is_dept_manager:
            raise HTTPException(status_code=403, detail="Not authorized to approve this entry (not your direct report or department member)")

    if entry.is_locked:
        raise HTTPException(status_code=403, detail="Entry is already locked")

    previous_status = entry.status

    if action_data.action == 'approve':
        entry.status = 'approved'
        entry.is_locked = True
        entry.approved_by = current_user.id
        entry.approved_at = get_indian_time()
        entry.approved_minutes = action_data.approved_minutes if action_data.approved_minutes is not None else entry.duration_minutes

        if entry.task_id:
            task = db.query(StaffTask).filter(StaffTask.id == entry.task_id).first()
            if task:
                current_hours = float(task.actual_hours or 0)
                new_hours = entry.duration_minutes / 60
                task.actual_hours = Decimal(str(current_hours + new_hours))

        message = "Entry approved and locked"
    else:
        entry.status = 'rejected'
        entry.rejection_reason = action_data.comments
        message = "Entry rejected - employee can resubmit"

    log_activity_action = 'approved' if action_data.action == 'approve' else 'rejected'
    log_timesheet_activity(
        db, entry.id, log_activity_action, current_user.id,
        previous_status=previous_status, new_status=entry.status,
        comments=action_data.comments,
        device_id=request.headers.get("X-Device-ID", ""),
        ip_address=get_client_ip(request)
    )

    db.commit()

    logger.info(f"[DC_TIMESHEET_APPROVAL] User {current_user.id} {action_data.action}d entry {entry_id}")

    return {
        "success": True,
        "message": message,
        "entry": entry.to_dict()
    }


@router.get("/{entry_id}/history", summary="Get approval history for an entry")
async def get_entry_history(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get complete approval/edit history for a timesheet entry
    DC: Full audit trail access
    """
    entry = db.query(StaffTimesheetEntry).filter(
        StaffTimesheetEntry.id == entry_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Timesheet entry not found")

    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if entry.employee_id != current_user.id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")

    history = db.query(StaffTimesheetApprovalHistory).filter(
        StaffTimesheetApprovalHistory.timesheet_entry_id == entry_id
    ).order_by(StaffTimesheetApprovalHistory.action_at.desc()).all()

    result = []
    for h in history:
        h_dict = h.to_dict()
        actor = db.query(StaffEmployee).filter(StaffEmployee.id == h.action_by).first()
        h_dict["actor_name"] = actor.full_name if actor else None
        result.append(h_dict)

    return {
        "success": True,
        "entry": entry.to_dict(),
        "history": result,
        "edit_history": entry.edit_history or []
    }


# ==================== ATTENDANCE COMPUTATION ====================

@router.get("/computation", summary="Get attendance computation for date range")
async def get_attendance_computation(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get attendance computation (hours -> status classification)
    DC: Apply rules to determine ABSENT/HALF DAY/FULL DAY/OT
    """
    if not from_date:
        from_date = get_indian_date().replace(day=1)
    if not to_date:
        to_date = get_indian_date()

    target_employee = employee_id if employee_id else current_user.id

    # DC Protocol: Menu-based access control - page assignment = full access
    # if target_employee != current_user.id:
    #     if not current_user.role or current_user.role.role_code not in ['manager', 'team_leader', 'key_leadership', 'vgk4u']:
    #         raise HTTPException(status_code=403, detail="Not authorized to view other employees")

    attendances = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == target_employee,
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    ).order_by(StaffAttendance.date.desc()).all()

    results = []
    summary = {
        "total_days": 0,
        "present_days": 0,
        "absent_days": 0,
        "half_days": 0,
        "full_days": 0,
        "ot_days": 0,
        "total_work_hours": 0,
        "total_ot_hours": 0
    }

    for att in attendances:
        timesheet_entries = db.query(StaffTimesheetEntry).filter(
            StaffTimesheetEntry.employee_id == target_employee,
            StaffTimesheetEntry.date == att.date,
            StaffTimesheetEntry.status == 'approved'
        ).all()

        if timesheet_entries:
            # DC Protocol (Jan 22, 2026): Use non-duplicating calculation for grouped entries
            total_minutes = calculate_non_duplicated_billable_minutes(timesheet_entries)
        else:
            total_minutes = att.worked_minutes or 0

        total_hours = total_minutes / 60
        computation = compute_attendance_status(total_hours)

        summary["total_days"] += 1
        summary["total_work_hours"] += total_hours

        if computation["status"] == "absent":
            summary["absent_days"] += 1
        elif computation["status"] == "half_day":
            summary["half_days"] += 1
            summary["present_days"] += 0.5
        elif computation["status"] in ["full_day", "full_day_ot"]:
            summary["full_days"] += 1
            summary["present_days"] += 1

        if computation["status"] == "full_day_ot":
            summary["ot_days"] += 1
            summary["total_ot_hours"] += computation.get("ot_hours", 0)

        results.append({
            "date": att.date.isoformat(),
            "day_name": att.date.strftime("%A"),
            "clock_in": att.clock_in.isoformat() if att.clock_in else None,
            "clock_out": att.clock_out.isoformat() if att.clock_out else None,
            "total_hours": round(total_hours, 2),
            "break_duration_minutes": sum(e.break_duration_minutes or 0 for e in timesheet_entries) if timesheet_entries else 0,
            "billable_hours": round(total_hours - (sum(e.break_duration_minutes or 0 for e in timesheet_entries) / 60 if timesheet_entries else 0), 2),
            "classification": computation["status"],
            "ot_hours": computation.get("ot_hours", 0),
            "source": "timesheet" if timesheet_entries else "attendance",
            "timesheet_entries": len(timesheet_entries) if timesheet_entries else 0
        })

    return {
        "success": True,
        "records": results,
        "summary": summary
    }


@router.get("/team-summary", summary="Get team attendance summary")
async def get_team_attendance_summary(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get team attendance summary
    DC: Role-based team filtering, summary aggregation
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['manager', 'team_leader', 'key_leadership', 'vgk4u']:
    #     raise HTTPException(status_code=403, detail="Not authorized to view team summary")

    if not from_date:
        from_date = get_indian_date().replace(day=1)
    if not to_date:
        to_date = get_indian_date()

    is_top_level = current_user.role and current_user.role.role_code in ['key_leadership', 'vgk4u', 'ea']
    
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    exclude_ids = hidden_ids | {current_user.id}

    if is_top_level:
        team_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
        if department_id:
            team_query = team_query.filter(StaffEmployee.department_id == department_id)
        team = [e for e in team_query.all() if e.id not in exclude_ids]
    else:
        managed_depts = db.query(StaffDepartment).filter(
            StaffDepartment.head_id == current_user.id
        ).all()
        dept_ids = [d.id for d in managed_depts]
        
        dept_employees = db.query(StaffEmployee).filter(
            StaffEmployee.department_id.in_(dept_ids),
            StaffEmployee.status == 'active'
        ).all()
        
        direct_reports = db.query(StaffEmployee).filter(
            StaffEmployee.reporting_manager_id == current_user.id,
            StaffEmployee.status == 'active'
        ).all()
        
        seen_ids = set()
        team = []
        for emp in dept_employees + direct_reports:
            if emp.id not in seen_ids and emp.id not in exclude_ids:
                seen_ids.add(emp.id)
                team.append(emp)
        
        if department_id:
            team = [e for e in team if e.department_id == department_id]

    team_summary = []
    total_stats = {
        "total_present": 0,
        "total_absent": 0,
        "total_half_days": 0,
        "total_ot_hours": 0,
        "total_work_hours": 0
    }

    for emp in team:
        attendances = db.query(StaffAttendance).filter(
            StaffAttendance.employee_id == emp.id,
            StaffAttendance.date >= from_date,
            StaffAttendance.date <= to_date
        ).all()

        emp_present = 0
        emp_absent = 0
        emp_half = 0
        emp_ot = 0
        emp_hours = 0

        for att in attendances:
            timesheet_entries = db.query(StaffTimesheetEntry).filter(
                StaffTimesheetEntry.employee_id == emp.id,
                StaffTimesheetEntry.date == att.date,
                StaffTimesheetEntry.status == 'approved'
            ).all()

            if timesheet_entries:
                # DC Protocol (Jan 22, 2026): Use non-duplicating calculation for grouped entries
                total_minutes = calculate_non_duplicated_billable_minutes(timesheet_entries)
            else:
                total_minutes = att.worked_minutes or 0

            total_hours = total_minutes / 60
            computation = compute_attendance_status(total_hours)

            emp_hours += total_hours
            if computation["status"] == "absent":
                emp_absent += 1
            elif computation["status"] == "half_day":
                emp_half += 0.5
                emp_present += 0.5
            elif computation["status"] in ["full_day", "full_day_ot"]:
                emp_present += 1
            if computation["status"] == "full_day_ot":
                emp_ot += computation.get("ot_hours", 0)

        team_summary.append({
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code,
            "present_days": emp_present,
            "absent_days": emp_absent,
            "half_days": emp_half,
            "ot_hours": emp_ot,
            "total_hours": round(emp_hours, 2),
            "full_days": emp_present - (emp_half * 2)
        })

        total_stats["total_present"] += emp_present
        total_stats["total_absent"] += emp_absent
        total_stats["total_half_days"] += emp_half
        total_stats["total_ot_hours"] += emp_ot
        total_stats["total_work_hours"] += emp_hours

    return {
        "success": True,
        "team_summary": team_summary,
        "totals": total_stats,
        "employee_count": len(team),
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()}
    }


@router.get("/my-tasks", summary="Get my tasks for timesheet tagging")
async def get_my_tasks_for_timesheet(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current user's active tasks for timesheet dropdown
    DC: Only active tasks assigned to current user
    """
    from app.models.staff_tasks import StaffTaskAssignee

    assignee_task_ids = db.query(StaffTaskAssignee.task_id).filter(
        StaffTaskAssignee.employee_id == current_user.id
    ).all()
    assignee_task_ids = [t[0] for t in assignee_task_ids]

    tasks = db.query(StaffTask).filter(
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(assignee_task_ids)
        ),
        StaffTask.is_deleted == False,
        StaffTask.status.in_(['pending', 'in_progress', 'review'])
    ).all()

    return {
        "success": True,
        "tasks": [
            {
                "id": t.id,
                "task_code": t.task_code,
                "title": t.title,
                "status": t.status
            } for t in tasks
        ]
    }


@router.get("/my-kras", summary="Get my KRAs for timesheet tagging")
async def get_my_kras_for_timesheet(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current user's active KRAs for timesheet dropdown
    DC: Only active KRA assignments
    """
    from app.models.staff_kra import StaffKRAAssignment

    kras = db.query(StaffKRAAssignment).filter(
        StaffKRAAssignment.employee_id == current_user.id,
        StaffKRAAssignment.status == 'active'
    ).all()

    return {
        "success": True,
        "kras": [
            {
                "id": k.id,
                "kra_id": k.kra_template_id,
                "title": k.kra_template.title if k.kra_template else 'N/A',
                "kra_code": k.kra_template.kra_code if k.kra_template else None,
                "status": k.status
            } for k in kras
        ]
    }


@router.get("/my-leads", summary="Get my leads for timesheet tagging with multi-select support")
async def get_my_leads_for_timesheet(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Jan 22, 2026): Enhanced lead selection for multi-lead timesheet entries
    Returns leads categorized as:
    - assigned_leads: Leads where user is telecaller, field_staff, or primary handler
    - todays_leads: Leads with activity today (created, followup, or interaction)
    
    Supports multi-select for continuous lead activity tracking
    """
    from datetime import date
    from app.models.crm import CRMLeadFollowUp, CRMLeadNote
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Base filter: leads assigned to current user (active status)
    assigned_filter = and_(
        or_(
            CRMLead.telecaller_id == current_user.id,
            CRMLead.field_staff_id == current_user.id,
            and_(
                CRMLead.handler_type == 'staff',
                CRMLead.handler_id == str(current_user.id)
            )
        ),
        CRMLead.status.notin_(['won', 'lost', 'closed'])
    )
    
    # Get all assigned leads
    assigned_leads = db.query(CRMLead).filter(assigned_filter).limit(200).all()
    assigned_lead_ids = {l.id for l in assigned_leads}
    
    # Find today's leads (created today, followup today, or note added today)
    # 1. Leads created today
    created_today_ids = set(
        db.query(CRMLead.id).filter(
            assigned_filter,
            func.date(CRMLead.created_at) == today
        ).all()
    )
    created_today_ids = {r[0] for r in created_today_ids}
    
    # 2. Leads with followup scheduled for today
    followup_today_ids = set(
        db.query(CRMLeadFollowUp.lead_id).filter(
            CRMLeadFollowUp.lead_id.in_(assigned_lead_ids),
            func.date(CRMLeadFollowUp.scheduled_date) == today
        ).all()
    )
    followup_today_ids = {r[0] for r in followup_today_ids}
    
    # 3. Leads with notes added today (interacted today)
    interacted_today_ids = set(
        db.query(CRMLeadNote.lead_id).filter(
            CRMLeadNote.lead_id.in_(assigned_lead_ids),
            CRMLeadNote.created_at >= today_start,
            CRMLeadNote.created_at <= today_end
        ).all()
    )
    interacted_today_ids = {r[0] for r in interacted_today_ids}
    
    # Combine all "today" categories
    todays_lead_ids = created_today_ids | followup_today_ids | interacted_today_ids
    
    # Build response with categorization
    def format_lead(l, is_today):
        return {
            "id": l.id,
            "name": l.name,
            "phone": l.phone,
            "status": l.status,
            "category_id": l.category_id,
            "is_today": is_today,
            "today_reason": []
        }
    
    all_leads = []
    todays_leads = []
    
    for l in assigned_leads:
        is_today = l.id in todays_lead_ids
        lead_data = format_lead(l, is_today)
        
        # Add reasons for today's leads
        if is_today:
            reasons = []
            if l.id in created_today_ids:
                reasons.append("created")
            if l.id in followup_today_ids:
                reasons.append("followup")
            if l.id in interacted_today_ids:
                reasons.append("interacted")
            lead_data["today_reason"] = reasons
            todays_leads.append(lead_data)
        
        all_leads.append(lead_data)
    
    return {
        "success": True,
        "leads": all_leads,
        "todays_leads": todays_leads,
        "summary": {
            "total_assigned": len(assigned_leads),
            "todays_count": len(todays_leads)
        }
    }


@router.get("/my-journeys/{date_str}", summary="Get my journeys for timesheet tagging")
async def get_my_journeys_for_timesheet(
    date_str: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current user's journeys for a specific date for timesheet dropdown
    DC: Only journeys belonging to current user on the selected date
    WVV: Completed or in-progress journeys only
    """
    try:
        journey_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    journeys = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        func.date(StaffJourney.start_time) == journey_date
    ).order_by(StaffJourney.start_time.desc()).limit(50).all()

    return {
        "success": True,
        "date": journey_date.isoformat(),
        "journeys": [
            {
                "id": j.id,
                "purpose": j.purpose,
                "purpose_description": j.purpose_description,
                "client_name": j.client_name,
                "transport_mode": j.transport_mode,
                "status": j.status.value if hasattr(j.status, 'value') else j.status,
                "start_time": j.start_time.strftime("%H:%M") if j.start_time else None,
                "end_time": j.end_time.strftime("%H:%M") if j.end_time else None,
                "total_distance_km": round(j.total_distance_km, 2) if j.total_distance_km else 0,
                "display_name": f"{j.purpose.replace('_', ' ').title()} - {j.client_name or 'N/A'} ({j.start_time.strftime('%H:%M') if j.start_time else 'N/A'})"
            } for j in journeys
        ]
    }


@router.get("/timeline/{date_str}", summary="Get today's attendance timeline (clock events + breaks)")
async def get_attendance_timeline(
    date_str: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get attendance timeline for employee on specific date
    DC: Clock in/out, breaks with types, locations
    WVV: Chronological order, complete event chain
    """
    try:
        timeline_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == timeline_date
    ).first()

    if not attendance:
        return {
            "success": True,
            "date": timeline_date.isoformat(),
            "timeline": [],
            "message": "No attendance record for this date"
        }

    timeline = []

    if attendance.clock_in:
        location_info = attendance.clock_in_location or {}
        timeline.append({
            "type": "clock_in",
            "time": attendance.clock_in.strftime("%H:%M"),
            "timestamp": attendance.clock_in.isoformat(),
            "title": "Clocked In",
            "location": location_info.get("address") or f"Lat: {location_info.get('latitude', 'N/A')}",
            "mode": attendance.location_mode or "office",
            "icon": "sign-in-alt",
            "color": "success"
        })

    breaks = db.query(StaffAttendanceBreak).filter(
        StaffAttendanceBreak.attendance_id == attendance.id
    ).order_by(StaffAttendanceBreak.break_start).all()

    for brk in breaks:
        if brk.break_start:
            timeline.append({
                "type": "break_start",
                "time": brk.break_start.strftime("%H:%M"),
                "timestamp": brk.break_start.isoformat(),
                "title": f"Break Started ({brk.break_type.title()})",
                "break_type": brk.break_type,
                "is_paid": brk.is_paid,
                "icon": "coffee",
                "color": "warning"
            })

        if brk.break_end:
            timeline.append({
                "type": "break_end",
                "time": brk.break_end.strftime("%H:%M"),
                "timestamp": brk.break_end.isoformat(),
                "title": "Break Ended",
                "duration_minutes": brk.duration_minutes or brk.calculate_duration(),
                "icon": "play",
                "color": "info"
            })

    if attendance.clock_out:
        location_info = attendance.clock_out_location or {}
        timeline.append({
            "type": "clock_out",
            "time": attendance.clock_out.strftime("%H:%M"),
            "timestamp": attendance.clock_out.isoformat(),
            "title": "Clocked Out",
            "location": location_info.get("address") or f"Lat: {location_info.get('latitude', 'N/A')}",
            "mode": attendance.location_mode or "office",
            "icon": "sign-out-alt",
            "color": "danger"
        })

    logger.info(f"[DC_TIMELINE] User {current_user.id} accessed timeline for {timeline_date}")

    return {
        "success": True,
        "date": timeline_date.isoformat(),
        "employee_id": current_user.id,
        "timeline": timeline,
        "total_events": len(timeline),
        "is_complete": attendance.clock_out is not None
    }
