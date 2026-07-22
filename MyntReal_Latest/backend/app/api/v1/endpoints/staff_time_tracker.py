"""
Staff Time Tracker & Attendance API Endpoints (DC Protocol Compliant)
Complete attendance and time tracking system with WVV Evidence Capture

Key Features:
- Daily clock in/out with timestamp capture
- Location tracking (office/WFH/field)
- Break management (lunch, tea, personal)
- Auto-calculation of worked hours
- Attendance history and reports
- WVV Protocol: Live selfie + GPS evidence capture

Created: Nov 26, 2025
Updated: Nov 29, 2025 - Added WVV evidence capture integration
DC Protocol: Write-Verify-Validate at all levels
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz
import logging

from app.core.database import get_db
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffRole, StaffDepartment
from app.models.staff_attendance import (
    StaffAttendance, StaffAttendanceBreak, StaffAttendanceLog,
    StaffBreakType, StaffLocationDriftEvent, StaffRealtimeLocation,
    StaffAttendanceEvidence, StaffActivityTimeLog,
    log_attendance_activity, generate_realtime_dc_code
)
from app.models.staff_journey import StaffJourney
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.api.v1.endpoints.staff_task_schemas import (
    ClockInRequest, ClockOutRequest, BreakStartRequest, BreakEndRequest,
    LocationDriftRequest
)
from app.services.attendance_evidence_service import AttendanceEvidenceService
from app.services.location_drift_service import LocationDriftService
from app.utils.staff_hierarchy import get_accessible_employee_ids, get_team_member_ids

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== OFFICE LOCATION CONSTANTS (DC_OFFICE_PROXIMITY_001) ====================

# ==================== LOCATION UPDATE REQUEST MODEL (DC_GPS_BODY_FIX_001) ====================
class LocationUpdateRequest(BaseModel):
    """
    DC_GPS_BODY_FIX_001 (Feb 03, 2026): Accept location data as JSON body
    Fixes: Android native background service sends JSON body, not query params
    Backward compatible: Accepts both 'accuracy' and 'accuracy_m' field names
    """
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    accuracy: Optional[float] = Field(None, description="GPS accuracy in meters (Android field name)")
    accuracy_m: Optional[float] = Field(None, description="GPS accuracy in meters (backend field name)")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    speed: Optional[float] = Field(None, description="Speed (Android sends this)")
    speed_kmh: Optional[float] = Field(None, description="Speed in km/h")
    heading: Optional[float] = Field(None, description="Heading/bearing in degrees")
    battery_level: Optional[float] = Field(None, ge=0, le=100, description="Battery level (Android field)")
    battery_percentage: Optional[int] = Field(None, ge=0, le=100, description="Battery percentage")
    timestamp: Optional[int] = Field(None, description="Unix timestamp from device")
    source: str = Field("heartbeat", description="Location source identifier")
    
    class Config:
        extra = "ignore"  # Ignore extra fields from Android

# Office locations for proximity validation (lat, lng)
OFFICE_LOCATIONS = [
    {"name": "Office 1 - Main", "lat": 17.815743, "lng": 83.205508},
    {"name": "Office 2 - Branch", "lat": 17.841482, "lng": 83.198658}
]
OFFICE_PROXIMITY_RADIUS_METERS = 100  # 100 meters radius for office proximity

def calculate_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    Returns distance in meters
    DC_OFFICE_PROXIMITY_001: Used for office proximity validation
    """
    import math
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def is_near_office(lat: float, lng: float) -> tuple:
    """
    Check if coordinates are within office proximity radius
    Returns (is_near, nearest_office_name, distance_meters)
    DC_OFFICE_PROXIMITY_001: 100m radius validation
    """
    if lat is None or lng is None:
        return (False, None, None)
    
    nearest_office = None
    min_distance = float('inf')
    
    for office in OFFICE_LOCATIONS:
        distance = calculate_distance_meters(lat, lng, office['lat'], office['lng'])
        if distance < min_distance:
            min_distance = distance
            nearest_office = office['name']
    
    is_near = min_distance <= OFFICE_PROXIMITY_RADIUS_METERS
    return (is_near, nearest_office, round(min_distance, 1))


