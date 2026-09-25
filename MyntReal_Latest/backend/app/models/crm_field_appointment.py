"""
CRM Field Appointment & Supporting Staff Models
DC Protocol Compliant - Unified across Web, Mobile SPA, Android, and iOS.
Tables:
- crm_field_appointments: Field appointments for physical visits (Bank, Customer Location, Others)
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text,
    ForeignKey, Index, Float, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, date
import pytz

from app.models.base import BaseModel


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


def _si(d):
    """Safe isoformat serializer guarding against out-of-range dates"""
    try:
        return d.isoformat() if d else None
    except (ValueError, OverflowError, AttributeError):
        return None


class CRMFieldAppointment(BaseModel):
    """
    Dedicated field appointment model for physical visits and supporting staff workflow.
    Supports visit types:
      - 'visit_bank': Bank/branch visit for lead documentation, loan filing, or verification
      - 'visit_customer': On-site customer location visit
      - 'others': Any other physical/support activity (service, inspection, liaison)
    """
    __tablename__ = 'crm_field_appointments'
    __table_args__ = (
        Index('ix_crm_field_appts_lead', 'lead_id'),
        Index('ix_crm_field_appts_company', 'company_id'),
        Index('ix_crm_field_appts_assigned', 'assigned_to_id', 'status', 'appointment_date'),
        Index('ix_crm_field_appts_status_date', 'status', 'appointment_date'),
        Index('ix_crm_field_appts_created_by', 'created_by_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='SET NULL'), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    appointment_code = Column(String(32), unique=True, nullable=False, index=True)

    # Lead linkage
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)

    # Classification & Purpose
    visit_type = Column(String(32), nullable=False, default='visit_customer')  # 'visit_bank' | 'visit_customer' | 'others'
    purpose = Column(Text, nullable=True)  # Free text purpose/goal of visit

    # Status Lifecycle
    # States: 'assigned', 'accepted', 'in_progress', 'reached', 'completed', 'rescheduled', 'unable_to_visit', 'cancelled'
    status = Column(String(32), default='assigned', nullable=False, index=True)

    # Scheduling
    appointment_date = Column(Date, nullable=False, index=True)
    preferred_time = Column(String(50), nullable=True)  # e.g. "10:30 AM", "11:00 AM - 01:00 PM"
    scheduled_start_time = Column(DateTime, nullable=True)

    # Staff Assignment
    assigned_to_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='RESTRICT'), nullable=False)
    created_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    assigned_at = Column(DateTime, default=get_indian_time, nullable=False)
    reassignment_history = Column(JSONB, default=list, nullable=False)

    # Location Snapshot - Bank Visit
    bank_name = Column(String(200), nullable=True)
    bank_branch = Column(String(200), nullable=True)
    bank_address = Column(Text, nullable=True)
    bank_contact_person = Column(String(200), nullable=True)
    bank_contact_phone = Column(String(50), nullable=True)
    bank_google_maps_url = Column(Text, nullable=True)

    # Location Snapshot - Customer Visit
    customer_address = Column(Text, nullable=True)
    customer_city = Column(String(100), nullable=True)
    customer_area = Column(String(200), nullable=True)
    customer_pincode = Column(String(20), nullable=True)
    customer_google_maps_url = Column(Text, nullable=True)

    # Location Snapshot - Others
    other_location_title = Column(String(256), nullable=True)
    other_location_address = Column(Text, nullable=True)
    other_contact_person = Column(String(200), nullable=True)
    other_contact_phone = Column(String(50), nullable=True)
    other_google_maps_url = Column(Text, nullable=True)

    # Telecaller Instructions
    telecaller_instructions = Column(Text, nullable=True)

    # Reached / Check-in Tracking
    reached_at = Column(DateTime, nullable=True)
    reached_latitude = Column(Float, nullable=True)
    reached_longitude = Column(Float, nullable=True)
    reached_accuracy_meters = Column(Float, nullable=True)

    # Execution & Outcome
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    outcome_status = Column(String(50), nullable=True)  # 'successful', 'customer_not_available', 'bank_closed', 'followup_required', 'other'
    outcome_summary = Column(Text, nullable=True)
    reschedule_reason = Column(Text, nullable=True)
    rescheduled_to_date = Column(Date, nullable=True)
    cancel_reason = Column(Text, nullable=True)

    # Physical Verification & GPS Evidence
    photo_path = Column(String(500), nullable=True)
    compressed_photo_path = Column(String(500), nullable=True)
    photo_uploaded_at = Column(DateTime, nullable=True)
    visit_latitude = Column(Float, nullable=True)
    visit_longitude = Column(Float, nullable=True)
    gps_accuracy_meters = Column(Float, nullable=True)
    device_captured_at = Column(DateTime, nullable=True)
    is_gps_verified = Column(Boolean, default=False, nullable=False)
    visited_on_time = Column(Boolean, nullable=True)

    # Performance / Timesheet Integration Link
    timesheet_entry_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    # Relationships
    lead = relationship("CRMLead", foreign_keys=[lead_id], backref="field_appointments")
    assigned_to = relationship("StaffEmployee", foreign_keys=[assigned_to_id])
    creator = relationship("StaffEmployee", foreign_keys=[created_by_id])

    def to_dict(self, include_lead_summary=True):
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'company_id': self.company_id,
            'appointment_code': self.appointment_code,
            'lead_id': self.lead_id,
            'visit_type': self.visit_type,
            'purpose': self.purpose or '',
            'status': self.status,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'preferred_time': self.preferred_time or '',
            'scheduled_start_time': _si(self.scheduled_start_time),
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.full_name if self.assigned_to else None,
            'assigned_to_emp_code': self.assigned_to.emp_code if self.assigned_to else None,
            'assigned_to_phone': getattr(self.assigned_to, 'phone', None) if self.assigned_to else None,
            'created_by_id': self.created_by_id,
            'created_by_name': self.creator.full_name if self.creator else None,
            'created_by_emp_code': self.creator.emp_code if self.creator else None,
            'assigned_at': _si(self.assigned_at),
            'reassignment_history': self.reassignment_history or [],
            # Bank Visit Info
            'bank_name': self.bank_name,
            'bank_branch': self.bank_branch,
            'bank_address': self.bank_address,
            'bank_contact_person': self.bank_contact_person,
            'bank_contact_phone': self.bank_contact_phone,
            'bank_google_maps_url': self.bank_google_maps_url,
            # Customer Visit Info
            'customer_address': self.customer_address,
            'customer_city': self.customer_city,
            'customer_area': self.customer_area,
            'customer_pincode': self.customer_pincode,
            'customer_google_maps_url': self.customer_google_maps_url,
            # Others Info
            'other_location_title': self.other_location_title,
            'other_location_address': self.other_location_address,
            'other_contact_person': self.other_contact_person,
            'other_contact_phone': self.other_contact_phone,
            'other_google_maps_url': self.other_google_maps_url,
            # Telecaller Instructions
            'telecaller_instructions': self.telecaller_instructions or '',
            # Reached
            'reached_at': _si(self.reached_at),
            'reached_latitude': self.reached_latitude,
            'reached_longitude': self.reached_longitude,
            'reached_accuracy_meters': self.reached_accuracy_meters,
            # Execution
            'started_at': _si(self.started_at),
            'completed_at': _si(self.completed_at),
            'outcome_status': self.outcome_status,
            'outcome_summary': self.outcome_summary,
            'reschedule_reason': self.reschedule_reason,
            'rescheduled_to_date': self.rescheduled_to_date.isoformat() if self.rescheduled_to_date else None,
            'cancel_reason': self.cancel_reason,
            # Evidence
            'photo_path': self.photo_path,
            'compressed_photo_path': self.compressed_photo_path or self.photo_path,
            'photo_uploaded_at': _si(self.photo_uploaded_at),
            'visit_latitude': self.visit_latitude,
            'visit_longitude': self.visit_longitude,
            'gps_accuracy_meters': self.gps_accuracy_meters,
            'device_captured_at': _si(self.device_captured_at),
            'is_gps_verified': bool(self.is_gps_verified),
            'visited_on_time': self.visited_on_time,
            'timesheet_entry_id': self.timesheet_entry_id,
            'created_at': _si(self.created_at),
            'updated_at': _si(self.updated_at),
        }

        # Resolve primary effective Google Maps URL and address depending on visit type
        if self.visit_type == 'visit_bank':
            data['resolved_location_name'] = f"{self.bank_name or ''} {self.bank_branch or ''}".strip() or 'Bank Branch'
            data['resolved_address'] = self.bank_address or ''
            data['resolved_maps_url'] = self.bank_google_maps_url or ''
            data['resolved_contact_name'] = self.bank_contact_person or ''
            data['resolved_contact_phone'] = self.bank_contact_phone or ''
        elif self.visit_type == 'visit_customer':
            loc_parts = [self.customer_address, self.customer_area, self.customer_city, self.customer_pincode]
            data['resolved_location_name'] = 'Customer Location'
            data['resolved_address'] = ', '.join([p for p in loc_parts if p]) or ''
            data['resolved_maps_url'] = self.customer_google_maps_url or ''
            data['resolved_contact_name'] = self.lead.name if self.lead else ''
            data['resolved_contact_phone'] = self.lead.phone if self.lead else ''
        else:  # 'others'
            data['resolved_location_name'] = self.other_location_title or 'Field Location'
            data['resolved_address'] = self.other_location_address or ''
            data['resolved_maps_url'] = self.other_google_maps_url or ''
            data['resolved_contact_name'] = self.other_contact_person or ''
            data['resolved_contact_phone'] = self.other_contact_phone or ''

        if include_lead_summary and self.lead:
            data['lead'] = {
                'id': self.lead.id,
                'name': self.lead.name,
                'phone': self.lead.phone,
                'status': self.lead.status,
                'priority': self.lead.priority,
                'loan_bank': getattr(self.lead, 'loan_bank', None),
                'bank_branch': getattr(self.lead, 'bank_branch', None),
                'application_no': getattr(self.lead, 'application_no', None),
                'solar_pipeline_status': getattr(self.lead, 'solar_pipeline_status', None),
                'telecaller_id': getattr(self.lead, 'telecaller_id', None),
                'field_staff_id': getattr(self.lead, 'field_staff_id', None),
                'support_staff_id': getattr(self.lead, 'support_staff_id', None),
            }
        else:
            data['lead'] = None

        return data
