"""
MYNTOS BILLING LIFECYCLE TEST SUITE — PRO FORMA VS GST TAX INVOICE
Verifies the authoritative commercial lifecycle:
SIGNUP -> ZYNOVA APPROVAL -> PRO FORMA INVOICE -> PAYMENT -> VERIFIED PAYMENT -> GST TAX INVOICE -> ACTIVATION

Scenarios:
1. Signup submitted: NO GST Tax Invoice exists.
2. Signup approved: PRO FORMA INVOICE exists; GST TAX INVOICE MUST NOT exist.
3. Razorpay order created: PRO FORMA remains; GST TAX INVOICE MUST NOT exist.
4. Unverified payment / payment pending: PRO FORMA remains; GST TAX INVOICE MUST NOT exist; Subscription NOT active.
5. Payment verified: GST TAX INVOICE created; Subscription ACTIVE; Modules enabled; Tenant ACTIVE; Tenant Admin provisioned.
6. Duplicate payment webhook / idempotent call: ONE payment, ONE GST tax invoice, ONE activation, ONE Tenant Admin.
7. Payment verification failure: NO GST Tax Invoice, NO Subscription Activation.
8. Retry safety: Zero duplicate GST tax invoices.
"""

import secrets
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffRole, StaffNdaVersion, StaffNdaAcceptance
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import (
    PlatformClient, PlatformSubscription, PlatformSubscriptionModule, PlatformModule
)
from app.models.platform_b2b_billing import PlatformInvoice, PlatformPayment
from app.services.platform_b2b_billing import (
    process_verified_payment, create_razorpay_order_for_invoice
)

client = TestClient(app, base_url="http://testserver")


def _get_super_admin_token() -> str:
    db = SessionLocal()
    try:
        role = db.query(StaffRole).filter(StaffRole.role_code.ilike("super_admin")).first()
        if not role:
            role = StaffRole(role_code="super_admin", role_name="Super Admin", hierarchy_level=100, is_active=True)
            db.add(role); db.commit()

        sa = db.query(StaffEmployee).filter(StaffEmployee.role_id == role.id).first()
        if not sa:
            sa = StaffEmployee(
                emp_code=f"SA_{secrets.token_hex(3).upper()}",
                full_name="Platform Billing Admin",
                email=f"billing_admin_{secrets.token_hex(3)}@platform.io",
                role_id=role.id,
                status="active",
                date_of_joining=date.today(),
                password_hash=SecurityManager.get_password_hash("SuperPass123!"),
                base_company_id=1,
                data_companies=[1],
            )
            db.add(sa); db.commit(); db.refresh(sa)

        for nda in db.query(StaffNdaVersion).filter_by(status='active').all():
            if not db.query(StaffNdaAcceptance).filter_by(employee_id=sa.id, nda_version_id=nda.id).first():
                db.add(StaffNdaAcceptance(
                    employee_id=sa.id,
                    nda_version_id=nda.id,
                    acceptance_ip="127.0.0.1",
                    document_type=nda.document_type or 'NDA'
                ))
        db.commit()

        return SecurityManager.create_access_token(data={
            "sub": str(sa.id), "emp_code": sa.emp_code,
            "employee_id": sa.emp_code, "user_type": "staff",
            "role": "super_admin", "is_super_admin": True
        })
    finally:
        db.close()