def get_area_name_from_coordinates(lat: float, lng: float) -> str:
    """
    Get area name from coordinates using reverse geocoding
    DC_OFFICE_PROXIMITY_001: Returns formatted location string
    Falls back to coordinate display if reverse geocoding unavailable
    """
    if lat is None or lng is None:
        return None
    
    # Check if near known offices first
    is_near, office_name, distance = is_near_office(lat, lng)
    if is_near:
        return f"{office_name} (In Office)"
    
    # For now, return coordinate-based location identifier
    # Could integrate with Google/OpenStreetMap reverse geocoding API in future
    try:
        import requests
        # Use free Nominatim reverse geocoding (rate limited, add delay for production)
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18"
        headers = {'User-Agent': 'MyntReal-Staff-App/1.0'}
        resp = requests.get(url, headers=headers, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get('address', {})
            # Build readable area name
            parts = []
            for key in ['road', 'neighbourhood', 'suburb', 'city', 'town', 'village']:
                if key in address:
                    parts.append(address[key])
                    if len(parts) >= 2:
                        break
            if parts:
                return ', '.join(parts)
    except Exception as e:
        logger.debug(f"[DC_GEOCODE] Reverse geocoding failed: {e}")
    
    # Fallback: just indicate away from office
    return f"Away ({round(distance, 0)}m from nearest office)"


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


# ==================== ATTENDANCE CLOCK IN/OUT ====================

@router.get("/today", summary="Get today's attendance status")
async def get_today_status(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current user's attendance status for today
    DC: Real-time status check
    """
    today = get_indian_date()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        return {
            "success": True,
            "status": "not_clocked_in",
            "attendance": None,
            "current_time": get_indian_time().strftime("%H:%M:%S"),
            "current_date": today.isoformat()
        }
    
    active_break = db.query(StaffAttendanceBreak).filter(
        StaffAttendanceBreak.attendance_id == attendance.id,
        StaffAttendanceBreak.break_end == None
    ).first()
    
    if not attendance.clock_in:
        status = "not_clocked_in"
    elif attendance.clock_out:
        status = "clocked_out"
    elif active_break:
        status = "on_break"
    else:
        status = "clocked_in"
    
    return {
        "success": True,
        "status": status,
        "attendance": attendance.to_dict(),
        "active_break": active_break.to_dict() if active_break else None,
        "current_time": get_indian_time().strftime("%H:%M:%S"),
        "current_date": today.isoformat()
    }


@router.post("/clock-in", summary="Clock in for the day")
async def clock_in(
    clock_data: ClockInRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Clock in for the day
    DC: One clock-in per day per employee
    WVV: Validate location mode
    """
    today = get_indian_date()
    now = get_indian_time()
    
    existing = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if existing and existing.clock_in:
        raise HTTPException(status_code=400, detail="Already clocked in today")
    
    location_mode = clock_data.work_mode
    
    location_data = None
    if clock_data.location and clock_data.location.latitude and clock_data.location.longitude:
        location_data = {
            "latitude": clock_data.location.latitude,
            "longitude": clock_data.location.longitude,
            "accuracy": clock_data.location.accuracy,
            "address": clock_data.location.address,
            "captured_at": now.isoformat()
        }
    
    device_info = {
        "user_agent": request.headers.get("User-Agent", ""),
        "ip": get_client_ip(request)
    }
    
    if existing:
        existing.clock_in = now
        existing.location_mode = location_mode
        existing.clock_in_location = location_data
        existing.clock_in_device = device_info
        existing.status = 'present'
        attendance = existing
    else:
        attendance = StaffAttendance(
            employee_id=current_user.id,
            date=today,
            clock_in=now,
            location_mode=location_mode,
            clock_in_location=location_data,
            clock_in_device=device_info,
            status='present'
        )
        db.add(attendance)
    
    db.flush()
    
    evidence_result = None
    if clock_data.evidence:
        try:
            gps_data = {
                'latitude': clock_data.evidence.gps_latitude,
                'longitude': clock_data.evidence.gps_longitude,
                'accuracy_m': clock_data.evidence.gps_accuracy_m,
                'altitude': clock_data.evidence.gps_altitude,
                'address': clock_data.evidence.location_address,
                'timestamp_overlay': clock_data.evidence.timestamp_overlay,
                'face_detected': clock_data.evidence.face_detected,
                'face_confidence': clock_data.evidence.face_confidence
            }
            
            evidence_result = await AttendanceEvidenceService.capture_evidence(
                photo_data=clock_data.evidence.photo_base64,
                event_type='clock_in',
                attendance_id=attendance.id,
                gps_data=gps_data,
                employee=current_user,
                db=db,
                device_info=device_info,
                remarks=clock_data.notes
            )
            logger.info(f"Clock-in evidence captured: {evidence_result.get('evidence_id')}")
            
            # DC_PHOTO_SYNC_001 (Dec 07, 2025): Sync photo path to attendance table for WVV compliance
            if evidence_result and evidence_result.get('storage_path'):
                attendance.clock_in_photo_path = evidence_result['storage_path']
                attendance.clock_in_photo_uploaded_at = now
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to capture clock-in evidence: {e}")
    
    log_attendance_activity(
        db=db,
        attendance_id=attendance.id,
        employee_id=current_user.id,
        action='clock_in',
        details={
            "time": now.isoformat(),
            "location_mode": location_mode,
            "location": location_data,
            "evidence_captured": evidence_result is not None,
            "evidence_id": evidence_result.get('evidence_id') if evidence_result else None
        },
        ip_address=get_client_ip(request),
        device_info=device_info
    )
    
    # DC_FALLBACK_LOCATION_001 (Feb 2026): Insert initial StaffRealtimeLocation on clock-in
    # This ensures at least one location record exists even if mobile heartbeats fail
    if location_data and location_data.get('latitude') and location_data.get('longitude'):
        try:
            from app.models.staff_attendance import StaffRealtimeLocation
            dc_code = generate_realtime_dc_code(current_user.emp_code, now)
            
            # DC_ACCURACY_VALIDATION_001: Validate and cap accuracy to 500m max
            raw_accuracy = location_data.get('accuracy') or 50
            validated_accuracy = min(max(raw_accuracy, 1), 500)  # Clamp between 1 and 500
            
            # Check WVV compliance for quality tracking
            is_wvv_compliant = validated_accuracy <= 100
            
            initial_device_info = {
                **device_info,
                "source": "attendance",
                "is_wvv_compliant": is_wvv_compliant,
                "accuracy_quality": "high" if validated_accuracy <= 50 else ("medium" if validated_accuracy <= 100 else ("low" if validated_accuracy <= 300 else "degraded"))
            }
            
            initial_location = StaffRealtimeLocation(
                employee_id=current_user.id,
                latitude=location_data['latitude'],
                longitude=location_data['longitude'],
                accuracy_m=validated_accuracy,
                source='attendance',  # DC Protocol: valid sources are attendance, journey, drift, manual, heartbeat
                attendance_id=attendance.id,
                is_clocked_in=True,
                is_on_break=False,
                is_on_journey=False,
                dc_code=dc_code,
                device_info=initial_device_info,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "") if request else "",
                captured_at=now
            )
            db.add(initial_location)
            
            # Initialize GPS tracking fields on attendance
            attendance.last_gps_at = now
            attendance.gps_status = 'active'
            
            print(f"[DC_FALLBACK_LOCATION] Inserted initial StaffRealtimeLocation for {current_user.emp_code} on clock-in (acc={validated_accuracy}m, wvv={is_wvv_compliant})")
        except Exception as e:
            print(f"[DC_FALLBACK_LOCATION] Failed to insert initial location for {current_user.emp_code}: {e}")

    try:
        from app.models.staff_attendance_sheet import (
            StaffAttendanceSheet, AttendanceStatus, ApprovalStatus, ReconciliationStatus
        )
        existing_sheet = db.query(StaffAttendanceSheet).filter(
            StaffAttendanceSheet.employee_id == current_user.id,
            StaffAttendanceSheet.date == today
        ).first()
        if not existing_sheet:
            auto_sheet = StaffAttendanceSheet(
                employee_id=current_user.id,
                date=today,
                attendance_status=AttendanceStatus.PRESENT,
                marked_hours=8,
                reconciliation_status=ReconciliationStatus.MANUAL_OVERRIDE,
                approval_status=ApprovalStatus.PENDING,
                # [DC_DAR_003 / Task #53] Tag the clocking-in employee's company.
                company_id=getattr(current_user, 'base_company_id', None),
            )
            db.add(auto_sheet)
            logger.info(f"[DC_SHEET_AUTO] Auto-created attendance sheet entry for {current_user.emp_code} on clock-in")
    except Exception as e:
        logger.warning(f"[DC_SHEET_AUTO] Failed to auto-create sheet for {current_user.emp_code}: {e}")

    db.commit()
    db.refresh(attendance)
    
    response_data = {
        "success": True,
        "message": f"Clocked in at {now.strftime('%H:%M')}",
        "attendance": attendance.to_dict()
    }
    
    if evidence_result:
        response_data["evidence"] = {
            "id": evidence_result.get('evidence_id'),
            "captured_at": evidence_result.get('captured_at'),
            "gps": evidence_result.get('gps')
        }
    
    return response_data


@router.post("/clock-out", summary="Clock out for the day")
async def clock_out(
    clock_data: ClockOutRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Clock out for the day
    DC: Must be clocked in first
    WVV: Calculate worked hours
    """
    today = get_indian_date()
    now = get_indian_time()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance or not attendance.clock_in:
        raise HTTPException(status_code=400, detail="Not clocked in today")
    
    if attendance.clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out today")
    
    active_break = db.query(StaffAttendanceBreak).filter(
        StaffAttendanceBreak.attendance_id == attendance.id,
        StaffAttendanceBreak.break_end == None
    ).first()
    
    if active_break:
        active_break.break_end = now
        active_break.duration_minutes = active_break.calculate_duration()
    
    location_data = None
    if clock_data.location and clock_data.location.latitude and clock_data.location.longitude:
        location_data = {
            "latitude": clock_data.location.latitude,
            "longitude": clock_data.location.longitude,
            "accuracy": clock_data.location.accuracy,
            "address": clock_data.location.address,
            "captured_at": now.isoformat()
        }
    
    device_info = {
        "user_agent": request.headers.get("User-Agent", ""),
        "ip": get_client_ip(request)
    }
    
    attendance.clock_out = now
    attendance.clock_out_location = location_data
    attendance.clock_out_device = device_info
    if clock_data.notes:
        attendance.remarks = clock_data.notes
    
    attendance.worked_minutes = attendance.calculate_worked_time()
    
    total_break_mins = sum(b.duration_minutes or 0 for b in attendance.breaks)
    attendance.break_minutes = total_break_mins
    
    attendance.overtime_minutes = attendance.calculate_overtime()
    
    attendance.update_status()
    
    evidence_result = None
    if clock_data.evidence:
        try:
            gps_data = {
                'latitude': clock_data.evidence.gps_latitude,
                'longitude': clock_data.evidence.gps_longitude,
                'accuracy_m': clock_data.evidence.gps_accuracy_m,
                'altitude': clock_data.evidence.gps_altitude,
                'address': clock_data.evidence.location_address,
                'timestamp_overlay': clock_data.evidence.timestamp_overlay,
                'face_detected': clock_data.evidence.face_detected,
                'face_confidence': clock_data.evidence.face_confidence
            }
            
            evidence_result = await AttendanceEvidenceService.capture_evidence(
                photo_data=clock_data.evidence.photo_base64,
                event_type='clock_out',
                attendance_id=attendance.id,
                gps_data=gps_data,
                employee=current_user,
                db=db,
                device_info=device_info,
                remarks=clock_data.notes
            )
            logger.info(f"Clock-out evidence captured: {evidence_result.get('evidence_id')}")
            
            # DC_PHOTO_SYNC_001 (Dec 07, 2025): Sync photo path to attendance table for WVV compliance
            if evidence_result and evidence_result.get('storage_path'):
                attendance.clock_out_photo_path = evidence_result['storage_path']
                attendance.clock_out_photo_uploaded_at = now
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to capture clock-out evidence: {e}")
    
    log_attendance_activity(
        db=db,
        attendance_id=attendance.id,
        employee_id=current_user.id,
        action='clock_out',
        details={
            "time": now.isoformat(),
            "worked_minutes": attendance.worked_minutes,
            "overtime_minutes": attendance.overtime_minutes,
            "location": location_data,
            "evidence_captured": evidence_result is not None,
            "evidence_id": evidence_result.get('evidence_id') if evidence_result else None
        },
        ip_address=get_client_ip(request),
        device_info=device_info
    )
    
    db.commit()
    db.refresh(attendance)
    
    hours = attendance.worked_minutes // 60
    mins = attendance.worked_minutes % 60
    
    response_data = {
        "success": True,
        "message": f"Clocked out at {now.strftime('%H:%M')}. Worked {hours}h {mins}m today.",
        "attendance": attendance.to_dict()
    }
    
    if evidence_result:
        response_data["evidence"] = {
            "id": evidence_result.get('evidence_id'),
            "captured_at": evidence_result.get('captured_at'),
            "gps": evidence_result.get('gps')
        }
    
    return response_data


# ==================== BREAK MANAGEMENT ====================

@router.get("/break-types", summary="Get available break types")
async def get_break_types(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get list of available break types
    DC: Returns active break types for selection
    """
    break_types = db.query(StaffBreakType).filter(
        StaffBreakType.is_active == True
    ).order_by(StaffBreakType.display_order.asc()).all()
    
    return {
        "success": True,
        "break_types": [
            {
                "id": bt.id,
                "code": bt.break_code,
                "name": bt.name,
                "description": bt.description,
                "max_duration_minutes": bt.max_duration_minutes,
                "is_paid": bt.is_paid,
                "requires_evidence": bt.requires_evidence,
                "display_order": bt.display_order
            }
            for bt in break_types
        ]
    }


@router.post("/break/start", summary="Start a break")
async def start_break(
    break_data: BreakStartRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Start a break
    DC: Must be clocked in and not already on break
    """
    today = get_indian_date()
    now = get_indian_time()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance or not attendance.clock_in:
        raise HTTPException(status_code=400, detail="Not clocked in today")
    
    if attendance.clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out")
    
    active_break = db.query(StaffAttendanceBreak).filter(
        StaffAttendanceBreak.attendance_id == attendance.id,
        StaffAttendanceBreak.break_end == None
    ).first()
    
    if active_break:
        raise HTTPException(status_code=400, detail="Already on break. End current break first.")
    
    break_type = break_data.break_type
    break_type_id = break_data.break_type_id
    break_type_record = None
    
    if break_type_id:
        break_type_record = db.query(StaffBreakType).filter(
            StaffBreakType.id == break_type_id,
            StaffBreakType.is_active == True
        ).first()
        if not break_type_record:
            raise HTTPException(status_code=400, detail="Invalid break type ID")
    else:
        code_map = {
            'lunch': 'LUNCH', 'tea': 'TEA', 'personal': 'PERSONAL',
            'client_visit': 'CLIENT_VISIT', 'travel': 'TRAVEL', 'emergency': 'EMERGENCY'
        }
        break_code = code_map.get(break_type)
        if break_code:
            break_type_record = db.query(StaffBreakType).filter(
                StaffBreakType.break_code == break_code,
                StaffBreakType.is_active == True
            ).first()
    
    is_paid = break_type in ['lunch', 'tea']
    if break_type_record:
        is_paid = break_type_record.is_paid
    
    new_break = StaffAttendanceBreak(
        attendance_id=attendance.id,
        break_start=now,
        break_type=break_type,
        break_type_id=break_type_record.id if break_type_record else None,
        is_paid=is_paid
    )
    db.add(new_break)
    
    log_attendance_activity(
        db=db,
        attendance_id=attendance.id,
        employee_id=current_user.id,
        action='break_start',
        details={
            "break_type": break_type,
            "break_type_id": break_type_record.id if break_type_record else None,
            "time": now.isoformat()
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(new_break)
    
    return {
        "success": True,
        "message": f"Break started at {now.strftime('%H:%M')}",
        "break": new_break.to_dict()
    }


@router.post("/break/end", summary="End current break")
async def end_break(
    break_data: BreakEndRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    End current break
    DC: Must have an active break
    """
    today = get_indian_date()
    now = get_indian_time()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        raise HTTPException(status_code=400, detail="No attendance record for today")
    
    active_break = db.query(StaffAttendanceBreak).filter(
        StaffAttendanceBreak.attendance_id == attendance.id,
        StaffAttendanceBreak.break_end == None
    ).first()
    
    if not active_break:
        raise HTTPException(status_code=400, detail="No active break to end")
    
    active_break.break_end = now
    active_break.duration_minutes = active_break.calculate_duration()
    if break_data.notes:
        active_break.remarks = break_data.notes
    
    log_attendance_activity(
        db=db,
        attendance_id=attendance.id,
        employee_id=current_user.id,
        action='break_end',
        details={
            "break_type": active_break.break_type,
            "duration_minutes": active_break.duration_minutes,
            "time": now.isoformat()
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(active_break)
    
    return {
        "success": True,
        "message": f"Break ended. Duration: {active_break.duration_minutes} minutes",
        "break": active_break.to_dict()
    }


# ==================== ATTENDANCE HISTORY ====================

@router.get("/my-history", summary="Get my attendance history")
async def get_my_attendance_history(
    from_date: date = None,
    to_date: date = None,
    page: int = Query(1, ge=1),
    limit: int = Query(31, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current user's attendance history
    DC: Personal attendance records
    """
    query = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id
    )
    
    if from_date:
        query = query.filter(StaffAttendance.date >= from_date)
    
    if to_date:
        query = query.filter(StaffAttendance.date <= to_date)
    
    total = query.count()
    
    total_worked = db.query(func.sum(StaffAttendance.worked_minutes)).filter(
        StaffAttendance.employee_id == current_user.id
    ).scalar() or 0
    
    total_overtime = db.query(func.sum(StaffAttendance.overtime_minutes)).filter(
        StaffAttendance.employee_id == current_user.id
    ).scalar() or 0
    
    present_days = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.status == 'present'
    ).count()
    
    records = query.order_by(StaffAttendance.date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "records": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "summary": {
            "total_records": total,
            "present_days": present_days,
            "total_worked_hours": round(total_worked / 60, 2),
            "total_overtime_hours": round(total_overtime / 60, 2)
        }
    }


@router.get("/team", summary="Get team attendance")
async def get_team_attendance(
    date_filter: date = None,
    from_date: date = None,
    to_date: date = None,
    department_id: int = None,
    employee_id: int = None,
    status: str = None,
    mode: str = None,
    search: str = None,
    staff_type: str = None,
    away_from_office: bool = None,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get team/all attendance for a specific date
    DC Protocol (Dec 04, 2025): Enhanced with filters and correct response format
    DC_STAFF_TYPE_FILTER_001 (Dec 05, 2025): Added staff_type filter
    DC_OFFICE_PROXIMITY_001 (Jan 01, 2026): Added location data and away_from_office filter
    - Managers see recursive downline, HR/Supreme see all
    - Added: from_date, to_date, employee_id, mode, search filters
    - Added: staff_type filter (MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL)
    - Added: away_from_office filter (true = only show away, false = only show in-office)
    - Added: Location data with area names and map links
    - Fixed: Response format matches frontend expectations (members, not attendance)
    - Added: Status column with actual attendance status
    - Added: VGK/EA/HR can clock out employees (can_admin_clockout flag)
    """
    filter_date = date_filter or from_date or get_indian_date()
    
    accessible_ids = get_team_member_ids(current_user, db, StaffEmployee, department_id)
    
    if not accessible_ids:
        return {
            "success": True,
            "date": filter_date.isoformat(),
            "members": [],
            "total": 0,
            "page": page,
            "summary": {"total": 0, "present": 0, "absent": 0, "late": 0, "wfh": 0, "on_leave": 0},
            "can_admin_clockout": False
        }
    
    employee_query = db.query(StaffEmployee).filter(
        StaffEmployee.id.in_(accessible_ids),
        StaffEmployee.status == 'active'
    )
    
    # DC_STAFF_TYPE_FILTER_001: Filter by staff type
    if staff_type and staff_type.upper() in ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']:
        employee_query = employee_query.filter(StaffEmployee.staff_type == staff_type.upper())
    
    if employee_id:
        employee_query = employee_query.filter(StaffEmployee.id == employee_id)
    
    if search:
        search_term = f"%{search.lower()}%"
        employee_query = employee_query.filter(
            or_(
                func.lower(StaffEmployee.full_name).like(search_term),
                func.lower(StaffEmployee.emp_code).like(search_term)
            )
        )
    
    employees = employee_query.order_by(StaffEmployee.full_name).all()
    employee_ids = [e.id for e in employees]
    
    attendance_query = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id.in_(employee_ids),
        StaffAttendance.date == filter_date
    )
    
    if status and status != 'all':
        attendance_query = attendance_query.filter(StaffAttendance.status == status)
    
    if mode and mode != 'all':
        mode_map = {'office': 'office', 'wfh': 'wfh', 'field': 'field'}
        if mode in mode_map:
            attendance_query = attendance_query.filter(StaffAttendance.location_mode == mode_map[mode])
    
    records = attendance_query.all()
    records_by_emp = {r.employee_id: r for r in records}
    
    realtime_query = db.query(StaffRealtimeLocation).filter(
        StaffRealtimeLocation.employee_id.in_(employee_ids)
    ).all()
    realtime_by_emp = {r.employee_id: r for r in realtime_query}
    
    members_list = []
    present_count = 0
    absent_count = 0
    late_count = 0
    wfh_count = 0
    on_leave_count = 0
    
    for emp in employees:
        attendance = records_by_emp.get(emp.id)
        realtime = realtime_by_emp.get(emp.id)
        
        current_status = 'offline'
        if attendance:
            if attendance.clock_in and not attendance.clock_out:
                current_status = 'active'
                if any(b.break_start and not b.break_end for b in attendance.breaks):
                    current_status = 'on_break'
            elif attendance.clock_out:
                current_status = 'clocked_out'
        
        # DC_BATTERY_002: Extract battery_percentage from realtime location device_info
        battery_percentage = None
        if realtime and realtime.device_info:
            battery_percentage = realtime.device_info.get("battery_percentage")
        
        attendance_status = 'absent'
        work_mode = None
        clock_in = None
        clock_out = None
        hours_worked = 0
        break_minutes = 0
        is_late = False
        
        if attendance:
            attendance_status = attendance.status or 'present'
            work_mode = attendance.location_mode
            clock_in = attendance.clock_in.isoformat() if attendance.clock_in else None
            clock_out = attendance.clock_out.isoformat() if attendance.clock_out else None
            hours_worked = attendance.worked_minutes or 0
            break_minutes = attendance.break_minutes or 0
            
            if attendance.clock_in:
                clock_in_time = attendance.clock_in.time()
                standard_start = datetime.strptime("09:30", "%H:%M").time()
                if clock_in_time > standard_start and attendance.status == 'present':
                    is_late = True
            
            if attendance_status == 'present':
                present_count += 1
            elif attendance_status == 'on_leave':
                on_leave_count += 1
            elif attendance_status == 'absent':
                absent_count += 1
            
            if is_late:
                late_count += 1
            if work_mode == 'wfh':
                wfh_count += 1
        else:
            absent_count += 1
        
        designation = emp.designation or (emp.role.role_name if emp.role else 'Staff')
        department_name = emp.department.name if emp.department else None
        
        # DC_PHOTO_VIEW_001 (Dec 05, 2025): Add photo paths for WVV Protocol compliance
        # DC_PHOTO_FIX_001 (Dec 07, 2025): Fetch from evidence table if main record is null
        clock_in_photo_url = None
        clock_out_photo_url = None
        clock_in_photo_time = None
        clock_out_photo_time = None
        
        # DC_OFFICE_PROXIMITY_001: Extract location data and check office proximity
        clock_in_location = None
        clock_out_location = None
        clock_in_lat = None
        clock_in_lng = None
        clock_out_lat = None
        clock_out_lng = None
        clock_in_area_name = None
        clock_out_area_name = None
        is_away_clock_in = False
        is_away_clock_out = False
        clock_in_distance_from_office = None
        clock_out_distance_from_office = None
        
        if attendance:
            # First try main attendance table
            if attendance.clock_in_photo_path:
                clock_in_photo_url = f"/storage/{attendance.clock_in_photo_path}"
                clock_in_photo_time = attendance.clock_in_photo_uploaded_at.isoformat() if attendance.clock_in_photo_uploaded_at else None
            if attendance.clock_out_photo_path:
                clock_out_photo_url = f"/storage/{attendance.clock_out_photo_path}"
                clock_out_photo_time = attendance.clock_out_photo_uploaded_at.isoformat() if attendance.clock_out_photo_uploaded_at else None
            
            # DC_PHOTO_FIX_001: Fallback to evidence table if photos not in main record
            if not clock_in_photo_url or not clock_out_photo_url:
                for evidence in attendance.evidence_entries:
                    if evidence.event_type == 'clock_in' and not clock_in_photo_url and evidence.photo_path:
                        clock_in_photo_url = f"/storage/{evidence.photo_path}"
                        clock_in_photo_time = evidence.captured_at.isoformat() if evidence.captured_at else None
                    elif evidence.event_type == 'clock_out' and not clock_out_photo_url and evidence.photo_path:
                        clock_out_photo_url = f"/storage/{evidence.photo_path}"
                        clock_out_photo_time = evidence.captured_at.isoformat() if evidence.captured_at else None
            
            # DC_OFFICE_PROXIMITY_001: Extract and validate location data
            if attendance.clock_in_location:
                clock_in_location = attendance.clock_in_location
                clock_in_lat = clock_in_location.get('latitude')
                clock_in_lng = clock_in_location.get('longitude')
                if clock_in_lat and clock_in_lng:
                    is_near, nearest_office, distance = is_near_office(clock_in_lat, clock_in_lng)
                    is_away_clock_in = not is_near
                    clock_in_distance_from_office = distance
                    clock_in_area_name = get_area_name_from_coordinates(clock_in_lat, clock_in_lng)
            
            if attendance.clock_out_location:
                clock_out_location = attendance.clock_out_location
                clock_out_lat = clock_out_location.get('latitude')
                clock_out_lng = clock_out_location.get('longitude')
                if clock_out_lat and clock_out_lng:
                    is_near, nearest_office, distance = is_near_office(clock_out_lat, clock_out_lng)
                    is_away_clock_out = not is_near
                    clock_out_distance_from_office = distance
                    clock_out_area_name = get_area_name_from_coordinates(clock_out_lat, clock_out_lng)
        
        # DC_OFFICE_PROXIMITY_001: Apply away_from_office filter if specified
        is_away = is_away_clock_in or is_away_clock_out
        if away_from_office is not None:
            if away_from_office and not is_away:
                continue  # Skip if filtering for away but this is in-office
            if not away_from_office and is_away:
                continue  # Skip if filtering for in-office but this is away
        
        members_list.append({
            "id": emp.id,
            "employee_id": emp.id,
            "name": emp.full_name,
            "employee_code": emp.emp_code,
            "designation": designation,
            "department": department_name,
            "department_id": emp.department_id,
            "current_status": current_status,
            "battery_percentage": battery_percentage,
            "attendance_status": attendance_status,
            "status": attendance_status,
            "work_mode": work_mode,
            "location_mode": work_mode,
            "clock_in": clock_in,
            "clock_out": clock_out,
            "hours_worked": hours_worked,
            "worked_minutes": hours_worked,
            "break_minutes": break_minutes,
            "is_late": is_late,
            "is_clocked_in": attendance is not None and attendance.clock_in is not None and attendance.clock_out is None,
            "can_clockout": attendance is not None and attendance.clock_in is not None and attendance.clock_out is None,
            "attendance_id": attendance.id if attendance else None,
            # DC_PHOTO_VIEW_001: WVV Protocol photo verification fields
            "clock_in_photo_url": clock_in_photo_url,
            "clock_out_photo_url": clock_out_photo_url,
            "clock_in_photo_time": clock_in_photo_time,
            "clock_out_photo_time": clock_out_photo_time,
            "has_photos": bool(clock_in_photo_url or clock_out_photo_url),
            # DC_OFFICE_PROXIMITY_001: Location data and proximity fields
            "clock_in_lat": clock_in_lat,
            "clock_in_lng": clock_in_lng,
            "clock_out_lat": clock_out_lat,
            "clock_out_lng": clock_out_lng,
            "clock_in_area_name": clock_in_area_name,
            "clock_out_area_name": clock_out_area_name,
            "is_away_clock_in": is_away_clock_in,
            "is_away_clock_out": is_away_clock_out,
            "is_away": is_away_clock_in or is_away_clock_out,
            "clock_in_distance_from_office": clock_in_distance_from_office,
            "clock_out_distance_from_office": clock_out_distance_from_office
        })
    
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    can_admin_clockout = hierarchy_level >= 85
    
    paginated_members = members_list[(page - 1) * limit:page * limit]
    
    # DC_OFFICE_PROXIMITY_001: Count away from office
    away_from_office_count = len([m for m in members_list if m.get('is_away')])
    
    return {
        "success": True,
        "date": filter_date.isoformat(),
        "members": paginated_members,
        "total": len(members_list),
        "page": page,
        "summary": {
            "total": len(employees),
            "total_employees": len(employees),
            "present": present_count,
            "absent": absent_count,
            "late": late_count,
            "wfh": wfh_count,
            "on_leave": on_leave_count,
            "half_day": len([m for m in members_list if m.get('attendance_status') == 'half_day']),
            "away_from_office": away_from_office_count
        },
        "can_admin_clockout": can_admin_clockout
    }


# ==================== ADMIN CLOCK OUT (VGK/EA/HR ONLY) ====================

@router.post("/admin-clockout/{employee_id}", summary="Admin clock out employee (VGK/EA/HR only)")
async def admin_clockout_employee(
    employee_id: int,
    request: Request,
    remarks: str = Query(None, description="Remarks for admin clock out"),
    date: Optional[date] = Query(None, description="Target date for clock out (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Dec 04, 2025): Admin clock out for VGK, EA, HR roles
    - Allows high-level roles to clock out employees who forgot to clock out
    - Creates audit log entry with admin details
    - Requires hierarchy_level >= 85 (HR/EA/VGK)
    - Accepts optional date parameter to clock out for specific date (not just today)
    
    WVV Protocol: Write clock_out → Verify attendance exists → Validate permissions
    """
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    if hierarchy_level < 85:
        raise HTTPException(status_code=403, detail="Only VGK, EA, or HR can perform admin clock out")
    
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    target_date = date if date else get_indian_date()
    logger.info(f"[DC_ADMIN_CLOCKOUT] Attempting clockout for employee {employee_id} on date {target_date}")
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == employee_id,
        StaffAttendance.date == target_date
    ).first()
    
    if not attendance:
        raise HTTPException(status_code=404, detail=f"No attendance record found for {target_date.isoformat()}")
    
    if not attendance.clock_in:
        raise HTTPException(status_code=400, detail=f"Employee has not clocked in on {target_date.isoformat()}")
    
    if attendance.clock_out:
        raise HTTPException(status_code=400, detail=f"Employee is already clocked out on {target_date.isoformat()}")
    
    now = get_indian_time()
    
    for break_record in attendance.breaks:
        if break_record.break_start and not break_record.break_end:
            break_record.break_end = now
            if break_record.break_start:
                duration = int((now - break_record.break_start).total_seconds() / 60)
                break_record.duration_minutes = duration
    
    attendance.clock_out = now
    attendance.remarks = f"[Admin Clock Out by {current_user.emp_code}] {remarks or 'No remarks'}"
    
    worked = attendance.calculate_worked_time()
    attendance.worked_minutes = worked
    attendance.break_minutes = sum(b.duration_minutes or 0 for b in attendance.breaks)
    
    overtime = attendance.calculate_overtime()
    attendance.overtime_minutes = overtime
    
    attendance.is_auto_closed = False
    
    log_attendance_activity(
        db=db,
        attendance_id=attendance.id,
        employee_id=employee_id,
        action='admin_clock_out',
        details={
            'admin_id': current_user.id,
            'admin_code': current_user.emp_code,
            'admin_name': current_user.full_name,
            'target_date': target_date.isoformat(),
            'clock_out_time': now.isoformat(),
            'worked_minutes': worked,
            'remarks': remarks
        },
        ip_address=get_client_ip(request)
    )
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"[DC_ADMIN_CLOCKOUT] Database commit failed: {error_msg}")
        # DC Protocol: Include actual error for debugging while maintaining security
        if 'constraint' in error_msg.lower():
            raise HTTPException(status_code=500, detail=f"Failed to clock out: Constraint violation - {error_msg[:200]}")
        elif 'foreign key' in error_msg.lower():
            raise HTTPException(status_code=500, detail=f"Failed to clock out: Foreign key error - {error_msg[:200]}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to clock out: {error_msg[:200]}")
    
    logger.info(f"[DC_ADMIN_CLOCKOUT] Employee {employee.emp_code} clocked out by {current_user.emp_code} for date {target_date}")
    
    return {
        "success": True,
        "message": f"Successfully clocked out {employee.full_name} for {target_date.isoformat()}",
        "data": {
            "employee_id": employee_id,
            "employee_name": employee.full_name,
            "employee_code": employee.emp_code,
            "date": target_date.isoformat(),
            "clock_out": now.isoformat(),
            "worked_minutes": worked,
            "admin_by": current_user.emp_code
        }
    }


# ==================== ATTENDANCE ANALYTICS ====================

@router.get("/analytics/summary", summary="Get attendance analytics")
async def get_attendance_analytics(
    from_date: date = None,
    to_date: date = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get attendance analytics summary
    DC: Available to HR and above
    """
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    if hierarchy_level < 85:
        raise HTTPException(status_code=403, detail="Insufficient permissions for analytics")
    
    if not from_date:
        from_date = get_indian_date() - timedelta(days=30)
    if not to_date:
        to_date = get_indian_date()
    
    total_employees = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active'
    ).count()
    
    total_attendance = db.query(StaffAttendance).filter(
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    ).count()
    
    present_count = db.query(StaffAttendance).filter(
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date,
        StaffAttendance.status == 'present'
    ).count()
    
    avg_worked_hours = db.query(func.avg(StaffAttendance.worked_minutes)).filter(
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date,
        StaffAttendance.status == 'present'
    ).scalar() or 0
    
    total_overtime = db.query(func.sum(StaffAttendance.overtime_minutes)).filter(
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    ).scalar() or 0
    
    by_location = db.query(
        StaffAttendance.location_mode,
        func.count(StaffAttendance.id)
    ).filter(
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    ).group_by(StaffAttendance.location_mode).all()
    
    location_breakdown = {l[0]: l[1] for l in by_location}
    
    daily_avg = db.query(
        StaffAttendance.date,
        func.count(StaffAttendance.id).label('count'),
        func.avg(StaffAttendance.worked_minutes).label('avg_mins')
    ).filter(
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date,
        StaffAttendance.status == 'present'
    ).group_by(StaffAttendance.date).order_by(StaffAttendance.date).all()
    
    daily_trend = [
        {
            "date": d.date.isoformat(),
            "attendance_count": d.count,
            "avg_hours": round((d.avg_mins or 0) / 60, 2)
        }
        for d in daily_avg
    ]
    
    return {
        "success": True,
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        },
        "summary": {
            "total_employees": total_employees,
            "total_attendance_records": total_attendance,
            "present_days": present_count,
            "avg_worked_hours": round(avg_worked_hours / 60, 2) if avg_worked_hours else 0,
            "total_overtime_hours": round(total_overtime / 60, 2),
            "by_location": location_breakdown
        },
        "daily_trend": daily_trend
    }


@router.get("/analytics/by-employee", summary="Get attendance by employee")
async def get_attendance_by_employee(
    from_date: date = None,
    to_date: date = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get attendance summary per employee
    DC: HR and above can view
    """
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    if hierarchy_level < 85:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if not from_date:
        from_date = get_indian_date() - timedelta(days=30)
    if not to_date:
        to_date = get_indian_date()
    
    employees = db.query(StaffEmployee).filter(StaffEmployee.status == 'active').all()
    
    employee_stats = []
    
    for emp in employees:
        attendance = db.query(StaffAttendance).filter(
            StaffAttendance.employee_id == emp.id,
            StaffAttendance.date >= from_date,
            StaffAttendance.date <= to_date
        ).all()
        
        present_days = len([a for a in attendance if a.status == 'present'])
        half_days = len([a for a in attendance if a.status == 'half_day'])
        total_worked = sum(a.worked_minutes or 0 for a in attendance)
        total_overtime = sum(a.overtime_minutes or 0 for a in attendance)
        
        avg_clock_in = None
        clock_in_times = [a.clock_in for a in attendance if a.clock_in]
        if clock_in_times:
            avg_minutes = sum(t.hour * 60 + t.minute for t in clock_in_times) // len(clock_in_times)
            avg_clock_in = f"{avg_minutes // 60:02d}:{avg_minutes % 60:02d}"
        
        employee_stats.append({
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code,
            "department": emp.department.name if emp.department else None,
            "present_days": present_days,
            "half_days": half_days,
            "total_worked_hours": round(total_worked / 60, 2),
            "total_overtime_hours": round(total_overtime / 60, 2),
            "avg_clock_in": avg_clock_in,
            "attendance_rate": round((present_days + half_days * 0.5) / max(1, (to_date - from_date).days) * 100, 1)
        })
    
    employee_stats.sort(key=lambda x: x['attendance_rate'], reverse=True)
    
    return {
        "success": True,
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        },
        "employees": employee_stats
    }


# ==================== ATTENDANCE REPORTS (DC_REPORTS_001, Dec 1, 2025) ====================

def _get_period_dates(period: str, to_date: date = None) -> tuple:
    """
    DC_PERIOD_CALC_001: Calculate date range from period string
    All dates use IST timezone (Asia/Kolkata)
    """
    if to_date is None:
        to_date = get_indian_date()
    
    period_map = {
        'week': 7,
        'month': 30,
        'quarter': 90,
        'year': 365
    }
    
    days = period_map.get(period, 30)
    from_date = to_date - timedelta(days=days)
    
    return from_date, to_date


def _is_late_check(attendance, late_threshold_hour: int = 9, late_threshold_minute: int = 30) -> bool:
    """
    DC_LATE_CALC_001 (Dec 04, 2025): Compute late arrival dynamically from clock_in time
    
    DC Protocol: Late is defined as clock_in after 9:30:00 AM (configurable threshold)
    WVV Protocol: Computed at runtime, no database column required
    
    Args:
        attendance: StaffAttendance record
        late_threshold_hour: Hour threshold (default 9 = 9 AM)
        late_threshold_minute: Minute threshold (default 30 = 30 minutes)
    
    Returns:
        True if employee clocked in after threshold (inclusive of seconds), False otherwise
    
    Note: Uses full time() comparison for DC precision - 09:30:01 is late, 09:30:00 is on-time
    """
    if not attendance.clock_in:
        return False
    
    from datetime import time
    
    clock_in_time = attendance.clock_in.time()
    threshold_time = time(hour=late_threshold_hour, minute=late_threshold_minute, second=0)
    
    return clock_in_time > threshold_time


@router.get("/reports", summary="Get attendance reports with period and department filtering")
async def get_attendance_reports(
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    department: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_REPORTS_001: Comprehensive attendance reports with filtering
    
    Features:
    - Period filtering (week, month, quarter, year) with IST dates
    - Department filtering (all or specific department ID)
    - Role-based access control (HR/EA 85+)
    - Complete audit trail logging
    - WVV-compliant attendance verification
    
    Returns:
    {
        "summary": { avg_attendance, total_hours, late_arrivals, absent_days },
        "trend": [{ date, attendance_count, avg_hours }],
        "mode_distribution": { office, wfh, field },
        "employees": [{ emp_id, name, dept, attendance_rate, hours, ... }]
    }
    """
    # DC_RBAC_REPORTS_001: Role-based access control
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    if hierarchy_level < 85:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. HR/EA roles (85+) required for attendance reports"
        )
    
    # DC_PERIOD_CALC_001: Calculate IST-based date range
    from_date, to_date = _get_period_dates(period)
    
    # DC_AUDIT_REPORTS_001: Log report access for audit trail (system level)
    logger.info(
        f"DC_AUDIT_REPORTS_001: Report generated by emp_code={current_user.emp_code} "
        f"period={period} department={department} generated_at={get_indian_time().isoformat()}"
    )
    
    # DC_DEPT_FILTER_001: Filter employees by department
    employees_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
    
    if department != 'all':
        try:
            dept_id = int(department)
            employees_query = employees_query.filter(StaffEmployee.department_id == dept_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid department ID")
    
    employees = employees_query.all()
    
    if not employees:
        return {
            "success": True,
            "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "summary": {
                "avg_attendance": 0,
                "total_hours": 0,
                "avg_hours_day": 0,
                "late_arrivals": 0,
                "absent_days": 0
            },
            "trend": [],
            "mode_distribution": {"office": 0, "wfh": 0, "field": 0},
            "employees": []
        }
    
    # DC_REPORT_CALC_001: Calculate overall summary statistics
    all_attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id.in_([e.id for e in employees]),
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    ).all()
    
    present_count = len([a for a in all_attendance if a.status == 'present'])
    # DC_LATE_CALC_001 (Dec 04, 2025): Use _is_late_check helper instead of non-existent is_late attribute
    late_count = len([a for a in all_attendance if a.status == 'present' and _is_late_check(a)])
    absent_count = len([a for a in all_attendance if a.status == 'absent'])
    total_worked_mins = sum(a.worked_minutes or 0 for a in all_attendance)
    
    total_days = (to_date - from_date).days + 1
    max_expected = len(employees) * total_days
    avg_attendance_pct = round((present_count / max(1, max_expected)) * 100, 1)
    
    # DC_TREND_CALC_001: Calculate daily trend
    daily_data = db.query(
        StaffAttendance.date,
        func.count(StaffAttendance.id).label('count'),
        func.avg(StaffAttendance.worked_minutes).label('avg_mins')
    ).filter(
        StaffAttendance.employee_id.in_([e.id for e in employees]),
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date,
        StaffAttendance.status == 'present'
    ).group_by(StaffAttendance.date).order_by(StaffAttendance.date).all()
    
    trend = [
        {
            "date": d.date.isoformat(),
            "attendance_count": d.count,
            "avg_hours": round((d.avg_mins or 0) / 60, 2)
        }
        for d in daily_data
    ]
    
    # DC_MODE_DIST_001: Calculate location mode distribution
    mode_data = db.query(
        StaffAttendance.location_mode,
        func.count(StaffAttendance.id).label('count')
    ).filter(
        StaffAttendance.employee_id.in_([e.id for e in employees]),
        StaffAttendance.date >= from_date,
        StaffAttendance.date <= to_date
    ).group_by(StaffAttendance.location_mode).all()
    
    mode_distribution = {
        "office": next((m.count for m in mode_data if m.location_mode == 'office'), 0),
        "wfh": next((m.count for m in mode_data if m.location_mode == 'wfh'), 0),
        "field": next((m.count for m in mode_data if m.location_mode == 'field'), 0)
    }
    
    # DC_EMP_STATS_001: Calculate per-employee statistics
    employee_stats = []
    
    for emp in employees:
        emp_attendance = [a for a in all_attendance if a.employee_id == emp.id]
        
        present_days = len([a for a in emp_attendance if a.status == 'present'])
        half_days = len([a for a in emp_attendance if a.status == 'half_day'])
        # DC_LATE_CALC_001 (Dec 04, 2025): Use _is_late_check helper instead of non-existent is_late attribute
        late_arrivals = len([a for a in emp_attendance if a.status == 'present' and _is_late_check(a)])
        total_emp_mins = sum(a.worked_minutes or 0 for a in emp_attendance)
        
        avg_clock_in = None
        clock_in_times = [a.clock_in for a in emp_attendance if a.clock_in]
        if clock_in_times:
            avg_minutes = sum(t.hour * 60 + t.minute for t in clock_in_times) // len(clock_in_times)
            avg_clock_in = f"{avg_minutes // 60:02d}:{avg_minutes % 60:02d}"
        
        attendance_rate = round((present_days + half_days * 0.5) / max(1, total_days) * 100, 1)
        
        employee_stats.append({
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code,
            "department": emp.department.name if emp.department else None,
            "present_date": present_days,
            "half_days": half_days,
            "absent_days": len([a for a in emp_attendance if a.status == 'absent']),
            "late_arrivals": late_arrivals,
            "total_hours": round(total_emp_mins / 60, 2),
            "avg_hours_day": round(total_emp_mins / 60 / max(1, present_days), 2),
            "avg_clock_in": avg_clock_in,
            "attendance_rate": attendance_rate
        })
    
    employee_stats.sort(key=lambda x: x['attendance_rate'], reverse=True)
    
    return {
        "success": True,
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "period_type": period
        },
        "summary": {
            "avg_attendance": avg_attendance_pct,
            "total_hours": round(total_worked_mins / 60, 2),
            "avg_hours_day": round(total_worked_mins / 60 / max(1, total_days), 2),
            "late_arrivals": late_count,
            "absent_days": absent_count
        },
        "trend": trend,
        "mode_distribution": mode_distribution,
        "employees": employee_stats
    }


# ==================== DC_ATTENDANCE_TIMELINE_001: Dynamic Timeline with Date Selection ====================

@router.get("/timeline", summary="Get attendance timeline for specific date")
async def get_attendance_timeline(
    date: date = Query(None, description="Date in YYYY-MM-DD format. Default: today"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    request: Request = None
):
    """
    DC_ATTENDANCE_TIMELINE_001: Get attendance timeline for specific date (dynamic date selection)
    Default: Shows today's data on initial load
    
    Supports:
    - Dynamic date selection (any past date)
    - DC_DEVICE_BINDING_001: Tracks device_id with request
    - DC_AUDIT_TRAIL_001: Logs all date selection queries
    - WVV_TIMESTAMP_001: IST timezone for all timestamps
    """
    # DC_AUDIT_TRAIL_001: Log timeline request
    timeline_date = date or get_indian_date()
    client_ip = get_client_ip(request) if request else "unknown"
    
    logger.info(f'[DC_TIMELINE] Employee {current_user.id} ({current_user.emp_code}) requested timeline for {timeline_date} from {client_ip}')
    
    # Query attendance for selected date
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == timeline_date
    ).first()
    
    if not attendance:
        return {
            "success": True,
            "attendance": None,
            "date": timeline_date.isoformat(),
            "device_id": f"[DC_DEVICE_ID_{current_user.id}]",  # DC_DEVICE_BINDING_001
            "message": f"No attendance record for {timeline_date.isoformat()}"
        }
    
    # Get breaks for this day
    breaks_list = db.query(StaffAttendanceBreak).filter(
        StaffAttendanceBreak.attendance_id == attendance.id
    ).order_by(StaffAttendanceBreak.break_start).all()
    
    # DC_BATTERY_003: Extract battery percentages from device_info JSONB
    clock_in_battery = None
    clock_out_battery = None
    
    if attendance.clock_in_device and isinstance(attendance.clock_in_device, dict):
        clock_in_battery = attendance.clock_in_device.get('battery_percentage')
    
    if attendance.clock_out_device and isinstance(attendance.clock_out_device, dict):
        clock_out_battery = attendance.clock_out_device.get('battery_percentage')
    
    return {
        "success": True,
        "attendance": {
            "id": attendance.id,
            "date": attendance.date.isoformat(),
            "status": attendance.status,
            "location_mode": attendance.location_mode,
            "clock_in": attendance.clock_in.isoformat() if attendance.clock_in else None,
            "clock_out": attendance.clock_out.isoformat() if attendance.clock_out else None,
            "clock_in_battery": clock_in_battery,  # DC_BATTERY_003
            "clock_out_battery": clock_out_battery,  # DC_BATTERY_003
            "work_hours": round((attendance.worked_minutes or 0) / 60, 2),
            "break_minutes": attendance.break_minutes or 0,
            "clock_in_location": attendance.clock_in_location,
            "clock_out_location": attendance.clock_out_location,
            "breaks": [
                {
                    "id": b.id,
                    "break_type": b.break_type,
                    "break_start": b.break_start.isoformat() if b.break_start else None,
                    "break_end": b.break_end.isoformat() if b.break_end else None,
                    "duration_minutes": b.duration_minutes,
                    "start_battery": None,  # DC_BATTERY_003: Future enhancement - store break battery
                    "end_battery": None
                }
                for b in breaks_list
            ]
        },
        "date": timeline_date.isoformat(),
        "device_id": f"[DC_DEVICE_ID_{current_user.id}]",  # DC_DEVICE_BINDING_001: Track requesting device
        "timestamp": get_indian_time().isoformat(),
        "timezone": "Asia/Kolkata"
    }


# ==================== FRONTEND COMPATIBILITY ALIASES (DC Protocol Nov 26, 2025) ====================

@router.get("/history", summary="Attendance history - Frontend alias")
async def get_attendance_history_alias(
    months: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Frontend compatibility alias for /my-history
    Accepts 'months' parameter from frontend attendance reports page
    """
    to_date = get_indian_date()
    from_date = to_date - timedelta(days=months * 30)
    
    return await get_my_attendance_history(
        from_date=from_date,
        to_date=to_date,
        page=1,
        limit=months * 31,
        db=db,
        current_user=current_user
    )


@router.get("/location/summary", summary="Location summary - Dashboard statistics")
async def get_location_summary(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Get location tracking summary for dashboard
    Returns location statistics and drift events for current day
    """
    today = get_indian_date()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        return {
            "success": True,
            "locations_today": 0,
            "location_changes": 0,
            "distance_km": 0.0,
            "last_location": None,
            "last_update": None
        }
    
    today_drifts = db.query(StaffLocationDriftEvent).filter(
        StaffLocationDriftEvent.attendance_id == attendance.id
    ).all()
    
    return {
        "success": True,
        "locations_today": len(today_drifts) + 1 if attendance.clock_in_location else len(today_drifts),
        "location_changes": len(today_drifts),
        "distance_km": round(sum(float(d.distance_km or 0) for d in today_drifts), 2) if today_drifts else 0.0,
        "last_location": {
            "latitude": attendance.clock_out_location.get('latitude') if attendance.clock_out_location else attendance.clock_in_location.get('latitude'),
            "longitude": attendance.clock_out_location.get('longitude') if attendance.clock_out_location else attendance.clock_in_location.get('longitude'),
            "address": attendance.clock_out_location.get('address') if attendance.clock_out_location else attendance.clock_in_location.get('address')
        } if (attendance.clock_out_location or attendance.clock_in_location) else None,
        "last_update": attendance.updated_at.isoformat() if attendance.updated_at else None
    }


@router.get("/summary", summary="Attendance summary - Frontend alias")
async def get_attendance_summary_alias(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Frontend compatibility alias for /analytics/summary
    Provides current user's personal summary without analytics overhead
    """
    today = get_indian_date()
    thirty_days_ago = today - timedelta(days=30)
    
    total_days = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date >= thirty_days_ago,
        StaffAttendance.date <= today
    ).count()
    
    present_days = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date >= thirty_days_ago,
        StaffAttendance.date <= today,
        StaffAttendance.status == 'present'
    ).count()
    
    total_worked = db.query(func.sum(StaffAttendance.worked_minutes)).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date >= thirty_days_ago,
        StaffAttendance.date <= today
    ).scalar() or 0
    
    total_overtime = db.query(func.sum(StaffAttendance.overtime_minutes)).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date >= thirty_days_ago,
        StaffAttendance.date <= today
    ).scalar() or 0
    
    avg_worked = db.query(func.avg(StaffAttendance.worked_minutes)).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date >= thirty_days_ago,
        StaffAttendance.date <= today,
        StaffAttendance.status == 'present'
    ).scalar() or 0
    
    return {
        "success": True,
        "employee_id": current_user.id,
        "employee_name": current_user.full_name,
        "employee_code": current_user.emp_code,
        "period": {
            "from": thirty_days_ago.isoformat(),
            "to": today.isoformat()
        },
        "summary": {
            "total_days": total_days,
            "present_days": present_days,
            "total_worked_hours": round(total_worked / 60, 2),
            "total_overtime_hours": round(total_overtime / 60, 2),
            "avg_worked_hours": round(avg_worked / 60, 2) if avg_worked else 0,
            "attendance_rate": round((present_days / max(1, 30)) * 100, 1)
        }
    }


# ==================== LOCATION DRIFT TRACKING ====================

@router.post("/location/drift", summary="Record location drift event")
async def record_location_drift(
    drift_data: LocationDriftRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Record a location drift event when user moves ≥200m from last known location
    
    WVV Protocol: GPS validation (accuracy ≤100m, staleness ≤5min)
    DC Protocol: Immutable records with DC code (LD-YYYYMMDD-EMP-SEQ)
    """
    today = get_indian_date()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        raise HTTPException(status_code=400, detail="No attendance record found. Clock in first.")
    
    if not attendance.clock_in:
        raise HTTPException(status_code=400, detail="Not clocked in. Clock in first.")
    
    if attendance.clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out. Cannot record location drift.")
    
    current_location = {
        "latitude": drift_data.latitude,
        "longitude": drift_data.longitude,
        "accuracy_m": drift_data.accuracy_m,
        "address": drift_data.address
    }
    
    result = await LocationDriftService.record_drift(
        db=db,
        attendance_id=attendance.id,
        employee=current_user,
        current_location=current_location,
        accuracy_m=drift_data.accuracy_m,
        capture_method=drift_data.capture_method,
        device_info=drift_data.device_info,
        ip_address=get_client_ip(request)
    )
    
    return {
        "success": True,
        **result
    }


@router.get("/location/today/drifts", summary="Get today's location drift events")
async def get_today_location_drifts(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get today's location drift events for current user
    DC Protocol: Returns drift sequence with timestamps
    """
    result = LocationDriftService.get_today_drifts(db, current_user.id)
    
    return {
        "success": True,
        **result
    }


@router.get("/location/history", summary="Get location drift history by date")
async def get_location_drift_history(
    date_str: Optional[str] = Query(None, alias="date", description="Date in YYYY-MM-DD format"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date for range query"),
    to_date: Optional[str] = Query(None, alias="to", description="End date for range query"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get location drift history for a specific date or date range
    
    DC Protocol: Historical drift data with date filters
    
    Options:
    - ?date=YYYY-MM-DD - Get single date's drifts
    - ?from=YYYY-MM-DD&to=YYYY-MM-DD - Get date range summary
    """
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        result = LocationDriftService.get_drifts_by_date(db, current_user.id, target_date)
        return {
            "success": True,
            **result
        }
    
    elif from_date and to_date:
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if (end_date - start_date).days > 31:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 31 days")
        
        results = LocationDriftService.get_drifts_by_date_range(db, current_user.id, start_date, end_date)
        
        total_distance = sum(r.get('total_distance_km', 0) for r in results)
        total_changes = sum(r.get('location_change_count', 0) for r in results)
        
        return {
            "success": True,
            "from_date": from_date,
            "to_date": to_date,
            "days_count": len(results),
            "summary": {
                "total_location_changes": total_changes,
                "total_distance_km": round(total_distance, 2)
            },
            "daily_data": results
        }
    
    else:
        today = get_indian_date()
        result = LocationDriftService.get_drifts_by_date(db, current_user.id, today)
        return {
            "success": True,
            **result
        }


@router.get("/location/last-known", summary="Get last known location")
async def get_last_known_location(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get the last known location for current user's today attendance
    Used for drift calculation on frontend
    """
    today = get_indian_date()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        return {
            "success": False,
            "has_location": False,
            "message": "No attendance record for today"
        }
    
    last_location = LocationDriftService.get_last_known_location(db, attendance.id)
    
    if not last_location:
        return {
            "success": True,
            "has_location": False,
            "message": "No location data available"
        }
    
    return {
        "success": True,
        "has_location": True,
        "location": last_location,
        "attendance_id": attendance.id,
        "location_change_count": attendance.location_change_count or 0,
        "unique_locations_count": attendance.unique_locations_count or 0,
        "total_distance_km": round(float(attendance.total_distance_meters or 0) / 1000, 2)
    }


# ==================== REAL-TIME LOCATION TRACKING ====================

@router.post("/location/update", summary="Update real-time location")
async def update_realtime_location(
    request: Request,
    data: Optional[LocationUpdateRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update current user's real-time location
    
    DC_GPS_BODY_FIX_001 (Feb 03, 2026): Accept JSON body instead of Query params
    - Fixes Android native background service which sends JSON body
    - Backward compatible: Accepts both 'accuracy' and 'accuracy_m' field names
    - Accepts both 'speed' and 'speed_kmh', 'battery_level' and 'battery_percentage'
    
    DC_GPS_QPARAM_BACKCOMPAT_001 (Feb 26, 2026): Accept query params as fallback
    - Old app versions (pre-Feb 2026) send lat/lng as query params
    - If body is absent/empty, construct LocationUpdateRequest from query params
    - Prevents 422 errors for users on older app versions until they update
    
    DC_GPS_DUAL_TIER_001 (Dec 05, 2025): Dual-tier GPS accuracy system
    - Location Tracking: Accept up to 500m accuracy (for indoor/degraded GPS)
    - Journey Reimbursement: Strict 100m WVV limit (separate validation)
    
    WVV Protocol: is_wvv_compliant flag tracks if point meets 100m accuracy
    DC Protocol: Creates audit trail with semantic DC code
    DC_BATTERY_001: Battery percentage stored in device_info for tracking
    """
    # DC_GPS_QPARAM_BACKCOMPAT_001: Fall back to query params if body is absent
    if data is None:
        qp = request.query_params
        lat_str = qp.get('latitude') or qp.get('lat')
        lng_str = qp.get('longitude') or qp.get('lng')
        if not lat_str or not lng_str:
            raise HTTPException(status_code=422, detail="GPS Error: latitude and longitude are required (body or query params)")
        try:
            acc_str = qp.get('accuracy_m') or qp.get('accuracy')
            data = LocationUpdateRequest(
                latitude=float(lat_str),
                longitude=float(lng_str),
                accuracy_m=float(acc_str) if acc_str else None,
                accuracy=float(acc_str) if acc_str else None,
                altitude=float(qp['altitude']) if qp.get('altitude') else None,
                speed=float(qp['speed']) if qp.get('speed') else None,
                heading=float(qp['heading']) if qp.get('heading') else None,
                battery_level=float(qp['battery_level']) if qp.get('battery_level') else None,
                source=qp.get('source', 'heartbeat'),
            )
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=422, detail=f"GPS Error: invalid param value — {e}")

    # DC_GPS_BODY_FIX_001: Extract and normalize field names from body
    latitude = data.latitude
    longitude = data.longitude
    # Accept both 'accuracy' (Android) and 'accuracy_m' (backend) - prefer accuracy_m if both provided
    accuracy_m = data.accuracy_m if data.accuracy_m is not None else (data.accuracy if data.accuracy is not None else None)
    if accuracy_m is None:
        raise HTTPException(status_code=400, detail="GPS Error: accuracy or accuracy_m is required")
    altitude = data.altitude
    # Accept both 'speed' (Android) and 'speed_kmh' (backend)
    speed_kmh = data.speed_kmh if data.speed_kmh is not None else data.speed
    heading = data.heading
    # Accept both 'battery_level' (Android) and 'battery_percentage' (backend)
    battery_percentage = data.battery_percentage if data.battery_percentage is not None else (int(data.battery_level) if data.battery_level is not None else None)
    source = data.source
    
    now = get_indian_time()
    today = get_indian_date()
    
    # DC_GPS_DUAL_TIER_001: Dual-tier validation
    # - Reject only completely invalid data (<=0 or >500m)
    # - Track WVV compliance (<=100m) as a flag for journey reimbursement
    if accuracy_m <= 0:
        raise HTTPException(
            status_code=400,
            detail="GPS Error: Invalid accuracy value (must be > 0)"
        )
    
    if accuracy_m > 500:
        raise HTTPException(
            status_code=400,
            detail=f"GPS Rejected: Accuracy {accuracy_m:.0f}m exceeds maximum 500m limit. Please move to better GPS signal."
        )
    
    # WVV Compliance: Track if point meets strict 100m accuracy for journey reimbursement
    is_wvv_compliant = accuracy_m <= 100
    
    # Get today's attendance
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    # Check if on break
    active_break = None
    if attendance:
        active_break = db.query(StaffAttendanceBreak).filter(
            StaffAttendanceBreak.attendance_id == attendance.id,
            StaffAttendanceBreak.break_end == None
        ).first()
    
    # Check if on journey
    from app.models.staff_journey import StaffJourney, JourneyStatus
    active_journey = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        StaffJourney.status == JourneyStatus.IN_PROGRESS
    ).first()
    
    # Generate DC code
    dc_code = generate_realtime_dc_code(current_user.emp_code, now)
    
    # DC_BATTERY_001 + DC_GPS_DUAL_TIER_001: Build device_info with battery and WVV compliance
    device_info_data = {
        "user_agent": request.headers.get("User-Agent", ""),
        "is_wvv_compliant": is_wvv_compliant,
        "accuracy_quality": "high" if accuracy_m <= 50 else ("medium" if accuracy_m <= 100 else ("low" if accuracy_m <= 300 else "degraded"))
    }
    if battery_percentage is not None:
        device_info_data["battery_percentage"] = battery_percentage
    
    # Log if degraded GPS for monitoring
    if not is_wvv_compliant:
        print(f"[DC_GPS_DUAL_TIER] Degraded GPS accepted: {current_user.emp_code}, accuracy={accuracy_m:.0f}m, quality={device_info_data['accuracy_quality']}")
    
    # DC_ALTITUDE_FIX_001: Clamp negative altitude values to 0
    # Mobile GPS devices may report slightly negative altitude (below sea level)
    # which can violate database CHECK constraints in production
    validated_altitude = altitude
    if altitude is not None and altitude < 0:
        validated_altitude = 0.0
        print(f"[DC_ALTITUDE_FIX] Clamped negative altitude {altitude:.2f}m to 0 for {current_user.emp_code}")
    
    # DC_APP_VERSION_001 (Jan 28, 2026): Capture app version from headers
    app_version = request.headers.get("X-App-Version", None)
    app_platform = request.headers.get("X-App-Platform", None)
    
    # Create location record
    location = StaffRealtimeLocation(
        employee_id=current_user.id,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        altitude=validated_altitude,
        speed_kmh=speed_kmh,
        heading=heading,
        source=source,
        attendance_id=attendance.id if attendance else None,
        journey_id=active_journey.id if active_journey else None,
        is_clocked_in=attendance is not None and attendance.clock_out is None,
        is_on_break=active_break is not None,
        is_on_journey=active_journey is not None,
        break_type=active_break.break_type.upper() if active_break and active_break.break_type else None,
        dc_code=dc_code,
        device_info=device_info_data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", ""),
        app_version=app_version,
        app_platform=app_platform,
        captured_at=now
    )
    
    # DC_GPS_DEDUP_001 (Feb 2026): Skip insert if dc_code already exists
    # Race condition: native_background + mobile_heartbeat can fire within the same second
    # generating identical dc_codes. Pre-check avoids UniqueViolation at commit.
    _existing_loc = db.query(StaffRealtimeLocation.id).filter(
        StaffRealtimeLocation.dc_code == dc_code
    ).first()
    _loc_queued = False
    if not _existing_loc:
        db.add(location)
        _loc_queued = True
        print(f"[DC_GPS_HEARTBEAT] Inserting StaffRealtimeLocation for {current_user.emp_code}: lat={latitude}, lng={longitude}, acc={accuracy_m}m, battery={battery_percentage}, source={source}")
    else:
        print(f"[DC_GPS_DEDUP] Skipping duplicate dc_code {dc_code} for {current_user.emp_code} (source={source})")
    
    # DC Protocol (Jan 28, 2026): Update attendance GPS tracking fields
    if attendance:
        attendance.last_gps_at = now
        attendance.gps_status = 'active'
        attendance.gps_status_reason = None
        attendance.gps_status_at = now
        if battery_percentage is not None:
            attendance.last_battery_pct = battery_percentage
        
        # DC_WORKED_MINUTES_REALTIME_001 (Feb 2026): Calculate worked_minutes on every heartbeat
        # This ensures real-time updates instead of only at clock-out
        # DC_BREAK_SYNC_001: Sync break_minutes from StaffAttendanceBreak records before calculation
        if attendance.clock_in and not attendance.clock_out:
            # First sync break_minutes from actual break records
            total_break_mins = db.query(func.coalesce(func.sum(StaffAttendanceBreak.duration_minutes), 0)).filter(
                StaffAttendanceBreak.attendance_id == attendance.id
            ).scalar() or 0
            attendance.break_minutes = int(total_break_mins)
            
            # Calculate elapsed time minus breaks
            elapsed_seconds = (now - attendance.clock_in).total_seconds()
            attendance.worked_minutes = max(0, int(elapsed_seconds / 60) - attendance.break_minutes)
            print(f"[DC_WORKED_MINUTES] Updated worked_minutes={attendance.worked_minutes}, break_minutes={attendance.break_minutes} for {current_user.emp_code}")
    
    # DC_GPS_DEDUP_002 (Apr 2026): Secondary safety net — catches the rare race condition
    # where two requests pass the pre-check simultaneously and both try to insert the same
    # dc_code. On IntegrityError: rollback, expunge location, re-apply attendance fields only.
    try:
        db.commit()
    except IntegrityError as _gps_ie:
        db.rollback()
        if _loc_queued:
            print(f"[DC_GPS_DEDUP_002] Race-condition duplicate dc_code {dc_code} for {current_user.emp_code} — location skipped, retrying attendance-only commit")
            if attendance and getattr(attendance, 'id', None):
                _att_retry = db.query(StaffAttendance).filter(StaffAttendance.id == attendance.id).first()
                if _att_retry:
                    _att_retry.last_gps_at = now
                    _att_retry.gps_status = 'active'
                    _att_retry.gps_status_reason = None
                    _att_retry.gps_status_at = now
                    if battery_percentage is not None:
                        _att_retry.last_battery_pct = battery_percentage
                    db.commit()
        else:
            raise

    # DC_SESSION_EXTEND_001: Generate extended session token while clocked in
    # This prevents session expiry while the user is actively tracked
    extended_token = None
    if attendance and attendance.clock_out is None:
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                current_token = auth_header.split(" ")[1]
                payload = SecurityManager.verify_token(current_token)
                if payload:
                    extended_token = SecurityManager.create_extended_session_token(payload, extend_minutes=30)
        except Exception as e:
            print(f"[DC_SESSION_EXTEND_001] Token refresh warning: {e}")
    
    # DC_GPS_DUAL_TIER_001: Include compliance status in response
    return {
        "success": True,
        "message": "Location updated" + (" (WVV compliant)" if is_wvv_compliant else " (degraded GPS)"),
        "dc_code": dc_code,
        "captured_at": now.isoformat(),
        "is_wvv_compliant": is_wvv_compliant,
        "accuracy_quality": device_info_data["accuracy_quality"],
        "battery_percentage": battery_percentage,
        "extended_token": extended_token  # DC_SESSION_EXTEND_001: Refreshed token for session continuity
    }


@router.post("/location/gps-status", summary="Report GPS status change")
async def update_gps_status(
    request: Request,
    status: str = Query("active", description="GPS status: active, permission_denied, gps_disabled, network_error, app_background, location_timeout"),
    reason: Optional[str] = Query(None, description="Human-readable reason"),
    battery_percentage: Optional[int] = Query(None, ge=0, le=100, description="Current battery percentage"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Jan 28, 2026): Report GPS status change for Team Live Tracker
    
    Called by mobile when GPS tracking fails or changes state:
    - permission_denied: User denied location permission
    - gps_disabled: Device GPS is turned off
    - network_error: Network unavailable for location services
    - app_background: App moved to background (Android)
    - location_timeout: GPS acquisition timed out
    - active: GPS resumed working
    """
    valid_statuses = ['active', 'permission_denied', 'gps_disabled', 'network_error', 'app_background', 'location_timeout']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid GPS status. Must be one of: {valid_statuses}")
    
    now = get_indian_time()
    today = get_indian_date()
    
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()
    
    if not attendance:
        return {"success": False, "message": "No attendance record for today"}
    
    # Update GPS status
    attendance.gps_status = status
    attendance.gps_status_reason = reason
    attendance.gps_status_at = now
    if battery_percentage is not None:
        attendance.last_battery_pct = battery_percentage
    
    db.commit()
    
    print(f"[DC_GPS_STATUS] {current_user.emp_code} status={status} reason={reason} battery={battery_percentage}%")
    
    return {
        "success": True,
        "message": f"GPS status updated to {status}",
        "gps_status": status,
        "gps_status_at": now.isoformat()
    }


@router.get("/check-active-session", summary="Check if staff has active tracking session")
async def check_active_session(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_RESUME_007: Check for active tracking session (Jan 13, 2026)
    
    Returns session state for resume prompt:
    - has_active_session: True if clocked in without clock out
    - active_journey: Journey details if one is in progress
    - gap_duration_minutes: Time since last location update
    - last_location_time: When last GPS point was captured
    """
    now = get_indian_time()
    today = get_indian_date()
    
    # Check for active attendance (clocked in, not clocked out)
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today,
        StaffAttendance.clock_out == None
    ).first()
    
    if not attendance:
        return {
            "success": True,
            "has_active_session": False,
            "message": "No active attendance session"
        }
    
    # Check for active journey
    from app.models.staff_journey import StaffJourney, JourneyStatus
    active_journey = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        StaffJourney.status == JourneyStatus.IN_PROGRESS
    ).first()
    
    # Get last location update
    last_location = db.query(StaffRealtimeLocation).filter(
        StaffRealtimeLocation.employee_id == current_user.id,
        StaffRealtimeLocation.attendance_id == attendance.id
    ).order_by(StaffRealtimeLocation.captured_at.desc()).first()
    
    gap_duration_minutes = 0
    last_location_time = None
    
    if last_location:
        last_location_time = last_location.captured_at
        # DC: Handle timezone-aware/naive datetime comparison
        # Convert to IST before stripping tzinfo for accurate gap calculation
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        captured_at = last_location.captured_at
        if captured_at.tzinfo is not None:
            captured_at = captured_at.astimezone(ist).replace(tzinfo=None)
        gap_duration_minutes = (now.replace(tzinfo=None) - captured_at).total_seconds() / 60
    
    return {
        "success": True,
        "has_active_session": True,
        "attendance_id": attendance.id,
        "clock_in_time": attendance.clock_in.isoformat() if attendance.clock_in else None,
        "active_journey": {
            "id": active_journey.id,
            "purpose": active_journey.purpose,
            "start_time": active_journey.actual_start_time.isoformat() if active_journey.actual_start_time else None,
            "transport_mode": active_journey.transport_mode
        } if active_journey else None,
        "gap_duration_minutes": round(gap_duration_minutes, 1),
        "last_location_time": last_location_time.isoformat() if last_location_time else None
    }


@router.post("/tracking-gap", summary="Report GPS tracking gap")
async def report_tracking_gap(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    DC_VISIBILITY_004: Report GPS tracking gap (Jan 13, 2026)
    
    Called via sendBeacon when:
    - Browser tab is hidden/minimized
    - Browser is closing
    - Page is unloading
    
    This helps detect gaps in GPS tracking for audit purposes.
    Uses sendBeacon so no auth header available - uses token from body if needed.
    """
    try:
        body = await request.json()
    except:
        return {"success": False, "message": "Invalid request body"}
    
    reason = body.get("reason", "unknown")
    timestamp = body.get("timestamp", get_indian_time().isoformat())
    last_location = body.get("last_known_location")
    gap_duration = body.get("gap_duration_seconds")
    
    # DC: Try to identify user from token in body (sendBeacon) or header
    token = body.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    employee_id = None
    emp_code = "UNKNOWN"
    
    if token:
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(token)
            if payload:
                employee_id = payload.get("sub") or payload.get("employee_id")
                emp_code = payload.get("emp_code", "UNKNOWN")
        except:
            pass
    
    if not employee_id:
        print(f"[DC_TRACKING_GAP] Unauthenticated gap report: {reason}")
        return {"success": False, "message": "Authentication required"}
    
    # Log the tracking gap for audit
    log_msg = f"[DC_TRACKING_GAP] reason={reason}, emp={emp_code}"
    if gap_duration:
        log_msg += f", duration={gap_duration}s"
    if last_location:
        log_msg += f", last_loc=({last_location.get('latitude', 'N/A')}, {last_location.get('longitude', 'N/A')})"
    
    print(log_msg)
    
    # Store in database if we have employee context
    if employee_id:
        try:
            now = get_indian_time()
            today = get_indian_date()
            
            attendance = db.query(StaffAttendance).filter(
                StaffAttendance.employee_id == employee_id,
                StaffAttendance.date == today
            ).first()
            
            if attendance:
                # Store gap in device_info of a special location record
                gap_record = StaffRealtimeLocation(
                    employee_id=employee_id,
                    latitude=last_location.get('latitude', 0) if last_location else 0,
                    longitude=last_location.get('longitude', 0) if last_location else 0,
                    accuracy_m=last_location.get('accuracy_m', 9999) if last_location else 9999,
                    source=f"gap_{reason}",
                    attendance_id=attendance.id,
                    is_clocked_in=True,
                    dc_code=f"GAP_{reason.upper()}_{now.strftime('%H%M%S')}",
                    device_info={
                        "gap_reason": reason,
                        "gap_duration_seconds": gap_duration,
                        "is_tracking_gap": True
                    },
                    ip_address=get_client_ip(request),
                    user_agent=request.headers.get("User-Agent", ""),
                    captured_at=now
                )
                db.add(gap_record)
                db.commit()
        except Exception as e:
            print(f"[DC_TRACKING_GAP] Failed to store gap record: {e}")
    
    return {"success": True, "message": "Tracking gap recorded"}


@router.get("/gps-gaps/{attendance_id}", summary="Get GPS gaps for attendance record")
async def get_gps_gaps(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_OFFLINE_PERIOD_001: Get GPS tracking gaps for an attendance record
    
    Returns all tracking gaps (periods when GPS was offline) for a specific
    attendance record, formatted for display in mobile app popup and
    attendance history.
    """
    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.id == attendance_id
    ).first()
    
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Check authorization - user can view their own or managers can view team
    if attendance.employee_id != current_user.id:
        hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
        if hierarchy_level < 60:
            raise HTTPException(status_code=403, detail="Not authorized to view this record")
    
    # Get gap records from location history
    gaps = db.query(StaffRealtimeLocation).filter(
        StaffRealtimeLocation.attendance_id == attendance_id,
        StaffRealtimeLocation.source.like('gap_%')
    ).order_by(StaffRealtimeLocation.captured_at).all()
    
    gap_list = []
    for gap in gaps:
        device_info = gap.device_info or {}
        gap_list.append({
            "id": gap.id,
            "timestamp": gap.captured_at.isoformat() if gap.captured_at else None,
            "reason": device_info.get("gap_reason", "unknown"),
            "description": device_info.get("description", ""),
            "duration_seconds": device_info.get("gap_duration_seconds"),
            "source": device_info.get("source", "web"),
            "latitude": float(gap.latitude) if gap.latitude else None,
            "longitude": float(gap.longitude) if gap.longitude else None
        })
    
    return {
        "success": True,
        "attendance_id": attendance_id,
        "gaps": gap_list,
        "total_gaps": len(gap_list),
        "total_gps_off_minutes": attendance.total_gps_off_minutes or 0
    }


@router.get("/location/my/history", summary="Get my location history")
async def get_my_location_history(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    from_date: Optional[str] = Query(None, description="Start date for range"),
    to_date: Optional[str] = Query(None, description="End date for range"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current user's location history
    
    DC Protocol: Staff can view their own location history
    """
    query = db.query(StaffRealtimeLocation).filter(
        StaffRealtimeLocation.employee_id == current_user.id
    )
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(func.date(StaffRealtimeLocation.captured_at) == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    elif from_date and to_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d")
            end = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(
                StaffRealtimeLocation.captured_at >= start,
                StaffRealtimeLocation.captured_at <= end
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    total = query.count()
    locations = query.order_by(StaffRealtimeLocation.captured_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "locations": [loc.to_dict() for loc in locations],
        "has_more": (offset + limit) < total
    }


@router.get("/location/team/live", summary="Get team live locations (Manager)")
async def get_team_live_locations(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format for viewing previous days"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get live locations of direct reports (for Managers/Leads)
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users with direct reports see their team's live locations
    - VGK/HR see all staff
    
    DC Protocol (Jan 28, 2026): Added date parameter for viewing previous days
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        (current_user.role.hierarchy_level or 0) >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(
            status_code=403,
            detail="Only those with direct reports or HR/VGK4U can view team live locations"
        )
    
    now = get_indian_time()
    # DC Protocol (Jan 28, 2026): Support date parameter for historical view
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = get_indian_date()
    
    today = get_indian_date()
    is_historical = target_date != today
    
    # DC Protocol (Dec 04, 2025): Get team members based on role with recursive downline
    accessible_ids = get_team_member_ids(current_user, db, StaffEmployee)
    logger.info(f"[DC_LIVE_TRACKER_DEBUG] User {current_user.emp_code} (id={current_user.id}), accessible_ids count: {len(accessible_ids)}, is_manager: {is_manager}, is_vgk4u_or_hr: {is_vgk4u_or_hr}")
    
    team_members = db.query(StaffEmployee).filter(
        StaffEmployee.id.in_(accessible_ids),
        StaffEmployee.status == 'active'
    ).all()
    
    logger.info(f"[DC_LIVE_TRACKER_DEBUG] Team members found: {len(team_members)}")
    
    if not team_members:
        return {
            "success": True,
            "message": "No team members found",
            "locations": [],
            "summary": {"total": 0, "active": 0, "on_break": 0, "on_journey": 0, "offline": 0}
        }
    
    team_ids = [m.id for m in team_members]
    
    # DC Protocol (Jan 28, 2026): For historical view, get last location of that date
    # For live view, use 30-minute cutoff
    if is_historical:
        # Get last location for target date only
        target_date_start = datetime.combine(target_date, datetime.min.time())
        target_date_end = datetime.combine(target_date, datetime.max.time())
        
        latest_subq = db.query(
            StaffRealtimeLocation.employee_id,
            func.max(StaffRealtimeLocation.captured_at).label('max_captured')
        ).filter(
            StaffRealtimeLocation.employee_id.in_(team_ids),
            StaffRealtimeLocation.captured_at >= target_date_start,
            StaffRealtimeLocation.captured_at <= target_date_end
        ).group_by(StaffRealtimeLocation.employee_id).subquery()
    else:
        # DC_REALTIME_TOLERANCE_001: Extended cutoff to 30 minutes for network latency
        cutoff_time = now - timedelta(minutes=30)
        
        latest_subq = db.query(
            StaffRealtimeLocation.employee_id,
            func.max(StaffRealtimeLocation.captured_at).label('max_captured')
        ).filter(
            StaffRealtimeLocation.employee_id.in_(team_ids),
            StaffRealtimeLocation.captured_at >= cutoff_time
        ).group_by(StaffRealtimeLocation.employee_id).subquery()
    
    # Get the actual latest records
    live_locations = db.query(StaffRealtimeLocation).join(
        latest_subq,
        and_(
            StaffRealtimeLocation.employee_id == latest_subq.c.employee_id,
            StaffRealtimeLocation.captured_at == latest_subq.c.max_captured
        )
    ).all()
    
    # Get attendance for target date for all team members
    attendances = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id.in_(team_ids),
        StaffAttendance.date == target_date
    ).all()
    attendance_map = {a.employee_id: a for a in attendances}
    
    # DC_JOURNEY_AUTHORITATIVE_001: Query active journeys from authoritative table
    from app.models.staff_journey import JourneyStatus
    # For historical view, get all journeys; for live view, only in-progress
    if is_historical:
        active_journeys = []  # No "active" journeys for past dates
        journey_map = {}
    else:
        active_journeys = db.query(StaffJourney).filter(
            StaffJourney.employee_id.in_(team_ids),
            StaffJourney.date == target_date,
            StaffJourney.status == JourneyStatus.IN_PROGRESS
        ).all()
        journey_map = {j.employee_id: j for j in active_journeys}
    
    # DC Protocol (Jan 28, 2026): Query all journeys for target date for stats
    all_journeys_target = db.query(StaffJourney).filter(
        StaffJourney.employee_id.in_(team_ids),
        StaffJourney.date == target_date
    ).all()
    
    # Build journey stats map per employee
    journey_stats_map = {}
    for j in all_journeys_target:
        emp_id = j.employee_id
        if emp_id not in journey_stats_map:
            journey_stats_map[emp_id] = {"count": 0, "total_km": 0.0, "total_duration_min": 0}
        journey_stats_map[emp_id]["count"] += 1
        journey_stats_map[emp_id]["total_km"] += float(j.total_distance_km or 0)
        journey_stats_map[emp_id]["total_duration_min"] += int(j.total_duration_minutes or 0)
    
    # DC Protocol (Jan 28, 2026): For historical mode, skip last_known_map since live_locations IS the last known
    # For live mode, fetch last known location for users without recent GPS
    if is_historical:
        # In historical mode, live_locations already contains the last known for that date
        last_known_map = {}
    else:
        # For live mode, fetch last known location for ALL employees (no time cutoff)
        last_known_subq = db.query(
            StaffRealtimeLocation.employee_id,
            func.max(StaffRealtimeLocation.captured_at).label('max_captured')
        ).filter(
            StaffRealtimeLocation.employee_id.in_(team_ids)
        ).group_by(StaffRealtimeLocation.employee_id).subquery()
        
        last_known_locations = db.query(StaffRealtimeLocation).join(
            last_known_subq,
            and_(
                StaffRealtimeLocation.employee_id == last_known_subq.c.employee_id,
                StaffRealtimeLocation.captured_at == last_known_subq.c.max_captured
            )
        ).all()
        last_known_map = {loc.employee_id: loc for loc in last_known_locations}
    
    # Build response with employee info
    location_data = []
    active_count = 0
    break_count = 0
    journey_count = 0
    offline_count = 0
    
    location_map = {loc.employee_id: loc for loc in live_locations}
    
    logger.info(f"[DC_LIVE_TRACKER_DEBUG] Attendances today: {len(attendances)}, Live locations: {len(live_locations)}, Last known: {len(last_known_map)}")
    for att in attendances:
        logger.info(f"[DC_LIVE_TRACKER_DEBUG] Att emp_id={att.employee_id}, clock_in={att.clock_in}, clock_out={att.clock_out}, location_mode={att.location_mode}, clock_in_location={att.clock_in_location}")
    
    for member in team_members:
        loc = location_map.get(member.id)
        att = attendance_map.get(member.id)
        journey = journey_map.get(member.id)
        
        # DC Protocol (Jan 28, 2026): Extract attendance details for popup display
        clock_in_time = None
        worked_minutes = 0
        total_break_minutes = 0
        total_distance_km = 0.0
        gps_status = 'active'
        gps_status_reason = None
        offline_duration_min = 0
        last_battery_pct = None
        last_gps_at = None
        if att:
            if att.clock_in:
                clock_in_time = att.clock_in.isoformat()
            worked_minutes = att.worked_minutes or 0
            total_break_minutes = att.break_minutes or 0
            # DC Protocol (Jan 28, 2026): Include total travel distance in km
            total_distance_km = round(float(att.total_distance_meters or 0) / 1000, 2)
            # DC Protocol (Jan 29, 2026): Defensive getattr for GPS status columns (production compatibility)
            gps_status = getattr(att, 'gps_status', None) or 'active'
            gps_status_reason = getattr(att, 'gps_status_reason', None)
            last_battery_pct = getattr(att, 'last_battery_pct', None)
            att_last_gps_at = getattr(att, 'last_gps_at', None)
            last_gps_at = att_last_gps_at.isoformat() if att_last_gps_at else None
            # Calculate offline duration if GPS is not active
            if att_last_gps_at and gps_status != 'active':
                offline_duration_min = int((now - att_last_gps_at).total_seconds() / 60)
        
        # DC Protocol (Jan 28, 2026): Get journey stats for this employee
        jstats = journey_stats_map.get(member.id, {"count": 0, "total_km": 0.0, "total_duration_min": 0})
        journey_count_today = jstats["count"]
        journey_km_today = round(jstats["total_km"], 2)
        journey_duration_min = jstats["total_duration_min"]
        # Calculate avg speed: km / hours
        avg_speed_kmh = round(journey_km_today / (journey_duration_min / 60), 1) if journey_duration_min > 0 else 0.0
        
        # DC Protocol (Jan 28, 2026): Get last known location for offline users
        last_known_loc = last_known_map.get(member.id)
        
        # DC_STATUS_AGGREGATION_001: Priority - Active Journey > Break > Active > Offline
        if journey:
            # WVV_JOURNEY_PRIORITY_001: Active journey takes precedence
            journey_count += 1
            
            # Use last known location even if older than 10 minutes
            if loc:
                marker = loc.to_map_marker()
                marker["status"] = "on_journey"
                marker["employee"] = {
                    "id": member.id,
                    "emp_code": member.emp_code,
                    "full_name": member.full_name,
                    "role_name": member.role.role_name if member.role else None,
                    "department_name": member.department.name if member.department else None
                }
                # DC Protocol (Jan 28, 2026): Add attendance details for popup
                marker["clock_in_time"] = clock_in_time
                marker["worked_minutes"] = worked_minutes
                marker["total_break_minutes"] = total_break_minutes
                marker["total_distance_km"] = total_distance_km
                marker["journey_count_today"] = journey_count_today
                marker["journey_km_today"] = journey_km_today
                marker["avg_speed_kmh"] = avg_speed_kmh
                marker["is_last_known"] = is_historical  # In historical mode, all locations are "last known"
                marker["gps_status"] = gps_status
                marker["gps_status_reason"] = gps_status_reason
                marker["offline_duration_min"] = offline_duration_min
                marker["last_battery_pct"] = last_battery_pct
                marker["last_gps_at"] = last_gps_at
                location_data.append(marker)
            else:
                # Journey active but no location - use journey start point
                location_data.append({
                    "employee_id": member.id,
                    "emp_code": member.emp_code,
                    "name": member.full_name,
                    "lat": float(journey.start_latitude) if journey.start_latitude else None,
                    "lng": float(journey.start_longitude) if journey.start_longitude else None,
                    "status": "on_journey",
                    "break_type": None,
                    "captured_at": now.isoformat(),
                    "accuracy_m": None,
                    "battery_percentage": last_battery_pct,
                    "clock_in_time": clock_in_time,
                    "worked_minutes": worked_minutes,
                    "total_break_minutes": total_break_minutes,
                    "total_distance_km": total_distance_km,
                    "journey_count_today": journey_count_today,
                    "journey_km_today": journey_km_today,
                    "avg_speed_kmh": avg_speed_kmh,
                    "is_last_known": False,  # Using journey start point, not last known
                    "gps_status": gps_status,
                    "gps_status_reason": gps_status_reason,
                    "offline_duration_min": offline_duration_min,
                    "last_battery_pct": last_battery_pct,
                    "last_gps_at": last_gps_at,
                    "employee": {
                        "id": member.id,
                        "emp_code": member.emp_code,
                        "full_name": member.full_name,
                        "role_name": member.role.role_name if member.role else None,
                        "department_name": member.department.name if member.department else None
                    },
                    "journey_id": journey.id
                })
                # DC_AUDIT_TRACKER_001: Log journey without recent GPS
                print(f"[DC_AUDIT_TRACKER_001] {member.emp_code} on_journey id={journey.id} no_recent_gps")
        elif loc:
            marker = loc.to_map_marker()
            marker["employee"] = {
                "id": member.id,
                "emp_code": member.emp_code,
                "full_name": member.full_name,
                "role_name": member.role.role_name if member.role else None,
                "department_name": member.department.name if member.department else None
            }
            # DC Protocol (Jan 28, 2026): Add attendance details for popup
            marker["clock_in_time"] = clock_in_time
            marker["worked_minutes"] = worked_minutes
            marker["total_break_minutes"] = total_break_minutes
            marker["total_distance_km"] = total_distance_km
            marker["journey_count_today"] = journey_count_today
            marker["journey_km_today"] = journey_km_today
            marker["avg_speed_kmh"] = avg_speed_kmh
            marker["is_last_known"] = is_historical  # In historical mode, all locations are "last known"
            marker["gps_status"] = gps_status
            marker["gps_status_reason"] = gps_status_reason
            marker["offline_duration_min"] = offline_duration_min
            marker["last_battery_pct"] = last_battery_pct
            marker["last_gps_at"] = last_gps_at
            location_data.append(marker)
            
            if loc.is_on_break:
                break_count += 1
            elif loc.is_clocked_in:
                active_count += 1
            else:
                offline_count += 1
        else:
            # No location AND no journey - check attendance
            # DC Protocol (Jan 28, 2026): Use last known location if available
            # DC Protocol (Jan 29, 2026): Fallback to clock_in_location for web clock-ins
            last_lat = float(last_known_loc.latitude) if last_known_loc and last_known_loc.latitude else None
            last_lng = float(last_known_loc.longitude) if last_known_loc and last_known_loc.longitude else None
            last_captured = last_known_loc.captured_at.isoformat() if last_known_loc and last_known_loc.captured_at else None
            
            # Fallback to clock_in_location from attendance if no realtime location
            if att and last_lat is None and att.clock_in_location:
                clock_in_loc = att.clock_in_location
                if isinstance(clock_in_loc, dict):
                    last_lat = float(clock_in_loc.get('latitude') or clock_in_loc.get('lat') or 0) or None
                    last_lng = float(clock_in_loc.get('longitude') or clock_in_loc.get('lng') or 0) or None
                    if att.clock_in:
                        last_captured = att.clock_in.isoformat()
            
            # DC Protocol (Jan 29, 2026): Fallback to office coordinates for office clock-ins
            if att and last_lat is None and att.location_mode == 'office':
                # Check clock_in_location for office name pattern
                office_name = None
                if att.clock_in_location and isinstance(att.clock_in_location, dict):
                    office_name = att.clock_in_location.get('office') or att.clock_in_location.get('address')
                
                # Match against known office locations
                for office in OFFICE_LOCATIONS:
                    if office_name and office['name'] in str(office_name):
                        last_lat = office['lat']
                        last_lng = office['lng']
                        if att.clock_in:
                            last_captured = att.clock_in.isoformat()
                        break
                
                # If no match found, use first office as default for 'office' mode
                if last_lat is None and OFFICE_LOCATIONS:
                    last_lat = OFFICE_LOCATIONS[0]['lat']
                    last_lng = OFFICE_LOCATIONS[0]['lng']
                    if att.clock_in:
                        last_captured = att.clock_in.isoformat()
            
            if att and att.clock_out is None:
                # DC_STATUS_AGGREGATION_001: Clocked in but no GPS - mark ACTIVE
                active_count += 1
                location_data.append({
                    "employee_id": member.id,
                    "emp_code": member.emp_code,
                    "name": member.full_name,
                    "lat": last_lat,
                    "lng": last_lng,
                    "status": "active",
                    "break_type": None,
                    "captured_at": last_captured,
                    "accuracy_m": float(last_known_loc.accuracy_m) if last_known_loc and last_known_loc.accuracy_m else None,
                    "battery_percentage": last_battery_pct,
                    "clock_in_time": clock_in_time,
                    "worked_minutes": worked_minutes,
                    "total_break_minutes": total_break_minutes,
                    "total_distance_km": total_distance_km,
                    "journey_count_today": journey_count_today,
                    "journey_km_today": journey_km_today,
                    "avg_speed_kmh": avg_speed_kmh,
                    "gps_status": gps_status,
                    "gps_status_reason": gps_status_reason,
                    "offline_duration_min": offline_duration_min,
                    "last_battery_pct": last_battery_pct,
                    "last_gps_at": last_gps_at,
                    "employee": {
                        "id": member.id,
                        "emp_code": member.emp_code,
                        "full_name": member.full_name,
                        "role_name": member.role.role_name if member.role else None,
                        "department_name": member.department.name if member.department else None
                    },
                    "is_clocked_in": True,
                    "is_last_known": last_lat is not None
                })
            else:
                # DC_STATUS_AGGREGATION_001: No location, no journey, not clocked - OFFLINE
                offline_count += 1
                location_data.append({
                    "employee_id": member.id,
                    "emp_code": member.emp_code,
                    "name": member.full_name,
                    "lat": last_lat,
                    "lng": last_lng,
                    "status": "offline",
                    "break_type": None,
                    "captured_at": last_captured,
                    "accuracy_m": float(last_known_loc.accuracy_m) if last_known_loc and last_known_loc.accuracy_m else None,
                    "battery_percentage": last_battery_pct,
                    "clock_in_time": clock_in_time,
                    "worked_minutes": worked_minutes,
                    "total_break_minutes": total_break_minutes,
                    "total_distance_km": total_distance_km,
                    "journey_count_today": journey_count_today,
                    "journey_km_today": journey_km_today,
                    "avg_speed_kmh": avg_speed_kmh,
                    "gps_status": gps_status,
                    "gps_status_reason": gps_status_reason,
                    "offline_duration_min": offline_duration_min,
                    "last_battery_pct": last_battery_pct,
                    "last_gps_at": last_gps_at,
                    "employee": {
                        "id": member.id,
                        "emp_code": member.emp_code,
                        "full_name": member.full_name,
                        "role_name": member.role.role_name if member.role else None,
                        "department_name": member.department.name if member.department else None
                    },
                    "is_clocked_in": False,
                    "is_last_known": last_lat is not None
                })
                # DC_AUDIT_TRACKER_001: Log why offline
                print(f"[DC_AUDIT_TRACKER_001] {member.emp_code} marked OFFLINE - no_location no_journey not_clocked_in last_known={last_lat is not None}")
    
    logger.info(f"[DC_LIVE_TRACKER_DEBUG] FINAL RESPONSE: locations={len(location_data)}, team_total={len(team_members)}, active={active_count}, break={break_count}, journey={journey_count}, offline={offline_count}")
    
    return {
        "success": True,
        "timestamp": now.isoformat(),
        "locations": location_data,
        "summary": {
            "total": len(team_members),
            "active": active_count,
            "on_break": break_count,
            "on_journey": journey_count,
            "offline": offline_count
        },
        "debug": {
            "user_emp_code": current_user.emp_code,
            "user_id": current_user.id,
            "is_manager": is_manager,
            "is_vgk4u_or_hr": is_vgk4u_or_hr,
            "accessible_count": len(accessible_ids),
            "team_count": len(team_members),
            "attendance_count": len(attendances),
            "live_locations_count": len(live_locations)
        }
    }


@router.get("/location/team/history", summary="Get team location history (Manager)")
async def get_team_location_history(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    from_date: Optional[str] = Query(None, description="Start date"),
    to_date: Optional[str] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get location history for team members (Manager/Lead)
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users with direct reports see their team's location history
    - VGK/HR see all staff history
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        (current_user.role.hierarchy_level or 0) >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(
            status_code=403,
            detail="Only those with direct reports or HR/VGK4U can view team location history"
        )
    
    # DC Protocol (Dec 04, 2025): Get accessible team member IDs with recursive downline
    team_ids = get_team_member_ids(current_user, db, StaffEmployee)
    
    if not team_ids:
        return {
            "success": True,
            "total": 0,
            "locations": [],
            "has_more": False
        }
    
    # Build query
    query = db.query(StaffRealtimeLocation).filter(
        StaffRealtimeLocation.employee_id.in_(team_ids)
    )
    
    # Filter by specific employee if provided
    if employee_id:
        if employee_id not in team_ids:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Cannot view this employee's location."
            )
        query = query.filter(StaffRealtimeLocation.employee_id == employee_id)
    
    # Date filters
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(func.date(StaffRealtimeLocation.captured_at) == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    elif from_date and to_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d")
            end = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(
                StaffRealtimeLocation.captured_at >= start,
                StaffRealtimeLocation.captured_at <= end
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    total = query.count()
    locations = query.order_by(StaffRealtimeLocation.captured_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "locations": [loc.to_dict(include_employee=True) for loc in locations],
        "has_more": (offset + limit) < total
    }


@router.get("/location/all/live", summary="Get all staff live locations (Manager view)")
async def get_all_staff_live_locations(
    department_id: Optional[int] = Query(None, description="Filter by department"),
    status_filter: Optional[str] = Query(None, description="Filter: active, break, journey, offline"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get live locations of all staff in user's reporting chain
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users with direct reports see locations from their entire recursive downline
    - VGK/HR see all staff
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        (current_user.role.hierarchy_level or 0) >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(
            status_code=403,
            detail="Only those with direct reports or HR/VGK4U can view all staff locations"
        )
    
    now = get_indian_time()
    today = get_indian_date()
    cutoff_time = now - timedelta(minutes=10)
    
    # DC Protocol: Get staff within user's reporting chain
    accessible_ids = get_team_member_ids(current_user, db, StaffEmployee, department_id)
    
    all_staff = db.query(StaffEmployee).filter(
        StaffEmployee.id.in_(accessible_ids),
        StaffEmployee.status == 'active'
    ).all()
    staff_ids = [s.id for s in all_staff]
    
    if not staff_ids:
        return {
            "success": True,
            "message": "No staff found",
            "locations": [],
            "summary": {"total": 0, "active": 0, "on_break": 0, "on_journey": 0, "offline": 0}
        }
    
    # Get latest location for each staff member
    latest_subq = db.query(
        StaffRealtimeLocation.employee_id,
        func.max(StaffRealtimeLocation.captured_at).label('max_captured')
    ).filter(
        StaffRealtimeLocation.employee_id.in_(staff_ids),
        StaffRealtimeLocation.captured_at >= cutoff_time
    ).group_by(StaffRealtimeLocation.employee_id).subquery()
    
    live_locations = db.query(StaffRealtimeLocation).join(
        latest_subq,
        and_(
            StaffRealtimeLocation.employee_id == latest_subq.c.employee_id,
            StaffRealtimeLocation.captured_at == latest_subq.c.max_captured
        )
    ).all()
    
    location_map = {loc.employee_id: loc for loc in live_locations}
    
    # Get today's attendance
    attendances = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id.in_(staff_ids),
        StaffAttendance.date == today
    ).all()
    attendance_map = {a.employee_id: a for a in attendances}
    
    location_data = []
    active_count = 0
    break_count = 0
    journey_count = 0
    offline_count = 0
    
    for member in all_staff:
        loc = location_map.get(member.id)
        att = attendance_map.get(member.id)
        
        # Determine status
        if loc:
            if loc.is_on_journey:
                status = "journey"
                journey_count += 1
            elif loc.is_on_break:
                status = "break"
                break_count += 1
            elif loc.is_clocked_in:
                status = "active"
                active_count += 1
            else:
                status = "offline"
                offline_count += 1
        else:
            status = "offline"
            offline_count += 1
        
        # Apply status filter if provided
        if status_filter and status != status_filter:
            continue
        
        # DC_BATTERY_001: Extract battery_percentage from device_info JSONB
        battery_pct = None
        if loc and loc.device_info:
            battery_pct = loc.device_info.get("battery_percentage")
        
        # DC_LIVE_TRACKER_004: Calculate clock-in time, break totals, worked hours
        clock_in_time = None
        total_break_minutes = 0
        worked_minutes = 0
        
        if att and att.clock_in:
            clock_in_time = att.clock_in.isoformat()
            total_break_minutes = att.break_minutes or 0
            # Calculate worked minutes (clock-in to now, minus breaks)
            if not att.clock_out:
                elapsed = (now - att.clock_in).total_seconds() / 60
                worked_minutes = max(0, int(elapsed - total_break_minutes))
            else:
                # Already clocked out - use stored worked_minutes
                worked_minutes = att.worked_minutes or 0
        
        marker = {
            "employee_id": member.id,
            "emp_code": member.emp_code,
            "name": member.full_name,
            "lat": float(loc.latitude) if loc else None,
            "lng": float(loc.longitude) if loc else None,
            "status": status,
            "break_type": loc.break_type if loc else None,
            "captured_at": loc.captured_at.isoformat() if loc else None,
            "accuracy_m": float(loc.accuracy_m) if loc else None,
            "battery_percentage": battery_pct,
            "clock_in_time": clock_in_time,
            "total_break_minutes": total_break_minutes,
            "worked_minutes": worked_minutes,
            "employee": {
                "id": member.id,
                "emp_code": member.emp_code,
                "full_name": member.full_name,
                "role_name": member.role.role_name if member.role else None,
                "department_name": member.department.name if member.department else None
            },
            "is_clocked_in": att is not None and att.clock_out is None if att else False
        }
        location_data.append(marker)
    
    return {
        "success": True,
        "timestamp": now.isoformat(),
        "locations": location_data,
        "summary": {
            "total": len(all_staff),
            "active": active_count,
            "on_break": break_count,
            "on_journey": journey_count,
            "offline": offline_count
        }
    }


@router.get("/location/all/history", summary="Get all staff location history (Manager view)")
async def get_all_staff_location_history(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    from_date: Optional[str] = Query(None, description="Start date"),
    to_date: Optional[str] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get location history for staff in user's reporting chain
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users with direct reports see locations from their entire recursive downline
    - VGK/HR see all staff
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        (current_user.role.hierarchy_level or 0) >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(
            status_code=403,
            detail="Only those with direct reports or HR/VGK4U can view all staff location history"
        )
    
    # DC Protocol: Get staff within user's reporting chain
    accessible_ids = get_team_member_ids(current_user, db, StaffEmployee, department_id)
    
    # Build base query - filter to accessible employees only
    query = db.query(StaffRealtimeLocation).filter(
        StaffRealtimeLocation.employee_id.in_(accessible_ids)
    )
    
    # Filter by specific employee (must be in accessible list)
    if employee_id:
        if employee_id in accessible_ids:
            query = query.filter(StaffRealtimeLocation.employee_id == employee_id)
    
    # Date filters
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(func.date(StaffRealtimeLocation.captured_at) == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    elif from_date and to_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d")
            end = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(
                StaffRealtimeLocation.captured_at >= start,
                StaffRealtimeLocation.captured_at <= end
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    total = query.count()
    locations = query.order_by(StaffRealtimeLocation.captured_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "locations": [loc.to_dict(include_employee=True) for loc in locations],
        "has_more": (offset + limit) < total
    }


class RegularizationRequest(BaseModel):
    date: str = Field(..., description="Date for regularization YYYY-MM-DD")
    exception_type: str = Field(..., description="Type of exception")
    reason: str = Field(..., description="Reason for regularization")
    requested_clock_in: Optional[str] = Field(None, description="Requested clock-in time HH:MM")
    requested_clock_out: Optional[str] = Field(None, description="Requested clock-out time HH:MM")


@router.post("/regularization-request", summary="Submit attendance regularization request")
async def submit_regularization_request(
    request_data: RegularizationRequest = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    now = datetime.now(pytz.timezone("Asia/Kolkata"))

    try:
        req_date = datetime.strptime(request_data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if req_date > now.date():
        raise HTTPException(status_code=400, detail="Cannot submit regularization for a future date")

    log_entry = StaffAttendanceLog(
        employee_id=current_user.id,
        action=f"regularization_request:{request_data.exception_type}",
        details=f"Date: {request_data.date} | Type: {request_data.exception_type} | "
                f"Reason: {request_data.reason} | "
                f"Clock In: {request_data.requested_clock_in or 'N/A'} | "
                f"Clock Out: {request_data.requested_clock_out or 'N/A'}",
        ip_address="mobile",
        performed_at=now
    )
    db.add(log_entry)
    db.commit()

    return {
        "success": True,
        "message": "Regularization request submitted successfully",
        "data": {
            "date": request_data.date,
            "exception_type": request_data.exception_type,
            "status": "pending"
        }
    }


# ============================================================================
# UNIFIED ACTIVITY TIME INTEGRATION (DC Protocol - Feb 24, 2026)
# Total/Planned/Completed/Pending counts per category + time tracking
# ============================================================================

@router.get("/activity-summary", summary="Get daily activity summary with category-wise counts and time")
async def get_activity_summary(
    target_date: str = Query(None, description="Date in YYYY-MM-DD format (defaults to today IST)"),
    employee_id: int = Query(None, description="Employee ID (for supervisor view, defaults to self)"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns category-wise activity summary with Total/Planned/Completed/Pending counts
    (like Day Planner tabs) plus Required/Planned/Completed time per category.
    
    Categories shown: KRA, Tasks, Day Planner, Journeys (for all)
    + Leads/CRM (sales departments), Service Tickets (service departments)
    + Custom/Other (always available)
    
    DC Protocol: Single source of truth for supervisor/employee activity overview.
    """
    from app.services.activity_time_service import get_daily_activity_summary
    from app.models.staff import StaffEmployeeDepartment
    
    if target_date:
        try:
            query_date = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        ist = pytz.timezone('Asia/Kolkata')
        query_date = datetime.now(ist).date()
    
    target_emp_id = employee_id or current_user.id
    
    if target_emp_id != current_user.id:
        is_top_level = current_user.role and current_user.role.role_code in ('vgk4u', 'key_leadership')
        is_manager = hasattr(current_user, 'role_type') and current_user.role_type in ('supreme_admin', 'admin', 'hr_admin', 'manager')
        if not is_top_level and not is_manager:
            raise HTTPException(status_code=403, detail="Only managers can view other employees' activity")
    
    target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == target_emp_id).first() if target_emp_id != current_user.id else current_user
    dept_ids = []
    if target_emp and target_emp.department_id:
        dept_ids.append(target_emp.department_id)
    
    additional = db.query(StaffEmployeeDepartment.department_id).filter(
        StaffEmployeeDepartment.employee_id == target_emp_id
    ).all()
    dept_ids.extend([d.department_id for d in additional])
    
    summary = get_daily_activity_summary(db, target_emp_id, query_date, dept_ids or None)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
    
    return {"success": True, "data": summary}


@router.get("/activity-detail/{source_type}", summary="Get detailed activity entries for a category")
async def get_activity_detail_endpoint(
    source_type: str,
    target_date: str = Query(None, description="Date in YYYY-MM-DD format"),
    employee_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get detailed source items and time entries for a specific category on a date."""
    from app.services.activity_time_service import get_activity_detail
    
    if target_date:
        try:
            query_date = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        ist = pytz.timezone('Asia/Kolkata')
        query_date = datetime.now(ist).date()
    
    target_emp_id = employee_id or current_user.id
    
    if target_emp_id != current_user.id:
        is_top_level = current_user.role and current_user.role.role_code in ('vgk4u', 'key_leadership')
        is_manager = hasattr(current_user, 'role_type') and current_user.role_type in ('supreme_admin', 'admin', 'hr_admin', 'manager')
        if not is_top_level and not is_manager:
            raise HTTPException(status_code=403, detail="Only managers can view other employees' activity")
    
    detail = get_activity_detail(db, target_emp_id, query_date, source_type)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
    
    return {"success": True, "data": detail}


@router.get("/activity-history/{source_type}", summary="Get activity history for a category")
async def get_activity_history_endpoint(
    source_type: str,
    days: int = Query(7, ge=1, le=90),
    employee_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get historical activity entries for a category over N days."""
    from app.services.activity_time_service import get_activity_history
    
    target_emp_id = employee_id or current_user.id
    
    history = get_activity_history(db, target_emp_id, source_type, days)
    return {"success": True, "data": history}


@router.post("/activity-log", summary="Log custom activity time entry")
async def log_custom_activity(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Log a custom/manual activity time entry.
    DC Protocol: Immutable insert into activity ledger.
    WVV Protocol: Minutes must be 1-1440.
    """
    from app.services.activity_time_service import log_activity_time
    
    completed_minutes = data.get("completed_minutes") or data.get("time_taken_minutes")
    if not completed_minutes or completed_minutes < 1:
        raise HTTPException(status_code=400, detail="Time taken (minutes) is required and must be at least 1")
    if completed_minutes > 1440:
        raise HTTPException(status_code=400, detail="Time taken cannot exceed 1440 minutes (24 hours)")
    
    source_type = data.get("source_type", "custom")
    target_date_str = data.get("date")
    
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        ist = pytz.timezone('Asia/Kolkata')
        target_date = datetime.now(ist).date()
    
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]
    
    try:
        entry = log_activity_time(
            db=db,
            employee_id=current_user.id,
            source_type=source_type,
            completed_minutes=completed_minutes,
            target_date=target_date,
            source_id=data.get("source_id"),
            source_title=data.get("source_title", data.get("description", "Custom entry")),
            source_code=data.get("source_code"),
            required_minutes=data.get("required_minutes", 0),
            planned_minutes=data.get("planned_minutes", 0),
            description=data.get("description"),
            ip_address=client_ip,
            user_agent=ua,
            created_by=current_user.id
        )
        db.commit()
        return {"success": True, "data": entry.to_dict(), "message": "Activity time logged successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _check_activity_approval_access(db: Session, current_user: StaffEmployee, target_employee_id: int):
    """DC Protocol: Verify supervisor has approval access to target employee's activities."""
    if target_employee_id == current_user.id:
        raise HTTPException(status_code=403, detail="Cannot approve your own activity entries")
    
    is_top_level = current_user.role and current_user.role.role_code in ('vgk4u', 'key_leadership')
    if is_top_level:
        return True
    
    target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == target_employee_id).first()
    if not target_emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    is_reporting_manager = target_emp.reporting_manager_id == current_user.id
    
    managed_depts = db.query(StaffDepartment).filter(
        StaffDepartment.head_id == current_user.id
    ).all()
    dept_ids = [d.id for d in managed_depts]
    is_dept_manager = target_emp.department_id in dept_ids
    
    is_manager_role = hasattr(current_user, 'role_type') and current_user.role_type in ('supreme_admin', 'admin', 'hr_admin', 'manager')
    
    if not is_reporting_manager and not is_dept_manager and not is_manager_role:
        raise HTTPException(status_code=403, detail="Not authorized to approve this employee's activities")
    
    return True


@router.post("/activity-approve/{entry_id}", summary="Approve or reject an individual activity time entry")
async def approve_activity_entry(
    entry_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve or reject an individual activity time entry with optional time adjustment.
    DC Protocol: Approval tracked on ledger entry, original minutes preserved.
    Status flow: submitted -> approved/rejected, rejected -> resubmitted -> approved/rejected
    """
    from app.services.activity_time_service import recalculate_attendance_activity
    
    entry = db.query(StaffActivityTimeLog).filter(StaffActivityTimeLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Activity entry not found")
    
    _check_activity_approval_access(db, current_user, entry.employee_id)
    
    if entry.approval_status not in ('submitted', 'resubmitted'):
        raise HTTPException(status_code=400, detail=f"Entry is already {entry.approval_status}, cannot change")
    
    action = data.get("action", "").lower()
    if action not in ('approve', 'reject'):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    if action == 'approve':
        adjusted_minutes = data.get("approved_minutes")
        if adjusted_minutes is not None:
            if adjusted_minutes < 1 or adjusted_minutes > 1440:
                raise HTTPException(status_code=400, detail="Approved minutes must be between 1 and 1440")
            entry.approved_minutes = int(adjusted_minutes)
        else:
            entry.approved_minutes = entry.completed_minutes
        
        entry.approval_status = 'approved'
        entry.approved_by = current_user.id
        entry.approved_at = get_indian_time()
        entry.rejection_reason = None
        message = "Activity entry approved"
    else:
        reason = data.get("comments") or data.get("rejection_reason")
        if not reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        entry.approval_status = 'rejected'
        entry.approved_by = current_user.id
        entry.approved_at = get_indian_time()
        entry.rejection_reason = reason
        entry.approved_minutes = None
        message = "Activity entry rejected"
    
    recalculate_attendance_activity(db, entry.employee_id, entry.date)
    db.commit()
    
    return {"success": True, "data": entry.to_dict(), "message": message}


@router.post("/activity-approve-bulk", summary="Bulk approve/reject activity entries by category")
async def bulk_approve_activity(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Bulk approve or reject all pending activity entries for a category on a date.
    DC Protocol: Category-wise batch operation with consistent access control.
    """
    from app.services.activity_time_service import recalculate_attendance_activity
    
    employee_id = data.get("employee_id")
    target_date_str = data.get("date")
    source_type = data.get("source_type")
    action = data.get("action", "").lower()
    
    if not employee_id or not target_date_str or not source_type:
        raise HTTPException(status_code=400, detail="employee_id, date, and source_type are required")
    if action not in ('approve', 'reject'):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    _check_activity_approval_access(db, current_user, employee_id)
    
    try:
        query_date = date.fromisoformat(target_date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    entries = db.query(StaffActivityTimeLog).filter(
        StaffActivityTimeLog.employee_id == employee_id,
        StaffActivityTimeLog.date == query_date,
        StaffActivityTimeLog.source_type == source_type,
        StaffActivityTimeLog.approval_status.in_(['submitted', 'resubmitted'])
    ).all()
    
    if not entries:
        return {"success": True, "data": [], "message": "No pending entries to process", "count": 0}
    
    processed = []
    for entry in entries:
        if action == 'approve':
            adjusted = data.get("approved_minutes")
            entry.approved_minutes = int(adjusted) if adjusted else entry.completed_minutes
            entry.approval_status = 'approved'
            entry.approved_by = current_user.id
            entry.approved_at = get_indian_time()
            entry.rejection_reason = None
        else:
            reason = data.get("comments") or data.get("rejection_reason") or "Bulk rejected"
            entry.approval_status = 'rejected'
            entry.approved_by = current_user.id
            entry.approved_at = get_indian_time()
            entry.rejection_reason = reason
            entry.approved_minutes = None
        processed.append(entry.to_dict())
    
    recalculate_attendance_activity(db, employee_id, query_date)
    db.commit()
    
    return {
        "success": True,
        "data": processed,
        "message": f"{len(processed)} entries {action}d",
        "count": len(processed)
    }


@router.post("/activity-resubmit/{entry_id}", summary="Resubmit a rejected activity entry")
async def resubmit_activity_entry(
    entry_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Resubmit a rejected activity entry with updated time.
    DC Protocol: Only the original employee can resubmit their own rejected entries.
    Status flow: rejected -> resubmitted (enters approval loop again)
    """
    entry = db.query(StaffActivityTimeLog).filter(StaffActivityTimeLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Activity entry not found")
    
    if entry.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the entry owner can resubmit")
    
    if entry.approval_status != 'rejected':
        raise HTTPException(status_code=400, detail=f"Only rejected entries can be resubmitted, current status: {entry.approval_status}")
    
    new_minutes = data.get("completed_minutes")
    if new_minutes:
        if new_minutes < 1 or new_minutes > 1440:
            raise HTTPException(status_code=400, detail="Minutes must be between 1 and 1440")
        entry.completed_minutes = int(new_minutes)
    
    new_desc = data.get("description")
    if new_desc:
        entry.description = new_desc
    
    new_title = data.get("source_title")
    if new_title:
        entry.source_title = new_title
    
    entry.approval_status = 'resubmitted'
    entry.rejection_reason = None
    entry.approved_by = None
    entry.approved_at = None
    entry.approved_minutes = None
    
    from app.services.activity_time_service import recalculate_attendance_activity
    recalculate_attendance_activity(db, entry.employee_id, entry.date)
    db.commit()
    
    return {"success": True, "data": entry.to_dict(), "message": "Activity entry resubmitted for approval"}
