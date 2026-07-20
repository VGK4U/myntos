"""
VGK Earner Celebration Card Generator (DC Protocol May 2026)

Generates a dark-blue/gold celebration card image when a VGK income entry is PAID.
Also publishes a shoutout announcement to the feedback/announcements system (visible
on VGK Shoutouts wall — vgk_login.html + voffers page).
Also fires WhatsApp congratulations to the earning member.

All operations are non-fatal: any failure is logged and swallowed.

Public API:
    run_earner_celebration(entry_id)  — call in a daemon thread after mark_paid commits
"""

import io
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CARD_W = 1080
CARD_H = 1080

NAVY       = (10,  27,  62)
NAVY_MID   = (15,  45,  90)
NAVY_LIGHT = (20,  65, 120)
GOLD       = (212, 175,  55)
GOLD_LIGHT = (240, 200,  80)
GOLD_PALE  = (255, 230, 150)
WHITE      = (255, 255, 255)
DARK_GOLD  = (160, 120,  30)

LOGO_PATH  = Path(__file__).resolve().parent.parent.parent.parent / 'frontend' / 'public' / 'vgk4u-logo.png'
FONT_DIR   = Path('/usr/share/fonts/truetype/dejavu')
SYSTEM_USER_ID = 'VGK-SYSTEM'
VGK_SHOUTOUT_CATEGORY_NAME = 'VGK4U Shoutouts'
MNR_SHOUTOUT_CATEGORY_NAME = 'MNR Shoutouts'


# ── Font helpers ─────────────────────────────────────────────────────────────

def _font(bold: bool = False, size: int = 28):
    try:
        from PIL import ImageFont
        name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except Exception:
        from PIL import ImageFont
        return ImageFont.load_default()


def _serif(bold: bool = False, size: int = 28):
    try:
        from PIL import ImageFont
        name = 'DejaVuSerif-Bold.ttf' if bold else 'DejaVuSerif.ttf'
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except Exception:
        return _font(bold, size)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_text_centered(draw, text, y, font, color, shadow=True, img_w=CARD_W):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
    except Exception:
        w = len(text) * (font.size if hasattr(font, 'size') else 14)
    x = (img_w - w) // 2
    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 140))
    draw.text((x, y), text, font=font, fill=color)


def _draw_rounded_rect(draw, x1, y1, x2, y2, r, fill=None, outline=None, width=2):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)


def _text_width(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    except Exception:
        return len(text) * 10


def _circular_crop(img, size):
    """Crop image to a circle, return RGBA image."""
    from PIL import Image, ImageDraw
    img = img.convert('RGBA')
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size, size], fill=255)
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result


def _gradient_bg():
    """Create the dark blue radial gradient background."""
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (CARD_W, CARD_H), NAVY)
    draw = ImageDraw.Draw(img)
    # vertical gradient bands
    for i in range(CARD_H):
        t = i / CARD_H
        r = int(NAVY[0] + (NAVY_MID[0] - NAVY[0]) * t)
        g = int(NAVY[1] + (NAVY_MID[1] - NAVY[1]) * t)
        b = int(NAVY[2] + (NAVY_MID[2] - NAVY[2]) * t)
        draw.line([(0, i), (CARD_W, i)], fill=(r, g, b))
    # radial light burst from center-top
    cx, cy = CARD_W // 2, int(CARD_H * 0.38)
    for radius in range(500, 0, -30):
        alpha = int(10 * (500 - radius) / 500)
        color = (NAVY_LIGHT[0], NAVY_LIGHT[1], NAVY_LIGHT[2] + alpha)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=(*color, 0))
    return img


def _draw_confetti(draw):
    """Scatter gold confetti strips — top 250px only, clear of photo/content."""
    import random
    rng = random.Random(42)
    colors = [GOLD, GOLD_LIGHT, GOLD_PALE, (255, 200, 50), (220, 180, 40)]
    for _ in range(80):
        x = rng.randint(0, CARD_W)
        y = rng.randint(0, 250)
        w = rng.randint(4, 14)
        h = rng.randint(14, 40)
        angle = rng.randint(-60, 60)
        col = rng.choice(colors)
        # Draw as a tilted thin rectangle (approximate with polygon)
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        hw, hh = w / 2, h / 2
        pts = [
            (x + (-hw * cos_a - (-hh) * sin_a), y + (-hw * sin_a + (-hh) * cos_a)),
            (x + (hw * cos_a  - (-hh) * sin_a), y + (hw * sin_a  + (-hh) * cos_a)),
            (x + (hw * cos_a  - hh * sin_a),    y + (hw * sin_a  + hh * cos_a)),
            (x + (-hw * cos_a - hh * sin_a),    y + (-hw * sin_a + hh * cos_a)),
        ]
        draw.polygon(pts, fill=col)


# ── Card composer ─────────────────────────────────────────────────────────────

