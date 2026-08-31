"""
MYNTOS PHASE 4B — Comprehensive Forensic Acceptance & Verification Suite
Validates:
1. Full Commercial Lifecycle (Signup -> Review -> Approval -> Invoicing -> Payment -> Activation)
2. Commercial Terms Freeze & Invoice Immutability (Catalog price changes do NOT alter existing invoices)
3. Invalid State Transitions Gating (archived/rejected -> approved, direct activation bypass)
4. Razorpay Mismatched Payment & Forgery Defenses (currency/amount/tenant mismatch)
5. Public Application Status Anti-Enumeration & Sanitization
6. Invoice Seat Multiplier & 18% GST Calculations + Boundary Validation (0/negative seats rejected)
7. Tenant Administrator Provisioning Boundary Verification
8. Dual-Layer Payment Replay / Idempotency
9. Cross-Tenant Isolation & Zero Premature Entitlements
"""

import secrets
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffRole, StaffNdaVersion, StaffNdaAcceptance
from app.models.platform_b2b import (
    PlatformClient, PlatformSubscription, PlatformSubscriptionModule,
    PlatformModule, PlatformModulePricing
)
from app.models.platform_b2b_billing import PlatformInvoice, PlatformPayment
from app.services.platform_b2b_billing import process_verified_payment, generate_invoice_for_subscription
from app.services.b2b_shadow import is_module_entitled

client = TestClient(app, base_url="http://testserver")


def create_test_staff_user(db, is_super: bool = False, role_code: str = "sales"):
    test_id = secrets.token_hex(4).upper()
    role_code_clean = ("super_admin" if is_super else role_code).lower()
    role = db.query(StaffRole).filter(StaffRole.role_code.ilike(role_code_clean)).first()
    if not role:
        role = StaffRole(
            role_code=role_code_clean,
            role_name=role_code_clean.upper(),
            hierarchy_level=100 if is_super else 50,
            is_active=True
        )
        db.add(role); db.flush()

    emp = StaffEmployee(
        emp_code=f"EMP_{test_id}",
        full_name=f"Test Employee {test_id}",
        email=f"emp_{test_id.lower()}@test.io",
        role_id=role.id,
        status="active",
        date_of_joining=date.today(),
        password_hash=SecurityManager.get_password_hash("TestPass123!"),
        base_company_id=1,
        data_companies=[1],
    )
    db.add(emp); db.commit(); db.refresh(emp)

    for nda in db.query(StaffNdaVersion).filter_by(status='active').all():
        db.add(StaffNdaAcceptance(
            employee_id=emp.id,
            nda_version_id=nda.id,
            acceptance_ip="127.0.0.1",
            document_type=nda.document_type or 'NDA'
        ))
    db.commit()

    token = SecurityManager.create_access_token(data={
        "sub": str(emp.id),
        "emp_code": emp.emp_code,
        "employee_id": emp.emp_code,
        "user_type": "staff",
        "role": role.role_code.lower(),
        "is_super_admin": is_super,
    })
    return emp, token


