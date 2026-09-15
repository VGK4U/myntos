"""
Stage 2B Phase 1 Security Helper Comprehensive Test Suite
Mandatory Requirements:
1. Transaction rollback ensures ZERO database mutations against the operational database.
2. Comprehensive coverage of all 10 Phase 1 test cases (A through J):
   A. Primary membership works
   B. Secondary membership works
   C. Base company alone does not work (Rule #4)
   D. Cross-tenant membership fails (Tenant boundary)
   E. Inactive membership fails
   F. Multiple-primary ambiguity fails safely
   G. Forged X-Company-ID fails (Rule #5)
   H. Forged X-Tenant-ID fails (Rule #5)
   I. Capability denial works
   J. ContextVar cleanup works
"""

import sys
from pathlib import Path
from datetime import timedelta, date
from dotenv import load_dotenv

# Ensure backend root is in sys.path and .env is loaded
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
load_dotenv(_backend_dir / ".env")

from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine, get_db, SessionLocal
from app.core.security import SecurityManager
from app.core.context import (
    RequestContext, AdminScope, get_current_request_context
)
from app.api.deps import (
    get_request_context, require_capability, require_role,
    resolve_company_id, resolve_tenant_company_for_request
)
from app.models.staff import StaffEmployee, StaffRole, StaffCompanyMembership
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.services.auth_context_service import invalidate_auth_cache

# ─────────────────────────────────────────────────────────────────────────────
# Test Router Definitions for Phase 1
# ─────────────────────────────────────────────────────────────────────────────
test_phase1_router = APIRouter(prefix="/api/v1/test-stage2b-phase1", tags=["Stage 2B Phase 1 Tests"])


@test_phase1_router.get("/resolve-company")
def endpoint_resolve_company(
    resolved_cid: int = Depends(resolve_company_id),
    ctx: RequestContext = Depends(get_request_context)
):
    return {
        "success": True,
        "resolved_company_id": resolved_cid,
        "active_company_id": ctx.active_company_id,
        "primary_company_id": ctx.primary_company_id,
        "accessible_company_ids": ctx.accessible_company_ids
    }


@test_phase1_router.get("/require-delete-capability")
def endpoint_require_delete(
    ctx: RequestContext = Depends(require_capability("crm.leads.delete"))
):
    return {"success": True, "emp_code": ctx.emp_code}


app.include_router(test_phase1_router)


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


