"""
Task #42 — Phase 4 billing services.

generate_invoice_for_subscription(db, subscription_id, period_start, period_end)
    Builds invoice + lines from effective pricing for that subscription.

apply_payment(db, invoice_id, amount, ...)
    Records a payment, updates invoice status (open→partial/paid).

run_dunning(db, *, grace_days=10, dry_run=False)
    Marks overdue invoices, suspends clients past grace_days. Returns counts.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.platform_b2b import (
    PlatformClient, PlatformSubscription, PlatformSubscriptionModule,
)
from app.models.platform_b2b_billing import (
    PlatformInvoice, PlatformInvoiceLine, PlatformPayment,
)
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)


def _next_invoice_number(db: Session) -> str:
    """B2B-YYYYMM-NNNN — sequential per month, race-safe.

    Uses a counter table with INSERT...ON CONFLICT DO UPDATE...RETURNING so two
    concurrent transactions can never claim the same sequence number. The table
    is created lazily so this works even on databases that haven't run the
    Phase 4 DDL yet (defensive — the seeder normally creates it).
    """
    today = date.today()
    period = f"{today.year:04d}{today.month:02d}"
    prefix = f"B2B-{period}-"
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS platform_invoice_counters (
            period   VARCHAR(8) PRIMARY KEY,
            last_seq INTEGER NOT NULL DEFAULT 0
        )
    """))
    # Seed counter from existing MAX(seq) for this period if not yet present —
    # protects against environments where invoices pre-existed the counter
    # table (i.e. the Phase-4 migration was rolled out after data already had
    # been inserted by an earlier development counter).
    existing_max = db.execute(text("""
        SELECT COALESCE(MAX(CAST(SUBSTRING(invoice_number FROM '\\d+$') AS INTEGER)), 0)
          FROM platform_invoices
         WHERE invoice_number LIKE :pfx
    """), {"pfx": prefix + "%"}).scalar() or 0
    seq = db.execute(text("""
        INSERT INTO platform_invoice_counters (period, last_seq)
             VALUES (:p, :start_at)
        ON CONFLICT (period) DO UPDATE
            SET last_seq = GREATEST(
                platform_invoice_counters.last_seq,
                EXCLUDED.last_seq - 1
            ) + 1
          RETURNING last_seq
    """), {"p": period, "start_at": int(existing_max) + 1}).scalar()
    return f"{prefix}{int(seq):04d}"


def _effective_lines_for_subscription(db: Session, subscription_id: int) -> List[Dict[str, Any]]:
    """Per-module lines using effective pricing (override > global)."""
    rows = db.execute(text("""
        SELECT
            pm.id          AS module_id,
            pm.module_code AS module_code,
            pm.module_name AS module_name,
            COALESCE(ovr.price_inr,    pmp.price_inr,    0)            AS price_inr,
            COALESCE(ovr.price_usd,    pmp.price_usd,    0)            AS price_usd,
            COALESCE(ovr.pricing_unit, pmp.pricing_unit, 'per_company') AS pricing_unit
          FROM platform_subscription_modules psm
          JOIN platform_subscriptions ps ON ps.id = psm.subscription_id
          JOIN platform_modules pm       ON pm.id = psm.module_id
     LEFT JOIN platform_module_pricing pmp                 ON pmp.module_id = pm.id
     LEFT JOIN platform_client_module_pricing_override ovr
                ON ovr.client_id = ps.client_id AND ovr.module_id = pm.id
         WHERE psm.subscription_id = :sid
           AND psm.enabled = TRUE
         ORDER BY pm.module_code
    """), {"sid": subscription_id}).mappings().all()
    return [dict(r) for r in rows]


