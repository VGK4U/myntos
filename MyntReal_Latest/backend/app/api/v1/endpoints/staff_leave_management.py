"""
Staff Leave Management API Endpoints (DC Protocol Compliant)
Three-tier approval workflow: Employee → Manager → HR

Key Features:
- Apply for leave (full/half day)
- View leave balance
- Cancel leave requests
- Manager/HR approval workflow
- Document upload support
- Attendance conflict resolution

Created: Jan 07, 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffDepartment, StaffMenuMaster, StaffEmployeeMenuSettings
from app.models.staff_attendance_sheet import (
    StaffAttendanceSheet, AttendanceStatus, ReconciliationStatus, ApprovalStatus,
    StaffLeaveType, StaffLeaveBalance, StaffLeaveRequest,
    StaffLeaveRequestDay, StaffLeaveApproval, LeaveRequestStatus
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)

# Menu access control codes for leave management
# DC Protocol (Jan 22, 2026): Use database menu_code format (staff_leave_approvals, not leave-approvals)
LEAVE_APPROVALS_MENU_CODE = "staff_leave_approvals"


def check_menu_access(db: Session, employee_id: int, menu_code: str, require_edit: bool = False) -> bool:
    """
    Check if employee has access to a menu item
    Uses RVZ Menu Access Control system (StaffEmployeeMenuSettings)
    
    Args:
        db: Database session
        employee_id: Employee ID to check
        menu_code: Menu code to check access for
        require_edit: If True, checks can_edit; otherwise checks can_view
    
    Returns:
        bool: True if employee has the required access
    """
    menu = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.menu_code == menu_code,
        StaffMenuMaster.is_active == True
    ).first()
    
    if not menu:
        logger.warning(f"[DC-LEAVE] Menu code '{menu_code}' not found in StaffMenuMaster")
        return False
    
    settings = db.query(StaffEmployeeMenuSettings).filter(
        StaffEmployeeMenuSettings.employee_id == employee_id,
        StaffEmployeeMenuSettings.menu_id == menu.id
    ).first()
    
    if settings:
        if require_edit:
            return settings.can_edit
        return settings.can_view
    
    if require_edit:
        return menu.is_default_accessible
    return menu.is_default_visible


router = APIRouter()


def get_indian_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def get_indian_datetime():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)


# ==================== SCHEMAS ====================

class LeaveTypeResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    requires_document: bool
    allow_half_day: bool
    max_consecutive_days: Optional[int]
    min_advance_days: int
    
    class Config:
        from_attributes = True


class LeaveBalanceResponse(BaseModel):
    leave_type_id: int
    leave_type_code: str
    leave_type_name: str
    balance: float
    used: float
    pending: float
    available: float
    
    class Config:
        from_attributes = True


class LeaveRequestDayCreate(BaseModel):
    leave_date: date
    is_half_day: bool = False
    half_day_type: Optional[str] = None  # 'first_half' or 'second_half'
    
    @validator('half_day_type')
    def validate_half_day_type(cls, v, values):
        if values.get('is_half_day') and not v:
            raise ValueError('half_day_type is required when is_half_day is True')
        if v and v not in ['first_half', 'second_half']:
            raise ValueError('half_day_type must be first_half or second_half')
        return v


class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    reason: str = Field(..., min_length=10, max_length=500)
    days: List[LeaveRequestDayCreate]
    document_ids: Optional[List[int]] = None
    conflict_resolution: Optional[str] = None  # 'skip' or 'replace'
    mark_as_lop: Optional[bool] = False  # Set to True if user acknowledges Loss of Pay when balance is 0
    
    @validator('days')
    def validate_days(cls, v):
        if not v:
            raise ValueError('At least one leave day is required')
        dates = [d.leave_date for d in v]
        if len(dates) != len(set(dates)):
            raise ValueError('Duplicate dates are not allowed')
        return v


class LeaveRequestResponse(BaseModel):
    id: int
    leave_type_id: int
    leave_type_name: str
    employee_id: int
    employee_name: str
    reason: str
    status: str
    total_days: float
    applied_at: datetime
    days: List[dict]
    can_cancel: bool
    
    class Config:
        from_attributes = True


class LeaveApprovalAction(BaseModel):
    action: str = Field(..., pattern='^(approve|reject)$')
    remarks: Optional[str] = None
    
    @validator('remarks')
    def validate_remarks_for_rejection(cls, v, values):
        if values.get('action') == 'reject' and not v:
            raise ValueError('Remarks are required when rejecting a leave request')
        return v


class LeaveHistoryFilter(BaseModel):
    leave_type_id: Optional[int] = None
    status: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None


# ==================== EMPLOYEE ENDPOINTS ====================

@router.get("/leave-types", summary="Get available leave types")
def get_leave_types(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all active leave types
    
    DC Protocol Note: Leave types are intentionally global master data 
    (Casual, Sick, Approved, Unpaid are standard across all companies).
    Company-wise segregation is enforced on leave_balances and leave_requests.
    """
    leave_types = db.query(StaffLeaveType).filter(
        StaffLeaveType.is_active == True
    ).order_by(StaffLeaveType.display_order).all()
    
    return {
        "success": True,
        "leave_types": [
            {
                "id": lt.id,
                "code": lt.code,
                "name": lt.name,
                "description": lt.description,
                "requires_document": lt.requires_document,
                "allow_half_day": lt.allow_half_day,
                "max_consecutive_days": lt.max_consecutive_days,
                "min_advance_days": lt.min_advance_days
            }
            for lt in leave_types
        ]
    }


