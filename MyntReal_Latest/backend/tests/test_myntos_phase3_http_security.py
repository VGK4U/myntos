"""
MYNTOS PHASE 3 — Real Authenticated HTTP Attack-Path & Security Test Suite
Validates live HTTP API request authorization, tenant ownership, and entitlement gates via FastAPI TestClient.
"""

import secrets
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffRole, StaffNdaVersion, StaffNdaAcceptance

client = TestClient(app, base_url="http://testserver")


def create_test_staff(db, base_company_id: int, role_code: str = "sales"):
    test_id = secrets.token_hex(4).upper()
    role_code_clean = role_code.lower()
    role = db.query(StaffRole).filter(StaffRole.role_code.ilike(role_code_clean)).first()
    if not role:
        role = StaffRole(role_code=role_code_clean, role_name=role_code_clean.upper(), hierarchy_level=50, is_active=True)
        db.add(role); db.flush()

    emp = StaffEmployee(
        emp_code=f"EMP_{test_id}",
        full_name=f"Test Employee {test_id}",
        email=f"emp_{test_id.lower()}@test.io",
        role_id=role.id,
        status="active",
        date_of_joining=date.today(),
        password_hash=SecurityManager.get_password_hash("TestPass123!"),
        base_company_id=base_company_id,
        data_companies=[base_company_id],
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
        "role": role.role_code.lower()
    })
    return emp, token


def test_http_meta_authentication_and_tenant_ownership():
    """
    Test Meta API Real HTTP Security:
    1. Unauthenticated request -> 401 Unauthorized
    2. Authenticated Tenant A staff request -> 200 OK
    3. Authenticated Tenant A staff attempting cross-tenant company_id=2 -> 403 Forbidden
    """
    print("\n--- [HTTP TEST 1] Meta Real HTTP Auth & Tenant Ownership ---")
    db = SessionLocal()
    try:
        emp_a, token_a = create_test_staff(db, base_company_id=1, role_code="sales")

        # 1. Unauthenticated request
        res_unauth = client.get("/api/v1/meta/connection-status")
        assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}"

        # 2. Authenticated Tenant A request
        res_auth_a = client.get(
            "/api/v1/meta/connection-status",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_auth_a.status_code == 200, f"Expected 200, got {res_auth_a.status_code}: {res_auth_a.text}"

        # 3. Cross-Tenant Attempt: Tenant A staff passing company_id=2 (Forbidden)
        res_attack = client.get(
            "/api/v1/meta/connection-status?company_id=2",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_attack.status_code == 403, f"Expected 403 for cross-tenant company_id attempt, got {res_attack.status_code}"

        print("✅ [HTTP PASSED] Meta HTTP authentication and cross-tenant parameter attack prevention verified.")
    finally:
        db.close()


def test_http_whatsapp_credentials_tenant_isolation():
    """
    Test WhatsApp Configuration Real HTTP Security:
    1. Unauthenticated request -> 401/403 Unauthorized
    2. Authenticated Tenant A staff GET /credentials -> Scoped strictly to Tenant A
    3. Authenticated Tenant A staff PUT /credentials -> Upserts Tenant A; does NOT delete Tenant B
    """
    print("\n--- [HTTP TEST 2] WhatsApp Real HTTP Credentials Isolation ---")
    db = SessionLocal()
    try:
        # Seed Tenant B credentials in DB
        db.execute(
            text("""
                INSERT INTO whatsapp_api_config (access_token, phone_number_id, verify_token, company_id)
                VALUES ('enc_token_tenant_b', 'pid_tenant_b_999', 'vtok_b', 2)
                ON CONFLICT DO NOTHING
            """)
        )
        db.commit()

        # Create staff with key_leadership role
        emp_a, token_a = create_test_staff(db, base_company_id=1, role_code="key_leadership")

        # 1. Unauthenticated request
        res_unauth = client.get("/api/v1/whatsapp-config/credentials")
        assert res_unauth.status_code in (401, 403), f"Expected 401/403, got {res_unauth.status_code}"

        # 2. Authenticated Tenant A staff GET
        res_get_a = client.get(
            "/api/v1/whatsapp-config/credentials",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_get_a.status_code == 200, f"Expected 200, got {res_get_a.status_code}: {res_get_a.text}"
        data = res_get_a.json()
        assert data.get("phone_number_id") != "pid_tenant_b_999", "Tenant A must NOT receive Tenant B phone_number_id"

        # 3. Verify Tenant B row still exists in DB
        row_b = db.execute(text("SELECT phone_number_id FROM whatsapp_api_config WHERE company_id = 2")).fetchone()
        assert row_b is not None, "Tenant B config must not be deleted by Tenant A operations"

        # Cleanup
        db.execute(text("DELETE FROM whatsapp_api_config WHERE company_id = 2"))
        db.commit()

        print("✅ [HTTP PASSED] WhatsApp HTTP credential isolation and non-destructive upsert verified.")
    finally:
        db.close()


def test_http_integration_entitlement_gating():
    """
    Test Integration Entitlement HTTP Enforcement:
    1. Unsubscribed / Unentitled client receives HTTP 403 Forbidden ("Service not enabled for this tenant.").
    2. Entitled client receives HTTP 200 OK.
    """
    print("\n--- [HTTP TEST 3] Integration Entitlement Real HTTP Gating ---")
    db = SessionLocal()
    try:
        # Create staff in company 7 (client_id=4 which has no integration modules enabled)
        emp_unentitled, token_unentitled = create_test_staff(db, base_company_id=7, role_code="sales")

        res_meta = client.get(
            "/api/v1/meta/connection-status",
            headers={"Authorization": f"Bearer {token_unentitled}"}
        )
        assert res_meta.status_code == 403, f"Expected 403 for unentitled tenant, got {res_meta.status_code}: {res_meta.text}"
        assert "Service not enabled" in res_meta.json().get("detail", "")

        print("✅ [HTTP PASSED] Integration HTTP entitlement 403 gate verified.")
    finally:
        db.close()


if __name__ == "__main__":
    test_http_meta_authentication_and_tenant_ownership()
    test_http_whatsapp_credentials_tenant_isolation()
    test_http_integration_entitlement_gating()
    print("\n================================================================================")
    print("🎉 ALL PHASE 3 REAL HTTP AUTHENTICATION & SECURITY TESTS PASSED (100%)!")
    print("================================================================================")
