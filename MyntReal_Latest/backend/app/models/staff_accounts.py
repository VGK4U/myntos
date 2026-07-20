"""
Staff Financial Management System Models (DC Protocol Compliant)
Multi-Company ERP for Accounts, Income, Expenses, Stock, and Ledgers

Tables Created:
- associated_companies: Company master with bank/stamp/signature
- company_segments: Configurable segments per company (VGK/EA)
- vendor_master: Vendor registration with GST/PAN/bank details
- stock_item_master: Stock item catalog
- pricing_configuration: Default markup and incentive settings
- income_source_types: Dynamic income sources
- income_entries: Income transactions
- vendor_transaction_header: Vendor purchase/payment header (with credit tracking)
- vendor_transaction_line_items: Multi-item line details
- service_items_used: Items used in service with incentive
- vendor_returns: Return/refund tracking
- stock_ledger: Company-wise stock movement
- stock_transfers: Inter-company stock transfers
- party_ledger: Vendor/Employee/MNR/External party ledger
- employee_fund_ledger: Employee fund tracking
- employee_fund_transfers: Employee-to-employee transfers
- employee_incentives: Service item sale incentives
- payment_receipts: Generated receipts
- generated_invoices: Invoice generation (with receivable tracking)
- invoice_line_items: Invoice line items
- balance_sheet_summary: Computed balance summaries
- approval_configuration: Approval workflow config
- approval_history: Approval audit trail
- accounts_payable_schedule: Payment schedules for vendor purchases (DC_CREDIT_001)
- accounts_receivable_schedule: Receipt schedules for customer invoices (DC_CREDIT_001)
- credit_aging_snapshots: Aging analysis buckets (0-30, 31-60, 61-90, 90+) (DC_CREDIT_001)
- payment_transactions: Payment/receipt transaction log (DC_CREDIT_001)
- purchase_invoice_uploads: Multi-format invoice upload with OCR (DC_PURCHASE_001)
- purchase_invoice_line_items: Extracted line items with HSN/Serial/IMEI (DC_PURCHASE_001)

Created: Dec 06, 2025
Updated: Dec 07, 2025 - Added Purchase Invoice Upload System (DC_PURCHASE_001)
DC Protocol: Write-Verify-Validate at all levels
DC_CREDIT_001: Credit tracking with payment_status, due_date, aging analysis
"""

from sqlalchemy import (
    Column, Integer, SmallInteger, String, DateTime, Date, Boolean, Text,
    ForeignKey, CheckConstraint, Index, Numeric, Float, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import pytz

from app.models.base import Base, BaseModel, get_indian_time
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory


class AssociatedCompany(BaseModel):
    """
    Associated Companies Master
    DC: All companies are equal peers, Mynt Real LLP handles book recording
    """
    __tablename__ = 'associated_companies'
    
    id = Column(Integer, primary_key=True, index=True)
    company_code = Column(String(20), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    company_type = Column(String(50), nullable=False, default='SUBSIDIARY')
    
    gst_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    cin_number = Column(String(25), nullable=True)

    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    website = Column(String(200), nullable=True)

    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    bank_name = Column(String(200), nullable=True)
    bank_branch = Column(String(200), nullable=True)
    account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(15), nullable=True)
    account_type = Column(String(20), nullable=True, default='CURRENT')
    upi_id = Column(String(100), nullable=True)
    
    logo_path = Column(String(500), nullable=True)
    stamp_path = Column(String(500), nullable=True)
    signature_path = Column(String(500), nullable=True)
    signatory_name = Column(String(200), nullable=True)
    signatory_designation = Column(String(100), nullable=True)
    
    receipt_prefix = Column(String(20), nullable=True)
    invoice_prefix = Column(String(20), nullable=True)
    receipt_counter = Column(Integer, default=0, nullable=False)
    invoice_counter = Column(Integer, default=0, nullable=False)
    
    is_book_keeper = Column(Boolean, default=False, nullable=False)
    is_marketplace_endpoint = Column(Boolean, default=False, nullable=False, server_default=text('false'))   # DC_STOCK_002: Lucky Enterprises etc — sells to marketplace customers
    is_active = Column(Boolean, default=True, nullable=False)

    # Task #39 — B2B SaaS Layer Phase 1 (Shadow Mode): nullable link to tenant.
    # NULL means "internal MNR-INTERNAL client" (back-filled by platform_b2b_seed).
    client_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='SET NULL'), nullable=True, index=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    segments = relationship("CompanySegment", back_populates="company", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "company_type IN ('PARENT', 'SUBSIDIARY', 'PARTNER', 'VENDOR')",
            name='associated_company_type_check'
        ),
        CheckConstraint(
            "account_type IN ('CURRENT', 'SAVINGS')",
            name='associated_company_account_type_check'
        ),
    )
    
    def __repr__(self):
        return f'<AssociatedCompany {self.company_code}: {self.company_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_code': self.company_code,
            'company_name': self.company_name,
            'company_type': self.company_type,
            'gst_number': self.gst_number,
            'pan_number': self.pan_number,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'is_book_keeper': self.is_book_keeper,
            'is_marketplace_endpoint': self.is_marketplace_endpoint,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CompanyBankAccount(BaseModel):
    """
    Company Bank Accounts
    DC-BANK-001: Multiple bank accounts per company.
    account_type: CURRENT | SAVINGS | OD | CC | UPI
    """
    __tablename__ = 'company_bank_accounts'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    bank_name = Column(String(200), nullable=False)
    branch = Column(String(200), nullable=True)
    account_number = Column(String(50), nullable=False)
    ifsc_code = Column(String(20), nullable=True)
    account_type = Column(String(20), nullable=False, default='CURRENT')
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "account_type IN ('CURRENT','SAVINGS','OD','CC','UPI','CASH')",
            name='cba_account_type_check'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'bank_name': self.bank_name,
            'branch': self.branch,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'account_type': self.account_type,
            'is_primary': self.is_primary,
            'is_active': self.is_active,
            'notes': self.notes,
            'display_label': f"{self.bank_name} — A/c {self.account_number[-4:] if self.account_number else ''}{'  ✓' if self.is_primary else ''} ({self.account_type})",
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CompanySegment(BaseModel):
    """
    Company Segments/Sections
    DC: Configurable by VGK/EA, company-wise and section-wise applicability
    """
    __tablename__ = 'company_segments'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_code = Column(String(20), nullable=False)
    segment_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    applicable_for = Column(JSONB, default=["ALL"], nullable=False)
    
    is_default = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    company = relationship("AssociatedCompany", back_populates="segments")
    
    __table_args__ = (
        UniqueConstraint('company_id', 'segment_code', name='uq_company_segment_code'),
        Index('idx_segment_company_active', 'company_id', 'is_active'),
    )
    
    def __repr__(self):
        return f'<CompanySegment {self.segment_code}: {self.segment_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'segment_code': self.segment_code,
            'segment_name': self.segment_name,
            'description': self.description,
            'applicable_for': self.applicable_for,
            'is_default': self.is_default,
            'display_order': self.display_order,
            'is_active': self.is_active
        }


class RevenueCategory(BaseModel):
    __tablename__ = 'revenue_categories'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    category_code = Column(String(30), nullable=False)
    category_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    company = relationship("AssociatedCompany", foreign_keys=[company_id])

    __table_args__ = (
        UniqueConstraint('company_id', 'category_code', name='uq_company_revenue_category'),
        Index('idx_revenue_cat_company_active', 'company_id', 'is_active'),
    )

    def __repr__(self):
        return f'<RevenueCategory {self.category_code}: {self.category_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'category_code': self.category_code,
            'category_name': self.category_name,
            'description': self.description,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class HSNMaster(BaseModel):
    """
    HSN/SAC Code Master
    DC_HSN_001: Central repository for HSN/SAC codes with GST rates
    Supports automatic GST calculation based on intra-state (CGST+SGST) vs inter-state (IGST)
    """
    __tablename__ = 'hsn_master'
    
    id = Column(Integer, primary_key=True, index=True)
    hsn_code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    
    cgst_rate = Column(Numeric(5, 2), nullable=False, default=9.00)
    sgst_rate = Column(Numeric(5, 2), nullable=False, default=9.00)
    igst_rate = Column(Numeric(5, 2), nullable=False, default=18.00)
    
    cess_rate = Column(Numeric(5, 2), nullable=True, default=0.00)
    
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_hsn_code_active', 'hsn_code', 'is_active'),
        Index('idx_hsn_effective', 'effective_from', 'effective_to'),
    )
    
    def __repr__(self):
        return f'<HSNMaster {self.hsn_code}: {self.description[:50]}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'hsn_code': self.hsn_code,
            'description': self.description,
            'cgst_rate': float(self.cgst_rate) if self.cgst_rate else 0,
            'sgst_rate': float(self.sgst_rate) if self.sgst_rate else 0,
            'igst_rate': float(self.igst_rate) if self.igst_rate else 0,
            'cess_rate': float(self.cess_rate) if self.cess_rate else 0,
            'effective_from': str(self.effective_from) if self.effective_from else None,
            'effective_to': str(self.effective_to) if self.effective_to else None,
            'is_active': self.is_active
        }
    
    def get_gst_rates(self, is_intra_state: bool) -> dict:
        """
        Get applicable GST rates based on transaction type
        DC_GST_CALC_001: Intra-state uses CGST+SGST, Inter-state uses IGST
        """
        if is_intra_state:
            return {
                'cgst_rate': float(self.cgst_rate) if self.cgst_rate else 0,
                'sgst_rate': float(self.sgst_rate) if self.sgst_rate else 0,
                'igst_rate': 0,
                'cess_rate': float(self.cess_rate) if self.cess_rate else 0,
                'total_gst_rate': float(self.cgst_rate or 0) + float(self.sgst_rate or 0) + float(self.cess_rate or 0)
            }
        else:
            return {
                'cgst_rate': 0,
                'sgst_rate': 0,
                'igst_rate': float(self.igst_rate) if self.igst_rate else 0,
                'cess_rate': float(self.cess_rate) if self.cess_rate else 0,
                'total_gst_rate': float(self.igst_rate or 0) + float(self.cess_rate or 0)
            }


class VendorMaster(BaseModel):
    """
    Vendor Master
    DC_VENDOR_001: Vendor registration with GST, PAN, bank details
    DC_VENDOR_002: Enhanced with 2 contact persons, map links, payment scanner, product association
    """
    __tablename__ = 'vendor_master'
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_code = Column(String(20), unique=True, nullable=False, index=True)
    vendor_name = Column(String(200), nullable=False)
    vendor_type = Column(String(20), nullable=False, default='BOTH')

    # Solar vendor fields (Apr 2026)
    mnre_empanelled = Column(Boolean, nullable=True, default=False)
    mnre_reg_no = Column(String(50), nullable=True)
    stamp_image_url = Column(Text, nullable=True)
    rep_signature_url = Column(Text, nullable=True)   # Authorized representative signature (all "Vendor Sig with Stamp" blocks)
    tech_signature_url = Column(Text, nullable=True)  # Technician/site-engineer signature (Commissioning/Site-Eng blocks)
    vendor_logo_url = Column(Text, nullable=True)     # Vendor logo — used in quotation/invoice/annexure letterhead (Apr 2026)

    contact_person = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    
    contact_person_1_name = Column(String(200), nullable=True)
    contact_person_1_phone = Column(String(20), nullable=True)
    contact_person_1_designation = Column(String(100), nullable=True)
    
    contact_person_2_name = Column(String(200), nullable=True)
    contact_person_2_phone = Column(String(20), nullable=True)
    contact_person_2_designation = Column(String(100), nullable=True)
    
    gst_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    map_link_1 = Column(String(500), nullable=True)
    map_link_1_label = Column(String(100), nullable=True, default='Office')
    map_link_2 = Column(String(500), nullable=True)
    map_link_2_label = Column(String(100), nullable=True, default='Warehouse')
    
    bank_name = Column(String(200), nullable=True)
    bank_branch = Column(String(200), nullable=True)
    account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(15), nullable=True)
    account_holder_name = Column(String(200), nullable=True)
    
    upi_id = Column(String(100), nullable=True)
    website_url = Column(String(300), nullable=True)
    terms_conditions = Column(Text, nullable=True)
    
    payment_scanner_path = Column(String(500), nullable=True)
    
    ship_to_address = Column(Text, nullable=True)
    ship_to_city = Column(String(100), nullable=True)
    ship_to_state = Column(String(100), nullable=True)
    ship_to_pincode = Column(String(10), nullable=True)
    
    payment_terms = Column(String(20), nullable=True, default='COD')
    credit_limit = Column(Numeric(15, 2), nullable=True, default=0)
    credit_days = Column(Integer, nullable=True, default=0)
    
    gst_type = Column(String(10), nullable=False, default='CGST_SGST')
    
    applicable_companies = Column(JSONB, default=[], nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "vendor_type IN ('PRODUCT', 'SERVICE', 'BOTH', 'SOLAR')",
            name='vendor_type_check'
        ),
        CheckConstraint(
            "payment_terms IN ('ADVANCE', 'COD', 'CREDIT_15', 'CREDIT_30', 'CREDIT_45', 'CREDIT_60')",
            name='vendor_payment_terms_check'
        ),
        Index('idx_vendor_name', 'vendor_name'),
        Index('idx_vendor_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<VendorMaster {self.vendor_code}: {self.vendor_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_code': self.vendor_code,
            'vendor_name': self.vendor_name,
            'vendor_type': self.vendor_type,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'contact_person_1_name': self.contact_person_1_name,
            'contact_person_1_phone': self.contact_person_1_phone,
            'contact_person_1_designation': self.contact_person_1_designation,
            'contact_person_2_name': self.contact_person_2_name,
            'contact_person_2_phone': self.contact_person_2_phone,
            'contact_person_2_designation': self.contact_person_2_designation,
            'gst_number': self.gst_number,
            'pan_number': self.pan_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'map_link_1': self.map_link_1,
            'map_link_1_label': self.map_link_1_label,
            'map_link_2': self.map_link_2,
            'map_link_2_label': self.map_link_2_label,
            'bank_name': self.bank_name,
            'bank_branch': self.bank_branch,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'account_holder_name': self.account_holder_name,
            'upi_id': self.upi_id,
            'website_url': self.website_url,
            'payment_scanner_path': self.payment_scanner_path,
            'ship_to_address': self.ship_to_address,
            'ship_to_city': self.ship_to_city,
            'ship_to_state': self.ship_to_state,
            'ship_to_pincode': self.ship_to_pincode,
            'payment_terms': self.payment_terms,
            'credit_limit': float(self.credit_limit) if self.credit_limit else 0,
            'credit_days': self.credit_days,
            'applicable_companies': self.applicable_companies or [],
            'is_active': self.is_active,
            'mnre_empanelled': getattr(self, 'mnre_empanelled', False) or False,
            'mnre_reg_no': getattr(self, 'mnre_reg_no', None),
            'stamp_image_url': getattr(self, 'stamp_image_url', None),
            'rep_signature_url': getattr(self, 'rep_signature_url', None),
            'tech_signature_url': getattr(self, 'tech_signature_url', None),
            'vendor_logo_url': getattr(self, 'vendor_logo_url', None),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class VendorStockItemAssociation(BaseModel):
    """
    Vendor-StockItem Association
    DC_VENDOR_003: Many-to-many vendor-product mapping for filtering and selection
    Bi-directional: Vendors can select products, Stock Items can select vendors
    """
    __tablename__ = 'vendor_stock_item_association'
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey('stock_item_master.id', ondelete='CASCADE'), nullable=False, index=True)
    
    is_preferred = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_vendor_item_unique', 'vendor_id', 'item_id', unique=True),
        Index('idx_vendor_stock_vendor', 'vendor_id'),
        Index('idx_vendor_stock_item', 'item_id'),
    )
    
    def __repr__(self):
        return f'<VendorStockItemAssociation Vendor:{self.vendor_id} Item:{self.item_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'item_id': self.item_id,
            'is_preferred': self.is_preferred,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StockItemMaster(BaseModel):
    """
    Stock Item Master
    DC_STOCK_001: Catalog of all stock items with HSN/SAC codes
    DC_STOCK_002: Enhanced with multi-company selection, specification, size, colors
    DC_STOCK_003: applicable_companies JSONB for multi-company filtering (like VendorMaster)
    """
    __tablename__ = 'stock_item_master'
    
    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(30), unique=True, nullable=False, index=True)
    item_name = Column(String(200), nullable=False)
    item_category = Column(String(30), nullable=False, default='PRODUCT')
    
    applicable_companies = Column(JSONB, default=[], nullable=False)
    
    description = Column(Text, nullable=True)
    brand = Column(String(150), nullable=True)
    model_compat = Column(String(300), nullable=True)   # "Compatible with" / Model from marketplace
    specification = Column(Text, nullable=True)
    size = Column(String(100), nullable=True)
    colors = Column(JSONB, nullable=True)
    
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    hsn_code = Column(String(20), nullable=True)
    hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    default_gst_rate = Column(Numeric(5, 2), nullable=True, default=18)
    
    reorder_level = Column(Integer, nullable=True, default=0)
    default_vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True)
    
    purchase_rate = Column(Numeric(15, 2), nullable=True, default=0)
    selling_rate = Column(Numeric(15, 2), nullable=True, default=0)

    # DC_STOCK_MKTLINK_001: Single-source-of-truth bridge to marketplace
    # When set, selling_rate → dealer_price and stock qty → available_qty auto-propagate
    marketplace_sku = Column(String(120), nullable=True, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "item_category IN ('PRODUCT', 'RAW_MATERIAL', 'CONSUMABLE', 'SPARE_PART', 'ACCESSORY')",
            name='stock_item_category_check'
        ),
        CheckConstraint(
            "unit_of_measure IN ('PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT')",
            name='stock_item_uom_check'
        ),
        Index('idx_stock_item_name', 'item_name'),
        Index('idx_stock_item_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<StockItemMaster {self.item_code}: {self.item_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'item_category': self.item_category,
            'applicable_companies': self.applicable_companies or [],
            'unit_of_measure': self.unit_of_measure,
            'specification': self.specification,
            'size': self.size,
            'colors': self.colors,
            'hsn_code': self.hsn_code,
            'hsn_id': self.hsn_id,
            'default_gst_rate': float(self.default_gst_rate) if self.default_gst_rate else 0,
            'purchase_rate': float(self.purchase_rate) if self.purchase_rate else 0,
            'selling_rate': float(self.selling_rate) if self.selling_rate else 0,
            'reorder_level': self.reorder_level,
            'marketplace_sku': self.marketplace_sku,
            'marketplace_linked': bool(self.marketplace_sku),
            'is_active': self.is_active,
            'description': self.description,
            'brand': self.brand,
            'model_compat': self.model_compat
        }


class StockItemImage(BaseModel):
    """
    Stock Item Images
    DC_STOCK_004: Multiple images per stock item with DC Protocol dual evidence
    DC_STOCK_005: Universal Upload integration with 100KB compression target
    WVV Protocol: 5MB upload limit, auto-compression, complete audit trail
    """
    __tablename__ = 'stock_item_images'
    
    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey('stock_item_master.id', ondelete='CASCADE'), nullable=False, index=True)
    
    original_path = Column(String(500), nullable=False)
    compressed_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    compressed_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    
    is_primary = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    source_type = Column(String(20), default='upload', nullable=False)
    source_url = Column(String(1000), nullable=True)
    
    uploaded_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_stock_item_images_item', 'stock_item_id'),
        Index('idx_stock_item_images_primary', 'stock_item_id', 'is_primary'),
    )
    
    def __repr__(self):
        return f'<StockItemImage {self.id} for Item:{self.stock_item_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_item_id': self.stock_item_id,
            'original_path': self.original_path,
            'compressed_path': self.compressed_path,
            'thumbnail_path': self.thumbnail_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'compressed_size': self.compressed_size,
            'mime_type': self.mime_type,
            'is_primary': self.is_primary,
            'display_order': self.display_order,
            'source_type': self.source_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PricingConfiguration(BaseModel):
    """
    Pricing Configuration
    DC: Default markup %, incentive %, configurable by VGK/EA/Accountant
    """
    __tablename__ = 'pricing_configuration'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    config_type = Column(String(30), nullable=False, default='SERVICE_ITEM_MARKUP')
    
    default_markup_pct = Column(Numeric(5, 2), nullable=False, default=20)
    incentive_pct = Column(Numeric(5, 2), nullable=False, default=50)
    allow_below_cost = Column(Boolean, default=False, nullable=False)
    min_markup_pct = Column(Numeric(5, 2), nullable=True, default=0)
    max_markup_pct = Column(Numeric(5, 2), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    configured_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "config_type IN ('SERVICE_ITEM_MARKUP', 'PRODUCT_MARKUP', 'GENERAL')",
            name='pricing_config_type_check'
        ),
        UniqueConstraint('company_id', 'config_type', name='uq_company_pricing_config'),
    )
    
    def __repr__(self):
        return f'<PricingConfiguration {self.config_type} - Markup: {self.default_markup_pct}%>'


class IncomeSourceType(BaseModel):
    """
    Income Source Types (Dynamic)
    DC: Configurable income sources with trigger actions
    DC_SFMS_001: is_taxable, default_tax_rate, requires_receipt configurable by VGK/EA/Accounts
    """
    __tablename__ = 'income_source_types'
    
    id = Column(Integer, primary_key=True, index=True)
    source_code = Column(String(30), unique=True, nullable=False, index=True)
    source_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    requires_reference = Column(Boolean, default=False, nullable=False)
    reference_type = Column(String(30), nullable=True)
    
    is_taxable = Column(Boolean, default=True, nullable=False)
    default_tax_rate = Column(Numeric(5, 2), default=18.00, nullable=False)
    requires_receipt = Column(Boolean, default=True, nullable=False)
    
    triggers_action = Column(JSONB, nullable=True)
    
    applicable_companies = Column(JSONB, default=["ALL"], nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "reference_type IS NULL OR reference_type IN ('MNR_USER', 'INVOICE', 'CONTRACT', 'CUSTOMER', 'OTHER')",
            name='income_source_ref_type_check'
        ),
        CheckConstraint(
            "default_tax_rate >= 0 AND default_tax_rate <= 100",
            name='income_source_tax_rate_check'
        ),
    )
    
    def __repr__(self):
        return f'<IncomeSourceType {self.source_code}: {self.source_name}>'


class IncomeEntry(BaseModel):
    """
    Income Entries
    DC: Income transactions with receipt generation support
    Status flow: PENDING → CONFIRMED → EXCEPTION_TALLY / ADJUSTMENT → TALLY_DONE
    """
    __tablename__ = 'income_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String(30), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    income_source_id = Column(Integer, ForeignKey('income_source_types.id'), nullable=False)
    revenue_category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=True, index=True)
    crm_transaction_id = Column(Integer, nullable=True, index=True)
    
    income_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    
    transaction_type = Column(String(20), nullable=True)
    
    reference_type = Column(String(30), nullable=True)
    reference_id = Column(String(50), nullable=True)
    
    payment_mode = Column(String(20), nullable=False)
    payment_type = Column(String(10), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_date = Column(Date, nullable=True)
    
    payer_name = Column(String(200), nullable=True)
    payer_contact = Column(String(50), nullable=True)
    payer_address = Column(Text, nullable=True)
    payer_city = Column(String(100), nullable=True)
    payer_state = Column(String(100), nullable=True)
    
    narration = Column(Text, nullable=True)
    receipt_path = Column(String(500), nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    lead_id = Column(Integer, nullable=True, index=True)
    lead_owner_id = Column(Integer, nullable=True, index=True)
    collected_by_id = Column(Integer, nullable=True, index=True)
    
    confirmed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    verified_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    tally_status = Column(String(20), nullable=False, default='NOT_SYNCED')
    tally_voucher_no = Column(String(50), nullable=True)
    
    ledger_updated = Column(Boolean, default=False, nullable=False)
    show_in_ledger = Column(Boolean, default=False, nullable=False)  # DC-SHOW-IN-LEDGER-001: optional, editable anytime
    # DC-ESTIMATIONS-001: confirmation split
    confirmation_type = Column(String(10), nullable=True)   # TAXED / ESTIMATED
    bank_account_id   = Column(Integer, nullable=True)       # account_ledger_masters.id used for TAXED

    # Destination routing — which entity receives this income
    destination_type        = Column(String(20), nullable=True)   # 'COMPANY' | 'EMPLOYEE'
    destination_company_id  = Column(Integer, nullable=True)
    destination_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    # DC-SOLAR-VENDOR-LEDGER-001: selected solar vendor at confirmation time
    solar_vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True, index=True)

    # Soft delete — visible only to VGK Mentor / EA roles (DC_INCOME_DELETE_001)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "payment_mode IN ('CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD')",
            name='income_payment_mode_check'
        ),
        CheckConstraint(
            "payment_type IS NULL OR payment_type IN ('CASH', 'BANK')",
            name='income_entries_payment_type_check'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'EXCEPTION_TALLY', 'ADJUSTMENT', 'TALLY_DONE')",
            name='income_status_check'
        ),
        CheckConstraint(
            "tally_status IN ('NOT_SYNCED', 'SELECTED', 'EXPORTED', 'SYNCED', 'MISMATCH', 'EXCLUDED')",
            name='income_tally_status_check'
        ),
        UniqueConstraint('company_id', 'entry_number', name='uq_income_entry_company_number'),
        Index('idx_income_company_date', 'company_id', 'income_date'),
        Index('idx_income_status', 'status'),
        Index('idx_income_crm_txn', 'crm_transaction_id'),
        Index('idx_income_lead_id', 'lead_id'),
        Index('idx_income_lead_owner', 'lead_owner_id'),
        Index('idx_income_collected_by', 'collected_by_id'),
    )
    
    def __repr__(self):
        return f'<IncomeEntry {self.entry_number}: ₹{self.amount}>'


class SolarVendorLedger(BaseModel):
    """
    DC-SOLAR-VENDOR-LEDGER-001
    Tracks payments from customer → MNR (direction=RECEIVED) and
    payments returned by vendor to MNR (direction=RETURNED).
    One row per income-entry confirmation or vendor-return event.
    """
    __tablename__ = 'solar_vendor_ledger'

    id = Column(Integer, primary_key=True, index=True)
    solar_vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=False, index=True)
    income_entry_id = Column(Integer, ForeignKey('income_entries.id'), nullable=True, index=True)
    entry_number    = Column(String(30), nullable=True)

    transaction_date = Column(Date, nullable=False, index=True)
    customer_name    = Column(String(200), nullable=True)
    amount           = Column(Numeric(15, 2), nullable=False)
    company_id       = Column(Integer, ForeignKey('associated_companies.id'), nullable=True)

    # RECEIVED = customer paid, MNR received; RETURNED = vendor returned money to MNR
    direction        = Column(String(10), nullable=False, default='RECEIVED')

    # Vendor-return fields
    utr_reference    = Column(String(100), nullable=True)
    payment_mode     = Column(String(20), nullable=True)
    notes            = Column(Text, nullable=True)

    created_by_id    = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at       = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("direction IN ('RECEIVED','RETURNED')", name='svl_direction_check'),
        Index('idx_svl_vendor_date', 'solar_vendor_id', 'transaction_date'),
    )


