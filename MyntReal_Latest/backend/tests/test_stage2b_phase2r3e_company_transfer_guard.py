"""
Stage 2B Phase 2R-3E: Lead Company Transfer Guard Verification Test Suite

Verifies that normal CRM lead update and bulk update endpoints strictly prevent
cross-company lead transfer and cross-company category assignment.

Scenarios Tested:
  Scenario A: PUT /leads/{lead_id} and PUT /unified-my-leads/{lead_id}/full-update with same company_id -> Allowed.
  Scenario B: PUT /leads/{lead_id} and PUT /unified-my-leads/{lead_id}/full-update with different company_id -> Rejected with HTTP 400, DB unmutated.
  Scenario C: PUT same-company category -> Allowed, category updated, company_id untouched.
  Scenario D: PUT cross-company category -> Rejected with HTTP 400, category & company_id untouched.
  Scenario E: Bulk update same-company category -> Allowed, category updated, company_id untouched.
  Scenario F: Bulk update cross-company category -> Error in response errors list, category & company_id untouched.
  Scenario G: Unauthorized caller attempt -> Rejected (HTTP 403/404), DB unmutated.
  Scenario H: Zero Operational Database Mutations Assertion (100% pristine baseline preserved).
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from unittest.mock import patch
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
load_dotenv(_backend_dir / ".env")

from sqlalchemy import text
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine, get_db, SessionLocal
from app.core.security import SecurityManager
from app.models.crm import CRMLead
from app.models.signup_category import SignupCategory
from app.models.staff import StaffEmployee, StaffCompanyMembership
from app.services.auth_context_service import invalidate_auth_cache
import app.services.auth_context_service as acs


def mint_token(employee_id: int, emp_code: str, tenant_id: int = 1, token_version: int = 1, hours: int = 24) -> str:
    return SecurityManager.create_access_token(
        data={
            "sub": str(employee_id),
            "emp_code": emp_code,
            "tenant_id": tenant_id,
            "token_version": token_version,
            "user_type": "staff"
        },
        expires_delta=timedelta(hours=hours)
    )


def test_stage2b_phase2r3e_company_transfer_guard():
    print("\n" + "=" * 80)
    print("STAGE 2B PHASE 2R-3E: LEAD COMPANY TRANSFER GUARD VERIFICATION SUITE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 0: Capture Pre-Test Operational Row Counts
    # ─────────────────────────────────────────────────────────────────────────
    baseline_db = SessionLocal()
    tables_to_audit = [
        "staff_employees",
        "staff_company_memberships",
        "associated_companies",
        "platform_clients",
        "staff_roles",
        "staff_departments",
        "crm_leads",
        "crm_lead_phones",
        "crm_lead_phone_provenances",
        "crm_lead_deals",
        "crm_lead_transactions",
        "signup_categories",
    ]
    pre_counts = {}
    print("\n[STEP 0] Capturing Baseline Row Counts:")
    for tbl in tables_to_audit:
        cnt = baseline_db.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
        pre_counts[tbl] = cnt
        print(f"  {tbl:<30}: {cnt}")
    baseline_db.close()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Connect Transactional Rollback Harness
    # STRICT SAFETY RULE: Operational database must remain 100% UNMUTATED.
    # ─────────────────────────────────────────────────────────────────────────
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    # Intercept commits within test to prevent persisting to live database
    session.commit = session.flush
    session.rollback = lambda: None

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="http://testserver")

    nda_patch = patch("app.api.v1.endpoints.staff_auth.check_all_pending_agreements", return_value=(False, None, None))
    nda_patch.start()

    try:
        invalidate_auth_cache()
        if hasattr(acs, "_auth_cache"):
            acs._auth_cache.clear()

        # Auth headers for MR10001 (Superadmin / Platform Admin / Tenant 1)
        token_admin = mint_token(1, "MR10001", tenant_id=1)
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # ─────────────────────────────────────────────────────────────────────
        # SETUP TEST ENTITIES (Within Rollback Transaction)
        # ─────────────────────────────────────────────────────────────────────
        # Lead 1 in Company 4 (tenant 1)
        lead_1 = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Guard Test Alpha",
            phone="9811199001",
            status="new",
            source="Manual",
            priority="medium"
        )
        session.add(lead_1)

        # Lead 2 in Company 2 (tenant 1)
        lead_2 = CRMLead(
            tenant_id=1,
            company_id=2,
            name="Guard Test Beta",
            phone="9811199002",
            status="new",
            source="Manual",
            priority="medium"
        )
        session.add(lead_2)
        session.flush()

        # Setup unauthorized staff employee (scoped ONLY to Company 2, no access to Company 4)
        emp_unauth = StaffEmployee(
            emp_code="EMP_UNAUTH_GUARD",
            full_name="Unauthorized Guard Staff",
            email="unauth_guard@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=5,
            staff_type="STAFF",
            date_of_joining=date(2026, 1, 1)
        )
        session.add(emp_unauth)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_unauth.id, company_id=2, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        token_unauth = mint_token(emp_unauth.id, emp_unauth.emp_code, tenant_id=1)
        headers_unauth = {"Authorization": f"Bearer {token_unauth}"}

        # Retrieve or create test categories
        # Category for Company 4
        cat_c4 = session.query(SignupCategory).filter(SignupCategory.company_id == 4).first()
        if not cat_c4:
            cat_c4 = SignupCategory(
                company_id=4,
                name="Test Category C4",
                slug="test-category-c4"
            )
            session.add(cat_c4)
            session.flush()

        # Category for Company 2
        cat_c2 = session.query(SignupCategory).filter(SignupCategory.company_id == 2).first()
        if not cat_c2:
            cat_c2 = SignupCategory(
                company_id=2,
                name="Test Category C2",
                slug="test-category-c2"
            )
            session.add(cat_c2)
            session.flush()

        print(f"\n[SETUP] Test entities initialized in rollback transaction:")
        print(f"  Lead 1 (Company 4): id={lead_1.id}, phone={lead_1.phone}")
        print(f"  Lead 2 (Company 2): id={lead_2.id}, phone={lead_2.phone}")
        print(f"  Unauth Staff (Company 2 only): id={emp_unauth.id}, emp_code={emp_unauth.emp_code}")
        print(f"  Category C4: id={cat_c4.id}, company_id={cat_c4.company_id}, name='{cat_c4.name}'")
        print(f"  Category C2: id={cat_c2.id}, company_id={cat_c2.company_id}, name='{cat_c2.name}'")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO A: PUT same company -> allowed
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO A] Testing PUT same company_id (allowed, company unchanged)...")
        # 1. Standard lead update endpoint with matching query company_id and payload company_id
        res_a1 = client.put(
            f"/api/v1/crm/leads/{lead_1.id}?company_id=4",
            json={"company_id": 4, "name": "Guard Test Alpha Updated"},
            headers=headers_admin
        )
        assert res_a1.status_code == 200, f"Expected 200, got {res_a1.status_code}: {res_a1.text}"
        session.refresh(lead_1)
        assert lead_1.company_id == 4, f"Expected company_id 4, got {lead_1.company_id}"
        assert lead_1.name == "Guard Test Alpha Updated", f"Expected updated name, got {lead_1.name}"
        print("  ✓ PUT /api/v1/crm/leads/{id} with matching company_id succeeded; company_id preserved as 4.")

        # 2. Unified full update endpoint
        res_a2 = client.put(
            f"/api/v1/crm/unified-my-leads/{lead_1.id}/full-update",
            json={"company_id": 4, "name": "Guard Test Alpha Full Updated"},
            headers=headers_admin
        )
        assert res_a2.status_code == 200, f"Expected 200, got {res_a2.status_code}: {res_a2.text}"
        session.refresh(lead_1)
        assert lead_1.company_id == 4, f"Expected company_id 4, got {lead_1.company_id}"
        assert lead_1.name == "Guard Test Alpha Full Updated", f"Expected full updated name, got {lead_1.name}"
        print("  ✓ PUT /api/v1/crm/unified-my-leads/{id}/full-update with matching company_id succeeded; company_id preserved as 4.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO B: PUT cross company -> HTTP 400, DB unchanged
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO B] Testing PUT cross-company transfer attempt (HTTP 400 rejection)...")
        # 1. Standard lead update endpoint with different company_id in payload
        res_b1 = client.put(
            f"/api/v1/crm/leads/{lead_1.id}?company_id=4",
            json={"company_id": 2, "name": "Malicious Transfer Attempt"},
            headers=headers_admin
        )
        assert res_b1.status_code == 400, f"Expected 400, got {res_b1.status_code}: {res_b1.text}"
        assert "Cross-company lead reassignment is not permitted" in res_b1.json().get("detail", ""), \
            f"Expected cross-company error message, got {res_b1.text}"
        session.refresh(lead_1)
        assert lead_1.company_id == 4, f"Database company_id was mutated! Expected 4, got {lead_1.company_id}"
        assert lead_1.name == "Guard Test Alpha Full Updated", f"Database name was mutated on rejected request!"
        print("  ✓ PUT /api/v1/crm/leads/{id} with mismatched company_id rejected with HTTP 400; DB company_id untouched.")

        # 2. Unified full update endpoint with different company_id
        res_b2 = client.put(
            f"/api/v1/crm/unified-my-leads/{lead_1.id}/full-update",
            json={"company_id": 2, "name": "Malicious Full Transfer Attempt"},
            headers=headers_admin
        )
        assert res_b2.status_code == 400, f"Expected 400, got {res_b2.status_code}: {res_b2.text}"
        assert "Cross-company lead reassignment is not permitted" in res_b2.json().get("detail", ""), \
            f"Expected cross-company error message, got {res_b2.text}"
        session.refresh(lead_1)
        assert lead_1.company_id == 4, f"Database company_id was mutated! Expected 4, got {lead_1.company_id}"
        print("  ✓ PUT /api/v1/crm/unified-my-leads/{id}/full-update with mismatched company_id rejected with HTTP 400; DB company_id untouched.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO C: PUT same-company category -> allowed, company unchanged
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO C] Testing PUT same-company category assignment (allowed, company unchanged)...")
        # 1. Standard lead update endpoint
        res_c1 = client.put(
            f"/api/v1/crm/leads/{lead_2.id}?company_id=2",
            json={"category_id": cat_c2.id},
            headers=headers_admin
        )
        assert res_c1.status_code == 200, f"Expected 200, got {res_c1.status_code}: {res_c1.text}"
        session.refresh(lead_2)
        assert lead_2.category_id == cat_c2.id, f"Expected category_id {cat_c2.id}, got {lead_2.category_id}"
        assert lead_2.company_id == 2, f"Expected company_id 2, got {lead_2.company_id}"
        print(f"  ✓ PUT /api/v1/crm/leads/ assigned Category #{cat_c2.id} to Lead 2; company_id preserved as 2.")

        # 2. Unified full update endpoint
        res_c2 = client.put(
            f"/api/v1/crm/unified-my-leads/{lead_1.id}/full-update",
            json={"category_id": cat_c4.id},
            headers=headers_admin
        )
        assert res_c2.status_code == 200, f"Expected 200, got {res_c2.status_code}: {res_c2.text}"
        session.refresh(lead_1)
        assert lead_1.category_id == cat_c4.id, f"Expected category_id {cat_c4.id}, got {lead_1.category_id}"
        assert lead_1.company_id == 4, f"Expected company_id 4, got {lead_1.company_id}"
        print(f"  ✓ PUT /api/v1/crm/unified-my-leads/ assigned Category #{cat_c4.id} to Lead 1; company_id preserved as 4.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO D: PUT cross-company category -> HTTP 400, company unchanged
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO D] Testing PUT cross-company category assignment (HTTP 400 rejection)...")
        # 1. Standard lead update endpoint: assign Company 2 category to Company 4 lead
        res_d1 = client.put(
            f"/api/v1/crm/leads/{lead_1.id}?company_id=4",
            json={"category_id": cat_c2.id},
            headers=headers_admin
        )
        assert res_d1.status_code == 400, f"Expected 400, got {res_d1.status_code}: {res_d1.text}"
        assert f"Category '{cat_c2.name}' belongs to Company #{cat_c2.company_id}" in res_d1.json().get("detail", ""), \
            f"Expected cross-company category error, got {res_d1.text}"
        session.refresh(lead_1)
        assert lead_1.category_id == cat_c4.id, f"Category was mutated on rejected request! Got {lead_1.category_id}"
        assert lead_1.company_id == 4, f"Company was mutated on rejected request! Expected 4, got {lead_1.company_id}"
        print("  ✓ PUT /api/v1/crm/leads/ rejected cross-company category with HTTP 400; DB category & company untouched.")

        # 2. Unified full update endpoint: assign Company 4 category to Company 2 lead
        res_d2 = client.put(
            f"/api/v1/crm/unified-my-leads/{lead_2.id}/full-update",
            json={"category_id": cat_c4.id},
            headers=headers_admin
        )
        assert res_d2.status_code == 400, f"Expected 400, got {res_d2.status_code}: {res_d2.text}"
        assert f"Category '{cat_c4.name}' belongs to Company #{cat_c4.company_id}" in res_d2.json().get("detail", ""), \
            f"Expected cross-company category error, got {res_d2.text}"
        session.refresh(lead_2)
        assert lead_2.category_id == cat_c2.id, f"Category was mutated on rejected request! Got {lead_2.category_id}"
        assert lead_2.company_id == 2, f"Company was mutated on rejected request! Expected 2, got {lead_2.company_id}"
        print("  ✓ PUT /api/v1/crm/unified-my-leads/ rejected cross-company category with HTTP 400; DB category & company untouched.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO E: Bulk update same-company category -> allowed
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO E] Testing POST bulk-update with same-company category (allowed)...")
        res_e = client.post(
            f"/api/v1/crm/leads/bulk-update?company_id=4",
            json={"lead_ids": [lead_1.id], "category_id": cat_c4.id},
            headers=headers_admin
        )
        assert res_e.status_code == 200, f"Expected 200, got {res_e.status_code}: {res_e.text}"
        data_e = res_e.json().get("data", {})
        assert data_e.get("updated_count") == 1, f"Expected updated_count 1, got {data_e.get('updated_count')}"
        assert len(data_e.get("errors", [])) == 0, f"Expected 0 errors, got {data_e.get('errors')}"
        session.refresh(lead_1)
        assert lead_1.category_id == cat_c4.id, f"Expected category_id {cat_c4.id}, got {lead_1.category_id}"
        assert lead_1.company_id == 4, f"Company was mutated! Expected 4, got {lead_1.company_id}"
        print("  ✓ POST /api/v1/crm/leads/bulk-update succeeded for same-company category; company_id preserved as 4.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO F: Bulk update cross-company category -> error returned in errors
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO F] Testing POST bulk-update with cross-company category (rejected via error dict)...")
        res_f = client.post(
            f"/api/v1/crm/leads/bulk-update?company_id=4",
            json={"lead_ids": [lead_1.id], "category_id": cat_c2.id},
            headers=headers_admin
        )
        assert res_f.status_code == 200, f"Expected 200, got {res_f.status_code}: {res_f.text}"
        data_f = res_f.json().get("data", {})
        assert data_f.get("updated_count") == 0, f"Expected updated_count 0, got {data_f.get('updated_count')}"
        assert len(data_f.get("errors", [])) == 1, f"Expected 1 error in errors list, got {data_f.get('errors')}"
        err_entry = data_f["errors"][0]
        assert err_entry["lead_id"] == lead_1.id, f"Expected error for lead {lead_1.id}, got {err_entry}"
        assert "Cross-company category assignment is not permitted" in err_entry["error"], \
            f"Expected cross-company error, got {err_entry['error']}"
        session.refresh(lead_1)
        assert lead_1.category_id == cat_c4.id, f"Category was mutated! Expected {cat_c4.id}, got {lead_1.category_id}"
        assert lead_1.company_id == 4, f"Company was mutated! Expected 4, got {lead_1.company_id}"
        print("  ✓ POST /api/v1/crm/leads/bulk-update rejected cross-company category with canonical error dict; DB untouched.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO G: Unauthorized attempt -> HTTP 403/404
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO G] Testing unauthorized access attempt (rejected with 403/404 anti-enumeration)...")
        # Unauth staff (Company 2 only) attempting to mutate Company 4 lead via PUT /leads/{id}
        res_g1 = client.put(
            f"/api/v1/crm/leads/{lead_1.id}?company_id=4",
            json={"company_id": 4, "name": "Hacker Edit"},
            headers=headers_unauth
        )
        assert res_g1.status_code in (403, 404), f"Expected 403 or 404, got {res_g1.status_code}: {res_g1.text}"
        session.refresh(lead_1)
        assert lead_1.name != "Hacker Edit", "Unauthorized request mutated database name!"
        assert lead_1.company_id == 4, "Unauthorized request mutated company_id!"
        print(f"  ✓ Cross-company unassigned mutation rejected with HTTP {res_g1.status_code}; DB unmutated.")

        # Unauth staff attempting to mutate Company 4 lead via PUT /unified-my-leads/{id}/full-update
        res_g2 = client.put(
            f"/api/v1/crm/unified-my-leads/{lead_1.id}/full-update",
            json={"company_id": 4, "name": "Hacker Edit Full"},
            headers=headers_unauth
        )
        assert res_g2.status_code in (403, 404), f"Expected 403 or 404, got {res_g2.status_code}: {res_g2.text}"
        session.refresh(lead_1)
        assert lead_1.name != "Hacker Edit Full", "Unauthorized request mutated database name!"
        assert lead_1.company_id == 4, "Unauthorized request mutated company_id!"
        print(f"  ✓ Cross-company unassigned full-update rejected with HTTP {res_g2.status_code}; DB unmutated.")

    finally:
        nda_patch.stop()
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()
        print("\n[TRANSACTION ROLLBACK] Test database transaction rolled back successfully.")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO H: Zero Operational Database Mutations Assertion
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[SCENARIO H] Verifying Operational DB Row Counts (Zero Mutations Assertion)...")
    post_db = SessionLocal()
    all_matched = True
    for tbl in tables_to_audit:
        post_cnt = post_db.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
        pre_cnt = pre_counts[tbl]
        match = (post_cnt == pre_cnt)
        status = "MATCHED (PRISTINE)" if match else f"MISMATCH! (pre={pre_cnt}, post={post_cnt})"
        print(f"  {tbl:<30}: before={pre_cnt:>5}, after={post_cnt:>5} -> {status}")
        if not match:
            all_matched = False
    post_db.close()

    assert all_matched, "FATAL: Operational database mutated during test execution!"
    print("\n" + "=" * 80)
    print("ALL 7 PHASE 2R-3E LEAD COMPANY TRANSFER GUARD SCENARIOS PASSED PERFECTLY!")
    print("=" * 80)
    print("[SUCCESS] Operational database is 100% UNMUTATED and PRISTINE.\n")


if __name__ == "__main__":
    test_stage2b_phase2r3e_company_transfer_guard()
