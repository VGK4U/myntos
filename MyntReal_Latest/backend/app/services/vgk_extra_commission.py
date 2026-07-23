"""
DC-EXTRA-COMM-001 (Jul 2026): Special Bonanza — Per-File Extra Commission Service.
DC-EC-PER-LEVEL-TRIGGER-001 (Jul 2026): Each level fires at its own configured trigger event.

Fires when a lead hits a pipeline trigger point and credits a flat extra commission
to configured partner levels immediately as PENDING VCI entries.

Per-level trigger logic:
  - If ec_lN_trigger is set for level N, use it as the effective trigger for that level.
  - If ec_lN_trigger is NULL, fall back to the bonanza's global trigger_event.
  - Level only fires if its effective trigger == current trigger_event argument.

Trigger events:
  file_submitted — CIBIL advance released (Solar) or advance released on any category
  first_payment  — DVR advance released (deal_value_received > 0)
  file_completed — lead.status = 'completed' / solar_pipeline_status = 'completed'

Idempotent via bonanza_extra_commission_log (UNIQUE bonanza_id+lead_id+level).
Non-blocking — exceptions are caught per-bonanza and per-level; caller txn is never
rolled back from this function.

Same lead fires independently per bonanza (different bonanza = different gift).
Same lead fires once per level per bonanza (idempotency guard).
"""
import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

ADMIN_CHARGE_PCT = Decimal('8')
TDS_PCT          = Decimal('2')


