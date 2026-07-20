"""
VGK Solar Advance 50% Cap Service (DC Protocol Jun 2026)

DC-VGK-ADV-CAP-001: At any moment in time, a partner's PAID advances (kind IN
('ADVANCE','BRAND_ADVANCE') in vgk_cash_income_entries) must not exceed
FLOOR(eligible_files × 0.5).

eligible_files = distinct lead_ids in vgk_solar_cibil_advances for this partner
                 WHERE the lead's solar_pipeline_status is in ELIGIBLE_STAGES
                 (i.e. not in loan_rejected / cancelled / not_interested)

Compensation rule: if a lead moves to a terminal failure stage AFTER its advance
was PAID, the eligible pool shrinks and future PAID advances are blocked until
more files progress. Already-paid amounts are not clawed back.

Cap applies to: Source (L1), L2, and L5 advance entries only.
RELEASED and STAGE1_APPROVED statuses are NOT gated — only PAID is.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

ELIGIBLE_STAGES = frozenset({
    'application_submitted', 'pending_with_bank', 'documents_issue',
    'load_extension', 'electricity_bill_change', 'installation_pending',
    'net_meter_pending', 'balance_pending', 'balance_received',
    'subsidy_pending', 'completed',
})


def get_cap_status(db: Session, partner_id: int, company_id: int) -> dict:
    """
    Returns the current 50% cap status for a partner.

    Returns:
        {
            'eligible_files':  int  — leads in ELIGIBLE_STAGES with an advance row,
            'cap_limit':       int  — floor(eligible_files × 0.5),
            'paid_advances':   int  — PAID advance VCI entries for this partner,
            'remaining':       int  — how many more can be PAID (0 if capped),
            'is_capped':       bool — True if paid_advances >= cap_limit,
        }
    """
    try:
        stages_tuple = tuple(ELIGIBLE_STAGES)
        stages_ph = ','.join(f':s{i}' for i in range(len(stages_tuple)))
        params: dict = {'pid': partner_id}
        for i, s in enumerate(stages_tuple):
            params[f's{i}'] = s

        eligible_row = db.execute(text(f"""
            SELECT COUNT(DISTINCT a.lead_id) AS cnt
            FROM vgk_solar_cibil_advances a
            JOIN crm_leads l ON l.id = a.lead_id
            WHERE a.partner_id = :pid
              AND l.solar_pipeline_status IN ({stages_ph})
        """), params).fetchone()

        eligible_files = int(eligible_row.cnt) if eligible_row else 0
        cap_limit = eligible_files // 2

        paid_row = db.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM vgk_cash_income_entries
            WHERE partner_id = :pid
              AND kind IN ('ADVANCE', 'BRAND_ADVANCE')
              AND status = 'PAID'
        """), {'pid': partner_id}).fetchone()

        paid_advances = int(paid_row.cnt) if paid_row else 0
        remaining = max(0, cap_limit - paid_advances)
        is_capped = paid_advances >= cap_limit

        return {
            'eligible_files': eligible_files,
            'cap_limit':      cap_limit,
            'paid_advances':  paid_advances,
            'remaining':      remaining,
            'is_capped':      is_capped,
        }

    except Exception as e:
        logger.warning(f'[DC-VGK-ADV-CAP] get_cap_status failed for partner {partner_id}: {e}')
        return {
            'eligible_files': 0,
            'cap_limit':      0,
            'paid_advances':  0,
            'remaining':      0,
            'is_capped':      False,
            'error':          str(e),
        }


def can_mark_paid(db: Session, partner_id: int, company_id: int) -> tuple:
    """
    Returns (allowed: bool, cap_info: dict).

    allowed=True  → proceed with PAID transition
    allowed=False → block with cap_info for error message
    """
    info = get_cap_status(db, partner_id, company_id)
    if info.get('error'):
        return (True, info)
    allowed = not info['is_capped']
    return (allowed, info)
