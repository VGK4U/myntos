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
import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import SecurityManager
from app.models.platform_b2b import (
    PlatformClient, PlatformSubscription, PlatformSubscriptionModule, PlatformAuditLog,
)
from app.models.platform_b2b_billing import (
    PlatformInvoice, PlatformInvoiceLine, PlatformPayment,
)
from app.models.staff import StaffEmployee, StaffRole
from app.models.staff_accounts import AssociatedCompany
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)


def _next_pro_forma_number(db: Session) -> str:
    """PI-YYYYMM-NNNN — sequential per month for Pro Forma quotations, race-safe."""
    today = date.today()
    period = f"{today.year:04d}{today.month:02d}"
    prefix = f"PI-{period}-"
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS platform_invoice_counters (
            period   VARCHAR(8) PRIMARY KEY,
            last_seq INTEGER NOT NULL DEFAULT 0
        )
    """))
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
    """), {"p": f"P{period}", "start_at": int(existing_max) + 1}).scalar()
    return f"{prefix}{int(seq):04d}"


def _next_tax_invoice_number(db: Session) -> str:
    """INV-YYYYMM-NNNN — sequential per month for official GST Tax Invoices, race-safe."""
    today = date.today()
    period = f"{today.year:04d}{today.month:02d}"
    prefix = f"INV-{period}-"
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS platform_invoice_counters (
            period   VARCHAR(8) PRIMARY KEY,
            last_seq INTEGER NOT NULL DEFAULT 0
        )
    """))
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
    """), {"p": f"I{period}", "start_at": int(existing_max) + 1}).scalar()
    return f"{prefix}{int(seq):04d}"


def _next_invoice_number(db: Session) -> str:
    """Default invoice number generator (creates Pro Forma for pre-payment quotations)."""
    return _next_pro_forma_number(db)



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
           AND (psm.enabled = TRUE OR ps.status IN ('pending_payment', 'trial'))
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

    pro_forma_num = _next_pro_forma_number(db)
    inv = PlatformInvoice(
        invoice_number=pro_forma_num,
        client_id=client.id,
        subscription_id=sub.id,
        currency=currency,
        period_start=period_start,
        period_end=period_end,
        due_date=today + timedelta(days=due_in_days),
        subtotal=0, tax=0, total=0, amount_paid=0,
        status="open",
        remarks="PRO FORMA INVOICE / PAYMENT REQUEST",
        so_number=pro_forma_num,
        notes=f"Pro Forma quotation generated for sub#{sub.id} ({cycle})",
    )
    db.add(inv); db.flush()

    subtotal = Decimal("0")
    seats = max(1, int(sub.seat_count or 1))

    for r in rows:
        unit_base = Decimal(str(r["price_inr" if currency == "INR" else "price_usd"]))
        pricing_unit = r.get("pricing_unit") or "per_company"
        qty = Decimal(seats) if pricing_unit == "per_seat" else Decimal("1")
        unit_price = unit_base * annual_factor
        line_total = unit_price * qty

        if cycle == "annual":
            qty_label = f"{annual_multiplier} mos" + (f" × {seats} seats" if pricing_unit == "per_seat" else "")
        else:
            qty_label = f"1 mo" + (f" × {seats} seats" if pricing_unit == "per_seat" else "")

        line = PlatformInvoiceLine(
            invoice_id=inv.id,
            module_id=r["module_id"],
            description=f"{r['module_code']} — {r['module_name']} [{qty_label}]",
            quantity=int(qty),
            unit_price=unit_price,
            line_total=line_total,
            pricing_unit=pricing_unit,
        )
        db.add(line)
        subtotal += line_total

    inv.subtotal = subtotal
    gst_rate = Decimal("18.00") if currency == "INR" else Decimal("0.00")
    inv.tax = ((subtotal * gst_rate) / Decimal("100.00")).quantize(Decimal("0.01"))
    inv.total = subtotal + inv.tax
    inv.balance_due = inv.total
    inv.updated_at = get_indian_time()
    db.commit(); db.refresh(inv)

    return {
        "id": inv.id, "invoice_number": inv.invoice_number,
        "pro_forma_number": inv.invoice_number,
        "invoice_type": "pro_forma",
        "tax_invoice_number": None,
        "document_title": "PRO FORMA INVOICE",
        "client_id": inv.client_id, "subscription_id": inv.subscription_id,
        "currency": inv.currency, "subtotal": float(inv.subtotal),
        "tax": float(inv.tax), "total": float(inv.total),
        "due_date": inv.due_date.isoformat(), "status": inv.status,
        "line_count": len(rows),
    }



