"""
Support Ticketing System Models
Complete implementation matching pre-migration Flask system
DC Protocol Jan 2026: Enhanced with EV Service workflow support
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, Float, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime, timedelta


class ServiceTicket(Base):
    """
    Main support ticket model with SLA tracking
    DC Protocol Jan 2026: Enhanced for EV Service workflow with:
    - Partner/Website ticket sources
    - Technical vs Spares categorization
    - Multi-stage workflow (acknowledge, diagnose, procure, close)
    - TAT management with working hours calculation
    """
    __tablename__ = 'service_ticket'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(String(20), unique=True, nullable=False, index=True)
    
    # User and assignment
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)
    assigned_to = Column(String(12), ForeignKey('user.id'), nullable=True, index=True)
    
    # Ticket details
    issue_category = Column(String(100), nullable=False)
    issue_description = Column(Text, nullable=False)
    priority = Column(String(20), default='Medium', nullable=False)
    
    # Status tracking
    status = Column(String(20), default='Open', nullable=False, index=True)
    
    # Timestamps
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_date = Column(DateTime, nullable=True)
    in_progress_date = Column(DateTime, nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    closed_date = Column(DateTime, nullable=True)
    
    # SLA tracking (24 hours from creation)
    sla_deadline = Column(DateTime, nullable=False)
    sla_status = Column(String(20), default='Within SLA', nullable=False)
    escalated_date = Column(DateTime, nullable=True)
    escalated_to = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Admin response tracking
    admin_response = Column(Text, nullable=True)
    last_response_date = Column(DateTime, nullable=True)
    
    # Resolution details
    resolution_summary = Column(Text, nullable=True)
    resolution_time_hours = Column(Float, nullable=True)
    customer_satisfaction = Column(Integer, nullable=True)
    
    # Security and tracking
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(200), nullable=True)
    
    # DC Protocol Jan 2026: Enhanced EV Service Ticket Fields
    # Ticket type and workflow
    ticket_type = Column(String(30), default='general', nullable=True, index=True)  # technical, spares, general
    sub_status = Column(String(50), default='new', nullable=True, index=True)  # new, acknowledged, diagnosing, awaiting_spares, procurement_in_progress, ready_for_work, work_complete, closed
    
    # Partner/Source tracking
    partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True, index=True)
    source_channel = Column(String(50), default='website', nullable=True)  # partner_portal, website, phone, email
    
    # Service team assignment
    service_manager_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    service_technician_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    # TAT (Turn Around Time) management
    tat_committed_at = Column(DateTime, nullable=True)
    tat_due_at = Column(DateTime, nullable=True)
    tat_base_hours = Column(Integer, default=24, nullable=True)  # Base TAT in working hours
    tat_extension_hours = Column(Integer, default=0, nullable=True)  # Extension for spares
    
    # Spares workflow
    spares_required = Column(Boolean, default=False, nullable=True)
    diagnosed_at = Column(DateTime, nullable=True)
    diagnosis_notes = Column(Text, nullable=True)
    spare_requested_at = Column(DateTime, nullable=True)
    spare_acknowledged_at = Column(DateTime, nullable=True)
    spare_released_at = Column(DateTime, nullable=True)
    
    # Work completion tracking
    work_completed_at = Column(DateTime, nullable=True)
    
    # Customer/Product details
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(200), nullable=True)
    customer_address = Column(Text, nullable=True)
    product_name = Column(String(200), nullable=True)
    product_serial = Column(String(100), nullable=True)
    product_model = Column(String(100), nullable=True)
    warranty_status = Column(String(50), nullable=True)  # under_warranty, out_of_warranty, amc
    warranty_invoice_number = Column(String(100), nullable=True)
    warranty_sale_date = Column(Date, nullable=True)
    warranty_motor_number = Column(String(100), nullable=True)
    warranty_chassis_number = Column(String(100), nullable=True)
    warranty_model = Column(String(150), nullable=True)
    warranty_notes = Column(Text, nullable=True)
    assigned_department_id = Column(Integer, ForeignKey('staff_departments.id'), nullable=True)

    # DC Protocol (Task #53, May 2026): Company scope for the DAR.
    # Backfilled at startup from service_technician / service_manager → base_company_id,
    # else from partner.company_id. Nullable for legacy rows that pre-date company tagging.
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='SET NULL'), nullable=True, index=True)

    # Relationships
    user = relationship('User', foreign_keys=[user_id], backref='raised_tickets')
    assigned_admin = relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')
    escalated_admin = relationship('User', foreign_keys=[escalated_to], backref='escalated_tickets')
    partner = relationship('OfficialPartner', foreign_keys=[partner_id], backref='service_tickets')
    service_manager = relationship('StaffEmployee', foreign_keys=[service_manager_id], backref='managed_tickets')
    service_technician = relationship('StaffEmployee', foreign_keys=[service_technician_id], backref='assigned_service_tickets')
    assigned_department = relationship('StaffDepartment', foreign_keys=[assigned_department_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('Open', 'In Progress', 'Resolved', 'Closed', 'Cancelled')", name='valid_ticket_status'),
        CheckConstraint("priority IN ('Low', 'Medium', 'High', 'Critical')", name='valid_ticket_priority'),
        CheckConstraint("sla_status IN ('Within SLA', 'SLA Breached', 'Escalated')", name='valid_sla_status'),
        CheckConstraint("customer_satisfaction >= 1 AND customer_satisfaction <= 5", name='valid_satisfaction_rating'),
        Index('idx_service_ticket_partner', 'partner_id'),
        Index('idx_service_ticket_type_status', 'ticket_type', 'sub_status'),
        Index('idx_service_ticket_spares', 'spares_required', 'sub_status'),
    )
    
    def __repr__(self):
        return f'<ServiceTicket {self.ticket_id}: {self.status}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses
        DC Protocol Feb 2026: Enhanced with defensive coding and web/mobile parity fields
        """
        # DC_DEFENSIVE_001: Safe relationship access to prevent serialization errors
        service_manager_name = None
        if self.service_manager_id:
            try:
                service_manager_name = getattr(self.service_manager, 'full_name', None) if self.service_manager else None
            except Exception:
                pass
        
        service_technician_name = None
        if self.service_technician_id:
            try:
                service_technician_name = getattr(self.service_technician, 'full_name', None) if self.service_technician else None
            except Exception:
                pass
        
        partner_name = None
        partner_obj = None
        if self.partner_id:
            try:
                if self.partner:
                    partner_name = getattr(self.partner, 'partner_name', None)
                    partner_obj = {
                        'id': self.partner.id,
                        'partner_name': partner_name,
                        'category': getattr(self.partner, 'category', None),
                        'category_label': getattr(self.partner, 'category_label', getattr(self.partner, 'category', None))
                    }
            except Exception:
                pass

        assigned_department_name = None
        if self.assigned_department_id:
            try:
                dept = self.assigned_department
                assigned_department_name = dept.name if dept else None
            except Exception:
                pass

        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'ticket_number': self.ticket_id,
            'user_id': self.user_id,
            'ticket_type': self.ticket_type,
            'sub_status': self.sub_status,
            'issue_category': self.issue_category,
            'issue_description': self.issue_description,
            'priority': self.priority,
            'status': self.status,
            'partner_id': self.partner_id,
            'partner_name': partner_name,
            'partner': partner_obj,
            'source_channel': self.source_channel,
            'spares_required': self.spares_required,
            'tat_due_at': self.tat_due_at.isoformat() if self.tat_due_at else None,
            'sla_status': self.sla_status,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_mobile': self.customer_phone,
            'customer_email': self.customer_email,
            'customer_address': self.customer_address,
            'product_name': self.product_name,
            'product_serial': self.product_serial,
            'product_model': self.product_model,
            'vehicle_number': self.product_serial,
            'vehicle_model': self.product_model,
            'warranty_status': self.warranty_status,
            'assigned_department_id': self.assigned_department_id,
            'assigned_department_name': assigned_department_name,
            'warranty_invoice_number': self.warranty_invoice_number,
            'warranty_sale_date': self.warranty_sale_date.isoformat() if self.warranty_sale_date else None,
            'warranty_motor_number': self.warranty_motor_number,
            'warranty_chassis_number': self.warranty_chassis_number,
            'warranty_model': self.warranty_model,
            'warranty_notes': self.warranty_notes,
            'diagnosis_notes': self.diagnosis_notes,
            'resolution_summary': self.resolution_summary,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_at': self.created_date.isoformat() if self.created_date else None,
            'resolved_date': self.resolved_date.isoformat() if self.resolved_date else None,
            'service_manager_id': self.service_manager_id,
            'service_manager_name': service_manager_name,
            'service_technician_id': self.service_technician_id,
            'service_technician_name': service_technician_name,
            'assigned_to': self.assigned_to
        }


