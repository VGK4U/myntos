"""
VGK Team Commission Calculation Service (DC Protocol Mar 2026 / Jun 2026)
5-level commission system (DC-VGK-L4CORE-001):
  L1 = Self (deal partner)
  L2 = Upline of L1 (parent_partner_id of L1)
  L3 = Upline of L2 (parent_partner_id of L2)
  L4 CORE = Upline of L3 (parent_partner_id of L3) — configurable, default 50% of L3
  L5 = Field Support per lead (lead.vgk_field_support_id) — stored as level=5 in income entries

Income entry levels: 1=L1, 2=L2, 3=L3, 4=L4 CORE, 5=L5 SUPPORT.
DB column mapping: level4_core_pct/type/amt → L4 CORE; level4_pct/type/amt → L5 SUPPORT.

Points are managed separately via VGKPointsLedger (not income entries).

PAID / NON-PAID RULE (DC Protocol Mar 2026):
  If L1 partner is_paid_activation = True (paid ₹4,999 PIN):
    - Full 5-level cascade fires: L1 + L2 + L3 + L4 CORE + L5 at Paid rates.
    - Spares discount: 10%.
    - Points on activation: +50,000 (ACTIVATION_BONUS) → total 60,000 (10,000 reg + 50,000 activation).
  If L1 partner is_paid_activation = False (registered only, not yet paid):
    - Only L1 fires at Non-Paid rate; L2, L3, L4 CORE, L5 are skipped.
    - Spares discount: 3%.
    - Points on registration: 10,000 (WELCOME_BONUS).

HOLD STATUS RULE (DC Protocol Mar 2026):
  If a partner's VGK points balance < required debit at the time of transaction validation:
    - Commission entry is created with status = HOLD
    - Points are NOT deducted (zero partial debit)
    - required_points_debit is stored on the income entry
    - Entry moves to PENDING only when process_held_commissions() confirms sufficient balance

PAYOUT DEDUCTIONS (applied at release by vgk_cash_income service):
  8% admin charges + 2% TDS deducted from gross commission → net payout credited to vgk_cash_wallet.
"""

import logging
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def get_indian_time():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


def _next_vgk_entry_number(db: Session, company_id: int, prefix: str = None) -> str:
    from pytz import timezone
    now = datetime.now(timezone('Asia/Kolkata'))
    yymm = now.strftime('%y%m')
    like_prefix = prefix or f"VGK-{yymm}"
    result = db.execute(text(
        "SELECT MAX(CAST(REGEXP_REPLACE(entry_number, '[^0-9]', '', 'g') AS BIGINT)) "
        "FROM vgk_team_income_entries "
        "WHERE entry_number LIKE :pfx"
    ), {"pfx": f"{like_prefix}-%"}).scalar()
    seq = (result or 0) + 1
    return f"{like_prefix}-{seq:04d}"


def add_vgk_points_entry(
    db: Session,
    partner_id: int,
    points_credit: Decimal = Decimal('0'),
    points_debit: Decimal = Decimal('0'),
    reason_code: str = 'MANUAL_ADJUSTMENT',
    reference_type: str = None,
    reference_id: int = None,
    notes: str = None,
    created_by: int = None,
) -> 'VGKPointsLedger':
    """
    Append a single entry to vgk_points_ledger and update official_partners.vgk_points_balance.
    Returns the new ledger row. Caller is responsible for db.commit().
    Points cannot be transferred between partners — always use partner's own id.
    Uses SELECT FOR UPDATE to prevent concurrent balance race conditions.
    """
    from app.models.staff_accounts import OfficialPartner, VGKPointsLedger

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).with_for_update().first()
    if not partner:
        raise ValueError(f"Partner {partner_id} not found for points entry")

    current_balance = partner.vgk_points_balance or Decimal('0')
    new_balance = current_balance + points_credit - points_debit

    if new_balance < Decimal('0'):
        raise ValueError(
            f"Insufficient points balance: available={float(current_balance)}, "
            f"debit requested={float(points_debit)}"
        )

    now = get_indian_time()
    entry = VGKPointsLedger(
        partner_id=partner_id,
        points_credit=points_credit,
        points_debit=points_debit,
        balance_after=new_balance,
        reason_code=reason_code,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        created_at=now,
        created_by=created_by,
    )
    db.add(entry)
    partner.vgk_points_balance = new_balance
    partner.updated_at = now
    return entry