def create_razorpay_order_for_invoice(
    db: Session,
    invoice_id: int,
) -> Dict[str, Any]:
    """
    Creates a Razorpay Order strictly using server-side PlatformInvoice.total.
    Frontend is NEVER trusted for payable amount.
    """
    inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
    if not inv:
        raise ValueError("Invoice not found")
    client = db.query(PlatformClient).filter_by(id=inv.client_id).first()
    if not client:
        raise ValueError("Client not found")
    if client.is_internal:
        raise ValueError("Internal tenant does not require payment")

    subtotal = Decimal(str(inv.total or 0))
    paid = Decimal(str(inv.amount_paid or 0))
    balance_due = max(Decimal("0"), subtotal - paid)
    if balance_due <= Decimal("0"):
        raise ValueError("Invoice is already fully paid")

    amount_paise = int(balance_due * 100)
    currency = (inv.currency or "INR").upper()

    order_id = None
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            client_rp = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                "amount": amount_paise,
                "currency": currency,
                "receipt": f"b2b_inv_{inv.id}",
                "notes": {
                    "client_id": str(client.id),
                    "client_code": str(client.client_code),
                    "invoice_id": str(inv.id),
                    "subscription_id": str(inv.subscription_id or ""),
                }
            }
            order = client_rp.order.create(data=order_data)
            order_id = order["id"]
        except Exception as e:
            logger.warning("[RAZORPAY-ORDER] Razorpay API order creation failed: %s", e)
            order_id = f"order_sim_{secrets.token_hex(8)}"
    else:
        order_id = f"order_sim_{secrets.token_hex(8)}"

    inv.razorpay_order_id = order_id
    inv.updated_at = get_indian_time()
    db.commit()
    db.refresh(inv)

    return {
        "ok": True,
        "order_id": order_id,
        "razorpay_order_id": order_id,
        "amount": amount_paise,
        "amount_inr": float(balance_due),
        "currency": currency,
        "key_id": settings.RAZORPAY_KEY_ID or "rzp_test_placeholder",
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "client_code": client.client_code,
        "client_name": client.client_name,
        "customer_email": client.contact_email,
        "customer_phone": client.contact_phone,
    }


def provision_tenant_admin(
    db: Session,
    client: PlatformClient,
) -> Dict[str, Any]:
    """
    Provisions initial Tenant Administrator on successful verified payment.
    Idempotent: If Tenant Admin exists for this tenant, returns existing info.
    """
    # 1. Resolve or create AssociatedCompany for this tenant
    company = db.query(AssociatedCompany).filter_by(client_id=client.id).first()
    if not company:
        company = AssociatedCompany(
            company_name=client.client_name,
            client_id=client.id,
            company_code=client.client_code[:20],
            is_active=True,
            created_at=get_indian_time(),
        )
        db.add(company)
        db.flush()

    # 2. Check if a Tenant Admin already exists for this tenant / company
    existing_admin = db.query(StaffEmployee).filter(
        StaffEmployee.base_company_id == company.id,
        StaffEmployee.status == "active",
    ).first()

    if existing_admin:
        return {
            "status": "already_exists",
            "employee_id": existing_admin.id,
            "emp_code": existing_admin.emp_code,
            "email": existing_admin.email,
        }

    # Also check by email to prevent duplicate employee identity across same tenant
    if client.contact_email:
        email_match = db.query(StaffEmployee).filter_by(email=client.contact_email).first()
        if email_match:
            if not email_match.base_company_id:
                email_match.base_company_id = company.id
            if company.id not in (email_match.data_companies or []):
                comps = list(email_match.data_companies or [])
                comps.append(company.id)
                email_match.data_companies = comps
            db.flush()
            return {
                "status": "already_exists",
                "employee_id": email_match.id,
                "emp_code": email_match.emp_code,
                "email": email_match.email,
            }

    # 3. Resolve role for Tenant Administrator
    role = db.query(StaffRole).filter_by(role_code="tenant_admin").first()
    if not role:
        role = db.query(StaffRole).filter_by(hierarchy_level=85).first()
    if not role:
        role = StaffRole(
            role_code="tenant_admin",
            role_name="Tenant Administrator",
            hierarchy_level=85,
            description="Tenant Administrator with authority over client users, CRM, and billing.",
            is_active=True,
        )
        db.add(role)
        db.flush()

    # 4. Generate unique emp_code
    base_code = f"ADM{client.id:04d}"
    emp_code = base_code
    clash_idx = 1
    while db.query(StaffEmployee).filter_by(emp_code=emp_code).first():
        emp_code = f"{base_code}_{clash_idx}"
        clash_idx += 1

    # 5. Generate secure temporary password
    temp_password = secrets.token_urlsafe(12)
    pwd_hash = SecurityManager.get_password_hash(temp_password)

    new_emp = StaffEmployee(
        emp_code=emp_code,
        staff_type="MN_EMPLOYEE",
        full_name=client.contact_name or f"{client.client_name} Admin",
        email=client.contact_email,
        phone=client.contact_phone,
        designation="Tenant Administrator",
        role_id=role.id,
        status="active",
        date_of_joining=date.today(),
        password_hash=pwd_hash,
        requires_password_change=True,
        base_company_id=company.id,
        data_companies=[company.id],
    )
    db.add(new_emp)
    db.flush()

    try:
        db.add(PlatformAuditLog(
            actor_staff_id=None,
            client_id=client.id,
            entity="STAFF-EMP",
            action="CREATE",
            entity_id=new_emp.id,
            after_json={"emp_code": emp_code, "email": client.contact_email, "role": role.role_code},
            created_at=get_indian_time(),
        ))
    except Exception:
        pass

    return {
        "status": "provisioned",
        "employee_id": new_emp.id,
        "emp_code": emp_code,
        "email": client.contact_email,
        "temp_password": temp_password,
    }


