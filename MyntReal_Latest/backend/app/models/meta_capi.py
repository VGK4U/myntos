"""
Meta CAPI Log Model (Release 1A CAPI Foundation)
Foundation table for Meta Conversions API (CAPI) events.
Outbound dispatch remains DISABLED in Release 1A (CAPI_ENABLED = False).
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Index
from datetime import datetime
from app.models.base import Base


class MetaCAPILog(Base):
    """
    Meta Conversions API Event Log.
    Event ID collision-free structure bound to database transaction/followup IDs.
    """
    __tablename__ = 'meta_capi_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    event_name = Column(String(50), nullable=False, index=True)  # Lead, Contact, QualifiedLead, Schedule, Purchase
    event_id = Column(String(150), unique=True, nullable=False, index=True)
    
    status = Column(String(20), nullable=False, default='QUEUED', index=True)  # QUEUED, SENT, FAILED, DISABLED
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f'<MetaCAPILog event={self.event_name} id={self.event_id} status={self.status}>'
