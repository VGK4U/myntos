"""
DC_STOCK_MULTICOMP_001 — Stock Service (Apr 2026)
Central service for all stock ledger writes, average cost calculation,
and inter-company invoice/transfer chain.

Entry types used (per existing StockLedger constraint):
  OPENING            — opening balance
  PURCHASE           — stock-in from vendor purchase invoice / intake
  SALE               — stock-out for any customer sale
  TRANSFER_IN        — inter-company receipt
  TRANSFER_OUT       — inter-company dispatch
  SERVICE_CONSUMPTION — material used in service ticket

Reference types used (per existing constraint):
  OPENING            — opening balance
  VENDOR_TXN         — purchase invoice / intake batch
  SALE               — marketplace / sales invoice / CRM sale
  STOCK_TRANSFER     — inter-company stock transfer
  SERVICE            — service ticket
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.staff_accounts import (
    StockItemMaster, StockLedger, StockTransfer, InterCompanyMarginConfig,
)

logger = logging.getLogger(__name__)

_TWO = Decimal("0.01")
_ZERO = Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Average cost utility
# ─────────────────────────────────────────────────────────────────────────────

def get_avg_cost(db: Session, item_id: int, company_id: int) -> Decimal:
    """
    Weighted average procurement cost for (item_id, company_id).
    Considers only OPENING and PURCHASE entries (quantity_in > 0).
    Returns 0 if no cost data exists.
    """
    row = db.execute(text("""
        SELECT
            SUM(quantity_in * unit_rate) AS total_cost,
            SUM(quantity_in)             AS total_qty
        FROM stock_ledger
        WHERE item_id    = :item_id
          AND company_id = :company_id
          AND entry_type IN ('OPENING', 'PURCHASE')
          AND quantity_in > 0
    """), {"item_id": item_id, "company_id": company_id}).fetchone()

    if not row or not row.total_qty or row.total_qty == 0:
        return _ZERO
    return (Decimal(str(row.total_cost)) / Decimal(str(row.total_qty))).quantize(_TWO, rounding=ROUND_HALF_UP)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Running balance helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_last_balance(db: Session, item_id: int, company_id: int) -> Tuple[Decimal, Decimal]:
    """
    Returns (balance_qty, balance_value) from the latest REAL (non-estimate) ledger row.
    Estimate rows (is_estimate=TRUE) are soft entries — they never contribute to the
    running balance, so we skip them here.
    """
    row = db.execute(text("""
        SELECT balance_qty, balance_value
        FROM stock_ledger
        WHERE item_id = :item_id AND company_id = :company_id
          AND (is_estimate IS NULL OR is_estimate = FALSE)
        ORDER BY id DESC LIMIT 1
    """), {"item_id": item_id, "company_id": company_id}).fetchone()
    if not row:
        return _ZERO, _ZERO
    return Decimal(str(row.balance_qty)), Decimal(str(row.balance_value))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Core ledger append — single source of truth for all stock writes
# ─────────────────────────────────────────────────────────────────────────────

def append_stock_ledger(
    db: Session,
    *,
    item_id:       int,
    company_id:    int,
    entry_type:    str,           # OPENING | PURCHASE | SALE | TRANSFER_IN | TRANSFER_OUT | SERVICE_CONSUMPTION
    reference_type: str,          # OPENING | VENDOR_TXN | SALE | STOCK_TRANSFER | SERVICE
    reference_id:  int,
    reference_number: Optional[str] = None,
    quantity_in:   Decimal = _ZERO,
    quantity_out:  Decimal = _ZERO,
    unit_rate:     Decimal = _ZERO,
    narration:     Optional[str] = None,
    txn_date:      Optional[date] = None,
    updated_by_id: Optional[int] = None,
    specification: Optional[str] = None,
    color:         Optional[str] = None,
    is_estimate:   bool = False,  # True = soft entry for estimation; excluded from real balance
) -> StockLedger:
    """
    Appends one row to stock_ledger and updates marketplace_spares.available_qty.
    Returns the newly created StockLedger row.
    DC: immutable append — never updates existing rows.

    is_estimate=True: The entry is recorded (for traceability) but does NOT move the
    running balance. balance_qty/balance_value stored = previous real balance unchanged.
    marketplace sync is also skipped. Confirm via confirm_estimate_ledger_entry()
    which deletes the soft row and creates a real one.
    """
    qty_in  = Decimal(str(quantity_in))
    qty_out = Decimal(str(quantity_out))
    rate    = Decimal(str(unit_rate))
    movement_val = abs(qty_in - qty_out) * rate

    prev_qty, prev_val = _get_last_balance(db, item_id, company_id)

    if is_estimate:
        # Soft entry: balance is unchanged — estimates are visible but not counted
        new_bal_qty = prev_qty
        new_bal_val = prev_val
    else:
        new_bal_qty = prev_qty + qty_in - qty_out
        new_bal_val = prev_val + (qty_in - qty_out) * rate

    entry = StockLedger(
        company_id       = company_id,
        item_id          = item_id,
        transaction_date = txn_date or date.today(),
        entry_type       = entry_type,
        reference_type   = reference_type,
        reference_id     = reference_id,
        reference_number = reference_number,
        quantity_in      = qty_in,
        quantity_out     = qty_out,
        unit_rate        = rate,
        total_value      = movement_val.quantize(_TWO),
        balance_qty      = new_bal_qty,
        balance_value    = new_bal_val.quantize(_TWO),
        narration        = narration,
        specification    = specification,
        color            = color,
        updated_by_id    = updated_by_id,
        is_estimate      = is_estimate,
    )
    db.add(entry)
    db.flush()  # get entry.id without committing

    # Only sync real stock movements to marketplace_spares
    if not is_estimate:
        _sync_marketplace_available_qty(db, item_id, company_id, new_bal_qty)

    logger.info(
        f"[DC_STOCK] Ledger {'ESTIMATE ' if is_estimate else ''}{entry_type} "
        f"item={item_id} co={company_id} in={qty_in} out={qty_out} "
        f"{'(soft, bal unchanged)' if is_estimate else f'bal={new_bal_qty}'}"
    )
    return entry


def confirm_estimate_ledger_entry(
    db: Session,
    *,
    entry_id: int,
    updated_by_id: Optional[int] = None,
) -> StockLedger:
    """
    Converts a soft estimate ledger entry into a real stock movement.
    Deletes the estimate row and creates a new real append_stock_ledger entry.
    This correctly recalculates the running balance chain at the point of confirmation.
    """
    soft = db.execute(
        text("SELECT * FROM stock_ledger WHERE id = :eid AND is_estimate = TRUE"),
        {"eid": entry_id}
    ).fetchone()
    if not soft:
        raise ValueError(f"No pending estimate ledger entry found with id={entry_id}")

    # Capture values before deletion
    item_id        = soft.item_id
    company_id     = soft.company_id
    entry_type     = soft.entry_type
    reference_type = soft.reference_type
    reference_id   = soft.reference_id
    reference_number = soft.reference_number
    qty_in         = Decimal(str(soft.quantity_in))
    qty_out        = Decimal(str(soft.quantity_out))
    unit_rate      = Decimal(str(soft.unit_rate))
    narration_orig = soft.narration
    txn_date       = soft.transaction_date
    specification  = soft.specification
    color          = soft.color

    # Delete the soft row first
    db.execute(text("DELETE FROM stock_ledger WHERE id = :eid"), {"eid": entry_id})
    db.flush()

    # Create the real entry — balance chain recalculated from scratch
    new_entry = append_stock_ledger(
        db=db,
        item_id=item_id,
        company_id=company_id,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        quantity_in=qty_in,
        quantity_out=qty_out,
        unit_rate=unit_rate,
        narration=f"[CONFIRMED] {narration_orig or ''}".strip(),
        txn_date=txn_date,
        updated_by_id=updated_by_id,
        specification=specification,
        color=color,
        is_estimate=False,
    )
    logger.info(f"[DC_STOCK] Estimate entry {entry_id} confirmed → new real entry {new_entry.id}")
    return new_entry


def _sync_marketplace_available_qty(
    db: Session, item_id: int, company_id: int, new_qty: Decimal
) -> None:
    """
    After any stock ledger write, sync available_qty back to marketplace_spares
    and ensure override_fields contains 'available_qty' (freeze flag).
    Only updates items whose marketplace_sku links to this stock item.
    """
    try:
        sim = db.execute(text(
            "SELECT marketplace_sku FROM stock_item_master WHERE id = :iid"
        ), {"iid": item_id}).fetchone()
        if not sim or not sim.marketplace_sku:
            return

        row = db.execute(text("""
            SELECT id, override_fields
            FROM marketplace_spares
            WHERE sku = :sku AND company_id = :cid
            LIMIT 1
        """), {"sku": sim.marketplace_sku, "cid": company_id}).fetchone()
        if not row:
            return

        existing_overrides = list(row.override_fields or [])
        if "available_qty" not in existing_overrides:
            existing_overrides.append("available_qty")

        db.execute(text("""
            UPDATE marketplace_spares
            SET available_qty   = :qty,
                override_fields = CAST(:ovr AS jsonb),
                updated_at      = NOW()
            WHERE id = :rid
        """), {
            "qty": int(max(new_qty, _ZERO)),
            "ovr": __import__("json").dumps(existing_overrides),
            "rid": row.id,
        })
        logger.debug(f"[DC_STOCK] Synced available_qty={int(new_qty)} → marketplace_spares.sku={sim.marketplace_sku}")
    except Exception as e:
        logger.warning(f"[DC_STOCK] available_qty sync failed for item_id={item_id}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Inter-company margin lookup
# ─────────────────────────────────────────────────────────────────────────────

def get_interco_margin(
    db: Session,
    from_company_id: int,
    to_company_id:   int,
    category_slug:   Optional[str] = None,
) -> Decimal:
    """
    Lookup priority:
      1. from + to + category
      2. from + to (any category)
      3. global (both NULL)
    Returns margin_pct (default 6.00 if nothing configured).
    """
    candidates = db.execute(text("""
        SELECT margin_pct,
               (CASE WHEN from_company_id IS NOT NULL THEN 2 ELSE 0 END +
                CASE WHEN to_company_id   IS NOT NULL THEN 2 ELSE 0 END +
                CASE WHEN category_slug   IS NOT NULL THEN 1 ELSE 0 END) AS specificity
        FROM inter_company_margin_config
        WHERE is_active = TRUE
          AND (from_company_id = :fco OR from_company_id IS NULL)
          AND (to_company_id   = :tco OR to_company_id   IS NULL)
          AND (category_slug   = :cat OR category_slug   IS NULL)
        ORDER BY specificity DESC
        LIMIT 1
    """), {"fco": from_company_id, "tco": to_company_id, "cat": category_slug}).fetchone()

    if candidates:
        return Decimal(str(candidates.margin_pct))
    return Decimal("6.00")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Inter-company transfer chain
# ─────────────────────────────────────────────────────────────────────────────

def process_inter_company_transfer(
    db:               Session,
    *,
    item_id:          int,
    stock_company_id: int,
    selling_company_id: int,
    quantity:         Decimal,
    reference_type:   str,     # SALE | STOCK_TRANSFER
    reference_id:     int,
    reference_number: Optional[str] = None,
    category_slug:    Optional[str] = None,
    txn_date:         Optional[date] = None,
    created_by_id:    Optional[int] = None,
    narration:        Optional[str] = None,
) -> dict:
    """
    Full inter-company stock chain:
      1. Avg cost from stock_company's ledger
      2. Apply configured margin → transfer_rate
      3. Create stock_transfer record
      4. TRANSFER_OUT from stock_company
      5. TRANSFER_IN  to selling_company
    Returns dict with transfer_id and transfer_rate.
    DC: All writes are flushed (not committed) — caller commits.
    """
    qty = Decimal(str(quantity))
    avg_cost      = get_avg_cost(db, item_id, stock_company_id)
    margin_pct    = get_interco_margin(db, stock_company_id, selling_company_id, category_slug)
    transfer_rate = (avg_cost * (1 + margin_pct / 100)).quantize(_TWO, rounding=ROUND_HALF_UP)

    # Generate transfer number
    count = db.execute(text("SELECT COUNT(*) FROM stock_transfers")).scalar() or 0
    t_num = f"IST-{(count+1):05d}"

    transfer = StockTransfer(
        transfer_number   = t_num,
        from_company_id   = stock_company_id,
        to_company_id     = selling_company_id,
        transfer_date     = txn_date or date.today(),
        item_id           = item_id,
        quantity          = qty,
        unit_rate         = transfer_rate,
        total_value       = (qty * transfer_rate).quantize(_TWO),
        transfer_type     = "SALE",
        narration         = narration or f"Inter-company: {reference_type} #{reference_id}",
        status            = "RECEIVED",
        dispatched_at     = datetime.utcnow(),
        received_at       = datetime.utcnow(),
        created_by_id     = created_by_id,
    )
    db.add(transfer)
    db.flush()

    # TRANSFER_OUT — stock company loses stock
    out_entry = append_stock_ledger(
        db,
        item_id          = item_id,
        company_id       = stock_company_id,
        entry_type       = "TRANSFER_OUT",
        reference_type   = "STOCK_TRANSFER",
        reference_id     = transfer.id,
        reference_number = t_num,
        quantity_out     = qty,
        unit_rate        = transfer_rate,
        narration        = f"Inter-co transfer to company {selling_company_id}: {narration or ''}",
        txn_date         = txn_date,
        updated_by_id    = created_by_id,
    )
    transfer.from_stock_entry_id = out_entry.id

    # TRANSFER_IN — selling company gains stock
    in_entry = append_stock_ledger(
        db,
        item_id          = item_id,
        company_id       = selling_company_id,
        entry_type       = "TRANSFER_IN",
        reference_type   = "STOCK_TRANSFER",
        reference_id     = transfer.id,
        reference_number = t_num,
        quantity_in      = qty,
        unit_rate        = transfer_rate,
        narration        = f"Inter-co transfer from company {stock_company_id}: {narration or ''}",
        txn_date         = txn_date,
        updated_by_id    = created_by_id,
    )
    transfer.to_stock_entry_id = in_entry.id
    db.flush()

    logger.info(
        f"[DC_STOCK] Inter-co transfer {t_num}: co{stock_company_id}→co{selling_company_id} "
        f"item={item_id} qty={qty} rate={transfer_rate} margin={margin_pct}%"
    )
    return {
        "transfer_id":    transfer.id,
        "transfer_number": t_num,
        "transfer_rate":  float(transfer_rate),
        "margin_pct":     float(margin_pct),
        "avg_cost":       float(avg_cost),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Stock balance query helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_stock_balance(db: Session, item_id: int, company_id: int) -> dict:
    """Current balance for a single item+company from latest ledger row."""
    qty, val = _get_last_balance(db, item_id, company_id)
    avg = get_avg_cost(db, item_id, company_id)
    return {
        "item_id":       item_id,
        "company_id":    company_id,
        "balance_qty":   float(qty),
        "balance_value": float(val),
        "avg_cost":      float(avg),
    }


def get_all_company_balances(db: Session, item_id: int) -> list:
    """Returns per-company balance for a given item across all companies."""
    rows = db.execute(text("""
        SELECT DISTINCT ON (company_id)
               company_id, balance_qty, balance_value
        FROM stock_ledger
        WHERE item_id = :iid
        ORDER BY company_id, id DESC
    """), {"iid": item_id}).fetchall()
    return [
        {
            "company_id":    r.company_id,
            "balance_qty":   float(r.balance_qty),
            "balance_value": float(r.balance_value),
        }
        for r in rows
    ]


def get_company_stock_summary(db: Session, company_id: Optional[int] = None) -> list:
    """
    Returns one row per stock item with current balance, avg cost, and low-qty flag.
    If company_id is None, aggregates across all companies.
    """
    if company_id:
        rows = db.execute(text("""
            SELECT
                sim.id           AS item_id,
                sim.item_code,
                sim.item_name,
                sim.item_category,
                sim.marketplace_sku,
                sim.reorder_level,
                sim.default_gst_rate,
                sl.balance_qty,
                sl.balance_value,
                sl.company_id
            FROM stock_item_master sim
            LEFT JOIN LATERAL (
                SELECT balance_qty, balance_value, company_id
                FROM stock_ledger
                WHERE item_id = sim.id AND company_id = :cid
                ORDER BY id DESC LIMIT 1
            ) sl ON TRUE
            WHERE sim.is_active = TRUE
            ORDER BY sim.item_name
        """), {"cid": company_id}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT
                sim.id           AS item_id,
                sim.item_code,
                sim.item_name,
                sim.item_category,
                sim.marketplace_sku,
                sim.reorder_level,
                sim.default_gst_rate,
                COALESCE(SUM(sl.balance_qty), 0)   AS balance_qty,
                COALESCE(SUM(sl.balance_value), 0) AS balance_value,
                NULL::integer                      AS company_id
            FROM stock_item_master sim
            LEFT JOIN LATERAL (
                SELECT balance_qty, balance_value
                FROM stock_ledger
                WHERE item_id = sim.id
                ORDER BY id DESC LIMIT 1
            ) sl ON TRUE
            WHERE sim.is_active = TRUE
            GROUP BY sim.id, sim.item_code, sim.item_name, sim.item_category,
                     sim.marketplace_sku, sim.reorder_level, sim.default_gst_rate
            ORDER BY sim.item_name
        """)).fetchall()

    result = []
    for r in rows:
        bal  = float(r.balance_qty or 0)
        rl   = int(r.reorder_level or 0)
        result.append({
            "item_id":       r.item_id,
            "item_code":     r.item_code,
            "item_name":     r.item_name,
            "item_category": r.item_category,
            "marketplace_sku": r.marketplace_sku,
            "company_id":    r.company_id,
            "balance_qty":   bal,
            "balance_value": float(r.balance_value or 0),
            "reorder_level": rl,
            "is_low_stock":  rl > 0 and bal < rl,
            "is_zero_stock": bal <= 0,
        })
    return result
