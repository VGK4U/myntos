"""
DC-AWARD-TRIGGER-001 (Jul 2026): Award/Gift bonanza trigger service.
DC-EC-PER-LEVEL-TRIGGER-001 (Jul 2026): Per-level trigger events for award/gift types.

When a pipeline event fires (file_submitted/first_payment/file_completed),
this service:
  1. Finds all APPROVED award/gift bonanzas active today.
  2. For each bonanza, resolves the effective trigger per level:
       effective_trigger = ec_lN_trigger (if set) else global trigger_event
     Only levels whose effective_trigger matches the current event are processed.
  3. For each participating + matching level (configured in award_level_notes JSONB):
       - Logs a trigger fire in bonanza_trigger_log (idempotent per bonanza+partner+lead)
       - Counts unconsumed fires for this partner+bonanza
       - If count >= target AND no open claim exists: auto-creates a Pending claim
       - Marks those trigger log rows as consumed by the new claim
       - Credits gross VGK points with reason BONANZA_CASH_CREDIT
  4. Returns counters for logging.

Uniqueness rules:
  - Within a bonanza: each (bonanza_id, partner_id, lead_id) is unique — no double-counting
    the same lead for the same bonanza across multiple claims.
  - Across bonanzas: independent — same lead counts for each different bonanza separately.
  - Same lead fires independently per level per bonanza (L1 and L5 can both fire).
"""

import json
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session