def test_billing_pro_forma_vs_gst_tax_invoice():
    print("\n================================================================================")
    print("🚀 [START] MYNTOS PRO FORMA VS GST TAX INVOICE BILLING LIFECYCLE TEST SUITE")
    print("================================================================================")

    sa_token = _get_super_admin_token()
    headers_sa = {"Authorization": f"Bearer {sa_token}"}
    hex_id = secrets.token_hex(3).upper()

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 1: Signup Submitted -> NO GST TAX INVOICE
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 1] Signup Submitted Verification ---")
    s_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Acme Solar {hex_id}",
        "contact_name": "John Solar",
        "contact_email": f"john_{hex_id.lower()}@acmesolar.io",
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "selected_modules": ["CRM_CORE", "CRM_LEADS_SOLAR", "WHATSAPP_INTEGRATION"],
        "seat_count": 5
    })
    assert s_res.status_code == 201, f"Signup failed: {s_res.text}"
    s_json = s_res.json()
    cid = s_json["client_id"]
    client_code = s_json["client_code"]

    db = SessionLocal()
    try:
        invoices = db.query(PlatformInvoice).filter_by(client_id=cid).all()
        assert len(invoices) == 0, "No invoice of any kind should exist immediately after signup submission"
    finally:
        db.close()
    print(f"✅ [PASSED] Scenario 1: Signup created for Client #{cid}. Zero invoices exist.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 2: Signup Approved -> PRO FORMA EXISTS, GST TAX INVOICE MUST NOT EXIST
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 2] Approval -> Pro Forma Issued (GST Tax Invoice MUST NOT exist) ---")
    appr_res = client.post(f"/api/v1/platform-b2b/signups/{cid}/approve", headers=headers_sa)
    assert appr_res.status_code == 200, f"Approval failed: {appr_res.text}"
    appr_data = appr_res.json()

    assert appr_data["ok"] is True
    assert appr_data["status"] == "approved"
    assert appr_data["document_title"] == "PRO FORMA INVOICE"
    assert appr_data["invoice_type"] == "pro_forma"
    assert appr_data["invoice_number"].startswith("PI-")
    assert appr_data["tax_invoice_number"] is None

    db = SessionLocal()
    try:
        inv = db.query(PlatformInvoice).filter_by(client_id=cid).first()
        assert inv is not None
        assert inv.status in ("open", "pro_forma")
        assert inv.invoice_type == "pro_forma"
        assert inv.tax_invoice_number is None, "GST Tax Invoice number MUST NOT exist before payment!"
        assert inv.invoice_number.startswith("PI-")
        assert "PRO FORMA" in inv.remarks
        assert float(inv.tax) > 0, "Pro Forma shows estimated GST calculation for transparent pricing"
        assert float(inv.total) > 0
        inv_id = inv.id
        pro_forma_num = inv.invoice_number
    finally:
        db.close()
    print(f"✅ [PASSED] Scenario 2: Pro Forma '{pro_forma_num}' issued. GST Tax Invoice does NOT exist.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 3: Razorpay Order Created -> Pro Forma Remains, GST TAX INVOICE MUST NOT EXIST
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 3] Razorpay Order Creation ---")
    rzp_res = client.post(f"/api/v1/platform-b2b/invoices/{inv_id}/checkout")
    assert rzp_res.status_code == 200, f"Checkout failed: {rzp_res.text}"
    rzp_data = rzp_res.json()
    assert "razorpay_order_id" in rzp_data

    db = SessionLocal()
    try:
        inv_rzp = db.query(PlatformInvoice).filter_by(id=inv_id).first()
        assert inv_rzp.status in ("open", "pro_forma")
        assert inv_rzp.invoice_type == "pro_forma"
        assert inv_rzp.tax_invoice_number is None, "GST Tax Invoice must not be generated when order is created"
    finally:
        db.close()

    print(f"✅ [PASSED] Scenario 3: Razorpay order created. Document remains Pro Forma.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 4: Unverified State / Payment Pending -> Subscription NOT Active
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 4] Payment Pending Status Gating ---")
    status_res = client.get(f"/api/v1/platform-b2b/application-status/{client_code}")
    assert status_res.status_code == 200, f"Status fetch failed: {status_res.text}"
    stat_data = status_res.json()
    assert stat_data["status"] == "approved"
    assert stat_data["invoice"]["is_pro_forma"] is True
    assert stat_data["invoice"]["document_title"] == "PRO FORMA INVOICE"
    assert stat_data["invoice"]["tax_invoice_number"] is None


    db = SessionLocal()
    try:
        sub = db.query(PlatformSubscription).filter_by(client_id=cid).first()
        assert sub.status == "pending_payment"
        mods = db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub.id).all()
        for m in mods:
            assert m.enabled is False, "Subscription modules MUST NOT be enabled before payment!"
    finally:
        db.close()
    print(f"✅ [PASSED] Scenario 4: Pre-payment state verified. Subscription is pending_payment, modules disabled.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 7: Payment Verification Failure -> No Tax Invoice, No Activation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 7] Payment Verification Failure Handling ---")
    db = SessionLocal()
    try:
        # Currency mismatch should fail with ValueError
        failed_as_expected = False
        try:
            process_verified_payment(
                db,
                invoice_id=inv_id,
                client_id=cid,
                amount=Decimal("1000.00"),
                currency="USD",  # Wrong currency!
                gateway_payment_id=f"pay_bad_{secrets.token_hex(4)}"
            )
        except ValueError:
            failed_as_expected = True
        assert failed_as_expected is True, "Currency mismatch must raise ValueError"

        sub_fail = db.query(PlatformSubscription).filter_by(client_id=cid).first()
        assert sub_fail.status == "pending_payment", "Subscription must not activate on payment failure"
        inv_fail = db.query(PlatformInvoice).filter_by(id=inv_id).first()
        assert inv_fail.tax_invoice_number is None, "No GST Tax Invoice issued on failed settlement"
    finally:
        db.close()
    print(f"✅ [PASSED] Scenario 7: Failed verification handled safely; zero premature tax invoices.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 5: Successful Verified Payment -> GST TAX INVOICE ISSUED & ACTIVATED
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 5] Verified Payment -> Official GST Tax Invoice Issuance & Activation ---")
    gateway_id = f"pay_live_{secrets.token_hex(6)}"
    db = SessionLocal()
    try:
        inv = db.query(PlatformInvoice).filter_by(id=inv_id).first()
        total_to_pay = inv.total

        pay_result = process_verified_payment(
            db,
            invoice_id=inv.id,
            client_id=cid,
            amount=total_to_pay,
            currency="INR",
            gateway_payment_id=gateway_id
        )
        assert pay_result["ok"] is True
        assert pay_result["invoice_status"] == "paid"
        assert pay_result["invoice_type"] == "tax_invoice"
        assert pay_result["document_title"] == "GST TAX INVOICE"
        assert pay_result["tax_invoice_number"] is not None
        assert pay_result["tax_invoice_number"].startswith("INV-")
        assert pay_result["pro_forma_number"] == pro_forma_num
        assert pay_result["subscription_status"] == "active"
        tax_inv_num = pay_result["tax_invoice_number"]

        # Check DB State
        inv_paid = db.query(PlatformInvoice).filter_by(id=inv_id).first()
        assert inv_paid.status == "paid"
        assert inv_paid.invoice_type == "tax_invoice"
        assert inv_paid.tax_invoice_number == tax_inv_num
        assert inv_paid.invoice_number == tax_inv_num
        assert inv_paid.so_number == pro_forma_num, "Original Pro Forma number preserved in reference link"
        assert inv_paid.remarks == "GST TAX INVOICE"

        sub_active = db.query(PlatformSubscription).filter_by(client_id=cid).first()
        assert sub_active.status == "active"
        active_mods = db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub_active.id).all()
        for m in active_mods:
            assert m.enabled is True, "All subscription modules must be enabled upon GST Tax Invoice issuance"

        client_active = db.query(PlatformClient).filter_by(id=cid).first()
        assert client_active.status == "active"

        # Tenant Admin provisioned
        company = db.query(AssociatedCompany).filter_by(client_id=cid).first()
        assert company is not None
        root_admin = db.query(StaffEmployee).filter_by(base_company_id=company.id).first()
        assert root_admin is not None
        assert root_admin.role.role_code == "tenant_admin"
    finally:
        db.close()
    print(f"✅ [PASSED] Scenario 5: Verified payment successfully issued GST Tax Invoice '{tax_inv_num}'. Subscription & Tenant ACTIVE.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 6 & 8: Duplicate Payment Webhook & Retry Idempotency
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [SCENARIO 6 & 8] Dual-Layer Idempotency & Webhook Retry Safety ---")
    db = SessionLocal()
    try:
        repeat_pay = process_verified_payment(
            db,
            invoice_id=inv_id,
            client_id=cid,
            amount=total_to_pay,
            currency="INR",
            gateway_payment_id=gateway_id  # Repeated webhook ID
        )
        assert repeat_pay["ok"] is True
        assert repeat_pay["status"] == "already_processed"

        # Ensure NO duplicate tax invoices or duplicate payments
        payments_count = db.query(PlatformPayment).filter_by(client_id=cid).count()
        assert payments_count == 1, "Exactly ONE payment record must exist"

        invoices_count = db.query(PlatformInvoice).filter_by(client_id=cid).count()
        assert invoices_count == 1, "Exactly ONE invoice record must exist"

        companies_count = db.query(AssociatedCompany).filter_by(client_id=cid).count()
        assert companies_count == 1, "Exactly ONE tenant legal entity must exist"
    finally:
        db.close()
    print(f"✅ [PASSED] Scenario 6 & 8: Duplicate webhook handled idempotently with zero duplicate invoices or payments.")

    print("\n================================================================================")
    print("🎉 ALL 8 SCENARIOS IN PRO FORMA VS GST TAX INVOICE SUITE PASSED (100% GREEN)!")
    print("================================================================================")


if __name__ == "__main__":
    test_billing_pro_forma_vs_gst_tax_invoice()