def apply_extra_commission_if_active(
    db: Session,
    lead,
    trigger_event: str,
) -> dict:
    """
    Find all active extra_commission bonanzas, resolve per-level trigger events,
    and create PENDING VCI entries for each level whose effective trigger matches.

    Args:
        db            — SQLAlchemy session (caller owns commit)
        lead          — CRMLead ORM object (or namedtuple with same fields)
        trigger_event — 'file_submitted' | 'first_payment' | 'file_completed'

    Returns:
        {'applied': int, 'skipped': int}
    """
    from app.services.vgk_cash_income import _next_entry_number, _get_ist

    applied = 0
    skipped = 0

    try:
        lead_id     = lead.id
        category_id = getattr(lead, 'category_id', None)
        company_id  = int(getattr(lead, 'company_id', None) or 4)

        _l1_id = getattr(lead, 'associated_partner_id', None)
        _l2_id = getattr(lead, 'team_senior_partner_id', None)
        _l3_id = getattr(lead, 'team_extended_partner_id', None)
        _l4_id = getattr(lead, 'team_core_partner_id', None)
        _l5_id = getattr(lead, 'vgk_field_support_id', None) or 31

        level_partner_map = {
            1: _l1_id,
            2: _l2_id,
            3: _l3_id,
            4: _l4_id,
            5: _l5_id,
        }

        # DC-EC-PER-LEVEL-TRIGGER-001: fetch all active EC bonanzas (no global trigger filter —
        # per-level trigger matching is done in Python below).
        _active = db.execute(text("""
            SELECT b.id, b.name,
                   b.trigger_event,
                   b.ec_l1_trigger, b.ec_l2_trigger, b.ec_l3_trigger,
                   b.ec_l4_trigger, b.ec_l5_trigger,
                   b.ec_l1_amount,  b.ec_l2_amount,  b.ec_l3_amount,
                   b.ec_l4_amount,  b.ec_l5_amount
            FROM   bonanza b
            WHERE  b.reward_type = 'extra_commission'
              AND  b.status      = 'Approved'
              AND  b.is_deleted  = FALSE
              AND  NOW()::date BETWEEN b.start_date::date AND b.end_date::date
        """)).fetchall()

        for _bz in _active:
            try:
                _cat_rows = db.execute(text("""
                    SELECT category_id FROM bonanza_category_filters
                    WHERE bonanza_id = :bid
                """), {'bid': _bz.id}).fetchall()

                if _cat_rows:
                    _allowed_cats = {r.category_id for r in _cat_rows}
                    if category_id not in _allowed_cats:
                        continue

                # DC-EC-PER-LEVEL-TRIGGER-001: resolve per-level amounts filtered by effective trigger.
                # For each level N: effective_trigger = ec_lN_trigger if set, else global trigger_event.
                # Only include level if effective_trigger == current trigger_event AND amount > 0.
                _global_trigger = getattr(_bz, 'trigger_event', None)
                level_amounts = {}
                for lv in [1, 2, 3, 4, 5]:
                    _per_trig = getattr(_bz, f'ec_l{lv}_trigger', None)
                    _eff_trig = _per_trig if _per_trig else _global_trigger
                    if _eff_trig != trigger_event:
                        continue
                    val = getattr(_bz, f'ec_l{lv}_amount', None)
                    if val and float(val) > 0:
                        level_amounts[lv] = Decimal(str(val))

                if not level_amounts:
                    continue

                now_ist = _get_ist().replace(tzinfo=None)

                for lv, amount in level_amounts.items():
                    partner_id = level_partner_map.get(lv)
                    if not partner_id:
                        skipped += 1
                        continue

                    _exists = db.execute(text("""
                        SELECT id FROM bonanza_extra_commission_log
                        WHERE bonanza_id = :bid AND lead_id = :lid AND level = :lv
                    """), {'bid': _bz.id, 'lid': lead_id, 'lv': lv}).fetchone()
                    if _exists:
                        skipped += 1
                        continue

                    admin  = (amount * ADMIN_CHARGE_PCT / 100).quantize(Decimal('0.01'))
                    tds    = (amount * TDS_PCT           / 100).quantize(Decimal('0.01'))
                    net    = amount - admin - tds
                    _sp = db.begin_nested()
                    try:
                        entry_no = _next_entry_number(db, company_id)
                        _inc_date = (lead.submit_date.date() if hasattr(lead.submit_date, 'date') else lead.submit_date) if getattr(lead, 'submit_date', None) else now_ist.date()

                        db.execute(text("""
                            INSERT INTO vgk_cash_income_entries
                              (company_id, entry_number, partner_id, source_lead_id,
                               kind, status, commission_amount, admin_charges,
                               tds_amount, net_payout, level, notes, income_date,
                               created_at, updated_at)
                            VALUES
                              (:co, :en, :pid, :lid,
                               'EXTRA_COMMISSION', 'PENDING',
                               :ca, :ac, :ta, :np, :lv,
                               :notes, :inc_date, :now, :now)
                        """), {
                            'co':       company_id,
                            'en':       entry_no,
                            'pid':      partner_id,
                            'lid':      lead_id,
                            'ca':       float(amount),
                            'ac':       float(admin),
                            'ta':       float(tds),
                            'np':       float(net),
                            'lv':       lv,
                            'notes':    (
                                f'Special Bonanza: {_bz.name} | '
                                f'Trigger: {trigger_event} | L{lv} Extra Commission'
                            ),
                            'inc_date': _inc_date,
                            'now':      now_ist,
                        })

                        db.execute(text("""
                            INSERT INTO bonanza_extra_commission_log
                              (bonanza_id, lead_id, level, partner_id, created_at)
                            VALUES (:bid, :lid, :lv, :pid, :now)
                            ON CONFLICT (bonanza_id, lead_id, level) DO NOTHING
                        """), {
                            'bid': _bz.id, 'lid': lead_id,
                            'lv': lv, 'pid': partner_id, 'now': now_ist,
                        })

                        _sp.commit()
                        applied += 1
                        logger.info(
                            f'[DC-EXTRA-COMM-001] ✅ {entry_no} L{lv} ₹{float(amount):.0f} '
                            f'→ partner {partner_id} '
                            f'(bonanza={_bz.id} lead={lead_id} trigger={trigger_event})'
                        )

                        _wp = db.begin_nested()
                        try:
                            # Fetch current wallet balance for logging
                            _partner = db.execute(text(
                                "SELECT vgk_cash_wallet FROM official_partners WHERE id = :pid FOR UPDATE"
                            ), {'pid': partner_id}).fetchone()
                            wallet_before = Decimal(str(_partner.vgk_cash_wallet or 0)) if _partner else Decimal('0')
                            wallet_after = wallet_before + amount

                            db.execute(text("""
                                UPDATE official_partners
                                   SET vgk_cash_wallet = :wa
                                 WHERE id = :pid
                            """), {'wa': float(wallet_after), 'pid': partner_id})

                            # Log wallet transaction using standard helper
                            from app.services.vgk_cash_income import _log_wallet_txn
                            _log_wallet_txn(
                                db,
                                partner_id=partner_id,
                                company_id=company_id,
                                txn_type='EXTRA_COMMISSION_CREDIT',
                                direction='CR',
                                amount=amount,
                                wallet_before=wallet_before,
                                wallet_after=wallet_after,
                                ref_type='VGK_EXTRA_COMMISSION',
                                ref_id=_bz.id,
                                description=(
                                    f'Special Bonanza Extra Commission — '
                                    f'{_bz.name} | {trigger_event} | L{lv}'
                                ),
                            )
                            _wp.commit()
                        except Exception as _we:
                            try:
                                _wp.rollback()
                            except Exception:
                                pass
                            logger.warning(
                                f'[DC-EXTRA-COMM-001] wallet credit non-fatal '
                                f'(partner={partner_id}): {_we}'
                            )

                    except Exception as _spe:
                        try:
                            _sp.rollback()
                        except Exception:
                            pass
                        logger.warning(
                            f'[DC-EXTRA-COMM-001] VCI insert non-fatal '
                            f'L{lv} partner={partner_id} bonanza={_bz.id}: {_spe}'
                        )

            except Exception as _bze:
                logger.warning(
                    f'[DC-EXTRA-COMM-001] bonanza={_bz.id} lead={lead_id}: {_bze}'
                )

    except Exception as _e:
        logger.warning(
            f'[DC-EXTRA-COMM-001] outer error lead={getattr(lead, "id", "?")}: {_e}'
        )

    return {'applied': applied, 'skipped': skipped}
