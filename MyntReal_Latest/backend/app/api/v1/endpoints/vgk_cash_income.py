"""
VGK Cash Income — Staff API Endpoints (DC Protocol Mar 2026)

Sales staff:   GET  /staff/vgk/cash-income/drafts        — list DRAFT entries
               POST /staff/vgk/cash-income/{id}/confirm  — confirm or reject
               GET  /staff/vgk/cash-income/all           — full history with filters

Accounts staff: GET  /staff/vgk/cash-income/pending      — list PENDING entries
                POST /staff/vgk/cash-income/{id}/release — release payout

Member:         GET  /vgk/member/cash-income             — own income + wallet

No negative impact on existing VGK Discount Credits (points) or income ledger endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List

from app.core.database import get_db
from app.models.staff_accounts import OfficialPartner
from app.models.staff import StaffEmployee
from app.models.vgk_cash_income import VGKCashIncomeEntry
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)
router = APIRouter()

LEVEL_LABELS = {
    1: 'Source',
    2: 'Senior',
    3: 'Extended',
    4: 'Core',
    5: 'Support',
}


def _enrich_entry(entry: VGKCashIncomeEntry, db: Session) -> dict:
    d = entry.to_dict()
    d['level_label'] = LEVEL_LABELS.get(entry.level, f'L{entry.level}')

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()
    if partner:
        d['partner_name'] = partner.partner_name
        d['partner_code'] = partner.partner_code
        d['partner_co_id'] = partner.company_id
        d['whatsapp_number'] = getattr(partner, 'whatsapp_number', '') or ''
        pts = float(getattr(partner, 'vgk_points_balance', 0) or 0)
        d['partner_points_balance'] = pts
        d['partner_points_sufficient'] = pts >= float(entry.net_payout or 0)
        # Derer ive salutation title
        _nt = (getattr(partner, 'name_title', '') or '').strip()
        if not _nt:
            _g = (getattr(partner, 'gender', '') or '').strip().lower()
            _nt = 'Mr.' if _g in ('male', 'm') else ('Ms.' if _g in ('female', 'f') else '')
        d['name_title'] = _nt

        # Cross-company detection (product company vs member company)
        product_co_id = entry.company_id
        member_co_id  = partner.company_id
        cross_company = (member_co_id != product_co_id)
        d['css_company'] = cross_company

        if cross_company:
            prod_co = db.execute(text(
                "SELECT company_name FROM associated_companies WHERE id=:cid"
            ), {'cid': product_co_id}).fetchone()
            mem_co = db.execute(text(
                "SELECT company_name FROM associated_companies WHERE id=:cid"
            ), {'cid': member_co_id}).fetchone()
            d['product_co_name'] = prod_co.company_name if prod_co else f'Co#{product_co_id}'
            d['member_co_name']  = mem_co.company_name  if mem_co  else f'Co#{member_co_id}'
        else:
            d['product_co_name'] = None
            d['member_co_name']  = None
    else:
        d['cross_company']   = False
        d['product_co_name'] = None
        d['member_co_name']  = None

    d['deal_value_received'] = None  # always present; populated below if lead found
    lead_row = db.execute(text(
        "SELECT name, deal_value_total, deal_value_excl_tax, category_id, solar_value, deal_value_received "
        "FROM crm_leads WHERE id = :lid"
    ), {'lid': entry.source_lead_id}).fetchone() if entry.source_lead_id else None
    if lead_row:
        d['client_name'] = lead_row.name if lead_row.name else '—'
        if d.get('solar_value') is None and lead_row.solar_value:
            d['solar_value'] = float(lead_row.solar_value)
        dvr = lead_row.deal_value_received
        d['deal_value_received'] = float(dvr) if dvr else None
    cat_row = db.execute(text(
        "SELECT name FROM signup_categories WHERE id = :cid"
    ), {'cid': entry.category_id}).fetchone() if entry.category_id else None
    d['category_name'] = cat_row.name if cat_row else '—'
    return d


def _enrich_entry_bulk(
    entry: VGKCashIncomeEntry,
    partner_map: dict,
    lead_map: dict,
    cat_map: dict,
    co_map: dict,
    adv_map: dict = None,
) -> dict:
    """DC-BULK-ENRICH-001: O(1) enrichment using pre-fetched in-memory maps.

    """
    d = entry.to_dict()
    if not d.get('income_date') and getattr(entry, 'created_at', None):
        d['income_date'] = entry.created_at.isoformat()
    d['level_label'] = LEVEL_LABELS.get(entry.level, f'L{entry.level}')

    partner = partner_map.get(entry.partner_id)
    if partner:
        d['partner_name']             = partner['partner_name']
        d['partner_code']             = partner['partner_code']
        d['partner_co_id']            = partner['company_id']
        d['whatsapp_number']          = partner['whatsapp_number']
        pts = partner['vgk_points_balance']
        d['partner_points_balance']   = pts
        d['partner_points_sufficient'] = pts >= float(entry.net_payout or 0)
        d['name_title']               = partner['name_title']

        product_co_id = entry.company_id
        member_co_id  = partner['company_id']
        cross_company = (member_co_id != product_co_id)
        d['css_company'] = cross_company
        if cross_company:
            d['product_co_name'] = co_map.get(product_co_id) or f'Co#{product_co_id}'
            d['member_co_name']  = co_map.get(member_co_id)  or f'Co#{member_co_id}'
        else:
            d['product_co_name'] = None
            d['member_co_name']  = None
    else:
        d['cross_company']   = False
        d['product_co_name'] = None
        d['member_co_name']  = None

    d['deal_value_received'] = None
    lead = lead_map.get(entry.source_lead_id) if entry.source_lead_id else None
    if lead:
        d['client_name'] = lead['name'] or '—'
        if d.get('solar_value') is None and lead.get('solar_value'):
            d['solar_value'] = float(lead['solar_value'])
        dvr = lead.get('deal_value_received')
        d['deal_value_received'] = float(dvr) if dvr else None

    d['category_name'] = cat_map.get(entry.category_id, '—') if entry.category_id else '—'

    # Advance resolution (Solar Advance / CIBIL Advance)
    if adv_map and entry.source_lead_id and entry.level and (entry.kind or '').upper() not in ('ADVANCE', 'DVR_ADVANCE'):
        adv_info = adv_map.get((int(entry.source_lead_id), int(entry.level)), {})
        d['stage1_adv']    = float(adv_info.get('stage1', 0.0))
        d['stage2_adv']    = float(adv_info.get('stage2', 0.0))
        d['advance_paid']  = float(adv_info.get('total', 0.0))
        gross_amt          = float(entry.commission_amount or 0)
        d['balance_gross'] = max(0.0, round(gross_amt - d['advance_paid'], 2))
    else:
        d['stage1_adv']    = 0.0
        d['stage2_adv']    = 0.0
        d['advance_paid']  = 0.0
        d['balance_gross'] = float(entry.commission_amount or 0)

    return d


# ────────────────────────────────────────────────────────────────────────────
# SALES STAFF ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@router.get('/staff/vgk/cash-income/drafts')
def list_draft_entries(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Sales staff: list all DRAFT income entries awaiting confirmation."""
    entries = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.company_id == company_id,
        VGKCashIncomeEntry.status == 'DRAFT',
    ).order_by(VGKCashIncomeEntry.created_at.asc()).all()

    return {
        'success': True,
        'count':   len(entries),
        'data':    [_enrich_entry(e, db) for e in entries],
    }


@router.post('/staff/vgk/cash-income/{entry_id}/confirm')
def confirm_or_reject_entry(
    entry_id: int,
    company_id: int = Query(...),
    action: str = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    rejection_reason: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Sales staff: confirm (DRAFT -> PENDING) or reject (DRAFT -> CANCELLED).
    On confirm: points debited (or waived if insufficient), cash income credited.
    """
    from app.services.vgk_cash_income import confirm_cash_income, reject_cash_income

    action = action.lower().strip()
    if action == 'confirm':
        result = confirm_cash_income(db, entry_id, company_id, current_employee.id, notes)
    elif action == 'reject':
        result = reject_cash_income(db, entry_id, company_id, current_employee.id, rejection_reason)
    else:
        raise HTTPException(status_code=400, detail="action must be 'confirm' or 'reject'")

    if not result.get('success'):
        status_code = result.get('status_code', 400)
        raise HTTPException(status_code=status_code, detail=result.get('error', 'Operation failed'))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f'[VGK-CI] commit failed: {e}')
        raise HTTPException(status_code=500, detail='Database error — please retry')

    return {'success': True, 'action': action, **result}


@router.get('/staff/vgk/cash-income/all')
def list_all_entries(
    company_id: int = Query(...),
    status: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Full income history with optional status/partner filters."""
    q = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.company_id == company_id
    )
    if status:
        q = q.filter(VGKCashIncomeEntry.status == status.upper())
    if partner_id:
        q = q.filter(VGKCashIncomeEntry.partner_id == partner_id)

    total = q.count()
    entries = q.order_by(VGKCashIncomeEntry.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        'success':  True,
        'total':    total,
        'page':     page,
        'per_page': per_page,
        'data':     [_enrich_entry(e, db) for e in entries],
    }


# ────────────────────────────────────────────────────────────────────────────
# ACCOUNTS STAFF ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@router.get('/staff/vgk/cash-income/pending')
def list_pending_entries(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Accounts staff: list all PENDING income entries awaiting payout release."""
    entries = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.company_id == company_id,
        VGKCashIncomeEntry.status == 'PENDING',
    ).order_by(VGKCashIncomeEntry.confirmed_at.asc()).all()

    return {
        'success': True,
        'count':   len(entries),
        'data':    [_enrich_entry(e, db) for e in entries],
    }


@router.post('/staff/vgk/cash-income/{entry_id}/release')
def release_entry(
    entry_id: int,
    company_id: int = Query(...),
    notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Accounts staff: release PENDING -> RELEASED.
    Deducts 8% admin charges + 2% TDS; credits net to partner's vgk_cash_wallet.
    """
    from app.services.vgk_cash_income import release_cash_income

    result = release_cash_income(db, entry_id, company_id, current_employee.id, notes)
    if not result.get('success'):
        status_code = result.get('status_code', 400)
        raise HTTPException(status_code=status_code, detail=result.get('error', 'Release failed'))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f'[VGK-CI] release commit failed: {e}')
        raise HTTPException(status_code=500, detail='Database error — please retry')

    return {'success': True, **result}


# ────────────────────────────────────────────────────────────────────────────
# MEMBER ENDPOINT
# ────────────────────────────────────────────────────────────────────────────

