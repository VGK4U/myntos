"""
VGK Brand Incentive Service (DC Protocol Jun 2026)

DC-VGK-BRAND-INCENTIVE-001: When a solar lead has solar_brand_id set and the
CIBIL gate fires, additional brand advances are created for L1/L2/L5 partners.
At income generation (lead completed), brand commission entries are created for
L2 and L5.

Brand advance VCI level mapping (avoids collision with regular entries):
  L1 brand advance → vgk_solar_cibil_advances level=1 kind='BRAND_ADVANCE'
                     VCI level=7 kind='BRAND_ADVANCE'
  L2 brand advance → vgk_solar_cibil_advances level=2 kind='BRAND_ADVANCE'
                     VCI level=8 kind='BRAND_ADVANCE'
  L5 brand advance → vgk_solar_cibil_advances level=5 kind='BRAND_ADVANCE'
                     VCI level=9 kind='BRAND_ADVANCE'

Brand commission VCI level mapping (at final income):
  L2 brand commission → VCI level=12 kind='BRAND_COMMISSION'
  L5 brand commission → VCI level=15 kind='BRAND_COMMISSION'

All brand advances follow the same PENDING → RELEASED lifecycle.
Narration: "For referring specific brand [Brand Name]"
"""

import logging
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

CIBIL_MIN_SCORE = 600

ELIGIBLE_STAGES = frozenset({
    'application_submitted', 'pending_with_bank', 'documents_issue',
    'load_extension', 'electricity_bill_change', 'installation_pending',
    'net_meter_pending', 'balance_pending', 'balance_received',
    'subsidy_pending', 'completed',
})

ADMIN_CHARGE_PCT = Decimal('8')
TDS_PCT          = Decimal('2')

# VCI level for brand advances (avoids collision with regular entries at level=0)
BRAND_ADV_VCI_LEVEL = {1: 7, 2: 8, 5: 9}
# VCI level for brand commissions (avoids collision with regular commissions)
BRAND_COMM_VCI_LEVEL = {2: 12, 5: 15}


def _get_ist():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


def _next_advance_number(db: Session) -> str:
    """Generate next VSCA-YYMM-NNNN advance number (shared sequence with main advance table)."""
    now = _get_ist()
    yymm = now.strftime('%y%m')
    prefix = f'VSCA-{yymm}'
    result = db.execute(text(
        "SELECT MAX(CAST(RIGHT(entry_number, 4) AS INTEGER)) "
        "FROM vgk_solar_cibil_advances "
        "WHERE entry_number ~ ('^VSCA-[0-9]{4}-[0-9]{4}$') "
        "  AND entry_number LIKE :pfx"
    ), {'pfx': f'{prefix}-%'}).scalar()
    seq = (result or 0) + 1
    return f'{prefix}-{seq:04d}'


def _next_vci_entry_number(db: Session, company_id: int) -> str:
    """Generate next VCI entry number (shared sequence)."""
    now = _get_ist()
    yymm = now.strftime('%y%m')
    prefix = f'VCI-{yymm}'
    result = db.execute(text(
        "SELECT MAX(CAST(RIGHT(entry_number, 4) AS INTEGER)) "
        "FROM vgk_cash_income_entries "
        "WHERE entry_number LIKE :pfx"
    ), {'pfx': f'{prefix}-%'}).scalar()
    seq = (result or 0) + 1
    return f'{prefix}-{seq:04d}'


def _log_wallet_txn(
    db, partner_id, company_id, txn_type, direction, amount,
    wallet_before, wallet_after, ref_type=None, ref_id=None,
    description=None, staff_id=None,
):
    try:
        from app.services.vgk_cash_income import _log_wallet_txn as _base
        _base(
            db, partner_id=partner_id, company_id=company_id,
            txn_type=txn_type, direction=direction, amount=amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type=ref_type, ref_id=ref_id,
            description=description, staff_id=staff_id,
        )
    except Exception as _e:
        logger.warning(f'[VGK-BRAND-ADV] wallet txn log failed (non-fatal): {_e}')


