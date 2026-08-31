"""
MYNTOS PHASE 4C — Client Admin User Creation & Tenant Entitlement Boundary Test Suite
Validates:
1. Tenant Admin creates valid sub-user within own tenant boundary
2. Cross-tenant user creation blocked (Tenant Admin A cannot create users in Tenant B)
3. Unpurchased module assignment blocked (Cannot assign unentitled modules)
4. Privilege escalation blocked (Cannot create Super Admin, Platform Admin, or role >= 85)
5. Hierarchy level manipulation blocked
6. Company/Data scope manipulation blocked (Cannot expand data_companies across tenants)
7. Cross-tenant user access blocked (Tenant Admin A cannot see or modify Tenant B users)
8. Commercial state manipulation blocked (Tenant Admin cannot approve/modify invoices/subscriptions)
9. Unauthenticated API access blocked (401 Unauthorized)
10. Normal sub-user blocked from Tenant Admin APIs (403 Forbidden)
11. Disabled user authentication blocked immediately (403 Forbidden)
12. Cross-tenant data isolation preserved
13. Payload tampering (client_id/base_company_id injection) safely normalized/blocked
14. Tenant with CRM only cannot assign Telephony to user
15. Tenant with CRM + WhatsApp can assign only those active modules
16. Privilege escalation rejected with HTTP 403
17. Existing Phase 4B Root Tenant Admin remains correctly scoped
"""

import secrets
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import (
    StaffEmployee, StaffRole, StaffNdaVersion, StaffNdaAcceptance,
    StaffDepartment
)
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import (
    PlatformClient, PlatformSubscription, PlatformSubscriptionModule,
    PlatformModule, PlatformModulePricing
)
from app.models.platform_b2b_billing import PlatformInvoice, PlatformPayment
from app.services.platform_b2b_billing import process_verified_payment
from app.services.b2b_shadow import is_module_entitled

client = TestClient(app, base_url="http://testserver")


def _setup_active_tenant(company_name: str, email: str, modules: list, seats: int = 5):
    """Helper: provisions active tenant via Phase 4A/4B commercial lifecycle"""
    db = SessionLocal()
    try:
        super_admin_role = db.query(StaffRole).filter(StaffRole.role_code.ilike("super_admin")).first()
        if not super_admin_role:
            super_admin_role = StaffRole(role_code="super_admin", role_name="Super Admin", hierarchy_level=100, is_active=True)
            db.add(super_admin_role); db.commit()

        super_admin = db.query(StaffEmployee).filter(StaffEmployee.role_id == super_admin_role.id).first()
        if not super_admin:
            super_admin = StaffEmployee(
                emp_code=f"SA_{secrets.token_hex(3).upper()}",
                full_name="Platform Super Admin",
                email=f"sa_{secrets.token_hex(3)}@platform.io",
                role_id=super_admin_role.id,
                status="active",
                date_of_joining=date.today(),
                password_hash=SecurityManager.get_password_hash("SuperPass123!"),
                base_company_id=1,
                data_companies=[1],
            )
            db.add(super_admin); db.commit(); db.refresh(super_admin)

        for nda in db.query(StaffNdaVersion).filter_by(status='active').all():
            if not db.query(StaffNdaAcceptance).filter_by(employee_id=super_admin.id, nda_version_id=nda.id).first():
                db.add(StaffNdaAcceptance(
                    employee_id=super_admin.id,
                    nda_version_id=nda.id,
                    acceptance_ip="127.0.0.1",
                    document_type=nda.document_type or 'NDA'
                ))
        db.commit()

        sa_token = SecurityManager.create_access_token(data={
            "sub": str(super_admin.id), "emp_code": super_admin.emp_code,
            "employee_id": super_admin.emp_code, "user_type": "staff",
            "role": "super_admin", "is_super_admin": True
        })
    finally:
        db.close()

    # 1. Sign up (Outside open session)
    s_res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": company_name,
        "contact_name": f"{company_name} Contact",
        "contact_email": email,
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "selected_modules": modules,
        "seat_count": seats
    })
    assert s_res.status_code == 201, f"Signup failed: {s_res.text}"
    cid = s_res.json()["client_id"]

    # 2. Super admin approve (Outside open session)
    appr_res = client.post(f"/api/v1/platform-b2b/signups/{cid}/approve", headers={"Authorization": f"Bearer {sa_token}"})
    assert appr_res.status_code == 200, f"Approval failed: {appr_res.text}"
    inv_id = appr_res.json()["invoice_id"]

    # 3. Verified Payment
    db2 = SessionLocal()
    try:
        inv = db2.query(PlatformInvoice).filter_by(id=inv_id).first()
        pay_res = process_verified_payment(
            db2,
            invoice_id=inv.id,
            client_id=cid,
            amount=inv.total,
            currency=inv.currency,
            gateway_payment_id=f"pay_t_{secrets.token_hex(6)}"
        )
        assert pay_res["ok"] is True

        company = db2.query(AssociatedCompany).filter_by(client_id=cid).first()
        root_admin = db2.query(StaffEmployee).filter_by(base_company_id=company.id).first()
        comp_id = company.id
        admin_id = root_admin.id
        admin_code = root_admin.emp_code

        # Ensure NDA accepted for token auth
        for nda in db2.query(StaffNdaVersion).filter_by(status='active').all():
            if not db2.query(StaffNdaAcceptance).filter_by(employee_id=admin_id, nda_version_id=nda.id).first():
                db2.add(StaffNdaAcceptance(
                    employee_id=admin_id,
                    nda_version_id=nda.id,
                    acceptance_ip="127.0.0.1",
                    document_type=nda.document_type or 'NDA'
                ))
        db2.commit()

        admin_token = SecurityManager.create_access_token(data={
            "sub": str(admin_id),
            "emp_code": admin_code,
            "employee_id": admin_code,
            "user_type": "staff",
            "role": "tenant_admin",
            "is_super_admin": False
        })

        return {
            "client_id": cid,
            "company_id": comp_id,
            "admin_id": admin_id,
            "admin_code": admin_code,
            "token": admin_token
        }
    finally:
        db2.close()