@router.get("/my-balance", summary="Get current user's leave balance")
def get_my_leave_balance(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get leave balance for current employee"""
    
    leave_types = db.query(StaffLeaveType).filter(
        StaffLeaveType.is_active == True
    ).order_by(StaffLeaveType.display_order).all()
    
    balances = []
    for lt in leave_types:
        balance_record = db.query(StaffLeaveBalance).filter(
            StaffLeaveBalance.employee_id == current_user.id,
            StaffLeaveBalance.leave_type_id == lt.id,
            StaffLeaveBalance.year == get_indian_date().year
        ).first()
        
        pending_days = db.query(func.sum(StaffLeaveRequestDay.day_value)).join(
            StaffLeaveRequest
        ).filter(
            StaffLeaveRequest.employee_id == current_user.id,
            StaffLeaveRequest.leave_type_id == lt.id,
            StaffLeaveRequest.status.in_(['draft', 'pending_manager', 'pending_hr'])
        ).scalar() or Decimal('0')
        
        current_balance = balance_record.balance if balance_record else Decimal('0')
        used = balance_record.used if balance_record else Decimal('0')
        available = current_balance - used - pending_days
        
        balances.append({
            "leave_type_id": lt.id,
            "leave_type_code": lt.code,
            "leave_type_name": lt.name,
            "balance": float(current_balance),
            "used": float(used),
            "pending": float(pending_days),
            "available": float(max(0, available))
        })
    
    return {
        "success": True,
        "employee_id": current_user.id,
        "employee_name": current_user.full_name,
        "year": get_indian_date().year,
        "balances": balances
    }


@router.post("/apply", summary="Apply for leave")
def apply_leave(
    data: LeaveRequestCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Submit a leave request"""
    
    leave_type = db.query(StaffLeaveType).filter(
        StaffLeaveType.id == data.leave_type_id,
        StaffLeaveType.is_active == True
    ).first()
    
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")
    
    if not leave_type.allow_half_day:
        for day in data.days:
            if day.is_half_day:
                raise HTTPException(
                    status_code=400,
                    detail=f"{leave_type.name} does not allow half-day leaves"
                )
    
    today = get_indian_date()
    # Advance notice only applies to future dates - allow retroactive applications for past dates
    if leave_type.min_advance_days > 0:
        min_date = today + timedelta(days=leave_type.min_advance_days)
        for day in data.days:
            # Only validate advance notice for future dates
            if day.leave_date >= today and day.leave_date < min_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"{leave_type.name} requires at least {leave_type.min_advance_days} day(s) advance notice"
                )
    
    if leave_type.max_consecutive_days:
        sorted_dates = sorted([d.leave_date for d in data.days])
        consecutive_count = 1
        max_consecutive = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 1
        if max_consecutive > leave_type.max_consecutive_days:
            raise HTTPException(
                status_code=400,
                detail=f"{leave_type.name} allows maximum {leave_type.max_consecutive_days} consecutive days"
            )
    
    total_days = Decimal('0')
    for day in data.days:
        total_days += Decimal('0.5') if day.is_half_day else Decimal('1')
    
    balance_record = db.query(StaffLeaveBalance).filter(
        StaffLeaveBalance.employee_id == current_user.id,
        StaffLeaveBalance.leave_type_id == data.leave_type_id,
        StaffLeaveBalance.year == today.year
    ).first()
    
    is_lop = False
    if leave_type.code != 'unpaid_leave':
        current_balance = balance_record.balance if balance_record else Decimal('0')
        used = balance_record.used if balance_record else Decimal('0')
        available = current_balance - used
        
        if total_days > available:
            if data.mark_as_lop:
                is_lop = True
                logger.info(f"[DC-LEAVE-LOP] Leave request marked as Loss of Pay - Employee: {current_user.emp_code}, Available: {available}, Requested: {total_days}")
            else:
                return {
                    "success": False,
                    "requires_lop_acknowledgment": True,
                    "available_balance": float(available),
                    "requested_days": float(total_days),
                    "message": f"Insufficient {leave_type.name} balance. Available: {float(available)}, Requested: {float(total_days)}. This will be marked as Loss of Pay (LOP)."
                }
    
    conflicts = []
    for day in data.days:
        existing_attendance = db.query(StaffAttendanceSheet).filter(
            StaffAttendanceSheet.employee_id == current_user.id,
            StaffAttendanceSheet.date == day.leave_date,
            StaffAttendanceSheet.attendance_status.in_([
                AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY
            ])
        ).first()
        
        if existing_attendance:
            conflicts.append({
                "date": str(day.leave_date),
                "status": existing_attendance.attendance_status.value
            })
    
    if conflicts and not data.conflict_resolution:
        return {
            "success": False,
            "requires_conflict_resolution": True,
            "conflicts": conflicts,
            "message": "Attendance records exist for some dates. Choose 'skip' to exclude conflicting dates or 'replace' to override attendance."
        }
    
    dates_to_skip = []
    if conflicts and data.conflict_resolution == 'skip':
        dates_to_skip = [c['date'] for c in conflicts]
    
    valid_days = [day for day in data.days if str(day.leave_date) not in dates_to_skip]
    if not valid_days:
        raise HTTPException(
            status_code=400,
            detail="No valid leave days after conflict resolution"
        )
    
    all_dates = [day.leave_date for day in valid_days]
    start_date = min(all_dates)
    end_date = max(all_dates)
    
    actual_total_days = Decimal('0')
    day_values = {}
    for day in valid_days:
        days_count = Decimal('0.5') if day.is_half_day else Decimal('1')
        actual_total_days += days_count
        day_values[day.leave_date] = days_count
    
    initial_status = 'pending_manager'
    skip_level_approval = False
    if not current_user.reporting_manager_id:
        initial_status = 'pending_hr'
        skip_level_approval = True
        logger.info(f"[DC-LEAVE-SKIP] No manager assigned for {current_user.emp_code}, escalating directly to HR")
    
    leave_request = StaffLeaveRequest(
        employee_id=current_user.id,
        leave_type_id=data.leave_type_id,
        company_id=current_user.base_company_id,
        reason=data.reason,
        status=initial_status,
        is_lop=is_lop,
        start_date=start_date,
        end_date=end_date,
        total_days=actual_total_days
    )
    db.add(leave_request)
    db.flush()
    
    for day in valid_days:
        request_day = StaffLeaveRequestDay(
            leave_request_id=leave_request.id,
            date=day.leave_date,
            is_half_day=day.is_half_day,
            half_day_type=day.half_day_type,
            day_value=day_values[day.leave_date]
        )
        db.add(request_day)
    
    if data.document_ids:
        pass
    
    db.commit()
    
    logger.info(f"Leave request #{leave_request.id} submitted by {current_user.emp_code}")
    
    message = "Leave request submitted successfully"
    if skip_level_approval:
        message = "Leave request submitted successfully (escalated to HR - no manager assigned)"
    
    return {
        "success": True,
        "message": message,
        "leave_request_id": leave_request.id,
        "total_days": float(actual_total_days),
        "status": initial_status,
        "skipped_dates": dates_to_skip,
        "skip_level_approval": skip_level_approval
    }