class TicketComment(Base):
    """
    Ticket comments and responses
    Supports user responses, admin responses, and internal notes
    """
    __tablename__ = 'ticket_comment'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False, index=True)
    
    # Comment details
    comment_text = Column(Text, nullable=False)
    comment_type = Column(String(20), default='user_response', nullable=False)
    
    # User tracking
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Status tracking
    is_visible_to_user = Column(Boolean, default=True, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)
    
    # Security tracking
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(200), nullable=True)
    
    # Relationships
    ticket = relationship('ServiceTicket', backref='comments')
    user = relationship('User', backref='ticket_comments')
    
    __table_args__ = (
        CheckConstraint("comment_type IN ('user_response', 'admin_response', 'internal_note')", 
                       name='valid_comment_type'),
    )
    
    def __repr__(self):
        return f'<TicketComment {self.ticket_id}: {self.comment_type}>'


class TicketAssignment(Base):
    """
    Track ticket assignments and reassignments
    Maintains history of all assignments
    """
    __tablename__ = 'ticket_assignment'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False, index=True)
    
    # Assignment details
    assigned_from = Column(String(12), ForeignKey('user.id'), nullable=True)
    assigned_to = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Assignment tracking
    assigned_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    assignment_reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Completion tracking
    completed_date = Column(DateTime, nullable=True)
    
    # Relationships
    ticket = relationship('ServiceTicket', backref='assignments')
    assigner = relationship('User', foreign_keys=[assigned_from], backref='assignments_made')
    assignee = relationship('User', foreign_keys=[assigned_to], backref='assignments_received')
    
    def __repr__(self):
        return f'<TicketAssignment {self.ticket_id} → {self.assigned_to}>'


