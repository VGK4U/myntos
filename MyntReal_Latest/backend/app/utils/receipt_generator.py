"""
MNR Business Access Program - Payment Receipt Generator
DC Protocol (Feb 2026) - Redesigned attractive format with logo
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
from io import BytesIO
from datetime import datetime
import os

COMPANY = {
    "name": "Mega Natural Resources (MNR)",
    "gstin": "37CPFPM3863M1ZA",
    "address_line1": "Second Floor, D.No: 17-53/3, Veterinary Hospital Road,",
    "address_line2": "Sec-B, Behind KK Homes Apartment,",
    "address_line3": "Pendurthi Mandal, Visakhapatnam, Andhra Pradesh – 531173"
}

PROGRAM = {
    "name": "MNR Business Access Program",
    "tagline": "One Access. Multiple Business Opportunities."
}

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'mnr-logo.png')

def number_to_words(num):
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    
    if num == 0:
        return 'Zero'
    
    def words_below_hundred(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
    
    def words_below_thousand(n):
        if n < 100:
            return words_below_hundred(n)
        return ones[n // 100] + ' Hundred' + (' ' + words_below_hundred(n % 100) if n % 100 else '')
    
    if num < 1000:
        return words_below_thousand(num)
    elif num < 100000:
        return words_below_thousand(num // 1000) + ' Thousand' + (' ' + words_below_thousand(num % 1000) if num % 1000 else '')
    elif num < 10000000:
        return words_below_thousand(num // 100000) + ' Lakh' + (' ' + words_below_thousand((num % 100000) // 1000) + ' Thousand' if (num % 100000) >= 1000 else '') + (' ' + words_below_thousand(num % 1000) if num % 1000 else '')
    else:
        return str(num)



def generate_membership_receipt(data: dict) -> BytesIO:
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=18*mm, leftMargin=18*mm,
                           topMargin=14*mm, bottomMargin=14*mm)
    
    primary = colors.HexColor('#0b3c5d')
    secondary = colors.HexColor('#0f5132')
    dark = colors.HexColor('#1f2937')
    muted = colors.HexColor('#6b7280')
    border_color = colors.HexColor('#e5e7eb')
    label_bg = colors.HexColor('#f9fafb')
    card_bg = colors.HexColor('#ffffff')
    note_bg = colors.HexColor('#f0f9ff')
    
    page_width = 174*mm
    
    title_white = ParagraphStyle('TitleWhite', fontSize=18, textColor=colors.white, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=2, leading=22)
    subtitle_white = ParagraphStyle('SubtitleWhite', fontSize=12, textColor=colors.Color(1, 1, 1, 0.95), alignment=TA_CENTER, fontName='Helvetica', spaceAfter=2, leading=15)
    desc_white = ParagraphStyle('DescWhite', fontSize=10, textColor=colors.Color(1, 1, 1, 0.9), alignment=TA_CENTER, fontName='Helvetica-Oblique', leading=13)
    
    section_title = ParagraphStyle('SectionTitle', fontSize=11, textColor=primary, fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=2)
    
    cell_label = ParagraphStyle('CellLabel', fontSize=9, textColor=dark, fontName='Helvetica-Bold', leading=12)
    cell_value = ParagraphStyle('CellValue', fontSize=9, textColor=dark, leading=12)
    
    amount_large = ParagraphStyle('AmountLarge', fontSize=12, textColor=dark, fontName='Helvetica-Bold', leading=15)
    amount_words = ParagraphStyle('AmountWords', fontSize=9, textColor=dark, fontName='Helvetica-Bold', leading=12)
    
    bullet_style = ParagraphStyle('Bullet', fontSize=9, textColor=dark, leading=13, leftIndent=10, bulletIndent=0)
    bullet_bold = ParagraphStyle('BulletBold', fontSize=9, textColor=dark, leading=13, leftIndent=10, bulletIndent=0, fontName='Helvetica-Bold')
    
    note_style = ParagraphStyle('Note', fontSize=8, textColor=muted, leading=11, leftIndent=8)
    
    small_text = ParagraphStyle('Small', fontSize=8, textColor=dark, leading=11)
    small_bold = ParagraphStyle('SmallBold', fontSize=8, textColor=dark, fontName='Helvetica-Bold', leading=11)
    
    footer_style = ParagraphStyle('Footer', fontSize=8, textColor=muted, alignment=TA_CENTER, leading=11)
    
    member_name = data.get('member_name', 'N/A')
    mnr_id = data.get('mnr_id', 'N/A')
    payment_date = data.get('payment_date', datetime.now().strftime('%d/%m/%Y'))
    enrollment_date = data.get('activation_date', payment_date)
    total_amount = data.get('amount_paid', 15000)
    points = data.get('points_credited', 30000)
    receipt_no = data.get('receipt_number', f"MNR/RCPT/{mnr_id[-6:]}" if mnr_id != 'N/A' else f"MNR/RCPT/{datetime.now().strftime('%Y%m%d%H%M%S')}")
    payment_mode = data.get('payment_mode', 'UPI / Bank Transfer')
    expiry = data.get('expiry_date', '24 Months from Enrollment Date')
    
    elements = []
    
    def add_header_block():
        header_data = []
        
        logo_path = LOGO_PATH
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=50*mm, height=21*mm)
                logo.hAlign = 'CENTER'
                header_data.append([logo])
            except Exception:
                pass
        
        header_data.append([Paragraph(PROGRAM['name'], title_white)])
        header_data.append([Paragraph(PROGRAM['tagline'], subtitle_white)])
        header_data.append([Spacer(1, 4)])
        header_data.append([Paragraph("Payment Receipt – Program Access &amp; Services", desc_white)])
        
        t = Table(header_data, colWidths=[page_width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), primary),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 14),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))
    
    def add_card_section(title, table_data, col_widths, bg_colors=None):
        elements.append(Paragraph(title, section_title))
        elements.append(Spacer(1, 2))
        
        style_commands = [
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]
        
        for row_idx in range(len(table_data)):
            style_commands.append(('BACKGROUND', (0, row_idx), (0, row_idx), label_bg))
        
        if bg_colors:
            style_commands.extend(bg_colors)
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle(style_commands))
        elements.append(t)
        elements.append(Spacer(1, 10))
    
    add_header_block()
    
    company_data = [
        [Paragraph('Legal Entity', cell_label), Paragraph(COMPANY['name'], cell_value)],
        [Paragraph('GSTIN', cell_label), Paragraph(COMPANY['gstin'], cell_value)],
        [Paragraph('Registered Address', cell_label), Paragraph(
            f"{COMPANY['address_line1']}<br/>{COMPANY['address_line2']}<br/>{COMPANY['address_line3']}", cell_value)],
    ]
    add_card_section("Company Details", company_data, [40*mm, 134*mm])
    
    member_data = [
        [Paragraph('Member Name', cell_label), Paragraph(member_name, cell_value)],
        [Paragraph('MNR Member ID', cell_label), Paragraph(mnr_id, cell_value)],
        [Paragraph('Receipt Number', cell_label), Paragraph(receipt_no, cell_value)],
        [Paragraph('Payment Date', cell_label), Paragraph(payment_date, cell_value)],
        [Paragraph('Enrollment Date', cell_label), Paragraph(enrollment_date, cell_value)],
        [Paragraph('Mode of Payment', cell_label), Paragraph(payment_mode, cell_value)],
    ]
    add_card_section("Member Details", member_data, [40*mm, 134*mm])
    
    elements.append(Paragraph("Payment Summary", section_title))
    elements.append(Spacer(1, 2))
    
    payment_data = [
        [Paragraph('Program Access &amp; Digital Enablement Services', cell_label),
         Paragraph(f'<b>\u20b9{total_amount:,}</b>', amount_large)],
    ]
    t = Table(payment_data, colWidths=[120*mm, 54*mm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('BACKGROUND', (0, 0), (0, 0), label_bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(t)
    
    amount_text = f"Rupees {number_to_words(total_amount)} Only"
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"<b>Amount in Words:</b> {amount_text}", amount_words))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("Program Features (Non-Cash)", section_title))
    elements.append(Spacer(1, 2))
    insurance_items = [
        [Paragraph('<bullet>&bull;</bullet><b>Accidental Insurance Coverage:</b> Facilitated through an authorised insurance partner as a program feature.', bullet_style)],
        [Paragraph('<bullet>&bull;</bullet>The amount paid does <b>not</b> represent insurance premium value.', bullet_style)],
    ]
    t = Table(insurance_items, colWidths=[page_width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fdf4')),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    
    points_data = [
        [Paragraph('Welcome Coupon', cell_label), Paragraph('Issued (Onboarding Promotional)', cell_value)],
        [Paragraph('Reward Points Credited', cell_label), Paragraph(f'<b>{points:,} Points</b>', cell_value)],
        [Paragraph('Nature', cell_label), Paragraph('Promotional Utility Credits (Non-Cash)', cell_value)],
        [Paragraph('Validity', cell_label), Paragraph(expiry, cell_value)],
        [Paragraph('Usage', cell_label), Paragraph(
            'Redeemable only as discounts/adjustments against eligible services offered through MNR-authorised platforms and partners.', cell_value)],
        [Paragraph('Maximum Usable Benefit', cell_label), Paragraph(f'\u20b9{total_amount:,} (Overall Cap)', cell_value)],
    ]
    add_card_section("Welcome Coupon &amp; Reward Points", points_data, [42*mm, 132*mm])
    
    note_data = [
        [Paragraph('Reward points have no cash value, are non-transferable, non-withdrawable, and cannot be exchanged for money.', note_style)]
    ]
    t = Table(note_data, colWidths=[page_width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), note_bg),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("Important Declarations", section_title))
    elements.append(Spacer(1, 2))
    
    declarations = [
        "This receipt confirms payment towards program access and enablement only.",
        "No income, return, or benefit is guaranteed or implied.",
        "Earnings, if any, arise only from successful sale or delivery of real products or services.",
        "Reward points and insurance coverage are promotional program features.",
        f"All participation is governed by the {PROGRAM['name']} – Terms &amp; Conditions (Version 5.1).",
    ]
    decl_data = [[Paragraph(f'<bullet>&bull;</bullet>{d}', bullet_style)] for d in declarations]
    t = Table(decl_data, colWidths=[page_width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fefce8')),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("GST Declaration", section_title))
    elements.append(Spacer(1, 2))
    gst_text = "GST is not charged on this receipt as the transaction represents program access and facilitation services. No taxable supply of goods or services is involved at this stage."
    gst_data = [[Paragraph(gst_text, small_text)]]
    t = Table(gst_data, colWidths=[page_width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), label_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("Jurisdiction", section_title))
    elements.append(Spacer(1, 2))
    jurisdiction_data = [[Paragraph(
        'All disputes are subject to the jurisdiction of <b>Kothavalasa, Andhra Pradesh</b>.', small_text)]]
    t = Table(jurisdiction_data, colWidths=[page_width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), label_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))
    
    elements.append(HRFlowable(width="60%", thickness=0.5, color=border_color, spaceAfter=6, hAlign='CENTER'))
    elements.append(Paragraph("This is a system-generated receipt. No physical seal or signature required.", footer_style))
    elements.append(Paragraph(f"\u00a9 Mega Natural Resources – {PROGRAM['name']}", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_sample_receipt(mnr_id: str = "MNR182313597"):
    return generate_membership_receipt({
        "member_name": "Sample Member",
        "mnr_id": mnr_id,
        "payment_date": "05/02/2026",
        "activation_date": "05/02/2026",
        "amount_paid": 15000,
        "points_credited": 30000,
        "receipt_number": f"MNR/RCPT/{mnr_id[-6:]}",
        "expiry_date": "24 Months from Enrollment Date",
        "payment_mode": "UPI",
        "transaction_ref": "N/A"
    })


VGK_COMPANY = {
    "legal_name":   "Lucky Enterprises",
    "proprietor":   "Aruna Kari",
    "brand":        "VGK4U Platform",
    "gstin":        "37ISOPK9135A1ZF",
    "address_line1":"D No 1-1, Desapatrunipalem Main Road",
    "address_line2":"Kothavalasa, Vizianagaram",
    "address_line3":"Andhra Pradesh – 535183",
    "state_code":   "37",
}
VGK_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'vgk4u-logo-pdf.png')

FIXED_TAXABLE  = 4237.29
FIXED_CGST     = 381.36
FIXED_SGST     = 381.36
FIXED_TOTAL    = 5000.00
SAC_CODE       = "998314"


def generate_vgk_receipt(data: dict) -> BytesIO:
    """Generate VGK GST Tax Invoice — Partner Platform Activation (Lucky Enterprises)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=10*mm, bottomMargin=10*mm)

    # ── Colours ───────────────────────────────────────────────────────────────
    purple      = colors.HexColor('#4c1d95')
    purple_mid  = colors.HexColor('#7c3aed')
    dark        = colors.HexColor('#1f2937')
    muted       = colors.HexColor('#6b7280')
    border_c    = colors.HexColor('#e5e7eb')
    label_bg    = colors.HexColor('#f9fafb')
    note_bg     = colors.HexColor('#f5f3ff')
    green_bg    = colors.HexColor('#f0fdf4')
    green_dark  = colors.HexColor('#15803d')
    amber_bg    = colors.HexColor('#fffbeb')

    PW = 174*mm   # usable page width

    # ── Styles ────────────────────────────────────────────────────────────────
    def ST(name, **kw):
        return ParagraphStyle(name, **kw)

    WH18B = ST('WH18B', fontSize=18, textColor=colors.white, alignment=TA_CENTER,
               fontName='Helvetica-Bold', leading=22)
    WH12  = ST('WH12',  fontSize=12, textColor=colors.Color(1,1,1,.95), alignment=TA_CENTER,
               fontName='Helvetica', leading=15)
    WH10I = ST('WH10I', fontSize=10, textColor=colors.Color(1,1,1,.90), alignment=TA_CENTER,
               fontName='Helvetica-Oblique', leading=13)
    WH9B  = ST('WH9B',  fontSize=9,  textColor=colors.white, fontName='Helvetica-Bold',
               alignment=TA_CENTER, leading=12)
    WH8   = ST('WH8',   fontSize=8,  textColor=colors.Color(1,1,1,.85), alignment=TA_CENTER,
               leading=11)

    SEC   = ST('SEC',   fontSize=11, textColor=purple, fontName='Helvetica-Bold',
               spaceAfter=3, spaceBefore=6)
    LBL   = ST('LBL',   fontSize=8,  textColor=dark, fontName='Helvetica-Bold', leading=11)
    VAL   = ST('VAL',   fontSize=8,  textColor=dark, leading=11)
    LBLC  = ST('LBLC',  fontSize=8,  textColor=dark, fontName='Helvetica-Bold',
               leading=11, alignment=TA_CENTER)
    VALC  = ST('VALC',  fontSize=8,  textColor=dark, leading=11, alignment=TA_CENTER)
    VALR  = ST('VALR',  fontSize=8,  textColor=dark, leading=11, alignment=TA_RIGHT)
    LBGR  = ST('LBGR',  fontSize=9,  textColor=green_dark, fontName='Helvetica-Bold',
               leading=12, alignment=TA_RIGHT)
    AMT   = ST('AMT',   fontSize=13, textColor=purple, fontName='Helvetica-Bold', leading=16)
    AMW   = ST('AMW',   fontSize=9,  textColor=dark, fontName='Helvetica-Bold', leading=12)
    DISC  = ST('DISC',  fontSize=7.5, textColor=muted, leading=11, alignment=TA_LEFT)
    FTR   = ST('FTR',   fontSize=7.5, textColor=muted, alignment=TA_CENTER, leading=11)

    G_TS = [
        ('GRID',          (0,0), (-1,-1), 0.5, border_c),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
    ]

    def kv_tbl(rows, c1=42*mm):
        cmds = list(G_TS)
        for i in range(len(rows)):
            cmds.append(('BACKGROUND', (0,i), (0,i), label_bg))
        t = Table(rows, colWidths=[c1, PW-c1])
        t.setStyle(TableStyle(cmds))
        return t

    def note_tbl(text, bg=note_bg):
        t = Table([[Paragraph(text, DISC)]], colWidths=[PW])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), bg),
            ('BOX',           (0,0), (-1,-1), 0.5, border_c),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
            ('RIGHTPADDING',  (0,0), (-1,-1), 10),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    # ── Extract data ──────────────────────────────────────────────────────────
    member_name     = data.get('member_name', 'N/A')
    vgk_id          = data.get('vgk_id', 'N/A')
    phone           = data.get('phone', 'N/A')
    email           = data.get('email', 'N/A')
    role            = data.get('role', 'VGK Associate')
    join_date       = data.get('join_date', 'N/A')
    activation_date = data.get('activation_date', 'N/A')
    points          = int(data.get('points_credited', 51000))
    receipt_no      = data.get('receipt_number', f"VGK-INV-{vgk_id[-6:]}")
    generated_on    = data.get('generated_on', datetime.now().strftime('%d %B %Y, %I:%M %p'))

    elements = []

    # ════════════════════════════════════════════════════════════════════════
    # HEADER — VGK4U branding + invoice title
    # ════════════════════════════════════════════════════════════════════════
    hdr_rows = []
    if os.path.exists(VGK_LOGO_PATH):
        try:
            logo = Image(VGK_LOGO_PATH, width=55*mm, height=22*mm)
            logo.hAlign = 'CENTER'
            hdr_rows.append([logo])
        except Exception:
            pass
    hdr_rows += [
        [Spacer(1, 3)],
        [Paragraph('TAX INVOICE', ST('INV_T', fontSize=13, textColor=colors.white,
                                     fontName='Helvetica-Bold', alignment=TA_CENTER, leading=16))],
        [Paragraph('Partner Platform Activation', WH10I)],
        [Spacer(1, 4)],
        [Paragraph('Powered by Lucky Enterprises (GST Registered)', WH8)],
    ]
    ht = Table(hdr_rows, colWidths=[PW])
    ht.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), purple),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,0),  14),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 12),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
    ]))
    elements += [ht, Spacer(1, 6)]

    # ════════════════════════════════════════════════════════════════════════
    # SUPPLIER DETAILS  (left) | MEMBER DETAILS (right) — side-by-side
    # ════════════════════════════════════════════════════════════════════════
    addr_str = (f"{VGK_COMPANY['address_line1']},<br/>"
                f"{VGK_COMPANY['address_line2']},<br/>"
                f"{VGK_COMPANY['address_line3']}")

    sup_rows = [
        [Paragraph('<b>Supplier Details</b>', ST('SH', fontSize=9, textColor=purple,
                                                  fontName='Helvetica-Bold', leading=12))],
        [Paragraph(f"<b>Lucky Enterprises</b>", VAL)],
        [Paragraph(f"Operator Brand: VGK4U Platform", VAL)],
        [Paragraph(f"GSTIN: {VGK_COMPANY['gstin']}", VAL)],
        [Paragraph(addr_str, VAL)],
        [Paragraph(f"State Code: {VGK_COMPANY['state_code']} — Andhra Pradesh", VAL)],
    ]
    sup_t = Table(sup_rows, colWidths=[85*mm])
    sup_t.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, border_c),
        ('BACKGROUND',    (0,0), (-1,0),  label_bg),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 7),
        ('RIGHTPADDING',  (0,0), (-1,-1), 7),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, border_c),
    ]))

    mem_rows = [
        [Paragraph('<b>Member Details</b>', ST('MH', fontSize=9, textColor=purple,
                                               fontName='Helvetica-Bold', leading=12))],
        [Paragraph(f"<b>{member_name}</b>", VAL)],
        [Paragraph(f"VGK ID: {vgk_id}", VAL)],
        [Paragraph(f"Role: {role}", VAL)],
        [Paragraph(f"Phone: {phone}", VAL)],
        [Paragraph(f"Email: {email}", VAL)],
    ]
    mem_t = Table(mem_rows, colWidths=[84*mm])
    mem_t.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, border_c),
        ('BACKGROUND',    (0,0), (-1,0),  label_bg),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 7),
        ('RIGHTPADDING',  (0,0), (-1,-1), 7),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, border_c),
    ]))

    two_col = Table([[sup_t, mem_t]], colWidths=[85*mm, 89*mm])
    two_col.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('COLPADDING',    (0,0), (-1,-1), 5),
    ]))
    elements += [two_col, Spacer(1, 6)]

    # ════════════════════════════════════════════════════════════════════════
    # INVOICE INFORMATION
    # ════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("Invoice Information", SEC))
    inv_rows = [
        [Paragraph('Receipt / Invoice No.', LBL), Paragraph(receipt_no, VAL),
         Paragraph('Enrollment Date', LBL),        Paragraph(join_date, VAL)],
        [Paragraph('Activation Date', LBL),         Paragraph(activation_date, VAL),
         Paragraph('Invoice Generated On', LBL),    Paragraph(generated_on, VAL)],
        [Paragraph('Place of Supply', LBL),          Paragraph('Andhra Pradesh (State Code: 37)', VAL),
         Paragraph('Reverse Charge', LBL),           Paragraph('No', VAL)],
    ]
    inv_t = Table(inv_rows, colWidths=[38*mm, 49*mm, 38*mm, 49*mm])
    inv_t.setStyle(TableStyle(G_TS + [
        ('BACKGROUND', (0,0), (0,-1), label_bg),
        ('BACKGROUND', (2,0), (2,-1), label_bg),
    ]))
    elements += [inv_t, Spacer(1, 6)]

    # ════════════════════════════════════════════════════════════════════════
    # LINE ITEM TABLE
    # ════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("Tax Invoice — Partner Platform Activation Fee", SEC))
    li_hdr_bg = [('BACKGROUND', (0,0), (-1,0), purple),
                 ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                 ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                 ('BACKGROUND', (0,2), (-1,2), green_bg)]
    li_data = [
        [Paragraph('Description', WH9B), Paragraph('SAC', WH9B),
         Paragraph('Taxable Value', WH9B), Paragraph('CGST @ 9%', WH9B),
         Paragraph('SGST @ 9%', WH9B), Paragraph('Total Amount', WH9B)],
        [Paragraph('VGK4U Partner Platform Access &amp; Activation Fee', VAL),
         Paragraph(SAC_CODE, VALC),
         Paragraph(f'\u20b9{FIXED_TAXABLE:,.2f}', VALR),
         Paragraph(f'\u20b9{FIXED_CGST:,.2f}', VALR),
         Paragraph(f'\u20b9{FIXED_SGST:,.2f}', VALR),
         Paragraph(f'\u20b9{FIXED_TOTAL:,.2f}', VALR)],
        [Paragraph('<b>Total</b>', LBL), Paragraph('', VAL),
         Paragraph(f'<b>\u20b9{FIXED_TAXABLE:,.2f}</b>', LBGR),
         Paragraph(f'<b>\u20b9{FIXED_CGST:,.2f}</b>', LBGR),
         Paragraph(f'<b>\u20b9{FIXED_SGST:,.2f}</b>', LBGR),
         Paragraph(f'<b>\u20b9{FIXED_TOTAL:,.2f}</b>',
                   ST('GT', fontSize=10, textColor=green_dark, fontName='Helvetica-Bold',
                      leading=13, alignment=TA_RIGHT))],
    ]
    li_t = Table(li_data, colWidths=[56*mm, 16*mm, 28*mm, 25*mm, 25*mm, 24*mm])
    li_t.setStyle(TableStyle(G_TS + li_hdr_bg + [
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
    ]))
    elements += [li_t, Spacer(1, 4)]

    # Amount in words
    elements.append(Paragraph(
        '<b>Amount in Words:</b> Rupees Five Thousand Only', AMW))
    elements.append(Spacer(1, 6))

    # ════════════════════════════════════════════════════════════════════════
    # GST SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("GST Summary", SEC))
    gst_data = [
        [Paragraph('Total Taxable Value', LBL), Paragraph(f'\u20b9{FIXED_TAXABLE:,.2f}', VALR)],
        [Paragraph('CGST @ 9%', LBL),           Paragraph(f'\u20b9{FIXED_CGST:,.2f}', VALR)],
        [Paragraph('SGST @ 9%', LBL),           Paragraph(f'\u20b9{FIXED_SGST:,.2f}', VALR)],
        [Paragraph('<b>Grand Total</b>', ST('GT2', fontSize=9, textColor=green_dark,
                                             fontName='Helvetica-Bold', leading=12)),
         Paragraph(f'<b>\u20b9{FIXED_TOTAL:,.2f}</b>',
                   ST('GT3', fontSize=10, textColor=green_dark, fontName='Helvetica-Bold',
                      leading=13, alignment=TA_RIGHT))],
    ]
    gst_t = Table(gst_data, colWidths=[PW - 50*mm, 50*mm])
    gst_t.setStyle(TableStyle(G_TS + [
        ('BACKGROUND', (0,0), (0,-2), label_bg),
        ('BACKGROUND', (0,-1), (-1,-1), green_bg),
    ]))
    gst_wrap = Table([[Paragraph('', VAL), gst_t]], colWidths=[PW - 95*mm, 95*mm])
    gst_wrap.setStyle(TableStyle([
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
    ]))
    elements += [gst_wrap, Spacer(1, 6)]

    # ════════════════════════════════════════════════════════════════════════
    # POINTS CREDITED
    # ════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("Platform Credits on Activation", SEC))
    pts_data = [
        [Paragraph('VGK Welcome Bonus', LBL),            Paragraph('1,000 Points', VAL)],
        [Paragraph('VGK Activation Bonus', LBL),         Paragraph('50,000 Points', VAL)],
        [Paragraph('<b>Total Points Credited</b>', LBL), Paragraph(f'<b>{points:,} Points</b>', AMT)],
    ]
    pts_t = Table(pts_data, colWidths=[80*mm, PW - 80*mm])
    pts_t.setStyle(TableStyle(G_TS + [
        ('BACKGROUND', (0,0), (0,-1), label_bg),
        ('BACKGROUND', (0,2), (-1,2), note_bg),
    ]))
    elements += [pts_t, Spacer(1, 5)]

    # ════════════════════════════════════════════════════════════════════════
    # LEGAL DISCLAIMER
    # ════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("Legal Disclaimer", SEC))
    disclaimer_paras = [
        ("VGK4U is a partner enablement platform operated by Lucky Enterprises that allows registered "
         "partners to source and facilitate deals across various product and service categories including "
         "electric vehicles, insurance, real estate, marketplace goods, and training services."),
        ("Partner Platform Activation provides access to the digital platform tools, partner dashboard, "
         "onboarding resources, and deal sourcing system. Activation does not constitute an investment, "
         "deposit scheme, or guaranteed income program."),
        ("Any income or commissions earned by partners depend solely on successful deal sourcing, confirmed "
         "transactions, and applicable commission configurations. The company does not guarantee earnings or returns."),
        ("VGK Coupons represent internal activation tokens used within the VGK4U system to activate partner "
         "accounts. Coupons do not represent monetary instruments, securities, or financial investments."),
        ("VGK Points are promotional utility credits issued within the platform ecosystem. They are non-cash, "
         "non-transferable, non-withdrawable and may only be used as discounts or benefits on eligible products "
         "and services available on the VGK4U platform."),
        ("Activation fees are non-refundable once the partner account has been activated and access to the "
         "digital platform has been granted."),
    ]
    disc_rows = [[Paragraph(f"\u2022  {t}", DISC)] for t in disclaimer_paras]
    disc_t = Table(disc_rows, colWidths=[PW])
    disc_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), amber_bg),
        ('BOX',           (0,0), (-1,-1), 0.5, border_c),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, border_c),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
    ]))
    elements += [disc_t, Spacer(1, 10)]

    # ════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════════════════════════════
    elements.append(HRFlowable(width="100%", thickness=0.5, color=border_c, spaceAfter=5))
    elements.append(Paragraph(
        f"This is a system-generated tax invoice issued by <b>Lucky Enterprises</b> "
        f"(GSTIN: {VGK_COMPANY['gstin']}).  No physical signature is required.",
        FTR))
    elements.append(Paragraph(
        f"Lucky Enterprises — Operator of VGK4U Platform  |  {VGK_COMPANY['address_line2']}, "
        f"{VGK_COMPANY['address_line3']}",
        FTR))

    doc.build(elements)
    buffer.seek(0)
    return buffer
