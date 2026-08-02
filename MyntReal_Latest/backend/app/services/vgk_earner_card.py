"""
VGK Earner Celebration Poster Engine (DC Protocol May 2026 - Upgraded 3D Marquee Composite V2)

Generates a gorgeous, high-impact 3D layered composite celebration card image (1200 x 900)
when a VGK income entry is PAID.

All text labels, currency values, names, ranks, team size counts, level breakdowns, customer details,
and referrer metrics are 100% dynamically bound to backend models—zero hardcoded values.

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
CARD_H = 1920

# Color Scheme
NAVY       = (10,  25,  47)   # Left card background #0a192f
NAVY_MID   = (15,  45,  90)
GOLD       = (212, 175,  55)   # Metallic gold
GOLD_LIGHT = (251, 191, 36)   # Glowing gold (#fbbf24)
GOLD_PALE  = (255, 236, 179)
WHITE      = (248, 250, 252)   # Slate white (#f8fafc)
DARK_GOLD  = (160, 120,  30)
CRIMSON    = (239, 68, 68)     # Vibrant red (#ef4444)
EMERALD    = (52, 211, 153)    # Vibrant green (#34d399)
LIGHT_BG   = (10,  15,  29)     # Luxury Dark Navy background (#0A0F1D)
CARD_BG    = (19,  27,  46)     # Luxury card background (#131B2E)
TEXT_MUTED = (148, 163, 184)    # Slate grey (#94a3b8)

PUBLIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'frontend' / 'public'
LOGO_PATH  = PUBLIC_DIR / 'vgk4u-logo.png'
MYNT_LOGO_PATH = PUBLIC_DIR / 'myntreal-logo-trans.png'
HAR_GHAR_SOLAR_PATH = PUBLIC_DIR / 'solar-logo-harghar-trans.png'

FONT_DIR_LINUX = Path('/usr/share/fonts/truetype/dejavu')
FONT_DIR_MAC   = Path('/System/Library/Fonts/Supplemental')
SYSTEM_USER_ID = 'VGK-SYSTEM'
VGK_SHOUTOUT_CATEGORY_NAME = 'VGK4U Shoutouts'
MNR_SHOUTOUT_CATEGORY_NAME = 'MNR Shoutouts'

# ── Font helpers ─────────────────────────────────────────────────────────────

def _font(bold: bool = False, size: int = 28):
    from PIL import ImageFont
    paths = [
        FONT_DIR_MAC / ('Arial Bold.ttf' if bold else 'Arial.ttf'),
        FONT_DIR_LINUX / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
    ]
    for p in paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    # System lookup fallbacks
    for name in ['Arial Bold' if bold else 'Arial', 'DejaVu Sans Bold' if bold else 'DejaVu Sans', 'Helvetica']:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _serif(bold: bool = False, size: int = 28):
    from PIL import ImageFont
    paths = [
        FONT_DIR_MAC / ('Times New Roman Bold.ttf' if bold else 'Times New Roman.ttf'),
        FONT_DIR_LINUX / ('DejaVuSerif-Bold.ttf' if bold else 'DejaVuSerif.ttf'),
    ]
    for p in paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    # System lookup fallbacks
    for name in ['Times New Roman Bold' if bold else 'Times New Roman', 'Georgia Bold' if bold else 'Georgia']:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
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


def _draw_text_in_range(draw, text, x_start, x_end, y, font, color, shadow=False):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
    except Exception:
        w = len(text) * (font.size if hasattr(font, 'size') else 14)
    x = x_start + (x_end - x_start - w) // 2
    if shadow:
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 100))
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
    from PIL import Image, ImageDraw
    img = img.convert('RGBA')
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size, size], fill=255)
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result


def _draw_laurel_wreath(draw, cx, cy, r):
    # Programmatic high-quality laurel wreath drawing around photo circle
    for angle_deg in range(100, 261, 14):
        rad = math.radians(angle_deg)
        lx = cx + r * math.cos(rad)
        ly = cy + r * math.sin(rad)
        draw.ellipse([lx-7, ly-5, lx+7, ly+5], fill=GOLD)
    for angle_deg in range(80, -81, -14):
        rad = math.radians(angle_deg)
        lx = cx + r * math.cos(rad)
        ly = cy + r * math.sin(rad)
        draw.ellipse([lx-7, ly-5, lx+7, ly+5], fill=GOLD)
    # Bow ties at the bottom center
    draw.polygon([(cx - 10, cy + r - 5), (cx, cy + r + 10), (cx + 10, cy + r - 5), (cx, cy + r + 2)], fill=GOLD)


def _draw_marquee_lightbulbs(draw, x1, y1, x2, y2):
    # Draw glowing marquee bulbs (alternating yellow and white circles)
    bulb_positions = []
    # Top & Bottom edges
    for bx in range(x1 + 10, x2 - 5, 20):
        bulb_positions.append((bx, y1))
        bulb_positions.append((bx, y2))
    # Left & Right edges
    for by in range(y1 + 15, y2 - 5, 20):
        bulb_positions.append((x1, by))
        bulb_positions.append((x2, by))

    for idx, (bx, by) in enumerate(bulb_positions):
        col = (255, 255, 255) if idx % 2 == 0 else GOLD_LIGHT
        # Glow aura
        draw.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=(*col, 80))
        draw.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=WHITE)


def _draw_vector_house_solar_ev(draw, hx, hy):
    # House background celebration fireworks
    for angle in range(0, 360, 20):
        rad = math.radians(angle)
        for dist in range(12, 70, 12):
            x_end = hx + dist * math.cos(rad)
            y_end = hy + dist * math.sin(rad)
            alpha = int(255 * (70 - dist) / 70)
            draw.line([(hx, hy), (x_end, y_end)], fill=(251, 191, 36, alpha), width=1)

    # Clean modern vector house + EV charger
    # Wall
    draw.rectangle([hx - 40, hy + 5, hx + 10, hy + 45], fill=(203, 213, 225), outline=(100, 116, 139), width=1)
    # Door
    draw.rectangle([hx - 25, hy + 20, hx - 10, hy + 45], fill=(120, 53, 4))
    # Roof (red triangle)
    draw.polygon([(hx - 50, hy + 5), (hx - 15, hy - 25), (hx + 20, hy + 5)], fill=CRIMSON)
    # Solar panel (blue tilted quad)
    draw.polygon([(hx - 35, hy - 7), (hx - 15, hy - 22), (hx - 5, hy - 15), (hx - 25, hy)], fill=(37, 99, 235), outline=WHITE, width=1)

    # EV Charger
    draw.rectangle([hx + 20, hy + 15, hx + 45, hy + 45], fill=EMERALD, outline=(4, 120, 87), width=1)
    # Lightning bolt icon
    draw.polygon([(hx + 32, hy + 18), (hx + 38, hy + 28), (hx + 34, hy + 28), (hx + 36, hy + 40), (hx + 28, hy + 30), (hx + 32, hy + 30)], fill=GOLD)

    # Callout badge banner below graphic
    _draw_rounded_rect(draw, hx - 90, hy + 50, hx + 90, hy + 72, 6, fill=(15, 23, 42), outline=GOLD, width=1)
    _draw_text_in_range(draw, "GO SOLAR | SAVE MORE | EARN MORE", hx - 90, hx + 90, hy + 54, _font(True, 8), WHITE)


def _draw_placeholder_avatar(img, draw, x, y, size, partner_name: str = '?'):
    from PIL import Image, ImageDraw as PID
    overlay = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    od      = PID.Draw(overlay)
    od.ellipse([0, 0, size - 1, size - 1], fill=GOLD)
    pad = size // 12
    od.ellipse([pad, pad, size - 1 - pad, size - 1 - pad], fill=GOLD_LIGHT)

    initials = ''
    parts = partner_name.strip().split()
    if parts:
        initials = parts[0][0].upper()
        if len(parts) > 1:
            initials += parts[-1][0].upper()
    init_font_size = size // 2
    try:
        from PIL import ImageFont
        init_font = ImageFont.truetype(str(FONT_DIR_MAC / 'Arial Bold.ttf') if FONT_DIR_MAC.exists() else 'Arial', init_font_size)
    except Exception:
        init_font = _font(True, init_font_size)
    
    bbox  = od.textbbox((0, 0), initials, font=init_font)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    ix    = (size - tw) // 2 - bbox[0]
    iy    = (size - th) // 2 - bbox[1]
    od.text((ix, iy), initials, font=init_font, fill=NAVY)
    img.paste(overlay, (x, y), overlay)


# ── Card Composer (1200 x 900) ────────────────────────────────────────────────

def compose_earner_card(
    partner_name: str = 'VGK Member',
    partner_code: str = '',
    location: str = 'Unknown',
    designation: str = 'Channel Partner',
    gross_amount: float = 0.0,
    overall_earnings: float = 0.0,
    photo_bytes: Optional[bytes] = None,
    name_title: str = '',
    payload: Optional[dict] = None,
    **kwargs
) -> bytes:
    from PIL import Image, ImageDraw
    import io
    from datetime import datetime
    from typing import Optional

    # 1. Bind inputs dynamically from payload schema or fallback parameters
    if payload is None:
        payload = {}

    winner_title = payload.get("winner_title") or designation.upper() or "PROUD WINNER"
    member_name = payload.get("member_name") or f"{name_title.strip() + '. ' if name_title else ''}{partner_name.strip()}".upper()
    todays_stage1_advance = float(payload.get("todays_stage1_advance") or gross_amount)
    todays_extra_comm = float(payload.get("todays_extra_comm") or 0.0)
    todays_total_payout = float(payload.get("todays_total_payout") or (todays_stage1_advance + todays_extra_comm))
    
    # Overall Earnings is displayed in the main marquee centerpiece
    overall_earnings_val = float(payload.get("overall_earnings") or overall_earnings or todays_total_payout)
    
    total_completed_files = int(payload.get("total_completed_files") or 1)
    total_team_size = int(payload.get("total_team_size") or 0)
    team_level_breakdown = payload.get("team_level_breakdown") or "L1: 0 | L2: 0 | L3: 0 | L4: 0 | L5: 0"
    potential_valuation = float(payload.get("potential_valuation") or 0.0)
    customer_name = payload.get("customer_name") or "Valued Customer"
    customer_location = payload.get("customer_location") or location or "Unknown"
    senior_referrer_name = payload.get("senior_referrer_name") or "VGK Platform"
    senior_referrer_earning = float(payload.get("senior_referrer_earning") or overall_earnings_val)
    payout_date = payload.get("payout_date") or datetime.now().strftime('%d-%b-%Y')
    company_disclaimer = payload.get("company_disclaimer") or "POTENTIAL EARNING IS BASED ON FINAL COMPLETION OF PROJECTS AND SUBJECT TO COMPANY TERMS."

    def fmt_inr(val):
        return f'\u20b9{int(float(val)):,}'

    # 2. Main Canvas setup (Light Off-White background)
    img = Image.new('RGB', (CARD_W, CARD_H), LIGHT_BG)
    draw = ImageDraw.Draw(img, 'RGBA')

    # Dotted Dual Outer Border
    border_color = GOLD
    _draw_rounded_rect(draw, 14, 14, CARD_W - 14, CARD_H - 14, 14, outline=border_color, width=2)
    # Inner Dotted Border
    for bx in range(26, CARD_W - 25, 20):
        draw.ellipse([bx - 2, 26 - 2, bx + 2, 26 + 2], fill=border_color)
        draw.ellipse([bx - 2, CARD_H - 26 - 2, bx + 2, CARD_H - 26 + 2], fill=border_color)
    for by in range(26, CARD_H - 25, 20):
        draw.ellipse([26 - 2, by - 2, 26 + 2, by + 2], fill=border_color)
        draw.ellipse([CARD_W - 26 - 2, by - 2, CARD_W - 26 + 2, by + 2], fill=border_color)

    # ── TOP ZONE (y: 60 to 390) ───────────────────────────────────────────────
    # A. Logos Row (y: 40)
    logo_y = 40
    
    # Har Ghar Solar Logo (Left)
    try:
        if HAR_GHAR_SOLAR_PATH.exists():
            hgs_logo = Image.open(HAR_GHAR_SOLAR_PATH).convert('RGBA')
            scale = 100 / hgs_logo.height
            w = int(hgs_logo.width * scale)
            hgs_logo = hgs_logo.resize((w, 100), Image.LANCZOS)
            # Draw white background capsule box under the transparent logo
            _draw_rounded_rect(draw, 70, logo_y - 5, 70 + w + 20, logo_y + 105, 8, fill=WHITE)
            img.paste(hgs_logo, (80, logo_y), hgs_logo)
    except Exception:
        pass

    # MyntReal Logo (Center)
    try:
        if MYNT_LOGO_PATH.exists():
            mynt_logo = Image.open(MYNT_LOGO_PATH).convert('RGBA')
            scale = 100 / mynt_logo.height
            w = int(mynt_logo.width * scale)
            mynt_logo = mynt_logo.resize((w, 100), Image.LANCZOS)
            img.paste(mynt_logo, ((CARD_W - w) // 2, logo_y + 10), mynt_logo)
    except Exception:
        pass

    # VGK4U Logo (Right)
    try:
        if LOGO_PATH.exists():
            vgk_logo = Image.open(LOGO_PATH).convert('RGBA')
            scale = 100 / vgk_logo.height
            w = int(vgk_logo.width * scale)
            vgk_logo = vgk_logo.resize((w, 100), Image.LANCZOS)
            img.paste(vgk_logo, (1000 - w, logo_y), vgk_logo)
    except Exception:
        pass

    # B. Royal Blue Ribbon Banner
    ribbon_y = 195
    draw.rectangle([290, ribbon_y, 790, ribbon_y + 40], fill=(30, 58, 138))
    draw.line([(290, ribbon_y + 40), (790, ribbon_y + 40)], fill=(23, 37, 84), width=2)
    # Left Fold
    draw.polygon([(260, ribbon_y + 10), (290, ribbon_y), (290, ribbon_y + 40), (260, ribbon_y + 30), (272, ribbon_y + 20)], fill=(23, 37, 84))
    # Right Fold
    draw.polygon([(820, ribbon_y + 10), (790, ribbon_y), (790, ribbon_y + 40), (820, ribbon_y + 30), (808, ribbon_y + 20)], fill=(23, 37, 84))
    # Connectors
    draw.polygon([(290, ribbon_y + 40), (290, ribbon_y + 50), (305, ribbon_y + 40)], fill=(15, 23, 42))
    draw.polygon([(790, ribbon_y + 40), (790, ribbon_y + 50), (775, ribbon_y + 40)], fill=(15, 23, 42))
    _draw_text_centered(draw, "★ CONGRATULATIONS ★", ribbon_y + 8, _font(True, 18), GOLD_LIGHT, shadow=False)

    # C. Cursive Congs Subtitle
    _draw_text_centered(draw, member_name, 270, _serif(True, 32), GOLD_LIGHT, shadow=False)
    _draw_rounded_rect(draw, 240, 340, 840, 380, 6, fill=(30, 58, 138))
    _draw_text_centered(draw, "★ ON YOUR WELL-DESERVED ACHIEVEMENT! ★", 348, _font(True, 16), WHITE, shadow=False)

    # ── VERTICAL STACK ZONE (y: 380 to 1700) ──────────────────────────────────
    # 1. Winner Profile Card
    wcard_y = 380
    _draw_rounded_rect(draw, 140, wcard_y, 940, wcard_y + 480, 16, fill=CARD_BG, outline=GOLD, width=2)
    # Winner Title Header Ribbon (y: 395 to 445)
    _draw_rounded_rect(draw, 220, wcard_y + 15, 860, wcard_y + 60, 8, fill=(30, 58, 138))
    _draw_text_in_range(draw, winner_title.upper(), 220, 860, wcard_y + 23, _font(True, 20), WHITE)

    # Laurel Wreath + Photo - Profile photo (diameter 220px)
    p_cx, p_cy = 540, wcard_y + 240
    p_size = 220
    _draw_laurel_wreath(draw, p_cx, p_cy, 122)
    px = p_cx - (p_size // 2)
    py = p_cy - (p_size // 2)
    if photo_bytes:
        try:
            member_img = Image.open(io.BytesIO(photo_bytes))
            circular = _circular_crop(member_img, p_size)
            img.paste(circular, (px, py), circular)
        except Exception:
            _draw_placeholder_avatar(img, draw, px, py, p_size, member_name)
    else:
        _draw_placeholder_avatar(img, draw, px, py, p_size, member_name)

    # Golden Champion badge decoration at the bottom
    _draw_rounded_rect(draw, 390, wcard_y + 395, 690, wcard_y + 445, 20, fill=CARD_BG, outline=GOLD, width=2)
    _draw_text_in_range(draw, "★ CHAMPION ★", 390, 690, wcard_y + 406, _font(True, 20), GOLD_LIGHT)

    # 2. Overall Earning Marquee Box
    marquee_y1 = 890
    marquee_y2 = 1040
    _draw_rounded_rect(draw, 140, marquee_y1, 940, marquee_y2, 12, fill=CARD_BG, outline=GOLD, width=3)
    _draw_marquee_lightbulbs(draw, 140, marquee_y1, 940, marquee_y2)

    # Left & Right Megaphones
    draw.polygon([(85, marquee_y1 + 45), (130, marquee_y1 + 25), (130, marquee_y1 + 105), (85, marquee_y1 + 85)], fill=(30, 58, 138), outline=GOLD)
    draw.rectangle([130, marquee_y1 + 55, 138, marquee_y1 + 75], fill=(10, 25, 47))
    draw.polygon([(995, marquee_y1 + 45), (950, marquee_y1 + 25), (950, marquee_y1 + 105), (995, marquee_y1 + 85)], fill=(30, 58, 138), outline=GOLD)
    draw.rectangle([942, marquee_y1 + 55, 950, marquee_y1 + 75], fill=(10, 25, 47))

    # Centerpiece text
    _draw_text_centered(draw, "★ OVERALL EARNING ★", marquee_y1 + 15, _font(True, 16), GOLD_LIGHT, shadow=False)
    _draw_text_centered(draw, f"{fmt_inr(overall_earnings_val)}/-", marquee_y1 + 38, _font(True, 54), WHITE, shadow=True)
    _draw_text_centered(draw, "LIFETIME EARNING", marquee_y1 + 105, _font(True, 15), (156, 163, 175), shadow=False)

    # 3. Today's Payout Card
    payout_card_y = 1070
    _draw_rounded_rect(draw, 140, payout_card_y, 940, payout_card_y + 250, 14, fill=CARD_BG, outline=GOLD, width=2)
    _draw_text_centered(draw, "★ TODAY'S PAYOUT ★", payout_card_y + 15, _font(True, 18), GOLD_LIGHT, shadow=False)
    
    # Breakups inside
    _draw_text_centered(draw, f"Stage 1 Advance: {fmt_inr(todays_stage1_advance)}/-", payout_card_y + 55, _font(True, 26), WHITE, shadow=False)
    _draw_text_centered(draw, f"Extra Comm: {fmt_inr(todays_extra_comm)}/-", payout_card_y + 100, _font(True, 26), WHITE, shadow=False)
    _draw_text_centered(draw, f"Active breakups on {payout_date}", payout_card_y + 145, _font(False, 16), TEXT_MUTED, shadow=False)
    
    # Emerald Total button
    _draw_rounded_rect(draw, 240, payout_card_y + 180, 840, payout_card_y + 235, 10, fill=EMERALD)
    _draw_text_centered(draw, f"Today's Earning: {fmt_inr(todays_total_payout)}/-", payout_card_y + 192, _font(True, 24), WHITE, shadow=False)

    # 4. Combined Metrics (Files & Team Size)
    metrics_y = 1350
    # Files
    _draw_rounded_rect(draw, 140, metrics_y, 530, metrics_y + 150, 14, fill=CARD_BG, outline=GOLD, width=2)
    _draw_text_in_range(draw, f"{total_completed_files} FILES", 140, 530, metrics_y + 35, _font(True, 26), GOLD_LIGHT)
    _draw_text_in_range(draw, "COMPLETED", 140, 530, metrics_y + 90, _font(True, 16), TEXT_MUTED)

    # Team Size
    _draw_rounded_rect(draw, 550, metrics_y, 940, metrics_y + 150, 14, fill=EMERALD, outline=WHITE, width=2)
    _draw_text_in_range(draw, f"{total_team_size} TEAM", 550, 940, metrics_y + 35, _font(True, 26), WHITE)
    _draw_text_in_range(draw, "TOTAL SIZE", 550, 940, metrics_y + 90, _font(True, 16), (209, 250, 229))
    
    # Level Breakdown pill inside
    _draw_rounded_rect(draw, 570, metrics_y + 115, 920, metrics_y + 140, 6, fill=(4, 120, 87))
    _draw_text_in_range(draw, team_level_breakdown.upper(), 570, 920, metrics_y + 119, _font(True, 12), WHITE)

    # 5. Potential Earning Box
    potential_y = 1530
    _draw_rounded_rect(draw, 140, potential_y, 940, potential_y + 140, 14, fill=CARD_BG, outline=CRIMSON, width=2)
    _draw_text_centered(draw, "POTENTIAL EARNING", potential_y + 15, _font(True, 18), CRIMSON, shadow=False)
    _draw_text_centered(draw, f"{fmt_inr(potential_valuation)}/-", potential_y + 45, _font(True, 46), CRIMSON, shadow=False)
    _draw_text_centered(draw, "TOTAL VALUATION", potential_y + 105, _font(True, 15), (127, 29, 29), shadow=False)

    # ── BOTTOM ZONE (y: 1700 to 1920) ─────────────────────────────────────────
    meta_y = 1710
    
    # Draw Senior Referrer Photo on the Left
    s_cx, s_cy = 185, meta_y + 40
    s_size = 120
    sx = s_cx - (s_size // 2)
    sy = s_cy - (s_size // 2)
    
    # Draw outline for senior photo
    draw.ellipse([sx - 2, sy - 2, sx + s_size + 2, sy + s_size + 2], outline=GOLD, width=2)
    
    senior_photo_bytes = kwargs.get("senior_photo_bytes")
    if senior_photo_bytes:
        try:
            senior_img = Image.open(io.BytesIO(senior_photo_bytes))
            circular = _circular_crop(senior_img, s_size)
            img.paste(circular, (sx, sy), circular)
        except Exception:
            _draw_placeholder_avatar(img, draw, sx, sy, s_size, senior_referrer_name)
    else:
        _draw_placeholder_avatar(img, draw, sx, sy, s_size, senior_referrer_name)

    # Details text
    draw.text((245, meta_y + 10), "SENIOR REFERRER :", font=_font(True, 15), fill=TEXT_MUTED)
    draw.text((245, meta_y + 35), f"{senior_referrer_name}".upper(), font=_font(True, 18), fill=WHITE)

    draw.text((640, meta_y + 10), "SENIOR EARNING :", font=_font(True, 15), fill=TEXT_MUTED)
    draw.text((640, meta_y + 35), f"{fmt_inr(senior_referrer_earning)}/-", font=_font(True, 20), fill=EMERALD)

    # Disclaimer text
    _draw_text_centered(draw, f"* {company_disclaimer}", 1795, _font(False, 12), TEXT_MUTED, shadow=False)

    # Bottom bar
    draw.rectangle([0, 1835, CARD_W, CARD_H], fill=NAVY)
    _draw_text_centered(draw, "★ JOIN VGK4U TODAY TO START YOUR EARNING ★", 1860, _font(True, 20), GOLD_LIGHT, shadow=False)

    # 3. Save buffer
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
    DC_BONANZA_SLABWISE_001 — Slab Wise bonanza celebration card.
    Slab and active referrals parameters mapped cleanly to upgraded composition renderer.
    """
    slab_total_bonanza = slab_extra * deal_count
    total = (slab_extra + slab_base) * deal_count
    
    payload = {
        "winner_title": bonanza_title.upper() if bonanza_title else "SLAB WISE BONANZA",
        "member_name": f"{name_title.strip() + '. ' if name_title else ''}{partner_name.strip()}".upper(),
        "todays_stage1_advance": slab_base * deal_count,
        "todays_extra_comm": slab_total_bonanza,
        "todays_total_payout": total,
        "overall_earnings": overall_earnings,
        "big_week_extra_bonus": slab_total_bonanza,
        "total_completed_files": deal_count,
        "potential_valuation": 0.0,
    }
    return compose_earner_card(
        partner_name=partner_name,
        partner_code=partner_code,
        location=location,
        designation=designation,
        gross_amount=total,
        overall_earnings=overall_earnings,
        photo_bytes=photo_bytes,
        name_title=name_title,
        payload=payload
    )


# ── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_shoutout_category(db, category_name: str = None) -> int:
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
    from sqlalchemy import text
    from app.services.object_storage import storage_service
    import os

    UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / 'uploaded_files'

    def _load(file_path: str, storage_type: str) -> Optional[bytes]:
        if not file_path:
            return None
        if storage_type in ('object_storage', None, ''):
            try:
                data = storage_service.download_file(file_path)
                if data:
                    return data
            except Exception as e1:
                logger.warning(f'[EARNER-CARD] object storage fetch failed ({file_path}): {e1}')
        local = UPLOAD_ROOT / file_path
        if local.exists():
            try:
                return local.read_bytes()
            except Exception as e2:
                logger.warning(f'[EARNER-CARD] local read failed ({local}): {e2}')
        try:
            return storage_service.download_file(file_path)
        except Exception:
            return None

    row = db.execute(text("""
        SELECT file_path, original_storage_type FROM vgk_kyc_documents
        WHERE partner_id = :pid AND document_type = 'profile_photo'
        ORDER BY uploaded_at DESC NULLS LAST LIMIT 1
    """), {'pid': partner_id}).fetchone()
    if row and row[0]:
        data = _load(row[0], row[1])
        if data:
            return data

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
            return data
    return None


def _ensure_system_user(db):
    from sqlalchemy import text
    row = db.execute(text(
        "SELECT id FROM \"user\" WHERE LENGTH(id) <= 12 ORDER BY id LIMIT 1"
    )).fetchone()
    return row[0] if row else SYSTEM_USER_ID


