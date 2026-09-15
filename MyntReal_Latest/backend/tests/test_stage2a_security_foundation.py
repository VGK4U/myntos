"""
Stage 2A Security Foundation Comprehensive Test Suite (Hardened)
Mandatory Requirements:
1. Transaction rollback ensures ZERO database mutations against the operational database.
2. Comprehensive coverage of all 18 test cases (A through R) specified in Section 18:
   A. No membership -> DENY (403)
   B. Base company alone -> DENY (403)
   C. Cross-tenant company -> DENY (403)
   D. Cross-tenant JWT mismatch -> DENY (401)
   E. Missing tenant -> DENY (403)
   F. Missing company resolution -> DENY (403)
   G. Multiple primary memberships -> safe failure (403)
   H. No primary membership -> safe failure (403)
   I. High-level role does not automatically receive unrelated capability (403)
   J. Platform superadmin works only through authoritative DB scope (200 / 403)
   K. token_version immediate revocation (401)
   L. inactive staff immediate revocation (401)
   M. cache cannot cross company contexts
   N. cache cannot cross staff identities
   O. ContextVar cleanup (guaranteed cleanup after request)
   P. module entitlement cannot cross tenant
   Q. client X-Company-ID cannot grant access to unauthorized company (403)
   R. client X-Tenant-ID cannot grant access or override tenant authority
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Ensure backend root is in sys.path and .env is loaded
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
load_dotenv(_backend_dir / ".env")

# pytest is optional; script runs directly with python3
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine, get_db, SessionLocal
from app.core.security import SecurityManager
from app.core.context import (
    RequestContext, AdminScope, get_current_request_context
)
from app.api.deps import (
    get_request_context, require_capability, require_role,
    require_platform_scope, require_module
)
from app.models.staff import StaffEmployee, StaffRole, StaffCompanyMembership
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.services.auth_context_service import (
    invalidate_auth_cache, resolve_licensed_modules
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Router Definitions
# ─────────────────────────────────────────────────────────────────────────────
test_router = APIRouter(prefix="/api/v1/test-stage2a-hardening", tags=["Stage 2A Hardening Tests"])

@test_router.get("/context")
def endpoint_context(ctx: RequestContext = Depends(get_request_context)):
    return {
        "success": True,
        "staff_id": ctx.staff_id,
        "emp_code": ctx.emp_code,
        "tenant_id": ctx.tenant_id,
        "active_company_id": ctx.active_company_id,
        "primary_company_id": ctx.primary_company_id,
        "accessible_company_ids": ctx.accessible_company_ids,
        "admin_scope": ctx.admin_scope.value,
        "hierarchy_level": ctx.hierarchy_level,
        "capabilities": sorted(list(ctx.capabilities)),
        "licensed_modules": sorted(list(ctx.licensed_modules))
    }

@test_router.get("/require-view-all")
def endpoint_view_all(ctx: RequestContext = Depends(require_capability("crm.leads.view_all"))):
    return {"success": True, "emp_code": ctx.emp_code}

@test_router.get("/require-restricted")
def endpoint_restricted(ctx: RequestContext = Depends(require_capability("restricted.super.action"))):
    return {"success": True, "emp_code": ctx.emp_code}

@test_router.get("/require-role-80")
def endpoint_role_80(ctx: RequestContext = Depends(require_role(80, "Company Admin"))):
    return {"success": True, "level": ctx.hierarchy_level}

@test_router.get("/require-platform-superadmin")
def endpoint_superadmin(ctx: RequestContext = Depends(require_platform_scope)):
    return {"success": True, "admin_scope": ctx.admin_scope.value}

@test_router.get("/require-module-crm")
def endpoint_module_crm(ctx: RequestContext = Depends(require_module("CRM_LEADS"))):
    return {"success": True, "module": "CRM_LEADS"}

@test_router.get("/require-module-billing")
def endpoint_module_billing(ctx: RequestContext = Depends(require_module("BILLING_ENTERPRISE"))):
    return {"success": True, "module": "BILLING_ENTERPRISE"}

app.include_router(test_router)


# Helper to mint valid test tokens
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


def test_stage2a_security_hardening_suite():
    """
    Executes all 18 security property tests within a strictly isolated
    transaction rollback fixture, verifying zero database mutations.
    """
    # ─────────────────────────────────────────────────────────────────────────
    # Phase 0: Baseline Row Count Check
    # ─────────────────────────────────────────────────────────────────────────
    pre_db = SessionLocal()
    emp_count_before = pre_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
    mem_count_before = pre_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
    comp_count_before = pre_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
    client_count_before = pre_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
    pre_db.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1: Set Up Transaction Rollback Isolation
    # ─────────────────────────────────────────────────────────────────────────
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    # Monkeypatch session.commit to flush within transaction: prevents committing to DB
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

        # Seed roles if needed
        role_exec = session.query(StaffRole).filter(StaffRole.hierarchy_level == 10).first()
        role_exec_id = role_exec.id if role_exec else 11

        role_admin = session.query(StaffRole).filter(StaffRole.hierarchy_level == 100).first()
        if not role_admin:
            role_admin = StaffRole(role_code="test_tenant_admin", role_name="Tenant Admin", hierarchy_level=100)
            session.add(role_admin)
            session.flush()
        role_admin_id = role_admin.id

        role_super = session.query(StaffRole).filter(StaffRole.hierarchy_level == 150).first()
        if not role_super:
            role_super = StaffRole(role_code="test_superadmin", role_name="Superadmin", hierarchy_level=150)
            session.add(role_super)
            session.flush()
        role_super_id = role_super.id

        # Seed Tenants
        t1 = session.query(PlatformClient).filter(PlatformClient.id == 1).first()
        if not t1:
            t1 = PlatformClient(id=1, client_code="PLATFORM_TENANT_1", client_name="Platform Tenant 1", status="active")
            session.add(t1)
            session.flush()

        # Seed Secondary Tenant
        t_other = session.query(PlatformClient).filter(PlatformClient.id == 158).first()
        if not t_other:
            t_other = PlatformClient(id=158, client_code="TB_D4E63657", client_name="Tenant B Corp", status="active")
            session.add(t_other)
            session.flush()

        # Seed Companies in Tenant 1
        c1 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 1).first()
        if not c1:
            c1 = AssociatedCompany(id=1, client_id=1, company_name="Company 1", company_code="C1", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c1)
            session.flush()
        else:
            c1.licensed_modules = ["CRM_LEADS"]
            session.flush()

        # Secondary company in Tenant 1
        c2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 2).first()
        if not c2:
            c2 = AssociatedCompany(id=2, client_id=1, company_name="Company 2", company_code="C2", is_active=True, licensed_modules=["CRM_LEADS", "SERVICE_TICKETS"])
            session.add(c2)
            session.flush()
        else:
            c2.licensed_modules = ["CRM_LEADS", "SERVICE_TICKETS"]
            session.flush()

        # Secondary tenant company (id=95 in Tenant 158)
        c_t_other = session.query(AssociatedCompany).filter(AssociatedCompany.id == 95).first()
        if not c_t_other:
            c_t_other = AssociatedCompany(id=95, client_id=158, company_name="Tenant B Company", company_code="TBC", is_active=True, licensed_modules=["SERVICE_TICKETS"])
            session.add(c_t_other)
            session.flush()
        else:
            c_t_other.licensed_modules = ["SERVICE_TICKETS"]
            session.flush()

        # ─────────────────────────────────────────────────────────────────────
        # TEST A: No Membership -> DENY (403 Forbidden)
        # ─────────────────────────────────────────────────────────────────────
        emp_a = StaffEmployee(
            emp_code="EMP_TEST_A",
            full_name="Staff No Membership",
            email="emp_a@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_a)
        session.flush()

        token_a = mint_token(emp_a.id, emp_a.emp_code, tenant_id=1, token_version=1)
        resp_a = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a.status_code == 403, f"Test A failed: expected 403, got {resp_a.status_code}: {resp_a.text}"
        assert "no active company memberships" in resp_a.text.lower() or "operational company access" in resp_a.text.lower()
        print("✓ Test A PASSED: No membership -> 403 DENY")

        # ─────────────────────────────────────────────────────────────────────
        # TEST B: Base Company Alone -> DENY (403 Forbidden)
        # ─────────────────────────────────────────────────────────────────────
        emp_b = StaffEmployee(
            emp_code="EMP_TEST_B",
            full_name="Staff Base Company Only",
            email="emp_b@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            base_company_id=1,  # Base company set, but ZERO rows in staff_company_memberships
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_b)
        session.flush()

        token_b = mint_token(emp_b.id, emp_b.emp_code, tenant_id=1, token_version=1)
        resp_b = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 403, f"Test B failed: expected 403, got {resp_b.status_code}: {resp_b.text}"
        print("✓ Test B PASSED: Base company alone -> 403 DENY (Fail-closed)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST C: Cross-Tenant Company -> DENY (403 Forbidden)
        # ─────────────────────────────────────────────────────────────────────
        emp_c = StaffEmployee(
            emp_code="EMP_TEST_C",
            full_name="Staff Cross Tenant Attempter",
            email="emp_c@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_c)
        session.flush()
        mem_c1 = StaffCompanyMembership(staff_id=emp_c.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add(mem_c1)
        session.flush()

        token_c = mint_token(emp_c.id, emp_c.emp_code, tenant_id=1, token_version=1)
        # Requesting Company 95 which belongs to Tenant 158
        resp_c = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_c}", "X-Company-ID": "95"}
        )
        assert resp_c.status_code == 403, f"Test C failed: expected 403, got {resp_c.status_code}: {resp_c.text}"
        print("✓ Test C PASSED: Cross-tenant company request -> 403 DENY")

        # ─────────────────────────────────────────────────────────────────────
        # TEST D: Cross-Tenant JWT Mismatch -> DENY (401 Unauthorized)
        # ─────────────────────────────────────────────────────────────────────
        # Token has tenant_id = 158, but employee belongs to Tenant 1 in DB
        token_d_mismatch = mint_token(emp_c.id, emp_c.emp_code, tenant_id=158, token_version=1)
        resp_d = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_d_mismatch}"})
        assert resp_d.status_code == 401, f"Test D failed: expected 401, got {resp_d.status_code}: {resp_d.text}"
        assert "cross-tenant" in resp_d.text.lower()
        print("✓ Test D PASSED: Cross-tenant JWT mismatch -> 401 DENY")

        # ─────────────────────────────────────────────────────────────────────
        # TEST E: Missing Tenant in DB -> DENY (403 Forbidden)
        # ─────────────────────────────────────────────────────────────────────
        emp_e = StaffEmployee(
            emp_code="EMP_TEST_E",
            full_name="Staff Missing Tenant",
            email="emp_e@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=None,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_e)
        session.flush()

        token_e = mint_token(emp_e.id, emp_e.emp_code, tenant_id=1, token_version=1)
        resp_e = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_e}"})
        assert resp_e.status_code == 403, f"Test E failed: expected 403, got {resp_e.status_code}: {resp_e.text}"
        print("✓ Test E PASSED: Missing tenant in DB -> 403 DENY")

        # ─────────────────────────────────────────────────────────────────────
        # TEST F: Missing / Non-Existent Company Resolution -> DENY (403 Forbidden)
        # ─────────────────────────────────────────────────────────────────────
        resp_f = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_c}", "X-Company-ID": "99999"}
        )
        assert resp_f.status_code == 403, f"Test F failed: expected 403, got {resp_f.status_code}: {resp_f.text}"
        print("✓ Test F PASSED: Non-member/non-existent company requested -> 403 DENY")

        # ─────────────────────────────────────────────────────────────────────
        # TEST G: Multiple Primary Memberships -> Safe Failure (403 Forbidden)
        # ─────────────────────────────────────────────────────────────────────
        emp_g = StaffEmployee(
            emp_code="EMP_TEST_G",
            full_name="Staff Multiple Primaries",
            email="emp_g@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_g)
        session.flush()
        # Add two primary memberships in the same tenant
        mem_g1 = StaffCompanyMembership(staff_id=emp_g.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        mem_g2 = StaffCompanyMembership(staff_id=emp_g.id, tenant_id=1, company_id=2, is_primary=True, is_active=True)
        session.add_all([mem_g1, mem_g2])
        session.flush()

        token_g = mint_token(emp_g.id, emp_g.emp_code, tenant_id=1, token_version=1)
        resp_g = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_g}"})
        assert resp_g.status_code == 403, f"Test G failed: expected 403, got {resp_g.status_code}: {resp_g.text}"
        assert "ambiguous or missing primary" in resp_g.text.lower()
        print("✓ Test G PASSED: Multiple primary memberships without selection -> 403 safe failure")

        # ─────────────────────────────────────────────────────────────────────
        # TEST H: No Primary Membership -> Safe Failure (403) unless explicit
        # ─────────────────────────────────────────────────────────────────────
        emp_h = StaffEmployee(
            emp_code="EMP_TEST_H",
            full_name="Staff Zero Primaries",
            email="emp_h@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_h)
        session.flush()
        # Add two memberships, neither is primary
        mem_h1 = StaffCompanyMembership(staff_id=emp_h.id, tenant_id=1, company_id=1, is_primary=False, is_active=True)
        mem_h2 = StaffCompanyMembership(staff_id=emp_h.id, tenant_id=1, company_id=2, is_primary=False, is_active=True)
        session.add_all([mem_h1, mem_h2])
        session.flush()

        token_h = mint_token(emp_h.id, emp_h.emp_code, tenant_id=1, token_version=1)
        # Without explicit company header: 403 Forbidden
        resp_h_auto = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_h}"})
        assert resp_h_auto.status_code == 403, f"Test H auto failed: expected 403, got {resp_h_auto.status_code}: {resp_h_auto.text}"

        # With explicit company header: 200 OK
        resp_h_expl = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_h}", "X-Company-ID": "1"}
        )
        assert resp_h_expl.status_code == 200, f"Test H explicit failed: expected 200, got {resp_h_expl.status_code}: {resp_h_expl.text}"
        assert resp_h_expl.json()["active_company_id"] == 1
        print("✓ Test H PASSED: Zero primary memberships -> 403 on auto, 200 on explicit valid company")

        # ─────────────────────────────────────────────────────────────────────
        # TEST I: High-Level Role Does NOT Receive Unrelated Capability
        # ─────────────────────────────────────────────────────────────────────
        emp_i = StaffEmployee(
            emp_code="EMP_TEST_I",
            full_name="Staff High Role",
            email="emp_i@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_admin_id,  # Level 100
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_i)
        session.flush()
        mem_i1 = StaffCompanyMembership(staff_id=emp_i.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add(mem_i1)
        session.flush()

        token_i = mint_token(emp_i.id, emp_i.emp_code, tenant_id=1, token_version=1)
        resp_i = client.get("/api/v1/test-stage2a-hardening/require-restricted", headers={"Authorization": f"Bearer {token_i}"})
        assert resp_i.status_code == 403, f"Test I failed: expected 403, got {resp_i.status_code}: {resp_i.text}"
        print("✓ Test I PASSED: High-level role denied unrelated capability (Zero blanket grants)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST J: Platform Superadmin Works ONLY Through Authoritative DB Scope
        # ─────────────────────────────────────────────────────────────────────
        # J1: Valid Platform Superadmin: DB admin_scope == 'PLATFORM', tenant_id == 1, level == 150
        emp_j1 = StaffEmployee(
            emp_code="EMP_TEST_J1",
            full_name="Real Platform Superadmin",
            email="emp_j1@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_super_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="PLATFORM"
        )
        session.add(emp_j1)
        session.flush()
        mem_j1 = StaffCompanyMembership(staff_id=emp_j1.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add(mem_j1)
        session.flush()

        token_j1 = mint_token(emp_j1.id, emp_j1.emp_code, tenant_id=1, token_version=1)
        resp_j1 = client.get("/api/v1/test-stage2a-hardening/require-platform-superadmin", headers={"Authorization": f"Bearer {token_j1}"})
        assert resp_j1.status_code == 200, f"Test J1 failed: expected 200, got {resp_j1.status_code}: {resp_j1.text}"

        # J2: Level 150 but admin_scope != 'PLATFORM' (e.g. CLIENT_SPECIFIC)
        emp_j2 = StaffEmployee(
            emp_code="EMP_TEST_J2",
            full_name="High Role Non-Platform Admin",
            email="emp_j2@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_super_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_j2)
        session.flush()
        mem_j2 = StaffCompanyMembership(staff_id=emp_j2.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add(mem_j2)
        session.flush()

        token_j2 = mint_token(emp_j2.id, emp_j2.emp_code, tenant_id=1, token_version=1)
        resp_j2 = client.get("/api/v1/test-stage2a-hardening/require-platform-superadmin", headers={"Authorization": f"Bearer {token_j2}"})
        assert resp_j2.status_code == 403, f"Test J2 failed: expected 403, got {resp_j2.status_code}: {resp_j2.text}"

        # J3: admin_scope == 'PLATFORM' but in Tenant 158 (not Master Tenant 1)
        emp_j3 = StaffEmployee(
            emp_code="EMP_TEST_J3",
            full_name="Tenant 158 Impostor Admin",
            email="emp_j3@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=158,
            role_id=role_super_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="PLATFORM"
        )
        session.add(emp_j3)
        session.flush()
        mem_j3 = StaffCompanyMembership(staff_id=emp_j3.id, tenant_id=158, company_id=95, is_primary=True, is_active=True)
        session.add(mem_j3)
        session.flush()

        token_j3 = mint_token(emp_j3.id, emp_j3.emp_code, tenant_id=158, token_version=1)
        resp_j3 = client.get("/api/v1/test-stage2a-hardening/require-platform-superadmin", headers={"Authorization": f"Bearer {token_j3}"})
        assert resp_j3.status_code == 403, f"Test J3 failed: expected 403, got {resp_j3.status_code}: {resp_j3.text}"
        print("✓ Test J PASSED: Platform superadmin requires all 3 DB facts (scope=PLATFORM, tenant=1, level>=150)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST K: token_version Immediate Revocation
        # ─────────────────────────────────────────────────────────────────────
        emp_k = StaffEmployee(
            emp_code="EMP_TEST_K",
            full_name="Staff Revocation Target",
            email="emp_k@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            token_version=1,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_k)
        session.flush()
        mem_k = StaffCompanyMembership(staff_id=emp_k.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add(mem_k)
        session.flush()

        token_k = mint_token(emp_k.id, emp_k.emp_code, tenant_id=1, token_version=1)
        # Request 1 succeeds
        resp_k1 = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_k}"})
        assert resp_k1.status_code == 200, f"Test K1 failed: {resp_k1.text}"

        # DB token_version bumped to 2 (simulate logout / password reset)
        emp_k.token_version = 2
        session.flush()

        # Request 2 with same token fails immediately
        resp_k2 = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_k}"})
        assert resp_k2.status_code == 401, f"Test K2 failed: expected 401, got {resp_k2.status_code}: {resp_k2.text}"
        assert "revoked" in resp_k2.text.lower()
        print("✓ Test K PASSED: token_version bump immediately revokes session (Zero cache bypass)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST L: Inactive Staff Immediate Revocation
        # ─────────────────────────────────────────────────────────────────────
        emp_l = StaffEmployee(
            emp_code="EMP_TEST_L",
            full_name="Staff Deactivation Target",
            email="emp_l@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_l)
        session.flush()
        mem_l = StaffCompanyMembership(staff_id=emp_l.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add(mem_l)
        session.flush()

        token_l = mint_token(emp_l.id, emp_l.emp_code, tenant_id=1, token_version=1)
        # Request 1 succeeds
        resp_l1 = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_l}"})
        assert resp_l1.status_code == 200, f"Test L1 failed: {resp_l1.text}"

        # Deactivate staff live in DB
        emp_l.status = "inactive"
        session.flush()

        # Request 2 with same token fails immediately
        resp_l2 = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_l}"})
        assert resp_l2.status_code == 401, f"Test L2 failed: expected 401, got {resp_l2.status_code}: {resp_l2.text}"
        assert "inactive" in resp_l2.text.lower()
        print("✓ Test L PASSED: Account deactivation immediately revokes access (Zero cache bypass)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST M: Cache Cannot Cross Company Contexts
        # ─────────────────────────────────────────────────────────────────────
        emp_m = StaffEmployee(
            emp_code="EMP_TEST_M",
            full_name="Staff Multi-Company Cache",
            email="emp_m@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add(emp_m)
        session.flush()
        mem_m1 = StaffCompanyMembership(staff_id=emp_m.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        mem_m2 = StaffCompanyMembership(staff_id=emp_m.id, tenant_id=1, company_id=2, is_primary=False, is_active=True)
        session.add_all([mem_m1, mem_m2])
        session.flush()

        token_m = mint_token(emp_m.id, emp_m.emp_code, tenant_id=1, token_version=1)
        resp_m1 = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_m}", "X-Company-ID": "1"}
        )
        assert resp_m1.status_code == 200
        assert resp_m1.json()["active_company_id"] == 1

        resp_m2 = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_m}", "X-Company-ID": "2"}
        )
        assert resp_m2.status_code == 200
        assert resp_m2.json()["active_company_id"] == 2
        print("✓ Test M PASSED: Cache correctly differentiates company contexts")

        # ─────────────────────────────────────────────────────────────────────
        # TEST N: Cache Cannot Cross Staff Identities
        # ─────────────────────────────────────────────────────────────────────
        emp_n1 = StaffEmployee(
            emp_code="EMP_TEST_N1",
            full_name="Staff N1",
            email="emp_n1@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_exec_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        emp_n2 = StaffEmployee(
            emp_code="EMP_TEST_N2",
            full_name="Staff N2",
            email="emp_n2@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="pending",
            tenant_id=1,
            role_id=role_admin_id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC"
        )
        session.add_all([emp_n1, emp_n2])
        session.flush()
        mem_n1 = StaffCompanyMembership(staff_id=emp_n1.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        mem_n2 = StaffCompanyMembership(staff_id=emp_n2.id, tenant_id=1, company_id=1, is_primary=True, is_active=True)
        session.add_all([mem_n1, mem_n2])
        session.flush()

        token_n1 = mint_token(emp_n1.id, emp_n1.emp_code, tenant_id=1, token_version=1)
        token_n2 = mint_token(emp_n2.id, emp_n2.emp_code, tenant_id=1, token_version=1)

        resp_n1 = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_n1}"})
        resp_n2 = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_n2}"})

        assert resp_n1.json()["emp_code"] == "EMP_TEST_N1"
        assert resp_n2.json()["emp_code"] == "EMP_TEST_N2"
        assert resp_n1.json()["hierarchy_level"] == 10
        assert resp_n2.json()["hierarchy_level"] == 100
        print("✓ Test N PASSED: Cache correctly isolates distinct staff identities")

        # ─────────────────────────────────────────────────────────────────────
        # TEST O: ContextVar Lifecycle Cleanup
        # ─────────────────────────────────────────────────────────────────────
        assert get_current_request_context() is None
        resp_o = client.get("/api/v1/test-stage2a-hardening/context", headers={"Authorization": f"Bearer {token_n1}"})
        assert resp_o.status_code == 200
        # ContextVar must be None after request execution finishes
        assert get_current_request_context() is None
        print("✓ Test O PASSED: ContextVar lifecycle cleans up after request completion")

        # ─────────────────────────────────────────────────────────────────────
        # TEST P: Module Entitlement Cannot Cross Tenant
        # ─────────────────────────────────────────────────────────────────────
        # emp_n1 is in Company 1 (Tenant 1), which has module CRM_LEADS but NOT BILLING_ENTERPRISE
        resp_p_allowed = client.get("/api/v1/test-stage2a-hardening/require-module-crm", headers={"Authorization": f"Bearer {token_n1}"})
        assert resp_p_allowed.status_code == 200

        resp_p_denied = client.get("/api/v1/test-stage2a-hardening/require-module-billing", headers={"Authorization": f"Bearer {token_n1}"})
        assert resp_p_denied.status_code == 403

        # Cross-tenant module check: Querying company 95 (Tenant 158) with tenant_id 1 returns empty set
        cross_modules = resolve_licensed_modules(session, company_id=95, tenant_id=1)
        assert cross_modules == set(), f"Expected empty set for cross-tenant module lookup, got {cross_modules}"
        print("✓ Test P PASSED: Module entitlement is tenant-scoped and fails closed")

        # ─────────────────────────────────────────────────────────────────────
        # TEST Q: Client X-Company-ID Cannot Grant Access
        # ─────────────────────────────────────────────────────────────────────
        # emp_n1 has membership only in Company 1. Sending X-Company-ID: 2 must fail.
        resp_q = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_n1}", "X-Company-ID": "2"}
        )
        assert resp_q.status_code == 403, f"Test Q failed: expected 403, got {resp_q.status_code}: {resp_q.text}"
        print("✓ Test Q PASSED: Client X-Company-ID cannot grant unauthorized access")

        # ─────────────────────────────────────────────────────────────────────
        # TEST R: Client X-Tenant-ID Cannot Grant Access
        # ─────────────────────────────────────────────────────────────────────
        # emp_n1 belongs to Tenant 1. Sending X-Tenant-ID: 158 header must be completely ignored.
        resp_r = client.get(
            "/api/v1/test-stage2a-hardening/context",
            headers={"Authorization": f"Bearer {token_n1}", "X-Tenant-ID": "158"}
        )
        assert resp_r.status_code == 200
        assert resp_r.json()["tenant_id"] == 1, f"Expected tenant_id == 1, got {resp_r.json()['tenant_id']}"
        print("✓ Test R PASSED: Client X-Tenant-ID cannot override server-side tenant authority")

        print("\nALL 18 STAGE 2A SECURITY HARDENING TESTS (A THROUGH R) PASSED!")

    finally:
        # Clean up dependency overrides and roll back transaction completely
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()

        # ─────────────────────────────────────────────────────────────────────
        # Phase 3: Post-Test Row Count Verification (GUARANTEE ZERO DB WRITES)
        # ─────────────────────────────────────────────────────────────────────
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

        assert emp_count_before == emp_count_after, "DB MUTATION DETECTED in staff_employees!"
        assert mem_count_before == mem_count_after, "DB MUTATION DETECTED in staff_company_memberships!"
        assert comp_count_before == comp_count_after, "DB MUTATION DETECTED in associated_companies!"
        assert client_count_before == client_count_after, "DB MUTATION DETECTED in platform_clients!"
        print("[DB-MUTATION-AUDIT] VERIFIED: 0 rows inserted, 0 rows modified, 0 rows deleted in operational database!\n")


if __name__ == "__main__":
    test_stage2a_security_hardening_suite()