class TicketAttachment(Base):
    """
    File attachments for support tickets
    Stores file metadata and paths
    DC Protocol Jan 2026: Enhanced with media type, compression support
    """
    __tablename__ = 'ticket_attachment'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False, index=True)
    
    # File details
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # DC Protocol Jan 2026: Media type classification
    media_type = Column(String(20), default='image', nullable=False)  # image, video, document
    
    # Upload tracking
    uploaded_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    uploaded_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    uploaded_by_partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Security
    is_scanned = Column(Boolean, default=False, nullable=False)
    scan_status = Column(String(20), default='Pending', nullable=True)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    # DC Protocol Jan 2026: Compression tracking
    processing_status = Column(String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    original_checksum = Column(String(64), nullable=True)
    compressed_file_path = Column(String(500), nullable=True)
    compressed_file_size = Column(Integer, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    video_duration_seconds = Column(Float, nullable=True)  # For video files
    
    # Relationships
    ticket = relationship('ServiceTicket', backref='attachments')
    uploader = relationship('User', foreign_keys=[uploaded_by], backref='uploaded_attachments')
    staff_uploader = relationship('StaffEmployee', foreign_keys=[uploaded_by_staff_id], backref='ticket_attachments')
    partner_uploader = relationship('OfficialPartner', foreign_keys=[uploaded_by_partner_id], backref='ticket_attachments')
    
    __table_args__ = (
        Index('idx_ticket_attachment_type', 'ticket_id', 'media_type'),
    )
    
    def __repr__(self):
        return f'<TicketAttachment {self.original_filename}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'file_path': self.file_path,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'media_type': self.media_type,
            'download_filename': self.download_filename,
            'processing_status': self.processing_status,
            'compressed_file_path': self.compressed_file_path,
            'compressed_file_size': self.compressed_file_size,
            'video_duration_seconds': self.video_duration_seconds,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }


class TicketLog(Base):
    """
    Audit trail for all ticket actions
    Tracks changes and maintains complete history
    DC Protocol Jan 2026: Extended action types for EV service workflow
    """
    __tablename__ = 'ticket_log'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(50), nullable=False)
    action_description = Column(Text, nullable=False)
    
    # User tracking - performed_by is nullable for staff-only actions (uses staff_performer_id instead)
    performed_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Change tracking
    old_value = Column(String(200), nullable=True)
    new_value = Column(String(200), nullable=True)
    
    # Additional context
    comments = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # DC Protocol Jan 2026: Staff performer tracking
    staff_performer_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    # Relationships
    ticket = relationship('ServiceTicket', backref='activity_logs')
    user = relationship('User', backref='ticket_actions')
    staff_performer = relationship('StaffEmployee', backref='ticket_log_actions')
    
    def __repr__(self):
        return f'<TicketLog {self.ticket_id}: {self.action_type}>'


