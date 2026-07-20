"""
MNR E-Com Lite — Centralized Price Calculation Service
All price logic lives here. No pricing computed outside this module.

PRICE ENGINE:
  dealer_price    = base cost from sheet (what MNR charges, excl. GST)
  display_mrp     = dealer_price × (1 + markup_percent/100)   ← shown as MRP / strikethrough
  discount_amount = dealer_price × discount_pct               ← applied on dealer_price
  net_before_tax  = dealer_price − discount_amount            ← discounted excl. GST
  gst_amount      = net_before_tax × gst_percent/100          ← GST on discounted price
  final_price     = net_before_tax + gst_amount

DISCOUNT MODES:
  'mnr'        → 3%   (MNR member)
  'mnr_points' → 1.5% (MNR Points balance)
  'partner'    → 12%  (Dealer/Partner code)
  'student'    → 10%  (ETC student)
  'vgk'        → 3%   (VGK Team member)

MARKUP RANDOMISATION:
  Each product gets a deterministic per-SKU markup % derived from a hash of its SKU.
  This gives natural variation (7–32%) across products even within the same category.
  Values are stable across page loads/syncs (same SKU → same markup always).

MARGIN GUARD:
  net_before_tax must be >= dealer_price × (1 - margin_floor_percent/100)
  Default floor = 20% (allows up to 20% discount; covers partner 12% + student 10%).
  If breached → discount blocked, margin_warning returned in payload.
"""

import hashlib
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional

# ── Per-product markup variants ──────────────────────────────────────────────
# 24 distinct values that look natural (not uniform %)
_MARKUP_VARIANTS = [
    7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
    17, 18, 19, 20, 22, 24, 25, 27, 28, 30, 32,
    9, 14, 21,   # extra weight on common values to skew distribution
]


def _sku_markup(sku: str) -> float:
    """
    Deterministic per-product markup % from SKU hash.
    Same SKU always returns the same markup. No DB column needed.
    """
    h = int(hashlib.md5((sku or 'DEFAULT').encode()).hexdigest(), 16)
    return float(_MARKUP_VARIANTS[h % len(_MARKUP_VARIANTS)])


def _d(val) -> Decimal:
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal('0')


