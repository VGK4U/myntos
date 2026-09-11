"""
VGK Bonanza Engine (Sep 2026) — Canonical, Reward-Agnostic Bonanza Engine.

Architecture:
  Eligibility       → How many qualifying files the member has achieved.
  Entitlement       → How many reward units the member has earned.
  Reward Catalogue  → What rewards the campaign makes available and their entitlement costs.
  Reward Selection  → Which configured reward (by canonical slab_id) the member chooses using available entitlement.
  Claim             → The member's actual claim transaction (BonanzaProgress).
  Fulfilment        → 5-step verification, procurement, dispatch, delivery / payment.

Zero hard-coded reward names. All rules, targets, and rewards are driven by configuration.
"""

import logging
import math
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.base import get_indian_time
from app.models.bonanza import Bonanza, BonanzaSlab, BonanzaProgress
from app.models.staff_accounts import OfficialPartner

logger = logging.getLogger(__name__)

# Solar Category IDs
_SOLAR_CAT_IDS = {6, 19, 36, 48}

# Completion stages past 'balance_pending' in Solar pipeline
_SOLAR_COMPLETION_STAGES = ('balance_received', 'subsidy_pending', 'completed')

# 5-step status chain for physical awards
PHYSICAL_STATUS_CHAIN = ['Pending', 'Staff Verified', 'Procurement In Progress', 'Dispatched', 'Delivered']

# 3-step status chain for monetary/cash rewards
MONETARY_STATUS_CHAIN = ['Pending', 'Payment Released', 'Paid']


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


def get_qualifying_leads_for_partner(
    db: Session,
    bonanza: Bonanza,
    partner_id: int
) -> Dict[str, Any]:
    """
    Stage 1: Eligibility Evaluation.
    Evaluates how many files a member has achieved according to campaign rules:
      - Qualification window: [start_date, end_date]
      - Completion window: [start_date, end_date + grace_days]
      - Category & Brand filters (if configured)
      - Completion criteria: 'balance_received_plus' | 'completed' | 'any'
    """
    bz_start = _to_date(bonanza.start_date)
    bz_end = _to_date(bonanza.end_date)
    grace = int(getattr(bonanza, 'grace_days', 0) or 0)
    completion_deadline = bz_end + timedelta(days=grace) if bz_end else None

    # Determine filters
    seg_id = getattr(bonanza, 'segment_id', None)
    is_solar = seg_id and (seg_id in _SOLAR_CAT_IDS)

    # Fetch configured brand filters
    brand_rows = db.execute(text("""
        SELECT brand_id FROM bonanza_brand_filters WHERE bonanza_id = :bid
    """), {'bid': bonanza.id}).fetchall()
    brand_ids = [r[0] for r in brand_rows] if brand_rows else None

    # Fetch partner code
    pt_row = db.execute(text("SELECT partner_code FROM official_partners WHERE id = :pid"), {'pid': partner_id}).fetchone()
    partner_code = pt_row[0] if pt_row else str(partner_id)

    # Build query
    qual_event = getattr(bonanza, 'qualification_event', None) or 'first_payment'
    comp_criteria = getattr(bonanza, 'completion_criteria', None) or 'balance_received_plus'

    seg_filter = ""
    if seg_id:
        if is_solar:
            seg_filter = f"AND cl.category_id = ANY(ARRAY{list(_SOLAR_CAT_IDS)})"
        else:
            seg_filter = f"AND cl.category_id = {seg_id}"

    brand_filter = ""
    if brand_ids:
        brand_filter = f"AND cl.solar_brand_id = ANY(ARRAY{brand_ids})"

    # Query leads associated with partner
    leads_sql = f"""
        SELECT cl.id, cl.category_id, cl.solar_brand_id, cl.solar_pipeline_status, cl.status,
               cl.first_payment_received_date, cl.submit_date, cl.complete_date,
               cl.solar_pipeline_status_updated_at, cl.updated_at, cl.created_at
        FROM crm_leads cl
        WHERE (
            cl.associated_partner_id = :pid
            OR cl.source_ref_id = :pcode
            OR cl.source_ref_id = CAST(:pid AS VARCHAR)
            OR EXISTS (
                SELECT 1 FROM vgk_solar_cibil_advances a 
                WHERE a.lead_id = cl.id AND a.partner_id = :pid AND a.level = 1 AND a.kind = 'ADVANCE'
            )
        )
        {seg_filter}
        {brand_filter}
    """
    leads = db.execute(text(leads_sql), {'pid': partner_id, 'pcode': partner_code}).fetchall()

    eligible_lead_ids = []
    completed_lead_ids = []

    for l in leads:
        lead_id = l.id
        
        # 1. Check qualification event date
        if qual_event == 'file_submitted':
            qual_dt = _to_date(l.submit_date or l.created_at)
        elif qual_event == 'completed':
            qual_dt = _to_date(l.complete_date or l.solar_pipeline_status_updated_at or l.updated_at)
        else:  # default 'first_payment'
            qual_dt = _to_date(l.first_payment_received_date)

        if not qual_dt or not bz_start or not bz_end:
            continue
        if not (bz_start <= qual_dt <= bz_end):
            continue

        eligible_lead_ids.append(lead_id)

        # 2. Check completion criteria
        if comp_criteria in ('none', 'any'):
            completed_lead_ids.append(lead_id)
            continue

        sps = (l.solar_pipeline_status or '').strip().lower()
        st = (l.status or '').strip().lower()

        is_completed_stage = False
        if comp_criteria == 'completed':
            is_completed_stage = (st == 'completed' or sps == 'completed')
        else:  # 'balance_received_plus' (crosses balance_pending)
            is_completed_stage = (sps in _SOLAR_COMPLETION_STAGES or st == 'completed')

        if not is_completed_stage:
            continue

        # Check completion deadline: must have occurred on or before completion_deadline
        comp_dt = _to_date(l.complete_date or l.solar_pipeline_status_updated_at or l.updated_at)
        if completion_deadline and comp_dt and comp_dt > completion_deadline:
            continue

        completed_lead_ids.append(lead_id)

    return {
        "eligible_lead_ids": eligible_lead_ids,
        "completed_lead_ids": completed_lead_ids,
        "eligible_count": len(eligible_lead_ids),
        "completed_count": len(completed_lead_ids),
        "completion_deadline": completion_deadline.isoformat() if completion_deadline else None
    }


