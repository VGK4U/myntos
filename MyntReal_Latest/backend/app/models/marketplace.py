"""
MNR E-Com Lite — Phase 1 + 2 + 3: Marketplace Spares + PO Management + Segment Models
DC Protocol: company_id enforced on all tables
Phase 1: Price Intelligence (non-transactional)
Phase 2: PO Management (transactional — orders, dispatch, procurement)
Phase 3: Segment Layer (multi-segment marketplace with per-segment discount rates)
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Text,
    DateTime, JSON, Index, UniqueConstraint, ForeignKey, text
)
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from app.core.database import Base
from app.models.base import get_indian_time


class MarketplaceSegment(Base):
    """
    Phase 3 Segment Layer — top-level grouping above categories.
    Each segment owns its own categories, products, discount rates, and optional Sheet URL.
    DC Protocol: company_id on all records.

    Segment 1 = 'EV Spares' (seeded at DB migration — backwards-compatible default).
    google_sheet_url: if set, sync runs for this segment using that URL.
    allow_mnr/partner/student: controls which ID types are shown in marketplace discount bar.
    mnr_pct/partner_pct/student_pct: configurable per-segment discount percentages.
    badge_labels: JSONB list of strings shown in marketplace header pills for this segment.
    """
    __tablename__ = 'marketplace_segments'
    __table_args__ = (
        UniqueConstraint('slug', 'company_id', name='uq_ms_slug_company'),
        Index('ix_mseg_company', 'company_id'),
        Index('ix_mseg_slug', 'slug'),
    )

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(100), nullable=False)
    slug             = Column(String(100), nullable=False)
    company_id       = Column(Integer, nullable=False, index=True)
    description      = Column(Text, nullable=True)
    google_sheet_url = Column(Text, nullable=True)
    mnr_pct          = Column(Numeric(5, 2), nullable=False, default=3.0)
    partner_pct      = Column(Numeric(5, 2), nullable=False, default=12.0)
    student_pct      = Column(Numeric(5, 2), nullable=False, default=10.0)
    vgk_pct          = Column(Numeric(5, 2), nullable=False, default=3.0)
    allow_mnr        = Column(Boolean, nullable=False, default=True)
    allow_partner    = Column(Boolean, nullable=False, default=True)
    allow_student    = Column(Boolean, nullable=False, default=True)
    allow_vgk        = Column(Boolean, nullable=False, default=True)
    badge_labels     = Column(JSONB, default=list, nullable=True)
    sort_order       = Column(Integer, nullable=False, default=0)
    is_active        = Column(Boolean, nullable=False, default=True)
    segment_type     = Column(String(30), nullable=False, default='ECOM')
    data_source      = Column(String(20), nullable=False, default='sheet')  # 'sheet' | 'stock'
    created_at       = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at       = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'company_id': self.company_id,
            'description': self.description,
            'google_sheet_url': self.google_sheet_url,
            'mnr_pct': float(self.mnr_pct) if self.mnr_pct is not None else 3.0,
            'partner_pct': float(self.partner_pct or 12.0),
            'student_pct': float(self.student_pct or 10.0),
            'vgk_pct': float(self.vgk_pct) if self.vgk_pct is not None else 3.0,
            'allow_mnr': bool(self.allow_mnr),
            'allow_partner': bool(self.allow_partner),
            'allow_student': bool(self.allow_student),
            'allow_vgk': bool(self.allow_vgk) if self.allow_vgk is not None else True,
            'badge_labels': self.badge_labels or [],
            'sort_order': self.sort_order or 0,
            'is_active': bool(self.is_active),
            'segment_type': self.segment_type or 'ECOM',
            'data_source': self.data_source or 'sheet',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketspareItem(Base):
    """
    Phase 1 marketplace spares catalogue.
    image_data JSONB supports both embedded sheet images (Phase 1)
    and future URL-based images (Phase 2) — NO schema change needed.

    IMAGE MIGRATION NOTE:
      Phase 1: image_data = []  (embedded images inaccessible via API key)
      Phase 2: image_data = [{"url": "...", "thumb": "..."}]
               — just add Image_URL column in sheet and re-sync
    """
    __tablename__ = 'marketplace_spares'
    __table_args__ = (
        Index('ix_ms_search', 'search_vector', postgresql_using='gin'),
        Index('ix_ms_category', 'category_name'),
        Index('ix_ms_company_active', 'company_id', 'is_active'),
        Index('ix_ms_sku', 'sku'),
        UniqueConstraint('sku', 'company_id', name='uq_marketplace_spares_sku_company'),
    )

    id             = Column(Integer, primary_key=True, autoincrement=True)
    sku            = Column(String(120), nullable=False)
    name           = Column(String(255), nullable=False)
    category_name  = Column(String(100), nullable=False, index=True)
    dealer_price   = Column(Numeric(12, 2), nullable=False, default=0)
    description    = Column(Text, nullable=True)
    brand          = Column(String(150), nullable=True)
    model_compat   = Column(String(200), nullable=True)
    specifications = Column(String(300), nullable=True)
    color          = Column(String(100), nullable=True)
    speciality     = Column(String(300), nullable=True)     # from sheet col 14 "Additional Info?" (display label only changed)
    gst_percent    = Column(Numeric(5, 2), nullable=True)   # per-product from sheet col 18; NULL = use category config
    stock_qty      = Column(Integer, nullable=False, default=0)  # legacy — kept for PO stock-check compatibility
    available_qty  = Column(Integer, nullable=False, default=0)  # from sheet col 23 "Available Quantity" — always synced
    company_name   = Column(String(200), nullable=True)          # from sheet col 4 "Available Company"
    image_url      = Column(String(500), nullable=True)          # from sheet col 9 "Images URL" — raw string
    image_data     = Column(JSONB, default=list, nullable=False)
    images_gallery = Column(JSONB, default=list, nullable=True)  # up to 5 uploaded images [{url,label,is_primary}]
    search_vector  = Column(TSVECTOR, nullable=True)
    is_active      = Column(Boolean, nullable=False, default=True)
    # Enhanced product management — March 2026
    min_stock_threshold     = Column(Integer, nullable=False, default=0)   # auto-raise ZYPR when available_qty < this
    revenue_contribution_pct = Column(Numeric(6, 2), nullable=False, default=0)  # % of total revenue this SKU contributes
    manually_overridden     = Column(Boolean, nullable=False, default=False)  # True = sync won't overwrite editable fields
    override_fields         = Column(JSONB, default=list, nullable=True)  # which specific fields are overridden
    # Procurement cost columns — from Google Sheet cols 27-31
    proc_cost      = Column(Numeric(12, 2), nullable=True)   # col 27 Proc. cost
    proc_transport = Column(Numeric(12, 2), nullable=True)   # col 28 Proc. Transport
    proc_ex_tax    = Column(Numeric(12, 2), nullable=True)   # col 29 proc. Ex. Tax
    proc_tax_pct   = Column(Numeric(5, 2), nullable=True)    # col 30 Proc. Tax%
    proc_with_tax  = Column(Numeric(12, 2), nullable=True)   # col 31 Proc. With Tax
    warranty_details = Column(Text, nullable=True)
    warranty_cost    = Column(Numeric(12, 2), nullable=True)
    # Phase 3: Segment Layer — Mar 2026
    segment_id     = Column(Integer, ForeignKey('marketplace_segments.id'), nullable=True, index=True)
    source         = Column(String(20), nullable=False, default='sheet')  # 'sheet' | 'direct' | 'stock'
    stock_item_id  = Column(Integer, ForeignKey('stock_item_master.id', ondelete='SET NULL'), nullable=True, index=True)
    company_id     = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    created_at     = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at     = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'category_name': self.category_name,
            'dealer_price': float(self.dealer_price or 0),
            'gst_percent': float(self.gst_percent) if self.gst_percent is not None else None,
            'stock_qty': int(self.stock_qty or 0),
            'available_qty': int(self.available_qty or 0),
            'company_name': self.company_name or '',
            'image_url': self.image_url or '',
            'images_gallery': self.images_gallery or [],
            'description': self.description,
            'brand': self.brand,
            'model_compat': self.model_compat,
            'specifications': self.specifications,
            'color': self.color,
            'speciality': self.speciality,
            'image_data': self.image_data or [],
            'is_active': self.is_active,
            'min_stock_threshold': int(self.min_stock_threshold or 0),
            'revenue_contribution_pct': float(self.revenue_contribution_pct or 0),
            'manually_overridden': bool(self.manually_overridden),
            'override_fields': self.override_fields or [],
            'proc_cost': float(self.proc_cost) if self.proc_cost is not None else None,
            'proc_transport': float(self.proc_transport) if self.proc_transport is not None else None,
            'proc_ex_tax': float(self.proc_ex_tax) if self.proc_ex_tax is not None else None,
            'proc_tax_pct': float(self.proc_tax_pct) if self.proc_tax_pct is not None else None,
            'proc_with_tax': float(self.proc_with_tax) if self.proc_with_tax is not None else None,
            'warranty_details': self.warranty_details or '',
            'warranty_cost': float(self.warranty_cost) if self.warranty_cost is not None else None,
            'segment_id': self.segment_id,
            'source': self.source or 'sheet',
            'stock_item_id': self.stock_item_id,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketplaceSyncLog(Base):
    """
    Audit log for every Google Sheet sync run.
    DC Protocol: company_id on all records.
    """
    __tablename__ = 'marketplace_spares_sync_log'
    __table_args__ = (
        Index('ix_msl_company', 'company_id'),
    )

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    sync_timestamp     = Column(DateTime, default=get_indian_time, nullable=False)
    total_records      = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)
    failed_records     = Column(Integer, default=0)
    error_summary      = Column(JSONB, default=dict)
    company_id         = Column(Integer, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'sync_timestamp': self.sync_timestamp.isoformat() if self.sync_timestamp else None,
            'total_records': self.total_records,
            'successful_records': self.successful_records,
            'failed_records': self.failed_records,
            'error_summary': self.error_summary or {},
            'company_id': self.company_id,
        }


class MarketplaceCategoryConfig(Base):
    """
    Per-category pricing configuration — ONLY source of markup, GST, margins.
    Sheet values for markup/tax are IGNORED at runtime (per Phase 1 spec).
    Staff manage these values on the config page.

    PRICE ENGINE:
      display_mrp   = dealer_price × (1 + markup_percent/100)
      dealer_price  = what customer pays (base)
      discount_pct  = markup_percent (shown as savings vs MRP)
      MNR discount  = 3% off dealer_price
      Dealer disc   = 12% off dealer_price
      GST           = applied on net price after discount
    """
    __tablename__ = 'marketplace_category_config'
    __table_args__ = (
        UniqueConstraint('category_name', 'company_id', name='uq_mcc_cat_company'),
        Index('ix_mcc_company', 'company_id'),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    category_name        = Column(String(100), nullable=False)
    hsn_code             = Column(String(20), nullable=True)
    gst_percent          = Column(Numeric(5, 2), nullable=False, default=18.0)
    markup_percent       = Column(Numeric(5, 2), nullable=False, default=15.0)
    margin_floor_percent = Column(Numeric(5, 2), nullable=False, default=20.0)
    updated_by           = Column(String(100), nullable=True)
    updated_at           = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    segment_id           = Column(Integer, ForeignKey('marketplace_segments.id'), nullable=True, index=True)
    company_id           = Column(Integer, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'category_name': self.category_name,
            'hsn_code': self.hsn_code,
            'gst_percent': float(self.gst_percent or 18),
            'markup_percent': float(self.markup_percent or 15),
            'margin_floor_percent': float(self.margin_floor_percent or 5),
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'segment_id': self.segment_id,
            'company_id': self.company_id,
        }


# ── Phase 2: PO Management Models ─────────────────────────────────────────────

class MarketplacePurchaseOrder(Base):
    """
    PO header — one record per order submitted from basket.
    DC Protocol: company_id on all records. WVV: atomic creation with items.
    PO number format: ZYPO-YYYYMM-NNNN
    """
    __tablename__ = 'marketplace_purchase_orders'
    __table_args__ = (
        Index('ix_mpo_company', 'company_id'),
        Index('ix_mpo_status', 'status'),
        Index('ix_mpo_created', 'created_at'),
    )

    id               = Column(Integer, primary_key=True, autoincrement=True)
    po_number        = Column(String(30), unique=True, nullable=False)
    po_count         = Column(Integer, nullable=False, default=1)
    customer_name    = Column(String(255), nullable=False)
    customer_phone   = Column(String(20), nullable=False)
    customer_email   = Column(String(255), nullable=True)
    mnr_id           = Column(String(30), nullable=True)
    partner_code     = Column(String(30), nullable=True)
    delivery_address = Column(Text, nullable=True)
    customer_type    = Column(String(20), nullable=False, default='public')
    discount_mode    = Column(String(20), nullable=True)
    discount_name    = Column(String(100), nullable=True)
    total_items      = Column(Integer, nullable=False, default=0)
    total_ordered_qty = Column(Integer, nullable=False, default=0)
    total_value      = Column(Numeric(14, 2), nullable=False, default=0)
    status           = Column(String(30), nullable=False, default='confirmed')
    notes            = Column(Text, nullable=True)
    # Cross-reference: ticket-originated POs (service_ticket / technical_ticket)
    source_type      = Column(String(30), nullable=True, default='public')   # 'public','service_ticket','technical_ticket'
    source_ticket_id = Column(Integer, nullable=True)  # FK to service_ticket.id enforced at DB level via migration
    # PO lifecycle tracking — March 2026
    # Statuses: confirmed → accepted → in_progress → under_procurement → received →
    #           payment_pending → payment_received → dispatched → hold → cancelled
    # (partial_dispatch, completed remain valid for backward compat)
    confirmed_by_staff_id = Column(Integer, nullable=True)   # staff_employees.id who confirmed/approved this PO
    confirmed_at          = Column(DateTime, nullable=True)
    payment_received_at   = Column(DateTime, nullable=True)
    completed_at          = Column(DateTime, nullable=True)
    # Store manager assignment — March 2026
    store_manager_id          = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    store_manager_assigned_at = Column(DateTime, nullable=True)
    # Invoice number — generated when staff issues Tax Invoice from terminal PO
    pi_number                 = Column(String(30), nullable=True, index=True)
    # Bill To / Ship To — March 2026
    bill_name        = Column(String(255), nullable=True)
    bill_phone       = Column(String(20), nullable=True)
    bill_address     = Column(Text, nullable=True)
    ship_name        = Column(String(255), nullable=True)
    ship_phone       = Column(String(20), nullable=True)
    ship_address     = Column(Text, nullable=True)
    ship_same_as_bill = Column(Boolean, nullable=True, default=False)
    # Discount coupon tracking — March 2026
    discount_coupon_id         = Column(String(120), nullable=True)              # coupon/ID entered by staff
    coupon_entered_by_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    coupon_entered_at          = Column(DateTime, nullable=True)
    company_id       = Column(Integer, nullable=False, index=True)
    created_at       = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at       = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'po_number': self.po_number,
            'po_count': self.po_count,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'mnr_id': self.mnr_id,
            'partner_code': self.partner_code,
            'delivery_address': self.delivery_address,
            'customer_type': self.customer_type,
            'discount_mode': self.discount_mode,
            'discount_name': self.discount_name,
            'discount_coupon_id': self.discount_coupon_id,
            'coupon_entered_by_staff_id': self.coupon_entered_by_staff_id,
            'coupon_entered_at': self.coupon_entered_at.isoformat() if self.coupon_entered_at else None,
            'total_items': self.total_items,
            'total_ordered_qty': self.total_ordered_qty,
            'total_value': float(self.total_value or 0),
            'status': self.status,
            'notes': self.notes,
            'source_type': self.source_type or 'public',
            'source_ticket_id': self.source_ticket_id,
            'confirmed_by_staff_id': self.confirmed_by_staff_id,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'payment_received_at': self.payment_received_at.isoformat() if self.payment_received_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'store_manager_id': self.store_manager_id,
            'store_manager_assigned_at': self.store_manager_assigned_at.isoformat() if self.store_manager_assigned_at else None,
            'pi_number': self.pi_number,
            'bill_name': self.bill_name,
            'bill_phone': self.bill_phone,
            'bill_address': self.bill_address,
            'ship_name': self.ship_name,
            'ship_phone': self.ship_phone,
            'ship_address': self.ship_address,
            'ship_same_as_bill': self.ship_same_as_bill,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketplacePOItem(Base):
    """
    PO line items — snapshot of basket item at time of order.
    DC Protocol: company_id. Immutable after creation (pricing snapshot).
    """
    __tablename__ = 'marketplace_po_items'
    __table_args__ = (
        Index('ix_mpoi_po', 'po_id'),
        Index('ix_mpoi_sku', 'sku'),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    po_id                = Column(Integer, ForeignKey('marketplace_purchase_orders.id', ondelete='CASCADE'), nullable=False)
    sku                  = Column(String(120), nullable=False)
    product_name         = Column(String(255), nullable=False)
    category_name        = Column(String(100), nullable=True)
    brand                = Column(String(150), nullable=True)
    specifications       = Column(String(300), nullable=True)
    speciality           = Column(String(300), nullable=True)   # additional info snapshot
    color                = Column(String(100), nullable=True)
    warranty_details     = Column(Text, nullable=True)          # warranty snapshot from catalog
    ordered_qty          = Column(Integer, nullable=False, default=1)
    dealer_price         = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount      = Column(Numeric(12, 2), nullable=False, default=0)
    net_price            = Column(Numeric(12, 2), nullable=False, default=0)
    gst_percent          = Column(Numeric(5, 2), nullable=False, default=18)
    gst_amount           = Column(Numeric(12, 2), nullable=False, default=0)
    unit_final_price     = Column(Numeric(12, 2), nullable=False, default=0)
    line_total           = Column(Numeric(14, 2), nullable=False, default=0)
    stock_available      = Column(Integer, nullable=False, default=0)
    procurement_required = Column(Boolean, nullable=False, default=False)
    company_id           = Column(Integer, nullable=False)
    created_at           = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'po_id': self.po_id,
            'sku': self.sku,
            'product_name': self.product_name,
            'category_name': self.category_name,
            'brand': self.brand,
            'specifications': self.specifications,
            'speciality': self.speciality,
            'color': self.color,
            'warranty_details': self.warranty_details,
            'ordered_qty': self.ordered_qty,
            'dealer_price': float(self.dealer_price or 0),
            'discount_amount': float(self.discount_amount or 0),
            'net_price': float(self.net_price or 0),
            'gst_percent': float(self.gst_percent or 18),
            'gst_amount': float(self.gst_amount or 0),
            'unit_final_price': float(self.unit_final_price or 0),
            'line_total': float(self.line_total or 0),
            'stock_available': self.stock_available,
            'procurement_required': self.procurement_required,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class MarketplacePODispatch(Base):
    """
    Staff dispatch log — each update by staff for a PO item (dispatched qty + revenue).
    WVV Protocol: sum of dispatched_qty per item must not exceed ordered_qty.
    """
    __tablename__ = 'marketplace_po_dispatch'
    __table_args__ = (
        Index('ix_mpod_po', 'po_id'),
        Index('ix_mpod_item', 'po_item_id'),
    )

    id                = Column(Integer, primary_key=True, autoincrement=True)
    po_id             = Column(Integer, ForeignKey('marketplace_purchase_orders.id', ondelete='CASCADE'), nullable=False)
    po_item_id        = Column(Integer, ForeignKey('marketplace_po_items.id', ondelete='CASCADE'), nullable=False)
    dispatched_qty    = Column(Integer, nullable=False, default=0)
    revenue_collected = Column(Numeric(14, 2), nullable=False, default=0)
    dispatch_notes    = Column(Text, nullable=True)
    dispatched_by     = Column(String(50), nullable=True)
    dispatched_at     = Column(DateTime, default=get_indian_time, nullable=False)
    # Delivery detail fields — March 2026
    courier_name      = Column(String(100), nullable=True)
    tracking_number   = Column(String(100), nullable=True)
    vehicle_number    = Column(String(50), nullable=True)
    driver_name       = Column(String(100), nullable=True)
    company_id        = Column(Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'po_id': self.po_id,
            'po_item_id': self.po_item_id,
            'dispatched_qty': self.dispatched_qty,
            'revenue_collected': float(self.revenue_collected or 0),
            'dispatch_notes': self.dispatch_notes,
            'dispatched_by': self.dispatched_by,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
            'courier_name': self.courier_name,
            'tracking_number': self.tracking_number,
            'vehicle_number': self.vehicle_number,
            'driver_name': self.driver_name,
            'company_id': self.company_id,
        }


class MarketplaceProcurementRequest(Base):
    """
    Procurement record created when ordered_qty > stock_qty at PO time.
    Status lifecycle: pending → confirmed → payment_received → procurement → ordered → received → completed | cancelled
    """
    __tablename__ = 'marketplace_procurement_requests'
    __table_args__ = (
        Index('ix_mpr_po', 'po_id'),
        Index('ix_mpr_status', 'status'),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    procurement_number   = Column(String(30), unique=True, nullable=False)
    po_id                = Column(Integer, ForeignKey('marketplace_purchase_orders.id', ondelete='CASCADE'), nullable=True)   # nullable: auto-sync proc has no PO
    po_item_id           = Column(Integer, ForeignKey('marketplace_po_items.id', ondelete='CASCADE'), nullable=True)           # nullable: auto-sync proc has no PO item
    sku                  = Column(String(120), nullable=False)
    product_name         = Column(String(255), nullable=False)
    ordered_qty          = Column(Integer, nullable=False, default=0)
    available_qty        = Column(Integer, nullable=False, default=0)
    shortfall_qty        = Column(Integer, nullable=False, default=0)
    received_qty         = Column(Integer, nullable=False, default=0)   # actual qty received — March 2026 for procurement KPI
    status               = Column(String(30), nullable=False, default='pending')
    triggered_by         = Column(String(30), nullable=True)   # 'manual', 'auto_sync', 'po_creation', 'service_ticket', 'technical_ticket'
    procurement_notes    = Column(Text, nullable=True)
    actioned_by          = Column(String(50), nullable=True)
    actioned_at          = Column(DateTime, nullable=True)
    # Store manager assignment — March 2026
    store_manager_id     = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    # Cross-reference: which ticket raised this procurement (service_ticket / technical_ticket source)
    source_type          = Column(String(30), nullable=True, default='manual')  # 'manual','auto_sync','po_creation','service_ticket','technical_ticket'
    source_ticket_id     = Column(Integer, nullable=True)  # FK to service_ticket.id enforced at DB level via migration
    company_id           = Column(Integer, nullable=False)
    created_at           = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at           = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'procurement_number': self.procurement_number,
            'po_id': self.po_id,
            'po_item_id': self.po_item_id,
            'sku': self.sku,
            'product_name': self.product_name,
            'ordered_qty': self.ordered_qty,
            'available_qty': self.available_qty,
            'shortfall_qty': self.shortfall_qty,
            'received_qty': int(self.received_qty or 0),
            'status': self.status,
            'triggered_by': self.triggered_by or 'manual',
            'source_type': self.source_type or 'manual',
            'source_ticket_id': self.source_ticket_id,
            'procurement_notes': self.procurement_notes,
            'actioned_by': self.actioned_by,
            'actioned_at': self.actioned_at.isoformat() if self.actioned_at else None,
            'store_manager_id': self.store_manager_id,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketplacePromoCode(Base):
    """
    Marketplace promo/discount codes — Codes & Segments admin (Mar 2026).
    Per-segment discount rates stored in segment_discounts JSONB {str(segment_id): pct}.
    DC Protocol: company_id on all records.
    status: 'active' | 'paused'
    """
    __tablename__ = 'marketplace_promo_codes'
    __table_args__ = (
        Index('ix_mpc_company', 'company_id'),
        Index('ix_mpc_status', 'status'),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    code                 = Column(String(50), unique=True, nullable=False)
    label                = Column(String(200), nullable=True)
    default_discount_pct = Column(Numeric(5, 2), nullable=False, default=0)
    segment_discounts    = Column(JSONB, default=dict, nullable=False)
    status               = Column(String(20), nullable=False, default='active')
    valid_from           = Column(DateTime, nullable=True)
    valid_to             = Column(DateTime, nullable=True)
    usage_limit          = Column(Integer, nullable=True)
    times_used           = Column(Integer, nullable=False, default=0)
    times_searched       = Column(Integer, nullable=False, default=0)
    created_by           = Column(String(50), nullable=True)
    company_id           = Column(Integer, nullable=False, index=True)
    created_at           = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at           = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'label': self.label or '',
            'default_discount_pct': float(self.default_discount_pct or 0),
            'segment_discounts': self.segment_discounts or {},
            'status': self.status,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'usage_limit': self.usage_limit,
            'times_used': int(self.times_used or 0),
            'times_searched': int(self.times_searched or 0),
            'created_by': self.created_by or '',
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketplaceCodeLookup(Base):
    """
    Logs every validation/search hit against discount IDs and promo codes.
    DC Protocol: company_id enforced. Used for analytics in Codes & Segments page.
    code_type: 'mnr' | 'partner' | 'student' | 'promo'
    """
    __tablename__ = 'marketplace_code_lookups'
    __table_args__ = (
        Index('ix_mcl_company_type', 'company_id', 'code_type'),
        Index('ix_mcl_code_value', 'code_value'),
        Index('ix_mcl_looked_up_at', 'looked_up_at'),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    code_type    = Column(String(20), nullable=False)
    code_value   = Column(String(100), nullable=False)
    was_valid    = Column(Boolean, nullable=False, default=False)
    segment_id   = Column(Integer, nullable=True)
    company_id   = Column(Integer, nullable=False, default=1)
    looked_up_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'code_type': self.code_type,
            'code_value': self.code_value,
            'was_valid': self.was_valid,
            'segment_id': self.segment_id,
            'company_id': self.company_id,
            'looked_up_at': self.looked_up_at.isoformat() if self.looked_up_at else None,
        }