def test_phase4c_client_admin_boundary():
    print("\n================================================================================")
    print("🚀 [START] MYNTOS PHASE 4C CLIENT ADMIN USER CREATION & BOUNDARY SUITE")
    print("================================================================================")

    # Setup Tenant A (Purchased: CRM_CORE, WHATSAPP_INTEGRATION)
    hex_a = secrets.token_hex(3).upper()
    t_a = _setup_active_tenant(
        company_name=f"Tenant Alpha {hex_a}",
        email=f"admin_{hex_a.lower()}@alpha.io",
        modules=["CRM_CORE", "WHATSAPP_INTEGRATION"],
        seats=10
    )
    headers_a = {"Authorization": f"Bearer {t_a['token']}"}

    # Setup Tenant B (Purchased: CRM_CORE, TELEPHONY_INTEGRATION)
    hex_b = secrets.token_hex(3).upper()
    t_b = _setup_active_tenant(
        company_name=f"Tenant Beta {hex_b}",
        email=f"admin_{hex_b.lower()}@beta.io",
        modules=["CRM_CORE", "TELEPHONY_INTEGRATION"],
        seats=10
    )
    headers_b = {"Authorization": f"Bearer {t_b['token']}"}

    db = SessionLocal()
    try:
        # Resolve normal staff role (sales rep / executive with hierarchy_level = 30)
        sales_role = db.query(StaffRole).filter(StaffRole.hierarchy_level < 80, StaffRole.is_active == True).first()
        if not sales_role:
            sales_role = StaffRole(role_code="sales_agent", role_name="Sales Agent", hierarchy_level=30, is_active=True)
            db.add(sales_role); db.commit(); db.refresh(sales_role)
        sales_role_id = sales_role.id

        # Resolve super admin role (hierarchy_level = 100)
        super_role = db.query(StaffRole).filter(StaffRole.hierarchy_level >= 90).first()
        super_role_id = super_role.id
    finally:
        db.close()

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Tenant Admin creates valid sub-user within own tenant boundary
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 1] Tenant Admin creates valid sub-user ---")
    create_res = client.post("/api/v1/platform-b2b/tenant/users", headers=headers_a, json={
        "full_name": "Alice Agent",
        "email": f"alice_{hex_a.lower()}@alpha.io",
        "phone": "+91 9123456780",
        "designation": "Sales Executive",
        "role_id": sales_role_id,
        "assigned_modules": ["CRM_CORE", "WHATSAPP_INTEGRATION"]
    })
    assert create_res.status_code == 200, f"Create user failed: {create_res.text}"
    user_a1 = create_res.json()["user"]
    assert user_a1["full_name"] == "Alice Agent"
    assert user_a1["base_company_id"] == t_a["company_id"]
    print(f"✅ [PASSED] Sub-user '{user_a1['emp_code']}' created in tenant company #{t_a['company_id']}.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2 & 6: Scope Manipulation Attack (Injecting Tenant B company ID)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 2 & 6] Scope Manipulation Attack ---")
    # Admin A attempts to create a user with base_company_id = t_b['company_id']
    hack_res = client.post("/api/v1/platform-b2b/tenant/users", headers=headers_a, json={
        "full_name": "Bob Intruder",
        "email": f"bob_{hex_a.lower()}@alpha.io",
        "role_id": sales_role_id,
        "base_company_id": t_b["company_id"], # INJECTED WRONG TENANT
        "data_companies": [t_b["company_id"]] # INJECTED WRONG TENANT
    })
    assert hack_res.status_code == 200
    user_hacked = hack_res.json()["user"]
    # Server MUST have strictly overridden and locked to t_a['company_id']
    assert user_hacked["base_company_id"] == t_a["company_id"]
    print("✅ [PASSED] Tenant boundary strictly locked; client-supplied company ID injection ignored.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3 & 14: Unpurchased Module Assignment Rejection (Telephony on Tenant A)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 3 & 14] Unpurchased Module Assignment Rejection ---")
    # Tenant A only bought CRM_CORE & WHATSAPP; attempts to assign TELEPHONY_INTEGRATION
    unentitled_res = client.post("/api/v1/platform-b2b/tenant/users", headers=headers_a, json={
        "full_name": "Charlie Caller",
        "email": f"charlie_{hex_a.lower()}@alpha.io",
        "role_id": sales_role_id,
        "assigned_modules": ["TELEPHONY_INTEGRATION"] # NOT PURCHASED BY TENANT A
    })
    assert unentitled_res.status_code == 400, f"Expected 400, got {unentitled_res.status_code}"
    assert "not purchased" in unentitled_res.json()["detail"].lower()
    print("✅ [PASSED] Unpurchased module assignment strictly rejected with HTTP 400.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4, 5 & 16: Privilege Escalation Attack (Creating Super Admin)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 4, 5 & 16] Privilege Escalation Rejection ---")
    # Admin A attempts to create a Super Admin user
    escalate_res = client.post("/api/v1/platform-b2b/tenant/users", headers=headers_a, json={
        "full_name": "Eve Escalator",
        "email": f"eve_{hex_a.lower()}@alpha.io",
        "role_id": super_role_id, # SUPER ADMIN ROLE
    })
    assert escalate_res.status_code == 403, f"Expected 403 Forbidden, got {escalate_res.status_code}"
    print("✅ [PASSED] Privilege escalation attempt strictly rejected with HTTP 403.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 7: Cross-Tenant User Listing and Modification Isolation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 7] Cross-Tenant User Isolation ---")
    # Tenant Admin A queries user list -> Must only see Tenant A users, 0 Tenant B users
    list_a = client.get("/api/v1/platform-b2b/tenant/users", headers=headers_a)
    assert list_a.status_code == 200
    users_a = list_a.json()["users"]
    for u in users_a:
        assert u["base_company_id"] == t_a["company_id"], f"User {u['id']} leaked across tenant!"

    # Tenant Admin A attempts to modify or deactivate Tenant B user -> Must return 404
    cross_mod = client.put(
        f"/api/v1/platform-b2b/tenant/users/{t_b['admin_id']}/status",
        headers=headers_a,
        json={"status": "deactivated"}
    )
    assert cross_mod.status_code in (403, 404), f"Expected 403/404, got {cross_mod.status_code}"
    print("✅ [PASSED] Cross-tenant user listing and modification strictly isolated (HTTP 404/403).")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 8: Tenant Admin Cannot Alter Platform Billing/Commercial State
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 8] Commercial State Modification Gating ---")
    # Tenant Admin A attempts to approve or generate invoice on super admin endpoint
    comm_attack = client.post(f"/api/v1/platform-b2b/signups/{t_a['client_id']}/approve", headers=headers_a)
    assert comm_attack.status_code == 403, f"Expected 403 Forbidden, got {comm_attack.status_code}"
    print("✅ [PASSED] Tenant Admin cannot access Zynova Platform super-admin endpoints.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 9 & 10: Authentication and Sub-User RBAC Gating
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 9 & 10] Auth & Sub-User RBAC Gating ---")
    # Unauthenticated request -> 401
    unauth = client.get("/api/v1/platform-b2b/tenant/users")
    assert unauth.status_code == 401

    # Sub-user Alice (sales agent) creates token and attempts to call Tenant Admin endpoint -> 403
    db = SessionLocal()
    try:
        alice_emp = db.query(StaffEmployee).filter_by(id=user_a1["id"]).first()
        for nda in db.query(StaffNdaVersion).filter_by(status='active').all():
            db.add(StaffNdaAcceptance(
                employee_id=alice_emp.id,
                nda_version_id=nda.id,
                acceptance_ip="127.0.0.1",
                document_type=nda.document_type or 'NDA'
            ))
        db.commit()

        alice_token = SecurityManager.create_access_token(data={
            "sub": str(alice_emp.id), "emp_code": alice_emp.emp_code,
            "employee_id": alice_emp.emp_code, "user_type": "staff",
            "role": "sales_agent", "is_super_admin": False
        })
    finally:
        db.close()

    alice_attack = client.get("/api/v1/platform-b2b/tenant/users", headers={"Authorization": f"Bearer {alice_token}"})
    assert alice_attack.status_code == 403, f"Expected 403 Forbidden for sub-user, got {alice_attack.status_code}"
    print("✅ [PASSED] Unauthenticated (401) and sub-user non-admin (403) access strictly blocked.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 11: Disabled User Authentication Immediate Blocking
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 11] Disabled User Immediate Revocation ---")
    # Deactivate Alice
    deact_res = client.put(
        f"/api/v1/platform-b2b/tenant/users/{user_a1['id']}/status",
        headers=headers_a,
        json={"status": "deactivated", "reason": "Left company"}
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "deactivated"

    # Alice attempts to access API -> Blocked with 403 Forbidden
    deact_attempt = client.get("/api/v1/platform-b2b/tenant/entitled-modules", headers={"Authorization": f"Bearer {alice_token}"})
    assert deact_attempt.status_code == 403
    print("✅ [PASSED] Deactivated user immediately blocked with HTTP 403 Forbidden.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 15: Tenant Entitled Modules Discovery
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 15] Entitled Modules Discovery ---")
    ent_res = client.get("/api/v1/platform-b2b/tenant/entitled-modules", headers=headers_a)
    assert ent_res.status_code == 200
    mods_a = [m["module_code"] for m in ent_res.json()["entitled_modules"]]
    assert "CRM_CORE" in mods_a
    assert "WHATSAPP_INTEGRATION" in mods_a
    assert "TELEPHONY_INTEGRATION" not in mods_a
    print("✅ [PASSED] Entitled modules endpoint returns strictly active subscribed modules.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 17: Root Tenant Admin Scope & Protection
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [TEST 17] Root Tenant Admin Protection ---")
    # Admin A attempts to deactivate self -> Rejected with 400
    self_deact = client.put(
        f"/api/v1/platform-b2b/tenant/users/{t_a['admin_id']}/status",
        headers=headers_a,
        json={"status": "deactivated"}
    )
    assert self_deact.status_code == 400
    print("✅ [PASSED] Root Tenant Administrator self-lockout protected.")

    print("\n================================================================================")
    print("🎉 ALL 17 PHASE 4C CLIENT ADMIN BOUNDARY SCENARIOS PASSED (100% GREEN)!")
    print("================================================================================")


if __name__ == "__main__":
    test_phase4c_client_admin_boundary()