class ServiceTicketSpareRequest(Base):
    """
    DC Protocol Jan 2026: Spare parts request tracking for service tickets
    Tracks spare requirements, stock availability, and procurement status
    Enhanced Jan 2026: GST pricing fields with stock item integration
    """
    __tablename__ = 'service_ticket_spare_request'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False, index=True)
    
    # Spare item details
    spare_item_name = Column(String(200), nullable=False)
    spare_item_code = Column(String(100), nullable=True)
    spare_description = Column(Text, nullable=True)
    quantity_required = Column(Integer, default=1, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    
    # Stock item integration (links to StockItemMaster for auto-populate)
    stock_item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)
    
    # Pricing fields (auto-populated from stock, can be overridden)
    unit_price = Column(Float, default=0.0, nullable=True)
    gst_rate = Column(Float, default=18.0, nullable=True)
    gst_amount = Column(Float, default=0.0, nullable=True)
    total_with_gst = Column(Float, default=0.0, nullable=True)
    hsn_code = Column(String(20), nullable=True)
    price_overridden = Column(Boolean, default=False, nullable=False)
    
    # Vendor settlement tracking
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True, index=True)
    vendor_invoice_number = Column(String(100), nullable=True)
    vendor_invoice_amount = Column(Float, nullable=True)
    vendor_settled = Column(Boolean, default=False, nullable=False)
    vendor_settled_at = Column(DateTime, nullable=True)
    
    # Stock and procurement status
    stock_available = Column(Boolean, default=False, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=True)
    procurement_status = Column(String(50), default='pending', nullable=False)  # pending, acknowledged, ordered, received, released
    vendor_name = Column(String(200), nullable=True)
    expected_delivery_date = Column(DateTime, nullable=True)
    actual_cost = Column(Float, nullable=True)
    
    # TAT extension
    tat_extension_hours = Column(Integer, default=48, nullable=False)  # Default +2 days for spares
    
    # Workflow tracking
    requested_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    acknowledged_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    released_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    ordered_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    
    # Notes
    request_notes = Column(Text, nullable=True)
    acknowledgment_notes = Column(Text, nullable=True)
    release_notes = Column(Text, nullable=True)
    
    # DC Protocol Jan 2026: Media files for spare requests (images/video)
    media_files = Column(JSONB, default=list, nullable=True)  # List of {type, filename, path, uploaded_at}
    
    # DC Protocol Jan 2026: Custom spares support
    # Allows free-text item entry, later verified/mapped to actual stock items by procurement
    is_custom = Column(Boolean, default=False, nullable=False)  # True if user-entered free-text item
    original_item_name = Column(String(200), nullable=True)  # Original name before verification
    verified_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Zynova Marketplace integration (March 2026)
    marketplace_spare_id       = Column(Integer, ForeignKey('marketplace_spares.id', ondelete='SET NULL'), nullable=True)
    marketplace_po_id          = Column(Integer, ForeignKey('marketplace_purchase_orders.id', ondelete='SET NULL'), nullable=True)
    marketplace_procurement_id = Column(Integer, ForeignKey('marketplace_procurement_requests.id', ondelete='SET NULL'), nullable=True)
    discount_mode              = Column(String(20), nullable=True)  # 'mnr','vgk','dealer','student', None
    discount_id                = Column(String(50), nullable=True)  # actual ID entered (e.g. VGK07108079)

    # DC Protocol Mar 2026: Basket-style price breakup columns
    catalog_price    = Column(Float, nullable=True)   # Original dealer/catalog price per unit (before any discount)
    discount_pct     = Column(Float, nullable=True)   # Discount percentage applied (e.g. 3.0 for MNR 3%)
    discount_amount  = Column(Float, nullable=True)   # Discount amount per unit
    net_before_tax   = Column(Float, nullable=True)   # Price after discount, before GST, per unit

    # DC Protocol Mar 2026: Customer payment tracking per spare item
    # procurement_status extended: payment_received, waiting_for_spares, dispatched
    payment_amount    = Column(Float, nullable=True)         # Amount customer paid for this spare
    payment_mode      = Column(String(20), nullable=True)    # CASH/UPI/BANK/CARD/NEFT
    payment_reference = Column(String(100), nullable=True)   # Transaction reference / UTR
    payment_date      = Column(DateTime, nullable=True)      # Date of payment
    payment_notes     = Column(Text, nullable=True)          # Additional payment notes
    income_entry_id   = Column(Integer, nullable=True)       # FK income_entries.id (soft ref — no FK constraint to avoid circular dep)
    dispatched_at     = Column(DateTime, nullable=True)      # When parts handed to technician
    dispatched_by_id  = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)

    # DC Protocol Mar 2026: Warranty tracking per spare item
    is_warranty             = Column(Boolean, default=False, nullable=False)
    warranty_invoice_number = Column(String(100), nullable=True)   # Original purchase invoice
    warranty_sale_date      = Column(Date, nullable=True)           # Date of original sale
    warranty_motor_number   = Column(String(100), nullable=True)
    warranty_chassis_number = Column(String(100), nullable=True)
    warranty_model          = Column(String(150), nullable=True)    # Vehicle model/variant
    warranty_notes          = Column(Text, nullable=True)

    # DC-VENDOR-REPAIR-TRACKER-001: Vendor repair tracking (June 2026)
    vendor_repair_status   = Column(String(50), nullable=True)       # sent / waiting_for_repair / repaired_received / cancelled
    sent_to_vendor_date    = Column(DateTime, nullable=True)          # When physically dispatched to vendor
    sent_courier_name      = Column(String(100), nullable=True)       # Outbound courier name
    sent_awb_number        = Column(String(100), nullable=True)       # Outbound AWB / tracking number
    sent_by_staff_id       = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    expected_return_date   = Column(Date, nullable=True)              # Vendor's promised return date
    return_received_date   = Column(DateTime, nullable=True)          # When repaired part came back
    return_courier_name    = Column(String(100), nullable=True)       # Return courier
    return_awb_number      = Column(String(100), nullable=True)       # Return AWB
    vendor_repair_cost     = Column(Float, nullable=True)             # What vendor charges for repair (₹)
    last_action_date       = Column(DateTime, nullable=True)          # Auto-updated on every status change
    vendor_repair_notes    = Column(Text, nullable=True)              # Notes on repair progress
    whatsapp_log           = Column(JSONB, nullable=True)             # [{sent_at, sent_by, phone, message, context}]

    # DC-CUSTOMER-SPARE-001 (Jun 2026): Customer-Supplied Parts tracking
    spare_source      = Column(String(20), nullable=False, default='company', server_default='company')
    # 'company' = MNR procures the part | 'customer' = customer brings their own part
    repair_route      = Column(String(30), nullable=True)
    # NULL = normal dispatch | 'vendor_external' = sent to vendor for repair | 'internal' = repaired in-house
    sub_ticket_number = Column(String(30), nullable=True)
    # Auto-generated when a spare (company or customer) is sent to vendor: TKT{ticket_id}-R{n}

    # Relationships
    ticket = relationship('ServiceTicket', backref='spare_requests')
    verified_by = relationship('StaffEmployee', foreign_keys=[verified_by_id], backref='spare_verifications')
    stock_item = relationship('StockItemMaster', foreign_keys=[stock_item_id], backref='spare_requests')
    vendor = relationship('VendorMaster', foreign_keys=[vendor_id], backref='spare_requests')
    requested_by = relationship('StaffEmployee', foreign_keys=[requested_by_id], backref='spare_requests_created')
    acknowledged_by = relationship('StaffEmployee', foreign_keys=[acknowledged_by_id], backref='spare_requests_acknowledged')
    released_by = relationship('StaffEmployee', foreign_keys=[released_by_id], backref='spare_requests_released')
    dispatched_by = relationship('StaffEmployee', foreign_keys=[dispatched_by_id], backref='spare_requests_dispatched')
    sent_by_vendor_repair = relationship('StaffEmployee', foreign_keys=[sent_by_staff_id], backref='spare_repair_sends')

    __table_args__ = (
        Index('idx_spare_request_ticket', 'ticket_id'),
        Index('idx_spare_request_status', 'procurement_status'),
        Index('idx_spare_request_stock_item', 'stock_item_id'),
        Index('idx_spare_request_vendor', 'vendor_id'),
    )
    
    def __repr__(self):
        return f'<ServiceTicketSpareRequest {self.id}: {self.spare_item_name} ({self.procurement_status})>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'spare_item_name': self.spare_item_name,
            'spare_item_code': self.spare_item_code,
            'quantity_required': self.quantity_required,
            'stock_available': self.stock_available,
            'procurement_status': self.procurement_status,
            'tat_extension_hours': self.tat_extension_hours,
            'estimated_cost': self.estimated_cost,
            'actual_cost': self.actual_cost,
            'stock_item_id': self.stock_item_id,
            'unit_price': self.unit_price,
            'gst_rate': self.gst_rate,
            'gst_amount': self.gst_amount,
            'total_with_gst': self.total_with_gst,
            'hsn_code': self.hsn_code,
            'price_overridden': self.price_overridden,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor_name,
            'vendor_invoice_number': self.vendor_invoice_number,
            'vendor_invoice_amount': self.vendor_invoice_amount,
            'vendor_settled': self.vendor_settled,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'vendor_settled_at': self.vendor_settled_at.isoformat() if self.vendor_settled_at else None,
            'is_custom': self.is_custom,
            'original_item_name': self.original_item_name,
            'verified_by_id': self.verified_by_id,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'verification_notes': self.verification_notes,
            'media_files': self.media_files or [],
            'request_notes': self.request_notes,
            'marketplace_spare_id': self.marketplace_spare_id,
            'marketplace_po_id': self.marketplace_po_id,
            'marketplace_procurement_id': self.marketplace_procurement_id,
            'discount_mode': self.discount_mode,
            'discount_id': self.discount_id,
            # DC Protocol Mar 2026: Payment & dispatch tracking
            'payment_amount': self.payment_amount,
            'payment_mode': self.payment_mode,
            'payment_reference': self.payment_reference,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_notes': self.payment_notes,
            'income_entry_id': self.income_entry_id,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
            'dispatched_by_id': self.dispatched_by_id,
            # Warranty fields
            'is_warranty': self.is_warranty or False,
            'warranty_invoice_number': self.warranty_invoice_number,
            'warranty_sale_date': self.warranty_sale_date.isoformat() if self.warranty_sale_date else None,
            'warranty_motor_number': self.warranty_motor_number,
            'warranty_chassis_number': self.warranty_chassis_number,
            'warranty_model': self.warranty_model,
            'warranty_notes': self.warranty_notes,
            # DC-VENDOR-REPAIR-TRACKER-001
            'vendor_repair_status': self.vendor_repair_status,
            'sent_to_vendor_date': self.sent_to_vendor_date.isoformat() if self.sent_to_vendor_date else None,
            'sent_courier_name': self.sent_courier_name,
            'sent_awb_number': self.sent_awb_number,
            'sent_by_staff_id': self.sent_by_staff_id,
            'expected_return_date': self.expected_return_date.isoformat() if self.expected_return_date else None,
            'return_received_date': self.return_received_date.isoformat() if self.return_received_date else None,
            'return_courier_name': self.return_courier_name,
            'return_awb_number': self.return_awb_number,
            'vendor_repair_cost': float(self.vendor_repair_cost) if self.vendor_repair_cost is not None else None,
            'last_action_date': self.last_action_date.isoformat() if self.last_action_date else None,
            'vendor_repair_notes': self.vendor_repair_notes,
            'whatsapp_log': self.whatsapp_log or [],
            # DC-CUSTOMER-SPARE-001
            'spare_source': self.spare_source or 'company',
            'repair_route': self.repair_route,
            'sub_ticket_number': self.sub_ticket_number,
        }