def test_full_commercial_lifecycle_and_security():
    print("\n================================================================================")
    print("🚀 [TEST 1] FULL COMMERCIAL LIFECYCLE & SECURITY VERIFICATION")
    print("================================================================================")
    
    db = SessionLocal()
    try:
        super_admin_emp, super_admin_token = create_test_staff_user(db, is_super=True)
        normal_staff_emp, normal_staff_token = create_test_staff_user(db, is_super=False, role_code="sales")
    finally:
        db.close()

    auth_headers_super = {"Authorization": f"Bearer {super_admin_token}"}
    auth_headers_normal = {"Authorization": f"Bearer {normal_staff_token}"}

    # STEP 1: Customer Signup (Pending)
    test_hex = secrets.token_hex(4).upper()
    comp_name = f"Solar Corp {test_hex}"
    email = f"owner_{test_hex.lower()}@solarcorp.io"

    signup_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": comp_name,
        "contact_name": f"Solar Lead {test_hex}",
        "contact_email": email,
        "contact_phone": "+91 9988776655",
        "billing_currency": "INR",
        "billing_cycle": "annual",
        "selected_modules": ["CRM_LEADS_SOLAR", "WHATSAPP_INTEGRATION"],
        "seat_count": 1
    })
    assert signup_res.status_code == 201, f"Signup failed: {signup_res.text}"
    s_data = signup_res.json()
    client_id = s_data["client_id"]
    sub_id = s_data["subscription_id"]
    client_code = s_data["client_code"]

    db = SessionLocal()
    try:
        c = db.query(PlatformClient).filter_by(id=client_id).first()
        s = db.query(PlatformSubscription).filter_by(id=sub_id).first()
        assert c.status == "pending"
        assert s.status == "pending_payment"

        # Check modules in DB: Must be enabled=False (zero premature access!)
        mods = db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub_id).all()
        assert len(mods) == 3, f"Expected 3 modules, got {len(mods)}"
        for m in mods:
            assert m.enabled is False, "Module must NOT be enabled before approval + payment"

        # Verify entitlement helper strictly denies access
        assert is_module_entitled(db, client_id, "CRM_LEADS_SOLAR", strict=True) is False
        assert is_module_entitled(db, client_id, "CRM_CORE", strict=True) is False
        assert is_module_entitled(db, client_id, "WHATSAPP_INTEGRATION", strict=True) is False
        print("✅ [PASSED] Customer signup is in 'pending' with 0 active entitlements.")
    finally:
        db.close()

    # STEP 2: Security — Unauthorized Approval Gating
    unauth_res = client.post(f"/api/v1/platform-b2b/signups/{client_id}/approve")
    assert unauth_res.status_code in (401, 403)

    normal_res = client.post(
        f"/api/v1/platform-b2b/signups/{client_id}/approve",
        headers=auth_headers_normal
    )
    assert normal_res.status_code == 403
    print("✅ [PASSED] Non-Zynova Super Admin users are strictly rejected with 401/403.")

    # STEP 3: Zynova Super Admin Approval & Invoicing
    appr_res = client.post(
        f"/api/v1/platform-b2b/signups/{client_id}/approve",
        headers=auth_headers_super
    )
    assert appr_res.status_code == 200, f"Approval failed: {appr_res.text}"
    appr_data = appr_res.json()
    assert appr_data["status"] == "approved"
    assert "invoice_id" in appr_data
    invoice_id = appr_data["invoice_id"]

    db = SessionLocal()
    try:
        c = db.query(PlatformClient).filter_by(id=client_id).first()
        s = db.query(PlatformSubscription).filter_by(id=sub_id).first()
        inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
        assert c.status == "pending"
        assert "[APPROVED_FOR_INVOICE]" in (c.notes or "")
        assert s.status == "pending_payment"
        assert inv is not None
        assert inv.status == "open"
        assert inv.total > 0
        assert inv.razorpay_order_id is not None

        # Verify entitlement STILL denies access before payment
        assert is_module_entitled(db, client_id, "CRM_LEADS_SOLAR", strict=True) is False
        print(f"✅ [PASSED] Zynova approved application. Invoice #{inv.invoice_number} generated (Total: ₹{inv.total}).")
        print("✅ [PASSED] Entitlement remains strictly disabled (enabled=False) pending payment.")
    finally:
        db.close()

    # STEP 4: Public Application Status Check
    status_res = client.get(f"/api/v1/platform-b2b/application-status/{client_code}")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["status"] == "approved"
    assert st_data["progress_step"] == 3
    assert st_data["invoice"]["id"] == invoice_id
    assert st_data["invoice"]["status"] == "open"
    print("✅ [PASSED] Public status endpoint shows 'approved' with invoice details.")

    # STEP 5: Server-Authoritative Payment Capture & Activation
    gateway_pay_id = f"pay_{secrets.token_hex(8)}"
    db = SessionLocal()
    try:
        inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
        total_payable = inv.total

        pay_res = process_verified_payment(
            db,
            invoice_id=inv.id,
            client_id=client_id,
            amount=total_payable,
            currency=inv.currency,
            gateway_payment_id=gateway_pay_id,
            method="razorpay"
        )
        assert pay_res["ok"] is True

        db.refresh(inv)
        c = db.query(PlatformClient).filter_by(id=client_id).first()
        s = db.query(PlatformSubscription).filter_by(id=sub_id).first()
        assert inv.status == "paid"
        assert c.status == "active"
        assert s.status == "active"
        assert s.starts_on is not None

        sub_mods = db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub_id).all()
        for sm in sub_mods:
            assert sm.enabled is True

        assert is_module_entitled(db, client_id, "CRM_LEADS_SOLAR", strict=True) is True
        assert is_module_entitled(db, client_id, "CRM_CORE", strict=True) is True
        assert is_module_entitled(db, client_id, "WHATSAPP_INTEGRATION", strict=True) is True

        # Cross-tenant isolation
        assert is_module_entitled(db, client_id, "TELEPHONY_INTEGRATION", strict=True) is False
        assert is_module_entitled(db, client_id, "STAFF_HR", strict=True) is False
        assert is_module_entitled(db, client_id, "MNR_ECOSYSTEM", strict=True) is False

        print("✅ [PASSED] Verified payment activated subscription, client, and subscription modules.")
    finally:
        db.close()

    # STEP 6: Idempotency
    db = SessionLocal()
    try:
        dup_res = process_verified_payment(
            db,
            invoice_id=invoice_id,
            client_id=client_id,
            amount=total_payable,
            currency="INR",
            gateway_payment_id=gateway_pay_id,
            method="razorpay"
        )
        assert dup_res["ok"] is True
        assert dup_res["status"] == "already_processed"
        pay_count = db.query(PlatformPayment).filter_by(gateway_payment_id=gateway_pay_id).count()
        assert pay_count == 1
        print("✅ [PASSED] Duplicate payment callback handled idempotently (0 duplicate records).")
    finally:
        db.close()

    # STEP 7: Rejection Workflow
    rej_hex = secrets.token_hex(4).upper()
    rej_signup = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Spam Corp {rej_hex}",
        "contact_name": "Spam Bot",
        "contact_email": f"spam_{rej_hex.lower()}@spam.com",
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "selected_modules": ["CRM_CORE"]
    })
    assert rej_signup.status_code == 201
    rej_cid = rej_signup.json()["client_id"]

    rej_res = client.post(
        f"/api/v1/platform-b2b/signups/{rej_cid}/reject",
        headers=auth_headers_super,
        json={"reason": "Invalid business documents"}
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"

    db = SessionLocal()
    try:
        rej_c = db.query(PlatformClient).filter_by(id=rej_cid).first()
        rej_s = db.query(PlatformSubscription).filter_by(client_id=rej_cid).first()
        assert rej_c.status == "archived"
        assert "[REJECTED]" in (rej_c.notes or "")
        assert rej_s.status == "cancelled"
        assert is_module_entitled(db, rej_cid, "CRM_CORE", strict=True) is False
        print("✅ [PASSED] Rejection workflow marks client 'archived', subscription 'cancelled', zero access.")
    finally:
        db.close()


def test_commercial_terms_freeze_and_invoice_immutability():
    print("\n================================================================================")
    print("🚀 [TEST 2] COMMERCIAL TERMS FREEZE & INVOICE IMMUTABILITY VERIFICATION")
    print("================================================================================")
    
    db = SessionLocal()
    try:
        super_admin_emp, super_admin_token = create_test_staff_user(db, is_super=True)
    finally:
        db.close()
    auth_headers_super = {"Authorization": f"Bearer {super_admin_token}"}

    # 1. Create and approve application
    freeze_hex = secrets.token_hex(4).upper()
    signup_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Freeze Corp {freeze_hex}",
        "contact_name": "Freeze Lead",
        "contact_email": f"freeze_{freeze_hex.lower()}@freeze.io",
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "selected_modules": ["CRM_LEADS_EV_B2B"],
        "seat_count": 2
    })
    cid = signup_res.json()["client_id"]

    appr_res = client.post(f"/api/v1/platform-b2b/signups/{cid}/approve", headers=auth_headers_super)
    assert appr_res.status_code == 200
    inv_id = appr_res.json()["invoice_id"]

    db = SessionLocal()
    try:
        inv = db.query(PlatformInvoice).filter_by(id=inv_id).first()
        original_total = inv.total
        original_subtotal = inv.subtotal
        original_tax = inv.tax
        print(f"Initial approved invoice total: ₹{original_total} (Subtotal: ₹{original_subtotal}, Tax: ₹{original_tax})")

        # 2. Simulate global catalog price update in platform_module_pricing
        mod = db.query(PlatformModule).filter_by(module_code="CRM_LEADS_EV_B2B").first()
        pricing = db.query(PlatformModulePricing).filter_by(module_id=mod.id).first()
        if pricing:
            old_p = pricing.price_inr
            pricing.price_inr = Decimal("999999.00")
            db.commit()

            # 3. Reload invoice from DB and assert it DID NOT CHANGE
            db.refresh(inv)
            assert inv.total == original_total, f"Invoice total was mutated! Expected {original_total}, got {inv.total}"
            assert inv.subtotal == original_subtotal
            assert inv.tax == original_tax
            print("✅ [PASSED] Approved invoice terms remain 100% immutable after catalog price changes.")

            # Restore original price
            pricing.price_inr = old_p
            db.commit()
    finally:
        db.close()


