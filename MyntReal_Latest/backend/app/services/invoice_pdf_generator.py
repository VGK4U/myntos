"""
Invoice PDF Generator Service
DC Protocol Mar 2026: Generates Tax Invoice or Estimate copy PDFs for service billings.

MODES:
  mode='tax_invoice' — Full GST-compliant invoice with CGST/SGST breakdown, GSTIN shown.
                       Heading: TAX INVOICE. Totals include tax.
  mode='estimate'    — Estimate copy without GST details. Heading: ESTIMATED BILL.
                       No CGST/SGST columns. Totals exclude tax.
"""

import os
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import logging


def _get_initials_avatar_table(name: str):
    """
    DC_PARTNER_LOGO_001: Generate a colored initials box for use in PDF header
    when no logo image is uploaded. Returns a ReportLab Table element.
    """
    # Pick a consistent color from the name
    _palette = [
        '#4f46e5', '#0891b2', '#059669', '#d97706',
        '#dc2626', '#7c3aed', '#db2777', '#0369a1',
    ]
    color_hex = _palette[sum(ord(c) for c in (name or 'X')) % len(_palette)]
    bg_color = HexColor(color_hex)
    text_color = colors.white

    # Build initials (up to 2 chars from first two words)
    words = (name or 'BZ').split()
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    else:
        initials = (name or 'BZ')[:2].upper()

    initials_style = ParagraphStyle(
        'InitialsAvatar',
        fontSize=20,
        fontName='Helvetica-Bold',
        textColor=text_color,
        alignment=TA_CENTER,
        leading=24,
    )
    cell = Paragraph(initials, initials_style)
    tbl = Table([[cell]], colWidths=[52*mm], rowHeights=[20*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [6]),
        ('BOX',        (0, 0), (-1, -1), 0, colors.white),
    ]))
    tbl.hAlign = 'CENTER'
    return tbl

_UPLOADS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

logger = logging.getLogger(__name__)

COMPANY_NAME = "MyntReal LLP"
COMPANY_ADDRESS = "Corporate Office Address"
COMPANY_GSTIN = "GSTIN: XXXXXXXXXXXXXXXXX"
COMPANY_PHONE = "Phone: +91-XXXXXXXXXX"
COMPANY_EMAIL = "Email: support@mnrteam.com"

# DC Protocol Mar 2026: Legal company name map for billing
COMPANY_ID_MAP = {
    1: ("Real Dreams", None),
    2: ("VGK4U Mobility Pvt Ltd", None),
    3: ("MNR Mega Natural Resources", None),
    4: ("MyntReal LLP", "GSTIN: XXXXXXXXXXXXXXXXX"),
    5: ("EV Service Center Operations", None),
}

COMPUTER_GENERATED_DISCLAIMER = (
    "This is a computer-generated document and does not require a physical signature. "
    "It is legally valid as per the Information Technology Act, 2000."
)

PROFORMA_TERMS = [
    "This is a PROFORMA INVOICE and is NOT a final Tax Invoice.",
    "GST amounts shown are indicative and will be confirmed on the final Tax Invoice upon order confirmation.",
    "Prices and availability are subject to change until the order is formally confirmed.",
    "This proforma is valid for 7 days from the date of issue.",
    "All products carry warranty as per the manufacturer's terms and conditions.",
    "E&OE — Errors and Omissions Excepted.",
]

PURCHASE_ORDER_TERMS = [
    "This is a PURCHASE ORDER issued by the Buyer and is NOT a tax invoice.",
    "The Seller (Vendor) is requested to supply the goods/services as per the terms specified herein.",
    "Goods must be accompanied by a valid Tax Invoice with correct HSN codes and GST amounts.",
    "Goods shall be provided with standard warranty and guarantee as applicable.",
    "Partial deliveries are not accepted unless explicitly approved in writing.",
    "The Buyer reserves the right to return goods that do not meet quality specifications.",
    "E&OE — Errors and Omissions Excepted.",
]

ESTIMATE_TERMS = [
    "This is an ESTIMATE only and is NOT a Tax Invoice.",
    "Final charges may vary based on actual work performed and parts used.",
    "This estimate is valid for 7 days from the date of issue.",
    "Taxes will be applicable as per prevailing GST rates on the final Tax Invoice.",
    "All products carry warranty as applicable per the manufacturer's or supplier's warranty terms. "
    "Warranty claims must be raised directly with the respective manufacturer or supplier.",
    "Once sold, goods cannot be returned or exchanged unless specifically agreed in writing.",
    "E&OE — Errors and Omissions Excepted.",
]