def generate_invoice_for_subscription(
    db: Session,
    subscription_id: int,
    *,
    period_start: Optional[date] = None,
    period_end:   Optional[date] = None,
    due_in_days:  int = 14,
    actor_staff_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create an invoice for the given subscription's current period."""
    sub = db.query(PlatformSubscription).filter_by(id=subscription_id).first()
    if not sub:
        raise ValueError("subscription not found")
    client = db.query(PlatformClient).filter_by(id=sub.client_id).first()
    if not client:
        raise ValueError("client not found")
    if client.is_internal:
        raise ValueError("internal tenant is never invoiced")

    today = date.today()
    if period_start is None:
        period_start = today.replace(day=1)
    if period_end is None:
        # last day of the same month
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1, day=1) - timedelta(days=1)

    currency = (sub.billing_currency or client.billing_currency or "INR").upper()
    cycle    = (sub.billing_cycle or "monthly").lower()

    rows = _effective_lines_for_subscription(db, subscription_id)

    # Annual gets "2 free months" → 10/12 of monthly subtotal × 12
    annual_multiplier = 1
    annual_factor = Decimal("1")
    if cycle == "annual":
        free_months = sub.annual_free_months if sub.annual_free_months is not None else 2
        annual_multiplier = 12 - int(free_months or 0)
        annual_factor = Decimal(annual_multiplier)
        # extend the period end to ~1 year ahead
        try:
            period_end = period_start.replace(year=period_start.year + 1) - timedelta(days=1)
        except ValueError:
            period_end = period_start + timedelta(days=365)

    inv = PlatformInvoice(
        invoice_number=_next_invoice_number(db),
        client_id=client.id,
        subscription_id=sub.id,
        currency=currency,
        period_start=period_start,
        period_end=period_end,
        due_date=today + timedelta(days=due_in_days),
        subtotal=0, tax=0, total=0, amount_paid=0,
        status="open",
        notes=f"auto-generated for sub#{sub.id} ({cycle})",
    )
    db.add(inv); db.flush()

    subtotal = Decimal("0")
    for r in rows:
        unit = Decimal(str(r["price_inr" if currency == "INR" else "price_usd"]))
        if cycle == "annual":
            unit = unit * annual_factor
            qty_label = f"{annual_multiplier} months (annual)"
        else:
            qty_label = "1 month"
        line = PlatformInvoiceLine(
            invoice_id=inv.id,
            module_id=r["module_id"],
            description=f"{r['module_code']} — {r['module_name']} [{qty_label}]",
            quantity=1,
            unit_price=unit,
            line_total=unit,
            pricing_unit=r["pricing_unit"],
        )
        db.add(line)
        subtotal += unit

    inv.subtotal = subtotal
    inv.tax = Decimal("0")
    inv.total = subtotal + inv.tax
    inv.updated_at = get_indian_time()
    db.commit(); db.refresh(inv)

    return {
        "id": inv.id, "invoice_number": inv.invoice_number,
        "client_id": inv.client_id, "subscription_id": inv.subscription_id,
        "currency": inv.currency, "subtotal": float(inv.subtotal),
        "tax": float(inv.tax), "total": float(inv.total),
        "due_date": inv.due_date.isoformat(), "status": inv.status,
        "line_count": len(rows),
    }


