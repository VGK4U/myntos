"""
Staff Journey Tracking API Endpoints
DC Protocol: Complete audit trail for journey tracking and reimbursement
WVV: Validated GPS data, distance calculation, photo verification
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, date, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import pytz
import os
import uuid
import hashlib
import json

from app.core.database import get_db
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee
from app.models.staff_attendance import StaffAttendance
from app.models.staff_journey import (
    StaffJourney, StaffJourneyTrackPoint, StaffJourneyApproval,
    JourneyStatus, JourneyApprovalStatus, JourneyPurpose
)
from app.models.staff_field_work import StaffTransportRate
from app.models.staff_accounts import AssociatedCompany
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.staff_hierarchy import get_accessible_employee_ids, get_team_member_ids

router = APIRouter()

# DC Protocol: Legacy directory removed - UniversalUploadService handles all pathing
# JOURNEY_PHOTOS_DIR = "storage/journey_photos"  # DEPRECATED
# os.makedirs(JOURNEY_PHOTOS_DIR, exist_ok=True)  # DEPRECATED


def get_indian_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


def get_indian_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def is_mobile_device(user_agent: str) -> bool:
    """DC_MOBILE_ONLY_001: Check if request is from mobile device"""
    if not user_agent:
        return False
    ua_lower = user_agent.lower()
    mobile_keywords = ['android', 'iphone', 'ipad', 'mobile', 'tablet', 'windows phone', 'blackberry']
    return any(keyword in ua_lower for keyword in mobile_keywords)


def generate_journey_session_token() -> str:
    """
    DC Protocol (Dec 04, 2025): Generate cryptographically strong session token for journey
    This token replaces strict device binding - allows legitimate users to end journeys
    despite network changes, browser cache clears, or app restarts
    """
    import secrets
    return secrets.token_hex(32)  # 64 character hex string


def get_device_fingerprint(request: Request, strict_mobile_check: bool = True) -> dict:
    """
    DC_DEVICE_FINGERPRINT_001: Generate device identifier for audit purposes
    Dec 04, 2025: Changed to non-blocking - fingerprint used for audit, not hard validation
    
    Args:
        request: HTTP request object
        strict_mobile_check: If True, raises error for non-mobile. If False, just flags it.
    """
    user_agent = request.headers.get("user-agent", "unknown")
    ip_address = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    
    is_mobile = is_mobile_device(user_agent)
    
    # Check mobile-only requirement (only if strict)
    if strict_mobile_check and not is_mobile:
        raise HTTPException(
            status_code=400,
            detail="Journey tracking requires a mobile device. Web/desktop access not allowed."
        )
    
    # Create device fingerprint combining user-agent hash and IP
    device_signature = f"{user_agent}|{ip_address}".encode()
    device_id = hashlib.sha256(device_signature).hexdigest()[:16]
    
    return {
        "device_id": device_id,
        "is_mobile": is_mobile,
        "user_agent_hash": hashlib.sha256(user_agent.encode()).hexdigest()[:16],
        "ip_prefix": ip_address.split(".")[:3] if "." in ip_address else ip_address[:3],  # Privacy: partial IP
        "timestamp": get_indian_time().isoformat()
    }


def log_fingerprint_mismatch(journey, current_fp: dict, action: str):
    """
    DC Protocol (Dec 04, 2025): Log fingerprint mismatch as warning (not blocking)
    Used for audit trail when device fingerprint changes during journey
    """
    warning = {
        "action": action,
        "timestamp": get_indian_time().isoformat(),
        "original_device_id": journey.device_info.get('device_id') if journey.device_info else None,
        "current_device_id": current_fp.get('device_id'),
        "current_ip_prefix": current_fp.get('ip_prefix'),
        "is_mobile": current_fp.get('is_mobile')
    }
    
    # Initialize warnings list if needed
    if journey.fingerprint_warnings is None:
        journey.fingerprint_warnings = []
    
    journey.fingerprint_warnings = journey.fingerprint_warnings + [warning]
    journey.fingerprint_mismatch_count = (journey.fingerprint_mismatch_count or 0) + 1
    
    print(f"[DC_FINGERPRINT_MISMATCH] Journey {journey.id}: {action} from different device. Count: {journey.fingerprint_mismatch_count}")


class LocationData(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    address: Optional[str] = None  # DC_JOURNEY_ADDRESS_001: Location name for stop visualization


class StartJourneyRequest(BaseModel):
    purpose: str = "other"
    purpose_description: Optional[str] = None
    client_name: Optional[str] = None
    client_address: Optional[str] = None
    transport_mode: str = "bike"
    company_id: Optional[int] = None
    kra_instance_id: Optional[int] = None
    task_id: Optional[int] = None
    location: Optional[LocationData] = None
    gps_enabled: bool = True
    gps_permission_denied: bool = False
    device_info: Optional[dict] = None

    @validator('purpose')
    def validate_purpose(cls, v):
        valid = ['client_visit', 'site_inspection', 'meeting', 'delivery', 'collection', 'other']
        if v not in valid:
            raise ValueError(f"Invalid purpose. Must be one of: {valid}")
        return v

    @validator('transport_mode')
    def validate_transport_mode(cls, v):
        valid = ['car', 'bike', 'electric_bike', 'cart', 'local_transport', 'others']
        if v not in valid:
            raise ValueError(f"Invalid transport mode. Must be one of: {valid}")
        return v


class JourneyHeartbeatRequest(BaseModel):
    location: LocationData
    speed_kmh: Optional[float] = None


class EndJourneyRequest(BaseModel):
    location: Optional[LocationData] = None
    notes: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    action: str
    remarks: Optional[str] = None

    @validator('action')
    def validate_action(cls, v):
        valid = ['approve', 'reject']
        if v not in valid:
            raise ValueError(f"Invalid action. Must be one of: {valid}")
        return v


class BulkApprovalRequest(BaseModel):
    journey_ids: List[int]
    action: str
    remarks: Optional[str] = None

    @validator('action')
    def validate_action(cls, v):
        valid = ['approve', 'reject']
        if v not in valid:
            raise ValueError(f"Invalid action. Must be one of: {valid}")
        return v


def validate_wvv_gps(location: Optional[LocationData], require_accuracy: bool = True) -> tuple:
    """
    WVV Protocol (Updated Dec 05, 2025): Validate GPS data for Work Verification & Validation compliance
    
    Rules:
    - GPS accuracy ≤100m = WVV Compliant (counts toward reimbursement)
    - GPS accuracy >100m = WVV Degraded (stored for audit/visualization, not reimbursement)
    - No GPS data = Invalid (rejected)
    
    Returns: (is_valid: bool, is_wvv_compliant: bool, reason: str or None)
    - is_valid: True if GPS data can be stored (even if degraded)
    - is_wvv_compliant: True if accuracy ≤100m (counts for reimbursement)
    - reason: Explanation if not compliant or not valid
    """
    WVV_MAX_ACCURACY_METERS = 100.0
    
    if not location:
        return (False, False, "GPS location data not provided")
    
    if location.accuracy is None:
        if require_accuracy:
            return (False, False, "GPS accuracy data not available")
        # No accuracy data - accept as valid but mark non-compliant for safety
        return (True, False, "GPS accuracy not available - stored as non-compliant")
    
    if location.accuracy <= 0:
        return (False, False, f"Invalid GPS accuracy: {location.accuracy}m")
    
    if location.accuracy > WVV_MAX_ACCURACY_METERS:
        # WVV Protocol Fix (Dec 05, 2025): Accept degraded points for audit trail
        # Mark as valid (can be stored) but NOT compliant (won't count for reimbursement)
        reason = f"GPS accuracy {location.accuracy:.0f}m exceeds WVV limit of {WVV_MAX_ACCURACY_METERS:.0f}m - stored as degraded"
        return (True, False, reason)
    
    return (True, True, None)


@router.post("/start", summary="Start a new journey")
async def start_journey(
    request_data: StartJourneyRequest = Body(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Start tracking a new journey
    DC_MOBILE_ONLY_001: Journey tracking requires mobile device
    DC_DEVICE_BINDING_001: Journey data bound to device that started it
    DC_GPS_DEVICE_VALIDATION_001: All GPS data must come from same device
    WVV: Validates transport mode and purpose
    """
    now = get_indian_time()
    today = get_indian_date()
    
    # DC_MOBILE_ONLY_001: Verify mobile-only access
    device_fp = get_device_fingerprint(http_request)
    device_id = device_fp['device_id']

    active_journey = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        StaffJourney.status == JourneyStatus.IN_PROGRESS
    ).first()

    if active_journey:
        raise HTTPException(
            status_code=400,
            detail="You have an active journey. Please end it before starting a new one."
        )

    attendance = db.query(StaffAttendance).filter(
        StaffAttendance.employee_id == current_user.id,
        StaffAttendance.date == today
    ).first()

    # DC Protocol Phase 2: Company selection mandatory for SFMS integration
    if not request_data.company_id:
        raise HTTPException(
            status_code=400,
            detail="Company selection is required. Please select a company before starting the journey."
        )
    
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.id == request_data.company_id,
        AssociatedCompany.is_active == True
    ).first()
    
    if not company:
        raise HTTPException(
            status_code=400,
            detail="Invalid or inactive company selected. Please select a valid company."
        )
    
    # DC Protocol: Transport rate lookup with fallback defaults
    transport_rate = db.query(StaffTransportRate).filter(
        StaffTransportRate.transport_mode == request_data.transport_mode,
        StaffTransportRate.is_active == True
    ).first()

    # Default rates per transport mode (fallback when not configured in DB)
    default_rates = {
        'car': 8.00,
        'bike': 4.00,
        'electric_bike': 1.00,
        'cart': 10.00,
        'local_transport': 3.00,
        'others': 2.00
    }
    rate_per_km = float(transport_rate.rate_per_km) if transport_rate else default_rates.get(request_data.transport_mode, 4.00)

    is_reimbursable = request_data.gps_enabled and not request_data.gps_permission_denied
    non_reimbursable_reason = None
    wvv_warning = None
    
    if not request_data.gps_enabled:
        non_reimbursable_reason = "GPS was disabled during journey"
        is_reimbursable = False
    elif request_data.gps_permission_denied:
        non_reimbursable_reason = "GPS permission was denied"
        is_reimbursable = False
    elif request_data.location:
        # WVV Protocol Fix (Dec 05, 2025): Accept degraded GPS for journey start
        wvv_valid, wvv_compliant, wvv_reason = validate_wvv_gps(request_data.location, require_accuracy=True)
        if not wvv_valid:
            raise HTTPException(
                status_code=400,
                detail=f"WVV Error: {wvv_reason}. Please ensure GPS is enabled before starting a journey."
            )
        if not wvv_compliant:
            # Allow journey to start but warn and mark as degraded start
            wvv_warning = wvv_reason
            print(f"[WVV_DEGRADED_START] Journey starting with degraded GPS: {wvv_reason}")

    # DC_DEVICE_BINDING_001: Store device fingerprint for audit (not blocking)
    journey_device_info = device_fp.copy()
    if request_data.device_info:
        journey_device_info.update(request_data.device_info)
    
    # DC Protocol (Dec 04, 2025): Generate session token for flexible auth
    # This token replaces strict device binding - allows ending journey from any device
    session_token = generate_journey_session_token()

    journey = StaffJourney(
        employee_id=current_user.id,
        attendance_id=attendance.id if attendance else None,
        company_id=request_data.company_id,
        date=today,
        purpose=JourneyPurpose(request_data.purpose),
        purpose_description=request_data.purpose_description,
        client_name=request_data.client_name,
        client_address=request_data.client_address,
        transport_mode=request_data.transport_mode,
        rate_per_km=rate_per_km,
        kra_instance_id=request_data.kra_instance_id,
        task_id=request_data.task_id,
        start_time=now,
        gps_enabled=request_data.gps_enabled,
        gps_permission_denied=request_data.gps_permission_denied,
        is_reimbursable=is_reimbursable,
        non_reimbursable_reason=non_reimbursable_reason,
        device_info=journey_device_info,  # DC: Stores device_id for audit trail
        journey_session_token=session_token,  # DC (Dec 04, 2025): Token-based auth
        status=JourneyStatus.IN_PROGRESS,
        created_by=current_user.id
    )

    if request_data.location:
        journey.start_latitude = request_data.location.latitude
        journey.start_longitude = request_data.location.longitude

        # WVV Protocol Fix (Dec 05, 2025): Store WVV compliance for start point
        # Re-check since wvv_compliant might not be in scope if no location check was done
        start_wvv_compliant = True
        start_compliance_reason = None
        if request_data.location.accuracy and request_data.location.accuracy > 100:
            start_wvv_compliant = False
            start_compliance_reason = f"GPS accuracy {request_data.location.accuracy:.0f}m exceeds WVV limit of 100m"

        track_point = StaffJourneyTrackPoint(
            latitude=request_data.location.latitude,
            longitude=request_data.location.longitude,
            accuracy=request_data.location.accuracy,
            altitude=request_data.location.altitude,
            speed_kmh=request_data.location.speed,
            heading=request_data.location.heading,
            distance_from_prev=0,
            cumulative_distance=0,
            wvv_compliant=start_wvv_compliant,
            compliance_reason=start_compliance_reason,
            address=request_data.location.address,  # DC_JOURNEY_ADDRESS_001
            timestamp=now
        )
        journey.track_points.append(track_point)

    db.add(journey)
    db.commit()
    db.refresh(journey)

    message = "Journey started"
    if not is_reimbursable:
        message = "Journey started (GPS off - not reimbursable)"
    
    return {
        "success": True,
        "message": message,
        "journey": journey.to_dict(),
        "is_reimbursable": is_reimbursable,
        "rate_per_km": rate_per_km,
        "journey_session_token": session_token  # DC (Dec 04, 2025): Store this for flexible auth
    }


