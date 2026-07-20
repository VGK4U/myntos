"""
Spare Parts Purchase Order PDF Generator
DC-CONSOL-SPARE-001: Generates per-vendor PO receipt for spare parts procurement workbench.
Uses ReportLab — same dependency as invoice_pdf_generator.py
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import logging

logger = logging.getLogger(__name__)

# Brand colours (MNR dark-blue palette)
_DARK = HexColor('#1e3a5f')
_MED  = HexColor('#2563eb')
_LITE = HexColor('#dbeafe')
_GREY = HexColor('#6b7280')
_BDR  = HexColor('#e5e7eb')


def _style(name, **kw):
    s = ParagraphStyle(name, **kw)
    return s


def generate_spare_po_pdf(
    order_number: str,
    order_date: str,
    company_name: str,
    company_address: str,
    company_gstin: str,
    vendor_name: str,
    vendor_address: str,
    vendor_city: str,
    vendor_state: str,
    vendor_gstin: str,
    vendor_phone: str,
    vendor_contact_person: str,
    items: list,          # [{'item_code','item_name','qty','uom','last_rate','estimated_value','demand_source'}]
    notes: str = None,
    created_by: str = None,
    approved_by: str = None,
) -> bytes:
    """
    Generate a Purchase Order PDF for one vendor's spare items.
    Returns raw bytes (PDF).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=15*mm,
    )

    # ── Styles ────────────────────────────────────────────────
    h1 = _style('H1', fontName='Helvetica-Bold', fontSize=16, textColor=colors.white,
                alignment=TA_CENTER, leading=20)
    h2 = _style('H2', fontName='Helvetica-Bold', fontSize=11, textColor=_DARK, leading=14)
    h3 = _style('H3', fontName='Helvetica-Bold', fontSize=9, textColor=_DARK, leading=12)
    body = _style('Body', fontName='Helvetica', fontSize=9, textColor=HexColor('#374151'), leading=12)
    small = _style('Small', fontName='Helvetica', fontSize=8, textColor=_GREY, leading=10)
    right = _style('Right', fontName='Helvetica', fontSize=9, textColor=HexColor('#374151'),
                   alignment=TA_RIGHT, leading=12)
    bold_right = _style('BRight', fontName='Helvetica-Bold', fontSize=9, textColor=_DARK,
                        alignment=TA_RIGHT, leading=12)
    label = _style('Lbl', fontName='Helvetica-Bold', fontSize=8, textColor=_GREY, leading=10)

    story = []

    # ── Header Banner ─────────────────────────────────────────
    header_tbl = Table(
        [[Paragraph('PURCHASE ORDER', h1), Paragraph(f'<b>{order_number}</b>', h1)]],
        colWidths=[100*mm, 65*mm]
    )
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), _DARK),
        ('ALIGN',       (0, 0), (0, 0),   'LEFT'),
        ('ALIGN',       (1, 0), (1, 0),   'RIGHT'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',  (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',(0, 0), (-1, -1), 12),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Company + PO Meta ─────────────────────────────────────
    meta_data = [
        [Paragraph('<b>From (Buyer)</b>', label), Paragraph('<b>PO Details</b>', label)],
        [Paragraph(company_name, h2), Paragraph(f'PO Date: <b>{order_date}</b>', body)],
        [Paragraph(company_address or '', body), Paragraph(f'PO #: <b>{order_number}</b>', body)],
        [Paragraph(f'GSTIN: {company_gstin or "—"}', small),
         Paragraph(f'Created by: {created_by or "—"}', small)],
    ]
    meta_tbl = Table(meta_data, colWidths=[92*mm, 73*mm])
    meta_tbl.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING',(0, 0), (-1, -1), 2),
        ('TOPPADDING',  (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2),
        ('LINEBELOW',   (0, 0), (-1, 0),  0.5, _BDR),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=_BDR))
    story.append(Spacer(1, 3*mm))

    # ── Vendor Block ──────────────────────────────────────────
    story.append(Paragraph('To (Vendor)', label))
    story.append(Spacer(1, 1*mm))
    vendor_data = [[
        Paragraph(f'<b>{vendor_name}</b>', h2),
        Paragraph(f'Contact: {vendor_contact_person or "—"}', body),
    ], [
        Paragraph(f'{vendor_address or ""}, {vendor_city or ""}, {vendor_state or ""}', body),
        Paragraph(f'Phone: {vendor_phone or "—"}', body),
    ], [
        Paragraph(f'GSTIN: {vendor_gstin or "—"}', small),
        Paragraph('', small),
    ]]
    vendor_tbl = Table(vendor_data, colWidths=[100*mm, 65*mm])
    vendor_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), _LITE),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',(0, 0), (-1, -1), 8),
        ('TOPPADDING',  (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('BOX',         (0, 0), (-1, -1), 0.5, _MED),
    ]))
    story.append(vendor_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Items Table ───────────────────────────────────────────
    story.append(Paragraph('Items Ordered', h3))
    story.append(Spacer(1, 2*mm))

    th_style = _style('TH', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white,
                      alignment=TA_CENTER, leading=10)
    td_style = _style('TD', fontName='Helvetica', fontSize=8, textColor=HexColor('#1f2937'),
                      leading=11)
    td_right = _style('TDR', fontName='Helvetica', fontSize=8, textColor=HexColor('#1f2937'),
                      alignment=TA_RIGHT, leading=11)
    td_bold  = _style('TDB', fontName='Helvetica-Bold', fontSize=8, textColor=_DARK,
                      alignment=TA_RIGHT, leading=11)
    td_grey  = _style('TDG', fontName='Helvetica', fontSize=7, textColor=_GREY, leading=9)

    tbl_header = [
        Paragraph('#', th_style),
        Paragraph('Item Code', th_style),
        Paragraph('Description / Specification', th_style),
        Paragraph('Model', th_style),
        Paragraph('Qty', th_style),
        Paragraph('UoM', th_style),
        Paragraph('Last Rate (₹)', th_style),
        Paragraph('Est. Value (₹)', th_style),
        Paragraph('Demand Source', th_style),
    ]
    tbl_data = [tbl_header]
    total_value = 0.0
    for i, item in enumerate(items, 1):
        rate = item.get('last_rate') or 0
        qty  = item.get('qty') or 0
        val  = item.get('estimated_value') or (qty * rate)
        total_value += float(val)
        # Build description cell: item name + specification below in grey
        item_name_para = item.get('item_name') or '—'
        spec_text      = item.get('specification') or ''
        if spec_text:
            desc_cell = Paragraph(f'{item_name_para}<br/><font size="7" color="#6b7280">{spec_text[:80]}</font>', td_style)
        else:
            desc_cell = Paragraph(item_name_para, td_style)
        model_text = item.get('model_compat') or item.get('model') or '—'
        tbl_data.append([
            Paragraph(str(i), td_style),
            Paragraph(item.get('item_code') or '—', td_style),
            desc_cell,
            Paragraph(model_text[:30] if model_text != '—' else '—', td_grey),
            Paragraph(str(qty), td_right),
            Paragraph(item.get('uom') or 'PCS', td_style),
            Paragraph(f"{float(rate):,.2f}" if rate else '—', td_right),
            Paragraph(f"{float(val):,.2f}" if val else '—', td_right),
            Paragraph(item.get('demand_source') or '—', td_grey),
        ])

    # Total row
    tbl_data.append([
        Paragraph('', td_style),
        Paragraph('', td_style),
        Paragraph('<b>TOTAL</b>', _style('TotL', fontName='Helvetica-Bold', fontSize=8,
                                         textColor=_DARK, alignment=TA_RIGHT, leading=11)),
        Paragraph('', td_style),
        Paragraph('', td_style),
        Paragraph('', td_style),
        Paragraph('', td_style),
        Paragraph(f'<b>₹ {total_value:,.2f}</b>', td_bold),
        Paragraph('', td_style),
    ])

    col_widths = [7*mm, 20*mm, 42*mm, 22*mm, 10*mm, 9*mm, 18*mm, 20*mm, 17*mm]
    items_tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  _DARK),
        ('BACKGROUND',   (0, -1), (-1, -1), HexColor('#f0f9ff')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, HexColor('#f9fafb')]),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',         (0, 0), (-1, -1), 0.3, _BDR),
        ('LINEBELOW',    (0, -1), (-1, -1), 1.0, _MED),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('LEFTPADDING',  (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Notes ─────────────────────────────────────────────────
    if notes:
        story.append(HRFlowable(width='100%', thickness=0.3, color=_BDR))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(f'<b>Notes:</b> {notes}', body))
        story.append(Spacer(1, 3*mm))

    # ── Authorization ─────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5, color=_BDR))
    story.append(Spacer(1, 3*mm))
    auth_data = [[
        Paragraph('Prepared by', label),
        Paragraph('Approved by', label),
        Paragraph('Authorised Signatory', label),
    ], [
        Paragraph(created_by or '________________', body),
        Paragraph(approved_by or '________________', body),
        Paragraph('________________', body),
    ], [
        Paragraph('', small),
        Paragraph('', small),
        Paragraph('For ' + company_name, small),
    ]]
    auth_tbl = Table(auth_data, colWidths=[55*mm, 55*mm, 55*mm])
    auth_tbl.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',  (0, 1), (-1, 1),  10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('ALIGN',       (2, 0), (2, -1),  'RIGHT'),
    ]))
    story.append(auth_tbl)
    story.append(Spacer(1, 3*mm))

    # ── Footer ────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.3, color=_BDR))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        'This is a system-generated Purchase Order. Prices are indicative based on last purchase history. '
        'Actual invoice may vary. All disputes subject to jurisdiction of registered office.',
        small
    ))

    doc.build(story)
    return buf.getvalue()