@router.get("/my-requests", summary="Get current user's leave requests")
def get_my_leave_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    year: Optional[int] = Query(None, description="Filter by year"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get leave request history for current employee"""
    
    query = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.employee_id == current_user.id
    )
    
    if status:
        query = query.filter(StaffLeaveRequest.status == status)
    
    if year:
        query = query.filter(
            func.extract('year', StaffLeaveRequest.created_at) == year
        )
    else:
        query = query.filter(
            func.extract('year', StaffLeaveRequest.created_at) == get_indian_date().year
        )
    
    requests = query.order_by(desc(StaffLeaveRequest.created_at)).all()
    
    result = []
    is_skip_level = not current_user.reporting_manager_id
    for req in requests:
        leave_type = db.query(StaffLeaveType).filter_by(id=req.leave_type_id).first()
        days = db.query(StaffLeaveRequestDay).filter_by(leave_request_id=req.id).order_by(
            StaffLeaveRequestDay.date
        ).all()
        
        can_cancel = req.status in ['draft', 'pending_manager'] or (is_skip_level and req.status == 'pending_hr')
        
        result.append({
            "id": req.id,
            "leave_type_id": req.leave_type_id,
            "leave_type_name": leave_type.name if leave_type else "Unknown",
            "reason": req.reason,
            "status": req.status,
            "total_days": float(req.total_days) if req.total_days else 0,
            "applied_at": req.created_at.isoformat() if req.created_at else None,
            "can_cancel": can_cancel,
            "days": [
                {
                    "date": str(d.date),
                    "is_half_day": d.is_half_day,
                    "half_day_type": d.half_day_type,
                    "days_count": float(d.day_value)
                }
                for d in days
            ]
        })
    
    return {
        "success": True,
        "requests": result,
        "total": len(result)
    }


@router.post("/cancel/{request_id}", summary="Cancel a leave request")
def cancel_leave_request(
    request_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending leave request"""
    
    leave_request = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.id == request_id,
        StaffLeaveRequest.employee_id == current_user.id
    ).first()
    
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    is_skip_level = not current_user.reporting_manager_id
    can_cancel = leave_request.status in ['draft', 'pending_manager'] or (is_skip_level and leave_request.status == 'pending_hr')
    
    if not can_cancel:
        raise HTTPException(
            status_code=400,
            detail="Only draft or pending requests can be cancelled"
        )
    
    leave_request.status = 'cancelled'
    leave_request.cancelled_at = get_indian_datetime()
    leave_request.cancelled_by = current_user.id
    
    db.commit()
    
    logger.info(f"Leave request #{request_id} cancelled by {current_user.emp_code}")
    
    return {
        "success": True,
        "message": "Leave request cancelled successfully"
    }