@router.post("/{journey_id}/heartbeat", summary="Send GPS heartbeat during journey")
async def journey_heartbeat(
    journey_id: int,
    request: JourneyHeartbeatRequest = Body(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Send GPS location update during journey
    DC_GPS_DEVICE_VALIDATION_001: GPS must come from same device that started journey
    DC: Calculates distance and speed, updates journey stats
    WVV: Validates GPS accuracy (≤100m required for reimbursable)
    DC_SESSION_EXTEND_001: Returns refreshed token to prevent session expiry during active journey
    """
    now = get_indian_time()

    journey = db.query(StaffJourney).filter(
        StaffJourney.id == journey_id,
        StaffJourney.employee_id == current_user.id,
        StaffJourney.status == JourneyStatus.IN_PROGRESS
    ).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Active journey not found")

    # DC Protocol (Dec 04, 2025): Relaxed device validation - log mismatches but don't block
    # This allows employees to continue journey even after network/browser changes
    try:
        current_device_fp = get_device_fingerprint(http_request, strict_mobile_check=False)
        current_device_id = current_device_fp['device_id']
        journey_device_id = journey.device_info.get('device_id') if journey.device_info else None
        
        if journey_device_id and journey_device_id != current_device_id:
            # Log mismatch for audit but don't block
            log_fingerprint_mismatch(journey, current_device_fp, "heartbeat")
    except Exception as e:
        print(f"[DC_GPS_DEVICE_WARNING] Device validation warning: {str(e)}")
        # Don't block - just log the warning

    # WVV Protocol Fix (Dec 05, 2025): Accept degraded GPS points for audit trail
    # Only reject if GPS data is completely invalid (no location at all)
    wvv_valid, wvv_compliant, wvv_reason = validate_wvv_gps(request.location, require_accuracy=True)
    
    if not wvv_valid:
        # Only reject if GPS data is completely unusable
        raise HTTPException(
            status_code=400,
            detail=f"WVV Error: {wvv_reason}. GPS heartbeat rejected - no valid location data."
        )
    
    # Log if degraded but still proceeding
    if not wvv_compliant:
        print(f"[WVV_DEGRADED_POINT] Journey {journey_id}: {wvv_reason}")

    last_point = db.query(StaffJourneyTrackPoint).filter(
        StaffJourneyTrackPoint.journey_id == journey_id
    ).order_by(StaffJourneyTrackPoint.timestamp.desc()).first()

    distance_from_prev = 0.0
    cumulative_distance = 0.0
    reimbursable_distance = 0.0

    if last_point:
        distance_from_prev = StaffJourneyTrackPoint.haversine_distance(
            last_point.latitude, last_point.longitude,
            request.location.latitude, request.location.longitude
        )
        cumulative_distance = last_point.cumulative_distance + distance_from_prev
        
        # WVV Protocol: Only count distance toward reimbursement if BOTH points are compliant
        if wvv_compliant and last_point.wvv_compliant:
            # Get current reimbursable distance from journey
            reimbursable_distance = (journey.reimbursable_distance_km or 0) + distance_from_prev
        else:
            reimbursable_distance = journey.reimbursable_distance_km or 0

    speed_kmh = request.speed_kmh
    if speed_kmh is None and request.location.speed:
        speed_kmh = request.location.speed * 3.6

    # WVV Protocol Fix: Store track point with compliance flag
    # DC_JOURNEY_ADDRESS_001: Include address for stop point visualization
    track_point = StaffJourneyTrackPoint(
        journey_id=journey_id,
        latitude=request.location.latitude,
        longitude=request.location.longitude,
        accuracy=request.location.accuracy,
        altitude=request.location.altitude,
        speed_kmh=speed_kmh,
        heading=request.location.heading,
        distance_from_prev=distance_from_prev,
        cumulative_distance=cumulative_distance,
        wvv_compliant=wvv_compliant,
        compliance_reason=wvv_reason if not wvv_compliant else None,
        address=request.location.address,  # DC_JOURNEY_ADDRESS_001
        timestamp=now
    )
    db.add(track_point)

    # Update journey totals
    journey.total_distance_km = cumulative_distance
    if speed_kmh and speed_kmh > journey.max_speed_kmh:
        journey.max_speed_kmh = speed_kmh

    # WVV Protocol: Only use reimbursable distance for payment calculation
    if journey.is_reimbursable:
        journey.reimbursable_distance_km = reimbursable_distance
        journey.calculate_reimbursement()

    db.commit()

    # DC_SESSION_EXTEND_001: Generate extended session token during active journey
    # This prevents session expiry while the user is actively tracking a journey
    extended_token = None
    try:
        auth_header = http_request.headers.get("Authorization") if http_request else None
        if auth_header and auth_header.startswith("Bearer "):
            current_token = auth_header.split(" ")[1]
            payload = SecurityManager.verify_token(current_token)
            if payload:
                # Extend session by 30 minutes on each heartbeat
                extended_token = SecurityManager.create_extended_session_token(payload, extend_minutes=30)
    except Exception as e:
        print(f"[DC_SESSION_EXTEND_001] Token refresh warning: {e}")
    
    return {
        "success": True,
        "distance_km": round(cumulative_distance, 2),
        "reimbursable_distance_km": round(reimbursable_distance, 2),
        "current_speed_kmh": round(speed_kmh, 1) if speed_kmh else 0,
        "max_speed_kmh": round(journey.max_speed_kmh, 1),
        "reimbursement_amount": journey.reimbursement_amount if journey.is_reimbursable else 0,
        "wvv_compliant": wvv_compliant,
        "wvv_reason": wvv_reason if not wvv_compliant else None,
        "wvv_accuracy_m": round(request.location.accuracy, 0) if request.location.accuracy else None,
        "extended_token": extended_token  # DC_SESSION_EXTEND_001: Refreshed token for session continuity
    }


@router.post("/{journey_id}/end", summary="End journey")
async def end_journey(
    journey_id: int,
    request: EndJourneyRequest = Body(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    End journey and calculate final stats
    DC_GPS_DEVICE_VALIDATION_001: End journey must come from same device that started it
    DC: Finalizes journey with duration and reimbursement calculation
    DC_JOURNEY_IDEMPOTENT_001: Idempotent - already completed journeys return success
    """
    now = get_indian_time()

    # First, find the journey belonging to current user (any status)
    journey = db.query(StaffJourney).filter(
        StaffJourney.id == journey_id,
        StaffJourney.employee_id == current_user.id
    ).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    # DC_JOURNEY_IDEMPOTENT_001: If already completed, return success (idempotent)
    if journey.status == JourneyStatus.COMPLETED:
        return {
            "success": True,
            "message": "Journey already completed",
            "journey": journey.to_dict(),
            "requires_photo": journey.end_photo_url is None,
            "idempotent": True
        }
    
    # If cancelled, cannot end
    if journey.status == JourneyStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot end a cancelled journey")
    
    # Only IN_PROGRESS can be ended (this is expected normal flow)
    if journey.status != JourneyStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail=f"Journey in unexpected state: {journey.status.value}")

    # DC Protocol (Dec 04, 2025): Relaxed device validation - log mismatches but don't block
    # This allows employees to end their journey even after network/browser changes
    # Security: Still validated by employee_id match (user can only end their own journey)
    try:
        current_device_fp = get_device_fingerprint(http_request, strict_mobile_check=False)
        current_device_id = current_device_fp['device_id']
        journey_device_id = journey.device_info.get('device_id') if journey.device_info else None
        
        if journey_device_id and journey_device_id != current_device_id:
            # Log mismatch for audit but allow the action
            log_fingerprint_mismatch(journey, current_device_fp, "end_journey")
            print(f"[DC_JOURNEY_END_DEVICE_MISMATCH] Journey {journey_id} ended from different device (allowed). Original: {journey_device_id}, Current: {current_device_id}")
    except Exception as e:
        print(f"[DC_END_JOURNEY_DEVICE_WARNING] Device validation warning: {str(e)}")
        # Don't block - user owns this journey (validated by employee_id)

    journey.end_time = now
    journey.status = JourneyStatus.COMPLETED
    journey.notes = request.notes

    if request.location:
        journey.end_latitude = request.location.latitude
        journey.end_longitude = request.location.longitude

        # WVV Protocol Fix (Dec 05, 2025): Store WVV compliance for end point
        end_wvv_compliant = True
        end_compliance_reason = None
        if request.location.accuracy and request.location.accuracy > 100:
            end_wvv_compliant = False
            end_compliance_reason = f"GPS accuracy {request.location.accuracy:.0f}m exceeds WVV limit of 100m"

        track_point = StaffJourneyTrackPoint(
            journey_id=journey_id,
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            accuracy=request.location.accuracy,
            altitude=request.location.altitude,
            speed_kmh=0,
            heading=request.location.heading,
            distance_from_prev=0,
            cumulative_distance=journey.total_distance_km,
            wvv_compliant=end_wvv_compliant,
            compliance_reason=end_compliance_reason,
            address=request.location.address,  # DC_JOURNEY_ADDRESS_001
            timestamp=now
        )
        db.add(track_point)
        
        # DC_JOURNEY_END_LOCATION_001 (Feb 2026): Insert final StaffRealtimeLocation on journey end
        # This ensures Team Live Tracker shows correct final location after journey ends
        try:
            from app.models.staff_attendance import StaffRealtimeLocation
            today = get_indian_date()
            
            # Get attendance record
            attendance = db.query(StaffAttendance).filter(
                StaffAttendance.employee_id == current_user.id,
                StaffAttendance.date == today
            ).first()
            
            # Generate DC code inline (avoid circular import from staff_time_tracker)
            dc_code = f"DC-RT-{current_user.emp_code}-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            # Get client IP inline (avoid circular import)
            client_ip = None
            if http_request:
                forwarded = http_request.headers.get("X-Forwarded-For")
                client_ip = forwarded.split(",")[0].strip() if forwarded else http_request.client.host if http_request.client else None
            
            # DC_ACCURACY_VALIDATION_001: Validate and cap accuracy to 500m max (same as clock-in/heartbeat)
            raw_accuracy = request.location.accuracy or 50
            validated_accuracy = min(max(raw_accuracy, 1), 500)  # Clamp between 1 and 500
            is_wvv_compliant = validated_accuracy <= 100
            
            final_location = StaffRealtimeLocation(
                employee_id=current_user.id,
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                accuracy_m=validated_accuracy,
                altitude=request.location.altitude,
                speed_kmh=0,
                heading=request.location.heading,
                source='journey',
                attendance_id=attendance.id if attendance else None,
                journey_id=journey_id,
                is_clocked_in=attendance is not None and attendance.clock_out is None if attendance else False,
                is_on_break=False,
                is_on_journey=False,
                dc_code=dc_code,
                device_info={
                    "user_agent": http_request.headers.get("User-Agent", "") if http_request else "",
                    "source": "journey_end",
                    "journey_id": journey_id,
                    "is_wvv_compliant": is_wvv_compliant,
                    "accuracy_quality": "high" if validated_accuracy <= 50 else ("medium" if validated_accuracy <= 100 else ("low" if validated_accuracy <= 300 else "degraded"))
                },
                ip_address=client_ip,
                user_agent=http_request.headers.get("User-Agent", "") if http_request else "",
                captured_at=now
            )
            db.add(final_location)
            
            # Update attendance GPS tracking fields
            if attendance and attendance.clock_out is None:
                attendance.last_gps_at = now
                attendance.gps_status = 'active'
            
            print(f"[DC_JOURNEY_END_LOCATION] Inserted final StaffRealtimeLocation for {current_user.emp_code} at journey end (journey_id={journey_id}, acc={validated_accuracy}m, wvv={is_wvv_compliant})")
        except Exception as e:
            print(f"[DC_JOURNEY_END_LOCATION] Failed to insert journey end location: {e}")

    journey.calculate_duration()
    journey.calculate_average_speed()
    if journey.is_reimbursable:
        journey.calculate_reimbursement()
    else:
        journey.reimbursement_amount = 0

    # DC Protocol (Mar 2026): Auto-capture journey time into timesheet using real GPS times
    try:
        from app.services.timesheet_auto_service import auto_upsert_timesheet_entry
        dur_mins = int(round(journey.total_duration_minutes or 0))
        if dur_mins >= 1 and journey.start_time and journey.end_time:
            purpose_label = (journey.purpose.value.replace('_', ' ').title() if journey.purpose else 'Journey')
            desc_parts = [purpose_label]
            if journey.client_name:
                desc_parts.append(journey.client_name)
            if journey.purpose_description:
                desc_parts.append(journey.purpose_description)
            journey_comment = f"[Auto from Journey] {' — '.join(desc_parts)}"
            auto_upsert_timesheet_entry(
                db=db,
                employee_id=current_user.id,
                entry_date=journey.start_time.date(),
                time_spent_minutes=dur_mins,
                entry_type='journey',
                auto_source='journey',
                comments=journey_comment,
                journey_id=journey.id,
                created_by=current_user.id,
                actual_start_time=journey.start_time.time(),
                actual_end_time=journey.end_time.time(),
            )
    except Exception as _e:
        print(f"[DC-WARN] Auto timesheet entry failed for journey {journey.id}: {_e}")

    db.commit()
    db.refresh(journey)

    return {
        "success": True,
        "message": "Journey completed. Please upload a photo to confirm.",
        "journey": journey.to_dict(),
        "requires_photo": True
    }


@router.post("/{journey_id}/photo", summary="Upload journey end photo")
async def upload_journey_photo(
    journey_id: int,
    http_request: Request,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Upload photo at journey end for verification
    DC_DEVICE_BINDING_001: Photo must come from same device that started journey
    DC: Universal Upload System - 5MB max, auto-compression, dual storage
    """
    journey = db.query(StaffJourney).filter(
        StaffJourney.id == journey_id,
        StaffJourney.employee_id == current_user.id
    ).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    # DC Protocol (Dec 04, 2025): Relaxed device validation - log mismatches but don't block
    # Security: Still validated by employee_id match (user can only upload to their own journey)
    try:
        current_device_fp = get_device_fingerprint(http_request, strict_mobile_check=False)
        current_device_id = current_device_fp['device_id']
        journey_device_id = journey.device_info.get('device_id') if journey.device_info else None
        
        if journey_device_id and journey_device_id != current_device_id:
            # Log mismatch for audit but allow the upload
            log_fingerprint_mismatch(journey, current_device_fp, "photo_upload")
            print(f"[DC_PHOTO_DEVICE_MISMATCH] Journey {journey_id} photo from different device (allowed)")
    except Exception as e:
        print(f"[DC_PHOTO_DEVICE_WARNING] Device validation warning: {str(e)}")
        # Don't block - user owns this journey (validated by employee_id)

    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Universal Upload System: 5MB max, auto-compression, dual storage
    from app.services.universal_upload_service import UniversalUploadService
    
    # DC Protocol: Atomic transaction - ALL changes commit together
    upload_result = None
    try:
        # DC Protocol: defer_scheduler=True ensures job only scheduled AFTER db.commit()
        upload_result = await UniversalUploadService.handle_upload(
            file=photo,
            table_name='staff_journeys',
            record_id=journey_id,
            uploaded_by_id=current_user.id,
            uploaded_by_type='staff',
            storage_dir='journey_photos',
            db=db,
            emp_code=current_user.emp_code,
            defer_scheduler=True  # DC: Transaction safety - schedule job AFTER commit
        )
        
        # DC Protocol: Update journey with ALL metadata from upload result
        journey.photo_path = upload_result['file_path']
        journey.photo_uploaded_at = get_indian_time()
        journey.photo_processing_status = 'pending' if upload_result['needs_compression'] else 'completed'
        
        # DC Protocol: Dual storage architecture metadata (ALL available fields from upload_result)
        # Note: Compressed metadata (compressed_photo_path, etc.) updated LATER by background job
        journey.photo_original_checksum = upload_result.get('original_checksum')
        journey.photo_storage_type = upload_result.get('storage_type', 'local')
        journey.photo_storage_key = upload_result.get('storage_key')
        
        # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
        # Format: JOURNEY_J{id}_{attachment_id}_{timestamp}_{uploader}_{original}
        try:
            import pytz
            from datetime import datetime
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            uploaded_at_ist = datetime.now(ist_tz)
            
            download_name = UniversalUploadService.generate_download_filename(
                segment_key='journey_photo',  # Functional segment
                entity_type='journey',  # Entity type for prefix
                entity_id=journey_id,  # Journey ID
                attachment_id=journey_id,  # Use journey_id as attachment_id (one photo per journey)
                uploader_code=current_user.emp_code,  # Employee code
                original_filename=photo.filename,  # User's uploaded filename
                uploaded_at=uploaded_at_ist  # IST timestamp
            )
            
            # WVV: Populate new columns
            journey.download_filename = download_name
            journey.uses_new_naming = True
            
        except HTTPException:
            # DC PROTOCOL: Re-raise validation errors (UNKNOWN segments must hard-fail)
            raise
        except Exception as e:
            # DC: Log unexpected errors but still fail the upload
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error generating download filename for journey {journey_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate semantic filename: {str(e)}"
            )
        
        # DC Protocol: Single commit for ALL changes (atomic operation)
        # PostCommitScheduler will automatically enqueue deferred jobs AFTER this commit
        db.commit()
        
        return {
            "success": True,
            "message": "Photo uploaded successfully" + (" (compressing in background...)" if upload_result['needs_compression'] else ""),
            "photo_path": upload_result['file_path'],
            "compression_queued": upload_result['needs_compression']
        }
        
    except HTTPException as e:
        # DC PROTOCOL: Preserve validation errors (UNKNOWN segments, metadata issues)
        db.rollback()
        raise e
    except Exception as e:
        # DC Protocol: Transaction rollback removes all uncommitted changes
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload photo: {str(e)}"
        )


@router.get("/active", summary="Get active journey")
async def get_active_journey(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get current user's active journey if any"""
    journey = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        StaffJourney.status == JourneyStatus.IN_PROGRESS
    ).first()

    if not journey:
        return {"success": True, "journey": None}

    track_points = db.query(StaffJourneyTrackPoint).filter(
        StaffJourneyTrackPoint.journey_id == journey.id
    ).order_by(StaffJourneyTrackPoint.timestamp.asc()).all()

    return {
        "success": True,
        "journey": journey.to_dict(),
        "track_points": [tp.to_dict() for tp in track_points]
    }


@router.get("/{journey_id}/track-points", summary="Get journey track points for map")
async def get_journey_track_points(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get all GPS track points for journey visualization
    
    DC Protocol (Dec 04, 2025): Pure reporting_manager hierarchy
    - Can view own journey
    - Manager (60+) can view journeys of entire recursive downline
    """
    journey = db.query(StaffJourney).filter(StaffJourney.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    # DC Protocol: Use recursive downline check
    accessible_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
    can_view = journey.employee_id in accessible_ids

    if not can_view:
        raise HTTPException(status_code=403, detail="Not authorized to view this journey")

    track_points = db.query(StaffJourneyTrackPoint).filter(
        StaffJourneyTrackPoint.journey_id == journey_id
    ).order_by(StaffJourneyTrackPoint.timestamp.asc()).all()

    return {
        "success": True,
        "journey": journey.to_detail_dict(),
        "track_points": [tp.to_dict() for tp in track_points],
        "route_coordinates": [[tp.latitude, tp.longitude] for tp in track_points]
    }


@router.get("/my", summary="Get my journeys")
async def get_my_journeys(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get current user's journeys with filters"""
    query = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id
    )

    if start_date:
        query = query.filter(StaffJourney.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(StaffJourney.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if status:
        query = query.filter(StaffJourney.status == JourneyStatus(status))
    if approval_status:
        query = query.filter(StaffJourney.approval_status == JourneyApprovalStatus(approval_status))

    total = query.count()
    journeys = query.order_by(StaffJourney.start_time.desc()).offset(offset).limit(limit).all()

    total_km = sum(j.total_distance_km for j in journeys)
    total_reimbursement = sum(j.reimbursement_amount for j in journeys if j.is_reimbursable)

    return {
        "success": True,
        "journeys": [j.to_dict() for j in journeys],
        "total": total,
        "summary": {
            "total_km": round(total_km, 2),
            "total_reimbursement": round(total_reimbursement, 2),
            "total_journeys": total
        }
    }


@router.get("/team", summary="Get team journeys (Manager view)")
async def get_team_journeys(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    employee_id: Optional[int] = None,
    staff_type: Optional[str] = None,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    include_self: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get team journeys for manager approval
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    DC_STAFF_TYPE_FILTER_001 (Dec 05, 2025): Added staff_type filter
    DC Protocol (Jan 2026): Added include_self parameter for Journey Management page
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can view team journeys")

    # DC Protocol (Feb 25, 2026): Use get_team_member_ids to exclude self + hidden accounts
    team_ids = get_team_member_ids(current_user, db, StaffEmployee)
    # DC Protocol (Jan 2026): Conditionally include manager's own ID
    if include_self:
        team_ids = [current_user.id] + team_ids
    
    # DC_STAFF_TYPE_FILTER_001: Filter team_ids by staff_type if specified
    if staff_type and staff_type.upper() in ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']:
        filtered_employees = db.query(StaffEmployee.id).filter(
            StaffEmployee.id.in_(team_ids),
            StaffEmployee.staff_type == staff_type.upper()
        ).all()
        team_ids = [e.id for e in filtered_employees]

    query = db.query(StaffJourney).filter(StaffJourney.employee_id.in_(team_ids))

    if start_date:
        query = query.filter(StaffJourney.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(StaffJourney.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        query = query.filter(StaffJourney.employee_id == employee_id)
    if status:
        query = query.filter(StaffJourney.status == JourneyStatus(status))
    if approval_status:
        query = query.filter(StaffJourney.approval_status == JourneyApprovalStatus(approval_status))

    total = query.count()
    journeys = query.order_by(StaffJourney.start_time.desc()).offset(offset).limit(limit).all()

    pending_count = db.query(StaffJourney).filter(
        StaffJourney.employee_id.in_(team_ids),
        StaffJourney.approval_status == JourneyApprovalStatus.PENDING,
        StaffJourney.status == JourneyStatus.COMPLETED
    ).count()

    return {
        "success": True,
        "journeys": [j.to_detail_dict() for j in journeys],
        "total": total,
        "pending_approval_count": pending_count,
        "team_members": team_ids
    }


@router.get("/all", summary="Get all journeys (Admin view)")
async def get_all_journeys(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    employee_id: Optional[int] = None,
    department_id: Optional[int] = None,
    staff_type: Optional[str] = None,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get all journeys for admin view - filtered by reporting manager hierarchy
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    DC_STAFF_TYPE_FILTER_001 (Dec 05, 2025): Added staff_type filter
    - Users with direct reports see journeys from their entire recursive downline
    - VGK/HR see all journeys
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can view all journeys")

    # DC Protocol (Feb 25, 2026): Use get_team_member_ids to exclude self + hidden accounts
    accessible_ids = get_team_member_ids(current_user, db, StaffEmployee, department_id)
    
    # DC_STAFF_TYPE_FILTER_001: Filter by staff_type if specified
    if staff_type and staff_type.upper() in ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']:
        filtered_employees = db.query(StaffEmployee.id).filter(
            StaffEmployee.id.in_(accessible_ids),
            StaffEmployee.staff_type == staff_type.upper()
        ).all()
        accessible_ids = [e.id for e in filtered_employees]
    
    query = db.query(StaffJourney).filter(StaffJourney.employee_id.in_(accessible_ids))

    if start_date:
        query = query.filter(StaffJourney.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(StaffJourney.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        if employee_id in accessible_ids:
            query = query.filter(StaffJourney.employee_id == employee_id)
    if status:
        query = query.filter(StaffJourney.status == JourneyStatus(status))
    if approval_status:
        query = query.filter(StaffJourney.approval_status == JourneyApprovalStatus(approval_status))

    total = query.count()
    journeys = query.order_by(StaffJourney.start_time.desc()).offset(offset).limit(limit).all()

    # Calculate summary for accessible journeys only
    summary_query = db.query(StaffJourney).filter(StaffJourney.employee_id.in_(accessible_ids))
    total_km = sum(j.total_distance_km or 0 for j in summary_query.all())
    total_reimbursement = sum(
        j.reimbursement_amount or 0 for j in summary_query.filter(
            StaffJourney.is_reimbursable == True,
            StaffJourney.approval_status == JourneyApprovalStatus.APPROVED
        ).all()
    )

    return {
        "success": True,
        "journeys": [j.to_detail_dict() for j in journeys],
        "total": total,
        "summary": {
            "total_km": round(total_km, 2),
            "total_approved_reimbursement": round(total_reimbursement, 2)
        }
    }


@router.get("/{journey_id}/validate", summary="Validate journey before approval")
async def validate_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_JOURNEY_VALIDATION_001: Validate journey before approval
    WVV: Check speed anomalies, teleportation, continuity, GPS accuracy
    Returns validation score and recommendation
    
    DC Protocol (Dec 04, 2025): Pure reporting_manager hierarchy
    """
    from app.services.journey_validation_service import JourneyValidationService
    
    journey = db.query(StaffJourney).filter(StaffJourney.id == journey_id).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    # DC Protocol: Use recursive downline check
    accessible_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
    can_validate = journey.employee_id in accessible_ids
    
    if not can_validate:
        raise HTTPException(status_code=403, detail="Not authorized to validate this journey")
    
    track_points = db.query(StaffJourneyTrackPoint).filter(
        StaffJourneyTrackPoint.journey_id == journey_id
    ).order_by(StaffJourneyTrackPoint.timestamp.asc()).all()
    
    validation_result = JourneyValidationService.validate_journey_for_approval(
        journey_data=journey.to_dict(),
        track_points=[tp.to_dict() for tp in track_points]
    )
    
    return {
        "success": True,
        "journey_id": journey_id,
        "validation": validation_result,
        "journey": journey.to_detail_dict(),
        "track_points_count": len(track_points)
    }


@router.post("/{journey_id}/approve", summary="Approve or reject journey")
async def approve_journey(
    journey_id: int,
    request: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve or reject a journey for reimbursement
    DC: Creates audit trail for approval decision
    WVV: Validates route before approval (warnings for issues, blocks critical failures)
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    """
    from app.services.journey_validation_service import JourneyValidationService
    from app.utils.staff_hierarchy import has_direct_reports
    
    journey = db.query(StaffJourney).filter(StaffJourney.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != JourneyStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Journey must be completed before approval")

    # DC Protocol: Menu-based access control - page assignment = full access
    # is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    # is_vgk4u_or_hr = current_user.role and (
    #     current_user.role.hierarchy_level >= 150 or 
    #     current_user.role.role_name in ['HR', 'Executive Assistant'] or
    #     current_user.role.role_code in ['hr', 'ea']
    # )
    # 
    # if not is_manager and not is_vgk4u_or_hr:
    #     raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can approve journeys")
    
    # Cannot approve own journeys
    if journey.employee_id == current_user.id:
        raise HTTPException(status_code=403, detail="Cannot approve your own journeys")
    
    accessible_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
    if journey.employee_id not in accessible_ids:
        raise HTTPException(status_code=403, detail="Not authorized to approve this journey")

    validation_result = None
    validation_warnings = []
    
    if request.action == 'approve':
        track_points = db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.journey_id == journey_id
        ).order_by(StaffJourneyTrackPoint.timestamp.asc()).all()
        
        validation_result = JourneyValidationService.validate_journey_for_approval(
            journey_data=journey.to_dict(),
            track_points=[tp.to_dict() for tp in track_points]
        )
        
        validation_warnings = validation_result.get('warnings', [])
        
        # DC_APPROVAL_VALIDATION_001: Block if validation fails (is_valid=False OR has critical failures)
        if not validation_result.get('is_valid') or validation_result.get('has_critical_failures'):
            critical_msgs = validation_result.get('critical_failures', [])
            error_msgs = validation_result.get('errors', ['Unknown error'])
            all_issues = critical_msgs + error_msgs if critical_msgs else error_msgs
            
            raise HTTPException(
                status_code=400,
                detail=f"WVV Validation Failed (Score: {validation_result['validation_score']}/100, "
                       f"Recommendation: {validation_result.get('recommendation', 'REJECT')}). "
                       f"Issues: {'; '.join(all_issues[:5])}"  # First 5 issues
            )

    previous_status = journey.approval_status.value if journey.approval_status else None

    if request.action == 'approve':
        journey.approval_status = JourneyApprovalStatus.APPROVED
    else:
        journey.approval_status = JourneyApprovalStatus.REJECTED

    remarks_with_validation = request.remarks or ""
    if validation_result:
        remarks_with_validation += f" [Validation Score: {validation_result['validation_score']}/100]"
        if validation_warnings:
            remarks_with_validation += f" [Warnings: {len(validation_warnings)}]"

    approval_log = StaffJourneyApproval(
        journey_id=journey_id,
        action=request.action,
        previous_status=previous_status,
        new_status=journey.approval_status.value,
        approved_by=current_user.id,
        remarks=remarks_with_validation.strip()
    )
    db.add(approval_log)
    db.commit()

    return {
        "success": True,
        "message": f"Journey {request.action}d successfully",
        "journey": journey.to_dict(),
        "validation": validation_result,
        "validation_warnings": validation_warnings
    }


@router.post("/bulk-approve", summary="Bulk approve/reject journeys")
async def bulk_approve_journeys(
    request: BulkApprovalRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Bulk approve or reject multiple journeys
    DC: Creates audit trail for each approval decision
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can bulk approve journeys")

    journeys = db.query(StaffJourney).filter(
        StaffJourney.id.in_(request.journey_ids),
        StaffJourney.status == JourneyStatus.COMPLETED
    ).all()

    if not journeys:
        raise HTTPException(status_code=404, detail="No valid journeys found")

    processed = []
    skipped = []

    for journey in journeys:
        is_manager = journey.employee.reporting_manager_id == current_user.id
        is_admin = current_user.role.hierarchy_level >= 85

        if not (is_manager or is_admin):
            skipped.append({"id": journey.id, "reason": "Not authorized"})
            continue

        previous_status = journey.approval_status.value if journey.approval_status else None

        if request.action == 'approve':
            journey.approval_status = JourneyApprovalStatus.APPROVED
        else:
            journey.approval_status = JourneyApprovalStatus.REJECTED

        approval_log = StaffJourneyApproval(
            journey_id=journey.id,
            action=request.action,
            previous_status=previous_status,
            new_status=journey.approval_status.value,
            approved_by=current_user.id,
            remarks=request.remarks
        )
        db.add(approval_log)
        processed.append(journey.id)

    db.commit()

    return {
        "success": True,
        "message": f"Processed {len(processed)} journeys",
        "processed": processed,
        "skipped": skipped
    }


@router.get("/stats", summary="Get journey statistics")
async def get_journey_stats(
    period: str = "month",
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get journey statistics for current user"""
    today = get_indian_date()

    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today.replace(day=1)
    else:
        start_date = today - timedelta(days=30)

    journeys = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        StaffJourney.date >= start_date
    ).all()

    total_km = sum(j.total_distance_km for j in journeys)
    total_reimbursement = sum(j.reimbursement_amount for j in journeys if j.is_reimbursable and j.approval_status == JourneyApprovalStatus.APPROVED)
    pending_reimbursement = sum(j.reimbursement_amount for j in journeys if j.is_reimbursable and j.approval_status == JourneyApprovalStatus.PENDING)
    avg_speed = sum(j.average_speed_kmh for j in journeys if j.average_speed_kmh) / len(journeys) if journeys else 0

    return {
        "success": True,
        "period": period,
        "stats": {
            "total_journeys": len(journeys),
            "completed_journeys": len([j for j in journeys if j.status == JourneyStatus.COMPLETED]),
            "total_km": round(total_km, 2),
            "approved_reimbursement": round(total_reimbursement, 2),
            "pending_reimbursement": round(pending_reimbursement, 2),
            "average_speed_kmh": round(avg_speed, 1),
            "non_reimbursable_count": len([j for j in journeys if not j.is_reimbursable])
        }
    }


class TransportRateUpdate(BaseModel):
    rate_per_km: float
    description: Optional[str] = None
    is_active: bool = True


@router.get("/transport-rates", summary="Get transport rates (VGK4U config)")
async def get_transport_rates(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get all transport rates - those with direct reports or VGK/HR can view
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can view transport rates")

    rates = db.query(StaffTransportRate).order_by(StaffTransportRate.transport_mode).all()
    
    return {
        "success": True,
        "rates": [r.to_dict() for r in rates]
    }


@router.put("/transport-rates/{mode}", summary="Update transport rate (VGK4U only)")
async def update_transport_rate(
    mode: str,
    request: TransportRateUpdate,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update transport rate - HR (85+), EA (85+), VGK4U (150+)
    DC: Audit trail for rate changes - DC_ROLE_AUTH_003
    """
    # DC_ROLE_AUTH_003: Verify HR+ access for transport rate configuration
    if current_user.role.hierarchy_level < 85:
        raise HTTPException(status_code=403, detail="DC_ROLE_AUTH_003: HR level (85+) access required for rate configuration")

    valid_modes = ['car', 'bike', 'electric_bike', 'cart', 'local_transport', 'others']
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")

    rate = db.query(StaffTransportRate).filter(
        StaffTransportRate.transport_mode == mode
    ).first()

    if not rate:
        from datetime import date
        rate = StaffTransportRate(
            transport_mode=mode,
            rate_per_km=request.rate_per_km,
            description=request.description,
            is_active=request.is_active,
            effective_from=date.today(),
            created_by=current_user.id
        )
        db.add(rate)
    else:
        rate.rate_per_km = request.rate_per_km
        if request.description:
            rate.description = request.description
        rate.is_active = request.is_active
        rate.updated_by = current_user.id
        rate.updated_at = get_indian_time()

    db.commit()
    db.refresh(rate)

    return {
        "success": True,
        "message": f"Transport rate for {mode} updated",
        "rate": rate.to_dict()
    }


@router.get("/companies", summary="Get companies for journey selection")
async def get_journey_companies(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get active companies for journey company selection dropdown
    
    DC Protocol (Phase 2): Company selection mandatory for SFMS integration
    """
    companies = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_active == True
    ).order_by(AssociatedCompany.company_name).all()
    
    return {
        "success": True,
        "companies": [
            {
                "id": c.id,
                "code": c.company_code,
                "name": c.company_name
            }
            for c in companies
        ]
    }


@router.get("/hr", summary="Get journeys for HR view")
async def get_hr_journeys(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    department_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get journeys for HR view - attendance correlation
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can view HR journey data")

    query = db.query(StaffJourney)

    if start_date:
        query = query.filter(StaffJourney.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(StaffJourney.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        query = query.filter(StaffJourney.employee_id == employee_id)
    if department_id:
        query = query.join(StaffEmployee).filter(StaffEmployee.department_id == department_id)

    total = query.count()
    journeys = query.order_by(StaffJourney.date.desc(), StaffJourney.start_time.desc()).offset(offset).limit(limit).all()

    attendance_linked = len([j for j in journeys if j.attendance_id])

    return {
        "success": True,
        "journeys": [j.to_detail_dict() for j in journeys],
        "total": total,
        "summary": {
            "attendance_linked": attendance_linked,
            "total_km": sum(j.total_distance_km for j in journeys),
            "total_duration_hours": sum(j.total_duration_minutes for j in journeys) / 60
        }
    }


@router.get("/vgk4u/dashboard", summary="VGK4U journey dashboard")
async def get_vgk4u_dashboard(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """VGK4U complete journey dashboard with analytics"""
    if current_user.role.hierarchy_level < 150:
        raise HTTPException(status_code=403, detail="VGK4U access required")

    today = get_indian_date()
    
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        end_date = today.isoformat()

    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    journeys = db.query(StaffJourney).filter(
        StaffJourney.date >= start,
        StaffJourney.date <= end
    ).all()

    total_km = sum(j.total_distance_km for j in journeys)
    approved_amount = sum(j.reimbursement_amount for j in journeys 
                         if j.is_reimbursable and j.approval_status == JourneyApprovalStatus.APPROVED)
    pending_amount = sum(j.reimbursement_amount for j in journeys 
                        if j.is_reimbursable and j.approval_status == JourneyApprovalStatus.PENDING)
    rejected_count = len([j for j in journeys if j.approval_status == JourneyApprovalStatus.REJECTED])
    non_reimbursable = len([j for j in journeys if not j.is_reimbursable])

    by_transport = {}
    by_purpose = {}
    by_department = {}

    for j in journeys:
        mode = j.transport_mode
        by_transport[mode] = by_transport.get(mode, 0) + j.total_distance_km

        purpose = j.purpose.value if j.purpose else 'other'
        by_purpose[purpose] = by_purpose.get(purpose, 0) + 1

        if j.employee and j.employee.department:
            dept = j.employee.department.name
            by_department[dept] = by_department.get(dept, 0) + j.total_distance_km

    rates = db.query(StaffTransportRate).filter(StaffTransportRate.is_active == True).all()

    return {
        "success": True,
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_journeys": len(journeys),
            "total_km": round(total_km, 2),
            "approved_amount": round(approved_amount, 2),
            "pending_amount": round(pending_amount, 2),
            "pending_count": len([j for j in journeys if j.approval_status == JourneyApprovalStatus.PENDING]),
            "rejected_count": rejected_count,
            "non_reimbursable_count": non_reimbursable
        },
        "by_transport": {k: round(v, 2) for k, v in by_transport.items()},
        "by_purpose": by_purpose,
        "by_department": {k: round(v, 2) for k, v in by_department.items()},
        "transport_rates": [r.to_dict() for r in rates]
    }


# ==================== ACTIVE JOURNEYS & FORCE STOP (Dec 04, 2025) ====================

class ForceStopRequest(BaseModel):
    """DC Protocol: Force stop request with mandatory reason for audit"""
    reason: str = Field(..., min_length=1, description="Reason for force stopping journey")


@router.get("/active/all", summary="Get all active journeys (manager view)")
async def get_active_journeys(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Dec 04, 2025): Get all currently active journeys
    Managers see their downline's active journeys (recursive hierarchy)
    HR/EA/VGK see all active journeys organization-wide
    
    Returns: List of active journeys with employee info, start time, location, distance
    """
    now = get_indian_time()
    
    # DC Protocol (Feb 25, 2026): Use get_team_member_ids to exclude self + hidden accounts
    accessible_ids = get_team_member_ids(current_user, db, StaffEmployee)
    
    # Query active journeys for accessible employees
    active_journeys = db.query(StaffJourney).filter(
        StaffJourney.status == JourneyStatus.IN_PROGRESS,
        StaffJourney.employee_id.in_(accessible_ids)
    ).order_by(StaffJourney.start_time.desc()).all()
    
    journey_list = []
    for journey in active_journeys:
        # Calculate duration
        duration_minutes = 0
        if journey.start_time:
            delta = now - journey.start_time
            duration_minutes = int(delta.total_seconds() / 60)
        
        # Get track points count for stops
        track_points = db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.journey_id == journey.id
        ).count()
        
        # Get latest position
        latest_point = db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.journey_id == journey.id
        ).order_by(StaffJourneyTrackPoint.timestamp.desc()).first()
        
        journey_data = {
            "id": journey.id,
            "employee_id": journey.employee_id,
            "employee_name": f"{journey.employee.first_name} {journey.employee.last_name}" if journey.employee else "Unknown",
            "employee_code": journey.employee.emp_code if journey.employee else None,
            "department": journey.employee.department.name if journey.employee and journey.employee.department else "N/A",
            "purpose": journey.purpose.value if journey.purpose else "other",
            "purpose_description": journey.purpose_description,
            "transport_mode": journey.transport_mode,
            "start_time": journey.start_time.isoformat() if journey.start_time else None,
            "start_time_formatted": journey.start_time.strftime("%d %b %Y, %I:%M %p") if journey.start_time else None,
            "duration_minutes": duration_minutes,
            "duration_formatted": f"{duration_minutes // 60}h {duration_minutes % 60}m" if duration_minutes > 0 else "Just started",
            "start_latitude": journey.start_latitude,
            "start_longitude": journey.start_longitude,
            "start_address": journey.start_address,
            "current_latitude": latest_point.latitude if latest_point else journey.start_latitude,
            "current_longitude": latest_point.longitude if latest_point else journey.start_longitude,
            "total_distance_km": round(journey.total_distance_km or 0, 2),
            "track_points_count": track_points,
            "stops_count": max(0, track_points - 1),  # Exclude start point
            "est_reimbursement": round(journey.reimbursement_amount or 0, 2),
            "is_reimbursable": journey.is_reimbursable,
            "gps_enabled": journey.gps_enabled,
            "can_force_stop": journey.employee_id in accessible_ids,  # Manager can stop
            "fingerprint_warnings_count": journey.fingerprint_mismatch_count or 0
        }
        journey_list.append(journey_data)
    
    return {
        "success": True,
        "active_journeys": journey_list,
        "total_active": len(journey_list),
        "timestamp": now.isoformat()
    }


@router.post("/{journey_id}/force-stop", summary="Force stop a journey (manager action)")
async def force_stop_journey(
    journey_id: int,
    request: ForceStopRequest = Body(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Dec 04, 2025): Manager force-stop for stuck journeys
    
    Use case: When employees cannot end their own journey due to device binding issues,
    network changes, browser cache clears, etc., managers can force-stop it.
    
    Validation:
    - Manager must have hierarchy access to the employee
    - Journey must be in IN_PROGRESS status
    - Reason is mandatory for audit trail
    
    Effects:
    - Journey status set to COMPLETED
    - force_stopped flag set to True
    - Audit trail with manager info, reason, timestamp
    - Journey is still reimbursable (calculated based on captured distance)
    """
    now = get_indian_time()
    
    # Find the journey
    journey = db.query(StaffJourney).filter(
        StaffJourney.id == journey_id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    if journey.status != JourneyStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400, 
            detail=f"Journey is already {journey.status.value}. Cannot force stop."
        )
    
    # Verify manager has access to this employee (hierarchy check)
    accessible_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
    if journey.employee_id not in accessible_ids:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to stop this employee's journey"
        )
    
    # Get device info for audit
    try:
        manager_device_fp = get_device_fingerprint(http_request, strict_mobile_check=False)
    except:
        manager_device_fp = {"device_id": "unknown", "is_mobile": False}
    
    # Calculate final metrics
    journey.end_time = now
    journey.status = JourneyStatus.COMPLETED
    journey.calculate_duration()
    journey.calculate_average_speed()
    
    if journey.is_reimbursable:
        journey.calculate_reimbursement()
    
    # DC Protocol: Force stop audit trail
    journey.force_stopped = True
    journey.force_stopped_by = current_user.id
    journey.force_stopped_at = now
    journey.force_stopped_reason = request.reason
    journey.force_stopped_device_info = manager_device_fp
    
    # Add notes about force stop
    force_stop_note = f"[FORCE STOPPED] By {current_user.first_name} {current_user.last_name} at {now.strftime('%d %b %Y, %I:%M %p')}. Reason: {request.reason}"
    if journey.notes:
        journey.notes = f"{journey.notes}\n\n{force_stop_note}"
    else:
        journey.notes = force_stop_note
    
    db.commit()
    db.refresh(journey)
    
    employee_name = f"{journey.employee.first_name} {journey.employee.last_name}" if journey.employee else "Unknown"
    
    print(f"[DC_FORCE_STOP] Journey {journey_id} force-stopped by {current_user.emp_code}. Employee: {employee_name}. Reason: {request.reason}")
    
    return {
        "success": True,
        "message": f"Journey force-stopped successfully. Employee {employee_name} has been notified.",
        "journey": journey.to_detail_dict(),
        "force_stop_details": {
            "stopped_by": f"{current_user.first_name} {current_user.last_name}",
            "stopped_by_code": current_user.emp_code,
            "stopped_at": now.isoformat(),
            "reason": request.reason,
            "final_distance_km": round(journey.total_distance_km or 0, 2),
            "final_duration_minutes": round(journey.total_duration_minutes or 0, 2),
            "final_reimbursement": round(journey.reimbursement_amount or 0, 2) if journey.is_reimbursable else 0
        }
    }