def _release_brand_advance(db: Session, advance_id: int, narration: str) -> dict:
    """
    Release a single brand advance row by ID.
    Same wallet mechanics as regular advance (8% admin + 2% TDS + payout DR),
    but no slab bonus.
    Mirrors the advance into a VCI entry at the brand VCI level.
    Non-blocking on failure.
    """
    try:
        adv = db.execute(text("""
            SELECT id, partner_id, advance_amount, status, entry_number, company_id, level, kind
            FROM vgk_solar_cibil_advances WHERE id = :aid FOR UPDATE
        """), {'aid': advance_id}).fetchone()

        if not adv:
            return {'success': False, 'error': 'Advance not found'}
        if adv.status != 'PENDING':
            return {'success': False, 'error': f'Advance is {adv.status}, not PENDING'}

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
                    f"net payout (₹{float(_pre_net):.2f}) for brand advance."
                ),
            }

        wallet_before = partner.vgk_cash_wallet or Decimal('0')
        wallet_after  = wallet_before + amount
        partner.vgk_cash_wallet = wallet_after
        partner.updated_at = _get_ist()

        now = _get_ist()
        db.execute(text("""
            UPDATE vgk_solar_cibil_advances SET
                status = 'RELEASED',
                wallet_before_release = :wb,
                wallet_after_release  = :wa,
                released_by_id = NULL,
                released_at    = :now,
                notes          = :notes,
                updated_at     = :now
            WHERE id = :aid
        """), {
            'wb': float(wallet_before), 'wa': float(wallet_after),
            'now': now.replace(tzinfo=None),
            'notes': narration, 'aid': adv.id,
        })

        _log_wallet_txn(
            db, partner_id=partner.id, company_id=_txn_company_id,
            txn_type='SOLAR_ADVANCE_CREDIT', direction='CR', amount=amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type='VGK_BRAND_ADV', ref_id=adv.id,
            description=f'Brand advance released — {adv.entry_number} | {narration}',
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
            ref_type='VGK_BRAND_ADV', ref_id=adv.id,
            description=f'Admin 8% + TDS 2% on brand advance — {adv.entry_number}',
        )

        try:
            _wb_payout = partner.vgk_cash_wallet
            partner.vgk_cash_wallet = _wb_payout - _adv_net
            _log_wallet_txn(
                db, partner_id=partner.id, company_id=_txn_company_id,
                txn_type='SOLAR_ADV_PAYOUT', direction='DR', amount=_adv_net,
                wallet_before=_wb_payout, wallet_after=partner.vgk_cash_wallet,
                ref_type='VGK_BRAND_ADV', ref_id=adv.id,
                description=f'Brand advance offset by points — {adv.entry_number}',
            )
        except Exception as _pe:
            logger.warning(f'[VGK-BRAND-ADV] payout DR failed (non-fatal): {_pe}')

        # Mirror into VCI entry
        _vci_level = BRAND_ADV_VCI_LEVEL.get(adv.level, 7)
        try:
            _create_brand_advance_vci(
                db=db, advance_row=adv, partner=partner,
                company_id=4,
                vci_level=_vci_level,
                narration=narration,
            )
        except Exception as _vci_e:
            logger.warning(f'[VGK-BRAND-ADV] VCI mirror failed (non-fatal): {_vci_e}')

        db.commit()
        logger.info(
            f'[VGK-BRAND-ADV] RELEASED {adv.entry_number} (L{adv.level}) '
            f'partner {getattr(partner, "partner_code", partner.id)} '
            f'₹{float(amount):.2f} | {narration}'
        )
        return {
            'success': True,
            'entry_number': adv.entry_number,
            'amount': float(amount),
            'wallet_before': float(wallet_before),
            'wallet_after': float(wallet_after),
        }

    except Exception as e:
        logger.warning(f'[VGK-BRAND-ADV] _release_brand_advance failed for advance {advance_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'success': False, 'error': str(e)}


def _create_brand_advance_vci(
    db: Session, advance_row, partner, company_id: int,
    vci_level: int, narration: str,
):
    """Mirror a brand advance into vgk_cash_income_entries. Idempotent."""
    from app.models.vgk_cash_income import VGKCashIncomeEntry

    existing = db.execute(text("""
        SELECT id FROM vgk_cash_income_entries
        WHERE partner_id = :pid AND source_lead_id = :lid
          AND kind = 'BRAND_ADVANCE' AND level = :lv
        LIMIT 1
    """), {
        'pid': advance_row.partner_id,
        'lid': advance_row.lead_id,
        'lv': vci_level,
    }).fetchone()
    if existing:
        return {'success': True, 'idempotent': True}

    amount = Decimal(str(advance_row.advance_amount or 0))
    _admin = (amount * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01'))
    _tds   = (amount * TDS_PCT          / Decimal('100')).quantize(Decimal('0.01'))
    _net   = amount - _admin - _tds

    now = _get_ist()
    entry_number = _next_vci_entry_number(db, company_id)

    entry = VGKCashIncomeEntry(
        company_id            = company_id,
        entry_number          = entry_number,
        partner_id            = advance_row.partner_id,
        source_lead_id        = advance_row.lead_id,
        level                 = vci_level,
        kind                  = 'BRAND_ADVANCE',
        status                = 'PENDING',
        commission_amount     = amount,
        admin_charges         = _admin,
        tds_amount            = _tds,
        net_payout            = _net,
        deal_value_total      = Decimal('0'),
        deal_value_excl_tax   = Decimal('0'),
        commission_pct        = Decimal('0'),
        points_debit_required = _net,
        points_actually_debited = Decimal('0'),
        notes                 = narration,
        created_at            = now,
        updated_at            = now,
    )
    db.add(entry)
    db.flush()
    logger.info(
        f'[VGK-BRAND-ADV] VCI entry {entry_number} L{vci_level} created for '
        f'partner {advance_row.partner_id} lead {advance_row.lead_id}'
    )
    return {'success': True, 'entry_number': entry_number}


def check_and_create_brand_advance(db: Session, lead_id: int) -> dict:
    """
    DC-VGK-BRAND-INCENTIVE-001: Called at the same CIBIL gate as the regular advance.
    Creates brand advance rows in vgk_solar_cibil_advances for L1, L2, and L5
    if solar_brand_id is set on the lead and the brand is active.

    Narration: "For referring specific brand [Brand Name]"
    Returns a summary dict.
    """
    try:
        lead = db.execute(text("""
            SELECT id, company_id,
                   associated_partner_id,
                   team_senior_partner_id,
                   vgk_field_support_id,
                   solar_pipeline_status,
                   cibil_confirmed, cibil_score,
                   solar_brand_id
            FROM crm_leads WHERE id = :lid
        """), {'lid': lead_id}).fetchone()

        if not lead or not lead.solar_brand_id:
            return {'created': False, 'reason': 'No brand set on lead'}

        pipeline = (lead.solar_pipeline_status or '').strip()
        if pipeline not in ELIGIBLE_STAGES:
            return {'created': False, 'reason': f'Stage {pipeline!r} not eligible'}

        if not lead.cibil_confirmed:
            return {'created': False, 'reason': 'CIBIL not confirmed'}

        score = lead.cibil_score or 0
        if score < CIBIL_MIN_SCORE:
            return {'created': False, 'reason': f'CIBIL score {score} < {CIBIL_MIN_SCORE}'}

        brand = db.execute(text("""
            SELECT id, brand_name, l1_amount, l2_amount, l5_amount, is_active
            FROM vgk_incentive_brands WHERE id = :bid
        """), {'bid': lead.solar_brand_id}).fetchone()

        if not brand or not brand.is_active:
            return {'created': False, 'reason': 'Brand not found or inactive'}

        narration = f'For referring specific brand {brand.brand_name}'
        now = _get_ist()

        tiers = []
        if lead.associated_partner_id and Decimal(str(brand.l1_amount or 0)) > 0:
            tiers.append((1, lead.associated_partner_id, Decimal(str(brand.l1_amount))))
        if lead.team_senior_partner_id and Decimal(str(brand.l2_amount or 0)) > 0:
            tiers.append((2, lead.team_senior_partner_id, Decimal(str(brand.l2_amount))))
        if lead.vgk_field_support_id and Decimal(str(brand.l5_amount or 0)) > 0:
            tiers.append((5, lead.vgk_field_support_id, Decimal(str(brand.l5_amount))))

        if not tiers:
            return {'created': False, 'reason': 'No eligible partners or zero amounts'}

        created_numbers = []
        for (level, partner_id, amount) in tiers:
            existing = db.execute(text("""
                SELECT id FROM vgk_solar_cibil_advances
                WHERE lead_id = :lid AND level = :lv AND kind = 'BRAND_ADVANCE'
                LIMIT 1
            """), {'lid': lead_id, 'lv': level}).fetchone()

            if existing:
                logger.debug(
                    f'[VGK-BRAND-ADV] L{level} brand advance already exists '
                    f'for lead {lead_id} — skipping'
                )
                continue

            entry_number = _next_advance_number(db)
            db.execute(text("""
                INSERT INTO vgk_solar_cibil_advances
                    (company_id, lead_id, partner_id, entry_number, advance_amount,
                     status, stage_at_eligibility, cibil_score_at_check,
                     level, kind, narration, created_at, updated_at)
                VALUES
                    (:cid, :lid, :pid, :en, :amt,
                     'PENDING', :stage, :score,
                     :lv, 'BRAND_ADVANCE', :narration, :now, :now)
            """), {
                'cid': lead.company_id,
                'lid': lead_id,
                'pid': partner_id,
                'en': entry_number,
                'amt': float(amount),
                'stage': pipeline,
                'score': score,
                'lv': level,
                'narration': narration,
                'now': now.replace(tzinfo=None),
            })
            db.commit()

            logger.info(
                f'[VGK-BRAND-ADV] PENDING brand advance {entry_number} L{level} '
                f'created for lead {lead_id}, partner {partner_id}'
            )

            new_adv = db.execute(text(
                "SELECT id FROM vgk_solar_cibil_advances WHERE entry_number = :en"
            ), {'en': entry_number}).fetchone()

            if new_adv:
                try:
                    rel = _release_brand_advance(db, new_adv.id, narration)
                    if not rel.get('success'):
                        logger.warning(
                            f'[VGK-BRAND-ADV] Auto-release of {entry_number} failed: '
                            f'{rel.get("error")}'
                        )
                    else:
                        logger.info(f'[VGK-BRAND-ADV] Auto-RELEASED {entry_number}')
                except Exception as _re:
                    logger.warning(
                        f'[VGK-BRAND-ADV] Auto-release exception for {entry_number}: {_re}'
                    )
                    try:
                        db.rollback()
                    except Exception:
                        pass

            created_numbers.append(entry_number)

        if created_numbers:
            return {'created': True, 'entry_numbers': created_numbers, 'brand': brand.brand_name}
        return {'created': False, 'reason': 'All brand advances already existed'}

    except Exception as e:
        logger.warning(
            f'[VGK-BRAND-ADV] check_and_create_brand_advance failed for lead {lead_id}: {e}'
        )
        try:
            db.rollback()
        except Exception:
            pass
        return {'created': False, 'reason': str(e)}


def generate_brand_commission_entries(db: Session, lead) -> int:
    """
    DC-VGK-BRAND-INCENTIVE-001: Called at income generation time (lead completed).
    Creates L2 and L5 brand commission VCI entries if solar_brand_id is set.
    Returns number of entries created.
    """
    try:
        solar_brand_id = getattr(lead, 'solar_brand_id', None)
        if not solar_brand_id:
            return 0

        brand = db.execute(text("""
            SELECT id, brand_name, l2_amount, l5_amount, is_active
            FROM vgk_incentive_brands WHERE id = :bid
        """), {'bid': solar_brand_id}).fetchone()

        if not brand or not brand.is_active:
            return 0

        company_id = 4

        tiers = []
        l2_pid = getattr(lead, 'team_senior_partner_id', None)
        l5_pid = getattr(lead, 'vgk_field_support_id', None)

        if l2_pid and Decimal(str(brand.l2_amount or 0)) > 0:
            tiers.append((BRAND_COMM_VCI_LEVEL[2], l2_pid, Decimal(str(brand.l2_amount))))
        if l5_pid and Decimal(str(brand.l5_amount or 0)) > 0:
            tiers.append((BRAND_COMM_VCI_LEVEL[5], l5_pid, Decimal(str(brand.l5_amount))))

        if not tiers:
            return 0

        from app.models.vgk_cash_income import VGKCashIncomeEntry
        narration = f'Brand commission — {brand.brand_name}'
        now = _get_ist()
        created = 0

        for (vci_level, partner_id, amount) in tiers:
            existing = db.execute(text("""
                SELECT id FROM vgk_cash_income_entries
                WHERE partner_id = :pid AND source_lead_id = :lid
                  AND kind = 'BRAND_COMMISSION' AND level = :lv
                LIMIT 1
            """), {'pid': partner_id, 'lid': lead.id, 'lv': vci_level}).fetchone()

            if existing:
                continue

            _admin = (amount * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01'))
            _tds   = (amount * TDS_PCT          / Decimal('100')).quantize(Decimal('0.01'))
            _net   = amount - _admin - _tds

            entry_number = _next_vci_entry_number(db, company_id)

            entry = VGKCashIncomeEntry(
                company_id              = company_id,
                entry_number            = entry_number,
                partner_id              = partner_id,
                source_lead_id          = lead.id,
                level                   = vci_level,
                kind                    = 'BRAND_COMMISSION',
                status                  = 'DRAFT',
                commission_amount       = amount,
                admin_charges           = _admin,
                tds_amount              = _tds,
                net_payout              = _net,
                deal_value_total        = Decimal('0'),
                deal_value_excl_tax     = Decimal('0'),
                commission_pct          = Decimal('0'),
                points_debit_required   = _net,
                points_actually_debited = Decimal('0'),
                notes                   = narration,
                created_at              = now,
                updated_at              = now,
            )
            db.add(entry)
            db.flush()
            created += 1
            logger.info(
                f'[VGK-BRAND-COMM] DRAFT {entry_number} L{vci_level} '
                f'partner={partner_id} ₹{float(amount):.2f} lead={lead.id}'
            )

        if created:
            db.commit()
        return created

    except Exception as e:
        logger.warning(
            f'[VGK-BRAND-ADV] generate_brand_commission_entries failed for lead {lead.id}: {e}'
        )
        try:
            db.rollback()
        except Exception:
            pass
        return 0


def recover_brand_advances(db: Session, lead_id: int, reason: str = None) -> dict:
    """
    Called when lead moves to RECOVERY_STAGES.
    Recovers ALL RELEASED brand advances for this lead (same logic as regular advance recovery).
    Non-blocking.
    """
    try:
        advs = db.execute(text("""
            SELECT id, partner_id, advance_amount, status, entry_number, company_id
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND kind = 'BRAND_ADVANCE' AND status = 'RELEASED'
            FOR UPDATE
        """), {'lid': lead_id}).fetchall()

        if not advs:
            return {'success': True, 'action': 'no_brand_advances_to_recover', 'count': 0}

        from app.models.staff_accounts import OfficialPartner
        recovered_count = 0
        now = _get_ist()

        for adv in advs:
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == adv.partner_id
            ).with_for_update().first()

            if not partner:
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
                    recovery_reason = :rr,
                    recovered_at    = :now,
                    updated_at      = :now
                WHERE id = :aid
            """), {
                'st': new_status,
                'ra': float(recovery_amt),
                'wb': float(wallet_before),
                'wa': float(wallet_after),
                'rr': reason or 'Lead cancelled/rejected',
                'now': now.replace(tzinfo=None),
                'aid': adv.id,
            })

            if recovery_amt > 0:
                _log_wallet_txn(
                    db, partner_id=partner.id, company_id=_txn_company_id,
                    txn_type='SOLAR_ADVANCE_RECOVERY', direction='DR', amount=recovery_amt,
                    wallet_before=wallet_before, wallet_after=wallet_after,
                    ref_type='VGK_BRAND_ADV', ref_id=adv.id,
                    description=f'Brand advance recovered ({new_status}) — {adv.entry_number}',
                )

            recovered_count += 1

        db.commit()
        logger.info(
            f'[VGK-BRAND-ADV] Recovered {recovered_count} brand advance(s) for lead {lead_id}'
        )
        return {'success': True, 'count': recovered_count}

    except Exception as e:
        logger.warning(f'[VGK-BRAND-ADV] recover_brand_advances failed for lead {lead_id}: {e}')
        try:
            db.rollback()
        except Exception:
            pass
        return {'success': False, 'error': str(e)}