class VendorTransactionHeader(BaseModel):
    """
    Vendor Transaction Header
    DC: Purchase/Payment transactions with multi-item support
    DC_CREDIT_001: Extended with payment_status and due_date for Accounts Payable tracking
    """
    __tablename__ = 'vendor_transaction_header'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_number = Column(String(30), unique=True, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=False, index=True)
    
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    record_type = Column(String(20), nullable=False)
    
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    total_discount = Column(Numeric(15, 2), nullable=False, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    total_cgst = Column(Numeric(15, 2), nullable=False, default=0)
    total_sgst = Column(Numeric(15, 2), nullable=False, default=0)
    total_igst = Column(Numeric(15, 2), nullable=False, default=0)
    total_gst = Column(Numeric(15, 2), nullable=False, default=0)
    total_tds = Column(Numeric(15, 2), nullable=False, default=0)
    round_off = Column(Numeric(10, 2), nullable=False, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    
    payment_mode = Column(String(20), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_date = Column(Date, nullable=True)
    amount_paid = Column(Numeric(15, 2), nullable=False, default=0)
    balance_due = Column(Numeric(15, 2), nullable=False, default=0)
    
    payment_status = Column(String(20), nullable=False, default='PENDING')
    due_date = Column(Date, nullable=True)
    credit_days = Column(Integer, nullable=True, default=0)
    last_payment_date = Column(Date, nullable=True)
    is_credit_purchase = Column(Boolean, default=False, nullable=False)
    
    vendor_invoice_no = Column(String(50), nullable=True)
    vendor_invoice_date = Column(Date, nullable=True)
    invoice_status = Column(String(20), nullable=False, default='NOT_RECEIVED')
    invoice_received_on = Column(Date, nullable=True)
    invoice_path = Column(String(500), nullable=True)
    
    category_id = Column(Integer, ForeignKey('expense_sub_category.id'), nullable=True)
    narration = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    
    status = Column(String(20), nullable=False, default='DRAFT')
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    tally_status = Column(String(20), nullable=False, default='NOT_SYNCED')
    tally_voucher_no = Column(String(50), nullable=True)
    
    ledger_updated = Column(Boolean, default=False, nullable=False)
    stock_updated = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    line_items = relationship("VendorTransactionLineItem", back_populates="transaction", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('PURCHASE', 'PAYMENT', 'ADVANCE', 'REFUND', 'DEBIT_NOTE', 'CREDIT_NOTE')",
            name='vendor_txn_type_check'
        ),
        CheckConstraint(
            "record_type IN ('PRODUCT', 'SERVICE')",
            name='vendor_txn_record_type_check'
        ),
        CheckConstraint(
            "invoice_status IN ('NOT_RECEIVED', 'PENDING', 'RECEIVED')",
            name='vendor_invoice_status_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name='vendor_txn_status_check'
        ),
        CheckConstraint(
            "payment_status IN ('PENDING', 'PARTIAL_PAID', 'FULLY_PAID', 'OVERDUE')",
            name='vendor_txn_payment_status_check'
        ),
        Index('idx_vendor_txn_company_date', 'company_id', 'transaction_date'),
        Index('idx_vendor_txn_vendor', 'vendor_id'),
        Index('idx_vendor_txn_payment_status', 'payment_status'),
        Index('idx_vendor_txn_due_date', 'due_date'),
    )
    
    def __repr__(self):
        return f'<VendorTransactionHeader {self.transaction_number}: ₹{self.grand_total}>'


class VendorTransactionLineItem(BaseModel):
    """
    Vendor Transaction Line Items
    DC: Multi-item support with qty, rate, tax, product/service status
    """
    __tablename__ = 'vendor_transaction_line_items'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey('vendor_transaction_header.id'), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    item_code = Column(String(30), nullable=True)
    item_description = Column(String(300), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    
    discount_percent = Column(Numeric(5, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=False, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    gst_rate = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    product_status = Column(String(20), nullable=True)
    defective_qty = Column(Numeric(15, 3), nullable=False, default=0)
    ok_qty = Column(Numeric(15, 3), nullable=False, default=0)
    
    service_status = Column(String(20), nullable=True)
    service_date = Column(Date, nullable=True)
    
    stock_updated = Column(Boolean, default=False, nullable=False)
    stock_entry_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    transaction = relationship("VendorTransactionHeader", back_populates="line_items")
    
    __table_args__ = (
        CheckConstraint(
            "product_status IS NULL OR product_status IN ('OK', 'DEFECTIVE', 'PARTIAL_DEFECTIVE')",
            name='line_item_product_status_check'
        ),
        CheckConstraint(
            "service_status IS NULL OR service_status IN ('RECEIVED', 'PENDING', 'PARTIAL')",
            name='line_item_service_status_check'
        ),
        Index('idx_line_item_transaction', 'transaction_id'),
    )
    
    def __repr__(self):
        return f'<VendorTransactionLineItem {self.line_number}: {self.item_description}>'


class ServiceItemsUsed(BaseModel):
    """
    Service Items Used
    DC: Items used in service with incentive calculation
    
    Business Logic (enforced in API layer):
    - default_price = purchase_cost + (purchase_cost * default_markup_pct / 100)
    - final_price = custom_price if is_custom_price else default_price
    - Custom price validation: final_price >= purchase_cost (enforced in service)
    - profit_per_unit = final_price - purchase_cost
    - total_profit = profit_per_unit * quantity_used
    - incentive_amount = total_profit * (incentive_pct / 100)
    - incentive_pct default = 50 (50% of profit to employee)
    """
    __tablename__ = 'service_items_used'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey('vendor_transaction_header.id'), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False)
    item_code = Column(String(30), nullable=False)
    item_name = Column(String(200), nullable=False)
    
    available_stock = Column(Numeric(15, 3), nullable=False, default=0)
    quantity_used = Column(Numeric(15, 3), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    purchase_cost = Column(Numeric(15, 2), nullable=False, default=0)
    total_cost = Column(Numeric(15, 2), nullable=False, default=0)
    
    default_price = Column(Numeric(15, 2), nullable=False, default=0)
    custom_price = Column(Numeric(15, 2), nullable=True)
    final_price = Column(Numeric(15, 2), nullable=False, default=0)
    total_selling = Column(Numeric(15, 2), nullable=False, default=0)
    
    profit_per_unit = Column(Numeric(15, 2), nullable=False, default=0)
    total_profit = Column(Numeric(15, 2), nullable=False, default=0)
    incentive_pct = Column(Numeric(5, 2), nullable=False, default=50)
    incentive_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    price_below_cost = Column(Boolean, default=False, nullable=False)
    is_custom_price = Column(Boolean, default=False, nullable=False)
    
    stock_deducted = Column(Boolean, default=False, nullable=False)
    stock_entry_id = Column(Integer, nullable=True)
    incentive_entry_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_service_items_transaction', 'transaction_id'),
    )
    
    def __repr__(self):
        return f'<ServiceItemsUsed {self.item_code}: Qty {self.quantity_used}>'


class VendorReturn(BaseModel):
    """
    Vendor Returns
    DC: Return/Refund tracking with credit note, replacement, refund options
    """
    __tablename__ = 'vendor_returns'
    
    id = Column(Integer, primary_key=True, index=True)
    return_number = Column(String(30), unique=True, nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey('vendor_transaction_header.id'), nullable=False, index=True)
    line_item_id = Column(Integer, ForeignKey('vendor_transaction_line_items.id'), nullable=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=False)
    
    return_date = Column(Date, nullable=False)
    return_qty = Column(Numeric(15, 3), nullable=False, default=0)
    return_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    return_reason = Column(String(30), nullable=False)
    return_remarks = Column(Text, nullable=True)
    
    resolution_type = Column(String(20), nullable=True)
    resolution_status = Column(String(20), nullable=False, default='PENDING')
    
    credit_note_number = Column(String(50), nullable=True)
    credit_note_amount = Column(Numeric(15, 2), nullable=True, default=0)
    credit_note_date = Column(Date, nullable=True)
    
    replacement_received = Column(Boolean, default=False, nullable=False)
    replacement_date = Column(Date, nullable=True)
    replacement_remarks = Column(Text, nullable=True)
    
    refund_amount = Column(Numeric(15, 2), nullable=True, default=0)
    refund_date = Column(Date, nullable=True)
    refund_reference = Column(String(100), nullable=True)
    
    stock_reversed = Column(Boolean, default=False, nullable=False)
    reversal_entry_id = Column(Integer, nullable=True)
    ledger_updated = Column(Boolean, default=False, nullable=False)
    
    status = Column(String(20), nullable=False, default='INITIATED')
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "return_reason IN ('DEFECTIVE', 'WRONG_ITEM', 'DAMAGED', 'QUALITY_ISSUE', 'EXCESS_ORDER', 'OTHER')",
            name='vendor_return_reason_check'
        ),
        CheckConstraint(
            "resolution_type IS NULL OR resolution_type IN ('CREDIT_NOTE', 'REPLACEMENT', 'REFUND')",
            name='vendor_return_resolution_type_check'
        ),
        CheckConstraint(
            "resolution_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name='vendor_return_resolution_status_check'
        ),
        CheckConstraint(
            "status IN ('INITIATED', 'RETURNED', 'RESOLVED', 'CANCELLED')",
            name='vendor_return_status_check'
        ),
        Index('idx_vendor_return_transaction', 'transaction_id'),
        Index('idx_vendor_return_vendor', 'vendor_id'),
    )
    
    def __repr__(self):
        return f'<VendorReturn {self.return_number}: Qty {self.return_qty}>'


class StockLedger(BaseModel):
    """
    Stock Ledger
    DC: Company-wise stock movement with running balance
    """
    __tablename__ = 'stock_ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    
    transaction_date = Column(Date, nullable=False, index=True)
    entry_type = Column(String(30), nullable=False)
    
    reference_type = Column(String(30), nullable=False)
    reference_id = Column(Integer, nullable=False)
    reference_number = Column(String(50), nullable=True)
    
    quantity_in = Column(Numeric(15, 3), nullable=False, default=0)
    quantity_out = Column(Numeric(15, 3), nullable=False, default=0)
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    total_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    balance_qty = Column(Numeric(15, 3), nullable=False, default=0)
    balance_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    specification = Column(Text, nullable=True)
    color = Column(String(100), nullable=True)
    serial_numbers = Column(JSONB, nullable=True)
    
    narration = Column(Text, nullable=True)
    is_estimate = Column(Boolean, nullable=False, default=False, server_default=text('false'))   # True = estimation soft-deduction (excluded from real balance)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('OPENING', 'PURCHASE', 'SALE', 'TRANSFER_IN', 'TRANSFER_OUT', 'RETURN', 'ADJUSTMENT', 'SERVICE_CONSUMPTION', 'DAMAGE', 'WRITE_OFF', 'MFG_CONSUMPTION', 'MFG_OUTPUT', 'MFG_WASTE')",
            name='stock_ledger_entry_type_check'
        ),
        CheckConstraint(
            "reference_type IN ('VENDOR_TXN', 'SALE', 'STOCK_TRANSFER', 'SERVICE', 'ADJUSTMENT', 'OPENING', 'RETURN', 'MANUFACTURING')",
            name='stock_ledger_ref_type_check'
        ),
        Index('idx_stock_ledger_company_item', 'company_id', 'item_id'),
        Index('idx_stock_ledger_date', 'transaction_date'),
    )
    
    def __repr__(self):
        return f'<StockLedger {self.entry_type}: Item {self.item_id} Qty {self.quantity_in - self.quantity_out}>'


class StockTransfer(BaseModel):
    """
    Stock Transfers
    DC: Inter-company stock transfers with ledger updates
    """
    __tablename__ = 'stock_transfers'
    
    id = Column(Integer, primary_key=True, index=True)
    transfer_number = Column(String(30), unique=True, nullable=False, index=True)
    
    from_company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    from_segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    to_company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    to_segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    transfer_date = Column(Date, nullable=False, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    total_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    transfer_type = Column(String(20), nullable=False, default='INTERNAL')
    narration = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    
    status = Column(String(20), nullable=False, default='INITIATED')
    
    dispatched_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    dispatched_at = Column(DateTime, nullable=True)
    received_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    received_at = Column(DateTime, nullable=True)
    
    from_stock_entry_id = Column(Integer, nullable=True)
    to_stock_entry_id = Column(Integer, nullable=True)
    from_party_entry_id = Column(Integer, nullable=True)
    to_party_entry_id = Column(Integer, nullable=True)
    
    stock_reversal_entry_id = Column(Integer, nullable=True)
    from_party_reversal_entry_id = Column(Integer, nullable=True)
    to_party_reversal_entry_id = Column(Integer, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    __table_args__ = (
        CheckConstraint(
            "transfer_type IN ('SALE', 'LOAN', 'INTERNAL', 'RETURN')",
            name='stock_transfer_type_check'
        ),
        CheckConstraint(
            "status IN ('INITIATED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED')",
            name='stock_transfer_status_check'
        ),
        Index('idx_stock_transfer_from_company', 'from_company_id'),
        Index('idx_stock_transfer_to_company', 'to_company_id'),
    )
    
    def __repr__(self):
        return f'<StockTransfer {self.transfer_number}: {self.from_company_id} → {self.to_company_id}>'


class InterCompanyMarginConfig(BaseModel):
    """
    DC_STOCK_003: Configurable inter-company margin for stock transfers.
    When stock-holding company ≠ selling/marketplace company, the selling company
    raises an invoice to the holding company at proc_ex_tax + margin_pct.
    Lookup priority: from+to+category → from+to (any category) → global default.
    """
    __tablename__ = 'inter_company_margin_config'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    from_company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True, index=True)  # NULL = any
    to_company_id   = Column(Integer, ForeignKey('associated_companies.id'), nullable=True, index=True)  # NULL = any
    category_slug   = Column(String(100), nullable=True)   # NULL = all categories
    margin_pct      = Column(Numeric(6, 2), nullable=False, default=6.00)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_by_id   = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at      = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at      = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id':              self.id,
            'from_company_id': self.from_company_id,
            'to_company_id':   self.to_company_id,
            'category_slug':   self.category_slug,
            'margin_pct':      float(self.margin_pct),
            'is_active':       self.is_active,
        }

    def __repr__(self):
        return f'<InterCompanyMarginConfig {self.from_company_id}→{self.to_company_id} {self.margin_pct}%>'


class PartyLedger(BaseModel):
    """
    Party Ledger
    DC: Vendor/Employee/MNR User/External party debit/credit ledger
    
    Ledger Linkage (enforced in API layer):
    - Income entries create CREDIT entries for payer
    - Expense entries create DEBIT entries for vendor/payee
    - Vendor transactions create CREDIT/DEBIT based on transaction type
    - Fund transfers create matching DEBIT/CREDIT for sender/receiver
    - Stock transfers create inter-company ledger entries
    - running_balance is computed sequentially by party
    """
    __tablename__ = 'party_ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    
    party_type = Column(String(20), nullable=False, index=True)
    party_id = Column(Integer, nullable=False, index=True)
    party_name = Column(String(200), nullable=False)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    transaction_date = Column(Date, nullable=False, index=True)
    entry_type = Column(String(10), nullable=False)
    
    reference_type = Column(String(30), nullable=False)
    reference_id = Column(Integer, nullable=False)
    reference_number = Column(String(50), nullable=True)
    
    debit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    credit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    running_balance = Column(Numeric(15, 2), nullable=False, default=0)
    
    narration = Column(Text, nullable=True)
    voucher_type = Column(String(50), nullable=True)    # e.g. Receipt, Sales, Credit Note, Journal
    particulars = Column(String(300), nullable=True)    # Counterpart account / stock item name from Tally
    source_status = Column(String(30), nullable=True, index=True)  # DC-SOURCE-STATUS-001: CONFIRMED/MANUAL/TALLY_IMPORT/OPENING_BALANCE
    category = Column(String(100), nullable=True)  # DC-PL-CAT-001: Optional user-entered category label for manual entries
    main_category_id = Column(Integer, nullable=True)   # DC_LEDGER_CATEGORY_001: expense_main_category.id (display only, no accounting effect)
    sub_category_id  = Column(Integer, nullable=True)   # DC_LEDGER_CATEGORY_001: expense_sub_category.id (display only, no accounting effect)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    __table_args__ = (
        CheckConstraint(
            "party_type IN ('VENDOR', 'EMPLOYEE', 'MNR_USER', 'CUSTOMER', 'COMPANY', 'EXTERNAL')",
            name='party_ledger_party_type_check'
        ),
        CheckConstraint(
            "entry_type IN ('DEBIT', 'CREDIT')",
            name='party_ledger_entry_type_check'
        ),
        CheckConstraint(
            "reference_type IN ('VENDOR_TXN', 'INCOME', 'EXPENSE', 'FUND_TRANSFER', 'STOCK_TRANSFER', 'RETURN', 'OPENING', 'CRM_REVENUE', 'SALES_INVOICE', 'PURCHASE_INVOICE', 'JOURNAL', 'MANUAL', 'TALLY_IMPORT')",
            name='party_ledger_ref_type_check'
        ),
        Index('idx_party_ledger_party', 'party_type', 'party_id'),
        Index('idx_party_ledger_company', 'company_id'),
        Index('idx_party_ledger_date', 'transaction_date'),
    )
    
    def __repr__(self):
        return f'<PartyLedger {self.party_type}:{self.party_id} {self.entry_type}: ₹{self.debit_amount or self.credit_amount}>'


class AccountLedger(BaseModel):
    """
    Account Ledger — Tally-style general ledger for non-party accounts.
    DC_ACCT_LEDGER_001: Covers Cash, Bank, UPI, Income heads, Expense heads.
    Every confirmed income/expense posts here alongside party_ledger for complete double-entry.

    Account types:
      CASH     — physical cash payments/receipts
      BANK     — bank transfers (NEFT, RTGS, DD, Cheque, Card)
      UPI      — UPI payments (can be split from bank if needed)
      INCOME   — income account head (Sales Revenue, Service Revenue, etc.)
      EXPENSE  — expense account head (by category name)
      STOCK    — stock/inventory account movements
    """
    __tablename__ = 'account_ledger'

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)

    account_type = Column(String(20), nullable=False, index=True)   # CASH/BANK/UPI/INCOME/EXPENSE/STOCK
    account_name = Column(String(200), nullable=False, index=True)  # "Cash", "Sales Revenue", etc.

    transaction_date = Column(Date, nullable=False, index=True)
    entry_type = Column(String(10), nullable=False)                 # DEBIT / CREDIT

    reference_type = Column(String(40), nullable=False)             # INCOME, EXPENSE, PO, etc.
    reference_id = Column(Integer, nullable=False)
    reference_number = Column(String(80), nullable=True)            # IE number, expense number, PO#

    debit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    credit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    running_balance = Column(Numeric(15, 2), nullable=False, default=0)

    narration = Column(Text, nullable=True)
    voucher_type = Column(String(50), nullable=True)   # Receipt, Payment, Journal, Contra
    particulars = Column(String(300), nullable=True)   # Counter-account or payer/payee name
    source_status = Column(String(30), nullable=True, index=True)  # DC-SOURCE-STATUS-001: CONFIRMED/MANUAL/TALLY_IMPORT/OPENING_BALANCE
    main_category_id = Column(Integer, nullable=True)   # DC_LEDGER_CATEGORY_001: expense_main_category.id (display only, no accounting effect)
    sub_category_id  = Column(Integer, nullable=True)   # DC_LEDGER_CATEGORY_001: expense_sub_category.id (display only, no accounting effect)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "account_type IN ('CASH','BANK','UPI','INCOME','EXPENSE','STOCK','CAPITAL','LOAN','LIABILITY','ASSET','PARTY','SUNDRY_DEBTOR','SUNDRY_CREDITOR','DUTIES_TAXES')",
            name='account_ledger_account_type_check'
        ),
        CheckConstraint(
            "entry_type IN ('DEBIT','CREDIT')",
            name='account_ledger_entry_type_check'
        ),
        Index('idx_acct_ledger_company_type', 'company_id', 'account_type'),
        Index('idx_acct_ledger_account', 'account_type', 'account_name'),
        Index('idx_acct_ledger_date', 'transaction_date'),
        Index('idx_acct_ledger_ref', 'reference_type', 'reference_id'),
    )

    def __repr__(self):
        return f'<AccountLedger {self.account_type}/{self.account_name} {self.entry_type}: ₹{self.debit_amount or self.credit_amount}>'


class AccountLedgerMaster(BaseModel):
    """
    Chart of Accounts — DC_LEDGER_MASTER_001
    Defines every ledger account for a company with optional opening balance.
    Auto-posts an 'Opening Balance' entry to account_ledger on creation.
    """
    __tablename__ = 'account_ledger_masters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False)
    account_type = Column(String(20), nullable=False)   # CASH/BANK/UPI/INCOME/EXPENSE/STOCK/PARTY
    account_name = Column(String(200), nullable=False)
    account_code = Column(String(40))                   # optional short code
    description  = Column(Text)
    parent_group = Column(String(100))                  # e.g. "Current Assets"
    opening_balance        = Column(Numeric(15,2), default=Decimal('0'))
    opening_balance_type   = Column(String(10), default='DEBIT')   # DEBIT / CREDIT
    opening_balance_date   = Column(Date)
    opening_balance_posted = Column(Boolean, default=False)
    is_active    = Column(Boolean, default=True)
    # Bank account details (used when account_type = BANK or UPI) — DC_LEDGER_MASTER_002
    bank_name      = Column(String(200), nullable=True)
    account_number = Column(String(50),  nullable=True)
    ifsc_code      = Column(String(20),  nullable=True)
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'))
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'))
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('company_id', 'account_type', 'account_name', name='uq_ledger_master_co_type_name'),
        CheckConstraint("account_type IN ('CASH','BANK','UPI','INCOME','EXPENSE','STOCK','PARTY','CAPITAL','LOAN','LIABILITY','ASSET','SUNDRY_DEBTOR','SUNDRY_CREDITOR','DUTIES_TAXES')", name='alm_type_check'),
        CheckConstraint("opening_balance_type IN ('DEBIT','CREDIT')", name='alm_ob_type_check'),
    )

    def __repr__(self):
        return f'<AccountLedgerMaster {self.account_type}/{self.account_name}>'


class JournalVoucher(BaseModel):
    """
    Journal / Transfer Voucher — DC_JOURNAL_001
    Records direct bank-to-party, bank-to-bank (contra), or any manual
    double-entry transfer that is not linked to an income/expense entry.

    Voucher types:
      JOURNAL   — manual adjustment entry
      CONTRA    — fund transfer between two accounts (Bank↔Cash, Bank↔Bank)
      PAYMENT   — money going out to a party (bank → vendor/person)
      RECEIPT   — money coming in from a party (person/company → bank)
    """
    __tablename__ = 'journal_vouchers'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)

    voucher_number = Column(String(40), nullable=False)
    voucher_date   = Column(Date, nullable=False, index=True)
    voucher_type   = Column(String(20), nullable=False, default='JOURNAL')

    # DR side — account that gets debited
    dr_account_type = Column(String(20), nullable=False)   # CASH/BANK/UPI/INCOME/EXPENSE/PARTY
    dr_account_name = Column(String(200), nullable=False)

    # CR side — account that gets credited
    cr_account_type = Column(String(20), nullable=False)
    cr_account_name = Column(String(200), nullable=False)

    # Optional party info (person/vendor/company receiving/sending)
    party_type = Column(String(20), nullable=True)   # VENDOR/CUSTOMER/STAFF/EXTERNAL/COMPANY
    party_name = Column(String(200), nullable=True)
    party_id   = Column(Integer, nullable=True)

    amount     = Column(Numeric(15, 2), nullable=False)
    narration  = Column(Text, nullable=True)

    # Payment instrument details
    payment_mode     = Column(String(20), nullable=True)   # NEFT/RTGS/CHEQUE/CASH/UPI
    reference_number = Column(String(100), nullable=True)  # UTR/cheque no.

    # DC_CATPICKER_001: optional expense sub-category tag
    category_id = Column(Integer, nullable=True)
    # DC_INCOME_CAT_001 (May 2026): optional income sub-category tag
    income_category_id = Column(Integer, nullable=True)

    status = Column(String(20), nullable=False, default='POSTED')   # POSTED/CANCELLED

    created_by_id  = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    cancelled_at   = Column(DateTime, nullable=True)
    cancel_reason  = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "voucher_type IN ('JOURNAL','CONTRA','PAYMENT','RECEIPT')",
            name='jv_voucher_type_check'
        ),
        CheckConstraint(
            "status IN ('POSTED','CANCELLED')",
            name='jv_status_check'
        ),
        UniqueConstraint('company_id', 'voucher_number', name='uq_jv_company_voucher_number'),
        Index('idx_jv_company_date', 'company_id', 'voucher_date'),
        Index('idx_jv_party', 'party_type', 'party_name'),
    )

    def __repr__(self):
        return f'<JournalVoucher {self.voucher_number} {self.voucher_type} ₹{self.amount}>'


class JournalVoucherLine(BaseModel):
    """
    DC-JV-COMPOUND-001: Child lines for compound (multi-line) journal vouchers.
    Each row is one DR or CR entry within the voucher.
    Legacy simple vouchers have no rows here — they keep the header DR/CR columns.
    """
    __tablename__ = 'journal_voucher_lines'

    id         = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey('journal_vouchers.id', ondelete='CASCADE'), nullable=False, index=True)
    entry_type = Column(String(10), nullable=False)   # DEBIT / CREDIT
    account_type = Column(String(30), nullable=False)
    account_name = Column(String(200), nullable=False)
    amount       = Column(Numeric(15, 2), nullable=False)
    party_name   = Column(String(200), nullable=True)
    party_type   = Column(String(30), nullable=True)
    party_id     = Column(Integer, nullable=True)
    line_narration = Column(Text, nullable=True)
    sort_order   = Column(Integer, nullable=False, default=0)
    created_at   = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("entry_type IN ('DEBIT','CREDIT')", name='jvl_entry_type_check'),
    )

    def __repr__(self):
        return f'<JournalVoucherLine {self.entry_type} {self.account_name} ₹{self.amount}>'


class EmployeeFundLedger(BaseModel):
    """
    Employee Fund Ledger
    DC: Track employee fund allocations, expenses, transfers
    """
    __tablename__ = 'employee_fund_ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    transaction_date = Column(Date, nullable=False, index=True)
    entry_type = Column(String(20), nullable=False)
    
    reference_type = Column(String(30), nullable=False)
    reference_id = Column(Integer, nullable=False)
    reference_number = Column(String(50), nullable=True)
    
    debit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    credit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    balance = Column(Numeric(15, 2), nullable=False, default=0)
    
    narration = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('FUND_RECEIVED', 'EXPENSE_MADE', 'TRANSFER_SENT', 'TRANSFER_RECEIVED', 'REFUND', 'ADJUSTMENT')",
            name='emp_fund_entry_type_check'
        ),
        CheckConstraint(
            "reference_type IN ('FUND_ALLOCATION', 'EXPENSE_ENTRY', 'FUND_TRANSFER', 'ADJUSTMENT')",
            name='emp_fund_ref_type_check'
        ),
        Index('idx_emp_fund_employee', 'employee_id'),
        Index('idx_emp_fund_company', 'company_id'),
    )
    
    def __repr__(self):
        return f'<EmployeeFundLedger Emp:{self.employee_id} {self.entry_type}: ₹{self.debit_amount or self.credit_amount}>'


class EmployeeFundTransfer(BaseModel):
    """
    Employee Fund Transfers
    DC: Employee-to-employee fund transfers with ledger association
    """
    __tablename__ = 'employee_fund_transfers'
    
    id = Column(Integer, primary_key=True, index=True)
    transfer_number = Column(String(30), unique=True, nullable=False, index=True)
    
    from_employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    to_employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    transfer_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    
    purpose = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('expense_sub_category.id'), nullable=True)
    
    payment_mode = Column(String(20), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    confirmed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    from_ledger_entry_id = Column(Integer, nullable=True)
    to_ledger_entry_id = Column(Integer, nullable=True)
    
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'REJECTED', 'CANCELLED')",
            name='emp_fund_transfer_status_check'
        ),
        Index('idx_emp_fund_transfer_from', 'from_employee_id'),
        Index('idx_emp_fund_transfer_to', 'to_employee_id'),
    )
    
    def __repr__(self):
        return f'<EmployeeFundTransfer {self.transfer_number}: ₹{self.amount}>'


class EmployeeIncentive(BaseModel):
    """
    Employee Incentives
    DC: Service item sale incentives (50% of profit above cost)
    """
    __tablename__ = 'employee_incentives'
    
    id = Column(Integer, primary_key=True, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    incentive_date = Column(Date, nullable=False, index=True)
    incentive_type = Column(String(30), nullable=False)
    
    reference_type = Column(String(30), nullable=False)
    reference_id = Column(Integer, nullable=False)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    quantity = Column(Numeric(15, 3), nullable=False, default=0)
    
    cost_price = Column(Numeric(15, 2), nullable=False, default=0)
    selling_price = Column(Numeric(15, 2), nullable=False, default=0)
    profit_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    incentive_pct = Column(Numeric(5, 2), nullable=False, default=50)
    incentive_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    paid_date = Column(Date, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "incentive_type IN ('SERVICE_ITEM_SALE', 'PRODUCT_SALE', 'TARGET_BONUS', 'OTHER')",
            name='emp_incentive_type_check'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'PAID', 'CANCELLED')",
            name='emp_incentive_status_check'
        ),
        Index('idx_emp_incentive_employee', 'employee_id'),
        Index('idx_emp_incentive_status', 'status'),
    )
    
    def __repr__(self):
        return f'<EmployeeIncentive Emp:{self.employee_id} ₹{self.incentive_amount}>'


class PaymentReceipt(BaseModel):
    """
    Payment Receipts
    DC: Generated receipts with company branding
    """
    __tablename__ = 'payment_receipts'
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    income_entry_id = Column(Integer, ForeignKey('income_entries.id'), nullable=False)
    
    receipt_date = Column(Date, nullable=False)
    
    payer_type = Column(String(20), nullable=True)
    payer_id = Column(String(50), nullable=True)
    payer_name = Column(String(200), nullable=False)
    payer_address = Column(Text, nullable=True)
    payer_phone = Column(String(20), nullable=True)
    
    amount = Column(Numeric(15, 2), nullable=False)
    amount_in_words = Column(String(500), nullable=True)
    
    payment_mode = Column(String(20), nullable=False)
    payment_reference = Column(String(100), nullable=True)
    payment_towards = Column(Text, nullable=True)
    
    receipt_pdf_path = Column(String(500), nullable=True)
    is_printed = Column(Boolean, default=False, nullable=False)
    print_count = Column(Integer, default=0, nullable=False)
    
    status = Column(String(20), nullable=False, default='GENERATED')
    
    generated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "payer_type IS NULL OR payer_type IN ('MNR_USER', 'CUSTOMER', 'VENDOR', 'COMPANY', 'OTHER')",
            name='receipt_payer_type_check'
        ),
        CheckConstraint(
            "status IN ('GENERATED', 'CANCELLED', 'REPRINTED')",
            name='receipt_status_check'
        ),
        Index('idx_receipt_company', 'company_id'),
        Index('idx_receipt_income', 'income_entry_id'),
    )
    
    def __repr__(self):
        return f'<PaymentReceipt {self.receipt_number}: ₹{self.amount}>'


class GeneratedInvoice(BaseModel):
    """
    Generated Invoices
    DC: Invoice generation with company bank details, stamp, signature
    """
    __tablename__ = 'generated_invoices'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=True)
    
    party_type = Column(String(20), nullable=False)
    party_id = Column(Integer, nullable=True)
    party_name = Column(String(200), nullable=False)
    party_gst = Column(String(20), nullable=True)
    party_address = Column(Text, nullable=True)
    party_state = Column(String(100), nullable=True)
    party_state_code = Column(String(5), nullable=True)
    
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    total_discount = Column(Numeric(15, 2), nullable=False, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    cgst_total = Column(Numeric(15, 2), nullable=False, default=0)
    sgst_total = Column(Numeric(15, 2), nullable=False, default=0)
    igst_total = Column(Numeric(15, 2), nullable=False, default=0)
    round_off = Column(Numeric(10, 2), nullable=False, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    amount_in_words = Column(String(500), nullable=True)
    
    bank_name = Column(String(200), nullable=True)
    account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(15), nullable=True)
    upi_id = Column(String(100), nullable=True)
    
    terms_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    invoice_pdf_path = Column(String(500), nullable=True)
    is_printed = Column(Boolean, default=False, nullable=False)
    print_count = Column(Integer, default=0, nullable=False)
    
    payment_status = Column(String(20), nullable=False, default='UNPAID')
    amount_received = Column(Numeric(15, 2), nullable=False, default=0)
    balance_due = Column(Numeric(15, 2), nullable=False, default=0)
    
    status = Column(String(20), nullable=False, default='DRAFT')
    
    generated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "party_type IN ('CUSTOMER', 'VENDOR', 'COMPANY', 'MNR_USER', 'OTHER')",
            name='invoice_party_type_check'
        ),
        CheckConstraint(
            "payment_status IN ('UNPAID', 'PARTIAL', 'PAID', 'OVERDUE')",
            name='invoice_payment_status_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'GENERATED', 'SENT', 'CANCELLED')",
            name='invoice_status_check'
        ),
        Index('idx_invoice_company', 'company_id'),
        Index('idx_invoice_date', 'invoice_date'),
    )
    
    def __repr__(self):
        return f'<GeneratedInvoice {self.invoice_number}: ₹{self.grand_total}>'


class InvoiceLineItem(BaseModel):
    """
    Invoice Line Items
    DC: Multi-item invoice support
    """
    __tablename__ = 'invoice_line_items'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('generated_invoices.id'), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    
    item_description = Column(String(300), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit = Column(String(20), nullable=False, default='PCS')
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    
    discount_percent = Column(Numeric(5, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=False, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    gst_rate = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    invoice = relationship("GeneratedInvoice", back_populates="line_items")
    
    __table_args__ = (
        Index('idx_invoice_line_item', 'invoice_id'),
    )
    
    def __repr__(self):
        return f'<InvoiceLineItem {self.line_number}: {self.item_description}>'


class BalanceSheetSummary(BaseModel):
    """
    Balance Sheet Summary
    DC: Computed balance summaries for dashboard
    """
    __tablename__ = 'balance_sheet_summary'
    
    id = Column(Integer, primary_key=True, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)
    period_date = Column(Date, nullable=False, index=True)
    financial_year = Column(String(10), nullable=False)
    
    total_income = Column(Numeric(15, 2), nullable=False, default=0)
    income_by_source = Column(JSONB, nullable=True)
    
    total_expense = Column(Numeric(15, 2), nullable=False, default=0)
    expense_by_category = Column(JSONB, nullable=True)
    
    pending_payouts = Column(Numeric(15, 2), nullable=False, default=0)
    pending_awards = Column(Numeric(15, 2), nullable=False, default=0)
    pending_allowances = Column(Numeric(15, 2), nullable=False, default=0)
    total_liability = Column(Numeric(15, 2), nullable=False, default=0)
    
    net_balance = Column(Numeric(15, 2), nullable=False, default=0)
    available_balance = Column(Numeric(15, 2), nullable=False, default=0)
    
    total_receivables = Column(Numeric(15, 2), nullable=False, default=0)
    total_payables = Column(Numeric(15, 2), nullable=False, default=0)
    
    total_stock_value = Column(Numeric(15, 2), nullable=False, default=0)
    items_below_reorder = Column(Integer, nullable=False, default=0)
    
    pending_incentives = Column(Numeric(15, 2), nullable=False, default=0)
    
    computed_at = Column(DateTime, default=get_indian_time, nullable=False)
    computed_by = Column(String(20), nullable=True, default='SYSTEM')
    
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('DAILY', 'MONTHLY', 'QUARTERLY', 'YEARLY')",
            name='balance_sheet_period_type_check'
        ),
        UniqueConstraint('company_id', 'period_type', 'period_date', name='uq_balance_sheet_company_period'),
        Index('idx_balance_sheet_company', 'company_id'),
    )
    
    def __repr__(self):
        return f'<BalanceSheetSummary Company:{self.company_id} {self.period_type} {self.period_date}>'


class ApprovalConfiguration(BaseModel):
    """
    Approval Configuration
    DC: Configurable approval workflows
    """
    __tablename__ = 'approval_configuration'
    
    id = Column(Integer, primary_key=True, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True)
    entry_type = Column(String(30), nullable=False)
    category_id = Column(Integer, nullable=True)
    
    threshold_min = Column(Numeric(15, 2), nullable=True, default=0)
    threshold_max = Column(Numeric(15, 2), nullable=True)
    
    approval_levels = Column(JSONB, nullable=False)
    
    auto_approve_below = Column(Numeric(15, 2), nullable=True, default=0)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('INCOME', 'EXPENSE', 'FUND_ALLOCATION', 'VENDOR_TXN', 'STOCK_TRANSFER', 'INCENTIVE')",
            name='approval_config_entry_type_check'
        ),
    )
    
    def __repr__(self):
        return f'<ApprovalConfiguration {self.entry_type}>'


class ApprovalHistory(BaseModel):
    """
    Approval History
    DC: Audit trail for all approvals
    """
    __tablename__ = 'approval_history'
    
    id = Column(Integer, primary_key=True, index=True)
    
    entry_type = Column(String(30), nullable=False, index=True)
    entry_id = Column(Integer, nullable=False, index=True)
    
    approval_level = Column(Integer, nullable=False)
    approver_role = Column(String(50), nullable=False)
    approver_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False)
    
    action = Column(String(20), nullable=False)
    comments = Column(Text, nullable=True)
    
    action_at = Column(DateTime, default=get_indian_time, nullable=False)
    ip_address = Column(String(50), nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('APPROVED', 'REJECTED', 'RETURNED', 'ESCALATED')",
            name='approval_history_action_check'
        ),
        Index('idx_approval_history_entry', 'entry_type', 'entry_id'),
    )
    
    def __repr__(self):
        return f'<ApprovalHistory {self.entry_type}:{self.entry_id} - {self.action}>'


