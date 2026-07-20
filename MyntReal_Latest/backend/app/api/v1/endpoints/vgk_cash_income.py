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
from typing import Optional

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
) -> dict:
    """DC-BULK-ENRICH-001: O(1) enrichment using pre-fetched in-memory maps.

    Replaces _enrich_entry() inside unified_list to eliminate N+1 queries.
    All four maps are keyed by integer ID and built before the loop.
    """
    d = entry.to_dict()
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
    Sales staff: confirm (DRAFT → PENDING) or reject (DRAFT → CANCELLED).
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
        raise HTTPException(status_code=400, detail=result.get('error', 'Operation failed'))

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
    Accounts staff: release PENDING → RELEASED.
    Deducts 8% admin charges + 2% TDS; credits net to partner's vgk_cash_wallet.
    """
    from app.services.vgk_cash_income import release_cash_income

    result = release_cash_income(db, entry_id, company_id, current_employee.id, notes)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Release failed'))

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

    # Build map: (ref_type, ref_id) → wallet_after of matching PAYOUT txn
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
            # post-payout value (e.g. ₹0) is confusing — the member sees "+₹1,000 → Balance ₹0".
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
    DC-SENIOR-COMM-001 (Jun 2026): When a Solar Advance (kind=ADVANCE) is Released,
    create a SENIOR_COMM entry (₹500 gross / ₹450 net) for the direct reporting senior
    and deduct ₹500 inline from the senior's current PENDING L2 COMMISSION entry.

    WVV:
      Write  — creates VGKCashIncomeEntry(kind=SENIOR_COMM) and/or mutates senior's L2 entry
      Verify — only fires if partner has parent_partner_id
      Validate — deducted amounts are floored at 0 (never go negative)
    """
    from app.services.vgk_cash_income import _get_ist

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()
    if not partner or not getattr(partner, 'parent_partner_id', None):
        return  # No direct reporting senior — skip

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

    if vgk_mode:
        # VGK programme view: join on official_partners and filter by VGK_TEAM category.
        # This surfaces VGK income regardless of which product-company the entry sits under.
        q = (
            db.query(VGKCashIncomeEntry)
            .join(OfficialPartner, OfficialPartner.id == VGKCashIncomeEntry.partner_id)
            .filter(OfficialPartner.category == 'VGK_TEAM')
        )
    else:
        if company_id is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="company_id is required when vgk_mode is false")
        # Exclude VGK_TEAM partners from company tabs — VGK entries belong on the Zynova/VGK-All tab
        q = (
            db.query(VGKCashIncomeEntry)
            .join(OfficialPartner, OfficialPartner.id == VGKCashIncomeEntry.partner_id)
            .filter(VGKCashIncomeEntry.company_id == company_id)
            .filter(OfficialPartner.category != 'VGK_TEAM')
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
    entries = q.order_by(VGKCashIncomeEntry.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    is_super = is_super_skip_user(current_employee)
    _dept_raw = getattr(current_employee, 'department', '') or ''
    if hasattr(_dept_raw, 'value'):
        _dept_raw = _dept_raw.value
    elif hasattr(_dept_raw, 'name'):
        _dept_raw = _dept_raw.name
    dept = str(_dept_raw or '').lower()
    can_sales    = is_super or 'sales' in dept or 'crm' in dept
    can_accounts = is_super or 'account' in dept or 'finance' in dept
    can_pay      = is_super or 'finance' in dept or 'bank' in dept or 'account' in dept

    def _actions_for(e):
        # DC-NO-RELEASE-001: Release button removed. All income flows PENDING→Stage1→Stage2(Paid).
        acts = []
        if e.status == 'DRAFT' and (can_sales or is_super):
            acts += ['confirm', 'reject']
        if e.status in ('PENDING', 'RELEASED') and (can_accounts or is_super):
            # RELEASED kept as backward-compat alias for PENDING (DB entries pre-migration)
            acts += ['stage1_approve', 'reject']
        # DC-VGK-STAGE1-001: Stage 1 is MANDATORY for ALL users — no skip, even for super staff.
        if e.status == 'STAGE1_APPROVED' and (can_pay or is_super):
            acts += ['mark_paid', 'reject']
        if is_super:
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

    def _enrich_full(e):
        d = _enrich_entry_bulk(e, _p_map, _lead_map, _cat_map, _co_map)
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
            JOIN official_partners p ON p.id = e.partner_id
            WHERE p.category = 'VGK_TEAM'
            GROUP BY e.status, e.kind
        """), {}).fetchall()
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
            WHERE company_id=:cid
            GROUP BY status, kind
        """), {'cid': company_id}).fetchall()

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
    entry_id: int = Body(..., embed=True),
    action: str = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    rejection_reason: Optional[str] = Body(None, embed=True),
    payment_mode: Optional[str] = Body(None, embed=True),
    bank_ledger_id: Optional[int] = Body(None, embed=True),
    cash_staff_id: Optional[int] = Body(None, embed=True),
    payment_utr: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Unified state-machine endpoint.
    action: 'confirm' | 'release' | 'mark_paid' | 'reject'
    Skip-level (EA / MR10001 / VGK4U_SUPREME) can run any forward action from any state.
    """
    from app.services.vgk_cash_income import (
        confirm_cash_income, release_cash_income, reject_cash_income,
        mark_paid_cash_income, post_jv_confirm, post_jv_release,
        post_jv_reject_reversal, is_super_skip_user, _get_ist,
    )

    act = (action or '').lower().strip()
    if act not in ('confirm', 'release', 'mark_paid', 'reject', 'stage1_approve'):
        raise HTTPException(status_code=400, detail="action must be confirm|release|mark_paid|reject|stage1_approve")

    # DC-FIX-2605-002: In vgk_mode the entry's company_id (product co, e.g. 4=MyntReal)
    # differs from the tab's company_id (2=Zynova). Accept entry by id alone and verify
    # the caller has access (is_super check happens below; non-super can only act on
    # entries whose company_id matches their own company or the tab company).
    entry = db.query(VGKCashIncomeEntry).filter(
        VGKCashIncomeEntry.id == entry_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail='Entry not found')
    # Access guard: entry must belong to the requested tab-company OR the entry's own company
    if entry.company_id != company_id:
        # Allow if the caller is a super-skip user or if the entry sits under the same
        # product group as the tab (vgk_mode: entry.company_id may differ from CO).
        # For now, any authenticated staff may act on VGK entries cross-company.
        pass  # VGK programme entries are accessible from the Zynova tab

    is_super = is_super_skip_user(current_employee)
    skipped_states = []
    result = {}

    try:
        if act == 'reject':
            now = _get_ist()
            if entry.status in ('PAID', 'CANCELLED'):
                raise HTTPException(status_code=400, detail=f'Cannot reject — already {entry.status}')
            # post reversal if any prior JV
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
                # DC-FIX-2605-003: use entry.company_id so VGK entries (co=4) resolve correctly
                inner = confirm_cash_income(db, entry_id, entry.company_id, current_employee.id, notes)
                if not inner.get('success'):
                    raise HTTPException(status_code=400, detail=inner.get('error', 'Confirm failed'))
                # Post JV-B
                post_jv_confirm(db, entry, current_employee.id)
                entry.ledger_posted = True
                result = inner
            elif is_super:
                # Skip-level confirm-equivalent on out-of-state row
                raise HTTPException(status_code=400, detail=f'Already {entry.status}; use a higher action')
            else:
                raise HTTPException(status_code=400, detail=f'Entry is {entry.status}, not DRAFT')

        elif act == 'release':
            # DC-NO-RELEASE-001: Release concept removed. Use stage1_approve instead.
            raise HTTPException(status_code=410, detail='Release action removed. Use Stage 1 Approve (stage1_approve) instead.')

        elif act == 'stage1_approve':
            # DC-NO-RELEASE-001 / DC-VGK-STAGE1-001:
            # Stage 1 Approve now handles BOTH PENDING and RELEASED (legacy) entries.
            # For non-ADVANCE PENDING entries: runs wallet deduction + JV (previously at Release).
            if entry.status not in ('PENDING', 'RELEASED'):
                raise HTTPException(status_code=400, detail=f'Entry must be PENDING or RELEASED to approve (got {entry.status})')

            # For non-ADVANCE/non-SLAB_BONUS entries coming from PENDING: apply admin/TDS/wallet deduction now
            # ADVANCE and SLAB_BONUS pre-compute wallet at creation; no deduction needed here.
            if entry.kind not in ('ADVANCE', 'SLAB_BONUS') and entry.status == 'PENDING':
                inner_rel = release_cash_income(db, entry_id, entry.company_id, current_employee.id, notes)
                if not inner_rel.get('success'):
                    raise HTTPException(status_code=400, detail=inner_rel.get('error', 'Wallet deduction at Stage1 failed'))
                post_jv_release(db, entry, current_employee.id)
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
            # Skip-level cascade (DC-NO-RELEASE-001: no intermediate RELEASED step)
            if entry.status == 'DRAFT' and is_super:
                inner1 = confirm_cash_income(db, entry_id, entry.company_id, current_employee.id, notes)
                if not inner1.get('success'):
                    raise HTTPException(status_code=400, detail=inner1.get('error', 'Auto-confirm failed'))
                post_jv_confirm(db, entry, current_employee.id)
                skipped_states.append('DRAFT->PENDING (super-skip)')
                db.flush(); db.refresh(entry)
            if entry.status in ('PENDING', 'RELEASED') and is_super:
                # DC-NO-RELEASE-001: bypass release; for non-ADVANCE/non-SLAB_BONUS apply wallet deduction
                if entry.kind not in ('ADVANCE', 'SLAB_BONUS'):
                    inner2 = release_cash_income(db, entry_id, entry.company_id, current_employee.id, notes)
                    if not inner2.get('success'):
                        raise HTTPException(status_code=400, detail=inner2.get('error', 'Auto wallet-deduction failed'))
                    post_jv_release(db, entry, current_employee.id)
                _now_s1 = _get_ist()
                entry.status = 'STAGE1_APPROVED'
                entry.stage_1_approved_by = (getattr(current_employee, 'full_name', '') or current_employee.emp_code or '').strip() or current_employee.emp_code
                entry.stage_1_approved_at = _now_s1
                db.flush(); db.refresh(entry)
                skipped_states.append('PENDING->STAGE1_APPROVED (super-skip)')
            # DC-VGK-STAGE1-001: Stage 1 is mandatory for ALL; legacy RELEASED auto-promoted above
            if entry.status == 'RELEASED' and is_super:
                _now_s1 = _get_ist()
                entry.status = 'STAGE1_APPROVED'
                entry.stage_1_approved_by = (getattr(current_employee, 'full_name', '') or current_employee.emp_code or '').strip() or current_employee.emp_code
                entry.stage_1_approved_at = _now_s1
                db.flush(); db.refresh(entry)
                skipped_states.append('RELEASED->STAGE1_APPROVED (super-skip)')
            if entry.status != 'STAGE1_APPROVED':
                raise HTTPException(status_code=400, detail=f'Entry must be STAGE1_APPROVED to mark paid (got {entry.status})')

            inner = mark_paid_cash_income(
                db, entry_id, entry.company_id,
                paid_by_id=current_employee.id,
                payment_mode=(payment_mode or '').upper(),
                bank_ledger_id=bank_ledger_id,
                cash_staff_id=cash_staff_id,
                utr=payment_utr,
                notes=notes,
            )
            if not inner.get('success'):
                raise HTTPException(status_code=400, detail=inner.get('error', 'Mark-paid failed'))
            if skipped_states:
                entry.skip_reason = (entry.skip_reason or '') + ' | ' + '; '.join(skipped_states)
            result = inner

        # Audit trail — wrapped in SAVEPOINT so any failure never poisons the outer transaction
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
            logger.warning(f'[VGK-UNIFIED] audit log failed (non-fatal): {_ae}')

        db.commit()

        # ── Post-payment celebration (non-fatal background thread) ─────────
        if act == 'mark_paid' and result.get('success') and not result.get('idempotent'):
            try:
                import threading
                from app.services.vgk_earner_card import run_earner_celebration
                t = threading.Thread(
                    target=run_earner_celebration,
                    args=(entry_id,),
                    daemon=True,
                    name=f'earner-card-{entry_id}',
                )
                t.start()
            except Exception as _ce:
                logger.warning(f'[VGK-UNIFIED] earner celebration thread failed to start: {_ce}')

        return {'success': True, 'action': act, 'skipped_states': skipped_states, 'result': result}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f'[VGK-UNIFIED] action={act} entry={entry_id} failed')
        raise HTTPException(status_code=500, detail=f'{type(e).__name__}: {e}')


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
    Moves status from 'Pending' → 'Stage1Approved'.
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
    Moves status from 'Stage1Approved' → 'Payout Completed'.
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
