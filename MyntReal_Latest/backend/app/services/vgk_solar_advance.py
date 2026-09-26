"""
VGK Solar CIBIL Advance Service (DC Protocol Apr 2026)

₹1,000 advance released to L1 VGK partner when their referred solar lead clears:
  1. solar_pipeline_status = 'application_submitted' (or any subsequent non-terminal stage)
  2. cibil_confirmed = True
  3. cibil_score >= 600

Advance Lifecycle:
  PENDING  → advance record created (eligibility gate passed), awaiting staff release
  RELEASED → staff releases ₹1,000 to partner's vgk_cash_wallet
  ADJUSTED → deal completes; ₹1,000 deducted from final cash income draft
  RECOVERED → lead cancelled / rejected after release; ₹1,000 auto-deducted from wallet
  DEFICIT  → recovery attempted but wallet insufficient; deducted from future earnings

Earnings commission (via vgk_cash_income) is ALWAYS based on confirmed transaction amounts,
not deal_value_total. This file handles only the advance lifecycle, not main commissions.

Zero negative impact: advance creation, release, and recovery are all non-blocking.
Walk-in saves, lead updates, and commission calculations are never rolled back due to this service.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# DC-VGK-STAGE2-CUTOFF-20260925: Hard business effective date for payment-based Stage 2 advances
STAGE2_EFFECTIVE_DATE = datetime(2026, 9, 25, 0, 0, 0)

# DC-SOLAR-SPEC-20260911: Stage 1 Advance (With Bank + CIBIL >= 700 + Ground Source set)
# L1 (Ground Source): 1000, L2 (Senior): 500 — per VGK Commission & Advance Payment Logic.
ADVANCE_AMOUNT    = Decimal('1000.00')
L2_ADVANCE_AMOUNT = Decimal('500.00')
# DC-SOLAR-SPEC-20260916: Stage 2 Advance (Installation / DVR > 0 confirmed)
# L1: 1000, L2: 500
DVR_L1_AMOUNT     = Decimal('1000.00')
DVR_L2_AMOUNT     = Decimal('500.00')
CIBIL_MIN_SCORE   = 700

# Solar pipeline stages that are eligible for Stage 1 advance (Strictly 'with bank' and onwards)
ELIGIBLE_STAGES = {
    'pending_with_bank', 'with_bank',
    'load_extension', 'electricity_bill_change', 'installation_pending',
    'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending', 'completed',
}

# Stages that trigger recovery of already-released advances
RECOVERY_STAGES = {'loan_rejected', 'not_interested', 'cancelled', 'bank_not_interested'}


def _get_ist():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


def _next_advance_number(db: Session) -> str:
    now = _get_ist()
    yymm = now.strftime('%y%m')
    prefix = f'VSCA-{yymm}'
    # DC-FIX-2606-ADV-NUM-V2: Only consider well-formed entries matching exactly
    # 'VSCA-YYMM-NNNN' (regex anchor). SPLIT_PART broke on malformed entries
    # like 'VSCA-2605-26050002' returning 26050002 instead of 2 — each successive
    # entry then embedded the previous malformed sequence as its prefix.
    result = db.execute(text(
        "SELECT MAX(CAST(RIGHT(entry_number, 4) AS INTEGER)) "
        "FROM vgk_solar_cibil_advances "
        "WHERE entry_number ~ ('^VSCA-[0-9]{4}-[0-9]{4}$') "
        "  AND entry_number LIKE :pfx"
    ), {'pfx': f'{prefix}-%'}).scalar()
    seq = (result or 0) + 1
    return f'{prefix}-{seq:04d}'


def check_and_create_advance(db: Session, lead_id: int, bypass_cibil: bool = False, notes: str = None) -> dict:
    """
    Called whenever solar_pipeline_status or CIBIL fields change on a lead.
    Creates PENDING advance records for L1 (₹1,000) and L2 (₹500, if senior
    partner set) if ALL eligibility criteria are met and no advance record
    already exists for that (lead_id, level, kind='ADVANCE').

    If bypass_cibil=True, called from Stage 2 (DVR advance) to release deferred
    Stage 1 advance for files whose CIBIL was < 700 at the 'with_bank' stage.

    Returns: {'created': bool, 'entry_numbers': list|None, 'reason': str}
    """
    try:
        db.flush()
        from app.models.crm import CRMLead
        lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()

        if not lead:
            return {'created': False, 'reason': 'Lead not found'}

        if not lead.associated_partner_id:
            return {'created': False, 'reason': 'No associated VGK partner'}

        # DC-L1-GROUND-SOURCE-001: L1 advance should credit the Ground Source instead of the Showroom partner
        l1_partner_id = None
        if lead.source_ref_type in ('partner', 'vgk_partner') and lead.source_ref_id and lead.source_ref_id.isdigit():
            l1_partner_id = int(lead.source_ref_id)
        elif lead.mnr_handler_id:
            l1_partner_id = lead.mnr_handler_id
        else:
            l1_partner_id = lead.associated_partner_id

        if not l1_partner_id:
            return {'created': False, 'reason': 'No Ground Source (L1) partner set'}

        pipeline = (lead.solar_pipeline_status or '').strip()

        if not bypass_cibil and pipeline not in ELIGIBLE_STAGES:
            return {'created': False, 'reason': f'Stage {pipeline!r} not eligible (must be with_bank or subsequent)'}

        # Require CIBIL verification (score >= 700) before calculating/releasing advances at with_bank stage
        score = getattr(lead, 'cibil_score', None)
        if not bypass_cibil:
            is_cibil_valid = ((score or 0) >= CIBIL_MIN_SCORE)
            if not is_cibil_valid:
                return {'created': False, 'reason': f'CIBIL score below {CIBIL_MIN_SCORE} (got {score}) — Stage 1 advance deferred until Stage 2 DVR'}

        now = _get_ist()
        created_numbers = []

        # Resolve L2 Senior Upliner: lead.team_senior_partner_id with fallback to official_partners.parent_partner_id
        l2_partner_id = getattr(lead, 'team_senior_partner_id', None)
        if not l2_partner_id and l1_partner_id:
            try:
                _p_row = db.execute(text(
                    "SELECT parent_partner_id FROM official_partners WHERE id = :pid"
                ), {'pid': l1_partner_id}).fetchone()
                if _p_row and _p_row.parent_partner_id:
                    l2_partner_id = _p_row.parent_partner_id
            except Exception as _p_err:
                logger.debug(f"[VGK-SOLAR-ADV] L2 parent lookup failed: {_p_err}")

        # Advance tiers: (level, partner_id, amount)
        tiers = []
        if l1_partner_id:
            tiers.append((1, l1_partner_id, ADVANCE_AMOUNT))
        if l2_partner_id:
            tiers.append((2, l2_partner_id, L2_ADVANCE_AMOUNT))

        for (level, partner_id, amount) in tiers:
            # Idempotency: one advance per (lead, level, kind='ADVANCE')
            existing = db.execute(text(
                "SELECT id, status FROM vgk_solar_cibil_advances "
                "WHERE lead_id = :lid AND level = :lv AND kind = 'ADVANCE' LIMIT 1"
            ), {'lid': lead_id, 'lv': level}).fetchone()

            if existing:
                logger.debug(
                    f'[VGK-SOLAR-ADV] L{level} advance already exists for lead {lead_id} '
                    f'(status: {existing.status}) — skipping'
                )
                continue

            entry_number = _next_advance_number(db)
            adv_notes = notes or ('Auto-created on with_bank' if not bypass_cibil else 'Deferred Stage 1 catch-up at Stage 2 DVR')

            db.execute(text("""
                INSERT INTO vgk_solar_cibil_advances
                    (company_id, lead_id, partner_id, entry_number, advance_amount,
                     status, stage_at_eligibility, cibil_score_at_check,
                     level, kind, notes, created_at, updated_at)
                VALUES
                    (:cid, :lid, :pid, :en, :amt,
                     'PENDING', :stage, :score,
                     :lv, 'ADVANCE', :notes, :now, :now)
            """), {
                'cid': lead.company_id,
                'lid': lead_id,
                'pid': partner_id,
                'en': entry_number,
                'amt': float(amount),
                'stage': pipeline or 'dvr_catchup',
                'score': score,
                'lv': level,
                'notes': adv_notes,
                'now': now.replace(tzinfo=None),
            })
            db.commit()

            logger.info(
                f'[VGK-SOLAR-ADV] PENDING L{level} advance {entry_number} created for '
                f'lead {lead_id}, partner {partner_id}, stage={pipeline}, CIBIL={score}'
            )

            # Mirror the advance into vgk_cash_income_entries as PENDING
            try:
                # Fetch the newly created advance row to pass to mirroring
                adv_row = db.execute(text(
                    "SELECT id, entry_number, partner_id, lead_id, advance_amount, company_id, COALESCE(level,1) AS level "
                    "FROM vgk_solar_cibil_advances WHERE entry_number = :en"
                ), {'en': entry_number}).fetchone()
                
                if adv_row:
                    from app.services.vgk_cash_income import record_solar_advance_as_income_row
                    record_solar_advance_as_income_row(db, adv_row, released_by_id=None)
                    db.commit()
            except Exception as _mr_e:
                logger.warning(f'[VGK-SOLAR-ADV] Auto-mirror PENDING L{level} failed: {_mr_e}')

            created_numbers.append(entry_number)

        if created_numbers:
            # DC-BONANZA-STAGE1-HOOK-001 (Sep 2026): Fire file_submitted extra commission & award triggers
            # on Stage 1 CIBIL advance creation. Runs once per qualified file. Idempotency guarded.
            try:
                from app.services.vgk_extra_commission import apply_extra_commission_if_active as _ec_stage1
                _ec_stage1(db, lead, 'file_submitted')
            except Exception as _ec_err:
                logger.warning(f'[VGK-SOLAR-ADV] Bonanza extra commission hook failed for lead {lead_id}: {_ec_err}')

            try:
                from app.services.vgk_award_trigger import apply_award_gift_trigger_if_active as _at_stage1
                _at_stage1(db, lead, 'file_submitted')
            except Exception as _at_err:
                logger.warning(f'[VGK-SOLAR-ADV] Bonanza award trigger hook failed for lead {lead_id}: {_at_err}')

            try:
                from app.services.vgk_cash_bonus_trigger import apply_cash_bonus_trigger_if_active as _cb_stage1
                _cb_stage1(db, lead, 'file_submitted')
            except Exception as _cb_err:
                logger.warning(f'[VGK-SOLAR-ADV] Bonanza cash bonus hook failed for lead {lead_id}: {_cb_err}')

            return {'created': True, 'entry_numbers': created_numbers}
        return {'created': False, 'reason': 'All advances already existed'}

    except Exception as e:
        logger.warning(f'[VGK-SOLAR-ADV] check_and_create_advance failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'created': False, 'reason': str(e)}


def _legacy_check_and_create_dvr_advance(db: Session, lead_id: int) -> dict:
    """
    Legacy Stage 2 Advance logic for transactions / events <= 2026-09-23.
    """
    DVR_L1_AMOUNT = Decimal('1000.00')
    DVR_L2_AMOUNT = Decimal('500.00')
    DVR_L5_AMOUNT = Decimal('1000.00')

    try:
        lead = db.execute(text("""
            SELECT id, company_id, category_id, associated_partner_id,
                   team_senior_partner_id, vgk_field_support_id, deal_value_received, first_dvr_confirmed_at
            FROM crm_leads WHERE id = :lid
        """), {'lid': lead_id}).fetchone()

        if not lead:
            return {'created': False, 'reason': 'Lead not found'}
        _SOLAR_CAT_IDS_ADV = (6, 19, 36, 48)
        if (lead.category_id or 0) not in _SOLAR_CAT_IDS_ADV:
            return {'created': False, 'reason': f'Not solar (category_id={lead.category_id})'}
        if not lead.associated_partner_id:
            return {'created': False, 'reason': 'No associated VGK partner'}

        dvr = Decimal(str(lead.deal_value_received or 0))
        if dvr <= 0:
            return {'created': False, 'reason': 'DVR is zero'}

        now_ist = _get_ist().replace(tzinfo=None)

        first_dvr_at = lead.first_dvr_confirmed_at
        if first_dvr_at is None:
            first_dvr_at = now_ist
            db.execute(text(
                "UPDATE crm_leads SET first_dvr_confirmed_at = :fda "
                "WHERE id = :lid AND first_dvr_confirmed_at IS NULL"
            ), {'fda': first_dvr_at, 'lid': lead_id})
            db.commit()

        if hasattr(first_dvr_at, 'tzinfo') and first_dvr_at.tzinfo is not None:
            first_dvr_at = first_dvr_at.replace(tzinfo=None)

        l1_partner_id = lead.associated_partner_id
        l2_partner_id = lead.team_senior_partner_id
        if not l2_partner_id and l1_partner_id:
            try:
                _p_row = db.execute(text(
                    "SELECT parent_partner_id FROM official_partners WHERE id = :pid"
                ), {'pid': l1_partner_id}).fetchone()
                if _p_row and _p_row.parent_partner_id:
                    l2_partner_id = _p_row.parent_partner_id
            except Exception as _p_err:
                logger.debug(f"[DVR-ADV] L2 parent lookup failed: {_p_err}")

        tiers = [(1, l1_partner_id, DVR_L1_AMOUNT)]
        if l2_partner_id:
            tiers.append((2, l2_partner_id, DVR_L2_AMOUNT))
        if lead.vgk_field_support_id:
            tiers.append((5, lead.vgk_field_support_id, DVR_L5_AMOUNT))

        created_numbers = []

        for (level, partner_id, amount) in tiers:
            existing = db.execute(text(
                "SELECT id, status FROM vgk_solar_cibil_advances "
                "WHERE lead_id=:lid AND level=:lv AND kind='DVR_ADVANCE' AND partner_id=:pid LIMIT 1"
            ), {'lid': lead_id, 'lv': level, 'pid': partner_id}).fetchone()
            if existing:
                logger.debug(
                    f'[DVR-ADV] L{level} already exists for lead {lead_id} '
                    f'(status:{existing.status}) — skipping'
                )
                continue

            entry_number = _next_advance_number(db)

            db.execute(text("""
                INSERT INTO vgk_solar_cibil_advances
                    (company_id, lead_id, partner_id, entry_number, advance_amount,
                     status, stage_at_eligibility, cibil_score_at_check,
                     level, kind, created_at, updated_at)
                VALUES
                    (:cid, :lid, :pid, :en, :amt,
                     'PENDING', 'dvr_confirmed', NULL,
                     :lv, 'DVR_ADVANCE', :now, :now)
            """), {
                'cid': lead.company_id, 'lid': lead_id, 'pid': partner_id,
                'en': entry_number, 'amt': float(amount),
                'lv': level, 'now': now_ist,
            })
            db.commit()

            logger.info(
                f'[DVR-ADV] PENDING L{level} DVR_ADVANCE {entry_number} — '
                f'lead {lead_id} partner {partner_id} DVR=₹{float(dvr)}'
            )

            try:
                adv_row = db.execute(text(
                    "SELECT id, entry_number, partner_id, lead_id, advance_amount, company_id, COALESCE(level,1) AS level "
                    "FROM vgk_solar_cibil_advances WHERE entry_number = :en"
                ), {'en': entry_number}).fetchone()
                
                if adv_row:
                    from app.services.vgk_cash_income import record_dvr_advance_as_income_row
                    record_dvr_advance_as_income_row(db, adv_row, released_by_id=None)
                    db.commit()
            except Exception as _mr_e:
                logger.warning(f'[DVR-ADV] Auto-mirror PENDING DVR L{level} failed: {_mr_e}')

            created_numbers.append(entry_number)

        try:
            s1_exists = db.execute(text(
                "SELECT id FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'ADVANCE' LIMIT 1"
            ), {'lid': lead_id}).fetchone()
            if not s1_exists:
                logger.info(f'[DVR-ADV] Triggering deferred Stage 1 advance catch-up for lead {lead_id}')
                _s1_res = check_and_create_advance(
                    db, lead_id, bypass_cibil=True,
                    notes="Stage 1 advance auto-triggered at Stage 2 DVR (deferred low CIBIL catch-up)"
                )
                if _s1_res.get('created') and _s1_res.get('entry_numbers'):
                    created_numbers.extend(_s1_res['entry_numbers'])
        except Exception as _s1_err:
            logger.warning(f'[DVR-ADV] Stage 1 deferred catch-up failed for lead {lead_id}: {_s1_err}')

        if created_numbers:
            return {'created': True, 'entry_numbers': created_numbers}
        return {'created': False, 'reason': 'All DVR advances already existed'}

    except Exception as e:
        logger.warning(f'[DVR-ADV] _legacy_check_and_create_dvr_advance failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'created': False, 'reason': str(e)}


def process_payment_stage2_advance(
    db: Session,
    lead_id: int,
    transaction_id: int,
    payment_amount: Decimal,
    transaction_date: Optional[Union[datetime, date]] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    VGK4U Stage 2 Advance Engine (Payment-Event Based, Effective 24 September 2026).
    
    1. Effective Date Guard: Payments prior to 2026-09-24 follow legacy DVR process.
    2. Dynamic 5 Commission Layers (L1 Producer, L2 Manager/Sponsor, L3 GM, L4 RM, L5 Field Support).
       Rates dynamically resolved from active canonical commission configuration.
    3. Option C (Pro-Rata Stage 1 Advance Recovery):
       Proposed = (Original L1 Stage 1 * (Payment Amount / Deal Value Total)).
       Actual = min(Proposed, Remaining Stage 1 Balance, L1 Stage 2 Gross).
       Final payment: proposed clears entire remaining Stage 1 balance.
       Adjustment applies ONLY against L1 (Producer). Uplines (L2..L5) receive 100% without reduction.
    4. Strict idempotency anchored to source_transaction_id.
    """
    from app.services.vgk4u_career_service import ROOT_APEX_PARTNER_ID
    from app.services.vgk4u_waterfall_engine import VGK4UWaterfallEngine
    from app.services.vgk_cash_income import record_dvr_advance_as_income_row

    try:
        now_ist = _get_ist().replace(tzinfo=None)

        # 1. Effective Cutoff Check
        txn_dt = transaction_date
        if txn_dt is not None:
            if isinstance(txn_dt, date) and not isinstance(txn_dt, datetime):
                txn_dt = datetime.combine(txn_dt, datetime.min.time())
            elif hasattr(txn_dt, 'tzinfo') and txn_dt.tzinfo is not None:
                txn_dt = txn_dt.replace(tzinfo=None)
        else:
            try:
                t_row = db.execute(text(
                    "SELECT transaction_date, validated_at, created_at FROM crm_lead_transactions WHERE id = :tid"
                ), {'tid': transaction_id}).fetchone()
                if t_row:
                    raw_d = t_row.transaction_date or t_row.validated_at or t_row.created_at
                    if raw_d:
                        if isinstance(raw_d, date) and not isinstance(raw_d, datetime):
                            txn_dt = datetime.combine(raw_d, datetime.min.time())
                        elif hasattr(raw_d, 'tzinfo') and raw_d.tzinfo is not None:
                            txn_dt = raw_d.replace(tzinfo=None)
                        else:
                            txn_dt = raw_d
            except Exception as _te:
                logger.debug(f"[STAGE2-ADV] Could not query txn #{transaction_id}: {_te}")

        effective_dt = txn_dt or now_ist

        if effective_dt < STAGE2_EFFECTIVE_DATE:
            logger.info(
                f"[STAGE2-ADV] Transaction #{transaction_id} date {effective_dt} is prior to cutoff {STAGE2_EFFECTIVE_DATE}. "
                f"Routing to legacy check_and_create_dvr_advance."
            )
            return _legacy_check_and_create_dvr_advance(db, lead_id)

        # 2. Idempotency Guard
        existing_advs = db.execute(text("""
            SELECT id, entry_number, status, level FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND kind = 'DVR_ADVANCE'
        """), {'tid': transaction_id}).fetchall()
        if existing_advs:
            logger.info(f"[STAGE2-ADV] Transaction #{transaction_id} already has Stage 2 advance(s) — skipping duplicate.")
            return {
                'created': False,
                'reason': f'Stage 2 advance already processed for transaction {transaction_id}',
                'existing_ids': [r.id for r in existing_advs]
            }

        # 3. Payment Amount Validation
        amt = Decimal(str(payment_amount or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amt <= 0:
            return {'created': False, 'reason': 'Payment amount must be greater than 0'}

        # 4. Lead & Partner Eligibility
        lead = db.execute(text("""
            SELECT id, company_id, category_id, associated_partner_id,
                   team_senior_partner_id, team_extended_partner_id, team_core_partner_id,
                   vgk_field_support_id, deal_value_total, deal_value_received,
                   deal_value_balance, solar_value, deal_value, remaining_stage1_advance,
                   solar_pipeline_status, first_dvr_confirmed_at
            FROM crm_leads WHERE id = :lid
        """), {'lid': lead_id}).fetchone()

        if not lead:
            return {'created': False, 'reason': 'Lead not found'}

        from app.services.vgk_cash_income import _resolve_category_slug
        category_slug = _resolve_category_slug(db, lead)
        cat_cfg = VGK4UWaterfallEngine.get_category_config(db, category_slug)
        earning_basis_type = getattr(cat_cfg, 'earning_basis_type', 'PAYMENT_RECEIVED') if cat_cfg else 'PAYMENT_RECEIVED'
        underlying_val = Decimal(str(lead.deal_value_total or lead.solar_value or lead.deal_value or 0))

        if not lead.associated_partner_id:
            return {'created': False, 'reason': 'No associated VGK partner'}

        # Stamp first_dvr_confirmed_at if not set
        if lead.first_dvr_confirmed_at is None:
            db.execute(text(
                "UPDATE crm_leads SET first_dvr_confirmed_at = :fda "
                "WHERE id = :lid AND first_dvr_confirmed_at IS NULL"
            ), {'fda': now_ist, 'lid': lead_id})
            db.commit()

        # 5. Resolve 5 Canonical Layers using Waterfall Engine (Universal 9% Network Model)
        wf_allocations = []
        try:
            wf_res = VGK4UWaterfallEngine.calculate_commission_structure(
                db=db,
                producer_partner_id=lead.associated_partner_id,
                deal_value=amt,
                category_slug=category_slug,
                direct_sponsor_id=lead.team_senior_partner_id,
                support_partner_id=lead.vgk_field_support_id,
                is_end_to_end_support=bool(lead.vgk_field_support_id),
                showroom_partner_id=None,
            )
            if isinstance(wf_res, dict) and wf_res.get('allocations'):
                wf_allocations = wf_res['allocations']
        except Exception as _wf_err:
            logger.warning(f"[STAGE2-ADV] Waterfall engine error for lead {lead_id}: {_wf_err}")

        # Map allocations into canonical 5 layers keyed by (target_lvl, pid)
        layer_map = {}
        for alloc in wf_allocations:
            lvl = alloc.get('level')
            role = alloc.get('role')
            pid = alloc.get('partner_id')
            if not pid or pid == ROOT_APEX_PARTNER_ID or role == 'APEX_REMAINDER':
                continue
            if role == 'SHOWROOM' or lvl == 6:
                continue

            if role == 'PRODUCER' or lvl == 1:
                target_lvl = 1
            elif role in ('DIRECT_SPONSOR_OVERRIDE', 'MANAGER_DIFFERENTIAL') or lvl == 2:
                target_lvl = 2
            elif role == 'GM_DIFFERENTIAL' or lvl == 3:
                target_lvl = 3
            elif role == 'RM_DIFFERENTIAL' or lvl == 4:
                target_lvl = 4
            elif role in ('FIELD_SUPPORT', 'FULL_SUPPORT') or lvl in (5, 7):
                target_lvl = 5
            else:
                continue

            target_key = (target_lvl, pid)
            if target_key not in layer_map:
                layer_map[target_key] = {
                    'level': target_lvl,
                    'partner_id': pid,
                    'role': role,
                    'commission_pct': Decimal(str(alloc.get('commission_pct', 0))),
                    'commission_amount': Decimal(str(alloc.get('commission_amount', 0))),
                }
            else:
                layer_map[target_key]['commission_pct'] += Decimal(str(alloc.get('commission_pct', 0)))
                layer_map[target_key]['commission_amount'] += Decimal(str(alloc.get('commission_amount', 0)))
                if role not in layer_map[target_key]['role']:
                    layer_map[target_key]['role'] = f"{layer_map[target_key]['role']}+{role}"

        # Fallback L1 Producer (5.00%) if not resolved
        l1_entries = [alloc for k, alloc in layer_map.items() if k[0] == 1]
        if not l1_entries and lead.associated_partner_id:
            cfg = cat_cfg or VGK4UWaterfallEngine.get_category_config(db, category_slug)
            l1_pct = Decimal(str(cfg.producer_base_pct if cfg else '5.00'))
            l1_amt = (amt * l1_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            target_key = (1, lead.associated_partner_id)
            layer_map[target_key] = {
                'level': 1, 'partner_id': lead.associated_partner_id, 'role': 'PRODUCER',
                'commission_pct': l1_pct, 'commission_amount': l1_amt
            }
            l1_entries = [layer_map[target_key]]

        # 6. Option C: Pro-Rata Stage 1 Advance Recovery (applied independently against L1 and L2)
        # Stage 1 Advance Pool: L1 = ₹1,000, L2 = ₹500. Total = ₹1,500.
        l1_entry = l1_entries[0] if l1_entries else None
        l1_gross = l1_entry['commission_amount'] if l1_entry else Decimal('0.00')

        l2_entries = [alloc for k, alloc in layer_map.items() if k[0] == 2 and 'DIRECT_SPONSOR_OVERRIDE' in alloc.get('role', '')]
        if not l2_entries:
            l2_entries = [alloc for k, alloc in layer_map.items() if k[0] == 2]
        l2_entry = l2_entries[0] if l2_entries else None
        l2_gross = l2_entry['commission_amount'] if l2_entry else Decimal('0.00')

        # Query existing Stage 1 advance records for L1 and L2
        s1_l1_row = db.execute(text("""
            SELECT id, advance_amount, COALESCE(adjustment_amount, 0) as adjustment_amount
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 1 AND kind = 'ADVANCE'
              AND status IN ('RELEASED', 'STAGE1_APPROVED', 'PAID')
            ORDER BY id ASC LIMIT 1
        """), {'lid': lead_id}).fetchone()

        s1_l2_row = db.execute(text("""
            SELECT id, advance_amount, COALESCE(adjustment_amount, 0) as adjustment_amount
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 2 AND kind = 'ADVANCE'
              AND status IN ('RELEASED', 'STAGE1_APPROVED', 'PAID')
            ORDER BY id ASC LIMIT 1
        """), {'lid': lead_id}).fetchone()

        # Determine remaining and original Stage 1 amounts for L1
        if s1_l1_row:
            orig_s1_l1 = Decimal(str(s1_l1_row.advance_amount or 1000.00))
            rem_s1_l1 = max(Decimal('0.00'), orig_s1_l1 - Decimal(str(s1_l1_row.adjustment_amount or 0)))
        elif getattr(lead, 'remaining_stage1_advance_l1', None) is not None:
            rem_s1_l1 = Decimal(str(lead.remaining_stage1_advance_l1 or 0))
            orig_s1_l1 = Decimal('1000.00') if rem_s1_l1 > 0 else Decimal('0.00')
        else:
            rem_s1_l1 = Decimal('0.00')
            orig_s1_l1 = Decimal('0.00')

        # Determine remaining and original Stage 1 amounts for L2
        if s1_l2_row:
            orig_s1_l2 = Decimal(str(s1_l2_row.advance_amount or 500.00))
            rem_s1_l2 = max(Decimal('0.00'), orig_s1_l2 - Decimal(str(s1_l2_row.adjustment_amount or 0)))
        elif getattr(lead, 'remaining_stage1_advance_l2', None) is not None:
            rem_s1_l2 = Decimal(str(lead.remaining_stage1_advance_l2 or 0))
            orig_s1_l2 = Decimal('500.00') if rem_s1_l2 > 0 else Decimal('0.00')
        else:
            rem_s1_l2 = Decimal('0.00')
            orig_s1_l2 = Decimal('0.00')

        # Fallback if lead.remaining_stage1_advance exists on crm_leads without L1/L2 breakdown
        if rem_s1_l1 == 0 and rem_s1_l2 == 0 and getattr(lead, 'remaining_stage1_advance', 0):
            tot_rem = Decimal(str(lead.remaining_stage1_advance or 0))
            if tot_rem > Decimal('0.00'):
                rem_s1_l1 = min(Decimal('1000.00'), tot_rem)
                orig_s1_l1 = Decimal('1000.00')
                rem_s1_l2 = max(Decimal('0.00'), tot_rem - rem_s1_l1)
                orig_s1_l2 = Decimal('500.00') if rem_s1_l2 > 0 else Decimal('0.00')

        actual_adj_l1 = Decimal('0.00')
        actual_adj_l2 = Decimal('0.00')
        new_rem_s1_l1 = rem_s1_l1
        new_rem_s1_l2 = rem_s1_l2

        if rem_s1_l1 > 0 or rem_s1_l2 > 0:
            deal_total = Decimal(str(lead.deal_value_total or lead.solar_value or lead.deal_value or 0))
            if deal_total <= 0:
                deal_total = amt

            payment_ratio = min(Decimal('1.0'), amt / deal_total)

            deal_bal = Decimal(str(lead.deal_value_balance)) if lead.deal_value_balance is not None else None
            dvr_so_far = Decimal(str(lead.deal_value_received or 0))
            is_final_payment = False
            if deal_bal is not None and deal_bal <= Decimal('0'):
                is_final_payment = True
            elif dvr_so_far >= deal_total and deal_total > Decimal('0'):
                is_final_payment = True

            # L1 proposed & actual recovery (capped at L1 remaining and L1 Stage 2 gross)
            if rem_s1_l1 > 0:
                if is_final_payment:
                    proposed_adj_l1 = rem_s1_l1
                else:
                    proposed_adj_l1 = (orig_s1_l1 * payment_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                actual_adj_l1 = min(proposed_adj_l1, rem_s1_l1, l1_gross)
                new_rem_s1_l1 = rem_s1_l1 - actual_adj_l1

            # L2 proposed & actual recovery (capped at L2 remaining and L2 Stage 2 gross)
            if rem_s1_l2 > 0:
                if is_final_payment:
                    proposed_adj_l2 = rem_s1_l2
                else:
                    proposed_adj_l2 = (orig_s1_l2 * payment_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                actual_adj_l2 = min(proposed_adj_l2, rem_s1_l2, l2_gross)
                new_rem_s1_l2 = rem_s1_l2 - actual_adj_l2

            # Update crm_leads remaining balances
            db.execute(text("""
                UPDATE crm_leads
                SET remaining_stage1_advance = :tot_rem,
                    remaining_stage1_advance_l1 = :l1_rem,
                    remaining_stage1_advance_l2 = :l2_rem
                WHERE id = :lid
            """), {
                'tot_rem': float(new_rem_s1_l1 + new_rem_s1_l2),
                'l1_rem': float(new_rem_s1_l1),
                'l2_rem': float(new_rem_s1_l2),
                'lid': lead_id,
            })

            # Update L1 Stage 1 advance record
            if actual_adj_l1 > Decimal('0.00'):
                if s1_l1_row:
                    db.execute(text("""
                        UPDATE vgk_solar_cibil_advances
                        SET adjustment_amount = COALESCE(adjustment_amount, 0) + :adj,
                            status = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN 'ADJUSTED' ELSE status END,
                            adjusted_at = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN :now ELSE adjusted_at END,
                            updated_at = :now
                        WHERE id = :aid
                    """), {'adj': float(actual_adj_l1), 'aid': s1_l1_row.id, 'now': now_ist})
                else:
                    db.execute(text("""
                        UPDATE vgk_solar_cibil_advances
                        SET adjustment_amount = COALESCE(adjustment_amount, 0) + :adj,
                            status = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN 'ADJUSTED' ELSE status END,
                            adjusted_at = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN :now ELSE adjusted_at END,
                            updated_at = :now
                        WHERE lead_id = :lid AND level = 1 AND kind = 'ADVANCE'
                    """), {'adj': float(actual_adj_l1), 'lid': lead_id, 'now': now_ist})

            # Update L2 Stage 1 advance record
            if actual_adj_l2 > Decimal('0.00'):
                if s1_l2_row:
                    db.execute(text("""
                        UPDATE vgk_solar_cibil_advances
                        SET adjustment_amount = COALESCE(adjustment_amount, 0) + :adj,
                            status = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN 'ADJUSTED' ELSE status END,
                            adjusted_at = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN :now ELSE adjusted_at END,
                            updated_at = :now
                        WHERE id = :aid
                    """), {'adj': float(actual_adj_l2), 'aid': s1_l2_row.id, 'now': now_ist})
                else:
                    db.execute(text("""
                        UPDATE vgk_solar_cibil_advances
                        SET adjustment_amount = COALESCE(adjustment_amount, 0) + :adj,
                            status = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN 'ADJUSTED' ELSE status END,
                            adjusted_at = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN :now ELSE adjusted_at END,
                            updated_at = :now
                        WHERE lead_id = :lid AND level = 2 AND kind = 'ADVANCE'
                    """), {'adj': float(actual_adj_l2), 'lid': lead_id, 'now': now_ist})

        # 7. Create Stage 2 advance records in vgk_solar_cibil_advances and mirror to vgk_cash_income_entries
        created_numbers = []

        class _AdvRowWrapper:
            def __init__(self, r, pct, src_tid):
                self._r = r
                self.commission_pct = pct
                self.source_transaction_id = src_tid
            def __getattr__(self, name):
                return getattr(self._r, name)

        for key in sorted(layer_map.keys(), key=lambda x: (x[0], x[1])):
            alloc = layer_map[key]
            lvl = alloc['level']
            partner_id = alloc['partner_id']
            comm_pct = alloc['commission_pct']
            adv_gross = alloc['commission_amount']

            if lvl == 1:
                layer_adj = actual_adj_l1
            elif lvl == 2 and (alloc.get('role') == 'DIRECT_SPONSOR_OVERRIDE' or not any(k[0] == 2 and 'DIRECT_SPONSOR_OVERRIDE' in layer_map[k].get('role', '') for k in layer_map)):
                layer_adj = actual_adj_l2
            else:
                layer_adj = Decimal('0.00')

            entry_number = _next_advance_number(db)
            adv_notes = notes or (
                f"Stage 2 Advance ({comm_pct}%) on Txn #{transaction_id} (₹{float(amt):.2f}) [{earning_basis_type}]"
                + (f" [Stage 1 Adj: ₹{float(layer_adj):.2f}]" if layer_adj > 0 else "")
            )

            db.execute(text("""
                INSERT INTO vgk_solar_cibil_advances
                    (company_id, lead_id, partner_id, entry_number, advance_amount,
                     adjustment_amount, status, stage_at_eligibility, cibil_score_at_check,
                     level, kind, notes, source_transaction_id, earning_basis_type,
                     earning_basis_amount, underlying_value, created_at, updated_at)
                VALUES
                    (:cid, :lid, :pid, :en, :amt,
                     :adj, 'PENDING', 'payment_validated', NULL,
                     :lv, 'DVR_ADVANCE', :notes, :tid, :ebt,
                     :eba, :uv, :now, :now)
            """), {
                'cid': lead.company_id or 4,
                'lid': lead_id,
                'pid': partner_id,
                'en': entry_number,
                'amt': float(adv_gross),
                'adj': float(layer_adj) if layer_adj > 0 else None,
                'lv': lvl,
                'notes': adv_notes,
                'tid': transaction_id,
                'ebt': earning_basis_type,
                'eba': float(amt),
                'uv': float(underlying_val),
                'now': now_ist,
            })
            db.flush()

            adv_row = db.execute(text("""
                SELECT id, entry_number, partner_id, lead_id, advance_amount,
                       company_id, COALESCE(level,1) AS level, source_transaction_id,
                       adjustment_amount, earning_basis_type, earning_basis_amount, underlying_value
                FROM vgk_solar_cibil_advances WHERE entry_number = :en
            """), {'en': entry_number}).fetchone()

            if adv_row:
                record_dvr_advance_as_income_row(db, _AdvRowWrapper(adv_row, comm_pct, transaction_id), released_by_id=None)

            created_numbers.append(entry_number)

        # Deferred Stage 1 catch-up if needed
        try:
            s1_exists = db.execute(text(
                "SELECT id FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'ADVANCE' LIMIT 1"
            ), {'lid': lead_id}).fetchone()
            if not s1_exists:
                logger.info(f'[STAGE2-ADV] Triggering deferred Stage 1 advance catch-up for lead {lead_id}')
                _s1_res = check_and_create_advance(
                    db, lead_id, bypass_cibil=True,
                    notes="Stage 1 advance auto-triggered at Stage 2 payment (deferred catch-up)"
                )
                if _s1_res.get('created') and _s1_res.get('entry_numbers'):
                    created_numbers.extend(_s1_res['entry_numbers'])
        except Exception as _s1_err:
            logger.warning(f'[STAGE2-ADV] Stage 1 deferred catch-up failed for lead {lead_id}: {_s1_err}')

        db.commit()
        logger.info(
            f"[STAGE2-ADV] Created {len(created_numbers)} Stage 2 advance(s) for lead {lead_id}, "
            f"txn #{transaction_id}, payment ₹{float(amt)}: {created_numbers}, L1 Adj: ₹{float(actual_adj_l1)}, L2 Adj: ₹{float(actual_adj_l2)}"
        )
        return {
            'created': True,
            'transaction_id': transaction_id,
            'payment_amount': float(amt),
            'entry_numbers': created_numbers,
            'stage1_adjusted': float(actual_adj_l1 + actual_adj_l2),
            'stage1_adjusted_l1': float(actual_adj_l1),
            'stage1_adjusted_l2': float(actual_adj_l2),
            'remaining_stage1': float(new_rem_s1_l1 + new_rem_s1_l2),
            'remaining_stage1_l1': float(new_rem_s1_l1),
            'remaining_stage1_l2': float(new_rem_s1_l2),
        }

    except Exception as e:
        logger.warning(f'[STAGE2-ADV] process_payment_stage2_advance failed for lead {lead_id} txn {transaction_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'created': False, 'reason': str(e)}


def cancel_payment_stage2_advance(
    db: Session,
    transaction_id: int,
    cancelled_by_id: Optional[int] = None,
    reason: Optional[str] = None
) -> dict:
    """
    Rollback and cancel Stage 2 advances associated with an unvalidated or rejected transaction.
    - Recovers advance from partner wallet if already released.
    - Restores remaining_stage1_advance on crm_leads if Stage 1 was adjusted against this transaction.
    - Cancels vgk_cash_income_entries.
    """
    from app.models.staff_accounts import OfficialPartner
    now = _get_ist()
    now_naive = now.replace(tzinfo=None)

    try:
        advs = db.execute(text("""
            SELECT id, lead_id, partner_id, advance_amount, status, entry_number, company_id,
                   adjustment_amount, level
            FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND kind = 'DVR_ADVANCE'
            FOR UPDATE
        """), {'tid': transaction_id}).fetchall()

        if not advs:
            return {'cancelled': False, 'reason': f'No Stage 2 advances found for transaction {transaction_id}'}

        cancelled_count = 0
        restored_adj_total = Decimal('0.00')

        for adv in advs:
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == adv.partner_id
            ).with_for_update().first()

            # If advance was released, recover net payout from wallet
            if adv.status in ('RELEASED', 'STAGE1_APPROVED', 'PAID') and partner:
                gross = Decimal(str(adv.advance_amount or 0))
                adj = Decimal(str(adv.adjustment_amount or 0))
                net_to_recover = max(Decimal('0'), gross - adj)

                wallet_before = partner.vgk_cash_wallet or Decimal('0')
                if wallet_before >= net_to_recover:
                    wallet_after = wallet_before - net_to_recover
                    rec_status = 'RECOVERED'
                    rec_amt = net_to_recover
                else:
                    wallet_after = Decimal('0')
                    rec_status = 'DEFICIT'
                    rec_amt = wallet_before

                partner.vgk_cash_wallet = wallet_after
                partner.updated_at = now

                _txn_company_id = partner.company_id or adv.company_id or 4
                db.execute(text("""
                    UPDATE vgk_solar_cibil_advances SET
                        status = :st,
                        recovery_amount = :ra,
                        wallet_before_recovery = :wb,
                        wallet_after_recovery  = :wa,
                        recovered_by_id = :rid,
                        recovered_at    = :now,
                        recovery_reason = :rr,
                        updated_at      = :now
                    WHERE id = :aid
                """), {
                    'st': rec_status, 'ra': float(rec_amt),
                    'wb': float(wallet_before), 'wa': float(wallet_after),
                    'rid': cancelled_by_id, 'now': now_naive,
                    'rr': reason or f'Transaction #{transaction_id} unvalidated/cancelled',
                    'aid': adv.id,
                })

                if rec_amt > Decimal('0.00'):
                    _log_wallet_txn(
                        db, partner_id=partner.id, company_id=_txn_company_id,
                        txn_type='SOLAR_ADV_RECOVERY', direction='DR', amount=rec_amt,
                        wallet_before=wallet_before, wallet_after=wallet_after,
                        ref_type='VGK_DVR_ADV', ref_id=adv.id,
                        description=f'DVR Advance recovery on txn #{transaction_id} cancellation — {adv.entry_number}',
                        staff_id=cancelled_by_id,
                    )
            else:
                db.execute(text("""
                    UPDATE vgk_solar_cibil_advances
                    SET status = 'CANCELLED',
                        recovery_reason = :rr,
                        updated_at = :now
                    WHERE id = :aid
                """), {
                    'rr': reason or f'Transaction #{transaction_id} unvalidated/cancelled',
                    'now': now_naive,
                    'aid': adv.id
                })

            # If Stage 1 was adjusted against this transaction, restore it independently to L1 and L2
            if adv.adjustment_amount and Decimal(str(adv.adjustment_amount)) > 0:
                adj_to_restore = Decimal(str(adv.adjustment_amount))
                restored_adj_total += adj_to_restore
                adv_lvl = adv.level or 1

                if adv_lvl == 1:
                    db.execute(text("""
                        UPDATE crm_leads
                        SET remaining_stage1_advance = remaining_stage1_advance + :adj,
                            remaining_stage1_advance_l1 = COALESCE(remaining_stage1_advance_l1, 0) + :adj
                        WHERE id = :lid
                    """), {'adj': float(adj_to_restore), 'lid': adv.lead_id})

                    db.execute(text("""
                        UPDATE vgk_solar_cibil_advances
                        SET adjustment_amount = GREATEST(0, COALESCE(adjustment_amount, 0) - :adj),
                            status = CASE WHEN (COALESCE(adjustment_amount, 0) - :adj) < advance_amount THEN 'RELEASED' ELSE status END,
                            updated_at = :now
                        WHERE lead_id = :lid AND level = 1 AND kind = 'ADVANCE'
                    """), {'adj': float(adj_to_restore), 'lid': adv.lead_id, 'now': now_naive})

                elif adv_lvl == 2:
                    db.execute(text("""
                        UPDATE crm_leads
                        SET remaining_stage1_advance = remaining_stage1_advance + :adj,
                            remaining_stage1_advance_l2 = COALESCE(remaining_stage1_advance_l2, 0) + :adj
                        WHERE id = :lid
                    """), {'adj': float(adj_to_restore), 'lid': adv.lead_id})

                    db.execute(text("""
                        UPDATE vgk_solar_cibil_advances
                        SET adjustment_amount = GREATEST(0, COALESCE(adjustment_amount, 0) - :adj),
                            status = CASE WHEN (COALESCE(adjustment_amount, 0) - :adj) < advance_amount THEN 'RELEASED' ELSE status END,
                            updated_at = :now
                        WHERE lead_id = :lid AND level = 2 AND kind = 'ADVANCE'
                    """), {'adj': float(adj_to_restore), 'lid': adv.lead_id, 'now': now_naive})

            cancelled_count += 1

        # Cancel vgk_cash_income_entries
        db.execute(text("""
            UPDATE vgk_cash_income_entries
            SET status = 'CANCELLED',
                cancelled_reason = :rr,
                updated_at = :now
            WHERE source_transaction_id = :tid AND kind = 'DVR_ADVANCE'
        """), {
            'rr': reason or f'Transaction #{transaction_id} unvalidated/cancelled',
            'now': now_naive,
            'tid': transaction_id,
        })

        db.commit()
        logger.info(
            f"[STAGE2-ADV] Cancelled {cancelled_count} Stage 2 advance(s) for txn #{transaction_id}, "
            f"restored Stage 1 adjustment: ₹{float(restored_adj_total):.2f}"
        )
        return {
            'cancelled': True,
            'count': cancelled_count,
            'cancelled_count': cancelled_count,
            'restored_stage1_adjustment': float(restored_adj_total)
        }

    except Exception as e:
        logger.warning(f"[STAGE2-ADV] cancel_payment_stage2_advance failed for txn #{transaction_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {'cancelled': False, 'reason': str(e)}


def check_and_create_dvr_advance(db: Session, lead_id: int) -> dict:
    """
    Stage 2 Advance Entry Point.
    - If lead has validated transactions on or after STAGE2_EFFECTIVE_DATE (24-Sep-2026),
      processes any unhandled transactions through process_payment_stage2_advance.
    - If lead has transactions <= 23-Sep-2026, routes to canonical legacy DVR advance logic.
    """
    try:
        # Check for validated transactions on this lead
        txns = db.execute(text("""
            SELECT id, amount, transaction_date, validated_at, created_at
            FROM crm_lead_transactions
            WHERE lead_id = :lid AND validation_status = 'validated'
            ORDER BY id ASC
        """), {'lid': lead_id}).fetchall()

        if txns:
            # Check if any transaction is >= STAGE2_EFFECTIVE_DATE
            cutoff_date = STAGE2_EFFECTIVE_DATE.date()
            post_cutoff_txns = []
            for t in txns:
                td = t.transaction_date or t.validated_at or t.created_at
                if td:
                    t_date = td.date() if hasattr(td, 'date') else td
                    if t_date >= cutoff_date:
                        post_cutoff_txns.append(t)

            if post_cutoff_txns:
                created_any = False
                all_numbers = []
                for t in post_cutoff_txns:
                    res = process_payment_stage2_advance(
                        db=db, lead_id=lead_id, transaction_id=t.id,
                        payment_amount=Decimal(str(t.amount or 0)),
                        transaction_date=t.transaction_date or t.validated_at or t.created_at
                    )
                    if res.get('created'):
                        created_any = True
                        all_numbers.extend(res.get('entry_numbers', []))
                if created_any:
                    return {'created': True, 'entry_numbers': all_numbers}
                return {'created': False, 'reason': 'All post-cutoff transaction advances already exist'}

        # Fallback to legacy DVR advance logic
        return _legacy_check_and_create_dvr_advance(db, lead_id)

    except Exception as e:
        logger.warning(f"[STAGE2-ADV] check_and_create_dvr_advance dispatch error for lead {lead_id}: {e}")
        return _legacy_check_and_create_dvr_advance(db, lead_id)


def release_dvr_advance(
    db: Session, lead_id: int, partner_id: int, level: int,
    released_by_id: int = None, notes: str = None,
    source_transaction_id: Optional[int] = None,
    adv_id: Optional[int] = None,
) -> dict:
    """
    Release a PENDING DVR_ADVANCE record.
    Supports specific advance ID, transaction ID, or lead/partner/level matching.
    Credits net advance amount (gross advance minus Stage 1 pro-rata adjustment)
    to partner wallet, deducting 8% admin charges and 2% TDS.
    """
    try:
        if adv_id:
            adv = db.execute(text("""
                SELECT id, partner_id, advance_amount, status, entry_number, company_id,
                       adjustment_amount, source_transaction_id
                FROM vgk_solar_cibil_advances
                WHERE id = :aid FOR UPDATE
            """), {'aid': adv_id}).fetchone()
        elif source_transaction_id:
            adv = db.execute(text("""
                SELECT id, partner_id, advance_amount, status, entry_number, company_id,
                       adjustment_amount, source_transaction_id
                FROM vgk_solar_cibil_advances
                WHERE source_transaction_id = :tid AND level = :lv AND kind = 'DVR_ADVANCE' AND partner_id = :pid
                FOR UPDATE
            """), {'tid': source_transaction_id, 'lv': level, 'pid': partner_id}).fetchone()
        else:
            adv = db.execute(text("""
                SELECT id, partner_id, advance_amount, status, entry_number, company_id,
                       adjustment_amount, source_transaction_id
                FROM vgk_solar_cibil_advances
                WHERE lead_id = :lid AND level = :lv AND kind = 'DVR_ADVANCE' AND partner_id = :pid
                ORDER BY id DESC LIMIT 1 FOR UPDATE
            """), {'lid': lead_id, 'lv': level, 'pid': partner_id}).fetchone()

        if not adv:
            return {'success': False, 'error': 'No DVR_ADVANCE record found'}
        if adv.status != 'PENDING':
            if adv.status in ('RELEASED', 'STAGE1_APPROVED', 'STAGE2_PAID', 'PAID'):
                logger.info(f'[VGK-SOLAR-ADV] DVR Advance {adv.id} is already {adv.status}; skipping duplicate release.')
                return {'success': True, 'already_released': True, 'message': f'DVR Advance was already {adv.status}'}
            return {'success': False, 'error': f'DVR_ADVANCE is {adv.status}, not PENDING'}

        from app.models.staff_accounts import OfficialPartner
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == adv.partner_id
        ).with_for_update().first()
        if not partner:
            return {'success': False, 'error': 'Partner not found'}

        _txn_company_id = partner.company_id or adv.company_id or 4
        gross_amount = Decimal(str(adv.advance_amount))
        adj_amount = Decimal(str(getattr(adv, 'adjustment_amount', 0) or 0))
        amount = max(Decimal('0'), gross_amount - adj_amount)

        _pre_admin = (amount * Decimal('0.08')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        _pre_tds   = ((amount - _pre_admin) * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        _pre_net   = amount - _pre_admin - _pre_tds
        _avail_pts = partner.vgk_points_balance or Decimal('0')
        # DC-NO-PTS-GATE-002: Points balance is informational for DVR advance release
        # (mirrors DC-NO-PTS-GATE-001 in release_advance). Advance release is not blocked by points.
        if _avail_pts < _pre_net:
            logger.info(
                f"[VGK-DVR-ADV] Informational: Partner {partner.id} points ({float(_avail_pts):.0f}) < "
                f"net DVR advance (₹{float(_pre_net):.2f}). Proceeding with release."
            )

        now = _get_ist()
        wallet_before = partner.vgk_cash_wallet or Decimal('0')
        wallet_after  = wallet_before + amount
        partner.vgk_cash_wallet = wallet_after
        partner.updated_at = now

        db.execute(text("""
            UPDATE vgk_solar_cibil_advances SET
                status                = 'RELEASED',
                wallet_before_release = :wb,
                wallet_after_release  = :wa,
                released_by_id        = :rid,
                released_at           = :now,
                notes                 = COALESCE(:notes, notes),
                updated_at            = :now
            WHERE id = :aid
        """), {
            'wb': float(wallet_before), 'wa': float(wallet_after),
            'rid': released_by_id, 'now': now.replace(tzinfo=None),
            'notes': notes, 'aid': adv.id,
        })

        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_txn_company_id,
            txn_type='SOLAR_ADVANCE_CREDIT', direction='CR', amount=amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type='VGK_DVR_ADV', ref_id=adv.id,
            description=f'DVR Advance released — {adv.entry_number}',
            staff_id=released_by_id,
        )

        _adv_admin = (amount * Decimal('0.08')).quantize(Decimal('0.01'))
        _adv_tds   = (amount * Decimal('0.02')).quantize(Decimal('0.01'))
        _adv_ded   = _adv_admin + _adv_tds
        _adv_net   = amount - _adv_ded

        _wb_ded = wallet_after
        partner.vgk_cash_wallet = _wb_ded - _adv_ded
        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_txn_company_id,
            txn_type='INCOME_DEDUCTION', direction='DR', amount=_adv_ded,
            wallet_before=_wb_ded, wallet_after=partner.vgk_cash_wallet,
            ref_type='VGK_DVR_ADV', ref_id=adv.id,
            description=f'Admin 8% + TDS 2% on DVR advance — {adv.entry_number}',
            staff_id=released_by_id,
        )

        try:
            deduct_pts = _adv_net
            _wb_payout = partner.vgk_cash_wallet
            partner.vgk_cash_wallet = _wb_payout - deduct_pts
            _log_wallet_txn(
                db, partner_id=partner.id, company_id=_txn_company_id,
                txn_type='SOLAR_ADV_PAYOUT', direction='DR', amount=deduct_pts,
                wallet_before=_wb_payout, wallet_after=partner.vgk_cash_wallet,
                ref_type='VGK_DVR_ADV', ref_id=adv.id,
                description=f'DVR advance offset by points — {adv.entry_number}',
                staff_id=released_by_id,
            )
        except Exception as _pe:
            logger.warning(f'[DVR-ADV] Payout DR failed (non-fatal): {_pe}')

        _slab = {'slab_applied': False}
        if level == 1:
            _slab = apply_slab_bonus_if_active(
                db, partner, adv.id, adv.entry_number, advance_kind='DVR'
            )
        _slab_amount = Decimal(str(_slab.get('slab_amount', 0))) if _slab.get('slab_applied') else Decimal('0')

        # DC-EXTRA-COMM-001: fire 'first_payment' extra commission for all configured levels.
        # Only on L1 DVR advance (level==1); idempotency log guards re-fire.
        if level == 1:
            try:
                from app.services.vgk_extra_commission import apply_extra_commission_if_active as _ec_first_pay
                _lead_dvr_ec = db.execute(text(
                    "SELECT * FROM crm_leads WHERE id=:lid"
                ), {'lid': lead_id}).fetchone()
                if _lead_dvr_ec:
                    _ec_first_pay(db, _lead_dvr_ec, 'first_payment')
            except Exception as _ec_dvr_e:
                logger.warning(f'[DC-EXTRA-COMM-001] first_payment (DVR release) non-fatal: {_ec_dvr_e}')

            # DC-AWARD-TRIGGER-001: fire 'first_payment' award/gift trigger for configured levels.
            try:
                from app.services.vgk_award_trigger import apply_award_gift_trigger_if_active as _at_first_pay
                if _lead_dvr_ec:
                    _at_first_pay(db, _lead_dvr_ec, 'first_payment')
            except Exception as _at_dvr_e:
                logger.warning(f'[DC-AWARD-TRIGGER-001] first_payment (DVR) non-fatal: {_at_dvr_e}')

            # DC-EC-PER-LEVEL-TRIGGER-001: fire 'first_payment' cash/bonus trigger for configured levels.
            try:
                from app.services.vgk_cash_bonus_trigger import apply_cash_bonus_trigger_if_active as _cb_first_pay
                if _lead_dvr_ec:
                    _cb_first_pay(db, _lead_dvr_ec, 'first_payment')
            except Exception as _cb_dvr_e:
                logger.warning(f'[DC-CB-TRIGGER-001] first_payment (DVR) non-fatal: {_cb_dvr_e}')

            # DC-STAGE1-DEFERRED-RELEASE: If any PENDING Stage 1 advances exist for this lead, auto-release them now
            try:
                _p_advs = db.execute(text(
                    "SELECT id, level FROM vgk_solar_cibil_advances "
                    "WHERE lead_id = :lid AND kind = 'ADVANCE' AND status = 'PENDING'"
                ), {'lid': lead_id}).fetchall()
                for _pa in _p_advs:
                    release_advance(db, lead_id=lead_id, released_by_id=released_by_id,
                                    notes="Stage 1 advance auto-released at Stage 2 DVR", _level=int(_pa.level))
            except Exception as _s1_rel_e:
                logger.warning(f'[DVR-ADV] Stage 1 deferred release failed for lead {lead_id}: {_s1_rel_e}')

        # DC-DVR-VCI-MIRROR-001 (Jul 2026): Mirror released DVR advance into
        # vgk_cash_income_entries so it appears in the Channel Partners income
        # breakdown (member_income_entries_detail only queries VCI table).
        # Uses savepoint so a UniqueViolation / conflict cannot abort outer txn.
        try:
            _dvr_mirror_sp = db.begin_nested()
            try:
                from app.services.vgk_cash_income import record_dvr_advance_as_income_row as _dvr_mirror_fn
                _adv_full = db.execute(text(
                    "SELECT id, entry_number, partner_id, lead_id, advance_amount, "
                    "company_id, COALESCE(level,1) AS level "
                    "FROM vgk_solar_cibil_advances WHERE id=:i"
                ), {'i': adv.id}).fetchone()
                if _adv_full:
                    _dvr_mirror_fn(db, _adv_full, released_by_id=released_by_id)
                _dvr_mirror_sp.commit()
            except Exception as _dm_e:
                try:
                    _dvr_mirror_sp.rollback()
                except Exception:
                    pass
                logger.warning(f'[DVR-ADV] VCI mirror failed (non-fatal): {_dm_e}')
        except Exception as _dm_sp_e:
            logger.warning(f'[DVR-ADV] mirror savepoint error (non-fatal): {_dm_sp_e}')

        db.commit()
        logger.info(
            f'[DVR-ADV] RELEASED {adv.entry_number} → partner '
            f'{getattr(partner, "partner_code", partner.id)} '
            f'wallet {float(wallet_before)} → {float(wallet_after)}'
            + (f' | slab ₹{_slab_amount}' if _slab.get('slab_applied') else '')
        )
        return {
            'success':            True,
            'entry_number':       adv.entry_number,
            'amount_released':    float(amount),
            'wallet_before':      float(wallet_before),
            'wallet_after':       float(wallet_after),
            'slab_bonus_applied': _slab.get('slab_applied', False),
            'slab_bonus_amount':  _slab.get('slab_amount', 0),
        }

    except Exception as e:
        logger.warning(f'[DVR-ADV] release_dvr_advance failed lead {lead_id} L{level}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'success': False, 'error': str(e)}


def apply_slab_bonus_if_active(
    db: Session, partner, advance_id: int, advance_entry_number: str,
    advance_kind: str = 'CIBIL'
) -> dict:
    """
    DC_BONANZA_SLABWISE_AUTO_001: Auto-credit slab bonus when Solar Advance is released.

    - Queries the first active Slab Wise bonanza (status=Approved, portal=VGK, within dates).
    - Credits slab_extra_amount to partner.vgk_cash_wallet in the same DB session (caller commits).
    - Idempotent: slab_bonus_paid flag prevents any double-crediting.
    - Non-blocking: exceptions are caught and logged; advance release is never rolled back.
    - Applies to ALL VGK members (activated or registered).
    """
    try:
        # Idempotency guard + fetch advance metadata in one query
        _chk = db.execute(text(
            "SELECT slab_bonus_paid, created_at, released_at, company_id, "
            "COALESCE(level, 1) AS level "
            "FROM vgk_solar_cibil_advances WHERE id = :aid"
        ), {'aid': advance_id}).fetchone()
        if _chk and _chk.slab_bonus_paid:
            return {'slab_applied': False, 'reason': 'already_paid'}
        # DC-SLAB-L1-GUARD-001: SLAB_BONUS is only for L1 (ground-source) partners.
        # release_advance() and release_dvr_advance() both guard this at call site, but
        # this defensive check prevents any future code path from bypassing that guard.
        if _chk and _chk.level != 1:
            logger.warning(
                f'[DC-SLAB-L1-GUARD-001] Blocked slab bonus for advance {advance_id} '
                f'(level={_chk.level}): only L1 advances qualify'
            )
            return {'slab_applied': False, 'reason': f'not_l1_advance (level={_chk.level})'}

        now_ist = _get_ist().replace(tzinfo=None)

        # DC-BONANZA-SUBMITDATE-001 (Jun 2026): Check bonanza window against the
        # LEAD's submit_date (when the bank file was actually submitted by the partner),
        # NOT advance.created_at (system release date).  A lead submitted in April
        # must NOT qualify for a May-June bonanza even if the advance is released in June.
        # Fallback chain: lead.submit_date → advance.created_at → now_ist.
        _lead_submit_date = None
        try:
            _lead_row = db.execute(text(
                "SELECT submit_date FROM crm_leads WHERE id = ("
                "  SELECT lead_id FROM vgk_solar_cibil_advances WHERE id = :aid"
                ")"
            ), {'aid': advance_id}).fetchone()
            if _lead_row and _lead_row.submit_date:
                import datetime as _dt
                _sd = _lead_row.submit_date
                if isinstance(_sd, _dt.date) and not isinstance(_sd, _dt.datetime):
                    _sd = _dt.datetime(_sd.year, _sd.month, _sd.day, 0, 0, 0)
                _lead_submit_date = _sd
        except Exception:
            pass
        _check_ts = _lead_submit_date or (_chk.created_at if _chk and _chk.created_at else now_ist)
        if hasattr(_check_ts, 'tzinfo') and _check_ts.tzinfo is not None:
            _check_ts = _check_ts.replace(tzinfo=None)

        # DC-SOLAR-DVR-ADV-20260701-001: filter by advance_count_basis so CIBIL
        # advances only match CIBIL/BOTH bonanzas and DVR advances only match DVR/BOTH.
        if advance_kind == 'DVR':
            _basis_clause = "AND advance_count_basis IN ('DVR', 'BOTH')"
        else:
            _basis_clause = "AND (advance_count_basis IS NULL OR advance_count_basis IN ('CIBIL', 'BOTH'))"

        # DC-BONANZA-DATEONLY-001 (Jul 2026): Use DATE-only comparison so that a submit_date
        # of the SAME CALENDAR DAY as the bonanza start/end qualifies regardless of the
        # time component stored in start_date/end_date (e.g. start at 23:56 != midnight).
        bonanza = db.execute(text(f"""
            SELECT id, name, slab_extra_amount
            FROM bonanza
            WHERE reward_type = 'slab_wise'
              AND status      = 'Approved'
              AND portal      = 'VGK'
              AND DATE(start_date) <= DATE(:check_ts)
              AND DATE(end_date)   >= DATE(:check_ts)
              {_basis_clause}
            ORDER BY start_date DESC
            LIMIT 1
        """), {'check_ts': _check_ts}).fetchone()

        if not bonanza:
            return {'slab_applied': False, 'reason': 'no_active_bonanza'}

        # DC-SLAB-DEDUP-001 (Jul 2026): Deduplicate to prevent multiple payouts for the same bonanza.
        # Check if the partner has already received a SLAB_BONUS entry matching this bonanza name.
        _already_received = db.execute(text("""
            SELECT id FROM vgk_cash_income_entries
            WHERE partner_id = :pid
              AND kind = 'SLAB_BONUS'
              AND notes LIKE :pfx
            LIMIT 1
        """), {
            'pid': partner.id,
            'pfx': f'Slab Wise Bonanza — {bonanza.name}%'
        }).fetchone()

        if _already_received:
            logger.info(
                f'[SLAB-DEDUP] Partner {partner.id} has already claimed slab bonus for '
                f'bonanza {bonanza.id} ({bonanza.name}) — skipping additional payout'
            )
            return {'slab_applied': False, 'reason': 'already_claimed_for_campaign'}

        slab_amount   = Decimal(str(bonanza.slab_extra_amount))
        wallet_before = partner.vgk_cash_wallet or Decimal('0')
        wallet_after  = wallet_before + slab_amount
        partner.vgk_cash_wallet = wallet_after

        db.execute(text("""
            UPDATE vgk_solar_cibil_advances
               SET slab_bonus_paid   = TRUE,
                   slab_bonus_amount = :sba,
                   updated_at        = :now
             WHERE id = :aid
        """), {'sba': float(slab_amount), 'now': now_ist, 'aid': advance_id})

        # DC-SLAB-VCI-SEPARATE-001: Create a SEPARATE SLAB_BONUS VCI entry (₹3000) so that
        # the ADVANCE entry stays at advance_amount only (₹1000). Both go through Stage1→Stage2.
        # Wallet accounting for the bonus is already done above (net wallet effect = 0).
        # Idempotent: skips if SLAB_BONUS entry already exists for this (lead, partner).
        try:
            from app.services.vgk_cash_income import _next_entry_number as _nen
            from app.models.vgk_cash_income import VGKCashIncomeEntry as _VCI
            _adv_lv = db.execute(text(
                "SELECT lead_id, COALESCE(level,1) AS level FROM vgk_solar_cibil_advances WHERE id=:aid"
            ), {'aid': advance_id}).fetchone()
            if _adv_lv:
                _sb_exists = db.execute(text(
                    "SELECT id FROM vgk_cash_income_entries "
                    "WHERE source_lead_id=:lid AND partner_id=:pid AND kind='SLAB_BONUS' LIMIT 1"
                ), {'lid': _adv_lv.lead_id, 'pid': partner.id}).fetchone()
                if not _sb_exists:
                    _sb_admin = (slab_amount * Decimal('0.08')).quantize(Decimal('0.01'))
                    _sb_tds   = (slab_amount * Decimal('0.02')).quantize(Decimal('0.01'))
                    _sb_net   = slab_amount - _sb_admin - _sb_tds
                    _sb_co    = (partner.company_id or (_chk.company_id if _chk else None) or 4)
                    # DC-SLAB-DATE-001: stamp created_at with the advance's released_at so the
                    # date column reflects the actual release date, not the migration run date.
                    _adv_released_at = None
                    if _chk and _chk.released_at:
                        _adv_released_at = _chk.released_at
                        if hasattr(_adv_released_at, 'tzinfo') and _adv_released_at.tzinfo is not None:
                            _adv_released_at = _adv_released_at.replace(tzinfo=None)
                    _vci_created_at = _adv_released_at or now_ist
                    _sb_e = _VCI(
                        company_id              = _sb_co,
                        entry_number            = _nen(db, _sb_co),
                        partner_id              = partner.id,
                        source_lead_id          = _adv_lv.lead_id,
                        level                   = 0,  # level=0 avoids unique constraint clash with ADVANCE (level>=1)
                        income_date             = _vci_created_at.date() if hasattr(_vci_created_at, 'date') else _vci_created_at,
                        deal_value_total        = 0,
                        deal_value_excl_tax     = 0,
                        commission_pct          = 0,
                        commission_amount       = slab_amount,
                        points_debit_required   = 0,
                        points_actually_debited = 0,
                        kind                    = 'SLAB_BONUS',
                        status                  = 'PENDING',
                        admin_charges           = _sb_admin,
                        tds_amount              = _sb_tds,
                        net_payout              = _sb_net,
                        created_at              = _vci_created_at,
                        updated_at              = _vci_created_at,
                        notes                   = (
                            f'Slab Wise Bonanza — {bonanza.name} | '
                            f'Solar Advance {advance_entry_number}'
                        ),
                    )
                    db.add(_sb_e)
                    db.flush()
        except Exception as _vci_e:
            logger.warning(
                f'[DC-SLAB-VCI-SEPARATE-001] SLAB_BONUS VCI creation failed (non-fatal): {_vci_e}'
            )

        # DC-FIX-2605-NULLCO: use company_id already fetched above (avoid second query)
        _slab_company_id = partner.company_id or (_chk.company_id if _chk else None)

        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_slab_company_id,
            txn_type='SLAB_BONUS_CREDIT', direction='CR', amount=slab_amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type='VGK_SLAB_BONANZA', ref_id=bonanza.id,
            description=(
                f'Slab Wise Bonus auto-credited — {bonanza.name} — '
                f'Solar Advance {advance_entry_number}'
            ),
        )

        # DC-ADV-NET: 8% admin + 2% TDS deducted immediately (bonus already disbursed)
        _slab_admin = (slab_amount * Decimal('0.08')).quantize(Decimal('0.01'))
        _slab_tds   = (slab_amount * Decimal('0.02')).quantize(Decimal('0.01'))
        _slab_ded   = _slab_admin + _slab_tds
        _slab_net   = slab_amount - _slab_ded

        _wb_ded = wallet_after
        partner.vgk_cash_wallet = _wb_ded - _slab_ded
        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_slab_company_id,
            txn_type='INCOME_DEDUCTION', direction='DR', amount=_slab_ded,
            wallet_before=_wb_ded, wallet_after=partner.vgk_cash_wallet,
            ref_type='VGK_SLAB_BONANZA', ref_id=bonanza.id,
            description=f'Admin 8% + TDS 2% on slab bonus — {advance_entry_number}',
        )

        # Fix C — DC_VGK_POINTS_AT_PAID_001: PAYOUT DR (wallet zeroing) happens at RELEASE.
        # Points debit (vgk_points_balance) is deferred to mark_paid_cash_income.
        # Soft check: log a warning if insufficient but do NOT block the slab credit —
        # the combined VCI entry will cover the points debit at PAID time.
        avail_pts = partner.vgk_points_balance or Decimal('0')
        if avail_pts < _slab_net:
            logger.warning(
                f'[VGK-SLAB-BONUS] Points balance ({float(avail_pts):.0f}) < slab net '
                f'(\u20b9{float(_slab_net):.2f}) for partner {partner.id} — '
                f'debit deferred to mark_paid_cash_income.'
            )
        try:
            deduct_pts = _slab_net
            _wb_payout = partner.vgk_cash_wallet
            partner.vgk_cash_wallet = _wb_payout - deduct_pts
            _log_wallet_txn(
                db, partner_id=partner.id, company_id=_slab_company_id,
                txn_type='SLAB_BONUS_PAYOUT', direction='DR', amount=deduct_pts,
                wallet_before=_wb_payout, wallet_after=partner.vgk_cash_wallet,
                ref_type='VGK_SLAB_BONANZA', ref_id=bonanza.id,
                description=f'Slab bonus offset by points — {advance_entry_number}',
            )
            # NOTE: add_vgk_points_entry intentionally NOT called here.
            # Points are debited when the VCI entry is marked PAID (mark_paid_cash_income).
        except Exception as _pe:
            logger.warning(f'[VGK-SLAB-BONUS] Payout DR failed (non-fatal): {_pe}')

        # Fix D — DC_VGK_BONANZA_PROGRESS_AUTO_001: mark the matching bonanza_progress row
        # as 'Payment Released' so it no longer appears in the staff Pending Bonanza panel
        # and does not get double-paid by the manual bonanza payment flow.
        try:
            db.execute(text("""
                UPDATE bonanza_progress
                   SET processed_status      = 'Payment Released',
                       finance_processed_at  = :now
                 WHERE bonanza_id = :bid
                   AND partner_id = :pid
                   AND processed_status = 'Pending'
            """), {'bid': bonanza.id, 'pid': partner.id, 'now': now_ist})
        except Exception as _bp_e:
            logger.warning(f'[VGK-SLAB-BONUS] bonanza_progress auto-release update failed (non-fatal): {_bp_e}')

        logger.info(
            f'[VGK-SLAB-BONUS] ₹{slab_amount} auto-credited to partner '
            f'{getattr(partner, "partner_code", partner.id)} | bonanza#{bonanza.id} '
            f'| advance {advance_entry_number} | wallet {float(wallet_before)} → {float(wallet_after)}'
        )
        return {
            'slab_applied':   True,
            'slab_amount':    float(slab_amount),
            'bonanza_id':     bonanza.id,
            'bonanza_name':   bonanza.name,
            'wallet_before':  float(wallet_before),
            'wallet_after':   float(wallet_after),
        }
    except Exception as _e:
        logger.warning(f'[VGK-SLAB-BONUS] apply failed for advance {advance_id}: {_e}')
        return {'slab_applied': False, 'reason': str(_e), 'error': True}


def release_advance(db: Session, lead_id: int, released_by_id: int, notes: str = None, _level: int = 1) -> dict:
    """
    Staff releases the advance to the partner's vgk_cash_wallet.
    Advance must be in PENDING status.
    _level=1 (default) releases the L1 advance; pass _level=2 to release the L2 advance.
    If an active Slab Wise bonanza exists, it is auto-credited for L1 advances only.
    """
    try:
        adv = db.execute(text("""
            SELECT id, partner_id, advance_amount, status, entry_number, company_id
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = :lv AND kind = 'ADVANCE'
            FOR UPDATE
        """), {'lid': lead_id, 'lv': _level}).fetchone()

        if not adv:
            return {'success': False, 'error': 'No advance record found for this lead'}
        if adv.status not in ('PENDING', 'DEFICIT'):
            if adv.status in ('RELEASED', 'STAGE1_APPROVED', 'STAGE2_PAID', 'PAID'):
                logger.info(f'[VGK-SOLAR-ADV] Advance {adv.id} is already {adv.status}; skipping duplicate release.')
                return {'success': True, 'already_released': True, 'message': f'Advance was already {adv.status}'}
            return {'success': False, 'error': f'Advance is {adv.status}, not PENDING'}

        from app.models.staff_accounts import OfficialPartner
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == adv.partner_id
        ).with_for_update().first()

        if not partner:
            return {'success': False, 'error': 'Partner not found'}

        # DC-FIX-2605-NULLCO: Some VGK partners have company_id=NULL (registered under no company).
        # Fall back to the advance's own company_id (= the lead's product company) so the
        # vgk_wallet_transactions NOT NULL constraint is never violated.
        _txn_company_id = partner.company_id or adv.company_id

        amount = Decimal(str(adv.advance_amount))

        # DC-NO-PTS-GATE-001: Points balance is informational only — advances are released
        # and income shown as PENDING regardless of available points. Points are only
        # debited at mark_paid time. The partner_points_balance field is surfaced on
        # the unified income page so accounts staff can see availability before approving.
        wallet_before = partner.vgk_cash_wallet or Decimal('0')
        wallet_after = wallet_before + amount
        partner.vgk_cash_wallet = wallet_after
        partner.updated_at = _get_ist()

        now = _get_ist()
        db.execute(text("""
            UPDATE vgk_solar_cibil_advances SET
                status = 'RELEASED',
                wallet_before_release = :wb,
                wallet_after_release  = :wa,
                released_by_id = :rid,
                released_at    = :now,
                notes          = COALESCE(:notes, notes),
                updated_at     = :now
            WHERE id = :aid
        """), {
            'wb': float(wallet_before), 'wa': float(wallet_after),
            'rid': released_by_id, 'now': now.replace(tzinfo=None),
            'notes': notes, 'aid': adv.id,
        })

        if _level in (1, 2):
            try:
                if _level == 1:
                    db.execute(text("""
                        UPDATE crm_leads
                        SET remaining_stage1_advance = COALESCE(remaining_stage1_advance, 0) + :amt,
                            remaining_stage1_advance_l1 = COALESCE(remaining_stage1_advance_l1, 0) + :amt
                        WHERE id = :lid
                    """), {'amt': float(amount), 'lid': lead_id})
                elif _level == 2:
                    db.execute(text("""
                        UPDATE crm_leads
                        SET remaining_stage1_advance = COALESCE(remaining_stage1_advance, 0) + :amt,
                            remaining_stage1_advance_l2 = COALESCE(remaining_stage1_advance_l2, 0) + :amt
                        WHERE id = :lid
                    """), {'amt': float(amount), 'lid': lead_id})
            except Exception as _r_err:
                logger.warning(f"[VGK-SOLAR-ADV] Could not increment remaining_stage1_advance on lead {lead_id}: {_r_err}")

        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_txn_company_id,
            txn_type='SOLAR_ADVANCE_CREDIT', direction='CR', amount=amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type='VGK_SOLAR_ADV', ref_id=adv.id,
            description=f'Solar CIBIL Advance released — {adv.entry_number}',
            staff_id=released_by_id,
        )

        # DC-ADV-NET: 8% admin + 2% TDS deducted immediately (advance already disbursed)
        _adv_admin = (amount * Decimal('0.08')).quantize(Decimal('0.01'))
        _adv_tds   = (amount * Decimal('0.02')).quantize(Decimal('0.01'))
        _adv_ded   = _adv_admin + _adv_tds
        _adv_net   = amount - _adv_ded

        _wb_ded = wallet_after
        partner.vgk_cash_wallet = _wb_ded - _adv_ded
        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_txn_company_id,
            txn_type='INCOME_DEDUCTION', direction='DR', amount=_adv_ded,
            wallet_before=_wb_ded, wallet_after=partner.vgk_cash_wallet,
            ref_type='VGK_SOLAR_ADV', ref_id=adv.id,
            description=f'Admin 8% + TDS 2% on advance — {adv.entry_number}',
            staff_id=released_by_id,
        )

        # Fix C — DC_VGK_POINTS_AT_PAID_001: PAYOUT DR (wallet zeroing) happens at RELEASE.
        # Points debit (vgk_points_balance) is deferred to mark_paid_cash_income so that
        # UTILISED stays 0 until accounts confirms the physical payment.
        # DC-NO-PTS-GATE-001: Points sufficiency is NOT checked here — advances release
        # regardless. Points balance is surfaced in the unified income page for staff review.
        try:
            deduct_pts = _adv_net
            _wb_payout = partner.vgk_cash_wallet
            partner.vgk_cash_wallet = _wb_payout - deduct_pts
            _log_wallet_txn(
                db, partner_id=partner.id, company_id=_txn_company_id,
                txn_type='SOLAR_ADV_PAYOUT', direction='DR', amount=deduct_pts,
                wallet_before=_wb_payout, wallet_after=partner.vgk_cash_wallet,
                ref_type='VGK_SOLAR_ADV', ref_id=adv.id,
                description=f'Advance offset by points — {adv.entry_number}',
                staff_id=released_by_id,
            )
            # NOTE: add_vgk_points_entry intentionally NOT called here.
            # Points are debited when the VCI entry is marked PAID (mark_paid_cash_income).
        except Exception as _pe:
            logger.warning(f'[VGK-SOLAR-ADV] Payout DR failed (non-fatal): {_pe}')

        # DC-VGK-INCOME-UNIFIED-001: mirror advance into vgk_cash_income_entries (ADVANCE only, no slab).
        # DC-SLAB-VCI-SEPARATE-001: slab bonus gets its OWN SLAB_BONUS VCI entry (created inside
        # apply_slab_bonus_if_active, which runs AFTER the mirror so the ADVANCE VCI already exists).
        # DC-MIRROR-SAVEPOINT-001 (Jul 2026): wrap in savepoint so any UniqueViolation inside
        # record_solar_advance_as_income_row cannot abort the outer transaction (wallet credits +
        # advance status update).  Without this, a flush failure leaves the session in a broken
        # state and the subsequent db.commit() re-raises, failing the entire release_advance call.
        try:
            _mirror_sp = db.begin_nested()
            try:
                from app.services.vgk_cash_income import record_solar_advance_as_income_row
                adv_full = db.execute(text(
                    "SELECT id, entry_number, partner_id, lead_id, advance_amount, company_id, COALESCE(level,1) AS level FROM vgk_solar_cibil_advances WHERE id=:i"
                ), {'i': adv.id}).fetchone()
                if adv_full:
                    record_solar_advance_as_income_row(
                        db, adv_full, released_by_id=released_by_id,
                    )
                _mirror_sp.commit()
            except Exception as _mr_e:
                try:
                    _mirror_sp.rollback()
                except Exception:
                    pass
                logger.warning(f'[VGK-SOLAR-ADV] income row mirror failed (non-fatal): {_mr_e}')
        except Exception as _mr_sp_e:
            logger.warning(f'[VGK-SOLAR-ADV] mirror savepoint error (non-fatal): {_mr_sp_e}')

        # DC_BONANZA_SLABWISE_AUTO_001: auto slab bonus — runs AFTER mirror so ADVANCE VCI exists.
        # Creates a separate SLAB_BONUS VCI entry (not merged into the ADVANCE row).
        # DC-SLAB-L1-ONLY-001 (Jul 2026): SLAB_BONUS (Solar Bonanza ₹3,000) is ONLY for the
        # L1 ground-source partner. The release_advance function handles both _level=1 (L1) and
        # _level=2 (L2 senior advance ₹500). Without this guard, every L2 advance release also
        # triggered apply_slab_bonus_if_active — giving the senior partner ₹3,000 they must not
        # receive. The DVR advance path already had this guard (line ~443); now mirrored here.
        _slab = apply_slab_bonus_if_active(db, partner, adv.id, adv.entry_number) if _level == 1 else {'slab_applied': False}
        _slab_amount = Decimal(str(_slab.get('slab_amount', 0))) if _slab.get('slab_applied') else Decimal('0')

        # DC-EXTRA-COMM-001: fire 'file_submitted' extra commission for all configured levels.
        # Runs once per file (only on L1 primary advance release); idempotency log guards re-fire.
        if _level == 1:
            try:
                from app.services.vgk_extra_commission import apply_extra_commission_if_active as _ec_submitted
                _lead_ec_row = db.execute(text(
                    "SELECT * FROM crm_leads WHERE id=:lid"
                ), {'lid': lead_id}).fetchone()
                if _lead_ec_row:
                    _ec_submitted(db, _lead_ec_row, 'file_submitted')
            except Exception as _ec_e:
                logger.warning(f'[DC-EXTRA-COMM-001] file_submitted (CIBIL release) non-fatal: {_ec_e}')

            # DC-AWARD-TRIGGER-001: fire 'file_submitted' award/gift trigger for configured levels.
            try:
                from app.services.vgk_award_trigger import apply_award_gift_trigger_if_active as _at_submitted
                if _lead_ec_row:
                    _at_submitted(db, _lead_ec_row, 'file_submitted')
            except Exception as _at_cibil_e:
                logger.warning(f'[DC-AWARD-TRIGGER-001] file_submitted (CIBIL) non-fatal: {_at_cibil_e}')

            # DC-EC-PER-LEVEL-TRIGGER-001: fire 'file_submitted' cash/bonus trigger for configured levels.
            try:
                from app.services.vgk_cash_bonus_trigger import apply_cash_bonus_trigger_if_active as _cb_submitted
                if _lead_ec_row:
                    _cb_submitted(db, _lead_ec_row, 'file_submitted')
            except Exception as _cb_cibil_e:
                logger.warning(f'[DC-CB-TRIGGER-001] file_submitted (CIBIL) non-fatal: {_cb_cibil_e}')

        db.commit()
        logger.info(
            f'[VGK-SOLAR-ADV] RELEASED {adv.entry_number} to partner {partner.partner_code}, '
            f'wallet {float(wallet_before)} → {float(wallet_after)}'
            + (f' | slab ₹{_slab_amount} auto-credited' if _slab.get('slab_applied') else '')
        )
        return {
            'success':              True,
            'entry_number':         adv.entry_number,
            'amount_released':      float(amount),
            'wallet_before':        float(wallet_before),
            'wallet_after':         float(wallet_after),
            'slab_bonus_applied':   _slab.get('slab_applied', False),
            'slab_bonus_amount':    _slab.get('slab_amount', 0),
            'slab_bonanza_name':    _slab.get('bonanza_name'),
        }

    except Exception as e:
        logger.warning(f'[VGK-SOLAR-ADV] release_advance failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'success': False, 'error': str(e)}


def recover_advance(db: Session, lead_id: int, reason: str = None, recovered_by_id: int = None) -> dict:
    """
    Auto-triggered when lead moves to loan_rejected / not_interested / cancelled.
    Recovers ALL RELEASED advance rows for this lead (L1, L2, and brand advances).

    Recovery logic per advance:
      - If wallet >= advance_amount → deduct immediately, status = RECOVERED
      - If wallet < advance_amount  → deduct what is available, status = DEFICIT
    """
    try:
        advs = db.execute(text("""
            SELECT id, partner_id, advance_amount, status, entry_number, company_id
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND status = 'RELEASED'
            FOR UPDATE
        """), {'lid': lead_id}).fetchall()

        if not advs:
            return {'success': True, 'action': 'no_advances_to_recover', 'count': 0}

        from app.models.staff_accounts import OfficialPartner
        now = _get_ist()
        results = []

        for adv in advs:
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == adv.partner_id
            ).with_for_update().first()

            if not partner:
                logger.warning(f'[VGK-SOLAR-ADV] Partner {adv.partner_id} not found for recovery of {adv.entry_number}')
                continue

            amount = Decimal(str(adv.advance_amount))
            wallet_before = partner.vgk_cash_wallet or Decimal('0')

            if wallet_before >= amount:
                wallet_after = wallet_before - amount
                new_status = 'RECOVERED'
                recovery_amt = amount
            else:
                wallet_after = Decimal('0')
                new_status = 'DEFICIT'
                recovery_amt = wallet_before

            partner.vgk_cash_wallet = wallet_after
            partner.updated_at = _get_ist()

            _txn_company_id = partner.company_id or adv.company_id

            db.execute(text("""
                UPDATE vgk_solar_cibil_advances SET
                    status = :st,
                    recovery_amount = :ra,
                    wallet_before_recovery = :wb,
                    wallet_after_recovery  = :wa,
                    recovered_by_id = :rid,
                    recovered_at    = :now,
                    recovery_reason = :rr,
                    updated_at      = :now
                WHERE id = :aid
            """), {
                'st': new_status,
                'ra': float(recovery_amt), 'wb': float(wallet_before), 'wa': float(wallet_after),
                'rid': recovered_by_id, 'now': now.replace(tzinfo=None),
                'rr': reason or 'Lead cancelled/rejected', 'aid': adv.id,
            })

            # DC-ADV-RECOVER-MIRROR-CANCEL-001: Auto-cancel mirrored vgk_cash_income_entries
            # to prevent orphaned or duplicate payouts if advance is recovered.
            db.execute(text("""
                UPDATE vgk_cash_income_entries
                   SET status = 'CANCELLED',
                       cancelled_reason = :cr,
                       notes = COALESCE(notes, '') || ' | Auto-cancelled via advance recovery (' || :entry_no || ')',
                       updated_at = :now
                 WHERE source_lead_id = :lid
                   AND partner_id = :pid
                   AND kind IN ('ADVANCE', 'DVR_ADVANCE', 'BRAND_ADVANCE')
                   AND status NOT IN ('PAID', 'CANCELLED')
            """), {
                'lid': lead_id,
                'pid': adv.partner_id,
                'entry_no': adv.entry_number,
                'cr': f'Advance {adv.entry_number} recovered ({new_status})',
                'now': now.replace(tzinfo=None),
            })

            if recovery_amt > 0:
                _log_wallet_txn(
                    db, partner_id=partner.id, company_id=_txn_company_id,
                    txn_type='SOLAR_ADVANCE_RECOVERY', direction='DR', amount=recovery_amt,
                    wallet_before=wallet_before, wallet_after=wallet_after,
                    ref_type='VGK_SOLAR_ADV', ref_id=adv.id,
                    description=f'Advance recovered ({new_status}) — {adv.entry_number}',
                    staff_id=recovered_by_id,
                )

            results.append({
                'entry_number': adv.entry_number,
                'status': new_status,
                'recovery_amount': float(recovery_amt),
            })
            logger.info(
                f'[VGK-SOLAR-ADV] {new_status} recovery for {adv.entry_number}, '
                f'partner {getattr(partner, "partner_code", partner.id)}, '
                f'recovered ₹{float(recovery_amt)}'
            )

        db.commit()
        return {'success': True, 'count': len(results), 'results': results}

    except Exception as e:
        logger.warning(f'[VGK-SOLAR-ADV] recover_advance failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'success': False, 'error': str(e)}


def apply_adjustment_at_completion(db: Session, lead_id: int, cash_income_entry_id: Optional[int] = None) -> dict:
    """
    Called when the final cash income draft is generated (lead completed, balance = 0).
    Reconciles and deducts any previously released advances (Stage 1 / Stage 2) for the entry's partner,
    preventing double payment. Status → ADJUSTED.
    """
    try:
        if not cash_income_entry_id:
            # Reconcile L1 draft by default if entry_id not specified
            l1_entry = db.execute(text(
                "SELECT id FROM vgk_cash_income_entries WHERE source_lead_id = :lid AND level = 1 AND status = 'DRAFT' ORDER BY id ASC LIMIT 1"
            ), {'lid': lead_id}).fetchone()
            if not l1_entry:
                return {'adjusted': False, 'reason': 'No L1 draft income entry found to adjust'}
            cash_income_entry_id = l1_entry.id

        entry = db.execute(text("""
            SELECT id, partner_id, level, commission_amount, advance_adjusted_amount FROM vgk_cash_income_entries
            WHERE id = :eid FOR UPDATE
        """), {'eid': cash_income_entry_id}).fetchone()

        if not entry:
            return {'adjusted': False, 'reason': 'Cash income entry not found'}

        advs = db.execute(text("""
            SELECT id, partner_id, advance_amount, COALESCE(adjustment_amount, 0) as adjustment_amount, status, entry_number, kind
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND partner_id = :pid
              AND kind IN ('ADVANCE', 'DVR_ADVANCE')
              AND status IN ('RELEASED', 'STAGE1_APPROVED', 'PAID')
            FOR UPDATE
        """), {'lid': lead_id, 'pid': entry.partner_id}).fetchall()

        if not advs:
            return {'adjusted': False, 'reason': f'No released advance to adjust for partner {entry.partner_id}'}

        original_commission = Decimal(str(entry.commission_amount or 0))
        total_unadj_adv = sum(max(Decimal('0'), Decimal(str(a.advance_amount or 0)) - Decimal(str(a.adjustment_amount or 0))) for a in advs)

        if total_unadj_adv <= Decimal('0.00'):
            return {'adjusted': False, 'reason': 'All advances already adjusted'}

        actual_adjustment = min(total_unadj_adv, original_commission)
        adjusted_commission = max(Decimal('0'), original_commission - actual_adjustment)

        now = _get_ist()
        now_naive = now.replace(tzinfo=None)

        db.execute(text("""
            UPDATE vgk_cash_income_entries
            SET commission_amount = :new_amt,
                advance_adjusted_amount = COALESCE(advance_adjusted_amount, 0) + :adj,
                updated_at = :now
            WHERE id = :eid
        """), {'new_amt': float(adjusted_commission), 'adj': float(actual_adjustment), 'now': now_naive, 'eid': cash_income_entry_id})

        rem_to_mark = actual_adjustment
        for adv in advs:
            if rem_to_mark <= Decimal('0.00'):
                break
            adv_unadj = max(Decimal('0'), Decimal(str(adv.advance_amount or 0)) - Decimal(str(adv.adjustment_amount or 0)))
            adj_this = min(rem_to_mark, adv_unadj)
            if adj_this > Decimal('0.00'):
                db.execute(text("""
                    UPDATE vgk_solar_cibil_advances SET
                        status = CASE WHEN (COALESCE(adjustment_amount, 0) + :adj) >= advance_amount THEN 'ADJUSTED' ELSE status END,
                        adjustment_amount = COALESCE(adjustment_amount, 0) + :adj,
                        adjustment_entry_id = :eid,
                        adjusted_at = :now,
                        updated_at  = :now
                    WHERE id = :aid
                """), {
                    'adj': float(adj_this),
                    'eid': cash_income_entry_id,
                    'now': now_naive,
                    'aid': adv.id,
                })
                rem_to_mark -= adj_this

        if entry.level == 1:
            db.execute(text("UPDATE crm_leads SET remaining_stage1_advance_l1 = 0 WHERE id = :lid"), {'lid': lead_id})
        elif entry.level == 2:
            db.execute(text("UPDATE crm_leads SET remaining_stage1_advance_l2 = 0 WHERE id = :lid"), {'lid': lead_id})

        db.execute(text("""
            UPDATE crm_leads
            SET remaining_stage1_advance = COALESCE(remaining_stage1_advance_l1, 0) + COALESCE(remaining_stage1_advance_l2, 0)
            WHERE id = :lid
        """), {'lid': lead_id})

        db.commit()
        logger.info(
            f'[VGK-SOLAR-ADV] Reconciled advances for lead {lead_id} partner {entry.partner_id}: '
            f'commission ₹{float(original_commission)} → ₹{float(adjusted_commission)} '
            f'(deducted ₹{float(actual_adjustment)}) via income entry {cash_income_entry_id}'
        )
        return {
            'adjusted': True,
            'entry_id': cash_income_entry_id,
            'original_commission': float(original_commission),
            'adjustment_amount': float(actual_adjustment),
            'adjusted_commission': float(adjusted_commission),
        }

    except Exception as e:
        logger.warning(f'[VGK-SOLAR-ADV] apply_adjustment_at_completion failed: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'adjusted': False, 'reason': str(e)}


def get_deficit_recovery_amount(db: Session, partner_id: int) -> Decimal:
    """
    Returns the total outstanding DEFICIT advance amount for a partner.
    This is used to deduct from future earnings automatically.
    """
    result = db.execute(text("""
        SELECT COALESCE(SUM(advance_amount - COALESCE(recovery_amount, 0)), 0)
        FROM vgk_solar_cibil_advances
        WHERE partner_id = :pid AND status = 'DEFICIT'
    """), {'pid': partner_id}).scalar()
    return Decimal(str(result or 0))


def _log_wallet_txn(
    db, partner_id, company_id, txn_type, direction, amount,
    wallet_before, wallet_after, ref_type=None, ref_id=None,
    description=None, staff_id=None,
):
    """Non-fatal wallet transaction logger — reuses vgk_cash_income pattern."""
    try:
        from app.services.vgk_cash_income import _log_wallet_txn as _base_log
        _base_log(
            db, partner_id=partner_id, company_id=company_id,
            txn_type=txn_type, direction=direction, amount=amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type=ref_type, ref_id=ref_id,
            description=description, staff_id=staff_id,
        )
    except Exception as _e:
        logger.warning(f'[VGK-SOLAR-ADV] Wallet txn log failed (non-fatal): {_e}')