@router.get('/member/cash-income')
def member_cash_income(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """VGK member: own cash income history + wallet balance."""
    company_id = current_member.company_id
    partner_id = current_member.id

    # DC-FIX-COMPANY-FILTER-001 (Jun 2026): Drop company_id filter on member income queries.
    # Income entries are created with the LEAD's company_id (e.g. company_id=3 for VGK4U SAAS),
    # but the partner may belong to a different company (e.g. company_id=1 for MyntReal).
    # Filtering by partner.company_id hides all cross-company commission entries.
    # Only filter by partner_id — matches the existing DC-FIX-ADV-WALLET-EARNED-001 pattern.
    q = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.partner_id == partner_id,
        VGKCashIncomeEntry.status != 'CANCELLED',
    )
    total = q.count()
    entries = q.order_by(VGKCashIncomeEntry.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # DC-VGK-FLOW-002: Summary card mapping:
    #   Under Review    = DRAFT + PENDING  (not yet stage-1 approved)
    #   Awaiting Release = STAGE1_APPROVED (stage 1 done, awaiting physical payment)
    #   Total Released  = RELEASED + PAID  (physically paid out)
    summary = db.execute(text("""
        SELECT
            SUM(commission_amount)                                                                       AS gross_total,
            SUM(CASE WHEN status='PENDING'        THEN commission_amount ELSE 0 END)                     AS pending_total,
            SUM(CASE WHEN status='STAGE1_APPROVED' THEN commission_amount ELSE 0 END)                    AS stage1_approved_total,
            SUM(CASE WHEN status IN ('RELEASED','PAID') THEN commission_amount  ELSE 0 END)               AS released_total,
            SUM(CASE WHEN status IN ('RELEASED','PAID') THEN admin_charges + tds_amount ELSE 0 END)      AS total_deductions,
            SUM(CASE WHEN status='DRAFT'          THEN commission_amount ELSE 0 END)                     AS draft_total,
            COUNT(*)                                                                                     AS total_entries
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid AND status != 'CANCELLED'
    """), {'pid': partner_id}).fetchone()

    wallet = float(getattr(current_member, 'vgk_cash_wallet', 0) or 0)

    def _member_entry(e: VGKCashIncomeEntry) -> dict:
        d = e.to_dict()
        d['level_label'] = LEVEL_LABELS.get(e.level, f'L{e.level}')
        cat_row = db.execute(text(
            "SELECT name FROM signup_categories WHERE id = :cid"
        ), {'cid': e.category_id}).fetchone() if e.category_id else None
        d['category_name'] = cat_row.name if cat_row else '—'
        lead_row = db.execute(text(
            "SELECT name, solar_value FROM crm_leads WHERE id = :lid"
        ), {'lid': e.source_lead_id}).fetchone() if e.source_lead_id else None
        d['client_name'] = (lead_row.name if lead_row and lead_row.name else '—')
        if lead_row and lead_row.solar_value and d.get('solar_value') is None:
            d['solar_value'] = float(lead_row.solar_value)
        return d

    # DC-FIX-ADV-WALLET-EARNED-001: Compute earned_total from VCI entries (RELEASED or PAID),
    # no company_id filter — ADVANCE entries sit under company_id=4 (MyntReal) regardless
    # of partner's own company_id. RELEASED included so wallet-credited advances show immediately.
    _earned_row = db.execute(text("""
        SELECT COALESCE(SUM(commission_amount), 0) AS total
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid AND status IN ('RELEASED', 'PAID')
    """), {'pid': current_member.id}).fetchone()
    earned_total = float(_earned_row.total if _earned_row else 0)

    return {
        'success':        True,
        'wallet_balance': wallet,
        'earned_total':   earned_total,
        'summary': {
            'gross_total':           float(summary.gross_total           or 0),
            'draft_total':           float(summary.draft_total           or 0),
            'pending_total':         float(summary.pending_total         or 0),
            'stage1_approved_total': float(summary.stage1_approved_total or 0),
            'released_total':        float(summary.released_total        or 0),
            'total_deductions':      float(summary.total_deductions      or 0),
            'total_entries':         int(summary.total_entries           or 0),
        },
        'total':    total,
        'page':     page,
        'per_page': per_page,
        'data':     [_member_entry(e) for e in entries],
    }


# ────────────────────────────────────────────────────────────────────────────
# MEMBER WALLET ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@router.get('/member/wallet')
def member_wallet(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """
    Member wallet view:
    - wallet_balance    = current spendable balance
    - earned_total      = lifetime income earned (net, never decreases)
    - transaction log   = every CR/DR with type, amount, running balance
    """
    from app.models.vgk_wallet_transaction import VGKWalletTransaction

    # Internal system txn types hidden from the member's wallet history view.
    # INCOME_DEDUCTION + PAYOUT types are accounting entries; the member sees
    # only the CR income credit rows (enriched with deduction_amount / net_amount).
    # BONANZA_CASH_PAYOUT is also hidden — it's the physical cash disbursement DR that
    # brings wallet back to 0 after a bonanza payout; it shows as "Balance: ₹0" on the CR row.
    # NOTE: ADVANCE_CASH_PAID is intentionally NOT hidden — member must see wallet DR when cash is paid out.
    _HIDDEN_TYPES = {'INCOME_DEDUCTION', 'SOLAR_ADV_PAYOUT', 'SLAB_BONUS_PAYOUT', 'COMPANY_PAYOUT_DEDUCT', 'BONANZA_CASH_PAYOUT'}
    _DEDUCT_CR_TYPES = {'SOLAR_ADVANCE_CREDIT', 'SLAB_BONUS_CREDIT', 'INCOME_CREDIT', 'COMPANY_PAYOUT', 'ADJUSTMENT'}

    # DC-FIX-COMPANY-FILTER-001: Drop company_id filter — wallet txns use the lead's
    # company_id (e.g. 3), not the partner's own company_id (e.g. 1). Only filter by partner_id.
    q = db.query(VGKWalletTransaction).filter(
        VGKWalletTransaction.partner_id == current_member.id,
        ~VGKWalletTransaction.txn_type.in_(_HIDDEN_TYPES),
    )
    total = q.count()
    txns = q.order_by(VGKWalletTransaction.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Build map: (ref_type, ref_id) -> wallet_after of matching PAYOUT txn
    # so the Balance column in the member view shows the post-disbursement balance.
    # BONANZA_CASH_PAYOUT takes precedence over SLAB_BONUS_PAYOUT for the final balance shown.
    _payout_rows = db.query(VGKWalletTransaction).filter(
        VGKWalletTransaction.partner_id == current_member.id,
        VGKWalletTransaction.txn_type.in_(['SOLAR_ADV_PAYOUT', 'SLAB_BONUS_PAYOUT', 'COMPANY_PAYOUT_DEDUCT', 'BONANZA_CASH_PAYOUT']),
    ).all()
    _payout_map = {(r.ref_type, r.ref_id): float(r.wallet_after) for r in _payout_rows}

    TXN_LABELS = {
        'INCOME_CREDIT':         'Cash Income Credited',
        'INCOME_DEDUCTION':      'Admin Charges & TDS',
        'SOLAR_ADVANCE_CREDIT':  'Solar Advance Credited',
        'SLAB_BONUS_CREDIT':     'Slab Bonus Credited',
        'COMPANY_PAYOUT':        'Company Payout Credited',
        'SERVICE_DEBIT':         'VGK Service Payment',
        'VENDOR_DEBIT':          'Vendor Purchase',
        'WITHDRAWAL':            'Withdrawal Payout',
        'ADJUSTMENT':            'Manual Adjustment',
        'SOLAR_ADVANCE_RECOVERY':'Solar Advance Recovery',
        'ADVANCE_CASH_PAID':     'Cash Paid Out',
    }

    # Fix A — DC_VGK_EARNED_RELEASED_001: earned_total = income credited to wallet (RELEASED or PAID).
    # RELEASED is included so solar advances show in earned total as soon as wallet is credited,
    # not just when accounts process the bank payment.
    # No company_id filter — solar advances sit under company_id=4 (MyntReal) regardless.
    earned_row = db.execute(text("""
        SELECT COALESCE(SUM(commission_amount), 0) AS total
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid
          AND status     IN ('RELEASED', 'PAID')
    """), {'pid': current_member.id}).fetchone()
    earned_total = float(earned_row.total if earned_row else 0)

    def _enrich_txn(t):
        d = {**t.to_dict(), 'label': TXN_LABELS.get(t.txn_type, t.txn_type)}
        if t.txn_type in _DEDUCT_CR_TYPES and t.direction == 'CR':
            gross = float(t.amount)
            # DC-FIX-DRAFT-DEDUCT-001 (Jun 2026): Only show deductions when the income entry has
            # actually had admin/TDS applied (RELEASED or PAID status). DRAFT and PENDING entries
            # have no deductions charged yet — show 0 so the member doesn't see phantom deductions.
            _entry_status = None
            if t.ref_type == 'VGK_CASH_INCOME' and t.ref_id:
                _es_row = db.execute(
                    text("SELECT status FROM vgk_cash_income_entries WHERE id = :eid"),
                    {'eid': t.ref_id}
                ).fetchone()
                _entry_status = _es_row.status if _es_row else None
            _has_deductions = _entry_status in ('RELEASED', 'PAID')
            d['deduction_amount'] = round(gross * 0.10, 2) if _has_deductions else 0.0
            d['net_amount']       = round(gross * 0.90, 2) if _has_deductions else gross
            # DC-WALLET-CUMBAL-002: Do NOT override wallet_after with the post-disbursement
            # balance. Payout/offset txns (SOLAR_ADV_PAYOUT, BONANZA_CASH_PAYOUT, etc.) are
            # hidden from the member view, so overriding the CR row's wallet_after with their
            # post-payout value (e.g. ₹0) is confusing — the member sees "+₹1,000 -> Balance ₹0".
            # The raw stored wallet_after (balance at the moment the credit hit) is the correct
            # value to display for a running balance visible to the member.
        return d

    # Points alert: check if any PENDING income entries require more points than the partner has
    points_balance = float(getattr(current_member, 'vgk_points_balance', 0) or 0)
    _pending_nets_row = db.execute(text("""
        SELECT COALESCE(MIN(COALESCE(net_payout, commission_amount * 0.90)), 0) AS min_net,
               COUNT(*) AS cnt
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid
          AND company_id = :cid
          AND status     = 'PENDING'
          AND COALESCE(net_payout, commission_amount * 0.90) > :pts
    """), {'pid': current_member.id, 'cid': current_member.company_id, 'pts': points_balance}).fetchone()
    _adv_nets_row = db.execute(text("""
        SELECT COALESCE(MIN(advance_amount * 0.90), 0) AS min_net,
               COUNT(*) AS cnt
        FROM vgk_solar_cibil_advances
        WHERE partner_id = :pid
          AND company_id = :cid
          AND status     = 'PENDING'
          AND advance_amount * 0.90 > :pts
    """), {'pid': current_member.id, 'cid': current_member.company_id, 'pts': points_balance}).fetchone()

    _candidates = []
    if _pending_nets_row and _pending_nets_row.cnt > 0:
        _candidates.append(float(_pending_nets_row.min_net))
    if _adv_nets_row and _adv_nets_row.cnt > 0:
        _candidates.append(float(_adv_nets_row.min_net))

    _has_alert    = len(_candidates) > 0
    _min_net      = min(_candidates) if _candidates else 0.0
    _shortfall    = round(max(0.0, _min_net - points_balance), 2)

    # DC_BONANZA_PAYMENT_002: fetch pending bonanza claims for wallet display.
    # Fix B — DC_VGK_PENDING_ADV_001: Exclude slab_wise rows that were auto-paid via
    # apply_slab_bonus_if_active (slab_bonus_paid=TRUE on the advance) — those are already
    # tracked in pending_advance_claims below, so showing them here would double-count.
    from app.models.bonanza import BonanzaProgress as _BP, Bonanza as _BZ
    _bp_rows = db.execute(text("""
        SELECT bp.id, bp.bonanza_id, bp.current_progress, bp.processed_status,
               bp.achieved_date,
               b.name AS bonanza_name, b.reward_type,
               b.slab_extra_amount, b.reward_amount, b.is_monetary
        FROM bonanza_progress bp
        JOIN bonanza b ON b.id = bp.bonanza_id
        WHERE bp.partner_id = :pid
          AND bp.processed_status IN ('Pending', 'Payment Released')
          AND (b.is_monetary = true OR b.reward_type = 'slab_wise')
          AND NOT (
            b.reward_type = 'slab_wise'
            AND EXISTS (
              SELECT 1 FROM vgk_solar_cibil_advances a
              WHERE a.partner_id = bp.partner_id
                AND a.slab_bonus_paid = TRUE
            )
          )
    """), {'pid': current_member.id}).fetchall()

    pending_bonanza_claims = []
    for _r in _bp_rows:
        _deal_count = _r.current_progress or 1
        if _r.reward_type == 'slab_wise' and _r.slab_extra_amount:
            _amount = float(_r.slab_extra_amount) * _deal_count
        else:
            _amount = float(_r.reward_amount or 0)
        pending_bonanza_claims.append({
            'claim_id':       _r.id,
            'bonanza_id':     _r.bonanza_id,
            'bonanza_name':   _r.bonanza_name,
            'amount':         _amount,
            'deal_count':     _deal_count,
            'slab_extra_amount': float(_r.slab_extra_amount) if _r.slab_extra_amount else None,
            'processed_status': _r.processed_status,
            'claimed_date':   _r.achieved_date.isoformat() if _r.achieved_date else None,
        })

    # Fix B — DC_VGK_PENDING_ADV_001: Pending advance claims — solar advances that have been
    # RELEASED by staff but whose VCI entry (kind=ADVANCE) has not yet been marked PAID.
    # These represent gross income the partner is owed but hasn't received as cash yet.
    # advance_pending_gross = advance_amount + slab_bonus_amount (if slab auto-paid).
    _adv_pending_rows = db.execute(text("""
        SELECT a.id, a.lead_id, a.entry_number, a.advance_amount,
               a.slab_bonus_amount, a.slab_bonus_paid, a.created_at
        FROM vgk_solar_cibil_advances a
        WHERE a.partner_id = :pid
          AND a.status     = 'RELEASED'
          AND NOT EXISTS (
            SELECT 1 FROM vgk_cash_income_entries vci
            WHERE vci.partner_id     = a.partner_id
              AND vci.source_lead_id = a.lead_id
              AND vci.kind           = 'ADVANCE'
              AND vci.status         = 'PAID'
          )
        ORDER BY a.created_at DESC
    """), {'pid': current_member.id}).fetchall()

    pending_advance_claims = []
    for _a in _adv_pending_rows:
        _adv_amt  = float(_a.advance_amount or 0)
        _slab_amt = float(_a.slab_bonus_amount or 0) if _a.slab_bonus_paid else 0.0
        pending_advance_claims.append({
            'advance_id':      _a.id,
            'entry_number':    _a.entry_number,
            'advance_amount':  _adv_amt,
            'slab_amount':     _slab_amt,
            'pending_gross':   round(_adv_amt + _slab_amt, 2),
            'created_at':      _a.created_at.isoformat() if _a.created_at else None,
        })

    return {
        'success':        True,
        'wallet_balance': float(getattr(current_member, 'vgk_cash_wallet', 0) or 0),
        'earned_total':   earned_total,
        'total':          total,
        'page':           page,
        'per_page':       per_page,
        'transactions':   [_enrich_txn(t) for t in txns],
        'pending_bonanza_claims':  pending_bonanza_claims,
        'pending_advance_claims':  pending_advance_claims,
        'points_alert': {
            'has_alert':      _has_alert,
            'points_balance': points_balance,
            'min_net_pending': round(_min_net, 2),
            'shortfall':      _shortfall,
        },
    }


@router.post('/member/wallet/use')
def member_use_wallet(
    amount: float = Body(..., embed=True),
    txn_type: str = Body('SERVICE_DEBIT', embed=True),
    description: str = Body(..., embed=True),
    ref_type: str = Body(None, embed=True),
    ref_id: int = Body(None, embed=True),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """
    Member uses wallet balance to pay for a VGK service or vendor/marketplace purchase.
    txn_type: 'SERVICE_DEBIT' | 'VENDOR_DEBIT'
    """
    from app.services.vgk_cash_income import debit_wallet_for_service
    from decimal import Decimal

    if txn_type not in ('SERVICE_DEBIT', 'VENDOR_DEBIT'):
        raise HTTPException(status_code=400, detail="txn_type must be 'SERVICE_DEBIT' or 'VENDOR_DEBIT'")

    result = debit_wallet_for_service(
        db,
        partner_id=current_member.id,
        company_id=current_member.company_id,
        amount=Decimal(str(amount)),
        txn_type=txn_type,
        description=description,
        ref_type=ref_type,
        ref_id=ref_id,
    )

    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Wallet debit failed'))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail='Database error — please retry')

    return {'success': True, **result}


# ────────────────────────────────────────────────────────────────────────────
# STAFF WALLET MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────

@router.get('/staff/vgk/wallet/transactions')
def staff_wallet_transactions(
    company_id: int = Query(...),
    partner_id: int = Query(...),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: view all wallet transactions for a specific partner."""
    from app.models.vgk_wallet_transaction import VGKWalletTransaction

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == partner_id,
        OfficialPartner.company_id == company_id,
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail='Partner not found')

    q = db.query(VGKWalletTransaction).filter(
        VGKWalletTransaction.company_id == company_id,
        VGKWalletTransaction.partner_id == partner_id,
    )
    total = q.count()
    txns = q.order_by(VGKWalletTransaction.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        'success':       True,
        'partner': {
            'id':                partner.id,
            'name':              partner.partner_name,
            'code':              partner.partner_code,
            'wallet':            float(getattr(partner, 'vgk_cash_wallet', 0) or 0),
            'earned_total':      float(getattr(partner, 'vgk_cash_earned_total', 0) or 0),
            'vgk_points_balance':float(getattr(partner, 'vgk_points_balance', 0) or 0),
        },
        'total':    total,
        'page':     page,
        'per_page': per_page,
        'data':     [t.to_dict() for t in txns],
    }


@router.post('/staff/vgk/wallet/withdrawal')
def staff_initiate_withdrawal(
    company_id: int = Query(...),
    partner_id: int = Body(..., embed=True),
    amount: float = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: initiate a cash withdrawal from a member's wallet."""
    from app.services.vgk_cash_income import initiate_wallet_withdrawal
    from decimal import Decimal

    result = initiate_wallet_withdrawal(
        db,
        partner_id=partner_id,
        company_id=company_id,
        amount=Decimal(str(amount)),
        staff_id=current_employee.id,
        notes=notes,
    )

    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Withdrawal failed'))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f'[VGK-WALLET] withdrawal commit failed: {e}')
        raise HTTPException(status_code=500, detail='Database error — please retry')

    return {'success': True, **result}


@router.get('/staff/vgk/wallet/summary')
def staff_wallet_summary(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: aggregate wallet stats across all partners for this company."""
    row = db.execute(text("""
        SELECT
            COUNT(*)                            AS total_partners,
            SUM(vgk_cash_wallet)                AS total_wallet,
            SUM(vgk_cash_earned_total)          AS total_earned,
            COUNT(*) FILTER (WHERE vgk_cash_wallet > 0)   AS partners_with_balance
        FROM official_partners
        WHERE company_id = :cid AND vgk_role IS NOT NULL
    """), {'cid': company_id}).fetchone()

    pending_row = db.execute(text("""
        SELECT COUNT(*) AS cnt, SUM(commission_amount) AS total
        FROM vgk_cash_income_entries
        WHERE company_id = :cid AND status = 'PENDING'
    """), {'cid': company_id}).fetchone()

    draft_row = db.execute(text("""
        SELECT COUNT(*) AS cnt FROM vgk_cash_income_entries
        WHERE company_id = :cid AND status = 'DRAFT'
    """), {'cid': company_id}).fetchone()

    return {
        'success': True,
        'stats': {
            'total_partners':       int(row.total_partners or 0),
            'partners_with_balance':int(row.partners_with_balance or 0),
            'total_wallet_held':    float(row.total_wallet or 0),
            'total_earned_ever':    float(row.total_earned or 0),
            'pending_entries':      int(pending_row.cnt or 0),
            'pending_amount':       float(pending_row.total or 0),
            'draft_entries':        int(draft_row.cnt or 0),
        }
    }


# ════════════════════════════════════════════════════════════════════════════
# DC-SENIOR-COMM-001: ₹500 senior commission on Solar Advance release
# ════════════════════════════════════════════════════════════════════════════

def _trigger_senior_comm(db: Session, entry: VGKCashIncomeEntry, staff_id: int):
    """
    DC-SENIOR-COMM-001-REMOVED (Jul 2026): Auto-trigger removed entirely to prevent create-cancel loops.
    """
    return

    senior_id = partner.parent_partner_id
    senior    = db.query(OfficialPartner).filter(OfficialPartner.id == senior_id).first()
    if not senior:
        return

    GROSS = 500.0
    ADMIN = 40.0   # 8%
    TDS   = 10.0   # 2%
    NET   = 450.0  # 90%

    now = _get_ist()

    # Step 1: Deduct ₹500 from senior's current PENDING L2 COMMISSION entry (inline)
    senior_pending = (
        db.query(VGKCashIncomeEntry)
        .filter(
            VGKCashIncomeEntry.partner_id == senior_id,
            VGKCashIncomeEntry.status     == 'PENDING',
            VGKCashIncomeEntry.kind       == 'COMMISSION',
            VGKCashIncomeEntry.level      == 2,
        )
        .order_by(VGKCashIncomeEntry.created_at.desc())
        .first()
    )
    if senior_pending:
        senior_pending.commission_amount = max(0, float(senior_pending.commission_amount or 0) - GROSS)
        senior_pending.admin_charges     = max(0, float(senior_pending.admin_charges     or 0) - ADMIN)
        senior_pending.tds_amount        = max(0, float(senior_pending.tds_amount        or 0) - TDS)
        senior_pending.net_payout        = max(0, float(senior_pending.net_payout        or 0) - NET)
        senior_pending.notes = (senior_pending.notes or '') + (
            f' | DC-SENIOR-COMM-001: ₹500 deducted — junior {partner.partner_code} '
            f'advance {entry.entry_number} released'
        )
        senior_pending.updated_at = now
        logger.info(
            f'[DC-SENIOR-COMM-001] Deducted ₹500 from senior entry {senior_pending.entry_number}'
        )

    # Step 2: Create a new SENIOR_COMM income entry for the senior (for Stage 1/2 approval)
    ts  = now.strftime('%y%m')
    seq_row = db.execute(text(
        "SELECT COUNT(*)+1 FROM vgk_cash_income_entries "
        "WHERE kind='SENIOR_COMM' AND entry_number LIKE :pfx"
    ), {'pfx': f'VSCC-{ts}-%'}).scalar() or 1
    entry_num = f'VSCC-{ts}-{int(seq_row):04d}'

    sc_entry = VGKCashIncomeEntry(
        company_id            = senior.company_id,
        entry_number          = entry_num,
        partner_id            = senior_id,
        source_lead_id        = entry.source_lead_id,
        category_id           = entry.category_id,
        level                 = 2,
        deal_value_total      = 0,
        deal_value_excl_tax   = 0,
        commission_amount     = GROSS,
        admin_charges         = ADMIN,
        tds_amount            = TDS,
        net_payout            = NET,
        points_debit_required = 0,
        points_actually_debited = 0,
        status                = 'PENDING',
        kind                  = 'SENIOR_COMM',
        confirmed_by_id       = staff_id,
        confirmed_at          = now,
        notes                 = (
            f'DC-SENIOR-COMM-001: ₹500 advance incentive — junior '
            f'{partner.partner_code} advance {entry.entry_number} released'
        ),
        ledger_posted         = False,
        created_at            = now,
        updated_at            = now,
    )
    db.add(sc_entry)
    logger.info(
        f'[DC-SENIOR-COMM-001] Created SENIOR_COMM entry {entry_num} for senior partner {senior_id}'
    )


# ════════════════════════════════════════════════════════════════════════════
# DC-VGK-INCOME-UNIFIED-001 (May 2026): Unified state-machine endpoints
# ════════════════════════════════════════════════════════════════════════════

@router.get('/staff/vgk/cash-income/unified-list')
def unified_list(
    company_id: Optional[int] = Query(None),
    vgk_mode: bool = Query(False),
    status: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    points_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Unified income list — all kinds (COMMISSION/ADVANCE) and statuses, with role-aware actions.

    vgk_mode=true: returns ALL entries whose partner is a VGK_TEAM member, regardless of which
    product company booked the income (used for the Zynova/VGK4U tab).
    """
    from app.services.vgk_cash_income import is_super_skip_user

    _vgk_team_pids = [r[0] for r in db.execute(text("SELECT id FROM official_partners WHERE category = 'VGK_TEAM'")).fetchall()]

    if vgk_mode:
        # VGK programme view: filter by VGK_TEAM partner IDs.
        # This surfaces VGK income regardless of which product-company the entry sits under.
        q = db.query(VGKCashIncomeEntry).filter(VGKCashIncomeEntry.partner_id.in_(_vgk_team_pids))
    else:
        if company_id is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="company_id is required when vgk_mode is false")
        # Exclude VGK_TEAM partners from company tabs — VGK entries belong on the Zynova/VGK-All tab
        q = (
            db.query(VGKCashIncomeEntry)
            .filter(VGKCashIncomeEntry.company_id == company_id)
            .filter(~VGKCashIncomeEntry.partner_id.in_(_vgk_team_pids))
        )
    if status:
        if status.upper() == 'BALANCE_RECEIVED_PLUS':
            # DC-BRP-001 (Jun 2026): grouped filter — entries whose source CRM lead is at
            # balance_received / subsidy_pending / completed solar pipeline stage.
            _brp_lead_ids = db.execute(text(
                "SELECT id FROM crm_leads WHERE solar_pipeline_status IN "
                "('balance_received','subsidy_pending','completed')"
            )).scalars().all()
            q = q.filter(VGKCashIncomeEntry.source_lead_id.in_(_brp_lead_ids))
        else:
            q = q.filter(VGKCashIncomeEntry.status == status.upper())
    if kind:
        q = q.filter(VGKCashIncomeEntry.kind == kind.upper())
    if partner_id:
        q = q.filter(VGKCashIncomeEntry.partner_id == partner_id)
    if points_filter:
        if points_filter.lower() == 'available':
            q = q.filter(OfficialPartner.vgk_points_balance >= VGKCashIncomeEntry.net_payout)
        elif points_filter.lower() == 'not_available':
            q = q.filter(OfficialPartner.vgk_points_balance < VGKCashIncomeEntry.net_payout)

    total = q.count()
    entries = q.order_by(VGKCashIncomeEntry.income_date.desc().nullslast(), VGKCashIncomeEntry.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    is_super = is_super_skip_user(current_employee)
    _dept_raw = getattr(current_employee, 'department', '') or ''
    if hasattr(_dept_raw, 'value'):
        _dept_raw = _dept_raw.value
    elif hasattr(_dept_raw, 'name'):
        _dept_raw = _dept_raw.name
    dept = str(_dept_raw or '').lower()
    _role_raw = getattr(current_employee, 'role_code', '') or ''
    role = str(_role_raw or '').lower()
    _emp_code = (getattr(current_employee, 'emp_code', '') or '').strip()

    is_privileged = is_super or _emp_code in ('MR10001', 'MR10025') or role in ('key_leadership', 'ea', 'executive_admin', 'admin', 'vgk4u')
    can_sales    = is_privileged or 'sales' in dept or 'crm' in dept
    can_accounts = is_privileged or 'account' in dept or 'finance' in dept or 'store' in dept
    can_pay      = is_privileged or 'finance' in dept or 'bank' in dept or 'account' in dept or 'store' in dept

    def _actions_for(e):
        # DC-NO-RELEASE-001: Release button removed. All income flows PENDING->Stage1->Stage2(Paid).
        acts = []
        if e.status == 'DRAFT' and (can_sales or is_privileged):
            acts += ['confirm', 'reject']
        if e.status in ('PENDING', 'RELEASED') and (can_accounts or is_privileged):
            # RELEASED kept as backward-compat alias for PENDING (DB entries pre-migration)
            acts += ['stage1_approve', 'reject']
        # DC-VGK-STAGE1-001: Stage 1 is MANDATORY for ALL users — no skip, even for super staff.
        if e.status == 'STAGE1_APPROVED' and (can_pay or is_privileged):
            acts += ['mark_paid', 'reject']
        if is_privileged:
            acts = list(dict.fromkeys(acts))
            valid = {
                'DRAFT':          ['confirm', 'stage1_approve', 'reject'],
                'PENDING':        ['stage1_approve', 'reject'],
                'RELEASED':       ['stage1_approve', 'reject'],
                'STAGE1_APPROVED':['mark_paid', 'reject'],
                'PAID':           [],
                'CANCELLED':      [],
            }.get(e.status, [])
            acts = [a for a in acts if a in valid]
        return acts

    # DC-BULK-ENRICH-001: bulk pre-fetch to replace N+1 queries in _enrich_entry.
    # 4 queries total for the page regardless of page size (vs 3-5 per row previously).
    _uniq_partner_ids = list({e.partner_id for e in entries if e.partner_id})
    _uniq_lead_ids    = list({e.source_lead_id for e in entries if e.source_lead_id})
    _uniq_cat_ids     = list({e.category_id for e in entries if e.category_id})

    # Query 1: partners
    _p_map: dict = {}
    if _uniq_partner_ids:
        for p in db.query(OfficialPartner).filter(OfficialPartner.id.in_(_uniq_partner_ids)).all():
            _nt = (getattr(p, 'name_title', '') or '').strip()
            if not _nt:
                _g = (getattr(p, 'gender', '') or '').strip().lower()
                _nt = 'Mr.' if _g in ('male', 'm') else ('Ms.' if _g in ('female', 'f') else '')
            _p_map[p.id] = {
                'partner_name':       p.partner_name,
                'partner_code':       p.partner_code,
                'company_id':         p.company_id,
                'whatsapp_number':    getattr(p, 'whatsapp_number', '') or '',
                'vgk_points_balance': float(getattr(p, 'vgk_points_balance', 0) or 0),
                'name_title':         _nt,
            }

    # Query 2: company names (product_co + member_co for cross-company detection)
    _co_id_set = {e.company_id for e in entries if e.company_id}
    for _pm in _p_map.values():
        if _pm.get('company_id'):
            _co_id_set.add(_pm['company_id'])
    _co_map: dict = {}
    if _co_id_set:
        for _row in db.execute(
            text("SELECT id, company_name FROM associated_companies WHERE id = ANY(:ids)"),
            {'ids': list(_co_id_set)},
        ).fetchall():
            _co_map[_row.id] = _row.company_name

    # Query 3: source leads (name + solar_value + deal_value_received only)
    _lead_map: dict = {}
    if _uniq_lead_ids:
        for _row in db.execute(
            text("SELECT id, name, solar_value, deal_value_received "
                 "FROM crm_leads WHERE id = ANY(:ids)"),
            {'ids': _uniq_lead_ids},
        ).fetchall():
            _lead_map[_row.id] = {
                'name':               _row.name,
                'solar_value':        _row.solar_value,
                'deal_value_received': _row.deal_value_received,
            }

    # Query 4: categories
    _cat_map: dict = {}
    if _uniq_cat_ids:
        for _row in db.execute(
            text("SELECT id, name FROM signup_categories WHERE id = ANY(:ids)"),
            {'ids': _uniq_cat_ids},
        ).fetchall():
            _cat_map[_row.id] = _row.name

    # Query 5: prior advances for (source_lead_id, level)
    _adv_map: dict = {}
    if _uniq_lead_ids:
        try:
            int_lead_ids = [int(x) for x in _uniq_lead_ids if x is not None]
            adv_vci = db.execute(text(
                "SELECT source_lead_id, level, "
                "  SUM(CASE WHEN kind = 'ADVANCE' THEN COALESCE(commission_amount, 0) ELSE 0 END) AS stage1_adv, "
                "  SUM(CASE WHEN kind = 'DVR_ADVANCE' THEN COALESCE(commission_amount, 0) ELSE 0 END) AS stage2_adv, "
                "  SUM(COALESCE(commission_amount, 0)) AS total_adv "
                "FROM vgk_cash_income_entries "
                "WHERE source_lead_id = ANY(:lids) "
                "  AND kind IN ('ADVANCE', 'DVR_ADVANCE') AND status != 'CANCELLED' "
                "GROUP BY source_lead_id, level"
            ), {"lids": int_lead_ids}).fetchall()
            for ar in adv_vci:
                if ar.source_lead_id is not None and ar.level is not None:
                    _adv_map[(int(ar.source_lead_id), int(ar.level))] = {
                        "stage1": float(ar.stage1_adv or 0),
                        "stage2": float(ar.stage2_adv or 0),
                        "total":  float(ar.total_adv or 0)
                    }

            adv_vsca = db.execute(text(
                "SELECT a.lead_id, a.level, "
                "  SUM(CASE WHEN a.kind = 'ADVANCE' THEN COALESCE(a.advance_amount, 0) ELSE 0 END) AS stage1_adv, "
                "  SUM(CASE WHEN a.kind = 'DVR_ADVANCE' THEN COALESCE(a.advance_amount, 0) ELSE 0 END) AS stage2_adv, "
                "  SUM(COALESCE(a.advance_amount, 0)) AS total_adv "
                "FROM vgk_solar_cibil_advances a "
                "WHERE a.lead_id = ANY(:lids) "
                "  AND a.status IN ('PENDING', 'RELEASED', 'PAID') "
                "  AND NOT EXISTS ( "
                "    SELECT 1 FROM vgk_cash_income_entries vci "
                "    WHERE vci.source_lead_id = a.lead_id "
                "      AND vci.level = a.level AND vci.kind = a.kind AND vci.status != 'CANCELLED' "
                "  ) "
                "GROUP BY a.lead_id, a.level"
            ), {"lids": int_lead_ids}).fetchall()
            for ar in adv_vsca:
                if ar.lead_id is not None and ar.level is not None:
                    key = (int(ar.lead_id), int(ar.level))
                    cur = _adv_map.get(key, {"stage1": 0.0, "stage2": 0.0, "total": 0.0})
                    cur["stage1"] += float(ar.stage1_adv or 0)
                    cur["stage2"] += float(ar.stage2_adv or 0)
                    cur["total"]  += float(ar.total_adv or 0)
                    _adv_map[key] = cur
        except Exception as _adv_err:
            try: db.rollback()
            except: pass
            logger.warning(f"[VGK-ADV-MAP] Non-fatal adv_map error: {_adv_err}")

    def _enrich_full(e):
        d = _enrich_entry_bulk(e, _p_map, _lead_map, _cat_map, _co_map, _adv_map)
        d['available_actions'] = _actions_for(e)
        return d

    # Live aggregates per status
    if vgk_mode:
        summary = db.execute(text("""
            SELECT e.status, e.kind,
              COUNT(*) AS cnt,
              COALESCE(SUM(e.commission_amount),0) AS gross,
              COALESCE(SUM(e.admin_charges),0)     AS admin,
              COALESCE(SUM(e.tds_amount),0)        AS tds,
              COALESCE(SUM(e.net_payout),0)        AS net
            FROM vgk_cash_income_entries e
            WHERE e.partner_id = ANY(:pids)
            GROUP BY e.status, e.kind
        """), {'pids': _vgk_team_pids}).fetchall()
    else:
        summary = db.execute(text("""
            SELECT
              status, kind,
              COUNT(*) AS cnt,
              COALESCE(SUM(commission_amount),0) AS gross,
              COALESCE(SUM(admin_charges),0)     AS admin,
              COALESCE(SUM(tds_amount),0)        AS tds,
              COALESCE(SUM(net_payout),0)        AS net
            FROM vgk_cash_income_entries
            WHERE company_id=:cid AND NOT (partner_id = ANY(:pids))
            GROUP BY status, kind
        """), {'cid': company_id, 'pids': _vgk_team_pids}).fetchall()

    return {
        'success': True,
        'total': total,
        'page': page,
        'per_page': per_page,
        'data': [_enrich_full(e) for e in entries],
        'role': {
            'can_sales': can_sales,
            'can_accounts': can_accounts,
            'can_pay': can_pay,
            'is_super': is_super,
        },
        'summary': [
            {'status': r.status, 'kind': r.kind, 'count': int(r.cnt or 0),
             'gross': float(r.gross or 0), 'admin': float(r.admin or 0),
             'tds':   float(r.tds   or 0), 'net':   float(r.net   or 0)}
            for r in summary
        ],
        'rates': {'admin_pct': 8.0, 'tds_pct': 2.0},
    }


@router.get('/staff/vgk/cash-income/payment-options')
def payment_options(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Lists banks (all companies via ledger masters) + cash-eligible staff for the Mark-Paid modal."""

    # Pull all active BANK-type ledger masters across all active companies
    banks_raw = db.execute(text("""
        SELECT alm.id        AS ledger_id,
               alm.company_id,
               alm.account_name,
               alm.bank_name,
               alm.account_number,
               alm.ifsc_code,
               ac.company_name
        FROM account_ledger_masters alm
        JOIN associated_companies ac ON ac.id = alm.company_id
        WHERE alm.account_type = 'BANK'
          AND alm.is_active    = TRUE
          AND ac.is_active     = TRUE
        ORDER BY ac.company_name ASC, alm.id ASC
    """)).fetchall()

    banks = []
    for b in banks_raw:
        masked = (b.account_number or '')[-4:]
        if masked:
            label = f"{b.account_name} ····{masked}"
        else:
            label = b.account_name
        banks.append({
            'ledger_id':    b.ledger_id,
            'company_id':   b.company_id,
            'company_name': b.company_name,
            'label':        label,
            'is_primary':   False,
        })

    # All active companies for the company selector
    companies_raw = db.execute(text("""
        SELECT id, company_name, company_code
        FROM associated_companies
        WHERE is_active = TRUE
        ORDER BY company_name ASC
    """)).fetchall()
    companies = [{'id': c.id, 'name': c.company_name, 'code': c.company_code} for c in companies_raw]

    # DC-FIX-2605-001: staff_employees uses status='active', NOT is_active/resignation_status
    cash_staff = db.execute(text("""
        SELECT id, emp_code, full_name, first_name, last_name
        FROM staff_employees
        WHERE status = 'active'
        ORDER BY emp_code ASC
        LIMIT 200
    """)).fetchall()
    staff = [{
        'staff_id': s.id,
        'emp_code': s.emp_code,
        'label': (s.full_name or f"{s.first_name or ''} {s.last_name or ''}".strip() or s.emp_code) + f' ({s.emp_code})',
    } for s in cash_staff]

    return {'success': True, 'companies': companies, 'banks': banks, 'cash_staff': staff,
            'rates': {'admin_pct': 8.0, 'tds_pct': 2.0}}


@router.post('/staff/vgk/cash-income/unified-action')
def unified_action(
    company_id: int = Query(...),
    entry_id: Optional[int] = Body(None, embed=True),
    entry_ids: Optional[List[int]] = Body(None, embed=True),
    action: str = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    rejection_reason: Optional[str] = Body(None, embed=True),
    payment_mode: Optional[str] = Body(None, embed=True),
    bank_ledger_id: Optional[int] = Body(None, embed=True),
    cash_staff_id: Optional[int] = Body(None, embed=True),
    payment_utr: Optional[str] = Body(None, embed=True),
    bypass: Optional[bool] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Unified state-machine endpoint.
    action: 'confirm' | 'release' | 'mark_paid' | 'reject' | 'stage1_approve'
    Supports single `entry_id` or batch `entry_ids: List[int]`.
    """
    from app.services.vgk_cash_income import (
        confirm_cash_income, release_cash_income, reject_cash_income,
        mark_paid_cash_income, post_jv_confirm, post_jv_release,
        post_jv_reject_reversal, is_super_skip_user, _get_ist,
    )

    act = (action or '').lower().strip()
    if act not in ('confirm', 'release', 'mark_paid', 'reject', 'stage1_approve'):
        raise HTTPException(status_code=400, detail="action must be confirm|release|mark_paid|reject|stage1_approve")

    ids_to_process = []
    if entry_ids and isinstance(entry_ids, list):
        ids_to_process = [int(x) for x in entry_ids if x is not None]
    elif entry_id is not None:
        ids_to_process = [int(entry_id)]

    if not ids_to_process:
        raise HTTPException(status_code=400, detail="entry_id or entry_ids required")

    results = []
    is_super = is_super_skip_user(current_employee)

    for target_id in ids_to_process:
        entry = db.query(VGKCashIncomeEntry).filter(
            VGKCashIncomeEntry.id == target_id,
        ).first()
        if not entry:
            if len(ids_to_process) == 1:
                raise HTTPException(status_code=404, detail=f'Entry {target_id} not found')
            continue

        skipped_states = []
        result = {}

        try:
            if act == 'reject':
                now = _get_ist()
                if entry.status in ('PAID', 'CANCELLED'):
                    raise HTTPException(status_code=400, detail=f'Cannot reject — already {entry.status}')
                try:
                    post_jv_reject_reversal(db, entry, current_employee.id)
                except Exception as e:
                    logger.warning(f'[VGK-UNIFIED] reversal failed: {e}')
                entry.status = 'CANCELLED'
                entry.rejection_reason = rejection_reason or 'Rejected'
                entry.updated_at = now
                result = {'success': True, 'status': 'CANCELLED', 'entry_number': entry.entry_number}

            elif act == 'confirm':
                if entry.status == 'DRAFT':
                    inner = confirm_cash_income(db, target_id, entry.company_id, current_employee.id, notes)
                    if not inner.get('success'):
                        raise HTTPException(status_code=400, detail=inner.get('error', 'Confirm failed'))
                    post_jv_confirm(db, entry, current_employee.id)
                    entry.ledger_posted = True
                    result = inner
                elif entry.status in ('PENDING', 'RELEASED', 'STAGE1_APPROVED', 'PAID'):
                    result = {'success': True, 'status': entry.status, 'entry_number': entry.entry_number, 'already_confirmed': True}
                else:
                    raise HTTPException(status_code=400, detail=f'Entry is {entry.status}, cannot confirm')

            elif act == 'stage1_approve':
                if entry.status not in ('PENDING', 'RELEASED'):
                    raise HTTPException(status_code=400, detail=f'Entry must be PENDING or RELEASED to approve (got {entry.status})')

                if entry.kind not in ('ADVANCE', 'SLAB_BONUS', 'DVR_ADVANCE') and entry.status == 'PENDING':
                    inner_rel = release_cash_income(db, target_id, entry.company_id, current_employee.id, notes)
                    if not inner_rel.get('success'):
                        raise HTTPException(status_code=400, detail=inner_rel.get('error', 'Wallet deduction at Stage1 failed'))
                    post_jv_release(db, entry, current_employee.id)
                    db.flush(); db.refresh(entry)
                elif entry.kind in ('ADVANCE', 'DVR_ADVANCE') and entry.status in ('PENDING', 'RELEASED'):
                    if entry.kind == 'ADVANCE':
                        from app.services.vgk_solar_advance import release_advance as _rel_adv
                        inner_rel = _rel_adv(
                            db=db, lead_id=entry.source_lead_id,
                            released_by_id=current_employee.id,
                            notes=notes, _level=entry.level
                        )
                    else:
                        from app.services.vgk_solar_advance import release_dvr_advance as _rel_dvr
                        inner_rel = _rel_dvr(
                            db=db, lead_id=entry.source_lead_id,
                            partner_id=entry.partner_id, level=entry.level,
                            released_by_id=current_employee.id, notes=notes
                        )
                    if not inner_rel.get('success') and not inner_rel.get('already_released'):
                        raise HTTPException(status_code=400, detail=inner_rel.get('error', 'Advance release failed'))
                    db.flush(); db.refresh(entry)

                _now = _get_ist()
                entry.status              = 'STAGE1_APPROVED'
                entry.stage_1_approved_by = (getattr(current_employee, 'full_name', '') or getattr(current_employee, 'name', '') or current_employee.emp_code or '').strip() or current_employee.emp_code
                entry.stage_1_approved_at = _now
                entry.updated_at          = _now
                entry.ledger_posted       = True
                if notes:
                    entry.notes = ((entry.notes or '') + f' | Stage1: {notes}').strip(' |')
                result = {'success': True, 'status': 'STAGE1_APPROVED', 'entry_number': entry.entry_number}

            elif act == 'mark_paid':
                if entry.status == 'DRAFT' and is_super:
                    inner1 = confirm_cash_income(db, target_id, entry.company_id, current_employee.id, notes)
                    if not inner1.get('success'):
                        raise HTTPException(status_code=400, detail=inner1.get('error', 'Auto-confirm failed'))
                    post_jv_confirm(db, entry, current_employee.id)
                    skipped_states.append('DRAFT->PENDING (super-skip)')
                    db.flush(); db.refresh(entry)
                if entry.status in ('PENDING', 'RELEASED'):
                    if entry.kind not in ('ADVANCE', 'SLAB_BONUS'):
                        try:
                            inner2 = release_cash_income(db, target_id, entry.company_id, current_employee.id, notes)
                            if inner2.get('success'):
                                post_jv_release(db, entry, current_employee.id)
                        except Exception as _rel_err:
                            logger.warning(f'[VGK-MARK-PAID] Auto-release notice: {_rel_err}')
                    _now_s1 = _get_ist()
                    entry.status = 'STAGE1_APPROVED'
                    entry.stage_1_approved_by = (getattr(current_employee, 'full_name', '') or current_employee.emp_code or '').strip() or current_employee.emp_code
                    entry.stage_1_approved_at = _now_s1
                    db.flush(); db.refresh(entry)
                    skipped_states.append('PENDING->STAGE1_APPROVED')

                if entry.status == 'PAID':
                    results.append({'success': True, 'status': 'PAID', 'entry_number': entry.entry_number, 'already_paid': True})
                    continue

                if entry.status != 'STAGE1_APPROVED':
                    raise HTTPException(status_code=400, detail=f'Entry must be PENDING, RELEASED or STAGE1_APPROVED to mark paid (got {entry.status})')

                inner = mark_paid_cash_income(
                    db, target_id, entry.company_id,
                    paid_by_id=current_employee.id,
                    payment_mode=(payment_mode or '').upper(),
                    bank_ledger_id=bank_ledger_id,
                    cash_staff_id=cash_staff_id,
                    utr=payment_utr,
                    notes=notes,
                    bypass=bool(bypass),
                )
                if not inner.get('success'):
                    if inner.get('error') == 'CAPPED_WARNING':
                        return inner
                    raise HTTPException(status_code=400, detail=inner.get('error', 'Mark-paid failed'))
                if skipped_states:
                    entry.skip_reason = (entry.skip_reason or '') + ' | ' + '; '.join(skipped_states)
                result = inner

            # Audit trail
            try:
                db.execute(text("SAVEPOINT sp_audit"))
                db.execute(text("""
                    INSERT INTO staff_audit_log
                      (employee_id, action, resource_type, resource_id, ip_address)
                    VALUES
                      (:eid, :ac, 'VGK_CASH_INCOME', :rid, :ip)
                """), {
                    'eid': current_employee.id,
                    'ac':  f'B2B-VGK-INCOME-{act.upper()}' + ('-SKIP' if skipped_states else ''),
                    'rid': entry.id, 'ip': '127.0.0.1',
                })
                db.execute(text("RELEASE SAVEPOINT sp_audit"))
            except Exception as _ae:
                try:
                    db.execute(text("ROLLBACK TO SAVEPOINT sp_audit"))
                except Exception:
                    pass

            db.commit()
            # Note: Announcement/Shoutout auto-posting on mark_paid removed per specification.
            # Announcements are now manually published via /staff/vgk/cash-income/post-shoutout endpoint.
            results.append(result)

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.exception(f'[VGK-UNIFIED] action={act} entry={target_id} failed')
            raise HTTPException(status_code=500, detail=f'{type(e).__name__}: {e}')

    return {'success': True, 'action': act, 'processed': len(results), 'result': results[0] if len(results) == 1 else None, 'results': results}


# ════════════════════════════════════════════════════════════════════════════
# DC_VGK_FIELD_ALLOWANCE_STAGE_20260615: Field Allowance Stage 1/2 endpoints
# ════════════════════════════════════════════════════════════════════════════

@router.get('/staff/vgk/field-allowances')
def list_field_allowances(
    company_id: Optional[int] = Query(None),
    status: Optional[str]     = Query(None),
    allowance_type: Optional[str] = Query(None),
    user_id: Optional[str]    = Query(None),
    month_year: Optional[str] = Query(None),
    search: Optional[str]     = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    DC_VGK_FIELD_ALLOWANCE_STAGE_20260615: List field allowance progress rows
    for the unified income page.  Returns data enriched with user name and company.
    """
    from app.models.field_allowance import FieldAllowanceProgress

    # DC-FIELD-ALLOW-SQL-001 (Jun 2026): original query had two bugs —
    # (a) LEFT JOIN associated_companies ON u.company_id: user table has no company_id column.
    # (b) JOIN "user" u: user table has no full_name/emp_code columns.
    # DC-FIELD-ALLOW-SQL-002 (Jun 2026): corrected to JOIN staff_employees (has full_name,
    # emp_code, email). company_id query param intentionally ignored (no column to filter on).
    q = db.execute(text("""
        SELECT
            fap.id,
            fap.user_id,
            fap.allowance_type,
            fap.month_year,
            fap.status,
            fap.amount_paid,
            fap.price_range_from,
            fap.price_range_to,
            fap.actual_price,
            fap.is_eligible,
            fap.eligibility_checked_at,
            fap.paid_at,
            fap.completion_percentage,
            fap.stage_1_approved_by,
            fap.stage_1_approved_at,
            fap.stage_2_paid_by,
            fap.stage_2_paid_at,
            se.full_name AS user_full_name,
            se.emp_code  AS user_emp_code,
            se.email     AS user_email
        FROM field_allowance_progress fap
        JOIN staff_employees se ON se.emp_code = fap.user_id
        WHERE 1=1
          {status_filter}
          {type_filter}
          {user_filter}
          {month_filter}
          {search_filter}
        ORDER BY fap.id DESC
        LIMIT :limit OFFSET :offset
    """.format(
        status_filter  = "AND fap.status = :status"       if status        else '',
        type_filter    = "AND fap.allowance_type = :atype" if allowance_type else '',
        user_filter    = "AND fap.user_id = :user_id"     if user_id       else '',
        month_filter   = "AND fap.month_year = :month"    if month_year    else '',
        search_filter  = "AND (se.full_name ILIKE :s OR se.emp_code ILIKE :s OR fap.month_year ILIKE :s)" if search else '',
    )), {
        k: v for k, v in {
            'status': status, 'atype': allowance_type, 'user_id': user_id,
            'month': month_year,
            's': f'%{search}%' if search else None,
            'limit': per_page, 'offset': (page - 1) * per_page,
        }.items() if v is not None
    }).fetchall()

    count_q = db.execute(text("""
        SELECT COUNT(*) FROM field_allowance_progress fap
        JOIN staff_employees se ON se.emp_code = fap.user_id
        WHERE 1=1
          {status_filter}
          {type_filter}
          {user_filter}
          {month_filter}
          {search_filter}
    """.format(
        status_filter  = "AND fap.status = :status"       if status        else '',
        type_filter    = "AND fap.allowance_type = :atype" if allowance_type else '',
        user_filter    = "AND fap.user_id = :user_id"     if user_id       else '',
        month_filter   = "AND fap.month_year = :month"    if month_year    else '',
        search_filter  = "AND (se.full_name ILIKE :s OR se.emp_code ILIKE :s OR fap.month_year ILIKE :s)" if search else '',
    )), {
        k: v for k, v in {
            'status': status, 'atype': allowance_type, 'user_id': user_id,
            'month': month_year,
            's': f'%{search}%' if search else None,
        }.items() if v is not None
    }).scalar() or 0

    rows = []
    for r in q:
        rows.append({
            'id':                   r.id,
            'user_id':              r.user_id,
            'user_name':            r.user_full_name or r.user_emp_code or r.user_id,
            'user_emp_code':        r.user_emp_code,
            'user_email':           r.user_email,
            'allowance_type':       r.allowance_type,
            'month_year':           r.month_year,
            'status':               r.status or 'Pending',
            'amount_paid':          float(r.amount_paid or r.actual_price or r.price_range_from or 0),
            'gross':                float(r.actual_price or r.price_range_from or 0),
            'is_eligible':          bool(r.is_eligible),
            'eligibility_checked_at': r.eligibility_checked_at.isoformat() if r.eligibility_checked_at else None,
            'paid_at':              r.paid_at.isoformat() if r.paid_at else None,
            'completion_pct':       float(r.completion_percentage or 0),
            'stage_1_approved_by':  r.stage_1_approved_by,
            'stage_1_approved_at':  r.stage_1_approved_at.isoformat() if r.stage_1_approved_at else None,
            'stage_2_paid_by':      r.stage_2_paid_by,
            'stage_2_paid_at':      r.stage_2_paid_at.isoformat() if r.stage_2_paid_at else None,
            'company_id':           None,
            'company_name':         None,
            'kind':                 'FIELD_ALLOWANCE',
            '_is_field_allowance':  True,
        })

    return {'success': True, 'total': count_q, 'page': page, 'per_page': per_page, 'data': rows}


@router.post('/staff/vgk/field-allowances/{fa_id}/stage1-approve')
def field_allowance_stage1_approve(
    fa_id: int,
    notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    DC_VGK_FIELD_ALLOWANCE_STAGE_20260615 — Stage 1: Approve a pending field allowance.
    Moves status from 'Pending' -> 'Stage1Approved'.
    WVV: Write sets stage_1_approved_by/at; Verify checks status==Pending; Validate emp exists.
    """
    from app.services.vgk_cash_income import _get_ist
    row = db.execute(text(
        "SELECT id, status FROM field_allowance_progress WHERE id = :fid LIMIT 1"
    ), {'fid': fa_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Field allowance record not found')
    if row.status not in ('Pending', None, ''):
        raise HTTPException(status_code=400, detail=f'Cannot approve — current status: {row.status}')

    now = _get_ist()
    db.execute(text("""
        UPDATE field_allowance_progress
           SET status               = 'Stage1Approved',
               stage_1_approved_by  = :approver,
               stage_1_approved_at  = :ts
         WHERE id = :fid
    """), {'approver': current_employee.emp_code, 'ts': now, 'fid': fa_id})
    db.execute(text("""
        INSERT INTO staff_audit_log (employee_id, action, resource_type, resource_id, ip_address)
        VALUES (:eid, 'FA-STAGE1-APPROVE', 'FIELD_ALLOWANCE', :rid, '127.0.0.1')
    """), {'eid': current_employee.id, 'rid': fa_id})
    db.commit()
    logger.info(f'[DC_VGK_FA_STAGE1] fa_id={fa_id} approved by {current_employee.emp_code}')
    return {'success': True, 'fa_id': fa_id, 'status': 'Stage1Approved',
            'approved_by': current_employee.emp_code, 'approved_at': now.isoformat()}


@router.post('/staff/vgk/field-allowances/{fa_id}/stage2-mark-paid')
def field_allowance_stage2_mark_paid(
    fa_id: int,
    notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    DC_VGK_FIELD_ALLOWANCE_STAGE_20260615 — Stage 2: Mark a Stage1Approved field allowance as paid.
    Moves status from 'Stage1Approved' -> 'Payout Completed'.
    WVV: Write sets stage_2_paid_by/at + paid_at; Verify checks status; Validate emp exists.
    """
    from app.services.vgk_cash_income import _get_ist
    row = db.execute(text(
        "SELECT id, status FROM field_allowance_progress WHERE id = :fid LIMIT 1"
    ), {'fid': fa_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Field allowance record not found')
    if row.status != 'Stage1Approved':
        raise HTTPException(status_code=400,
            detail=f'Cannot mark paid — must be Stage1Approved (got: {row.status})')

    now = _get_ist()
    db.execute(text("""
        UPDATE field_allowance_progress
           SET status           = 'Payout Completed',
               stage_2_paid_by  = :payer,
               stage_2_paid_at  = :ts,
               paid_at          = :ts
         WHERE id = :fid
    """), {'payer': current_employee.emp_code, 'ts': now, 'fid': fa_id})
    db.execute(text("""
        INSERT INTO staff_audit_log (employee_id, action, resource_type, resource_id, ip_address)
        VALUES (:eid, 'FA-STAGE2-MARK-PAID', 'FIELD_ALLOWANCE', :rid, '127.0.0.1')
    """), {'eid': current_employee.id, 'rid': fa_id})
    db.commit()
    logger.info(f'[DC_VGK_FA_STAGE2] fa_id={fa_id} marked paid by {current_employee.emp_code}')
    return {'success': True, 'fa_id': fa_id, 'status': 'Payout Completed',
            'paid_by': current_employee.emp_code, 'paid_at': now.isoformat()}


@router.get('/member/cash-income/earner-cards')
def member_earner_cards(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """
    [DC_PERF_TAB_001] Member: list their own PAID cash income entries that have
    a generated earner celebration card, plus lifetime earned total.
    Returns up to 20 most recent, newest first.
    """
    import re as _re
    from app.services.vgk_earner_card import _card_public_url

    entries = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.company_id == current_member.company_id,
        VGKCashIncomeEntry.partner_id == current_member.id,
        VGKCashIncomeEntry.status == 'PAID',
    ).order_by(VGKCashIncomeEntry.created_at.desc()).limit(50).all()

    cards = []
    for e in entries:
        notes = e.notes or ''
        m = _re.search(r'\[earner_card:([^\]]+)\]', notes)
        if not m:
            # Fallback: standard key pattern
            safe_num = (e.entry_number or str(e.id)).replace('/', '-')
            candidate_key = f'earner_cards/{safe_num}.png'
        else:
            candidate_key = m.group(1)
        url = _card_public_url(candidate_key)
        if url:
            cards.append({
                'id':             e.id,
                'entry_number':   e.entry_number,
                'commission_amount': float(e.commission_amount or 0),
                'net_payout':     float(e.net_payout or 0),
                'card_url':       url,
                'paid_at':        e.paid_at.isoformat() if e.paid_at else None,
            })
        if len(cards) >= 20:
            break

    earned_total = float(getattr(current_member, 'vgk_cash_earned_total', 0) or 0)
    return {'success': True, 'cards': cards, 'earned_total': earned_total}


@router.get("/staff/vgk/cash-income/{entry_id}/earner-card")
async def download_earner_card(
    entry_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Stream the earner celebration card PNG for a PAID entry.
    Generates on-the-fly if not cached; uses object storage if already generated.
    """
    from fastapi.responses import Response
    from sqlalchemy import text as sa_text
    from app.services.object_storage import storage_service

    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail='Entry not found')
    if entry.status != 'PAID':
        raise HTTPException(status_code=400, detail='Entry is not PAID yet')

    # Try to find card path from notes field
    card_key = None
    notes = entry.notes or ''
    import re as _re
    m = _re.search(r'\[earner_card:([^\]]+)\]', notes)
    if m:
        card_key = m.group(1)
    else:
        safe_num = (entry.entry_number or str(entry_id)).replace('/', '-')
        candidate = f'earner_cards/{safe_num}.png'
        test_bytes = storage_service.download_file(candidate)
        if test_bytes:
            card_key = candidate

    if card_key:
        img_bytes = storage_service.download_file(card_key)
        if img_bytes:
            return Response(
                content=img_bytes,
                media_type='image/png',
                headers={'Content-Disposition': f'attachment; filename="{card_key.split("/")[-1]}"'},
            )

    # Not found — generate now synchronously
    try:
        from app.services.vgk_earner_card import (
            compose_earner_card, _get_kyc_photo_bytes,
        )
        row = db.execute(sa_text("""
            SELECT p.partner_name, p.partner_code, p.city, p.state,
                   p.contact_person_1_designation,
                   e.commission_amount, e.partner_id,
                   p.name_title, p.gender
            FROM vgk_cash_income_entries e
            JOIN official_partners p ON p.id = e.partner_id
            WHERE e.id = :eid
        """), {'eid': entry_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Partner data missing')
        pname, pcode, city, state, desig, gross, pid, _ntitle, _gender = row
        # Derive display title: stored name_title wins; fall back to gender
        _t = (_ntitle or '').strip()
        if not _t:
            _g = (_gender or '').strip().lower()
            _t = 'Mr' if _g in ('male', 'm') else ('Ms' if _g in ('female', 'f') else '')
        name_title = _t
        # DC-FIX: compute overall from PAID SUM — vgk_cash_earned_total column
        # may be stale when skip-state release bypassed the normal release path.
        paid_sum = db.execute(sa_text("""
            SELECT COALESCE(SUM(commission_amount), 0)
            FROM vgk_cash_income_entries
            WHERE partner_id = :pid AND status = 'PAID'
        """), {'pid': pid}).fetchone()
        overall = float(paid_sum[0] or 0) if paid_sum else float(gross or 0)
        loc_parts = [p for p in [city, state] if p and str(p).strip()]
        photo = _get_kyc_photo_bytes(db, pid)
        img_bytes = compose_earner_card(
            partner_name     = pname or 'VGK Member',
            partner_code     = pcode or '',
            location         = ', '.join(loc_parts),
            designation      = desig or 'Channel Partner',
            gross_amount     = float(gross or 0),
            overall_earnings = overall,
            photo_bytes      = photo,
            name_title       = name_title,
        )
        safe_num = (entry.entry_number or str(entry_id)).replace('/', '-')
        storage_service.upload_file(f'earner_cards/{safe_num}.png', img_bytes)
        return Response(
            content=img_bytes,
            media_type='image/png',
            headers={'Content-Disposition': f'attachment; filename="earner-card-{safe_num}.png"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f'[VGK-EARNER-CARD] on-demand generate failed: {e}')
        raise HTTPException(status_code=500, detail=f'Card generation failed: {e}')


@router.post('/staff/vgk/cash-income/post-shoutout')
def post_shoutout(
    entry_ids: List[int] = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Manual Admin Action: Post Announcement / Shoutout for selected payment entries.
    Groups selected entries by partner and generates ONE combined earner card image
    and ONE announcement record per payment operation batch. Prevents duplicates.
    """
    from app.services.vgk_earner_card import run_earner_celebration_batch
    from collections import defaultdict
    from sqlalchemy import text as sa_text

    if not entry_ids:
        raise HTTPException(status_code=400, detail="entry_ids list is required")

    clean_ids = list(set([int(x) for x in entry_ids if x is not None]))
    if not clean_ids:
        raise HTTPException(status_code=400, detail="No valid entry_ids provided")

    # Fetch entries
    entries = db.execute(sa_text("""
        SELECT id, partner_id, status, commission_amount, notes
        FROM vgk_cash_income_entries
        WHERE id IN :eids
    """), {'eids': tuple(clean_ids)}).fetchall()

    if not entries:
        raise HTTPException(status_code=404, detail="No matching payment entries found")

    # Group entry IDs by partner_id
    partner_groups = defaultdict(list)
    for e in entries:
        partner_groups[e.partner_id].append(e.id)

    results = []
    for pid, p_eids in partner_groups.items():
        res = run_earner_celebration_batch(db, partner_id=pid, entry_ids=p_eids)
        results.append({
            'partner_id': pid,
            'result': res
        })

    all_already = all(r['result'].get('already_published') for r in results)
    first_ann_id = next((r['result'].get('announcement_id') for r in results if r['result'].get('announcement_id')), None)

    return {
        'success': True,
        'already_published': all_already,
        'announcement_id': first_ann_id,
        'results': results,
        'message': 'Announcement already published for these payment records' if all_already else 'Announcement & shoutout card created successfully'
    }


@router.post("/staff/vgk/cash-income/{entry_id}/send-whatsapp")
async def resend_earner_whatsapp(
    entry_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Manually resend WhatsApp congratulations for a PAID entry.
    """
    import re as _re
    from sqlalchemy import text as sa_text
    from app.services.vgk_earner_card import _send_earner_wa, _ensure_wa_trigger, _card_public_url

    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail='Entry not found')
    if entry.status != 'PAID':
        raise HTTPException(status_code=400, detail='Entry is not PAID yet')

    row = db.execute(sa_text("""
        SELECT p.partner_name, p.partner_code, p.whatsapp_number,
               e.commission_amount, e.partner_id
        FROM vgk_cash_income_entries e
        JOIN official_partners p ON p.id = e.partner_id
        WHERE e.id = :eid
    """), {'eid': entry_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Partner data missing')

    pname, pcode, phone, gross, pid = row
    if not phone or len(str(phone).strip()) < 10:
        raise HTTPException(status_code=400, detail='No WhatsApp number on file for this partner')

    # DC-FIX: compute overall from PAID SUM — vgk_cash_earned_total column
    # may be stale when skip-state release bypassed the normal release path.
    paid_sum = db.execute(sa_text("""
        SELECT COALESCE(SUM(commission_amount), 0)
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid AND status = 'PAID'
    """), {'pid': pid}).fetchone()
    overall = float(paid_sum[0] or 0) if paid_sum else float(gross or 0)

    # Extract card storage key from entry notes; fallback: derive from entry_number
    # (same derivation used in run_earner_celebration so key matches what was uploaded)
    _notes = entry.notes or ''
    _card_m = _re.search(r'\[earner_card:([^\]]+)\]', _notes)
    if _card_m:
        _card_key = _card_m.group(1)
    else:
        _safe_num = (getattr(entry, 'entry_number', None) or str(entry_id)).replace('/', '-')
        _card_key = f'earner_cards/{_safe_num}.png'

    img_result = {'success': False, 'reason': 'no_card_url', 'wamid': ''}
    try:
        _ensure_wa_trigger(db)
        db.flush()
        img_result = _send_earner_wa(db, pname, pcode, phone,
                                     float(gross or 0), overall, entry_id,
                                     card_url=_card_public_url(_card_key)) or img_result
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f'[VGK-EARNER-WA] resend failed: {e}')
        raise HTTPException(status_code=500, detail=f'WhatsApp send failed: {e}')

    return {
        'success':          True,
        'sent_to':          phone,
        'partner':          pname,
        'card_image_sent':  img_result.get('success', False),
        'card_image_reason': img_result.get('reason', '') or None,
    }


@router.get('/member/company-payouts')
def get_member_company_payouts(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """
    [DC-COMPANY-PAYOUT-001] Returns all company-side payouts for the current VGK member.
    Each record includes gross_amount, tds_pct, tds_amount, net_amount (released payout).
    """
    from app.models.staff_accounts import VGKCompanyPayout
    payouts = (
        db.query(VGKCompanyPayout)
        .filter(VGKCompanyPayout.partner_id == current_member.id)
        .order_by(VGKCompanyPayout.created_at.desc())
        .all()
    )
    total_gross = sum(float(p.gross_amount  or 0) for p in payouts)
    total_admin = sum(float(p.admin_charges or 0) for p in payouts)
    total_tds   = sum(float(p.tds_amount   or 0) for p in payouts)
    total_net   = sum(float(p.net_amount   or 0) for p in payouts)
    return {
        "success":     True,
        "count":       len(payouts),
        "total_gross": total_gross,
        "total_admin": total_admin,
        "total_tds":   total_tds,
        "total_net":   total_net,
        "data":        [p.to_dict() for p in payouts],
    }


@router.post("/staff/vgk/cash-income/seed-ledgers")
def seed_income_ledgers(
    company_id: int = Query(..., description="Company ID to seed (2=Zynova, 3=MNR, 4=MyntReal)"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Idempotently seed all standard + VGK-specific ledger masters for a company.
    Restricted to EA / Super staff only.
    """
    from app.services.vgk_cash_income import seed_default_income_ledgers, is_super_skip_user
    if not is_super_skip_user(current_employee):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail='Super / EA access required')
    result = seed_default_income_ledgers(db, company_id)
    return {'success': True, **result}


@router.get("/staff/vgk/member-executive-summary/{partner_id}")
def get_member_executive_summary(
    partner_id: str,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    [DC-VGK-EXEC-SUMMARY-001] Executive-Level Member Earning & Progress Breakdown
    Includes:
    - Stage-wise files breakup (Stage 1, Stage 2, Stage 3, Active, Lost)
    - Financial buckets (Overall Earned, Earned Till Date, Potential, Active Advance, Lost Lead Advance)
    - 50% Capped Lost Lead Advance Deduction & Carry-Forward Ledger
    - Payout Eligibility Status (Eligible / Under Warning / Blocked)
    """
    from app.models.staff_accounts import OfficialPartner
    from app.models.crm import CRMLead
    from app.models.staff import StaffEmployee
    from sqlalchemy import text

    # Locate partner
    partner = None
    if str(partner_id).isdigit():
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == int(partner_id)).first()
    if not partner:
        partner = db.query(OfficialPartner).filter(OfficialPartner.partner_code == str(partner_id).strip()).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Channel Partner not found")

    p_id = partner.id
    p_code = getattr(partner, 'partner_code', None) or f"VGK{partner.id:06d}"

    # Load potential earnings from earner card service
    from app.services.vgk_earner_card import get_bulk_partner_potential_earning
    pot_map = get_bulk_partner_potential_earning(db, [p_id], exclude_l1=False)
    potential_earnings = float(pot_map.get(p_id, 0.0))

    # Load partner leads
    leads = db.execute(text("""
        SELECT id, name, phone, city, status, solar_pipeline_status, submit_date, created_at, updated_at, deal_value
        FROM crm_leads
        WHERE (associated_partner_id = :pid OR primary_owner_id = :pid OR source_ref_id = CAST(:pid AS VARCHAR) OR id IN (
            SELECT source_lead_id FROM vgk_cash_income_entries WHERE partner_id = :pid AND source_lead_id IS NOT NULL
        ))
        ORDER BY created_at DESC
    """), {"pid": p_id}).fetchall()

    # Load NON-CANCELLED income entries from vgk_cash_income_entries
    income_rows = db.execute(text("""
        SELECT 
            id, entry_number, source_lead_id, level, partner_id, kind,
            commission_amount AS gross_amount, 
            status, created_at, commission_pct AS calc_pct
        FROM vgk_cash_income_entries
        WHERE partner_id = :pid AND (status IS NULL OR status NOT IN ('CANCELLED', 'REJECTED'))
        ORDER BY created_at DESC
    """), {"pid": p_id}).fetchall()

    total_files = len(leads)
    stage1_count = 0
    stage1_total_adv = 0.0
    stage2_count = 0
    stage2_total_adv = 0.0
    stage3_count = 0
    stage3_total_comm = 0.0
    active_count = 0
    lost_count = 0
    lost_lead_advances_paid = 0.0

    lost_leads_ledger = []

    # Separate advances chronologically by lead: 1st advance = Stage 1, 2nd+ advance = Stage 2
    adv_by_lead = {}
    stage3_count = 0
    stage3_total_comm = 0.0
    bonus_count = 0
    bonus_total_amt = 0.0

    for r in income_rows:
        k = (r.kind or '').upper()
        amt = float(r.gross_amount or 0)
        lid = r.source_lead_id
        
        if k in ('ADVANCE', 'DVR_ADVANCE', 'STAGE1_ADVANCE', 'STAGE2_ADVANCE', 'STAGE_2_ADVANCE'):
            if lid not in adv_by_lead:
                adv_by_lead[lid] = []
            adv_by_lead[lid].append((amt, r))
        elif k in ('COMMISSION', 'SENIOR_COMM', 'BRAND_COMMISSION'):
            stage3_count += 1
            stage3_total_comm += amt
        elif k in ('SLAB_BONUS', 'BONANZA_BONUS', 'EXTRA_COMMISSION', 'REFERRAL_BONUS'):
            bonus_count += 1
            bonus_total_amt += amt

    stage1_count = 0
    stage1_total_adv = 0.0
    stage2_count = 0
    stage2_total_adv = 0.0

    for lid, adv_list in adv_by_lead.items():
        stage1_count += 1
        stage1_total_adv += adv_list[0][0]
        if len(adv_list) > 1:
            for extra_adv in adv_list[1:]:
                stage2_count += 1
                stage2_total_adv += extra_adv[0]

    from datetime import date as date_cls
    today_dt = date_cls.today()

    b_10 = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    b_20 = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    b_30 = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    b_over30 = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}

    stg_sub = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    stg_bnk = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    stg_pnd = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    stg_cmp = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}
    stg_rst = {'cnt': 0, 'deal_val': 0.0, 'potential': 0.0}

    for l in leads:
        st = (l.status or '').lower()
        pipe_st = (getattr(l, 'solar_pipeline_status', None) or '').lower()
        
        sub_dt = getattr(l, 'submit_date', None) or getattr(l, 'created_at', None) or today_dt
        if hasattr(sub_dt, 'date'):
            sub_dt = sub_dt.date()
        elif isinstance(sub_dt, str):
            try: sub_dt = datetime.strptime(sub_dt[:10], '%Y-%m-%d').date()
            except: sub_dt = today_dt
            
        age_days = max(0, (today_dt - sub_dt).days)
        val = float(getattr(l, 'deal_value', 198000) or 198000)
        pot = round(val * 0.04, 2)
        
        if age_days <= 10:
            b_10['cnt'] += 1; b_10['deal_val'] += val; b_10['potential'] += pot
        elif age_days <= 20:
            b_20['cnt'] += 1; b_20['deal_val'] += val; b_20['potential'] += pot
        elif age_days <= 30:
            b_30['cnt'] += 1; b_30['deal_val'] += val; b_30['potential'] += pot
        else:
            b_over30['cnt'] += 1; b_over30['deal_val'] += val; b_over30['potential'] += pot
            
        # Solar Pipeline Stage Classification based on actual workflow stage
        if pipe_st in ('loan_rejected', 'bank_loan_rejected', 'rejected', 'cancelled', 'different_vendor', 'opted_out') or st in ('lost', 'cancelled', 'rejected', 'loan_rejected', 'bank_loan_rejected'):
            stg_rst['cnt'] += 1; stg_rst['deal_val'] += val; stg_rst['potential'] += pot
            lost_count += 1
        elif pipe_st in ('completed', 'installed', 'subsidy_pending', 'subsidy_claimed', 'commissioned', 'work_completed') or st == 'completed':
            stg_cmp['cnt'] += 1; stg_cmp['deal_val'] += val; stg_cmp['potential'] += pot
        elif pipe_st in ('installation_pending', 'material_dispatch', 'work_in_progress', 'net_meter_pending', 'net_metering_pending') or st in ('in_progress', 'installation'):
            stg_pnd['cnt'] += 1; stg_pnd['deal_val'] += val; stg_pnd['potential'] += pot
            active_count += 1
        elif pipe_st in ('pending_with_bank', 'bank_loan_process', 'loan_submitted', 'bank_process', 'sanction_pending') or st in ('loan_process', 'pending_with_bank'):
            stg_bnk['cnt'] += 1; stg_bnk['deal_val'] += val; stg_bnk['potential'] += pot
            active_count += 1
        else:
            stg_sub['cnt'] += 1; stg_sub['deal_val'] += val; stg_sub['potential'] += pot
            active_count += 1

    # Check for lost leads where advance was paid (checking both status AND solar_pipeline_status)
    lost_lead_rows = db.execute(text("""
        SELECT c.id AS lead_id, c.name, c.phone, c.status, c.solar_pipeline_status, c.created_at, c.submit_date,
               COALESCE(SUM(v.commission_amount), 0) AS adv_paid
        FROM crm_leads c
        JOIN vgk_cash_income_entries v ON v.source_lead_id = c.id
        WHERE (c.associated_partner_id = :pid OR c.primary_owner_id = :pid OR v.partner_id = :pid)
          AND (c.status IN ('lost', 'cancelled', 'rejected') OR c.solar_pipeline_status IN ('loan_rejected', 'bank_loan_rejected', 'rejected', 'cancelled', 'different_vendor', 'opted_out'))
          AND v.kind IN ('ADVANCE', 'DVR_ADVANCE', 'STAGE1_ADVANCE', 'STAGE2_ADVANCE', 'COMMISSION')
          AND (v.status IS NULL OR v.status NOT IN ('CANCELLED', 'REJECTED'))
        GROUP BY c.id, c.name, c.phone, c.status, c.solar_pipeline_status, c.created_at, c.submit_date
    """), {"pid": p_id}).fetchall()

    for l in lost_lead_rows:
        tot_adv = float(l.adv_paid or 0)
        if tot_adv > 0:
            lost_lead_advances_paid += tot_adv
            pipe_st_str = (l.solar_pipeline_status or '').lower()
            reason_label = (l.solar_pipeline_status or l.status or "Rejected / Lost").replace("_", " ").title()
            if "loan_rejected" in pipe_st_str:
                reason_label = "Loan Rejected by Bank"
            elif "different_vendor" in pipe_st_str:
                reason_label = "Selected Different Vendor"

            lost_leads_ledger.append({
                "lead_id": l.lead_id,
                "customer_name": l.name or f"Lead #{l.lead_id}",
                "phone": l.phone or "—",
                "status": l.status,
                "pipeline_status": l.solar_pipeline_status or l.status or "lost",
                "rejection_reason": reason_label,
                "submitted_date": (l.submit_date or l.created_at).strftime("%Y-%m-%d") if (l.submit_date or l.created_at) else "—",
                "stage1_adv": tot_adv,
                "stage2_adv": 0.0,
                "total_lost_adv_paid": tot_adv,
                "deducted_so_far": 0.0,
                "remaining_balance": tot_adv
            })

    # Compute 50% capping lost lead advance deduction across income entries (applied chronologically after lead rejection date, excluding bonuses)
    total_lost_adv_deducted = 0.0
    itemized_income_breakdown = []

    gross_overall_earned = sum(float(r.gross_amount or 0) for r in income_rows)
    earned_till_date_net = round(gross_overall_earned * 0.90, 2)

    # Track lost advance pool dynamically per rejection date
    for r in income_rows:
        gross = float(r.gross_amount or 0)
        k = (r.kind or '').upper()
        s1 = gross if k in ('ADVANCE', 'DVR_ADVANCE', 'STAGE1_ADVANCE') else 0.0
        s2 = gross if k in ('STAGE2_ADVANCE', 'STAGE_2_ADVANCE') else 0.0
        entry_created = getattr(r, 'created_at', None) or today_dt

        # Calculate lost advance pool available at the time of entry creation
        active_lost_pool = 0.0
        for lr in lost_lead_rows:
            rejection_time = getattr(lr, 'updated_at', None) or getattr(lr, 'created_at', None) or today_dt
            if (entry_created and rejection_time and entry_created >= rejection_time) or getattr(r, 'status', '') == 'PENDING':
                active_lost_pool += float(lr.adv_paid or 0)

        lost_lead_deduction = 0.0
        if active_lost_pool > 0 and k not in ('SLAB_BONUS', 'BONANZA_BONUS', 'EXTRA_COMMISSION', 'REFERRAL_BONUS'):
            # Calculate prior lost lead advance deductions applied on entries created after rejection time
            prior_ded_sum = 0.0
            for prev_item in itemized_income_breakdown:
                prev_k = (prev_item.get('kind') or '').upper()
                if prev_k not in ('SLAB_BONUS', 'BONANZA_BONUS', 'EXTRA_COMMISSION', 'REFERRAL_BONUS'):
                    prior_ded_sum += float(prev_item.get('lost_lead_deduction', 0.0))

            avail_pool = max(0.0, active_lost_pool - prior_ded_sum)
            if avail_pool > 0 and gross > 0:
                max_50_cap = round(gross * 0.50, 2)
                lost_lead_deduction = round(min(avail_pool, max_50_cap), 2)
                total_lost_adv_deducted += lost_lead_deduction

        total_adv_paid = lost_lead_deduction
        bal_gross = max(0.0, round(gross - total_adv_paid, 2))
        admin_fee = round(bal_gross * 0.08, 2)
        tds_fee = round(bal_gross * 0.02, 2)
        net_payable = round(bal_gross * 0.90, 2)

        itemized_income_breakdown.append({
            "entry_id": r.id,
            "entry_number": getattr(r, 'entry_number', None) or f"VCI-{r.id}",
            "created_at": r.created_at.strftime("%Y-%m-%d") if getattr(r, 'created_at', None) else "—",
            "client_name": getattr(r, 'client_name', '—') or "—",
            "kind": getattr(r, 'kind', 'COMMISSION'),
            "gross_amount": gross,
            "stage1_adv": s1,
            "stage2_adv": s2,
            "lost_lead_deduction": lost_lead_deduction,
            "advance_paid_total": total_adv_paid,
            "balance_gross": bal_gross,
            "admin_fee": admin_fee,
            "tds_fee": tds_fee,
            "net_amount": net_payable,
            "status": r.status or "Pending"
        })

    # Update lost leads ledger deduction details
    remaining_lost_carry_forward = lost_lead_advances_paid - total_lost_adv_deducted
    running_ded = total_lost_adv_deducted
    for item in lost_leads_ledger:
        adv = item["total_lost_adv_paid"]
        ded = min(adv, running_ded)
        running_ded -= ded
        item["deducted_so_far"] = round(ded, 2)
        item["remaining_balance"] = round(adv - ded, 2)

    # 20-Day Inactivity Check: Count leads submitted in last 20 days (< 10 Days + 11-20 Days)
    recent_leads_in_20_days = b_10['cnt'] + b_20['cnt']

    p_status = str(getattr(partner, 'status', None) or ('ACTIVE' if getattr(partner, 'is_active', True) else 'INACTIVE')).lower()
    if p_status in ['inactive', 'blocked', 'suspended', 'disabled']:
        payout_status = "BLOCKED"
        payout_status_label = "🔴 Blocked / Administrative Hold"
    elif remaining_lost_carry_forward > 0 and recent_leads_in_20_days == 0:
        payout_status = "WARNING"
        payout_status_label = "⚠️ Under Warning / Inactive (No Leads in 20 Days) & Lost Lead Carry-Forward"
    elif remaining_lost_carry_forward > 0:
        payout_status = "WARNING"
        payout_status_label = "⚠️ Under Warning / Lost Lead Advance Carry-Forward"
    elif recent_leads_in_20_days == 0:
        payout_status = "WARNING"
        payout_status_label = "⚠️ Under Warning / Inactive Pipeline (No Leads Submitted in Last 20 Days)"
    else:
        payout_status = "ELIGIBLE"
        payout_status_label = "🟢 Eligible for Payout Disbursal"

    p_name = getattr(partner, 'partner_name', None) or getattr(partner, 'full_name', None) or getattr(partner, 'name', 'Channel Partner')
    p_code = getattr(partner, 'partner_code', None) or getattr(partner, 'user_code', None) or f"VGK{partner.id:06d}"
    reg_date = getattr(partner, 'created_at', None) or getattr(partner, 'registered_at', None)

    # Compute Gross Pending, Lost Lead Deductions (Pending), and Net Pending Payable
    gross_pending = sum(
        float(r.get('gross_amount', 0))
        for r in itemized_income_breakdown
        if str(r.get('status', '')).upper() in ('DRAFT', 'PENDING', 'STAGE1_APPROVED')
    )
    lost_ded_pending = sum(
        float(r.get('lost_lead_deduction', 0))
        for r in itemized_income_breakdown
        if str(r.get('status', '')).upper() in ('DRAFT', 'PENDING', 'STAGE1_APPROVED')
    )
    net_pending = sum(
        float(r.get('net_amount', 0))
        for r in itemized_income_breakdown
        if str(r.get('status', '')).upper() in ('DRAFT', 'PENDING', 'STAGE1_APPROVED')
    )

    return {
        "success": True,
        "member_id": partner.id,
        "member_name": p_name,
        "user_code": p_code,
        "phone": getattr(partner, 'phone', '—') or "—",
        "designation": getattr(partner, 'designation_label', '') or getattr(partner, 'category', '') or "Channel Partner",
        "registered_at": reg_date.strftime("%Y-%m-%d") if reg_date else "—",
        "payout_status": payout_status,
        "payout_status_label": payout_status_label,
        "files_summary": {
            "total_files": total_files,
            "stage1_files": stage1_count,
            "stage1_total_adv": round(stage1_total_adv, 2),
            "stage2_files": stage2_count,
            "stage2_total_adv": round(stage2_total_adv, 2),
            "stage3_completed_files": stage3_count,
            "stage3_total_comm": round(stage3_total_comm, 2),
            "bonus_entries_count": bonus_count,
            "bonus_total_amt": round(bonus_total_amt, 2),
            "active_pipeline_files": active_count,
            "potential_earnings": round(potential_earnings, 2),
            "lost_files": lost_count,
            "lost_lead_advances_paid": round(lost_lead_advances_paid, 2)
        },
        "financial_buckets": {
            "overall_gross_earned": round(gross_overall_earned, 2),
            "earned_till_date_net": round(earned_till_date_net, 2),
            "potential_earnings": round(potential_earnings, 2),
            "active_files_advance_paid": round(stage1_total_adv + stage2_total_adv, 2),
            "bonus_extra_value": round(bonus_total_amt, 2),
            "lost_lead_advances_paid": round(lost_lead_advances_paid, 2),
            "total_lost_adv_deducted": round(total_lost_adv_deducted, 2),
            "remaining_lost_carry_forward": round(remaining_lost_carry_forward, 2),
            "gross_pending": round(gross_pending, 2),
            "lost_lead_adv_deducted_pending": round(lost_ded_pending, 2),
            "net_pending": round(net_pending, 2),
            "max_deduction_cap_pct": "50%"
        },
        "leads_ageing_breakup": {
            "under_10_days": {"files": b_10['cnt'], "deal_valuation": round(b_10['deal_val'], 2), "potential_earning": round(b_10['potential'], 2)},
            "days_11_to_20": {"files": b_20['cnt'], "deal_valuation": round(b_20['deal_val'], 2), "potential_earning": round(b_20['potential'], 2)},
            "days_21_to_30": {"files": b_30['cnt'], "deal_valuation": round(b_30['deal_val'], 2), "potential_earning": round(b_30['potential'], 2)},
            "over_30_days":  {"files": b_over30['cnt'], "deal_valuation": round(b_over30['deal_val'], 2), "potential_earning": round(b_over30['potential'], 2)}
        },
        "pipeline_stage_breakup": {
            "submitted":     {"files": stg_sub['cnt'], "deal_valuation": round(stg_sub['deal_val'], 2), "potential_earning": round(stg_sub['potential'], 2)},
            "at_bank":       {"files": stg_bnk['cnt'], "deal_valuation": round(stg_bnk['deal_val'], 2), "potential_earning": round(stg_bnk['potential'], 2)},
            "net_pending":   {"files": stg_pnd['cnt'], "deal_valuation": round(stg_pnd['deal_val'], 2), "potential_earning": round(stg_pnd['potential'], 2)},
            "completed":     {"files": stg_cmp['cnt'], "deal_valuation": round(stg_cmp['deal_val'], 2), "potential_earning": round(stg_cmp['potential'], 2)},
            "rejected_lost": {"files": stg_rst['cnt'], "deal_valuation": round(stg_rst['deal_val'], 2), "potential_earning": round(stg_rst['potential'], 2)}
        },
        "lost_leads_adjustment_ledger": lost_leads_ledger,
        "itemized_breakdown": itemized_income_breakdown
    }


@router.post("/members/{member_id}/send-whatsapp-statement")
@router.post("/staff/vgk/member-executive-summary/{member_id}/send-whatsapp")
def send_member_whatsapp_statement(
    member_id: str,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Dispatches member revenue breakup statement directly to member's WhatsApp phone via local WhatsApp Bot Gateway (port 5002).
    Does NOT use direct wa.me link. Returns immediate on-screen status confirmation.
    """
    import requests
    
    # 1. Fetch executive summary for this member
    summary = get_member_executive_summary(partner_id=member_id, db=db, current_employee=current_employee)
    
    m_name = summary.get("member_name", "Channel Partner")
    m_code = summary.get("user_code", "VGK")
    phone = summary.get("phone", "").strip()
    desig = summary.get("designation", "Channel Partner")
    st_lbl = summary.get("payout_status_label", "🟢 Eligible for Payout Disbursal")
    
    b = summary.get("financial_buckets", {})
    f = summary.get("files_summary", {})

    clean_phone = "".join(ch for ch in phone if ch.isdigit())
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Member does not have a valid WhatsApp phone number registered.")

    # 2. Format clean revenue statement text
    msg_text = (
        f"🌅 *GOOD MORNING! YOUR VGK4U DAILY REVENUE & PROGRESS UPDATE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Member*: {m_name} ({m_code})\n"
        f"📱 *Phone*: {phone}\n"
        f"🏷️ *Designation*: {desig}\n"
        f"📌 *Payout Status*: {st_lbl}\n\n"
        f"💰 *FINANCIAL REVENUE BREAKUP*\n"
        f"• Overall Earned (Gross): ₹{int(b.get('overall_gross_earned', 0)):,}\n"
        f"• Earned Till Date (Released): ₹{int(b.get('earned_till_date_net', 0)):,}\n"
        f"• Potential Earnings: ₹{int(b.get('potential_earnings', 0)):,}\n"
        f"• L0 Bonus & Extra Value: ₹{int(b.get('bonus_extra_value', 0)):,}\n"
        f"• Active Files Advance: ₹{int(b.get('active_files_advance_paid', 0)):,}\n"
        f"• Gross Pending (Draft + Pending): ₹{int(b.get('gross_pending', 0)):,}\n"
        f"• Lost Lead Adv. Deductions: ₹{int(b.get('lost_lead_adv_deducted_pending', 0) or b.get('total_lost_adv_deducted', 0)):,}\n"
        f"• Net Pending Payable: ₹{int(b.get('net_pending', 0)):,}\n\n"
        f"📂 *STAGE-WISE FILE BREAKUP*\n"
        f"• Total Sourced Files: {f.get('total_files', 0)}\n"
        f"• Stage 1 Adv. Paid: {f.get('stage1_files', 0)} files (₹{int(f.get('stage1_total_adv', 0)):,})\n"
        f"• Stage 2 Adv. Paid: {f.get('stage2_files', 0)} files (₹{int(f.get('stage2_total_adv', 0)):,})\n"
        f"• Stage 3 Completed: {f.get('stage3_completed_files', 0)} files (₹{int(f.get('stage3_total_comm', 0)):,})\n"
        f"• L0 Bonus & Extra Entries: {f.get('bonus_entries_count', 0)} entries (₹{int(f.get('bonus_total_amt', 0)):,})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌟 _Wishing you a productive and successful day ahead!_\n"
        f"💬 _Auto-generated VGK4U Executive Member Revenue Report_"
    )

    # 3. Send payload via local WhatsApp Bot Gateway (http://localhost:5002/api/send-message)
    bot_url = "http://localhost:5002/api/send-message"
    bot_payload = {
        "phone": clean_phone,
        "message": msg_text
    }

    try:
        resp = requests.post(bot_url, json=bot_payload, timeout=8)
        res_json = resp.json() if resp.status_code == 200 else {}
        if resp.status_code == 200 and res_json.get("success"):
            return {
                "success": True,
                "message": f"Revenue statement successfully sent to {m_name} ({phone}) via WhatsApp Bot!",
                "member_name": m_name,
                "phone": phone,
                "bot_message_id": res_json.get("message_id") or res_json.get("wamid")
            }
        else:
            err = res_json.get("error") or f"Bot returned HTTP {resp.status_code}"
            raise HTTPException(status_code=500, detail=f"WhatsApp Bot dispatch failed: {err}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="WhatsApp Bot is currently offline on port 5002. Please ensure the Bot daemon is running.")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=str(exc))