def apply_payment(
    db: Session,
    *,
    invoice_id: Optional[int],
    client_id:  Optional[int],
    amount: float,
    currency: str = "INR",
    method:  Optional[str] = None,
    reference: Optional[str] = None,
    received_on: Optional[date] = None,
    notes: Optional[str] = None,
    recorded_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Record a payment. Updates invoice status if invoice_id is provided."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    inv: Optional[PlatformInvoice] = None
    if invoice_id:
        inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
        if not inv:
            raise ValueError("invoice not found")
        client_id = inv.client_id
        currency  = inv.currency
    if client_id is None:
        raise ValueError("client_id is required when invoice_id is not provided")

    p = PlatformPayment(
        client_id=client_id, invoice_id=invoice_id,
        amount=Decimal(str(amount)), currency=currency,
        method=method, reference=reference,
        received_on=received_on or date.today(),
        notes=notes, recorded_by=recorded_by,
    )
    db.add(p); db.flush()

    if inv is not None:
        inv.amount_paid = (Decimal(str(inv.amount_paid or 0)) + Decimal(str(amount)))
        if inv.amount_paid >= inv.total:
            inv.status = "paid"
        elif inv.amount_paid > 0:
            inv.status = "partial"
        inv.updated_at = get_indian_time()

    db.commit(); db.refresh(p)
    return {
        "id": p.id, "invoice_id": p.invoice_id, "client_id": p.client_id,
        "amount": float(p.amount), "currency": p.currency, "method": p.method,
        "received_on": p.received_on.isoformat(),
        "invoice_status": inv.status if inv else None,
        "invoice_amount_paid": float(inv.amount_paid) if inv else None,
    }


def _period_for_subscription(sub) -> tuple:
    """Return (period_start, period_end, cycle) for the *current* billing window.

    Monthly  — calendar month containing today.
    Annual   — sub.starts_on .. sub.starts_on + 1y - 1d  (or current year if no
               starts_on); we stick to subscription-anniversary semantics so
               pro-rata for annual subs is sensible.
    """
    today = date.today()
    cycle = (getattr(sub, "billing_cycle", None) or "monthly").lower()
    if cycle == "annual":
        ps = sub.starts_on or today.replace(month=1, day=1)
        try:
            pe = ps.replace(year=ps.year + 1) - timedelta(days=1)
        except ValueError:
            pe = ps + timedelta(days=365)
        # If the sub has an explicit ends_on within that window, prefer it.
        if sub.ends_on and sub.ends_on >= ps:
            pe = sub.ends_on
        return ps, pe, cycle
    # monthly default
    ps = today.replace(day=1)
    if ps.month == 12:
        pe = ps.replace(year=ps.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        pe = ps.replace(month=ps.month + 1, day=1) - timedelta(days=1)
    return ps, pe, cycle


def _module_pricing_for(db: Session, client_id: int, module_id: int) -> Optional[Dict[str, Any]]:
    """Effective pricing (override > global > zero) for a single module."""
    row = db.execute(text("""
        SELECT pm.module_code, pm.module_name,
               COALESCE(ovr.price_inr,    pmp.price_inr,    0)            AS price_inr,
               COALESCE(ovr.price_usd,    pmp.price_usd,    0)            AS price_usd,
               COALESCE(ovr.pricing_unit, pmp.pricing_unit, 'per_company') AS pricing_unit
          FROM platform_modules pm
          LEFT JOIN platform_module_pricing pmp ON pmp.module_id = pm.id
          LEFT JOIN platform_client_module_pricing_override ovr
                 ON ovr.client_id = :cid AND ovr.module_id = pm.id
         WHERE pm.id = :mid
    """), {"mid": module_id, "cid": client_id}).mappings().first()
    return dict(row) if row else None


def apply_subscription_module_delta(
    db: Session,
    subscription_id: int,
    *,
    add_module_ids: Optional[List[int]] = None,
    remove_module_ids: Optional[List[int]] = None,
    actor_staff_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Phase 3a.2 — apply a module delta to a subscription and (when eligible)
    emit a single pro-rata adjustment invoice for the remainder of the
    current billing window.

    Eligibility for pro-rata invoicing:
      • client is not internal
      • subscription.status == 'active'
      • days_remaining > 0 in the current window
      • at least one nonzero-priced add or remove

    Always-applied side-effects (regardless of pro-rata eligibility):
      • for each add_id: insert/enable the platform_subscription_modules row.
      • for each remove_id: delete the platform_subscription_modules row.

    Returns:
      {sub_id, added, removed, invoice_id|None, invoice_number|None,
       charged, credited, currency, skipped_reason|None}
    """
    sub = db.query(PlatformSubscription).filter_by(id=subscription_id).first()
    if not sub:
        raise ValueError("subscription not found")
    client = db.query(PlatformClient).filter_by(id=sub.client_id).first()
    if not client:
        raise ValueError("client not found")

    add_ids = list(dict.fromkeys(int(x) for x in (add_module_ids or [])))
    remove_ids = list(dict.fromkeys(int(x) for x in (remove_module_ids or [])))

    # ── Mutate sub_modules first (these always apply) ────────────────────────
    added_actually: List[int] = []
    removed_actually: List[int] = []
    for mid in add_ids:
        ex = db.query(PlatformSubscriptionModule).filter_by(
            subscription_id=subscription_id, module_id=mid).first()
        if ex:
            if not ex.enabled:
                ex.enabled = True
                ex.updated_at = get_indian_time()
                added_actually.append(mid)
        else:
            db.add(PlatformSubscriptionModule(
                subscription_id=subscription_id, module_id=mid, enabled=True))
            added_actually.append(mid)
    for mid in remove_ids:
        ex = db.query(PlatformSubscriptionModule).filter_by(
            subscription_id=subscription_id, module_id=mid).first()
        if ex:
            db.delete(ex)
            removed_actually.append(mid)
    db.flush()

    base_result = {
        "sub_id": subscription_id,
        "added": added_actually, "removed": removed_actually,
        "invoice_id": None, "invoice_number": None,
        "charged": 0.0, "credited": 0.0,
        "currency": (sub.billing_currency or "INR").upper(),
    }

    if client.is_internal:
        db.commit()
        return {**base_result, "skipped_reason": "internal-tenant"}
    if (sub.status or "").lower() != "active":
        db.commit()
        return {**base_result, "skipped_reason": f"sub-status-{sub.status}"}
    if not (added_actually or removed_actually):
        db.commit()
        return {**base_result, "skipped_reason": "no-delta"}

    period_start, period_end, cycle = _period_for_subscription(sub)
    today = date.today()
    if today > period_end:
        db.commit()
        return {**base_result, "skipped_reason": "period-ended"}
    days_in_period = max(1, (period_end - period_start).days + 1)
    days_remaining = max(0, (period_end - today).days + 1)
    if days_remaining <= 0:
        db.commit()
        return {**base_result, "skipped_reason": "zero-days-remaining"}

    fraction = Decimal(days_remaining) / Decimal(days_in_period)
    currency = base_result["currency"]
    seats = int(getattr(sub, "seat_count", 1) or 1)

    # Annual cycle: list price for the cycle = monthly_price × (12 - free_months).
    annual_factor = Decimal("1")
    if cycle == "annual":
        free = sub.annual_free_months if sub.annual_free_months is not None else 2
        annual_factor = Decimal(max(0, 12 - int(free or 0)))

    def _line_for(module_id: int, sign: int) -> Optional[Dict[str, Any]]:
        m = _module_pricing_for(db, sub.client_id, module_id)
        if not m:
            return None
        base = Decimal(str(m["price_inr" if currency == "INR" else "price_usd"]))
        if m["pricing_unit"] == "per_seat":
            base = base * Decimal(seats)
        cycle_unit = base * annual_factor
        prorated = (cycle_unit * fraction).quantize(Decimal("0.01"))
        if prorated == 0:
            return None
        signed = prorated if sign > 0 else (-prorated)
        tag = "pro-rata add" if sign > 0 else "pro-rata credit"
        return {
            "module_id": module_id,
            "description": (
                f"{m['module_code']} — {m['module_name']} "
                f"[{tag}: {days_remaining}/{days_in_period} days of {cycle}]"
            ),
            "unit_price": signed,
            "pricing_unit": m["pricing_unit"],
            "abs": prorated,
        }

    lines: List[Dict[str, Any]] = []
    charged = Decimal("0")
    credited = Decimal("0")
    for mid in added_actually:
        L = _line_for(mid, +1)
        if L is not None:
            lines.append(L); charged += L["abs"]
    for mid in removed_actually:
        L = _line_for(mid, -1)
        if L is not None:
            lines.append(L); credited += L["abs"]

    if not lines:
        db.commit()
        return {**base_result, "skipped_reason": "all-zero-priced"}

    inv = PlatformInvoice(
        invoice_number=_next_invoice_number(db),
        client_id=client.id, subscription_id=sub.id, currency=currency,
        period_start=today, period_end=period_end,
        due_date=today + timedelta(days=14),
        subtotal=0, tax=0, total=0, amount_paid=0, status="open",
        notes=(f"pro-rata adjustment for sub#{sub.id} ({cycle}) — "
               f"adds={len(added_actually)} removes={len(removed_actually)}"),
    )
    db.add(inv); db.flush()
    subtotal = Decimal("0")
    for L in lines:
        line = PlatformInvoiceLine(
            invoice_id=inv.id, module_id=L["module_id"],
            description=L["description"], quantity=1,
            unit_price=L["unit_price"], line_total=L["unit_price"],
            pricing_unit=L["pricing_unit"],
        )
        db.add(line)
        subtotal += L["unit_price"]
    inv.subtotal = subtotal
    inv.tax = Decimal("0")
    inv.total = subtotal
    # Tally/Zoho-parity totals (Phase 5 columns):
    try:
        inv.taxable_amount = subtotal
        inv.grand_total    = subtotal
        inv.balance_due    = subtotal
    except AttributeError:
        pass
    inv.updated_at = get_indian_time()
    db.commit(); db.refresh(inv)

    return {
        **base_result,
        "invoice_id": inv.id, "invoice_number": inv.invoice_number,
        "charged": float(charged), "credited": float(credited),
        "skipped_reason": None,
    }


def run_dunning(
    db: Session,
    *,
    grace_days: int = 10,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    1) Mark unpaid invoices past due_date as 'overdue'.
    2) For invoices overdue by > grace_days, suspend the client.
    Returns counts; non-destructive when dry_run=True.
    """
    today = date.today()
    cutoff = today - timedelta(days=grace_days)

    overdue_rows = db.execute(text("""
        SELECT id, client_id, due_date FROM platform_invoices
         WHERE status IN ('open','partial')
           AND due_date < :today
    """), {"today": today}).mappings().all()
    overdue_ids = [r["id"] for r in overdue_rows]
    suspend_clients = sorted({
        r["client_id"] for r in overdue_rows if r["due_date"] < cutoff
    })

    actions: List[str] = []
    if not dry_run and overdue_ids:
        db.execute(
            text("UPDATE platform_invoices SET status='overdue', updated_at=NOW() "
                 "WHERE id = ANY(:ids) AND status IN ('open','partial')"),
            {"ids": overdue_ids},
        )
        actions.append(f"marked {len(overdue_ids)} invoices overdue")
    if not dry_run and suspend_clients:
        db.execute(
            text("UPDATE platform_clients SET status='suspended', updated_at=NOW() "
                 "WHERE id = ANY(:ids) AND is_internal=FALSE AND status NOT IN ('suspended','archived')"),
            {"ids": suspend_clients},
        )
        actions.append(f"suspended {len(suspend_clients)} clients past grace ({grace_days}d)")
    if not dry_run:
        db.commit()

    return {
        "today": today.isoformat(),
        "grace_days": grace_days,
        "dry_run": dry_run,
        "overdue_invoice_count": len(overdue_ids),
        "suspend_client_count": len(suspend_clients),
        "actions": actions,
    }