def calculate_member_entitlement(
    db: Session,
    bonanza: Union[Bonanza, int],
    completed_count: Optional[int] = None,
    partner_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Stage 2: Entitlement Calculation.
    Calculates how many reward units the member has earned for each configured slab:
      - 'one_time': 1 unit if completed_count >= target else 0.
      - 'repeatable': floor(completed_count / target), subject to max_repeat cap.
      - 'highest_only': 1 unit only on the single highest qualifying milestone.
    """
    if isinstance(bonanza, int):
        bonanza_obj = db.query(Bonanza).filter(Bonanza.id == bonanza).first()
        if not bonanza_obj:
            return {"units_earned": 0, "completed_deals": 0, "entitled_slabs": []}
        bonanza = bonanza_obj

    if completed_count is None:
        if partner_id is not None:
            qual = get_qualifying_leads_for_partner(db, bonanza, partner_id)
            completed_count = qual["completed_count"]
        else:
            completed_count = 0

    slabs = db.query(BonanzaSlab).filter(
        BonanzaSlab.bonanza_id == bonanza.id,
        BonanzaSlab.is_active == True
    ).order_by(BonanzaSlab.target_from.asc()).all()

    slabs_entitlement = []
    total_units_earned = 0

    # First pass: calculate raw earned units per slab
    for sl in slabs:
        target = sl.target_from or 1
        mode = getattr(sl, 'reward_mode', None) or 'one_time'
        max_repeat = getattr(sl, 'max_repeat', None)
        cost = getattr(sl, 'entitlement_cost', None) or 1

        if mode == 'repeatable':
            units = math.floor(completed_count / target) if target > 0 else 0
            if max_repeat is not None and max_repeat > 0:
                units = min(units, max_repeat)
        else:
            units = 1 if completed_count >= target else 0

        is_unlocked = units > 0
        slabs_entitlement.append({
            "slab_id": sl.id,
            "slab_label": sl.slab_label,
            "target": target,
            "award_name": sl.award_name or sl.slab_label,
            "reward_type": sl.reward_type,
            "reward_mode": mode,
            "max_repeat": max_repeat,
            "reward_quantity": getattr(sl, 'reward_quantity', 1) or 1,
            "entitlement_cost": cost,
            "units_earned": units,
            "is_unlocked": is_unlocked,
            "progress_to_target": min(completed_count, target),
            "target_gap": max(0, target - completed_count),
            "image_url": getattr(sl, 'image_url', None)
        })

    # Second pass: handle 'highest_only'
    # If any unlocked slab is 'highest_only', ensure only the highest applicable slab awards units
    has_highest_only = any(s["reward_mode"] == 'highest_only' and s["is_unlocked"] for s in slabs_entitlement)
    if has_highest_only:
        highest_target = max((s["target"] for s in slabs_entitlement if s["is_unlocked"]), default=0)
        for s in slabs_entitlement:
            if s["reward_mode"] == 'highest_only' and s["target"] < highest_target:
                s["units_earned"] = 0
                s["is_unlocked"] = False

    total_units_earned = sum(s["units_earned"] for s in slabs_entitlement)

    return {
        "completed_count": completed_count,
        "slabs_entitlement": slabs_entitlement,
        "total_units_earned": total_units_earned
    }


def get_member_reward_catalogue(
    db: Session,
    bonanza_id: int,
    partner_id: int,
    completed_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Stage 3: Available Reward Catalogue with Entitlement & Claim Tracking.
    Returns:
      Total entitlement earned → entitlement already consumed → entitlement remaining → rewards currently selectable.
    """
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.is_deleted == False).first()
    if not bonanza:
        return {"error": "Bonanza not found"}

    # 1. Eligibility
    if completed_count is None:
        elig_info = get_qualifying_leads_for_partner(db, bonanza, partner_id)
        completed_count = elig_info["completed_count"]
        eligible_count = elig_info["eligible_count"]
        completion_deadline = elig_info["completion_deadline"]
    else:
        eligible_count = completed_count
        completion_deadline = None

    # 2. Entitlement
    entitlement_info = calculate_member_entitlement(db, bonanza, completed_count=completed_count)
    slabs_entitlement = entitlement_info["slabs_entitlement"]
    total_units_earned = entitlement_info["total_units_earned"]

    # 3. Claims & Consumption
    claims = db.query(BonanzaProgress).filter(
        BonanzaProgress.bonanza_id == bonanza_id,
        BonanzaProgress.partner_id == partner_id
    ).all()

    # Map existing claims by canonical slab_id
    slab_cost_map = {s["slab_id"]: (s.get("entitlement_cost") or 1) for s in slabs_entitlement}
    claims_by_slab = {}
    total_units_claimed = 0
    for c in claims:
        sl_id = getattr(c, 'slab_id', None) or c.claim_level
        qty_claimed = getattr(c, 'quantity_claimed', 1) or 1
        claims_by_slab[sl_id] = {
            "claim_id": c.id,
            "quantity_claimed": qty_claimed,
            "processed_status": c.processed_status,
            "achieved_date": c.achieved_date.isoformat() if c.achieved_date else None,
            "processed_date": c.processed_date.isoformat() if c.processed_date else None,
            "selected_reward_name": getattr(c, 'selected_reward_name', None) or c.notes
        }
        # Only non-rejected claims consume entitlement
        if c.processed_status != 'Rejected':
            cost_per_item = slab_cost_map.get(sl_id, 1)
            total_units_claimed += qty_claimed * cost_per_item

    total_units_remaining = max(0, total_units_earned - total_units_claimed)

    # 4. Catalogue with Selectability
    reward_catalogue = []
    for s in slabs_entitlement:
        sl_id = s["slab_id"]
        cost = s["entitlement_cost"]
        mode = s["reward_mode"]
        units_earned = s["units_earned"]

        claim_info = claims_by_slab.get(sl_id)
        already_claimed_qty = claim_info["quantity_claimed"] if claim_info else 0
        units_remaining_for_slab = max(0, units_earned - already_claimed_qty)

        # Selection rules:
        # A member can select this reward only when:
        # 1. The slab is unlocked (units_earned > 0)
        # 2. Total remaining entitlement >= cost
        # 3. Slab units remaining >= 1 (and for one-time, already_claimed_qty == 0)
        is_selectable = False
        if mode == 'one_time':
            is_selectable = (units_earned >= 1) and (already_claimed_qty == 0) and (total_units_remaining >= cost)
        else:  # repeatable
            is_selectable = (units_remaining_for_slab >= 1) and (total_units_remaining >= cost)

        reward_catalogue.append({
            "slab_id": sl_id,  # CANONICAL REFERENCE
            "slab_label": s["slab_label"],
            "target": s["target"],
            "award_name": s["award_name"],
            "reward_type": s["reward_type"],
            "reward_mode": mode,
            "max_repeat": s["max_repeat"],
            "reward_quantity": s["reward_quantity"],
            "entitlement_cost": cost,
            "units_earned": units_earned,
            "units_claimed": already_claimed_qty,
            "units_remaining": units_remaining_for_slab,
            "is_unlocked": s["is_unlocked"],
            "is_selectable": is_selectable,
            "claim_status": claim_info["processed_status"] if claim_info else None,
            "claim_id": claim_info["claim_id"] if claim_info else None,
            "image_url": s["image_url"]
        })

    return {
        "bonanza_id": bonanza.id,
        "bonanza_name": bonanza.name,
        "partner_id": partner_id,
        "eligible_files": eligible_count,
        "completed_files": completed_count,
        "completion_deadline": completion_deadline,
        "total_entitlement_earned": total_units_earned,
        "total_entitlement_claimed": total_units_claimed,
        "total_entitlement_remaining": total_units_remaining,
        "reward_catalogue": reward_catalogue
    }


