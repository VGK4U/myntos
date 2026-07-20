"""
Staff Field Work & KM Tracking API Endpoints (DC Protocol Compliant)
GPS-driven field work tracking with reimbursement calculation

Key Features:
- Real-time GPS tracking for field work
- Transport mode selection with rate calculation
- KM tracking and reimbursement calculation
- GPS permission status monitoring
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
from pydantic import BaseModel, Field, validator
import pytz

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.staff_attendance import StaffAttendance
from app.models.staff_field_work import (
    StaffFieldWorkSession, StaffFieldWorkTrackPoint, StaffTransportRate,
    StaffAttendanceApproval, StaffFieldWorkLog, log_field_work_activity,
    haversine_distance
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.staff_hierarchy import get_accessible_employee_ids, get_team_member_ids

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


class FieldWorkStartRequest(BaseModel):
    transport_mode: str = Field(default="bike")
    location: Optional[dict] = None
    
    class Config:
        extra = "allow"


class GPSTrackPointRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: Optional[str] = None


class GPSStatusRequest(BaseModel):
    status: str = Field(default="granted")
    reason: Optional[str] = None


class TransportModeUpdateRequest(BaseModel):
    transport_mode: str


class ApprovalActionRequest(BaseModel):
    action: str = Field(...)
    remarks: Optional[str] = None
    worked_minutes_approved: Optional[int] = None
    reimbursement_approved: Optional[float] = None
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['approve', 'reject']
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")
        return v


@router.get("/transport-rates", summary="Get transport rates")
async def get_transport_rates(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get active transport rates
    DC: Return current effective rates
    """
    today = get_indian_date()
    
    rates = db.query(StaffTransportRate).filter(
        StaffTransportRate.is_active == True,
        StaffTransportRate.effective_from <= today,
        or_(
            StaffTransportRate.effective_to == None,
            StaffTransportRate.effective_to >= today
        )
    ).all()
    
    return {
        "success": True,
        "rates": [r.to_dict() for r in rates]
    }