def calculate_price_breakdown(
    dealer_price: float,
    markup_percent: float,
    gst_percent: float,
    margin_floor_percent: float,
    discount_mode: Optional[str] = None,
    segment_discount_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Full price breakdown for one product.

    Args:
        dealer_price: Base cost from sheet (our actual sell target)
        markup_percent: Per-product markup % (from _sku_markup or category_config)
        gst_percent: Category GST % (from category_config)
        margin_floor_percent: Minimum margin floor % (from category_config)
        discount_mode: None | 'mnr' (3%) | 'mnr_points' (1.5%) | 'partner' (12%) | 'student' (10%)
        segment_discount_rates: Optional dict with keys 'mnr_pct', 'partner_pct', 'student_pct'
            from MarketplaceSegment. When provided, overrides hardcoded defaults.

    Returns dict with all price components for UI rendering.
    """
    dp = _d(dealer_price)
    mk = _d(markup_percent) / 100
    gst = _d(gst_percent) / 100
    floor = _d(margin_floor_percent) / 100

    if dp <= 0:
        return _zero_breakdown(dealer_price, markup_percent, gst_percent)

    display_mrp = (dp * (1 + mk)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    mrp_discount_amount = (display_mrp - dp).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    mrp_discount_pct = float(markup_percent)

    seg = segment_discount_rates if segment_discount_rates is not None else {}
    seg_mnr = seg['mnr_pct'] if 'mnr_pct' in seg else 3.0
    seg_partner = seg['partner_pct'] if 'partner_pct' in seg else 12.0
    seg_student = seg['student_pct'] if 'student_pct' in seg else 10.0

    discount_label = None
    discount_amount = Decimal('0')
    margin_warning = None

    if discount_mode == 'mnr_points':
        discount_pct = Decimal('0.015')
        discount_label = 'MNR Points Discount (1.5%)'
    elif discount_mode == 'mnr':
        discount_pct = _d(seg_mnr) / 100
        discount_label = f'MNR Member Discount ({seg_mnr:.4g}%)'
    elif discount_mode in ('dealer', 'partner'):
        discount_pct = _d(seg_partner) / 100
        discount_label = f'Partner Discount ({seg_partner:.4g}%)'
    elif discount_mode == 'student':
        discount_pct = _d(seg_student) / 100
        discount_label = f'ETC Student Discount ({seg_student:.4g}%)'
    elif discount_mode == 'vgk':
        discount_pct = Decimal('0.03')
        discount_label = 'VGK4U Member Discount (3%)'
    else:
        discount_pct = Decimal('0')

    if discount_pct > 0:
        discount_amount = (dp * discount_pct).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net_before_tax = dp - discount_amount

        # Margin guard
        min_net = (dp * (1 - floor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if net_before_tax < min_net:
            margin_warning = f'Discount blocked — net price would breach {float(margin_floor_percent):.1f}% margin floor'
            discount_amount = Decimal('0')
            net_before_tax = dp
            discount_label = None
    else:
        net_before_tax = dp

    gst_amount = (net_before_tax * gst).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    final_price = (net_before_tax + gst_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Base (no-discount) final for display
    base_gst = (dp * gst).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    base_final = (dp + base_gst).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if base_final < dp:
        base_final = dp

    return {
        'dealer_price': float(dp),
        'display_mrp': float(display_mrp),
        'mrp_discount_amount': float(mrp_discount_amount),
        'mrp_discount_pct': mrp_discount_pct,
        'discount_mode': discount_mode,
        'discount_label': discount_label,
        'discount_amount': float(discount_amount),
        'net_before_tax': float(net_before_tax),
        'gst_percent': float(gst_percent),
        'gst_amount': float(gst_amount),
        'final_price': float(final_price),
        'base_final_price': float(base_final),
        'margin_warning': margin_warning,
        'markup_percent': float(markup_percent),
    }


def _zero_breakdown(dealer_price, markup_percent, gst_percent) -> Dict[str, Any]:
    return {
        'dealer_price': float(dealer_price),
        'display_mrp': float(dealer_price),
        'mrp_discount_amount': 0,
        'mrp_discount_pct': float(markup_percent),
        'discount_mode': None,
        'discount_label': None,
        'discount_amount': 0,
        'net_before_tax': float(dealer_price),
        'gst_percent': float(gst_percent),
        'gst_amount': 0,
        'final_price': float(dealer_price),
        'base_final_price': float(dealer_price),
        'margin_warning': None,
        'markup_percent': float(markup_percent),
    }


def enrich_product_with_pricing(
    product: Dict[str, Any],
    category_config: Optional[Dict[str, Any]],
    discount_mode: Optional[str] = None,
    segment_discount_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Merge product dict with full price breakdown.
    Markup is per-product (SKU hash) — category config is used for GST/floor/HSN only.
    segment_discount_rates: optional dict with mnr_pct/partner_pct/student_pct from segment.
    """
    cfg = category_config or {}
    markup = _sku_markup(product.get('sku', ''))
    product_gst = product.get('gst_percent')
    gst = float(product_gst) if product_gst is not None else float(cfg.get('gst_percent', 18))
    floor = float(cfg.get('margin_floor_percent', 20))
    hsn = cfg.get('hsn_code', '')

    breakdown = calculate_price_breakdown(
        dealer_price=product.get('dealer_price', 0),
        markup_percent=markup,
        gst_percent=gst,
        margin_floor_percent=floor,
        discount_mode=discount_mode,
        segment_discount_rates=segment_discount_rates,
    )
    return {**product, **breakdown, 'hsn_code': hsn}