# ==================== MANAGER APPROVAL ENDPOINTS ====================

@router.get("/pending-approvals/manager", summary="Get pending approvals for manager")
def get_pending_manager_approvals(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get leave requests pending manager approval
    
    Access Control: Requires can_view access to leave-approvals menu
    Manager sees only their direct subordinates' requests
    """
    
    if not check_menu_access(db, current_user.id, LEAVE_APPROVALS_MENU_CODE, require_edit=False):
        raise HTTPException(status_code=403, detail="You do not have access to leave approvals")
    
    subordinate_ids = db.query(StaffEmployee.id).filter(
        StaffEmployee.reporting_manager_id == current_user.id,
        StaffEmployee.status == 'active'
    ).all()
    subordinate_ids = [s[0] for s in subordinate_ids]
    
    if not subordinate_ids:
        return {
            "success": True,
            "requests": [],
            "total": 0,
            "message": "No subordinates assigned"
        }
    
    pending_requests = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.employee_id.in_(subordinate_ids),
        StaffLeaveRequest.status == 'pending_manager'
    ).order_by(StaffLeaveRequest.created_at).all()
    
    result = []
    for req in pending_requests:
        employee = db.query(StaffEmployee).filter_by(id=req.employee_id).first()
        leave_type = db.query(StaffLeaveType).filter_by(id=req.leave_type_id).first()
        days = db.query(StaffLeaveRequestDay).filter_by(leave_request_id=req.id).order_by(
            StaffLeaveRequestDay.date
        ).all()
        
        result.append({
            "id": req.id,
            "employee_id": req.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "employee_code": employee.emp_code if employee else "Unknown",
            "leave_type_id": req.leave_type_id,
            "leave_type_name": leave_type.name if leave_type else "Unknown",
            "reason": req.reason,
            "total_days": float(req.total_days) if req.total_days else 0,
            "applied_at": req.created_at.isoformat() if req.created_at else None,
            "days": [
                {
                    "date": str(d.date),
                    "is_half_day": d.is_half_day,
                    "half_day_type": d.half_day_type
                }
                for d in days
            ]
        })
    
    return {
        "success": True,
        "requests": result,
        "total": len(result)
    }


@router.post("/approve/manager/{request_id}", summary="Manager approves/rejects leave")
def manager_approve_leave(
    request_id: int,
    data: LeaveApprovalAction = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Manager approves or rejects a leave request
    
    Access Control: Requires can_edit access to leave-approvals menu
    """
    
    if not check_menu_access(db, current_user.id, LEAVE_APPROVALS_MENU_CODE, require_edit=True):
        raise HTTPException(status_code=403, detail="You do not have edit access to leave approvals")
    
    leave_request = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.id == request_id,
        StaffLeaveRequest.status == 'pending_manager'
    ).first()
    
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found or not pending manager approval")
    
    employee = db.query(StaffEmployee).filter_by(id=leave_request.employee_id).first()
    if not employee or employee.reporting_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the manager of this employee")
    
    new_status = LeaveRequestStatus.PENDING_HR if data.action == 'approve' else LeaveRequestStatus.REJECTED_MANAGER
    
    approval = StaffLeaveApproval(
        leave_request_id=request_id,
        approver_role='manager',
        approver_id=current_user.id,
        action=data.action,
        previous_status=leave_request.status,
        new_status=new_status,
        comments=data.remarks
    )
    db.add(approval)
    
    if data.action == 'approve':
        leave_request.status = 'pending_hr'
        leave_request.manager_id = current_user.id
        leave_request.manager_decision_at = get_indian_datetime()
        leave_request.manager_comments = data.remarks
        message = "Leave request approved and forwarded to HR"
    else:
        leave_request.status = 'rejected_manager'
        leave_request.manager_id = current_user.id
        leave_request.manager_decision_at = get_indian_datetime()
        leave_request.manager_comments = data.remarks
        message = "Leave request rejected"
    
    db.commit()
    
    logger.info(f"Leave request #{request_id} {data.action}d by manager {current_user.emp_code}")
    
    return {
        "success": True,
        "message": message,
        "new_status": leave_request.status
    }


