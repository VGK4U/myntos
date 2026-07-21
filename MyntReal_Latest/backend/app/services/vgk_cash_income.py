"""
VGK Cash Income Service (DC Protocol Mar 2026)

Called when: CRM lead.status == 'completed' AND lead.associated_partner_id is set.
No deal_value_balance == 0 gate — income is generated on completion regardless of
outstanding subsidy/balance.

For each eligible level (L1/L2/L3/L4/L5/L6):
  - Resolves the partner using same logic as vgk_commission.py
  - Creates a DRAFT VGKCashIncomeEntry (idempotent — skips if already exists)

DC-VGK-FLOW-001 (May 2026) — Realigned flow:
  DRAFT creation:
    - vgk_cash_wallet += commission_amount   (member sees income immediately)
    - vgk_points_balance += commission_amount (points credited, reason INCOME_EARNED)
  Confirmation (Sales staff):
    - Status-only: DRAFT → PENDING  (no wallet / points movement)
  Release (Accounts staff):
    - 8% admin charges + 2% TDS deducted from wallet
    - NET points debited from vgk_points_balance (reason COMMISSION_ADJUSTMENT)
    - vgk_cash_earned_total += GROSS commission
    - Entry → RELEASED
  Backward compat: entries where points_actually_debited > 0 were confirmed under the old
  flow (debit at confirm) — release skips the second debit.

No negative impact on existing vgk_team_income_entries or points ledger.
"""

import logging
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

ADMIN_CHARGE_PCT = Decimal('8')
TDS_PCT          = Decimal('2')
GST_PCT          = Decimal('9')   # CGST 9% + SGST 9% on marketing support fee (cross-company)


def _get_ist():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


def _next_entry_number(db: Session, company_id: int) -> str:
    now = _get_ist()
    yymm = now.strftime('%y%m')
    prefix = f'VCI-{yymm}'
    # DC-VCI-SEQLOCK-001: pg_advisory_xact_lock serialises concurrent / rapid-sequential
    # callers so two sessions never compute the same MAX+1 simultaneously.
    # The lock is released automatically when the enclosing transaction commits or rolls back.
    lock_key = int(f'9{yymm}')
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {'k': lock_key})
    # Only consider new short-format entries (VCI-YYMM-{1-6 digits}).
    # Old entries used a long timestamp-embedded format whose numeric value
    # overflows BIGINT when all non-digit characters are stripped.
    result = db.execute(text(
        "SELECT MAX(CAST(SPLIT_PART(entry_number, '-', 3) AS INTEGER)) "
        "FROM vgk_cash_income_entries "
        "WHERE entry_number ~ :pat"
    ), {'pat': f'^VCI-{yymm}-[0-9]{{1,6}}$'}).scalar()
    seq = (result or 0) + 1
    return f'{prefix}-{seq:04d}'


