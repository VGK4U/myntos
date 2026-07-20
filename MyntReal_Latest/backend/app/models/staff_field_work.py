"""
Staff Field Work & KM Tracking Models (DC Protocol Compliant)
GPS-driven field work tracking with reimbursement calculation

Tables:
- staff_transport_rates: Configurable rates per transport mode
- staff_field_work_sessions: Active field work session per attendance
- staff_field_work_track_points: GPS coordinate log with distance calculation
- staff_attendance_approval: Manager approval workflow for attendance

Key Features:
- Real-time KM tracking using GPS coordinates
- Haversine distance calculation between points
- Transport mode-based reimbursement rates
- GPS permission status tracking
- Manager approval workflow with audit trail

Created: Nov 27, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text,
    ForeignKey, CheckConstraint, Index, Numeric, Float
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from decimal import Decimal
import math
import pytz

from app.models.base import Base


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth (in kilometers)
    DC: Uses Haversine formula for accuracy
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


class StaffTransportRate(Base):
    """
    Transport Mode Rate Configuration
    DC: Configurable reimbursement rates per transport type
    WVV: Only one active rate per transport mode at a time
    """
    __tablename__ = 'staff_transport_rates'
    
    id = Column(Integer, primary_key=True, index=True)
    
    transport_mode = Column(String(32), nullable=False, index=True)
    rate_per_km = Column(Numeric(10, 2), nullable=False)
    description = Column(String(256), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "transport_mode IN ('car', 'bike', 'electric_bike', 'cart', 'local_transport', 'others')",
            name='staff_transport_mode_check'
        ),
        Index('idx_transport_rate_mode_active', 'transport_mode', 'is_active'),
    )
    
    creator = relationship("StaffEmployee", foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "transport_mode": self.transport_mode,
            "transport_mode_display": self.transport_mode.replace('_', ' ').title(),
            "rate_per_km": float(self.rate_per_km) if self.rate_per_km else 0,
            "description": self.description,
            "is_active": self.is_active,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffFieldWorkSession(Base):
    """
    Field Work Session per Attendance Record
    DC: One active session per attendance (field mode only)
    WVV: Tracks transport mode, total KM, and reimbursement
    """
    __tablename__ = 'staff_field_work_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    transport_mode = Column(String(32), nullable=False, default='bike')
    
    session_start = Column(DateTime, nullable=False)
    session_end = Column(DateTime, nullable=True)
    
    total_km = Column(Numeric(10, 3), default=0, nullable=False)
    rate_per_km = Column(Numeric(10, 2), nullable=True)
    reimbursement_amount = Column(Numeric(12, 2), default=0, nullable=False)
    
    total_gps_off_minutes = Column(Integer, default=0, nullable=False)
    gps_permission_status = Column(String(32), default='granted')
    
    last_gps_off_at = Column(DateTime, nullable=True)
    
    point_count = Column(Integer, default=0, nullable=False)
    
    status = Column(String(32), default='active')
    
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "transport_mode IN ('car', 'bike', 'electric_bike', 'cart', 'local_transport', 'others')",
            name='staff_field_session_transport_check'
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'cancelled')",
            name='staff_field_session_status_check'
        ),
        CheckConstraint(
            "gps_permission_status IN ('granted', 'denied', 'prompt', 'unavailable')",
            name='staff_field_gps_status_check'
        ),
        Index('idx_field_session_attendance', 'attendance_id'),
        Index('idx_field_session_employee_date', 'employee_id'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    track_points = relationship("StaffFieldWorkTrackPoint", back_populates="session", 
                                cascade="all, delete-orphan", order_by="StaffFieldWorkTrackPoint.captured_at")
    
    def calculate_total_km(self):
        """
        Calculate total KM from all track points
        DC: Sum of segment_km from all valid points
        """
        if not self.track_points:
            return Decimal('0')
        
        total = sum(Decimal(str(p.segment_km or 0)) for p in self.track_points if p.is_valid)
        return total
    
    def calculate_reimbursement(self):
        """
        Calculate reimbursement based on total KM and rate
        DC: total_km × rate_per_km
        """
        if not self.rate_per_km or not self.total_km:
            return Decimal('0')
        
        return Decimal(str(self.total_km)) * Decimal(str(self.rate_per_km))
    
    def update_gps_off_duration(self):
        """
        Calculate total GPS off duration
        DC: Track time when GPS permission was denied
        """
        if self.last_gps_off_at and self.gps_permission_status == 'denied':
            now = get_indian_time()
            off_minutes = int((now - self.last_gps_off_at).total_seconds() / 60)
            self.total_gps_off_minutes += off_minutes
            self.last_gps_off_at = None
    
    def to_dict(self, include_points=False):
        data = {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "transport_mode": self.transport_mode,
            "transport_mode_display": self.transport_mode.replace('_', ' ').title(),
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "session_end": self.session_end.isoformat() if self.session_end else None,
            "total_km": float(self.total_km) if self.total_km else 0,
            "rate_per_km": float(self.rate_per_km) if self.rate_per_km else 0,
            "reimbursement_amount": float(self.reimbursement_amount) if self.reimbursement_amount else 0,
            "total_gps_off_minutes": self.total_gps_off_minutes or 0,
            "gps_permission_status": self.gps_permission_status,
            "point_count": self.point_count or 0,
            "status": self.status,
            "remarks": self.remarks,
            "is_active": self.status == 'active',
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_points and self.track_points:
            data["track_points"] = [p.to_dict() for p in self.track_points[-50:]]
        
        return data


class StaffFieldWorkTrackPoint(Base):
    """
    GPS Track Point for Field Work
    DC: Individual GPS coordinate with distance calculation
    WVV: Calculate segment_km using haversine from previous point
    """
    __tablename__ = 'staff_field_work_track_points'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('staff_field_work_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    
    segment_km = Column(Numeric(10, 4), default=0, nullable=False)
    
    gps_status = Column(String(32), default='active')
    
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_reason = Column(String(128), nullable=True)
    
    captured_at = Column(DateTime, nullable=False, index=True)
    
    raw_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "gps_status IN ('active', 'paused', 'denied', 'unavailable')",
            name='staff_track_point_gps_status_check'
        ),
        Index('idx_track_point_session_time', 'session_id', 'captured_at'),
    )
    
    session = relationship("StaffFieldWorkSession", back_populates="track_points")
    
    def calculate_segment_distance(self, prev_lat, prev_lon):
        """
        Calculate distance from previous point using haversine
        DC: Only calculate if accuracy is acceptable (<50m)
        """
        if self.accuracy and self.accuracy > 50:
            self.is_valid = False
            self.validation_reason = 'Low accuracy (>50m)'
            return Decimal('0')
        
        if prev_lat is None or prev_lon is None:
            return Decimal('0')
        
        distance = haversine_distance(prev_lat, prev_lon, self.latitude, self.longitude)
        
        if distance > 5:
            self.is_valid = False
            self.validation_reason = 'Abnormal jump (>5km)'
            return Decimal('0')
        
        if distance < 0.01:
            self.is_valid = True
            self.validation_reason = 'Stationary'
            return Decimal('0')
        
        return Decimal(str(round(distance, 4)))
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "altitude": self.altitude,
            "speed": self.speed,
            "heading": self.heading,
            "segment_km": float(self.segment_km) if self.segment_km else 0,
            "gps_status": self.gps_status,
            "is_valid": self.is_valid,
            "validation_reason": self.validation_reason,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None
        }


class StaffAttendanceApproval(Base):
    """
    Manager Approval Workflow for Daily Attendance
    DC: Tracks approval status, approver, and reimbursement snapshot
    WVV: Immutable audit trail for all approval actions
    """
    __tablename__ = 'staff_attendance_approvals'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    approval_status = Column(String(32), default='pending', nullable=False, index=True)
    
    submitted_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    worked_minutes_submitted = Column(Integer, default=0)
    break_minutes_submitted = Column(Integer, default=0)
    overtime_minutes_submitted = Column(Integer, default=0)
    
    field_work_km = Column(Numeric(10, 3), nullable=True)
    field_work_transport_mode = Column(String(32), nullable=True)
    field_work_reimbursement = Column(Numeric(12, 2), nullable=True)
    gps_off_minutes = Column(Integer, default=0)
    
    approver_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    worked_minutes_approved = Column(Integer, nullable=True)
    reimbursement_approved = Column(Numeric(12, 2), nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    approver_remarks = Column(Text, nullable=True)
    
    snapshot_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'auto_approved', 'revision_requested')",
            name='staff_approval_status_check'
        ),
        Index('idx_approval_status', 'approval_status'),
        Index('idx_approval_approver', 'approver_id'),
        Index('idx_approval_employee', 'employee_id'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    approver = relationship("StaffEmployee", foreign_keys=[approver_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "approval_status": self.approval_status,
            "approval_status_display": self.approval_status.replace('_', ' ').title(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "worked_minutes_submitted": self.worked_minutes_submitted or 0,
            "worked_hours_submitted": round((self.worked_minutes_submitted or 0) / 60, 2),
            "break_minutes_submitted": self.break_minutes_submitted or 0,
            "overtime_minutes_submitted": self.overtime_minutes_submitted or 0,
            "field_work_km": float(self.field_work_km) if self.field_work_km else None,
            "field_work_transport_mode": self.field_work_transport_mode,
            "field_work_reimbursement": float(self.field_work_reimbursement) if self.field_work_reimbursement else None,
            "gps_off_minutes": self.gps_off_minutes or 0,
            "approver_id": self.approver_id,
            "approver_name": self.approver.full_name if self.approver else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "worked_minutes_approved": self.worked_minutes_approved,
            "worked_hours_approved": round((self.worked_minutes_approved or 0) / 60, 2) if self.worked_minutes_approved else None,
            "reimbursement_approved": float(self.reimbursement_approved) if self.reimbursement_approved else None,
            "rejection_reason": self.rejection_reason,
            "approver_remarks": self.approver_remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffFieldWorkLog(Base):
    """
    Field Work Activity Audit Trail (Immutable)
    DC: Complete history of all field work actions
    """
    __tablename__ = 'staff_field_work_log'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('staff_field_work_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    action = Column(String(64), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    
    previous_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    
    ip_address = Column(String(64), nullable=True)
    device_info = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('session_start', 'session_end', 'transport_change', 'gps_on', 'gps_off', 'point_added', 'approval_submitted', 'approved', 'rejected', 'rate_updated')",
            name='staff_field_work_log_action_check'
        ),
    )
    
    session = relationship("StaffFieldWorkSession", foreign_keys=[session_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else "System",
            "action": self.action,
            "action_display": self.action.replace('_', ' ').title(),
            "details": self.details,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def log_field_work_activity(db, session_id, employee_id, action, details=None, 
                            previous_value=None, new_value=None, ip_address=None, device_info=None):
    """
    Helper function to create field work activity log entries
    DC: Ensures consistent audit logging across all field work operations
    """
    log = StaffFieldWorkLog(
        session_id=session_id,
        employee_id=employee_id,
        action=action,
        details=details,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
        device_info=device_info
    )
    db.add(log)
    return log
