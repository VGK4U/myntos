"""
Staff Call Tracking System Models
DC Protocol: All tables include company_id for multi-company segregation
Tracks call logs synced from mobile devices and auto-matches with CRM leads
Includes call recording storage and playback support
Created: Feb 2026
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Index, BigInteger
from app.models.base import BaseModel
from datetime import datetime
import pytz


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class StaffCallLog(BaseModel):
    __tablename__ = 'staff_call_logs'
    __table_args__ = (
        Index('ix_call_logs_staff_company', 'staff_id', 'company_id'),
        Index('ix_call_logs_phone', 'phone_number'),
        Index('ix_call_logs_datetime', 'call_datetime'),
        Index('ix_call_logs_crm_lead', 'matched_lead_id'),
        Index('ix_call_logs_staff_date', 'staff_id', 'call_date'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)

    phone_number = Column(String(20), nullable=False)
    contact_name = Column(String(200), nullable=True)
    call_type = Column(String(20), nullable=False)
    call_datetime = Column(DateTime, nullable=False)
    call_date = Column(String(10), nullable=False)
    duration_seconds = Column(Integer, default=0, nullable=False)

    source = Column(String(20), default='native', nullable=False)
    device_call_id = Column(String(100), nullable=True)

    matched_lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True)
    matched_at = Column(DateTime, nullable=True)

    has_recording = Column(Boolean, default=False, nullable=False)
    recording_id = Column(Integer, ForeignKey('staff_call_recordings.id', ondelete='SET NULL'), nullable=True)

    synced_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'staff_id': self.staff_id,
            'phone_number': self.phone_number,
            'contact_name': self.contact_name,
            'call_type': self.call_type,
            'call_datetime': self.call_datetime.isoformat() if self.call_datetime else None,
            'call_date': self.call_date,
            'duration_seconds': self.duration_seconds,
            'source': self.source,
            'matched_lead_id': self.matched_lead_id,
            'has_recording': self.has_recording,
            'recording_id': self.recording_id,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StaffCallRecording(BaseModel):
    __tablename__ = 'staff_call_recordings'
    __table_args__ = (
        Index('ix_call_rec_staff_company', 'staff_id', 'company_id'),
        Index('ix_call_rec_call_log', 'call_log_id'),
        Index('ix_call_rec_device_id', 'device_recording_id', 'staff_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    call_log_id = Column(Integer, ForeignKey('staff_call_logs.id', ondelete='SET NULL'), nullable=True)

    original_filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, nullable=True)

    device_recording_id = Column(String(256), nullable=True)
    source_device = Column(String(256), nullable=True)

    uploaded_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'staff_id': self.staff_id,
            'call_log_id': self.call_log_id,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'duration_seconds': self.duration_seconds,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'device_recording_id': self.device_recording_id,
            'source_device': self.source_device,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CallQualityReview(BaseModel):
    """
    Call Quality Review System — DC Protocol (Mar 2026)
    Tracks sampled calls for quality review by leadership/managers.
    Sampling: max(5, ceil(total_calls * 0.05)) per executive per day.
    """
    __tablename__ = 'call_quality_reviews'
    __table_args__ = (
        Index('ix_cqr_company_date', 'company_id', 'sample_date'),
        Index('ix_cqr_staff_date', 'staff_id', 'sample_date'),
        Index('ix_cqr_status', 'status'),
        Index('ix_cqr_reviewer', 'reviewer_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)

    staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    call_log_id = Column(Integer, ForeignKey('staff_call_logs.id', ondelete='SET NULL'), nullable=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True)

    sample_date = Column(String(10), nullable=False)
    sampled_by = Column(String(20), default='auto', nullable=False)

    status = Column(String(20), default='pending', nullable=False)

    reviewer_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    score_script = Column(Integer, nullable=True)
    score_tone = Column(Integer, nullable=True)
    score_info_accuracy = Column(Integer, nullable=True)
    score_customer_handling = Column(Integer, nullable=True)
    score_closing = Column(Integer, nullable=True)
    score_disposition = Column(Integer, nullable=True)
    overall_score = Column(Float, nullable=True)
    overall_remarks = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        scores = [self.score_script, self.score_tone, self.score_info_accuracy,
                  self.score_customer_handling, self.score_closing, self.score_disposition]
        filled = [s for s in scores if s is not None]
        computed_overall = round(sum(filled) / len(filled), 2) if filled else None
        return {
            'id': self.id,
            'company_id': self.company_id,
            'staff_id': self.staff_id,
            'call_log_id': self.call_log_id,
            'lead_id': self.lead_id,
            'sample_date': self.sample_date,
            'sampled_by': self.sampled_by,
            'status': self.status,
            'reviewer_id': self.reviewer_id,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'score_script': self.score_script,
            'score_tone': self.score_tone,
            'score_info_accuracy': self.score_info_accuracy,
            'score_customer_handling': self.score_customer_handling,
            'score_closing': self.score_closing,
            'score_disposition': self.score_disposition,
            'overall_score': self.overall_score or computed_overall,
            'overall_remarks': self.overall_remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StaffCallSyncLog(BaseModel):
    __tablename__ = 'staff_call_sync_logs'
    __table_args__ = (
        Index('ix_sync_logs_staff', 'staff_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)

    sync_started_at = Column(DateTime, default=get_indian_time, nullable=False)
    sync_completed_at = Column(DateTime, nullable=True)
    records_synced = Column(Integer, default=0, nullable=False)
    records_matched = Column(Integer, default=0, nullable=False)
    records_duplicates_skipped = Column(Integer, default=0, nullable=False)
    last_call_datetime = Column(DateTime, nullable=True)
    status = Column(String(20), default='completed', nullable=False)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'sync_started_at': self.sync_started_at.isoformat() if self.sync_started_at else None,
            'sync_completed_at': self.sync_completed_at.isoformat() if self.sync_completed_at else None,
            'records_synced': self.records_synced,
            'records_matched': self.records_matched,
            'records_duplicates_skipped': self.records_duplicates_skipped,
            'status': self.status,
        }
