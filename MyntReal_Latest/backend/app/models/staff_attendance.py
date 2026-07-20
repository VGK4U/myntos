"""
Staff Attendance & Time Tracker Models (DC Protocol Compliant)
Single source of truth for attendance and time tracking

Tables:
- staff_attendance: Daily punch records (clock-in/out)
- staff_attendance_breaks: Break intervals

Key Features:
- Daily clock in/out with timestamp capture
- Location tracking (office/WFH/field)
- Break management (paid/unpaid)
- Auto-calculation of worked hours
- Immutable audit trail

Created: Nov 26, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text, 
    ForeignKey, CheckConstraint, Index, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import pytz

from app.models.base import Base


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


def get_indian_date():
    """Get current date in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


class StaffAttendance(Base):
    """
    Daily Attendance Record
    DC: Single source of truth for daily punch data
    WVV: One record per employee per date
    """
    __tablename__ = 'staff_attendance'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    clock_in = Column(DateTime, nullable=True)
    clock_out = Column(DateTime, nullable=True)
    
    clock_in_location = Column(JSONB, nullable=True)
    clock_out_location = Column(JSONB, nullable=True)
    
    location_mode = Column(String(16), default='office')
    
    worked_minutes = Column(Integer, default=0)
    break_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    
    status = Column(String(32), default='absent')
    
    approval_status = Column(String(32), default='pending')
    
    field_session_id = Column(Integer, nullable=True)
    
    gps_permission_status = Column(String(32), default='granted')
    total_gps_off_minutes = Column(Integer, default=0)
    
    # DC Protocol (Jan 28, 2026): Real-time GPS status tracking for Team Live Tracker
    # Tracks current GPS status and reason when tracking stops
    gps_status = Column(String(32), default='active')  # active, permission_denied, gps_disabled, network_error, app_background, location_timeout
    gps_status_reason = Column(String(128), nullable=True)  # Human-readable reason
    gps_status_at = Column(DateTime, nullable=True)  # When status changed
    last_gps_at = Column(DateTime, nullable=True)  # Last successful GPS update
    last_battery_pct = Column(Integer, nullable=True)  # Last known battery percentage (0-100)
    
    # Location Drift Tracking Summary (WVV Protocol)
    location_change_count = Column(Integer, default=0)  # Times location changed (≥200m)
    unique_locations_count = Column(Integer, default=0)  # Distinct locations visited
    total_distance_meters = Column(Numeric(10, 2), default=0)  # Total distance traveled
    
    clock_in_device = Column(JSONB, nullable=True)
    clock_out_device = Column(JSONB, nullable=True)
    
    # DC_PHOTO_VIEW_001 (Dec 05, 2025): WVV Protocol photo verification fields
    clock_in_photo_path = Column(String(512), nullable=True)
    clock_out_photo_path = Column(String(512), nullable=True)
    clock_in_photo_uploaded_at = Column(DateTime, nullable=True)
    clock_out_photo_uploaded_at = Column(DateTime, nullable=True)
    
    remarks = Column(Text, nullable=True)
    
    is_auto_closed = Column(Boolean, default=False)
    auto_closed_at = Column(DateTime, nullable=True)
    
    activity_minutes_total = Column(Integer, default=0, nullable=False)
    kra_minutes = Column(Integer, default=0, nullable=False)
    task_minutes = Column(Integer, default=0, nullable=False)
    dayplan_minutes = Column(Integer, default=0, nullable=False)
    lead_minutes = Column(Integer, default=0, nullable=False)
    ticket_minutes = Column(Integer, default=0, nullable=False)
    journey_minutes = Column(Integer, default=0, nullable=False)
    custom_minutes = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_attendance_emp_date', 'employee_id', 'date', unique=True),
        CheckConstraint(
            "location_mode IN ('office', 'wfh', 'field', 'hybrid')",
            name='staff_attendance_location_mode_check'
        ),
        CheckConstraint(
            "status IN ('absent', 'present', 'half_day', 'on_leave', 'holiday', 'weekend')",
            name='staff_attendance_status_check'
        ),
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'auto_approved', 'revision_requested')",
            name='staff_attendance_approval_status_check'
        ),
        CheckConstraint(
            "gps_status IN ('active', 'permission_denied', 'gps_disabled', 'network_error', 'app_background', 'location_timeout')",
            name='staff_attendance_gps_status_check'
        ),
        Index('idx_attendance_date', 'date'),
        Index('idx_attendance_status', 'status'),
        Index('idx_attendance_approval', 'approval_status'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    breaks = relationship("StaffAttendanceBreak", back_populates="attendance", cascade="all, delete-orphan", order_by="StaffAttendanceBreak.break_start")
    evidence_entries = relationship("StaffAttendanceEvidence", back_populates="attendance", cascade="all, delete-orphan", order_by="StaffAttendanceEvidence.captured_at")
    
    def calculate_worked_time(self):
        """
        Calculate total worked minutes excluding breaks
        DC: Auto-compute when clock_out is set
        """
        if not self.clock_in or not self.clock_out:
            return 0
        
        total_minutes = int((self.clock_out - self.clock_in).total_seconds() / 60)
        
        break_mins = sum(b.duration_minutes or 0 for b in self.breaks if b.break_end)
        
        worked = max(0, total_minutes - break_mins)
        return worked
    
    def calculate_overtime(self, standard_hours=8):
        """
        Calculate overtime minutes beyond standard hours
        DC: Standard workday is 8 hours
        """
        if not self.worked_minutes:
            return 0
        
        standard_minutes = standard_hours * 60
        if self.worked_minutes > standard_minutes:
            return self.worked_minutes - standard_minutes
        return 0
    
    def update_status(self):
        """
        Update attendance status based on worked hours
        DC: Auto-determine status
        """
        if not self.clock_in:
            self.status = 'absent'
        elif self.worked_minutes >= 240:
            if self.worked_minutes >= 400:
                self.status = 'present'
            else:
                self.status = 'half_day'
        else:
            self.status = 'half_day'
    
    def to_dict(self, include_breaks=True, include_field_work=False):
        data = {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "date": self.date.isoformat() if self.date else None,
            "clock_in": self.clock_in.isoformat() if self.clock_in else None,
            "clock_out": self.clock_out.isoformat() if self.clock_out else None,
            "clock_in_time": self.clock_in.strftime("%H:%M") if self.clock_in else None,
            "clock_out_time": self.clock_out.strftime("%H:%M") if self.clock_out else None,
            "clock_in_location": self.clock_in_location,
            "clock_out_location": self.clock_out_location,
            "location_mode": self.location_mode,
            "worked_minutes": self.worked_minutes or 0,
            "worked_hours": round((self.worked_minutes or 0) / 60, 2),
            "break_minutes": self.break_minutes or 0,
            "overtime_minutes": self.overtime_minutes or 0,
            "overtime_hours": round((self.overtime_minutes or 0) / 60, 2),
            "status": self.status,
            "approval_status": self.approval_status or 'pending',
            "gps_permission_status": self.gps_permission_status or 'granted',
            "total_gps_off_minutes": self.total_gps_off_minutes or 0,
            "field_session_id": self.field_session_id,
            "remarks": self.remarks,
            "is_auto_closed": self.is_auto_closed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_clocked_in": self.clock_in is not None and self.clock_out is None,
            "is_complete": self.clock_in is not None and self.clock_out is not None,
            "is_field_work": self.location_mode == 'field',
            "location_change_count": self.location_change_count or 0,
            "unique_locations_count": self.unique_locations_count or 0,
            "total_distance_meters": float(self.total_distance_meters) if self.total_distance_meters else 0,
            "total_distance_km": round(float(self.total_distance_meters or 0) / 1000, 2),
            "clock_in_photo_url": f"/storage/{self.clock_in_photo_path}" if self.clock_in_photo_path else None,
            "clock_out_photo_url": f"/storage/{self.clock_out_photo_path}" if self.clock_out_photo_path else None,
            "clock_in_photo_time": self.clock_in_photo_uploaded_at.isoformat() if self.clock_in_photo_uploaded_at else None,
            "clock_out_photo_time": self.clock_out_photo_uploaded_at.isoformat() if self.clock_out_photo_uploaded_at else None,
            "has_photos": bool(self.clock_in_photo_path or self.clock_out_photo_path),
            "activity_minutes_total": self.activity_minutes_total or 0,
            "kra_minutes": self.kra_minutes or 0,
            "task_minutes": self.task_minutes or 0,
            "dayplan_minutes": self.dayplan_minutes or 0,
            "lead_minutes": self.lead_minutes or 0,
            "ticket_minutes": self.ticket_minutes or 0,
            "journey_minutes": self.journey_minutes or 0,
            "custom_minutes": self.custom_minutes or 0,
            "activity_hours": round((self.activity_minutes_total or 0) / 60, 2)
        }
        
        if include_breaks and self.breaks:
            data["breaks"] = [b.to_dict() for b in self.breaks]
            data["total_break_count"] = len(self.breaks)
        else:
            data["breaks"] = []
            data["total_break_count"] = 0
        
        return data


class StaffAttendanceBreak(Base):
    """
    Break Intervals during work day
    DC: Track paid/unpaid breaks with type reference
    WVV: Break must be within attendance clock_in and clock_out
    
    Updated: Nov 29, 2025 - Added break_type_id for type reference
    """
    __tablename__ = 'staff_attendance_breaks'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    
    break_start = Column(DateTime, nullable=False)
    break_end = Column(DateTime, nullable=True)
    
    # Legacy break_type field (kept for backward compatibility)
    break_type = Column(String(32), default='other')
    # New: Reference to StaffBreakType for standardized break types
    break_type_id = Column(Integer, ForeignKey('staff_break_types.id', ondelete='SET NULL'), nullable=True, index=True)
    is_paid = Column(Boolean, default=True)
    
    duration_minutes = Column(Integer, nullable=True)
    
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "break_type IN ('lunch', 'tea', 'personal', 'meeting', 'client_visit', 'travel', 'emergency', 'other')",
            name='staff_break_type_check'
        ),
        Index('idx_staff_break_type_id', 'break_type_id'),
    )
    
    attendance = relationship("StaffAttendance", back_populates="breaks")
    break_type_ref = relationship("StaffBreakType", foreign_keys=[break_type_id])
    evidence_entries = relationship("StaffAttendanceEvidence", back_populates="break_record", cascade="all, delete-orphan")
    
    def calculate_duration(self):
        """Calculate break duration in minutes"""
        if self.break_start and self.break_end:
            delta = self.break_end - self.break_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def to_dict(self, include_evidence=False):
        data = {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "break_start": self.break_start.isoformat() if self.break_start else None,
            "break_end": self.break_end.isoformat() if self.break_end else None,
            "break_start_time": self.break_start.strftime("%H:%M") if self.break_start else None,
            "break_end_time": self.break_end.strftime("%H:%M") if self.break_end else None,
            "break_type": self.break_type,
            "break_type_id": self.break_type_id,
            "break_type_name": self.break_type_ref.name if self.break_type_ref else self.break_type.replace('_', ' ').title(),
            "is_paid": self.is_paid,
            "duration_minutes": self.duration_minutes or self.calculate_duration(),
            "remarks": self.remarks,
            "is_active": self.break_start is not None and self.break_end is None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_evidence and hasattr(self, 'evidence_entries') and self.evidence_entries:
            data["evidence"] = [e.to_dict() for e in self.evidence_entries]
        
        return data


class StaffAttendanceLog(Base):
    """
    Attendance Activity Audit Trail (Immutable)
    DC: Complete history of all attendance actions
    """
    __tablename__ = 'staff_attendance_log'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    action = Column(String(64), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    device_info = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('clock_in', 'clock_out', 'break_start', 'break_end', 'auto_closed', 'manual_update', 'location_updated', 'admin_clock_out')",
            name='staff_attendance_log_action_check'
        ),
    )
    
    attendance = relationship("StaffAttendance", foreign_keys=[attendance_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else "System",
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def log_attendance_activity(db, attendance_id, employee_id, action, details=None, ip_address=None, device_info=None):
    """
    Helper function to create attendance activity log entries
    DC: Ensures consistent audit logging across all attendance operations
    """
    log = StaffAttendanceLog(
        attendance_id=attendance_id,
        employee_id=employee_id,
        action=action,
        details=details,
        ip_address=ip_address,
        device_info=device_info
    )
    db.add(log)
    return log


# ============================================================================
# ATTENDANCE EVIDENCE SYSTEM - WVV & DC Protocol Compliant
# Created: Nov 29, 2025
# Purpose: Photo + GPS evidence capture for clock-in/clock-out/breaks
# ============================================================================

class StaffBreakType(Base):
    """
    Break Type Reference Table
    DC: Standardized break categories with duration limits
    WVV: Used for break type selection during break start
    
    Created: Nov 29, 2025
    """
    __tablename__ = 'staff_break_types'
    
    id = Column(Integer, primary_key=True, index=True)
    break_code = Column(String(32), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    max_duration_minutes = Column(Integer, nullable=True)  # NULL = no limit
    is_paid = Column(Boolean, nullable=False, default=True)
    requires_evidence = Column(Boolean, nullable=False, default=False)  # Require photo for this break type
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=100)
    
    # DC: Audit fields
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    updated_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_staff_break_types_active_order', 'is_active', 'display_order'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "break_code": self.break_code,
            "name": self.name,
            "description": self.description,
            "max_duration_minutes": self.max_duration_minutes,
            "is_paid": self.is_paid,
            "requires_evidence": self.requires_evidence,
            "is_active": self.is_active,
            "display_order": self.display_order,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffAttendanceEvidence(Base):
    """
    Attendance Evidence Records (Photos + GPS)
    DC: Immutable evidence storage for clock-in/out/breaks
    WVV: Validates work presence with photo + location
    
    Evidence Types:
    - clock_in: Photo + GPS when clocking in
    - clock_out: Photo + GPS when clocking out
    - break_start: Optional photo when starting a break
    - break_end: Optional photo when ending a break
    
    Created: Nov 29, 2025
    """
    __tablename__ = 'staff_attendance_evidence'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    break_id = Column(Integer, ForeignKey('staff_attendance_breaks.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Evidence type
    event_type = Column(String(32), nullable=False, index=True)  # clock_in, clock_out, break_start, break_end
    captured_at = Column(DateTime, nullable=False, default=get_indian_time)
    
    # Photo evidence (Universal Upload System integration)
    photo_path = Column(String(512), nullable=False)  # Storage path
    photo_filename = Column(String(256), nullable=True)  # Original filename
    download_filename = Column(String(255), nullable=True)  # DC: Semantic filename for downloads
    uses_new_naming = Column(Boolean, default=True, nullable=False)  # DC: Uses new naming convention
    
    # GPS Location evidence
    gps_latitude = Column(Numeric(10, 7), nullable=False)  # Precision to ~1cm
    gps_longitude = Column(Numeric(10, 7), nullable=False)
    gps_accuracy_m = Column(Numeric(8, 2), nullable=True)  # Accuracy in meters
    gps_altitude = Column(Numeric(10, 2), nullable=True)  # Altitude if available
    
    # Location metadata (reverse geocoding, etc.)
    location_address = Column(Text, nullable=True)  # Human-readable address
    location_meta = Column(JSONB, nullable=True)  # Additional location data
    
    # Device info
    device_info = Column(JSONB, nullable=True)  # Browser, OS, device type
    
    # DC_PHOTO_TIMESTAMP_001: Photo metadata with timestamp and face detection
    timestamp_overlay = Column(Boolean, default=True, nullable=False)  # Photo has IST timestamp overlay
    face_detected = Column(Boolean, default=False, nullable=False)  # Human face detected
    face_confidence = Column(Integer, default=0, nullable=False)  # Face detection confidence 0-100
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # DC: Audit fields
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('clock_in', 'clock_out', 'break_start', 'break_end')",
            name='staff_attendance_evidence_event_type_check'
        ),
        CheckConstraint(
            'gps_accuracy_m IS NULL OR gps_accuracy_m >= 0',
            name='staff_attendance_evidence_accuracy_check'
        ),
        Index('idx_staff_attendance_evidence_attendance_event', 'attendance_id', 'event_type'),
        Index('idx_staff_attendance_evidence_break', 'break_id'),
    )
    
    # Relationships
    attendance = relationship("StaffAttendance", foreign_keys=[attendance_id])
    break_record = relationship("StaffAttendanceBreak", foreign_keys=[break_id])
    created_by_user = relationship("StaffEmployee", foreign_keys=[created_by])
    
    def to_dict(self, include_photo_url=True):
        data = {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "break_id": self.break_id,
            "event_type": self.event_type,
            "event_type_display": self.event_type.replace('_', ' ').title(),
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "captured_time": self.captured_at.strftime("%H:%M:%S") if self.captured_at else None,
            "gps_latitude": float(self.gps_latitude) if self.gps_latitude else None,
            "gps_longitude": float(self.gps_longitude) if self.gps_longitude else None,
            "gps_accuracy_m": float(self.gps_accuracy_m) if self.gps_accuracy_m else None,
            "gps_altitude": float(self.gps_altitude) if self.gps_altitude else None,
            "location_address": self.location_address,
            "location_meta": self.location_meta,
            "device_info": self.device_info,
            "timestamp_overlay": self.timestamp_overlay,
            "face_detected": self.face_detected,
            "face_confidence": self.face_confidence,
            "remarks": self.remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "uses_new_naming": self.uses_new_naming,
            "download_filename": self.download_filename
        }
        
        if include_photo_url:
            data["photo_url"] = f"/storage/{self.photo_path}" if self.photo_path else None
        
        return data


# ============================================================================
# LOCATION DRIFT TRACKING SYSTEM - WVV & DC Protocol Compliant
# Created: Nov 29, 2025
# Purpose: Track significant location changes (≥200m) during work hours
# ============================================================================

class StaffLocationDriftEvent(Base):
    """
    Location Drift Event - Captures significant location changes during work hours
    
    DC Protocol: Immutable records with semantic DC codes (LD-YYYYMMDD-SEQ)
    WVV Protocol: GPS validation (accuracy ≤100m, staleness ≤5min), distance ≥200m
    
    Created: Nov 29, 2025
    """
    __tablename__ = 'staff_location_drift_events'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Drift sequence (1st, 2nd, 3rd change of the day)
    drift_sequence = Column(Integer, nullable=False, default=1)
    
    # Previous location (where they were)
    previous_latitude = Column(Numeric(10, 7), nullable=False)
    previous_longitude = Column(Numeric(10, 7), nullable=False)
    previous_address = Column(String(512), nullable=True)
    
    # Current location (where they moved to)
    current_latitude = Column(Numeric(10, 7), nullable=False)
    current_longitude = Column(Numeric(10, 7), nullable=False)
    current_address = Column(String(512), nullable=True)
    
    # Distance and accuracy
    distance_meters = Column(Numeric(10, 2), nullable=False)  # Must be ≥200m
    gps_accuracy_m = Column(Numeric(8, 2), nullable=True)  # GPS accuracy at capture
    
    # Capture metadata
    captured_at = Column(DateTime, nullable=False, default=get_indian_time)
    capture_method = Column(String(32), default='foreground_poll')  # foreground_poll, explicit_capture, resume
    
    # DC Protocol compliance
    dc_code = Column(String(64), nullable=False, unique=True, index=True)  # LD-YYYYMMDD-EMP-SEQ
    
    # Device and context
    device_info = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    
    # Optional: Link to evidence if photo was captured
    evidence_id = Column(Integer, ForeignKey('staff_attendance_evidence.id', ondelete='SET NULL'), nullable=True)
    
    # Audit fields (immutable after creation)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_location_drift_emp_date', 'employee_id', 'attendance_id'),
        Index('idx_location_drift_attendance_seq', 'attendance_id', 'drift_sequence'),
        Index('idx_location_drift_captured_at', 'captured_at'),
        CheckConstraint(
            "capture_method IN ('foreground_poll', 'explicit_capture', 'resume', 'manual')",
            name='staff_location_drift_capture_method_check'
        ),
    )
    
    attendance = relationship("StaffAttendance", foreign_keys=[attendance_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    evidence = relationship("StaffAttendanceEvidence", foreign_keys=[evidence_id])
    
    def to_dict(self, include_addresses=True):
        data = {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "employee_id": self.employee_id,
            "drift_sequence": self.drift_sequence,
            "previous_location": {
                "latitude": float(self.previous_latitude) if self.previous_latitude else None,
                "longitude": float(self.previous_longitude) if self.previous_longitude else None,
            },
            "current_location": {
                "latitude": float(self.current_latitude) if self.current_latitude else None,
                "longitude": float(self.current_longitude) if self.current_longitude else None,
            },
            "distance_meters": float(self.distance_meters) if self.distance_meters else 0,
            "distance_display": f"+{int(self.distance_meters)}m" if self.distance_meters else "+0m",
            "gps_accuracy_m": float(self.gps_accuracy_m) if self.gps_accuracy_m else None,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "captured_time": self.captured_at.strftime("%H:%M") if self.captured_at else None,
            "capture_method": self.capture_method,
            "dc_code": self.dc_code,
            "evidence_id": self.evidence_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_addresses:
            data["previous_location"]["address"] = self.previous_address
            data["current_location"]["address"] = self.current_address
        
        return data


def generate_drift_dc_code(employee_code: str, date, sequence: int) -> str:
    """
    Generate DC-compliant code for location drift event
    Format: LD-YYYYMMDD-{EMP_CODE}-{SEQ}
    """
    date_str = date.strftime("%Y%m%d") if hasattr(date, 'strftime') else str(date).replace('-', '')
    return f"LD-{date_str}-{employee_code}-{sequence:03d}"


# Default break types to seed
DEFAULT_BREAK_TYPES = [
    {
        "break_code": "LUNCH",
        "name": "Lunch Break",
        "description": "Standard meal break (paid)",
        "max_duration_minutes": 60,
        "is_paid": True,
        "requires_evidence": False,
        "display_order": 10
    },
    {
        "break_code": "TEA",
        "name": "Tea / Coffee Break",
        "description": "Short refreshment break",
        "max_duration_minutes": 15,
        "is_paid": True,
        "requires_evidence": False,
        "display_order": 20
    },
    {
        "break_code": "PERSONAL",
        "name": "Personal Break",
        "description": "Personal needs / restroom break",
        "max_duration_minutes": 15,
        "is_paid": True,
        "requires_evidence": False,
        "display_order": 30
    },
    {
        "break_code": "CLIENT_VISIT",
        "name": "Client Visit",
        "description": "Visiting client location (field work)",
        "max_duration_minutes": None,  # No limit
        "is_paid": True,
        "requires_evidence": True,  # Requires photo evidence
        "display_order": 40
    },
    {
        "break_code": "TRAVEL",
        "name": "Travel Break",
        "description": "Transit between locations",
        "max_duration_minutes": None,
        "is_paid": True,
        "requires_evidence": False,
        "display_order": 50
    },
    {
        "break_code": "EMERGENCY",
        "name": "Emergency Break",
        "description": "Personal emergency situations",
        "max_duration_minutes": None,
        "is_paid": False,  # Unpaid
        "requires_evidence": False,
        "display_order": 60
    }
]


class StaffRealtimeLocation(Base):
    """
    Real-time Employee Location Tracking
    DC Protocol: Complete audit trail for live location tracking
    
    DC_GPS_DUAL_TIER_001 (Dec 05, 2025): Dual-tier GPS accuracy system
    - Location Tracking: Accept up to 500m accuracy (for indoor/degraded GPS)
    - Journey Reimbursement: Strict 100m WVV limit (tracked via is_wvv_compliant in device_info)
    
    Access Control:
    - Staff: Own data + history
    - Manager/Lead: Direct reports + history  
    - HR/EA: All staff + history
    - VGK: Full access + export
    """
    __tablename__ = 'staff_realtime_locations'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # WVV Protocol: GPS Data (validated accuracy ≤100m)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    accuracy_m = Column(Numeric(10, 2), nullable=False)
    altitude = Column(Numeric(10, 2), nullable=True)
    speed_kmh = Column(Numeric(10, 2), nullable=True)
    heading = Column(Numeric(6, 2), nullable=True)
    
    # Source tracking
    source = Column(String(32), default='manual', nullable=False)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='SET NULL'), nullable=True)
    journey_id = Column(Integer, ForeignKey('staff_journeys.id', ondelete='SET NULL'), nullable=True)
    drift_event_id = Column(Integer, ForeignKey('staff_location_drift_events.id', ondelete='SET NULL'), nullable=True)
    
    # Status flags
    is_clocked_in = Column(Boolean, default=False)
    is_on_break = Column(Boolean, default=False)
    is_on_journey = Column(Boolean, default=False)
    break_type = Column(String(32), nullable=True)
    
    # DC Protocol: Semantic code for audit
    dc_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Device/Network metadata
    device_info = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # DC_APP_VERSION_001 (Jan 28, 2026): Mobile app version tracking
    app_version = Column(String(32), nullable=True)
    app_platform = Column(String(16), nullable=True)
    
    # Timestamps
    captured_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "accuracy_m > 0 AND accuracy_m <= 500",
            name='valid_accuracy_check'
        ),
        CheckConstraint(
            "source IN ('attendance', 'journey', 'drift', 'manual', 'heartbeat', 'native_background', 'native_foreground', 'background', 'foreground', 'mobile_heartbeat') OR source LIKE 'gap_%'",
            name='valid_source_check'
        ),
        CheckConstraint(
            "break_type IS NULL OR break_type IN ('LUNCH', 'TEA', 'PERSONAL', 'CLIENT_VISIT', 'TRAVEL', 'EMERGENCY', 'MEETING', 'OTHER')",
            name='valid_break_type_check'
        ),
        Index('idx_realtime_loc_emp_captured', 'employee_id', 'captured_at'),
    )
    
    # Relationships
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    attendance = relationship("StaffAttendance", foreign_keys=[attendance_id])
    
    def to_dict(self, include_employee=False):
        """Convert to dictionary for API response with battery percentage and accuracy quality"""
        # DC_LOCATION_BATTERY_001: Extract battery % from device_info JSONB
        # DC_GPS_DUAL_TIER_001: Extract WVV compliance and accuracy quality
        battery_percentage = None
        is_wvv_compliant = True
        accuracy_quality = "high"
        
        if self.device_info and isinstance(self.device_info, dict):
            battery_percentage = self.device_info.get('battery_percentage')
            is_wvv_compliant = self.device_info.get('is_wvv_compliant', True)
            accuracy_quality = self.device_info.get('accuracy_quality', 'high')
        
        # Fallback accuracy quality calculation if not in device_info
        if accuracy_quality == "high" and self.accuracy_m:
            acc = float(self.accuracy_m)
            if acc > 300:
                accuracy_quality = "degraded"
            elif acc > 100:
                accuracy_quality = "low"
            elif acc > 50:
                accuracy_quality = "medium"
        
        data = {
            "id": self.id,
            "employee_id": self.employee_id,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy_m": float(self.accuracy_m) if self.accuracy_m else None,
            "altitude": float(self.altitude) if self.altitude else None,
            "speed_kmh": float(self.speed_kmh) if self.speed_kmh else None,
            "heading": float(self.heading) if self.heading else None,
            "source": self.source,
            "attendance_id": self.attendance_id,
            "journey_id": self.journey_id,
            "drift_event_id": self.drift_event_id,
            "is_clocked_in": self.is_clocked_in,
            "is_on_break": self.is_on_break,
            "is_on_journey": self.is_on_journey,
            "break_type": self.break_type,
            "dc_code": self.dc_code,
            "battery_percentage": battery_percentage,
            "is_wvv_compliant": is_wvv_compliant,
            "accuracy_quality": accuracy_quality,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_employee and self.employee:
            data["employee"] = {
                "id": self.employee.id,
                "emp_code": self.employee.emp_code,
                "full_name": self.employee.full_name,
                "role_name": self.employee.role.role_name if self.employee.role else None,
                "department_name": self.employee.department.name if self.employee.department else None
            }
        
        return data
    
    def to_map_marker(self):
        """Minimal data for map markers with battery percentage and accuracy quality"""
        # DC_LOCATION_BATTERY_001 + DC_GPS_DUAL_TIER_001: Extract battery % and accuracy quality from device_info JSONB
        battery_percentage = None
        is_wvv_compliant = True
        accuracy_quality = "high"
        
        if self.device_info and isinstance(self.device_info, dict):
            battery_percentage = self.device_info.get('battery_percentage')
            is_wvv_compliant = self.device_info.get('is_wvv_compliant', True)
            accuracy_quality = self.device_info.get('accuracy_quality', 'high')
        
        # Fallback accuracy quality calculation if not in device_info
        if accuracy_quality == "high" and self.accuracy_m:
            acc = float(self.accuracy_m)
            if acc > 300:
                accuracy_quality = "degraded"
            elif acc > 100:
                accuracy_quality = "low"
            elif acc > 50:
                accuracy_quality = "medium"
        
        return {
            "employee_id": self.employee_id,
            "emp_code": self.employee.emp_code if self.employee else None,
            "name": self.employee.full_name if self.employee else None,
            "lat": float(self.latitude) if self.latitude else None,
            "lng": float(self.longitude) if self.longitude else None,
            "status": "journey" if self.is_on_journey else ("break" if self.is_on_break else ("active" if self.is_clocked_in else "offline")),
            "break_type": self.break_type,
            "battery_percentage": battery_percentage,
            "is_wvv_compliant": is_wvv_compliant,
            "accuracy_quality": accuracy_quality,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "accuracy_m": float(self.accuracy_m) if self.accuracy_m else None,
            "app_version": self.app_version,
            "app_platform": self.app_platform
        }


class StaffActivityTimeLog(Base):
    """
    Unified Activity Time Ledger (DC Protocol - Immutable)
    Tracks time spent across KRA, Tasks, DayPlan, Leads, Tickets, Journeys, Custom
    Single source of truth for activity-based time reporting
    
    Created: Feb 24, 2026
    DC Protocol: Insert-only, no updates/deletes
    WVV Protocol: Minutes > 0 and <= 1440, source validated
    """
    __tablename__ = 'staff_activity_time_log'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    source_type = Column(String(20), nullable=False, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    source_title = Column(String(512), nullable=True)
    source_code = Column(String(64), nullable=True)
    
    required_minutes = Column(Integer, default=0, nullable=False)
    planned_minutes = Column(Integer, default=0, nullable=False)
    completed_minutes = Column(Integer, nullable=False)
    
    description = Column(Text, nullable=True)
    
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='SET NULL'), nullable=True, index=True)
    
    approval_status = Column(String(20), default='submitted', nullable=False)
    approved_minutes = Column(Integer, nullable=True)
    approved_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('kra', 'task', 'dayplan', 'lead', 'ticket', 'journey', 'custom')",
            name='staff_activity_time_source_type_check'
        ),
        CheckConstraint(
            'completed_minutes > 0 AND completed_minutes <= 1440',
            name='staff_activity_time_minutes_check'
        ),
        Index('idx_activity_time_emp_date', 'employee_id', 'date'),
        Index('idx_activity_time_source', 'source_type', 'source_id'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    attendance = relationship("StaffAttendance", foreign_keys=[attendance_id])
    approver = relationship("StaffEmployee", foreign_keys=[approved_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "date": self.date.isoformat() if self.date else None,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "source_code": self.source_code,
            "required_minutes": self.required_minutes or 0,
            "planned_minutes": self.planned_minutes or 0,
            "completed_minutes": self.completed_minutes,
            "approved_minutes": self.approved_minutes,
            "approval_status": self.approval_status or 'submitted',
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "description": self.description,
            "attendance_id": self.attendance_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


def generate_realtime_dc_code(employee_code: str, timestamp) -> str:
    """
    Generate DC-compliant code for real-time location
    Format: RL-{EMP_CODE}-{YYYYMMDD}-{HHMMSS}
    """
    ts_str = timestamp.strftime("%Y%m%d-%H%M%S") if hasattr(timestamp, 'strftime') else str(timestamp)
    return f"RL-{employee_code}-{ts_str}"
