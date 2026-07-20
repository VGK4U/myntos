"""
Staff Attendance Sheet API Endpoints (DC Protocol Compliant)
Bulk marking system for HR/EA/VGK with monthly reporting

Key Features:
- Mark attendance (HR role)
- Approve hours (EA/VGK role)
- Monthly data with date columns
- Reconciliation with timesheet
- Dynamic filters (Manager, Department, Team, Role)
- Custom alerts

Created: Dec 01, 2025
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz
import logging

# DC-TIMEREPORT-GEOCODE-001: Process-level reverse-geocode cache (lat/lng → address string)
# Keyed at ~100m precision (3 decimal places). Survives for process lifetime.
_geocode_cache: dict = {}

def _nominatim_reverse(lat: float, lng: float) -> Optional[str]:
    """Call Nominatim reverse-geocode with a process-level cache. Returns a short
    human-readable name like 'MVP Colony, Visakhapatnam' or None on failure."""
    key = (round(lat, 3), round(lng, 3))
    if key in _geocode_cache:
        return _geocode_cache[key]
    try:
        import requests as _req
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?format=json&lat={lat}&lon={lng}&zoom=16&addressdetails=1"
        )
        r = _req.get(url, headers={"User-Agent": "MyntReal-Staff-App/1.0"}, timeout=3)
        if r.status_code == 200:
            data = r.json()
            addr = data.get("address", {})
            parts = []
            for field in ["road", "neighbourhood", "suburb", "quarter",
                          "city_district", "city", "town", "village"]:
                val = addr.get(field)
                if val:
                    parts.append(val)
                    if len(parts) >= 2:
                        break
            result = ", ".join(parts) if parts else data.get("display_name", "")[:80]
            _geocode_cache[key] = result or None
            return _geocode_cache[key]
    except Exception:
        pass
    _geocode_cache[key] = None   # cache failures too
    return None

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffDepartment
from app.models.staff_attendance_sheet import (
    StaffAttendanceSheet, StaffAttendanceSheetAudit, StaffAttendanceException,
    AttendanceStatus, ApprovalStatus, ReconciliationStatus, ExceptionBypassType
)
from app.models.staff_timesheet import StaffTimesheetEntry
from app.models.staff_attendance import StaffAttendance
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.staff_hierarchy import get_accessible_employee_ids, get_team_member_ids

logger = logging.getLogger(__name__)
router = APIRouter()


def get_indian_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


# ==================== SCHEMAS ====================

class AttendanceSheetCreate(BaseModel):
    date: date
    employee_id: int
    attendance_status: AttendanceStatus
    notes: Optional[str] = None


class AttendanceSheetApprove(BaseModel):
    approved_hours: Decimal
    approval_reason: Optional[str] = None
    new_attendance_status: Optional[str] = None  # EA/VGK can change status (present, half_day, etc.)
    # DC Protocol (Jan 01, 2026): Exception bypass for EA/VGK
    bypass_exception: Optional[bool] = False  # True = bypass no-timesheet check
    exception_reason: Optional[str] = None  # Mandatory when bypass_exception=True


class BulkApproveRequest(BaseModel):
    month_year: str
    department_id: Optional[int] = None
    manager_id: Optional[int] = None


class AttendanceSheetEdit(BaseModel):
    """Schema for EA/VGK to directly edit attendance status"""
    new_attendance_status: str  # present, half_day, absent, leave types, etc.
    edit_reason: str  # Required: reason for the edit


class AttendanceSheetResponse(BaseModel):
    id: int
    date: date
    employee_id: int
    attendance_status: AttendanceStatus
    marked_hours: float
    approved_hours: Optional[float]
    approval_status: ApprovalStatus
    net_days: float
    reconciliation_status: ReconciliationStatus
    notes: Optional[str]

    class Config:
        from_attributes = True


# ==================== ENDPOINTS ====================

@router.post("/mark", summary="Mark attendance (HR/EA/VGK only)")
def mark_attendance(
    data: AttendanceSheetCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """HR marks attendance for an employee"""
    
    # Authorization check
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['hr', 'ea', 'vgk4u']:
    #     raise HTTPException(status_code=403, detail="Only HR/EA/VGK can mark attendance")
    
    # Validate employee exists
    employee = db.query(StaffEmployee).filter_by(id=data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate marked hours based on status
    marked_hours_map = {
        AttendanceStatus.PRESENT: 8,
        AttendanceStatus.HALF_DAY: 4,
        AttendanceStatus.ABSENT: 0,
        AttendanceStatus.SICK_LEAVE: 0,
        AttendanceStatus.APPROVED_LEAVE: 0,
        AttendanceStatus.CASUAL_LEAVE: 0,
        AttendanceStatus.UNPAID_LEAVE: 0,
    }
    marked_hours = Decimal(str(marked_hours_map.get(data.attendance_status, 0)))
    
    # DC PROTOCOL - RECONCILIATION LOGIC (Issue #7)
    # Check employee timesheet for the date (breaks excluded = billable hours)
    timesheet_entries = db.query(StaffTimesheetEntry).filter_by(
        employee_id=data.employee_id,
        date=data.date
    ).all()
    
    # Calculate actual billable hours from timesheet
    actual_hours = Decimal(0)
    reconciliation_status = ReconciliationStatus.NO_ENTRY
    employee_actual_hours = None
    
    if timesheet_entries:
        # Sum all entries for the day, excluding breaks
        total_minutes = sum(entry.duration_minutes - entry.break_duration_minutes for entry in timesheet_entries)
        actual_hours = Decimal(str(total_minutes / 60))  # Convert minutes to hours
        employee_actual_hours = actual_hours
        
        # Reconciliation tolerance: ±0.5 hours (30 minutes)
        tolerance = Decimal('0.5')
        difference = abs(marked_hours - actual_hours)
        
        if difference <= tolerance:
            reconciliation_status = ReconciliationStatus.MATCHED
        else:
            reconciliation_status = ReconciliationStatus.MISMATCH_WARNING
    else:
        # No timesheet entry for this date
        reconciliation_status = ReconciliationStatus.NO_ENTRY
    
    # Check if already marked for this date
    existing = db.query(StaffAttendanceSheet).filter_by(
        date=data.date,
        employee_id=data.employee_id
    ).first()
    
    if existing:
        # Update existing
        existing.attendance_status = data.attendance_status
        existing.marked_hours = marked_hours
        existing.marked_by_id = current_user.id
        existing.marked_at = datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
        existing.employee_actual_hours = employee_actual_hours
        existing.reconciliation_status = reconciliation_status
        existing.notes = data.notes
        db.add(existing)
        sheet = existing
    else:
        # Create new
        # [DC_DAR_003 / Task #53] Tag company_id from the employee so the row
        # counts toward that company in the DAR Staff Attendance section.
        _emp_cid = db.query(StaffEmployee.base_company_id).filter(
            StaffEmployee.id == data.employee_id
        ).scalar()
        sheet = StaffAttendanceSheet(
            date=data.date,
            employee_id=data.employee_id,
            attendance_status=data.attendance_status,
            marked_hours=marked_hours,
            marked_by_id=current_user.id,
            employee_actual_hours=employee_actual_hours,
            reconciliation_status=reconciliation_status,
            net_days=0,
            notes=data.notes,
            company_id=_emp_cid,
        )
        db.add(sheet)
    
    # Audit log
    audit = StaffAttendanceSheetAudit(
        attendance_sheet=sheet,
        changed_by_id=current_user.id,
        changed_by_role=current_user.role.role_code,
        change_type="marked",
        field_changed="attendance_status,marked_hours",
        new_value={
            "status": data.attendance_status.value,
            "marked_hours": str(marked_hours)
        },
        reason="HR marked attendance"
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "attendance_id": sheet.id, "marked_hours": float(marked_hours)}


@router.post("/{sheet_id}/approve", summary="Approve attendance hours (EA/VGK only)")
def approve_attendance(
    sheet_id: int,
    data: AttendanceSheetApprove,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    EA/VGK approves hours for attendance marking.
    
    DC Protocol (Dec 04, 2025):
    - BLOCKS approval if reconciliation_status = NO_ENTRY (no timesheet)
    - Validates 30-min tolerance between timesheet and marked hours
    - Allows EA/VGK to change attendance status during approval
    """
    
    # Authorization check
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['ea', 'vgk4u']:
    #     raise HTTPException(status_code=403, detail="Only EA/VGK can approve attendance")
    
    sheet = db.query(StaffAttendanceSheet).filter_by(id=sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Attendance sheet not found")
    
    # DC PROTOCOL (Jan 01, 2026): Exception bypass for EA/VGK when no timesheet
    exception_record = None
    if sheet.reconciliation_status == ReconciliationStatus.NO_ENTRY:
        if data.bypass_exception:
            # Validate bypass request
            if not data.exception_reason or len(data.exception_reason.strip()) < 10:
                raise HTTPException(
                    status_code=400,
                    detail="Exception bypass requires a reason (minimum 10 characters)"
                )
            
            # Get employee's company_id for DC Protocol compliance
            employee = db.query(StaffEmployee).filter_by(id=sheet.employee_id).first()
            if not employee:
                raise HTTPException(status_code=404, detail="Employee not found")
            
            # Create exception record for audit trail
            reconciliation_snapshot = {
                "marked_hours": float(sheet.marked_hours),
                "timesheet_hours": None,
                "reconciliation_status": sheet.reconciliation_status.value,
                "marked_status": sheet.attendance_status.value
            }
            
            exception_record = StaffAttendanceException(
                company_id=employee.base_company_id,
                attendance_sheet_id=sheet.id,
                employee_id=sheet.employee_id,
                date=sheet.date,
                bypass_type=ExceptionBypassType.NO_TIMESHEET,
                exception_reason=data.exception_reason.strip(),
                approver_id=current_user.id,
                approver_role=current_user.role.role_code,
                reconciliation_snapshot=reconciliation_snapshot,
                approved_hours=data.approved_hours
            )
            
            # Set exception fields on attendance sheet
            sheet.exception_bypass = True
            sheet.exception_reason = data.exception_reason.strip()
            sheet.exception_approved_at = datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
            sheet.exception_approved_by_id = current_user.id
            
            # Set reconciliation to manual override since bypassed
            sheet.reconciliation_status = ReconciliationStatus.MANUAL_OVERRIDE
            
            logger.info(f"Exception bypass granted by {current_user.role.role_code} for sheet {sheet_id}")
        else:
            # Standard block - no bypass requested
            raise HTTPException(
                status_code=400, 
                detail="Cannot approve: Employee has no timesheet entry for this date. Employee must submit timesheet first."
            )
    
    # Track old values for audit
    old_status = sheet.attendance_status.value
    old_marked_hours = float(sheet.marked_hours)
    status_was_changed = False
    
    # EA/VGK can change attendance status during approval
    # IMPORTANT: Process status change FIRST, then validate tolerance
    if data.new_attendance_status:
        try:
            new_status = AttendanceStatus(data.new_attendance_status)
            if new_status != sheet.attendance_status:
                status_was_changed = True
                sheet.attendance_status = new_status
                
                # Recalculate marked hours based on new status
                marked_hours_map = {
                    AttendanceStatus.PRESENT: Decimal('8'),
                    AttendanceStatus.HALF_DAY: Decimal('4'),
                    AttendanceStatus.ABSENT: Decimal('0'),
                    AttendanceStatus.SICK_LEAVE: Decimal('0'),
                    AttendanceStatus.APPROVED_LEAVE: Decimal('0'),
                    AttendanceStatus.CASUAL_LEAVE: Decimal('0'),
                    AttendanceStatus.UNPAID_LEAVE: Decimal('0'),
                    AttendanceStatus.HOLIDAY: Decimal('8'),
                    AttendanceStatus.WEEKEND: Decimal('0'),
                }
                sheet.marked_hours = marked_hours_map.get(new_status, Decimal('0'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid attendance status: {data.new_attendance_status}")
    
    # DC PROTOCOL: 30-minute tolerance validation (AFTER status change)
    # Check if timesheet hours are within 30 mins (0.5 hours) of marked hours
    tolerance = Decimal('0.5')  # 30 minutes
    is_mismatch = False
    
    if sheet.employee_actual_hours is not None:
        difference = abs(sheet.marked_hours - sheet.employee_actual_hours)
        if difference > tolerance:
            is_mismatch = True
            # DC PROTOCOL: Require reason for mismatch or status override
            if not data.approval_reason:
                if status_was_changed:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Status change causes timesheet mismatch (New Marked: {sheet.marked_hours}hrs, Timesheet: {sheet.employee_actual_hours}hrs). Please provide approval reason."
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Timesheet mismatch detected (Marked: {sheet.marked_hours}hrs, Timesheet: {sheet.employee_actual_hours}hrs). Please provide approval reason."
                    )
    
    # DC PROTOCOL: If status was changed OR mismatch detected, set MANUAL_OVERRIDE
    if status_was_changed or is_mismatch:
        sheet.reconciliation_status = ReconciliationStatus.MANUAL_OVERRIDE
    
    # Update approval
    sheet.approved_hours = data.approved_hours
    sheet.approved_by_id = current_user.id
    sheet.approved_at = datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
    sheet.approval_status = ApprovalStatus.APPROVED
    sheet.approval_reason = data.approval_reason
    
    # Calculate net days (approved hours / 8)
    sheet.net_days = Decimal(str(float(data.approved_hours) / 8))
    
    # DC PROTOCOL - Re-validate reconciliation after approval
    # If approved hours differ significantly from marked hours, flag as manual override
    if sheet.approved_hours != sheet.marked_hours:
        tolerance = Decimal('0.5')
        if abs(sheet.approved_hours - sheet.marked_hours) > tolerance:
            sheet.reconciliation_status = ReconciliationStatus.MANUAL_OVERRIDE
    
    # Audit log with status change tracking
    fields_changed = ["approved_hours", "approval_status"]
    if data.new_attendance_status:
        fields_changed.extend(["attendance_status", "marked_hours"])
    
    audit = StaffAttendanceSheetAudit(
        attendance_sheet=sheet,
        changed_by_id=current_user.id,
        changed_by_role=current_user.role.role_code,
        change_type="approved",
        field_changed=",".join(fields_changed),
        old_value={
            "approved_hours": None,
            "attendance_status": old_status,
            "marked_hours": str(old_marked_hours)
        },
        new_value={
            "approved_hours": str(data.approved_hours),
            "attendance_status": sheet.attendance_status.value,
            "marked_hours": str(sheet.marked_hours)
        },
        reason=data.approval_reason or "Approved by EA/VGK"
    )
    db.add(audit)
    
    # DC Protocol (Jan 01, 2026): Add exception record if bypass was granted
    if exception_record:
        db.add(exception_record)
        logger.info(f"Exception record created for sheet {sheet_id}")
    
    db.commit()
    
    return {
        "success": True, 
        "approval_status": "approved",
        "status_changed": data.new_attendance_status is not None,
        "new_status": sheet.attendance_status.value if data.new_attendance_status else None,
        "exception_bypass": exception_record is not None,
        "exception_id": exception_record.id if exception_record else None
    }


@router.put("/{sheet_id}/edit", summary="Edit attendance status (EA/VGK only)")
def edit_attendance(
    sheet_id: int,
    data: AttendanceSheetEdit,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    EA/VGK directly edits attendance status (e.g., change present to leave).
    
    DC Protocol (Dec 04, 2025):
    - Allows changing any attendance status (present, half_day, leave types, etc.)
    - Recalculates marked_hours based on new status
    - Resets approval status to PENDING for re-approval
    - Full audit trail maintained
    """
    
    # Authorization check
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['ea', 'vgk4u']:
    #     raise HTTPException(status_code=403, detail="Only EA/VGK can edit attendance status")
    
    sheet = db.query(StaffAttendanceSheet).filter_by(id=sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Attendance sheet not found")
    
    # Validate new status
    try:
        new_status = AttendanceStatus(data.new_attendance_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid attendance status: {data.new_attendance_status}")
    
    # Store old values for audit
    old_status = sheet.attendance_status.value
    old_marked_hours = float(sheet.marked_hours)
    old_approved_hours = float(sheet.approved_hours) if sheet.approved_hours else None
    old_approval_status = sheet.approval_status.value
    
    # Update status and recalculate marked hours
    marked_hours_map = {
        AttendanceStatus.PRESENT: Decimal('8'),
        AttendanceStatus.HALF_DAY: Decimal('4'),
        AttendanceStatus.ABSENT: Decimal('0'),
        AttendanceStatus.SICK_LEAVE: Decimal('0'),
        AttendanceStatus.APPROVED_LEAVE: Decimal('0'),
        AttendanceStatus.CASUAL_LEAVE: Decimal('0'),
        AttendanceStatus.UNPAID_LEAVE: Decimal('0'),
        AttendanceStatus.HOLIDAY: Decimal('8'),
        AttendanceStatus.WEEKEND: Decimal('0'),
    }
    
    sheet.attendance_status = new_status
    sheet.marked_hours = marked_hours_map.get(new_status, Decimal('0'))
    
    # Reset approval status to pending for re-approval (DC Protocol)
    sheet.approval_status = ApprovalStatus.PENDING
    sheet.approved_hours = None
    sheet.approved_by_id = None
    sheet.approved_at = None
    sheet.net_days = Decimal('0')
    
    # Mark as manual override since status was directly edited
    sheet.reconciliation_status = ReconciliationStatus.MANUAL_OVERRIDE
    
    # Create audit trail
    audit = StaffAttendanceSheetAudit(
        attendance_sheet=sheet,
        changed_by_id=current_user.id,
        changed_by_role=current_user.role.role_code,
        change_type="edited",
        field_changed="attendance_status,marked_hours,approval_status",
        old_value={
            "attendance_status": old_status,
            "marked_hours": str(old_marked_hours),
            "approved_hours": str(old_approved_hours) if old_approved_hours else None,
            "approval_status": old_approval_status
        },
        new_value={
            "attendance_status": new_status.value,
            "marked_hours": str(sheet.marked_hours),
            "approved_hours": None,
            "approval_status": "pending"
        },
        reason=data.edit_reason
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "message": f"Attendance status changed from {old_status} to {new_status.value}",
        "old_status": old_status,
        "new_status": new_status.value,
        "new_marked_hours": float(sheet.marked_hours),
        "approval_reset": True
    }


@router.get("/employee/{employee_id}/records/{month_year}", summary="Get employee's attendance records for editing")
def get_employee_records_for_edit(
    employee_id: int,
    month_year: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all attendance records for an employee in a month (for edit modal).
    EA/VGK use this to view and edit records.
    """
    
    # Authorization check
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['ea', 'vgk4u', 'hr']:
    #     raise HTTPException(status_code=403, detail="Only HR/EA/VGK can view employee records")
    
    # Validate employee exists
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Parse month
    try:
        month_parts = month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    # Get all records for the employee in this month
    from calendar import monthrange
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    records = db.query(StaffAttendanceSheet).filter(
        StaffAttendanceSheet.employee_id == employee_id,
        StaffAttendanceSheet.date >= start_date,
        StaffAttendanceSheet.date <= end_date
    ).order_by(StaffAttendanceSheet.date).all()
    
    return {
        "success": True,
        "employee_id": employee_id,
        "employee_name": employee.full_name,
        "month_year": month_year,
        "records": [
            {
                "id": r.id,
                "date": r.date.isoformat(),
                "attendance_status": r.attendance_status.value,
                "marked_hours": float(r.marked_hours),
                "approved_hours": float(r.approved_hours) if r.approved_hours else None,
                "approval_status": r.approval_status.value,
                "reconciliation_status": r.reconciliation_status.value,
                "notes": r.notes
            }
            for r in records
        ]
    }


@router.post("/bulk-approve", summary="Bulk approve all pending attendance (EA/VGK only)")
def bulk_approve_attendance(
    data: BulkApproveRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Bulk approve all pending attendance markings for a month.
    
    DC Protocol (Dec 04, 2025):
    - SKIPS employees with NO_ENTRY (no timesheet) during bulk approve
    - Validates 30-min tolerance for mismatch detection
    - Returns detailed counts of approved and skipped records
    """
    
    # Authorization check - EA/VGK only
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['ea', 'vgk4u']:
    #     raise HTTPException(status_code=403, detail="Only EA/VGK can bulk approve attendance")
    
    # Parse month
    try:
        month_parts = data.month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    # Build date range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Build query for pending attendance sheets
    query = db.query(StaffAttendanceSheet).filter(
        and_(
            StaffAttendanceSheet.date >= start_date,
            StaffAttendanceSheet.date <= end_date,
            StaffAttendanceSheet.approval_status == ApprovalStatus.PENDING
        )
    )
    
    # Apply filters if provided
    if data.department_id:
        employee_ids = db.query(StaffEmployee.id).filter_by(department_id=data.department_id).scalar_subquery()
        query = query.filter(StaffAttendanceSheet.employee_id.in_(employee_ids))
    
    if data.manager_id:
        employee_ids = db.query(StaffEmployee.id).filter_by(reporting_manager_id=data.manager_id).scalar_subquery()
        query = query.filter(StaffAttendanceSheet.employee_id.in_(employee_ids))
    
    pending_sheets = query.all()
    
    if not pending_sheets:
        return {
            "success": True,
            "message": "No pending attendance records found",
            "approved_count": 0,
            "skipped_count": 0,
            "skipped_reason": None
        }
    
    # DC PROTOCOL: Track approved and skipped records
    approved_count = 0
    skipped_count = 0
    skipped_employees = []  # Track which employees were skipped
    approval_time = datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
    
    for sheet in pending_sheets:
        # DC PROTOCOL: Skip if NO_ENTRY (no timesheet)
        if sheet.reconciliation_status == ReconciliationStatus.NO_ENTRY:
            skipped_count += 1
            # Get employee name for reporting
            employee = db.query(StaffEmployee).filter_by(id=sheet.employee_id).first()
            if employee:
                skipped_employees.append({
                    "employee_id": employee.id,
                    "name": employee.display_name or employee.full_name,
                    "date": str(sheet.date),
                    "reason": "No timesheet entry"
                })
            continue  # Skip this record
        
        # Approve records with timesheet entries
        sheet.approved_hours = sheet.marked_hours
        sheet.approved_by_id = current_user.id
        sheet.approved_at = approval_time
        sheet.approval_status = ApprovalStatus.APPROVED
        sheet.approval_reason = "Bulk approved by EA/VGK"
        sheet.net_days = Decimal(str(float(sheet.marked_hours) / 8))
        
        # Audit log for each approval
        audit = StaffAttendanceSheetAudit(
            attendance_sheet=sheet,
            changed_by_id=current_user.id,
            changed_by_role=current_user.role.role_code,
            change_type="bulk_approved",
            field_changed="approved_hours,approval_status",
            old_value={"approved_hours": None, "approval_status": "pending"},
            new_value={"approved_hours": str(sheet.marked_hours), "approval_status": "approved"},
            reason="Bulk approved by EA/VGK"
        )
        db.add(audit)
        approved_count += 1
    
    db.commit()
    
    # Build response message
    message = f"Successfully approved {approved_count} attendance records"
    if skipped_count > 0:
        message += f". Skipped {skipped_count} records (no timesheet entry)"
    
    return {
        "success": True,
        "message": message,
        "approved_count": approved_count,
        "skipped_count": skipped_count,
        "skipped_employees": skipped_employees if skipped_count > 0 else None
    }


@router.get("/monthly/{month_year}", summary="Get monthly attendance data")
def get_monthly_attendance(
    month_year: str,  # Format: "2025-12" for December 2025
    manager_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    team_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) - overrides month start"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) - overrides month end"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly attendance data with all dates as columns.
    Supports optional from_date/to_date for custom date ranges.
    
    Returns: {
        dates: [2025-12-01, 2025-12-02, ...],
        employees: [
            {id, name, dept, marked_hrs[day1], approved_hrs[day1], net_days[day1], ...},
            ...
        ],
        totals: {marked_hrs_total, approved_hrs_total, net_days_total}
    }
    """
    
    try:
        month_parts = month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    # DC Protocol (Jan 07, 2026): Support custom date range
    # Build date range - use from_date/to_date if provided, otherwise default to month
    if from_date:
        try:
            start_date = date.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format (use YYYY-MM-DD)")
    else:
        start_date = date(year, month, 1)
    
    if to_date:
        try:
            end_date = date.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format (use YYYY-MM-DD)")
    else:
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Validate date range
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="to_date cannot be before from_date")
    
    # Get employees (filter by manager/dept/team if provided)
    emp_query = db.query(StaffEmployee)
    if manager_id:
        emp_query = emp_query.filter_by(manager_id=manager_id)
    if department_id:
        emp_query = emp_query.filter_by(department_id=department_id)
    
    employees = emp_query.all()
    
    # Get all attendance data for month
    attendance_data = db.query(StaffAttendanceSheet).filter(
        and_(
            StaffAttendanceSheet.date >= start_date,
            StaffAttendanceSheet.date <= end_date,
            StaffAttendanceSheet.employee_id.in_([e.id for e in employees])
        )
    ).all()
    
    # Build response
    date_list = [(start_date + timedelta(days=i)).isoformat() for i in range((end_date - start_date).days + 1)]
    
    employee_rows = []
    total_marked = Decimal(0)
    total_approved = Decimal(0)
    total_net_days = Decimal(0)
    
    # Get timesheet data for all employees in date range
    timesheet_data = db.query(StaffTimesheetEntry).filter(
        and_(
            StaffTimesheetEntry.date >= start_date,
            StaffTimesheetEntry.date <= end_date,
            StaffTimesheetEntry.employee_id.in_([e.id for e in employees]),
            StaffTimesheetEntry.status == 'submitted'
        )
    ).all()
    
    for emp in employees:
        # Calculate employee monthly summary
        emp_attendance = [a for a in attendance_data if a.employee_id == emp.id]
        emp_timesheet = [t for t in timesheet_data if t.employee_id == emp.id]
        
        # Summary calculations (DC Protocol: Single source of truth)
        pending_hours = Decimal(0)
        approved_hours = Decimal(0)
        rejected_hours = Decimal(0)
        marked_hours_total = Decimal(0)
        submitted_hours = Decimal(0)  # From timesheet billable_minutes
        
        for att in emp_attendance:
            marked_hours_total += att.marked_hours
            if att.approval_status == ApprovalStatus.PENDING:
                pending_hours += att.marked_hours
            elif att.approval_status == ApprovalStatus.APPROVED and att.approved_hours:
                approved_hours += att.approved_hours
            elif att.approval_status == ApprovalStatus.REJECTED:
                rejected_hours += att.marked_hours
        
        # Calculate submitted hours from timesheet (billable minutes / 60)
        for ts in emp_timesheet:
            if ts.billable_minutes and ts.billable_minutes > 0:
                submitted_hours += Decimal(str(ts.billable_minutes / 60))
        
        # Eligible days for payroll (approved_hours / 8 only - DC/WVV Protocol)
        eligible_days = approved_hours / Decimal(8) if approved_hours > 0 else Decimal(0)
        
        # Calculate attendance category counts (DC Protocol: grouped by attendance_status)
        leaves_hours = Decimal(0)
        absences_count = 0
        half_days_count = 0
        present_days_count = 0
        holidays_count = 0
        weekends_count = 0
        
        for att in emp_attendance:
            if att.attendance_status == AttendanceStatus.SICK_LEAVE or att.attendance_status == AttendanceStatus.APPROVED_LEAVE or att.attendance_status == AttendanceStatus.CASUAL_LEAVE or att.attendance_status == AttendanceStatus.UNPAID_LEAVE:
                leaves_hours += att.marked_hours
            elif att.attendance_status == AttendanceStatus.ABSENT:
                absences_count += 1
            elif att.attendance_status == AttendanceStatus.HALF_DAY:
                half_days_count += 1
            elif att.attendance_status == AttendanceStatus.PRESENT:
                present_days_count += 1
            elif att.attendance_status == AttendanceStatus.HOLIDAY:
                holidays_count += 1
            elif att.attendance_status == AttendanceStatus.WEEKEND:
                weekends_count += 1
        
        leaves_days = leaves_hours / Decimal(8) if leaves_hours > 0 else Decimal(0)
        
        row = {
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code,
            "team_manager": emp.reporting_manager.full_name if emp.reporting_manager else "N/A",
            "department": emp.department.name if emp.department else "N/A",
            "summary": {
                "pending_hours": float(pending_hours),
                "submitted_hours": float(submitted_hours),
                "approved_hours": float(approved_hours),
                "rejected_hours": float(rejected_hours),
                "total_marked_hours": float(marked_hours_total),
                "eligible_days": float(eligible_days),
                "leaves_days": float(leaves_days),
                "absences_count": absences_count,
                "half_days_count": half_days_count,
                "present_days_count": present_days_count,
                "holidays_count": holidays_count,
                "weekends_count": weekends_count
            },
            "dates": {}
        }
        
        for date_str in date_list:
            curr_date = date.fromisoformat(date_str)
            att = next((a for a in attendance_data if a.employee_id == emp.id and a.date == curr_date), None)
            
            if att:
                row["dates"][date_str] = {
                    "sheet_id": att.id,
                    "marked_hours": float(att.marked_hours),
                    "approved_hours": float(att.approved_hours) if att.approved_hours else None,
                    "net_days": float(att.net_days),
                    "status": att.approval_status.value,
                    "attendance_status": att.attendance_status.value,
                    "reconciliation_status": att.reconciliation_status.value,
                    "employee_actual_hours": float(att.employee_actual_hours) if att.employee_actual_hours else None
                }
                total_marked += att.marked_hours
                if att.approved_hours:
                    total_approved += att.approved_hours
                    total_net_days += att.net_days
            else:
                row["dates"][date_str] = None
        
        employee_rows.append(row)
    
    return {
        "success": True,
        "month": month_year,
        "dates": date_list,
        "employees": employee_rows,
        "totals": {
            "total_marked_hours": float(total_marked),
            "total_approved_hours": float(total_approved),
            "total_net_days": float(total_net_days)
        }
    }


@router.get("/alerts/{date_str}", summary="Get custom date alerts")
def get_attendance_alerts(
    date_str: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get alerts for a specific date (pending approvals, discrepancies, etc)"""
    
    try:
        curr_date = date.fromisoformat(date_str)
    except:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
    
    # Count pending approvals
    pending = db.query(func.count(StaffAttendanceSheet.id)).filter(
        and_(
            StaffAttendanceSheet.date == curr_date,
            StaffAttendanceSheet.approval_status == ApprovalStatus.PENDING
        )
    ).scalar()
    
    # Count mismatches
    mismatches = db.query(func.count(StaffAttendanceSheet.id)).filter(
        and_(
            StaffAttendanceSheet.date == curr_date,
            StaffAttendanceSheet.reconciliation_status == ReconciliationStatus.MISMATCH_WARNING
        )
    ).scalar()
    
    # Count manual overrides
    overrides = db.query(func.count(StaffAttendanceSheet.id)).filter(
        and_(
            StaffAttendanceSheet.date == curr_date,
            StaffAttendanceSheet.reconciliation_status == ReconciliationStatus.MANUAL_OVERRIDE
        )
    ).scalar()
    
    alerts = []
    if pending:
        alerts.append(f"⏳ {pending} employees pending approval")
    if mismatches:
        alerts.append(f"⚠️  {mismatches} employees with discrepancies")
    if overrides:
        alerts.append(f"✋ {overrides} manual overrides (no timesheet entry)")
    
    return {
        "success": True,
        "date": date_str,
        "alerts": alerts,
        "counts": {
            "pending": pending,
            "mismatches": mismatches,
            "manual_overrides": overrides
        }
    }


@router.get("/employee/{employee_id}/marked-data/{month_year}", summary="Get employee's marked attendance (for computation tab)")
def get_employee_marked_data(
    employee_id: int,
    month_year: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get marked/approved attendance data for employee (read-only for employee view)"""
    
    # Employee can only view their own data
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != employee_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        month_parts = month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    # Build date range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get all marked attendance for employee in month
    attendance_data = db.query(StaffAttendanceSheet).filter(
        and_(
            StaffAttendanceSheet.employee_id == employee_id,
            StaffAttendanceSheet.date >= start_date,
            StaffAttendanceSheet.date <= end_date
        )
    ).order_by(StaffAttendanceSheet.date).all()
    
    # DC Protocol (Dec 04, 2025): Get punch data (login/logout times) from StaffAttendance
    punch_data = db.query(StaffAttendance).filter(
        and_(
            StaffAttendance.employee_id == employee_id,
            StaffAttendance.date >= start_date,
            StaffAttendance.date <= end_date
        )
    ).all()
    
    # Create lookup dictionary for punch data by date
    punch_lookup = {punch.date: punch for punch in punch_data}
    
    # Helper function to format time with null-safety
    def format_time(dt):
        if dt is None:
            return None
        return dt.strftime("%I:%M %p")  # e.g., "09:15 AM"
    
    # Helper function to format worked hours
    def format_worked_hours(minutes):
        if minutes is None or minutes == 0:
            return None
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"
    
    # Build response with login/logout data
    records = []
    total_marked_hours = Decimal(0)
    total_approved_hours = Decimal(0)
    total_net_days = Decimal(0)
    
    for att in attendance_data:
        # Get punch data for this date (if exists)
        punch = punch_lookup.get(att.date)
        
        records.append({
            "date": att.date.isoformat(),
            "status": att.attendance_status.value,
            "marked_hours": float(att.marked_hours),
            "approved_hours": float(att.approved_hours) if att.approved_hours else None,
            "net_days": float(att.net_days),
            "approval_status": att.approval_status.value,
            "reconciliation": att.reconciliation_status.value,
            # DC Protocol (Dec 04, 2025): Login/Logout/Total Hours from punch data
            "login_time": format_time(punch.clock_in) if punch else None,
            "logout_time": format_time(punch.clock_out) if punch else None,
            "total_hours": format_worked_hours(punch.worked_minutes) if punch else None,
            "worked_minutes": punch.worked_minutes if punch else None
        })
        total_marked_hours += att.marked_hours
        if att.approved_hours:
            total_approved_hours += att.approved_hours
            total_net_days += att.net_days
    
    return {
        "success": True,
        "employee_id": employee_id,
        "month": month_year,
        "records": records,
        "summary": {
            "total_marked_hours": float(total_marked_hours),
            "total_approved_hours": float(total_approved_hours),
            "total_net_days": float(total_net_days),
            "total_days_in_month": (end_date - start_date).days + 1
        }
    }


@router.get("/manager/team/{manager_id}/{month_year}", summary="Get team attendance data for manager view")
def get_manager_team_data(
    manager_id: int,
    month_year: str,
    filter_employee_id: Optional[int] = Query(None, description="Filter by specific employee ID"),
    filter_employee_name: Optional[str] = Query(None, description="Filter by employee name (partial match)"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get team attendance data for manager dashboard
    Dec 04, 2025: Enhanced to return per-day records with employee filters
    - Returns individual daily records (not just aggregated)
    - Supports filtering by employee ID or name
    - Includes login/logout/total hours for each record
    """
    
    # Manager can only view their own team
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != manager_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        month_parts = month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    # Build date range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # DC Protocol (Dec 04, 2025): Get team members using recursive downline
    manager = db.query(StaffEmployee).filter(StaffEmployee.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    team_ids = get_team_member_ids(manager, db, StaffEmployee)
    team_members_query = db.query(StaffEmployee).filter(StaffEmployee.id.in_(team_ids))
    
    # DC Protocol (Dec 04, 2025): Apply optional employee filters
    if filter_employee_id:
        team_members_query = team_members_query.filter(StaffEmployee.id == filter_employee_id)
    if filter_employee_name:
        team_members_query = team_members_query.filter(
            StaffEmployee.full_name.ilike(f"%{filter_employee_name}%")
        )
    
    team_members_list = team_members_query.all()
    
    team_members = sorted(team_members_list, key=lambda m: m.full_name)
    
    # Build employee lookup for quick access
    employee_lookup = {m.id: m for m in team_members}
    
    # Get attendance data for all team members including self
    attendance_data = db.query(StaffAttendanceSheet).filter(
        and_(
            StaffAttendanceSheet.employee_id.in_([m.id for m in team_members]),
            StaffAttendanceSheet.date >= start_date,
            StaffAttendanceSheet.date <= end_date
        )
    ).order_by(StaffAttendanceSheet.employee_id, StaffAttendanceSheet.date).all()
    
    # DC Protocol (Dec 04, 2025): Get punch data (login/logout times) from StaffAttendance
    punch_data = db.query(StaffAttendance).filter(
        and_(
            StaffAttendance.employee_id.in_([m.id for m in team_members]),
            StaffAttendance.date >= start_date,
            StaffAttendance.date <= end_date
        )
    ).all()
    
    # Create lookup dictionary for punch data by (employee_id, date)
    punch_lookup = {(punch.employee_id, punch.date): punch for punch in punch_data}
    
    # Helper function to format time with null-safety
    def format_time(dt):
        if dt is None:
            return None
        return dt.strftime("%I:%M %p")  # e.g., "09:15 AM"
    
    # Helper function to format worked hours
    def format_worked_hours(minutes):
        if minutes is None or minutes == 0:
            return None
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"
    
    # DC Protocol (Dec 04, 2025): Build per-day records (not just aggregated summaries)
    daily_records = []
    total_team_marked = Decimal(0)
    total_team_approved = Decimal(0)
    
    for att in attendance_data:
        emp = employee_lookup.get(att.employee_id)
        if not emp:
            continue
            
        # Get punch data for this employee on this date
        punch = punch_lookup.get((att.employee_id, att.date))
        
        daily_records.append({
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code if emp.emp_code else f"EMP{emp.id:04d}",
            "department_name": emp.department.name if emp.department else "-",
            "is_self": emp.id == manager_id,
            "date": att.date.isoformat(),
            "day": att.date.strftime("%a"),
            "status": att.attendance_status.value,
            "marked_hours": float(att.marked_hours),
            "approved_hours": float(att.approved_hours) if att.approved_hours else None,
            "approval_status": att.approval_status.value,
            # DC Protocol (Dec 04, 2025): Login/Logout/Total Hours from punch data
            "login_time": format_time(punch.clock_in) if punch else None,
            "logout_time": format_time(punch.clock_out) if punch else None,
            "total_hours": format_worked_hours(punch.worked_minutes) if punch else None,
            "worked_minutes": punch.worked_minutes if punch else None
        })
        
        total_team_marked += att.marked_hours
        if att.approved_hours:
            total_team_approved += att.approved_hours
    
    # Build employee list for filter dropdown
    employee_list = [
        {
            "id": m.id,
            "name": m.full_name,
            "code": m.emp_code if m.emp_code else f"EMP{m.id:04d}",
            "is_self": m.id == manager_id
        }
        for m in team_members
    ]
    
    return {
        "success": True,
        "manager_id": manager_id,
        "month": month_year,
        "records": daily_records,
        "employees": employee_list,
        "team_summary": {
            "total_team_marked_hours": float(total_team_marked),
            "total_team_approved_hours": float(total_team_approved),
            "team_size": len(team_members),
            "total_records": len(daily_records)
        }
    }


# ==================== TEAM ATTENDANCE - DOWNLINE TEAM (BULK MARKING FORMAT) ====================

@router.get("/manager/team-monthly/{manager_id}/{month_year}", summary="Get team attendance in bulk-marking format (VIEW ONLY)")
def get_manager_team_monthly(
    manager_id: int,
    month_year: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 04, 2025): Team Attendance - Downline Team tab
    Returns same format as /monthly endpoint but scoped to manager's downline
    
    Key Features:
    - VIEW ONLY: No edit/approval access
    - Self First: First row is always the logged-in manager
    - Department-wise: Team members sorted by department after self
    - Same format as Bulk Marking for consistency
    
    Returns: {
        dates: [2025-12-01, 2025-12-02, ...],
        employees: [self, ...team_members_by_department],
        totals: {total_marked_hours, total_approved_hours, total_net_days}
    }
    """
    
    # Authorization: Manager can only view their own team
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != manager_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        month_parts = month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    # Build date range for month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # DC Protocol: Get manager's accessible employees (self + recursive downline)
    manager = db.query(StaffEmployee).filter(StaffEmployee.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")

    # DC-SCOPE-001: Super-admin (MR10001 or hierarchy_level >= 90) sees ALL employees
    _req_code = (current_user.emp_code or '').upper()
    _req_level = current_user.role.hierarchy_level if current_user.role else 0
    _is_super_admin = _req_code == 'MR10001' or _req_level >= 90
    if _is_super_admin:
        team_members_list = db.query(StaffEmployee).all()
    else:
        team_ids = get_team_member_ids(manager, db, StaffEmployee)
        team_members_list = db.query(StaffEmployee).filter(StaffEmployee.id.in_(team_ids)).all()

    def sort_key(emp):
        dept_name = emp.department.name if emp.department else "ZZZ"
        return (dept_name, emp.full_name)
    
    employees = sorted(team_members_list, key=sort_key)
    
    # Get all attendance data for month
    attendance_data = db.query(StaffAttendanceSheet).filter(
        and_(
            StaffAttendanceSheet.date >= start_date,
            StaffAttendanceSheet.date <= end_date,
            StaffAttendanceSheet.employee_id.in_([e.id for e in employees])
        )
    ).all()
    
    # Get timesheet data for all employees in date range
    timesheet_data = db.query(StaffTimesheetEntry).filter(
        and_(
            StaffTimesheetEntry.date >= start_date,
            StaffTimesheetEntry.date <= end_date,
            StaffTimesheetEntry.employee_id.in_([e.id for e in employees]),
            StaffTimesheetEntry.status == 'submitted'
        )
    ).all()
    
    # DC Protocol (Jan 07, 2026): Get exception data for all employees in date range
    exception_data = db.query(StaffAttendanceException).filter(
        and_(
            StaffAttendanceException.date >= start_date,
            StaffAttendanceException.date <= end_date,
            StaffAttendanceException.employee_id.in_([e.id for e in employees])
        )
    ).all()
    
    # Build response
    date_list = [(start_date + timedelta(days=i)).isoformat() for i in range((end_date - start_date).days + 1)]
    
    employee_rows = []
    total_marked = Decimal(0)
    total_approved = Decimal(0)
    total_net_days = Decimal(0)
    total_exception_hours = Decimal(0)
    total_exception_days = 0
    
    for emp in employees:
        # Calculate employee monthly summary
        emp_attendance = [a for a in attendance_data if a.employee_id == emp.id]
        emp_timesheet = [t for t in timesheet_data if t.employee_id == emp.id]
        emp_exceptions = [e for e in exception_data if e.employee_id == emp.id]
        
        # Summary calculations (DC Protocol: Single source of truth)
        pending_hours = Decimal(0)
        approved_hours = Decimal(0)
        rejected_hours = Decimal(0)
        marked_hours_total = Decimal(0)
        submitted_hours = Decimal(0)
        
        # DC Protocol (Jan 07, 2026): Calculate exception hours and days
        exception_hours = Decimal(0)
        exception_days_count = len(emp_exceptions)
        for exc in emp_exceptions:
            if exc.approved_hours:
                exception_hours += exc.approved_hours
        
        for att in emp_attendance:
            marked_hours_total += att.marked_hours
            if att.approval_status == ApprovalStatus.PENDING:
                pending_hours += att.marked_hours
            elif att.approval_status == ApprovalStatus.APPROVED and att.approved_hours:
                approved_hours += att.approved_hours
            elif att.approval_status == ApprovalStatus.REJECTED:
                rejected_hours += att.marked_hours
        
        # Calculate submitted hours from timesheet
        for ts in emp_timesheet:
            if ts.billable_minutes and ts.billable_minutes > 0:
                submitted_hours += Decimal(str(ts.billable_minutes / 60))
        
        # Eligible days for payroll (approved_hours / 8 only - DC/WVV Protocol)
        eligible_days = approved_hours / Decimal(8) if approved_hours > 0 else Decimal(0)
        
        # Calculate attendance category counts
        # DC Protocol (Jan 07, 2026): Count leave days by net_days, not marked_hours
        leaves_days = Decimal(0)
        absences_count = 0
        half_days_count = 0
        present_days_count = 0
        holidays_count = 0
        weekends_count = 0
        
        for att in emp_attendance:
            if att.attendance_status in [AttendanceStatus.SICK_LEAVE, AttendanceStatus.APPROVED_LEAVE, 
                                         AttendanceStatus.CASUAL_LEAVE, AttendanceStatus.UNPAID_LEAVE]:
                # Count leave days using net_days (1.0 for full day, 0.5 for half day)
                leaves_days += att.net_days if att.net_days else Decimal('1')
            elif att.attendance_status == AttendanceStatus.ABSENT:
                absences_count += 1
            elif att.attendance_status == AttendanceStatus.HALF_DAY:
                half_days_count += 1
            elif att.attendance_status == AttendanceStatus.PRESENT:
                present_days_count += 1
            elif att.attendance_status == AttendanceStatus.HOLIDAY:
                holidays_count += 1
            elif att.attendance_status == AttendanceStatus.WEEKEND:
                weekends_count += 1
        
        row = {
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code if emp.emp_code else f"EMP{emp.id:04d}",
            "team_manager": emp.reporting_manager.full_name if emp.reporting_manager else "N/A",
            "department": emp.department.name if emp.department else "Unassigned",
            "is_self": emp.id == manager_id,
            "summary": {
                "pending_hours": float(pending_hours),
                "submitted_hours": float(submitted_hours),
                "approved_hours": float(approved_hours),
                "rejected_hours": float(rejected_hours),
                "exception_hours": float(exception_hours),
                "total_marked_hours": float(marked_hours_total),
                "exception_days": exception_days_count,
                "eligible_days": float(eligible_days),
                "leaves_days": float(leaves_days),
                "absences_count": absences_count,
                "half_days_count": half_days_count,
                "present_days_count": present_days_count,
                "holidays_count": holidays_count,
                "weekends_count": weekends_count
            },
            "dates": {}
        }
        
        # Update totals for exception data
        total_exception_hours += exception_hours
        total_exception_days += exception_days_count
        
        for date_str in date_list:
            curr_date = date.fromisoformat(date_str)
            att = next((a for a in attendance_data if a.employee_id == emp.id and a.date == curr_date), None)
            
            if att:
                row["dates"][date_str] = {
                    "sheet_id": att.id,
                    "marked_hours": float(att.marked_hours),
                    "approved_hours": float(att.approved_hours) if att.approved_hours else None,
                    "net_days": float(att.net_days),
                    "status": att.approval_status.value,
                    "attendance_status": att.attendance_status.value,
                    "reconciliation_status": att.reconciliation_status.value
                }
                total_marked += att.marked_hours
                if att.approved_hours:
                    total_approved += att.approved_hours
                    total_net_days += att.net_days
            else:
                row["dates"][date_str] = None
        
        employee_rows.append(row)
    
    return {
        "success": True,
        "month": month_year,
        "manager_id": manager_id,
        "dates": date_list,
        "employees": employee_rows,
        "totals": {
            "total_marked_hours": float(total_marked),
            "total_approved_hours": float(total_approved),
            "total_net_days": float(total_net_days),
            "total_exception_hours": float(total_exception_hours),
            "total_exception_days": total_exception_days,
            "team_size": len(employees),
            "total_employees": len(employees)
        }
    }


# ==================== SIDEBAR ENDPOINT ====================

@router.get("/summary/{month_year}", summary="Get employee-wise attendance summary (DC Protocol)")
def get_attendance_summary(
    month_year: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    manager_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get employee-wise attendance summary with status columns (Pending, Approved, Rejected)
    DC Protocol: Single calculation source, verifiable per-employee totals
    WVV Protocol: Immutable calculations, eligible_days = approved_hours / 8 (payroll safe)
    Returns: Employee rows with hours breakdown + totals row
    """
    try:
        month_parts = month_year.split("-")
        year = int(month_parts[0])
        month = int(month_parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid month format (use YYYY-MM)")
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get all attendance records for date range
    query = db.query(StaffAttendanceSheet).filter(
        and_(
            StaffAttendanceSheet.date >= start_date,
            StaffAttendanceSheet.date <= end_date
        )
    )
    
    # Apply optional filters - DC Protocol (Dec 04, 2025): Use recursive downline
    if manager_id:
        # Get manager to calculate their entire downline
        manager = db.query(StaffEmployee).filter(StaffEmployee.id == manager_id).first()
        if manager:
            downline_ids = get_team_member_ids(manager, db, StaffEmployee)
            query = query.filter(StaffAttendanceSheet.employee_id.in_(downline_ids))
    if department_id:
        query = query.join(StaffEmployee).filter(StaffEmployee.department_id == department_id)
    
    attendance_records = query.all()
    
    # Group by employee and calculate totals
    employee_data = {}
    
    for record in attendance_records:
        emp_id = record.employee_id
        
        # Get employee details
        emp = db.query(StaffEmployee).filter_by(id=emp_id).first()
        if not emp:
            continue
        
        if emp_id not in employee_data:
            employee_data[emp_id] = {
                "employee_id": emp_id,
                "employee_name": emp.full_name,
                "department": emp.department.name if emp.department else "Unassigned",
                "pending_hours": Decimal(0),
                "approved_hours": Decimal(0),
                "rejected_hours": Decimal(0),
                "total_marked_hours": Decimal(0)
            }
        
        # Categorize hours by status (DC Protocol: single source of truth)
        if record.approval_status == ApprovalStatus.PENDING:
            employee_data[emp_id]["pending_hours"] += record.marked_hours
        elif record.approval_status == ApprovalStatus.APPROVED and record.approved_hours:
            employee_data[emp_id]["approved_hours"] += record.approved_hours
        elif record.approval_status == ApprovalStatus.REJECTED:
            employee_data[emp_id]["rejected_hours"] += record.marked_hours
        
        employee_data[emp_id]["total_marked_hours"] += record.marked_hours
    
    # Calculate eligible days and format response (WVV Protocol: only approved_hours for payroll)
    employee_rows = []
    total_pending = Decimal(0)
    total_approved = Decimal(0)
    total_rejected = Decimal(0)
    total_marked = Decimal(0)
    
    for emp_id, data in employee_data.items():
        # Eligible days = approved_hours / 8 (payroll safe, never from pending/rejected)
        eligible_days = data["approved_hours"] / Decimal(8) if data["approved_hours"] > 0 else Decimal(0)
        
        row = {
            "employee_id": data["employee_id"],
            "employee_name": data["employee_name"],
            "department": data["department"],
            "pending_hours": float(data["pending_hours"]),
            "approved_hours": float(data["approved_hours"]),
            "rejected_hours": float(data["rejected_hours"]),
            "total_marked_hours": float(data["total_marked_hours"]),
            "eligible_days": float(eligible_days),
            "status": "approved" if data["approved_hours"] > 0 and data["pending_hours"] == 0 else "pending" if data["pending_hours"] > 0 else "rejected"
        }
        
        employee_rows.append(row)
        total_pending += data["pending_hours"]
        total_approved += data["approved_hours"]
        total_rejected += data["rejected_hours"]
        total_marked += data["total_marked_hours"]
    
    # Calculate total eligible days for payroll
    total_eligible_days = total_approved / Decimal(8) if total_approved > 0 else Decimal(0)
    
    # Sort by department, then employee name
    employee_rows.sort(key=lambda x: (x["department"], x["employee_name"]))
    
    return {
        "success": True,
        "month": month_year,
        "employees": employee_rows,
        "totals": {
            "total_employees": len(employee_rows),
            "total_pending_hours": float(total_pending),
            "total_approved_hours": float(total_approved),
            "total_rejected_hours": float(total_rejected),
            "total_marked_hours": float(total_marked),
            "total_eligible_days": float(total_eligible_days)
        }
    }


@router.get("", summary="Get staff sidebar data (DC Protocol)")
def get_sidebar(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's sidebar context including role, department, and team
    DC Protocol: Single source of truth for user context validation
    WVV Protocol: Immutable user context for audit trails
    """
    return {
        "success": True,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "user_role": current_user.role.role_name if current_user.role else "Unknown",
        "user_role_code": current_user.role.role_code if current_user.role else "unknown",
        "department": current_user.department.name if current_user.department else "N/A",
        "team_manager": current_user.reporting_manager.full_name if current_user.reporting_manager else "N/A",
        "hierarchy_level": current_user.role.hierarchy_level if current_user.role else 0
    }


# ==================== EXCEPTION RECORDS ENDPOINT (DC Protocol Jan 01, 2026) ====================

@router.get("/exceptions", summary="List exception approval records with filters")
def get_attendance_exceptions(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    approver_id: Optional[int] = Query(None, description="Filter by approver"),
    bypass_type: Optional[str] = Query(None, description="Filter by bypass type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Records per page"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get list of exception approval records.
    
    DC Protocol (Jan 01, 2026):
    - Company-wise data segregation enforced
    - Role-based access: EA/VGK/HR can view
    - All filters optional
    - Paginated response
    """
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # MR10001 (VGK Mentor) and key_leadership roles see ALL companies' exceptions
    _role_code = (current_user.role.role_code if current_user.role else '').lower()
    _emp_code = (current_user.emp_code or '').upper()
    _cross_company = _emp_code == 'MR10001' or _role_code in ('key_leadership', 'vgk4u', 'ea')
    
    # Base query - apply company filter unless cross-company viewer
    if _cross_company:
        query = db.query(StaffAttendanceException)
    else:
        query = db.query(StaffAttendanceException).filter(
            StaffAttendanceException.company_id == current_user.base_company_id
        )
    
    # Apply date range filter
    if from_date:
        query = query.filter(StaffAttendanceException.date >= from_date)
    if to_date:
        query = query.filter(StaffAttendanceException.date <= to_date)
    
    # Apply employee filter
    if employee_id:
        query = query.filter(StaffAttendanceException.employee_id == employee_id)
    
    # Apply department filter (join with employee)
    if department_id:
        query = query.join(
            StaffEmployee, StaffAttendanceException.employee_id == StaffEmployee.id
        ).filter(StaffEmployee.department_id == department_id)
    
    # Apply approver filter
    if approver_id:
        query = query.filter(StaffAttendanceException.approver_id == approver_id)
    
    # Apply bypass type filter
    if bypass_type:
        try:
            bypass_enum = ExceptionBypassType(bypass_type)
            query = query.filter(StaffAttendanceException.bypass_type == bypass_enum)
        except ValueError:
            pass  # Invalid bypass type, ignore filter
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    offset = (page - 1) * per_page
    exceptions = query.order_by(desc(StaffAttendanceException.created_at)).offset(offset).limit(per_page).all()
    
    # Helper function to format time with null-safety
    def format_time(dt):
        if dt is None:
            return None
        return dt.strftime("%I:%M %p")  # e.g., "09:15 AM"
    
    # Helper function to format worked hours
    def format_worked_hours(minutes):
        if minutes is None or minutes == 0:
            return None
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"
    
    # Format response
    records = []
    for exc in exceptions:
        # Get employee details
        employee = db.query(StaffEmployee).filter_by(id=exc.employee_id).first()
        approver = db.query(StaffEmployee).filter_by(id=exc.approver_id).first() if exc.approver_id else None
        
        # Get punch data (clock in/out times) for this date
        punch = db.query(StaffAttendance).filter(
            and_(
                StaffAttendance.employee_id == exc.employee_id,
                StaffAttendance.date == exc.date
            )
        ).first()
        
        records.append({
            "id": exc.id,
            "date": str(exc.date),
            "employee_id": exc.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "employee_code": employee.emp_code if employee else "N/A",
            "department": employee.department.name if employee and employee.department else "N/A",
            "bypass_type": exc.bypass_type.value,
            "exception_reason": exc.exception_reason,
            "approver_id": exc.approver_id,
            "approver_name": approver.full_name if approver else "Unknown",
            "approver_role": exc.approver_role,
            "approved_hours": float(exc.approved_hours),
            "reconciliation_snapshot": exc.reconciliation_snapshot,
            "created_at": exc.created_at.isoformat() if exc.created_at else None,
            "clock_in": format_time(punch.clock_in) if punch else None,
            "clock_out": format_time(punch.clock_out) if punch else None,
            "total_hours": format_worked_hours(punch.worked_minutes) if punch else None
        })
    
    # Get filter options for dropdowns
    # Get distinct approvers
    approvers_q = db.query(StaffAttendanceException.approver_id).distinct()
    if not _cross_company:
        approvers_q = approvers_q.filter(StaffAttendanceException.company_id == current_user.base_company_id)
    approvers_query = db.query(
        StaffEmployee.id, StaffEmployee.full_name
    ).filter(
        StaffEmployee.id.in_(approvers_q)
    ).all()
    
    return {
        "success": True,
        "records": records,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page if total_count > 0 else 1
        },
        "filter_options": {
            "approvers": [{"id": a.id, "name": a.full_name} for a in approvers_query],
            "bypass_types": [bt.value for bt in ExceptionBypassType]
        }
    }


@router.get("/time-report", summary="DC-TIMEREPORT-001: Per-employee daily time report with punch + sheet + exception data")
def get_time_report(
    employee_id: int = Query(..., description="Employee ID (required)"),
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC-TIMEREPORT-001: Daily time detail report for a specific employee.
    Columns: Date, In Time, Out Time, Total Hours, Submitted Hours,
             Approved Hours, Exception Hours, In Location, Out Location, Logout Type.
    Access: Key Leadership / EA / Accounts / MR10001 (same as exceptions tab).
    """
    _role_code = (current_user.role.role_code if current_user.role else '').lower()
    _emp_code  = (current_user.emp_code or '').upper()
    _dept_name = (current_user.department.name if current_user.department else '').lower()
    _allowed   = (
        _emp_code == 'MR10001'
        or _role_code in ('key_leadership', 'ea', 'vgk4u', 'vgk4u_supreme', 'vgk_mentor', 'hr')
        or 'accounts' in _dept_name
        or (current_user.hierarchy_level or 0) >= 80
    )
    if not _allowed:
        raise HTTPException(status_code=403, detail="Access restricted to Key Leadership, EA, Accounts, or MR10001")

    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if not from_date:
        today = get_indian_date()
        from_date = date(today.year, today.month, 1)
    if not to_date:
        to_date = get_indian_date()

    punch_q = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == employee_id,
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    )
    total_count = punch_q.count()
    offset      = (page - 1) * per_page
    punches     = punch_q.order_by(StaffAttendance.date.desc()).offset(offset).limit(per_page).all()

    sheet_map = {}
    if punches:
        dates = [p.date for p in punches]
        sheets = db.query(StaffAttendanceSheet).filter(
            StaffAttendanceSheet.employee_id == employee_id,
            StaffAttendanceSheet.date.in_(dates)
        ).all()
        sheet_map = {s.date: s for s in sheets}

    exc_map = {}
    if punches:
        dates = [p.date for p in punches]
        excs = db.query(StaffAttendanceException).filter(
            StaffAttendanceException.employee_id == employee_id,
            StaffAttendanceException.date.in_(dates)
        ).all()
        exc_map = {e.date: e for e in excs}

    def fmt_time(dt):
        return dt.strftime("%I:%M %p") if dt else None

    def fmt_loc(loc_json):
        if not loc_json:
            return None
        if isinstance(loc_json, dict):
            # Prefer stored human-readable address first
            addr = loc_json.get('address') or loc_json.get('formatted_address') or loc_json.get('place')
            if addr:
                return str(addr)[:120]
            # Extract coordinates (JSONB uses latitude/longitude keys)
            lat = loc_json.get('lat') or loc_json.get('latitude')
            lng = loc_json.get('lng') or loc_json.get('longitude')
            if lat and lng:
                # Try Nominatim reverse-geocode (cached at ~100m granularity)
                readable = _nominatim_reverse(float(lat), float(lng))
                if readable:
                    return readable
                # Fallback: show coordinates only if geocoding failed
                return f"{round(float(lat),4)}, {round(float(lng),4)}"
        return None

    records = []
    for p in punches:
        s   = sheet_map.get(p.date)
        exc = exc_map.get(p.date)

        total_mins = p.worked_minutes or 0
        total_hrs  = round(total_mins / 60, 2) if total_mins else None

        # submitted_hours = marked_hours (HR-submitted; always populated once sheet exists)
        submitted_hrs    = float(s.marked_hours) if s and s.marked_hours is not None else None
        approved_hrs     = float(s.approved_hours) if s and s.approved_hours is not None else None
        exception_hrs    = float(exc.approved_hours) if exc else None
        # DC-TIMEREPORT-V3: timesheet_approved = approved_hours / submitted_hours ratio
        # No timestamp — show how many hours were approved out of submitted.
        # attendance_status = final status ONLY when HR has approved (approval_status='approved')
        attendance_status = (
            s.attendance_status.value
            if (s and s.attendance_status
                and s.approval_status
                and s.approval_status.value == 'approved')
            else None
        )

        # "Company" = auto-closed by system; "Self" = employee manually logged out
        logout_type = "Company" if p.is_auto_closed else "Self"

        records.append({
            "date":               p.date.isoformat(),
            "in_time":            fmt_time(p.clock_in),
            "out_time":           fmt_time(p.clock_out),
            "total_hours":        total_hrs,
            "submitted_hours":    submitted_hrs,
            "approved_hours":     approved_hrs,
            "exception_hours":    exception_hrs,
            "attendance_status":  attendance_status,
            "in_location":        fmt_loc(p.clock_in_location),
            "out_location":       fmt_loc(p.clock_out_location),
            "logout_type":        logout_type,
        })

    return {
        "success": True,
        "employee": {
            "id":        employee.id,
            "name":      employee.full_name,
            "emp_code":  employee.emp_code,
            "department": employee.department.name if employee.department else None,
        },
        "records": records,
        "pagination": {
            "total":       total_count,
            "page":        page,
            "per_page":    per_page,
            "total_pages": max(1, (total_count + per_page - 1) // per_page),
        }
    }