def calculate_vgk_commissions(db: Session, lead_id: int, transaction_id: int, revenue_amount: float) -> bool:
    """
    DC Protocol Mar 2026: Calculate and create VGK commission entries for L1–L4.
    Called after a CRM transaction is validated on a VGK-program lead.

    For each earning partner (L1–L4):
      1. Commission income entry is created in vgk_team_income_entries.
      2. VGK Discount Credits are checked against the partner's current balance.

      IF balance >= required_debit (revenue × level_pct / 100):
        - Points are debited via add_vgk_points_entry() — safe FOR UPDATE lock
        - Income entry status = PENDING (eligible for payout)

      IF balance < required_debit:
        - Points are NOT deducted (zero debit)
        - Income entry status = HOLD
        - required_points_debit is stored on the entry
        - Entry releases to PENDING when process_held_commissions() finds sufficient balance
    """
    from app.models.crm import CRMLead
    from app.models.staff_accounts import OfficialPartner, VGKTeamCommissionConfig, VGKTeamIncomeEntry

    try:
        lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
        if not lead or not lead.is_vgk_program:
            return False

        category_id = lead.category_id if hasattr(lead, 'category_id') else None
        if not category_id:
            logger.info(f"[VGK-COMM] Lead {lead_id} has no category_id — skipping commission")
            return False

        # ── Resolve L1 early (needed for paid/non-paid config selection) ──
        _l1_early = None
        if lead.primary_owner_type == 'partner' and lead.primary_owner_id:
            _l1_early = db.query(OfficialPartner).filter(
                OfficialPartner.id == lead.primary_owner_id,
                OfficialPartner.category == 'VGK_TEAM'
            ).first()
        if not _l1_early and hasattr(lead, 'associated_partner_id') and lead.associated_partner_id:
            _l1_early = db.query(OfficialPartner).filter(
                OfficialPartner.id == lead.associated_partner_id,
                OfficialPartner.category == 'VGK_TEAM'
            ).first()

        is_paid = bool(getattr(_l1_early, 'is_paid_activation', False)) if _l1_early else False

        # Select config matching paid/non-paid status; fall back to paid config if non-paid row missing
        config = db.query(VGKTeamCommissionConfig).filter(
            VGKTeamCommissionConfig.category_id == category_id,
            VGKTeamCommissionConfig.is_paid_member == is_paid,
            VGKTeamCommissionConfig.is_active == True
        ).first()
        if not config:
            config = db.query(VGKTeamCommissionConfig).filter(
                VGKTeamCommissionConfig.category_id == category_id,
                VGKTeamCommissionConfig.is_active == True
            ).first()

        if not config:
            logger.info(f"[VGK-COMM] No active config for cat={category_id} — skipping commission")
            return False

        revenue = Decimal(str(revenue_amount))
        now = get_indian_time()
        from pytz import timezone
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def make_entry(partner: OfficialPartner, level: int, pct: Decimal, flat_amt: Decimal = Decimal('0'), comm_type: str = 'PCT') -> None:
            if not partner or partner.category != 'VGK_TEAM' or not partner.is_active:
                return
            if comm_type == 'AMOUNT':
                commission = flat_amt.quantize(Decimal('0.01'))
            else:
                commission = (revenue * pct / Decimal('100')).quantize(Decimal('0.01'))
            if commission <= 0:
                return

            month_revenue = db.execute(text(
                "SELECT COALESCE(SUM(revenue_amount),0) FROM vgk_team_income_entries "
                "WHERE partner_id=:pid AND status!='CANCELLED' AND created_at>=:ms"
            ), {"pid": partner.id, "ms": month_start.replace(tzinfo=None)}).scalar() or 0

            bonus = Decimal('0')
            if config.monthly_target > 0 and Decimal(str(month_revenue)) + revenue >= config.monthly_target:
                if config.bonus_pct > 0:
                    bonus = (commission * config.bonus_pct / Decimal('100')).quantize(Decimal('0.01'))

            required_debit = (revenue * pct / Decimal('100')).quantize(Decimal('0.01'))
            available = partner.vgk_points_balance or Decimal('0')

            if available >= required_debit:
                entry_status = 'PENDING'
            else:
                entry_status = 'HOLD'

            entry_no = _next_vgk_entry_number(db, lead.company_id)
            entry = VGKTeamIncomeEntry(
                company_id=lead.company_id,
                entry_number=entry_no,
                partner_id=partner.id,
                source_lead_id=lead_id,
                source_transaction_id=transaction_id,
                category_id=category_id,
                level=level,
                revenue_amount=revenue,
                commission_pct=pct,
                commission_amount=commission,
                bonus_amount=bonus,
                status=entry_status,
                required_points_debit=required_debit,
                notes=f"L{level} commission on deal #{lead_id}",
                created_at=now,
                updated_at=now
            )
            db.add(entry)

            if entry_status == 'PENDING':
                add_vgk_points_entry(
                    db=db,
                    partner_id=partner.id,
                    points_credit=Decimal('0'),
                    points_debit=required_debit,
                    reason_code='PRODUCT_DISCOUNT',
                    reference_type='crm_transaction',
                    reference_id=transaction_id,
                    notes=(
                        f"L{level} auto-discount debit: {float(pct)}% of "
                        f"\u20b9{float(revenue)} on deal #{lead_id} (txn #{transaction_id})"
                    ),
                    created_by=None,
                )
                logger.info(
                    f"[VGK-COMM] L{level} PENDING for {partner.partner_code}: "
                    f"commission={float(commission)}, points debited={float(required_debit)}"
                )
            else:
                logger.warning(
                    f"[VGK-COMM] L{level} HOLD for {partner.partner_code}: "
                    f"commission={float(commission)}, required_debit={float(required_debit)}, "
                    f"available={float(available)} — entry placed on HOLD"
                )

        # ── L1 (self — deal partner) — already resolved above as _l1_early ─
        l1_partner = _l1_early

        if l1_partner:
            make_entry(l1_partner, 1, config.level1_pct,
                       Decimal(str(config.level1_amt or 0)), getattr(config, 'level1_type', 'PCT') or 'PCT')

            if not is_paid:
                # DC Protocol Mar 2026: Non-Paid member — L1 only; L2/L3/L4 CORE/L5 skipped.
                logger.info(
                    f"[VGK-COMM] Non-Paid member {l1_partner.partner_code} — only L1 fires; L2/L3/L4 CORE/L5 skipped"
                )
            else:
                # Paid member — full 5-level cascade (DC-VGK-L4CORE-001)
                # ── L2: Upline of L1 ────────────────────────────────────────
                l2_partner = None
                if l1_partner.parent_partner_id:
                    l2_partner = db.query(OfficialPartner).filter(
                        OfficialPartner.id == l1_partner.parent_partner_id
                    ).first()
                    make_entry(l2_partner, 2, config.level2_pct,
                               Decimal(str(config.level2_amt or 0)), getattr(config, 'level2_type', 'PCT') or 'PCT')

                # ── L3: Upline of L2 ─────────────────────────────────────────
                # Loyal Coupon members — L3/L4 CORE/L5 excluded regardless of paid status.
                l3_partner = None
                if not getattr(l1_partner, 'is_loyal_coupon', False):
                    if l2_partner and l2_partner.parent_partner_id:
                        l3_partner = db.query(OfficialPartner).filter(
                            OfficialPartner.id == l2_partner.parent_partner_id
                        ).first()
                        make_entry(l3_partner, 3, config.level3_pct,
                                   Decimal(str(config.level3_amt or 0)), getattr(config, 'level3_type', 'PCT') or 'PCT')
                else:
                    logger.info(
                        f"[VGK-COMM] Loyal Coupon member {l1_partner.partner_code} — L3/L4 CORE skipped"
                    )

                # ── L4 CORE: Upline of L3 (DC-VGK-L4CORE-001) ───────────────
                if not getattr(l1_partner, 'is_loyal_coupon', False):
                    _l4core_pct = Decimal(str(getattr(config, 'level4_core_pct', 0) or 0))
                    _l4core_amt = Decimal(str(getattr(config, 'level4_core_amt', 0) or 0))
                    _l4core_type = getattr(config, 'level4_core_type', 'PCT') or 'PCT'
                    if l3_partner and l3_partner.parent_partner_id and _l4core_pct > 0:
                        l4_core_partner = db.query(OfficialPartner).filter(
                            OfficialPartner.id == l3_partner.parent_partner_id
                        ).first()
                        make_entry(l4_core_partner, 4, _l4core_pct, _l4core_amt, _l4core_type)
                    else:
                        logger.debug(
                            f"[VGK-COMM] L4 CORE skipped: l3={l3_partner and l3_partner.partner_code} "
                            f"has_parent={bool(l3_partner and l3_partner.parent_partner_id)} "
                            f"core_pct={float(_l4core_pct)}"
                        )

                # ── L5 SUPPORT: Field Support per lead ────────────────────────
                if lead.vgk_field_support_id and not getattr(l1_partner, 'is_loyal_coupon', False):
                    l5_partner = db.query(OfficialPartner).filter(
                        OfficialPartner.id == lead.vgk_field_support_id
                    ).first()
                    make_entry(l5_partner, 5, config.level4_pct,
                               Decimal(str(config.level4_amt or 0)), getattr(config, 'level4_type', 'PCT') or 'PCT')
                elif lead.vgk_field_support_id and getattr(l1_partner, 'is_loyal_coupon', False):
                    logger.info(
                        f"[VGK-COMM] Loyal Coupon member {l1_partner.partner_code} — L5 field support skipped"
                    )
        elif lead.vgk_field_support_id and is_paid:
            # L5 SUPPORT only if no L1 but field support assigned (paid deals)
            l5_partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == lead.vgk_field_support_id
            ).first()
            make_entry(l5_partner, 5, config.level4_pct,
                       Decimal(str(config.level4_amt or 0)), getattr(config, 'level4_type', 'PCT') or 'PCT')

        db.commit()
        logger.info(f"[VGK-COMM] Commissions calculated for lead {lead_id}, txn {transaction_id}")
        return True

    except Exception as e:
        logger.warning(f"[VGK-COMM] Failed for lead {lead_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return False


def process_held_commissions(db: Session, partner_id: int) -> int:
    """
    DC Protocol Mar 2026: Check all HOLD commission entries for a partner.
    For each HOLD entry where current balance >= required_points_debit:
      - Debit the required points via add_vgk_points_entry()
      - Move entry status from HOLD → PENDING

    Returns the number of entries released.
    Called automatically whenever a partner receives new points.
    """
    from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry

    released = 0
    try:
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == partner_id
        ).with_for_update().first()
        if not partner:
            return 0

        held_entries = (
            db.query(VGKTeamIncomeEntry)
            .filter(
                VGKTeamIncomeEntry.partner_id == partner_id,
                VGKTeamIncomeEntry.status == 'HOLD',
                VGKTeamIncomeEntry.required_points_debit > 0,
            )
            .order_by(VGKTeamIncomeEntry.id.asc())
            .with_for_update(skip_locked=True)
            .all()
        )

        if not held_entries:
            return 0

        now = get_indian_time()

        for entry in held_entries:
            required = entry.required_points_debit or Decimal('0')
            available = partner.vgk_points_balance or Decimal('0')

            if available < required:
                logger.info(
                    f"[VGK-HOLD] Entry #{entry.id} still HOLD for {partner.partner_code}: "
                    f"need {float(required)}, have {float(available)}"
                )
                continue

            add_vgk_points_entry(
                db=db,
                partner_id=partner_id,
                points_credit=Decimal('0'),
                points_debit=required,
                reason_code='PRODUCT_DISCOUNT',
                reference_type='crm_transaction',
                reference_id=entry.source_transaction_id,
                notes=(
                    f"HOLD released: L{entry.level} debit of {float(required)} pts "
                    f"for deal #{entry.source_lead_id} (entry #{entry.id})"
                ),
                created_by=None,
            )

            entry.status = 'PENDING'
            entry.updated_at = now
            released += 1

            logger.info(
                f"[VGK-HOLD] Released entry #{entry.id} ({entry.entry_number}) "
                f"for {partner.partner_code} — debited {float(required)} pts, status → PENDING"
            )

        if released:
            db.commit()
            logger.info(f"[VGK-HOLD] Released {released} HOLD entries for partner {partner_id}")

    except Exception as e:
        logger.warning(f"[VGK-HOLD] process_held_commissions failed for partner {partner_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass

    return released


def activate_vgk_member(db: Session, partner_id: int, company_id: int, activated_by_staff_id: int) -> bool:
    """
    DC Protocol Mar 2026: Activate a VGK_TEAM member (paid ₹4,999 PIN).
    Sets is_active=True, is_paid_activation=True, vgk_activated_at=now().
    Credits 50,000 activation bonus points via VGKPointsLedger (NOT income entries) — total 60,000 with registration.
    After crediting, triggers process_held_commissions() to release any HOLD entries.
    """
    from app.models.staff_accounts import OfficialPartner

    try:
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == partner_id,
            OfficialPartner.category == 'VGK_TEAM'
        ).first()

        if not partner:
            logger.warning(f"[VGK-ACTIVATE] Partner {partner_id} not found or not VGK_TEAM")
            return False

        if partner.is_active and partner.is_paid_activation:
            logger.info(f"[VGK-ACTIVATE] Partner {partner.partner_code} already paid-activated — skipping")
            return True

        now = get_indian_time()
        partner.is_active = True
        partner.is_paid_activation = True
        partner.vgk_activated_at = now
        # DC-CP-TIER-001 (Apr 25 2026): auto-enable visiting card + ID card on paid activation.
        partner.vcard_enabled = True
        partner.idcard_enabled = True
        partner.card_manually_activated = True

        # Mark any PENDING coupon activation request for this member as APPROVED
        try:
            db.execute(
                text(
                    "UPDATE vgk_member_activation_requests SET status='APPROVED', updated_at=NOW() "
                    "WHERE target_partner_id = :pid AND status = 'PENDING'"
                ),
                {"pid": partner_id}
            )
        except Exception as _ar:
            logger.warning(f"[VGK-ACTIVATE] Could not update activation request for {partner_id}: {_ar}")

        add_vgk_points_entry(
            db=db,
            partner_id=partner_id,
            points_credit=Decimal('50000'),
            points_debit=Decimal('0'),
            reason_code='ACTIVATION_BONUS',
            reference_type='activation',
            reference_id=None,
            notes='Partner paid activation bonus (₹4,999 PIN) — 50,000 VGK Discount Credits (total 60,000 with registration)',
            created_by=activated_by_staff_id,
        )

        db.commit()
        logger.info(f"[VGK-ACTIVATE] Partner {partner.partner_code} paid-activated, 50,000 points credited to ledger (total 60,000)")

        # [DC-REFERRAL] Credit 2,000 points to referrer on activation
        if partner.parent_partner_id:
            try:
                referrer = db.query(OfficialPartner).filter(
                    OfficialPartner.id == partner.parent_partner_id,
                    OfficialPartner.category == 'VGK_TEAM'
                ).first()
                if referrer and referrer.partner_code != 'VGK07102207':
                    add_vgk_points_entry(
                        db=db,
                        partner_id=referrer.id,
                        points_credit=Decimal('2000'),
                        points_debit=Decimal('0'),
                        reason_code='CAMPAIGN_BONUS',
                        reference_type='referral_activation',
                        reference_id=partner_id,
                        notes=f'Referral activation reward — {partner.partner_code} activated (paid ₹5,000)',
                        created_by=activated_by_staff_id,
                    )
                    db.commit()
                    logger.info(f"[DC-REFERRAL] 2,000 pts credited to referrer {referrer.partner_code} for activation of {partner.partner_code}")
            except Exception as _re:
                logger.warning(f"[DC-REFERRAL] Could not credit referrer activation reward: {_re}")
                try:
                    db.rollback()
                except Exception:
                    pass

        process_held_commissions(db, partner_id)

        return True

    except Exception as e:
        logger.warning(f"[VGK-ACTIVATE] Failed for partner {partner_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return False


def activate_loyal_coupon_member(
    db: Session,
    partner_id: int,
    company_id: int,
    activated_by_staff_id: int,
) -> bool:
    """
    DC Protocol Mar 2026: Activate a VGK_TEAM member via Loyal Coupon (zero-cost, VGK Mentor only).

    Rules:
    - Can only be applied once per member (is_loyal_coupon guard).
    - Sets is_active=True, is_loyal_coupon=True, vgk_activated_at=now().
    - Credits 50,000 points via LOYAL_BONUS reason code (total 60,000 with registration).
    - Commission rules on future deals: L1 (self) and L2 (support) earn; L3 and L4 are excluded.
    - Triggers process_held_commissions() after crediting (same as standard activation).
    - Counted as +1 in all team/leg/awards/bonanza counts (is_active=True applies normally).
    """
    from app.models.staff_accounts import OfficialPartner

    try:
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == partner_id,
            OfficialPartner.category == 'VGK_TEAM'
        ).first()

        if not partner:
            logger.warning(f"[VGK-LOYAL] Partner {partner_id} not found or not VGK_TEAM")
            return False

        if partner.is_loyal_coupon:
            logger.warning(
                f"[VGK-LOYAL] Partner {partner.partner_code} already has Loyal Coupon applied — one-time only"
            )
            return False

        if partner.is_active:
            logger.warning(
                f"[VGK-LOYAL] Partner {partner.partner_code} already active — Loyal Coupon requires inactive member"
            )
            return False

        now = get_indian_time()
        partner.is_active = True
        partner.is_loyal_coupon = True
        partner.vgk_activated_at = now

        add_vgk_points_entry(
            db=db,
            partner_id=partner_id,
            points_credit=Decimal('50000'),
            points_debit=Decimal('0'),
            reason_code='LOYAL_BONUS',
            reference_type='loyal_coupon',
            reference_id=None,
            notes='Loyal Coupon activation bonus — 50,000 VGK Discount Credits (total 60,000 with registration)',
            created_by=activated_by_staff_id,
        )

        db.commit()
        logger.info(
            f"[VGK-LOYAL] Partner {partner.partner_code} activated via Loyal Coupon, "
            f"50,000 points credited by staff_id={activated_by_staff_id} (total 60,000)"
        )

        # [DC-REFERRAL] Credit 2,000 points to referrer on loyal coupon activation
        if partner.parent_partner_id:
            try:
                referrer = db.query(OfficialPartner).filter(
                    OfficialPartner.id == partner.parent_partner_id,
                    OfficialPartner.category == 'VGK_TEAM'
                ).first()
                if referrer and referrer.partner_code != 'VGK07102207':
                    add_vgk_points_entry(
                        db=db,
                        partner_id=referrer.id,
                        points_credit=Decimal('2000'),
                        points_debit=Decimal('0'),
                        reason_code='CAMPAIGN_BONUS',
                        reference_type='referral_activation',
                        reference_id=partner_id,
                        notes=f'Referral activation reward — {partner.partner_code} activated (Loyal Coupon)',
                        created_by=activated_by_staff_id,
                    )
                    db.commit()
                    logger.info(f"[DC-REFERRAL] 2,000 pts credited to referrer {referrer.partner_code} for loyal-coupon activation of {partner.partner_code}")
            except Exception as _re:
                logger.warning(f"[DC-REFERRAL] Could not credit referrer loyal-coupon activation reward: {_re}")
                try:
                    db.rollback()
                except Exception:
                    pass

        process_held_commissions(db, partner_id)

        return True

    except Exception as e:
        logger.warning(f"[VGK-LOYAL] Failed for partner {partner_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return False
