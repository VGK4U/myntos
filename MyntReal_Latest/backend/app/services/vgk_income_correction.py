"""
VGK Income Correction Service — DC-HANDLER-CHANGE-INCOME-001 (Jul 2026)

Called when a CRM lead's Ground Source (associated_partner_id / source_ref_id)
changes AFTER income entries already exist.

Rules:
  DRAFT / PENDING / STAGE1_APPROVED  → CANCELLED  (wallet credit reversed)
  RELEASED                            → CANCELLED  (net_payout reversed from wallet)
  PAID                                → ADJUSTMENT entry created (debit on next payout)

After cancellation: re-triggers generate_vgk_cash_income_drafts for the new partner.
"""

import logging
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_ist():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


def _partner_name(partner) -> str:
    if partner is None:
        return '—'
    return (getattr(partner, 'partner_name', None) or
            getattr(partner, 'partner_code', None) or str(partner.id))


def _log_wallet_txn(db, partner_id, company_id, txn_type, direction, amount,
                    wallet_before, wallet_after, ref_type=None, ref_id=None,
                    description=None, staff_id=None):
    try:
        from app.models.vgk_wallet_transaction import VGKWalletTransaction
        db.add(VGKWalletTransaction(
            company_id=company_id, partner_id=partner_id,
            txn_type=txn_type, direction=direction, amount=amount,
            wallet_before=wallet_before, wallet_after=wallet_after,
            ref_type=ref_type, ref_id=ref_id, description=description,
            initiated_by_staff_id=staff_id, created_at=_get_ist(),
        ))
        db.flush()
    except Exception as _e:
        logger.warning(f'[DC-HCI-001] Wallet txn log failed (non-fatal): {_e}')


# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW  (dry-run — no DB changes)
# ─────────────────────────────────────────────────────────────────────────────

