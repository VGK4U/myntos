"""
DC Protocol Apr 2026: CRM Commission Calculation — MNR / Partner referral chain.

Trigger: Called from crm.py after a CRM lead transaction is validated (same point VGK hook runs).
Applies to source_ref_type in ('mnr', 'partner') ONLY. VGK path is untouched.

Commission chain:
  L1  – source_ref_id earns non-activated VGK L1 rate (category from lead)
  guru – guru_id earns 2% OF L1 commission amount (same system, MNR only)
  L4  – adi_guru_id earns non-activated VGK L4 rate (same system, MNR only)

Partner sources only earn L1 (no guru_id / adi_guru_id partner fields on the lead).
"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def _next_crm_comm_entry_number(db: Session) -> str:
    from datetime import datetime
    from pytz import timezone as tz
    now = datetime.now(tz('Asia/Kolkata'))
    prefix = f"CC-{now.strftime('%y%m')}"
    result = db.execute(
        text(
            "SELECT MAX(CAST(REGEXP_REPLACE(entry_number, '[^0-9]', '', 'g') AS BIGINT)) "
            "FROM crm_commission_entries "
            "WHERE entry_number LIKE :pfx"
        ),
        {"pfx": f"{prefix}-%"},
    ).scalar()
    seq = (result or 0) + 1
    return f"{prefix}-{seq:04d}"


def calculate_referrer_commissions(
    db: Session,
    lead_id: int,
    txn_id: int,
    revenue_amount: float,
) -> bool:
    """
    Compute and persist MNR/Partner commission entries for a CRM lead transaction.
    Idempotent: duplicate (txn_id, referrer_id, level) rows are silently skipped.
    Returns True if at least one entry was created, False otherwise.
    """
    from app.models.crm import CRMLead
    from app.models.staff_accounts import VGKTeamCommissionConfig
    from app.models.crm_commission import CRMCommissionEntry

    try:
        lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
        if not lead:
            return False

        source_type = getattr(lead, 'source_ref_type', None)
        source_id = getattr(lead, 'source_ref_id', None)

        if source_type not in ('mnr', 'partner') or not source_id:
            return False

        category_id = lead.category_id
        if not category_id:
            logger.info(f"[CRM-COMM] lead {lead_id} has no category_id — skipping")
            return False

        company_id = lead.company_id

        config = (
            db.query(VGKTeamCommissionConfig)
            .filter(
                VGKTeamCommissionConfig.category_id == category_id,
                VGKTeamCommissionConfig.is_paid_member == False,
                VGKTeamCommissionConfig.is_active == True,
            )
            .first()
        )
        if not config:
            logger.info(
                f"[CRM-COMM] No non-paid commission config for cat={category_id} — skipping"
            )
            return False

        revenue = Decimal(str(revenue_amount))
        l1_pct = Decimal(str(config.level1_pct or 0))
        l4_pct = Decimal(str(config.level4_pct or 0))       # L5 Support (field support)

        source_name = getattr(lead, 'source_ref_name', None) or source_id

        cat_row = db.execute(
            text("SELECT category_name FROM signup_categories WHERE id=:cid LIMIT 1"),
            {"cid": category_id},
        ).fetchone()
        cat_name = cat_row[0] if cat_row else None

        created = False

        def _entry_exists(rid: str, lvl: str) -> bool:
            row = db.execute(
                text(
                    "SELECT id FROM crm_commission_entries "
                    "WHERE source_transaction_id=:tid AND referrer_id=:rid AND level=:lvl LIMIT 1"
                ),
                {"tid": txn_id, "rid": rid, "lvl": lvl},
            ).fetchone()
            return row is not None

        def _make_entry(
            referrer_id: str,
            referrer_name: str,
            level: str,
            pct: Decimal,
            amount: Decimal,
        ) -> bool:
            nonlocal created
            if amount <= 0:
                return False
            if _entry_exists(referrer_id, level):
                return False
            entry_no = _next_crm_comm_entry_number(db)
            entry = CRMCommissionEntry(
                entry_number=entry_no,
                company_id=company_id,
                referrer_type=source_type,
                referrer_id=referrer_id,
                referrer_name=referrer_name,
                level=level,
                source_lead_id=lead_id,
                source_transaction_id=txn_id,
                category_id=category_id,
                category_name=cat_name,
                revenue_amount=revenue,
                commission_pct=pct,
                commission_amount=amount,
                status='PENDING',
                notes=f"{level} commission — lead #{lead_id} txn #{txn_id}",
            )
            db.add(entry)
            db.flush()
            created = True
            return True

        # ── L1: Source earns L1 rate ─────────────────────────────────────
        l1_amount = (revenue * l1_pct / Decimal('100')).quantize(Decimal('0.01'))
        _make_entry(source_id, source_name, 'L1', l1_pct, l1_amount)

        # ── Guru and L4: MNR chain only (guru_id / adi_guru_id are MNR FK fields) ──
        if source_type == 'mnr' and l1_amount > 0:

            guru_id = getattr(lead, 'guru_id', None)
            if guru_id:
                guru_row = db.execute(
                    text('SELECT id, name FROM "user" WHERE id=:gid LIMIT 1'),
                    {"gid": guru_id},
                ).fetchone()
                if guru_row:
                    guru_pct = Decimal('2.00')
                    guru_amount = (l1_amount * guru_pct / Decimal('100')).quantize(
                        Decimal('0.01')
                    )
                    _make_entry(
                        guru_id,
                        guru_row.name or guru_id,
                        'guru',
                        guru_pct,
                        guru_amount,
                    )

            adi_guru_id = getattr(lead, 'adi_guru_id', None)
            if adi_guru_id and l4_pct > 0:
                l4_amount = (revenue * l4_pct / Decimal('100')).quantize(Decimal('0.01'))
                adi_row = db.execute(
                    text('SELECT id, name FROM "user" WHERE id=:aid LIMIT 1'),
                    {"aid": adi_guru_id},
                ).fetchone()
                if adi_row:
                    _make_entry(
                        adi_guru_id,
                        adi_row.name or adi_guru_id,
                        'L5',  # DC-VGK-L4CORE-001: field support is now level 5
                        l4_pct,
                        l4_amount,
                    )

        return created

    except Exception as exc:
        logger.error(
            f"[CRM-COMM] calculate_referrer_commissions failed lead={lead_id} "
            f"txn={txn_id}: {exc}",
            exc_info=True,
        )
        return False