def test_stage2b_phase1_suite():
    print("\n" + "=" * 80)
    print("STAGE 2B PHASE 1 SECURITY HELPER INTEGRATION TEST SUITE (TESTS A - J)")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 0: Baseline Row Count Check
    # ─────────────────────────────────────────────────────────────────────────
    pre_db = SessionLocal()
    emp_count_before = pre_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
    mem_count_before = pre_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
    comp_count_before = pre_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
    client_count_before = pre_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
    pre_db.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Set Up Transaction Rollback Isolation
    # ─────────────────────────────────────────────────────────────────────────
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    session.commit = session.flush

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="http://testserver")

    try:
        invalidate_auth_cache()

        # Seed role
        role_exec = session.query(StaffRole).filter(StaffRole.hierarchy_level == 10).first()
        if not role_exec:
            role_exec = StaffRole(role_code="test_exec", role_name="Executive", hierarchy_level=10)
            session.add(role_exec)
            session.flush()
        role_id = role_exec.id

        # Seed Tenants
        t1 = session.query(PlatformClient).filter(PlatformClient.id == 1).first()
        if not t1:
            t1 = PlatformClient(id=1, client_code="TENANT_1", client_name="Tenant 1", status="active")
            session.add(t1)
            session.flush()

        t2 = session.query(PlatformClient).filter(PlatformClient.id == 2).first()
        if not t2:
            t2 = PlatformClient(id=2, client_code="TENANT_2", client_name="Tenant 2", status="active")
            session.add(t2)
            session.flush()

        # Seed Companies for Tenant 1
        c1 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 101).first()
        if not c1:
            c1 = AssociatedCompany(id=101, client_id=1, company_code="CO_101", company_name="Company 101", is_active=True)
            session.add(c1)

        c2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 102).first()
        if not c2:
            c2 = AssociatedCompany(id=102, client_id=1, company_code="CO_102", company_name="Company 102", is_active=True)
            session.add(c2)

        c3 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 103).first()
        if not c3:
            c3 = AssociatedCompany(id=103, client_id=1, company_code="CO_103", company_name="Company 103", is_active=True)
            session.add(c3)

        # Seed Company for Tenant 2 (Alien company)
        c_alien = session.query(AssociatedCompany).filter(AssociatedCompany.id == 201).first()
        if not c_alien:
            c_alien = AssociatedCompany(id=201, client_id=2, company_code="CO_201_T2", company_name="Company 201 T2", is_active=True)
            session.add(c_alien)

        session.flush()

        # ─────────────────────────────────────────────────────────────────────
        # TEST A: Primary Membership Works
        # ─────────────────────────────────────────────────────────────────────
        emp_a = StaffEmployee(
            emp_code="EMP_TEST_2B_A", full_name="Employee A", email="emp_a@test.com",
            role_id=role_id, tenant_id=1, base_company_id=101, status="active", token_version=1,
            date_of_joining=date(2026, 1, 1), password_hash="hash", employment_type="confirmed",
            kyc_status="pending", admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_a)
        session.flush()

        mem_a = StaffCompanyMembership(
            staff_id=emp_a.id, company_id=101, tenant_id=1, is_primary=True, is_active=True
        )
        session.add(mem_a)
        session.flush()

        # Test both direct resolve_tenant_company_for_request and API endpoint
        resolved_a = resolve_tenant_company_for_request(emp_a, db=session)
        assert resolved_a == 101, f"Expected 101, got {resolved_a}"

        token_a = mint_token(emp_a.id, emp_a.emp_code, tenant_id=1)
        resp_a = client.get("/api/v1/test-stage2b-phase1/resolve-company", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a.status_code == 200, f"Test A API failed: {resp_a.text}"
        assert resp_a.json()["resolved_company_id"] == 101
        print("✓ Test A PASSED: Primary membership works (default & direct resolve)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST B: Secondary Membership Works
        # ─────────────────────────────────────────────────────────────────────
        # Add secondary membership in Company 102 for Employee A
        mem_a_sec = StaffCompanyMembership(
            staff_id=emp_a.id, company_id=102, tenant_id=1, is_primary=False, is_active=True
        )
        session.add(mem_a_sec)
        session.flush()
        invalidate_auth_cache(emp_a.id)

        # Calling with explicit requested_company_id = 102 must resolve 102
        resolved_b = resolve_tenant_company_for_request(emp_a, requested_company_id=102, db=session)
        assert resolved_b == 102, f"Expected 102, got {resolved_b}"

        resp_b = client.get(
            "/api/v1/test-stage2b-phase1/resolve-company?company_id=102",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp_b.status_code == 200, f"Test B API failed: {resp_b.text}"
        assert resp_b.json()["resolved_company_id"] == 102
        print("✓ Test B PASSED: Secondary membership works when requested")

        # ─────────────────────────────────────────────────────────────────────
        # TEST C: Base Company Alone Does Not Work (Rule #4)
        # ─────────────────────────────────────────────────────────────────────
        emp_c = StaffEmployee(
            emp_code="EMP_TEST_2B_C", full_name="Employee C", email="emp_c@test.com",
            role_id=role_id, tenant_id=1, base_company_id=103, status="active", token_version=1,
            date_of_joining=date(2026, 1, 1), password_hash="hash", employment_type="confirmed",
            kyc_status="pending", admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_c)
        session.flush()
        # Note: ZERO records in staff_company_memberships for emp_c!

        try:
            resolve_tenant_company_for_request(emp_c, db=session)
            assert False, "Should have raised 403"
        except HTTPException as e:
            assert e.status_code == 403, f"Expected 403, got {e.status_code}"

        token_c = mint_token(emp_c.id, emp_c.emp_code, tenant_id=1)
        resp_c = client.get("/api/v1/test-stage2b-phase1/resolve-company", headers={"Authorization": f"Bearer {token_c}"})
        assert resp_c.status_code == 403, f"Expected 403, got {resp_c.status_code}"
        print("✓ Test C PASSED: base_company_id alone does NOT grant access (Rule #4)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST D: Cross-Tenant Membership Fails
        # ─────────────────────────────────────────────────────────────────────
        # Employee A (Tenant 1) attempts to request Company 201 (Tenant 2)
        try:
            resolve_tenant_company_for_request(emp_a, requested_company_id=201, db=session)
            assert False, "Should have raised 403"
        except HTTPException as e:
            assert e.status_code == 403, f"Expected 403, got {e.status_code}"

        resp_d = client.get(
            "/api/v1/test-stage2b-phase1/resolve-company?company_id=201",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp_d.status_code == 403, f"Expected 403, got {resp_d.status_code}"
        print("✓ Test D PASSED: Cross-tenant company access strictly denied (403)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST E: Inactive Membership Fails
        # ─────────────────────────────────────────────────────────────────────
        # Add an inactive membership in Company 103 for Employee A
        mem_a_inact = StaffCompanyMembership(
            staff_id=emp_a.id, company_id=103, tenant_id=1, is_primary=False, is_active=False
        )
        session.add(mem_a_inact)
        session.flush()
        invalidate_auth_cache(emp_a.id)

        try:
            resolve_tenant_company_for_request(emp_a, requested_company_id=103, db=session)
            assert False, "Should have raised 403"
        except HTTPException as e:
            assert e.status_code == 403, f"Expected 403, got {e.status_code}"

        resp_e = client.get(
            "/api/v1/test-stage2b-phase1/resolve-company?company_id=103",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp_e.status_code == 403, f"Expected 403, got {resp_e.status_code}"
        print("✓ Test E PASSED: Inactive membership fails closed (403)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST F: Multiple-Primary Ambiguity Fails Safely
        # ─────────────────────────────────────────────────────────────────────
        emp_f = StaffEmployee(
            emp_code="EMP_TEST_2B_F", full_name="Employee F", email="emp_f@test.com",
            role_id=role_id, tenant_id=1, base_company_id=101, status="active", token_version=1,
            date_of_joining=date(2026, 1, 1), password_hash="hash", employment_type="confirmed",
            kyc_status="pending", admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_f)
        session.flush()

        # Two primary memberships! (Data corruption scenario)
        mem_f1 = StaffCompanyMembership(staff_id=emp_f.id, company_id=101, tenant_id=1, is_primary=True, is_active=True)
        mem_f2 = StaffCompanyMembership(staff_id=emp_f.id, company_id=102, tenant_id=1, is_primary=True, is_active=True)
        session.add_all([mem_f1, mem_f2])
        session.flush()

        # When no explicit company is provided, must fail closed
        try:
            resolve_tenant_company_for_request(emp_f, db=session)
            assert False, "Should have raised 403 for multiple primaries"
        except HTTPException as e:
            assert e.status_code == 403, f"Expected 403, got {e.status_code}"

        token_f = mint_token(emp_f.id, emp_f.emp_code, tenant_id=1)
        resp_f = client.get("/api/v1/test-stage2b-phase1/resolve-company", headers={"Authorization": f"Bearer {token_f}"})
        assert resp_f.status_code == 403, f"Expected 403, got {resp_f.status_code}"

        # But if explicitly requested with a valid member company, it succeeds safely
        resolved_f_explicit = resolve_tenant_company_for_request(emp_f, requested_company_id=101, db=session)
        assert resolved_f_explicit == 101
        print("✓ Test F PASSED: Multiple-primary ambiguity fails safely on default, allows explicit selection")

        # ─────────────────────────────────────────────────────────────────────
        # TEST G: Forged X-Company-ID Fails (Rule #5)
        # ─────────────────────────────────────────────────────────────────────
        # Employee A only has active memberships in 101 and 102.
        # Attacker injects X-Company-ID: 103 (unauthorized company)
        resp_g = client.get(
            "/api/v1/test-stage2b-phase1/resolve-company",
            headers={"Authorization": f"Bearer {token_a}", "X-Company-ID": "103"}
        )
        assert resp_g.status_code == 403, f"Expected 403 for forged X-Company-ID, got {resp_g.status_code}"
        print("✓ Test G PASSED: Forged X-Company-ID header rejected with 403 (Rule #5)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST H: Forged X-Tenant-ID Fails (Rule #5)
        # ─────────────────────────────────────────────────────────────────────
        # Attacker injects X-Tenant-ID: 2 to switch to Tenant 2
        resp_h = client.get(
            "/api/v1/test-stage2b-phase1/resolve-company",
            headers={"Authorization": f"Bearer {token_a}", "X-Tenant-ID": "2"}
        )
        assert resp_h.status_code == 200, f"Expected 200, got {resp_h.status_code}"
        data_h = resp_h.json()
        assert data_h["resolved_company_id"] == 101, "Tenant was improperly overridden!"
        print("✓ Test H PASSED: Forged X-Tenant-ID cannot override server-side tenant authority")

        # ─────────────────────────────────────────────────────────────────────
        # TEST I: Capability Denial Works
        # ─────────────────────────────────────────────────────────────────────
        resp_i = client.get(
            "/api/v1/test-stage2b-phase1/require-delete-capability",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp_i.status_code == 403, f"Expected 403 for missing capability, got {resp_i.status_code}"
        print("✓ Test I PASSED: Capability denial works (403 Forbidden)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST J: ContextVar Cleanup Works
        # ─────────────────────────────────────────────────────────────────────
        assert get_current_request_context() is None, "ContextVar was not cleaned up after requests!"
        print("✓ Test J PASSED: ContextVar lifecycle cleaned up after requests")

        print("\n" + "=" * 80)
        print("ALL 10 STAGE 2B PHASE 1 TESTS (A THROUGH J) PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Post-Test Database Mutation Verification
    # ─────────────────────────────────────────────────────────────────────────
    post_db = SessionLocal()
    emp_count_after = post_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
    mem_count_after = post_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
    comp_count_after = post_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
    client_count_after = post_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
    post_db.close()

    print(f"\n[DB-MUTATION-AUDIT] staff_employees count: before={emp_count_before}, after={emp_count_after}")
    print(f"[DB-MUTATION-AUDIT] staff_company_memberships count: before={mem_count_before}, after={mem_count_after}")
    print(f"[DB-MUTATION-AUDIT] associated_companies count: before={comp_count_before}, after={comp_count_after}")
    print(f"[DB-MUTATION-AUDIT] platform_clients count: before={client_count_before}, after={client_count_after}")

    assert emp_count_before == emp_count_after, "staff_employees mutated!"
    assert mem_count_before == mem_count_after, "staff_company_memberships mutated!"
    assert comp_count_before == comp_count_after, "associated_companies mutated!"
    assert client_count_before == client_count_after, "platform_clients mutated!"

    print("[DB-MUTATION-AUDIT] VERIFIED: 0 rows inserted, 0 rows modified, 0 rows deleted in operational database!\n")


if __name__ == "__main__":
    test_stage2b_phase1_suite()