def generate_vgk_cash_income_drafts(db: Session, lead) -> int:
    """
    Create DRAFT VGKCashIncomeEntry rows for all eligible levels on a completed lead.
    Idempotent — skips levels that already have an entry.
    Returns count of new DRAFT entries created.
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner, VGKTeamCommissionConfig

    if not lead.associated_partner_id:
        logger.info(f'[VGK-CI] Lead {lead.id} has no associated_partner_id — skipping cash income')
        return 0

    company_id = lead.company_id
    category_id = lead.category_id
    deal_total  = Decimal(str(lead.deal_value_total or 0))
    # DC Protocol: commission is always calculated on the OVERALL deal value (inc. tax).
    # deal_value_excl_tax is stored in the entry for audit only — not used in calculation.
    deal_ex_tax = Decimal(str(lead.deal_value_excl_tax or 0))

    # DC-COMM-DVR-001 (Jun 2026): Commission base = deal_value_received (DVR) for ALL categories.
    # DVR = actual amount received from the customer at balance-received stage.
    # confirmed_final_value and solar_value are NOT used as the commission base (audit/snapshot only).
    # Fallback to deal_value_total only when DVR is zero (payment not yet recorded).
    _dvr = Decimal(str(lead.deal_value_received or 0))
    commission_base = _dvr if _dvr > 0 else deal_total

    if commission_base <= 0:
        _cfv = getattr(lead, 'confirmed_final_value', None)
        logger.info(f'[VGK-CI] Lead {lead.id} has zero commission base (dvr={float(_dvr)}, total={float(deal_total)}, cfv={_cfv}) — skipping')
        return 0

    # DC-ADV-PERLEVEL-001 (Jul 2026): Advances are deducted per-level from the specific
    # recipient's own commission entry (see apply_adjustment_at_completion in
    # vgk_solar_advance.py, called by the CRM completion hooks), NOT from the shared
    # commission_base used to compute every level's commission.
    # Previously this block subtracted the TOTAL advance (across all levels) from the
    # base before splitting into L1..L6 percentages, silently under-paying L2-L6
    # partners for an advance they never received. Removed per DC-SOLAR-SPEC-20260710
    # ("deduct advances already paid... pay only the remaining balance TO EACH ELIGIBLE
    # LEVEL" — i.e. per-level, not company-wide).

    if commission_base <= 0:
        logger.info(f'[VGK-CI] Lead {lead.id}: commission base zero after advance deduction — skipping')
        return 0

    # DC-SHOWROOM-CLEAR-001 (Jul 2026): If showroom_vgk_id was cleared (None), cancel any
    # existing DRAFT L6 entries for this lead NOW — before the solar stage gate — so orphan
    # DRAFTs are cleaned up even when the lead is at installation_pending or other pre-balance
    # stages.  DC-DEDUP-LEVEL-001 only fires inside the levels_map loop (far below), and L6 is
    # absent from the map when showroom is None.  Only DRAFT status is touched; PENDING and
    # beyond are left for manual review.
    _showroom_id_early = getattr(lead, 'showroom_vgk_id', None)
    if not _showroom_id_early:
        _l6_orphans_early = db.query(VGKCashIncomeEntry).filter(
            VGKCashIncomeEntry.company_id     == company_id,
            VGKCashIncomeEntry.source_lead_id == lead.id,
            VGKCashIncomeEntry.level          == 6,
            VGKCashIncomeEntry.status         == 'DRAFT',
        ).all()
        for _l6_orph in _l6_orphans_early:
            _l6_orph.status = 'CANCELLED'
            if hasattr(_l6_orph, 'updated_at'):
                _l6_orph.updated_at = _get_ist()
            logger.info(
                f'[VGK-CI] DC-SHOWROOM-CLEAR-001: Lead {lead.id} L6 orphan '
                f'{_l6_orph.entry_number} (partner {_l6_orph.partner_id}) → CANCELLED '
                f'(showroom_vgk_id cleared)'
            )

    # DC-SOLAR-STAGE-GATE-001 (Jul 2026): Solar leads (category_id=6) must only generate
    # COMMISSION entries once the deal balance is confirmed (solar_pipeline_status in
    # balance_received / subsidy_pending / completed).  ADVANCEs are unaffected — they are
    # created by create_vgk_advance_mirror_entry, which has its own release gate.
    # This guard covers ALL callers: previously two call sites (CRM transaction creation and
    # income-entry confirmation) had no pipeline check and silently created drafts at
    # installation_pending / other pre-balance stages.
    # DC-SOLAR-SPEC-20260710: Final commission must trigger ONLY at solar_pipeline_status
    # = 'completed' — explicitly NOT at balance_received or subsidy_pending (those stages
    # now only carry CIBIL/DVR advances, not the final settlement).
    # DC-SOLAR-GATE-ALLCAT-001 (Jul 2026): Extended from category_id==6 to ANY lead that has
    # a solar_pipeline_status set (e.g. category_id=19 EV/Solar hybrids). Any non-null,
    # non-empty solar_pipeline_status that is not 'completed' must block COMMISSION generation.
    _sps_gate = (getattr(lead, 'solar_pipeline_status', '') or '').lower()
    _is_solar = (category_id == 6) or bool(_sps_gate)
    if _is_solar:
        _SOLAR_COMM_STAGES = {'subsidy_pending', 'completed'}
        if _sps_gate not in _SOLAR_COMM_STAGES:
            logger.info(
                f'[VGK-CI] DC-SOLAR-STAGE-GATE-001: Lead {lead.id} cat={category_id} '
                f'solar_pipeline_status={_sps_gate!r} — COMMISSION draft skipped '
                f'(requires {_SOLAR_COMM_STAGES})'
            )
            return 0

    # DC Protocol May 2026: Resolve L1 partner first — their activation status drives config selection.
    l1 = db.query(OfficialPartner).filter(OfficialPartner.id == lead.associated_partner_id).first()
    if not l1:
        return 0

    # DC-ALL-PAID-001 (Jun 2026): All official partners (dealers, distributors, staff-linked)
    # are treated as paid/activated members for commission rate selection.
    # The is_paid_activation flag on OfficialPartner is NOT used — always select the
    # is_paid_member=True (Activated) config row which carries the full commission cascade.
    cfg = db.query(VGKTeamCommissionConfig).filter(
        VGKTeamCommissionConfig.company_id == company_id,
        VGKTeamCommissionConfig.category_id == category_id,
        VGKTeamCommissionConfig.is_active == True,
        VGKTeamCommissionConfig.is_paid_member == True,
    ).order_by(VGKTeamCommissionConfig.updated_at.desc()).first() if category_id else None
    if not cfg:
        # Fallback: any active config for this company+category (e.g. only Registered row exists)
        cfg = db.query(VGKTeamCommissionConfig).filter(
            VGKTeamCommissionConfig.company_id == company_id,
            VGKTeamCommissionConfig.category_id == category_id,
            VGKTeamCommissionConfig.is_active == True,
        ).order_by(VGKTeamCommissionConfig.updated_at.desc()).first() if category_id else None

    if not cfg:
        logger.info(f'[VGK-CI] No VGK commission config for lead {lead.id} category {category_id} company {company_id}')
        return 0

    logger.info(f'[VGK-CI] Lead {lead.id} L1={l1.partner_code} → config id={cfg.id} is_paid_member={cfg.is_paid_member} (DC-ALL-PAID-001)')

    # DC-TEAM-ASSIGN-001 (Jun 2026): Respect staff-selected override partners for L2/L3/L4.
    # If staff manually overrode the upline chain, use that; else fall back to tree walk.
    _l2_ovr = db.query(OfficialPartner).filter(OfficialPartner.id == getattr(lead, 'team_senior_partner_id', None)).first() if getattr(lead, 'team_senior_partner_id', None) else None
    _l3_ovr = db.query(OfficialPartner).filter(OfficialPartner.id == getattr(lead, 'team_extended_partner_id', None)).first() if getattr(lead, 'team_extended_partner_id', None) else None
    _l4_ovr = db.query(OfficialPartner).filter(OfficialPartner.id == getattr(lead, 'team_core_partner_id', None)).first() if getattr(lead, 'team_core_partner_id', None) else None
    l2 = _l2_ovr if _l2_ovr else (db.query(OfficialPartner).filter(OfficialPartner.id == l1.parent_partner_id).first() if l1.parent_partner_id else None)
    l3 = _l3_ovr if _l3_ovr else (db.query(OfficialPartner).filter(OfficialPartner.id == l2.parent_partner_id).first() if (l2 and l2.parent_partner_id) else None)
    # DC-VGK-L4CORE-001: L4 CORE = upliner of L3
    l4_core = _l4_ovr if _l4_ovr else (db.query(OfficialPartner).filter(OfficialPartner.id == l3.parent_partner_id).first() if (l3 and l3.parent_partner_id) else None)

    # DC-L4-FALLBACK-001: Use assigned field support for L5.
    # If no field support is assigned, fall back to VGK07102207 (partner 31) as company-level support.
    _l5_id = lead.vgk_field_support_id or 31
    l5 = db.query(OfficialPartner).filter(OfficialPartner.id == _l5_id).first()

    # DC-VGK-ACTIVATION-001: L2/L3 earn only if they hold a VGK07 partner code (default activation).
    def _vgk_active(p) -> bool:
        return p is not None and bool(getattr(p, 'partner_code', None)) and p.partner_code.upper().startswith('VGK07')

    is_loyal = bool(getattr(l1, 'is_loyal_coupon', False))

    _l4core_pct = Decimal(str(getattr(cfg, 'level4_core_pct', 0) or 0))

    # DC-SHOWROOM-COMMISSION-001: Showroom commission if showroom_vgk_id is set on lead.
    _showroom_id   = getattr(lead, 'showroom_vgk_id', None)
    _showroom_pct  = Decimal(str(getattr(cfg, 'showroom_pct',  0) or 0))
    _showroom_type = str(getattr(cfg, 'showroom_type', 'PCT') or 'PCT')
    _showroom_amt  = Decimal(str(getattr(cfg, 'showroom_amt',  0) or 0))
    _showroom_p    = db.query(OfficialPartner).filter(OfficialPartner.id == _showroom_id).first() if _showroom_id else None

    # DC-BUG-FIX-001 (Jun 2026): _cfv and _sv must be bound BEFORE the entry-creation loop.
    # Previously only assigned inside the early-exit block → UnboundLocalError on every real lead.
    _cfv = getattr(lead, 'confirmed_final_value', None)
    _sv  = getattr(lead, 'solar_value', None)

    def _calc_comm(base: Decimal, pct: Decimal, type_: str, amt: Decimal) -> Decimal:
        """Calculate commission: AMOUNT type uses flat amt; PCT type uses base × pct / 100."""
        if type_ == 'AMOUNT':
            return Decimal(str(amt)).quantize(Decimal('0.01'))
        return (base * pct / Decimal('100')).quantize(Decimal('0.01'))

    levels_map = {
        1: (l1,  Decimal(str(cfg.level1_pct or 0))),
        2: (l2 if _vgk_active(l2) else None,  Decimal(str(cfg.level2_pct or 0))),
        3: (None if is_loyal else (l3 if _vgk_active(l3) else None),
            Decimal('0') if is_loyal else Decimal(str(cfg.level3_pct or 0))),
        # L4 CORE (DC-VGK-L4CORE-001): upliner of L3
        4: (None if is_loyal else (l4_core if _vgk_active(l4_core) else None),
            Decimal('0') if is_loyal else _l4core_pct),
        # L5 SUPPORT: field support per lead
        5: (None if is_loyal else l5,
            Decimal('0') if is_loyal else Decimal(str(cfg.level4_pct or 0))),
    }
    # DC-AMOUNT-OVERRIDE-001 (Jun 2026): Populate commission overrides for AMOUNT-type
    # levels (L1–L5). When a level is configured as flat AMOUNT, its pct column = 0,
    # so the loop guard (pct<=0 AND level not in overrides) would silently skip the
    # entry. Pre-computing the flat amount here unlocks those entries.
    # Tuple: (income level, pct_attr, type_attr, amt_attr) — L5 is stored as level4_* in schema.
    _level_comm_overrides: dict = {}   # level → pre-computed Decimal commission
    for _il, _pa, _ta, _aa in [
        (1, 'level1_pct', 'level1_type', 'level1_amt'),
        (2, 'level2_pct', 'level2_type', 'level2_amt'),
        (3, 'level3_pct', 'level3_type', 'level3_amt'),
        (4, 'level4_core_pct', 'level4_core_type', 'level4_core_amt'),  # L4 Core
        (5, 'level4_pct',      'level4_type',      'level4_amt'),       # L5 Support
    ]:
        if str(getattr(cfg, _ta, 'PCT') or 'PCT') == 'AMOUNT':
            _flat = Decimal(str(getattr(cfg, _aa, 0) or 0))
            if _flat > 0:
                _level_comm_overrides[_il] = _flat.quantize(Decimal('0.01'))

    # L6 SHOWROOM — same AMOUNT-type override pattern for the showroom partner
    if _showroom_p and (_showroom_pct > 0 or (_showroom_type == 'AMOUNT' and _showroom_amt > 0)):
        if _showroom_type == 'AMOUNT' and _showroom_amt > 0:
            levels_map[6] = (_showroom_p, Decimal('0'))          # pct placeholder
        else:
            levels_map[6] = (_showroom_p, _showroom_pct)

    # DC-CHAIN-DEDUP-001: Deduplicate partners in chain map so lower levels (L5/L6)
    # do not grant double commissions to a partner already assigned at L1/L2.
    _chain_seen_pids: set = set()
    _deduped_levels_map: dict = {}
    for _cl, (_cp, _cpct) in levels_map.items():
        if _cp is None:
            continue
        if _cp.id in _chain_seen_pids:
            pass
        else:
            _chain_seen_pids.add(_cp.id)
            _deduped_levels_map[_cl] = (_cp, _cpct)
    levels_map = _deduped_levels_map

    created = 0
    for level, (partner, pct) in levels_map.items():
        if not partner or (pct <= 0 and level not in _level_comm_overrides):
            continue

        # DC-DEDUP-LEVEL-001 (Jun 2026): When a partner is reassigned, cancel any DRAFT
        # entries for the same (lead, level) but a DIFFERENT partner before creating the
        # new entry. This prevents orphan DRAFTs accumulating on every re-assignment.
        # Only DRAFT status is auto-cancelled — PENDING/STAGE1_APPROVED/PAID are not touched.
        _orphans = db.query(VGKCashIncomeEntry).filter(
            VGKCashIncomeEntry.company_id     == company_id,
            VGKCashIncomeEntry.source_lead_id == lead.id,
            VGKCashIncomeEntry.level          == level,
            VGKCashIncomeEntry.partner_id     != partner.id,
            VGKCashIncomeEntry.status         == 'DRAFT',
        ).all()
        for _orph in _orphans:
            _orph.status = 'CANCELLED'
            if hasattr(_orph, 'updated_at'):
                _orph.updated_at = _get_ist()
            logger.info(f'[VGK-CI] DC-DEDUP-LEVEL-001: Lead {lead.id} L{level} orphan '
                        f'{_orph.entry_number} (partner {_orph.partner_id}) → CANCELLED')

        # DC-CANCEL-REGEN-001 (Jun 2026): Exclude CANCELLED entries from idempotency check.
        # A CANCELLED entry must not block regeneration — it is historical/voided.
        # Without this filter the retrigger silently skips any level that was ever cancelled.
        # DC-ADV-IDEM-001 (Jul 2026): Exclude ADVANCE entries from idempotency check.
        # An ADVANCE mirror entry (kind='ADVANCE') is a pre-payment, not the final commission.
        # It must NOT block creation of the COMMISSION entry for the same level — the partner
        # is entitled to both: the advance (already paid) and the remaining commission on
        # the full deal value. Without this exclusion, any level with an advance mirror never
        # receives a commission entry, silently losing the bulk of their payout.
        exists = db.query(VGKCashIncomeEntry).filter(
            VGKCashIncomeEntry.company_id     == company_id,
            VGKCashIncomeEntry.source_lead_id == lead.id,
            VGKCashIncomeEntry.partner_id     == partner.id,
            VGKCashIncomeEntry.level          == level,
            VGKCashIncomeEntry.status         != 'CANCELLED',
            VGKCashIncomeEntry.kind           != 'ADVANCE',
        ).first()
        if exists:
            logger.info(f'[VGK-CI] Lead {lead.id} L{level} entry already exists (kind={exists.kind}, status={exists.status}) — skipping')
            continue

        commission = _level_comm_overrides.get(level) or _calc_comm(commission_base, pct, 'PCT', Decimal('0'))
        # Flush before generating the next entry_number so the sequence counter
        # reflects any previously-added entries in this same batch.
        db.flush()
        entry = VGKCashIncomeEntry(
            company_id            = company_id,
            entry_number          = _next_entry_number(db, company_id),
            partner_id            = partner.id,
            source_lead_id        = lead.id,
            category_id           = category_id,
            level                 = level,
            income_date           = getattr(lead, 'income_date', None) or _get_ist().date(),
            deal_value_total      = deal_total,
            deal_value_excl_tax   = deal_ex_tax,
            confirmed_final_value = Decimal(str(_cfv)) if (_cfv is not None) else None,
            solar_value           = Decimal(str(_sv)) if (_sv is not None and _sv > 0) else None,
            commission_pct        = pct,
            commission_amount     = commission,
            points_debit_required = commission,
            points_actually_debited = Decimal('0'),
            status                = 'DRAFT',
        )
        db.add(entry)
        db.flush()  # get entry.id for wallet/points log reference

        # DC-VGK-FLOW-001: Credit wallet + points immediately on DRAFT creation so
        # the member sees earned income before staff confirms.
        _now_d = _get_ist()
        _wb_d = partner.vgk_cash_wallet or Decimal('0')
        _wa_d = _wb_d + commission
        partner.vgk_cash_wallet = _wa_d
        partner.updated_at = _now_d
        _log_wallet_txn(
            db, partner.id, company_id,
            txn_type='INCOME_CREDIT', direction='CR', amount=commission,
            wallet_before=_wb_d, wallet_after=_wa_d,
            ref_type='VGK_CASH_INCOME', ref_id=entry.id,
            description=f'Income credited (DRAFT) — {entry.entry_number}',
            staff_id=None,
        )
        # DC-VGK-PTS-RULE-001: Points are NEVER credited for income events.
        # Points credit sources: signup, referral code, promo code, admin manual only.
        # Points debit happens ONLY at mark_paid_cash_income (PAID stage), 90% of net payout.

        created += 1
        logger.info(f'[VGK-CI] DRAFT created+credited: lead={lead.id} L{level} partner={partner.partner_code} ₹{float(commission)}')

    # DC-EXTRA-COMM-001: fire 'file_completed' extra commission for all configured levels.
    # Runs here (after all DRAFT entries created) so the trigger is always executed once per
    # lead completion regardless of how many commission levels were generated.
    try:
        from app.services.vgk_extra_commission import apply_extra_commission_if_active as _ec_completed
        _ec_completed(db, lead, 'file_completed')
    except Exception as _ec_e:
        logger.warning(f'[DC-EXTRA-COMM-001] file_completed non-fatal lead={lead.id}: {_ec_e}')

    # DC-AWARD-TRIGGER-001: fire 'file_completed' award/gift trigger for configured levels.
    try:
        from app.services.vgk_award_trigger import apply_award_gift_trigger_if_active as _at_completed
        _at_completed(db, lead, 'file_completed')
    except Exception as _at_e:
        logger.warning(f'[DC-AWARD-TRIGGER-001] file_completed non-fatal lead={lead.id}: {_at_e}')

    # DC-EC-PER-LEVEL-TRIGGER-001: fire 'file_completed' cash/bonus trigger for configured levels.
    try:
        from app.services.vgk_cash_bonus_trigger import apply_cash_bonus_trigger_if_active as _cb_completed
        _cb_completed(db, lead, 'file_completed')
    except Exception as _cb_e:
        logger.warning(f'[DC-CB-TRIGGER-001] file_completed non-fatal lead={lead.id}: {_cb_e}')

    return created


def confirm_cash_income(db: Session, entry_id: int, company_id: int, confirmed_by_id: int, notes: str = None) -> dict:
    """
    Sales staff confirms a DRAFT entry.
    DC-VGK-FLOW-001: Wallet + points are credited at DRAFT creation.
    Confirm is a status-only promotion — no wallet / points movement here.
    Status → PENDING.
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner

    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
        VGKCashIncomeEntry.company_id == company_id,
        VGKCashIncomeEntry.status == 'DRAFT',
    ).with_for_update().first()

    if not entry:
        return {'success': False, 'error': 'Entry not found or not in DRAFT status'}

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == entry.partner_id
    ).with_for_update().first()

    if not partner:
        return {'success': False, 'error': 'Partner not found'}

    now = _get_ist()
    commission = entry.commission_amount or Decimal('0')

    entry.points_actually_debited = Decimal('0')
    entry.status           = 'PENDING'
    entry.confirmed_by_id  = confirmed_by_id
    entry.confirmed_at     = now
    if notes:
        entry.notes = notes
    entry.updated_at = now

    # DC-VGK-NO-AUTO-JV-001: Auto JV posting removed — all entries are manual via SFMS Entries page.

    return {
        'success': True,
        'entry_number': entry.entry_number,
        'commission_amount': float(commission),
        'points_debited': 0,
        'points_waived': 0,
        'new_cash_wallet': float(partner.vgk_cash_wallet or Decimal('0')),
    }


