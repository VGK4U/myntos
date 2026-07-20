"""
Staff Journey Tracking Models
DC Protocol: Complete audit trail for journey tracking and reimbursement
WVV: Validated GPS data, distance calculation, photo verification
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Float, Text, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import math

from app.models.base import Base


class JourneyStatus(enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class JourneyApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class JourneyPurpose(enum.Enum):
    CLIENT_VISIT = "client_visit"
    SITE_INSPECTION = "site_inspection"
    MEETING = "meeting"
    DELIVERY = "delivery"
    COLLECTION = "collection"
    OTHER = "other"


class StaffJourney(Base):
    """
    Main journey record tracking start to end point
    DC: Complete audit trail with GPS verification
    """
    __tablename__ = "staff_journeys"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("staff_employees.id"), nullable=False, index=True)
    attendance_id = Column(Integer, ForeignKey("staff_attendance.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("associated_companies.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    
    purpose = Column(SQLEnum(JourneyPurpose), default=JourneyPurpose.OTHER)
    purpose_description = Column(Text, nullable=True)
    client_name = Column(String(200), nullable=True)
    client_address = Column(Text, nullable=True)
    
    kra_instance_id = Column(Integer, ForeignKey("staff_kra_daily_instances.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("staff_tasks.id"), nullable=True)
    
    transport_mode = Column(String(50), default="bike")
    rate_per_km = Column(Float, default=4.00)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    start_address = Column(Text, nullable=True)
    
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)
    end_address = Column(Text, nullable=True)
    
    total_distance_km = Column(Float, default=0.0)
    # WVV Protocol (Dec 05, 2025): Separate reimbursable distance from total distance
    # reimbursable_distance_km only includes segments where BOTH points are WVV compliant
    reimbursable_distance_km = Column(Float, default=0.0)
    total_duration_minutes = Column(Float, default=0.0)
    average_speed_kmh = Column(Float, default=0.0)
    max_speed_kmh = Column(Float, default=0.0)
    
    reimbursement_amount = Column(Float, default=0.0)
    
    status = Column(SQLEnum(JourneyStatus), default=JourneyStatus.IN_PROGRESS)
    approval_status = Column(SQLEnum(JourneyApprovalStatus), default=JourneyApprovalStatus.PENDING)
    
    photo_path = Column(String(500), nullable=True)
    photo_uploaded_at = Column(DateTime, nullable=True)
    
    # Universal Upload System: Compression fields (DC Protocol)
    compressed_photo_path = Column(String(500), nullable=True)
    compressed_photo_size = Column(Integer, nullable=True)
    photo_processing_status = Column(String(20), default='pending', nullable=True)
    compressed_photo_checksum = Column(String(64), nullable=True)
    has_compressed_photo = Column(Boolean, default=False, nullable=True)
    
    # DC Protocol: Dual Storage Architecture (object storage vs local)
    photo_original_checksum = Column(String(64), nullable=True)
    photo_storage_type = Column(String(20), default='local', nullable=True)
    photo_storage_key = Column(String(500), nullable=True)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    gps_enabled = Column(Boolean, default=True)
    gps_permission_denied = Column(Boolean, default=False)
    is_reimbursable = Column(Boolean, default=True)
    non_reimbursable_reason = Column(String(200), nullable=True)
    
    notes = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)
    
    # DC Protocol (Dec 04, 2025): Journey Session Token - replaces strict device binding
    # Token-based auth allows legitimate users to end journeys despite network/browser changes
    journey_session_token = Column(String(64), nullable=True)  # Crypto token issued at start
    fingerprint_mismatch_count = Column(Integer, default=0)  # Audit: how many mismatches occurred
    fingerprint_warnings = Column(JSON, default=list)  # Audit log of mismatch events
    
    # DC Protocol (Dec 04, 2025): Force Stop by Manager
    # When employees cannot end journey due to device binding issues, managers can force-stop
    force_stopped = Column(Boolean, default=False, nullable=False)
    force_stopped_by = Column(Integer, ForeignKey("staff_employees.id"), nullable=True)
    force_stopped_at = Column(DateTime, nullable=True)
    force_stopped_reason = Column(Text, nullable=True)
    force_stopped_device_info = Column(JSON, nullable=True)  # Manager's device info for audit
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_employees.id"), nullable=True)
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id], backref="journeys")
    force_stopped_by_employee = relationship("StaffEmployee", foreign_keys=[force_stopped_by])
    attendance = relationship("StaffAttendance", backref="journeys")
    company = relationship("AssociatedCompany", backref="journeys")
    kra_instance = relationship("StaffKRADailyInstance", backref="journeys")
    task = relationship("StaffTask", backref="journeys")
    track_points = relationship("StaffJourneyTrackPoint", back_populates="journey", cascade="all, delete-orphan")
    approvals = relationship("StaffJourneyApproval", back_populates="journey", cascade="all, delete-orphan")

    def calculate_reimbursement(self):
        """
        Calculate reimbursement based on distance and rate
        WVV Protocol (Dec 05, 2025): Use reimbursable_distance_km (WVV compliant segments only)
        Falls back to total_distance_km if reimbursable_distance not tracked
        """
        distance = self.reimbursable_distance_km if self.reimbursable_distance_km else self.total_distance_km
        self.reimbursement_amount = round(distance * self.rate_per_km, 2)
        return self.reimbursement_amount

    def calculate_duration(self):
        """Calculate journey duration in minutes"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.total_duration_minutes = round(delta.total_seconds() / 60, 2)
        return self.total_duration_minutes

    def calculate_average_speed(self):
        """Calculate average speed in km/h"""
        if self.total_duration_minutes > 0 and self.total_distance_km > 0:
            hours = self.total_duration_minutes / 60
            self.average_speed_kmh = round(self.total_distance_km / hours, 2)
        return self.average_speed_kmh

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "attendance_id": self.attendance_id,
            "company_id": self.company_id,
            "company_name": self.company.company_name if self.company else None,
            "date": self.date.isoformat() if self.date else None,
            "purpose": self.purpose.value if self.purpose else None,
            "purpose_description": self.purpose_description,
            "client_name": self.client_name,
            "client_address": self.client_address,
            "kra_instance_id": self.kra_instance_id,
            "task_id": self.task_id,
            "transport_mode": self.transport_mode,
            "rate_per_km": self.rate_per_km,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "start_latitude": self.start_latitude,
            "start_longitude": self.start_longitude,
            "start_address": self.start_address,
            "end_latitude": self.end_latitude,
            "end_longitude": self.end_longitude,
            "end_address": self.end_address,
            "total_distance_km": self.total_distance_km,
            "reimbursable_distance_km": self.reimbursable_distance_km,
            "total_duration_minutes": self.total_duration_minutes,
            "average_speed_kmh": self.average_speed_kmh,
            "max_speed_kmh": self.max_speed_kmh,
            "reimbursement_amount": self.reimbursement_amount,
            "status": self.status.value if self.status else None,
            "approval_status": self.approval_status.value if self.approval_status else None,
            "photo_path": self.photo_path,
            "photo_uploaded_at": self.photo_uploaded_at.isoformat() if self.photo_uploaded_at else None,
            "gps_enabled": self.gps_enabled,
            "gps_permission_denied": self.gps_permission_denied,
            "is_reimbursable": self.is_reimbursable,
            "non_reimbursable_reason": self.non_reimbursable_reason,
            "notes": self.notes,
            "force_stopped": self.force_stopped,
            "force_stopped_by": self.force_stopped_by,
            "force_stopped_at": self.force_stopped_at.isoformat() if self.force_stopped_at else None,
            "force_stopped_reason": self.force_stopped_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def to_detail_dict(self, include_track_points: bool = False):
        """Extended dict with relationships"""
        data = self.to_dict()
        data["employee_name"] = f"{self.employee.first_name} {self.employee.last_name}" if self.employee else None
        data["employee_id_code"] = self.employee.emp_code if self.employee else None
        data["track_points_count"] = len(self.track_points) if self.track_points else 0
        data["kra_name"] = self.kra_instance.kra_template.name if self.kra_instance and self.kra_instance.kra_template else None
        data["task_title"] = self.task.title if self.task else None
        
        # DC Protocol (Dec 04, 2025): Force Stop by Manager - include stopper's name
        if self.force_stopped and self.force_stopped_by_employee:
            data["force_stopped_by_name"] = f"{self.force_stopped_by_employee.first_name} {self.force_stopped_by_employee.last_name}"
        else:
            data["force_stopped_by_name"] = None
        
        if include_track_points and self.track_points:
            data["track_points"] = [tp.to_dict() for tp in sorted(self.track_points, key=lambda x: x.timestamp)]
            data["route_coordinates"] = [[tp.latitude, tp.longitude] for tp in sorted(self.track_points, key=lambda x: x.timestamp)]
        
        return data