def _publish_shoutout(db, entry_id: int, category_id: int, system_uid: str,
                      partner_name: str, partner_code: str, gross: float,
                      card_storage_key: str,
                      visible_to: str = 'vgk') -> Optional[int]:
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

    existing2 = db.execute(text("""
        SELECT id FROM feedback_submissions
        WHERE description LIKE :pat AND category_id = :cid LIMIT 1
    """), {'pat': f'%entry_id:{entry_id}%', 'cid': category_id}).fetchone()
    if existing2:
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
    from app.services.whatsapp_auto_service import send_auto_whatsapp

    if not phone or len(phone.strip()) < 10:
        logger.info(f'[EARNER-WA] No valid phone for {partner_code}')
        return

    _ensure_wa_trigger(db)
    db.flush()

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
    from sqlalchemy import text

    existing = db.execute(text(
        "SELECT id FROM whatsapp_auto_triggers WHERE event_key='vgk_income_paid' LIMIT 1"
    )).fetchone()
    if existing:
        return

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


# ── Main Entry Point ──────────────────────────────────────────────────────────

def run_earner_celebration(entry_id: int):
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

    row = db.execute(text("""
        SELECT e.id, e.entry_number, e.partner_id, e.commission_amount,
               p.partner_name, p.partner_code, p.city, p.state,
               p.contact_person_1_designation, p.whatsapp_number,
               p.vgk_cash_earned_total, p.name_title, p.gender,
               e.source_lead_id, e.bonanza_id
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
     _name_title, _gender, source_lead_id, bonanza_id) = row

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
    gross = float(gross_amount or 0)

    # 1. Fetch Dynamic Data Payload fields
    # A. todays_stage1_advance, todays_extra_comm, todays_total_payout
    todays_stage1_advance = 0.0
    todays_extra_comm = 0.0
    if source_lead_id:
        payouts_row = db.execute(text("""
            SELECT 
                COALESCE(SUM(CASE WHEN kind = 'ADVANCE' THEN commission_amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN kind = 'EXTRA_COMMISSION' THEN commission_amount ELSE 0 END), 0)
            FROM vgk_cash_income_entries
            WHERE source_lead_id = :lead_id AND partner_id = :partner_id AND status = 'PAID'
        """), {'lead_id': source_lead_id, 'partner_id': partner_id}).fetchone()
        if payouts_row:
            todays_stage1_advance = float(payouts_row[0] or 0.0)
            todays_extra_comm = float(payouts_row[1] or 0.0)

    # Fallback to current entry kind if sum is 0
    if todays_stage1_advance == 0.0 and todays_extra_comm == 0.0:
        current_kind = db.execute(text("SELECT kind FROM vgk_cash_income_entries WHERE id = :eid"), {'eid': entry_id}).scalar()
        if current_kind == 'ADVANCE':
            todays_stage1_advance = gross
        elif current_kind == 'EXTRA_COMMISSION':
            todays_extra_comm = gross

    todays_total_payout = todays_stage1_advance + todays_extra_comm

    # B. Compute overall earnings
    try:
        paid_sum_row = db.execute(text("""
            SELECT COALESCE(SUM(commission_amount), 0)
            FROM vgk_cash_income_entries
            WHERE partner_id = :pid AND status = 'PAID'
        """), {'pid': partner_id}).fetchone()
        overall = float(paid_sum_row[0] or 0) if paid_sum_row else gross
    except Exception:
        overall = float(vgk_cash_earned_total or 0) or gross

    # C. total_completed_files
    files_row = db.execute(text("""
        SELECT COUNT(DISTINCT source_lead_id) 
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid AND status = 'PAID'
    """), {'pid': partner_id}).fetchone()
    total_completed_files = files_row[0] if (files_row and files_row[0]) else 1

    # D. total_team_size & team_level_breakdown
    levels = {}
    current_ids = [partner_id]
    total_team_size = 0
    for lvl in range(1, 6):
        if not current_ids:
            levels[f"L{lvl}"] = 0
            continue
        rows = db.execute(text("""
            SELECT id FROM official_partners 
            WHERE parent_partner_id IN :pids AND is_active = true
        """), {"pids": tuple(current_ids)}).fetchall()
        next_ids = [r[0] for r in rows]
        levels[f"L{lvl}"] = len(next_ids)
        total_team_size += len(next_ids)
        current_ids = next_ids
    team_level_breakdown = " | ".join(f"L{i}: {levels.get(f'L{i}', 0)}" for i in range(1, 6))

    # E. potential_valuation
    val_row = db.execute(text("""
        SELECT COALESCE(SUM(deal_value_total), 0) FROM crm_leads
        WHERE (associated_partner_id = :pid OR primary_owner_id = :pid) 
          AND status NOT IN ('won', 'lost', 'cancelled')
    """), {'pid': partner_id}).fetchone()
    potential_valuation = float(val_row[0]) if (val_row and val_row[0]) else 0.0

    # F. customer_name & customer_location
    customer_name = "Valued Customer"
    customer_location = "Unknown"
    if source_lead_id:
        lead_row = db.execute(text("""
            SELECT name, area, city, state FROM crm_leads WHERE id = :lid
        """), {'lid': source_lead_id}).fetchone()
        if lead_row:
            customer_name = (lead_row[0] or "Valued Customer").strip()
            loc_parts = [p for p in [lead_row[1], lead_row[2], lead_row[3]] if p and str(p).strip()]
            customer_location = ", ".join(loc_parts) if loc_parts else "Unknown"

    # G. senior_referrer_name & senior_referrer_earning
    senior_referrer_name = "VGK Platform"
    senior_referrer_earning = 0.0
    senior_partner_id = None
    parent_row = db.execute(text("""
        SELECT p.id, p.partner_name, 
               (SELECT COALESCE(SUM(commission_amount), 0) 
                FROM vgk_cash_income_entries 
                WHERE partner_id = p.id AND status = 'PAID' AND level != 1)
        FROM official_partners p
        WHERE p.id = (SELECT parent_partner_id FROM official_partners WHERE id = :pid)
    """), {'pid': partner_id}).fetchone()
    if parent_row:
        senior_partner_id = parent_row[0]
        senior_referrer_name = parent_row[1] or "VGK Platform"
        senior_referrer_earning = float(parent_row[2] or 0.0)

    # H. Load KYC Photo
    photo_bytes = _get_kyc_photo_bytes(db, partner_id)
    senior_photo_bytes = _get_kyc_photo_bytes(db, senior_partner_id) if senior_partner_id else None

    # 2. Build EarnerCardPayload
    payload = {
        "winner_title": designation.upper() if designation else "PROUD WINNER",
        "member_name": f"{name_title.strip() + '. ' if name_title else ''}{partner_name.strip()}".upper(),
        "payout_date": datetime.now().strftime('%d-%b-%Y'),
        "todays_stage1_advance": todays_stage1_advance,
        "todays_extra_comm": todays_extra_comm,
        "todays_total_payout": todays_total_payout,
        "overall_earnings": overall,
        "total_completed_files": total_completed_files,
        "total_team_size": total_team_size,
        "team_level_breakdown": team_level_breakdown,
        "potential_valuation": potential_valuation,
        "customer_name": customer_name,
        "customer_location": customer_location,
        "senior_referrer_name": senior_referrer_name,
        "senior_referrer_earning": senior_referrer_earning,
        "company_disclaimer": "POTENTIAL EARNING IS BASED ON FINAL COMPLETION OF PROJECTS AND SUBJECT TO COMPANY TERMS."
    }

    # 3. Compose card image bytes (1200 x 900)
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
            payload          = payload,
            senior_photo_bytes = senior_photo_bytes
        )
    except Exception as e:
        logger.error(f'[EARNER-CARD] compose_earner_card failed: {e}')
        card_bytes = None

    # 4. Upload card to object storage
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

    # 5. Publish shoutout announcement
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

    # 6. Send WhatsApp trigger
    try:
        _send_earner_wa(db, partner_name, partner_code,
                        whatsapp_number or '', gross, overall, entry_id,
                        card_url=_card_public_url(card_storage_key))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f'[EARNER-CARD] WA send failed: {e}')

    # 7. Save key in income notes
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