class FundAllocation(BaseModel):
    """
    Fund Allocations
    DC: Accountant to employee fund allocation with tracking
    """
    __tablename__ = 'fund_allocations'
    
    id = Column(Integer, primary_key=True, index=True)
    allocation_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    from_employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False)
    to_employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    
    allocation_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    
    purpose = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('expense_sub_category.id'), nullable=True)
    
    payment_mode = Column(String(20), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    balance_remaining = Column(Numeric(15, 2), nullable=False)
    total_expensed = Column(Numeric(15, 2), nullable=False, default=0)
    
    settlement_date = Column(Date, nullable=True)
    settlement_remarks = Column(Text, nullable=True)
    
    confirmed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    ledger_entry_id = Column(Integer, nullable=True)
    bank_account_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'PARTIALLY_SETTLED', 'SETTLED', 'CANCELLED')",
            name='fund_allocation_status_check'
        ),
        Index('idx_fund_allocation_to_employee', 'to_employee_id'),
        Index('idx_fund_allocation_from_employee', 'from_employee_id'),
    )
    
    def __repr__(self):
        return f'<FundAllocation {self.allocation_number}: ₹{self.amount}>'


class ExpenseEntry(BaseModel):
    """
    Expense Entries
    DC: Individual expense records with approval workflow
    """
    __tablename__ = 'expense_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String(30), nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    fund_allocation_id = Column(Integer, ForeignKey('fund_allocations.id'), nullable=True)
    
    main_category_id = Column(Integer, ForeignKey('expense_main_category.id'), nullable=False)
    sub_category_id = Column(Integer, ForeignKey('expense_sub_category.id'), nullable=True)
    
    expense_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True)
    vendor_name = Column(String(200), nullable=True)
    vendor_contact = Column(String(50), nullable=True)
    
    payment_mode = Column(String(20), nullable=False)
    payment_reference = Column(String(100), nullable=True)
    
    narration = Column(Text, nullable=True)
    
    bill_number = Column(String(50), nullable=True)
    bill_date = Column(Date, nullable=True)
    bill_path = Column(String(500), nullable=True)
    bill_remarks = Column(Text, nullable=True)
    
    related_entity_type = Column(String(20), nullable=True)
    related_entity_id = Column(String(50), nullable=True)
    
    gst_applicable = Column(Boolean, default=False, nullable=False)
    gst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    tds_applicable = Column(Boolean, default=False, nullable=False)
    tds_amount = Column(Numeric(15, 2), nullable=False, default=0)
    net_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    status = Column(String(20), nullable=False, default='DRAFT')
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    tally_status = Column(String(20), nullable=False, default='NOT_SYNCED')
    tally_voucher_no = Column(String(50), nullable=True)

    bank_account_id = Column(Integer, ForeignKey('company_bank_accounts.id'), nullable=True)
    bank_ledger_category = Column(String(20), nullable=True)
    custom_category_name = Column(String(100), nullable=True)
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    paid_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    payment_utr = Column(String(100), nullable=True)

    ledger_updated = Column(Boolean, default=False, nullable=False)
    show_in_ledger = Column(Boolean, default=False, nullable=False)  # DC-SHOW-IN-LEDGER-001: optional, editable anytime

    # DC-RETURN-001: Purchase Return / Debit Note flag
    is_return = Column(Boolean, default=False, nullable=False)
    return_reference = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "payment_mode IN ('CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD')",
            name='expense_entry_payment_mode_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name='expense_entry_status_check'
        ),
        CheckConstraint(
            "tally_status IN ('NOT_SYNCED', 'SELECTED', 'EXPORTED', 'SYNCED', 'MISMATCH', 'EXCLUDED')",
            name='expense_entry_tally_status_check'
        ),
        UniqueConstraint('company_id', 'entry_number', name='uq_expense_entry_company_number'),
        Index('idx_expense_entry_company_date', 'company_id', 'expense_date'),
        Index('idx_expense_entry_status', 'status'),
        Index('idx_expense_entry_fund_allocation', 'fund_allocation_id'),
    )
    
    created_by = relationship("StaffEmployee", foreign_keys=[created_by_id], lazy="joined")
    approved_by = relationship("StaffEmployee", foreign_keys=[approved_by_id], lazy="joined")
    paid_by = relationship("StaffEmployee", foreign_keys=[paid_by_id], lazy="joined")
    company = relationship("AssociatedCompany", foreign_keys=[company_id], lazy="select")
    main_cat = relationship("ExpenseMainCategory", foreign_keys=[main_category_id], lazy="select")

    @property
    def created_by_name(self):
        if self.created_by:
            return f"{self.created_by.first_name or ''} {self.created_by.last_name or ''}".strip()
        return None

    @property
    def approved_by_name(self):
        if self.approved_by:
            return f"{self.approved_by.first_name or ''} {self.approved_by.last_name or ''}".strip()
        return None

    @property
    def company_name(self):
        if self.company:
            return self.company.company_name
        return None

    @property
    def category_name(self):
        if self.main_cat:
            return self.main_cat.name
        return None

    def __repr__(self):
        return f'<ExpenseEntry {self.entry_number}: ₹{self.amount}>'


class AccountsPayableSchedule(BaseModel):
    """
    Accounts Payable Payment Schedule
    DC_CREDIT_001: Track partial payments to vendors with WVV protocol
    Status: PENDING → PARTIAL_PAID → FULLY_PAID
    """
    __tablename__ = 'accounts_payable_schedule'
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_number = Column(String(30), unique=True, nullable=False, index=True)
    
    transaction_id = Column(Integer, ForeignKey('vendor_transaction_header.id'), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    scheduled_amount = Column(Numeric(15, 2), nullable=False)
    paid_amount = Column(Numeric(15, 2), nullable=False, default=0)
    balance_amount = Column(Numeric(15, 2), nullable=False)
    
    due_date = Column(Date, nullable=False, index=True)
    payment_date = Column(Date, nullable=True)
    
    payment_mode = Column(String(20), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    bank_reference = Column(String(100), nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    reminder_count = Column(Integer, default=0, nullable=False)
    last_reminder_date = Column(Date, nullable=True)
    
    narration = Column(Text, nullable=True)
    
    wvv_hash = Column(String(64), nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    paid_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    ledger_entry_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PARTIAL_PAID', 'FULLY_PAID', 'OVERDUE', 'CANCELLED')",
            name='ap_schedule_status_check'
        ),
        Index('idx_ap_schedule_transaction', 'transaction_id'),
        Index('idx_ap_schedule_vendor', 'vendor_id'),
        Index('idx_ap_schedule_due_date', 'due_date'),
        Index('idx_ap_schedule_status', 'status'),
    )
    
    def __repr__(self):
        return f'<AccountsPayableSchedule {self.schedule_number}: ₹{self.scheduled_amount}>'


class AccountsReceivableSchedule(BaseModel):
    """
    Accounts Receivable Receipt Schedule
    DC_CREDIT_001: Track partial receipts from customers with WVV protocol
    Status: PENDING → PARTIAL_RECEIVED → FULLY_RECEIVED
    """
    __tablename__ = 'accounts_receivable_schedule'
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_number = Column(String(30), unique=True, nullable=False, index=True)
    
    invoice_id = Column(Integer, ForeignKey('generated_invoices.id'), nullable=False, index=True)
    party_type = Column(String(20), nullable=False)
    party_id = Column(Integer, nullable=True)
    party_name = Column(String(200), nullable=False)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    scheduled_amount = Column(Numeric(15, 2), nullable=False)
    received_amount = Column(Numeric(15, 2), nullable=False, default=0)
    balance_amount = Column(Numeric(15, 2), nullable=False)
    
    due_date = Column(Date, nullable=False, index=True)
    receipt_date = Column(Date, nullable=True)
    
    payment_mode = Column(String(20), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    bank_reference = Column(String(100), nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    reminder_count = Column(Integer, default=0, nullable=False)
    last_reminder_date = Column(Date, nullable=True)
    
    narration = Column(Text, nullable=True)
    
    wvv_hash = Column(String(64), nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    received_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    ledger_entry_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PARTIAL_RECEIVED', 'FULLY_RECEIVED', 'OVERDUE', 'CANCELLED')",
            name='ar_schedule_status_check'
        ),
        CheckConstraint(
            "party_type IN ('CUSTOMER', 'VENDOR', 'COMPANY', 'MNR_USER', 'OTHER')",
            name='ar_schedule_party_type_check'
        ),
        Index('idx_ar_schedule_invoice', 'invoice_id'),
        Index('idx_ar_schedule_party', 'party_type', 'party_id'),
        Index('idx_ar_schedule_due_date', 'due_date'),
        Index('idx_ar_schedule_status', 'status'),
    )
    
    def __repr__(self):
        return f'<AccountsReceivableSchedule {self.schedule_number}: ₹{self.scheduled_amount}>'


class CreditAgingSnapshot(BaseModel):
    """
    Credit Aging Snapshot
    DC_CREDIT_001: Periodic aging analysis for payables and receivables
    Buckets: 0-30, 31-60, 61-90, 90+ days
    """
    __tablename__ = 'credit_aging_snapshots'
    
    id = Column(Integer, primary_key=True, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    credit_type = Column(String(20), nullable=False)
    
    party_type = Column(String(20), nullable=True)
    party_id = Column(Integer, nullable=True)
    party_name = Column(String(200), nullable=True)
    
    snapshot_date = Column(Date, nullable=False, index=True)
    
    bucket_current = Column(Numeric(15, 2), nullable=False, default=0)
    bucket_1_30 = Column(Numeric(15, 2), nullable=False, default=0)
    bucket_31_60 = Column(Numeric(15, 2), nullable=False, default=0)
    bucket_61_90 = Column(Numeric(15, 2), nullable=False, default=0)
    bucket_90_plus = Column(Numeric(15, 2), nullable=False, default=0)
    
    total_outstanding = Column(Numeric(15, 2), nullable=False, default=0)
    total_overdue = Column(Numeric(15, 2), nullable=False, default=0)
    
    transaction_count = Column(Integer, default=0, nullable=False)
    overdue_count = Column(Integer, default=0, nullable=False)
    
    avg_days_outstanding = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "credit_type IN ('PAYABLE', 'RECEIVABLE')",
            name='aging_credit_type_check'
        ),
        Index('idx_aging_company_date', 'company_id', 'snapshot_date'),
        Index('idx_aging_credit_type', 'credit_type'),
        UniqueConstraint('company_id', 'credit_type', 'party_type', 'party_id', 'snapshot_date', name='uq_aging_snapshot'),
    )
    
    def __repr__(self):
        return f'<CreditAgingSnapshot {self.credit_type} {self.snapshot_date}: ₹{self.total_outstanding}>'


class PaymentTransaction(BaseModel):
    """
    Payment Transactions Log
    DC_CREDIT_001: Track all payment/receipt transactions for audit trail
    """
    __tablename__ = 'payment_transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_number = Column(String(30), unique=True, nullable=False, index=True)
    
    transaction_type = Column(String(20), nullable=False)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    source_type = Column(String(30), nullable=False)
    source_id = Column(Integer, nullable=False)
    schedule_id = Column(Integer, nullable=True)
    
    party_type = Column(String(20), nullable=False)
    party_id = Column(Integer, nullable=True)
    party_name = Column(String(200), nullable=False)
    
    transaction_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    
    payment_mode = Column(String(20), nullable=False)
    payment_reference = Column(String(100), nullable=True)
    bank_name = Column(String(200), nullable=True)
    bank_reference = Column(String(100), nullable=True)
    cheque_number = Column(String(20), nullable=True)
    cheque_date = Column(Date, nullable=True)
    
    narration = Column(Text, nullable=True)
    
    status = Column(String(20), nullable=False, default='COMPLETED')
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    ledger_entry_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('PAYMENT_TO_VENDOR', 'RECEIPT_FROM_CUSTOMER', 'ADVANCE_PAYMENT', 'ADVANCE_RECEIPT', 'REFUND_TO_CUSTOMER', 'REFUND_FROM_VENDOR')",
            name='payment_txn_type_check'
        ),
        CheckConstraint(
            "source_type IN ('VENDOR_TRANSACTION', 'INVOICE', 'FUND_ALLOCATION', 'OTHER')",
            name='payment_source_type_check'
        ),
        CheckConstraint(
            "party_type IN ('VENDOR', 'CUSTOMER', 'COMPANY', 'MNR_USER', 'EMPLOYEE', 'OTHER')",
            name='payment_party_type_check'
        ),
        CheckConstraint(
            "payment_mode IN ('CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD', 'ADJUSTMENT')",
            name='payment_txn_mode_check'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED', 'REVERSED', 'CANCELLED')",
            name='payment_txn_status_check'
        ),
        Index('idx_payment_txn_company_date', 'company_id', 'transaction_date'),
        Index('idx_payment_txn_source', 'source_type', 'source_id'),
        Index('idx_payment_txn_party', 'party_type', 'party_id'),
    )
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_number}: ₹{self.amount}>'


class BOMMaster(BaseModel):
    """
    Bill of Materials Master
    DC_BOM_001 (Dec 06, 2025): Recipe header linking finished product to components
    """
    __tablename__ = 'bom_master'
    
    id = Column(Integer, primary_key=True, index=True)
    bom_code = Column(String(30), unique=True, nullable=False, index=True)
    bom_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    finished_product_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    standard_qty = Column(Numeric(15, 3), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    version = Column(Integer, nullable=False, default=1)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    
    status = Column(String(20), nullable=False, default='DRAFT')
    
    estimated_cost = Column(Numeric(15, 2), nullable=True, default=0)
    estimated_time_hours = Column(Numeric(10, 2), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    line_items = relationship('BOMLineItem', back_populates='bom', cascade='all, delete-orphan')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    finished_product = relationship('StockItemMaster', foreign_keys=[finished_product_id], lazy='joined')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='joined')
    approved_by = relationship('StaffEmployee', foreign_keys=[approved_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'OBSOLETE', 'REJECTED')",
            name='bom_status_check'
        ),
        CheckConstraint(
            "unit_of_measure IN ('PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT')",
            name='bom_uom_check'
        ),
        UniqueConstraint('company_id', 'finished_product_id', 'version', name='uq_bom_product_version'),
        Index('idx_bom_company', 'company_id'),
        Index('idx_bom_product', 'finished_product_id'),
    )
    
    def __repr__(self):
        return f'<BOMMaster {self.bom_code}: {self.bom_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'bom_code': self.bom_code,
            'bom_name': self.bom_name,
            'description': self.description,
            'company_id': self.company_id,
            'finished_product_id': self.finished_product_id,
            'standard_qty': float(self.standard_qty) if self.standard_qty else 1,
            'unit_of_measure': self.unit_of_measure,
            'version': self.version,
            'status': self.status,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else 0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BOMLineItem(BaseModel):
    """
    Bill of Materials Line Items
    DC_BOM_001: Components and quantities required per unit of finished product
    """
    __tablename__ = 'bom_line_items'
    
    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey('bom_master.id', ondelete='CASCADE'), nullable=False, index=True)
    
    component_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    quantity_required = Column(Numeric(15, 4), nullable=False)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    wastage_pct = Column(Numeric(5, 2), nullable=True, default=0)
    
    unit_cost = Column(Numeric(15, 2), nullable=True, default=0)
    total_cost = Column(Numeric(15, 2), nullable=True, default=0)
    
    sequence_order = Column(Integer, nullable=False, default=1)
    
    is_optional = Column(Boolean, default=False, nullable=False)
    substitute_for_id = Column(Integer, ForeignKey('bom_line_items.id'), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    bom = relationship('BOMMaster', back_populates='line_items')
    component = relationship('StockItemMaster', foreign_keys=[component_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "unit_of_measure IN ('PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT')",
            name='bom_line_uom_check'
        ),
        UniqueConstraint('bom_id', 'component_id', name='uq_bom_component'),
        Index('idx_bom_line_bom', 'bom_id'),
        Index('idx_bom_line_component', 'component_id'),
    )
    
    def __repr__(self):
        return f'<BOMLineItem BOM:{self.bom_id} Component:{self.component_id} Qty:{self.quantity_required}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'bom_id': self.bom_id,
            'component_id': self.component_id,
            'quantity_required': float(self.quantity_required) if self.quantity_required else 0,
            'unit_of_measure': self.unit_of_measure,
            'wastage_pct': float(self.wastage_pct) if self.wastage_pct else 0,
            'unit_cost': float(self.unit_cost) if self.unit_cost else 0,
            'total_cost': float(self.total_cost) if self.total_cost else 0,
            'sequence_order': self.sequence_order,
            'is_optional': self.is_optional
        }


class ManufacturingOrder(BaseModel):
    """
    Manufacturing Orders
    DC_BOM_001: Work orders to produce finished goods from components
    """
    __tablename__ = 'manufacturing_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    bom_id = Column(Integer, ForeignKey('bom_master.id'), nullable=False, index=True)
    
    finished_product_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    
    planned_qty = Column(Numeric(15, 3), nullable=False)
    actual_qty = Column(Numeric(15, 3), nullable=True, default=0)
    rejected_qty = Column(Numeric(15, 3), nullable=True, default=0)
    
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    
    status = Column(String(20), nullable=False, default='PLANNED')
    priority = Column(String(10), nullable=False, default='NORMAL')
    
    estimated_cost = Column(Numeric(15, 2), nullable=True, default=0)
    actual_cost = Column(Numeric(15, 2), nullable=True, default=0)
    
    notes = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    started_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    completed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    approved_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    output_stock_entry_id = Column(Integer, nullable=True)
    
    material_status = Column(String(20), nullable=True, default='UNKNOWN')
    last_material_check_at = Column(DateTime, nullable=True)
    
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    line_items = relationship('ManufacturingOrderLine', back_populates='manufacturing_order', cascade='all, delete-orphan')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    bom = relationship('BOMMaster', foreign_keys=[bom_id], lazy='joined')
    finished_product = relationship('StockItemMaster', foreign_keys=[finished_product_id], lazy='joined')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='joined')
    approved_by = relationship('StaffEmployee', foreign_keys=[approved_by_id], lazy='joined')
    started_by = relationship('StaffEmployee', foreign_keys=[started_by_id], lazy='joined')
    completed_by = relationship('StaffEmployee', foreign_keys=[completed_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED', 'APPROVED', 'IN_PROGRESS', 'COMPLETED', 'PARTIALLY_COMPLETED', 'CANCELLED', 'ON_HOLD')",
            name='mfg_order_status_check'
        ),
        CheckConstraint(
            "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')",
            name='mfg_order_priority_check'
        ),
        CheckConstraint(
            "unit_of_measure IN ('PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT')",
            name='mfg_order_uom_check'
        ),
        Index('idx_mfg_order_company', 'company_id'),
        Index('idx_mfg_order_bom', 'bom_id'),
        Index('idx_mfg_order_status', 'status'),
        Index('idx_mfg_order_dates', 'planned_start_date', 'planned_end_date'),
    )
    
    def __repr__(self):
        return f'<ManufacturingOrder {self.order_number}: Qty {self.planned_qty} Status {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'company_id': self.company_id,
            'bom_id': self.bom_id,
            'finished_product_id': self.finished_product_id,
            'planned_qty': float(self.planned_qty) if self.planned_qty else 0,
            'actual_qty': float(self.actual_qty) if self.actual_qty else 0,
            'rejected_qty': float(self.rejected_qty) if self.rejected_qty else 0,
            'unit_of_measure': self.unit_of_measure,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'status': self.status,
            'priority': self.priority,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else 0,
            'actual_cost': float(self.actual_cost) if self.actual_cost else 0,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ManufacturingOrderLine(BaseModel):
    """
    Manufacturing Order Line Items
    DC_BOM_001: Tracks component consumption during manufacturing
    DC_COMPONENT_001: Additional materials tracking for items added during production
    """
    __tablename__ = 'manufacturing_order_lines'
    
    id = Column(Integer, primary_key=True, index=True)
    manufacturing_order_id = Column(Integer, ForeignKey('manufacturing_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    
    component_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    
    planned_qty = Column(Numeric(15, 4), nullable=False)
    actual_qty_consumed = Column(Numeric(15, 4), nullable=True, default=0)
    wastage_qty = Column(Numeric(15, 4), nullable=True, default=0)
    returned_qty = Column(Numeric(15, 4), nullable=True, default=0)
    
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    planned_cost = Column(Numeric(15, 2), nullable=True, default=0)
    actual_cost = Column(Numeric(15, 2), nullable=True, default=0)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    is_additional = Column(Boolean, default=False, nullable=False)
    added_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    added_at = Column(DateTime, nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    stock_consumption_entry_id = Column(Integer, nullable=True)
    stock_wastage_entry_id = Column(Integer, nullable=True)
    stock_return_entry_id = Column(Integer, nullable=True)
    
    consumed_at = Column(DateTime, nullable=True)
    consumed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    manufacturing_order = relationship('ManufacturingOrder', back_populates='line_items')
    component = relationship('StockItemMaster', foreign_keys=[component_id], lazy='joined')
    consumed_by = relationship('StaffEmployee', foreign_keys=[consumed_by_id], lazy='joined')
    added_by = relationship('StaffEmployee', foreign_keys=[added_by_id], lazy='joined')
    updated_by = relationship('StaffEmployee', foreign_keys=[updated_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ISSUED', 'PARTIALLY_CONSUMED', 'CONSUMED', 'RETURNED')",
            name='mfg_line_status_check'
        ),
        CheckConstraint(
            "unit_of_measure IN ('PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT')",
            name='mfg_line_uom_check'
        ),
        UniqueConstraint('manufacturing_order_id', 'component_id', name='uq_mfg_order_component'),
        Index('idx_mfg_line_order', 'manufacturing_order_id'),
        Index('idx_mfg_line_component', 'component_id'),
        Index('idx_mfg_line_additional', 'is_additional'),
    )
    
    def __repr__(self):
        return f'<ManufacturingOrderLine Order:{self.manufacturing_order_id} Component:{self.component_id} Additional:{self.is_additional}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'manufacturing_order_id': self.manufacturing_order_id,
            'component_id': self.component_id,
            'planned_qty': float(self.planned_qty) if self.planned_qty else 0,
            'actual_qty_consumed': float(self.actual_qty_consumed) if self.actual_qty_consumed else 0,
            'wastage_qty': float(self.wastage_qty) if self.wastage_qty else 0,
            'returned_qty': float(self.returned_qty) if self.returned_qty else 0,
            'unit_of_measure': self.unit_of_measure,
            'planned_cost': float(self.planned_cost) if self.planned_cost else 0,
            'actual_cost': float(self.actual_cost) if self.actual_cost else 0,
            'status': self.status,
            'is_additional': self.is_additional,
            'added_by_id': self.added_by_id,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'updated_by_id': self.updated_by_id
        }


# ==================== OFFICIAL PARTNER ORDER MANAGEMENT SYSTEM ====================
# DC_PARTNER_001: Official Partner Order Management with PI, Approval, Manufacturing/Procurement Integration
# Created: Dec 06, 2025


class OfficialPartner(BaseModel):
    """
    Official Partner Master (Unified Business Partners)
    DC_PARTNER_001: Partners (Dealer/Distributor/Vendor) who can place orders
    DC_PARTNER_002: Enhanced with vendor-specific fields for unified partner management
    """
    __tablename__ = 'official_partners'
    
    id = Column(Integer, primary_key=True, index=True)
    partner_code = Column(String(30), unique=True, nullable=False, index=True)
    partner_name = Column(String(200), nullable=False)
    category = Column(String(20), nullable=False)
    partner_type = Column(String(20), nullable=True, default='BOTH')
    
    contact_person = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    whatsapp_number = Column(String(20), nullable=True)
    
    contact_person_1_name = Column(String(200), nullable=True)
    contact_person_1_phone = Column(String(20), nullable=True)
    contact_person_1_designation = Column(String(100), nullable=True)
    
    contact_person_2_name = Column(String(200), nullable=True)
    contact_person_2_phone = Column(String(20), nullable=True)
    contact_person_2_designation = Column(String(100), nullable=True)
    
    gst_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    zone = Column(String(50), nullable=True)
    
    map_link_1 = Column(String(500), nullable=True)
    map_link_1_label = Column(String(100), nullable=True, default='Office')
    map_link_2 = Column(String(500), nullable=True)
    map_link_2_label = Column(String(100), nullable=True, default='Warehouse')
    
    bank_name = Column(String(200), nullable=True)
    bank_branch = Column(String(200), nullable=True)
    account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(15), nullable=True)
    payment_scanner_qr_url = Column(String(500), nullable=True)
    
    payment_terms = Column(String(20), nullable=True, default='ADVANCE')
    credit_limit = Column(Numeric(15, 2), nullable=True, default=0)
    credit_days = Column(Integer, nullable=True, default=0)
    
    legacy_vendor_id = Column(Integer, nullable=True)
    
    # DC Protocol Jan 2026: Service Center specific fields
    service_coverage_radius_km = Column(Integer, nullable=True)  # Service area in kilometers
    certified_technician_count = Column(Integer, nullable=True, default=0)
    specialized_equipment_list = Column(Text, nullable=True)  # JSON or comma-separated list
    service_center_sla_hours = Column(Integer, nullable=True, default=24)  # Custom SLA for this center
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # DC_PARTNER_LOGO_001: Business logo path (partner_logos/{partner_id}_{uuid}.ext)
    logo_path = Column(String(500), nullable=True)

    # [DC-PARTNER-CONTACTS-001] Dedicated sales & service point-of-contact
    sales_contact_number = Column(String(20), nullable=True)
    sales_contact_name = Column(String(200), nullable=True)
    service_contact_number = Column(String(20), nullable=True)
    service_contact_name = Column(String(200), nullable=True)

    # [DC-PARTNER-CONTACTS-001] Per-module on/off flags
    # Keys: walkins, leads, service, marketplace, stock, sales
    module_settings = Column(JSONB, nullable=True, default=dict)

    # [DC-PARTNER-GST-001] Apr 2026: GST treatment type for invoicing (IGST or CGST_SGST)
    gst_type = Column(String(10), nullable=True, default='CGST_SGST')

    # DC_PARTNER_AUTH_001: Authentication fields for partner login (Dec 2025)
    password_hash = Column(String(256), nullable=True)
    login_status = Column(String(20), nullable=True, default='active')  # active, suspended, locked
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=True, default=0)
    login_count = Column(Integer, nullable=True, default=0)
    password_changed_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    # DC Protocol Mar 2026: Company association for VGK_TEAM members
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True, index=True)

    # VGK Team fields (DC Protocol Mar 2026)
    parent_partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)
    vgk_role = Column(String(30), nullable=True)
    vgk_points_balance = Column(Numeric(15, 2), nullable=False, default=0)
    vgk_activated_at = Column(DateTime, nullable=True)

    # DC Protocol Mar 2026: Loyal Coupon — zero-cost activation by VGK Mentor staff only.
    # is_loyal_coupon=True means the member was activated via Loyal Coupon (not standard 5K PIN).
    # Commission rules: L1 (self) and L2 (support) earn; L3 and L4 are excluded.
    # Counted as +1 in all team/leg counts for awards and bonanza (is_active=True applies normally).
    is_loyal_coupon = Column(Boolean, default=False, nullable=False)

    # DC Protocol Mar 2026: Paid activation flag (₹4,999 PIN payment).
    # True = member has paid ₹4,999 activation → earns 25,000 points, unlocks full 4-level commission cascade and 3% EV Spares discount.
    # False = registered only (welcome bonus 5,000 pts) → L1 commission only, 2% EV Spares discount.
    is_paid_activation = Column(Boolean, default=False, nullable=False)

    # [DC-POINTS-REFILL] Apr 2026 — Auto-refill 50,000 points when activated member zeroes balance within 180 days of last credit. Maximum 2 refills total.
    # vgk_points_refill_count: how many auto-refills have fired for this member (0 = never refilled).
    # vgk_points_last_refill_at: timestamp of the most recent auto-refill credit (used as start of next 180-day window).
    vgk_points_refill_count   = Column(Integer, nullable=False, default=0)
    vgk_points_last_refill_at = Column(DateTime, nullable=True)

    # DC-VGK-PARTNER-SYNC-001: declare existing DB columns on model (created
    # via earlier raw-SQL bootstrap) so ORM reads/writes work for solar advance
    # auto-release flow.
    vgk_cash_wallet       = Column(Numeric(15, 2), nullable=False, default=0)
    vgk_cash_earned_total = Column(Numeric(15, 2), nullable=False, default=0)

    # DC Protocol Mar 2026: KYC status for VGK/Partner members (mirrors User.kyc_status)
    kyc_status = Column(String(30), nullable=True, default='Not Submitted')

    # [DC-VGK-DOB] Date of Birth fields — member-editable, stored as DATE
    dob_document = Column(Date, nullable=True)   # DOB as printed on Aadhaar / PAN
    dob_actual   = Column(Date, nullable=True)   # Member's actual date of birth

    # [DC-NAME-GENDER] Apr 2026 — split name fields for VGK members and partners
    name_title = Column(String(10),  nullable=True)   # Mr. / Ms. / Mrs.
    first_name = Column(String(100), nullable=True)
    last_name  = Column(String(100), nullable=True)
    gender     = Column(String(20),  nullable=True)   # Male / Female / Other

    # [DC-BLOOD-GROUP] Apr 2026 — member blood group for ID card and emergency use
    blood_group = Column(String(5), nullable=True)    # A+, A-, B+, B-, AB+, AB-, O+, O-
    is_card_admin = Column(Boolean, default=False, nullable=False)   # [DC_VGK_CARD_ADMIN_001] MR10001/EA preview gate
    vcard_enabled  = Column(Boolean, default=False, nullable=False)  # [DC_VGK_CARD_ENABLED_001] staff-granted visiting card access
    idcard_enabled = Column(Boolean, default=False, nullable=False)  # [DC_VGK_CARD_ENABLED_001] staff-granted ID card access
    card_manually_activated = Column(Boolean, default=False, nullable=False)  # [DC_CP_CARD_001] staff-granted CP tier activation

    # [DC-BANK-DETAILS-001] Apr 2026: Bank details approval flow for VGK members
    bank_details_status = Column(String(30), nullable=False, default='Not Submitted')  # Not Submitted / Pending / Approved / Rejected
    bank_rejection_reason = Column(Text, nullable=True)

    # [DC-PARTNER-KYC-001] May 2026: Aadhaar number text field
    aadhaar_number = Column(String(20), nullable=True)

    # [DC-PARTNER-TERMS-001] May 2026: Partnership agreement dates, reminder, and security deposit
    partner_start_date = Column(Date, nullable=True)
    partner_end_date   = Column(Date, nullable=True)
    reminder_days_before = Column(Integer, nullable=True, default=90)
    security_deposit = Column(Numeric(15, 2), nullable=True, default=0)

    # [DC-PARTNER-DOCS-001] May 2026: Agreement and application document paths
    agreement_document_path   = Column(String(500), nullable=True)
    application_document_path = Column(String(500), nullable=True)

    # [DC-VGK-STAFF-REG-001] Jun 2026: Emp code of the staff who registered this VGK member (nullable; new regs only)
    registered_by_emp_code = Column(String(50), nullable=True)

    company_segments = relationship('PartnerCompanySegment', back_populates='partner', cascade='all, delete-orphan')
    pricing_profiles = relationship('PartnerPricingProfile', back_populates='partner', cascade='all, delete-orphan')
    orders = relationship('PartnerOrder', back_populates='partner')

    __table_args__ = (
        CheckConstraint(
            "category IN ('DEALER', 'DISTRIBUTOR', 'VENDOR', 'REAL_DREAM_PARTNER', 'SERVICE_CENTER', 'VGK_TEAM')",
            name='partner_category_check'
        ),
        CheckConstraint(
            "payment_terms IN ('ADVANCE', 'COD', 'CREDIT', 'PARTIAL_ADVANCE')",
            name='partner_payment_terms_check'
        ),
        Index('idx_partner_category', 'category'),
        Index('idx_partner_active', 'is_active'),
        Index('idx_partner_login_status', 'login_status'),
    )
    
    def __repr__(self):
        return f'<OfficialPartner {self.partner_code}: {self.partner_name} ({self.category})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'partner_code': self.partner_code,
            'partner_name': self.partner_name,
            'category': self.category,
            'partner_type': self.partner_type,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'whatsapp_number': self.whatsapp_number,
            'contact_person_1_name': self.contact_person_1_name,
            'contact_person_1_phone': self.contact_person_1_phone,
            'contact_person_1_designation': self.contact_person_1_designation,
            'contact_person_2_name': self.contact_person_2_name,
            'contact_person_2_phone': self.contact_person_2_phone,
            'contact_person_2_designation': self.contact_person_2_designation,
            'gst_number': self.gst_number,
            'pan_number': self.pan_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'zone': self.zone,
            'map_link_1': self.map_link_1,
            'map_link_1_label': self.map_link_1_label,
            'map_link_2': self.map_link_2,
            'map_link_2_label': self.map_link_2_label,
            'bank_name': self.bank_name,
            'bank_branch': self.bank_branch,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'payment_scanner_qr_url': self.payment_scanner_qr_url,
            'payment_terms': self.payment_terms,
            'credit_limit': float(self.credit_limit) if self.credit_limit else 0,
            'credit_days': self.credit_days,
            'legacy_vendor_id': self.legacy_vendor_id,
            'is_active': self.is_active,
            'login_status': self.login_status,
            'service_coverage_radius_km': self.service_coverage_radius_km,
            'certified_technician_count': self.certified_technician_count,
            'specialized_equipment_list': self.specialized_equipment_list,
            'service_center_sla_hours': self.service_center_sla_hours,
            'parent_partner_id': self.parent_partner_id,
            'vgk_role': self.vgk_role,
            'vgk_points_balance': float(self.vgk_points_balance) if self.vgk_points_balance else 0,
            'vgk_cash_wallet': float(self.vgk_cash_wallet) if getattr(self, 'vgk_cash_wallet', None) else 0,
            'vgk_activated_at': self.vgk_activated_at.isoformat() if self.vgk_activated_at else None,
            'is_loyal_coupon': self.is_loyal_coupon,
            'is_paid_activation': bool(self.is_paid_activation),
            # [DC-NAME-GENDER] split name + gender fields
            'name_title': self.name_title,
            'first_name': self.first_name,
            'last_name':  self.last_name,
            'gender':     self.gender,
            # [DC-BLOOD-GROUP]
            'blood_group': self.blood_group,
            # [DC-VGK-DOB] Date of Birth fields
            'dob_document': self.dob_document.isoformat() if self.dob_document else None,
            'dob_actual':   self.dob_actual.isoformat()   if self.dob_actual   else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            # [DC-PARTNER-CONTACTS-001]
            'sales_contact_number': self.sales_contact_number,
            'sales_contact_name': self.sales_contact_name,
            'service_contact_number': self.service_contact_number,
            'service_contact_name': self.service_contact_name,
            'module_settings': self.module_settings or {},
            # [DC_VGK_CARD_ADMIN_001 / DC_VGK_CARD_ENABLED_001]
            'is_card_admin':  bool(getattr(self, 'is_card_admin',  False)),
            'vcard_enabled':  bool(getattr(self, 'vcard_enabled',  False)),
            'idcard_enabled': bool(getattr(self, 'idcard_enabled', False)),
            # [DC-BANK-DETAILS-001] Apr 2026
            'bank_details_status': self.bank_details_status or 'Not Submitted',
            'bank_rejection_reason': self.bank_rejection_reason,
            # [DC-PARTNER-GST-001] Apr 2026
            'gst_type': self.gst_type or 'CGST_SGST',
            # [DC-PARTNER-KYC-001] May 2026: Aadhaar number
            'aadhaar_number': self.aadhaar_number,
            # [DC-PARTNER-TERMS-001] May 2026: Partnership terms
            'partner_start_date': self.partner_start_date.isoformat() if self.partner_start_date else None,
            'partner_end_date':   self.partner_end_date.isoformat()   if self.partner_end_date   else None,
            'reminder_days_before': self.reminder_days_before if self.reminder_days_before is not None else 90,
            'security_deposit': float(self.security_deposit) if self.security_deposit else 0,
            # [DC-PARTNER-DOCS-001] May 2026: Document paths
            'agreement_document_path':   self.agreement_document_path,
            'application_document_path': self.application_document_path,
            # [DC-VGK-STAFF-REG-001] Jun 2026: Registering staff emp code
            'registered_by_emp_code': self.registered_by_emp_code,
            # Derived from company_segments for company-based filtering
            'applicable_companies': [cs.company_id for cs in self.company_segments if cs.is_active] if self.company_segments else [],
        }