class StaffJourneyTrackPoint(Base):
    """
    GPS track points during journey for route visualization
    DC: Immutable GPS log with timestamp
    WVV Protocol (Dec 05, 2025): Added wvv_compliant flag for degraded GPS acceptance
    """
    __tablename__ = "staff_journey_track_points"

    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("staff_journeys.id"), nullable=False, index=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    
    speed_kmh = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    
    distance_from_prev = Column(Float, default=0.0)
    cumulative_distance = Column(Float, default=0.0)
    
    # WVV Protocol (Dec 05, 2025): Track GPS quality for reimbursement vs audit
    # wvv_compliant=True: Accuracy ≤100m, counts toward reimbursement
    # wvv_compliant=False: Accuracy >100m, stored for audit/visualization only
    wvv_compliant = Column(Boolean, default=True, nullable=False)
    compliance_reason = Column(String(255), nullable=True)  # Reason if not compliant
    
    # DC_JOURNEY_ADDRESS_001 (Jan 22, 2026): Location address for stop point visualization
    address = Column(String(500), nullable=True)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    journey = relationship("StaffJourney", back_populates="track_points")

    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS coordinates in kilometers"""
        R = 6371
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return round(R * c, 4)

    def to_dict(self):
        return {
            "id": self.id,
            "journey_id": self.journey_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "altitude": self.altitude,
            "speed_kmh": self.speed_kmh,
            "heading": self.heading,
            "distance_from_prev": self.distance_from_prev,
            "cumulative_distance": self.cumulative_distance,
            "wvv_compliant": self.wvv_compliant,
            "compliance_reason": self.compliance_reason,
            "address": self.address,  # DC_JOURNEY_ADDRESS_001: Location name for stops
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class StaffJourneyApproval(Base):
    """
    Journey approval workflow
    DC: Audit trail for approval decisions
    """
    __tablename__ = "staff_journey_approvals"

    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("staff_journeys.id"), nullable=False, index=True)
    
    action = Column(String(50), nullable=False)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    
    approved_by = Column(Integer, ForeignKey("staff_employees.id"), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow)
    
    remarks = Column(Text, nullable=True)
    
    journey = relationship("StaffJourney", back_populates="approvals")
    approver = relationship("StaffEmployee", foreign_keys=[approved_by])

    def to_dict(self):
        return {
            "id": self.id,
            "journey_id": self.journey_id,
            "action": self.action,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "approved_by": self.approved_by,
            "approver_name": f"{self.approver.first_name} {self.approver.last_name}" if self.approver else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "remarks": self.remarks
        }