def process_verified_payment(
    db: Session,
    *,
    invoice_id: int,
    client_id: int,
    amount: Decimal,
    currency: str = "INR",
    gateway_payment_id: str,
    method: str = "razorpay",
    notes: Optional[str] = None,
    recorded_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Core atomic payment processing engine.
    Guarantees dual-layer idempotency and triggers Subscription Start Event.
    """
    # ── 1. DUAL-LAYER IDEMPOTENCY CHECK ──────────────────────────────────────
    if gateway_payment_id:
        existing_pay = db.query(PlatformPayment).filter_by(
            gateway_payment_id=gateway_payment_id
        ).first()
        if existing_pay:
            return {
                "ok": True,
                "status": "already_processed",
                "payment_id": existing_pay.id,
                "invoice_id": existing_pay.invoice_id,
                "client_id": existing_pay.client_id,
                "amount": float(existing_pay.amount),
                "message": "Payment was already captured and processed",
            }

    # ── 2. OWNERSHIP & TENANT VALIDATION ────────────────────────────────────
    inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
    if not inv:
        raise ValueError("Invoice not found")

    client = db.query(PlatformClient).filter_by(id=client_id).first()
    if not client:
        raise ValueError("Client not found")

    if inv.client_id != client.id:
        raise ValueError("Tenant ownership mismatch between invoice and client")

    sub: Optional[PlatformSubscription] = None
    if inv.subscription_id:
        sub = db.query(PlatformSubscription).filter_by(id=inv.subscription_id).first()
        if sub and sub.client_id != client.id:
            raise ValueError("Subscription does not belong to specified tenant")

    # ── 3. AMOUNT & CURRENCY VALIDATION ─────────────────────────────────────
    if (inv.currency or "INR").upper() != currency.upper():
        raise ValueError(f"Currency mismatch: expected {inv.currency}, got {currency}")

    if amount <= Decimal("0"):
        raise ValueError("Payment amount must be positive")

    # ── 4. ATOMIC DATABASE MUTATION ─────────────────────────────────────────
    # ── 4. ATOMIC DATABASE MUTATION ─────────────────────────────────────────
    p = PlatformPayment(
        client_id=client.id,
        invoice_id=inv.id,
        amount=amount,
        currency=currency.upper(),
        method=method,
        reference=gateway_payment_id,
        gateway_payment_id=gateway_payment_id,
        received_on=date.today(),
        notes=notes or f"Automated capture via {method} ({gateway_payment_id})",
        recorded_by=recorded_by,
    )
    db.add(p)
    db.flush()

    # Update Invoice Status and Issue Official GST Tax Invoice
    current_paid = Decimal(str(inv.amount_paid or 0)) + amount
    inv.amount_paid = current_paid
    inv.balance_due = max(Decimal("0"), Decimal(str(inv.total or 0)) - current_paid)

    tax_invoice_num = None
    if inv.amount_paid >= Decimal(str(inv.total or 0)):
        inv.status = "paid"
        # Issue official GST Tax Invoice if not already assigned
        if not (inv.invoice_number and inv.invoice_number.startswith("INV-")):
            tax_invoice_num = _next_tax_invoice_number(db)
            # Preserve original Pro Forma reference in so_number
            if not inv.so_number:
                inv.so_number = inv.invoice_number
            inv.invoice_number = tax_invoice_num
            inv.invoice_date = date.today()
            inv.remarks = "GST TAX INVOICE"
        else:
            tax_invoice_num = inv.invoice_number
    elif inv.amount_paid > Decimal("0"):
        inv.status = "partial"

    inv.updated_at = get_indian_time()

    # ── 5. SUBSCRIPTION START EVENT (PAYMENT SUCCESS) ────────────────────────
    admin_info = None
    if inv.status == "paid":
        today = date.today()
        if sub is not None:
            sub.status = "active"
            sub.is_trial = False
            sub.starts_on = today
            # Calculate end date
            period_start, period_end, cycle = _period_for_subscription(sub)
            sub.ends_on = period_end
            sub.updated_at = get_indian_time()
            # Enable all subscription modules for this active subscription
            db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub.id).update({"enabled": True})

        client.status = "active"
        client.updated_at = get_indian_time()

        # ── 6. TENANT ADMIN PROVISIONING ─────────────────────────────────────
        admin_info = provision_tenant_admin(db, client)

    db.commit()
    db.refresh(p)

    try:
        db.add(PlatformAuditLog(
            actor_staff_id=recorded_by,
            client_id=client.id,
            entity="B2B-PAY",
            action="CREATE",
            entity_id=p.id,
            after_json={
                "gateway_payment_id": gateway_payment_id,
                "amount": float(amount),
                "invoice_id": inv.id,
                "tax_invoice_number": tax_invoice_num,
                "pro_forma_number": getattr(inv, "so_number", None),
                "invoice_status": inv.status,
                "subscription_status": sub.status if sub else None,
                "admin_provisioned": admin_info.get("status") if admin_info else None,
            },
            created_at=get_indian_time(),
        ))
        db.commit()
    except Exception:
        pass

    return {
        "ok": True,
        "payment_id": p.id,
        "gateway_payment_id": gateway_payment_id,
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "invoice_type": getattr(inv, "invoice_type", "tax_invoice"),
        "tax_invoice_number": getattr(inv, "tax_invoice_number", tax_invoice_num),
        "pro_forma_number": getattr(inv, "so_number", inv.invoice_number),
        "document_title": "GST TAX INVOICE",
        "invoice_status": inv.status,
        "amount_paid": float(inv.amount_paid),
        "balance_due": float(inv.balance_due or 0),
        "subscription_status": sub.status if sub else None,
        "subscription_start": sub.starts_on.isoformat() if sub and sub.starts_on else None,
        "tenant_status": client.status,
        "admin_provisioning": admin_info,
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
    gateway_payment_id: Optional[str] = None,
    received_on: Optional[date] = None,
    notes: Optional[str] = None,
    recorded_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Record a payment. Updates invoice status and activates subscription if fully paid."""
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

    if invoice_id is not None:
        return process_verified_payment(
            db,
            invoice_id=invoice_id,
            client_id=client_id,
            amount=Decimal(str(amount)),
            currency=currency,
            gateway_payment_id=gateway_payment_id or reference or f"MANUAL_{secrets.token_hex(6)}",
            method=method or "manual",
            notes=notes,
            recorded_by=recorded_by,
        )

    p = PlatformPayment(
        client_id=client_id, invoice_id=None,
        amount=Decimal(str(amount)), currency=currency,
        method=method, reference=reference,
        gateway_payment_id=gateway_payment_id,
        received_on=received_on or date.today(),
        notes=notes, recorded_by=recorded_by,
    )
    db.add(p); db.commit(); db.refresh(p)
    return {
        "id": p.id, "invoice_id": None, "client_id": p.client_id,
        "amount": float(p.amount), "currency": p.currency, "method": p.method,
        "received_on": p.received_on.isoformat(),
        "invoice_status": None,
        "invoice_amount_paid": None,
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