class PartnerCompanySegment(BaseModel):
    """
    Partner to Company/Segment Assignment
    DC_PARTNER_001: Links partners to specific companies and segments (stores/zones)
    """
    __tablename__ = 'partner_company_segments'
    
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    partner = relationship('OfficialPartner', back_populates='company_segments')
    
    __table_args__ = (
        UniqueConstraint('partner_id', 'company_id', 'segment_id', name='uq_partner_company_segment'),
        Index('idx_partner_company_segment', 'partner_id', 'company_id'),
    )
    
    def __repr__(self):
        return f'<PartnerCompanySegment Partner:{self.partner_id} Company:{self.company_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'partner_id': self.partner_id,
            'company_id': self.company_id,
            'segment_id': self.segment_id,
            'is_primary': self.is_primary,
            'is_active': self.is_active
        }


class PartnerPricingProfile(BaseModel):
    """
    Partner-Specific Pricing
    DC_PARTNER_001: Dynamic pricing per partner per item per company
    """
    __tablename__ = 'partner_pricing_profiles'
    
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    
    discount_pct = Column(Numeric(5, 2), nullable=True)
    special_rate = Column(Numeric(15, 2), nullable=True)
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    partner = relationship('OfficialPartner', back_populates='pricing_profiles')
    
    __table_args__ = (
        UniqueConstraint('partner_id', 'company_id', 'item_id', 'effective_from', name='uq_partner_pricing'),
        Index('idx_partner_pricing_active', 'partner_id', 'company_id', 'is_active'),
    )
    
    def __repr__(self):
        return f'<PartnerPricingProfile Partner:{self.partner_id} Item:{self.item_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'partner_id': self.partner_id,
            'company_id': self.company_id,
            'item_id': self.item_id,
            'discount_pct': float(self.discount_pct) if self.discount_pct else None,
            'special_rate': float(self.special_rate) if self.special_rate else None,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'is_active': self.is_active
        }


class PartnerOrder(BaseModel):
    """
    Partner Order Header
    DC_PARTNER_001: Orders placed by partners with PI, approval workflow, and lifecycle tracking
    """
    __tablename__ = 'partner_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), nullable=False, index=True)
    pi_number = Column(String(30), nullable=True, index=True)
    
    partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    order_date = Column(Date, nullable=False)
    commitment_date = Column(Date, nullable=True)
    
    status = Column(String(30), nullable=False, default='DRAFT')
    
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True, default=0)
    tax_amount = Column(Numeric(15, 2), nullable=True, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    
    placed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    placed_by_partner = Column(Boolean, default=False, nullable=False)
    
    pi_generated_at = Column(DateTime, nullable=True)
    pi_generated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_remarks = Column(Text, nullable=True)
    
    payment_confirmed_at = Column(DateTime, nullable=True)
    payment_confirmed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    routed_to = Column(String(30), nullable=True)
    routed_at = Column(DateTime, nullable=True)
    routed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    manufacturing_order_id = Column(Integer, ForeignKey('manufacturing_orders.id'), nullable=True)
    
    remarks = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    partner = relationship('OfficialPartner', back_populates='orders')
    line_items = relationship('PartnerOrderLine', back_populates='order', cascade='all, delete-orphan')
    status_logs = relationship('PartnerOrderStatusLog', back_populates='order', cascade='all, delete-orphan')
    dispatch_info = relationship('PartnerOrderDispatch', back_populates='order', uselist=False)
    payment_records = relationship('PartnerPaymentRecord', back_populates='order', cascade='all, delete-orphan')
    procurement_links = relationship('PartnerProcurementLink', back_populates='order', cascade='all, delete-orphan')
    invoice = relationship('PartnerInvoice', back_populates='order', uselist=False)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PI_GENERATED', 'PENDING_APPROVAL', 'APPROVED', 'PAYMENT_PENDING', 'PAYMENT_CONFIRMED', "
            "'ROUTED_TO_PRODUCTION', 'ROUTED_TO_PROCUREMENT', 'IN_MANUFACTURING', 'PROCUREMENT_IN_PROGRESS', "
            "'READY_TO_DISPATCH', 'DISPATCHED', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED', 'REJECTED', 'CLOSED')",
            name='partner_order_status_check'
        ),
        CheckConstraint(
            "routed_to IN ('PRODUCTION', 'PROCUREMENT', 'DIRECT_DISPATCH') OR routed_to IS NULL",
            name='partner_order_routed_to_check'
        ),
        UniqueConstraint('company_id', 'order_number', name='uq_partner_order_company_order_num'),
        UniqueConstraint('company_id', 'pi_number', name='uq_partner_order_company_pi_num'),
        Index('idx_partner_order_status', 'status'),
        Index('idx_partner_order_company', 'company_id'),
        Index('idx_partner_order_dates', 'order_date', 'commitment_date'),
    )
    
    def __repr__(self):
        return f'<PartnerOrder {self.order_number}: {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'pi_number': self.pi_number,
            'partner_id': self.partner_id,
            'company_id': self.company_id,
            'segment_id': self.segment_id,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'commitment_date': self.commitment_date.isoformat() if self.commitment_date else None,
            'status': self.status,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'grand_total': float(self.grand_total) if self.grand_total else 0,
            'placed_by_partner': self.placed_by_partner,
            'routed_to': self.routed_to,
            'manufacturing_order_id': self.manufacturing_order_id,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PartnerOrderLine(BaseModel):
    """
    Partner Order Line Items
    DC_PARTNER_001: Individual items in a partner order
    """
    __tablename__ = 'partner_order_lines'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('partner_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    bom_id = Column(Integer, ForeignKey('bom_master.id'), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    unit_rate = Column(Numeric(15, 2), nullable=False)
    discount_pct = Column(Numeric(5, 2), nullable=True, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True, default=0)
    tax_rate = Column(Numeric(5, 2), nullable=True, default=0)
    tax_amount = Column(Numeric(15, 2), nullable=True, default=0)
    line_total = Column(Numeric(15, 2), nullable=False)
    
    manufacturing_order_id = Column(Integer, ForeignKey('manufacturing_orders.id'), nullable=True)
    
    stock_available = Column(Boolean, default=False, nullable=False)
    requires_manufacturing = Column(Boolean, default=False, nullable=False)
    requires_procurement = Column(Boolean, default=False, nullable=False)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    order = relationship('PartnerOrder', back_populates='line_items')
    
    __table_args__ = (
        CheckConstraint(
            "unit_of_measure IN ('PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT')",
            name='partner_order_line_uom_check'
        ),
        Index('idx_partner_order_line_order', 'order_id'),
        Index('idx_partner_order_line_item', 'item_id'),
    )
    
    def __repr__(self):
        return f'<PartnerOrderLine Order:{self.order_id} Item:{self.item_id} Qty:{self.quantity}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'item_id': self.item_id,
            'bom_id': self.bom_id,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_of_measure': self.unit_of_measure,
            'unit_rate': float(self.unit_rate) if self.unit_rate else 0,
            'discount_pct': float(self.discount_pct) if self.discount_pct else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'tax_rate': float(self.tax_rate) if self.tax_rate else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'line_total': float(self.line_total) if self.line_total else 0,
            'manufacturing_order_id': self.manufacturing_order_id,
            'stock_available': self.stock_available,
            'requires_manufacturing': self.requires_manufacturing,
            'requires_procurement': self.requires_procurement
        }


class PartnerOrderStatusLog(BaseModel):
    """
    Partner Order Status Change Log
    DC_PARTNER_001: Complete audit trail of order status changes
    """
    __tablename__ = 'partner_order_status_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('partner_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    
    changed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    changed_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    remarks = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    
    order = relationship('PartnerOrder', back_populates='status_logs')
    
    __table_args__ = (
        Index('idx_partner_order_status_log', 'order_id', 'changed_at'),
    )
    
    def __repr__(self):
        return f'<PartnerOrderStatusLog Order:{self.order_id} {self.from_status} -> {self.to_status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'changed_by_id': self.changed_by_id,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'remarks': self.remarks
        }


class PartnerOrderDispatch(BaseModel):
    """
    Partner Order Dispatch Details
    DC_PARTNER_001: Tracking and delivery information for dispatched orders
    """
    __tablename__ = 'partner_order_dispatches'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('partner_orders.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    courier_name = Column(String(100), nullable=True)
    awb_number = Column(String(100), nullable=True)
    tracking_url = Column(String(500), nullable=True)
    
    dispatch_date = Column(Date, nullable=True)
    expected_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)
    
    dispatched_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    dispatched_at = Column(DateTime, nullable=True)
    
    received_by = Column(String(200), nullable=True)
    received_at = Column(DateTime, nullable=True)
    
    proof_of_delivery_path = Column(String(500), nullable=True)
    
    webhook_status = Column(String(50), nullable=True)
    webhook_last_update = Column(DateTime, nullable=True)
    
    delivery_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    order = relationship('PartnerOrder', back_populates='dispatch_info')
    
    __table_args__ = (
        Index('idx_partner_dispatch_dates', 'dispatch_date', 'expected_delivery_date'),
        Index('idx_partner_dispatch_awb', 'awb_number'),
    )
    
    def __repr__(self):
        return f'<PartnerOrderDispatch Order:{self.order_id} AWB:{self.awb_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'courier_name': self.courier_name,
            'awb_number': self.awb_number,
            'tracking_url': self.tracking_url,
            'dispatch_date': self.dispatch_date.isoformat() if self.dispatch_date else None,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'actual_delivery_date': self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            'received_by': self.received_by,
            'proof_of_delivery_path': self.proof_of_delivery_path,
            'webhook_status': self.webhook_status
        }


class PartnerPaymentRecord(BaseModel):
    """
    Partner Order Payment Records
    DC_PARTNER_001: Payment tracking for PI confirmation
    """
    __tablename__ = 'partner_payment_records'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('partner_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_mode = Column(String(30), nullable=False)
    
    reference_number = Column(String(100), nullable=True)
    bank_name = Column(String(200), nullable=True)
    
    receipt_path = Column(String(500), nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    verified_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    remarks = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    order = relationship('PartnerOrder', back_populates='payment_records')
    
    __table_args__ = (
        CheckConstraint(
            "payment_mode IN ('CASH', 'BANK_TRANSFER', 'UPI', 'CHEQUE', 'NEFT', 'RTGS', 'IMPS', 'CARD')",
            name='partner_payment_mode_check'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'REJECTED', 'REFUNDED')",
            name='partner_payment_status_check'
        ),
        Index('idx_partner_payment_order', 'order_id'),
        Index('idx_partner_payment_date', 'payment_date'),
    )
    
    def __repr__(self):
        return f'<PartnerPaymentRecord Order:{self.order_id} Amount:{self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': float(self.amount) if self.amount else 0,
            'payment_mode': self.payment_mode,
            'reference_number': self.reference_number,
            'bank_name': self.bank_name,
            'status': self.status,
            'verified_by_id': self.verified_by_id,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'remarks': self.remarks
        }


class PartnerProcurementLink(BaseModel):
    """
    Partner Order to Procurement Link
    DC_PARTNER_001: Links partner orders to vendor transactions when procurement is triggered
    """
    __tablename__ = 'partner_procurement_links'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('partner_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    order_line_id = Column(Integer, ForeignKey('partner_order_lines.id'), nullable=True)
    
    vendor_transaction_id = Column(Integer, ForeignKey('vendor_transaction_header.id'), nullable=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False)
    shortage_qty = Column(Numeric(15, 3), nullable=False)
    
    status = Column(String(30), nullable=False, default='PENDING')
    
    fund_allocation_id = Column(Integer, ForeignKey('fund_allocations.id'), nullable=True)
    finance_approved_at = Column(DateTime, nullable=True)
    finance_approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    material_received_at = Column(DateTime, nullable=True)
    material_received_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    order = relationship('PartnerOrder', back_populates='procurement_links')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCUREMENT_CREATED', 'FINANCE_PENDING', 'FINANCE_APPROVED', "
            "'ORDERED', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED')",
            name='partner_procurement_status_check'
        ),
        Index('idx_partner_procurement_order', 'order_id'),
        Index('idx_partner_procurement_status', 'status'),
    )
    
    def __repr__(self):
        return f'<PartnerProcurementLink Order:{self.order_id} Item:{self.item_id} Status:{self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_line_id': self.order_line_id,
            'vendor_transaction_id': self.vendor_transaction_id,
            'item_id': self.item_id,
            'shortage_qty': float(self.shortage_qty) if self.shortage_qty else 0,
            'status': self.status,
            'fund_allocation_id': self.fund_allocation_id,
            'finance_approved_at': self.finance_approved_at.isoformat() if self.finance_approved_at else None,
            'material_received_at': self.material_received_at.isoformat() if self.material_received_at else None
        }


class PurchaseInvoiceUpload(BaseModel):
    """
    Purchase Invoice Upload
    DC_PURCHASE_001: Multi-format invoice upload with OCR extraction
    Status: UPLOADED → EXTRACTED → REVIEWED → CONFIRMED → PROCESSED
    Supports: PDF, Image (JPEG, PNG), Excel, CSV
    WVV Protocol: Write-Verify-Validate for all operations
    """
    __tablename__ = 'purchase_invoice_uploads'
    
    id = Column(Integer, primary_key=True, index=True)
    upload_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True, index=True)
    
    file_path = Column(String(500), nullable=True)  # DC: NULL for MANUAL entries
    file_name = Column(String(200), nullable=True)  # DC: NULL for MANUAL entries
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)
    
    vendor_invoice_no = Column(String(50), nullable=True)
    vendor_invoice_date = Column(Date, nullable=True)
    
    extracted_data = Column(JSONB, nullable=True)
    extraction_confidence = Column(Numeric(5, 2), nullable=True)
    extraction_method = Column(String(30), nullable=True)
    extraction_errors = Column(JSONB, nullable=True)
    
    subtotal = Column(Numeric(15, 2), nullable=True, default=0)
    total_discount = Column(Numeric(15, 2), nullable=True, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=True, default=0)
    cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    cess_amount = Column(Numeric(15, 2), nullable=True, default=0)
    total_tax = Column(Numeric(15, 2), nullable=True, default=0)
    round_off = Column(Numeric(10, 2), nullable=True, default=0)
    grand_total = Column(Numeric(15, 2), nullable=True, default=0)

    # DC-COURIER-001 (Apr 2026): Courier / freight charges on purchase invoice
    courier_amount = Column(Numeric(15, 2), nullable=True, default=0)
    courier_hsn_code = Column(String(20), nullable=True)
    courier_hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    # True = Part of Invoice (service line in invoice total); False = Exclusive expenditure (cost distributed to products)
    courier_is_inclusive = Column(Boolean, nullable=True, default=True)
    courier_gst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    courier_cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    courier_sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    courier_igst_amount = Column(Numeric(15, 2), nullable=True, default=0)

    # DC-TRANSPORT-001 (Apr 2026): Transport / freight charges on purchase invoice
    transport_amount = Column(Numeric(15, 2), nullable=True, default=0)
    transport_hsn_code = Column(String(20), nullable=True)
    transport_hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    transport_is_inclusive = Column(Boolean, nullable=True, default=True)
    transport_gst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    transport_cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    transport_sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    transport_igst_amount = Column(Numeric(15, 2), nullable=True, default=0)

    is_igst = Column(Boolean, default=False, nullable=False)
    seller_state = Column(String(100), nullable=True)
    buyer_state = Column(String(100), nullable=True)
    
    credit_days = Column(Integer, nullable=True, default=0)
    due_date = Column(Date, nullable=True)
    is_credit_purchase = Column(Boolean, default=False, nullable=False)
    
    status = Column(String(20), nullable=False, default='UPLOADED')
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # DC-RETURN-INV-001: Purchase Return / Debit Note
    document_type = Column(String(20), nullable=False, default='invoice')
    return_reference = Column(String(100), nullable=True)

    voucher_number = Column(String(30), unique=True, nullable=True, index=True)
    
    vendor_transaction_id = Column(Integer, ForeignKey('vendor_transaction_header.id'), nullable=True, index=True)
    
    uploaded_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    confirmed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    uploaded_at = Column(DateTime, default=get_indian_time, nullable=False)
    extracted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    # DC-VOID-001: Void audit fields — set when a CONFIRMED upload is fully reversed
    voided_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    voided_at = Column(DateTime, nullable=True)
    void_reason = Column(Text, nullable=True)
    # DC-DISPATCH-003: opt-in flag — pending receipt tab only shows invoices where this is True
    track_physical_receipt = Column(Boolean, nullable=False, default=False, server_default='false')
    
    wvv_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    line_items = relationship("PurchaseInvoiceLineItem", back_populates="upload", cascade="all, delete-orphan")
    vendor = relationship("VendorMaster", foreign_keys=[vendor_id], lazy="joined")
    company = relationship("AssociatedCompany", foreign_keys=[company_id], lazy="joined")
    voided_by = relationship("StaffEmployee", foreign_keys=[voided_by_id], lazy="joined")
    
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('PDF', 'JPEG', 'PNG', 'EXCEL', 'CSV', 'IMAGE', 'MANUAL')",
            name='purchase_upload_file_type_check'
        ),
        CheckConstraint(
            "status IN ('UPLOADED', 'EXTRACTING', 'EXTRACTED', 'REVIEWED', 'CONFIRMED', 'PROCESSED', 'REJECTED', 'CANCELLED', 'VOIDED')",
            name='purchase_upload_status_check'
        ),
        CheckConstraint(
            "extraction_method IN ('OCR', 'PDF_PARSER', 'EXCEL_PARSER', 'CSV_PARSER', 'MANUAL', 'AI_EXTRACTION')",
            name='purchase_upload_extraction_method_check'
        ),
        Index('idx_purchase_upload_company', 'company_id'),
        Index('idx_purchase_upload_vendor', 'vendor_id'),
        Index('idx_purchase_upload_status', 'status'),
        Index('idx_purchase_upload_date', 'uploaded_at'),
    )
    
    def __repr__(self):
        return f'<PurchaseInvoiceUpload {self.upload_number}: {self.status}>'
    
    def to_dict(self, include_line_items: bool = True):
        vendor_name = None
        vendor_code = None
        if hasattr(self, 'vendor') and self.vendor:
            vendor_name = self.vendor.vendor_name
            vendor_code = self.vendor.vendor_code
        
        result = {
            'id': self.id,
            'upload_number': self.upload_number,
            'voucher_number': self.voucher_number,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'vendor_id': self.vendor_id,
            'vendor_name': vendor_name,
            'vendor_code': vendor_code,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'vendor_invoice_no': self.vendor_invoice_no,
            'vendor_invoice_date': self.vendor_invoice_date.isoformat() if self.vendor_invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'taxable_amount': float(self.taxable_amount) if self.taxable_amount else 0,
            'cgst_amount': float(self.cgst_amount) if self.cgst_amount else 0,
            'sgst_amount': float(self.sgst_amount) if self.sgst_amount else 0,
            'igst_amount': float(self.igst_amount) if self.igst_amount else 0,
            'total_tax': float(self.total_tax) if self.total_tax else 0,
            'grand_total': float(self.grand_total) if self.grand_total else 0,
            'is_igst': self.is_igst,
            'seller_state': self.seller_state,
            'buyer_state': self.buyer_state,
            'review_notes': self.review_notes,
            'status': self.status,
            'extraction_confidence': float(self.extraction_confidence) if self.extraction_confidence else None,
            'extraction_method': self.extraction_method,
            'extracted_data': self.extracted_data,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'voided_by_id': self.voided_by_id,
            'voided_by_name': self.voided_by.full_name if (hasattr(self, 'voided_by') and self.voided_by) else None,
            'voided_at': self.voided_at.isoformat() if self.voided_at else None,
            'void_reason': self.void_reason,
            'track_physical_receipt': bool(self.track_physical_receipt),
            'courier_amount': float(self.courier_amount) if self.courier_amount else 0,
            'courier_hsn_code': self.courier_hsn_code,
            'courier_hsn_id': self.courier_hsn_id,
            'courier_is_inclusive': self.courier_is_inclusive if self.courier_is_inclusive is not None else True,
            'courier_gst_rate': float(self.courier_gst_rate) if self.courier_gst_rate else 0,
            'courier_cgst_amount': float(self.courier_cgst_amount) if self.courier_cgst_amount else 0,
            'courier_sgst_amount': float(self.courier_sgst_amount) if self.courier_sgst_amount else 0,
            'courier_igst_amount': float(self.courier_igst_amount) if self.courier_igst_amount else 0,
            'transport_amount': float(self.transport_amount) if self.transport_amount else 0,
            'transport_hsn_code': self.transport_hsn_code,
            'transport_hsn_id': self.transport_hsn_id,
            'transport_is_inclusive': self.transport_is_inclusive if self.transport_is_inclusive is not None else True,
            'transport_gst_rate': float(self.transport_gst_rate) if self.transport_gst_rate else 0,
            'transport_cgst_amount': float(self.transport_cgst_amount) if self.transport_cgst_amount else 0,
            'transport_sgst_amount': float(self.transport_sgst_amount) if self.transport_sgst_amount else 0,
            'transport_igst_amount': float(self.transport_igst_amount) if self.transport_igst_amount else 0,
            'round_off': float(self.round_off) if self.round_off is not None else 0,
        }
        
        if include_line_items and hasattr(self, 'line_items') and self.line_items:
            result['line_items'] = [item.to_dict() for item in self.line_items]
        else:
            result['line_items'] = []
        
        return result


