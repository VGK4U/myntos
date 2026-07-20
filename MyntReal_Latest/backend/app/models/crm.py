"""
Universal CRM/Lead Management System Models
DC Protocol: All tables include company_id for multi-company segregation
Supports leads from any category: Real Estate, EV, Solar, Distributorship, etc.
Handlers can be: Staff Employees, Official Partners, or MNR Members
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, Enum, Float, Index, UniqueConstraint, Numeric, text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import pytz
import enum


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


def _si(d):
    """DC-DATE-GUARD-001: safe isoformat — guards against out-of-range years.
    Returns None for any date/datetime that cannot be serialized so one bad
    row never crashes the entire endpoint response."""
    try:
        return d.isoformat() if d else None
    except (ValueError, OverflowError, AttributeError):
        return None


class LeadStatus(enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    LOAN_PROCESS = "loan_process"
    WON = "won"
    PROCESSING = "processing"
    COMPLETED = "completed"
    LOST = "lost"
    ON_HOLD = "on_hold"


class LeadPriority(enum.Enum):
    NORMAL = "normal"
    MEDIUM = "medium"
    HIGH = "high"


class HandlerType(enum.Enum):
    STAFF = "staff"
    PARTNER = "partner"
    MEMBER = "member"
    UNASSIGNED = "unassigned"


class FollowUpType(enum.Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    SITE_VISIT = "site_visit"
    WHATSAPP = "whatsapp"
    OTHER = "other"


class FollowUpStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class CRMLead(BaseModel):
    """
    Universal Lead model for all business categories
    DC Protocol: company_id segregation for multi-company support
    Enhanced: Dec 2025 - Added WhatsApp flags, looking_for, recent_comments, depends_on_staff_id
    """
    __tablename__ = 'crm_leads'
    __table_args__ = (
        Index('ix_crm_leads_company_status', 'company_id', 'status'),
        Index('ix_crm_leads_company_category', 'company_id', 'category_id'),
        Index('ix_crm_leads_company_handler', 'company_id', 'handler_type', 'handler_id'),
        Index('ix_crm_leads_depends_on', 'depends_on_staff_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    phone_primary_whatsapp = Column(Boolean, default=False, nullable=False)
    alternate_phone = Column(String(20), nullable=True)
    phone_secondary_whatsapp = Column(Boolean, default=False, nullable=False)
    
    category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=True)
    
    source = Column(String(100), nullable=True)
    source_details = Column(Text, nullable=True)
    
    status = Column(String(20), default='new', nullable=False)
    priority = Column(String(20), default='medium', nullable=False)
    
    handler_type = Column(String(20), default='unassigned', nullable=False)
    handler_id = Column(String(50), nullable=True)
    
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    looking_for = Column(Text, nullable=True)
    recent_comments = Column(Text, nullable=True)
    
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    
    address = Column(Text, nullable=True)
    area = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    expected_close_date = Column(DateTime, nullable=True)
    actual_close_date = Column(DateTime, nullable=True)
    
    # Deal Value System (3-part: Total, Received, Balance)
    # deal_value retained for backward compatibility, maps to deal_value_total
    deal_value = Column(Float, nullable=True)  # Legacy field - use deal_value_total
    deal_value_total = Column(Float, default=0, nullable=False)  # Overall deal closed value (incl. tax)
    deal_value_excl_tax = Column(Float, default=0, nullable=False)  # Pre-tax value (commission base)
    deal_tax_rate = Column(Float, default=0, nullable=False)        # GST % applied (0/5/12/18/28)
    deal_value_received = Column(Float, default=0, nullable=False)  # Amount received so far
    deal_value_balance = Column(Float, default=0, nullable=False)  # Auto-calculated: total - received
    confirmed_final_value = Column(Float, nullable=True)            # Locked at completion stage — used for all payouts/incentives
    solar_value = Column(Float, nullable=True)                      # DC-SOLAR-VALUE-001: Manual project value for VGK incentive base (set at Balance Received)

    lost_reason = Column(Text, nullable=True)
    
    tags = Column(Text, nullable=True)
    
    last_contact_date = Column(DateTime, nullable=True)
    next_followup_date = Column(DateTime, nullable=True)
    
    depends_on_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    # Multi-handler assignment fields (Dec 2025)
    # DC Protocol: Staff handlers must belong to same company; Partner is cross-company read
    telecaller_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    field_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    associated_partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)
    # Vendor/Partner assignment (Dec 2025) - DC Protocol: vendor_id links to VendorMaster
    # Note: vendor_id is exposed as "Partner" in UI for simplicity
    vendor_id = Column(Integer, ForeignKey('vendor_master.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # MNR Handler assignment (Dec 2025) - Assign leads to MNR members
    # DC Protocol: Links to user table for MNR member assignment (user.id is VARCHAR(12))
    mnr_handler_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)

    # VGK Program fields (DC Protocol Mar 2026)
    # is_vgk_program: marks lead as VGK member onboarding or VGK-attributed deal
    # vgk_field_support_id: VGK_TEAM partner who provided field support for this deal (L3 commission)
    is_vgk_program = Column(Boolean, nullable=False, default=False)
    vgk_field_support_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)
    # DC-VGK-BRAND-INCENTIVE-001 (Jun 2026): optional brand for brand-specific additional incentive
    solar_brand_id = Column(Integer, ForeignKey('vgk_incentive_brands.id', ondelete='SET NULL'), nullable=True, index=True)

    # DC Protocol (Mar 2026): KYC / Document / Banking / Location fields
    aadhaar_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    electricity_bill_number = Column(String(50), nullable=True)
    google_maps_link = Column(Text, nullable=True)
    bank_account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(15), nullable=True)
    subsidy_status = Column(String(30), nullable=True)  # not_applied/applied/under_review/approved/rejected/received
    # Solar-specific fields (Mar 2026)
    application_no = Column(String(50), nullable=True)
    accepted_date = Column(DateTime, nullable=True)
    loan_bank = Column(String(100), nullable=True)
    bank_branch = Column(String(100), nullable=True)
    documents_folder_link = Column(Text, nullable=True)
    material_reach_date = Column(DateTime, nullable=True)
    installation_date = Column(DateTime, nullable=True)
    existing_association = Column(String(50), nullable=True)  # none/partner/vendor/mnr/vgk/customer
    # Solar finance qualification fields (Mar 2026)
    bank_entry_updated = Column(Boolean, nullable=True)       # Customer bank entry updated?
    bank_statement_available = Column(Boolean, nullable=True) # Bank statement available?
    regular_income_available = Column(Boolean, nullable=True) # Regular monthly income available?
    monthly_income = Column(Numeric(12, 2), nullable=True)    # Monthly income (manual entry, Apr 2026)
    co_applicant_name = Column(String(200), nullable=True)    # Co-applicant full name
    co_applicant_phone = Column(String(20), nullable=True)    # Co-applicant phone number
    co_applicant_aadhaar = Column(String(20), nullable=True)  # Co-applicant Aadhaar number
    co_applicant_pan = Column(String(15), nullable=True)      # Co-applicant PAN number
    co_applicant_bank_account = Column(String(30), nullable=True)  # Co-applicant bank account number
    co_applicant_ifsc = Column(String(15), nullable=True)     # Co-applicant IFSC code
    # Solar pipeline status (Mar 2026): tracks project stage post-acceptance
    # Values: bank / procurement_pending / installed / net_meter_pending / bank_loan_completed / subsidy_cleared
    solar_pipeline_status = Column(String(50), nullable=True)
    # Timestamp set whenever solar_pipeline_status is changed (DC_SOLAR_STAGE_DATE_001, Apr 2026)
    solar_pipeline_status_updated_at = Column(DateTime, nullable=True)
    submit_date = Column(Date, nullable=True)  # DC-SUBMIT-DATE-001: Manual submit date for solar leads
    complete_date = Column(Date, nullable=True)  # DC-COMPLETE-DATE-001: Completion/handover date for solar leads
    first_dvr_confirmed_at = Column(DateTime, nullable=True)  # DC-SOLAR-DVR-ADV-20260701-001: system timestamp when DVR advance was created
    first_payment_received_date = Column(Date, nullable=True)  # DC-FIRST-PMT-001: earliest validated crm_lead_transactions.transaction_date for this lead
    # CIBIL validation fields (DC Protocol Apr 2026) — gate for ₹1,000 Solar Advance
    cibil_confirmed = Column(Boolean, default=False, nullable=False, server_default='false')
    cibil_score = Column(Integer, nullable=True)  # Must be >= 600 for advance eligibility
    # DC-CIBIL-DATE-OVERRIDE-001: stamped whenever cibil_score or cibil_confirmed is written
    cibil_score_updated_at = Column(DateTime, nullable=True)

    # EV B2B stage (Apr 2026): tracks EV B2B dealership onboarding stage
    # Values: application_pending / agreement_pending / gst_pending / training_pending / branding_pending / payment_pending / dispatch_pending / confirmation_pending / completed
    ev_b2b_stage = Column(String(50), nullable=True)

    # Solar document generation fields (Apr 2026)
    kw_size = Column(String(10), nullable=True)           # e.g. "3KW"
    discom = Column(String(60), nullable=True)            # e.g. "APEPDCL"
    sc_number = Column(String(40), nullable=True)         # service connection no
    consumer_no = Column(String(40), nullable=True)       # DISCOM consumer no
    sanction_date = Column(DateTime, nullable=True)       # DISCOM sanction date
    mnre_app_ref = Column(String(60), nullable=True)      # PM Surya Ghar App Ref
    discom_reg_no = Column(String(40), nullable=True)     # DISCOM reg no
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    grid_phase = Column(String(20), nullable=True)        # "Single Phase" / "Three Phase"

    # B2B Meta Lead Form fields (Mar 2026)
    investment_capacity = Column(String(100), nullable=True)   # e.g. "Below ₹5 Lakhs" / "₹5-10 Lakhs"
    planning_to_start   = Column(String(100), nullable=True)   # e.g. "Immediately" / "Within 3 months"
    full_time_business  = Column(String(20),  nullable=True)   # e.g. "Yes" / "No" / "Part-time"

    # On Ground Team fields (Ground Source chain — Mar 2026)
    # Handler upliner chain (auto-fetched via referrer_id walk):
    #   L1 SOURCE  (guru_id)    — manual entry by staff
    #   L2 SENIOR  (z_guru_id)  — auto-fetched: upliner of Source
    #   L3 EXTENDED(adi_guru_id)— auto-fetched: upliner of Senior
    #   L4 CORE    (core_id)    — auto-fetched: upliner of Extended
    #   L5 SUPPORT             — manual selection (field_staff / partner)
    # Note: user.id is VARCHAR(12), so these are String columns
    guru_id    = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    z_guru_id  = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    adi_guru_id= Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    core_id    = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    # DC Protocol Fix (Apr 2026): Text-only name storage for partner-chain uplines.
    # When Ground Source is a VGK/official partner (no user FK), guru_id/z_guru_id remain
    # null but the parent partner chain is stored here for display. These are plain text
    # columns — no FK constraint — so partner names persist even if the partner record changes.
    guru_name  = Column(String(200), nullable=True)
    z_guru_name= Column(String(200), nullable=True)
    core_name  = Column(String(200), nullable=True)
    # DC-TEAM-ASSIGN-001 (Jun 2026): OfficialPartner override FKs for L2/L3/L4 slots.
    # When staff manually selects an upline partner (overriding the auto-fetched tree),
    # these store the chosen OfficialPartner.id so commission pipeline can respect the
    # override instead of always walking parent_partner_id.
    team_senior_partner_id   = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)
    team_extended_partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)
    team_core_partner_id     = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)

    # Unified Network Assignment (Mar 2026)
    # DC Protocol: Additive. Preserves mnr_handler_id + vgk_field_support_id for legacy/commission.
    # source_ref_type / field_support_ref_type: 'mnr' | 'vgk' | 'partner' | 'vendor' | 'staff'
    source_ref_type = Column(String(20), nullable=True, index=True)
    source_ref_id = Column(String(50), nullable=True)
    source_ref_name = Column(String(200), nullable=True)
    field_support_ref_type = Column(String(20), nullable=True, index=True)
    field_support_ref_id = Column(String(50), nullable=True)
    field_support_ref_name = Column(String(200), nullable=True)
    # technical_id: Staff employee assigned as technical resource for the deal (Technical Staff 2)
    technical_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    # DC-SUPPORT-TECH1-STAFF-001 (Jul 2026): Two additional staff roles before Technical Staff 2
    support_staff_id    = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    technical_staff1_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)

    # DC Protocol Apr 2026: Per-handler support confirmation flags
    # null=pending (no decision), true=confirmed, false=denied
    guru_supported          = Column(Boolean, nullable=True)   # Source (L1) confirmed field support
    z_guru_supported        = Column(Boolean, nullable=True)   # Senior (L2) confirmed field support
    adi_guru_supported      = Column(Boolean, nullable=True)   # Extended (L3) confirmed field support
    core_supported          = Column(Boolean, nullable=True)   # Core (L4 Core) confirmed field support
    telecaller_supported    = Column(Boolean, nullable=True)   # Telecaller staff confirmed
    showroom_supported      = Column(Boolean, nullable=True)   # Support / Showroom / Field Staff confirmed
    technical_supported          = Column(Boolean, nullable=True)   # Technical Staff 2 confirmed
    field_support_supported      = Column(Boolean, nullable=True)   # Non-VGK Field Support person confirmed
    support_staff_supported      = Column(Boolean, nullable=True)   # Support Staff confirmed
    technical_staff1_supported   = Column(Boolean, nullable=True)   # Technical Staff 1 confirmed

    # DC-SHOWROOM-COMMISSION-001 (May 2026): VGK partner ID of the showroom that supported this deal.
    # When set + showroom_pct > 0 in commission config → showroom partner earns level-5 commission.
    showroom_vgk_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)

    # Primary Lead Owner (Dec 2025) - Single owner for accountability
    # Can be: 'staff' (telecaller/field), 'partner', 'vendor', 'mnr'
    # Auto-assigned on first contact (new → contacted status change)
    primary_owner_type = Column(String(20), nullable=True, index=True)  # staff, partner, vendor, mnr
    primary_owner_id = Column(Integer, nullable=True, index=True)
    
    # Property reference for Real Dreams enquiries
    property_id = Column(Integer, nullable=True, index=True)

    # DC Protocol (Mar 2026): Tracks when a lead was marked as 'lost'
    # Used for 60-day re-entry rule: lost leads re-enter the dialer queue after 60 days
    lost_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    created_by_type = Column(String(20), nullable=True)
    created_by_id = Column(String(50), nullable=True)
    
    followups = relationship("CRMLeadFollowUp", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("CRMLeadNote", back_populates="lead", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'phone_primary_whatsapp': self.phone_primary_whatsapp,
            'alternate_phone': self.alternate_phone,
            'phone_secondary_whatsapp': self.phone_secondary_whatsapp,
            'category_id': self.category_id,
            'source': self.source,
            'source_details': self.source_details,
            'status': self.status,
            'priority': self.priority,
            'handler_type': self.handler_type,
            'handler_id': self.handler_id,
            'description': self.description,
            'requirements': self.requirements,
            'looking_for': self.looking_for,
            'recent_comments': self.recent_comments,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'address': self.address,
            'area': self.area,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'expected_close_date': _si(self.expected_close_date),
            'actual_close_date': _si(self.actual_close_date),
            'deal_value': getattr(self, 'deal_value', None),
            'deal_value_total': getattr(self, 'deal_value_total', 0) or 0,
            'deal_value_excl_tax': getattr(self, 'deal_value_excl_tax', 0) or 0,
            'deal_tax_rate': getattr(self, 'deal_tax_rate', 0) or 0,
            'deal_value_received': getattr(self, 'deal_value_received', 0) or 0,
            'deal_value_balance': getattr(self, 'deal_value_balance', 0) or 0,
            'confirmed_final_value': getattr(self, 'confirmed_final_value', None),
            'solar_value': getattr(self, 'solar_value', None),
            'lost_reason': self.lost_reason,
            'tags': self.tags,
            'last_contact_date': _si(self.last_contact_date),
            'next_followup_date': _si(self.next_followup_date),
            'depends_on_staff_id': self.depends_on_staff_id,
            'telecaller_id': self.telecaller_id,
            'field_staff_id': self.field_staff_id,
            'associated_partner_id': self.associated_partner_id,
            'vendor_id': self.vendor_id,
            'partner_id': self.vendor_id,  # Alias for UI - vendor shown as Partner
            'mnr_handler_id': self.mnr_handler_id,
            'guru_id': self.guru_id,
            'z_guru_id': self.z_guru_id,
            'adi_guru_id': self.adi_guru_id,
            'core_id': getattr(self, 'core_id', None),
            'guru_name': getattr(self, 'guru_name', None),
            'z_guru_name': getattr(self, 'z_guru_name', None),
            'core_name': getattr(self, 'core_name', None),
            'source_ref_type': getattr(self, 'source_ref_type', None),
            'source_ref_id': getattr(self, 'source_ref_id', None),
            'source_ref_name': getattr(self, 'source_ref_name', None),
            'field_support_ref_type': getattr(self, 'field_support_ref_type', None),
            'field_support_ref_id': getattr(self, 'field_support_ref_id', None),
            'field_support_ref_name': getattr(self, 'field_support_ref_name', None),
            'technical_id': getattr(self, 'technical_id', None),
            'support_staff_id': getattr(self, 'support_staff_id', None),
            'technical_staff1_id': getattr(self, 'technical_staff1_id', None),
            'guru_supported': getattr(self, 'guru_supported', None),
            'z_guru_supported': getattr(self, 'z_guru_supported', None),
            'adi_guru_supported': getattr(self, 'adi_guru_supported', None),
            'core_supported': getattr(self, 'core_supported', None),
            'telecaller_supported': getattr(self, 'telecaller_supported', None),
            'showroom_supported': getattr(self, 'showroom_supported', None),
            'showroom_vgk_id': getattr(self, 'showroom_vgk_id', None),
            'team_senior_partner_id': getattr(self, 'team_senior_partner_id', None),
            'team_extended_partner_id': getattr(self, 'team_extended_partner_id', None),
            'team_core_partner_id': getattr(self, 'team_core_partner_id', None),
            'technical_supported': getattr(self, 'technical_supported', None),
            'field_support_supported': getattr(self, 'field_support_supported', None),
            'support_staff_supported': getattr(self, 'support_staff_supported', None),
            'technical_staff1_supported': getattr(self, 'technical_staff1_supported', None),
            'is_vgk_program': self.is_vgk_program,
            'vgk_field_support_id': self.vgk_field_support_id,
            'primary_owner_type': self.primary_owner_type,
            'primary_owner_id': self.primary_owner_id,
            'property_id': self.property_id,
            'aadhaar_number': getattr(self, 'aadhaar_number', None),
            'pan_number': getattr(self, 'pan_number', None),
            'electricity_bill_number': getattr(self, 'electricity_bill_number', None),
            'google_maps_link': getattr(self, 'google_maps_link', None),
            'bank_account_number': getattr(self, 'bank_account_number', None),
            'ifsc_code': getattr(self, 'ifsc_code', None),
            'subsidy_status': getattr(self, 'subsidy_status', None),
            'application_no': getattr(self, 'application_no', None),
            'accepted_date': _si(getattr(self, 'accepted_date', None)),
            'loan_bank': getattr(self, 'loan_bank', None),
            'bank_branch': getattr(self, 'bank_branch', None),
            'documents_folder_link': getattr(self, 'documents_folder_link', None),
            'material_reach_date': _si(getattr(self, 'material_reach_date', None)),
            'installation_date': _si(getattr(self, 'installation_date', None)),
            'existing_association': getattr(self, 'existing_association', None),
            'bank_entry_updated': getattr(self, 'bank_entry_updated', None),
            'bank_statement_available': getattr(self, 'bank_statement_available', None),
            'regular_income_available': getattr(self, 'regular_income_available', None),
            'monthly_income': float(self.monthly_income) if getattr(self, 'monthly_income', None) is not None else None,
            'co_applicant_name': getattr(self, 'co_applicant_name', None),
            'co_applicant_phone': getattr(self, 'co_applicant_phone', None),
            'co_applicant_aadhaar': getattr(self, 'co_applicant_aadhaar', None),
            'co_applicant_pan': getattr(self, 'co_applicant_pan', None),
            'co_applicant_bank_account': getattr(self, 'co_applicant_bank_account', None),
            'co_applicant_ifsc': getattr(self, 'co_applicant_ifsc', None),
            'solar_pipeline_status': getattr(self, 'solar_pipeline_status', None),
            'solar_pipeline_status_updated_at': _si(getattr(self, 'solar_pipeline_status_updated_at', None)),
            'submit_date': _si(getattr(self, 'submit_date', None)),
            'complete_date': _si(getattr(self, 'complete_date', None)),
            'cibil_confirmed': bool(getattr(self, 'cibil_confirmed', False)),
            'cibil_score': getattr(self, 'cibil_score', None),
            'ev_b2b_stage': getattr(self, 'ev_b2b_stage', None),
            'kw_size': getattr(self, 'kw_size', None),
            'discom': getattr(self, 'discom', None),
            'sc_number': getattr(self, 'sc_number', None),
            'consumer_no': getattr(self, 'consumer_no', None),
            'sanction_date': _si(getattr(self, 'sanction_date', None)),
            'mnre_app_ref': getattr(self, 'mnre_app_ref', None),
            'discom_reg_no': getattr(self, 'discom_reg_no', None),
            'latitude': getattr(self, 'latitude', None),
            'longitude': getattr(self, 'longitude', None),
            'grid_phase': getattr(self, 'grid_phase', None),
            'investment_capacity': getattr(self, 'investment_capacity', None),
            'planning_to_start':   getattr(self, 'planning_to_start', None),
            'full_time_business':  getattr(self, 'full_time_business', None),
            'created_at': _si(self.created_at),
            'updated_at': _si(self.updated_at),
            'created_by_type': self.created_by_type,
            'created_by_id': self.created_by_id
        }


class CRMLeadFollowUp(BaseModel):
    """
    Follow-up tracking for leads
    DC Protocol: company_id for direct multi-company segregation
    """
    __tablename__ = 'crm_lead_followups'
    __table_args__ = (
        Index('ix_crm_followups_company', 'company_id'),
        Index('ix_crm_followups_lead', 'lead_id'),
        Index('ix_crm_followups_scheduled', 'scheduled_date', 'status'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    
    followup_type = Column(String(20), default='call', nullable=False)
    status = Column(String(20), default='scheduled', nullable=False)
    
    scheduled_date = Column(DateTime, nullable=False)
    completed_date = Column(DateTime, nullable=True)
    
    subject = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    
    reminder_sent = Column(Boolean, default=False, nullable=False)
    
    handler_type = Column(String(20), nullable=True)
    handler_id = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    created_by_type = Column(String(20), nullable=True)
    created_by_id = Column(String(50), nullable=True)
    
    lead = relationship("CRMLead", back_populates="followups")
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'followup_type': self.followup_type,
            'status': self.status,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'subject': self.subject,
            'notes': self.notes,
            'outcome': self.outcome,
            'reminder_sent': self.reminder_sent,
            'handler_type': self.handler_type,
            'handler_id': self.handler_id,
            'created_at': _si(self.created_at),
            'updated_at': _si(self.updated_at),
            'created_by_type': self.created_by_type,
            'created_by_id': self.created_by_id
        }


class CRMLeadNote(BaseModel):
    """
    Notes/comments on leads
    DC Protocol: company_id for direct multi-company segregation
    """
    __tablename__ = 'crm_lead_notes'
    __table_args__ = (
        Index('ix_crm_notes_company', 'company_id'),
        Index('ix_crm_notes_lead', 'lead_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    
    note = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    created_by_type = Column(String(20), nullable=True)
    created_by_id = Column(String(50), nullable=True)
    
    lead = relationship("CRMLead", back_populates="notes")
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'note': self.note,
            'is_private': self.is_private,
            'created_at': _si(self.created_at),
            'updated_at': _si(self.updated_at),
            'created_by_type': self.created_by_type,
            'created_by_id': self.created_by_id
        }


class CRMLeadAssignment(BaseModel):
    """
    Assignment history tracking for leads
    DC Protocol: company_id for direct multi-company segregation
    """
    __tablename__ = 'crm_lead_assignments'
    __table_args__ = (
        Index('ix_crm_assignments_company', 'company_id'),
        Index('ix_crm_assignments_lead', 'lead_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    
    from_handler_type = Column(String(20), nullable=True)
    from_handler_id = Column(String(50), nullable=True)
    
    to_handler_type = Column(String(20), nullable=False)
    to_handler_id = Column(String(50), nullable=True)
    
    reason = Column(Text, nullable=True)
    
    assigned_at = Column(DateTime, default=get_indian_time, nullable=False)
    assigned_by_type = Column(String(20), nullable=True)
    assigned_by_id = Column(String(50), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'from_handler_type': self.from_handler_type,
            'from_handler_id': self.from_handler_id,
            'to_handler_type': self.to_handler_type,
            'to_handler_id': self.to_handler_id,
            'reason': self.reason,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'assigned_by_type': self.assigned_by_type,
            'assigned_by_id': self.assigned_by_id
        }


class CRMLeadSource(BaseModel):
    """
    Lead source catalog per company
    DC Protocol: company_id segregation
    Enhanced: Jan 2026 - Added icon and color fields
    """
    __tablename__ = 'crm_lead_sources'
    __table_args__ = (
        Index('ix_crm_sources_company', 'company_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


DEFAULT_LEAD_SOURCES = [
    {'name': 'Self Lead', 'description': 'Lead added by employee themselves', 'display_order': 0},
    {'name': 'Website', 'description': 'Lead from company website', 'display_order': 1},
    {'name': 'Referral', 'description': 'Referred by existing customer/partner', 'display_order': 2},
    {'name': 'Walk-in', 'description': 'Walk-in inquiry', 'display_order': 3},
    {'name': 'Phone Call', 'description': 'Direct phone inquiry', 'display_order': 4},
    {'name': 'Social Media', 'description': 'From social media platforms', 'display_order': 5},
    {'name': 'Online - M', 'description': 'Online Meta / Facebook Lead Ads campaign', 'display_order': 6},
    {'name': 'Advertisement', 'description': 'Response to advertisement', 'display_order': 7},
    {'name': 'Event/Exhibition', 'description': 'From trade shows or events', 'display_order': 8},
    {'name': 'Partner', 'description': 'Lead from partner network', 'display_order': 9},
    {'name': 'MNR', 'description': 'Lead sourced via MNR Member (ground source)', 'display_order': 10},
    {'name': 'VGK4U', 'description': 'Lead submitted via VGK4U member portal', 'display_order': 11},
    {'name': 'Other', 'description': 'Other sources', 'display_order': 12},
]

# [DC-VGK-SOURCE] VGK4U member portal source name constant
VGK4U_SOURCE_NAME = 'VGK4U'

# DC Protocol (Jan 22, 2026): Constant for Self Lead source name - used for stats calculation
SELF_LEAD_SOURCE_NAME = 'Self Lead'


class CRMLeadDeal(BaseModel):
    __tablename__ = 'crm_lead_deals'
    __table_args__ = (
        Index('ix_crm_deal_lead', 'lead_id'),
        Index('ix_crm_deal_company', 'company_id'),
        Index('ix_crm_deal_category', 'revenue_category_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    revenue_category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=False)

    deal_code = Column(String(30), unique=True, nullable=True, index=True)
    deal_fy_seq = Column(Integer, nullable=True)

    deal_date = Column(DateTime, nullable=True)
    deal_value_total = Column(Float, default=0, nullable=False)    # incl. tax
    deal_value_excl_tax = Column(Float, default=0, nullable=False) # pre-tax (commission base)
    deal_tax_rate = Column(Float, default=0, nullable=False)        # GST % applied
    deal_value_received = Column(Float, default=0, nullable=False)
    deal_value_balance = Column(Float, default=0, nullable=False)
    status = Column(String(20), default='active', nullable=False)
    notes = Column(Text, nullable=True)

    # Credit attribution — each field accepts either an MNR Member ID or VGK Partner Code
    deal_source_id = Column(String(30), nullable=True, index=True)        # who sourced the deal
    deal_referrer_id = Column(String(30), nullable=True, index=True)      # who referred the deal
    deal_field_support_id = Column(String(30), nullable=True, index=True) # who provided field support

    # Timeline for bonanza eligibility (separate from deal_date)
    start_date = Column(DateTime, nullable=True)   # when deal negotiations started
    close_date = Column(DateTime, nullable=True)   # when deal was closed/completed

    created_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'company_id': self.company_id,
            'revenue_category_id': self.revenue_category_id,
            'deal_code': self.deal_code,
            'deal_fy_seq': self.deal_fy_seq,
            'deal_date': self.deal_date.isoformat() if self.deal_date else None,
            'deal_value_total': self.deal_value_total or 0,
            'deal_value_excl_tax': self.deal_value_excl_tax or 0,
            'deal_tax_rate': self.deal_tax_rate or 0,
            'deal_value_received': self.deal_value_received or 0,
            'deal_value_balance': self.deal_value_balance or 0,
            'status': self.status,
            'notes': self.notes,
            'deal_source_id': self.deal_source_id,
            'deal_referrer_id': self.deal_referrer_id,
            'deal_field_support_id': self.deal_field_support_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'close_date': self.close_date.isoformat() if self.close_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CRMRevenueApprovalStatus(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CRMRevenueEntry(BaseModel):
    """
    Revenue Entry with Approval Workflow for CRM Leads
    DC Protocol: company_id for multi-company segregation
    Tracks deal payments with approval workflow before ledger posting
    Finance Integration: Links to SFMS ledger on approval
    """
    __tablename__ = 'crm_revenue_entries'
    __table_args__ = (
        Index('ix_crm_revenue_company', 'company_id'),
        Index('ix_crm_revenue_lead', 'lead_id'),
        Index('ix_crm_revenue_status', 'approval_status'),
        Index('ix_crm_revenue_handler', 'handler_type', 'handler_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    
    amount_total = Column(Float, default=0, nullable=False)
    amount_received = Column(Float, default=0, nullable=False)
    amount_balance = Column(Float, default=0, nullable=False)
    
    approval_status = Column(String(20), default='draft', nullable=False)
    
    submitted_by_type = Column(String(20), nullable=True)
    submitted_by_id = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    handler_type = Column(String(20), nullable=True)
    handler_id = Column(Integer, nullable=True)
    
    ledger_posting_id = Column(Integer, nullable=True)
    ledger_posted_at = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'amount_total': self.amount_total or 0,
            'amount_received': self.amount_received or 0,
            'amount_balance': self.amount_balance or 0,
            'approval_status': self.approval_status,
            'submitted_by_type': self.submitted_by_type,
            'submitted_by_id': self.submitted_by_id,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_by_id': self.approved_by_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'handler_type': self.handler_type,
            'handler_id': self.handler_id,
            'ledger_posting_id': self.ledger_posting_id,
            'ledger_posted_at': self.ledger_posted_at.isoformat() if self.ledger_posted_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TransactionType(enum.Enum):
    ADVANCE = "advance"
    PARTIAL = "partial"
    FINAL = "final"
    REFUND = "refund"
    OTHER = "other"


class PaymentMode(enum.Enum):
    CASH = "cash"
    UPI = "upi"
    NEFT = "neft"
    RTGS = "rtgs"
    CHEQUE = "cheque"
    CARD = "card"
    DD = "dd"
    OTHER = "other"


class TransactionValidationStatus(enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    POSTED_TO_LEDGER = "posted_to_ledger"


class LedgerPartySource(enum.Enum):
    LEAD = "lead"
    CUSTOM = "custom"


class CRMLeadTransaction(BaseModel):
    """
    Transaction-wise payment tracking for CRM Leads
    DC Protocol: company_id for multi-company segregation
    Tracks individual transactions with receipt uploads and validation workflow
    """
    __tablename__ = 'crm_lead_transactions'
    __table_args__ = (
        Index('ix_crm_txn_company', 'company_id'),
        Index('ix_crm_txn_lead', 'lead_id'),
        Index('ix_crm_txn_status', 'validation_status'),
        Index('ix_crm_txn_date', 'transaction_date'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=True)   # nullable: PO-linked payments have no lead
    po_id = Column(Integer, nullable=True, index=True)   # FK to marketplace_purchase_orders.id (nullable FK enforced by app)
    revenue_entry_id = Column(Integer, ForeignKey('crm_revenue_entries.id', ondelete='SET NULL'), nullable=True)
    revenue_category_id = Column(Integer, ForeignKey('signup_categories.id', ondelete='SET NULL'), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey('crm_lead_deals.id', ondelete='SET NULL'), nullable=True, index=True)
    income_entry_id = Column(Integer, nullable=True, index=True)
    
    transaction_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20), default='partial', nullable=False)
    payment_mode = Column(String(20), default='cash', nullable=False)
    
    collected_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    receipt_upload_id = Column(Integer, nullable=True)
    receipt_filename = Column(String(255), nullable=True)
    
    validation_status = Column(String(20), default='pending', nullable=False)
    validated_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    finance_notes = Column(Text, nullable=True)
    
    ledger_entry_id = Column(Integer, nullable=True)
    ledger_party_source = Column(String(20), nullable=True)
    ledger_party_lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True)
    ledger_party_name = Column(String(200), nullable=True)
    ledger_posted_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    ledger_posted_at = Column(DateTime, nullable=True)
    
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'po_id': self.po_id,
            'revenue_entry_id': self.revenue_entry_id,
            'revenue_category_id': self.revenue_category_id,
            'deal_id': self.deal_id,
            'income_entry_id': self.income_entry_id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'amount': self.amount or 0,
            'transaction_type': self.transaction_type,
            'payment_mode': self.payment_mode,
            'collected_by_id': self.collected_by_id,
            'receipt_upload_id': self.receipt_upload_id,
            'receipt_filename': self.receipt_filename,
            'validation_status': self.validation_status,
            'validated_by_id': self.validated_by_id,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'rejection_reason': self.rejection_reason,
            'finance_notes': self.finance_notes,
            'ledger_entry_id': self.ledger_entry_id,
            'ledger_party_source': self.ledger_party_source,
            'ledger_party_lead_id': self.ledger_party_lead_id,
            'ledger_party_name': self.ledger_party_name,
            'ledger_posted_by_id': self.ledger_posted_by_id,
            'ledger_posted_at': self.ledger_posted_at.isoformat() if self.ledger_posted_at else None,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CRMLeadAuditLog(BaseModel):
    """
    Audit log for CRM lead field-level changes.
    DC Protocol (Apr 2026): Records every meaningful change with who made it and when.
    Tracks both staff portal changes and VGK member portal changes for compliance.
    """
    __tablename__ = 'crm_lead_audit_log'
    __table_args__ = (
        Index('ix_crm_audit_lead_id',    'lead_id'),
        Index('ix_crm_audit_changed_at', 'changed_at'),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    lead_id         = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    changed_by_type = Column(String(20),  nullable=False)  # 'staff', 'vgk_member', 'system'
    changed_by_id   = Column(String(50),  nullable=True)   # emp_code, user_id, or 'SYSTEM'
    changed_by_name = Column(String(200), nullable=True)
    field_name      = Column(String(100), nullable=False)
    old_value       = Column(Text, nullable=True)
    new_value       = Column(Text, nullable=True)
    change_category = Column(String(50),  nullable=True)   # 'handler','status','confirmation','basic'
    changed_at      = Column(DateTime, default=get_indian_time, nullable=False)


TRANSACTION_TYPES = [
    {'value': 'advance', 'label': 'Advance Payment'},
    {'value': 'partial', 'label': 'Partial Payment'},
    {'value': 'final', 'label': 'Final Payment'},
    {'value': 'refund', 'label': 'Refund'},
    {'value': 'other', 'label': 'Other'},
]

PAYMENT_MODES = [
    {'value': 'cash', 'label': 'Cash'},
    {'value': 'upi', 'label': 'UPI'},
    {'value': 'neft', 'label': 'NEFT'},
    {'value': 'rtgs', 'label': 'RTGS'},
    {'value': 'cheque', 'label': 'Cheque'},
    {'value': 'card', 'label': 'Card'},
    {'value': 'dd', 'label': 'Demand Draft'},
    {'value': 'other', 'label': 'Other'},
]