@router.post("/session/start", summary="Start field work session")
async def start_field_work_session(
    session_data: FieldWorkStartRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Start field work session
    DC: One active session per attendance
    WVV: Validate attendance exists and is field mode
    """
    today = get_indian_date()
    now = get_indian_time()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance or not attendance.clock_in:
        raise HTTPException(status_code=400, detail="Must clock in first before starting field work")
    
    if attendance.clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out for the day")
    
    if attendance.location_mode != 'field':
        attendance.location_mode = 'field'
    
    existing_session = db.query(StaffFieldWorkSession).filter(
        StaffFieldWorkSession.attendance_id == attendance.id,
        StaffFieldWorkSession.status == 'active'
    ).first()
    
    if existing_session:
        return {
            "success": True,
            "message": "Field work session already active",
            "session": existing_session.to_dict()
        }
    
    rate = db.query(StaffTransportRate).filter(
        StaffTransportRate.transport_mode == session_data.transport_mode,
        StaffTransportRate.is_active == True
    ).first()
    
    rate_per_km = Decimal(str(rate.rate_per_km)) if rate else Decimal('4.00')
    
    session = StaffFieldWorkSession(
        attendance_id=attendance.id,
        employee_id=current_user.id,
        transport_mode=session_data.transport_mode,
        session_start=now,
        rate_per_km=rate_per_km,
        status='active'
    )
    db.add(session)
    db.flush()
    
    attendance.field_session_id = session.id
    
    if session_data.location and session_data.location.get('latitude'):
        track_point = StaffFieldWorkTrackPoint(
            session_id=session.id,
            latitude=session_data.location['latitude'],
            longitude=session_data.location['longitude'],
            accuracy=session_data.location.get('accuracy'),
            captured_at=now,
            gps_status='active',
            is_valid=True
        )
        db.add(track_point)
        session.point_count = 1
    
    log_field_work_activity(
        db=db,
        session_id=session.id,
        employee_id=current_user.id,
        action='session_start',
        details={
            "transport_mode": session_data.transport_mode,
            "rate_per_km": float(rate_per_km),
            "time": now.isoformat()
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(session)
    
    return {
        "success": True,
        "message": f"Field work session started with {session_data.transport_mode}",
        "session": session.to_dict()
    }


@router.post("/session/heartbeat", summary="Update GPS position")
async def update_gps_position(
    point_data: GPSTrackPointRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update GPS position (heartbeat)
    DC: Calculate distance from previous point
    WVV: Validate accuracy and detect anomalies
    """
    today = get_indian_date()
    now = get_indian_time()
    
    session = db.query(StaffFieldWorkSession).join(
        StaffAttendance
    ).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today,
        StaffFieldWorkSession.status == 'active'
    ).first()
    
    if not session:
        raise HTTPException(status_code=400, detail="No active field work session")
    
    last_point = db.query(StaffFieldWorkTrackPoint).filter(
        StaffFieldWorkTrackPoint.session_id == session.id,
        StaffFieldWorkTrackPoint.is_valid == True
    ).order_by(StaffFieldWorkTrackPoint.captured_at.desc()).first()
    
    track_point = StaffFieldWorkTrackPoint(
        session_id=session.id,
        latitude=point_data.latitude,
        longitude=point_data.longitude,
        accuracy=point_data.accuracy,
        altitude=point_data.altitude,
        speed=point_data.speed,
        heading=point_data.heading,
        captured_at=now,
        gps_status='active'
    )
    
    segment_km = Decimal('0')
    if last_point:
        segment_km = track_point.calculate_segment_distance(
            last_point.latitude,
            last_point.longitude
        )
        track_point.segment_km = segment_km
    
    db.add(track_point)
    
    session.point_count = (session.point_count or 0) + 1
    session.total_km = Decimal(str(session.total_km or 0)) + segment_km
    session.reimbursement_amount = session.total_km * Decimal(str(session.rate_per_km or 0))
    session.gps_permission_status = 'granted'
    
    if session.last_gps_off_at:
        off_minutes = int((now - session.last_gps_off_at).total_seconds() / 60)
        session.total_gps_off_minutes = (session.total_gps_off_minutes or 0) + off_minutes
        session.last_gps_off_at = None
    
    db.commit()
    
    return {
        "success": True,
        "segment_km": float(segment_km),
        "total_km": float(session.total_km),
        "reimbursement_amount": float(session.reimbursement_amount),
        "point_count": session.point_count,
        "is_valid": track_point.is_valid,
        "validation_reason": track_point.validation_reason
    }