class PurchaseInvoiceLineItem(BaseModel):
    """
    Purchase Invoice Line Items
    DC_PURCHASE_001: Line items extracted from uploaded invoices
    Links to HSN Master for GST calculation
    """
    __tablename__ = 'purchase_invoice_line_items'
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey('purchase_invoice_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    item_code = Column(String(30), nullable=True)
    item_description = Column(String(500), nullable=False)
    
    hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    hsn_code = Column(String(20), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    
    gross_amount = Column(Numeric(15, 2), nullable=False, default=0)
    discount_percent = Column(Numeric(5, 2), nullable=True, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    gst_rate = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    sgst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    igst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    cess_rate = Column(Numeric(5, 2), nullable=True, default=0)
    cess_amount = Column(Numeric(15, 2), nullable=True, default=0)
    
    total_tax = Column(Numeric(15, 2), nullable=False, default=0)
    line_total = Column(Numeric(15, 2), nullable=False, default=0)
    
    specification = Column(Text, nullable=True)
    color = Column(String(100), nullable=True)
    
    serial_numbers = Column(JSONB, nullable=True)
    imei_numbers = Column(JSONB, nullable=True)
    batch_number = Column(String(50), nullable=True)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    warranty_months = Column(Integer, nullable=True, default=0)
    warranty_end_date = Column(Date, nullable=True)
    
    is_matched = Column(Boolean, default=False, nullable=False)
    match_confidence = Column(Numeric(5, 2), nullable=True)
    manual_override = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)  # DC Protocol audit trail
    
    upload = relationship("PurchaseInvoiceUpload", back_populates="line_items")
    
    __table_args__ = (
        Index('idx_purchase_line_upload', 'upload_id'),
        Index('idx_purchase_line_item', 'item_id'),
        Index('idx_purchase_line_hsn', 'hsn_id'),
    )
    
    def __repr__(self):
        return f'<PurchaseInvoiceLineItem {self.upload_id}:{self.line_number} - {self.item_description}>'
    
    def to_dict(self):
        unit_rate_val = float(self.unit_rate) if self.unit_rate else 0
        taxable_val = float(self.taxable_amount) if self.taxable_amount else 0
        tax_val = float(self.total_tax) if self.total_tax else 0
        line_total_val = float(self.line_total) if self.line_total else 0
        
        return {
            'id': self.id,
            'upload_id': self.upload_id,
            'line_number': self.line_number,
            'item_id': self.item_id,
            'stock_item_id': self.item_id,
            'item_code': self.item_code,
            'item_description': self.item_description,
            'hsn_id': self.hsn_id,
            'hsn_code': self.hsn_code,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_of_measure': self.unit_of_measure,
            'unit_rate': unit_rate_val,
            'rate': unit_rate_val,
            'taxable_amount': taxable_val,
            'amount': taxable_val,
            'gst_rate': float(self.gst_rate) if self.gst_rate else 0,
            'total_tax': tax_val,
            'tax_amount': tax_val,
            'line_total': line_total_val,
            'total_amount': line_total_val,
            'specification': self.specification,
            'color': self.color,
            'serial_numbers': self.serial_numbers,
            'imei_numbers': self.imei_numbers,
            'warranty_months': self.warranty_months,
            'is_matched': self.is_matched
        }


class PartnerInvoice(BaseModel):
    """
    Partner Order Invoice
    DC_PARTNER_001: Invoice generation with company-wise numbering
    """
    __tablename__ = 'partner_invoices'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(30), nullable=False, index=True)
    
    order_id = Column(Integer, ForeignKey('partner_orders.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    cgst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    sgst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    igst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    
    total_tax = Column(Numeric(15, 2), nullable=True, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    amount_in_words = Column(String(500), nullable=True)
    
    payment_status = Column(String(20), nullable=False, default='PENDING')
    amount_received = Column(Numeric(15, 2), nullable=True, default=0)
    balance_due = Column(Numeric(15, 2), nullable=True, default=0)
    
    pdf_path = Column(String(500), nullable=True)
    pdf_generated_at = Column(DateTime, nullable=True)
    
    irn_number = Column(String(100), nullable=True)
    e_way_bill_number = Column(String(50), nullable=True)
    
    remarks = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    
    generated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    order = relationship('PartnerOrder', back_populates='invoice')
    
    __table_args__ = (
        CheckConstraint(
            "payment_status IN ('PENDING', 'PARTIAL', 'PAID', 'OVERDUE', 'CANCELLED')",
            name='partner_invoice_payment_status_check'
        ),
        UniqueConstraint('company_id', 'invoice_number', name='uq_partner_invoice_company_inv_num'),
        Index('idx_partner_invoice_company', 'company_id'),
        Index('idx_partner_invoice_date', 'invoice_date'),
        Index('idx_partner_invoice_payment', 'payment_status'),
    )
    
    def __repr__(self):
        return f'<PartnerInvoice {self.invoice_number}: {self.grand_total}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'order_id': self.order_id,
            'partner_id': self.partner_id,
            'company_id': self.company_id,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'taxable_amount': float(self.taxable_amount) if self.taxable_amount else 0,
            'cgst_amount': float(self.cgst_amount) if self.cgst_amount else 0,
            'sgst_amount': float(self.sgst_amount) if self.sgst_amount else 0,
            'igst_amount': float(self.igst_amount) if self.igst_amount else 0,
            'total_tax': float(self.total_tax) if self.total_tax else 0,
            'grand_total': float(self.grand_total) if self.grand_total else 0,
            'amount_in_words': self.amount_in_words,
            'payment_status': self.payment_status,
            'amount_received': float(self.amount_received) if self.amount_received else 0,
            'balance_due': float(self.balance_due) if self.balance_due else 0,
            'pdf_path': self.pdf_path,
            'irn_number': self.irn_number,
            'e_way_bill_number': self.e_way_bill_number
        }


class SalesInvoice(BaseModel):
    """
    Sales Invoice Master
    DC_SALES_001: Company-wise sales invoice with HSN-linked GST calculation
    MANDATORY: company_id for company-wise data segregation
    Auto-updates: Stock Ledger (SALE), Accounts Receivable, Party Ledger, GST Output
    """
    __tablename__ = 'sales_invoices'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(30), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    customer_type = Column(String(20), nullable=False, default='WALK_IN')
    customer_id = Column(Integer, nullable=True)
    customer_real_type = Column(String(30), nullable=True, default='CUSTOMER')
    customer_name = Column(String(200), nullable=False)
    customer_address = Column(Text, nullable=True)
    customer_gstin = Column(String(20), nullable=True)
    customer_state = Column(String(50), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(100), nullable=True)
    
    billing_address = Column(Text, nullable=True)
    shipping_address = Column(Text, nullable=True)
    
    is_igst = Column(Boolean, default=False, nullable=False)
    seller_state = Column(String(50), nullable=True)
    buyer_state = Column(String(50), nullable=True)
    
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    total_discount = Column(Numeric(15, 2), nullable=True, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    cess_amount = Column(Numeric(15, 2), nullable=True, default=0)
    total_tax = Column(Numeric(15, 2), nullable=False, default=0)
    
    round_off = Column(Numeric(10, 2), nullable=True, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    amount_in_words = Column(String(500), nullable=True)
    
    payment_mode = Column(String(30), nullable=True, default=None)
    payment_status = Column(String(20), nullable=False, default='PENDING')
    amount_received = Column(Numeric(15, 2), nullable=True, default=0)
    balance_due = Column(Numeric(15, 2), nullable=True, default=0)
    
    is_credit_sale = Column(Boolean, default=False, nullable=False)
    credit_days = Column(Integer, nullable=True, default=0)
    due_date = Column(Date, nullable=True)
    
    status = Column(String(20), nullable=False, default='DRAFT')
    
    pdf_path = Column(String(500), nullable=True)
    irn_number = Column(String(100), nullable=True)
    ack_number = Column(String(100), nullable=True)
    ack_date = Column(DateTime, nullable=True)
    e_way_bill_number = Column(String(50), nullable=True)
    e_way_bill_date = Column(DateTime, nullable=True)
    
    document_type = Column(String(20), nullable=False, default='tax_invoice')
    return_reference = Column(String(100), nullable=True)  # DC-RETURN-INV-001: original invoice ref for Credit Note
    billing_company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True)

    coupon_code = Column(String(50), nullable=True)
    coupon_discount_pct = Column(Numeric(5, 2), nullable=True, default=0, server_default=text('0'))
    coupon_discount_amount = Column(Numeric(15, 2), nullable=True, default=0, server_default=text('0'))
    manual_discount_amount = Column(Numeric(15, 2), nullable=True, default=0, server_default=text('0'))
    manual_discount_note = Column(Text, nullable=True)
    net_payable = Column(Numeric(15, 2), nullable=True, default=0, server_default=text('0'))

    terms_conditions = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    so_number = Column(String(50), nullable=True)

    # DC-COURIER-001 (Apr 2026): Courier / freight charges on sales invoice (always part of invoice)
    courier_amount = Column(Numeric(15, 2), nullable=True, default=0)
    courier_hsn_code = Column(String(20), nullable=True)
    courier_hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    courier_gst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    courier_cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    courier_sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    courier_igst_amount = Column(Numeric(15, 2), nullable=True, default=0)

    # DC-TRANSPORT-001 (Apr 2026): Transport charges on sales invoice (always part of invoice)
    transport_amount = Column(Numeric(15, 2), nullable=True, default=0)
    transport_hsn_code = Column(String(20), nullable=True)
    transport_hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    transport_gst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    transport_cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    transport_sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    transport_igst_amount = Column(Numeric(15, 2), nullable=True, default=0)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    created_by_type = Column(String(10), nullable=False, default='STAFF')
    partner_id = Column(Integer, nullable=True, index=True)
    linked_walkin_id = Column(Integer, nullable=True)
    fy_sequence = Column(Integer, nullable=True)

    wvv_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    dispatch_status = Column(String(30), nullable=False, default='NOT_DISPATCHED', server_default='NOT_DISPATCHED')
    # DC-DISPATCH-003: opt-in flag — pending dispatch tab only shows invoices where this is True
    track_physical_dispatch = Column(Boolean, nullable=False, default=False, server_default='false')

    line_items = relationship('SalesInvoiceLineItem', back_populates='invoice', cascade='all, delete-orphan')
    payments = relationship('SalesInvoicePayment', back_populates='invoice', cascade='all, delete-orphan', lazy='dynamic')
    billing_company = relationship('AssociatedCompany', foreign_keys=[billing_company_id], lazy='joined')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    cancelled_by = relationship('StaffEmployee', foreign_keys=[cancelled_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'CANCELLED', 'RETURNED', 'VOIDED')",
            name='sales_invoice_status_check'
        ),
        CheckConstraint(
            "payment_status IN ('PENDING', 'PARTIAL', 'PAID', 'OVERDUE')",
            name='sales_invoice_payment_status_check'
        ),
        CheckConstraint(
            "payment_mode IN ('CASH', 'CARD', 'UPI', 'NEFT', 'RTGS', 'CHEQUE', 'CREDIT')",
            name='sales_invoice_payment_mode_check'
        ),
        CheckConstraint(
            "customer_type IN ('WALK_IN', 'REGISTERED', 'PARTNER', 'CORPORATE')",
            name='sales_invoice_customer_type_check'
        ),
        UniqueConstraint('company_id', 'invoice_number', name='uq_sales_invoice_company_inv_num'),
        Index('idx_sales_invoice_company', 'company_id'),
        Index('idx_sales_invoice_date', 'invoice_date'),
        Index('idx_sales_invoice_customer', 'customer_name'),
        Index('idx_sales_invoice_status', 'status'),
    )
    
    def __repr__(self):
        return f'<SalesInvoice {self.invoice_number}: {self.grand_total}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'segment_id': self.segment_id,
            'document_type': self.document_type or 'tax_invoice',
            'billing_company_id': self.billing_company_id,
            'billing_company_name': self.billing_company.company_name if self.billing_company else None,
            'customer_type': self.customer_type,
            'customer_real_type': self.customer_real_type or 'CUSTOMER',
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_address': self.customer_address,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'customer_gstin': self.customer_gstin,
            'customer_state': self.customer_state,
            'is_igst': self.is_igst,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'total_discount': float(self.total_discount) if self.total_discount else 0,
            'taxable_amount': float(self.taxable_amount) if self.taxable_amount else 0,
            'cgst_amount': float(self.cgst_amount) if self.cgst_amount else 0,
            'sgst_amount': float(self.sgst_amount) if self.sgst_amount else 0,
            'igst_amount': float(self.igst_amount) if self.igst_amount else 0,
            'total_tax': float(self.total_tax) if self.total_tax else 0,
            'round_off': float(self.round_off) if self.round_off else 0,
            'grand_total': float(self.grand_total) if self.grand_total else 0,
            'coupon_code': self.coupon_code,
            'coupon_discount_pct': float(self.coupon_discount_pct) if self.coupon_discount_pct else 0,
            'coupon_discount_amount': float(self.coupon_discount_amount) if self.coupon_discount_amount else 0,
            'manual_discount_amount': float(self.manual_discount_amount) if self.manual_discount_amount else 0,
            'manual_discount_note': self.manual_discount_note,
            'net_payable': float(self.net_payable) if self.net_payable else float(self.grand_total) if self.grand_total else 0,
            'payment_mode': self.payment_mode,
            'payment_status': self.payment_status,
            'amount_received': float(self.amount_received) if self.amount_received else 0,
            'balance_due': float(self.balance_due) if self.balance_due else 0,
            'status': self.status,
            'is_credit_sale': self.is_credit_sale,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'terms_conditions': self.terms_conditions,
            'remarks': self.remarks,
            'so_number': self.so_number,
            'billing_address': self.billing_address,
            'shipping_address': self.shipping_address,
            'courier_amount': float(self.courier_amount) if self.courier_amount else 0,
            'courier_hsn_code': self.courier_hsn_code,
            'courier_hsn_id': self.courier_hsn_id,
            'courier_gst_rate': float(self.courier_gst_rate) if self.courier_gst_rate else 0,
            'courier_cgst_amount': float(self.courier_cgst_amount) if self.courier_cgst_amount else 0,
            'courier_sgst_amount': float(self.courier_sgst_amount) if self.courier_sgst_amount else 0,
            'courier_igst_amount': float(self.courier_igst_amount) if self.courier_igst_amount else 0,
            'transport_amount': float(self.transport_amount) if self.transport_amount else 0,
            'transport_hsn_code': self.transport_hsn_code,
            'transport_hsn_id': self.transport_hsn_id,
            'transport_gst_rate': float(self.transport_gst_rate) if self.transport_gst_rate else 0,
            'transport_cgst_amount': float(self.transport_cgst_amount) if self.transport_cgst_amount else 0,
            'transport_sgst_amount': float(self.transport_sgst_amount) if self.transport_sgst_amount else 0,
            'transport_igst_amount': float(self.transport_igst_amount) if self.transport_igst_amount else 0,
            'dispatch_status': self.dispatch_status,
            'track_physical_dispatch': bool(self.track_physical_dispatch),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'cancelled_by_id': self.cancelled_by_id,
            'cancelled_by_name': self.cancelled_by.full_name if (hasattr(self, 'cancelled_by') and self.cancelled_by) else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancellation_reason': self.cancellation_reason,
        }


class SalesInvoiceLineItem(BaseModel):
    """
    Sales Invoice Line Items
    DC_SALES_001: Line items with HSN-linked GST and serial/IMEI tracking
    """
    __tablename__ = 'sales_invoice_line_items'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    item_code = Column(String(30), nullable=True)
    item_description = Column(String(500), nullable=False)
    
    hsn_id = Column(Integer, ForeignKey('hsn_master.id'), nullable=True)
    hsn_code = Column(String(20), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    mrp = Column(Numeric(15, 2), nullable=True)
    
    gross_amount = Column(Numeric(15, 2), nullable=False, default=0)
    discount_percent = Column(Numeric(5, 2), nullable=True, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True, default=0)
    taxable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    gst_rate = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    cgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    sgst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    sgst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    igst_rate = Column(Numeric(5, 2), nullable=True, default=0)
    igst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    cess_rate = Column(Numeric(5, 2), nullable=True, default=0)
    cess_amount = Column(Numeric(15, 2), nullable=True, default=0)
    
    total_tax = Column(Numeric(15, 2), nullable=False, default=0)
    line_total = Column(Numeric(15, 2), nullable=False, default=0)
    
    specification = Column(Text, nullable=True)
    color = Column(String(100), nullable=True)
    
    serial_numbers = Column(JSONB, nullable=True)
    imei_numbers = Column(JSONB, nullable=True)
    batch_number = Column(String(50), nullable=True)
    warranty_months = Column(Integer, nullable=True, default=0)
    warranty_details = Column(Text, nullable=True)
    warranty_end_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    invoice = relationship('SalesInvoice', back_populates='line_items')
    stock_item = relationship('StockItemMaster', foreign_keys=[item_id])
    hsn = relationship('HSNMaster', foreign_keys=[hsn_id])
    
    __table_args__ = (
        Index('idx_sales_line_invoice', 'invoice_id'),
        Index('idx_sales_line_item', 'item_id'),
    )
    
    def __repr__(self):
        return f'<SalesInvoiceLineItem {self.line_number}: {self.item_description}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'line_number': self.line_number,
            'item_id': self.item_id,
            'item_code': self.item_code,
            'item_description': self.item_description,
            'hsn_id': self.hsn_id,
            'hsn_code': self.hsn_code,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_of_measure': self.unit_of_measure,
            'unit_rate': float(self.unit_rate) if self.unit_rate else 0,
            'mrp': float(self.mrp) if self.mrp else None,
            'gross_amount': float(self.gross_amount) if self.gross_amount else 0,
            'discount_percent': float(self.discount_percent) if self.discount_percent else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'taxable_amount': float(self.taxable_amount) if self.taxable_amount else 0,
            'gst_rate': float(self.gst_rate) if self.gst_rate else 0,
            'cgst_amount': float(self.cgst_amount) if self.cgst_amount else 0,
            'sgst_amount': float(self.sgst_amount) if self.sgst_amount else 0,
            'igst_amount': float(self.igst_amount) if self.igst_amount else 0,
            'total_tax': float(self.total_tax) if self.total_tax else 0,
            'line_total': float(self.line_total) if self.line_total else 0,
            'specification': self.specification,
            'color': self.color,
            'serial_numbers': self.serial_numbers,
            'imei_numbers': self.imei_numbers,
            'batch_number': self.batch_number,
            'warranty_months': self.warranty_months,
            'warranty_end_date': self.warranty_end_date.isoformat() if self.warranty_end_date else None
        }


class SalesDispatchRecord(BaseModel):
    """
    Sales Dispatch Records
    DC-DISPATCH-001 (Jun 2026): Tracks partial/full dispatch of items against confirmed sales invoices.
    Confirmed invoice → stock deducted immediately; this table records physical dispatch to customer.
    dispatch_status on SalesInvoice: NOT_DISPATCHED → PARTIALLY_DISPATCHED → FULLY_DISPATCHED
    """
    __tablename__ = 'sales_dispatch_records'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    invoice_line_id = Column(Integer, ForeignKey('sales_invoice_line_items.id'), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)

    dispatched_qty = Column(Numeric(15, 3), nullable=False, default=0)
    dispatched_value = Column(Numeric(15, 2), nullable=False, default=0)
    avg_cost = Column(Numeric(15, 2), nullable=True, default=0)

    dispatch_date = Column(Date, nullable=False)
    narration = Column(Text, nullable=True)

    dispatched_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_sales_dispatch_invoice', 'invoice_id'),
        Index('idx_sales_dispatch_company', 'company_id'),
        Index('idx_sales_dispatch_line', 'invoice_line_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'invoice_id': self.invoice_id,
            'invoice_line_id': self.invoice_line_id,
            'item_id': self.item_id,
            'dispatched_qty': float(self.dispatched_qty) if self.dispatched_qty else 0,
            'dispatched_value': float(self.dispatched_value) if self.dispatched_value else 0,
            'avg_cost': float(self.avg_cost) if self.avg_cost else 0,
            'dispatch_date': self.dispatch_date.isoformat() if self.dispatch_date else None,
            'narration': self.narration,
            'dispatched_by_id': self.dispatched_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SalesInvoicePayment(BaseModel):
    """
    Sales Invoice Payment Transactions
    DC-SALES-PAY: Records individual payment receipts against a sales invoice.
    Supports partial payments, multiple payment modes, reference tracking.
    """
    __tablename__ = 'sales_invoice_payments'

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_mode = Column(String(30), nullable=False, default='CASH')
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    invoice = relationship('SalesInvoice', back_populates='payments', foreign_keys=[invoice_id])
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id])

    __table_args__ = (
        CheckConstraint(
            "payment_mode IN ('CASH', 'CARD', 'UPI', 'NEFT', 'RTGS', 'CHEQUE', 'CREDIT', 'OTHER')",
            name='sip_payment_mode_check'
        ),
        Index('idx_sip_invoice', 'invoice_id'),
    )

    def __repr__(self):
        return f'<SalesInvoicePayment {self.id}: {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': float(self.amount) if self.amount else 0,
            'payment_mode': self.payment_mode,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_by': self.created_by.full_name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SalesCouponMaster(BaseModel):
    """
    Sales billing coupon master — pre-GST percentage discount coupons
    applicable to sales invoices. Managed by accounts staff.
    """
    __tablename__ = 'sales_coupon_master'

    id = Column(Integer, primary_key=True)
    coupon_code = Column(String(50), unique=True, nullable=False)
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    description = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    max_uses = Column(Integer, nullable=True)
    times_used = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'coupon_code': self.coupon_code,
            'discount_percentage': float(self.discount_percentage) if self.discount_percentage else 0,
            'description': self.description,
            'is_active': self.is_active,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'max_uses': self.max_uses,
            'times_used': self.times_used,
        }


class ProcurementRequirement(BaseModel):
    """
    Procurement Requirements Header
    DC_PROCUREMENT_001: Aggregated procurement needs from Manufacturing and Partner Orders
    Tracks material shortages requiring procurement action
    """
    __tablename__ = 'procurement_requirements'
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    priority = Column(String(10), nullable=False, default='NORMAL')
    
    source_type = Column(String(30), nullable=False)
    
    total_items = Column(Integer, nullable=False, default=0)
    total_shortage_value = Column(Numeric(15, 2), nullable=True, default=0)
    
    notes = Column(Text, nullable=True)
    
    triggered_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    triggered_at = Column(DateTime, nullable=True)
    
    acknowledged_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    line_items = relationship('ProcurementRequirementLine', back_populates='requirement', cascade='all, delete-orphan')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    triggered_by = relationship('StaffEmployee', foreign_keys=[triggered_by_id], lazy='joined')
    acknowledged_by = relationship('StaffEmployee', foreign_keys=[acknowledged_by_id], lazy='joined')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ACKNOWLEDGED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name='procurement_req_status_check'
        ),
        CheckConstraint(
            "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')",
            name='procurement_req_priority_check'
        ),
        CheckConstraint(
            "source_type IN ('MANUFACTURING', 'PARTNER_ORDER', 'LOW_STOCK', 'MANUAL')",
            name='procurement_req_source_check'
        ),
        Index('idx_procurement_req_company', 'company_id'),
        Index('idx_procurement_req_status', 'status'),
        Index('idx_procurement_req_priority', 'priority'),
    )
    
    def __repr__(self):
        return f'<ProcurementRequirement {self.requirement_number}: {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'requirement_number': self.requirement_number,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'status': self.status,
            'priority': self.priority,
            'source_type': self.source_type,
            'total_items': self.total_items,
            'total_shortage_value': float(self.total_shortage_value) if self.total_shortage_value else 0,
            'notes': self.notes,
            'triggered_by_name': self.triggered_by.full_name if self.triggered_by else None,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'acknowledged_by_name': self.acknowledged_by.full_name if self.acknowledged_by else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'line_items': [l.to_dict() for l in self.line_items] if self.line_items else []
        }


class ProcurementRequirementLine(BaseModel):
    """
    Procurement Requirement Line Items
    DC_PROCUREMENT_001: Individual component shortage details
    """
    __tablename__ = 'procurement_requirement_lines'
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey('procurement_requirements.id', ondelete='CASCADE'), nullable=False, index=True)
    
    component_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    
    required_qty = Column(Numeric(15, 4), nullable=False)
    available_qty = Column(Numeric(15, 4), nullable=False, default=0)
    shortage_qty = Column(Numeric(15, 4), nullable=False)
    
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    unit_rate = Column(Numeric(15, 2), nullable=True, default=0)
    shortage_value = Column(Numeric(15, 2), nullable=True, default=0)
    
    source_order_ids = Column(JSONB, nullable=True)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    requirement = relationship('ProcurementRequirement', back_populates='line_items')
    component = relationship('StockItemMaster', foreign_keys=[component_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ORDERED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED')",
            name='procurement_line_status_check'
        ),
        Index('idx_procurement_line_req', 'requirement_id'),
        Index('idx_procurement_line_component', 'component_id'),
        UniqueConstraint('requirement_id', 'component_id', name='uq_procurement_req_component'),
    )
    
    def __repr__(self):
        return f'<ProcurementRequirementLine {self.id}: {self.shortage_qty} short>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'component_id': self.component_id,
            'component_code': self.component.item_code if self.component else None,
            'component_name': self.component.item_name if self.component else None,
            'required_qty': float(self.required_qty) if self.required_qty else 0,
            'available_qty': float(self.available_qty) if self.available_qty else 0,
            'shortage_qty': float(self.shortage_qty) if self.shortage_qty else 0,
            'unit_of_measure': self.unit_of_measure,
            'unit_rate': float(self.unit_rate) if self.unit_rate else 0,
            'shortage_value': float(self.shortage_value) if self.shortage_value else 0,
            'source_order_ids': self.source_order_ids,
            'status': self.status
        }


class ProcurementRequest(BaseModel):
    """
    Procurement Request Header - Multi-Quote Workflow
    DC_PROCUREMENT_002: Formal procurement requests with minimum 2 quotes required
    Supports blind bidding (no prices shown to vendors)
    """
    __tablename__ = 'procurement_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    request_date = Column(Date, nullable=False)
    
    status = Column(String(30), nullable=False, default='DRAFT')
    
    min_quotes_required = Column(Integer, nullable=False, default=2)
    quotes_received_count = Column(Integer, nullable=False, default=0)
    
    approved_quote_id = Column(Integer, ForeignKey('procurement_quotes.id', use_alter=True), nullable=True)
    approved_vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    sent_to_vendors_at = Column(DateTime, nullable=True)
    sent_to_vendors_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    approved_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approval_remarks = Column(Text, nullable=True)
    
    po_generated_at = Column(DateTime, nullable=True)
    po_reference_id = Column(Integer, nullable=True)
    
    completed_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    request_items = relationship('ProcurementRequestItem', back_populates='request', cascade='all, delete-orphan')
    quotes = relationship('ProcurementQuote', back_populates='request', foreign_keys='ProcurementQuote.request_id', cascade='all, delete-orphan')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    approved_vendor = relationship('VendorMaster', foreign_keys=[approved_vendor_id], lazy='joined')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='joined')
    approved_by = relationship('StaffEmployee', foreign_keys=[approved_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SENT_TO_VENDORS', 'QUOTES_RECEIVED', 'QUOTE_APPROVED', 'PO_CREATED', 'COMPLETED', 'CANCELLED')",
            name='procurement_request_status_check'
        ),
        Index('idx_proc_request_company', 'company_id'),
        Index('idx_proc_request_status', 'status'),
    )
    
    def __repr__(self):
        return f'<ProcurementRequest {self.request_number}: {self.status}>'
    
    def to_dict(self, include_items=True, include_quotes=False):
        result = {
            'id': self.id,
            'request_number': self.request_number,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'request_date': self.request_date.isoformat() if self.request_date else None,
            'status': self.status,
            'min_quotes_required': self.min_quotes_required,
            'quotes_received_count': self.quotes_received_count,
            'approved_quote_id': self.approved_quote_id,
            'approved_vendor_id': self.approved_vendor_id,
            'approved_vendor_name': self.approved_vendor.vendor_name if self.approved_vendor else None,
            'notes': self.notes,
            'sent_to_vendors_at': self.sent_to_vendors_at.isoformat() if self.sent_to_vendors_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by_name': self.approved_by.full_name if self.approved_by else None,
            'approval_remarks': self.approval_remarks,
            'po_generated_at': self.po_generated_at.isoformat() if self.po_generated_at else None,
            'po_reference_id': self.po_reference_id,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'return_notes': getattr(self, 'return_notes', None),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'approved_vendor_phone': self.approved_vendor.phone if self.approved_vendor else None,
            'created_by_name': self.created_by.full_name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'item_count': len(self.request_items) if self.request_items else 0
        }
        if include_items and self.request_items:
            result['items'] = [i.to_dict() for i in self.request_items]
        if include_quotes and self.quotes:
            result['quotes'] = [q.to_dict() for q in self.quotes]
        return result


class ProcurementRequestItem(BaseModel):
    """
    Procurement Request Line Items - BLIND BIDDING (NO PRICES)
    DC_PROCUREMENT_002: Items required in the procurement request
    No price fields to ensure fair vendor competition
    """
    __tablename__ = 'procurement_request_items'
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey('procurement_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    
    required_qty = Column(Numeric(15, 4), nullable=False)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    specifications = Column(Text, nullable=True)
    
    source_type = Column(String(30), nullable=True)
    source_requirement_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    request = relationship('ProcurementRequest', back_populates='request_items')
    item = relationship('StockItemMaster', foreign_keys=[item_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('LOW_STOCK', 'MANUFACTURING', 'PARTNER_ORDER', 'MANUAL') OR source_type IS NULL",
            name='proc_req_item_source_check'
        ),
        Index('idx_proc_req_item_request', 'request_id'),
        Index('idx_proc_req_item_item', 'item_id'),
        UniqueConstraint('request_id', 'item_id', name='uq_proc_request_item'),
    )
    
    def __repr__(self):
        return f'<ProcurementRequestItem {self.id}: {self.required_qty}>'
    
    def to_dict(self):
        item = self.item
        return {
            'id': self.id,
            'request_id': self.request_id,
            'item_id': self.item_id,
            'item_code': item.item_code if item else None,
            'item_name': item.item_name if item else None,
            'item_category': item.item_category if item else None,
            'hsn_code': item.hsn_code if item else None,
            'brand': item.brand if item else None,
            'model_compat': item.model_compat if item else None,
            'specification': item.specification if item else None,
            'colors': item.colors if item else None,
            'required_qty': float(self.required_qty) if self.required_qty else 0,
            'unit_of_measure': self.unit_of_measure,
            'specifications': self.specifications,
            'source_type': self.source_type,
            'source_requirement_id': self.source_requirement_id
        }


class ProcurementQuote(BaseModel):
    """
    Vendor Quotes (Proforma Invoices)
    DC_PROCUREMENT_002: Minimum 2 quotes required before approval
    Supports quote comparison and approval workflow
    """
    __tablename__ = 'procurement_quotes'
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey('procurement_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=False, index=True)
    
    quote_number = Column(String(50), nullable=True)
    quote_date = Column(Date, nullable=True)
    validity_days = Column(Integer, nullable=True, default=30)
    
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    gst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    other_charges = Column(Numeric(15, 2), nullable=True, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    
    delivery_days = Column(Integer, nullable=True)
    payment_terms = Column(String(100), nullable=True)
    
    quote_document_path = Column(String(500), nullable=True)
    
    status = Column(String(20), nullable=False, default='SUBMITTED')
    is_selected = Column(Boolean, default=False, nullable=False)
    
    review_remarks = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    request = relationship('ProcurementRequest', back_populates='quotes', foreign_keys=[request_id])
    quote_items = relationship('ProcurementQuoteItem', back_populates='quote', cascade='all, delete-orphan')
    vendor = relationship('VendorMaster', foreign_keys=[vendor_id], lazy='joined')
    reviewed_by = relationship('StaffEmployee', foreign_keys=[reviewed_by_id], lazy='joined')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='joined')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED')",
            name='proc_quote_status_check'
        ),
        Index('idx_proc_quote_request', 'request_id'),
        Index('idx_proc_quote_vendor', 'vendor_id'),
        UniqueConstraint('request_id', 'vendor_id', name='uq_proc_quote_vendor'),
    )
    
    def __repr__(self):
        return f'<ProcurementQuote {self.id}: {self.vendor_id} - {self.grand_total}>'
    
    def to_dict(self, include_items=True):
        result = {
            'id': self.id,
            'request_id': self.request_id,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.vendor_name if self.vendor else None,
            'vendor_code': self.vendor.vendor_code if self.vendor else None,
            'quote_number': self.quote_number,
            'quote_date': self.quote_date.isoformat() if self.quote_date else None,
            'validity_days': self.validity_days,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'gst_amount': float(self.gst_amount) if self.gst_amount else 0,
            'other_charges': float(self.other_charges) if self.other_charges else 0,
            'grand_total': float(self.grand_total) if self.grand_total else 0,
            'delivery_days': self.delivery_days,
            'payment_terms': self.payment_terms,
            'quote_document_path': self.quote_document_path,
            'status': self.status,
            'is_selected': self.is_selected,
            'review_remarks': self.review_remarks,
            'reviewed_by_name': self.reviewed_by.full_name if self.reviewed_by else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_by_name': self.created_by.full_name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_items and self.quote_items:
            result['items'] = [i.to_dict() for i in self.quote_items]
        return result


class ProcurementQuoteItem(BaseModel):
    """
    Procurement Quote Line Items - Vendor Pricing
    DC_PROCUREMENT_002: Individual item pricing from vendor quote
    """
    __tablename__ = 'procurement_quote_items'
    
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey('procurement_quotes.id', ondelete='CASCADE'), nullable=False, index=True)
    
    request_item_id = Column(Integer, ForeignKey('procurement_request_items.id'), nullable=False, index=True)
    
    quoted_rate = Column(Numeric(15, 2), nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False)
    
    gst_rate = Column(Numeric(5, 2), nullable=True, default=18)
    gst_amount = Column(Numeric(15, 2), nullable=True, default=0)
    
    amount = Column(Numeric(15, 2), nullable=False)
    
    delivery_date = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    quote = relationship('ProcurementQuote', back_populates='quote_items')
    request_item = relationship('ProcurementRequestItem', foreign_keys=[request_item_id], lazy='joined')
    
    __table_args__ = (
        Index('idx_proc_quote_item_quote', 'quote_id'),
        Index('idx_proc_quote_item_req_item', 'request_item_id'),
    )
    
    def __repr__(self):
        return f'<ProcurementQuoteItem {self.id}: {self.quoted_rate}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'request_item_id': self.request_item_id,
            'item_id': self.request_item.item_id if self.request_item else None,
            'item_code': self.request_item.item.item_code if self.request_item and self.request_item.item else None,
            'item_name': self.request_item.item.item_name if self.request_item and self.request_item.item else None,
            'quoted_rate': float(self.quoted_rate) if self.quoted_rate else 0,
            'quantity': float(self.quantity) if self.quantity else 0,
            'gst_rate': float(self.gst_rate) if self.gst_rate else 0,
            'gst_amount': float(self.gst_amount) if self.gst_amount else 0,
            'amount': float(self.amount) if self.amount else 0,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'remarks': self.remarks
        }


class StaffReimbursementClaim(BaseModel):
    """
    Staff Reimbursement Claims
    DC Protocol: Company-wise expense reimbursement with 2-level approval workflow
    WVV Protocol: Staff token authentication throughout
    
    Workflow: DRAFT → SUBMITTED → MANAGER_APPROVED → FINANCE_APPROVED → SETTLED
    
    Dec 19, 2025: Initial implementation
    """
    __tablename__ = 'staff_reimbursement_claims'
    
    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String(30), unique=True, nullable=False, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey('company_segments.id'), nullable=True)
    
    journey_id = Column(Integer, ForeignKey('staff_journeys.id'), nullable=True, index=True)
    is_travel_claim = Column(Boolean, default=False, nullable=False)
    travel_mode = Column(String(20), nullable=True)
    travel_from = Column(String(200), nullable=True)
    travel_to = Column(String(200), nullable=True)
    distance_km = Column(Numeric(10, 2), nullable=True)
    mileage_rate = Column(Numeric(10, 2), nullable=True)
    
    claim_title = Column(String(200), nullable=False)
    claim_description = Column(Text, nullable=True)
    claim_period_from = Column(Date, nullable=True)
    claim_period_to = Column(Date, nullable=True)
    
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default='INR')
    
    status = Column(String(30), nullable=False, default='DRAFT')
    
    submitted_at = Column(DateTime, nullable=True)
    
    manager_approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    manager_approved_at = Column(DateTime, nullable=True)
    manager_remarks = Column(Text, nullable=True)
    
    finance_approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    finance_approved_at = Column(DateTime, nullable=True)
    finance_remarks = Column(Text, nullable=True)
    
    rejected_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejection_stage = Column(String(20), nullable=True)
    
    settlement_mode = Column(String(20), nullable=True)
    settlement_reference = Column(String(100), nullable=True)
    settled_at = Column(DateTime, nullable=True)
    settled_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    fund_allocation_id = Column(Integer, ForeignKey('fund_allocations.id'), nullable=True)
    expense_entry_id = Column(Integer, ForeignKey('expense_entries.id'), nullable=True)
    
    audit_json = Column(JSONB, nullable=True, default=list)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    employee = relationship('StaffEmployee', foreign_keys=[employee_id], backref='reimbursement_claims')
    company = relationship('AssociatedCompany', foreign_keys=[company_id])
    segment = relationship('CompanySegment', foreign_keys=[segment_id])
    journey = relationship('StaffJourney', foreign_keys=[journey_id])
    manager_approved_by = relationship('StaffEmployee', foreign_keys=[manager_approved_by_id])
    finance_approved_by = relationship('StaffEmployee', foreign_keys=[finance_approved_by_id])
    rejected_by = relationship('StaffEmployee', foreign_keys=[rejected_by_id])
    settled_by = relationship('StaffEmployee', foreign_keys=[settled_by_id])
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id])
    fund_allocation = relationship('FundAllocation', foreign_keys=[fund_allocation_id])
    
    items = relationship('StaffReimbursementClaimItem', back_populates='claim', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'MANAGER_APPROVED', 'FINANCE_APPROVED', 'REJECTED', 'SETTLED', 'CANCELLED')",
            name='reimbursement_claim_status_check'
        ),
        CheckConstraint(
            "travel_mode IS NULL OR travel_mode IN ('BIKE', 'CAR', 'AUTO', 'BUS', 'TRAIN', 'FLIGHT', 'OTHER')",
            name='reimbursement_claim_travel_mode_check'
        ),
        CheckConstraint(
            "settlement_mode IS NULL OR settlement_mode IN ('MANUAL', 'FUND_ALLOCATION', 'BANK_TRANSFER', 'CASH')",
            name='reimbursement_claim_settlement_mode_check'
        ),
        Index('idx_reimb_claim_employee', 'employee_id'),
        Index('idx_reimb_claim_company', 'company_id'),
        Index('idx_reimb_claim_status', 'status'),
        Index('idx_reimb_claim_company_status', 'company_id', 'status'),
    )
    
    def __repr__(self):
        return f'<StaffReimbursementClaim {self.claim_number}: ₹{self.total_amount}>'
    
    def add_audit_entry(self, action: str, user_id: int, details: dict = None):
        """Add audit trail entry"""
        if self.audit_json is None:
            self.audit_json = []
        self.audit_json.append({
            'action': action,
            'user_id': user_id,
            'timestamp': get_indian_time().isoformat(),
            'details': details or {}
        })
    
    def to_dict(self, include_items=False):
        result = {
            'id': self.id,
            'claim_number': self.claim_number,
            'employee_id': self.employee_id,
            'employee_name': self.employee.full_name if self.employee else None,
            'employee_code': self.employee.emp_code if self.employee else None,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'segment_id': self.segment_id,
            'segment_name': self.segment.segment_name if self.segment else None,
            'journey_id': self.journey_id,
            'is_travel_claim': self.is_travel_claim,
            'travel_mode': self.travel_mode,
            'travel_from': self.travel_from,
            'travel_to': self.travel_to,
            'distance_km': float(self.distance_km) if self.distance_km else None,
            'mileage_rate': float(self.mileage_rate) if self.mileage_rate else None,
            'claim_title': self.claim_title,
            'claim_description': self.claim_description,
            'claim_period_from': self.claim_period_from.isoformat() if self.claim_period_from else None,
            'claim_period_to': self.claim_period_to.isoformat() if self.claim_period_to else None,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'currency': self.currency,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'manager_approved_by_id': self.manager_approved_by_id,
            'manager_approved_by_name': self.manager_approved_by.full_name if self.manager_approved_by else None,
            'manager_approved_at': self.manager_approved_at.isoformat() if self.manager_approved_at else None,
            'manager_remarks': self.manager_remarks,
            'finance_approved_by_id': self.finance_approved_by_id,
            'finance_approved_by_name': self.finance_approved_by.full_name if self.finance_approved_by else None,
            'finance_approved_at': self.finance_approved_at.isoformat() if self.finance_approved_at else None,
            'finance_remarks': self.finance_remarks,
            'rejected_by_id': self.rejected_by_id,
            'rejected_by_name': self.rejected_by.full_name if self.rejected_by else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'rejection_stage': self.rejection_stage,
            'settlement_mode': self.settlement_mode,
            'settlement_reference': self.settlement_reference,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None,
            'fund_allocation_id': self.fund_allocation_id,
            'expense_entry_id': self.expense_entry_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'item_count': len(self.items) if self.items else 0
        }
        if include_items:
            result['items'] = [item.to_dict() for item in self.items] if self.items else []
        return result


