"""
Solar Document Generator Service
DC Protocol (Apr 2026): Generates all 7 solar document types using ReportLab.

Documents:
  1. Quotation (attractive letterhead + partner logos footer)
  2. Annexure-A (Undertaking / Self-Declaration for domestic content)
  3. Annexure-C Completion (Project Completion Report)
  4. Annexure-C Technical (Technical Installation Details)
  5. Commissioning Test Report
  6. Synchronisation Certificate
  7. Annexure-IV Work Completion Report
"""
import os
import logging
from io import BytesIO
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# ── DC_PDF_IMG_COMPRESS_001: Compress images to display size before embedding ─
# Without this, a 1.5 MB PNG logo embedded at 28 mm × 12 mm still carries its
# full ~1.5 MB payload inside the PDF.  We resize to the actual display pixel
# dimensions at 150 DPI and re-encode as JPEG at quality=82, which keeps logos
# crisp on screen while slashing each image to < 15 KB.
def _compress_img_bytes(img_bytes: bytes, w_mm: float, h_mm: float,
                         dpi: int = 150, quality: int = 82) -> bytes:
    """
    Resize img_bytes to the pixel dimensions implied by (w_mm × h_mm) at `dpi`
    and re-encode as JPEG.  Transparent PNGs are composited over white first.
    Returns compressed bytes, or the original bytes on any Pillow failure.
    """
    try:
        from PIL import Image as _PILImage
        px_w = max(1, int(round(w_mm * dpi / 25.4)))
        px_h = max(1, int(round(h_mm * dpi / 25.4)))
        img = _PILImage.open(BytesIO(img_bytes))
        # Handle transparency (RGBA / P mode) → composite on white
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
            bg = _PILImage.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        else:
            img = img.convert('RGB')
        img = img.resize((px_w, px_h), _PILImage.LANCZOS)
        out = BytesIO()
        img.save(out, format='JPEG', quality=quality, optimize=True)
        return out.getvalue()
    except Exception as _e:
        logger.debug("[DC_PDF_IMG_COMPRESS_001] Pillow compress failed, using raw bytes: %s", _e)
        return img_bytes


# ── Logo paths (copied to frontend/public, served by backend via /static or direct path) ──
_BASE = os.path.dirname(os.path.abspath(__file__))
_LOGO_DIR = os.path.join(_BASE, '..', '..', '..', 'frontend', 'public')
LOGO_MYNTREAL = os.path.join(_LOGO_DIR, 'solar-logo-myntreal.png')
LOGO_MNR = os.path.join(_LOGO_DIR, 'solar-logo-mnr.png')
LOGO_VGK4U = os.path.join(_LOGO_DIR, 'solar-logo-vgk4u.png')
LOGO_HARGHAR = os.path.join(_LOGO_DIR, 'solar-logo-harghar.jpg')

# ── Brand colours ─────────────────────────────────────────────────────────────
NAVY = colors.HexColor('#0f2440')
NAVY_LIGHT = colors.HexColor('#1e3a5f')
ORANGE = colors.HexColor('#e55a2b')
GOLD = colors.HexColor('#f59e0b')
GREEN = colors.HexColor('#166534')
GREY_LIGHT = colors.HexColor('#f1f5f9')
GREY_BORDER = colors.HexColor('#cbd5e1')
WHITE = colors.white
BLACK = colors.black

A4_W, A4_H = A4


def _doc(buf, top=18*mm, bottom=20*mm, left=15*mm, right=15*mm):
    return SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=top, bottomMargin=bottom,
        leftMargin=left, rightMargin=right
    )


def _styles():
    ss = getSampleStyleSheet()

    def _add(name, **kw):
        if name not in ss:
            ss.add(ParagraphStyle(name=name, **kw))
        return ss[name]

    _add('VendorName', fontName='Helvetica-Bold', fontSize=16, textColor=NAVY,
         spaceAfter=2, alignment=TA_LEFT)
    _add('VendorSub', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#334155'),
         spaceAfter=1, alignment=TA_LEFT, leading=12)
    _add('SectionTitle', fontName='Helvetica-Bold', fontSize=10, textColor=WHITE,
         spaceAfter=4, alignment=TA_LEFT)
    _add('BodySmall', fontName='Helvetica', fontSize=9, textColor=BLACK,
         spaceAfter=2, leading=13)
    _add('BodySmallBold', fontName='Helvetica-Bold', fontSize=9, textColor=BLACK,
         spaceAfter=2, leading=13)
    _add('CellBody', fontName='Helvetica', fontSize=8.5, textColor=BLACK, leading=12)
    _add('CellBold', fontName='Helvetica-Bold', fontSize=8.5, textColor=BLACK, leading=12)
    _add('DocTitle', fontName='Helvetica-Bold', fontSize=13, textColor=NAVY,
         spaceAfter=6, alignment=TA_CENTER)
    _add('FooterTiny', fontName='Helvetica', fontSize=7, textColor=colors.HexColor('#64748b'),
         alignment=TA_CENTER, leading=10)
    _add('RedNote', fontName='Helvetica-BoldOblique', fontSize=8, textColor=ORANGE,
         alignment=TA_CENTER)
    _add('TableHeader', fontName='Helvetica-Bold', fontSize=8.5, textColor=WHITE)
    _add('CGNote', fontName='Helvetica-Oblique', fontSize=7.5,
         textColor=colors.HexColor('#888888'), alignment=TA_CENTER, leading=10)
    return ss


def _rl_image(path, w, h):
    """Return an RLImage if the file exists and is readable, else a spacer.
    DC Protocol: Pre-reads file bytes into BytesIO so any I/O error is caught
    here (inside try-except) rather than lazily during doc.build().
    DC_PDF_IMG_COMPRESS_001: images are resized to display dimensions before
    embedding so large logo PNGs don't bloat the PDF.
    """
    if path and os.path.isfile(path):
        try:
            from io import BytesIO as _BytesIO
            with open(path, 'rb') as _f:
                _img_bytes = _f.read()
            # Convert ReportLab units (points) → mm for the compressor
            _w_mm = w / mm
            _h_mm = h / mm
            _img_bytes = _compress_img_bytes(_img_bytes, _w_mm, _h_mm)
            return RLImage(_BytesIO(_img_bytes), width=w, height=h)
        except Exception:
            pass
    return Spacer(w, h)


def _norm_kw(kw_str) -> str:
    """
    DC Protocol (Apr 2026): Ensure kw string always has 'KW' suffix.
    '3' → '3KW', '3KW' → '3KW', '3kw' → '3KW', '3 KW' → '3KW'
    """
    if not kw_str:
        return '3KW'
    s = str(kw_str).strip().upper().replace(' ', '')
    if s.endswith('KW'):
        return s
    import re as _re
    if _re.search(r'\d', s):
        return s + 'KW'
    return s or '3KW'


def _valid_kw_val(val, fallback_kw: str = '3KW') -> str:
    """
    DC Protocol (Apr 2026): Return val if it looks like a valid kW reading (contains a digit),
    else return normalised fallback_kw. Prevents garbage tech-DB values appearing in PDFs.
    """
    import re as _re
    if val and _re.search(r'\d', str(val)):
        return str(val).strip()
    return _norm_kw(fallback_kw)


def _kv_table(rows, col_widths=None, stripe=True):
    """Key-value 2-column table, navy header stripe on even rows."""
    if col_widths is None:
        col_widths = [60*mm, 105*mm]
    ss = _styles()
    data = []
    for k, v in rows:
        data.append([
            Paragraph(str(k), ss['CellBold']),
            Paragraph(str(v) if v is not None else '—', ss['CellBody'])
        ])
    t = Table(data, colWidths=col_widths, repeatRows=0)
    style = [
        ('GRID', (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
    ]
    t.setStyle(TableStyle(style))
    return t


def _section_header(text):
    """A navy band with white text acting as a section divider."""
    ss = _styles()
    t = Table([[Paragraph(text, ss['SectionTitle'])]], colWidths=[A4_W - 30*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


def _partner_logos_footer(logo_h=12*mm):
    """Horizontal strip of 4 partner logos for quotation footer."""
    logos = [
        (LOGO_MYNTREAL, 42*mm, logo_h),
        (LOGO_HARGHAR, 42*mm, logo_h),
        (LOGO_MNR, 32*mm, logo_h),
        (LOGO_VGK4U, 28*mm, logo_h),
    ]
    cells = [_rl_image(p, w, h) for p, w, h in logos]
    t = Table([cells], colWidths=[42*mm, 42*mm, 32*mm, 28*mm])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 0), (-1, 0), 1, GREY_BORDER),
    ]))
    return t


def _fetch_url_image(url: str, width=38*mm, height=24*mm):
    """
    DC Fix (Apr 2026): Download an image from a URL and return an RLImage.
    Returns None silently on any failure (missing URL, network error, bad image).
    Used to embed vendor stamp and tech-signature images in PDFs.

    Supports two modes:
    - Full https:// URL → fetched via HTTP
    - /storage/<key>   → fetched directly from object storage (no HTTP round-trip)

    DC_PDF_IMG_COMPRESS_001: downloaded bytes are resized to display dimensions
    before embedding so vendor stamps/logos never bloat the PDF.
    """
    if not url or not str(url).strip():
        return None
    url = str(url).strip()
    _w_mm = width / mm
    _h_mm = height / mm
    try:
        # Internal object-storage path — read directly without HTTP
        if url.startswith('/storage/'):
            storage_key = url[len('/storage/'):]
            from app.services.object_storage import storage_service
            _data = storage_service.download_file(storage_key)
            if not _data:
                # Fallback: check local frontend/storage directory
                from pathlib import Path as _Path
                _local = _Path(__file__).parent.parent.parent.parent / "frontend" / "storage" / storage_key
                if _local.exists():
                    _data = _local.read_bytes()
            if not _data:
                return None
            _data = _compress_img_bytes(_data, _w_mm, _h_mm)
            return RLImage(BytesIO(_data), width=width, height=height)
        # External URL → HTTP fetch
        import urllib.request as _urlreq
        _req = _urlreq.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _urlreq.urlopen(_req, timeout=8) as _resp:
            _data = _resp.read()
        if not _data:
            return None
        _data = _compress_img_bytes(_data, _w_mm, _h_mm)
        return RLImage(BytesIO(_data), width=width, height=height)
    except Exception as _e:
        logger.warning("[DC-SOLAR] Could not load stamp/signature image from %s: %s", url, _e)
        return None


def _computer_generated_note(ss):
    """Centred italic grey line: 'This is a Computer Generated Document'."""
    return Paragraph('This is a Computer Generated Document', ss['CGNote'])


