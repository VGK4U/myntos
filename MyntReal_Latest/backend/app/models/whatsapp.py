"""
WhatsApp Messaging Models
Models for WhatsApp messaging control, message logging, and app settings
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, JSON, Numeric, text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class WhatsAppControl(Base):
    """
    WhatsApp messaging control system for RVZ ID users during development/testing
    Allows RVZ ID users to pause/resume WhatsApp OTP and messaging functionality
    """
    __tablename__ = 'whatsapp_control'
    
    id = Column(Integer, primary_key=True)
    
    # Control status
    is_paused = Column(Boolean, default=False, nullable=False)
    
    # Pause/Resume tracking
    paused_by_user_id = Column(String(12), ForeignKey('user.id'))
    paused_at = Column(DateTime)
    pause_reason = Column(Text)
    
    resumed_by_user_id = Column(String(12), ForeignKey('user.id'))
    resumed_at = Column(DateTime)
    
    # Relationships
    paused_by = relationship('User', foreign_keys=[paused_by_user_id])
    resumed_by = relationship('User', foreign_keys=[resumed_by_user_id])
    
    def __repr__(self):
        status = "PAUSED" if self.is_paused else "ACTIVE"
        return f'<WhatsAppControl Status:{status} Reason:{self.pause_reason}>'


class MessageLog(Base):
    """
    Track WhatsApp message delivery status via Meta Cloud API webhooks.
    message_sid stores the Meta WAMID (wamid.HBgL...) which can be 100–500 chars.
    """
    __tablename__ = 'message_log'
    
    id = Column(Integer, primary_key=True)
    
    # Message identification — WAMID from Meta can be up to 500 chars
    message_sid = Column(String(500), unique=True, nullable=False)
    message_type = Column(String(50), default='whatsapp_otp')
    
    # Recipient details
    mobile_number = Column(String(15))
    user_name = Column(String(100))
    otp_code = Column(String(10))  # Store securely or hash if needed
    
    # Message content
    message_body = Column(Text)
    from_number = Column(String(20))
    to_number = Column(String(30))  # whatsapp:+91XXXXXXXXXX format
    
    # Delivery tracking
    provider = Column(String(50), default='TWILIO_WHATSAPP')
    initial_status = Column(String(20))  # queued, sent, delivered, failed, etc.
    current_status = Column(String(20))
    
    # Timestamps
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)
    failed_at = Column(DateTime)
    last_status_update = Column(DateTime, default=datetime.utcnow)
    
    # Error tracking
    error_code = Column(String(20))
    error_message = Column(Text)

    # Sender tracking — who triggered this message
    sent_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    sent_by_name = Column(String(200), nullable=True)   # denormalized: "John (MR10001)" or "System/Auto"
    sender_type = Column(String(50), nullable=True)      # 'staff', 'partner', 'auto', 'system'

    # Relationship
    sent_by_staff = relationship('StaffEmployee', foreign_keys=[sent_by_staff_id])

    def __repr__(self):
        return f'<MessageLog {self.message_sid} {self.mobile_number} Status:{self.current_status}>'


# Note: AppSettings already exists in app.models.system_control
# Import it from there if needed


class WhatsAppTemplate(Base):
    """
    WhatsApp message templates — stored locally, optionally mapped to a Meta-approved template name.
    Supports text, image, video, document headers and variable placeholders.
    """
    __tablename__ = 'whatsapp_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)

    segment = Column(String(50), nullable=False, default='general')
    # segments: ev_b2b, ev_b2c, etc_training, real_estate, general, system

    template_type = Column(String(50), nullable=False, default='custom')
    # types: intro, follow_up, otp, forgot_password, welcome, thank_you,
    #        payment_receipt, order_confirmed, dispatched, reminder, custom

    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # OTP/password — read-only

    # Header
    header_type = Column(String(20), default='none')  # none, text, image, video, document
    header_text = Column(String(200))
    header_media_url = Column(Text)        # external URL (YouTube, Drive, CDN)
    header_media_path = Column(Text)       # internal storage path

    # Body — supports {{name}}, {{custom_1}}, {{custom_2}} variables
    body_text = Column(Text, nullable=False)

    # Footer
    footer_text = Column(String(200))

    # Buttons (JSON array of {type: 'quick_reply'|'url', text, url?})
    buttons = Column(JSON, default=list)

    # Meta Cloud API — approved template name for cold outreach
    meta_template_name = Column(String(200))
    meta_template_language = Column(String(10), default='en')
    is_meta_approved = Column(Boolean, default=False)

    # DC-WA-META-SUBMIT-001: Self-serve Meta template submission
    # meta_approval_status: PENDING | APPROVED | REJECTED | PAUSED | IN_APPEAL | DISABLED | ARCHIVED | DELETED | <none>
    meta_approval_status = Column(String(30), nullable=True)
    meta_submitted_at = Column(DateTime, nullable=True)
    meta_category = Column(String(30), nullable=True)  # MARKETING | UTILITY | AUTHENTICATION
    meta_template_id = Column(String(100), nullable=True)  # Meta's own template ID after creation
    meta_rejected_reason = Column(String(500), nullable=True)  # DC-WA-REJECTED-001: persisted from Meta sync

    # Usage scope — controls where this template appears
    # 'meta'     = submitted to Meta, used in campaigns/bulk outreach; NOT in local auto-triggers
    # 'internal' = local test/auto-triggers only; cannot be submitted to Meta
    # 'both'     = everywhere (default for backward compat)
    usage_scope = Column(String(20), nullable=False, default='both')

    # Example values for each positional variable {{1}}, {{2}}, … — shown in test send UI
    example_values = Column(JSON, nullable=True)

    # Audit
    created_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_staff_id])
    updated_by = relationship('StaffEmployee', foreign_keys=[updated_by_staff_id])
    auto_triggers = relationship('WhatsAppAutoTrigger', back_populates='template')
    campaign_logs = relationship('WhatsAppCampaignLog', back_populates='template')

    def __repr__(self):
        return f'<WhatsAppTemplate {self.slug} [{self.segment}]>'

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'slug': self.slug,
            'segment': self.segment, 'template_type': self.template_type,
            'is_active': self.is_active, 'is_system': self.is_system,
            'header_type': self.header_type, 'header_text': self.header_text,
            'header_media_url': self.header_media_url,
            'body_text': self.body_text, 'footer_text': self.footer_text,
            'buttons': self.buttons or [],
            'meta_template_name': self.meta_template_name,
            'meta_template_language': self.meta_template_language,
            'is_meta_approved': self.is_meta_approved,
            'meta_approval_status': self.meta_approval_status,
            'meta_submitted_at': self.meta_submitted_at.isoformat() if self.meta_submitted_at else None,
            'meta_category': self.meta_category,
            'meta_template_id': self.meta_template_id,
            'meta_rejected_reason': self.meta_rejected_reason,
            'usage_scope': self.usage_scope or 'both',
            'example_values': self.example_values or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WhatsAppAutoTrigger(Base):
    """
    Maps system events to WhatsApp templates.
    Each row = one auto-send rule (event_key → template).
    Staff can enable/disable and customise per trigger.
    """
    __tablename__ = 'whatsapp_auto_triggers'

    id = Column(Integer, primary_key=True)

    event_key = Column(String(100), unique=True, nullable=False)
    # Examples:
    # crm_lead_created, crm_status_contacted, crm_status_interested,
    # crm_status_qualified, crm_status_proposal, crm_status_won,
    # crm_status_lost, crm_status_not_answered, crm_status_loan_process,
    # crm_status_completed, crm_followup_scheduled, crm_transaction_created,
    # crm_transaction_validated,
    # po_confirmed, po_payment_received, po_dispatched, po_completed,
    # ticket_raised, ticket_acknowledged, ticket_resolved, ticket_closed,
    # partner_created, etc_enrolled, etc_completed,
    # staff_morning_reminder

    event_label = Column(String(200), nullable=False)  # Human readable
    event_category = Column(String(50), nullable=False)  # crm, po, ticket, partner, etc, staff

    template_id = Column(Integer, ForeignKey('whatsapp_templates.id'), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Recipient override: 'customer', 'staff', 'both'
    recipient_type = Column(String(20), default='customer')

    # Delay in minutes before sending (0 = immediate)
    delay_minutes = Column(Integer, default=0)

    # Audit
    updated_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    template = relationship('WhatsAppTemplate', back_populates='auto_triggers')
    updated_by = relationship('StaffEmployee', foreign_keys=[updated_by_staff_id])

    def __repr__(self):
        return f'<WhatsAppAutoTrigger {self.event_key} enabled={self.is_enabled}>'

    def to_dict(self):
        return {
            'id': self.id, 'event_key': self.event_key,
            'event_label': self.event_label, 'event_category': self.event_category,
            'template_id': self.template_id, 'is_enabled': self.is_enabled,
            'recipient_type': self.recipient_type, 'delay_minutes': self.delay_minutes,
            'template': self.template.to_dict() if self.template else None,
        }


class WhatsAppCampaign(Base):
    """
    Bulk WhatsApp broadcast campaign — targets CRM leads by segment/status/filters.
    Sends via Meta Cloud API with rate limiting and daily batching.
    """
    __tablename__ = 'whatsapp_campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)

    template_id = Column(Integer, ForeignKey('whatsapp_templates.id'), nullable=False)

    # Targeting filters (stored as JSON for flexibility)
    filters = Column(JSON, default=dict)
    # {
    #   segment: ['ev_b2b', 'ev_b2c'],
    #   status: ['new', 'contacted'],
    #   date_from: '2026-01-01', date_to: '2026-03-31',
    #   telecaller_id: 12,
    #   phone_filter: 'all' | 'whatsapp_confirmed' | 'all_with_fallback',
    #   custom_phones: ['919876543210', ...]
    # }

    # Status lifecycle
    status = Column(String(20), default='draft', nullable=False)
    # draft → scheduled → running → completed | paused | failed | cancelled

    # Send stats
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)

    # Rate-limit batching
    daily_limit = Column(Integer, default=1000)
    sends_per_minute = Column(Integer, default=50)
    current_batch_day = Column(Integer, default=1)

    # Provider
    provider = Column(String(50), default='META_WHATSAPP')

    # Notes
    notes = Column(Text)

    # Audit
    created_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    paused_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    template = relationship('WhatsAppTemplate')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_staff_id])
    logs = relationship('WhatsAppCampaignLog', back_populates='campaign', lazy='dynamic')

    def __repr__(self):
        return f'<WhatsAppCampaign {self.name} status={self.status}>'

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'status': self.status,
            'template_id': self.template_id,
            'template_name': self.template.name if self.template else None,
            'filters': self.filters or {},
            'total_recipients': self.total_recipients,
            'sent_count': self.sent_count, 'delivered_count': self.delivered_count,
            'failed_count': self.failed_count, 'pending_count': self.pending_count,
            'provider': self.provider,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class WhatsAppCampaignLog(Base):
    """
    Per-recipient log for a campaign send.
    One row per phone number per campaign.
    """
    __tablename__ = 'whatsapp_campaign_logs'

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('whatsapp_campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey('whatsapp_templates.id'), nullable=True)

    # Recipient
    phone = Column(String(20), nullable=False)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True, index=True)
    recipient_name = Column(String(200))

    # Delivery
    status = Column(String(20), default='queued', nullable=False)
    # queued, sent, delivered, read, failed, skipped
    wamid = Column(String(200))  # Meta message ID
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Timestamps
    queued_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    failed_at = Column(DateTime)

    campaign = relationship('WhatsAppCampaign', back_populates='logs')
    template = relationship('WhatsAppTemplate', back_populates='campaign_logs')

    def __repr__(self):
        return f'<WhatsAppCampaignLog campaign={self.campaign_id} phone={self.phone} status={self.status}>'


class WAInbox(Base):
    """
    Incoming WhatsApp messages received via Meta Cloud API webhook.
    DC Protocol Apr 2026: Stores all inbound messages, auto-links to CRM leads by phone.
    DC Protocol Apr 2026 (CRM Extension): Adds assignment, category, status, lead & ticket linking.
    """
    __tablename__ = 'wa_inbox'

    id              = Column(Integer, primary_key=True)
    wamid           = Column(String(100), unique=True, nullable=True)
    from_phone      = Column(String(30), nullable=False, index=True)
    from_name       = Column(String(200), nullable=True)
    message_type    = Column(String(30), default='text')
    body_text       = Column(Text, nullable=True)
    media_url       = Column(Text, nullable=True)
    media_mime_type = Column(String(100), nullable=True)
    lead_id         = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True, index=True)
    is_read         = Column(Boolean, nullable=False, default=False)
    replied         = Column(Boolean, nullable=False, default=False)
    replied_at      = Column(DateTime, nullable=True)
    replied_by_id   = Column(Integer, nullable=True)
    received_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_payload     = Column(Text, nullable=True)

    # CRM Extension columns
    dept_code           = Column(String(50), nullable=True)
    assigned_to_emp_id  = Column(Integer, nullable=True)
    assigned_at         = Column(DateTime, nullable=True)
    target_date         = Column(Date, nullable=True)
    category_code       = Column(String(50), nullable=True)
    status              = Column(String(30), nullable=True, default='new')
    crm_lead_id         = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True)
    service_ticket_id   = Column(Integer, nullable=True)
    assigned_notes      = Column(Text, nullable=True)
    auto_replied        = Column(Boolean, nullable=False, default=False)
    auto_replied_at     = Column(DateTime, nullable=True)

    def __repr__(self):
        return f'<WAInbox from={self.from_phone} type={self.message_type} read={self.is_read}>'

    def to_dict(self):
        return {
            'id':                  self.id,
            'wamid':               self.wamid,
            'from_phone':          self.from_phone,
            'from_name':           self.from_name,
            'message_type':        self.message_type,
            'body_text':           self.body_text,
            'media_url':           self.media_url,
            'media_mime_type':     self.media_mime_type,
            'lead_id':             self.lead_id,
            'is_read':             self.is_read,
            'replied':             self.replied,
            'replied_at':          self.replied_at.isoformat() if self.replied_at else None,
            'received_at':         self.received_at.isoformat() if self.received_at else None,
            'dept_code':           self.dept_code,
            'assigned_to_emp_id':  self.assigned_to_emp_id,
            'assigned_at':         self.assigned_at.isoformat() if self.assigned_at else None,
            'target_date':         self.target_date.isoformat() if self.target_date else None,
            'category_code':       self.category_code,
            'status':              self.status or 'new',
            'crm_lead_id':         self.crm_lead_id,
            'service_ticket_id':   self.service_ticket_id,
            'assigned_notes':      self.assigned_notes,
            'auto_replied':        self.auto_replied,
            'auto_replied_at':     self.auto_replied_at.isoformat() if self.auto_replied_at else None,
        }