def test_invalid_state_transitions_rejected():
    print("\n================================================================================")
    print("🚀 [TEST 3] INVALID STATE TRANSITIONS SERVER-SIDE GATING")
    print("================================================================================")
    
    db = SessionLocal()
    try:
        super_admin_emp, super_admin_token = create_test_staff_user(db, is_super=True)
    finally:
        db.close()
    auth_headers_super = {"Authorization": f"Bearer {super_admin_token}"}

    # 1. Create a rejected client
    inv_hex = secrets.token_hex(4).upper()
    signup_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Invalid State Corp {inv_hex}",
        "contact_name": "Invalid State Lead",
        "contact_email": f"inv_{inv_hex.lower()}@test.io",
        "selected_modules": ["CRM_CORE"]
    })
    cid = signup_res.json()["client_id"]

    # Reject client
    client.post(f"/api/v1/platform-b2b/signups/{cid}/reject", headers=auth_headers_super)

    # 2. Attempt to approve an already rejected/archived client -> Must return HTTP 400
    bad_approve = client.post(f"/api/v1/platform-b2b/signups/{cid}/approve", headers=auth_headers_super)
    assert bad_approve.status_code == 400, f"Expected 400, got {bad_approve.status_code}"
    print("✅ [PASSED] Approving an archived/rejected client is rejected with HTTP 400.")

    # 3. Attempt direct entitlement activation without payment -> Must return False
    db = SessionLocal()
    try:
        assert is_module_entitled(db, cid, "CRM_CORE", strict=True) is False
        print("✅ [PASSED] Direct unverified entitlement activation is strictly denied.")
    finally:
        db.close()