def _sig_stamp_table(ss, sig_img, stamp_img, sig_label='Authorised Signatory'):
    """
    Returns a Table that places the signature (left) and round stamp (right)
    side-by-side. Stamp uses square 30×30 mm so circular seals stay round.
    """
    sig_cell = [Paragraph(f'<b>{sig_label}</b>', ss['BodySmall'])]
    if sig_img:
        sig_cell += [Spacer(1, 1*mm), sig_img]
    else:
        sig_cell.append(Spacer(1, 16*mm))

    stamp_cell = [Paragraph('<b>Stamp</b>', ss['BodySmall'])]
    if stamp_img:
        stamp_cell += [Spacer(1, 1*mm), stamp_img]
    else:
        stamp_cell.append(Spacer(1, 24*mm))

    t = Table([[sig_cell, stamp_cell]], colWidths=[115*mm, 65*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN',   (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _vendor_letterhead(vendor: dict, ss):
    """
    Attractive letterhead block with optional vendor logo.
    If vendor_logo_url is set: [Logo | Vendor Name+Address | Contact Info]
    Otherwise: [Vendor Name+Address | Contact Info]
    """
    name = vendor.get('vendor_name', '')
    gst = vendor.get('gst_number', '')
    phone = vendor.get('phone', '')
    email = vendor.get('email', '')
    addr = vendor.get('address', '')
    city = vendor.get('city', '')
    state = vendor.get('state', '')
    pincode = vendor.get('pincode', '')
    mnre = vendor.get('mnre_empanelled', False)
    mnre_no = vendor.get('mnre_reg_no', '')
    logo_url = vendor.get('vendor_logo_url', '') or ''

    addr_str = ', '.join(filter(None, [addr, city, state, pincode]))

    # Try to fetch vendor logo
    logo_img = _fetch_url_image(logo_url, width=28*mm, height=28*mm) if logo_url else None

    left_cells = [
        Paragraph(name, ss['VendorName']),
        Spacer(1, 1.5*mm),
        Paragraph(addr_str, ss['VendorSub']),
        Paragraph(f'GSTIN: {gst}' if gst else '', ss['VendorSub']),
    ]
    right_lines = []
    if phone:
        right_lines.append(f'Ph: {phone}')
    if email:
        right_lines.append(f'E-mail: {email}')
    if mnre:
        right_lines.append('<font color="#166534"><b>✔ MNRE Empanelled Vendor</b></font>')
        if mnre_no:
            right_lines.append(f'Reg: {mnre_no}')

    right_cells = [Paragraph(l, ss['VendorSub']) for l in right_lines]

    right_col = [Spacer(1, 2)] + right_cells

    if logo_img:
        # Three-column: [Logo | Vendor details | Contact]
        text_col = [Spacer(1, 2)] + left_cells
        header_data = [[logo_img, text_col, right_col]]
        header_t = Table(header_data, colWidths=[32*mm, 90*mm, 53*mm])
        header_t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('VALIGN', (1, 0), (2, 0), 'TOP'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef4fb')),
            ('BOX', (0, 0), (-1, -1), 1.2, NAVY),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 3, NAVY),
        ]))
    else:
        # Two-column: [Vendor details | Contact]
        left_col = [Spacer(1, 2)] + left_cells
        header_data = [[left_col, right_col]]
        header_t = Table(header_data, colWidths=[110*mm, 65*mm])
        header_t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef4fb')),
            ('BOX', (0, 0), (-1, -1), 1.2, NAVY),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 3, NAVY),
        ]))
    return header_t