@router.post("/session/gps-status", summary="Update GPS permission status")
async def update_gps_status(
    status_data: GPSStatusRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update GPS permission status
    DC: Track GPS on/off periods for attendance calculation
    WVV: Record duration when GPS is denied
    """
    today = get_indian_date()
    now = get_indian_time()
    
    session = db.query(StaffFieldWorkSession).join(
        StaffAttendance
    ).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today,
        StaffFieldWorkSession.status == 'active'
    ).first()
    
    if not session:
        raise HTTPException(status_code=400, detail="No active field work session")
    
    previous_status = session.gps_permission_status
    session.gps_permission_status = status_data.status
    
    if status_data.status == 'denied' and previous_status != 'denied':
        session.last_gps_off_at = now
        log_field_work_activity(
            db=db,
            session_id=session.id,
            employee_id=current_user.id,
            action='gps_off',
            details={"reason": status_data.reason, "time": now.isoformat()},
            previous_value={"status": previous_status},
            new_value={"status": status_data.status},
            ip_address=get_client_ip(request)
        )
    elif status_data.status == 'granted' and previous_status == 'denied':
        if session.last_gps_off_at:
            off_minutes = int((now - session.last_gps_off_at).total_seconds() / 60)
            session.total_gps_off_minutes = (session.total_gps_off_minutes or 0) + off_minutes
            session.last_gps_off_at = None
        
        log_field_work_activity(
            db=db,
            session_id=session.id,
            employee_id=current_user.id,
            action='gps_on',
            details={"time": now.isoformat()},
            previous_value={"status": previous_status},
            new_value={"status": status_data.status},
            ip_address=get_client_ip(request)
        )
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.id == session.attendance_id
    ).first()
    if attendance:
        attendance.gps_permission_status = status_data.status
        attendance.total_gps_off_minutes = session.total_gps_off_minutes
    
    db.commit()
    
    return {
        "success": True,
        "gps_status": session.gps_permission_status,
        "total_gps_off_minutes": session.total_gps_off_minutes,
        "message": "GPS is OFF - Your attendance is not being calculated" if status_data.status == 'denied' else "GPS tracking resumed"
    }


@router.post("/session/transport-mode", summary="Update transport mode")
async def update_transport_mode(
    mode_data: TransportModeUpdateRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update transport mode during field work
    DC: Apply new rate from point of change
    WVV: Log transport mode change for audit
    """
    today = get_indian_date()
    now = get_indian_time()
    
    session = db.query(StaffFieldWorkSession).join(
        StaffAttendance
    ).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today,
        StaffFieldWorkSession.status == 'active'
    ).first()
    
    if not session:
        raise HTTPException(status_code=400, detail="No active field work session")
    
    rate = db.query(StaffTransportRate).filter(
        StaffTransportRate.transport_mode == mode_data.transport_mode,
        StaffTransportRate.is_active == True
    ).first()
    
    if not rate:
        raise HTTPException(status_code=400, detail=f"Invalid transport mode: {mode_data.transport_mode}")
    
    previous_mode = session.transport_mode
    previous_rate = float(session.rate_per_km) if session.rate_per_km else 0
    
    session.transport_mode = mode_data.transport_mode
    session.rate_per_km = rate.rate_per_km
    session.reimbursement_amount = session.total_km * rate.rate_per_km
    
    log_field_work_activity(
        db=db,
        session_id=session.id,
        employee_id=current_user.id,
        action='transport_change',
        details={"time": now.isoformat()},
        previous_value={"transport_mode": previous_mode, "rate_per_km": previous_rate},
        new_value={"transport_mode": mode_data.transport_mode, "rate_per_km": float(rate.rate_per_km)},
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "transport_mode": session.transport_mode,
        "rate_per_km": float(session.rate_per_km),
        "total_km": float(session.total_km),
        "reimbursement_amount": float(session.reimbursement_amount),
        "message": f"Transport mode changed to {mode_data.transport_mode}"
    }