class ServiceTicketSpareTransaction(Base):
    """
    DC Protocol Mar 2026: Multi-transaction payment records for spare requests.
    Mirrors CRM deal transaction pattern — one spare can have multiple partial payments.
    Each transaction creates a PENDING IncomeEntry that Accounts must CONFIRM.
    Dispatch is blocked until ALL linked income entries are CONFIRMED (or spare is_warranty=True).
    """
    __tablename__ = 'service_ticket_spare_transactions'

    id                  = Column(Integer, primary_key=True)
    spare_request_id    = Column(Integer, ForeignKey('service_ticket_spare_request.id', ondelete='CASCADE'), nullable=False, index=True)
    ticket_id           = Column(Integer, nullable=False, index=True)       # denormalized
    transaction_number  = Column(String(30), unique=True, nullable=False, index=True)  # SPRTXN-YYMM-NNNN
    amount              = Column(Float, nullable=False)
    payment_mode        = Column(String(20), nullable=False)                # CASH/UPI/NEFT/CARD/BANK/CHEQUE
    payment_reference   = Column(String(100), nullable=True)
    payment_date        = Column(DateTime, nullable=True)
    payment_notes       = Column(Text, nullable=True)
    income_entry_id     = Column(Integer, nullable=True)                   # soft FK income_entries.id
    income_entry_number = Column(String(30), nullable=True)                # denormalized for display
    income_entry_status = Column(String(20), default='PENDING', nullable=False)  # PENDING / CONFIRMED
    created_by_id       = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)

    spare_request = relationship('ServiceTicketSpareRequest', backref='transactions')
    created_by    = relationship('StaffEmployee', foreign_keys=[created_by_id], backref='spare_transactions_created')

    __table_args__ = (
        Index('idx_spare_txn_spare', 'spare_request_id'),
        Index('idx_spare_txn_ie', 'income_entry_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'spare_request_id': self.spare_request_id,
            'ticket_id': self.ticket_id,
            'transaction_number': self.transaction_number,
            'amount': self.amount,
            'payment_mode': self.payment_mode,
            'payment_reference': self.payment_reference,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_notes': self.payment_notes,
            'income_entry_id': self.income_entry_id,
            'income_entry_number': self.income_entry_number,
            'income_entry_status': self.income_entry_status,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.full_name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ServiceTicketPartnerHistory(Base):
    """
    DC Protocol Jan 2026: Audit trail for partner reassignments on service tickets
    Tracks all partner changes with reason/comment for accountability
    """
    __tablename__ = 'service_ticket_partner_history'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False, index=True)
    
    # Partner change details
    old_partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    new_partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    
    # Reason for change (required for audit - enforced at DB level)
    change_reason = Column(Text, nullable=False)
    
    # Who made the change
    changed_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    changed_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Timestamp
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # IP tracking for audit
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    ticket = relationship('ServiceTicket', backref='partner_history')
    old_partner = relationship('OfficialPartner', foreign_keys=[old_partner_id])
    new_partner = relationship('OfficialPartner', foreign_keys=[new_partner_id])
    changed_by_staff = relationship('StaffEmployee', foreign_keys=[changed_by_staff_id])
    
    __table_args__ = (
        Index('idx_partner_history_ticket', 'ticket_id'),
        Index('idx_partner_history_date', 'changed_at'),
    )
    
    def __repr__(self):
        return f'<ServiceTicketPartnerHistory {self.id}: Ticket {self.ticket_id} - {self.old_partner_id} -> {self.new_partner_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'old_partner_id': self.old_partner_id,
            'new_partner_id': self.new_partner_id,
            'old_partner_name': self.old_partner.partner_name if self.old_partner else None,
            'new_partner_name': self.new_partner.partner_name if self.new_partner else None,
            'change_reason': self.change_reason,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'changed_by_staff_id': self.changed_by_staff_id
        }