# ==================== HR APPROVAL ENDPOINTS ====================

@router.get("/pending-approvals/hr", summary="Get pending approvals for HR")
def get_pending_hr_approvals(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get leave requests pending HR final approval
    
    Access Control: Requires can_view access to leave-approvals menu
    HR users see all pending requests in their company
    """
    
    if not check_menu_access(db, current_user.id, LEAVE_APPROVALS_MENU_CODE, require_edit=False):
        raise HTTPException(status_code=403, detail="You do not have access to leave approvals")
    
    pending_requests = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.company_id == current_user.base_company_id,
        StaffLeaveRequest.status == 'pending_hr'
    ).order_by(StaffLeaveRequest.created_at).all()
    
    result = []
    for req in pending_requests:
        employee = db.query(StaffEmployee).filter_by(id=req.employee_id).first()
        leave_type = db.query(StaffLeaveType).filter_by(id=req.leave_type_id).first()
        days = db.query(StaffLeaveRequestDay).filter_by(leave_request_id=req.id).order_by(
            StaffLeaveRequestDay.date
        ).all()
        
        manager_approval = db.query(StaffLeaveApproval).filter(
            StaffLeaveApproval.leave_request_id == req.id,
            StaffLeaveApproval.approver_role == 'manager'
        ).first()
        
        is_skip_level = employee and not employee.reporting_manager_id
        
        result.append({
            "id": req.id,
            "employee_id": req.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "employee_code": employee.emp_code if employee else "Unknown",
            "department": employee.department.name if employee and employee.department else "Unknown",
            "leave_type_id": req.leave_type_id,
            "leave_type_name": leave_type.name if leave_type else "Unknown",
            "reason": req.reason,
            "total_days": float(req.total_days) if req.total_days else 0,
            "applied_at": req.created_at.isoformat() if req.created_at else None,
            "manager_approved_at": req.manager_decision_at.isoformat() if req.manager_decision_at else None,
            "manager_remarks": manager_approval.comments if manager_approval else None,
            "is_skip_level": is_skip_level,
            "days": [
                {
                    "date": str(d.date),
                    "is_half_day": d.is_half_day,
                    "half_day_type": d.half_day_type
                }
                for d in days
            ]
        })
    
    return {
        "success": True,
        "requests": result,
        "total": len(result)
    }


@router.post("/approve/hr/{request_id}", summary="HR approves/rejects leave")
def hr_approve_leave(
    request_id: int,
    data: LeaveApprovalAction = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    HR gives final approval or rejects a leave request
    
    Access Control: Requires can_edit access to leave-approvals menu
    """
    
    if not check_menu_access(db, current_user.id, LEAVE_APPROVALS_MENU_CODE, require_edit=True):
        raise HTTPException(status_code=403, detail="You do not have edit access to leave approvals")
    
    leave_request = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.id == request_id,
        StaffLeaveRequest.status == 'pending_hr'
    ).first()
    
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found or not pending HR approval")
    
    new_status = LeaveRequestStatus.APPROVED if data.action == 'approve' else LeaveRequestStatus.REJECTED_HR
    
    approval = StaffLeaveApproval(
        leave_request_id=request_id,
        approver_role='hr',
        approver_id=current_user.id,
        action=data.action,
        previous_status=leave_request.status,
        new_status=new_status,
        comments=data.remarks
    )
    db.add(approval)
    
    if data.action == 'approve':
        leave_request.status = 'approved'
        leave_request.hr_id = current_user.id
        leave_request.hr_decision_at = get_indian_datetime()
        leave_request.hr_comments = data.remarks
        
        leave_type = db.query(StaffLeaveType).filter_by(id=leave_request.leave_type_id).first()
        days = db.query(StaffLeaveRequestDay).filter_by(leave_request_id=request_id).all()
        
        for day in days:
            existing_attendance = db.query(StaffAttendanceSheet).filter(
                StaffAttendanceSheet.employee_id == leave_request.employee_id,
                StaffAttendanceSheet.date == day.date
            ).first()
            
            # DC Protocol (Jan 07, 2026): Set marked_hours based on full/half day leave
            leave_hours = Decimal('4') if day.is_half_day else Decimal('8')
            leave_net_days = Decimal('0.5') if day.is_half_day else Decimal('1')
            
            if existing_attendance:
                existing_attendance.attendance_status = leave_type.attendance_status
                existing_attendance.marked_hours = leave_hours
                existing_attendance.approved_hours = leave_hours
                existing_attendance.net_days = leave_net_days
                existing_attendance.approval_status = ApprovalStatus.APPROVED
                existing_attendance.notes = f"Leave: {leave_type.name} (Request #{request_id})"
                existing_attendance.updated_at = get_indian_datetime()
            else:
                # [DC_DAR_003 / Task #53] Inherit company_id from the leave
                # requester so this auto-created sheet counts toward the right
                # company in the DAR.
                new_attendance = StaffAttendanceSheet(
                    employee_id=leave_request.employee_id,
                    date=day.date,
                    attendance_status=leave_type.attendance_status,
                    marked_hours=leave_hours,
                    approved_hours=leave_hours,
                    net_days=leave_net_days,
                    approval_status=ApprovalStatus.APPROVED,
                    notes=f"Leave: {leave_type.name} (Request #{request_id})",
                    marked_by_id=current_user.id,
                    reconciliation_status=ReconciliationStatus.MANUAL_OVERRIDE,
                    created_at=get_indian_datetime(),
                    company_id=getattr(leave_request.employee, 'base_company_id', None),
                )
                db.add(new_attendance)
        
        balance = db.query(StaffLeaveBalance).filter(
            StaffLeaveBalance.employee_id == leave_request.employee_id,
            StaffLeaveBalance.leave_type_id == leave_request.leave_type_id,
            StaffLeaveBalance.year == get_indian_date().year
        ).first()
        
        if balance:
            balance.used = (balance.used or Decimal('0')) + leave_request.total_days
            balance.updated_at = get_indian_datetime()
        
        message = "Leave request approved and attendance updated"
    else:
        leave_request.status = 'rejected_hr'
        leave_request.hr_id = current_user.id
        leave_request.hr_decision_at = get_indian_datetime()
        leave_request.hr_comments = data.remarks
        message = "Leave request rejected by HR"
    
    db.commit()
    
    logger.info(f"Leave request #{request_id} {data.action}d by HR {current_user.emp_code}")
    
    return {
        "success": True,
        "message": message,
        "new_status": leave_request.status
    }


