"""
VGK Vendor Master System — Models (DC Protocol Mar 2026)

Tables:
  vgk_vendor_categories          — master category list (Sweet Shop, Restaurant, etc.)
  vgk_vendors                    — vendor master record + QR token + marketplace flag
  vgk_vendor_kyc                 — KYC documents per vendor
  vgk_vendor_agreements          — T&C acceptance ledger (discount %, validity, sign timestamp)
  vgk_vendor_product_categories  — per-vendor product sub-categories with GST% + flat discount%
  vgk_vendor_logins              — vendor portal login credentials
  vgk_vendor_transactions        — member purchase submissions (invoice → approval → wallet credit)
  vgk_vendor_marketplace_products— marketplace products listed by opted-in vendors
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Text,
    ForeignKey, Index, UniqueConstraint, SmallInteger
)
from app.models.base import Base, BaseModel, get_indian_time


# ── 1. Vendor Category Master ─────────────────────────────────────────────────
class VGKVendorCategory(BaseModel):
    """
    Master list of vendor business categories.
    Staff-managed; used as marketplace segment filter tokens.
    """
    __tablename__ = 'vgk_vendor_categories'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)

    name = Column(String(100), nullable=False)          # "Sweet Shop"
    slug = Column(String(60), nullable=False)           # "sweet-shop"
    icon = Column(String(80), nullable=True)            # Font-Awesome class
    description = Column(Text, nullable=True)
    display_order = Column(SmallInteger, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        UniqueConstraint('company_id', 'slug', name='uq_vgk_vendor_cat_slug'),
        Index('idx_vgk_vendor_cat_company', 'company_id', 'is_active'),
    )


# ── 2. Vendor Master ──────────────────────────────────────────────────────────
class VGKVendor(BaseModel):
    """
    VGK Empanelled Vendor (sweet shop, restaurant, furniture store, etc.)
    Each vendor gets a unique QR token on creation.
    """
    __tablename__ = 'vgk_vendors'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)

    vendor_code = Column(String(30), unique=True, nullable=False, index=True)
    vendor_name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey('vgk_vendor_categories.id'), nullable=False)
    category_name = Column(String(100), nullable=True)   # denormalised for speed

    # Business identity
    gst_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    shop_description = Column(Text, nullable=True)
    established_year = Column(SmallInteger, nullable=True)

    # Contact
    contact_person = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=False)
    alternate_phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    whatsapp_number = Column(String(20), nullable=True)

    # Address
    address_line1 = Column(String(300), nullable=True)
    address_line2 = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True, index=True)
    map_link = Column(String(500), nullable=True)

    # Flat discount % agreed across all categories (overridden per product category)
    flat_discount_pct = Column(Numeric(5, 2), default=0)

    # QR
    qr_token = Column(String(64), unique=True, nullable=False, index=True)

    # Status
    status = Column(String(20), default='PENDING', nullable=False)
    # PENDING | ACTIVE | SUSPENDED | TERMINATED
    is_active = Column(Boolean, default=False)

    # Marketplace
    marketplace_opted = Column(Boolean, default=False)

    # Branding
    logo_url = Column(Text, nullable=True)
    banner_url = Column(Text, nullable=True)

    # Portal login exists
    has_login = Column(Boolean, default=False)

    # Onboarding
    created_by_staff_id = Column(Integer, nullable=True)
    activated_by_staff_id = Column(Integer, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Aggregate stats (updated on transaction approval)
    total_transactions = Column(Integer, default=0)
    total_business_value = Column(Numeric(14, 2), default=0)
    total_discount_given = Column(Numeric(14, 2), default=0)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        Index('idx_vgk_vendor_company_status', 'company_id', 'status'),
        Index('idx_vgk_vendor_pincode', 'pincode'),
    )


# ── 3. Vendor KYC ─────────────────────────────────────────────────────────────
class VGKVendorKYC(BaseModel):
    __tablename__ = 'vgk_vendor_kyc'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vgk_vendors.id'), nullable=False, index=True)

    doc_type = Column(String(50), nullable=False)
    # AADHAR_FRONT | AADHAR_BACK | PAN | GST_CERT | SHOP_PHOTO | OTHER
    doc_label = Column(String(100), nullable=True)
    doc_url = Column(Text, nullable=True)          # uploaded file URL
    doc_number = Column(String(100), nullable=True)
    verified = Column(Boolean, default=False)
    verified_by_staff_id = Column(Integer, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        Index('idx_vgk_vendor_kyc_vendor', 'vendor_id'),
    )


# ── 4. Vendor Agreement (T&C) ─────────────────────────────────────────────────
class VGKVendorAgreement(BaseModel):
    """
    Records the vendor's digital acceptance of T&C + agreed discount % and validity.
    A new record is created on each re-acceptance (agreement renewal).
    """
    __tablename__ = 'vgk_vendor_agreements'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vgk_vendors.id'), nullable=False, index=True)

    terms_version = Column(String(20), nullable=False, default='V1.0')
    agreed_discount_pct = Column(Numeric(5, 2), nullable=False)  # flat % committed
    valid_from = Column(DateTime, nullable=False, default=get_indian_time)
    valid_till = Column(DateTime, nullable=True)   # NULL = open-ended until cancelled

    # Digital signature fields
    signed_at = Column(DateTime, nullable=True)
    signed_by_name = Column(String(200), nullable=True)
    signed_by_designation = Column(String(100), nullable=True)
    signing_ip = Column(String(45), nullable=True)

    is_current = Column(Boolean, default=True)  # only one current per vendor
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_staff_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=get_indian_time)

    __table_args__ = (
        Index('idx_vgk_vendor_agreement_vendor', 'vendor_id', 'is_current'),
    )


# ── 5. Vendor Product Categories ──────────────────────────────────────────────
class VGKVendorProductCategory(BaseModel):
    """
    Per-vendor product sub-categories.
    Each carries its own GST % and optional discount % override.
    Example: Vendor = Grand Sweets → cats = [Sweets 5%GST 4%disc, Bakery 18%GST 3%disc]

    DC-VGK-MKT-ENHANCE-001: category_prefix used to auto-generate product kit codes.
    e.g. category_name='Rice' + category_prefix='RC' → kit = RC2507001
    """
    __tablename__ = 'vgk_vendor_product_categories'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vgk_vendors.id'), nullable=False, index=True)

    category_name = Column(String(150), nullable=False)   # "Sweets", "Bakery", "Savouries"
    category_prefix = Column(String(10), nullable=True)   # "RC", "GR" — used for kit code gen
    gst_pct = Column(Numeric(5, 2), default=0)
    discount_pct = Column(Numeric(5, 2), nullable=True)   # overrides flat_discount_pct
    description = Column(Text, nullable=True)
    display_order = Column(SmallInteger, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        Index('idx_vgk_vendor_prod_cat_vendor', 'vendor_id', 'is_active'),
    )


# ── 6. Vendor Portal Login ────────────────────────────────────────────────────
class VGKVendorLogin(BaseModel):
    __tablename__ = 'vgk_vendor_logins'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vgk_vendors.id'), nullable=False, unique=True)

    username = Column(String(100), nullable=False, index=True)   # phone or email
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(SmallInteger, default=0)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        UniqueConstraint('company_id', 'username', name='uq_vgk_vendor_login_username'),
        Index('idx_vgk_vendor_login_vendor', 'vendor_id'),
    )


# ── 7. Vendor Transaction (Member Purchase) ───────────────────────────────────
class VGKVendorTransaction(BaseModel):
    """
    Member submits a purchase invoice at a VGK vendor.
    On Accounts approval → discount credited to member VGK wallet.
    Member may also optionally pay from wallet (wallet_used_amount).

    DC-VGK-MKT-ENHANCE-001: marketplace_product_id (nullable) links the purchase to a
    specific marketplace product so that on approval, vendor stock (stock_qty) auto-decrements.
    """
    __tablename__ = 'vgk_vendor_transactions'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)

    txn_number = Column(String(40), nullable=False, unique=True)

    # Parties
    vendor_id = Column(Integer, ForeignKey('vgk_vendors.id'), nullable=False, index=True)
    vendor_name = Column(String(200), nullable=True)
    member_partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    product_category_id = Column(Integer, ForeignKey('vgk_vendor_product_categories.id'), nullable=True)
    product_category_name = Column(String(150), nullable=True)

    # Marketplace product link (optional) — enables auto stock deduction on approval
    marketplace_product_id = Column(
        Integer,
        ForeignKey('vgk_vendor_marketplace_products.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # Invoice details
    invoice_number = Column(String(100), nullable=False)
    invoice_date = Column(DateTime, nullable=True)
    amount_excl_tax = Column(Numeric(12, 2), nullable=False)
    gst_amount = Column(Numeric(12, 2), default=0)
    amount_total = Column(Numeric(12, 2), nullable=False)

    # Discount
    discount_pct = Column(Numeric(5, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), nullable=False)

    # Wallet usage (member pays from wallet)
    wallet_used_amount = Column(Numeric(12, 2), default=0)
    wallet_debited = Column(Boolean, default=False)

    # Cashback (discount credited to wallet on approval)
    cashback_credited = Column(Boolean, default=False)

    # Status
    status = Column(String(20), default='PENDING', nullable=False)
    # PENDING | APPROVED | REJECTED | CANCELLED

    # Staff action
    reviewed_by_staff_id = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Invoice image URL (optional attachment)
    invoice_image_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        Index('idx_vgk_vendor_txn_vendor_status', 'vendor_id', 'status'),
        Index('idx_vgk_vendor_txn_member', 'member_partner_id', 'status'),
        Index('idx_vgk_vendor_txn_company', 'company_id', 'status'),
    )


# ── 8. Vendor Marketplace Product ─────────────────────────────────────────────
class VGKVendorMarketplaceProduct(BaseModel):
    """
    Products listed by marketplace-opted vendors.
    Browseable by VGK members in the vendor directory.

    DC-VGK-MKT-ENHANCE-001:
    - approval_status (PENDING/APPROVED/REJECTED): only APPROVED products visible to members
    - image_caption_1/2/3: per-photo captions
    - stock_qty: vendor-managed inventory counter; auto-decrements on transaction approval
      when the transaction includes marketplace_product_id (via VGKVendorTransaction)
    """
    __tablename__ = 'vgk_vendor_marketplace_products'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('vgk_vendors.id'), nullable=False, index=True)

    segment_slug = Column(String(60), nullable=False, index=True)
    # ev-spares | real-dreams | furniture | restaurant | sweet-shop | general | etc.

    product_name = Column(String(200), nullable=False)
    product_kit = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    price_excl_tax = Column(Numeric(12, 2), nullable=True)
    gst_pct = Column(Numeric(5, 2), default=0)
    price_with_tax = Column(Numeric(12, 2), nullable=True)
    discount_pct = Column(Numeric(5, 2), default=0)

    # Photos (uploaded via universal upload; stored in object storage)
    image_url_1 = Column(Text, nullable=True)
    image_url_2 = Column(Text, nullable=True)
    image_url_3 = Column(Text, nullable=True)
    image_caption_1 = Column(Text, nullable=True)
    image_caption_2 = Column(Text, nullable=True)
    image_caption_3 = Column(Text, nullable=True)

    # Approval workflow (PENDING → APPROVED / REJECTED)
    # Only APPROVED products are visible to members.
    approval_status = Column(String(20), nullable=True, default='PENDING')
    approved_by_staff_id = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Vendor stock counter — vendor manages; auto-decrements on confirmed sale
    stock_qty = Column(Integer, nullable=True, default=0)

    display_order = Column(SmallInteger, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    views_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        Index('idx_vgk_mkt_product_vendor', 'vendor_id', 'is_active'),
        Index('idx_vgk_mkt_product_segment', 'company_id', 'segment_slug', 'is_active'),
        Index('idx_vgk_mkt_product_approval', 'company_id', 'approval_status', 'is_active'),
    )
