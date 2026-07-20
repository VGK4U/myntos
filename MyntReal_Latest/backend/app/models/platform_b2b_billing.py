"""Task #42 / #43 — Phase 4 + Phase 3a.0 SQLAlchemy models for billing tables.

Phase 3a.0 adds Tally/Zoho-parity columns mirroring sales_invoices schema —
all under one SaaS umbrella, zero impact on the existing sales_invoices /
purchase_invoice / associated_companies tables.
"""
from __future__ import annotations
from sqlalchemy import (
    Column, Integer, String, Date, Numeric, ForeignKey, Text, DateTime, Boolean, text,
)
from sqlalchemy.sql import func
from app.core.database import Base


class PlatformInvoice(Base):
    __tablename__ = "platform_invoices"
    id              = Column(Integer, primary_key=True)
    invoice_number  = Column(String(40), unique=True, nullable=False)
    client_id       = Column(Integer, ForeignKey("platform_clients.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("platform_subscriptions.id"))
    currency        = Column(String(8),  nullable=False, default="INR")
    period_start    = Column(Date, nullable=False)
    period_end      = Column(Date, nullable=False)
    issue_date      = Column(Date, nullable=False, server_default=func.current_date())
    due_date        = Column(Date, nullable=False)
    subtotal        = Column(Numeric(14, 2), nullable=False, default=0)
    tax             = Column(Numeric(14, 2), nullable=False, default=0)
    total           = Column(Numeric(14, 2), nullable=False, default=0)
    amount_paid     = Column(Numeric(14, 2), nullable=False, default=0)
    status          = Column(String(20), nullable=False, default="open")
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now())

    # ── Phase 3a.0 Tally/Zoho parity (mirrors sales_invoices header) ──────────
    company_id          = Column(Integer, ForeignKey("associated_companies.id", ondelete="RESTRICT"), nullable=True, index=True)
    invoice_date        = Column(Date, nullable=True)
    customer_type       = Column(String(40), nullable=True, server_default=text("'B2B_SAAS_TENANT'"))
    customer_name       = Column(String(255), nullable=True)
    customer_address    = Column(Text, nullable=True)
    customer_gstin      = Column(String(20), nullable=True)
    customer_state      = Column(String(80), nullable=True)
    customer_phone      = Column(String(40), nullable=True)
    customer_email      = Column(String(120), nullable=True)
    billing_address     = Column(Text, nullable=True)
    shipping_address    = Column(Text, nullable=True)
    is_igst             = Column(Boolean, nullable=True, server_default=text("false"))
    seller_state        = Column(String(80), nullable=True)
    buyer_state         = Column(String(80), nullable=True)
    taxable_amount      = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    cgst_amount         = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    sgst_amount         = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    igst_amount         = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    cess_amount         = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    total_tax           = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    round_off           = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    grand_total         = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    amount_in_words     = Column(String(255), nullable=True)
    payment_mode        = Column(String(40), nullable=True)
    amount_received     = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    balance_due         = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    is_credit_sale      = Column(Boolean, nullable=True, server_default=text("true"))
    credit_days         = Column(Integer, nullable=True)
    pdf_path            = Column(String(255), nullable=True)
    irn_number          = Column(String(64), nullable=True)
    ack_number          = Column(String(64), nullable=True)
    ack_date            = Column(DateTime, nullable=True)
    e_way_bill_number   = Column(String(64), nullable=True)
    e_way_bill_date     = Column(DateTime, nullable=True)
    terms_conditions    = Column(Text, nullable=True)
    remarks             = Column(Text, nullable=True)
    fy_sequence         = Column(Integer, nullable=True)
    wvv_hash            = Column(String(255), nullable=True)
    billing_company_id  = Column(Integer, ForeignKey("associated_companies.id"), nullable=True)
    so_number           = Column(String(64), nullable=True)


class PlatformInvoiceLine(Base):
    __tablename__ = "platform_invoice_lines"
    id           = Column(Integer, primary_key=True)
    invoice_id   = Column(Integer, ForeignKey("platform_invoices.id", ondelete="CASCADE"), nullable=False)
    module_id    = Column(Integer, ForeignKey("platform_modules.id"))
    description  = Column(String(255), nullable=False)
    quantity     = Column(Numeric(12, 2), nullable=False, default=1)
    unit_price   = Column(Numeric(14, 2), nullable=False, default=0)
    line_total   = Column(Numeric(14, 2), nullable=False, default=0)
    pricing_unit = Column(String(20))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    # ── Phase 3a.0 Tally/Zoho line-level tax parity ──────────────────────────
    hsn_sac_code  = Column(String(20), nullable=True)
    gst_rate      = Column(Numeric(5, 2), nullable=True, server_default=text("0"))
    cgst_amount   = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    sgst_amount   = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    igst_amount   = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    cess_amount   = Column(Numeric(14, 2), nullable=True, server_default=text("0"))
    taxable_value = Column(Numeric(14, 2), nullable=True, server_default=text("0"))


class PlatformPayment(Base):
    __tablename__ = "platform_payments"
    id           = Column(Integer, primary_key=True)
    client_id    = Column(Integer, ForeignKey("platform_clients.id"), nullable=False)
    invoice_id   = Column(Integer, ForeignKey("platform_invoices.id"))
    amount       = Column(Numeric(14, 2), nullable=False)
    currency     = Column(String(8), nullable=False, default="INR")
    method       = Column(String(40))
    reference    = Column(String(120))
    received_on  = Column(Date, nullable=False, server_default=func.current_date())
    notes        = Column(Text)
    recorded_by  = Column(Integer)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
