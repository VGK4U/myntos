"""
MyOperator Call Dashboard Model
DC Protocol: All tables include company_id for multi-company segregation
Tracks inbound/outbound operator calls from MyOperator cloud telephony.
Created: Mar 2026
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, Index, BigInteger, UniqueConstraint
from app.models.base import BaseModel
from datetime import datetime
import pytz


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class OperatorCall(BaseModel):
    """
    Stores call events received from MyOperator via webhook + periodic sync.
    DC Protocol: company_id scoped; call_id is the unique MyOperator call ID (upsert key).
    Status values: ringing | active | answered | missed | ended
    Call type: inbound | outbound
    """
    __tablename__ = 'operator_calls'
    __table_args__ = (
        UniqueConstraint('company_id', 'call_id', name='uq_opcalls_company_call'),
        Index('ix_opcalls_company_status', 'company_id', 'status'),
        Index('ix_opcalls_call_id', 'call_id'),
        Index('ix_opcalls_caller', 'caller_number'),
        Index('ix_opcalls_created', 'created_at'),
        Index('ix_opcalls_lead', 'crm_lead_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)

    call_id = Column(String(100), nullable=False, index=True)

    caller_number = Column(String(20), nullable=True)
    called_number = Column(String(20), nullable=True)
    operator_name = Column(String(200), nullable=True)
    operator_number = Column(String(20), nullable=True)
    handled_by = Column(String(200), nullable=True)
    miss_reason = Column(String(50), nullable=True)
    missed_status = Column(String(20), nullable=True)  # 'pending' | 'disposed' (only for missed calls)

    call_type = Column(String(20), default='inbound', nullable=False)
    status = Column(String(30), default='ringing', nullable=False)

    started_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)

    recording_url = Column(Text, nullable=True)
    recording_expires_at = Column(DateTime, nullable=True)

    crm_lead_id = Column(Integer, nullable=True, index=True)
    followup_created = Column(Boolean, default=False, nullable=False)
    followup_id = Column(Integer, nullable=True)
    lead_matched = Column(Boolean, default=False, nullable=False)
    call_note_posted = Column(Boolean, default=False, nullable=False)

    raw_payload = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    @staticmethod
    def _fmt_dt(dt):
        """Serialize datetime: append 'Z' for naive (UTC) datetimes so JS correctly converts to IST."""
        if not dt:
            return None
        if dt.tzinfo is None:
            return dt.isoformat() + 'Z'
        return dt.isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'call_id': self.call_id,
            'caller_number': self.caller_number,
            'called_number': self.called_number,
            'operator_name': self.operator_name,
            'operator_number': self.operator_number,
            'handled_by': self.handled_by,
            'miss_reason': self.miss_reason,
            'missed_status': self.missed_status,
            'call_type': self.call_type,
            'status': self.status,
            'started_at': self._fmt_dt(self.started_at),
            'answered_at': self._fmt_dt(self.answered_at),
            'ended_at': self._fmt_dt(self.ended_at),
            'duration_seconds': self.duration_seconds or 0,
            'recording_url': self.recording_url,
            'recording_expires_at': self._fmt_dt(self.recording_expires_at),
            'crm_lead_id': self.crm_lead_id,
            'followup_created': self.followup_created,
            'followup_id': self.followup_id,
            'lead_matched': self.lead_matched,
            'call_note_posted': self.call_note_posted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
