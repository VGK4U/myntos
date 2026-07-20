"""
DC-EC-PER-LEVEL-TRIGGER-001 (Jul 2026): Cash/Bonus Bonanza Trigger Service.

When a pipeline event fires (file_submitted/first_payment/file_completed),
this service:
  1. Finds all APPROVED cash/bonus bonanzas that have any per-level trigger set.
  2. Per level N: effective_trigger = ec_lN_trigger (if set) else global trigger_event.
     Only fires if effective_trigger == current event AND ec_lN_amount > 0.
  3. Creates a BonanzaProgress PENDING claim for the level's partner.
  4. Logs to bonanza_extra_commission_log for idempotency (UNIQUE bonanza+lead+level).

Same lead fires independently per bonanza (different bonanza = different campaign).
Same lead fires once per level per bonanza (idempotency guard).
The claim enters the normal 5-step approval flow (Pending → Admin Approved → ... → Paid).
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply_cash_bonus_trigger_if_active(
    db: Session,
    lead,
    trigger_event: str,
) -> dict:
    """
    Find all active cash/bonus bonanzas with per-level triggers, resolve effective
    trigger per level, and auto-create BonanzaProgress PENDING claims.

    Args:
        db            — SQLAlchemy session (caller owns commit)
        lead          — CRMLead ORM object (or namedtuple with same fields)
        trigger_event — 'file_submitted' | 'first_payment' | 'file_completed'

    Returns:
        {'applied': int, 'skipped': int}
    """
    from app.models.base import get_indian_time

    applied = 0
    skipped = 0

    try:
        lead_id     = lead.id
        category_id = getattr(lead, 'category_id', None)

        _l1_id = getattr(lead, 'associated_partner_id', None)
        _l2_id = getattr(lead, 'team_senior_partner_id', None)
        _l3_id = getattr(lead, 'team_extended_partner_id', None)
        _l4_id = getattr(lead, 'team_core_partner_id', None)
        _l5_id = getattr(lead, 'vgk_field_support_id', None)

        level_partner_map = {
            1: _l1_id,
            2: _l2_id,
            3: _l3_id,
            4: _l4_id,
            5: _l5_id,
        }

        if not any(level_partner_map.values()):
            return {'applied': 0, 'skipped': 0}

        # Fetch all active cash/bonus bonanzas that have at least one per-level trigger configured.
        # Also include bonanzas using the legacy global trigger_event (backward compat).
        _active = db.execute(text("""
            SELECT b.id, b.name, b.max_winners, b.current_winners,
                   b.trigger_event,
                   b.ec_l1_trigger, b.ec_l2_trigger, b.ec_l3_trigger,
                   b.ec_l4_trigger, b.ec_l5_trigger,
                   b.ec_l1_amount,  b.ec_l2_amount,  b.ec_l3_amount,
                   b.ec_l4_amount,  b.ec_l5_amount
            FROM   bonanza b
            WHERE  b.reward_type IN ('cash', 'bonus')
              AND  b.status      = 'Approved'
              AND  b.is_deleted  = FALSE
              AND  NOW()::date BETWEEN b.start_date::date AND b.end_date::date
              AND  (
                   b.ec_l1_trigger IS NOT NULL OR b.ec_l2_trigger IS NOT NULL
                OR b.ec_l3_trigger IS NOT NULL OR b.ec_l4_trigger IS NOT NULL
                OR b.ec_l5_trigger IS NOT NULL OR b.trigger_event IS NOT NULL
              )
        """)).fetchall()

        for _bz in _active:
            try:
                # --- Category filter check ---
                _cat_rows = db.execute(text("""
                    SELECT category_id FROM bonanza_category_filters
                    WHERE bonanza_id = :bid
                """), {'bid': _bz.id}).fetchall()
                if _cat_rows:
                    _allowed_cats = {r.category_id for r in _cat_rows}
                    if category_id not in _allowed_cats:
                        continue

                _global_trigger = getattr(_bz, 'trigger_event', None)
                _max_w = int(_bz.max_winners or 9999)
                _cur_w = int(_bz.current_winners or 0)

                for lv in [1, 2, 3, 4, 5]:
                    partner_id = level_partner_map.get(lv)
                    if not partner_id:
                        skipped += 1
                        continue

                    # DC-EC-PER-LEVEL-TRIGGER-001: resolve effective trigger for this level.
                    _per_trig = getattr(_bz, f'ec_l{lv}_trigger', None)
                    _eff_trig = _per_trig if _per_trig else _global_trigger
                    if _eff_trig != trigger_event:
                        continue

                    # Check amount configured for this level
                    _amt_val = getattr(_bz, f'ec_l{lv}_amount', None)
                    if not _amt_val or float(_amt_val) <= 0:
                        continue

                    # --- Idempotency check ---
                    _exists = db.execute(text("""
                        SELECT id FROM bonanza_extra_commission_log
                        WHERE bonanza_id = :bid AND lead_id = :lid AND level = :lv
                    """), {'bid': _bz.id, 'lid': lead_id, 'lv': lv}).fetchone()
                    if _exists:
                        skipped += 1
                        continue

                    # --- Check max winners ---
                    if _cur_w >= _max_w:
                        logger.warning(
                            f'[DC-CB-TRIGGER-001] Bonanza {_bz.id} max_winners reached '
                            f'— skipping partner {partner_id} L{lv}'
                        )
                        skipped += 1
                        continue

                    _sp = db.begin_nested()
                    try:
                        now_ist = get_indian_time().replace(tzinfo=None)

                        # --- Create BonanzaProgress PENDING claim ---
                        _claim_result = db.execute(text("""
                            INSERT INTO bonanza_progress
                              (bonanza_id, partner_id, current_progress, processed_status,
                               processed_by, auto_triggered, trigger_event_source,
                               claim_level, notes, created_at, updated_at)
                            VALUES
                              (:bid, :pid, 1, 'Pending',
                               'AUTO-TRIGGER', TRUE, :te,
                               :lv, :notes, :now, :now)
                            RETURNING id
                        """), {
                            'bid':   _bz.id,
                            'pid':   partner_id,
                            'te':    trigger_event,
                            'lv':    lv,
                            'notes': (
                                f'Auto-triggered: {_bz.name} | '
                                f'L{lv} | trigger={trigger_event} | '
                                f'amount=₹{float(_amt_val):.0f}'
                            ),
                            'now':   now_ist,
                        })
                        _claim_id = _claim_result.fetchone()[0]

                        # --- Log idempotency record ---
                        db.execute(text("""
                            INSERT INTO bonanza_extra_commission_log
                              (bonanza_id, lead_id, level, partner_id, created_at)
                            VALUES (:bid, :lid, :lv, :pid, :now)
                            ON CONFLICT (bonanza_id, lead_id, level) DO NOTHING
                        """), {
                            'bid': _bz.id, 'lid': lead_id,
                            'lv': lv, 'pid': partner_id, 'now': now_ist,
                        })

                        # --- Increment current_winners ---
                        db.execute(text("""
                            UPDATE bonanza
                            SET current_winners = current_winners + 1
                            WHERE id = :bid
                        """), {'bid': _bz.id})
                        _cur_w += 1

                        _sp.commit()
                        applied += 1
                        logger.info(
                            f'[DC-CB-TRIGGER-001] ✅ Claim #{_claim_id} created: '
                            f'bonanza={_bz.id} partner={partner_id} L{lv} '
                            f'₹{float(_amt_val):.0f} trigger={trigger_event} lead={lead_id}'
                        )

                    except Exception as _spe:
                        try:
                            _sp.rollback()
                        except Exception:
                            pass
                        logger.warning(
                            f'[DC-CB-TRIGGER-001] claim insert non-fatal '
                            f'L{lv} partner={partner_id} bonanza={_bz.id}: {_spe}'
                        )

            except Exception as _bze:
                logger.warning(
                    f'[DC-CB-TRIGGER-001] bonanza={_bz.id} lead={lead_id}: {_bze}'
                )

    except Exception as _e:
        logger.warning(
            f'[DC-CB-TRIGGER-001] outer error lead={getattr(lead, "id", "?")}: {_e}'
        )

    return {'applied': applied, 'skipped': skipped}