class StaffReimbursementClaimItem(BaseModel):
    """
    Staff Reimbursement Claim Line Items
    DC Protocol: Individual expense items within a claim
    
    Dec 19, 2025: Initial implementation
    """
    __tablename__ = 'staff_reimbursement_claim_items'
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('staff_reimbursement_claims.id', ondelete='CASCADE'), nullable=False, index=True)
    
    main_category_id = Column(Integer, ForeignKey('expense_main_category.id'), nullable=True)
    sub_category_id = Column(Integer, ForeignKey('expense_sub_category.id'), nullable=True)
    
    expense_date = Column(Date, nullable=False)
    description = Column(String(500), nullable=False)
    vendor_name = Column(String(200), nullable=True)
    
    amount = Column(Numeric(15, 2), nullable=False)
    gst_applicable = Column(Boolean, default=False, nullable=False)
    gst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    net_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    bill_number = Column(String(50), nullable=True)
    bill_date = Column(Date, nullable=True)
    bill_path = Column(String(500), nullable=True)
    bill_remarks = Column(Text, nullable=True)
    
    is_travel_expense = Column(Boolean, default=False, nullable=False)
    travel_mode = Column(String(20), nullable=True)
    travel_from = Column(String(200), nullable=True)
    travel_to = Column(String(200), nullable=True)
    distance_km = Column(Numeric(10, 2), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    claim = relationship('StaffReimbursementClaim', back_populates='items')
    main_category = relationship('ExpenseMainCategory', foreign_keys=[main_category_id])
    sub_category = relationship('ExpenseSubCategory', foreign_keys=[sub_category_id])
    
    __table_args__ = (
        Index('idx_reimb_claim_item_claim', 'claim_id'),
        Index('idx_reimb_claim_item_date', 'expense_date'),
    )
    
    def __repr__(self):
        return f'<StaffReimbursementClaimItem {self.id}: ₹{self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'claim_id': self.claim_id,
            'main_category_id': self.main_category_id,
            'main_category_name': self.main_category.name if self.main_category else None,
            'sub_category_id': self.sub_category_id,
            'sub_category_name': self.sub_category.name if self.sub_category else None,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'description': self.description,
            'vendor_name': self.vendor_name,
            'amount': float(self.amount) if self.amount else 0,
            'gst_applicable': self.gst_applicable,
            'gst_amount': float(self.gst_amount) if self.gst_amount else 0,
            'net_amount': float(self.net_amount) if self.net_amount else 0,
            'bill_number': self.bill_number,
            'bill_date': self.bill_date.isoformat() if self.bill_date else None,
            'bill_path': self.bill_path,
            'bill_remarks': self.bill_remarks,
            'is_travel_expense': self.is_travel_expense,
            'travel_mode': self.travel_mode,
            'travel_from': self.travel_from,
            'travel_to': self.travel_to,
            'distance_km': float(self.distance_km) if self.distance_km else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StockValidationSession(BaseModel):
    """
    Stock Validation Session Header
    DC_STOCK_VALIDATION_001: Periodic stock validation with VGK Supreme approval workflow
    
    Jan 2026: Initial implementation for physical stock verification
    - Supports on-demand and periodic validation cycles
    - Compares system stock (X) vs physical/ground stock (Y)
    - Requires VGK Supreme approval for adjustments
    - Full audit trail maintained
    """
    __tablename__ = 'stock_validation_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    session_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    validation_date = Column(Date, nullable=False, index=True)
    validation_type = Column(String(20), nullable=False, default='ON_DEMAND')
    validation_period = Column(String(20), nullable=True)
    
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    total_items = Column(Integer, nullable=False, default=0)
    items_verified = Column(Integer, nullable=False, default=0)
    items_with_discrepancy = Column(Integer, nullable=False, default=0)
    total_system_value = Column(Numeric(15, 2), nullable=False, default=0)
    total_physical_value = Column(Numeric(15, 2), nullable=False, default=0)
    total_difference_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    status = Column(String(30), nullable=False, default='DRAFT')
    
    initiated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    initiated_at = Column(DateTime, nullable=True)
    
    submitted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    rejected_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    completed_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    entries = relationship('StockValidationEntry', back_populates='session', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint(
            "validation_type IN ('ON_DEMAND', 'MONTHLY', 'QUARTERLY', 'YEARLY')",
            name='stock_validation_type_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'IN_PROGRESS', 'VERIFIED', 'AWAITING_APPROVAL', 'APPROVED', 'REJECTED', 'COMPLETED', 'CANCELLED')",
            name='stock_validation_status_check'
        ),
        Index('idx_stock_validation_company', 'company_id'),
        Index('idx_stock_validation_date', 'validation_date'),
        Index('idx_stock_validation_status', 'status'),
    )
    
    def __repr__(self):
        return f'<StockValidationSession {self.session_number}: {self.status}>'
    
    def to_dict(self, include_entries=False):
        result = {
            'id': self.id,
            'session_number': self.session_number,
            'company_id': self.company_id,
            'validation_date': self.validation_date.isoformat() if self.validation_date else None,
            'validation_type': self.validation_type,
            'validation_period': self.validation_period,
            'title': self.title,
            'description': self.description,
            'total_items': self.total_items,
            'items_verified': self.items_verified,
            'items_with_discrepancy': self.items_with_discrepancy,
            'total_system_value': float(self.total_system_value) if self.total_system_value else 0,
            'total_physical_value': float(self.total_physical_value) if self.total_physical_value else 0,
            'total_difference_value': float(self.total_difference_value) if self.total_difference_value else 0,
            'status': self.status,
            'initiated_by_id': self.initiated_by_id,
            'initiated_at': self.initiated_at.isoformat() if self.initiated_at else None,
            'submitted_by_id': self.submitted_by_id,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_by_id': self.approved_by_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'rejected_by_id': self.rejected_by_id,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_entries and hasattr(self, 'entries') and self.entries:
            result['entries'] = [e.to_dict() for e in self.entries]
        return result


class StockValidationEntry(BaseModel):
    """
    Stock Validation Entry Line Item
    DC_STOCK_VALIDATION_002: Individual item validation within a session
    
    Tracks system qty (X) vs physical qty (Y) with serial number reconciliation
    """
    __tablename__ = 'stock_validation_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('stock_validation_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    item_code = Column(String(30), nullable=False)
    item_name = Column(String(200), nullable=False)
    item_category = Column(String(30), nullable=True)
    
    specification = Column(Text, nullable=True)
    color = Column(String(100), nullable=True)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    
    system_qty = Column(Numeric(15, 3), nullable=False, default=0)
    system_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    physical_qty = Column(Numeric(15, 3), nullable=True)
    physical_value = Column(Numeric(15, 2), nullable=True)
    
    difference_qty = Column(Numeric(15, 3), nullable=True)
    difference_value = Column(Numeric(15, 2), nullable=True)
    
    serial_numbers_expected = Column(JSONB, nullable=True)
    serial_numbers_found = Column(JSONB, nullable=True)
    serial_numbers_missing = Column(JSONB, nullable=True)
    serial_numbers_extra = Column(JSONB, nullable=True)
    
    reason_for_difference = Column(String(50), nullable=True)
    difference_notes = Column(Text, nullable=True)
    
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    ledger_entry_id = Column(Integer, ForeignKey('stock_ledger.id'), nullable=True)
    adjustment_processed = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    session = relationship('StockValidationSession', back_populates='entries')
    stock_item = relationship('StockItemMaster', foreign_keys=[item_id])
    
    __table_args__ = (
        CheckConstraint(
            "reason_for_difference IS NULL OR reason_for_difference IN ('DAMAGED', 'STOLEN', 'MISCOUNTED', 'TRANSFER_PENDING', 'EXPIRED', 'QUALITY_ISSUE', 'OTHER')",
            name='stock_validation_reason_check'
        ),
        Index('idx_stock_validation_entry_session', 'session_id'),
        Index('idx_stock_validation_entry_item', 'item_id'),
        UniqueConstraint('session_id', 'item_id', name='uq_validation_session_item'),
    )
    
    def __repr__(self):
        return f'<StockValidationEntry {self.item_code}: System={self.system_qty} Physical={self.physical_qty}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'item_id': self.item_id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'item_category': self.item_category,
            'specification': self.specification,
            'color': self.color,
            'unit_of_measure': self.unit_of_measure,
            'system_qty': float(self.system_qty) if self.system_qty else 0,
            'system_value': float(self.system_value) if self.system_value else 0,
            'physical_qty': float(self.physical_qty) if self.physical_qty is not None else None,
            'physical_value': float(self.physical_value) if self.physical_value is not None else None,
            'difference_qty': float(self.difference_qty) if self.difference_qty is not None else None,
            'difference_value': float(self.difference_value) if self.difference_value is not None else None,
            'serial_numbers_expected': self.serial_numbers_expected,
            'serial_numbers_found': self.serial_numbers_found,
            'serial_numbers_missing': self.serial_numbers_missing,
            'serial_numbers_extra': self.serial_numbers_extra,
            'reason_for_difference': self.reason_for_difference,
            'difference_notes': self.difference_notes,
            'is_verified': self.is_verified,
            'verified_by_id': self.verified_by_id,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'ledger_entry_id': self.ledger_entry_id,
            'adjustment_processed': self.adjustment_processed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StockValidationAuditLog(BaseModel):
    """
    Stock Validation Audit Log
    DC_STOCK_VALIDATION_003: Complete audit trail for all validation actions
    """
    __tablename__ = 'stock_validation_audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('stock_validation_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    entry_id = Column(Integer, ForeignKey('stock_validation_entries.id', ondelete='SET NULL'), nullable=True)
    
    action = Column(String(50), nullable=False)
    action_details = Column(JSONB, nullable=True)
    
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    
    performed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False)
    performed_at = Column(DateTime, default=get_indian_time, nullable=False)
    ip_address = Column(String(50), nullable=True)
    
    __table_args__ = (
        Index('idx_validation_audit_session', 'session_id'),
        Index('idx_validation_audit_action', 'action'),
        Index('idx_validation_audit_performer', 'performed_by_id'),
    )
    
    def __repr__(self):
        return f'<StockValidationAuditLog {self.action} by {self.performed_by_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'entry_id': self.entry_id,
            'action': self.action,
            'action_details': self.action_details,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'performed_by_id': self.performed_by_id,
            'performed_at': self.performed_at.isoformat() if self.performed_at else None,
            'ip_address': self.ip_address
        }


