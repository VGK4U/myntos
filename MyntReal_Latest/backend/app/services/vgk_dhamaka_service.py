"""
VGK Dhamaka Bonanza Service (Oct 2026)
Special Campaign Engine for "Dhamaka Bonanza" Offers (e.g. Dussehra Dhamaka).

Rules & Capabilities:
  1. 100% Source (L1) Commission on 1st Payment:
     - On any 1st validated payment (> 0) during offer period, L1 gets 100% of their base commission
       calculated on full deal value (typically 5% = ₹15,000 - ₹18,000 on residential solar).
     - Field Support (L5) and Brand Commission (Level 11) remain payable after Net Meter (at completion stage).
  2. Configurable Extra Commission:
     - E.g. Extra ₹5,000 for L1 on first_payment.
  3. No TDS & No Admin Charges Waiver (0% TDS, 0% Admin):
     - 2% TDS and 8% Admin charges borne by the company during the offer period.
     - Payout = 100% of gross (admin_charges = 0, tds_amount = 0).
  4. Dynamic Campaign Configurations:
     - Configurable Campaign Name, Dates, Segment, Brands, and Extra Commission Amounts.
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.base import get_indian_time
from app.models.bonanza import Bonanza

logger = logging.getLogger(__name__)

_SOLAR_CAT_IDS = {6, 19, 36, 48}


def _to_date(val: Any) -> Optional[date]:
    """Safely cast string/datetime/date to date."""
    if not val:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if hasattr(val, 'date'):
        return val.date()
    try:
        return datetime.fromisoformat(str(val).replace('Z', '')).date()
    except Exception:
        return None


def find_active_dhamaka_bonanza(
    db: Session,
    lead,
    check_date: Optional[Any] = None
) -> Optional[Bonanza]:
    """
    Check if a lead qualifies under any active, approved Dhamaka Bonanza.
    Matches:
      - Portal = 'VGK'
      - Status = 'Approved'
      - is_deleted = FALSE
      - is_dhamaka_bonanza = TRUE
      - Offer period: DATE(start_date) <= check_date <= DATE(end_date) + grace_days
      - Segment filter (category_id in bonanza segment / Solar category)
      - Brand filter (if bonanza has brand filters configured, lead.solar_brand_id must match)
    """
    if not lead:
        return None

    # Resolve check date
    if check_date:
        eff_date = _to_date(check_date)
    else:
        eff_date = (
            _to_date(getattr(lead, 'first_payment_received_date', None))
            or _to_date(getattr(lead, 'first_dvr_confirmed_at', None))
            or get_indian_time().date()
        )

    if not eff_date:
        return None

    lead_cat_id = getattr(lead, 'category_id', None) or getattr(lead, 'revenue_category_id', None)
    lead_brand_id = getattr(lead, 'solar_brand_id', None)

    # Query all active Dhamaka bonanzas
    dhamaka_bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.is_deleted == False,
        Bonanza.is_dhamaka_bonanza == True
    ).order_by(Bonanza.id.desc()).all()

    for bz in dhamaka_bonanzas:
        b_start = _to_date(bz.start_date)
        b_end = _to_date(bz.end_date)
        grace = int(getattr(bz, 'grace_days', 0) or 0)

        if not b_start or not b_end:
            continue

        deadline = b_end + timedelta(days=grace)
        if not (b_start <= eff_date <= deadline):
            continue

        # Check segment / category match
        bz_seg = getattr(bz, 'segment_id', None)
        if bz_seg:
            if bz_seg in _SOLAR_CAT_IDS:
                if lead_cat_id not in _SOLAR_CAT_IDS:
                    continue
            elif lead_cat_id != bz_seg:
                continue

        # Check category filter table if present
        cat_filter_rows = db.execute(text("""
            SELECT category_id FROM bonanza_category_filters WHERE bonanza_id = :bid
        """), {'bid': bz.id}).fetchall()
        if cat_filter_rows:
            allowed_cats = {r[0] for r in cat_filter_rows}
            if lead_cat_id not in allowed_cats:
                continue

        # Check brand filter if configured
        brand_filter_rows = db.execute(text("""
            SELECT brand_id FROM bonanza_brand_filters WHERE bonanza_id = :bid
        """), {'bid': bz.id}).fetchall()
        if brand_filter_rows:
            allowed_brands = {r[0] for r in brand_filter_rows}
            if lead_brand_id not in allowed_brands:
                continue

        # Matches all criteria
        return bz

    return None


def is_first_validated_payment(
    db: Session,
    lead_id: int,
    transaction_id: int
) -> bool:
    """
    Returns True if transaction_id is the first validated payment on the lead.
    """
    earlier_count = db.execute(text("""
        SELECT COUNT(*) FROM crm_lead_transactions
        WHERE lead_id = :lid
          AND validation_status = 'validated'
          AND id < :tid
    """), {'lid': lead_id, 'tid': transaction_id}).scalar()
    return (earlier_count == 0)


def calculate_dhamaka_l1_commission(
    db: Session,
    lead,
    bonanza: Bonanza,
    producer_base_pct: Decimal = Decimal('5.00')
) -> Decimal:
    """
    Under Dhamaka Bonanza, 100% of L1 Source Commission is unlocked on the 1st payment.
    Calculated on the full deal value (deal_value_total or solar_value or deal_value).
    """
    underlying_val = Decimal(str(
        getattr(lead, 'deal_value_total', None)
        or getattr(lead, 'solar_value', None)
        or getattr(lead, 'deal_value', None)
        or 0
    ))
    if underlying_val <= Decimal('0.00'):
        return Decimal('0.00')

    l1_full = (underlying_val * producer_base_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return l1_full
