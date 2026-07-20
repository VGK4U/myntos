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
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# DC-SOLAR-SPEC-20260710: Stage 1 Advance (Application Submitted + CIBIL >= 600)
# L1 (Ground Source): 1000, L2 (Senior): 500 — per VGK Commission & Advance Payment Logic.
ADVANCE_AMOUNT    = Decimal('1000.00')
L2_ADVANCE_AMOUNT = Decimal('500.00')
CIBIL_MIN_SCORE   = 600

# Solar pipeline stages that are eligible (application_submitted and above, excluding terminal failure stages)
ELIGIBLE_STAGES = {
    'application_submitted', 'pending_with_bank', 'documents_issue',
    'load_extension', 'electricity_bill_change', 'installation_pending',
    'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending', 'completed',
}

# Stages that trigger recovery of already-released advances
RECOVERY_STAGES = {'loan_rejected', 'not_interested', 'cancelled'}


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


def check_and_create_advance(db: Session, lead_id: int) -> dict:
    """
    Called whenever solar_pipeline_status or CIBIL fields change on a lead.
    Creates PENDING advance records for L1 (₹1,000) and L2 (₹500, if senior
    partner set) if ALL eligibility criteria are met and no advance record
    already exists for that (lead_id, level, kind='ADVANCE').

    Returns: {'created': bool, 'entry_numbers': list|None, 'reason': str}
    """
    try:
        lead = db.execute(text("""
            SELECT id, company_id, associated_partner_id, team_senior_partner_id,
                   solar_pipeline_status, cibil_confirmed, cibil_score,
                   status AS lead_status
            FROM crm_leads WHERE id = :lid
        """), {'lid': lead_id}).fetchone()

        if not lead:
            return {'created': False, 'reason': 'Lead not found'}

        if not lead.associated_partner_id:
            return {'created': False, 'reason': 'No associated VGK partner'}

        pipeline = (lead.solar_pipeline_status or '').strip()

        if pipeline not in ELIGIBLE_STAGES:
            return {'created': False, 'reason': f'Stage {pipeline!r} not eligible'}

        if not lead.cibil_confirmed:
            return {'created': False, 'reason': 'CIBIL not confirmed'}

        score = lead.cibil_score or 0
        if score < CIBIL_MIN_SCORE:
            return {'created': False, 'reason': f'CIBIL score {score} < {CIBIL_MIN_SCORE}'}

        now = _get_ist()
        created_numbers = []

        # Advance tiers: (level, partner_id, amount)
        tiers = [(1, lead.associated_partner_id, ADVANCE_AMOUNT)]
        if lead.team_senior_partner_id:
            tiers.append((2, lead.team_senior_partner_id, L2_ADVANCE_AMOUNT))

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

            db.execute(text("""
                INSERT INTO vgk_solar_cibil_advances
                    (company_id, lead_id, partner_id, entry_number, advance_amount,
                     status, stage_at_eligibility, cibil_score_at_check,
                     level, kind, created_at, updated_at)
                VALUES
                    (:cid, :lid, :pid, :en, :amt,
                     'PENDING', :stage, :score,
                     :lv, 'ADVANCE', :now, :now)
            """), {
                'cid': lead.company_id,
                'lid': lead_id,
                'pid': partner_id,
                'en': entry_number,
                'amt': float(amount),
                'stage': pipeline,
                'score': score,
                'lv': level,
                'now': now.replace(tzinfo=None),
            })
            db.commit()

            logger.info(
                f'[VGK-SOLAR-ADV] PENDING L{level} advance {entry_number} created for '
                f'lead {lead_id}, partner {partner_id}, stage={pipeline}, CIBIL={score}'
            )

            # DC-VGK-PARTNER-SYNC-001: Auto-release on eligibility (non-blocking)
            # L1: apply slab bonus; L2: no slab bonus
            try:
                rel = release_advance(
                    db=db, lead_id=lead_id,
                    released_by_id=None,
                    notes='Auto-released on eligibility (system)',
                    _level=level,
                )
                if rel.get('success'):
                    logger.info(
                        f'[VGK-SOLAR-ADV] Auto-RELEASED L{level} {entry_number} '
                        f'₹{rel.get("wallet_before")} → ₹{rel.get("wallet_after")}'
                    )
                else:
                    logger.warning(
                        f'[VGK-SOLAR-ADV] Auto-release L{level} {entry_number} failed: '
                        f'{rel.get("error")}'
                    )
            except Exception as _ar:
                logger.warning(
                    f'[VGK-SOLAR-ADV] Auto-release exception L{level} {entry_number}: {_ar}'
                )
                try:
                    db.rollback()
                except Exception:
                    pass

            created_numbers.append(entry_number)

        if created_numbers:
            return {'created': True, 'entry_numbers': created_numbers}
        return {'created': False, 'reason': 'All advances already existed'}

    except Exception as e:
        logger.warning(f'[VGK-SOLAR-ADV] check_and_create_advance failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'created': False, 'reason': str(e)}


def check_and_create_dvr_advance(db: Session, lead_id: int) -> dict:
    """
    DC-SOLAR-DVR-ADV-20260701-001 / DC-SOLAR-SPEC-20260710: Stage 2 Advance
    ("First Payment Received").

    When a solar lead's DVR > 0 is confirmed in vgk_cash_income_entries for the
    first time, auto-creates and releases:
      L1 (direct partner,  associated_partner_id): ₹500
      L5 (field support,   vgk_field_support_id):  ₹1,000

    Separate from and additive to the Stage-1 CIBIL advance (kind='ADVANCE').
    Kind = 'DVR_ADVANCE'. Idempotent per (lead, partner, level). Non-blocking.
    """
    DVR_L1_AMOUNT  = Decimal('500.00')
    DVR_L2_AMOUNT  = Decimal('1000.00')

    try:
        lead = db.execute(text("""
            SELECT id, company_id, category_id, associated_partner_id,
                   vgk_field_support_id, deal_value_received, first_dvr_confirmed_at
            FROM crm_leads WHERE id = :lid
        """), {'lid': lead_id}).fetchone()

        if not lead:
            return {'created': False, 'reason': 'Lead not found'}
        # DC-SOLAR-MULTICOMP-DVR-001: accept all solar categories across all 4 companies
        # (6=MNR, 19=co2, 36=co3, 48=co4). Prev guard was != 6, silently skipping companies 2-4.
        _SOLAR_CAT_IDS_ADV = (6, 19, 36, 48)
        if (lead.category_id or 0) not in _SOLAR_CAT_IDS_ADV:
            return {'created': False, 'reason': f'Not solar (category_id={lead.category_id})'}
        if not lead.associated_partner_id:
            return {'created': False, 'reason': 'No associated VGK partner'}

        dvr = Decimal(str(lead.deal_value_received or 0))
        if dvr <= 0:
            return {'created': False, 'reason': 'DVR is zero'}

        # DC-FIX-DVR-GATE-001 (Jul 2026): Removed income_row gate.
        # Previously required a vgk_cash_income_entries row to exist, but after
        # DC-SOLAR-STAGE-GATE-001 COMMISSION entries are blocked until sps='completed',
        # making Stage-2 DVR advance impossible at balance_received / installation_pending.
        # DVR > 0 + associated_partner_id is the correct and sufficient eligibility signal.
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
        # DC-SOLAR-SPEC-20260710: removed the 2026-07-01 hard cutoff — spec has no such
        # gate; Stage-2 advance applies to any lead reaching first-payment-received.

        tiers = [(1, lead.associated_partner_id, DVR_L1_AMOUNT)]
        if lead.vgk_field_support_id:
            # DC-DVR-L5-001: field support partner earns at level 5 (Support), not level 2
            tiers.append((5, lead.vgk_field_support_id, DVR_L2_AMOUNT))

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
                rel = release_dvr_advance(
                    db=db, lead_id=lead_id, partner_id=partner_id, level=level,
                    released_by_id=None,
                    notes='Auto-released on DVR confirmation (DC-SOLAR-DVR-ADV-20260701-001)',
                )
                if rel.get('success'):
                    logger.info(
                        f'[DVR-ADV] Auto-RELEASED L{level} {entry_number} '
                        f'₹{rel.get("amount_released")}'
                    )
                else:
                    logger.warning(f'[DVR-ADV] Auto-release L{level} {entry_number} failed: {rel.get("error")}')
            except Exception as _ar:
                logger.warning(f'[DVR-ADV] Auto-release exception L{level} {entry_number}: {_ar}')
                try:
                    db.rollback()
                except Exception:
                    pass

            created_numbers.append(entry_number)

        if created_numbers:
            return {'created': True, 'entry_numbers': created_numbers}
        return {'created': False, 'reason': 'All DVR advances already existed'}

    except Exception as e:
        logger.warning(f'[DVR-ADV] check_and_create_dvr_advance failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'created': False, 'reason': str(e)}


def release_dvr_advance(
    db: Session, lead_id: int, partner_id: int, level: int,
    released_by_id: int = None, notes: str = None,
) -> dict:
    """
    DC-SOLAR-DVR-ADV-20260701-001: Release a PENDING DVR_ADVANCE record.
    Credits advance_amount to partner wallet. L1 also gets slab bonus if an
    active slab_wise bonanza with advance_count_basis='DVR'/'BOTH' exists.
    """
    try:
        adv = db.execute(text("""
            SELECT id, partner_id, advance_amount, status, entry_number, company_id
            FROM vgk_solar_cibil_advances
            WHERE lead_id=:lid AND level=:lv AND kind='DVR_ADVANCE' AND partner_id=:pid
            FOR UPDATE
        """), {'lid': lead_id, 'lv': level, 'pid': partner_id}).fetchone()

        if not adv:
            return {'success': False, 'error': 'No DVR_ADVANCE record found'}
        if adv.status != 'PENDING':
            return {'success': False, 'error': f'DVR_ADVANCE is {adv.status}, not PENDING'}

        from app.models.staff_accounts import OfficialPartner
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == adv.partner_id
        ).with_for_update().first()
        if not partner:
            return {'success': False, 'error': 'Partner not found'}

        _txn_company_id = partner.company_id or adv.company_id
        amount = Decimal(str(adv.advance_amount))

        _pre_admin = (amount * Decimal('0.08')).quantize(Decimal('0.01'))
        _pre_tds   = (amount * Decimal('0.02')).quantize(Decimal('0.01'))
        _pre_net   = amount - _pre_admin - _pre_tds
        _avail_pts = partner.vgk_points_balance or Decimal('0')
        if _avail_pts < _pre_net:
            return {
                'success': False,
                'error': (
                    f"Partner's VGK Points ({float(_avail_pts):.0f} pts) < "
                    f"net DVR advance payout (₹{float(_pre_net):.2f})."
                ),
            }

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
                    "SELECT id, associated_partner_id, team_senior_partner_id, "
                    "team_extended_partner_id, team_core_partner_id, vgk_field_support_id, "
                    "category_id, company_id FROM crm_leads WHERE id=:lid"
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
        if adv.status != 'PENDING':
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
                    "SELECT id, associated_partner_id, team_senior_partner_id, "
                    "team_extended_partner_id, team_core_partner_id, vgk_field_support_id, "
                    "category_id, company_id FROM crm_leads WHERE id=:lid"
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


def apply_adjustment_at_completion(db: Session, lead_id: int, cash_income_entry_id: int) -> dict:
    """
    Called when the final cash income draft is generated (lead completed, balance = 0).
    If a RELEASED advance exists, deducts ₹1,000 from that cash income entry's net payout
    by recording an adjustment on the advance record.
    The cash income entry's commission_amount is reduced by ₹1,000 (minimum ₹0).
    Status → ADJUSTED.
    """
    try:
        advs = db.execute(text("""
            SELECT id, partner_id, advance_amount, status, entry_number, kind
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 1 AND kind IN ('ADVANCE', 'DVR_ADVANCE') AND status = 'RELEASED'
            FOR UPDATE
        """), {'lid': lead_id}).fetchall()

        if not advs:
            return {'adjusted': False, 'reason': 'No released L1 advance (CIBIL or DVR) to adjust'}

        entry = db.execute(text("""
            SELECT id, commission_amount FROM vgk_cash_income_entries
            WHERE id = :eid FOR UPDATE
        """), {'eid': cash_income_entry_id}).fetchone()

        if not entry:
            return {'adjusted': False, 'reason': 'Cash income entry not found'}

        original_commission = Decimal(str(entry.commission_amount or 0))
        total_advance_amt = sum(Decimal(str(a.advance_amount or 0)) for a in advs)
        adjusted_commission = max(Decimal('0'), original_commission - total_advance_amt)
        actual_adjustment = original_commission - adjusted_commission

        now = _get_ist()
        db.execute(text("""
            UPDATE vgk_cash_income_entries
            SET commission_amount = :new_amt, updated_at = :now
            WHERE id = :eid
        """), {'new_amt': float(adjusted_commission), 'now': now.replace(tzinfo=None), 'eid': cash_income_entry_id})

        for adv in advs:
            db.execute(text("""
                UPDATE vgk_solar_cibil_advances SET
                    status = 'ADJUSTED',
                    adjustment_amount = :adj,
                    adjustment_entry_id = :eid,
                    adjusted_at = :now,
                    updated_at  = :now
                WHERE id = :aid
            """), {
                'adj': float(adv.advance_amount or 0),
                'eid': cash_income_entry_id,
                'now': now.replace(tzinfo=None),
                'aid': adv.id,
            })

        db.commit()
        logger.info(
            f'[VGK-SOLAR-ADV] ADJUSTED {adv.entry_number}: '
            f'commission ₹{float(original_commission)} → ₹{float(adjusted_commission)} '
            f'(deducted ₹{float(actual_adjustment)}) via income entry {cash_income_entry_id}'
        )
        return {
            'adjusted': True,
            'entry_number': adv.entry_number,
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