def compose_earner_card(
    partner_name: str,
    partner_code: str,
    location: str,
    designation: str,
    gross_amount: float,
    overall_earnings: float,
    photo_bytes: Optional[bytes] = None,
    name_title: str = '',
) -> bytes:
    """
    Compose the celebration PNG card (1080×1080).

    Fully centered vertical layout — uses ALL available space:
      [24 ]  VGK4U Logo (80px)
      [110]  "Congratulations!" serif 54pt
      [182]  "ACHIEVEMENT UNLOCKED" pill badge (46px)
      [234]  ★ stars row (24px)
      [264]  Photo circle (240px, elevated with drop-shadow + gold ring)  ← ends at 504
      [514]  Partner name (bold 38pt, auto-shrink)
      [568]  Designation (17pt)
      [600]  Thin gold separator
      [612]  INFO STRIP — 3 cells, h=110  (label 14pt, value 26pt)
      [730]  EARNINGS BOX — 2 cells, h=118 (label 14pt, value 50pt)
      [856]  "REWARDED WITH CASH REWARD" banner (68px)
      [932]  Gold footer bar "TOGETHER WE ACHIEVE MORE!" (62px)
      [1002] ONE TEAM | ONE VISION | ONE SUCCESS row (52px)
      [1058] Bottom quote line (20px)
      [1080] border margin
    """
    from PIL import Image, ImageDraw, ImageFilter

    def fmt_inr(val):
        try:
            return f'\u20b9{int(float(val)):,}'
        except Exception:
            return str(val)

    # ── Background ──────────────────────────────────────────────────────────
    img = _gradient_bg()
    draw = ImageDraw.Draw(img, 'RGBA')

    # Double gold border
    _draw_rounded_rect(draw, 8,  8,  CARD_W - 8,  CARD_H - 8,  20, outline=GOLD,        width=6)
    _draw_rounded_rect(draw, 18, 18, CARD_W - 18, CARD_H - 18, 15, outline=(*GOLD, 80),  width=2)

    # Confetti — top 260px only
    _draw_confetti(draw)

    # ── S1: Logo (y=24, h=80) ───────────────────────────────────────────────
    LOGO_Y, LOGO_H = 24, 80
    try:
        logo = Image.open(LOGO_PATH).convert('RGBA')
        scale  = LOGO_H / logo.height
        logo_w = int(logo.width * scale)
        logo   = logo.resize((logo_w, LOGO_H), Image.LANCZOS)
        img.paste(logo, ((CARD_W - logo_w) // 2, LOGO_Y), logo)
    except Exception as e:
        logger.warning(f'[EARNER-CARD] logo load failed: {e}')
        draw.text((CARD_W // 2 - 70, LOGO_Y + 12), 'VGK4U', font=_font(True, 52), fill=GOLD)

    # ── S2: "Congratulations!" (y=110, h=66) — dark backdrop to cut through confetti
    CONG_FONT = _serif(True, 54)
    cong_text = 'Congratulations!'
    cong_w    = _text_width(draw, cong_text, CONG_FONT)
    CONG_Y    = 110
    # Semi-transparent pill behind text so confetti doesn't obscure it
    PAD_X, PAD_Y = 32, 8
    cx1 = (CARD_W - cong_w) // 2 - PAD_X
    cx2 = (CARD_W + cong_w) // 2 + PAD_X
    cy1 = CONG_Y - PAD_Y
    cy2 = CONG_Y + 62 + PAD_Y
    _draw_rounded_rect(draw, cx1, cy1, cx2, cy2, 18, fill=(0, 0, 20, 160))
    _draw_text_centered(draw, cong_text, CONG_Y, CONG_FONT, GOLD_LIGHT)

    # ── S3: Achievement badge pill (y=182, h=46) ────────────────────────────
    BADGE_Y = 182
    _draw_rounded_rect(draw, 50, BADGE_Y, CARD_W - 50, BADGE_Y + 46, 23,
                       fill=(0, 0, 30, 210), outline=GOLD, width=2)
    _draw_text_centered(draw, '✦  ACHIEVEMENT UNLOCKED  ✦', BADGE_Y + 12,
                        _font(True, 22), GOLD_LIGHT)

    # ── S4: Stars (y=234, h=24) ─────────────────────────────────────────────
    _draw_text_centered(draw, '★     ★     ★     ★     ★', 234, _font(True, 22), GOLD)

    # ── S5: Photo circle (y=264, size=240) — elevated with drop-shadow ───────
    PHOTO_SIZE = 240
    PHOTO_Y    = 264
    PHOTO_X    = (CARD_W - PHOTO_SIZE) // 2   # 420

    # Drop shadow (elevation effect — offset 0, +10)
    SHADOW_OFF = 10
    sh_size    = PHOTO_SIZE + 20
    shadow     = Image.new('RGBA', (sh_size, sh_size), (0, 0, 0, 0))
    sd2        = ImageDraw.Draw(shadow)
    sd2.ellipse([0, 0, sh_size - 1, sh_size - 1], fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img.paste(shadow,
              (PHOTO_X - 10, PHOTO_Y + SHADOW_OFF - 10),
              shadow)

    # Outer gold glow
    GLOW_PAD  = 22
    glow_size = PHOTO_SIZE + GLOW_PAD * 2
    glow_img  = Image.new('RGBA', (glow_size, glow_size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_img)
    gd.ellipse([0, 0, glow_size - 1, glow_size - 1], fill=(*GOLD, 100))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(16))
    img.paste(glow_img, (PHOTO_X - GLOW_PAD, PHOTO_Y - GLOW_PAD), glow_img)

    # Outer gold ring (10px)
    RING      = 10
    ring_size = PHOTO_SIZE + RING * 2
    ring_img  = Image.new('RGBA', (ring_size, ring_size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_img)
    rd.ellipse([0, 0, ring_size - 1, ring_size - 1], fill=GOLD)
    img.paste(ring_img, (PHOTO_X - RING, PHOTO_Y - RING), ring_img)

    # Inner thin white separator ring
    sep_size = PHOTO_SIZE + 2
    sep_img  = Image.new('RGBA', (sep_size, sep_size), (0, 0, 0, 0))
    sd3 = ImageDraw.Draw(sep_img)
    sd3.ellipse([0, 0, sep_size - 1, sep_size - 1], fill=(255, 255, 255, 50))
    img.paste(sep_img, (PHOTO_X - 1, PHOTO_Y - 1), sep_img)

    # Photo or placeholder
    if photo_bytes:
        try:
            member_img = Image.open(io.BytesIO(photo_bytes))
            circular   = _circular_crop(member_img, PHOTO_SIZE)
            img.paste(circular, (PHOTO_X, PHOTO_Y), circular)
        except Exception as e:
            logger.warning(f'[EARNER-CARD] member photo failed: {e}')
            _draw_placeholder_avatar(img, draw, PHOTO_X, PHOTO_Y, PHOTO_SIZE, partner_name)
    else:
        _draw_placeholder_avatar(img, draw, PHOTO_X, PHOTO_Y, PHOTO_SIZE, partner_name)

    # ── S6: Partner name with optional title (y=514, h=50) ──────────────────
    NAME_Y = PHOTO_Y + PHOTO_SIZE + 10    # 514
    # Normalize title: "Mr" → "Mr.", "mrs" → "Mrs." etc.
    _t = (name_title or '').strip().rstrip('.')
    title_prefix = (_t.capitalize() + '. ') if _t else ''
    name_disp = title_prefix + partner_name.strip().upper()
    name_font = _font(True, 38)
    while name_disp and _text_width(draw, name_disp, name_font) > 980:
        name_font = _font(True, max(20, name_font.size - 2))
    _draw_text_centered(draw, name_disp, NAME_Y, name_font, GOLD_LIGHT)

    # ── S7: Designation (y=568, h=26) ───────────────────────────────────────
    DESG_Y    = NAME_Y + 54
    desg_text = (designation or 'Channel Partner')[:40]
    _draw_text_centered(draw, desg_text, DESG_Y, _font(False, 17), (*WHITE, 190))

    # ── S8: Thin gold separator (y=600) ─────────────────────────────────────
    SEP_Y = DESG_Y + 30
    draw.line([(50, SEP_Y), (CARD_W - 50, SEP_Y)], fill=(*GOLD, 160), width=2)

    # ── S9: INFO STRIP (h=80) — 2 cells: VGK ID | LOCATION ────────────────
    INFO_Y = SEP_Y + 12
    INFO_H = 80
    _draw_rounded_rect(draw, 26, INFO_Y, CARD_W - 26, INFO_Y + INFO_H, 14,
                       fill=(0, 0, 44, 185), outline=GOLD, width=2)
    STRIP_W   = CARD_W - 52          # 1028px
    half_strip = STRIP_W // 2
    loc_label = 'LOCATION' if (location and location.strip()) else 'ROLE'
    loc_val   = (location.strip() if location and location.strip()
                 else (designation or 'Channel Partner'))[:24]
    info_cells = [
        ('VGK ID',  partner_code),
        (loc_label, loc_val),
    ]
    cx_pos = 26
    for ci, (lbl, val) in enumerate(info_cells):
        if ci > 0:
            draw.line([(cx_pos, INFO_Y + 8), (cx_pos, INFO_Y + INFO_H - 8)],
                      fill=(*GOLD, 140), width=1)
        draw.text((cx_pos + 18, INFO_Y + 9),  lbl, font=_font(True, 13), fill=GOLD)
        draw.text((cx_pos + 18, INFO_Y + 28), val, font=_font(True, 24), fill=WHITE)
        cx_pos += half_strip

    # ── S10: EARNINGS BOX (h=90) — large numbers ────────────────────────────
    EARN_Y = INFO_Y + INFO_H + 8
    EARN_H = 90
    _draw_rounded_rect(draw, 26, EARN_Y, CARD_W - 26, EARN_Y + EARN_H, 14,
                       fill=(0, 8, 58, 220), outline=GOLD, width=2)
    half_w = (CARD_W - 52) // 2

    # Left cell
    draw.text((40, EARN_Y + 9),  'AMOUNT EARNED',       font=_font(True, 13),  fill=(*WHITE, 190))
    draw.text((40, EARN_Y + 28), fmt_inr(gross_amount),  font=_font(True, 44),  fill=GOLD_LIGHT)
    # Divider
    DX = 26 + half_w
    draw.line([(DX, EARN_Y + 10), (DX, EARN_Y + EARN_H - 10)], fill=GOLD, width=2)
    # Right cell
    rx2 = DX + 16
    draw.text((rx2, EARN_Y + 9),  'LIFETIME EARNINGS',      font=_font(True, 13),  fill=(*WHITE, 190))
    draw.text((rx2, EARN_Y + 28), fmt_inr(overall_earnings), font=_font(True, 44),  fill=GOLD)

    # ── S11: "REWARDED WITH CASH REWARD" banner (y=856, h=68) ───────────────
    BAND_Y = EARN_Y + EARN_H + 8
    _draw_rounded_rect(draw, 26, BAND_Y, CARD_W - 26, BAND_Y + 68, 14,
                       fill=(*DARK_GOLD, 230), outline=GOLD, width=2)
    _draw_text_centered(draw, '* *   REWARDED WITH CASH REWARD   * *', BAND_Y + 20,
                        _font(True, 24), (255, 255, 220), shadow=False)

    # ── S12: Gold footer bar (y=932, h=62) ──────────────────────────────────
    FOOT_Y = BAND_Y + 76
    draw.rectangle([0, FOOT_Y, CARD_W, FOOT_Y + 62], fill=GOLD)
    _draw_text_centered(draw, 'TOGETHER,  WE ACHIEVE MORE!',
                        FOOT_Y + 14, _font(True, 28), NAVY, shadow=False)

    # ── S13: Icons row (y=1002, h=52) ───────────────────────────────────────
    ICON_Y  = FOOT_Y + 66
    seg_w   = CARD_W // 3
    icon_symbols = ['\u2605\u2605\u2605', '\u25ba\u25ba\u25ba', '\u2714\u2714\u2714']
    icon_labels  = ['ONE TEAM', 'ONE VISION', 'ONE SUCCESS']
    for i, label in enumerate(icon_labels):
        sx = i * seg_w
        if i > 0:
            draw.line([(sx, ICON_Y + 4), (sx, ICON_Y + 48)], fill=GOLD, width=1)
        lw_ = _text_width(draw, label, _font(True, 15))
        draw.text((sx + (seg_w - lw_) // 2, ICON_Y + 4), label, font=_font(True, 15), fill=WHITE)
        sym = icon_symbols[i]
        sw  = _text_width(draw, sym, _font(True, 19))
        draw.text((sx + (seg_w - sw) // 2, ICON_Y + 26), sym, font=_font(True, 19), fill=GOLD)

    # ── S14: Bottom quote ────────────────────────────────────────────────────
    draw.line([(40, ICON_Y + 56), (CARD_W - 40, ICON_Y + 56)], fill=(*GOLD, 150), width=1)
    _draw_text_centered(draw, '"Your commitment inspires us all and drives our mission forward."',
                        ICON_Y + 62, _font(False, 26), (*GOLD_LIGHT, 230))

    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def compose_bonanza_slab_card(
    partner_name: str,
    partner_code: str,
    location: str,
    designation: str,
    bonanza_title: str,
    slab_extra: float,
    slab_base: float,
    overall_earnings: float,
    photo_bytes: Optional[bytes] = None,
    name_title: str = '',
    deal_count: int = 1,
) -> bytes:
    """
    DC_BONANZA_SLABWISE_001 — Slab Wise bonanza celebration card (1080×1080).
    Per-file model: bonanza pays slab_extra × deal_count.

    Earnings box shows:
      • ₹<slab_extra> × N files = ₹<slab_extra × deal_count>  (gold, large)
      • ₹<slab_base>/file — Solar File Advance base            (white, small)
      • ₹<total incl base × deal_count>                        (gold, medium)

    Badge shows the bonanza campaign title instead of generic "ACHIEVEMENT UNLOCKED".
    """
    from PIL import Image, ImageDraw, ImageFilter

    slab_total_bonanza = slab_extra * deal_count          # what bonanza pays
    total = (slab_extra + slab_base) * deal_count         # display total incl base

    def fmt_inr(val):
        try:
            return f'\u20b9{int(float(val)):,}'
        except Exception:
            return str(val)

    img = _gradient_bg()
    draw = ImageDraw.Draw(img, 'RGBA')

    _draw_rounded_rect(draw, 8,  8,  CARD_W - 8,  CARD_H - 8,  20, outline=GOLD,       width=6)
    _draw_rounded_rect(draw, 18, 18, CARD_W - 18, CARD_H - 18, 15, outline=(*GOLD, 80), width=2)
    _draw_confetti(draw)

    # Logo
    LOGO_Y, LOGO_H = 24, 80
    try:
        logo = Image.open(LOGO_PATH).convert('RGBA')
        scale  = LOGO_H / logo.height
        logo_w = int(logo.width * scale)
        logo   = logo.resize((logo_w, LOGO_H), Image.LANCZOS)
        img.paste(logo, ((CARD_W - logo_w) // 2, LOGO_Y), logo)
    except Exception:
        draw.text((CARD_W // 2 - 70, LOGO_Y + 12), 'VGK4U', font=_font(True, 52), fill=GOLD)

    # "Congratulations!"
    CONG_FONT = _serif(True, 54)
    cong_text = 'Congratulations!'
    cong_w    = _text_width(draw, cong_text, CONG_FONT)
    CONG_Y    = 110
    PAD_X, PAD_Y = 32, 8
    cx1 = (CARD_W - cong_w) // 2 - PAD_X
    cx2 = (CARD_W + cong_w) // 2 + PAD_X
    _draw_rounded_rect(draw, cx1, CONG_Y - PAD_Y, cx2, CONG_Y + 62 + PAD_Y, 18, fill=(0, 0, 20, 160))
    _draw_text_centered(draw, cong_text, CONG_Y, CONG_FONT, GOLD_LIGHT)

    # Bonanza title badge (replaces generic "ACHIEVEMENT UNLOCKED")
    BADGE_Y = 182
    _draw_rounded_rect(draw, 50, BADGE_Y, CARD_W - 50, BADGE_Y + 46, 23,
                       fill=(80, 0, 100, 220), outline=GOLD, width=2)
    title_short = bonanza_title[:48] if bonanza_title else 'SLAB WISE BONANZA'
    _draw_text_centered(draw, f'\u2726  {title_short.upper()}  \u2726', BADGE_Y + 12,
                        _font(True, 20), GOLD_LIGHT)

    # Stars
    _draw_text_centered(draw, '\u2605     \u2605     \u2605     \u2605     \u2605', 234, _font(True, 22), GOLD)

    # Photo circle
    PHOTO_SIZE = 240
    PHOTO_Y    = 264
    PHOTO_X    = (CARD_W - PHOTO_SIZE) // 2
    SHADOW_OFF = 10
    sh_size    = PHOTO_SIZE + 20
    shadow     = Image.new('RGBA', (sh_size, sh_size), (0, 0, 0, 0))
    sd2        = ImageDraw.Draw(shadow)
    sd2.ellipse([0, 0, sh_size - 1, sh_size - 1], fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img.paste(shadow, (PHOTO_X - 10, PHOTO_Y + SHADOW_OFF - 10), shadow)
    GLOW_PAD  = 22
    glow_size = PHOTO_SIZE + GLOW_PAD * 2
    glow_img  = Image.new('RGBA', (glow_size, glow_size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_img)
    gd.ellipse([0, 0, glow_size - 1, glow_size - 1], fill=(*GOLD, 100))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(16))
    img.paste(glow_img, (PHOTO_X - GLOW_PAD, PHOTO_Y - GLOW_PAD), glow_img)
    RING      = 10
    ring_size = PHOTO_SIZE + RING * 2
    ring_img  = Image.new('RGBA', (ring_size, ring_size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_img)
    rd.ellipse([0, 0, ring_size - 1, ring_size - 1], fill=GOLD)
    img.paste(ring_img, (PHOTO_X - RING, PHOTO_Y - RING), ring_img)
    sep_size = PHOTO_SIZE + 2
    sep_img  = Image.new('RGBA', (sep_size, sep_size), (0, 0, 0, 0))
    sd3 = ImageDraw.Draw(sep_img)
    sd3.ellipse([0, 0, sep_size - 1, sep_size - 1], fill=(255, 255, 255, 50))
    img.paste(sep_img, (PHOTO_X - 1, PHOTO_Y - 1), sep_img)
    if photo_bytes:
        try:
            member_img = Image.open(io.BytesIO(photo_bytes))
            circular   = _circular_crop(member_img, PHOTO_SIZE)
            img.paste(circular, (PHOTO_X, PHOTO_Y), circular)
        except Exception:
            _draw_placeholder_avatar(img, draw, PHOTO_X, PHOTO_Y, PHOTO_SIZE, partner_name)
    else:
        _draw_placeholder_avatar(img, draw, PHOTO_X, PHOTO_Y, PHOTO_SIZE, partner_name)

    # Partner name
    NAME_Y = PHOTO_Y + PHOTO_SIZE + 10
    _t = (name_title or '').strip().rstrip('.')
    title_prefix = (_t.capitalize() + '. ') if _t else ''
    name_disp = title_prefix + partner_name.strip().upper()
    name_font = _font(True, 38)
    while name_disp and _text_width(draw, name_disp, name_font) > 980:
        name_font = _font(True, max(20, name_font.size - 2))
    _draw_text_centered(draw, name_disp, NAME_Y, name_font, GOLD_LIGHT)

    # Designation
    DESG_Y = NAME_Y + 54
    _draw_text_centered(draw, (designation or 'Channel Partner')[:40], DESG_Y, _font(False, 17), (*WHITE, 190))

    # Separator
    SEP_Y = DESG_Y + 30
    draw.line([(50, SEP_Y), (CARD_W - 50, SEP_Y)], fill=(*GOLD, 160), width=2)

    # Info strip (VGK ID | Location)
    INFO_Y = SEP_Y + 12
    INFO_H = 80
    _draw_rounded_rect(draw, 26, INFO_Y, CARD_W - 26, INFO_Y + INFO_H, 14,
                       fill=(0, 0, 44, 185), outline=GOLD, width=2)
    STRIP_W   = CARD_W - 52
    half_strip = STRIP_W // 2
    loc_label = 'LOCATION' if (location and location.strip()) else 'ROLE'
    loc_val   = (location.strip() if location and location.strip() else (designation or 'Partner'))[:24]
    cx_pos = 26
    for ci, (lbl, val) in enumerate([('VGK ID', partner_code), (loc_label, loc_val)]):
        if ci > 0:
            draw.line([(cx_pos, INFO_Y + 8), (cx_pos, INFO_Y + INFO_H - 8)], fill=(*GOLD, 140), width=1)
        draw.text((cx_pos + 18, INFO_Y + 9),  lbl, font=_font(True, 13), fill=GOLD)
        draw.text((cx_pos + 18, INFO_Y + 28), val, font=_font(True, 24), fill=WHITE)
        cx_pos += half_strip

    # ── SLAB EARNINGS BOX — per-file model ───────────────────────────────────
    EARN_Y = INFO_Y + INFO_H + 8
    EARN_H = 158
    _draw_rounded_rect(draw, 26, EARN_Y, CARD_W - 26, EARN_Y + EARN_H, 14,
                       fill=(0, 8, 58, 220), outline=GOLD, width=2)

    # Row 1 LEFT: ₹3000/file × N files = ₹Total Slab (bonanza payout)
    per_file_label = f'{fmt_inr(slab_extra)}/file \xd7 {deal_count} file{"s" if deal_count != 1 else ""} = {fmt_inr(slab_total_bonanza)}'
    draw.text((46, EARN_Y + 10), 'SLAB BONUS (PER FILE)',   font=_font(True, 12), fill=(*WHITE, 190))
    draw.text((46, EARN_Y + 30), fmt_inr(slab_total_bonanza), font=_font(True, 46), fill=GOLD_LIGHT)
    draw.text((46, EARN_Y + 78), per_file_label,              font=_font(False, 14), fill=(*WHITE, 160))

    # Divider between left and right
    DX = CARD_W // 2
    draw.line([(DX, EARN_Y + 12), (DX, EARN_Y + EARN_H - 12)], fill=GOLD, width=2)

    # Row 1 RIGHT: Lifetime earnings
    rx2 = DX + 16
    draw.text((rx2, EARN_Y + 10), 'LIFETIME EARNINGS',        font=_font(True, 13), fill=(*WHITE, 190))
    draw.text((rx2, EARN_Y + 30), fmt_inr(overall_earnings),   font=_font(True, 46), fill=GOLD)

    # Row 2 (bottom strip): base ref + grand total
    BASE_ROW_Y = EARN_Y + 100
    draw.line([(46, BASE_ROW_Y), (CARD_W - 46, BASE_ROW_Y)], fill=(*GOLD, 80), width=1)
    draw.text((46, BASE_ROW_Y + 8), f'Solar Advance {fmt_inr(slab_base)}/file (display only)',
              font=_font(False, 14), fill=(*WHITE, 140))
    total_str = f'= {fmt_inr(total)} incl. base'
    tw = _text_width(draw, total_str, _font(True, 15))
    draw.text((CARD_W - 46 - tw, BASE_ROW_Y + 7), total_str, font=_font(True, 15), fill=GOLD_LIGHT)

    # Slab banner
    BAND_Y = EARN_Y + EARN_H + 8
    _draw_rounded_rect(draw, 26, BAND_Y, CARD_W - 26, BAND_Y + 68, 14,
                       fill=(*DARK_GOLD, 230), outline=GOLD, width=2)
    _draw_text_centered(draw, f'\u2605 \u2605   SLAB WISE \xb7 {deal_count} FILE{"S" if deal_count != 1 else ""} \xb7 {fmt_inr(slab_total_bonanza)} EARNED   \u2605 \u2605',
                        BAND_Y + 20, _font(True, 20), (255, 255, 220), shadow=False)

    # Gold footer
    FOOT_Y = BAND_Y + 76
    draw.rectangle([0, FOOT_Y, CARD_W, FOOT_Y + 62], fill=GOLD)
    _draw_text_centered(draw, 'TOGETHER,  WE ACHIEVE MORE!', FOOT_Y + 14, _font(True, 28), NAVY, shadow=False)

    # Icons row
    ICON_Y  = FOOT_Y + 66
    seg_w   = CARD_W // 3
    for i, (sym, label) in enumerate([('\u2605\u2605\u2605', 'ONE TEAM'), ('\u25ba\u25ba\u25ba', 'ONE VISION'), ('\u2714\u2714\u2714', 'ONE SUCCESS')]):
        sx = i * seg_w
        if i > 0:
            draw.line([(sx, ICON_Y + 4), (sx, ICON_Y + 48)], fill=GOLD, width=1)
        lw_ = _text_width(draw, label, _font(True, 15))
        draw.text((sx + (seg_w - lw_) // 2, ICON_Y + 4), label, font=_font(True, 15), fill=WHITE)
        sw  = _text_width(draw, sym, _font(True, 19))
        draw.text((sx + (seg_w - sw) // 2, ICON_Y + 26), sym, font=_font(True, 19), fill=GOLD)

    # Bottom quote
    draw.line([(40, ICON_Y + 56), (CARD_W - 40, ICON_Y + 56)], fill=(*GOLD, 150), width=1)
    _draw_text_centered(draw, '"Your commitment inspires us all and drives our mission forward."',
                        ICON_Y + 62, _font(False, 26), (*GOLD_LIGHT, 230))

    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _draw_placeholder_avatar(img, draw, x, y, size, partner_name: str = '?'):
    """
    Gold-filled circle with dark navy initials — clearly visible on any background.
    Signature: takes img + draw so it can paste a circular overlay.
    """
    from PIL import Image, ImageDraw as PID
    overlay = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    od      = PID.Draw(overlay)

    # Gold filled circle
    od.ellipse([0, 0, size - 1, size - 1], fill=GOLD)

    # Inner lighter gold ring for depth
    pad = size // 12
    od.ellipse([pad, pad, size - 1 - pad, size - 1 - pad], fill=GOLD_LIGHT)

    # Initials — up to 2 chars, dark navy
    initials = ''
    parts = partner_name.strip().split()
    if parts:
        initials = parts[0][0].upper()
        if len(parts) > 1:
            initials += parts[-1][0].upper()
    init_font_size = size // 2
    try:
        from PIL import ImageFont
        init_font = ImageFont.truetype(str(FONT_DIR / 'DejaVuSans-Bold.ttf'), init_font_size)
    except Exception:
        from PIL import ImageFont
        init_font = ImageFont.load_default()
    bbox  = od.textbbox((0, 0), initials, font=init_font)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    ix    = (size - tw) // 2 - bbox[0]
    iy    = (size - th) // 2 - bbox[1]
    od.text((ix, iy), initials, font=init_font, fill=NAVY)

    img.paste(overlay, (x, y), overlay)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_shoutout_category(db, category_name: str = None) -> int:
    """Return (or create) a feedback category by name. Defaults to VGK4U Shoutouts."""
    from sqlalchemy import text
    name = category_name or VGK_SHOUTOUT_CATEGORY_NAME
    desc_map = {
        VGK_SHOUTOUT_CATEGORY_NAME: 'Auto-generated earner celebration shoutouts from VGK income payments',
        MNR_SHOUTOUT_CATEGORY_NAME: 'Auto-generated earner celebration shoutouts from MNR income payments',
    }
    row = db.execute(text(
        "SELECT id FROM feedback_categories WHERE name = :n LIMIT 1"
    ), {'n': name}).fetchone()
    if row:
        return row[0]
    try:
        result = db.execute(text("""
            INSERT INTO feedback_categories (name, description, is_active)
            VALUES (:n, :d, true)
            RETURNING id
        """), {'n': name, 'd': desc_map.get(name, 'Earner shoutouts')})
        db.flush()
        row = result.fetchone()
        return row[0] if row else 10
    except Exception:
        db.rollback()
        row = db.execute(text(
            "SELECT id FROM feedback_categories WHERE name = :n LIMIT 1"
        ), {'n': name}).fetchone()
        return row[0] if row else 10


def _get_kyc_photo_bytes(db, partner_id: int) -> Optional[bytes]:
    """
    Fetch the best available photo for the partner.
    Priority order:
      1. vgk_kyc_documents.profile_photo  (VGK-specific upload)
      2. kyc_document.passport_photo       (MNR KYC — approved preferred)
    Supports both object_storage and local (uploaded_files/) storage types.
    """
    from sqlalchemy import text
    from app.services.object_storage import storage_service
    import os

    UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / 'uploaded_files'

    def _load(file_path: str, storage_type: str) -> Optional[bytes]:
        if not file_path:
            return None
        # Object storage (default)
        if storage_type in ('object_storage', None, ''):
            try:
                data = storage_service.download_file(file_path)
                if data:
                    return data
            except Exception as e1:
                logger.warning(f'[EARNER-CARD] object storage fetch failed ({file_path}): {e1}')
        # Local file fallback
        local = UPLOAD_ROOT / file_path
        if local.exists():
            try:
                return local.read_bytes()
            except Exception as e2:
                logger.warning(f'[EARNER-CARD] local read failed ({local}): {e2}')
        # Last resort: try object storage anyway
        try:
            return storage_service.download_file(file_path)
        except Exception:
            return None

    # 1. VGK profile photo
    row = db.execute(text("""
        SELECT file_path, original_storage_type FROM vgk_kyc_documents
        WHERE partner_id = :pid AND document_type = 'profile_photo'
        ORDER BY uploaded_at DESC NULLS LAST LIMIT 1
    """), {'pid': partner_id}).fetchone()
    if row and row[0]:
        data = _load(row[0], row[1])
        if data:
            logger.info(f'[EARNER-CARD] VGK profile_photo loaded for partner {partner_id}')
            return data

    # 2. MNR KYC passport_photo (approved first, then any)
    row = db.execute(text("""
        SELECT file_path, original_storage_type FROM kyc_document
        WHERE partner_id = :pid AND document_type = 'passport_photo'
        ORDER BY
            CASE WHEN status ILIKE 'approved' THEN 0 ELSE 1 END,
            uploaded_at DESC NULLS LAST
        LIMIT 1
    """), {'pid': partner_id}).fetchone()
    if row and row[0]:
        data = _load(row[0], row[1])
        if data:
            logger.info(f'[EARNER-CARD] KYC passport_photo loaded for partner {partner_id}')
            return data

    logger.info(f'[EARNER-CARD] No KYC photo found for partner {partner_id} — using initials')
    return None


def _ensure_system_user(db):
    """Return a real user id (max 12 chars) that exists in the user table."""
    from sqlalchemy import text
    row = db.execute(text(
        "SELECT id FROM \"user\" WHERE LENGTH(id) <= 12 ORDER BY id LIMIT 1"
    )).fetchone()
    return row[0] if row else SYSTEM_USER_ID


def _publish_shoutout(db, entry_id: int, category_id: int, system_uid: str,
                      partner_name: str, partner_code: str, gross: float,
                      card_storage_key: str,
                      visible_to: str = 'vgk') -> Optional[int]:
    """Insert feedback_submissions + feedback_media rows for the earner shoutout."""
    from sqlalchemy import text
    from datetime import timezone

    now = datetime.now(timezone.utc)
    inr_fmt = f'\u20b9{int(gross):,}'
    network = 'VGK' if visible_to == 'vgk' else 'MNR'
    title = f'{partner_name} earned {inr_fmt} — {network} Cash Commission'
    description = (
        f'Congratulations to {partner_name} ({partner_code}) on earning '
        f'{inr_fmt} in {network} Cash Commission! Another Achievement Unlocked! '
        f'Keep Leading. Keep Inspiring. Keep Growing! — Team {network}'
    )

    # Idempotency: one shoutout per income entry
    existing2 = db.execute(text("""
        SELECT id FROM feedback_submissions
        WHERE description LIKE :pat AND category_id = :cid LIMIT 1
    """), {'pat': f'%entry_id:{entry_id}%', 'cid': category_id}).fetchone()
    if existing2:
        # If a new card was generated, refresh the media record so the shoutout
        # wall always shows the latest card (avoids stale-card-in-shoutout bug).
        if card_storage_key:
            db.execute(text("""
                UPDATE feedback_media
                SET file_path             = :fp,
                    original_storage_type = 'object_storage',
                    original_storage_key  = :fp
                WHERE submission_id = :sid
            """), {'fp': card_storage_key, 'sid': existing2[0]})
            db.flush()
        return existing2[0]

    desc_with_ref = description + f' [entry_id:{entry_id}]'
    result = db.execute(text("""
        INSERT INTO feedback_submissions
          (category_id, submission_type, title, description, status,
           is_visible, visible_to, user_id, submitted_at, approved_at,
           approved_by, approved_media_count, rejected_media_count,
           shares_count, views_count, display_order)
        VALUES
          (:cat, 'TEXT', :title, :desc, 'APPROVED',
           true, :vto, :uid, :now, :now,
           'VGK-SYS', 1, 0,
           0, 0, NULL)
        RETURNING id
    """), {
        'cat': category_id, 'title': title, 'desc': desc_with_ref,
        'uid': system_uid, 'now': now, 'vto': visible_to,
    })
    db.flush()
    sub_row = result.fetchone()
    if not sub_row:
        return None
    sub_id = sub_row[0]

    # Attach the card image as approved media
    if card_storage_key:
        db.execute(text("""
            INSERT INTO feedback_media
              (submission_id, file_path, file_type, media_status, is_visible,
               uploaded_at, uses_new_naming,
               original_storage_type, original_storage_key)
            VALUES
              (:sid, :fp, 'image', 'APPROVED', true, :now, true,
               'object_storage', :fp)
        """), {'sid': sub_id, 'fp': card_storage_key, 'now': now})

    db.flush()
    return sub_id


def _card_public_url(card_storage_key: str) -> str:
    """
    Build an absolute HTTPS URL for a card stored in object storage.
    Canonical pattern (matches crm.py / staff_ai_calling.py):
      - Production (REPL_DEPLOYMENT set or PROD_DATABASE_URL set) → https://mnrteam.com
      - Dev → https://{REPLIT_DEV_DOMAIN}
    Returns '' if neither domain signal is available — callers must handle empty string
    and will skip the image send gracefully.
    """
    import os as _os
    if not card_storage_key:
        return ''
    if _os.environ.get('REPL_DEPLOYMENT') or _os.environ.get('PROD_DATABASE_URL'):
        base = 'https://mnrteam.com'
    else:
        dev_domain = _os.environ.get('REPLIT_DEV_DOMAIN', '').strip()
        if not dev_domain:
            return ''
        base = f'https://{dev_domain}'
    return f'{base}/storage/{card_storage_key}'


def _send_earner_card_image(db, phone: str, card_url: str, partner_name: str) -> dict:
    """
    Send the earner card PNG as a WhatsApp image message via Meta Cloud API.
    Fires a direct 'image' type message (not a template) so no Meta approval needed.

    Returns a dict with keys:
        success  bool   — True only when Meta returns HTTP 200
        reason   str    — populated on skip or failure ('invalid_phone', 'no_credentials',
                          'api_error:<status>', 'exception:<msg>')
        wamid    str    — Meta message ID on success
    The text congratulations message is always sent separately regardless of this result.
    """
    import re as _re
    import requests as _req
    from app.services.whatsapp_auto_service import _get_meta_creds, _is_valid_phone

    if not _is_valid_phone(phone):
        logger.warning(f'[EARNER-WA-IMG] Invalid/placeholder phone {phone} — skipping image')
        return {'success': False, 'reason': 'invalid_phone', 'wamid': ''}

    token, phone_id = _get_meta_creds(db)
    if not token or not phone_id:
        logger.warning('[EARNER-WA-IMG] No Meta credentials — skipping image send')
        return {'success': False, 'reason': 'no_credentials', 'wamid': ''}

    _digits = _re.sub(r'\D', '', phone)
    recipient = _digits if (_digits.startswith('91') and len(_digits) == 12) else '91' + _digits[-10:]

    caption = f'\U0001f3c6 Congratulations {partner_name}! Your VGK4U Achievement Card'
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type':    'individual',
        'to':                recipient,
        'type':              'image',
        'image': {
            'link':    card_url,
            'caption': caption,
        },
    }
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type':  'application/json',
    }
    result: dict = {'success': False, 'reason': '', 'wamid': ''}
    try:
        resp = _req.post(
            f'https://graph.facebook.com/v21.0/{phone_id}/messages',
            json=payload, headers=headers, timeout=10,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code == 200:
            wamid = data.get('messages', [{}])[0].get('id', '')
            logger.info(f'[EARNER-WA-IMG] Card image sent to {phone} (wamid={wamid})')
            result = {'success': True, 'reason': '', 'wamid': wamid}
        else:
            err = data.get('error', {}).get('message', resp.text[:200])
            logger.warning(f'[EARNER-WA-IMG] Meta API error ({resp.status_code}) for {phone}: {err}')
            result = {'success': False, 'reason': f'api_error:{resp.status_code}:{err}', 'wamid': ''}
    except Exception as e:
        logger.warning(f'[EARNER-WA-IMG] Request exception for {phone}: {e}')
        result = {'success': False, 'reason': f'exception:{e}', 'wamid': ''}

    if result.get('success'):
        try:
            from app.services.whatsapp_auto_service import _log_message
            _log_message(db, phone, caption, result, 'earner_card_image',
                         sent_by_name='System/Auto', sender_type='auto',
                         message_type='earner_card_image')
        except Exception as _log_exc:
            logger.warning(f'[EARNER-WA-IMG] Failed to log message: {_log_exc}')

    return result


def _send_whatsapp_celebration(phone: str, card_url: str,
                               partner_name: str, gross: float,
                               partner_code: str) -> dict:
    """Send the earner card PNG as a WhatsApp media attachment via Twilio.

    Uses Twilio messages.create() with media_url pointing to the public
    object-storage URL so the card image appears inline in the chat.

    Env vars read:
        TWILIO_SID            — Twilio Account SID
        TWILIO_AUTH_TOKEN     — Twilio Auth Token
        TWILIO_WHATSAPP_FROM  — WhatsApp-enabled Twilio number in
                                'whatsapp:+<number>' format (e.g.
                                'whatsapp:+14155238886' for sandbox).
                                Falls back to wrapping TWILIO_PHONE_NUMBER.

    Returns dict with keys:
        success  bool  — True only when Twilio returns successfully
        reason   str   — populated on skip or failure
        sid      str   — Twilio message SID on success
    """
    import os as _os
    import re as _re

    if not card_url:
        return {'success': False, 'reason': 'no_card_url', 'sid': ''}

    digits = _re.sub(r'\D', '', phone or '')
    if len(digits) < 10:
        logger.warning(f'[WA-CELEBRATION] Invalid phone {phone!r} — skipping')
        return {'success': False, 'reason': 'invalid_phone', 'sid': ''}

    twilio_sid   = _os.environ.get('TWILIO_SID', '').strip()
    twilio_token = _os.environ.get('TWILIO_AUTH_TOKEN', '').strip()

    wa_from = _os.environ.get('TWILIO_WHATSAPP_FROM', '').strip()
    if not wa_from:
        raw_from = _re.sub(r'\D', '', _os.environ.get('TWILIO_PHONE_NUMBER', ''))
        wa_from = f'whatsapp:+{raw_from}' if raw_from else ''

    if not twilio_sid or not twilio_token:
        logger.warning('[WA-CELEBRATION] Twilio credentials not configured — skipping card send')
        return {'success': False, 'reason': 'no_credentials', 'sid': ''}
    if not wa_from or wa_from == 'whatsapp:+':
        logger.warning('[WA-CELEBRATION] No Twilio WhatsApp From number configured — skipping card send')
        return {'success': False, 'reason': 'no_from_number', 'sid': ''}

    wa_to = 'whatsapp:+' + (
        digits if (digits.startswith('91') and len(digits) == 12)
        else '91' + digits[-10:]
    )

    body = (
        f'\U0001f3c6 Congratulations {partner_name}! '
        f'You have earned \u20b9{int(gross):,} with VGK4U. '
        f'Here is your Achievement Card!'
    )

    try:
        from twilio.rest import Client as _TwilioClient
        client = _TwilioClient(twilio_sid, twilio_token)
        msg = client.messages.create(
            from_=wa_from,
            to=wa_to,
            body=body,
            media_url=[card_url],
        )
        logger.info(
            f'[WA-CELEBRATION] Card sent to {partner_code} at {wa_to} '
            f'(sid={msg.sid})'
        )
        return {'success': True, 'reason': '', 'sid': msg.sid}
    except ImportError:
        logger.warning('[WA-CELEBRATION] Twilio SDK not installed — skipping card send')
        return {'success': False, 'reason': 'twilio_not_installed', 'sid': ''}
    except Exception as e:
        logger.warning(f'[WA-CELEBRATION] Send failed for {partner_code}: {e}')
        return {'success': False, 'reason': f'exception:{e}', 'sid': ''}


def _send_earner_wa(db, partner_name: str, partner_code: str,
                    phone: str, gross: float, overall: float,
                    entry_id: int, card_url: str = ''):
    """Send WhatsApp congratulations to the earning member.

    If card_url is provided (absolute HTTPS URL reachable from Twilio servers,
    i.e. the deployed prod URL), the earner card PNG is sent as a Twilio media
    attachment first, followed by the standard congratulations text/template.
    """
    from app.services.whatsapp_auto_service import send_auto_whatsapp

    if not phone or len(phone.strip()) < 10:
        logger.info(f'[EARNER-WA] No valid phone for {partner_code}')
        return

    # Ensure the event trigger exists
    _ensure_wa_trigger(db)
    db.flush()

    # Send card image via Twilio media attachment — always attempt text regardless of result
    card_image_result: dict = {'success': False, 'reason': 'no_card_url', 'sid': ''}
    if card_url:
        try:
            card_image_result = _send_whatsapp_celebration(
                phone, card_url, partner_name, gross, partner_code,
            )
        except Exception as e:
            card_image_result = {'success': False, 'reason': f'exception:{e}', 'sid': ''}
            logger.warning(f'[EARNER-WA] Card image send raised for {partner_code}: {e}')
    if card_url and not card_image_result.get('success'):
        logger.warning(
            f'[EARNER-WA] Card image NOT sent for {partner_code}: '
            f'reason={card_image_result.get("reason")} url={card_url[:80]}'
        )

    context = {
        'name':             partner_name,
        'partner_code':     partner_code,
        'amount':           f'{int(float(gross)):,}',
        'overall_earnings': f'{int(float(overall)):,}',
    }
    try:
        send_auto_whatsapp(
            db=db,
            event_key='vgk_income_paid',
            phone=phone,
            context=context,
            lead_id=None,
            staff_id=None,
        )
        logger.info(f'[EARNER-WA] Sent to {partner_code} at {phone}')
    except Exception as e:
        logger.warning(f'[EARNER-WA] Send failed for {partner_code}: {e}')

    return card_image_result


def _ensure_wa_trigger(db):
    """Idempotently create the WhatsApp template + auto trigger for vgk_income_paid."""
    from sqlalchemy import text

    # Check trigger
    existing = db.execute(text(
        "SELECT id FROM whatsapp_auto_triggers WHERE event_key='vgk_income_paid' LIMIT 1"
    )).fetchone()
    if existing:
        return

    # Create template first
    body = (
        "\U0001f3c6 *Congratulations, {{1}}!* \U0001f389\n\n"
        "\u2728 *Achievement Unlocked!*\n"
        "You've just been rewarded with a *Cash Commission*\n"
        "from the *VGK4U Family!* \U0001f4b0\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f464 *Name:* {{1}}\n"
        "\U0001f194 *VGK ID:* {{2}}\n"
        "\U0001f4b5 *Amount Earned:* \u20b9{{3}}\n"
        "\U0001f4ca *Overall Earnings:* \u20b9{{4}}\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "Your commitment inspires us all and drives our mission forward. \U0001f64f\n\n"
        "\U0001f31f *Keep Leading. Keep Inspiring. Keep Growing!*\n\n"
        "\U0001f91d *Together, We Achieve More!*\n"
        "\u2014 Team VGK4U"
    )
    tmpl_result = db.execute(text("""
        INSERT INTO whatsapp_templates
          (name, slug, segment, template_type, is_active, is_system,
           header_type, body_text, meta_template_name, meta_template_language,
           is_meta_approved, meta_approval_status, meta_category, usage_scope)
        VALUES
          ('VGK4U Cash Earned', 'vgk_income_paid', 'vgk', 'transactional', true, true,
           'none', :body, 'vgk4u_cash_earned', 'en',
           false, 'PENDING_SUBMISSION', 'MARKETING', 'auto')
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
    """), {'body': body})
    db.flush()
    tmpl_row = tmpl_result.fetchone()
    if not tmpl_row:
        tmpl_row = db.execute(text(
            "SELECT id FROM whatsapp_templates WHERE slug='vgk_income_paid' LIMIT 1"
        )).fetchone()
    if not tmpl_row:
        return
    tmpl_id = tmpl_row[0]

    db.execute(text("""
        INSERT INTO whatsapp_auto_triggers
          (event_key, event_label, event_category, template_id, is_enabled, recipient_type, delay_minutes)
        VALUES
          ('vgk_income_paid', 'VGK Income Paid', 'vgk', :tid, true, 'partner', 0)
        ON CONFLICT (event_key) DO NOTHING
    """), {'tid': tmpl_id})
    db.flush()
    logger.info(f'[EARNER-WA] Created WA template {tmpl_id} + trigger for vgk_income_paid')


# ── Main entry point ──────────────────────────────────────────────────────────

def run_earner_celebration(entry_id: int):
    """
    Called in a daemon thread after mark_paid commits.
    Creates its own DB session (short-lived), non-fatal.
    """
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            _do_celebration(db, entry_id)
        finally:
            db.close()
    except Exception as e:
        logger.error(f'[EARNER-CARD] run_earner_celebration failed for entry {entry_id}: {e}')


def _do_celebration(db, entry_id: int):
    from sqlalchemy import text
    from app.services.object_storage import storage_service

    # Load entry + partner
    row = db.execute(text("""
        SELECT e.id, e.entry_number, e.partner_id, e.commission_amount,
               p.partner_name, p.partner_code, p.city, p.state,
               p.contact_person_1_designation, p.whatsapp_number,
               p.vgk_cash_earned_total, p.name_title, p.gender
        FROM vgk_cash_income_entries e
        JOIN official_partners p ON p.id = e.partner_id
        WHERE e.id = :eid
    """), {'eid': entry_id}).fetchone()
    if not row:
        logger.warning(f'[EARNER-CARD] Entry {entry_id} not found')
        return

    (eid, entry_number, partner_id, gross_amount,
     partner_name, partner_code, city, state,
     designation, whatsapp_number, vgk_cash_earned_total,
     _name_title, _gender) = row

    # Derive display title: stored name_title wins; fall back to gender
    def _resolve_title(nt, g):
        t = (nt or '').strip()
        if t:
            return t
        gv = (g or '').strip().lower()
        if gv in ('male', 'm'):
            return 'Mr'
        if gv in ('female', 'f'):
            return 'Ms'
        return ''
    name_title = _resolve_title(_name_title, _gender)

    location_parts = [p for p in [city, state] if p and str(p).strip()]
    location = ', '.join(location_parts)
    gross   = float(gross_amount or 0)

    # Compute overall from sum of all PAID entries — column may lag behind commit
    try:
        paid_sum_row = db.execute(text("""
            SELECT COALESCE(SUM(commission_amount), 0)
            FROM vgk_cash_income_entries
            WHERE partner_id = :pid AND status = 'PAID'
        """), {'pid': partner_id}).fetchone()
        overall = float(paid_sum_row[0] or 0) if paid_sum_row else gross
    except Exception:
        overall = float(vgk_cash_earned_total or 0) or gross

    # 1. Get KYC photo
    photo_bytes = _get_kyc_photo_bytes(db, partner_id)

    # 2. Compose card
    try:
        card_bytes = compose_earner_card(
            partner_name     = partner_name or 'VGK Member',
            partner_code     = partner_code or '',
            location         = location,
            designation      = designation or 'Channel Partner',
            gross_amount     = gross,
            overall_earnings = overall,
            photo_bytes      = photo_bytes,
            name_title       = name_title,
        )
    except Exception as e:
        logger.error(f'[EARNER-CARD] compose_earner_card failed: {e}')
        card_bytes = None

    # 3. Upload card to object storage
    card_storage_key = ''
    if card_bytes:
        safe_num = (entry_number or str(entry_id)).replace('/', '-')
        tmp_key = f'earner_cards/{safe_num}.png'
        try:
            ok = storage_service.upload_file(tmp_key, card_bytes)
            if ok:
                card_storage_key = tmp_key
            else:
                logger.warning(f'[EARNER-CARD] Upload failed for {tmp_key}')
        except Exception as e:
            logger.warning(f'[EARNER-CARD] Upload exception for {tmp_key}: {e}')

    # 4. Publish shoutout announcement — route by network
    #    VGK partner codes start with 'VGK'; all others (DLAP, DST, SV-, etc.) are MNR
    is_vgk = str(partner_code or '').upper().startswith('VGK')
    shoutout_visible_to   = 'vgk' if is_vgk else 'mnr'
    shoutout_category_name = VGK_SHOUTOUT_CATEGORY_NAME if is_vgk else MNR_SHOUTOUT_CATEGORY_NAME
    try:
        system_uid  = _ensure_system_user(db)
        category_id = _ensure_shoutout_category(db, shoutout_category_name)
        _publish_shoutout(db, entry_id, category_id, system_uid,
                          partner_name, partner_code, gross, card_storage_key,
                          visible_to=shoutout_visible_to)
        db.commit()
        logger.info(f'[EARNER-CARD] Shoutout published ({shoutout_visible_to}) for entry {entry_id}')
    except Exception as e:
        db.rollback()
        logger.warning(f'[EARNER-CARD] Shoutout publish failed: {e}')

    # 5. Send WhatsApp — attach card image when URL is available
    try:
        _send_earner_wa(db, partner_name, partner_code,
                        whatsapp_number or '', gross, overall, entry_id,
                        card_url=_card_public_url(card_storage_key))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f'[EARNER-CARD] WA send failed: {e}')

    # 6. Return card storage key for download endpoint
    if card_storage_key:
        try:
            db.execute(text("""
                UPDATE vgk_cash_income_entries
                SET notes = COALESCE(notes,'') || ' [earner_card:' || :key || ']'
                WHERE id = :eid
                  AND (notes IS NULL OR notes NOT LIKE '%[earner_card:%]%')
            """), {'eid': entry_id, 'key': card_storage_key})
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f'[EARNER-CARD] note update failed: {e}')
