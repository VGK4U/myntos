"""
VoIP Call Session Model — MyntReal In-App PSTN Telephony & Centralized Call Recording Engine
DC Protocol: All tables include company_id for multi-company segregation.
Authoritative call session state management for In-App PSTN, MyOperator Bridge, and Native calls.
Created: Aug 2026
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Index, BigInteger, UniqueConstraint
)
from app.models.base import BaseModel, get_indian_time
from app.models.voip_enums import CallMethodEnum, CallStateEnum, RecordingStatusEnum


class VoIPCallSession(BaseModel):
    """
    Authoritative server-side call session entity.
    Stores complete lifecycle events, provider identifiers, timestamps,
    recording storage keys, and CRM entity relationships.
    """
    __tablename__ = 'voip_call_sessions'
    __table_args__ = (
        UniqueConstraint('call_session_id', name='uq_vcs_session_id'),
        Index('ix_vcs_company_status', 'company_id', 'status'),
        Index('ix_vcs_operator_company', 'operator_id', 'company_id'),
        Index('ix_vcs_lead_company', 'lead_id', 'company_id'),
        Index('ix_vcs_provider_call_id', 'provider', 'provider_call_id'),
        Index('ix_vcs_customer_phone', 'customer_phone'),
        Index('ix_vcs_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_session_id = Column(String(64), nullable=False, unique=True, index=True)

    company_id = Column(Integer, nullable=False, index=True)
    branch_id = Column(Integer, nullable=True, index=True)

    lead_id = Column(Integer, nullable=True, index=True)
    operator_id = Column(Integer, nullable=True, index=True)
    operator_user_ref = Column(String(50), nullable=True)
    operator_name = Column(String(200), nullable=True)

    customer_phone = Column(String(30), nullable=False, index=True)
    direction = Column(String(20), default='outbound', nullable=False)
    call_method = Column(String(30), default=CallMethodEnum.IN_APP_PSTN.value, nullable=False)

    provider = Column(String(50), default='mock', nullable=False)
    provider_call_id = Column(String(128), nullable=True, index=True)

    caller_id = Column(String(30), nullable=False)           # MyntReal Dedicated Business Outbound Number
    destination_number = Column(String(30), nullable=False)  # Normalized customer destination E.164 phone

    status = Column(String(30), default=CallStateEnum.CREATED.value, nullable=False, index=True)

    # State Machine Lifecycle Timestamps
    started_at = Column(DateTime, nullable=True)
    dialing_at = Column(DateTime, nullable=True)
    ringing_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    duration_seconds = Column(Integer, default=0, nullable=False)

    termination_reason = Column(String(100), nullable=True)
    failure_reason = Column(String(255), nullable=True)

    # Independent Recording Lifecycle
    recording_status = Column(String(30), default=RecordingStatusEnum.NOT_STARTED.value, nullable=False)
    recording_id = Column(Integer, nullable=True)
    recording_storage_key = Column(String(512), nullable=True)
    recording_mime_type = Column(String(50), nullable=True)
    recording_file_size = Column(BigInteger, nullable=True)
    recording_duration_seconds = Column(Integer, nullable=True)
    recording_checksum = Column(String(64), nullable=True)

    # Relationship to existing OperatorCall
    operator_call_id = Column(Integer, nullable=True, index=True)

    # Telephony WebRTC Token / Session Config
    client_token = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'call_session_id': self.call_session_id,
            'company_id': self.company_id,
            'branch_id': self.branch_id,
            'lead_id': self.lead_id,
            'operator_id': self.operator_id,
            'operator_user_ref': self.operator_user_ref,
            'operator_name': self.operator_name,
            'customer_phone': self.customer_phone,
            'customer_phone_masked': self.customer_phone_masked,
            'direction': self.direction,
            'call_method': self.call_method,
            'provider': self.provider,
            'provider_call_id': self.provider_call_id,
            'caller_id': self.caller_id,
            'destination_number': self.destination_number,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'dialing_at': self.dialing_at.isoformat() if self.dialing_at else None,
            'ringing_at': self.ringing_at.isoformat() if self.ringing_at else None,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': self.duration_seconds,
            'termination_reason': self.termination_reason,
            'failure_reason': self.failure_reason,
            'recording_status': self.recording_status,
            'has_recording': self.recording_status == RecordingStatusEnum.AVAILABLE.value,
            'recording_storage_key': self.recording_storage_key,
            'operator_call_id': self.operator_call_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def customer_phone_masked(self) -> str:
        """Return masked phone number for privacy/security display e.g. ******8501"""
        num = str(self.customer_phone or '')
        if len(num) > 4:
            return '*' * (len(num) - 4) + num[-4:]
        return num