class PurchaseIntakeBatch(BaseModel):
    """
    Purchase Intake Batch
    DC_INTAKE_001: Links purchase invoice to validation process
    Jan 2026: All purchased items must pass through QC before inventory update
    
    Flow: Invoice CONFIRMED → Intake Batch Created → QC → Approval → Stock Update
    Tracks: Ordered vs Received vs QC Passed quantities
    """
    __tablename__ = 'purchase_intake_batches'
    
    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    purchase_invoice_id = Column(Integer, ForeignKey('purchase_invoice_uploads.id'), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True, index=True)
    
    total_ordered_qty = Column(Numeric(15, 3), nullable=False, default=0)
    total_received_qty = Column(Numeric(15, 3), nullable=False, default=0)
    total_accepted_qty = Column(Numeric(15, 3), nullable=False, default=0)
    total_rejected_qty = Column(Numeric(15, 3), nullable=False, default=0)
    total_pending_qty = Column(Numeric(15, 3), nullable=False, default=0)
    
    total_ordered_value = Column(Numeric(15, 2), nullable=False, default=0)
    total_received_value = Column(Numeric(15, 2), nullable=False, default=0)
    total_accepted_value = Column(Numeric(15, 2), nullable=False, default=0)
    total_rejected_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    intake_status = Column(String(30), nullable=False, default='PENDING_RECEIPT')
    
    received_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    received_at = Column(DateTime, nullable=True)
    receipt_notes = Column(Text, nullable=True)
    
    qc_started_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    qc_started_at = Column(DateTime, nullable=True)
    qc_completed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    qc_completed_at = Column(DateTime, nullable=True)
    
    submitted_for_approval_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    submitted_for_approval_at = Column(DateTime, nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    rejected_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    stock_ledger_updated = Column(Boolean, default=False, nullable=False)
    stock_ledger_updated_at = Column(DateTime, nullable=True)
    
    validation_session_id = Column(Integer, ForeignKey('stock_validation_sessions.id'), nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    items = relationship('PurchaseIntakeItem', back_populates='batch', cascade='all, delete-orphan')
    purchase_invoice = relationship('PurchaseInvoiceUpload', backref='intake_batches')
    vendor = relationship('OfficialPartner', backref='intake_batches')
    
    __table_args__ = (
        CheckConstraint(
            "intake_status IN ('PENDING_RECEIPT', 'PARTIALLY_RECEIVED', 'FULLY_RECEIVED', 'QC_PENDING', 'QC_IN_PROGRESS', 'QC_COMPLETE', 'AWAITING_APPROVAL', 'APPROVED', 'REJECTED', 'COMPLETED', 'CANCELLED')",
            name='intake_batch_status_check'
        ),
        Index('idx_intake_batch_company', 'company_id'),
        Index('idx_intake_batch_invoice', 'purchase_invoice_id'),
        Index('idx_intake_batch_status', 'intake_status'),
        Index('idx_intake_batch_vendor', 'vendor_id'),
    )
    
    def __repr__(self):
        return f'<PurchaseIntakeBatch {self.batch_number}: {self.intake_status}>'
    
    def to_dict(self, include_items=False):
        result = {
            'id': self.id,
            'batch_number': self.batch_number,
            'company_id': self.company_id,
            'purchase_invoice_id': self.purchase_invoice_id,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.partner_name if self.vendor else None,
            'total_ordered_qty': float(self.total_ordered_qty) if self.total_ordered_qty else 0,
            'total_received_qty': float(self.total_received_qty) if self.total_received_qty else 0,
            'total_accepted_qty': float(self.total_accepted_qty) if self.total_accepted_qty else 0,
            'total_rejected_qty': float(self.total_rejected_qty) if self.total_rejected_qty else 0,
            'total_pending_qty': float(self.total_pending_qty) if self.total_pending_qty else 0,
            'total_ordered_value': float(self.total_ordered_value) if self.total_ordered_value else 0,
            'total_received_value': float(self.total_received_value) if self.total_received_value else 0,
            'total_accepted_value': float(self.total_accepted_value) if self.total_accepted_value else 0,
            'total_rejected_value': float(self.total_rejected_value) if self.total_rejected_value else 0,
            'intake_status': self.intake_status,
            'received_by_id': self.received_by_id,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'receipt_notes': self.receipt_notes,
            'qc_started_at': self.qc_started_at.isoformat() if self.qc_started_at else None,
            'qc_completed_at': self.qc_completed_at.isoformat() if self.qc_completed_at else None,
            'submitted_for_approval_at': self.submitted_for_approval_at.isoformat() if self.submitted_for_approval_at else None,
            'approved_by_id': self.approved_by_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'rejected_by_id': self.rejected_by_id,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'stock_ledger_updated': self.stock_ledger_updated,
            'validation_session_id': self.validation_session_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_items and hasattr(self, 'items') and self.items:
            result['items'] = [item.to_dict() for item in self.items]
        return result


class PurchaseIntakeItem(BaseModel):
    """
    Purchase Intake Item
    DC_INTAKE_002: Per-item/serial tracking with QC results
    
    Tracks individual item QC status and disposition
    """
    __tablename__ = 'purchase_intake_items'
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey('purchase_intake_batches.id', ondelete='CASCADE'), nullable=False, index=True)
    purchase_line_id = Column(Integer, ForeignKey('purchase_invoice_line_items.id'), nullable=True, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)
    item_code = Column(String(30), nullable=True)
    item_name = Column(String(200), nullable=False)
    item_description = Column(Text, nullable=True)
    hsn_code = Column(String(20), nullable=True)
    
    serial_number = Column(String(100), nullable=True, index=True)
    imei_number = Column(String(50), nullable=True, index=True)
    batch_number = Column(String(50), nullable=True)
    
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    
    ordered_qty = Column(Numeric(15, 3), nullable=False, default=0)
    received_qty = Column(Numeric(15, 3), nullable=False, default=0)
    accepted_qty = Column(Numeric(15, 3), nullable=False, default=0)
    rejected_qty = Column(Numeric(15, 3), nullable=False, default=0)
    
    ordered_value = Column(Numeric(15, 2), nullable=False, default=0)
    received_value = Column(Numeric(15, 2), nullable=False, default=0)
    accepted_value = Column(Numeric(15, 2), nullable=False, default=0)
    rejected_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    qc_status = Column(String(20), nullable=False, default='PENDING')
    
    qc_checklist = Column(JSONB, nullable=True)
    
    disposition = Column(String(20), nullable=True)
    
    qc_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    qc_at = Column(DateTime, nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    rejection_category = Column(String(50), nullable=True)
    
    warranty_months = Column(Integer, nullable=True, default=0)
    warranty_start_date = Column(Date, nullable=True)
    warranty_end_date = Column(Date, nullable=True)
    
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    
    specification = Column(Text, nullable=True)
    color = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    batch = relationship('PurchaseIntakeBatch', back_populates='items')
    
    __table_args__ = (
        CheckConstraint(
            "qc_status IN ('PENDING', 'IN_PROGRESS', 'ACCEPTED', 'REJECTED', 'PARTIAL')",
            name='intake_item_qc_status_check'
        ),
        CheckConstraint(
            "disposition IN ('STOCK', 'RETURN', 'EXCHANGE', 'PENDING_VENDOR', 'SCRAPPED') OR disposition IS NULL",
            name='intake_item_disposition_check'
        ),
        Index('idx_intake_item_batch', 'batch_id'),
        Index('idx_intake_item_serial', 'serial_number'),
        Index('idx_intake_item_qc_status', 'qc_status'),
    )
    
    def __repr__(self):
        return f'<PurchaseIntakeItem {self.item_name}: {self.qc_status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'purchase_line_id': self.purchase_line_id,
            'item_id': self.item_id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'item_description': self.item_description,
            'hsn_code': self.hsn_code,
            'serial_number': self.serial_number,
            'imei_number': self.imei_number,
            'batch_number': self.batch_number,
            'unit_of_measure': self.unit_of_measure,
            'unit_rate': float(self.unit_rate) if self.unit_rate else 0,
            'ordered_qty': float(self.ordered_qty) if self.ordered_qty else 0,
            'received_qty': float(self.received_qty) if self.received_qty else 0,
            'accepted_qty': float(self.accepted_qty) if self.accepted_qty else 0,
            'rejected_qty': float(self.rejected_qty) if self.rejected_qty else 0,
            'ordered_value': float(self.ordered_value) if self.ordered_value else 0,
            'received_value': float(self.received_value) if self.received_value else 0,
            'accepted_value': float(self.accepted_value) if self.accepted_value else 0,
            'rejected_value': float(self.rejected_value) if self.rejected_value else 0,
            'qc_status': self.qc_status,
            'qc_checklist': self.qc_checklist,
            'disposition': self.disposition,
            'qc_by_id': self.qc_by_id,
            'qc_at': self.qc_at.isoformat() if self.qc_at else None,
            'rejection_reason': self.rejection_reason,
            'rejection_category': self.rejection_category,
            'warranty_months': self.warranty_months,
            'warranty_start_date': self.warranty_start_date.isoformat() if self.warranty_start_date else None,
            'warranty_end_date': self.warranty_end_date.isoformat() if self.warranty_end_date else None,
            'manufacturing_date': self.manufacturing_date.isoformat() if self.manufacturing_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'specification': self.specification,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class InventoryLifecycleEvent(BaseModel):
    """
    Inventory Lifecycle Event
    DC_LIFECYCLE_001: Immutable audit log for every item movement
    
    Tracks complete journey: Purchase → QC → Stock → Service → Vendor
    Every handover point is recorded with checksum for immutability
    """
    __tablename__ = 'inventory_lifecycle_events'
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)
    item_code = Column(String(30), nullable=True)
    item_name = Column(String(200), nullable=True)
    
    serial_number = Column(String(100), nullable=True, index=True)
    imei_number = Column(String(50), nullable=True, index=True)
    batch_number = Column(String(50), nullable=True)
    
    event_type = Column(String(50), nullable=False, index=True)
    
    source_document_type = Column(String(50), nullable=True)
    source_document_id = Column(Integer, nullable=True)
    source_document_number = Column(String(50), nullable=True)
    
    from_location = Column(String(100), nullable=True)
    to_location = Column(String(100), nullable=True)
    
    from_entity_type = Column(String(30), nullable=True)
    from_entity_id = Column(Integer, nullable=True)
    from_entity_name = Column(String(200), nullable=True)
    
    to_entity_type = Column(String(30), nullable=True)
    to_entity_id = Column(Integer, nullable=True)
    to_entity_name = Column(String(200), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_value = Column(Numeric(15, 2), nullable=True)
    total_value = Column(Numeric(15, 2), nullable=True)
    
    event_data = Column(JSONB, nullable=True)
    
    event_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    event_by_partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    event_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    checksum = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('PURCHASE_ORDERED', 'PURCHASE_RECEIVED', 'QC_STARTED', 'QC_PASSED', 'QC_REJECTED', 'ADDED_TO_STOCK', 'REMOVED_FROM_STOCK', 'TRANSFERRED', 'DISPATCHED_TO_SERVICE', 'RECEIVED_AT_SERVICE', 'DIAGNOSIS_COMPLETE', 'REPAIR_STARTED', 'REPAIR_COMPLETE', 'DISPATCHED_TO_VENDOR', 'VENDOR_RECEIVED', 'VENDOR_RETURNED', 'CREDIT_NOTE_ISSUED', 'EXCHANGE_RECEIVED', 'REPLACEMENT_ISSUED', 'RETURNED_TO_CUSTOMER', 'SCRAPPED', 'ADJUSTED')",
            name='lifecycle_event_type_check'
        ),
        Index('idx_lifecycle_company', 'company_id'),
        Index('idx_lifecycle_item', 'item_id'),
        Index('idx_lifecycle_serial', 'serial_number'),
        Index('idx_lifecycle_event_type', 'event_type'),
        Index('idx_lifecycle_event_at', 'event_at'),
    )
    
    def __repr__(self):
        return f'<InventoryLifecycleEvent {self.event_id}: {self.event_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'company_id': self.company_id,
            'item_id': self.item_id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'serial_number': self.serial_number,
            'imei_number': self.imei_number,
            'batch_number': self.batch_number,
            'event_type': self.event_type,
            'source_document_type': self.source_document_type,
            'source_document_id': self.source_document_id,
            'source_document_number': self.source_document_number,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'from_entity_type': self.from_entity_type,
            'from_entity_id': self.from_entity_id,
            'from_entity_name': self.from_entity_name,
            'to_entity_type': self.to_entity_type,
            'to_entity_id': self.to_entity_id,
            'to_entity_name': self.to_entity_name,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_value': float(self.unit_value) if self.unit_value else None,
            'total_value': float(self.total_value) if self.total_value else None,
            'event_data': self.event_data,
            'event_by_id': self.event_by_id,
            'event_by_partner_id': self.event_by_partner_id,
            'event_at': self.event_at.isoformat() if self.event_at else None,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class VendorReturnRequest(BaseModel):
    """
    Vendor Return Request
    DC_RETURN_001: Header for return/exchange requests to vendors
    
    Tracks complete return lifecycle with email/WhatsApp notifications
    Integrates with SFMS for credit note and AP adjustments
    """
    __tablename__ = 'vendor_return_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    intake_batch_id = Column(Integer, ForeignKey('purchase_intake_batches.id'), nullable=True, index=True)
    
    request_type = Column(String(20), nullable=False)
    
    total_items = Column(Integer, nullable=False, default=0)
    total_qty = Column(Numeric(15, 3), nullable=False, default=0)
    total_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    status = Column(String(30), nullable=False, default='CREATED')
    
    vendor_response_deadline = Column(DateTime, nullable=True)
    vendor_acknowledged_at = Column(DateTime, nullable=True)
    vendor_remarks = Column(Text, nullable=True)
    
    dispatch_date = Column(Date, nullable=True)
    dispatch_courier = Column(String(100), nullable=True)
    dispatch_tracking_number = Column(String(100), nullable=True)
    dispatch_notes = Column(Text, nullable=True)
    
    received_by_vendor_at = Column(DateTime, nullable=True)
    vendor_received_notes = Column(Text, nullable=True)
    
    credit_note_number = Column(String(50), nullable=True)
    credit_note_date = Column(Date, nullable=True)
    credit_note_amount = Column(Numeric(15, 2), nullable=True)
    
    exchange_received_at = Column(DateTime, nullable=True)
    exchange_qc_status = Column(String(20), nullable=True)
    exchange_intake_batch_id = Column(Integer, ForeignKey('purchase_intake_batches.id'), nullable=True)
    
    sfms_journal_id = Column(Integer, nullable=True)
    
    email_log = Column(JSONB, nullable=True)
    whatsapp_log = Column(JSONB, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    items = relationship('VendorReturnItem', back_populates='request', cascade='all, delete-orphan')
    vendor = relationship('OfficialPartner', foreign_keys=[vendor_id], backref='return_requests')
    intake_batch = relationship('PurchaseIntakeBatch', foreign_keys=[intake_batch_id], backref='return_requests')
    
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('RETURN', 'EXCHANGE')",
            name='vendor_return_type_check'
        ),
        CheckConstraint(
            "status IN ('CREATED', 'VENDOR_NOTIFIED', 'VENDOR_ACKNOWLEDGED', 'PICKUP_SCHEDULED', 'IN_TRANSIT', 'VENDOR_RECEIVED', 'CREDIT_NOTE_PENDING', 'CREDIT_NOTE_ISSUED', 'EXCHANGE_DISPATCHED', 'EXCHANGE_RECEIVED', 'CLOSED', 'CANCELLED')",
            name='vendor_return_status_check'
        ),
        Index('idx_return_company', 'company_id'),
        Index('idx_return_vendor', 'vendor_id'),
        Index('idx_return_status', 'status'),
        Index('idx_return_type', 'request_type'),
    )
    
    def __repr__(self):
        return f'<VendorReturnRequest {self.request_number}: {self.status}>'
    
    def to_dict(self, include_items=False):
        result = {
            'id': self.id,
            'request_number': self.request_number,
            'company_id': self.company_id,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.partner_name if self.vendor else None,
            'intake_batch_id': self.intake_batch_id,
            'request_type': self.request_type,
            'total_items': self.total_items,
            'total_qty': float(self.total_qty) if self.total_qty else 0,
            'total_value': float(self.total_value) if self.total_value else 0,
            'status': self.status,
            'vendor_response_deadline': self.vendor_response_deadline.isoformat() if self.vendor_response_deadline else None,
            'vendor_acknowledged_at': self.vendor_acknowledged_at.isoformat() if self.vendor_acknowledged_at else None,
            'vendor_remarks': self.vendor_remarks,
            'dispatch_date': self.dispatch_date.isoformat() if self.dispatch_date else None,
            'dispatch_courier': self.dispatch_courier,
            'dispatch_tracking_number': self.dispatch_tracking_number,
            'received_by_vendor_at': self.received_by_vendor_at.isoformat() if self.received_by_vendor_at else None,
            'credit_note_number': self.credit_note_number,
            'credit_note_date': self.credit_note_date.isoformat() if self.credit_note_date else None,
            'credit_note_amount': float(self.credit_note_amount) if self.credit_note_amount else None,
            'exchange_received_at': self.exchange_received_at.isoformat() if self.exchange_received_at else None,
            'exchange_qc_status': self.exchange_qc_status,
            'sfms_journal_id': self.sfms_journal_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_items and hasattr(self, 'items') and self.items:
            result['items'] = [item.to_dict() for item in self.items]
        return result


class VendorReturnItem(BaseModel):
    """
    Vendor Return Item
    DC_RETURN_002: Line items being returned with serial tracking
    """
    __tablename__ = 'vendor_return_items'
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey('vendor_return_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    intake_item_id = Column(Integer, ForeignKey('purchase_intake_items.id'), nullable=True, index=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)
    item_code = Column(String(30), nullable=True)
    item_name = Column(String(200), nullable=False)
    
    serial_number = Column(String(100), nullable=True, index=True)
    imei_number = Column(String(50), nullable=True)
    batch_number = Column(String(50), nullable=True)
    
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_rate = Column(Numeric(15, 2), nullable=False, default=0)
    total_value = Column(Numeric(15, 2), nullable=False, default=0)
    
    rejection_reason = Column(Text, nullable=True)
    rejection_category = Column(String(50), nullable=True)
    qc_checklist = Column(JSONB, nullable=True)
    
    item_status = Column(String(30), nullable=False, default='PENDING')
    
    exchange_serial_number = Column(String(100), nullable=True)
    exchange_imei_number = Column(String(50), nullable=True)
    exchange_qc_status = Column(String(20), nullable=True)
    exchange_qc_at = Column(DateTime, nullable=True)
    exchange_qc_checklist = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    request = relationship('VendorReturnRequest', back_populates='items')
    
    __table_args__ = (
        CheckConstraint(
            "item_status IN ('PENDING', 'DISPATCHED', 'RECEIVED_BY_VENDOR', 'CREDIT_ISSUED', 'EXCHANGE_DISPATCHED', 'EXCHANGE_RECEIVED', 'CLOSED')",
            name='return_item_status_check'
        ),
        Index('idx_return_item_request', 'request_id'),
        Index('idx_return_item_serial', 'serial_number'),
        Index('idx_return_item_status', 'item_status'),
    )
    
    def __repr__(self):
        return f'<VendorReturnItem {self.item_name}: {self.item_status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'intake_item_id': self.intake_item_id,
            'item_id': self.item_id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'serial_number': self.serial_number,
            'imei_number': self.imei_number,
            'batch_number': self.batch_number,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_rate': float(self.unit_rate) if self.unit_rate else 0,
            'total_value': float(self.total_value) if self.total_value else 0,
            'rejection_reason': self.rejection_reason,
            'rejection_category': self.rejection_category,
            'qc_checklist': self.qc_checklist,
            'item_status': self.item_status,
            'exchange_serial_number': self.exchange_serial_number,
            'exchange_imei_number': self.exchange_imei_number,
            'exchange_qc_status': self.exchange_qc_status,
            'exchange_qc_at': self.exchange_qc_at.isoformat() if self.exchange_qc_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ServiceCenterReceipt(BaseModel):
    """
    Service Center Receipt
    DC_SERVICE_001: Items received at service center from partner/customer
    
    Tracks: Receipt → Diagnosis → Repair/Replace/Escalate workflow
    Links to service tickets and inventory lifecycle
    """
    __tablename__ = 'service_center_receipts'
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    service_center_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    service_ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=True, index=True)
    
    customer_name = Column(String(200), nullable=True)
    customer_contact = Column(String(20), nullable=True)
    customer_email = Column(String(200), nullable=True)
    customer_address = Column(Text, nullable=True)
    
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)
    item_code = Column(String(30), nullable=True)
    item_name = Column(String(200), nullable=False)
    item_description = Column(Text, nullable=True)
    
    serial_number = Column(String(100), nullable=True, index=True)
    imei_number = Column(String(50), nullable=True)
    
    item_condition_on_receipt = Column(JSONB, nullable=True)
    reported_issue = Column(Text, nullable=True)
    accessories_received = Column(JSONB, nullable=True)
    receipt_photos = Column(JSONB, nullable=True)
    
    receipt_status = Column(String(30), nullable=False, default='REGISTERED')
    
    received_by_id = Column(Integer, nullable=True)
    received_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    diagnosis_status = Column(String(20), nullable=True, default='PENDING')
    diagnosis_result = Column(String(30), nullable=True)
    diagnosis_notes = Column(Text, nullable=True)
    diagnosis_cost_estimate = Column(Numeric(15, 2), nullable=True)
    diagnosed_by_id = Column(Integer, nullable=True)
    diagnosed_at = Column(DateTime, nullable=True)
    
    repair_status = Column(String(20), nullable=True)
    repair_notes = Column(Text, nullable=True)
    repair_cost = Column(Numeric(15, 2), nullable=True)
    parts_used = Column(JSONB, nullable=True)
    repaired_by_id = Column(Integer, nullable=True)
    repaired_at = Column(DateTime, nullable=True)
    
    replacement_item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    replacement_serial_number = Column(String(100), nullable=True)
    replacement_issued_at = Column(DateTime, nullable=True)
    
    returned_to_customer_at = Column(DateTime, nullable=True)
    customer_acknowledgment = Column(Text, nullable=True)
    customer_signature_path = Column(String(500), nullable=True)
    
    escalated_to_head_office = Column(Boolean, default=False, nullable=False)
    escalation_date = Column(DateTime, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    escalation_dispatch_id = Column(Integer, ForeignKey('service_center_dispatches.id'), nullable=True)
    
    warranty_status = Column(String(20), nullable=True)
    warranty_claim_number = Column(String(50), nullable=True)
    
    created_by_id = Column(Integer, nullable=True)
    updated_by_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    service_center = relationship('OfficialPartner', foreign_keys=[service_center_id], backref='service_receipts')
    
    __table_args__ = (
        CheckConstraint(
            "receipt_status IN ('REGISTERED', 'DIAGNOSIS_PENDING', 'DIAGNOSIS_IN_PROGRESS', 'DIAGNOSED', 'REPAIR_IN_PROGRESS', 'REPAIRED', 'REPLACEMENT_PENDING', 'REPLACEMENT_ISSUED', 'ESCALATED', 'RETURNED_TO_CUSTOMER', 'CLOSED', 'CANCELLED')",
            name='service_receipt_status_check'
        ),
        CheckConstraint(
            "diagnosis_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED') OR diagnosis_status IS NULL",
            name='diagnosis_status_check'
        ),
        CheckConstraint(
            "diagnosis_result IN ('REPAIRABLE', 'REPLACEMENT_REQUIRED', 'ESCALATE_TO_VENDOR', 'NO_ISSUE_FOUND', 'BEYOND_REPAIR') OR diagnosis_result IS NULL",
            name='diagnosis_result_check'
        ),
        Index('idx_service_receipt_company', 'company_id'),
        Index('idx_service_receipt_center', 'service_center_id'),
        Index('idx_service_receipt_ticket', 'service_ticket_id'),
        Index('idx_service_receipt_serial', 'serial_number'),
        Index('idx_service_receipt_status', 'receipt_status'),
    )
    
    def __repr__(self):
        return f'<ServiceCenterReceipt {self.receipt_number}: {self.receipt_status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'receipt_number': self.receipt_number,
            'company_id': self.company_id,
            'service_center_id': self.service_center_id,
            'service_center_name': self.service_center.partner_name if self.service_center else None,
            'service_ticket_id': self.service_ticket_id,
            'customer_name': self.customer_name,
            'customer_contact': self.customer_contact,
            'customer_email': self.customer_email,
            'item_id': self.item_id,
            'item_code': self.item_code,
            'item_name': self.item_name,
            'item_description': self.item_description,
            'serial_number': self.serial_number,
            'imei_number': self.imei_number,
            'item_condition_on_receipt': self.item_condition_on_receipt,
            'reported_issue': self.reported_issue,
            'accessories_received': self.accessories_received,
            'receipt_status': self.receipt_status,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'diagnosis_status': self.diagnosis_status,
            'diagnosis_result': self.diagnosis_result,
            'diagnosis_notes': self.diagnosis_notes,
            'diagnosis_cost_estimate': float(self.diagnosis_cost_estimate) if self.diagnosis_cost_estimate else None,
            'diagnosed_at': self.diagnosed_at.isoformat() if self.diagnosed_at else None,
            'repair_status': self.repair_status,
            'repair_notes': self.repair_notes,
            'repair_cost': float(self.repair_cost) if self.repair_cost else None,
            'parts_used': self.parts_used,
            'repaired_at': self.repaired_at.isoformat() if self.repaired_at else None,
            'replacement_serial_number': self.replacement_serial_number,
            'replacement_issued_at': self.replacement_issued_at.isoformat() if self.replacement_issued_at else None,
            'returned_to_customer_at': self.returned_to_customer_at.isoformat() if self.returned_to_customer_at else None,
            'escalated_to_head_office': self.escalated_to_head_office,
            'escalation_date': self.escalation_date.isoformat() if self.escalation_date else None,
            'escalation_reason': self.escalation_reason,
            'warranty_status': self.warranty_status,
            'warranty_claim_number': self.warranty_claim_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ServiceCenterDispatch(BaseModel):
    """
    Service Center Dispatch
    DC_SERVICE_002: Items sent from service center to vendor
    
    Tracks: Dispatch → Vendor Acknowledge → Replacement/Resolution workflow
    """
    __tablename__ = 'service_center_dispatches'
    
    id = Column(Integer, primary_key=True, index=True)
    dispatch_number = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    service_center_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    
    dispatch_type = Column(String(30), nullable=False)
    
    total_items = Column(Integer, nullable=False, default=0)
    
    status = Column(String(30), nullable=False, default='DRAFT')
    
    dispatched_at = Column(DateTime, nullable=True)
    dispatch_courier = Column(String(100), nullable=True)
    dispatch_tracking_number = Column(String(100), nullable=True)
    dispatch_notes = Column(Text, nullable=True)
    dispatch_photos = Column(JSONB, nullable=True)
    
    vendor_acknowledged_at = Column(DateTime, nullable=True)
    vendor_remarks = Column(Text, nullable=True)
    
    expected_resolution_date = Column(Date, nullable=True)
    
    replacement_dispatched_at = Column(DateTime, nullable=True)
    replacement_courier = Column(String(100), nullable=True)
    replacement_tracking_number = Column(String(100), nullable=True)
    
    replacement_received_at = Column(DateTime, nullable=True)
    replacement_qc_status = Column(String(20), nullable=True)
    replacement_qc_notes = Column(Text, nullable=True)
    
    linked_receipt_ids = Column(JSONB, nullable=True)
    
    email_log = Column(JSONB, nullable=True)
    whatsapp_log = Column(JSONB, nullable=True)
    
    closed_at = Column(DateTime, nullable=True)
    closure_notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, nullable=True)
    updated_by_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    service_center = relationship('OfficialPartner', foreign_keys=[service_center_id], backref='dispatches_from')
    vendor = relationship('OfficialPartner', foreign_keys=[vendor_id], backref='dispatches_to')
    
    __table_args__ = (
        CheckConstraint(
            "dispatch_type IN ('WARRANTY_CLAIM', 'REPLACEMENT_REQUEST', 'REPAIR_REQUEST', 'RETURN')",
            name='dispatch_type_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'DISPATCHED', 'VENDOR_ACKNOWLEDGED', 'IN_PROCESS', 'REPLACEMENT_DISPATCHED', 'REPLACEMENT_RECEIVED', 'QC_PENDING', 'QC_COMPLETE', 'CLOSED', 'CANCELLED')",
            name='dispatch_status_check'
        ),
        Index('idx_dispatch_company', 'company_id'),
        Index('idx_dispatch_service_center', 'service_center_id'),
        Index('idx_dispatch_vendor', 'vendor_id'),
        Index('idx_dispatch_status', 'status'),
    )
    
    def __repr__(self):
        return f'<ServiceCenterDispatch {self.dispatch_number}: {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'dispatch_number': self.dispatch_number,
            'company_id': self.company_id,
            'service_center_id': self.service_center_id,
            'service_center_name': self.service_center.partner_name if self.service_center else None,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.partner_name if self.vendor else None,
            'dispatch_type': self.dispatch_type,
            'total_items': self.total_items,
            'status': self.status,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
            'dispatch_courier': self.dispatch_courier,
            'dispatch_tracking_number': self.dispatch_tracking_number,
            'dispatch_notes': self.dispatch_notes,
            'vendor_acknowledged_at': self.vendor_acknowledged_at.isoformat() if self.vendor_acknowledged_at else None,
            'vendor_remarks': self.vendor_remarks,
            'expected_resolution_date': self.expected_resolution_date.isoformat() if self.expected_resolution_date else None,
            'replacement_dispatched_at': self.replacement_dispatched_at.isoformat() if self.replacement_dispatched_at else None,
            'replacement_received_at': self.replacement_received_at.isoformat() if self.replacement_received_at else None,
            'replacement_qc_status': self.replacement_qc_status,
            'linked_receipt_ids': self.linked_receipt_ids,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'closure_notes': self.closure_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ServiceCenterGivenOut(BaseModel):
    """
    DC_SERVICE_003: Items Given Out to Customers/Partners
    Tracks items dispatched outward (loan, demo, exchange, trial).
    Stock deducted on creation; restored on return/exchange; stays deducted on billing/write-off.
    """
    __tablename__ = 'service_center_given_out'

    id = Column(Integer, primary_key=True, index=True)
    given_out_number = Column(String(30), unique=True, nullable=False, index=True)

    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    service_center_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    service_ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=True, index=True)

    recipient_type = Column(String(20), nullable=False, default='CUSTOMER')
    recipient_name = Column(String(200), nullable=False)
    recipient_contact = Column(String(20), nullable=True)
    recipient_email = Column(String(200), nullable=True)
    recipient_partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True, index=True)

    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True, index=True)
    item_name = Column(String(200), nullable=False)
    item_code = Column(String(30), nullable=True)
    serial_number = Column(String(100), nullable=True, index=True)
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    unit_rate = Column(Numeric(15, 2), nullable=True, default=0)

    purpose = Column(String(20), nullable=False, default='LOAN')
    notes = Column(Text, nullable=True)

    given_at = Column(DateTime, default=get_indian_time, nullable=False)
    expected_return_date = Column(Date, nullable=True)

    status = Column(String(20), nullable=False, default='GIVEN_OUT')

    returned_at = Column(DateTime, nullable=True)
    return_notes = Column(Text, nullable=True)
    return_item_condition = Column(String(30), nullable=True)
    exchange_return_type = Column(String(20), nullable=True)

    sales_invoice_id = Column(Integer, ForeignKey('sales_invoices.id'), nullable=True, index=True)
    invoice_reference = Column(String(100), nullable=True)

    reminder_sent_at = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, nullable=False, default=0)

    created_by_id = Column(Integer, nullable=True)
    updated_by_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    service_center = relationship('OfficialPartner', foreign_keys=[service_center_id])
    recipient_partner = relationship('OfficialPartner', foreign_keys=[recipient_partner_id])
    sales_invoice = relationship('SalesInvoice', foreign_keys=[sales_invoice_id])

    __table_args__ = (
        CheckConstraint(
            "recipient_type IN ('CUSTOMER', 'PARTNER')",
            name='given_out_recipient_type_check'
        ),
        CheckConstraint(
            "purpose IN ('LOAN', 'DEMO', 'EXCHANGE', 'TRIAL')",
            name='given_out_purpose_check'
        ),
        CheckConstraint(
            "status IN ('GIVEN_OUT', 'RETURNED', 'BILLED', 'EXCHANGED', 'WRITTEN_OFF')",
            name='given_out_status_check'
        ),
        CheckConstraint(
            "exchange_return_type IN ('NORMAL_STOCK', 'DEFECTIVE') OR exchange_return_type IS NULL",
            name='given_out_exchange_return_type_check'
        ),
        Index('idx_given_out_company', 'company_id'),
        Index('idx_given_out_center', 'service_center_id'),
        Index('idx_given_out_status', 'status'),
        Index('idx_given_out_ticket', 'service_ticket_id'),
    )

    def __repr__(self):
        return f'<ServiceCenterGivenOut {self.given_out_number}: {self.status}>'

    def to_dict(self):
        from datetime import date as date_type
        today = date_type.today()
        overdue = False
        if self.status == 'GIVEN_OUT' and self.expected_return_date and self.expected_return_date < today:
            overdue = True
        return {
            'id': self.id,
            'given_out_number': self.given_out_number,
            'company_id': self.company_id,
            'service_center_id': self.service_center_id,
            'service_center_name': self.service_center.partner_name if self.service_center else None,
            'service_ticket_id': self.service_ticket_id,
            'recipient_type': self.recipient_type,
            'recipient_name': self.recipient_name,
            'recipient_contact': self.recipient_contact,
            'recipient_email': self.recipient_email,
            'recipient_partner_id': self.recipient_partner_id,
            'recipient_partner_name': self.recipient_partner.partner_name if self.recipient_partner else None,
            'item_id': self.item_id,
            'item_name': self.item_name,
            'item_code': self.item_code,
            'serial_number': self.serial_number,
            'quantity': float(self.quantity) if self.quantity else 1,
            'unit_rate': float(self.unit_rate) if self.unit_rate else 0,
            'purpose': self.purpose,
            'notes': self.notes,
            'given_at': self.given_at.isoformat() if self.given_at else None,
            'expected_return_date': self.expected_return_date.isoformat() if self.expected_return_date else None,
            'status': self.status,
            'overdue': overdue,
            'days_overdue': (today - self.expected_return_date).days if overdue else 0,
            'returned_at': self.returned_at.isoformat() if self.returned_at else None,
            'return_notes': self.return_notes,
            'return_item_condition': self.return_item_condition,
            'exchange_return_type': self.exchange_return_type,
            'sales_invoice_id': self.sales_invoice_id,
            'invoice_reference': self.invoice_reference,
            'invoice_number': self.sales_invoice.invoice_number if self.sales_invoice else None,
            'reminder_sent_at': self.reminder_sent_at.isoformat() if self.reminder_sent_at else None,
            'reminder_count': self.reminder_count,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VGKTeamCommissionConfig(BaseModel):
    """
    VGK Team Commission Configuration (DC Protocol Mar 2026 / Jun 2026)
    Per-category commission rates for 5-level VGK referral network.
    L1=self, L2=upline of L1, L3=upline of L2, L4 CORE=upline of L3, L5=field support per lead.
    level4_* columns store L5 SUPPORT rates (kept for DB compat).
    level4_core_* columns store L4 CORE rates (default 50% of L3).
    """
    __tablename__ = 'vgk_team_commission_config'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=False, index=True)

    level1_pct = Column(Numeric(5, 2), nullable=False, default=5.0)
    level1_type = Column(String(6), nullable=False, default='PCT')   # 'PCT' or 'AMOUNT'
    level1_amt = Column(Numeric(12, 2), nullable=False, default=0)   # flat ₹ per deal

    level2_pct = Column(Numeric(5, 2), nullable=False, default=3.0)
    level2_type = Column(String(6), nullable=False, default='PCT')
    level2_amt = Column(Numeric(12, 2), nullable=False, default=0)

    level3_pct = Column(Numeric(5, 2), nullable=False, default=1.0)
    level3_type = Column(String(6), nullable=False, default='PCT')
    level3_amt = Column(Numeric(12, 2), nullable=False, default=0)

    level4_pct = Column(Numeric(5, 2), nullable=False, default=0)
    level4_type = Column(String(6), nullable=False, default='PCT')
    level4_amt = Column(Numeric(12, 2), nullable=False, default=0)

    # DC-VGK-L4CORE-001 (Jun 2026): L4 CORE = upliner of L3. Default 50% of L3 rate.
    level4_core_pct  = Column(Numeric(5, 2),  nullable=False, default=0)
    level4_core_type = Column(String(6),       nullable=False, default='PCT')
    level4_core_amt  = Column(Numeric(12, 2),  nullable=False, default=0)

    monthly_target = Column(Numeric(15, 2), nullable=False, default=0)
    bonus_pct = Column(Numeric(5, 2), nullable=False, default=0)

    markup_pct = Column(Numeric(5, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    # DC Protocol Mar 2026: Paid/Non-Paid split — one config row per category per paid status.
    # is_paid_member=True → rates for members who paid ₹4,999 activation (full L1-L4 cascade).
    # is_paid_member=False → rates for non-paid members (L1 only).
    is_paid_member = Column(Boolean, nullable=False, default=True)

    # DC-SHOWROOM-COMMISSION-001 (May 2026): Configurable showroom commission (L6).
    # If showroom_vgk_id is set on a lead AND showroom_pct/amt > 0, the showroom partner earns this.
    showroom_pct  = Column(Numeric(5, 2),  nullable=False, default=0)
    showroom_type = Column(String(6),       nullable=False, default='PCT')   # 'PCT' | 'AMOUNT'
    showroom_amt  = Column(Numeric(12, 2),  nullable=False, default=0)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        UniqueConstraint('company_id', 'category_id', 'is_paid_member', name='uq_vgk_config_company_category_paid'),
        Index('idx_vgk_config_company', 'company_id'),
    )

    def __repr__(self):
        return f'<VGKTeamCommissionConfig company={self.company_id} cat={self.category_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'category_id': self.category_id,
            'level1_pct': float(self.level1_pct or 0),
            'level1_type': self.level1_type or 'PCT',
            'level1_amt': float(self.level1_amt or 0),
            'level2_pct': float(self.level2_pct or 0),
            'level2_type': self.level2_type or 'PCT',
            'level2_amt': float(self.level2_amt or 0),
            'level3_pct': float(self.level3_pct or 0),
            'level3_type': self.level3_type or 'PCT',
            'level3_amt': float(self.level3_amt or 0),
            'level4_pct': float(self.level4_pct or 0),
            'level4_type': self.level4_type or 'PCT',
            'level4_amt': float(self.level4_amt or 0),
            'level4_core_pct':  float(self.level4_core_pct  or 0),
            'level4_core_type': self.level4_core_type or 'PCT',
            'level4_core_amt':  float(self.level4_core_amt  or 0),
            'monthly_target': float(self.monthly_target or 0),
            'bonus_pct': float(self.bonus_pct or 0),
            'markup_pct': float(self.markup_pct or 0),
            'is_active': self.is_active,
            'is_paid_member': bool(self.is_paid_member),
            'showroom_pct':       float(self.showroom_pct or 0),
            'showroom_type':      self.showroom_type or 'PCT',
            'showroom_amt':       float(self.showroom_amt or 0),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VGKTeamIncomeEntry(BaseModel):
    """
    VGK Team Income / Commission Ledger (DC Protocol Mar 2026)
    WVV Protocol: PENDING -> CONFIRMED (EA confirms) -> points credited to member balance.
    Separate ledger from MNR income_entries.
    Level 0 = activation bonus (50000 points on joining).
    L1=self, L2=upline of L1, L3=upline of L2, L4=field support per lead.
    """
    __tablename__ = 'vgk_team_income_entries'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    entry_number = Column(String(30), nullable=False, index=True)

    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    source_lead_id = Column(Integer, nullable=True)
    source_transaction_id = Column(Integer, nullable=True)
    category_id = Column(Integer, ForeignKey('signup_categories.id', ondelete='SET NULL'), nullable=True)

    level = Column(SmallInteger, nullable=False)

    revenue_amount = Column(Numeric(15, 2), nullable=False, default=0)
    commission_pct = Column(Numeric(5, 2), nullable=False, default=0)
    commission_amount = Column(Numeric(15, 2), nullable=False, default=0)
    bonus_amount = Column(Numeric(15, 2), nullable=False, default=0)

    status = Column(String(20), nullable=False, default='PENDING')
    notes = Column(Text, nullable=True)

    required_points_debit = Column(Numeric(15, 2), nullable=False, default=0)

    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, nullable=True)

    support_confirmed = Column(Boolean, nullable=True)
    support_confirmed_at = Column(DateTime, nullable=True)
    support_confirmed_by_id = Column(Integer, nullable=True)
    support_confirmed_by_type = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        UniqueConstraint('company_id', 'entry_number', name='uq_vgk_income_entry_number'),
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'HOLD')",
            name='vgk_income_status_check'
        ),
        CheckConstraint('level BETWEEN 0 AND 4', name='vgk_income_level_check'),
        Index('idx_vgk_income_partner_status', 'company_id', 'partner_id', 'status'),
        Index('idx_vgk_income_lead', 'company_id', 'source_lead_id'),
    )

    def __repr__(self):
        return f'<VGKTeamIncomeEntry {self.entry_number}: partner={self.partner_id} L{self.level} {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entry_number': self.entry_number,
            'partner_id': self.partner_id,
            'source_lead_id': self.source_lead_id,
            'source_transaction_id': self.source_transaction_id,
            'category_id': self.category_id,
            'level': self.level,
            'revenue_amount': float(self.revenue_amount or 0),
            'commission_pct': float(self.commission_pct or 0),
            'commission_amount': float(self.commission_amount or 0),
            'bonus_amount': float(self.bonus_amount or 0),
            'status': self.status,
            'required_points_debit': float(self.required_points_debit or 0),
            'notes': self.notes,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'confirmed_by': self.confirmed_by,
            'support_confirmed': self.support_confirmed,
            'support_confirmed_at': self.support_confirmed_at.isoformat() if self.support_confirmed_at else None,
            'support_confirmed_by_id': self.support_confirmed_by_id,
            'support_confirmed_by_type': self.support_confirmed_by_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VGKPointsLedger(BaseModel):
    """
    VGK Points Ledger (DC Protocol Mar 2026)
    Immutable append-only ledger for all partner point movements.
    Points are promotional discount credits — not financial instruments.
    Cannot be transferred between partners or redeemed for cash.

    reason_code values:
        WELCOME_BONUS         — 1,000 points on registration
        ACTIVATION_BONUS      — 50,000 points on account activation (standard 5K PIN)
        LOYAL_BONUS           — 25,000 points on Loyal Coupon activation (zero-cost, VGK Mentor only)
        BONANZA_REWARD        — points from bonanza achievement
        PRODUCT_DISCOUNT      — points used against a vendor product purchase
        COMMISSION_ADJUSTMENT — manual deduction linked to commission policy
        MANUAL_ADJUSTMENT     — staff-initiated credit or debit with justification
        MIGRATION_BALANCE     — one-time seed entry for pre-ledger balances
        AUTO_REFILL           — 50,000 points auto-credited when balance hits 0 within 180 days of last credit (max 2 times)
    """
    __tablename__ = 'vgk_points_ledger'

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    points_credit = Column(Numeric(15, 2), nullable=False, default=0)
    points_debit  = Column(Numeric(15, 2), nullable=False, default=0)
    balance_after = Column(Numeric(15, 2), nullable=False)

    reason_code    = Column(String(40), nullable=False)
    reference_type = Column(String(40), nullable=True)
    reference_id   = Column(Integer, nullable=True)
    notes          = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_by = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "reason_code IN ('WELCOME_BONUS','ACTIVATION_BONUS','LOYAL_BONUS','BONANZA_REWARD',"
            "'PRODUCT_DISCOUNT','COMMISSION_ADJUSTMENT','MANUAL_ADJUSTMENT','MIGRATION_BALANCE',"
            "'CAMPAIGN_BONUS','AUTO_REFILL','COMPANY_ROYALTY','INCOME_EARNED','BONANZA_CASH_CREDIT')",
            name='vgk_points_reason_check'
        ),
        Index('idx_vgk_pts_partner', 'partner_id'),
        Index('idx_vgk_pts_reason', 'reason_code'),
    )

    def __repr__(self):
        return (f'<VGKPointsLedger #{self.id}: partner={self.partner_id} '
                f'+{self.points_credit}/-{self.points_debit} [{self.reason_code}]>')

    def to_dict(self):
        return {
            'id': self.id,
            'partner_id': self.partner_id,
            'points_credit': float(self.points_credit or 0),
            'points_debit': float(self.points_debit or 0),
            'balance_after': float(self.balance_after or 0),
            'reason_code': self.reason_code,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }


class VGKCompanyPayout(Base):
    """
    [DC-COMPANY-PAYOUT-001] May 2026
    Records company-side gross payouts made by MR10001 or MR10025 to any VGK member.
    Breakdown: 8% admin charges + 2% TDS = 10% total deduction. Net = gross × 90%.
    Each payout creates a COMPANY_PAYOUT wallet transaction and debits partner points.
    """
    __tablename__ = 'vgk_company_payouts'

    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)

    gross_amount   = Column(Numeric(15, 2), nullable=False)
    admin_charges  = Column(Numeric(15, 2), nullable=False, default=Decimal('0'))
    tds_pct        = Column(Numeric(5, 2),  nullable=False, default=Decimal('2.00'))
    tds_amount     = Column(Numeric(15, 2), nullable=False)
    net_amount     = Column(Numeric(15, 2), nullable=False)

    notes        = Column(Text,        nullable=True)
    paid_by      = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    paid_by_code = Column(String(30),  nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_vgk_payout_partner', 'partner_id'),
    )

    def to_dict(self):
        gross = float(self.gross_amount or 0)
        admin = float(self.admin_charges or 0)
        tds   = float(self.tds_amount or 0)
        return {
            'id':             self.id,
            'company_id':     self.company_id,
            'partner_id':     self.partner_id,
            'gross_amount':   gross,
            'admin_charges':  admin,
            'admin_pct':      round(admin / gross * 100, 2) if gross else 8.0,
            'tds_pct':        float(self.tds_pct or 2),
            'tds_amount':     tds,
            'total_deduction': round(admin + tds, 2),
            'net_amount':     float(self.net_amount or 0),
            'notes':          self.notes,
            'paid_by_code':   self.paid_by_code,
            'created_at':     self.created_at.isoformat() if self.created_at else None,
        }