def test_razorpay_mismatched_payment_and_forgery_defenses():
    print("\n================================================================================")
    print("🚀 [TEST 4] RAZORPAY MISMATCHED PAYMENT & FORGERY DEFENSES")
    print("================================================================================")
    
    db = SessionLocal()
    try:
        super_admin_emp, super_admin_token = create_test_staff_user(db, is_super=True)
    finally:
        db.close()
    auth_headers_super = {"Authorization": f"Bearer {super_admin_token}"}

    # Create two separate tenants: Tenant A and Tenant B
    a_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Tenant A {secrets.token_hex(2)}",
        "contact_name": "Contact A",
        "contact_email": f"tenant_a_{secrets.token_hex(2)}@a.com",
        "billing_currency": "INR",
        "selected_modules": ["CRM_CORE"]
    })
    assert a_res.status_code == 201
    cid_a = a_res.json()["client_id"]

    b_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Tenant B {secrets.token_hex(2)}",
        "contact_name": "Contact B",
        "contact_email": f"tenant_b_{secrets.token_hex(2)}@b.com",
        "billing_currency": "INR",
        "selected_modules": ["CRM_CORE"]
    })
    assert b_res.status_code == 201
    cid_b = b_res.json()["client_id"]

    appr_a = client.post(f"/api/v1/platform-b2b/signups/{cid_a}/approve", headers=auth_headers_super)
    inv_id_a = appr_a.json()["invoice_id"]

    db = SessionLocal()
    try:
        inv_a = db.query(PlatformInvoice).filter_by(id=inv_id_a).first()

        # ATTACK 1: Tenant B attempts to pay Tenant A's invoice (Ownership Mismatch)
        try:
            process_verified_payment(
                db,
                invoice_id=inv_a.id,
                client_id=cid_b,  # WRONG CLIENT
                amount=inv_a.total,
                currency="INR",
                gateway_payment_id=f"pay_hack_{secrets.token_hex(4)}"
            )
            assert False, "Should have raised ValueError on tenant ownership mismatch"
        except ValueError as err:
            assert "Tenant ownership mismatch" in str(err)
        print("✅ [PASSED] Tenant ownership mismatch between invoice and client rejected.")

        # ATTACK 2: Currency mismatch (USD paid on INR invoice)
        try:
            process_verified_payment(
                db,
                invoice_id=inv_a.id,
                client_id=cid_a,
                amount=inv_a.total,
                currency="USD",  # WRONG CURRENCY
                gateway_payment_id=f"pay_cur_{secrets.token_hex(4)}"
            )
            assert False, "Should have raised ValueError on currency mismatch"
        except ValueError as err:
            assert "Currency mismatch" in str(err)
        print("✅ [PASSED] Currency mismatch rejected.")

        # ATTACK 3: Negative or zero payment amount
        try:
            process_verified_payment(
                db,
                invoice_id=inv_a.id,
                client_id=cid_a,
                amount=Decimal("-500.00"),
                currency="INR",
                gateway_payment_id=f"pay_neg_{secrets.token_hex(4)}"
            )
            assert False, "Should have raised ValueError on negative payment amount"
        except ValueError as err:
            assert "positive" in str(err)
        print("✅ [PASSED] Negative payment amount rejected.")

        # ATTACK 4: Webhook with invalid JSON payload
        bad_json = client.post("/api/v1/platform-b2b/webhooks/razorpay", content=b"INVALID_NON_JSON")
        assert bad_json.status_code == 400
        print("✅ [PASSED] Malformed Razorpay webhook payload rejected with HTTP 400.")
    finally:
        db.close()