@router.get("/session/current", summary="Get current field work session")
async def get_current_session(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current field work session with stats
    DC: Return real-time session data
    """
    today = get_indian_date()
    
    session = db.query(StaffFieldWorkSession).join(
        StaffAttendance
    ).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).order_by(StaffFieldWorkSession.created_at.desc()).first()
    
    if not session:
        return {
            "success": True,
            "session": None,
            "has_active_session": False
        }
    
    return {
        "success": True,
        "session": session.to_dict(include_points=True),
        "has_active_session": session.status == 'active'
    }


@router.post("/session/finalize", summary="Finalize field work session")
async def finalize_field_work_session(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Finalize field work session
    DC: Calculate final totals and create approval request
    WVV: Validate all data before submission
    """
    today = get_indian_date()
    now = get_indian_time()
    
    session = db.query(StaffFieldWorkSession).join(
        StaffAttendance
    ).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today,
        StaffFieldWorkSession.status == 'active'
    ).first()
    
    if not session:
        raise HTTPException(status_code=400, detail="No active field work session")
    
    if session.last_gps_off_at:
        off_minutes = int((now - session.last_gps_off_at).total_seconds() / 60)
        session.total_gps_off_minutes = (session.total_gps_off_minutes or 0) + off_minutes
        session.last_gps_off_at = None
    
    session.session_end = now
    session.status = 'completed'
    session.total_km = session.calculate_total_km()
    session.reimbursement_amount = session.calculate_reimbursement()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.id == session.attendance_id
    ).first()
    
    if attendance:
        attendance.total_gps_off_minutes = session.total_gps_off_minutes
    
    log_field_work_activity(
        db=db,
        session_id=session.id,
        employee_id=current_user.id,
        action='session_end',
        details={
            "time": now.isoformat(),
            "total_km": float(session.total_km),
            "reimbursement": float(session.reimbursement_amount),
            "gps_off_minutes": session.total_gps_off_minutes
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(session)
    
    return {
        "success": True,
        "message": "Field work session finalized",
        "session": session.to_dict(),
        "summary": {
            "total_km": float(session.total_km),
            "transport_mode": session.transport_mode,
            "rate_per_km": float(session.rate_per_km) if session.rate_per_km else 0,
            "reimbursement_amount": float(session.reimbursement_amount),
            "gps_off_minutes": session.total_gps_off_minutes,
            "point_count": session.point_count
        }
    }


@router.get("/session/history", summary="Get field work session history")
async def get_session_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get field work session history
    DC: Return historical session data
    """
    query = db.query(StaffFieldWorkSession).filter(
        StaffFieldWorkSession.employee_id == current_user.id
    )
    
    if start_date:
        query = query.filter(StaffFieldWorkSession.session_start >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.filter(StaffFieldWorkSession.session_start <= datetime.combine(end_date, datetime.max.time()))
    
    sessions = query.order_by(StaffFieldWorkSession.session_start.desc()).limit(50).all()
    
    return {
        "success": True,
        "sessions": [s.to_dict() for s in sessions],
        "total_km": sum(float(s.total_km or 0) for s in sessions),
        "total_reimbursement": sum(float(s.reimbursement_amount or 0) for s in sessions)
    }


@router.get("/pending-approvals", summary="Get pending attendance approvals (Manager)")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get pending attendance approvals for manager review
    DC Protocol (Dec 04, 2025): Return pending approvals for entire downline (recursive)
    """
    # DC Protocol (Feb 25, 2026): Use get_team_member_ids to exclude self + hidden accounts
    subordinate_ids = get_team_member_ids(current_user, db, StaffEmployee)
    
    if not subordinate_ids:
        return {
            "success": True,
            "approvals": [],
            "count": 0
        }
    
    approvals = db.query(StaffAttendanceApproval).filter(
        StaffAttendanceApproval.employee_id.in_(subordinate_ids),
        StaffAttendanceApproval.approval_status == 'pending'
    ).order_by(StaffAttendanceApproval.submitted_at.desc()).all()
    
    return {
        "success": True,
        "approvals": [a.to_dict() for a in approvals],
        "count": len(approvals)
    }


@router.post("/approve/{approval_id}", summary="Approve/Reject attendance")
async def process_approval(
    approval_id: int,
    action_data: ApprovalActionRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve or reject attendance record
    DC: Manager approval workflow
    WVV: Validate manager authority
    """
    now = get_indian_time()
    
    approval = db.query(StaffAttendanceApproval).filter(
        StaffAttendanceApproval.id == approval_id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval record not found")
    
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == approval.employee_id
    ).first()
    
    # DC Protocol (Dec 04, 2025): Check if employee is in manager's downline (recursive)
    downline_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
    is_in_downline = employee.id in downline_ids and employee.id != current_user.id
    is_hr = current_user.role and current_user.role.role_code in ['hr', 'vgk4u', 'ea']
    
    if not is_in_downline and not is_hr:
        raise HTTPException(status_code=403, detail="Not authorized to approve this record")
    
    if action_data.action == 'approve':
        approval.approval_status = 'approved'
        approval.approver_id = current_user.id
        approval.approved_at = now
        approval.approver_remarks = action_data.remarks
        
        if action_data.worked_minutes_approved is not None:
            approval.worked_minutes_approved = action_data.worked_minutes_approved
        else:
            approval.worked_minutes_approved = approval.worked_minutes_submitted
        
        if action_data.reimbursement_approved is not None:
            approval.reimbursement_approved = Decimal(str(action_data.reimbursement_approved))
        else:
            approval.reimbursement_approved = approval.field_work_reimbursement
        
        attendance = db.query(StaffAttendance).filter(
            StaffAttendance.id == approval.attendance_id
        ).first()
        if attendance:
            attendance.approval_status = 'approved'
            attendance.worked_minutes = approval.worked_minutes_approved
        
        message = "Attendance approved successfully"
        
    elif action_data.action == 'reject':
        if not action_data.remarks:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        approval.approval_status = 'rejected'
        approval.approver_id = current_user.id
        approval.approved_at = now
        approval.rejection_reason = action_data.remarks
        
        attendance = db.query(StaffAttendance).filter(
            StaffAttendance.id == approval.attendance_id
        ).first()
        if attendance:
            attendance.approval_status = 'rejected'
        
        message = "Attendance rejected"
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    db.commit()
    
    return {
        "success": True,
        "message": message,
        "approval": approval.to_dict()
    }
