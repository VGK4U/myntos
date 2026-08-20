"""
Staff Journey Checkin Model
DC Protocol: Bi-Hourly Photo Verification & GPS Location Audit Trail
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base


class StaffJourneyCheckin(Base):
    """
    Periodic photo check-ins during an active journey (every 2 hours)
    DC Protocol: Low footprint WebP storage + live GPS location stamp
    """
    __tablename__ = "staff_journey_checkins"

    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("staff_journeys.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("staff_employees.id"), nullable=False, index=True)
    
    photo_path = Column(String(500), nullable=False)
    compressed_photo_path = Column(String(500), nullable=True)
    photo_size_bytes = Column(Integer, nullable=True)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    
    wvv_compliant = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    journey = relationship("StaffJourney", backref="checkins")
    employee = relationship("StaffEmployee", backref="journey_checkins")

    def to_dict(self):
        return {
            "id": self.id,
            "journey_id": self.journey_id,
            "employee_id": self.employee_id,
            "employee_name": f"{self.employee.first_name} {self.employee.last_name}" if self.employee else None,
            "photo_path": self.photo_path,
            "compressed_photo_path": self.compressed_photo_path or self.photo_path,
            "photo_size_bytes": self.photo_size_bytes,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "address": self.address,
            "wvv_compliant": self.wvv_compliant,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