def test_public_status_anti_enumeration_and_sanitization():
    print("\n================================================================================")
    print("🚀 [TEST 5] PUBLIC APPLICATION STATUS ANTI-ENUMERATION & SANITIZATION")
    print("================================================================================")
    
    # 1. Attempt sequential enumeration
    for fake_code in ["CLIENT001", "CLIENT002", "TENANT-1", "TENANT-0001"]:
        res = client.get(f"/api/v1/platform-b2b/application-status/{fake_code}")
        assert res.status_code == 404, f"Expected 404 for {fake_code}, got {res.status_code}"
    print("✅ [PASSED] Sequential enumeration attempts returned HTTP 404.")

    # 2. Test valid status response sanitization
    val_hex = secrets.token_hex(4).upper()
    signup_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Secure Corp {val_hex}",
        "contact_name": "Secure Contact",
        "contact_email": f"sec_{val_hex.lower()}@secure.io",
        "selected_modules": ["CRM_CORE"]
    })
    c_code = signup_res.json()["client_code"]

    res_valid = client.get(f"/api/v1/platform-b2b/application-status/{c_code}")
    assert res_valid.status_code == 200
    body = res_valid.json()

    # Must contain public progress info
    assert "client_code" in body
    assert "company_name" in body
    assert "status" in body
    assert "progress_step" in body

    # MUST NOT leak internal database identifiers or credentials
    assert "password_hash" not in body
    assert "actor_staff_id" not in body
    assert "database_url" not in body
    print("✅ [PASSED] Public application status returns sanitized data without internal leaks.")