def apply_award_gift_trigger_if_active(
    db: Session,
    lead,
    trigger_event: str,
) -> dict:
    """
    Find all active award/gift bonanzas, resolve per-level trigger events,
    log trigger fires per participating level, and auto-create Pending claims
    when a partner's unconsumed fire count reaches the bonanza target.

    Args:
        db            — SQLAlchemy session (caller owns commit)
        lead          — CRMLead ORM object (or namedtuple with same fields)
        trigger_event — 'file_submitted' | 'first_payment' | 'file_completed'

    Returns:
        {'logged': int, 'claims_created': int, 'skipped': int}
    """
    from app.models.base import get_indian_time

    logged = 0
    claims_created = 0
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
            return {'logged': 0, 'claims_created': 0, 'skipped': 0}

        # DC-EC-PER-LEVEL-TRIGGER-001: fetch all active award/gift bonanzas (no global trigger filter —
        # per-level trigger matching is done in Python below).
        _active = db.execute(text("""
            SELECT b.id, b.name, b.target_requirement, b.max_winners,
                   b.current_winners, b.total_budget, b.award_name,
                   b.award_level_notes,
                   b.trigger_event,
                   b.ec_l1_trigger, b.ec_l2_trigger, b.ec_l3_trigger,
                   b.ec_l4_trigger, b.ec_l5_trigger
            FROM   bonanza b
            WHERE  b.reward_type IN ('award', 'gift')
              AND  b.status      = 'Approved'
              AND  b.is_deleted  = FALSE
              AND  NOW()::date BETWEEN b.start_date::date AND b.end_date::date
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

                # --- Parse level participation from award_level_notes JSONB ---
                _raw_notes = _bz.award_level_notes
                if isinstance(_raw_notes, str):
                    try:
                        _lvl_cfg = json.loads(_raw_notes)
                    except Exception:
                        _lvl_cfg = {}
                elif isinstance(_raw_notes, dict):
                    _lvl_cfg = _raw_notes
                else:
                    _lvl_cfg = {}

                # If no config, all levels with a non-null partner participate
                if not _lvl_cfg:
                    _participating = [lv for lv, pid in level_partner_map.items() if pid]
                else:
                    _participating = []
                    for _lv_str, _cfg in _lvl_cfg.items():
                        try:
                            _lv_int = int(_lv_str)
                        except Exception:
                            continue
                        if isinstance(_cfg, dict):
                            if _cfg.get('participate', False):
                                _participating.append(_lv_int)
                        elif bool(_cfg):
                            _participating.append(_lv_int)

                if not _participating:
                    continue

                _global_trigger = getattr(_bz, 'trigger_event', None)
                _target = max(int(_bz.target_requirement or 1), 1)
                _max_w  = int(_bz.max_winners or 9999)
                _budget = float(_bz.total_budget or 0)

                for lv in _participating:
                    partner_id = level_partner_map.get(lv)
                    if not partner_id:
                        continue

                    # DC-EC-PER-LEVEL-TRIGGER-001: resolve per-level effective trigger.
                    _per_trig = getattr(_bz, f'ec_l{lv}_trigger', None)
                    _eff_trig = _per_trig if _per_trig else _global_trigger
                    if _eff_trig != trigger_event:
                        continue  # this level's trigger doesn't match current event

                    # --- Log trigger fire (idempotent — UNIQUE bonanza+partner+lead) ---
                    try:
                        db.execute(text("""
                            INSERT INTO bonanza_trigger_log
                              (bonanza_id, partner_id, lead_id, trigger_event, created_at)
                            VALUES (:bid, :pid, :lid, :te, NOW())
                            ON CONFLICT (bonanza_id, partner_id, lead_id) DO NOTHING
                        """), {'bid': _bz.id, 'pid': partner_id, 'lid': lead_id, 'te': trigger_event})
                        logged += 1
                    except Exception as _log_e:
                        print(f"[DC-AWARD-TRIGGER-001] ⚠️ Log insert error: {_log_e}", flush=True)
                        skipped += 1
                        continue

                    # --- Skip if open claim already exists for this partner+bonanza ---
                    _existing = db.execute(text("""
                        SELECT id FROM bonanza_progress
                        WHERE bonanza_id       = :bid
                          AND partner_id       = :pid
                          AND processed_status NOT IN ('Rejected')
                        LIMIT 1
                    """), {'bid': _bz.id, 'pid': partner_id}).fetchone()
                    if _existing:
                        skipped += 1
                        continue

                    # --- Count unconsumed fires for this partner+bonanza ---
                    _avail_row = db.execute(text("""
                        SELECT COUNT(*) AS cnt
                        FROM bonanza_trigger_log
                        WHERE bonanza_id           = :bid
                          AND partner_id           = :pid
                          AND consumed_by_claim_id IS NULL
                    """), {'bid': _bz.id, 'pid': partner_id}).fetchone()
                    _avail_count = int(_avail_row.cnt if _avail_row else 0)

                    if _avail_count < _target:
                        continue

                    # --- Check max winners ---
                    _cur_winners = int(_bz.current_winners or 0)
                    if _cur_winners >= _max_w:
                        print(
                            f"[DC-AWARD-TRIGGER-001] ⚠️ Bonanza {_bz.id} max_winners reached — "
                            f"skipping partner {partner_id}", flush=True
                        )
                        skipped += 1
                        continue

                    # --- Auto-create Pending claim ---
                    now_ist = get_indian_time().replace(tzinfo=None)
                    _claim_result = db.execute(text("""
                        INSERT INTO bonanza_progress
                          (bonanza_id, partner_id, current_progress, processed_status,
                           processed_by, auto_triggered, trigger_event_source,
                           claim_level, notes, created_at, updated_at)
                        VALUES
                          (:bid, :pid, :progress, 'Pending',
                           'AUTO-TRIGGER', TRUE, :te,
                           :lv, :notes, :now, :now)
                        RETURNING id
                    """), {
                        'bid':      _bz.id,
                        'pid':      partner_id,
                        'progress': _target,
                        'te':       trigger_event,
                        'lv':       lv,
                        'notes':    (
                            f"Auto-triggered: {_bz.award_name or _bz.name} | "
                            f"L{lv} | trigger={trigger_event} | "
                            f"{_target} deal(s) achieved"
                        ),
                        'now':      now_ist,
                    })
                    _claim_id = _claim_result.fetchone()[0]
                    claims_created += 1

                    # --- Consume exactly target-count trigger log rows (oldest first) ---
                    db.execute(text("""
                        UPDATE bonanza_trigger_log
                        SET consumed_by_claim_id = :cid
                        WHERE id IN (
                            SELECT id FROM bonanza_trigger_log
                            WHERE bonanza_id           = :bid
                              AND partner_id           = :pid
                              AND consumed_by_claim_id IS NULL
                            ORDER BY created_at ASC
                            LIMIT :tgt
                        )
                    """), {'cid': _claim_id, 'bid': _bz.id, 'pid': partner_id, 'tgt': _target})

                    # --- Increment current_winners ---
                    db.execute(text("""
                        UPDATE bonanza
                        SET current_winners = current_winners + 1
                        WHERE id = :bid
                    """), {'bid': _bz.id})

                    print(
                        f"[DC-AWARD-TRIGGER-001] ✅ Auto-claim #{_claim_id} created: "
                        f"bonanza={_bz.id} partner={partner_id} L{lv} trigger={trigger_event}",
                        flush=True
                    )

                    # --- Credit gross VGK points (if budget is set) ---
                    if _budget > 0:
                        try:
                            _pts_gross = Decimal(str(int(round(_budget))))
                            _pts_row = db.execute(text("""
                                SELECT vgk_points_balance, company_id
                                FROM official_partners
                                WHERE id = :pid
                                FOR UPDATE
                            """), {'pid': partner_id}).fetchone()
                            if _pts_row:
                                _pts_bal   = Decimal(str(float(_pts_row.vgk_points_balance or 0)))
                                _pts_after = _pts_bal + _pts_gross
                                db.execute(text("""
                                    INSERT INTO vgk_points_ledger
                                      (partner_id, points_credit, points_debit, balance_after,
                                       reason_code, reference_type, reference_id,
                                       notes, created_at)
                                    VALUES
                                      (:pid, :cr, 0, :bal,
                                       'BONANZA_CASH_CREDIT', 'bonanza_progress', :ref_id,
                                       :notes, :now)
                                """), {
                                    'pid':    partner_id,
                                    'cr':     _pts_gross,
                                    'bal':    _pts_after,
                                    'ref_id': _claim_id,
                                    'notes':  (
                                        f"Bonanza achieved — "
                                        f"{_bz.award_name or _bz.name} | "
                                        f"L{lv} | claim #{_claim_id}"
                                    ),
                                    'now':    now_ist,
                                })
                                db.execute(text("""
                                    UPDATE official_partners
                                    SET vgk_points_balance = :bal
                                    WHERE id = :pid
                                """), {'bal': _pts_after, 'pid': partner_id})
                        except Exception as _pts_e:
                            print(f"[DC-AWARD-TRIGGER-001] ⚠️ Points credit error: {_pts_e}", flush=True)

            except Exception as _bz_e:
                print(f"[DC-AWARD-TRIGGER-001] ⚠️ Bonanza {_bz.id} error: {_bz_e}", flush=True)
                try:
                    db.rollback()
                except Exception:
                    pass
                skipped += 1
                continue

    except Exception as _outer:
        print(f"[DC-AWARD-TRIGGER-001] ⚠️ Outer error: {_outer}", flush=True)

    return {'logged': logged, 'claims_created': claims_created, 'skipped': skipped}


def release_trigger_log_for_claim(db: Session, claim_id: int) -> int:
    """
    DC-AWARD-TRIGGER-001: When a claim is Rejected, release all trigger_log rows
    consumed by this claim back to the pool (set consumed_by_claim_id = NULL).
    Also decrements current_winners on the bonanza if auto-triggered.
    Returns count of rows released.
    """
    result = db.execute(text("""
        UPDATE bonanza_trigger_log
        SET consumed_by_claim_id = NULL
        WHERE consumed_by_claim_id = :cid
    """), {'cid': claim_id})
    released = result.rowcount

    if released > 0:
        db.execute(text("""
            UPDATE bonanza b
            SET current_winners = GREATEST(0, current_winners - 1)
            FROM bonanza_progress bp
            WHERE bp.id            = :cid
              AND b.id             = bp.bonanza_id
              AND bp.auto_triggered = TRUE
        """), {'cid': claim_id})

    return released