# ==================== UTILITY ENDPOINTS ====================

@router.get("/check-conflicts", summary="Check attendance conflicts for dates")
def check_attendance_conflicts(
    dates: str = Query(..., description="Comma-separated dates (YYYY-MM-DD)"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Check if attendance records exist for given dates"""
    
    date_list = [datetime.strptime(d.strip(), '%Y-%m-%d').date() for d in dates.split(',')]
    
    conflicts = []
    for check_date in date_list:
        existing = db.query(StaffAttendanceSheet).filter(
            StaffAttendanceSheet.employee_id == current_user.id,
            StaffAttendanceSheet.date == check_date
        ).first()
        
        if existing:
            conflicts.append({
                "date": str(check_date),
                "status": existing.attendance_status.value,
                "has_conflict": existing.attendance_status in [
                    AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY
                ]
            })
    
    return {
        "success": True,
        "conflicts": conflicts,
        "has_any_conflict": any(c['has_conflict'] for c in conflicts)
    }


@router.get("/request/{request_id}", summary="Get leave request details")
def get_leave_request_details(
    request_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a leave request"""
    
    leave_request = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.id == request_id
    ).first()
    
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    is_owner = leave_request.employee_id == current_user.id
    is_hr = current_user.role and current_user.role.role_code in ['hr', 'ea', 'vgk4u']
    employee = db.query(StaffEmployee).filter_by(id=leave_request.employee_id).first()
    is_manager = employee and employee.reporting_manager_id == current_user.id
    is_skip_level = employee and not employee.reporting_manager_id
    
    if not (is_owner or is_hr or is_manager):
        raise HTTPException(status_code=403, detail="Access denied")
    
    leave_type = db.query(StaffLeaveType).filter_by(id=leave_request.leave_type_id).first()
    days = db.query(StaffLeaveRequestDay).filter_by(leave_request_id=request_id).order_by(
        StaffLeaveRequestDay.date
    ).all()
    approvals = db.query(StaffLeaveApproval).filter_by(leave_request_id=request_id).order_by(
        StaffLeaveApproval.created_at
    ).all()
    
    approval_history = []
    for a in approvals:
        approver = db.query(StaffEmployee).filter_by(id=a.approver_id).first()
        approval_history.append({
            "stage": a.approver_role,
            "action": a.action,
            "remarks": a.comments,
            "action_at": a.created_at.isoformat() if a.created_at else None,
            "approved_by": approver.full_name if approver else "Unknown"
        })
    
    can_cancel = (leave_request.status in ['draft', 'pending_manager'] or (is_skip_level and leave_request.status == 'pending_hr')) and is_owner
    
    return {
        "success": True,
        "request": {
            "id": leave_request.id,
            "employee_id": leave_request.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "leave_type_id": leave_request.leave_type_id,
            "leave_type_name": leave_type.name if leave_type else "Unknown",
            "reason": leave_request.reason,
            "status": leave_request.status,
            "total_days": float(leave_request.total_days) if leave_request.total_days else 0,
            "applied_at": leave_request.created_at.isoformat() if leave_request.created_at else None,
            "is_skip_level": is_skip_level,
            "days": [
                {
                    "date": str(d.date),
                    "is_half_day": d.is_half_day,
                    "half_day_type": d.half_day_type,
                    "days_count": float(d.day_value)
                }
                for d in days
            ],
            "approval_history": approval_history,
            "can_cancel": can_cancel
        }
    }