def reject_cash_income(db: Session, entry_id: int, company_id: int, rejected_by_id: int, reason: str = None) -> dict:
    """Sales staff rejects a DRAFT entry — no points/money movement."""
    from app.models.vgk_cash_income import VGKCashIncomeEntry

    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
        VGKCashIncomeEntry.company_id == company_id,
        VGKCashIncomeEntry.status == 'DRAFT',
    ).with_for_update().first()

    if not entry:
        return {'success': False, 'error': 'Entry not found or not in DRAFT status'}

    now = _get_ist()
    entry.status           = 'CANCELLED'
    entry.confirmed_by_id  = rejected_by_id
    entry.confirmed_at     = now
    entry.rejection_reason = reason or 'Rejected by sales staff'
    entry.updated_at       = now

    return {'success': True, 'entry_number': entry.entry_number}


def release_cash_income(db: Session, entry_id: int, company_id: int, released_by_id: int, notes: str = None) -> dict:
    """
    Accounts staff releases a PENDING entry.
    Deducts 8% admin + 2% TDS from commission_amount.
    Net payout goes to partner's vgk_cash_wallet as final withdrawable credit.
    (wallet already has gross credited at confirmation — we subtract charges now)
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner

    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
        VGKCashIncomeEntry.company_id == company_id,
        VGKCashIncomeEntry.status == 'PENDING',
    ).with_for_update().first()

    if not entry:
        return {'success': False, 'error': 'Entry not found or not in PENDING status'}

    # DC-SOLAR-RELEASE-GATE-001 (Jul 2026): Final COMMISSION entries for solar leads
    # must only be released once solar_pipeline_status = 'completed'.
    # ADVANCE / DVR_ADVANCE / BRAND_ADVANCE / SLAB_BONUS / ADJUSTMENT kinds are
    # exempt — they follow their own release rules.
    _ADVANCE_KINDS = {'ADVANCE', 'DVR_ADVANCE', 'BRAND_ADVANCE', 'SLAB_BONUS', 'ADJUSTMENT'}
    if (entry.kind or 'COMMISSION') not in _ADVANCE_KINDS and entry.source_lead_id:
        _lead_row = db.execute(
            text("SELECT category_id, solar_pipeline_status FROM crm_leads WHERE id=:lid"),
            {'lid': entry.source_lead_id}
        ).fetchone()
        if _lead_row and (_lead_row.category_id or 0) == 6:
            _sps_rel = (_lead_row.solar_pipeline_status or '').lower()
            if _sps_rel not in ('subsidy_pending', 'completed'):
                _stage_label = _sps_rel.replace('_', ' ').title() if _sps_rel else 'Not Set'
                return {
                    'success': False,
                    'error': (
                        f'Solar final commission can only be released after the lead reaches '
                        f'"Subsidy Pending" or "Completed" stage. Current stage: {_stage_label}.'
                    ),
                }

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == entry.partner_id
    ).with_for_update().first()

    if not partner:
        return {'success': False, 'error': 'Partner not found'}

    gross   = entry.commission_amount or Decimal('0')
    admin   = (gross * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01'))
    payable = gross - admin
    # DC-FIX-2605-007: TDS must be on payable (=gross−admin), matching post_jv_paid.
    # Using gross*2% caused a systematic discrepancy (e.g. ₹150 vs ₹138 on ₹7500 entries).
    tds     = (payable * TDS_PCT / Decimal('100')).quantize(Decimal('0.01'))
    net     = payable - tds
    deductions = admin + tds

    # DC-VGK-FLOW-002: Points debit DEFERRED to mark_paid_cash_income (PAID stage).
    # Do NOT debit points here (Stage 1 Approve = AWAITING RELEASE, not yet physically paid).
    # points_actually_debited stays 0 so mark_paid_cash_income knows to do the debit.
    entry.points_actually_debited = Decimal('0')

    wallet_before = partner.vgk_cash_wallet or Decimal('0')
    wallet_after  = max(Decimal('0'), wallet_before - deductions)
    partner.vgk_cash_wallet = wallet_after

    earned_before = getattr(partner, 'vgk_cash_earned_total', None) or Decimal('0')
    # DC-VGK-FLOW-001: record GROSS earned (not net) so member sees full commission earned.
    partner.vgk_cash_earned_total = earned_before + gross

    now = _get_ist()
    entry.admin_charges   = admin
    entry.tds_amount      = tds
    entry.net_payout      = net
    entry.status          = 'RELEASED'
    entry.released_by_id  = released_by_id
    entry.released_at     = now
    if notes:
        entry.notes = (entry.notes or '') + f' | Release note: {notes}'
    entry.updated_at = now
    partner.updated_at = now

    _log_wallet_txn(
        db, partner.id, partner.company_id,
        txn_type='INCOME_DEDUCTION', direction='DR', amount=deductions,
        wallet_before=wallet_before, wallet_after=wallet_after,
        ref_type='VGK_CASH_INCOME', ref_id=entry.id,
        description=f'Admin {float(admin):.2f} + TDS {float(tds):.2f} deducted — {entry.entry_number}',
        staff_id=released_by_id,
    )

    # DC-VGK-NO-AUTO-JV-001: Auto JV posting removed — all entries are manual via SFMS Entries page.

    return {
        'success':          True,
        'entry_number':     entry.entry_number,
        'gross':            float(gross),
        'admin_charges':    float(admin),
        'tds_amount':       float(tds),
        'net_payout':       float(net),
        'new_wallet':       float(wallet_after),
        'earned_total':     float(partner.vgk_cash_earned_total),
    }


# ────────────────────────────────────────────────────────────────────────────
# Wallet helper — log every transaction
# ────────────────────────────────────────────────────────────────────────────

def _log_wallet_txn(
    db: Session,
    partner_id: int,
    company_id: int,
    txn_type: str,
    direction: str,
    amount: Decimal,
    wallet_before: Decimal,
    wallet_after: Decimal,
    ref_type: str = None,
    ref_id: int = None,
    description: str = None,
    staff_id: int = None,
):
    """Insert a single row into vgk_wallet_transactions (non-fatal if fails)."""
    try:
        from app.models.vgk_wallet_transaction import VGKWalletTransaction
        txn = VGKWalletTransaction(
            company_id=company_id,
            partner_id=partner_id,
            txn_type=txn_type,
            direction=direction,
            amount=amount,
            wallet_before=wallet_before,
            wallet_after=wallet_after,
            ref_type=ref_type,
            ref_id=ref_id,
            description=description,
            initiated_by_staff_id=staff_id,
            created_at=_get_ist(),
        )
        db.add(txn)
        db.flush()
    except Exception as _e:
        logger.warning(f'[VGK-WALLET] Txn log failed (non-fatal): {_e}')


# ────────────────────────────────────────────────────────────────────────────
# Wallet Debit — member uses balance for VGK service / vendor purchase
# ────────────────────────────────────────────────────────────────────────────

def debit_wallet_for_service(
    db: Session,
    partner_id: int,
    company_id: int,
    amount: Decimal,
    txn_type: str,
    description: str,
    ref_type: str = None,
    ref_id: int = None,
    staff_id: int = None,
) -> dict:
    """
    Debit a member's wallet for a VGK service or vendor purchase.
    txn_type: 'SERVICE_DEBIT' or 'VENDOR_DEBIT'
    Returns success=False if wallet has insufficient balance.
    """
    from app.models.staff_accounts import OfficialPartner

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == partner_id,
        OfficialPartner.company_id == company_id,
    ).with_for_update().first()

    if not partner:
        return {'success': False, 'error': 'Partner not found'}

    amount = Decimal(str(amount))
    if amount <= 0:
        return {'success': False, 'error': 'Amount must be positive'}

    wallet_before = partner.vgk_cash_wallet or Decimal('0')
    if wallet_before < amount:
        return {
            'success': False,
            'error': f'Insufficient wallet balance. Available: ₹{float(wallet_before):.2f}, Requested: ₹{float(amount):.2f}',
            'wallet_balance': float(wallet_before),
        }

    wallet_after = wallet_before - amount
    partner.vgk_cash_wallet = wallet_after
    partner.updated_at = _get_ist()

    _log_wallet_txn(
        db, partner_id, company_id,
        txn_type=txn_type, direction='DR', amount=amount,
        wallet_before=wallet_before, wallet_after=wallet_after,
        ref_type=ref_type, ref_id=ref_id,
        description=description,
        staff_id=staff_id,
    )

    return {
        'success':        True,
        'amount_debited': float(amount),
        'wallet_before':  float(wallet_before),
        'wallet_after':   float(wallet_after),
    }


# ────────────────────────────────────────────────────────────────────────────
# Wallet Withdrawal — staff initiates payout for a member
# ────────────────────────────────────────────────────────────────────────────

def initiate_wallet_withdrawal(
    db: Session,
    partner_id: int,
    company_id: int,
    amount: Decimal,
    staff_id: int,
    notes: str = None,
) -> dict:
    """
    Staff initiates a cash withdrawal from a member's wallet.
    Debits wallet immediately; actual fund transfer happens offline.
    Returns insufficient-balance error if wallet is low.
    """
    from app.models.staff_accounts import OfficialPartner

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == partner_id,
        OfficialPartner.company_id == company_id,
    ).with_for_update().first()

    if not partner:
        return {'success': False, 'error': 'Partner not found'}

    amount = Decimal(str(amount))
    if amount <= 0:
        return {'success': False, 'error': 'Withdrawal amount must be positive'}

    wallet_before = partner.vgk_cash_wallet or Decimal('0')
    if wallet_before < amount:
        return {
            'success': False,
            'error': f'Insufficient wallet balance. Available: ₹{float(wallet_before):.2f}, Requested: ₹{float(amount):.2f}',
            'wallet_balance': float(wallet_before),
        }

    wallet_after = wallet_before - amount
    partner.vgk_cash_wallet = wallet_after
    partner.updated_at = _get_ist()

    desc = f'Withdrawal initiated by staff — ₹{float(amount):.2f}'
    if notes:
        desc += f' | Notes: {notes}'

    _log_wallet_txn(
        db, partner_id, company_id,
        txn_type='WITHDRAWAL', direction='DR', amount=amount,
        wallet_before=wallet_before, wallet_after=wallet_after,
        ref_type='WITHDRAWAL', ref_id=None,
        description=desc,
        staff_id=staff_id,
    )

    return {
        'success':       True,
        'amount':        float(amount),
        'wallet_before': float(wallet_before),
        'wallet_after':  float(wallet_after),
        'partner_name':  partner.partner_name,
        'partner_code':  partner.partner_code,
    }


# ════════════════════════════════════════════════════════════════════════════
# DC-VGK-INCOME-UNIFIED-001 (May 2026): Unified state machine + JV postings
# ════════════════════════════════════════════════════════════════════════════
#
# State machine: DRAFT → PENDING → RELEASED → PAID
#                Reject (any forward stage) → CANCELLED (with reversal JVs)
#
# Skip-level (EA / MR10001 / VGK4U_SUPREME): one-click any forward jump.
#
# JV postings (idempotent on voucher_number):
#
#   B (Sales Confirm) — SAME-COMPANY:
#       Dr Commission Expense / Cr Admin Charges Recovery + Cr Commission Payable to Members
#
#   B (Sales Confirm) — CROSS-COMPANY (marketing support structure, CGST+SGST 9%+9%):
#     JV-B1 in product company:
#       Dr Commission Expense + Dr CGST Input + Dr SGST Input
#       Cr Admin Charges Recovery + Cr Marketing Support Payable — <member_co>
#     JV-B2 in member company:
#       Dr Marketing Support Receivable — <product_co>
#       Cr CGST Output + Cr SGST Output + Cr TDS Payable + Cr Commission Payable to Members
#
#   C (Accounts Release): Dr Commission Payable / Cr Commission Advance  (advance knock-off only)
#   D (Mark Paid) — SAME-COMPANY:
#       Dr Commission Payable / Cr TDS Payable + Cr Bank|Cash  (in product company)
#   D (Mark Paid) — CROSS-COMPANY:
#       Dr Commission Payable / Cr Bank|Cash                   (in member company; TDS from B2)
#   A (Solar Advance): Dr Commission Advance / Cr Admin + Cr TDS + Cr Bank
#   F (Reject reversal): sign-flipped of ALL prior JVs on this entry (both companies)
#
# Wallet behaviour unchanged. Ledger always posted in parallel.

SUPER_STAFF_TYPES = {'VGK4U', 'VGK4U Supreme', 'VGK4U_EA', 'VGK4U_SUPREME'}
SUPER_EMP_CODES   = {'MR10001'}


def is_super_skip_user(staff) -> bool:
    """Return True if staff can skip-jump any income state in one click."""
    if not staff:
        return False
    st = (getattr(staff, 'staff_type', '') or '').strip()
    ec = (getattr(staff, 'emp_code', '') or '').strip()
    return st in SUPER_STAFF_TYPES or ec in SUPER_EMP_CODES


def _next_voucher_number(db: Session, company_id: int) -> str:
    """Generate next JV number per company per month: <CO>/JV/YYYYMM/NNNN"""
    from app.models.staff_accounts import AssociatedCompany
    co = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
    code = (getattr(co, 'company_code', None) or f'CO{company_id}').strip().upper()[:6]
    now = _get_ist()
    yyyymm = now.strftime('%Y%m')
    prefix = f'{code}/JV/{yyyymm}/'
    last = db.execute(text(
        "SELECT voucher_number FROM journal_vouchers WHERE voucher_number LIKE :pfx "
        "ORDER BY voucher_number DESC LIMIT 1"
    ), {'pfx': f'{prefix}%'}).scalar()
    seq = 1
    if last:
        try:
            seq = int(last.split('/')[-1]) + 1
        except Exception:
            seq = 1
    return f'{prefix}{seq:04d}'


def _ledger_master_id(db: Session, company_id: int, account_type: str, account_name: str):
    """Look up ledger master id; returns None if not found."""
    row = db.execute(text(
        "SELECT id FROM account_ledger_masters "
        "WHERE company_id=:cid AND account_type=:t AND account_name=:n"
    ), {'cid': company_id, 't': account_type, 'n': account_name}).fetchone()
    return row.id if row else None


def _company_name(db: Session, company_id: int) -> str:
    """Return the display name for a company id (e.g. 'MyntReal LLP')."""
    row = db.execute(text(
        "SELECT company_name FROM associated_companies WHERE id=:cid"
    ), {'cid': company_id}).fetchone()
    return (row.company_name if row else None) or f'Company#{company_id}'


def _ensure_marketing_support_ledgers(db: Session, product_co_id: int, member_co_id: int):
    """
    Idempotently create Marketing Support Payable / Receivable ledger masters for
    cross-company commission routing (marketing support structure, CGST+SGST applicable).

      Product company (e.g. MyntReal)  → LIABILITY 'Marketing Support Payable — <member_co>'
      Member  company (e.g. Zynova)    → ASSET     'Marketing Support Receivable — <product_co>'
    """
    member_name  = _company_name(db, member_co_id)
    product_name = _company_name(db, product_co_id)

    db.execute(text("""
        INSERT INTO account_ledger_masters
          (company_id, account_type, account_name, account_code, parent_group,
           description, is_active, created_at, updated_at)
        VALUES
          (:cid, 'LIABILITY', :name, :code,
           'Current Liabilities/Provisions',
           :desc, TRUE, NOW(), NOW())
        ON CONFLICT (company_id, account_type, account_name) DO NOTHING
    """), {
        'cid':  product_co_id,
        'name': f'Marketing Support Payable \u2014 {member_name}',
        'code': f'MSP-{member_co_id}',
        'desc': f'Marketing support fee payable to {member_name} (VGK commission channel)',
    })

    db.execute(text("""
        INSERT INTO account_ledger_masters
          (company_id, account_type, account_name, account_code, parent_group,
           description, is_active, created_at, updated_at)
        VALUES
          (:cid, 'ASSET', :name, :code,
           'Current Assets/Loans & Advances (Asset)',
           :desc, TRUE, NOW(), NOW())
        ON CONFLICT (company_id, account_type, account_name) DO NOTHING
    """), {
        'cid':  member_co_id,
        'name': f'Marketing Support Receivable \u2014 {product_name}',
        'code': f'MSR-{product_co_id}',
        'desc': f'Marketing support fee receivable from {product_name} (VGK commission channel)',
    })
    logger.info(
        f'[VGK-JV] Mktg-support ledgers ensured: '
        f'co#{product_co_id}\u2192Payable / co#{member_co_id}\u2190Receivable'
    )


def _mirror_tds_payable(db: Session, entry, tds: Decimal, paid_by_id: int, company_id: int):
    """
    G5: Mirror TDS withheld at mark-paid into tds_payable for quarterly government returns.
    Upserts into the current financial-quarter row (or creates one).
    Uses a SAVEPOINT so failure never aborts the caller's transaction.
    """
    try:
        db.execute(text("SAVEPOINT sp_tds"))
        from datetime import date
        today = _get_ist().date()
        m, y = today.month, today.year
        if m in (4, 5, 6):
            ps, pe = date(y, 4, 1),  date(y, 6, 30)
        elif m in (7, 8, 9):
            ps, pe = date(y, 7, 1),  date(y, 9, 30)
        elif m in (10, 11, 12):
            ps, pe = date(y, 10, 1), date(y, 12, 31)
        else:
            ps, pe = date(y, 1, 1),  date(y, 3, 31)

        existing = db.execute(text(
            "SELECT id, tds_amount, pending_amount FROM tds_payable "
            "WHERE period_start=:ps AND period_end=:pe AND is_active=TRUE "
            "ORDER BY id ASC LIMIT 1 FOR UPDATE"
        ), {'ps': ps, 'pe': pe}).fetchone()

        if existing:
            new_total   = Decimal(str(existing.tds_amount))    + tds
            new_pending = Decimal(str(existing.pending_amount)) + tds
            db.execute(text(
                "UPDATE tds_payable "
                "SET tds_amount=:ta, pending_amount=:pa, updated_at=NOW() WHERE id=:id"
            ), {'ta': float(new_total), 'pa': float(new_pending), 'id': existing.id})
        else:
            db.execute(text("""
                INSERT INTO tds_payable
                  (tds_amount, paid_amount, pending_amount, payment_status,
                   period_start, period_end, generated_date, updated_at, is_active,
                   updated_by, user_id)
                VALUES
                  (:ta, 0, :pa, 'pending',
                   :ps, :pe, NOW(), NOW(), TRUE,
                   :ub, :uid)
            """), {
                'ta': float(tds), 'pa': float(tds),
                'ps': ps, 'pe': pe,
                'ub':  str(paid_by_id)[:12],
                'uid': f'VCI-{entry.entry_number}'[:12],
            })
        db.execute(text("RELEASE SAVEPOINT sp_tds"))
        logger.info(
            f'[VGK-TDS] Mirrored TDS \u20b9{float(tds):.2f} '
            f'for {entry.entry_number} \u2192 tds_payable {ps}/{pe}'
        )
    except Exception as e:
        try:
            db.execute(text("ROLLBACK TO SAVEPOINT sp_tds"))
        except Exception:
            pass
        logger.warning(f'[VGK-TDS] tds_payable mirror failed (non-fatal): {e}')


def ensure_bank_ledger_master(db: Session, company_id: int, bank_account_id: int) -> dict:
    """
    Ensure an account_ledger_masters row exists for a given company_bank_accounts row.
    Returns {id, account_type, account_name}.
    """
    bk = db.execute(text(
        "SELECT id, bank_name, branch, account_number, ifsc_code "
        "FROM company_bank_accounts WHERE id=:id AND company_id=:cid AND is_active=TRUE"
    ), {'id': bank_account_id, 'cid': company_id}).fetchone()
    if not bk:
        raise ValueError(f'Bank account {bank_account_id} not found for company {company_id}')

    masked = (bk.account_number or '')[-4:] if bk.account_number else ''
    name = f'Bank A/c — {bk.bank_name}{(" ····" + masked) if masked else ""}'

    existing = _ledger_master_id(db, company_id, 'BANK', name)
    if existing:
        return {'id': existing, 'account_type': 'BANK', 'account_name': name}

    res = db.execute(text("""
        INSERT INTO account_ledger_masters
          (company_id, account_type, account_name, account_code, parent_group,
           description, bank_name, account_number, ifsc_code,
           opening_balance, opening_balance_type,
           is_active, created_at, updated_at)
        VALUES
          (:cid, 'BANK', :name, :code, 'Current Assets/Bank Accounts',
           'Auto-created from company_bank_accounts', :bn, :an, :ifsc,
           0, 'DEBIT',
           TRUE, NOW(), NOW())
        ON CONFLICT (company_id, account_type, account_name) DO UPDATE SET updated_at = NOW()
        RETURNING id
    """), {
        'cid': company_id, 'name': name,
        'code': f'BANK-{bk.id}',
        'bn': bk.bank_name, 'an': bk.account_number, 'ifsc': bk.ifsc_code,
    }).fetchone()
    return {'id': res.id, 'account_type': 'BANK', 'account_name': name}


def ensure_cash_ledger_master(db: Session, company_id: int, staff_id: int) -> dict:
    """
    Ensure an account_ledger_masters row exists for a staff cash float.
    Mirrors employee_fund_ledger.employee_id 1:1.
    Returns {id, account_type, account_name}.
    """
    from app.models.staff import StaffEmployee
    s = db.query(StaffEmployee).filter(StaffEmployee.id == staff_id).first()
    if not s:
        raise ValueError(f'Staff {staff_id} not found')
    full_name = (getattr(s, 'full_name', None)
                 or f"{getattr(s,'first_name','') or ''} {getattr(s,'last_name','') or ''}".strip()
                 or s.emp_code or f'Staff#{s.id}')
    name = f'Cash A/c — {full_name} ({s.emp_code or s.id})'

    existing = _ledger_master_id(db, company_id, 'CASH', name)
    if existing:
        return {'id': existing, 'account_type': 'CASH', 'account_name': name}

    res = db.execute(text("""
        INSERT INTO account_ledger_masters
          (company_id, account_type, account_name, account_code, parent_group,
           description, opening_balance, opening_balance_type,
           is_active, created_at, updated_at)
        VALUES
          (:cid, 'CASH', :name, :code, 'Current Assets/Cash-in-hand',
           'Auto-created for staff cash float', 0, 'DEBIT',
           TRUE, NOW(), NOW())
        ON CONFLICT (company_id, account_type, account_name) DO UPDATE SET updated_at = NOW()
        RETURNING id
    """), {
        'cid': company_id, 'name': name, 'code': f'CASH-EMP-{s.id}',
    }).fetchone()
    return {'id': res.id, 'account_type': 'CASH', 'account_name': name}


def _post_jv_lines(
    db: Session,
    company_id: int,
    voucher_number: str,
    voucher_date,
    voucher_type: str,
    legs: list,                 # [{type, name, dr, cr, particulars}]
    narration: str,
    reference_type: str,
    reference_id: int,
    party_type: str = None,
    party_name: str = None,
    party_id: int = None,
    payment_mode: str = None,
    reference_number: str = None,
    created_by_id: int = None,
):
    """
    Post a multi-leg journal voucher. Idempotent: if a JV with this voucher_number
    already exists, returns its id without duplicating lines.

    Each leg posts:
      - 1 row in journal_vouchers (Dr×Cr pair: leg vs first non-matching counter-leg)
        but to keep the existing single Dr/Cr schema, we post N journal_voucher rows
        sharing the same voucher_number (one per leg), with Dr=this-leg / Cr='Suspense'
        is NOT used. Instead we encode the multi-leg as N rows where each Dr line is
        paired with each Cr line proportionally — to stay schema-compatible we post
        ONE journal_vouchers header row (largest leg) + all legs go into account_ledger.

    Simpler scheme (in line with existing code in the codebase): we insert ONE row
    into journal_vouchers (representing the dominant Dr→Cr summary) AND post each
    leg as its own row in account_ledger keyed off the voucher_number. This matches
    how multi-leg JVs are already posted by the contra entry / journal voucher endpoints.
    """
    # Idempotency: skip if already posted under this voucher_number for this ref
    existing = db.execute(text(
        "SELECT id FROM journal_vouchers WHERE voucher_number=:vn"
    ), {'vn': voucher_number}).fetchone()
    if existing:
        logger.info(f'[VGK-JV] voucher {voucher_number} already exists — idempotent skip')
        return existing.id

    # Choose primary Dr (largest debit leg) and primary Cr (largest credit leg) for the header
    drs = [l for l in legs if (l.get('dr') or 0) > 0]
    crs = [l for l in legs if (l.get('cr') or 0) > 0]
    if not drs or not crs:
        raise ValueError('JV legs must contain at least one debit and one credit')
    primary_dr = max(drs, key=lambda l: l['dr'])
    primary_cr = max(crs, key=lambda l: l['cr'])
    total_amt  = sum(Decimal(str(l.get('dr') or 0)) for l in legs)

    jv_res = db.execute(text("""
        INSERT INTO journal_vouchers
          (company_id, voucher_number, voucher_date, voucher_type,
           dr_account_type, dr_account_name, cr_account_type, cr_account_name,
           party_type, party_name, party_id, amount, narration,
           payment_mode, reference_number, status, created_by_id, created_at, updated_at)
        VALUES
          (:cid, :vn, :vd, :vt,
           :drt, :drn, :crt, :crn,
           :pt, :pn, :pid, :amt, :narr,
           :pm, :rn, 'POSTED', :cb, NOW(), NOW())
        RETURNING id
    """), {
        'cid': company_id, 'vn': voucher_number, 'vd': voucher_date, 'vt': voucher_type,
        'drt': primary_dr['type'], 'drn': primary_dr['name'],
        'crt': primary_cr['type'], 'crn': primary_cr['name'],
        'pt': party_type, 'pn': party_name, 'pid': party_id,
        'amt': float(total_amt), 'narr': narration,
        'pm': payment_mode, 'rn': reference_number, 'cb': created_by_id,
    }).fetchone()
    jv_id = jv_res.id

    # Post each leg into account_ledger with the same voucher_number
    for leg in legs:
        dr = Decimal(str(leg.get('dr') or 0))
        cr = Decimal(str(leg.get('cr') or 0))
        if dr == 0 and cr == 0:
            continue
        entry_type = 'DEBIT' if dr > 0 else 'CREDIT'
        amount     = dr if dr > 0 else cr
        db.execute(text("""
            INSERT INTO account_ledger
              (company_id, account_type, account_name, transaction_date, entry_type,
               reference_type, reference_id, reference_number,
               debit_amount, credit_amount, running_balance,
               narration, voucher_type, particulars, created_by_id, created_at, updated_at)
            VALUES
              (:cid, :at, :an, :td, :et,
               :rt, :rid, :rn,
               :dr, :cr, 0,
               :narr, :vt, :prt, :cb, NOW(), NOW())
        """), {
            'cid': company_id,
            'at': leg['type'], 'an': leg['name'], 'td': voucher_date, 'et': entry_type,
            'rt': reference_type, 'rid': reference_id, 'rn': voucher_number,
            'dr': float(dr), 'cr': float(cr),
            'narr': narration, 'vt': voucher_type,
            'prt': leg.get('particulars') or narration,
            'cb': created_by_id,
        })

    logger.info(f'[VGK-JV] posted {voucher_number} ({len(legs)} legs, ₹{float(total_amt):.2f}) for {reference_type}#{reference_id}')
    return jv_id


def _vci_party_info(db: Session, entry):
    """Return (party_type, party_name, party_id) for an income entry."""
    from app.models.staff_accounts import OfficialPartner
    p = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()
    if p:
        return ('VGK_MEMBER', p.partner_name or p.partner_code, p.id)
    return (None, None, None)


def post_jv_confirm(db: Session, entry, created_by_id: int):
    """
    JV-B: Sales confirm.

    Same-company:
        Dr Commission Expense
        Cr Admin Charges Recovery + Cr Commission Payable to Members

    Cross-company (marketing support structure, CGST+SGST 9%+9%):
      JV-B1 in product company (e.g. MyntReal):
        Dr Commission Expense + Dr CGST Input + Dr SGST Input
        Cr Admin Charges Recovery + Cr Marketing Support Payable — <member_co>
      JV-B2 in member company (e.g. Zynova/MNR):
        Dr Marketing Support Receivable — <product_co>
        Cr CGST Output + Cr SGST Output
        Cr TDS Payable on Member Commission + Cr Commission Payable to Members
    """
    if entry.kind == 'ADVANCE':
        return None

    from app.models.staff_accounts import OfficialPartner
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()

    product_co_id = entry.company_id
    member_co_id  = partner.company_id if partner else product_co_id
    cross_company = (member_co_id != product_co_id)

    gross       = Decimal(str(entry.commission_amount or 0))
    admin       = (gross * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01'))
    mkt_support = gross - admin   # net marketing support fee flowing to member company

    party_type, party_name, party_id = _vci_party_info(db, entry)

    if not cross_company:
        # ── Same-company JV-B ─────────────────────────────────────────────
        vn = _next_voucher_number(db, product_co_id)
        legs = [
            {'type': 'EXPENSE',   'name': 'Commission Expense',
             'dr': gross,       'cr': 0,
             'particulars': f'Gross commission L{entry.level} {entry.entry_number}'},
            {'type': 'INCOME',    'name': 'Admin Charges Recovery',
             'dr': 0,           'cr': admin,
             'particulars': f'Admin 8% recovered {entry.entry_number}'},
            {'type': 'LIABILITY', 'name': 'Commission Payable to Members',
             'dr': 0,           'cr': mkt_support,
             'particulars': f'Payable to {party_name or party_id} {entry.entry_number}'},
        ]
        return _post_jv_lines(
            db, product_co_id, vn, _get_ist().date(), 'JOURNAL', legs,
            narration=(
                f'Sales-Confirm {entry.entry_number} '
                f'gross \u20b9{float(gross):.2f} admin \u20b9{float(admin):.2f}'
            ),
            reference_type='VGK_CASH_INCOME', reference_id=entry.id,
            party_type=party_type, party_name=party_name, party_id=party_id,
            created_by_id=created_by_id,
        )

    # ── Cross-company: marketing support structure ────────────────────────
    _ensure_marketing_support_ledgers(db, product_co_id, member_co_id)

    product_name = _company_name(db, product_co_id)
    member_name  = _company_name(db, member_co_id)

    cgst                  = (mkt_support * GST_PCT / Decimal('100')).quantize(Decimal('0.01'))
    sgst                  = cgst
    tds_on_commission     = (mkt_support * TDS_PCT / Decimal('100')).quantize(Decimal('0.01'))
    net_payable_to_member = mkt_support - tds_on_commission
    total_to_member_co    = mkt_support + cgst + sgst   # inc. GST payable to member company

    # JV-B1: product company books expense + ITC + payable ────────────────
    vn1 = _next_voucher_number(db, product_co_id)
    legs_b1 = [
        {'type': 'EXPENSE',   'name': 'Commission Expense',
         'dr': gross,              'cr': 0,
         'particulars': f'Gross commission L{entry.level} {entry.entry_number}'},
        {'type': 'ASSET',     'name': 'CGST Input',
         'dr': cgst,               'cr': 0,
         'particulars': f'CGST 9% ITC on mktg support {entry.entry_number}'},
        {'type': 'ASSET',     'name': 'SGST Input',
         'dr': sgst,               'cr': 0,
         'particulars': f'SGST 9% ITC on mktg support {entry.entry_number}'},
        {'type': 'INCOME',    'name': 'Admin Charges Recovery',
         'dr': 0,                  'cr': admin,
         'particulars': f'Admin 8% recovered {entry.entry_number}'},
        {'type': 'LIABILITY', 'name': f'Marketing Support Payable \u2014 {member_name}',
         'dr': 0,                  'cr': total_to_member_co,
         'particulars': f'Mktg support+GST payable to {member_name} {entry.entry_number}'},
    ]
    _post_jv_lines(
        db, product_co_id, vn1, _get_ist().date(), 'JOURNAL', legs_b1,
        narration=(
            f'Sales-Confirm {entry.entry_number} \u2014 mktg support to {member_name} '
            f'\u20b9{float(mkt_support):.2f}+GST \u20b9{float(cgst+sgst):.2f}'
        ),
        reference_type='VGK_CASH_INCOME', reference_id=entry.id,
        party_type=party_type, party_name=party_name, party_id=party_id,
        created_by_id=created_by_id,
    )

    # JV-B2: member company books receivable + GST output + member payable ─
    vn2 = _next_voucher_number(db, member_co_id)
    legs_b2 = [
        {'type': 'ASSET',     'name': f'Marketing Support Receivable \u2014 {product_name}',
         'dr': total_to_member_co, 'cr': 0,
         'particulars': f'Mktg support receivable from {product_name} {entry.entry_number}'},
        {'type': 'LIABILITY', 'name': 'CGST Output',
         'dr': 0,                  'cr': cgst,
         'particulars': f'CGST 9% output {entry.entry_number}'},
        {'type': 'LIABILITY', 'name': 'SGST Output',
         'dr': 0,                  'cr': sgst,
         'particulars': f'SGST 9% output {entry.entry_number}'},
        {'type': 'LIABILITY', 'name': 'TDS Payable on Member Commission',
         'dr': 0,                  'cr': tds_on_commission,
         'particulars': f'TDS 2% on commission {entry.entry_number}'},
        {'type': 'LIABILITY', 'name': 'Commission Payable to Members',
         'dr': 0,                  'cr': net_payable_to_member,
         'particulars': f'Payable to {party_name or party_id} {entry.entry_number}'},
    ]
    return _post_jv_lines(
        db, member_co_id, vn2, _get_ist().date(), 'JOURNAL', legs_b2,
        narration=(
            f'Sales-Confirm mirror {entry.entry_number} \u2014 '
            f'{product_name} mktg support \u20b9{float(mkt_support):.2f}+GST'
        ),
        reference_type='VGK_CASH_INCOME', reference_id=entry.id,
        party_type=party_type, party_name=party_name, party_id=party_id,
        created_by_id=created_by_id,
    )


def post_jv_release(db: Session, entry, released_by_id: int):
    """JV-C: Accounts release / Stage 1 Approve. Knock off any prior advance for same partner+lead, if any."""
    if entry.kind == 'ADVANCE':
        return None

    company_id = entry.company_id
    # DC-NO-RELEASE-001: PENDING/STAGE1_APPROVED/PAID all accepted — RELEASED is legacy.
    # Find an advance for same lead/partner that is still un-knocked
    adv = db.execute(text("""
        SELECT id, commission_amount FROM vgk_cash_income_entries
        WHERE company_id=:cid AND partner_id=:pid AND source_lead_id=:lid
          AND kind='ADVANCE' AND status IN ('PENDING','RELEASED','STAGE1_APPROVED','PAID')
          AND id <> :eid
        ORDER BY id ASC LIMIT 1
    """), {'cid': company_id, 'pid': entry.partner_id, 'lid': entry.source_lead_id, 'eid': entry.id}).fetchone() if entry.source_lead_id else None

    if not adv:
        return None  # no advance to knock off

    amount = Decimal(str(adv.commission_amount or 0))
    if amount <= 0:
        return None

    party_type, party_name, party_id = _vci_party_info(db, entry)
    vn = _next_voucher_number(db, company_id)
    legs = [
        {'type': 'LIABILITY', 'name': 'Commission Payable to Members',  'dr': amount, 'cr': 0,
         'particulars': f'Knock-off advance against {entry.entry_number}'},
        {'type': 'ASSET',     'name': 'Commission Advance to Members',  'dr': 0,      'cr': amount,
         'particulars': f'Advance recovered against advance#{adv.id}'},
    ]
    return _post_jv_lines(
        db, company_id, vn, _get_ist().date(), 'JOURNAL', legs,
        narration=f'Release knock-off ₹{float(amount):.2f} of advance against {entry.entry_number}',
        reference_type='VGK_CASH_INCOME', reference_id=entry.id,
        party_type=party_type, party_name=party_name, party_id=party_id,
        created_by_id=released_by_id,
    )


def post_jv_paid(db: Session, entry, paid_by_id: int, payment_mode: str,
                 bank_ledger_id: int = None, cash_staff_id: int = None,
                 utr: str = None):
    """
    JV-D: Bank/Cash mark paid. Payment always posts in the MEMBER's company.

    Same-company:
        Dr Commission Payable to Members (payable=gross-admin)
        Cr TDS Payable on Member Commission (2%)
        Cr Bank|Cash  (net)

    Cross-company (TDS already booked in JV-B2 at confirm time):
        Dr Commission Payable to Members (net=gross-admin-tds)
        Cr Bank|Cash  (net)

    Also writes employee_fund_ledger if CASH mode, and mirrors TDS to tds_payable.
    """
    from app.models.staff_accounts import OfficialPartner
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()

    product_co_id  = entry.company_id
    member_co_id   = partner.company_id if partner else product_co_id
    cross_company  = (member_co_id != product_co_id)
    # DC-FIX-2605-006: ADVANCE entries are booked in the product company (e.g. MyntReal=4).
    # The advance payment originates from the product company, NOT the member's company
    # (Real Dreams=1). Cross-company ADVANCE: pay_company_id = product company.
    # COMMISSION cross-company: pay from member's company (original rule preserved).
    entry_kind = getattr(entry, 'kind', 'COMMISSION') or 'COMMISSION'
    if cross_company and entry_kind == 'ADVANCE':
        pay_company_id = product_co_id  # advance was booked and funds are in product co
    else:
        pay_company_id = member_co_id   # commission: payment from member's company

    gross   = Decimal(str(entry.commission_amount or 0))
    admin   = Decimal(str(entry.admin_charges   or 0))
    payable = gross - admin
    tds     = (payable * TDS_PCT / Decimal('100')).quantize(Decimal('0.01'))
    net     = payable - tds

    if payment_mode == 'BANK':
        if not bank_ledger_id:
            raise ValueError('bank_ledger_id required for BANK mode')
        bk_row = db.execute(text(
            "SELECT account_type, account_name FROM account_ledger_masters "
            "WHERE id=:id AND company_id=:cid"
        ), {'id': bank_ledger_id, 'cid': pay_company_id}).fetchone()
        if not bk_row:
            # Backward-compat: accept ledger from either company
            bk_row = db.execute(text(
                "SELECT account_type, account_name FROM account_ledger_masters WHERE id=:id"
            ), {'id': bank_ledger_id}).fetchone()
        if not bk_row:
            raise ValueError(f'Bank ledger {bank_ledger_id} not found for company {pay_company_id}')
        cred_type, cred_name = bk_row.account_type, bk_row.account_name
    elif payment_mode == 'CASH':
        if not cash_staff_id:
            raise ValueError('cash_staff_id required for CASH mode')
        cash_led = ensure_cash_ledger_master(db, pay_company_id, cash_staff_id)
        cred_type, cred_name = 'CASH', cash_led['account_name']
    else:
        raise ValueError(f"payment_mode must be 'BANK' or 'CASH' (got {payment_mode!r})")

    party_type, party_name, party_id = _vci_party_info(db, entry)
    vn   = _next_voucher_number(db, pay_company_id)
    narr = f'Pay {entry.entry_number} net \u20b9{float(net):.2f} via {payment_mode}'
    if utr:
        narr += f' (UTR {utr})'

    if cross_company:
        # TDS already booked in JV-B2; settle only the net payable amount
        legs = [
            {'type': 'LIABILITY', 'name': 'Commission Payable to Members',
             'dr': net, 'cr': 0,
             'particulars': f'Settle {entry.entry_number}'},
            {'type': cred_type,   'name': cred_name,
             'dr': 0,   'cr': net,
             'particulars': f'Net payout {entry.entry_number}'},
        ]
    else:
        # Same-company: TDS first booked here
        legs = [
            {'type': 'LIABILITY', 'name': 'Commission Payable to Members',
             'dr': payable, 'cr': 0,
             'particulars': f'Settle {entry.entry_number}'},
            {'type': 'LIABILITY', 'name': 'TDS Payable on Member Commission',
             'dr': 0,       'cr': tds,
             'particulars': f'TDS 2% on {entry.entry_number}'},
            {'type': cred_type,   'name': cred_name,
             'dr': 0,       'cr': net,
             'particulars': f'Net payout {entry.entry_number}'},
        ]

    jv_id = _post_jv_lines(
        db, pay_company_id, vn, _get_ist().date(), 'PAYMENT', legs,
        narration=narr,
        reference_type='VGK_CASH_INCOME', reference_id=entry.id,
        party_type=party_type, party_name=party_name, party_id=party_id,
        payment_mode=payment_mode, reference_number=utr,
        created_by_id=paid_by_id,
    )

    # Mirror cash payouts into employee_fund_ledger so per-staff float is accurate
    if payment_mode == 'CASH' and cash_staff_id:
        try:
            db.execute(text("SAVEPOINT sp_efl"))
            row = db.execute(text(
                "SELECT COALESCE(balance,0) AS bal FROM employee_fund_ledger "
                "WHERE company_id=:cid AND employee_id=:eid ORDER BY id DESC LIMIT 1"
            ), {'cid': pay_company_id, 'eid': cash_staff_id}).fetchone()
            prev_bal = Decimal(str(row.bal if row else 0))
            new_bal  = prev_bal - net
            db.execute(text("""
                INSERT INTO employee_fund_ledger
                  (employee_id, company_id, transaction_date, entry_type, reference_type, reference_id,
                   reference_number, debit_amount, credit_amount, balance, narration, created_at, updated_by_id)
                VALUES
                  (:eid, :cid, :td, 'EXPENSE_MADE', 'INCOME_ENTRY', :rid,
                   :rn, 0, :amt, :bal, :narr, NOW(), :uid)
            """), {
                'eid': cash_staff_id, 'cid': pay_company_id, 'td': _get_ist().date(),
                'rid': entry.id, 'rn': vn, 'amt': float(net), 'bal': float(new_bal),
                'narr': f'VGK payout {entry.entry_number} \u2192 {party_name}',
                'uid': paid_by_id,
            })
            db.execute(text("RELEASE SAVEPOINT sp_efl"))
        except Exception as e:
            db.execute(text("ROLLBACK TO SAVEPOINT sp_efl"))
            logger.warning(f'[VGK-JV] employee_fund_ledger mirror failed (non-fatal): {e}')

    # G5: Mirror TDS into tds_payable for quarterly government returns
    _mirror_tds_payable(db, entry, tds, paid_by_id, pay_company_id)

    return jv_id


def post_jv_advance(db: Session, entry, released_by_id: int, bank_ledger_id: int = None):
    """
    JV-A: Solar advance released. Dr Advance / Cr Admin, TDS, Bank.
    Posted when a solar advance row is released (auto via service).
    """
    if entry.kind != 'ADVANCE':
        return None
    company_id = entry.company_id
    gross   = Decimal(str(entry.commission_amount or 0))
    admin   = (gross * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01'))
    payable = gross - admin
    # DC-FIX-2605-007b: TDS on payable for consistency with release + post_jv_paid
    tds     = (payable * TDS_PCT / Decimal('100')).quantize(Decimal('0.01'))
    net     = payable - tds

    # Bank ledger: caller-supplied or fall back to company primary bank
    bk_type, bk_name = 'BANK', 'Bank A/c — Primary'
    if bank_ledger_id:
        r = db.execute(text(
            "SELECT account_type, account_name FROM account_ledger_masters WHERE id=:id AND company_id=:cid"
        ), {'id': bank_ledger_id, 'cid': company_id}).fetchone()
        if r:
            bk_type, bk_name = r.account_type, r.account_name
    else:
        # Try to pick primary bank from company_bank_accounts
        prim = db.execute(text(
            "SELECT id FROM company_bank_accounts WHERE company_id=:cid AND is_active=TRUE "
            "ORDER BY is_primary DESC, id ASC LIMIT 1"
        ), {'cid': company_id}).fetchone()
        if prim:
            try:
                lm = ensure_bank_ledger_master(db, company_id, prim.id)
                bk_type, bk_name = lm['account_type'], lm['account_name']
            except Exception as _e:
                logger.warning(f'[VGK-JV-ADV] bank ledger ensure failed: {_e}')
        else:
            # Fallback: use existing default 'Bank Account' if present, else default Cash
            existing = _ledger_master_id(db, company_id, 'BANK', 'Bank Account')
            if not existing:
                bk_type, bk_name = 'CASH', 'Cash'

    party_type, party_name, party_id = _vci_party_info(db, entry)
    vn = _next_voucher_number(db, company_id)
    legs = [
        {'type': 'ASSET',     'name': 'Commission Advance to Members',     'dr': gross, 'cr': 0,
         'particulars': f'Solar CIBIL advance {entry.entry_number}'},
        {'type': 'INCOME',    'name': 'Admin Charges Recovery',            'dr': 0,     'cr': admin,
         'particulars': f'Admin 8% on advance {entry.entry_number}'},
        {'type': 'LIABILITY', 'name': 'TDS Payable on Member Commission',  'dr': 0,     'cr': tds,
         'particulars': f'TDS 2% on advance {entry.entry_number}'},
        {'type': bk_type,     'name': bk_name,                              'dr': 0,     'cr': net,
         'particulars': f'Net advance disbursed {entry.entry_number}'},
    ]
    return _post_jv_lines(
        db, company_id, vn, _get_ist().date(), 'PAYMENT', legs,
        narration=f'Solar CIBIL advance {entry.entry_number} disbursed',
        reference_type='VGK_CASH_INCOME', reference_id=entry.id,
        party_type=party_type, party_name=party_name, party_id=party_id,
        payment_mode='BANK', created_by_id=released_by_id,
    )


def post_jv_reject_reversal(db: Session, entry, rejected_by_id: int):
    """
    JV-F: Reverse all prior JV postings on this entry (sign-flipped).
    For cross-company entries, reverses ledger lines in BOTH the product company
    and the member company.
    """
    from app.models.staff_accounts import OfficialPartner
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()
    member_co_id = partner.company_id if partner else entry.company_id

    # Collect ledger lines from all involved companies
    company_ids = list({entry.company_id, member_co_id})
    rows = db.execute(text("""
        SELECT company_id, account_type, account_name, debit_amount, credit_amount, reference_number
        FROM account_ledger
        WHERE company_id = ANY(:cids)
          AND reference_type='VGK_CASH_INCOME' AND reference_id=:rid
          AND COALESCE(reference_number,'') NOT LIKE '%/REV/%'
    """), {'cids': company_ids, 'rid': entry.id}).fetchall()
    if not rows:
        return None

    # Group by company and post one reversal JV per company
    from collections import defaultdict
    by_co = defaultdict(list)
    for r in rows:
        by_co[r.company_id].append(r)

    party_type, party_name, party_id = _vci_party_info(db, entry)
    last_jv_id = None

    for co_id, co_rows in by_co.items():
        legs = []
        for r in co_rows:
            dr = Decimal(str(r.debit_amount  or 0))
            cr = Decimal(str(r.credit_amount or 0))
            # flip: Dr → Cr, Cr → Dr
            legs.append({
                'type': r.account_type, 'name': r.account_name,
                'dr': cr, 'cr': dr,
                'particulars': f'Reversal of {r.reference_number}',
            })
        vn = _next_voucher_number(db, co_id) + '/REV'
        last_jv_id = _post_jv_lines(
            db, co_id, vn, _get_ist().date(), 'JOURNAL', legs,
            narration=f'Reversal \u2014 reject {entry.entry_number}',
            reference_type='VGK_CASH_INCOME', reference_id=entry.id,
            party_type=party_type, party_name=party_name, party_id=party_id,
            created_by_id=rejected_by_id,
        )

    return last_jv_id


# ────────────────────────────────────────────────────────────────────────────
# Mark-Paid (RELEASED → PAID)
# ────────────────────────────────────────────────────────────────────────────

def mark_paid_cash_income(
    db: Session, entry_id: int, company_id: int,
    paid_by_id: int,
    payment_mode: str,
    bank_ledger_id: int = None,
    cash_staff_id: int = None,
    utr: str = None,
    notes: str = None,
) -> dict:
    """RELEASED → PAID. Posts JV-D and stamps payment fields. Idempotent on PAID."""
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
        VGKCashIncomeEntry.company_id == company_id,
    ).with_for_update().first()
    if not entry:
        return {'success': False, 'error': 'Entry not found'}
    if entry.status == 'PAID':
        return {'success': True, 'idempotent': True, 'entry_number': entry.entry_number}
    if entry.status not in ('RELEASED', 'STAGE1_APPROVED'):
        return {'success': False, 'error': f'Entry is {entry.status}, expected RELEASED or STAGE1_APPROVED'}

    # DC-VGK-ADV-CAP-001: 50% advance cap — PAID advances ≤ floor(eligible_files × 0.5)
    if entry.kind in ('ADVANCE', 'BRAND_ADVANCE'):
        try:
            from app.services.vgk_advance_cap import can_mark_paid as _cap_check
            _cap_allowed, _cap_info = _cap_check(db, entry.partner_id, entry.company_id)
            if not _cap_allowed:
                return {
                    'success': False,
                    'error': (
                        f"50% advance cap reached: {_cap_info['paid_advances']} of "
                        f"{_cap_info['eligible_files']} eligible files already advanced "
                        f"(cap: {_cap_info['cap_limit']}). "
                        f"Wait for more files to progress before paying next advance."
                    ),
                    'cap_info': _cap_info,
                }
        except Exception as _cap_e:
            logger.warning(f'[DC-VGK-ADV-CAP] Cap check failed (non-blocking): {_cap_e}')

    pm = (payment_mode or '').upper().strip()
    if pm not in ('BANK', 'CASH'):
        return {'success': False, 'error': "payment_mode must be 'BANK' or 'CASH'"}
    if pm == 'BANK' and not utr:
        return {'success': False, 'error': 'UTR is required for BANK payments'}

    # DC-VGK-NO-AUTO-JV-001: Auto JV posting removed — all entries are manual via SFMS Entries page.

    now = _get_ist()
    entry.status              = 'PAID'
    entry.paid_by_id          = paid_by_id
    entry.paid_at             = now
    entry.payment_mode        = pm
    entry.payment_utr         = utr
    entry.paid_bank_ledger_id = bank_ledger_id if pm == 'BANK' else None
    entry.paid_cash_staff_id  = cash_staff_id if pm == 'CASH' else None
    if notes:
        entry.notes = (entry.notes or '') + f' | Paid: {notes}'
    entry.updated_at = now

    # DC_VGK_POINTS_AT_PAID_001 + DC-FIX-ADV-WALLET-EARNED-001:
    # For ADVANCE kind entries at PAID time:
    #   1. Debit vgk_points_balance by net_payout (advance+slab combined net)
    #   2. Debit vgk_cash_wallet by commission_amount (gross) — wallet held income pending cash
    #   3. Update vgk_cash_earned_total += commission_amount (lifetime income tracker)
    if entry.kind in ('ADVANCE', 'SLAB_BONUS'):
        try:
            from app.services.vgk_commission import add_vgk_points_entry
            from app.models.staff_accounts import OfficialPartner as _OP
            _partner = db.query(_OP).filter(_OP.id == entry.partner_id).with_for_update().first()
            if _partner is not None:

                # DC_VGK_FIX_STALE_POINTS_20260615: Guard — purge any surviving stale INCOME_EARNED
                # debit rows created by old release_advance() code (reference_type='VGK_SOLAR_ADV').
                # Startup migration already removes these; this guard prevents double-debit
                # in the rare case migration was skipped or rows were re-inserted.
                try:
                    _stale_pts = db.execute(text("""
                        SELECT id, points_debit FROM vgk_points_ledger
                        WHERE partner_id = :pid
                          AND reason_code = 'INCOME_EARNED'
                          AND points_debit > 0
                          AND reference_type = 'VGK_SOLAR_ADV'
                    """), {'pid': _partner.id}).fetchall()
                    if _stale_pts:
                        _stale_restore = sum(float(r.points_debit) for r in _stale_pts)
                        _stale_ids = [r.id for r in _stale_pts]
                        # Use IN (...) with integer literals — safe, avoids ANY(:ids) bind issues
                        _stale_id_csv = ','.join(str(i) for i in _stale_ids)
                        db.execute(text(
                            f"DELETE FROM vgk_points_ledger WHERE id IN ({_stale_id_csv})"
                        ))
                        _partner.vgk_points_balance = (
                            (_partner.vgk_points_balance or Decimal('0')) + Decimal(str(_stale_restore))
                        )
                        logger.warning(
                            f'[VGK-MARK-PAID] Stale-guard: reversed {len(_stale_pts)} old SOLAR_ADV '
                            f'debit rows for partner {_partner.id}, restored {_stale_restore:.0f} pts'
                        )
                except Exception as _sg_e:
                    logger.warning(f'[VGK-MARK-PAID] Stale-guard check failed (non-fatal): {_sg_e}')

                # 1) Points debit — net_payout covers advance+slab combined after re-sync above
                _net_due = entry.net_payout if entry.net_payout else (entry.commission_amount * Decimal('0.90'))
                _net_due = Decimal(str(_net_due))
                _avail   = _partner.vgk_points_balance or Decimal('0')
                if _avail < _net_due:
                    logger.warning(
                        f'[VGK-MARK-PAID] Insufficient points for entry {entry.entry_number}: '
                        f'need {float(_net_due):.2f}, have {float(_avail):.2f}. Debiting available.'
                    )
                    _debit = _avail
                else:
                    _debit = _net_due
                if _debit > Decimal('0'):
                    add_vgk_points_entry(
                        db, _partner.id,
                        points_debit=_debit,
                        reason_code='INCOME_EARNED',
                        reference_type='VGK_CASH_INCOME',
                        reference_id=entry.id,
                        notes=f'Points debited on payment confirmation — {entry.entry_number}',
                    )

                # 2) Wallet debit + lifetime total — ADVANCE only.
                # SLAB_BONUS wallet is already balanced (net=0) at release_advance time;
                # no further wallet ops needed at mark_paid for SLAB_BONUS entries.
                if entry.kind == 'ADVANCE':
                    _gross     = Decimal(str(entry.commission_amount or 0))
                    _wb_before = _partner.vgk_cash_wallet or Decimal('0')
                    _wb_after  = max(Decimal('0'), _wb_before - _gross)
                    _partner.vgk_cash_wallet = _wb_after
                    _log_wallet_txn(
                        db, partner_id=_partner.id,
                        company_id=(_partner.company_id or entry.company_id),
                        txn_type='ADVANCE_CASH_PAID', direction='DR', amount=_gross,
                        wallet_before=_wb_before, wallet_after=_wb_after,
                        ref_type='VGK_CASH_INCOME', ref_id=entry.id,
                        description=f'Advance income paid out — {entry.entry_number}',
                        staff_id=paid_by_id,
                    )
                    # 3) Lifetime earned total
                    _partner.vgk_cash_earned_total = (
                        Decimal(str(_partner.vgk_cash_earned_total or 0)) + _gross
                    )
                _partner.updated_at = _get_ist()

        except Exception as _pts_e:
            logger.warning(f'[VGK-MARK-PAID] Partner update failed (non-fatal): {_pts_e}')

    # DC-VGK-FLOW-002: COMMISSION kind — debit points at PAID stage.
    # Wallet deduction (admin+TDS) already happened at Stage 1 Approve (release_cash_income).
    # Only debit if not already debited (guard against double-debit).
    if entry.kind == 'COMMISSION':
        try:
            from app.services.vgk_commission import add_vgk_points_entry as _avpe_paid
            from app.models.staff_accounts import OfficialPartner as _OP2
            _cp = db.query(_OP2).filter(_OP2.id == entry.partner_id).with_for_update().first()
            if _cp is not None:
                _already_debited = entry.points_actually_debited or Decimal('0')
                if _already_debited == Decimal('0'):
                    _net_due = Decimal(str(entry.net_payout or 0))
                    _avail   = _cp.vgk_points_balance or Decimal('0')
                    _debit   = min(_net_due, _avail) if _net_due > Decimal('0') else Decimal('0')
                    if _debit > Decimal('0'):
                        _avpe_paid(
                            db, _cp.id,
                            points_debit=_debit,
                            reason_code='COMMISSION_ADJUSTMENT',
                            reference_type='VGK_CASH_INCOME',
                            reference_id=entry.id,
                            notes=f'Net payout points debit at paid — {entry.entry_number}',
                        )
                        entry.points_actually_debited = _debit
                        entry.updated_at = _get_ist()
                        logger.info(
                            f'[VGK-MARK-PAID] COMMISSION points debit: '
                            f'partner={_cp.id} entry={entry.entry_number} debit={float(_debit):.2f}'
                        )
        except Exception as _comm_pts_e:
            logger.warning(f'[VGK-MARK-PAID] COMMISSION points debit failed (non-fatal): {_comm_pts_e}')

    return {
        'success':      True,
        'entry_number': entry.entry_number,
        'payment_mode': pm,
        'utr':          utr,
        'paid_at':      now.isoformat(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Solar advance mirror — called from vgk_solar_advance.release_advance
# ────────────────────────────────────────────────────────────────────────────

def record_solar_advance_as_income_row(
    db: Session,
    advance_row,
    released_by_id: int,
    slab_bonus_amount: Decimal = Decimal('0'),
) -> dict:
    """
    Mirror a vgk_solar_cibil_advances RELEASED row into vgk_cash_income_entries
    as kind='ADVANCE', status='RELEASED', and post JV-A.
    Idempotent on (company_id, source_lead_id, partner_id, level=advance_row.level, kind=ADVANCE).

    DC_BONANZA_SLABWISE_AUTO_001: When slab_bonus_amount > 0, the income row
    records the combined total (advance_amount + slab_bonus_amount) so the JV
    and the member statement both reflect the full payout in one entry.
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == advance_row.partner_id).first()
    if not partner:
        return {'success': False, 'error': 'partner missing'}
    # DC-FIX-SOLAR-CO-001: Solar advances always belong to MyntReal (company_id=4).
    # The lead/advance may be created under any company (MNR=3, etc.) but the
    # income entry and wallet credit must always sit under MyntReal so it shows
    # on the MyntReal tab of the unified income page.
    company_id = 4

    # DC_BONANZA_SLABWISE_AUTO_001: Convert to Decimal early — needed by both the
    # idempotent-update path and the new-entry creation path (advance_base was previously
    # defined only after the idempotency block, causing NameError in the update path).
    slab_bonus_amount = Decimal(str(slab_bonus_amount or 0))
    advance_base      = Decimal(str(getattr(advance_row, 'advance_amount', 0) or 0))

    # Idempotency check via (lead, partner, kind=ADVANCE) — company_id-agnostic
    existing = db.execute(text("""
        SELECT id, commission_amount, status FROM vgk_cash_income_entries
        WHERE partner_id=:pid AND source_lead_id=:lid
          AND kind='ADVANCE' LIMIT 1
    """), {'pid': partner.id, 'lid': getattr(advance_row, 'lead_id', None)}).fetchone()
    if existing:
        # DC-SLAB-VCI-SEPARATE-001: ADVANCE entry always reflects advance_amount only.
        # Slab bonus is a separate SLAB_BONUS VCI entry — no patching needed here.
        return {'success': True, 'idempotent': True, 'income_entry_id': existing.id}

    # DC-ADV-MIRROR-CONFLICT-001 (Jul 2026): Guard against unique constraint violation.
    # The constraint uq_vgk_cash_income_lead_partner_level covers (company_id, partner_id,
    # source_lead_id, level) regardless of kind.  When the regular income pipeline ran first
    # it already created a DRAFT/PENDING entry for the same key — inserting an ADVANCE mirror
    # would hit the constraint, corrupting the outer SQLAlchemy session.
    # If a non-ADVANCE, non-CANCELLED entry already occupies this slot, skip the mirror.
    _adv_level = getattr(advance_row, 'level', 1) or 1
    # DC-DVR-L1-COEXIST-001: DVR_ADVANCE and ADVANCE are sibling kinds — both valid at the
    # same level for the same partner+lead (Stage-1 CIBIL advance + Stage-2 DVR advance).
    # Only COMMISSION/BRAND/SENIOR_COMM/etc. at the same level should block the mirror.
    _conflict = db.execute(text("""
        SELECT id, kind, status FROM vgk_cash_income_entries
        WHERE company_id=:cid AND partner_id=:pid AND source_lead_id=:lid AND level=:lv
          AND COALESCE(kind,'DRAFT') NOT IN ('ADVANCE', 'DVR_ADVANCE') AND status != 'CANCELLED'
        LIMIT 1
    """), {
        'cid': company_id,
        'pid': partner.id,
        'lid': getattr(advance_row, 'lead_id', None),
        'lv':  _adv_level,
    }).fetchone()
    if _conflict:
        logger.warning(
            f'[VGK-ADV-MIRROR] DC-ADV-MIRROR-CONFLICT-001: non-ADVANCE entry id={_conflict.id} '
            f'kind={_conflict.kind} status={_conflict.status} already exists for '
            f'(company_id={company_id}, partner_id={partner.id}, '
            f'lead={getattr(advance_row,"lead_id",None)}, level={_adv_level}) — skipping ADVANCE mirror'
        )
        return {'success': True, 'idempotent': True, 'conflict': True, 'income_entry_id': _conflict.id}

    # DC-SLAB-VCI-SEPARATE-001: ADVANCE entry = advance_base only. Slab bonus is separate.
    amount = advance_base

    _notes = f'Solar CIBIL advance mirror (advance#{advance_row.id} {advance_row.entry_number})'

    # DC-NO-RELEASE-001: New ADVANCE entries start as PENDING — Stage 1 Approve is the first action.
    entry = VGKCashIncomeEntry(
        company_id        = company_id,
        entry_number      = _next_entry_number(db, company_id),
        partner_id        = partner.id,
        source_lead_id    = getattr(advance_row, 'lead_id', None),
        category_id       = None,
        level             = getattr(advance_row, 'level', 1) or 1,
        deal_value_total  = 0,
        deal_value_excl_tax = 0,
        commission_pct    = 0,
        commission_amount = amount,
        points_debit_required = 0,
        points_actually_debited = 0,
        kind              = 'ADVANCE',
        status            = 'PENDING',
        admin_charges     = (amount * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01')),
        tds_amount        = (amount * TDS_PCT          / Decimal('100')).quantize(Decimal('0.01')),
        net_payout        = amount - (amount * (ADMIN_CHARGE_PCT + TDS_PCT) / Decimal('100')).quantize(Decimal('0.01')),
        confirmed_by_id   = released_by_id,
        confirmed_at      = _get_ist(),
        notes             = _notes,
    )
    db.add(entry)
    db.flush()

    # DC-VGK-NO-AUTO-JV-001: Auto JV posting removed — all entries are manual via SFMS Entries page.

    # DC-SENIOR-COMM-001 (Jun 2026): ₹500 to direct reporting senior on each solar advance.
    # Only fires for L1 advances (level==1). L2 advance recipient IS already the senior —
    # firing on L2 would cascade one level too high and create a duplicate VSCC.
    # No date guard — applies to all advances (backfill via startup migration for older ones).
    # company_id uses the advance entry's company_id (4=MyntReal) so it shows on correct tab.
    # DC-SENIOR-COMM-001-REMOVED (Jul 2026): Auto-creation of SENIOR_COMM (VSCC) on advance release
    # was causing a create->cancel->create loop. Removed auto-trigger entirely.
    return {'success': True, 'income_entry_id': entry.id, 'entry_number': entry.entry_number}


# ────────────────────────────────────────────────────────────────────────────
# T004: CRM hook alias
# ────────────────────────────────────────────────────────────────────────────

def create_draft_for_completed_lead(db: Session, lead) -> int:
    """
    Thin alias for generate_vgk_cash_income_drafts — called from the CRM
    update_lead_full hook when lead.status transitions to 'completed'.
    Returns the number of DRAFT rows created (0 means all already exist).
    """
    return generate_vgk_cash_income_drafts(db, lead)


# ────────────────────────────────────────────────────────────────────────────
# T002: Default ledger seeder (idempotent)
# ────────────────────────────────────────────────────────────────────────────

_VGK_LEDGER_SEED = [
    # Standard GST / Tax ledgers
    ('LIABILITY', 'CGST Output',                        'GST-CGST-OUT',   'Current Liabilities/Duties & Taxes'),
    ('LIABILITY', 'SGST Output',                        'GST-SGST-OUT',   'Current Liabilities/Duties & Taxes'),
    ('LIABILITY', 'IGST Output',                        'GST-IGST-OUT',   'Current Liabilities/Duties & Taxes'),
    ('LIABILITY', 'TDS Payable',                        'TDS-PAY',        'Current Liabilities/Duties & Taxes'),
    ('ASSET',     'CGST Input',                         'GST-CGST-IN',    'Current Assets/Loans & Advances (Asset)'),
    ('ASSET',     'SGST Input',                         'GST-SGST-IN',    'Current Assets/Loans & Advances (Asset)'),
    ('ASSET',     'IGST Input',                         'GST-IGST-IN',    'Current Assets/Loans & Advances (Asset)'),
    ('ASSET',     'Loans & Advances',                   'LA-MISC',        'Current Assets/Loans & Advances (Asset)'),
    # VGK-specific ledgers
    ('LIABILITY', 'Commission Payable to Members',      'VGK-COMM-PAY',   'Current Liabilities/Provisions'),
    ('LIABILITY', 'TDS Payable on Member Commission',   'VGK-TDS-PAY',    'Current Liabilities/Duties & Taxes'),
    ('INCOME',    'Commission Income \u2014 VGK',       'VGK-COMM-INC',   'Income/Commission Income'),
    ('INCOME',    'Admin Charges Recovery',             'VGK-ADM-REC',    'Income/Other Income'),
    ('EXPENSE',   'Commission Expense',                 'VGK-COMM-EXP',   'Expenses/Indirect Expenses'),
    ('ASSET',     'Commission Advance to Members',      'VGK-COMM-ADV',   'Current Assets/Loans & Advances (Asset)'),
    ('ASSET',     'TDS Receivable \u2014 Member Commissions', 'VGK-TDS-REC', 'Current Assets/Loans & Advances (Asset)'),
]


def seed_default_income_ledgers(db: Session, company_id: int) -> dict:
    """
    Idempotently create all standard + VGK-specific ledger masters for
    a given company. Safe to call multiple times — uses ON CONFLICT DO NOTHING.
    Returns {'inserted': N, 'skipped': M, 'company_id': company_id}.
    """
    inserted = 0
    skipped  = 0
    for (acct_type, acct_name, acct_code, parent_group) in _VGK_LEDGER_SEED:
        existing = _ledger_master_id(db, company_id, acct_type, acct_name)
        if existing:
            skipped += 1
            continue
        db.execute(text("""
            INSERT INTO account_ledger_masters
              (company_id, account_type, account_name, account_code, parent_group,
               description, opening_balance, opening_balance_type,
               is_active, created_at, updated_at)
            VALUES
              (:cid, :t, :n, :code, :pg,
               'Auto-seeded by VGK income pipeline bootstrap', 0, 'DEBIT',
               TRUE, NOW(), NOW())
            ON CONFLICT (company_id, account_type, account_name) DO NOTHING
        """), {
            'cid': company_id, 't': acct_type, 'n': acct_name,
            'code': f'{acct_code}-{company_id}', 'pg': parent_group,
        })
        inserted += 1
    db.commit()
    logger.info(f'[VGK-SEED] company#{company_id}: {inserted} inserted, {skipped} already existed')
    return {'company_id': company_id, 'inserted': inserted, 'skipped': skipped}


def record_dvr_advance_as_income_row(
    db: Session,
    advance_row,
    released_by_id: int,
) -> dict:
    """
    DC-DVR-VCI-MIRROR-001 (Jul 2026): Mirror a RELEASED DVR_ADVANCE row from
    vgk_solar_cibil_advances into vgk_cash_income_entries as kind='DVR_ADVANCE',
    status='PENDING'. Idempotent on (partner_id, source_lead_id, level, kind='DVR_ADVANCE').

    DVR advances do NOT trigger a VSCC senior commission — the L1 partner's senior
    already received VSCC from the CIBIL advance (Stage 1), and L2 partners have their
    own DVR entry. The idempotency guard in record_solar_advance_as_income_row would
    block a second VSCC anyway, but we explicitly skip it here for clarity.

    If a non-DVR_ADVANCE non-cancelled VCI entry already occupies the unique slot
    (company_id, partner_id, source_lead_id, level) — e.g., a CIBIL ADVANCE or COMMISSION
    entry — the mirror is skipped (logged as conflict) because the DB constraint would reject
    a second row at the same slot regardless of kind.
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == advance_row.partner_id).first()
    if not partner:
        return {'success': False, 'error': 'partner missing'}

    # DC-FIX-SOLAR-CO-001: Solar income always under MyntReal (company_id=4).
    company_id   = 4
    _adv_level   = int(getattr(advance_row, 'level', 1) or 1)
    advance_base = Decimal(str(getattr(advance_row, 'advance_amount', 0) or 0))
    _lead_id     = getattr(advance_row, 'lead_id', None)

    # Idempotency: one DVR_ADVANCE VCI per (partner, lead, level)
    existing = db.execute(text("""
        SELECT id FROM vgk_cash_income_entries
        WHERE partner_id=:pid AND source_lead_id=:lid AND level=:lv AND kind='DVR_ADVANCE'
        LIMIT 1
    """), {'pid': partner.id, 'lid': _lead_id, 'lv': _adv_level}).fetchone()
    if existing:
        return {'success': True, 'idempotent': True, 'income_entry_id': existing.id}

    # Conflict guard — unique constraint uq_vgk_cash_income_lead_partner_level_kind covers
    # (company_id, partner_id, source_lead_id, level, kind). ADVANCE and DVR_ADVANCE have
    # different kind values so they CAN coexist at the same level (DC-DVR-L1-COEXIST-001).
    # Only COMMISSION/SENIOR_COMM/SLAB_BONUS/etc. at the same level genuinely block this slot.
    _conflict = db.execute(text("""
        SELECT id, kind, status FROM vgk_cash_income_entries
        WHERE company_id=:cid AND partner_id=:pid AND source_lead_id=:lid AND level=:lv
          AND COALESCE(kind,'COMMISSION') NOT IN ('DVR_ADVANCE', 'ADVANCE') AND status != 'CANCELLED'
        LIMIT 1
    """), {
        'cid': company_id, 'pid': partner.id, 'lid': _lead_id, 'lv': _adv_level,
    }).fetchone()
    if _conflict:
        logger.warning(
            f'[DVR-VCI-MIRROR] DC-DVR-VCI-MIRROR-001: slot occupied by id={_conflict.id} '
            f'kind={_conflict.kind} status={_conflict.status} — skipping DVR mirror '
            f'(company={company_id}, partner={partner.id}, lead={_lead_id}, level={_adv_level})'
        )
        return {'success': True, 'idempotent': True, 'conflict': True, 'income_entry_id': _conflict.id}

    _notes = (
        f'DVR Advance mirror (advance#{getattr(advance_row,"id","?")} '
        f'{getattr(advance_row,"entry_number","?")})'
    )
    entry = VGKCashIncomeEntry(
        company_id              = company_id,
        entry_number            = _next_entry_number(db, company_id),
        partner_id              = partner.id,
        source_lead_id          = _lead_id,
        category_id             = None,
        level                   = _adv_level,
        deal_value_total        = 0,
        deal_value_excl_tax     = 0,
        commission_pct          = 0,
        commission_amount       = advance_base,
        points_debit_required   = 0,
        points_actually_debited = 0,
        kind                    = 'DVR_ADVANCE',
        status                  = 'PENDING',
        admin_charges           = (advance_base * ADMIN_CHARGE_PCT / Decimal('100')).quantize(Decimal('0.01')),
        tds_amount              = (advance_base * TDS_PCT          / Decimal('100')).quantize(Decimal('0.01')),
        net_payout              = advance_base - (advance_base * (ADMIN_CHARGE_PCT + TDS_PCT) / Decimal('100')).quantize(Decimal('0.01')),
        confirmed_by_id         = released_by_id,
        confirmed_at            = _get_ist(),
        notes                   = _notes,
    )
    db.add(entry)
    db.flush()
    logger.info(
        f'[DVR-VCI-MIRROR] Created VCI mirror {entry.entry_number} for DVR advance '
        f'{getattr(advance_row,"entry_number","?")} partner={partner.partner_code} level={_adv_level}'
    )
    return {'success': True, 'income_entry_id': entry.id, 'entry_number': entry.entry_number}