class ServiceTicketBilling(Base):
    """
    DC Protocol Jan 2026: Billing/Invoice model for service tickets
    Supports both formal GST invoices and simple e-bills/estimations
    Integrates with SFMS for accounting
    """
    __tablename__ = 'service_ticket_billing'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), unique=True, nullable=False, index=True)
    
    # Document type
    document_type = Column(String(20), default='bill', nullable=False)  # invoice, bill
    is_gst_invoice = Column(Boolean, default=False, nullable=False)
    
    # Invoice/Bill numbers
    invoice_number = Column(String(50), unique=True, nullable=True)  # For formal invoices
    bill_reference = Column(String(50), nullable=True)  # For simple bills
    
    # Company for invoice (if GST invoice, link to company for proper GST details)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True)
    
    # Service center that performed the work
    service_center_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    
    # Customer details (snapshot for billing)
    billing_customer_name = Column(String(200), nullable=True)
    billing_customer_phone = Column(String(20), nullable=True)
    billing_customer_address = Column(Text, nullable=True)
    billing_customer_gstin = Column(String(20), nullable=True)
    
    # Financial amounts (DECIMAL precision for accounting)
    service_amount = Column(Float, default=0.0, nullable=False)
    spares_amount = Column(Float, default=0.0, nullable=False)
    labour_amount = Column(Float, default=0.0, nullable=False)
    taxable_amount = Column(Float, default=0.0, nullable=False)
    
    # GST breakdown (for invoices)
    cgst_rate = Column(Float, default=0.0, nullable=True)
    cgst_amount = Column(Float, default=0.0, nullable=True)
    sgst_rate = Column(Float, default=0.0, nullable=True)
    sgst_amount = Column(Float, default=0.0, nullable=True)
    igst_rate = Column(Float, default=0.0, nullable=True)
    igst_amount = Column(Float, default=0.0, nullable=True)
    
    # Total and payment
    total_amount = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=True)
    round_off = Column(Float, default=0.0, nullable=True)
    net_payable = Column(Float, default=0.0, nullable=False)

    # Coupon discount (DC-BILLING-COUPON Mar 2026) — applied BEFORE GST
    coupon_code = Column(String(50), nullable=True)
    coupon_discount_pct = Column(Float, default=0.0, nullable=True, server_default=text('0'))

    # Manual discount (DC-BILLING-MANUAL-DISC Mar 2026) — applied AFTER GST, flat rupee amount
    manual_discount_amount = Column(Float, default=0.0, nullable=True, server_default=text('0'))
    manual_discount_note = Column(String(200), nullable=True)
    
    # Billing lifecycle status
    status = Column(String(20), default='draft', nullable=False)  # draft, confirmed, cancelled
    
    # Payment details
    payment_mode = Column(String(50), nullable=True)  # cash, upi, card, neft
    payment_reference = Column(String(100), nullable=True)
    payment_status = Column(String(30), default='pending', nullable=False)  # pending, partial, paid
    amount_paid = Column(Float, default=0.0, nullable=True)
    amount_due = Column(Float, default=0.0, nullable=True)
    
    # Warranty info
    warranty_status = Column(String(50), nullable=True)  # under_warranty, out_of_warranty, amc
    warranty_claim_amount = Column(Float, default=0.0, nullable=True)
    
    # SFMS integration
    sfms_status = Column(String(30), default='draft', nullable=False)  # draft, pending_sfms, posted
    sfms_journal_id = Column(Integer, nullable=True)
    sfms_posted_at = Column(DateTime, nullable=True)
    sfms_error = Column(Text, nullable=True)
    
    # Receipt/Invoice PDF
    receipt_pdf_path = Column(String(500), nullable=True)
    invoice_pdf_path = Column(String(500), nullable=True)
    
    # HSN summary (JSON for multiple items)
    hsn_summary = Column(Text, nullable=True)  # JSON string of HSN codes used
    
    # Audit
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    posted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    # Relationships
    ticket = relationship('ServiceTicket', backref='billing', uselist=False)
    company = relationship('AssociatedCompany', backref='service_ticket_billings')
    service_center = relationship('OfficialPartner', foreign_keys=[service_center_id], backref='service_billings')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], backref='created_billings')
    posted_by = relationship('StaffEmployee', foreign_keys=[posted_by_id], backref='posted_billings')
    
    __table_args__ = (
        Index('idx_billing_ticket', 'ticket_id'),
        Index('idx_billing_sfms_status', 'sfms_status'),
        Index('idx_billing_payment_status', 'payment_status'),
    )
    
    def __repr__(self):
        return f'<ServiceTicketBilling {self.id}: {self.document_type} - {self.total_amount}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses
        
        DC Protocol Jan 2026: Enhanced to include document titles and reference numbers
        - document_title: 'Tax Invoice' for document_type='invoice', 'Estimated Bill' for 'estimate'
        - reference_number: INV-YYYYMMDD-XXXX or EST-YYYYMMDD-XXXX based on document_type
        """
        is_invoice = self.document_type == 'invoice'
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'document_type': self.document_type,
            'document_title': 'Tax Invoice' if is_invoice else 'Estimated Bill',
            'is_gst_invoice': self.is_gst_invoice or is_invoice,
            'invoice_number': self.invoice_number,
            'bill_reference': self.bill_reference,
            'reference_number': self.invoice_number if is_invoice else self.bill_reference,
            'status': self.status,
            'service_amount': self.service_amount,
            'spares_amount': self.spares_amount,
            'labour_amount': self.labour_amount,
            'taxable_amount': self.taxable_amount,
            'cgst_rate': self.cgst_rate,
            'cgst_amount': self.cgst_amount,
            'sgst_rate': self.sgst_rate,
            'sgst_amount': self.sgst_amount,
            'igst_rate': self.igst_rate,
            'igst_amount': self.igst_amount,
            'total_amount': self.total_amount,
            'discount_amount': self.discount_amount,
            'coupon_code': self.coupon_code,
            'coupon_discount_pct': float(self.coupon_discount_pct or 0),
            'manual_discount_amount': float(self.manual_discount_amount or 0),
            'manual_discount_note': self.manual_discount_note or '',
            'net_payable': self.net_payable,
            'payment_mode': self.payment_mode,
            'payment_status': self.payment_status,
            'amount_paid': self.amount_paid,
            'warranty_status': self.warranty_status,
            'sfms_status': self.sfms_status,
            'receipt_pdf_path': self.receipt_pdf_path,
            'invoice_pdf_path': self.invoice_pdf_path,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'billing_customer_name': self.billing_customer_name,
            'billing_customer_phone': self.billing_customer_phone,
            'service_center_id': self.service_center_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'generation_date': self.created_at.strftime('%d-%b-%Y %I:%M %p') if self.created_at else None
        }


class ServiceTicketBillingItem(Base):
    """
    DC Protocol Jan 2026: Line items for service ticket billing
    Supports itemized billing with HSN codes for GST calculation
    """
    __tablename__ = 'service_ticket_billing_item'
    
    id = Column(Integer, primary_key=True)
    billing_id = Column(Integer, ForeignKey('service_ticket_billing.id'), nullable=False, index=True)
    
    # Item details
    item_type = Column(String(30), default='service', nullable=False)  # service, spare, labour
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0, nullable=False)
    unit = Column(String(20), default='Nos', nullable=True)
    rate = Column(Float, default=0.0, nullable=False)
    
    # HSN/SAC code for GST
    hsn_code = Column(String(20), nullable=True)
    hsn_description = Column(String(200), nullable=True)
    
    # Specification and color (DC Protocol Jan 2026)
    specification = Column(Text, nullable=True)
    color = Column(String(100), nullable=True)
    serial_numbers = Column(JSONB, nullable=True)
    warranty_info = Column(Text, nullable=True)
    
    # Tax calculation
    taxable_amount = Column(Float, default=0.0, nullable=False)
    tax_rate = Column(Float, default=0.0, nullable=True)  # Combined GST rate
    cgst_rate = Column(Float, default=0.0, nullable=True)
    cgst_amount = Column(Float, default=0.0, nullable=True)
    sgst_rate = Column(Float, default=0.0, nullable=True)
    sgst_amount = Column(Float, default=0.0, nullable=True)
    igst_rate = Column(Float, default=0.0, nullable=True)
    igst_amount = Column(Float, default=0.0, nullable=True)
    
    # Line total
    line_total = Column(Float, default=0.0, nullable=False)
    
    # Warranty adjustment
    is_warranty_covered = Column(Boolean, default=False, nullable=False)
    warranty_discount = Column(Float, default=0.0, nullable=True)
    
    # Spare part reference
    spare_request_id = Column(Integer, ForeignKey('service_ticket_spare_request.id'), nullable=True)

    # Product category — used to determine VGK commission tier at billing coupon time
    # e.g. 'EV Vehicle', 'Solar', or null for spares/labour/service
    product_category = Column(String(50), nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    billing = relationship('ServiceTicketBilling', backref='items')
    spare_request = relationship('ServiceTicketSpareRequest', backref='billing_items')
    
    __table_args__ = (
        Index('idx_billing_item_billing', 'billing_id'),
        Index('idx_billing_item_type', 'item_type'),
    )
    
    def __repr__(self):
        return f'<ServiceTicketBillingItem {self.id}: {self.description} - {self.line_total}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'billing_id': self.billing_id,
            'item_type': self.item_type,
            'description': self.description,
            'quantity': self.quantity,
            'unit': self.unit,
            'rate': self.rate,
            'hsn_code': self.hsn_code,
            'taxable_amount': self.taxable_amount,
            'tax_rate': self.tax_rate,
            'cgst_amount': self.cgst_amount,
            'sgst_amount': self.sgst_amount,
            'line_total': self.line_total,
            'is_warranty_covered': self.is_warranty_covered,
            'specification': self.specification,
            'color': self.color,
            'serial_numbers': self.serial_numbers,
            'warranty_info': self.warranty_info,
            'product_category': self.product_category
        }