def get_income_correction_preview(db: Session, lead_id: int) -> dict:
    """
    Returns a summary of income entries that would be cancelled / adjusted
    if the handler/source on this lead were changed. No writes made.
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner

    entries = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.source_lead_id == lead_id,
        VGKCashIncomeEntry.status.notin_(['CANCELLED']),
        VGKCashIncomeEntry.kind.notin_(['ADJUSTMENT']),
    ).all()

    if not entries:
        return {'has_entries': False, 'cancellable': [], 'adjustable_paid': [], 'total': 0}

    cancellable = []
    adjustable_paid = []
    partner_cache = {}

    def _get_partner(pid):
        if pid not in partner_cache:
            partner_cache[pid] = db.query(OfficialPartner).filter(
                OfficialPartner.id == pid).first()
        return partner_cache[pid]

    for e in entries:
        p = _get_partner(e.partner_id)
        pname = _partner_name(p)
        rec = {
            'id': e.id,
            'entry_number': e.entry_number,
            'status': e.status,
            'kind': e.kind,
            'level': e.level,
            'partner_id': e.partner_id,
            'partner_name': pname,
            'commission_amount': float(e.commission_amount or 0),
            'net_payout': float(e.net_payout or 0),
        }
        if e.status == 'PAID':
            adjustable_paid.append(rec)
        else:
            cancellable.append(rec)

    return {
        'has_entries': True,
        'cancellable': cancellable,
        'adjustable_paid': adjustable_paid,
        'total': len(entries),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CORRECTION  (writes — called after lead.associated_partner_id changes)
# ─────────────────────────────────────────────────────────────────────────────

def handle_handler_change_income_correction(
    db: Session,
    lead,
    old_partner_id: int,
    new_partner_id: int,
    changed_by_name: str = 'Staff',
    staff_id: int = None,
) -> dict:
    """
    DC-HANDLER-CHANGE-INCOME-001:
    Cancel / adjust existing income entries for old_partner_id on this lead,
    then re-trigger income pipeline for new_partner_id.

    Returns a summary dict for logging / audit.
    """
    from app.models.vgk_cash_income import VGKCashIncomeEntry
    from app.models.staff_accounts import OfficialPartner

    if not old_partner_id or old_partner_id == new_partner_id:
        return {'skipped': True, 'reason': 'no partner change'}

    old_partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == old_partner_id).first()
    new_partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == new_partner_id).first() if new_partner_id else None

    old_name = _partner_name(old_partner)
    new_name = _partner_name(new_partner)
    now      = _get_ist()

    cancel_reason = (
        f'Handler changed — source updated from {old_name} to {new_name} '
        f'on {now.strftime("%d %b %Y")} by {changed_by_name}'
    )

    entries = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.source_lead_id == lead.id,
        VGKCashIncomeEntry.status.notin_(['CANCELLED']),
        VGKCashIncomeEntry.kind.notin_(['ADJUSTMENT']),
    ).with_for_update().all()

    cancelled_count = 0
    adjusted_count  = 0
    summary_lines   = []

    for entry in entries:
        ep = db.query(OfficialPartner).filter(
            OfficialPartner.id == entry.partner_id).first()
        gross     = Decimal(str(entry.commission_amount or 0))
        net_pay   = Decimal(str(entry.net_payout or 0))
        c_id      = ep.company_id if ep else entry.company_id

        if entry.status == 'PAID':
            # ── PAID: create ADJUSTMENT entry (debit on old partner's next payout) ──
            adj_amount = net_pay if net_pay > 0 else gross
            if adj_amount > 0 and ep:
                from app.services.vgk_cash_income import _next_entry_number
                db.flush()
                adj_entry = VGKCashIncomeEntry(
                    company_id             = entry.company_id,
                    entry_number           = _next_entry_number(db, entry.company_id),
                    partner_id             = entry.partner_id,
                    source_lead_id         = lead.id,
                    category_id            = entry.category_id,
                    level                  = entry.level,
                    deal_value_total       = entry.deal_value_total,
                    deal_value_excl_tax    = entry.deal_value_excl_tax,
                    commission_pct         = entry.commission_pct,
                    commission_amount      = adj_amount,
                    points_debit_required  = Decimal('0'),
                    points_actually_debited= Decimal('0'),
                    status                 = 'PENDING',
                    kind                   = 'ADJUSTMENT',
                    net_payout             = adj_amount,
                    adjustment_ref_entry_id= entry.id,
                    adjustment_reason      = (
                        f'Adjusted with Lead #{lead.id} ({lead.name or ""}) — '
                        f'handler changed from {old_name} to {new_name} '
                        f'on {now.strftime("%d %b %Y")} by {changed_by_name}'
                    ),
                    notes                  = f'Deduction from next payout — replaces paid entry {entry.entry_number}',
                )
                db.add(adj_entry)
                db.flush()

                # Wallet: deduct adjustment amount from old partner's wallet
                if ep:
                    wb = ep.vgk_cash_wallet or Decimal('0')
                    wa = max(Decimal('0'), wb - adj_amount)
                    ep.vgk_cash_wallet = wa
                    ep.updated_at      = now
                    _log_wallet_txn(
                        db, ep.id, c_id,
                        txn_type='HANDLER_CHANGE_ADJUSTMENT', direction='DR',
                        amount=adj_amount, wallet_before=wb, wallet_after=wa,
                        ref_type='VGK_CASH_INCOME', ref_id=adj_entry.id,
                        description=(
                            f'Adjustment (handler changed) — replaces {entry.entry_number} '
                            f'Lead #{lead.id}'
                        ),
                        staff_id=staff_id,
                    )

                adjusted_count += 1
                summary_lines.append(
                    f'PAID entry {entry.entry_number} L{entry.level} → '
                    f'ADJUSTMENT {adj_entry.entry_number} (₹{float(adj_amount):.2f})'
                )

        else:
            # ── DRAFT / PENDING / STAGE1_APPROVED / RELEASED: cancel + reverse wallet ──
            reverse_amount = Decimal('0')

            if entry.status in ('DRAFT', 'PENDING', 'STAGE1_APPROVED'):
                # Wallet was credited gross on DRAFT creation; confirm/stage1 did not move wallet
                reverse_amount = gross

            elif entry.status == 'RELEASED':
                # Wallet: gross credited at DRAFT, (admin+tds) debited at release → net_payout remains
                reverse_amount = net_pay if net_pay > 0 else gross
                # Also reverse earned_total
                if ep:
                    earned = getattr(ep, 'vgk_cash_earned_total', None) or Decimal('0')
                    ep.vgk_cash_earned_total = max(Decimal('0'), earned - gross)

            entry.status           = 'CANCELLED'
            entry.cancelled_reason = cancel_reason
            entry.updated_at       = now

            # Reverse wallet credit
            if reverse_amount > 0 and ep:
                wb = ep.vgk_cash_wallet or Decimal('0')
                wa = max(Decimal('0'), wb - reverse_amount)
                ep.vgk_cash_wallet = wa
                ep.updated_at      = now
                _log_wallet_txn(
                    db, ep.id, c_id,
                    txn_type='HANDLER_CHANGE_REVERSAL', direction='DR',
                    amount=reverse_amount, wallet_before=wb, wallet_after=wa,
                    ref_type='VGK_CASH_INCOME', ref_id=entry.id,
                    description=(
                        f'Income reversed (handler changed) — {entry.entry_number} '
                        f'Lead #{lead.id}'
                    ),
                    staff_id=staff_id,
                )

            cancelled_count += 1
            summary_lines.append(
                f'{entry.status} entry {entry.entry_number} L{entry.level} → CANCELLED '
                f'(reversed ₹{float(reverse_amount):.2f})'
            )

    db.flush()

    # ── Re-trigger income pipeline for new partner ──────────────────────────
    new_drafts = 0
    if new_partner_id and lead.associated_partner_id == new_partner_id:
        _sps = (getattr(lead, 'solar_pipeline_status', '') or '').lower()
        _income_eligible = (
            lead.status == 'completed'
            or _sps in ('balance_received', 'subsidy_pending', 'completed')
        )
        if _income_eligible:
            try:
                from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
                new_drafts = generate_vgk_cash_income_drafts(db, lead)
                logger.info(
                    f'[DC-HCI-001] Lead {lead.id}: {new_drafts} new DRAFT(s) created '
                    f'for new partner {new_name}'
                )
            except Exception as _re:
                logger.warning(f'[DC-HCI-001] Retrigger for new partner failed: {_re}')

    result = {
        'skipped':         False,
        'cancelled':       cancelled_count,
        'adjusted_paid':   adjusted_count,
        'new_drafts':      new_drafts,
        'old_partner':     old_name,
        'new_partner':     new_name,
        'summary':         summary_lines,
    }
    logger.info(
        f'[DC-HCI-001] Lead {lead.id}: handler change correction done — '
        f'cancelled={cancelled_count} adjusted={adjusted_count} new_drafts={new_drafts}'
    )
    return result