WARRANTY_TERMS = [
    "All products carry warranty as per the manufacturer's or supplier's terms and conditions.",
    "Warranty claims must be raised directly with the manufacturer or authorised service centre. "
    "The seller's liability is limited to facilitating the claim process only.",
    "Warranty does not cover physical damage, water damage, misuse, tampering, or unauthorised modifications.",
    "Once sold, goods cannot be taken back or exchanged. Services rendered are non-refundable once performed.",
    "Payment is due on receipt unless otherwise agreed in writing.",
    "E&OE — Errors and Omissions Excepted.",
]


def generate_invoice_pdf(billing, items, ticket, mode: str = 'tax_invoice',
                         company_info: dict = None) -> bytes:
    """
    Generate a PDF for a service billing / sales invoice / purchase order.

    Args:
        billing:      Billing adapter object
        items:        List of line-item adapter objects
        ticket:       ServiceTicket object (may be None for sales/purchase invoices)
        mode:         'tax_invoice'        → TAX INVOICE  (green, GST shown)
                      'estimate'           → ESTIMATED BILL (blue, no GST)
                      'proforma_invoice'   → PROFORMA INVOICE (navy, GST shown, pre-confirmation)
                      'purchase_order'     → PURCHASE ORDER (amber, GST shown, pre-confirmation)
        company_info: Optional dict with real AssociatedCompany data:
                      {name, gst_number, address, city, state, pincode, phone, email}
                      When provided, overrides the COMPANY_ID_MAP placeholder values.

    Returns:
        bytes: PDF file content
    """
    is_estimate       = (mode == 'estimate')
    is_proforma       = (mode == 'proforma_invoice')
    is_purchase_order = (mode == 'purchase_order')

    # DC Protocol Mar 2026: Coupon discount — applied proportionally to each item's amounts
    _coupon_pct   = float(getattr(billing, 'coupon_discount_pct', None) or 0)
    _coupon_ratio = 1.0 - _coupon_pct / 100.0
    _coupon_code  = (getattr(billing, 'coupon_code', None) or '').strip()
    _has_coupon   = _coupon_pct > 0
    # DC_IGST_PDF_001: Detect IGST mode from billing adapter
    _is_igst_mode = bool(getattr(billing, 'is_igst', False))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # Colour theme per mode
    if is_estimate:
        _theme_color = colors.Color(0.1, 0.3, 0.6)       # blue
    elif is_proforma:
        _theme_color = colors.Color(0.2, 0.1, 0.55)      # deep indigo
    elif is_purchase_order:
        _theme_color = colors.Color(0.6, 0.3, 0.0)       # amber/brown
    else:
        _theme_color = colors.darkgreen                    # confirmed green

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=_theme_color,
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=5
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=3
    )

    terms_style = ParagraphStyle(
        'Terms',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.grey,
        spaceAfter=2,
        leading=9
    )

    elements = []

    # ── Header — DC_PDF_PARTNER_001: use seller_override if present, else company map ──
    _seller_name    = getattr(billing, 'seller_name', None)
    _seller_address = getattr(billing, 'seller_address', None)
    _seller_gstin   = getattr(billing, 'seller_gstin', None)
    _seller_phone   = getattr(billing, 'seller_phone', None)
    _facilitated_by = getattr(billing, 'facilitated_by', None)
    _logo_path      = getattr(billing, 'logo_path', None)

    if _seller_name:
        # DC_PARTNER_LOGO_001: Show logo if uploaded, else initials-based placeholder
        _logo_rendered = False
        if _logo_path:
            try:
                _full_logo = os.path.join(_UPLOADS_ROOT, _logo_path.lstrip('/'))
                if os.path.exists(_full_logo):
                    _logo_img = RLImage(_full_logo, width=60*mm, height=20*mm, kind='proportional')
                    _logo_img.hAlign = 'CENTER'
                    elements.append(_logo_img)
                    elements.append(Spacer(1, 4))
                    _logo_rendered = True
            except Exception:
                pass
        if not _logo_rendered:
            # Show branded initials box as placeholder
            elements.append(_get_initials_avatar_table(_seller_name))
            elements.append(Spacer(1, 4))
        # Partner invoice: header = partner details
        elements.append(Paragraph(f"<b>{_seller_name}</b>", title_style))
        if _seller_address:
            elements.append(Paragraph(_seller_address, header_style))
        if not is_estimate:
            _gstin_ph = _seller_gstin if _seller_gstin else "GSTIN: N/A"
            _phone_ph = _seller_phone if _seller_phone else ""
            _info_line = f"{_gstin_ph}" + (f" | Phone: {_seller_phone}" if _seller_phone else "")
            elements.append(Paragraph(_info_line, header_style))
        elif _seller_phone:
            elements.append(Paragraph(f"Phone: {_seller_phone}", header_style))
    else:
        # DC_COMPANY_CONTACT_001: Use real AssociatedCompany data when provided,
        # else fall back to COMPANY_ID_MAP placeholder values.
        if company_info and company_info.get('name'):
            cname  = company_info['name']
            cgstin = company_info.get('gst_number') or ''
            caddr_parts = [p for p in [
                company_info.get('address', ''),
                company_info.get('city', ''),
                company_info.get('state', ''),
                company_info.get('pincode', ''),
            ] if p]
            caddr  = ', '.join(caddr_parts) or COMPANY_ADDRESS
            cphone = company_info.get('phone', '') or ''
            cemail = company_info.get('email', '') or ''
        else:
            cname, cgstin = COMPANY_ID_MAP.get(billing.company_id, (COMPANY_NAME, COMPANY_GSTIN)) \
                if billing.company_id else (COMPANY_NAME, COMPANY_GSTIN)
            caddr  = COMPANY_ADDRESS
            cphone = ''
            cemail = ''

        elements.append(Paragraph(f"<b>{cname}</b>", title_style))
        elements.append(Paragraph(caddr, header_style))
        if not is_estimate:
            gstin_line = (f"GSTIN: {cgstin}" if cgstin and not cgstin.startswith('GSTIN:') else cgstin) or COMPANY_GSTIN
            contact_parts = [gstin_line]
            if cphone:
                contact_parts.append(f"Ph: {cphone}")
            if cemail:
                contact_parts.append(cemail)
            elements.append(Paragraph(' | '.join(contact_parts), header_style))
        else:
            _est_contact = ' | '.join(p for p in [
                (f"Ph: {cphone}" if cphone else ''),
                cemail,
            ] if p) or COMPANY_PHONE
            elements.append(Paragraph(_est_contact, header_style))
    elements.append(Spacer(1, 10))

    # ── Document title ────────────────────────────────────────────────
    if is_estimate:
        doc_title_text  = "ESTIMATED BILL"
        doc_title_color = colors.Color(0.1, 0.3, 0.6)
    elif is_proforma:
        doc_title_text  = "PROFORMA INVOICE"
        doc_title_color = colors.Color(0.2, 0.1, 0.55)
    elif is_purchase_order:
        doc_title_text  = "PURCHASE ORDER"
        doc_title_color = colors.Color(0.6, 0.3, 0.0)
    else:
        doc_title_text  = "TAX INVOICE"
        doc_title_color = colors.darkblue
    elements.append(Paragraph(f"<b>{doc_title_text}</b>", ParagraphStyle(
        'DocTitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        textColor=doc_title_color,
        spaceAfter=15,
        spaceBefore=10,
        borderWidth=1,
        borderColor=doc_title_color,
        borderPadding=5
    )))

    # ── Invoice / Estimate metadata ───────────────────────────────────
    if is_estimate:
        ref_label = "Estimate Ref:"
    elif is_proforma:
        ref_label = "Proforma Ref:"
    elif is_purchase_order:
        ref_label = "PO Number:"
    else:
        ref_label = "Invoice No:"
    ref_number = billing.invoice_number or billing.bill_reference or f"EST-{billing.id}"
    invoice_date = billing.created_at.strftime('%d-%b-%Y') if billing.created_at else datetime.now().strftime('%d-%b-%Y')

    # DC_PDF_STATUS_002: Only show Status row on confirmed tax invoices where
    # payment status is meaningful (PAID / PARTIAL). Never show "PENDING" on drafts/proforma.
    invoice_info = [
        [ref_label, ref_number, 'Date:', invoice_date],
    ]
    if not is_purchase_order and not is_proforma and not is_estimate:
        _pay_status_val = (getattr(billing, 'payment_status', '') or '').strip().upper()
        if _pay_status_val and _pay_status_val not in ('PENDING', 'UNPAID', ''):
            invoice_info.append(['', '', 'Status:', _pay_status_val])
    info_table = Table(invoice_info, colWidths=[70, 150, 70, 150])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # ── Bill To ───────────────────────────────────────────────────────
    customer_name = billing.billing_customer_name or (ticket.customer_name if ticket else 'N/A')
    customer_phone = billing.billing_customer_phone or (ticket.customer_phone if ticket else 'N/A')
    customer_address = billing.billing_customer_address or ''
    customer_gstin = billing.billing_customer_gstin or ''

    if is_purchase_order:
        # DC_PO_VENDOR_BLOCK_001: Vendor block — left-aligned, constrained to left half of page
        _vb_rows = []
        _vb_rows.append([Paragraph("<b>Vendor:</b>", normal_style)])
        _vb_rows.append([Paragraph(f"Name: {customer_name}", normal_style)])
        if customer_phone and customer_phone not in ('N/A', ''):
            _vb_rows.append([Paragraph(f"Phone: {customer_phone}", normal_style)])
        if customer_address:
            # Split at commas: first 2 parts = street, rest = city/state/pin
            _ap = [p.strip() for p in customer_address.split(',') if p.strip()]
            _line1 = ', '.join(_ap[:2]) if len(_ap) > 1 else _ap[0] if _ap else ''
            _line2 = ', '.join(_ap[2:]) if len(_ap) > 2 else ''
            _vb_rows.append([Paragraph(f"Address: {_line1}", normal_style)])
            if _line2:
                _vb_rows.append([Paragraph(f"    {_line2}", normal_style)])
        if customer_gstin:
            _vb_rows.append([Paragraph(f"GSTIN: {customer_gstin}", normal_style)])
        _vt = Table(_vb_rows, colWidths=[85 * mm])
        _vt.setStyle(TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        _vt.hAlign = 'LEFT'
        elements.append(_vt)
    else:
        elements.append(Paragraph("<b>Bill To:</b>", normal_style))
        elements.append(Paragraph(f"Name: {customer_name}", normal_style))
        elements.append(Paragraph(f"Phone: {customer_phone}", normal_style))
        if customer_address:
            elements.append(Paragraph(f"Address: {customer_address}", normal_style))
        if customer_gstin and not is_estimate:
            elements.append(Paragraph(f"GSTIN: {customer_gstin}", normal_style))

        # ── Ship To (only if different from billing address) ────────────
        shipping_addr = getattr(billing, 'shipping_address', None) or ''
        if shipping_addr and shipping_addr.strip() != (customer_address or '').strip():
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("<b>Ship To:</b>", normal_style))
            elements.append(Paragraph(f"Address: {shipping_addr}", normal_style))

    elements.append(Spacer(1, 15))

    # ── Service details ───────────────────────────────────────────────
    if ticket:
        product_info = f"Product: {ticket.product_name or 'N/A'} | Serial: {ticket.product_serial or 'N/A'}"
        elements.append(Paragraph(f"<b>Service Details:</b> {product_info}", normal_style))
        elements.append(Spacer(1, 10))

    # ── Line items table ──────────────────────────────────────────────
    # Shared helper to build a description Paragraph with sub-lines for specs/warranty/serial
    desc_normal = ParagraphStyle('DescNormal', parent=styles['Normal'], fontSize=8, leading=11,
                                 fontName='Helvetica-Bold')
    desc_code = ParagraphStyle('DescCode', parent=styles['Normal'], fontSize=6.5, leading=8,
                               textColor=colors.Color(0.25, 0.25, 0.65), fontName='Courier')
    desc_sub = ParagraphStyle('DescSub', parent=styles['Normal'], fontSize=7, leading=9,
                              textColor=colors.Color(0.25, 0.25, 0.25))
    desc_serial = ParagraphStyle('DescSerial', parent=styles['Normal'], fontSize=7, leading=9,
                                 textColor=colors.Color(0.1, 0.35, 0.6))
    desc_warranty = ParagraphStyle('DescWarranty', parent=styles['Normal'], fontSize=6.5, leading=9,
                                   textColor=colors.Color(0.1, 0.5, 0.2))

    def _build_desc_cell(item):
        parts = [Paragraph(item.description or '—', desc_normal)]
        # Item code / SKU line
        item_code = getattr(item, 'item_code', None) or ''
        if item_code:
            parts.append(Paragraph(f"Item#: {item_code}", desc_code))
        # Specification
        spec = getattr(item, 'specification', None) or ''
        color = getattr(item, 'color', None) or ''
        spec_color = ' | '.join(filter(None, [spec, (f"Colour: {color}" if color else '')]))
        if spec_color:
            parts.append(Paragraph(spec_color, desc_sub))
        # Batch number
        batch = getattr(item, 'batch_number', None) or ''
        if batch:
            parts.append(Paragraph(f"Batch: {batch}", desc_sub))
        # Warranty
        w_info = getattr(item, 'warranty_info', None) or ''
        if w_info:
            w_display = w_info if len(str(w_info)) <= 150 else str(w_info)[:150] + '…'
            parts.append(Paragraph(f"Warranty: {w_display}", desc_warranty))
        # Serial numbers
        serials = getattr(item, 'serial_numbers', None) or []
        if serials:
            parts.append(Paragraph(f"S/N: {', '.join(str(s) for s in serials)}", desc_serial))
        return parts

    # Running totals — accumulated from per-item coupon-adjusted amounts for summary use
    _sum_raw_taxable = 0.0
    _sum_raw_cgst    = 0.0
    _sum_raw_sgst    = 0.0
    _sum_raw_igst    = 0.0
    _sum_adj_taxable = 0.0
    _sum_adj_cgst    = 0.0
    _sum_adj_sgst    = 0.0
    _sum_adj_igst    = 0.0

    if is_estimate or is_proforma or is_purchase_order:
        # Estimate / Proforma / PO columns — no confirmed GST breakdown; Proforma+PO still show indicative GST
        # With coupon:    # | Desc | HSN/SAC | Qty | Rate (Ex-Tax) | Coupon (-X%) | Amount (After Disc.)
        # Without coupon: # | Desc | HSN/SAC | Qty | Rate (Ex-Tax) | Amount (Ex-Tax)
        if _has_coupon:
            table_header = ['#', 'Description', 'HSN/SAC', 'Qty', 'Rate\n(Ex-Tax)',
                            f'Coupon\n(-{_coupon_pct:.0f}%)', 'Amount\n(After Disc.)']
            col_widths = [14, 150, 38, 22, 65, 55, 70]   # = 414 — fits A4
        else:
            table_header = ['#', 'Description', 'HSN/SAC', 'Qty', 'Rate\n(Ex-Tax)', 'Amount\n(Ex-Tax)']
            col_widths = [14, 185, 42, 25, 85, 95]   # = 446 — fits A4
        table_data = [table_header]
        for idx, item in enumerate(items, 1):
            raw_taxable = float(item.taxable_amount or 0)
            qty = int(item.quantity or 1)
            adj_taxable = round(raw_taxable * _coupon_ratio, 2)
            coupon_disc = round(raw_taxable * _coupon_pct / 100, 2)
            _sum_raw_taxable += raw_taxable
            _sum_adj_taxable += adj_taxable
            if _has_coupon:
                row = [
                    str(idx),
                    _build_desc_cell(item),
                    item.hsn_code or '—',
                    str(qty),
                    f"Rs.{raw_taxable:.2f}",
                    f"−Rs.{coupon_disc:.2f}",
                    f"Rs.{adj_taxable:.2f}",
                ]
            else:
                row = [
                    str(idx),
                    _build_desc_cell(item),
                    item.hsn_code or '—',
                    str(qty),
                    f"Rs.{raw_taxable:.2f}",
                    f"Rs.{adj_taxable:.2f}",
                ]
            table_data.append(row)
        hdr_color = _theme_color
    else:
        # Tax Invoice columns match web table exactly:
        # With coupon:    # | Desc | HSN/SAC | Qty | Rate (Ex-Tax) | Coupon (-X%) | Taxable (After Disc.) | GST% | GST Amt | Total (Incl. GST)
        # Without coupon: # | Desc | HSN/SAC | Qty | Rate (Ex-Tax) | Taxable (After Disc.) | GST% | GST Amt | Total (Incl. GST)
        _coupon_col_label = f'Coupon\n(-{_coupon_pct:.0f}%)' if _has_coupon else None
        if _has_coupon:
            table_header = ['#', 'Description', 'HSN/SAC', 'Qty', 'Rate\n(Ex-Tax)', _coupon_col_label,
                            'Taxable\n(After Disc.)', 'GST\n%', 'GST\nAmount', 'Total\n(Incl. GST)']
            col_widths = [14, 98, 32, 20, 58, 46, 52, 22, 48, 52]  # = 442 — fits A4 (482pt); Rate+Coupon widened to prevent overflow
        else:
            table_header = ['#', 'Description', 'HSN/SAC', 'Qty', 'Rate\n(Ex-Tax)',
                            'Taxable\n(After Disc.)', 'GST\n%', 'GST\nAmount', 'Total\n(Incl. GST)']
            col_widths = [14, 130, 38, 22, 58, 62, 24, 50, 58]   # = 456 — fits A4 (482pt)
        table_data = [table_header]
        for idx, item in enumerate(items, 1):
            raw_taxable = float(item.taxable_amount or 0)
            raw_cgst    = float(item.cgst_amount or 0)
            raw_sgst    = float(item.sgst_amount or 0)
            raw_igst    = float(getattr(item, 'igst_amount', None) or 0)
            # Effective GST rate for display
            gst_rate = float(item.tax_rate or 0)
            if not gst_rate:
                gst_rate = float(item.cgst_rate or 0) * 2 + float(getattr(item, 'igst_rate', None) or 0)
            # Apply coupon ratio proportionally — matches web computation exactly
            adj_taxable = round(raw_taxable * _coupon_ratio, 2)
            adj_gst     = round((raw_cgst + raw_sgst + raw_igst) * _coupon_ratio, 2)
            adj_total   = adj_taxable + adj_gst
            _sum_raw_taxable += raw_taxable
            _sum_raw_cgst    += raw_cgst
            _sum_raw_sgst    += raw_sgst
            _sum_raw_igst    += raw_igst
            _sum_adj_taxable += adj_taxable
            _sum_adj_cgst    += round(raw_cgst * _coupon_ratio, 2)
            _sum_adj_sgst    += round(raw_sgst * _coupon_ratio, 2)
            _sum_adj_igst    += round(raw_igst * _coupon_ratio, 2)
            coupon_disc = round(raw_taxable * _coupon_pct / 100, 2)
            gst_pct_str = f"{gst_rate:.0f}%" if gst_rate else "—"
            gst_amt_str = f"Rs.{adj_gst:.2f}" if adj_gst else "—"
            if _has_coupon:
                row = [
                    str(idx),
                    _build_desc_cell(item),
                    item.hsn_code or '—',
                    str(int(item.quantity)) if item.quantity else '1',
                    f"Rs.{raw_taxable:.2f}",        # Rate (Ex-Tax)
                    f"−Rs.{coupon_disc:.2f}",        # Coupon deduction
                    f"Rs.{adj_taxable:.2f}",         # Taxable after coupon
                    gst_pct_str,                     # GST %
                    gst_amt_str,                     # GST Amount (combined)
                    f"Rs.{adj_total:.2f}"            # Total incl. GST
                ]
            else:
                row = [
                    str(idx),
                    _build_desc_cell(item),
                    item.hsn_code or '—',
                    str(int(item.quantity)) if item.quantity else '1',
                    f"Rs.{raw_taxable:.2f}",         # Rate (Ex-Tax)
                    f"Rs.{adj_taxable:.2f}",          # Taxable (= raw when no coupon)
                    gst_pct_str,
                    gst_amt_str,
                    f"Rs.{adj_total:.2f}"
                ]
            table_data.append(row)
        hdr_color = colors.Color(0.2, 0.4, 0.2)

    items_table = Table(table_data, colWidths=col_widths)
    _tbl_style = [
        ('BACKGROUND', (0, 0), (-1, 0), hdr_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        # # column — center
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        # Description column — left
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        # HSN col (2) — center; Qty col (3) — center
        ('ALIGN', (2, 1), (3, -1), 'CENTER'),
        # All numeric cols from Rate onward — right
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
    ]
    if _has_coupon:
        # Coupon column (index 5) — amber; Amount/Taxable col (index 6) — green
        _tbl_style += [
            ('BACKGROUND', (5, 1), (5, -1), colors.Color(1.0, 0.97, 0.88)),
            ('TEXTCOLOR', (5, 1), (5, -1), colors.Color(0.65, 0.33, 0.0)),
            ('BACKGROUND', (6, 1), (6, -1), colors.Color(0.92, 1.0, 0.92)),
            ('TEXTCOLOR', (6, 1), (6, -1), colors.Color(0.0, 0.4, 0.1)),
        ]
    if not is_estimate:
        # GST% column center: index 7 with coupon, index 6 without
        _gst_pct_col = 7 if _has_coupon else 6
        _tbl_style += [('ALIGN', (_gst_pct_col, 1), (_gst_pct_col, -1), 'CENTER')]
    items_table.setStyle(TableStyle(_tbl_style))
    elements.append(items_table)

    # DC_SERIAL_SECTION_001: Serial Numbers reference section below item table
    _serial_entries = []
    for item in items:
        _serials = getattr(item, 'serial_numbers', None) or []
        if _serials:
            _item_label = getattr(item, 'description', '') or getattr(item, 'item_name', '') or 'Item'
            _serial_str = ', '.join(str(s) for s in _serials)
            _serial_entries.append((_item_label, _serial_str))
    if _serial_entries:
        elements.append(Spacer(1, 6))
        _sn_header_style = ParagraphStyle(
            'SNHeader', parent=styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold',
            textColor=colors.Color(0.1, 0.25, 0.5),
            spaceAfter=2, leading=10,
        )
        _sn_val_style = ParagraphStyle(
            'SNVal', parent=styles['Normal'],
            fontSize=8, textColor=colors.Color(0.15, 0.15, 0.15),
            spaceAfter=1, leading=10,
        )
        _sn_data = [
            [Paragraph('<b>Serial Numbers Reference</b>', _sn_header_style), '']
        ]
        for _label, _sns in _serial_entries:
            _sn_data.append([
                Paragraph(_label, _sn_val_style),
                Paragraph(_sns, _sn_val_style)
            ])
        _sn_table = Table(_sn_data, colWidths=[140, 300])
        _sn_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.88, 0.92, 0.98)),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('TEXTCOLOR', (0, 1), (0, -1), colors.Color(0.3, 0.3, 0.3)),
        ]))
        elements.append(_sn_table)

    elements.append(Spacer(1, 15))

    # ── Summary / Totals ──────────────────────────────────────────────
    # Use fresh sums accumulated in the items loop above (coupon-adjusted per item).
    # _sum_raw_* = pre-coupon stored values; _sum_adj_* = post-coupon values (what customer pays).

    _manual_disc = float(getattr(billing, 'manual_discount_amount', None) or 0)
    _manual_note = (getattr(billing, 'manual_discount_note', None) or '').strip()

    if is_estimate:
        # Estimate: show raw subtotal; note taxes applicable later
        _est_subtotal = _sum_raw_taxable or float(billing.taxable_amount or 0)
        _est_after_coupon = _sum_adj_taxable if _has_coupon else _est_subtotal
        summary_data = [
            ['', '', 'Subtotal (Excl. Tax):', f"Rs.{_est_subtotal:.2f}"],
        ]
        if _has_coupon:
            _code_tag = f" [{_coupon_code}]" if _coupon_code else ''
            summary_data.append(['', '', f'Coupon Discount{_code_tag} {_coupon_pct:.0f}%:', f"- Rs.{round(_est_subtotal - _est_after_coupon, 2):.2f}"])
        summary_data.append(['', '', '* Taxes applicable on final invoice', ''])
        grand_label = 'Estimated Amount (Excl. Tax)'
        grand_value = _est_after_coupon
    else:
        # DC_IGST_PDF_001: Tax Invoice — show IGST row when IGST mode, else CGST+SGST rows
        raw_taxable = _sum_raw_taxable or float(billing.taxable_amount or 0)
        raw_cgst    = _sum_raw_cgst    or float(billing.cgst_amount    or 0)
        raw_sgst    = _sum_raw_sgst    or float(billing.sgst_amount    or 0)
        raw_igst    = _sum_raw_igst    or float(getattr(billing, 'igst_amount', None) or 0)
        # Fix: raw_grand must include IGST when in IGST mode for correct coupon saving calculation
        if _is_igst_mode:
            raw_grand = raw_taxable + raw_igst
        else:
            raw_grand = raw_taxable + raw_cgst + raw_sgst

        # Grand total = post-coupon, post-roundoff (from billing if available, else sum of adj items)
        if _is_igst_mode:
            grand_value = float(billing.total_amount or (_sum_adj_taxable + _sum_adj_igst))
        else:
            grand_value = float(billing.total_amount or (_sum_adj_taxable + _sum_adj_cgst + _sum_adj_sgst))

        # Full coupon saving = raw total minus grand total (includes savings on GST too)
        _coupon_saving = round(raw_grand - grand_value, 2) if _has_coupon else 0.0

        summary_data = [
            ['', '', 'Taxable Amount:', f"Rs.{raw_taxable:.2f}"],
        ]
        if _is_igst_mode:
            _igst_pct = f"{raw_igst / raw_taxable * 100:g}" if raw_taxable else "0"
            summary_data.append(['', '', f'IGST @ {_igst_pct}%:', f"Rs.{raw_igst:.2f}"])
        else:
            _cgst_pct = f"{raw_cgst / raw_taxable * 100:g}" if raw_taxable else "0"
            _sgst_pct = f"{raw_sgst / raw_taxable * 100:g}" if raw_taxable else "0"
            summary_data.append(['', '', f'CGST @ {_cgst_pct}%:', f"Rs.{raw_cgst:.2f}"])
            summary_data.append(['', '', f'SGST @ {_sgst_pct}%:', f"Rs.{raw_sgst:.2f}"])
        if _has_coupon and _coupon_saving > 0:
            _code_tag = f" [{_coupon_code}]" if _coupon_code else ''
            _coupon_label = f"Coupon Discount{_code_tag} {_coupon_pct:.0f}% (incl. GST saving):"
            summary_data.append(['', '', _coupon_label, f"- Rs.{_coupon_saving:.2f}"])
        grand_label = 'Grand Total (Incl. Tax)'

    # DC_IGST_PDF_001: Only mark coupon row if the coupon row was actually appended (saving > 0)
    _coupon_row_idx = (len(summary_data) - 1) if (_has_coupon and not is_estimate and _coupon_saving > 0) else None

    # Grand total row
    summary_data.append(['', '', grand_label + ':', f"Rs.{grand_value:.2f}"])
    _grand_row_idx = len(summary_data) - 1

    _has_net = _manual_disc > 0
    if _has_net:
        _disc_label = f"Manual Discount{(' (' + _manual_note + ')') if _manual_note else ''} (Post-Tax):"
        summary_data.append(['', '', _disc_label, f"- Rs.{_manual_disc:.2f}"])
        _net_payable_val = float(billing.net_payable or (grand_value - _manual_disc))
        summary_data.append(['', '', 'Net Payable:', f"Rs.{_net_payable_val:.2f}"])

    _last_row_idx = len(summary_data) - 1
    _style_cmds = [
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        # Grand Total row — always highlighted
        ('BACKGROUND', (2, _grand_row_idx), (-1, _grand_row_idx), hdr_color),
        ('TEXTCOLOR', (2, _grand_row_idx), (-1, _grand_row_idx), colors.whitesmoke),
        ('FONTNAME', (2, _grand_row_idx), (-1, _grand_row_idx), 'Helvetica-Bold'),
    ]
    if _coupon_row_idx is not None:
        # Coupon discount row — green tint
        _style_cmds += [
            ('BACKGROUND', (2, _coupon_row_idx), (-1, _coupon_row_idx), colors.Color(0.9, 1.0, 0.9)),
            ('TEXTCOLOR', (2, _coupon_row_idx), (-1, _coupon_row_idx), colors.Color(0.0, 0.45, 0.1)),
            ('FONTNAME', (2, _coupon_row_idx), (-1, _coupon_row_idx), 'Helvetica-Bold'),
        ]
    if _has_net:
        # Manual discount row — amber tint
        _disc_row_idx = _grand_row_idx + 1
        _style_cmds += [
            ('BACKGROUND', (2, _disc_row_idx), (-1, _disc_row_idx), colors.Color(1.0, 0.95, 0.7)),
            ('TEXTCOLOR', (2, _disc_row_idx), (-1, _disc_row_idx), colors.Color(0.6, 0.3, 0.0)),
            ('FONTNAME', (2, _disc_row_idx), (-1, _disc_row_idx), 'Helvetica-Bold'),
        ]
        # Net Payable row — dark highlight
        _style_cmds += [
            ('BACKGROUND', (2, _last_row_idx), (-1, _last_row_idx), colors.Color(0.1, 0.18, 0.3)),
            ('TEXTCOLOR', (2, _last_row_idx), (-1, _last_row_idx), colors.whitesmoke),
            ('FONTNAME', (2, _last_row_idx), (-1, _last_row_idx), 'Helvetica-Bold'),
            ('FONTSIZE', (2, _last_row_idx), (-1, _last_row_idx), 10),
        ]

    summary_table = Table(summary_data, colWidths=[150, 100, 130, 80])
    summary_table.setStyle(TableStyle(_style_cmds))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # ── Remarks / Notes ──────────────────────────────────────────────
    # DC_PDF_REMARKS_001: Show remarks/notes when present (mandatory per DC Protocol).
    _remarks = (getattr(billing, 'remarks', None) or '').strip()
    if _remarks:
        remarks_label_style = ParagraphStyle(
            'RemarksLabel', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica-Bold', spaceAfter=2,
        )
        remarks_val_style = ParagraphStyle(
            'RemarksVal', parent=styles['Normal'],
            fontSize=9, spaceAfter=2, leading=12,
            textColor=colors.Color(0.15, 0.15, 0.15),
            leftIndent=8,
        )
        elements.append(Paragraph("Remarks / Notes:", remarks_label_style))
        elements.append(Paragraph(_remarks, remarks_val_style))
        elements.append(Spacer(1, 12))

    # ── Payment info (Tax Invoice only — not shown on PO / proforma / estimate) ─
    # DC_PDF_STATUS_002: Only show payment line when an actual payment mode is recorded.
    # Never print "Payment Status: Pending" on unpaid or draft invoices.
    if not is_estimate and not is_purchase_order and not is_proforma:
        _pay_mode = (getattr(billing, 'payment_mode', '') or '').strip().upper()
        if _pay_mode:
            payment_info = f"<b>Payment Mode:</b> {_pay_mode}"
            if getattr(billing, 'payment_reference', None):
                payment_info += f" | <b>Reference:</b> {billing.payment_reference}"
            elements.append(Paragraph(payment_info, normal_style))
            elements.append(Spacer(1, 20))

    # ── Terms & Conditions ────────────────────────────────────────────
    if is_estimate:
        terms_list = ESTIMATE_TERMS
    elif is_proforma:
        terms_list = PROFORMA_TERMS
    elif is_purchase_order:
        terms_list = PURCHASE_ORDER_TERMS
    else:
        terms_list = WARRANTY_TERMS
    elements.append(Paragraph("<b>Terms &amp; Conditions:</b>", normal_style))
    for idx, clause in enumerate(terms_list, 1):
        elements.append(Paragraph(f"{idx}. {clause}", terms_style))

    elements.append(Spacer(1, 18))

    # ── Facilitated-by footer (partner invoices only) ─────────────────
    if _facilitated_by:
        facilitated_style = ParagraphStyle(
            'Facilitated',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.Color(0.25, 0.35, 0.55),
            alignment=TA_CENTER,
            leading=10,
            borderWidth=0.5,
            borderColor=colors.Color(0.7, 0.8, 0.95),
            borderPadding=4,
        )
        elements.append(Paragraph(_facilitated_by, facilitated_style))
        elements.append(Spacer(1, 6))

    # ── Computer-generated disclaimer (no signature required) ─────────
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.Color(0.4, 0.4, 0.4),
        alignment=TA_CENTER,
        leading=10,
        borderWidth=0.5,
        borderColor=colors.lightgrey,
        borderPadding=5,
    )
    elements.append(Paragraph(COMPUTER_GENERATED_DISCLAIMER, disclaimer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated {mode} PDF for billing {billing.id} ({len(pdf_bytes)} bytes)")
    return pdf_bytes
