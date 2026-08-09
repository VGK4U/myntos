"""
AI Voice Calling Models (Release 1A Engine)
Stores call records, call eligibility, call status history, transcripts, and human transfer logs.
External AI Voice dispatches remain strictly DISABLED (VOICE_AI_ENABLED = False).
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey, Index
from datetime import datetime
from app.models.base import Base


class VoiceCallRecord(Base):
    """
    Voice Call Record model.
    Tracks call lifecycle, provider call ID, duration, AI call transcript, summary, and status.
    """
    __tablename__ = 'voice_call_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    phone = Column(String(20), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False, default='NULL_VOICE_PROVIDER')
    provider_call_id = Column(String(100), unique=True, nullable=True, index=True)
    
    call_direction = Column(String(10), nullable=False, default='OUTBOUND')  # OUTBOUND / INBOUND
    status = Column(String(30), nullable=False, default='QUEUED', index=True)  # QUEUED, IN_PROGRESS, COMPLETED, FAILED, TRANSFERRED
    
    duration_seconds = Column(Integer, nullable=False, default=0)
    transcript = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    
    intent_detected = Column(String(50), nullable=True)
    qualification_result = Column(String(50), nullable=True)
    is_transferred_to_human = Column(Boolean, nullable=False, default=False)
    
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<VoiceCallRecord id={self.id} lead={self.lead_id} status={self.status} provider={self.provider_name}>'