def select_and_claim_reward(
    db: Session,
    bonanza_id: int,
    partner_id: int,
    slab_id: int,
    quantity: int = 1,
    admin_user: Any = None,
    completed_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Stage 4: Reward Selection & Claim Transaction.
    Uses canonical slab_id as the single source of truth.
    Enforces entitlement consumption rules:
      - Validates quantity > 0
      - Validates sufficient total entitlement remaining
      - Validates one-time rewards cannot be selected more than once
      - Idempotently creates / updates BonanzaProgress record in 'Pending' status
    """
    if quantity < 1:
        return {"success": False, "error": "Claim quantity must be at least 1"}

    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.status == 'Approved', Bonanza.is_deleted == False).first()
    if not bonanza:
        return {"success": False, "error": "Campaign not found or not currently approved"}

    slab = db.query(BonanzaSlab).filter(BonanzaSlab.id == slab_id, BonanzaSlab.bonanza_id == bonanza_id, BonanzaSlab.is_active == True).first()
    if not slab:
        return {"success": False, "error": "Invalid reward option (slab not found in this campaign)"}

    # Fetch current catalogue & entitlement
    catalogue_data = get_member_reward_catalogue(db, bonanza_id, partner_id, completed_count=completed_count)
    if "error" in catalogue_data:
        return {"success": False, "error": catalogue_data["error"]}

    total_remaining = catalogue_data["total_entitlement_remaining"]
    cost = getattr(slab, 'entitlement_cost', 1) or 1
    total_cost_required = cost * quantity

    # Find this slab in catalogue
    slab_data = next((s for s in catalogue_data["reward_catalogue"] if s["slab_id"] == slab_id), None)
    if not slab_data:
        return {"success": False, "error": "Reward option not available for evaluation"}

    mode = slab_data["reward_mode"]
    already_claimed_qty = slab_data["units_claimed"]
    units_remaining = slab_data["units_remaining"]

    # Validations
    if not slab_data["is_unlocked"]:
        return {
            "success": False,
            "error": f"Milestone target not yet reached. Required: {slab.target_from} completed deals, Current: {catalogue_data['completed_files']}."
        }

    if mode == 'one_time' and already_claimed_qty > 0:
        return {"success": False, "error": "This one-time reward has already been claimed for this campaign"}

    if total_cost_required > total_remaining:
        return {
            "success": False,
            "error": f"Insufficient remaining entitlement. Required: {total_cost_required} unit(s), Available: {total_remaining} unit(s)."
        }

    if quantity > units_remaining:
        return {
            "success": False,
            "error": f"Requested quantity ({quantity}) exceeds available units for this reward ({units_remaining})."
        }

    now = get_indian_time()

    # Check for existing claim record for this partner and slab
    existing_claim = db.query(BonanzaProgress).filter(
        BonanzaProgress.bonanza_id == bonanza_id,
        BonanzaProgress.partner_id == partner_id,
        BonanzaProgress.slab_id == slab_id
    ).first()

    if existing_claim:
        existing_claim.quantity_claimed = (existing_claim.quantity_claimed or 0) + quantity
        existing_claim.current_progress = catalogue_data["completed_files"]
        existing_claim.updated_at = now
        existing_claim.selected_reward_name = slab.award_name or slab.slab_label
        claim_rec = existing_claim
    else:
        claim_rec = BonanzaProgress(
            bonanza_id=bonanza_id,
            partner_id=partner_id,
            slab_id=slab.id,  # CANONICAL REFERENCE
            claim_level=slab.slab_order or 1,
            selected_reward_name=slab.award_name or slab.slab_label,  # Snapshot
            current_progress=catalogue_data["completed_files"],
            achievement_status='Achieved',
            achieved_date=now,
            processed_status='Pending',
            reward_given=False,
            quantity_earned=slab_data["units_earned"],
            quantity_claimed=quantity,
            notes=f"Selected Reward: {slab.award_name} (Cost: {cost} unit(s) × {quantity})",
            created_at=now,
            updated_at=now
        )
        db.add(claim_rec)

    # Increment campaign winners count if new claim
    if not existing_claim:
        bonanza.current_winners = (bonanza.current_winners or 0) + 1
        slab.current_winners = (slab.current_winners or 0) + 1

    db.commit()
    db.refresh(claim_rec)

    return {
        "success": True,
        "message": f"Reward '{slab.award_name}' selected successfully! Claim #{claim_rec.id} submitted for processing.",
        "claim_id": claim_rec.id,
        "slab_id": slab.id,
        "reward_name": slab.award_name,
        "quantity_claimed": claim_rec.quantity_claimed,
        "processed_status": claim_rec.processed_status,
        "units_remaining": max(0, total_remaining - total_cost_required)
    }


def backfill_extra_commission(db: Session, bonanza_id: int) -> Dict[str, Any]:
    """
    Idempotent backfill evaluator for Extra Commission bonanzas (e.g. BZ096).
    Evaluates all eligible leads in the campaign window that reached 'file_submitted'
    (or other configured trigger) and creates PENDING EXTRA_COMMISSION in vgk_cash_income_entries.
    Guaranteed idempotent via bonanza_extra_commission_log.
    """
    from app.services.vgk_cash_income import _next_entry_number, _get_ist

    ADMIN_CHARGE_PCT = Decimal('8')
    TDS_PCT = Decimal('2')

    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.is_deleted == False).first()
    if not bonanza:
        return {"error": "Bonanza not found"}

    bz_start = _to_date(bonanza.start_date)
    bz_end = _to_date(bonanza.end_date)
    grace = int(getattr(bonanza, 'grace_days', 0) or 0)
    bz_end_with_grace = bz_end + timedelta(days=grace) if bz_end else None

    seg_id = getattr(bonanza, 'segment_id', None)
    is_solar = seg_id and (seg_id in _SOLAR_CAT_IDS)

    # Query leads
    seg_clause = f"AND cl.category_id = ANY(ARRAY{list(_SOLAR_CAT_IDS)})" if is_solar else (f"AND cl.category_id = {seg_id}" if seg_id else "")

    # DC-SOLAR-SPEC-20260911: For solar leads, file_submitted bonanza requires that the lead
    # has reached 'with_bank' (or subsequent stages) or has an approved/released Stage 1 advance.
    # Fresh leads with no stage set (e.g. Lead #8921) do not qualify.
    solar_stage_clause = ""
    if is_solar:
        solar_stage_clause = """
            AND (
                cl.solar_pipeline_status IN ('pending_with_bank', 'with_bank', 'load_extension', 'electricity_bill_change',
                                             'installation_pending', 'net_meter_pending', 'balance_pending',
                                             'balance_received', 'subsidy_pending', 'completed')
                OR cl.id IN (SELECT lead_id FROM vgk_solar_cibil_advances WHERE status IN ('RELEASED', 'STAGE1_APPROVED', 'PAID') AND kind = 'ADVANCE')
            )
        """

    leads_sql = f"""
        SELECT cl.id, cl.category_id, cl.associated_partner_id, cl.team_senior_partner_id,
               cl.submit_date, cl.created_at, cl.solar_pipeline_status, cl.name
        FROM crm_leads cl
        WHERE (
            (cl.submit_date IS NOT NULL AND cl.submit_date >= :start AND cl.submit_date <= :end)
            OR (cl.created_at >= CAST(:start AS TIMESTAMP) AND cl.created_at <= CAST(:end AS TIMESTAMP) + INTERVAL '1 day')
        )
        {seg_clause}
        {solar_stage_clause}
        ORDER BY cl.id ASC
    """
    leads = db.execute(text(leads_sql), {'start': bz_start, 'end': bz_end_with_grace}).fetchall()

    reconciliation = {
        "bonanza_id": bonanza.id,
        "bonanza_name": bonanza.name,
        "eligible_files": len(leads),
        "l1_eligible_count": 0,
        "l1_total_amount": 0.0,
        "l2_eligible_count": 0,
        "l2_total_amount": 0.0,
        "existing_records": 0,
        "newly_created": 0,
        "duplicates_prevented": 0,
        "details": []
    }

    now_ist = _get_ist().replace(tzinfo=None)
    company_id = 4

    l1_amt = float(bonanza.ec_l1_amount or 0)
    l2_amt = float(bonanza.ec_l2_amount or 0)

    for l in leads:
        lead_id = l.id
        l1_id = l.associated_partner_id
        l2_id = l.team_senior_partner_id

        levels = []
        if l1_amt > 0 and l1_id:
            levels.append((1, l1_id, Decimal(str(l1_amt))))
            reconciliation["l1_eligible_count"] += 1
            reconciliation["l1_total_amount"] += l1_amt
        if l2_amt > 0 and l2_id:
            levels.append((2, l2_id, Decimal(str(l2_amt))))
            reconciliation["l2_eligible_count"] += 1
            reconciliation["l2_total_amount"] += l2_amt

        for lv, pid, amt in levels:
            # Check idempotency log
            exists = db.execute(text("""
                SELECT id, vci_entry_id FROM bonanza_extra_commission_log
                WHERE bonanza_id = :bid AND lead_id = :lid AND level = :lv
            """), {'bid': bonanza.id, 'lid': lead_id, 'lv': lv}).fetchone()

            if exists:
                reconciliation["existing_records"] += 1
                reconciliation["duplicates_prevented"] += 1
                continue

            # Calculate deductions
            admin = (amt * ADMIN_CHARGE_PCT / 100).quantize(Decimal('0.01'))
            tds = (amt * TDS_PCT / 100).quantize(Decimal('0.01'))
            net = amt - admin - tds

            entry_no = _next_entry_number(db, company_id)
            inc_date = _to_date(l.submit_date or l.created_at) or now_ist.date()

            vci_id = db.execute(text("""
                INSERT INTO vgk_cash_income_entries
                  (company_id, entry_number, partner_id, source_lead_id,
                   kind, status, commission_amount, admin_charges,
                   tds_amount, net_payout, level, notes, income_date,
                   bonanza_id, created_at, updated_at)
                VALUES
                  (:co, :en, :pid, :lid,
                   'EXTRA_COMMISSION', 'PENDING',
                   :ca, :ac, :ta, :np, :lv,
                   :notes, :inc_date, :bid, :now, :now)
                RETURNING id
            """), {
                'co': company_id,
                'en': entry_no,
                'pid': pid,
                'lid': lead_id,
                'ca': float(amt),
                'ac': float(admin),
                'ta': float(tds),
                'np': float(net),
                'lv': lv,
                'notes': f"Special Bonanza: {bonanza.name} | File Submitted | L{lv} Extra Commission",
                'inc_date': inc_date,
                'bid': bonanza.id,
                'now': now_ist,
            }).scalar()

            # Record in idempotency log
            db.execute(text("""
                INSERT INTO bonanza_extra_commission_log
                  (bonanza_id, lead_id, level, partner_id, vci_entry_id, created_at)
                VALUES
                  (:bid, :lid, :lv, :pid, :vid, :now)
                ON CONFLICT (bonanza_id, lead_id, level) DO NOTHING
            """), {
                'bid': bonanza.id,
                'lid': lead_id,
                'lv': lv,
                'pid': pid,
                'vid': vci_id,
                'now': now_ist,
            })

            reconciliation["newly_created"] += 1
            reconciliation["details"].append({
                "lead_id": lead_id,
                "lead_name": l.name,
                "level": lv,
                "partner_id": pid,
                "amount": float(amt),
                "entry_number": entry_no,
                "vci_id": vci_id
            })

    db.commit()
    return reconciliation