class VGKPINPurchaseRequest(Base):
    """
    VGK PIN Purchase Request (DC Protocol Mar 2026)
    Mirrors MNR PINPurchaseRequest for VGK member-initiated PIN purchases.
    Flow: Member submits request with payment proof -> Staff approves/rejects -> On approval, member is activated with 50K points.
    """
    __tablename__ = 'vgk_pin_purchase_requests'

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True)

    amount = Column(Numeric(12, 2), nullable=False, default=5000)
    payment_method = Column(String(50), nullable=True)
    transaction_ref = Column(String(100), nullable=True)
    payment_screenshot_url = Column(String(500), nullable=True)
    payment_notes = Column(Text, nullable=True)

    status = Column(String(20), nullable=False, default='PENDING')
    request_date = Column(DateTime, default=get_indian_time, nullable=False)

    approved_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    staff_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED')", name='vgk_pin_request_status_check'),
        Index('idx_vgk_pin_req_partner_status', 'partner_id', 'status'),
    )

    def __repr__(self):
        return f'<VGKPINPurchaseRequest #{self.id}: partner={self.partner_id} {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'partner_id': self.partner_id,
            'company_id': self.company_id,
            'amount': float(self.amount or 0),
            'payment_method': self.payment_method,
            'transaction_ref': self.transaction_ref,
            'payment_screenshot_url': self.payment_screenshot_url,
            'payment_notes': self.payment_notes,
            'status': self.status,
            'request_date': self.request_date.isoformat() if self.request_date else None,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'staff_notes': self.staff_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CashflowRegister(Base):
    """
    Daily Cash Flow Register — DC_CASHFLOW_001
    Multi-company daily in/out register: MNR | MyntReal (Sales/Spares/Service) | Zynova | Escrow
    Opening balance per entry; closing = opening + total_in - total_out.
    Data entry from 1st April 2026 onwards.
    """
    __tablename__ = 'cashflow_register'

    id = Column(Integer, primary_key=True, index=True)
    entry_date = Column(Date, nullable=False, unique=True, index=True)
    opening_balance = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)

    mnr_in           = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    mynt_sales_in    = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    mynt_spares_in   = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    mynt_service_in  = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    zynova_in        = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    escrow_in        = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)

    mnr_out          = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    mynt_sales_out   = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    mynt_spares_out  = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    mynt_service_out = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    zynova_out       = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    escrow_out       = Column(Numeric(14, 2), default=Decimal('0.00'), nullable=False)

    notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id])

    def total_in(self):
        return float(
            (self.mnr_in or 0) + (self.mynt_sales_in or 0) + (self.mynt_spares_in or 0) +
            (self.mynt_service_in or 0) + (self.zynova_in or 0) + (self.escrow_in or 0)
        )

    def total_out(self):
        return float(
            (self.mnr_out or 0) + (self.mynt_sales_out or 0) + (self.mynt_spares_out or 0) +
            (self.mynt_service_out or 0) + (self.zynova_out or 0) + (self.escrow_out or 0)
        )

    def for_the_day(self):
        return self.total_in() - self.total_out()

    def closing_balance(self):
        return float(self.opening_balance or 0) + self.for_the_day()

    def to_dict(self):
        tin  = self.total_in()
        tout = self.total_out()
        ftd  = tin - tout
        ob   = float(self.opening_balance or 0)
        return {
            'id':               self.id,
            'entry_date':       self.entry_date.isoformat() if self.entry_date else None,
            'opening_balance':  ob,
            'mnr_in':           float(self.mnr_in or 0),
            'mynt_sales_in':    float(self.mynt_sales_in or 0),
            'mynt_spares_in':   float(self.mynt_spares_in or 0),
            'mynt_service_in':  float(self.mynt_service_in or 0),
            'zynova_in':        float(self.zynova_in or 0),
            'escrow_in':        float(self.escrow_in or 0),
            'total_in':         tin,
            'mnr_out':          float(self.mnr_out or 0),
            'mynt_sales_out':   float(self.mynt_sales_out or 0),
            'mynt_spares_out':  float(self.mynt_spares_out or 0),
            'mynt_service_out': float(self.mynt_service_out or 0),
            'zynova_out':       float(self.zynova_out or 0),
            'escrow_out':       float(self.escrow_out or 0),
            'total_out':        tout,
            'for_the_day':      ftd,
            'closing_balance':  ob + ftd,
            'notes':            self.notes,
            'created_by':       self.created_by.full_name if self.created_by else None,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
            'updated_at':       self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<CashflowRegister {self.entry_date} ob={self.opening_balance}>'


# ═══════════════════════════════════════════════════════════════════════════════
# VGK PROMO CODES SYSTEM  (DC Protocol Apr 2026)
# ═══════════════════════════════════════════════════════════════════════════════

class VGKPromoCode(Base):
    """
    Staff-managed VGK promo codes that award points to VGK members.
    promo_type:
        GENERAL     — standard campaign code, points awarded on claim
        MNR_MEMBER  — member supplies MNR User ID; 15k pts (activated) / 5k pts (non-activated)
        ETC_STUDENT — member supplies ETC Student ID; points derived from package_value tier_config
    status: 'ACTIVE' | 'PAUSED' | 'INACTIVE'
    tier_config (ETC_STUDENT only): list of {min_val, max_val, points} dicts sorted by min_val.
    """
    __tablename__ = 'vgk_promo_codes'
    __table_args__ = (
        Index('ix_vpc_status', 'status'),
        Index('ix_vpc_company', 'company_id'),
        Index('ix_vpc_type', 'promo_type'),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    code          = Column(String(50), unique=True, nullable=False)
    label         = Column(String(200), nullable=True)
    promo_type    = Column(String(20), nullable=False, default='GENERAL')
    points_credit = Column(Numeric(12, 2), nullable=False, default=0)
    tier_config   = Column(JSONB, nullable=True)
    status        = Column(String(20), nullable=False, default='ACTIVE')
    valid_from    = Column(DateTime, nullable=True)
    valid_to      = Column(DateTime, nullable=True)
    usage_limit             = Column(Integer, nullable=True)
    times_used              = Column(Integer, nullable=False, default=0)
    applicability_timing    = Column(String(20), nullable=False, default='BOTH')
    applicability_status    = Column(String(20), nullable=False, default='ALL')
    company_id    = Column(Integer, nullable=False, index=True)
    created_by    = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at    = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id':            self.id,
            'code':          self.code,
            'label':         self.label or '',
            'promo_type':    self.promo_type,
            'points_credit': float(self.points_credit or 0),
            'tier_config':   self.tier_config or [],
            'status':        self.status,
            'valid_from':    self.valid_from.isoformat() if self.valid_from else None,
            'valid_to':      self.valid_to.isoformat() if self.valid_to else None,
            'usage_limit':              self.usage_limit,
            'times_used':               int(self.times_used or 0),
            'applicability_timing':     self.applicability_timing or 'BOTH',
            'applicability_status':     self.applicability_status or 'ALL',
            'company_id':    self.company_id,
            'created_by':    self.created_by,
            'created_at':    self.created_at.isoformat() if self.created_at else None,
            'updated_at':    self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<VGKPromoCode #{self.id}: {self.code} [{self.promo_type}] {self.status}>'


class VGKPromoRedemption(Base):
    """
    Tracks each member's promo code redemption.
    One row per (promo_code_id, partner_id) — enforced by unique constraint.
    verified_ref: the MNR User ID or ETC Student ID supplied by the member.
    """
    __tablename__ = 'vgk_promo_redemptions'
    __table_args__ = (
        UniqueConstraint('promo_code_id', 'partner_id', name='uq_vpr_code_partner'),
        Index('ix_vpr_partner', 'partner_id'),
        Index('ix_vpr_code', 'promo_code_id'),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    promo_code_id = Column(Integer, ForeignKey('vgk_promo_codes.id', ondelete='CASCADE'), nullable=False)
    partner_id    = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False)
    verified_ref  = Column(String(50), nullable=True)
    points_awarded = Column(Numeric(12, 2), nullable=False, default=0)
    redeemed_at   = Column(DateTime, default=get_indian_time, nullable=False)
    notes         = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id':             self.id,
            'promo_code_id':  self.promo_code_id,
            'partner_id':     self.partner_id,
            'verified_ref':   self.verified_ref,
            'points_awarded': float(self.points_awarded or 0),
            'redeemed_at':    self.redeemed_at.isoformat() if self.redeemed_at else None,
            'notes':          self.notes,
        }

    def __repr__(self):
        return f'<VGKPromoRedemption #{self.id}: code={self.promo_code_id} partner={self.partner_id}>'


class VGKUplineChangeLog(BaseModel):
    """Audit log for every upline (parent_partner_id) change on a VGK member."""
    __tablename__ = 'vgk_upline_change_log'

    id               = Column(Integer, primary_key=True, index=True)
    member_id        = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    old_upline_id    = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True)
    new_upline_id    = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True)
    changed_by_id    = Column(Integer, ForeignKey('staff_employees.id',   ondelete='SET NULL'), nullable=True)
    reason           = Column(Text,    nullable=False)
    pending_entries_affected = Column(Integer, nullable=False, default=0)
    entries_reassigned       = Column(Boolean, nullable=False, default=False)
    created_at       = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_vgk_upline_log_member', 'member_id'),
        Index('idx_vgk_upline_log_created', 'created_at'),
    )

    def to_dict(self):
        return {
            'id':                       self.id,
            'member_id':                self.member_id,
            'old_upline_id':            self.old_upline_id,
            'new_upline_id':            self.new_upline_id,
            'changed_by_id':            self.changed_by_id,
            'reason':                   self.reason,
            'pending_entries_affected': self.pending_entries_affected,
            'entries_reassigned':       self.entries_reassigned,
            'created_at':               self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<VGKUplineChangeLog #{self.id}: member={self.member_id} {self.old_upline_id}->{self.new_upline_id}>'


# ============================================================================
# VGK MEDIA — Media Items + Reactions (Apr 2026)
# ============================================================================

class VGKMediaItem(Base):
    """
    Stores media content published by staff for the public hub Media section.
    Types: youtube (video link), publication (news links + optional PDF), blog (rich text).
    DC Protocol: soft-delete only, no hard deletes.
    """
    __tablename__ = 'vgk_media_items'

    id              = Column(Integer, primary_key=True, index=True)
    company_id      = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, default=4)
    media_type      = Column(String(20), nullable=False)          # youtube | publication | blog | image
    vgk_category    = Column(String(20), nullable=True)           # [DC-VGK-MEDIA-002] promotional | training | NULL (public hub)
    title           = Column(String(500), nullable=False)
    description     = Column(Text, nullable=True)
    body            = Column(Text, nullable=True)                 # Blog HTML body / rich text
    url             = Column(String(2000), nullable=True)         # YouTube URL
    thumbnail_url   = Column(String(2000), nullable=True)
    links           = Column(JSONB, nullable=True)                # Publication: [{label,url}]
    pdf_path        = Column(String(2000), nullable=True)
    pdf_name        = Column(String(500), nullable=True)
    status          = Column(String(20), nullable=False, default='active')  # active|paused|inactive|deleted
    display_order   = Column(Integer, nullable=False, default=0)
    click_count     = Column(Integer, nullable=False, default=0)
    share_count     = Column(Integer, nullable=False, default=0)
    created_by_id   = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    published_at    = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at      = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=True)
    deleted_at      = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_vgk_media_company_type',   'company_id', 'media_type'),
        Index('idx_vgk_media_status',         'status'),
        Index('idx_vgk_media_display_order',  'display_order'),
    )

    def to_dict(self):
        return {
            'id':           self.id,
            'company_id':   self.company_id,
            'media_type':   self.media_type,
            'vgk_category': self.vgk_category,
            'title':        self.title,
            'description':  self.description,
            'body':         self.body,
            'url':          self.url,
            'thumbnail_url':self.thumbnail_url,
            'links':        self.links or [],
            'pdf_path':     self.pdf_path,
            'pdf_name':     self.pdf_name,
            'status':       self.status,
            'display_order':self.display_order,
            'click_count':  self.click_count,
            'share_count':  self.share_count,
            'created_by_id':self.created_by_id,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
            'updated_at':   self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<VGKMediaItem #{self.id}: {self.media_type} — {self.title[:40]}>'


class VGKMediaReaction(Base):
    """
    Tracks public reactions (like/love/shoutout) on media items.
    reactor_key: browser fingerprint UUID or hashed IP (for unauthenticated visitors).
    DC Protocol: no hard deletes — toggle removes via delete of specific row.
    """
    __tablename__ = 'vgk_media_reactions'

    id              = Column(Integer, primary_key=True, index=True)
    media_id        = Column(Integer, ForeignKey('vgk_media_items.id', ondelete='CASCADE'), nullable=False, index=True)
    reaction_type   = Column(String(20), nullable=False)   # like | love | shoutout
    reactor_type    = Column(String(20), nullable=False, default='visitor')  # visitor | partner | staff
    reactor_key     = Column(String(256), nullable=False)  # fingerprint UUID / partner_code
    created_at      = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        UniqueConstraint('media_id', 'reaction_type', 'reactor_key', name='uq_vgk_media_reaction'),
        Index('idx_vgk_reaction_media', 'media_id'),
    )

    def __repr__(self):
        return f'<VGKMediaReaction: media={self.media_id} {self.reaction_type} by {self.reactor_key[:8]}>'


class ManualPartyMaster(Base):
    """DC-BANK-002c (May 2026): Persisted external / manual parties.
    When staff selects 'Use X as external party' in journal voucher autocomplete,
    the party is saved here so it appears in future party-search results.
    Idempotent by name (case-insensitive). No hard deletes.
    """
    __tablename__ = 'manual_party_master'

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(255), nullable=False, index=True)
    phone          = Column(String(20), nullable=True)
    email          = Column(String(150), nullable=True)
    notes          = Column(String(500), nullable=True)
    created_by_id  = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at     = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at     = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_manual_party_name', 'name'),
    )

    def __repr__(self):
        return f'<ManualPartyMaster: {self.name}>'


class EstimationOutRecord(Base):
    """DC-ESTIMATIONS-001: Planned/estimated outgoing amounts — purely informational, zero ledger impact."""
    __tablename__ = 'estimation_out_records'
    id               = Column(Integer, primary_key=True, index=True)
    company_id       = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    entry_date       = Column(Date, nullable=False)
    description      = Column(String(500), nullable=False)
    estimated_amount = Column(Numeric(15, 2), nullable=False, default=Decimal('0'))
    party_name       = Column(String(200), nullable=True)
    account_name     = Column(String(200), nullable=True)
    notes            = Column(Text, nullable=True)
    status           = Column(String(20), nullable=False, default='PENDING')
    created_by_id    = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at       = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at       = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'company_id': self.company_id,
            'entry_date': str(self.entry_date) if self.entry_date else None,
            'description': self.description,
            'estimated_amount': float(self.estimated_amount or 0),
            'party_name': self.party_name, 'account_name': self.account_name,
            'notes': self.notes, 'status': self.status,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EstimationPayment(Base):
    """DC-ESTIMATIONS-001: Payments recorded against ESTIMATED income entries. No ledger impact."""
    __tablename__ = 'estimation_payments'
    id               = Column(Integer, primary_key=True, index=True)
    income_entry_id  = Column(Integer, ForeignKey('income_entries.id', ondelete='CASCADE'), nullable=False, index=True)
    payment_date     = Column(Date, nullable=False)
    amount           = Column(Numeric(15, 2), nullable=False)
    payment_mode     = Column(String(20), nullable=False, default='CASH')
    party_name       = Column(String(200), nullable=True)
    account_received = Column(String(200), nullable=True)
    notes            = Column(Text, nullable=True)
    created_by_id    = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at       = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'income_entry_id': self.income_entry_id,
            'payment_date': str(self.payment_date) if self.payment_date else None,
            'amount': float(self.amount or 0),
            'payment_mode': self.payment_mode, 'party_name': self.party_name,
            'account_received': self.account_received, 'notes': self.notes,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class InvoiceNarrationLog(BaseModel):
    """
    DC_NARR_001 (May 2026): Narration / remarks history log for Sales and Purchase invoices.
    invoice_type: 'SALES' | 'PURCHASE'
    invoice_id: id from sales_invoices or purchase_invoice_uploads respectively
    Each entry is immutable — append-only audit trail.
    """
    __tablename__ = 'invoice_narration_log'

    id = Column(Integer, primary_key=True, index=True)
    invoice_type = Column(String(10), nullable=False)   # 'SALES' or 'PURCHASE'
    invoice_id = Column(Integer, nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    narration = Column(Text, nullable=False)
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_by_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_narr_log_invoice', 'invoice_type', 'invoice_id'),
        Index('idx_narr_log_company', 'company_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_type': self.invoice_type,
            'invoice_id': self.invoice_id,
            'company_id': self.company_id,
            'narration': self.narration,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SparePurchaseOrder(BaseModel):
    """
    Spare Parts Procurement Draft Order Header
    DC-CONSOL-SPARE-001: Staff-side consolidated spare procurement workbench
    Status machine: DRAFT → WAITING_APPROVAL → APPROVED → (cancelled from DRAFT/WAITING)
    On APPROVED: creates procurement_request records per vendor (IDs stored in procurement_req_ids)
    """
    __tablename__ = 'spare_purchase_orders'

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='DRAFT')
    notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    submitted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    procurement_req_ids = Column(JSONB, default=list, nullable=False)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    lines = relationship('SparePurchaseOrderLine', back_populates='order', cascade='all, delete-orphan')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='joined')
    submitted_by = relationship('StaffEmployee', foreign_keys=[submitted_by_id], lazy='joined')
    approved_by = relationship('StaffEmployee', foreign_keys=[approved_by_id], lazy='joined')

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','WAITING_APPROVAL','APPROVED','CANCELLED')",
            name='spo_status_check'
        ),
        Index('idx_spo_company_status', 'company_id', 'status'),
    )

    def to_dict(self, include_lines=True):
        d = {
            'id': self.id,
            'order_number': self.order_number,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'status': self.status,
            'notes': self.notes,
            'created_by_name': self.created_by.full_name if self.created_by else None,
            'submitted_by_name': self.submitted_by.full_name if self.submitted_by else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_by_name': self.approved_by.full_name if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'procurement_req_ids': self.procurement_req_ids or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'line_count': len(self.lines) if self.lines else 0,
        }
        if include_lines:
            d['lines'] = [l.to_dict() for l in (self.lines or [])]
        return d


class SparePurchaseOrderLine(BaseModel):
    """
    Spare Purchase Order Line Item — one row per vendor+item combination
    DC-CONSOL-SPARE-001
    """
    __tablename__ = 'spare_purchase_order_lines'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('spare_purchase_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('vendor_master.id'), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    item_code = Column(String(30), nullable=True)
    item_name = Column(String(200), nullable=True)
    quantity = Column(Numeric(15, 4), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    last_purchase_rate = Column(Numeric(15, 2), nullable=True)
    demand_source = Column(String(100), nullable=True)
    demand_qty = Column(Numeric(15, 4), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    order = relationship('SparePurchaseOrder', back_populates='lines')
    vendor = relationship('VendorMaster', foreign_keys=[vendor_id], lazy='joined')
    item = relationship('StockItemMaster', foreign_keys=[item_id], lazy='joined')

    __table_args__ = (
        Index('idx_spol_order_vendor', 'order_id', 'vendor_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.vendor_name if self.vendor else 'Vendor TBD',
            'vendor_phone': self.vendor.phone if self.vendor else None,
            'vendor_code': self.vendor.vendor_code if self.vendor else None,
            'item_id': self.item_id,
            'item_code': self.item_code or (self.item.item_code if self.item else None),
            'item_name': self.item_name or (self.item.item_name if self.item else None),
            'quantity': float(self.quantity),
            'unit_of_measure': self.unit_of_measure,
            'last_purchase_rate': float(self.last_purchase_rate) if self.last_purchase_rate else None,
            'estimated_value': float(self.quantity * self.last_purchase_rate) if self.last_purchase_rate else None,
            'demand_source': self.demand_source,
            'demand_qty': float(self.demand_qty) if self.demand_qty else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PartnerSpareRequest(BaseModel):
    """
    Partner Spare Parts Request — raised by dealer/distributor from their portal
    DC-PARTNER-SPARE-001: Partners request spare items; staff sees these as demand
    Status: SUBMITTED → ACKNOWLEDGED → FULFILLED / CANCELLED
    """
    __tablename__ = 'partner_spare_requests'

    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(30), unique=True, nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='SUBMITTED')
    notes = Column(Text, nullable=True)
    acknowledged_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    fulfilled_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    fulfilled_at = Column(DateTime, nullable=True)
    spare_order_id = Column(Integer, ForeignKey('spare_purchase_orders.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    lines = relationship('PartnerSpareRequestLine', back_populates='request', cascade='all, delete-orphan')
    partner = relationship('OfficialPartner', foreign_keys=[partner_id], lazy='joined')
    company = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='joined')
    acknowledged_by = relationship('StaffEmployee', foreign_keys=[acknowledged_by_id], lazy='joined')

    __table_args__ = (
        CheckConstraint(
            "status IN ('SUBMITTED','ACKNOWLEDGED','FULFILLED','CANCELLED')",
            name='psr_status_check'
        ),
        Index('idx_psr_partner_status', 'partner_id', 'status'),
    )

    def to_dict(self, include_lines=True):
        d = {
            'id': self.id,
            'request_number': self.request_number,
            'partner_id': self.partner_id,
            'partner_name': self.partner.partner_name if self.partner else None,
            'partner_code': self.partner.partner_code if self.partner else None,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'status': self.status,
            'notes': self.notes,
            'acknowledged_by_name': self.acknowledged_by.full_name if self.acknowledged_by else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'fulfilled_at': self.fulfilled_at.isoformat() if self.fulfilled_at else None,
            'spare_order_id': self.spare_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'line_count': len(self.lines) if self.lines else 0,
        }
        if include_lines:
            d['lines'] = [l.to_dict() for l in (self.lines or [])]
        return d


class PartnerSpareRequestLine(BaseModel):
    """
    Partner Spare Request Line — one row per requested item
    DC-PARTNER-SPARE-001
    """
    __tablename__ = 'partner_spare_request_lines'

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey('partner_spare_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey('stock_item_master.id'), nullable=False, index=True)
    item_code = Column(String(30), nullable=True)
    item_name = Column(String(200), nullable=True)
    quantity = Column(Numeric(15, 4), nullable=False, default=1)
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    request = relationship('PartnerSpareRequest', back_populates='lines')
    item = relationship('StockItemMaster', foreign_keys=[item_id], lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'item_id': self.item_id,
            'item_code': self.item_code or (self.item.item_code if self.item else None),
            'item_name': self.item_name or (self.item.item_name if self.item else None),
            'hsn_code': self.item.hsn_code if self.item else None,
            'unit_of_measure': self.unit_of_measure,
            'quantity': float(self.quantity),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# DC_TRAINING_VIDEOS_001: Training Videos System
# ─────────────────────────────────────────────────────────────────────────────

class TrainingVideo(BaseModel):
    """Training video synced from Google Doc. order_num is the unique stable key."""
    __tablename__ = 'training_videos'

    id               = Column(Integer, primary_key=True, index=True)
    order_num        = Column(Integer, unique=True, nullable=False)
    title            = Column(String(200), nullable=False)
    youtube_url      = Column(String(500), nullable=False)
    youtube_video_id = Column(String(50),  nullable=False)
    is_short         = Column(Boolean, default=False, nullable=False)
    is_active        = Column(Boolean, default=True,  nullable=False)
    synced_at        = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, nullable=False, default=get_indian_time)
    updated_at       = Column(DateTime, nullable=False, default=get_indian_time, onupdate=get_indian_time)

    def to_dict(self):
        return {
            'id':               self.id,
            'order_num':        self.order_num,
            'title':            self.title,
            'youtube_url':      self.youtube_url,
            'youtube_video_id': self.youtube_video_id,
            'is_short':         self.is_short,
            'is_active':        self.is_active,
        }


class TrainingVideoProgress(BaseModel):
    """Per-employee per-video completion record. Immutable — resets via admin only."""
    __tablename__ = 'training_video_progress'

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    video_id     = Column(Integer, ForeignKey('training_videos.id', ondelete='CASCADE'),
                          nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)    # IST naive datetime
    created_at   = Column(DateTime, nullable=False, default=get_indian_time)

    __table_args__ = (
        UniqueConstraint('employee_id', 'video_id', name='uq_training_progress_emp_vid'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# DC-INV-DISPATCH-001: Inventory Dispatch & Warranty Ledger
# Tracks individual battery / vehicle / charger units IN/OUT with serial numbers,
# warranty, partner assignment, and full movement history.
# ─────────────────────────────────────────────────────────────────────────────

class InventoryBatteryDispatch(BaseModel):
    """
    DC-INV-DISPATCH-001-BAT: Battery Dispatch & Warranty Ledger
    One row per battery unit — tracks IN arrival, dispatch, warranty, assignment.
    """
    __tablename__ = 'inventory_battery_dispatch'

    id                = Column(Integer, primary_key=True, index=True)
    company_id        = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    entry_date        = Column(Date, nullable=True)
    vendor_invoice_no = Column(String(100), nullable=True)
    vendor_code       = Column(String(20), nullable=True, index=True)
    battery_spec      = Column(String(100), nullable=True, index=True)
    warranty_months   = Column(Integer, nullable=True)
    battery_serial_no = Column(String(150), nullable=True)
    status            = Column(String(30), nullable=True, index=True)
    dispatch_date     = Column(Date, nullable=True)
    dispatch_month    = Column(String(20), nullable=True)
    assigned_vehicle_no = Column(String(100), nullable=True)
    sales_invoice_no  = Column(String(100), nullable=True)
    owner_name        = Column(String(200), nullable=True)
    location          = Column(String(200), nullable=True)
    warranty_end_date = Column(Date, nullable=True)
    deliverable       = Column(String(200), nullable=True)
    comments          = Column(Text, nullable=True)
    is_deleted        = Column(Boolean, default=False, nullable=False)
    created_by_id     = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id     = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at        = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at        = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    company    = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='select')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='select')
    updated_by = relationship('StaffEmployee', foreign_keys=[updated_by_id], lazy='select')

    __table_args__ = (
        Index('idx_inv_bat_disp_date',    'dispatch_date'),
        Index('idx_inv_bat_company',       'company_id'),
        Index('idx_inv_bat_status',        'status'),
        Index('idx_inv_bat_vendor_code',   'vendor_code'),
        Index('idx_inv_bat_deleted',       'is_deleted'),
    )

    def to_dict(self):
        return {
            'id':                   self.id,
            'company_id':           self.company_id,
            'entry_date':           self.entry_date.isoformat() if self.entry_date else None,
            'vendor_invoice_no':    self.vendor_invoice_no,
            'vendor_code':          self.vendor_code,
            'battery_spec':         self.battery_spec,
            'warranty_months':      self.warranty_months,
            'battery_serial_no':    self.battery_serial_no,
            'status':               self.status,
            'dispatch_date':        self.dispatch_date.isoformat() if self.dispatch_date else None,
            'dispatch_month':       self.dispatch_month,
            'assigned_vehicle_no':  self.assigned_vehicle_no,
            'sales_invoice_no':     self.sales_invoice_no,
            'owner_name':           self.owner_name,
            'location':             self.location,
            'warranty_end_date':    self.warranty_end_date.isoformat() if self.warranty_end_date else None,
            'deliverable':          self.deliverable,
            'comments':             self.comments,
            'created_at':           self.created_at.isoformat() if self.created_at else None,
            'updated_at':           self.updated_at.isoformat() if self.updated_at else None,
        }


class InventoryVehicleDispatch(BaseModel):
    """
    DC-INV-DISPATCH-001-VEH: Vehicle Dispatch Ledger
    One row per vehicle unit — tracks chassis/motor, dispatch, customer, battery/charger linkage.
    """
    __tablename__ = 'inventory_vehicle_dispatch'

    id                = Column(Integer, primary_key=True, index=True)
    company_id        = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    vehicle_no        = Column(String(50), nullable=True, index=True)
    vendor_invoice_no = Column(String(100), nullable=True)
    vendor_code       = Column(String(20), nullable=True, index=True)
    vehicle_model     = Column(String(100), nullable=True, index=True)
    vehicle_color     = Column(String(50), nullable=True)
    chassis_no        = Column(String(100), nullable=True)
    motor_no          = Column(String(100), nullable=True)
    status            = Column(String(30), nullable=True, index=True)
    dispatch_date     = Column(Date, nullable=True)
    dispatch_month    = Column(String(20), nullable=True)
    sales_invoice_no  = Column(String(100), nullable=True)
    customer_name     = Column(String(200), nullable=True)
    contact_number    = Column(String(30), nullable=True)
    battery_spec      = Column(String(100), nullable=True)
    battery_serial_no = Column(String(150), nullable=True)
    charger_no        = Column(String(100), nullable=True)
    address           = Column(String(500), nullable=True)
    return_date       = Column(Date, nullable=True)
    comments          = Column(Text, nullable=True)
    is_deleted        = Column(Boolean, default=False, nullable=False)
    created_by_id     = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id     = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at        = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at        = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    company    = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='select')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='select')
    updated_by = relationship('StaffEmployee', foreign_keys=[updated_by_id], lazy='select')

    __table_args__ = (
        Index('idx_inv_veh_disp_date',  'dispatch_date'),
        Index('idx_inv_veh_company',     'company_id'),
        Index('idx_inv_veh_status',      'status'),
        Index('idx_inv_veh_model',       'vehicle_model'),
        Index('idx_inv_veh_deleted',     'is_deleted'),
    )

    def to_dict(self):
        return {
            'id':               self.id,
            'company_id':       self.company_id,
            'vehicle_no':       self.vehicle_no,
            'vendor_invoice_no':self.vendor_invoice_no,
            'vendor_code':      self.vendor_code,
            'vehicle_model':    self.vehicle_model,
            'vehicle_color':    self.vehicle_color,
            'chassis_no':       self.chassis_no,
            'motor_no':         self.motor_no,
            'status':           self.status,
            'dispatch_date':    self.dispatch_date.isoformat() if self.dispatch_date else None,
            'dispatch_month':   self.dispatch_month,
            'sales_invoice_no': self.sales_invoice_no,
            'customer_name':    self.customer_name,
            'contact_number':   self.contact_number,
            'battery_spec':     self.battery_spec,
            'battery_serial_no':self.battery_serial_no,
            'charger_no':       self.charger_no,
            'address':          self.address,
            'return_date':      self.return_date.isoformat() if self.return_date else None,
            'comments':         self.comments,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
            'updated_at':       self.updated_at.isoformat() if self.updated_at else None,
        }


class InventoryChargerDispatch(BaseModel):
    """
    DC-INV-DISPATCH-001-CHR: Charger Dispatch & Warranty Ledger
    One row per charger unit — tracks dispatch, warranty, vehicle assignment, owner.
    """
    __tablename__ = 'inventory_charger_dispatch'

    id                  = Column(Integer, primary_key=True, index=True)
    company_id          = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    entry_date          = Column(Date, nullable=True)
    vendor_invoice_no   = Column(String(100), nullable=True)
    vendor_code         = Column(String(20), nullable=True, index=True)
    charger_spec        = Column(String(100), nullable=True, index=True)
    warranty_months     = Column(Integer, nullable=True)
    charger_no          = Column(String(150), nullable=True)
    status              = Column(String(30), nullable=True, index=True)
    dispatch_date       = Column(Date, nullable=True)
    dispatch_month      = Column(String(20), nullable=True)
    assigned_vehicle_no = Column(String(100), nullable=True)
    sales_invoice_no    = Column(String(100), nullable=True)
    owner_name          = Column(String(200), nullable=True)
    location            = Column(String(200), nullable=True)
    warranty_end_date   = Column(Date, nullable=True)
    deliverable         = Column(String(200), nullable=True)
    comments            = Column(Text, nullable=True)
    is_deleted          = Column(Boolean, default=False, nullable=False)
    created_by_id       = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id       = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at          = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at          = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    company    = relationship('AssociatedCompany', foreign_keys=[company_id], lazy='select')
    created_by = relationship('StaffEmployee', foreign_keys=[created_by_id], lazy='select')
    updated_by = relationship('StaffEmployee', foreign_keys=[updated_by_id], lazy='select')

    __table_args__ = (
        Index('idx_inv_chr_disp_date',  'dispatch_date'),
        Index('idx_inv_chr_company',     'company_id'),
        Index('idx_inv_chr_status',      'status'),
        Index('idx_inv_chr_deleted',     'is_deleted'),
    )

    def to_dict(self):
        return {
            'id':                   self.id,
            'company_id':           self.company_id,
            'entry_date':           self.entry_date.isoformat() if self.entry_date else None,
            'vendor_invoice_no':    self.vendor_invoice_no,
            'vendor_code':          self.vendor_code,
            'charger_spec':         self.charger_spec,
            'warranty_months':      self.warranty_months,
            'charger_no':           self.charger_no,
            'status':               self.status,
            'dispatch_date':        self.dispatch_date.isoformat() if self.dispatch_date else None,
            'dispatch_month':       self.dispatch_month,
            'assigned_vehicle_no':  self.assigned_vehicle_no,
            'sales_invoice_no':     self.sales_invoice_no,
            'owner_name':           self.owner_name,
            'location':             self.location,
            'warranty_end_date':    self.warranty_end_date.isoformat() if self.warranty_end_date else None,
            'deliverable':          self.deliverable,
            'comments':             self.comments,
            'created_at':           self.created_at.isoformat() if self.created_at else None,
            'updated_at':           self.updated_at.isoformat() if self.updated_at else None,
        }


# ── DC-DISPATCH-EXTRA-001: Pending line config + extra items (Jun 2026) ────────

class SalesPendingLineConfig(BaseModel):
    """
    DC-DISPATCH-EXTRA-001: Per-line pending qty override for sales dispatch tracking.
    If a row exists for a (invoice_id, invoice_line_id) pair the pending tab uses
    this qty instead of the raw invoice line qty. No stock ledger impact.
    """
    __tablename__ = 'sales_pending_line_config'

    id             = Column(Integer, primary_key=True, index=True)
    company_id     = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    invoice_id     = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    invoice_line_id = Column(Integer, ForeignKey('sales_invoice_line_items.id', ondelete='CASCADE'), nullable=False, index=True)
    pending_qty    = Column(Numeric(15, 3), nullable=False)
    created_at     = Column(DateTime, default=get_indian_time, nullable=False)
    created_by_id  = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('invoice_id', 'invoice_line_id', name='uq_sal_pending_line_config'),
        Index('idx_splc_invoice', 'invoice_id'),
    )


class SalesPendingExtraItem(BaseModel):
    """
    DC-DISPATCH-EXTRA-001: Extra items for sales dispatch tracking not present on the invoice.
    E.g. batteries / chargers bundled with a vehicle sale.
    Tracking only — no stock ledger entries created from this table.
    """
    __tablename__ = 'sales_pending_extra_items'

    id              = Column(Integer, primary_key=True, index=True)
    company_id      = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    invoice_id      = Column(Integer, ForeignKey('sales_invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id         = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    item_description = Column(String(255), nullable=False)
    item_code       = Column(String(100), nullable=True)
    unit_of_measure = Column(String(30), nullable=False, default='PCS', server_default='PCS')
    pending_qty     = Column(Numeric(15, 3), nullable=False, default=0)
    dispatched_qty  = Column(Numeric(15, 3), nullable=False, default=0, server_default='0')
    dispatch_status = Column(String(30), nullable=False, default='NOT_DISPATCHED', server_default='NOT_DISPATCHED')
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=get_indian_time, nullable=False)
    created_by_id   = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)

    __table_args__ = (Index('idx_spei_invoice', 'invoice_id'),)


class PurchasePendingLineConfig(BaseModel):
    """
    DC-DISPATCH-EXTRA-001: Per-line pending qty override for purchase receipt tracking.
    Mirror of SalesPendingLineConfig for the purchase side.
    """
    __tablename__ = 'purchase_pending_line_config'

    id             = Column(Integer, primary_key=True, index=True)
    company_id     = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    invoice_id     = Column(Integer, ForeignKey('purchase_invoice_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    invoice_line_id = Column(Integer, ForeignKey('purchase_invoice_line_items.id', ondelete='CASCADE'), nullable=False, index=True)
    pending_qty    = Column(Numeric(15, 3), nullable=False)
    created_at     = Column(DateTime, default=get_indian_time, nullable=False)
    created_by_id  = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('invoice_id', 'invoice_line_id', name='uq_pur_pending_line_config'),
        Index('idx_pplc_invoice', 'invoice_id'),
    )


class PurchasePendingExtraItem(BaseModel):
    """
    DC-DISPATCH-EXTRA-001: Extra items for purchase receipt tracking not on the invoice.
    E.g. accessories / spare parts arriving with a purchase shipment.
    Tracking only — no stock ledger entries created from this table.
    """
    __tablename__ = 'purchase_pending_extra_items'

    id              = Column(Integer, primary_key=True, index=True)
    company_id      = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    invoice_id      = Column(Integer, ForeignKey('purchase_invoice_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id         = Column(Integer, ForeignKey('stock_item_master.id'), nullable=True)
    item_description = Column(String(255), nullable=False)
    item_code       = Column(String(100), nullable=True)
    unit_of_measure = Column(String(30), nullable=False, default='PCS', server_default='PCS')
    pending_qty     = Column(Numeric(15, 3), nullable=False, default=0)
    received_qty    = Column(Numeric(15, 3), nullable=False, default=0, server_default='0')
    receipt_status  = Column(String(30), nullable=False, default='NOT_RECEIVED', server_default='NOT_RECEIVED')
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=get_indian_time, nullable=False)
    created_by_id   = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)

    __table_args__ = (Index('idx_ppei_invoice', 'invoice_id'),)