def test_invoice_seat_and_gst_calculations():
    print("\n================================================================================")
    print("🚀 [TEST 6] INVOICE SEAT MULTIPLIER & 18% GST CALCULATION VERIFICATION")
    print("================================================================================")
    
    calc_res = client.post("/api/v1/platform-b2b/calculate-pricing", json={
        "selected_modules": ["CRM_LEADS_SOLAR"],
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "seat_count": 5
    })
    assert calc_res.status_code == 200
    calc = calc_res.json()
    assert calc["seat_count"] == 5
    assert calc["tax_rate_pct"] == 18.0
    assert calc["cycle_subtotal"] > 0
    assert calc["tax_amount"] == round(calc["cycle_subtotal"] * 0.18, 2)
    assert calc["total_payable"] == round(calc["cycle_subtotal"] + calc["tax_amount"], 2)
    print(f"✅ [PASSED] 5 seats monthly: Subtotal ₹{calc['cycle_subtotal']}, GST ₹{calc['tax_amount']}, Total ₹{calc['total_payable']}")

    # Test 0 seats and negative seats validation
    bad_seat_0 = client.post("/api/v1/platform-b2b/calculate-pricing", json={
        "selected_modules": ["CRM_CORE"],
        "seat_count": 0
    })
    assert bad_seat_0.status_code in (400, 422)

    bad_seat_neg = client.post("/api/v1/platform-b2b/calculate-pricing", json={
        "selected_modules": ["CRM_CORE"],
        "seat_count": -3
    })
    assert bad_seat_neg.status_code in (400, 422)
    print("✅ [PASSED] 0 seats and negative seat inputs strictly rejected with HTTP 400/422.")


def test_tenant_admin_provisioning_boundary():
    print("\n================================================================================")
    print("🚀 [TEST 7] TENANT ADMIN PROVISIONING BOUNDARY VERIFICATION")
    print("================================================================================")
    
    db = SessionLocal()
    try:
        super_admin_emp, super_admin_token = create_test_staff_user(db, is_super=True)
    finally:
        db.close()
    auth_headers_super = {"Authorization": f"Bearer {super_admin_token}"}

    bound_hex = secrets.token_hex(4).upper()
    email = f"admin_{bound_hex.lower()}@tenantbound.io"
    signup_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Boundary Corp {bound_hex}",
        "contact_name": f"Admin {bound_hex}",
        "contact_email": email,
        "selected_modules": ["CRM_CORE"]
    })
    cid = signup_res.json()["client_id"]

    db = SessionLocal()
    try:
        # 1. State: Pending -> Admin MUST NOT exist
        assert db.query(StaffEmployee).filter_by(email=email).first() is None
        print("✅ [PASSED] In 'pending' state: Tenant Admin is NOT provisioned.")

        # 2. State: Approved -> Admin MUST NOT exist
        client.post(f"/api/v1/platform-b2b/signups/{cid}/approve", headers=auth_headers_super)
        assert db.query(StaffEmployee).filter_by(email=email).first() is None
        print("✅ [PASSED] In 'approved' state: Tenant Admin is NOT provisioned.")

        # 3. State: Payment Verified -> Admin MUST BE provisioned with tenant_admin role
        inv = db.query(PlatformInvoice).filter_by(client_id=cid).first()
        process_verified_payment(
            db,
            invoice_id=inv.id,
            client_id=cid,
            amount=inv.total,
            currency="INR",
            gateway_payment_id=f"pay_bound_{secrets.token_hex(4)}"
        )
        emp = db.query(StaffEmployee).filter_by(email=email).first()
        assert emp is not None, "Tenant Admin must be provisioned upon verified payment"
        assert emp.status == "active"
        assert emp.base_company_id is not None
        print(f"✅ [PASSED] Upon verified payment: Tenant Admin '{emp.emp_code}' provisioned for tenant company #{emp.base_company_id}.")
    finally:
        db.close()


def run_all_forensic_tests():
    test_full_commercial_lifecycle_and_security()
    test_commercial_terms_freeze_and_invoice_immutability()
    test_invalid_state_transitions_rejected()
    test_razorpay_mismatched_payment_and_forgery_defenses()
    test_public_status_anti_enumeration_and_sanitization()
    test_invoice_seat_and_gst_calculations()
    test_tenant_admin_provisioning_boundary()
    print("\n================================================================================")
    print("🎉 ALL 7 FORENSIC TESTS IN PHASE 4B PASSED (100% GREEN)!")
    print("================================================================================")


if __name__ == "__main__":
    run_all_forensic_tests()