# ══════════════════════════════════════════════════════════════════════════════
#  1. QUOTATION
# ══════════════════════════════════════════════════════════════════════════════
def generate_quotation(
    lead: dict, vendor: dict,
    kw_size: str, quote_value: float, discount: float,
    final_amount: float, subsidy_amount: float,
    ref_no: str, quote_date=None,
    panel_brand: str = "",
) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, top=12*mm, bottom=5*mm)  # tighter margins to fit 1 page
    ss = _styles()
    story = []

    # Compact mode: MNRE empanelled vendors add ~6-8mm extra content; tighten
    # spacers and logos so everything still fits on one page. Zero impact on
    # standard (non-MNRE) vendors — those use the normal 1mm/1.5mm values.
    compact = bool(vendor.get('mnre_empanelled'))
    sp    = 0.5*mm if compact else 1*mm    # minor spacers throughout
    sp_lg = 1*mm   if compact else 1.5*mm  # slightly larger spacer (customer block)
    _logo_h = 10*mm if compact else 12*mm  # partner footer logo height

    # Normalise kw_size: "3" → "3KW", "3kw" → "3KW", "3.5kW" → "3.5KW"
    import re as _re
    _ks = (kw_size or '').strip()
    _m = _re.match(r'^([\d.]+)\s*[kK][wW]$', _ks)
    if _m:
        kw_size = _m.group(1) + 'KW'
    elif _re.match(r'^[\d.]+$', _ks):
        kw_size = _ks + 'KW'
    else:
        kw_size = _ks or '3KW'

    # Letterhead
    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, sp))

    # Ref + Date row
    ref_date = quote_date or date.today()
    date_str = ref_date.strftime('%d-%m-%Y') if hasattr(ref_date, 'strftime') else str(ref_date)
    ref_data = [
        [Paragraph(f'Ref: {ref_no}', ss['BodySmallBold']),
         Paragraph(f'Date: {date_str}', ss['BodySmallBold'])]
    ]
    rt = Table(ref_data, colWidths=[110*mm, 65*mm])
    rt.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(rt)
    story.append(Spacer(1, sp))

    # Customer address block
    cust_name = lead.get('customer_name') or lead.get('name', '')
    cust_addr = lead.get('address', '')
    cust_city = lead.get('city', '') or ''
    cust_state = lead.get('state', '') or ''
    app_no = lead.get('sc_number', '')

    story.append(Paragraph('To,', ss['BodySmall']))
    story.append(Paragraph(f'<b>{cust_name}</b>', ss['BodySmall']))
    if cust_addr:
        story.append(Paragraph(cust_addr, ss['BodySmall']))
    addr2 = ', '.join(filter(None, [cust_city, cust_state]))
    if addr2:
        story.append(Paragraph(addr2, ss['BodySmall']))
    if app_no:
        story.append(Paragraph(f'S.No. {app_no}', ss['BodySmall']))
    story.append(Spacer(1, sp_lg))

    # Title
    story.append(Paragraph(
        f'Estimation for Supply of <b>{kw_size} Solar Power Generating System (SPGS)</b>'
        f' - On-grid for Net meter',
        ss['DocTitle']
    ))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, sp))

    # System Description + Pricing side by side
    # DC-SOLAR-PANEL-BRAND-001: brand from modal param takes priority;
    # fallback to vendor default; never show a hardcoded placeholder.
    if not panel_brand.strip():
        panel_brand = vendor.get('panel_make_default', '') or ''
    if panel_brand.strip().upper() == 'DCR SOLAR PANEL':
        panel_brand = ''
    inv_make = vendor.get('inverter_make_default', '') or f'{kw_size.replace("KW","").replace("kw","").strip()}kVa Grid Tie Solar Inverter (IEC/BIS Approved)'
    discom = (lead.get('discom') or 'APEPDCL').strip() or 'APEPDCL'
    grid_phase = lead.get('grid_phase', 'Single Phase') or 'Single Phase'
    # "Single Phase" → "1", "Three Phase" → "3"
    phase_code = '3' if '3' in str(grid_phase) or 'three' in str(grid_phase).lower() else '1'
    sanction_load = lead.get('kw_size') or kw_size  # prefer DB value; fallback to modal input

    panel_watt = kw_size.replace('KW', '000W').replace('kw', '000W')

    _brand_line = (f'&nbsp;&nbsp;&nbsp;{panel_brand}<br/>' if panel_brand.strip() else '')
    desc_lines = [
        f'<b>Solar Panel:</b> {panel_watt}<br/>'
        f'{_brand_line}'
        f'&nbsp;&nbsp;&nbsp;DCR Solar Panel',
        '',
        f'<b>Solar Inverter:</b> {inv_make}',
        '',
        '<b>Accessories:</b> 4Sq. Copper AC Cable,<br/>'
        '&nbsp;&nbsp;&nbsp;4Sq. Copper DC cable<br/>'
        '&nbsp;&nbsp;&nbsp;GI Mounting Structure<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(North Pole&#8211;6 Feet, South Pole&#8211;4 Feet)<br/>'
        '&nbsp;&nbsp;&nbsp;AC-DCDB, Earthing,<br/>'
        '&nbsp;&nbsp;&nbsp;1" PVC Pipe, Flexible PVC Pipe<br/>'
        '&nbsp;&nbsp;&nbsp;GI/SS Nuts, Bolts &amp; Hardware',
    ]
    desc_para = Paragraph('<br/>'.join(desc_lines), ss['BodySmall'])

    # Price table (right column) — use "Rs." because Helvetica cannot render ₹ (U+20B9)
    def _fmt(v):
        try:
            return f'Rs.{float(v):,.2f}'
        except Exception:
            return str(v)

    price_rows = [
        ['Price (Including GST)', _fmt(quote_value)],
        ['Discount', _fmt(discount) if discount else '—'],
        ['Final Amount', _fmt(final_amount)],
        ['Application Charge', 'Actuals'],
        ['Net Meters Cost', f'Actuals\n(Estimating given by {discom})'],
        ['MNRE SRT National Solar Portal Subsidy', _fmt(subsidy_amount)],
    ]

    # price_t must fit inside body_t's right cell (100mm) — 62+36=98mm leaves 2mm breathing room
    price_data = [[Paragraph(r[0], ss['CellBold']),
                   r[1] if isinstance(r[1], Paragraph) else Paragraph(str(r[1]), ss['CellBody'])]
                  for r in price_rows]
    price_t = Table(price_data, colWidths=[62*mm, 36*mm])
    price_t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),   # right-align all value cells
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # body_t: 80 + 100 = 180mm = full usable width
    body_t = Table([[desc_para, price_t]], colWidths=[80*mm, 100*mm])
    body_t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
    ]))
    story.append(body_t)
    story.append(Spacer(1, sp))

    story.append(Paragraph(
        'The above prices are for the complete SPV kit which includes SPV modules, Solar Inverter, '
        'Structure &amp; all Accessories. Fabricated Shed, High Rise Structure, Civil Work, '
        'Net Meter Equipment, Extra cables (AC-DC), Contract Load Enhancement Charges, '
        'Special Drawings &amp; Internal Wiring are customer scope.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, sp))

    # System designed for
    story.append(Paragraph(
        f'Above system designed for S.No. {app_no or "—"}<br/>'
        f'Discom Sanction Load: {sanction_load}-Cat-{phase_code}-Phase-1',
        ss['BodySmall']
    ))
    story.append(Spacer(1, sp))

    # T&C + Bank details
    bank_name = vendor.get('bank_name', '')
    bank_branch = vendor.get('bank_branch', '')
    acc_no = vendor.get('account_number', '')
    acc_holder = vendor.get('account_holder_name', '') or vendor.get('vendor_name', '')
    ifsc = vendor.get('ifsc_code', '')

    tc_lines = [
        '1. Taxes: GST Included',
        '2. Payment terms: 100% Advance upon placing order.',
        '3. Delivery: 2-4 weeks',
    ]
    tc_para = '\n'.join(tc_lines)
    bank_str = (
        f'<b>A/c Name:</b> {acc_holder}<br/>'
        f'<b>A/c No.:</b> {acc_no}<br/>'
        f'<b>Bank:</b> {bank_name}, {bank_branch}<br/>'
        f'<b>NEFT/RTGS/IFSC:</b> {ifsc}'
    )

    tc_bank = Table(
        [[Paragraph('<b>Terms and Conditions:</b><br/>' + tc_para, ss['BodySmall']),
          Paragraph('<b>Our Banking Details (CC Account)</b><br/>' + bank_str, ss['BodySmall'])]],
        colWidths=[90*mm, 85*mm]
    )
    tc_bank.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('LINEAFTER', (0, 0), (0, 0), 0.5, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(tc_bank)
    story.append(Spacer(1, sp))

    # Warranty
    story.append(_section_header('Product Warranty'))
    story.append(Spacer(1, sp))
    story.append(Paragraph(
        '<b>Modules:</b> As per MNRE guidelines IEC/BIS standards<br/>'
        '1. 10-year workmanship warranty (Minimum power output 90% for first 10 years; 80% from Year 11 to 25)<br/>'
        '2. 25 Years Life<br/>'
        '<b>Solar Inverter:</b> As per IEC/BIS Standard<br/>'
        '1. 5 year warranty against manufacturing defects',
        ss['BodySmall']
    ))
    story.append(Spacer(1, sp))

    if vendor.get('mnre_empanelled'):
        story.append(Paragraph(
            'MNRE NATIONAL SOLAR PORTAL (PMSURYAGHAR) EMPANELLED VENDOR',
            ss['RedNote']
        ))
        story.append(Spacer(1, sp))

    # Signature + stamp (rendered independently so they stay on page 1)
    _q_sig   = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=16*mm)
    _q_stamp = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=26*mm, height=24*mm)
    story.append(_sig_stamp_table(ss, _q_sig, _q_stamp, 'Authorised Signatory'))
    story.append(Spacer(1, sp))

    # Footer
    story.append(Paragraph('Authorised Partners', ss['FooterTiny']))
    story.append(Spacer(1, sp))
    story.append(_partner_logos_footer(_logo_h))

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  1b. INVOICE
# ══════════════════════════════════════════════════════════════════════════════
def generate_invoice(
    lead: dict, vendor: dict, tech: dict,
    invoice_number: str = '',
    invoice_date=None,
    kw_size: str = '',
    quote_value: float = 0,
    discount: float = 0,
    final_amount: float = 0,
    subsidy_amount: float = 0,
    application_charge: str = 'Actuals',
    net_meters_cost: str = '',
) -> bytes:
    import re as _re
    buf = BytesIO()
    doc = _doc(buf, top=12*mm, bottom=12*mm)
    ss = _styles()
    story = []

    # Normalise kw_size
    _ks = (kw_size or '').strip()
    _m = _re.match(r'^([\d.]+)\s*[kK][wW]$', _ks)
    if _m:
        kw_size = _m.group(1) + 'KW'
    elif _re.match(r'^[\d.]+$', _ks):
        kw_size = _ks + 'KW'
    else:
        kw_size = _ks or '3KW'

    # Letterhead
    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 2*mm))

    # Invoice header — Invoice No + Date row
    inv_date = invoice_date or date.today()
    date_str = inv_date.strftime('%d-%m-%Y') if hasattr(inv_date, 'strftime') else str(inv_date)
    inv_no_str = invoice_number or f'INV-{date.today().strftime("%Y%m%d")}'

    ref_data = [
        [Paragraph(f'<b>Invoice No:</b> {inv_no_str}', ss['BodySmallBold']),
         Paragraph(f'<b>Date:</b> {date_str}', ss['BodySmallBold'])]
    ]
    rt = Table(ref_data, colWidths=[110*mm, 65*mm])
    rt.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(rt)
    story.append(Spacer(1, 1.5*mm))

    # Bill To block
    cust_name = lead.get('customer_name') or lead.get('name', '')
    cust_phone = lead.get('phone', '') or ''
    cust_addr = lead.get('address', '')
    cust_city = lead.get('city', '') or ''
    cust_state = lead.get('state', '') or ''
    cust_pincode = lead.get('pincode', '') or ''
    app_no = lead.get('sc_number', '')
    discom = (lead.get('discom') or 'APEPDCL').strip() or 'APEPDCL'
    grid_phase = lead.get('grid_phase', 'Single Phase') or 'Single Phase'
    phase_code = '3' if '3' in str(grid_phase) or 'three' in str(grid_phase).lower() else '1'
    sanction_load = lead.get('kw_size') or kw_size

    story.append(Paragraph('<b>Bill To:</b>', ss['BodySmallBold']))
    story.append(Paragraph(f'<b>{cust_name}</b>', ss['BodySmall']))
    if cust_addr:
        story.append(Paragraph(cust_addr, ss['BodySmall']))
    addr2_parts = [p for p in [cust_city, cust_state, cust_pincode] if p]
    if addr2_parts:
        story.append(Paragraph(', '.join(addr2_parts), ss['BodySmall']))
    if cust_phone:
        story.append(Paragraph(f'Ph: {cust_phone}', ss['BodySmall']))
    if app_no:
        story.append(Paragraph(f'S.No. {app_no}', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))

    # Title
    story.append(Paragraph(
        f'Invoice for Supply of <b>{kw_size} Solar Power Generating System (SPGS)</b>'
        f' - On-grid for Net meter',
        ss['DocTitle']
    ))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 1.5*mm))

    # System description (left) + pricing table (right)
    # DC-SOLAR-PANEL-BRAND-001: use vendor default if set; strip DCR placeholder; no hardcoded fallback.
    _inv_panel_brand = vendor.get('panel_make_default', '') or ''
    if _inv_panel_brand.strip().upper() == 'DCR SOLAR PANEL':
        _inv_panel_brand = ''
    inv_make = vendor.get('inverter_make_default', '') or \
        f'{kw_size.replace("KW","").replace("kw","").strip()}kVa Grid Tie Solar Inverter (IEC/BIS Approved)'
    panel_watt = kw_size.replace('KW', '000W').replace('kw', '000W')

    _inv_brand_line = (f'&nbsp;&nbsp;&nbsp;{_inv_panel_brand}<br/>' if _inv_panel_brand.strip() else '')
    desc_lines = [
        f'<b>Solar Panel:</b> {panel_watt}<br/>'
        f'{_inv_brand_line}'
        f'&nbsp;&nbsp;&nbsp;DCR Solar Panel',
        '',
        f'<b>Solar Inverter:</b> {inv_make}',
        '',
        '<b>Accessories:</b> 4Sq. Copper AC Cable,<br/>'
        '&nbsp;&nbsp;&nbsp;4Sq. Copper DC cable<br/>'
        '&nbsp;&nbsp;&nbsp;GI Mounting Structure<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(North Pole&#8211;6 Feet, South Pole&#8211;4 Feet)<br/>'
        '&nbsp;&nbsp;&nbsp;AC-DCDB, Earthing,<br/>'
        '&nbsp;&nbsp;&nbsp;1" PVC Pipe, Flexible PVC Pipe<br/>'
        '&nbsp;&nbsp;&nbsp;GI/SS Nuts, Bolts &amp; Hardware',
    ]
    desc_para = Paragraph('<br/>'.join(desc_lines), ss['BodySmall'])

    def _fmt(v):
        try:
            return f'Rs.{float(v):,.2f}'
        except Exception:
            return str(v)

    net_m_label = net_meters_cost if net_meters_cost else f'Actuals\n(Estimating given by {discom})'
    app_chg_label = application_charge if application_charge else 'Actuals'

    # [DC-INV-GST-REV-001] Reverse-calculate GST from final amount (5% total: CGST 2.5% + SGST 2.5%)
    _gst_base_val = float(final_amount or quote_value or 0)
    _taxable = _gst_base_val / 1.05 if _gst_base_val else 0
    _cgst    = _taxable * 0.025
    _sgst    = _taxable * 0.025

    price_rows = [
        ['Amount (Including GST)', _fmt(quote_value)],
        ['Discount', _fmt(discount) if discount else '—'],
        ['Final Amount', _fmt(final_amount)],
        ['Taxable Value (Excl. GST)', _fmt(_taxable)],
        ['CGST @ 2.5%', _fmt(_cgst)],
        ['SGST @ 2.5%', _fmt(_sgst)],
        ['Application Charge', app_chg_label],
        ['Net Meters Cost', net_m_label],
        ['MNRE SRT National Solar Portal Subsidy', _fmt(subsidy_amount)],
    ]

    price_data = [[Paragraph(r[0], ss['CellBold']),
                   r[1] if isinstance(r[1], Paragraph) else Paragraph(str(r[1]), ss['CellBody'])]
                  for r in price_rows]
    price_t = Table(price_data, colWidths=[62*mm, 36*mm])
    price_t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    body_t = Table([[desc_para, price_t]], colWidths=[80*mm, 100*mm])
    body_t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
    ]))
    story.append(body_t)
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph(
        'The above prices are for the complete SPV kit which includes SPV modules, Solar Inverter, '
        'Structure &amp; all Accessories. Fabricated Shed, High Rise Structure, Civil Work, '
        'Net Meter Equipment, Extra cables (AC-DC), Contract Load Enhancement Charges, '
        'Special Drawings &amp; Internal Wiring are customer scope.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph(
        f'Above system designed for S.No. {app_no or "—"}<br/>'
        f'Discom Sanction Load: {sanction_load}-Cat-{phase_code}-Phase-1',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 1.5*mm))

    # T&C + Bank details
    bank_name = vendor.get('bank_name', '')
    bank_branch = vendor.get('bank_branch', '')
    acc_no = vendor.get('account_number', '')
    acc_holder = vendor.get('account_holder_name', '') or vendor.get('vendor_name', '')
    ifsc = vendor.get('ifsc_code', '')

    tc_lines = [
        '1. Taxes: GST Included',
        '2. Payment terms: 100% Advance upon placing order.',
        '3. Delivery: 2-4 weeks',
    ]
    bank_str = (
        f'<b>A/c Name:</b> {acc_holder}<br/>'
        f'<b>A/c No.:</b> {acc_no}<br/>'
        f'<b>Bank:</b> {bank_name}, {bank_branch}<br/>'
        f'<b>NEFT/RTGS/IFSC:</b> {ifsc}'
    )

    tc_bank = Table(
        [[Paragraph('<b>Terms and Conditions:</b><br/>' + '\n'.join(tc_lines), ss['BodySmall']),
          Paragraph('<b>Our Banking Details (CC Account)</b><br/>' + bank_str, ss['BodySmall'])]],
        colWidths=[90*mm, 85*mm]
    )
    tc_bank.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('LINEAFTER', (0, 0), (0, 0), 0.5, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tc_bank)
    story.append(Spacer(1, 1.5*mm))

    # [DC-INV-HYPOTHICATION-001] Narration: Invoice Hypothicated to <loan_bank>
    _loan_bank = (lead.get('loan_bank') or '').strip()
    if _loan_bank:
        story.append(Paragraph(
            f'<b>Narration:</b> Invoice Hypothicated to {_loan_bank}',
            ss['BodySmall']
        ))
        story.append(Spacer(1, 1.5*mm))

    # Warranty
    story.append(_section_header('Product Warranty'))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        '<b>Modules:</b> As per MNRE guidelines IEC/BIS standards<br/>'
        '1. 10-year workmanship warranty (Minimum power output 90% for first 10 years; 80% from Year 11 to 25)<br/>'
        '2. 25 Years Life<br/>'
        '<b>Solar Inverter:</b> As per IEC/BIS Standard<br/>'
        '1. 5 year warranty against manufacturing defects',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 2*mm))

    if vendor.get('mnre_empanelled'):
        story.append(Paragraph(
            'MNRE NATIONAL SOLAR PORTAL (PMSURYAGHAR) EMPANELLED VENDOR',
            ss['RedNote']
        ))
        story.append(Spacer(1, 1.5*mm))

    # Signature + stamp block
    _inv_sig   = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _inv_stamp = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    story.append(_sig_stamp_table(ss, _inv_sig, _inv_stamp, 'Authorised Signatory'))
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph('Authorised Partners', ss['FooterTiny']))
    story.append(Spacer(1, 1*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  1c. CO-APPLICANT QUOTATION
# ══════════════════════════════════════════════════════════════════════════════
def generate_co_applicant_quotation(
    lead: dict, vendor: dict,
    kw_size: str, quote_value: float, discount: float,
    final_amount: float, subsidy_amount: float,
    ref_no: str, quote_date=None,
    panel_brand: str = "",
) -> bytes:
    """
    Identical to generate_quotation() but addressed to the co-applicant.
    The 'To:' block uses co_applicant_name; primary customer name shown as reference.
    """
    import re as _re
    buf = BytesIO()
    doc = _doc(buf, top=12*mm, bottom=12*mm)
    ss = _styles()
    story = []

    _ks = (kw_size or '').strip()
    _m = _re.match(r'^([\d.]+)\s*[kK][wW]$', _ks)
    if _m:
        kw_size = _m.group(1) + 'KW'
    elif _re.match(r'^[\d.]+$', _ks):
        kw_size = _ks + 'KW'
    else:
        kw_size = _ks or '3KW'

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 2*mm))

    ref_date = quote_date or date.today()
    date_str = ref_date.strftime('%d-%m-%Y') if hasattr(ref_date, 'strftime') else str(ref_date)
    ref_data = [
        [Paragraph(f'Ref: {ref_no}', ss['BodySmallBold']),
         Paragraph(f'Date: {date_str}', ss['BodySmallBold'])]
    ]
    rt = Table(ref_data, colWidths=[110*mm, 65*mm])
    rt.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(rt)
    story.append(Spacer(1, 1.5*mm))

    # Co-applicant as primary addressee
    co_app_name  = lead.get('co_applicant_name', '') or ''
    cust_name    = lead.get('customer_name') or lead.get('name', '')
    cust_addr    = lead.get('address', '')
    cust_city    = lead.get('city', '') or ''
    cust_state   = lead.get('state', '') or ''
    app_no       = lead.get('sc_number', '')

    story.append(Paragraph('To,', ss['BodySmall']))
    story.append(Paragraph(f'<b>{co_app_name}</b>', ss['BodySmall']))
    if cust_addr:
        story.append(Paragraph(cust_addr, ss['BodySmall']))
    addr2 = ', '.join(filter(None, [cust_city, cust_state]))
    if addr2:
        story.append(Paragraph(addr2, ss['BodySmall']))
    if cust_name:
        story.append(Paragraph(f'<i>(Primary Applicant: {cust_name})</i>', ss['BodySmall']))
    if app_no:
        story.append(Paragraph(f'S.No. {app_no}', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph(
        f'Estimation for Supply of <b>{kw_size} Solar Power Generating System (SPGS)</b>'
        f' - On-grid for Net meter',
        ss['DocTitle']
    ))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 1.5*mm))

    # DC-SOLAR-PANEL-BRAND-001: brand from modal param takes priority;
    # fallback to vendor default; never show a hardcoded placeholder.
    if not panel_brand.strip():
        panel_brand = vendor.get('panel_make_default', '') or ''
    if panel_brand.strip().upper() == 'DCR SOLAR PANEL':
        panel_brand = ''
    inv_make = vendor.get('inverter_make_default', '') or f'{kw_size.replace("KW","").replace("kw","").strip()}kVa Grid Tie Solar Inverter (IEC/BIS Approved)'
    discom = (lead.get('discom') or 'APEPDCL').strip() or 'APEPDCL'
    grid_phase = lead.get('grid_phase', 'Single Phase') or 'Single Phase'
    phase_code = '3' if '3' in str(grid_phase) or 'three' in str(grid_phase).lower() else '1'
    sanction_load = lead.get('kw_size') or kw_size
    panel_watt = kw_size.replace('KW', '000W').replace('kw', '000W')

    _brand_line = (f'&nbsp;&nbsp;&nbsp;{panel_brand}<br/>' if panel_brand.strip() else '')
    desc_lines = [
        f'<b>Solar Panel:</b> {panel_watt}<br/>'
        f'{_brand_line}'
        f'&nbsp;&nbsp;&nbsp;DCR Solar Panel',
        '',
        f'<b>Solar Inverter:</b> {inv_make}',
        '',
        '<b>Accessories:</b> 4Sq. Copper AC Cable,<br/>'
        '&nbsp;&nbsp;&nbsp;4Sq. Copper DC cable<br/>'
        '&nbsp;&nbsp;&nbsp;GI Mounting Structure<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(North Pole&#8211;6 Feet, South Pole&#8211;4 Feet)<br/>'
        '&nbsp;&nbsp;&nbsp;AC-DCDB, Earthing,<br/>'
        '&nbsp;&nbsp;&nbsp;1" PVC Pipe, Flexible PVC Pipe<br/>'
        '&nbsp;&nbsp;&nbsp;GI/SS Nuts, Bolts &amp; Hardware',
    ]
    desc_para = Paragraph('<br/>'.join(desc_lines), ss['BodySmall'])

    def _fmt(v):
        try:
            return f'Rs.{float(v):,.2f}'
        except Exception:
            return str(v)

    price_rows = [
        ['Price (Including GST)', _fmt(quote_value)],
        ['Discount', _fmt(discount) if discount else '—'],
        ['Final Amount', _fmt(final_amount)],
        ['Application Charge', 'Actuals'],
        ['Net Meters Cost', f'Actuals\n(Estimating given by {discom})'],
        ['MNRE SRT National Solar Portal Subsidy', _fmt(subsidy_amount)],
    ]
    price_data = [[Paragraph(r[0], ss['CellBold']),
                   r[1] if isinstance(r[1], Paragraph) else Paragraph(str(r[1]), ss['CellBody'])]
                  for r in price_rows]
    price_t = Table(price_data, colWidths=[62*mm, 36*mm])
    price_t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    body_t = Table([[desc_para, price_t]], colWidths=[80*mm, 100*mm])
    body_t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
    ]))
    story.append(body_t)
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph(
        'The above prices are for the complete SPV kit which includes SPV modules, Solar Inverter, '
        'Structure &amp; all Accessories. Fabricated Shed, High Rise Structure, Civil Work, '
        'Net Meter Equipment, Extra cables (AC-DC), Contract Load Enhancement Charges, '
        'Special Drawings &amp; Internal Wiring are customer scope.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph(
        f'Above system designed for S.No. {app_no or "—"}<br/>'
        f'Discom Sanction Load: {sanction_load}-Cat-{phase_code}-Phase-1',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 1.5*mm))

    bank_name   = vendor.get('bank_name', '')
    bank_branch = vendor.get('bank_branch', '')
    acc_no      = vendor.get('account_number', '')
    acc_holder  = vendor.get('account_holder_name', '') or vendor.get('vendor_name', '')
    ifsc        = vendor.get('ifsc_code', '')
    tc_lines = [
        '1. Taxes: GST Included',
        '2. Payment terms: 100% Advance upon placing order.',
        '3. Delivery: 2-4 weeks',
    ]
    bank_str = (
        f'<b>A/c Name:</b> {acc_holder}<br/>'
        f'<b>A/c No.:</b> {acc_no}<br/>'
        f'<b>Bank:</b> {bank_name}, {bank_branch}<br/>'
        f'<b>NEFT/RTGS/IFSC:</b> {ifsc}'
    )
    tc_bank = Table(
        [[Paragraph('<b>Terms and Conditions:</b><br/>' + '\n'.join(tc_lines), ss['BodySmall']),
          Paragraph('<b>Our Banking Details (CC Account)</b><br/>' + bank_str, ss['BodySmall'])]],
        colWidths=[90*mm, 85*mm]
    )
    tc_bank.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('LINEAFTER', (0, 0), (0, 0), 0.5, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tc_bank)
    story.append(Spacer(1, 1.5*mm))

    story.append(_section_header('Product Warranty'))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        '<b>Modules:</b> As per MNRE guidelines IEC/BIS standards<br/>'
        '1. 10-year workmanship warranty (Minimum power output 90% for first 10 years; 80% from Year 11 to 25)<br/>'
        '2. 25 Years Life<br/>'
        '<b>Solar Inverter:</b> As per IEC/BIS Standard<br/>'
        '1. 5 year warranty against manufacturing defects',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 2*mm))

    if vendor.get('mnre_empanelled'):
        story.append(Paragraph(
            'MNRE NATIONAL SOLAR PORTAL (PMSURYAGHAR) EMPANELLED VENDOR',
            ss['RedNote']
        ))
        story.append(Spacer(1, 1.5*mm))

    # Signature + stamp block
    _ca_sig   = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _ca_stamp = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    story.append(_sig_stamp_table(ss, _ca_sig, _ca_stamp, 'Authorised Signatory'))
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph('Authorised Partners', ss['FooterTiny']))
    story.append(Spacer(1, 1*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  2. ANNEXURE-A
# ══════════════════════════════════════════════════════════════════════════════
def generate_annexure_a(lead: dict, vendor: dict, tech: dict) -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('Annexure - A', ss['DocTitle']))
    story.append(Paragraph('Undertaking / Self-Declaration for Domestic Content Requirement Fulfilment', ss['BodySmall']))
    story.append(HRFlowable(width='100%', thickness=1, color=NAVY))
    story.append(Spacer(1, 4*mm))

    vendor_name = vendor.get('vendor_name', '')
    kw = lead.get('kw_size', '3KW')
    cust_name = lead.get('customer_name') or lead.get('name', '')
    cust_addr = lead.get('address', '')
    sanction_no = lead.get('mnre_app_ref', '')
    sanction_date_str = lead.get('sanction_date', '')
    if sanction_date_str and len(str(sanction_date_str)) >= 10:
        try:
            _sd = datetime.fromisoformat(str(sanction_date_str)[:10])
            sanction_date_str = _sd.strftime('%d-%m-%Y')
        except Exception:
            pass
    discom = lead.get('discom', 'APEPDCL')

    story.append(Paragraph(
        f'This is to certify that <b>{vendor_name}</b> has installed <b>{kw} Grid Connected Rooftop Solar PV '
        f'Power Plant</b> for <b>{cust_name}</b> at {cust_addr}. Sanction number <b>{sanction_no}</b> '
        f'dated {sanction_date_str} Issued by <b>{discom}</b>.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(
        '2. It is hereby undertaken that the PV modules installed for the above-mentioned project '
        'are domestically manufactured using domestic manufactured solar cells. The details of '
        'installed PV Modules are as follows:',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 3*mm))

    num_pan = tech.get('num_panels', '')
    panel_cap = tech.get('panel_capacity_each_w', '')
    pan_cap_str = f'{panel_cap}Wp' if panel_cap else '—'
    pan_make = tech.get('panel_make', '—')
    pan_model = tech.get('panel_model', '—')
    pan_serials = tech.get('panel_serial_numbers', '—')
    pan_type = tech.get('panel_type', '—')
    po_no = tech.get('purchase_order_no', '—')
    po_date = tech.get('purchase_order_date', '')
    if po_date and len(str(po_date)) >= 10:
        try:
            _pd = datetime.fromisoformat(str(po_date)[:10])
            po_date = _pd.strftime('%d-%m-%Y')
        except Exception:
            pass
    cell_mfg = tech.get('cell_manufacturer', '—')
    gst_inv = tech.get('cell_gst_invoice_no', '—')
    inst_date = tech.get('installation_date', '')
    if inst_date and len(str(inst_date)) >= 10:
        try:
            _id2 = datetime.fromisoformat(str(inst_date)[:10])
            inst_date = _id2.strftime('%d-%m-%Y')
        except Exception:
            pass

    module_rows = [
        ('1. PV Module Capacity:', pan_cap_str),
        ('2. PV Module Type:', pan_model or pan_type),
        ('3. Number of PV Modules:', f'{num_pan} No.' if num_pan else '—'),
        ('4. Sr. No. of PV Modules:', pan_serials),
        ('5. PV Module Make:', pan_make),
        ('6. Purchase Order Number:', po_no),
        ('7. Purchase Order Date:', po_date or '—'),
        ('8. Cell manufacturer\'s name:', cell_mfg),
        ('9. Cell GST Invoice No:', gst_inv),
        ('10. Installation Date:', inst_date or '—'),
    ]
    story.append(_kv_table(module_rows, col_widths=[75*mm, 95*mm]))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(
        '3. The above undertaking is based on the certificate issued by PV Module manufacturer/supplier '
        'while supplying the above-mentioned order.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f'4. I, <b>{vendor_name}</b> on behalf of further declare that the information given above is '
        'true and correct and nothing has been concealed therein. If anything is found incorrect at any '
        'stage then the due Central Financial Assistance (CFA) can be withheld and appropriate action '
        'may be taken against me and my company for wrong declaration.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 8*mm))

    # Signature + stamp block: stamp uses square 30×30 mm to preserve circular shape
    _ann_a_sign  = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _ann_a_stamp = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    # Render sig (left) and stamp (right) at full page width so stamp is never clipped
    story.append(_sig_stamp_table(ss, _ann_a_sign, _ann_a_stamp, '(Signature with Official Seal)'))
    story.append(Spacer(1, 4*mm))
    story.append(_computer_generated_note(ss))
    story.append(Spacer(1, 2*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  3. ANNEXURE-C (Project Completion Report)
# ══════════════════════════════════════════════════════════════════════════════
def generate_annexure_c_completion(lead: dict, vendor: dict, tech: dict) -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('Annexure - C', ss['DocTitle']))
    story.append(Paragraph('Project Completion Report for Grid-Connected Rooftop', ss['DocTitle']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 4*mm))

    cust_name = lead.get('customer_name') or lead.get('name', '')
    addr = lead.get('address', '')
    city = lead.get('city', '')
    state_val = lead.get('state', 'ANDHRA PRADESH')
    district = lead.get('district', city)
    pin = lead.get('pincode', '')
    phone = lead.get('phone', '') or lead.get('mobile', '')
    email = lead.get('email', '')
    aadhaar = lead.get('aadhaar_number', '')
    lat = lead.get('latitude', '')
    lon = lead.get('longitude', '')
    kw = lead.get('kw_size', '3KW')
    discom = lead.get('discom', 'APEPDCL')
    sanction_load = lead.get('kw_size', kw)
    mnre_ref = lead.get('mnre_app_ref', '')
    discom_reg = lead.get('discom_reg_no', '')
    sc_no = lead.get('sc_number', '')
    grid_phase = lead.get('grid_phase', 'Single Phase')
    vendor_name = vendor.get('vendor_name', '')

    project_rows = [
        ('PM Surya Ghar Application Reference Number', mnre_ref or '—'),
        ('Discom Solar Roof Top Registration No', discom_reg or '—'),
        ('SC No', sc_no or '—'),
        ('Installed by Vendor', vendor_name),
        ('Title of the Project', f'{_norm_kw(kw)} ON GRID SOLAR ROOF TOP'),
        ('SPV Capacity (kWp)', kw),
        ('Category of the organization / beneficiary', cust_name),
        ('Name of the contact person', cust_name),
        ('Address of contact person', addr),
        ('State', state_val or 'ANDHRA PRADESH'),
        ('District / City', f'{district}-{pin}' if pin else district),
        ('Mobile', phone or '—'),
        ('Email', email or '—'),
        ('Aadhaar Card Number (For Residential)', aadhaar or '—'),
        ('Latitude', lat or '—'),
        ('Longitude', lon or '—'),
        ('DISCOM', discom),
        ('Sanction Load', sanction_load),
    ]
    story.append(_kv_table(project_rows))
    story.append(Spacer(1, 4*mm))

    story.append(_section_header('Technology Description & System Design / Specification'))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        '<i>(Compliance to BIS / IEC Standards is mandatory)</i>', ss['BodySmall']
    ))
    story.append(Spacer(1, 2*mm))

    num_pan = tech.get('num_panels', '')
    pan_cap = tech.get('panel_capacity_each_w', '')
    total_kw = f'{kw}' if kw else (f'{int(pan_cap)*int(num_pan)//1000}KW' if pan_cap and num_pan else '—')
    pan_make = tech.get('panel_make', '—')
    pan_model = tech.get('panel_model', '—')
    pan_type = tech.get('panel_type', '—')
    pan_tech = tech.get('panel_technology', '—')
    tilt = tech.get('tilt_angle', '—')
    azimuth = tech.get('azimuth', '—')
    rfid = tech.get('rfid_position') or 'INSIDE'

    # DC Fix (Apr 2026): Auto-derive inverter fields from KW capacity when DB values are absent.
    # These defaults reflect the standard GoodWE inverter used for most residential installs.
    _kw_norm = _norm_kw(kw)  # e.g. "3KW"
    inv_make = tech.get('inverter_make') or 'GoodWE'
    inv_model = tech.get('inverter_model') or f'{_kw_norm} Inverter'
    inv_type = tech.get('inverter_type') or _kw_norm
    inv_eff = tech.get('inverter_efficiency_pct') or '—'
    mppt = tech.get('mppt_type') or f'{_kw_norm} MPPT Inverter'
    num_inv = tech.get('num_inverters', 1)
    grid_v = tech.get('grid_voltage', '240 V')

    # Capacity display: show as KWp (e.g. "3KWp") per MNRE format
    _raw_inv_cap = tech.get('inverter_capacity_kw') or kw or _kw_norm
    _ic = str(_raw_inv_cap).strip()
    if _ic.upper().endswith('KW') and not _ic.upper().endswith('KWP'):
        inv_cap = _ic + 'p'
    else:
        inv_cap = _ic

    tech_rows = [
        ('Solar PV Module', pan_make),
        ('Power of each PV Module', f'Each {pan_cap}W' if pan_cap else '—'),
        ('Number of Modules', f'{num_pan} Nos' if num_pan else '—'),
        ('Cumulative Capacity of Modules', total_kw),
        ('Solar cell technology', pan_tech or pan_type),
        ('Tilt Angle of Modules', tilt),
        ('Module efficiency', 'Attached'),
        ('Azimuth', azimuth),
        ('Indigenous or imported (Cell)', 'Indigenous'),
        ('RFID passed inside or outside', rfid),
        ('Indigenous or imported (Module)', 'Indigenous'),
        # F4: guard '— —' when both make and model are empty/default
        ('Inverter', f'{inv_make} {inv_model}' if (inv_make and inv_make != '—') or (inv_model and inv_model != '—') else '—'),
        ('Type of inverter', inv_type),
        ('Power of each PCU / Nos of inverters', f'0{num_inv} No' if num_inv else '01 No'),
        ('Capacity / Power of PCU / inverters', inv_cap),
        ('Type of Charge Controller / MPPT', mppt),
        ('Inverter efficiency', inv_eff),
        ('Grid connectivity level phase', grid_phase),
        ('Grid connectivity level Voltage', grid_v),
    ]
    story.append(_kv_table(tech_rows))
    story.append(Spacer(1, 6*mm))

    # Sig + stamp side-by-side; stamp square to keep circular seal round
    _rep_sig_img = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _stamp_img   = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    story.append(_sig_stamp_table(ss, _rep_sig_img, _stamp_img, 'Signature of Vendor (With Stamp & Seal)'))
    story.append(Spacer(1, 4*mm))
    story.append(_computer_generated_note(ss))
    story.append(Spacer(1, 2*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  4. ANNEXURE-C (Technical Installation Details)
# ══════════════════════════════════════════════════════════════════════════════
def generate_annexure_c_technical(lead: dict, vendor: dict, tech: dict) -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('Technical Installation Details', ss['DocTitle']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 4*mm))

    story.append(_section_header('3. Mounting Structures'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('Type', tech.get('mounting_type', 'Rooftop')),
        ('Surface Finish', tech.get('surface_finish', 'GALVANIZED')),
        ('Material', tech.get('structure_material', 'Galvanized MS Module Structure')),
        ('Wind Speed Tolerance', tech.get('wind_speed_tolerance', '150KW/HR')),
    ]))
    story.append(Spacer(1, 3*mm))

    story.append(_section_header('4. Cables: POLYCAB'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('DC Cable Make', tech.get('dc_cable_make', 'Polycab / 4 Square mm')),
        ('Size / Length (DC)', f'{tech.get("dc_cable_sqmm","4")} Sq.mm / {tech.get("dc_cable_length_m",90)} Mtrs'),
        ('AC Cable Make (Inverter to ACDB)', tech.get('ac_cable_inv_acdb_make', 'Polycab / 4 Square mm')),
        ('Size / Length (Inv-ACDB)', f'{tech.get("ac_cable_inv_acdb_sqmm","4")} Sq.mm / {tech.get("ac_cable_inv_acdb_length_m",60)} Mtrs'),
        ('AC Cable Make (ACDB to Electric Panel)', tech.get('ac_cable_acdb_panel_make', 'Polycab / 4 Square mm')),
        ('Size / Length (ACDB-Panel)', f'{tech.get("ac_cable_acdb_panel_sqmm","4")} Sq.mm / {tech.get("ac_cable_acdb_panel_length_m",40)} Mtrs'),
        ('Conductor', 'Multi Strand High Conductivity Copper'),
        ('Insulation / sheath', 'PVC / XLPE Insulated'),
    ]))
    story.append(Spacer(1, 3*mm))

    story.append(_section_header('5. Junction Box & Distribution Boards'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('ACDB', 'Weatherproof dust & vermin proof'),
        ('ACDB Nos.', str(tech.get('acdb_count', 1))),
        ('DCDB', 'Weatherproof dust & vermin proof'),
        ('DCDB Nos.', str(tech.get('dcdb_count', 1))),
    ]))
    story.append(Spacer(1, 3*mm))

    story.append(_section_header('6. Earthing & Lightning Protection'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('AC Earthing (Nos.)', str(tech.get('ac_earthing_nos', 1))),
        ('AC Earth Resistance', tech.get('earth_resistance_ac', '0.5 Ohms')),
        ('DC Earthing (Nos.)', str(tech.get('dc_earthing_nos', 1))),
        ('DC Earth Resistance', tech.get('earth_resistance_dc', '0.5 Ohms')),
        ('Lightning Arrestors (LA) (Nos.)', str(tech.get('la_nos', 1))),
        ('LA Earth Resistance', tech.get('earth_resistance_la', '0.5 Ohms')),
    ]))
    story.append(Spacer(1, 3*mm))

    story.append(_section_header('7. Online Monitoring Mechanism'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('Web Portal User ID', tech.get('monitoring_user_id', '—')),
        ('Web Portal Password', tech.get('monitoring_password', '—')),
    ]))
    story.append(Spacer(1, 3*mm))

    story.append(_section_header('10. Danger Board'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('Danger Board', tech.get('danger_board', 'AVAILABLE')),
    ]))
    story.append(Spacer(1, 6*mm))

    # Sig + stamp side-by-side; stamp square to keep circular seal round
    _rep_sig_img_t = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _stamp_img_t   = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    story.append(_sig_stamp_table(ss, _rep_sig_img_t, _stamp_img_t, 'Signature of Vendor (With Stamp & Seal)'))
    story.append(Spacer(1, 4*mm))
    story.append(_computer_generated_note(ss))
    story.append(Spacer(1, 2*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  5. COMMISSIONING TEST REPORT
# ══════════════════════════════════════════════════════════════════════════════
def generate_commissioning_test_report(lead: dict, vendor: dict, tech: dict) -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 4*mm))
    kw = _norm_kw(lead.get('kw_size', '3KW'))
    story.append(Paragraph(f'Commissioning Test Report: Solar Project {kw}', ss['DocTitle']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 4*mm))

    inv_sn = tech.get('inverter_serial_no', '—')
    inv_cap = _valid_kw_val(tech.get('inverter_capacity_kw', ''), kw)
    num_inv = tech.get('num_inverters', 1)
    s1 = tech.get('string1_voc', '—')
    s2 = tech.get('string2_voc', '—')
    grid_v = tech.get('grid_voltage', '240.0V')
    acdb_ic = tech.get('acdb_ic_voltage', '240')
    acdb_og = tech.get('acdb_og_voltage', '240')
    er_ac = tech.get('earth_resistance_ac', '0.5 Ohms')
    er_dc = tech.get('earth_resistance_dc', '0.5 Ohms')
    er_la = tech.get('earth_resistance_la', '0.5 Ohms')

    story.append(Paragraph(f'<b>Inverter Testing (DC Side):</b> Nos. of Inverter {num_inv} Nos.', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))

    hdr_style = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY_LIGHT),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    # DC Side
    dc_data = [
        ['Inverter S. No.', 'Capacity', 'String 1: Voc', 'String 2: Voc', 'Remark'],
        [inv_sn, inv_cap, s1, s2, ''],
    ]
    dc_t = Table(dc_data, colWidths=[50*mm, 25*mm, 30*mm, 30*mm, 25*mm], repeatRows=1)
    dc_t.setStyle(TableStyle(hdr_style))
    story.append(dc_t)
    story.append(Spacer(1, 4*mm))

    # AC Side
    story.append(Paragraph('<b>Inverter Testing (AC Side – Single Phase)</b>', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))
    ac_data = [
        ['Inverter S. No.', 'Capacity', 'R-Y/P-N', 'Y-B', 'B-R', 'R-N', 'Y-N', 'B-N', 'Remark'],
        [inv_sn, inv_cap, grid_v, '', '', '', '', '', ''],
    ]
    ac_t = Table(ac_data, colWidths=[42*mm, 22*mm, 22*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 14*mm], repeatRows=1)
    ac_t.setStyle(TableStyle(hdr_style))
    story.append(ac_t)
    story.append(Spacer(1, 4*mm))

    # ACDB & Meter Panel
    story.append(Paragraph('<b>ACDB &amp; Meter Panel Testing – Single Phase</b>', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))
    acdb_data = [
        ['', 'R-Y/P-N', 'Y-B', 'B-R', 'R-N', 'Y-N', 'B-N'],
        ['ACDB I/C (V)', acdb_ic, '', '', '', '', ''],
        ['ACDB O/G (V)', acdb_og, '', '', '', '', ''],
    ]
    acdb_t = Table(acdb_data, colWidths=[40*mm, 25*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm], repeatRows=1)
    acdb_t.setStyle(TableStyle(hdr_style))
    story.append(acdb_t)
    story.append(Spacer(1, 4*mm))

    # Earthing Pit
    story.append(Paragraph('<b>Earthing Pit Details:</b> Nos. of Earth Pit', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))
    ep_data = [
        ['', 'Earthing AC', 'Earthing DC', 'Earthing LA', 'Remark'],
        ['Earth Test Value (Ohm)', er_ac, er_dc, er_la, ''],
    ]
    ep_t = Table(ep_data, colWidths=[45*mm, 35*mm, 35*mm, 35*mm, 25*mm], repeatRows=1)
    ep_t.setStyle(TableStyle(hdr_style))
    story.append(ep_t)
    story.append(Spacer(1, 8*mm))

    # Stamp square (30×30 mm) so circular seal stays round; sig and stamp side-by-side inside vendor cell
    _rep_sig_img_c = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _stamp_img_c   = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    # Mini inner table: sig left (52mm) | stamp right (33mm) within the 88mm vendor column
    _inner_sig_cell = [Paragraph('<b>Signature</b>', ss['BodySmall'])]
    if _rep_sig_img_c:
        _inner_sig_cell += [Spacer(1, 1*mm), _rep_sig_img_c]
    else:
        _inner_sig_cell.append(Spacer(1, 22*mm))
    _inner_stamp_cell = [Paragraph('<b>Stamp</b>', ss['BodySmall'])]
    if _stamp_img_c:
        _inner_stamp_cell += [Spacer(1, 1*mm), _stamp_img_c]
    else:
        _inner_stamp_cell.append(Spacer(1, 30*mm))
    _inner_t = Table([[_inner_sig_cell, _inner_stamp_cell]], colWidths=[52*mm, 34*mm])
    _inner_t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                   ('FONTSIZE', (0,0), (-1,-1), 8)]))
    _vendor_sig_cell = [Paragraph('<b>Counter Signed by Vendor with Stamp</b>', ss['BodySmall']),
                        Spacer(1, 2*mm), _inner_t]
    _tech_sig_url = vendor.get('tech_signature_url', '')
    _tech_sig_img = _fetch_url_image(_tech_sig_url, width=40*mm, height=24*mm) if _tech_sig_url else None
    _site_eng_cell = [
        Paragraph('<b>Signature of the Site Engineer</b>', ss['BodySmall']),
        _tech_sig_img if _tech_sig_img else Spacer(40*mm, 24*mm),
    ]
    sig_t = Table(
        [[_vendor_sig_cell, _site_eng_cell]],
        colWidths=[88*mm, 87*mm]
    )
    sig_t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LINEABOVE', (0, 0), (0, 0), 0.5, GREY_BORDER),
        ('LINEABOVE', (1, 0), (1, 0), 0.5, GREY_BORDER),
    ]))
    story.append(sig_t)
    story.append(Spacer(1, 4*mm))
    story.append(_computer_generated_note(ss))
    story.append(Spacer(1, 2*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  6. SYNCHRONISATION CERTIFICATE
# ══════════════════════════════════════════════════════════════════════════════
def generate_synchronisation_certificate(lead: dict, vendor: dict, discom_reg_date: str = '') -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('SYNCHRONISATION CERTIFICATE', ss['DocTitle']))
    story.append(Paragraph(
        'Synchronization with the DISCOM Grid, Installation of Meter(s) and COD.'
        '<br/><i>(To be filled by the DISCOM)</i>',
        ss['BodySmall']
    ))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 4*mm))

    cust_name = lead.get('customer_name') or lead.get('name', '')
    addr = lead.get('address', '')
    consumer_no = lead.get('consumer_no', '—')
    mnre_ref = lead.get('mnre_app_ref', '—')
    discom_reg = lead.get('discom_reg_no', '—')
    kw = lead.get('kw_size', '3KW')
    # DC Fix: strip any trailing "KW"/"KWP" so we can append "kWp" without duplication
    _kw_num = str(kw).strip().upper().replace('KWP', '').replace('KW', '').strip()
    kw_kwp = f'{_kw_num}kWp'   # e.g. "3kWp"
    vendor_name = vendor.get('vendor_name', '')
    discom = lead.get('discom', 'APEPDCL')

    # DC Fix (Apr 2026): parse sanction_date → DD-MM-YYYY; default to today when absent/null.
    # Both "Ref: Dated:" and "DISCOM Registration No Dated:" use this value.
    _raw_sd = lead.get('sanction_date') or ''
    sanction_date_str = ''
    if _raw_sd and str(_raw_sd).strip():
        try:
            _sd = datetime.fromisoformat(str(_raw_sd).strip()[:10])
            sanction_date_str = _sd.strftime('%d-%m-%Y')
        except Exception:
            sanction_date_str = str(_raw_sd).strip()
    if not sanction_date_str:
        sanction_date_str = date.today().strftime('%d-%m-%Y')

    story.append(Paragraph('To,', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f'<b>APPLICANT NAME:</b> {cust_name}, {addr}',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f'<b>Consumer No:</b> {consumer_no}', ss['BodySmall']))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f'<b>Ref:</b> Your Application No: {mnre_ref} Dated: {sanction_date_str}<br/>'
        f'<b>DISCOM Registration No:</b> {discom_reg} Dated: {discom_reg_date or "___________"}',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('Sir/Madam,', ss['BodySmall']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('<b>Sub:</b>', ss['BodySmall']))
    story.append(Paragraph('1. Synchronization with the DISCOM Grid;', ss['BodySmall']))
    story.append(Paragraph('2. Installation of Meter(s);', ss['BodySmall']))
    story.append(Paragraph('3. Commercial Operation Date.', ss['BodySmall']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        f'Synchronization test of Solar Rooftop PV system of <b>{kw_kwp}</b> installed on the roof of '
        f'your installation by <b>{vendor_name}</b> Application No <b>{mnre_ref}</b> has been conducted '
        f'and your RTSPV system found satisfactory and successfully synchronized with the DISCOM grid. '
        f'Meter with no ________________ has been installed and sealed on Dt. ________________.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('Yours faithfully,', ss['BodySmall']))
    story.append(Spacer(1, 10*mm))

    # Sig + stamp block: stamp square 30×30 mm to preserve circular seal
    _sc_sign  = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _sc_stamp = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    # Top block: signature (left) | stamp (right)
    _sc_sig_stamp = _sig_stamp_table(ss, _sc_sign, _sc_stamp, '(Signature of Officer)')
    # Name / Date rows below
    detail_t = Table(
        [['Name and Designation: ___________________________', ''],
         [f'Date: {sanction_date_str}', '']],
        colWidths=[130*mm, 50*mm]
    )
    detail_t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(_sc_sig_stamp)
    story.append(Spacer(1, 3*mm))
    story.append(detail_t)
    story.append(Spacer(1, 4*mm))
    story.append(_computer_generated_note(ss))
    story.append(Spacer(1, 2*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  7. ANNEXURE-IV WORK COMPLETION REPORT
# ══════════════════════════════════════════════════════════════════════════════
def generate_annexure_iv(lead: dict, vendor: dict, tech: dict) -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('ANNEXURE – IV', ss['DocTitle']))
    story.append(Paragraph(
        'Work Completion Report for Synchronization of Rooftop Solar PV System',
        ss['DocTitle']
    ))
    story.append(Paragraph(
        '(To be submitted by Eligible Consumer/Applicant)',
        ss['BodySmall']
    ))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    story.append(Spacer(1, 4*mm))

    cust_name = lead.get('customer_name') or lead.get('name', '')
    phone = lead.get('phone', '') or lead.get('mobile', '')
    kw = _norm_kw(lead.get('kw_size', '3KW'))
    consumer_no = lead.get('consumer_no', '—')
    mnre_ref = lead.get('mnre_app_ref', '—')
    discom_reg = lead.get('discom_reg_no') or '—'
    sc_no = lead.get('sc_number', '—')
    # consumer_category: injected via pre-flight modal; falls back to lead or 'HT'
    consumer_category = (tech.get('consumer_category') or lead.get('consumer_category') or 'HT').strip()

    sanction_date_str = lead.get('sanction_date', '')
    if sanction_date_str and str(sanction_date_str).strip() != '—' and len(str(sanction_date_str)) >= 10:
        try:
            _sd = datetime.fromisoformat(str(sanction_date_str)[:10])
            sanction_date_str = _sd.strftime('%d-%m-%Y')
        except Exception:
            pass

    story.append(_section_header('A. Applicant / Consumer Details'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('1. Net Meter Registration Number', discom_reg),
        ('2. Registration Date', sanction_date_str or '—'),
        ('3. Name of the applicant', cust_name),
        ('4. Service Number', sc_no),
        ('5. Category', consumer_category),
        ('6. Load in kW', kw),
    ]))
    story.append(Spacer(1, 3*mm))

    # Vendor details
    v_addr = vendor.get('address', '')
    v_city = vendor.get('city', '')
    v_state = vendor.get('state', '')
    v_pin = vendor.get('pincode', '')
    v_phone = vendor.get('phone', '')
    v_email = vendor.get('email', '')
    v_name = vendor.get('vendor_name', '')

    story.append(_section_header('B. Vendor of the Rooftop Solar PV System Details'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('1. Name of Vendor', v_name),
        ('2. Address', v_addr),
        ('3. City / Village', v_city),
        ('4. State', v_state),
        ('5. Pin Code', v_pin),
        ('6. Phone', v_phone),
        ('7. Email ID', v_email),
    ]))
    story.append(Spacer(1, 3*mm))

    # PV Module — all values come from tech dict (pre-flight overrides injected there)
    pan_make = tech.get('panel_make') or '—'
    pan_serials = tech.get('panel_serial_numbers') or '—'
    # panel_type from pre-flight override takes priority over panel_model (DB field)
    pan_type = tech.get('panel_type') or tech.get('panel_model') or '—'
    pan_cap = tech.get('panel_capacity_each_w') or '—'
    # num_panels from pre-flight; auto fallback: kWp × 2 (standard 250W panels for 3KW → 6)
    _kw_num = ''.join(c for c in kw if c.isdigit() or c == '.') or '3'
    _auto_panels = str(int(float(_kw_num) * 2)) if _kw_num else '6'
    num_pan = str(tech.get('num_panels') or _auto_panels)
    total_cap = _norm_kw(kw)

    story.append(_section_header('C. Solar PV Module Details'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('1. Make', pan_make),
        ('2. Serial number', pan_serials),
        ('3. Type of module', pan_type),
        ('4. Capacity of each module', f'{pan_cap}W' if pan_cap not in ('—', '') else '—'),
        ('5. Number of modules', num_pan),
        ('6. Total capacity', total_cap),
    ]))
    story.append(Spacer(1, 3*mm))

    # Inverter — all values come from tech dict (pre-flight overrides injected there)
    inv_make = tech.get('inverter_make') or '—'
    inv_sn = tech.get('inverter_serial_no') or '—'
    inv_cap = _valid_kw_val(tech.get('inverter_capacity_kw', ''), kw)
    inv_in_v = tech.get('grid_voltage') or '240 V'

    story.append(_section_header('D. Grid Tie Inverter / Connector'))
    story.append(Spacer(1, 2*mm))
    story.append(_kv_table([
        ('1. Make', inv_make),
        ('2. Serial number', inv_sn),
        ('3. Capacity', inv_cap),
        ('4. Input voltage', inv_in_v),
        ('5. Output voltage', '240 V'),
        ('6. If grid supply fails, no return supply to the grid (Yes or No)', 'Yes'),
    ]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        '<b>Encl.:</b> Connected SPV generator Single line diagram, CEIG Approval copy',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 8*mm))

    # Stamp square (30×30 mm) so circular seal stays round; sig and stamp side-by-side inside vendor cell
    _iv_sign  = _fetch_url_image(vendor.get('rep_signature_url', ''), width=40*mm, height=22*mm)
    _iv_stamp = _fetch_url_image(vendor.get('stamp_image_url', ''),   width=30*mm, height=30*mm)
    # Mini inner table within the 88mm vendor column
    _iv_inner_sig = [Paragraph('<b>Signature</b>', ss['BodySmall'])]
    if _iv_sign:
        _iv_inner_sig += [Spacer(1, 1*mm), _iv_sign]
    else:
        _iv_inner_sig.append(Spacer(1, 22*mm))
    _iv_inner_stamp = [Paragraph('<b>Stamp</b>', ss['BodySmall'])]
    if _iv_stamp:
        _iv_inner_stamp += [Spacer(1, 1*mm), _iv_stamp]
    else:
        _iv_inner_stamp.append(Spacer(1, 30*mm))
    _iv_inner_t = Table([[_iv_inner_sig, _iv_inner_stamp]], colWidths=[52*mm, 34*mm])
    _iv_inner_t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                      ('FONTSIZE', (0,0), (-1,-1), 8)]))
    _iv_vendor_cell = [Paragraph('<b>Vendor Signature (with Stamp)</b>', ss['BodySmall']),
                       Spacer(1, 2*mm), _iv_inner_t]
    sig_t = Table(
        [[_iv_vendor_cell, Paragraph('<b>Eligible Consumer Signature</b>', ss['BodySmall'])]],
        colWidths=[88*mm, 87*mm]
    )
    sig_t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(sig_t)
    story.append(Spacer(1, 4*mm))
    story.append(_computer_generated_note(ss))
    story.append(Spacer(1, 2*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  BANK SUBMISSION LETTER
# ══════════════════════════════════════════════════════════════════════════════
def generate_bank_submission_letter(lead: dict, vendor: dict, remaining_loan_amount: str = '') -> bytes:
    buf = BytesIO()
    doc = _doc(buf)
    ss = _styles()
    story = []

    story.append(_vendor_letterhead(vendor, ss))
    story.append(Spacer(1, 6*mm))

    cust_name    = lead.get('customer_name') or lead.get('name', '')
    bank_name    = lead.get('loan_bank', '')
    bank_branch  = lead.get('bank_branch', '')
    loan_acc     = lead.get('bank_account_number', '')
    cust_addr    = lead.get('address', '')
    cust_phone   = lead.get('phone', '') or lead.get('mobile', '')

    # ── Addressee block ───────────────────────────────────────────────────────
    story.append(Paragraph('To,', ss['BodySmall']))
    story.append(Paragraph('The Branch Manager,', ss['BodySmall']))
    story.append(Paragraph(f'<b>{bank_name}</b>,', ss['BodySmall']))
    story.append(Paragraph(f'{bank_branch}.', ss['BodySmall']))
    story.append(Spacer(1, 4*mm))

    # ── Subject ───────────────────────────────────────────────────────────────
    story.append(Paragraph(
        '<b>Subject: Request for Release of Remaining Loan Amount for Solar Installation</b>',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph('Dear Sir/Madam,', ss['BodySmall']))
    story.append(Spacer(1, 3*mm))

    # ── Body paragraphs ───────────────────────────────────────────────────────
    story.append(Paragraph(
        f'I, <b>{cust_name}</b>, holding a loan account number <b>{loan_acc}</b> with your bank, '
        f'would like to inform you that the solar system installation at my premises has been '
        f'successfully completed.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 3*mm))

    amt_str = f'₹ {remaining_loan_amount}/-' if remaining_loan_amount else '₹ ___________/-'
    story.append(Paragraph(
        f'As per the loan agreement, a portion of the loan amount has already been disbursed. '
        f'I kindly request you to release the remaining sanctioned amount of <b>{amt_str}</b> '
        f'to complete the payment to the vendor.',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        'I have attached the necessary documents, including:',
        ss['BodySmall']
    ))
    story.append(Spacer(1, 2*mm))

    bullet_style = ParagraphStyle(
        'Bullet', parent=ss['BodySmall'],
        leftIndent=14, firstLineIndent=0,
        spaceBefore=1, spaceAfter=1,
    )
    for item in [
        'Installation completion report',
        'Invoice from the solar vendor',
        'Photographs of the installed system',
    ]:
        story.append(Paragraph(f'\u2022 {item}', bullet_style))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('I request you to process the disbursement at the earliest.', ss['BodySmall']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('Thanking you.', ss['BodySmall']))
    story.append(Spacer(1, 8*mm))

    # ── Sign-off ──────────────────────────────────────────────────────────────
    story.append(Paragraph('Yours faithfully,', ss['BodySmall']))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(f'<b>{cust_name}</b>,', ss['BodySmall']))
    if cust_addr:
        story.append(Paragraph(f'{cust_addr},', ss['BodySmall']))
    if cust_phone:
        story.append(Paragraph(f'{cust_phone},', ss['BodySmall']))

    story.append(Spacer(1, 6*mm))
    story.append(_partner_logos_footer())

    doc.build(story)
    return buf.getvalue()


# ── Dispatch map ──────────────────────────────────────────────────────────────
DOC_GENERATORS = {
    'quotation': generate_quotation,
    'co_applicant_quotation': generate_co_applicant_quotation,
    'invoice': generate_invoice,
    'annexure_a': generate_annexure_a,
    'annexure_c_completion': generate_annexure_c_completion,
    'annexure_c_technical': generate_annexure_c_technical,
    'commissioning_test_report': generate_commissioning_test_report,
    'synchronisation_certificate': generate_synchronisation_certificate,
    'annexure_iv': generate_annexure_iv,
    'bank_submission_letter': generate_bank_submission_letter,
}

# Required fields per doc type — used by endpoint to return missing-field list
REQUIRED_FIELDS = {
    'quotation': {
        'lead': ['kw_size', 'address'],
        'tech': [],
        'vendor': ['vendor_name', 'gst_number', 'address', 'phone'],
        'params': ['kw_size', 'quote_value', 'final_amount'],
    },
    'co_applicant_quotation': {
        'lead': ['kw_size', 'address', 'co_applicant_name'],
        'tech': [],
        'vendor': ['vendor_name', 'gst_number', 'address', 'phone'],
        'params': ['kw_size', 'quote_value', 'final_amount'],
    },
    'invoice': {
        'lead': ['address'],
        'tech': [],
        'vendor': ['vendor_name', 'gst_number', 'address', 'phone'],
        'params': ['kw_size', 'quote_value', 'final_amount'],
    },
    'annexure_a': {
        'lead': ['kw_size', 'mnre_app_ref', 'sanction_date', 'discom'],
        'tech': ['panel_make', 'panel_capacity_each_w', 'num_panels', 'panel_serial_numbers',
                 'purchase_order_no', 'installation_date',
                 'purchase_order_date', 'cell_manufacturer', 'cell_gst_invoice_no'],
        'vendor': ['vendor_name'],
        'params': [],
    },
    'annexure_c_completion': {
        'lead': ['kw_size', 'mnre_app_ref', 'discom_reg_no', 'sc_number', 'latitude', 'longitude',
                 'discom', 'grid_phase', 'aadhaar_number'],
        'tech': ['panel_make', 'panel_capacity_each_w', 'num_panels', 'panel_type',
                 'tilt_angle', 'inverter_make', 'inverter_model', 'inverter_capacity_kw',
                 'inverter_efficiency_pct', 'inverter_type', 'grid_voltage'],
        'vendor': ['vendor_name'],
        'params': [],
    },
    'annexure_c_technical': {
        'lead': [],
        'tech': [],
        'vendor': ['vendor_name'],
        'params': [],
    },
    'commissioning_test_report': {
        'lead': ['kw_size'],
        'tech': [],  # All commissioning tech fields collected via pre-flight modal
        'vendor': ['vendor_name'],
        'params': [],
    },
    'synchronisation_certificate': {
        'lead': ['kw_size', 'mnre_app_ref', 'consumer_no', 'discom'],
        'tech': [],
        'vendor': ['vendor_name'],
        'params': ['discom_reg_date'],
    },
    'annexure_iv': {
        'lead': ['kw_size', 'sc_number'],
        'tech': [],  # All tech fields collected via pre-flight modal; payload overrides injected
        'vendor': ['vendor_name', 'address'],
        'params': [],
    },
    'bank_submission_letter': {
        'lead': ['loan_bank', 'bank_branch', 'bank_account_number', 'address', 'phone'],
        'tech': [],
        'vendor': ['vendor_name'],
        'params': ['remaining_loan_amount'],
    },
}

FIELD_LABELS = {
    # ── Lead fields (base names) ───────────────────────────────────────────────
    'address': 'Customer Address',
    'kw_size': 'System Size (e.g. 3KW)',
    'co_applicant_name': 'Co-Applicant Name',
    'discom': 'DISCOM Name (e.g. APEPDCL)',
    'sc_number': 'Service Connection (SC) Number',
    'consumer_no': 'DISCOM Consumer Number',
    'sanction_date': 'DISCOM Sanction Date',
    'mnre_app_ref': 'PM Surya Ghar Application Ref No',
    'discom_reg_no': 'DISCOM Registration Number',
    'latitude': 'Site Latitude',
    'longitude': 'Site Longitude',
    'grid_phase': 'Grid Phase (Single / Three Phase)',
    'aadhaar_number': 'Customer Aadhaar Number',
    # ── Lead fields — dotted keys for context-specific lookup ─────────────────
    'lead.address': 'Customer Address',
    'lead.kw_size': 'System Size (e.g. 3KW)',
    'lead.phone': 'Customer Phone',
    'lead.loan_bank': 'Customer Loan Bank Name',
    'lead.bank_branch': 'Bank Branch Address',
    'lead.bank_account_number': 'Customer Loan Account Number',
    # ── Tech fields ───────────────────────────────────────────────────────────
    'panel_make': 'Solar Panel Make',
    'panel_model': 'Panel Model',
    'panel_capacity_each_w': 'Panel Capacity (W each)',
    'num_panels': 'Number of Panels',
    'panel_serial_numbers': 'Panel Serial Numbers (comma-separated)',
    'panel_type': 'Panel Type (e.g. MONO PERC)',
    'panel_technology': 'Panel Technology',
    'tilt_angle': 'Tilt Angle',
    'azimuth': 'Azimuth',
    'cell_manufacturer': 'Cell Manufacturer',
    'inverter_make': 'Inverter Make',
    'inverter_model': 'Inverter Model',
    'inverter_serial_no': 'Inverter Serial Number',
    'inverter_capacity_kw': 'Inverter Capacity (e.g. 3KW)',
    'consumer_category': 'Consumer Category (e.g. HT, LT)',
    'inverter_type': 'Inverter Type',
    'inverter_efficiency_pct': 'Inverter Efficiency (%)',
    'grid_voltage': 'Grid Voltage (e.g. 240 V)',
    'string1_voc': 'String 1 Voc Reading',
    'string2_voc': 'String 2 Voc Reading',
    'purchase_order_no': 'Purchase Order Number',
    'purchase_order_date': 'Purchase Order Date',
    'installation_date': 'Installation Date',
    'cell_manufacturer': 'Cell Manufacturer Name',
    'cell_gst_invoice_no': 'Cell GST Invoice Number',
    # ── Vendor fields (base names) ─────────────────────────────────────────────
    'vendor_name': 'Vendor Name',
    'gst_number': 'Vendor GSTIN',
    'phone': 'Vendor Phone',
    'account_number': 'Vendor Bank Account Number',
    'ifsc_code': 'Vendor IFSC Code',
    # ── Vendor fields — dotted keys (no collision with lead.address) ──────────
    'vendor.address': 'Vendor Address',
    'vendor.vendor_name': 'Vendor Name',
    'vendor.gst_number': 'Vendor GSTIN',
    'vendor.phone': 'Vendor Phone',
    'vendor.account_number': 'Vendor Bank Account Number',
    'vendor.ifsc_code': 'Vendor IFSC Code',
    # ── Lead — bank/loan ──────────────────────────────────────────────────────
    'loan_bank': 'Customer Loan Bank Name',
    'bank_branch': 'Bank Branch Address',
    'bank_account_number': 'Customer Loan Account Number',
    # ── Params ────────────────────────────────────────────────────────────────
    'quote_value': 'Quote Value (₹ incl. GST)',
    'final_amount': 'Final Amount (₹)',
    'subsidy': 'MNRE Subsidy Amount (₹)',
    'remaining_loan_amount': 'Remaining Loan Amount (₹)',
    'discom_reg_date': 'DISCOM Registration Date (DD-MM-YYYY)',
}


# ══════════════════════════════════════════════════════════════════════════════
#  PDF / IMAGE MERGE UTILITIES (for Complete Bundle download)
# ══════════════════════════════════════════════════════════════════════════════
def _image_bytes_to_pdf(img_bytes: bytes) -> bytes:
    """Convert image bytes (JPEG/PNG/WEBP) to a single-page PDF."""
    from PIL import Image as PILImage
    import io as _io
    img = PILImage.open(_io.BytesIO(img_bytes)).convert('RGB')
    out = _io.BytesIO()
    img.save(out, format='PDF')
    return out.getvalue()


def merge_docs_to_pdf(pdf_or_image_list: list) -> bytes:
    """
    Merge a list of (bytes, mime_hint) tuples into one PDF.
    mime_hint is a string: 'pdf', 'image', or a filename (extension is checked).
    Returns merged PDF bytes.
    """
    from pypdf import PdfWriter, PdfReader
    import io as _io

    writer = PdfWriter()
    for item_bytes, mime_hint in pdf_or_image_list:
        if not item_bytes:
            continue
        hint = (mime_hint or '').lower()
        is_image = (
            hint in ('image', 'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp')
            or hint.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'))
            or (item_bytes[:4] in (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1',  # JPEG
                                   b'\x89PNG',))                                # PNG
        )
        if is_image:
            try:
                pdf_bytes = _image_bytes_to_pdf(item_bytes)
            except Exception:
                continue
        else:
            pdf_bytes = item_bytes
        try:
            reader = PdfReader(_io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)
        except Exception:
            continue
    out = _io.BytesIO()
    writer.write(out)
    return out.getvalue()
