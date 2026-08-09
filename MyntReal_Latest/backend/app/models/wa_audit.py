"""
WhatsApp Audit Models (Release 1A WhatsApp Layer)
Implements 1:N session history relationship (ONE CRM Lead -> MANY Sessions -> MANY Messages).
Decouples permanent customer conversation history from operational 24h Meta service windows.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, text
from datetime import datetime, timedelta
from app.models.base import Base


class WAConversation(Base):
    """
    WhatsApp Operational Session / Conversation.
    1 Lead -> Many Sessions over time.
    Tracks 24h Meta window expiration and state without fragmenting lead history.
    """
    __tablename__ = 'wa_conversations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    phone = Column(String(20), nullable=False, index=True)
    session_uuid = Column(String(100), unique=True, nullable=False, index=True)
    
    current_state = Column(String(50), nullable=False, default='NEW_LEAD', index=True)
    previous_state = Column(String(50), nullable=True)
    channel_provider = Column(String(30), nullable=False, default='META_CLOUD_API')
    
    window_24h_expires_at = Column(DateTime, nullable=False, index=True)
    service_window_open = Column(Boolean, nullable=False, default=True)
    messaging_policy_window_type = Column(String(30), nullable=False, default='24H_SERVICE')
    
    is_human_takeover = Column(Boolean, nullable=False, default=False)
    assigned_staff_id = Column(Integer, nullable=True)
    
    last_inbound_at = Column(DateTime, nullable=True)
    last_outbound_at = Column(DateTime, nullable=True)
    last_inbound_wamid = Column(String(250), nullable=True)
    
    session_started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<WAConversation session={self.session_uuid} lead={self.lead_id} phone={self.phone}>'


class WAMessage(Base):
    """
    WhatsApp Message Audit Trail.
    1 Conversation Session -> Many Messages.
    Permanent record of all customer and system WhatsApp messages.
    """
    __tablename__ = 'wa_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey('wa_conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    wamid = Column(String(250), unique=True, nullable=True, index=True)
    direction = Column(String(10), nullable=False)  # INBOUND / OUTBOUND
    sender_type = Column(String(20), nullable=False, default='CUSTOMER')  # CUSTOMER, AI_AGENT, HUMAN_STAFF, SYSTEM
    message_type = Column(String(20), nullable=False, default='TEXT')  # TEXT, IMAGE, BUTTON_REPLY, TEMPLATE
    
    body_text = Column(Text, nullable=True)
    delivery_status = Column(String(20), nullable=False, default='QUEUED')  # QUEUED, SENT, DELIVERED, READ, FAILED
    
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f'<WAMessage wamid={self.wamid} direction={self.direction} status={self.delivery_status}>'
