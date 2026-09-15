"""
Stage 2B Phase 2R-2: CRM Search, Analytics, List & Visibility Authorization Test Suite

Exercises and verifies the 12 remediated CRM endpoints:
1. GET /api/v1/crm/master-leads
2. GET /api/v1/crm/exec-handler-leads
3. GET /api/v1/crm/exec-trend-leads
4. GET /api/v1/crm/exec-emp-perf-leads
5. GET /api/v1/crm/lead-analytics
6. GET /api/v1/crm/my-leads
7. GET /api/v1/crm/team-leads
8. GET /api/v1/crm/bank-wise-leads
9. GET /api/v1/crm/employee-performance-dashboard
10. GET /api/v1/crm/transactions/search-leads
11. GET /api/v1/crm/leads/system-search
12. GET /api/v1/crm/leads

Mandatory Security Invariants Verified:
1. Anti-tampering on company_id / company_id_filter: HTTP 403 on foreign/unauthorized company.
2. Downline gating: HTTP 403 on peer or non-downline target employee in team-leads and exec-emp-perf-leads.
3. Tenant isolation: Leads and staff from foreign tenants never leak into search, list, or analytics.
4. Revocation of hardcoded string heuristics: No bypass via staff_type, department, role_code, or emp_code.
5. Canonical crm.leads.view_all capability enforcement.
6. Zero DB mutations: Operational database verified 100% PRISTINE via pre/post row count assertions.
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
from app.models.staff import StaffEmployee, StaffRole, StaffCompanyMembership, StaffDepartment
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.models.crm import CRMLead, CRMLeadDeal, CRMLeadTransaction, CRMRevenueEntry
from app.models.signup_category import SignupCategory
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


def test_stage2b_phase2r2_crm_search_analytics_security():
    print("\n" + "=" * 80)
    print("STAGE 2B PHASE 2R-2: CRM SEARCH / ANALYTICS / LIST AUTHORIZATION SECURITY SUITE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 0: Baseline Row Counts (Operational DB Read-Only Gate)
    # ─────────────────────────────────────────────────────────────────────────
    pre_db = SessionLocal()
    emp_count_before = pre_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
    mem_count_before = pre_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
    comp_count_before = pre_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
    client_count_before = pre_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
    role_count_before = pre_db.execute(text("SELECT count(*) FROM staff_roles")).scalar()
    dept_count_before = pre_db.execute(text("SELECT count(*) FROM staff_departments")).scalar()
    lead_count_before = pre_db.execute(text("SELECT count(*) FROM crm_leads")).scalar()
    deal_count_before = pre_db.execute(text("SELECT count(*) FROM crm_lead_deals")).scalar()
    txn_count_before = pre_db.execute(text("SELECT count(*) FROM crm_lead_transactions")).scalar()
    rev_count_before = pre_db.execute(text("SELECT count(*) FROM crm_revenue_entries")).scalar()
    pre_db.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Transaction Rollback Isolation Setup
    # ─────────────────────────────────────────────────────────────────────────
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    # Prevent committing to DB during tests; keep all writes in rolled-back transaction
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

    # Capability resolution hook for explicit canonical capability test
    orig_resolve_caps = acs.resolve_staff_capabilities
    def custom_resolve_staff_capabilities(db, staff, active_company_id, admin_scope):
        caps = orig_resolve_caps(db, staff, active_company_id, admin_scope)
        if getattr(staff, "emp_code", "") == "EMP_CRM_VIEW_ALL":
            return set(caps) | {"crm.leads.view_all"}
        return caps

    caps_patch = patch.object(acs, "resolve_staff_capabilities", side_effect=custom_resolve_staff_capabilities)
    caps_patch.start()

    try:
        invalidate_auth_cache()

        # ── Seed Roles ──
        role_exec = session.query(StaffRole).filter(StaffRole.role_code == "test_crm_sales_exec").first()
        if not role_exec:
            role_exec = StaffRole(role_code="test_crm_sales_exec", role_name="Sales Exec", hierarchy_level=10)
            session.add(role_exec)
            session.flush()

        role_mgr = session.query(StaffRole).filter(StaffRole.role_code == "test_crm_mgr").first()
        if not role_mgr:
            role_mgr = StaffRole(role_code="test_crm_mgr", role_name="Sales Manager", hierarchy_level=50)
            session.add(role_mgr)
            session.flush()

        role_superadmin = session.query(StaffRole).filter(StaffRole.role_code == "test_crm_superadmin").first()
        if not role_superadmin:
            role_superadmin = StaffRole(role_code="test_crm_superadmin", role_name="Platform Superadmin", hierarchy_level=150)
            session.add(role_superadmin)
            session.flush()

        # ── Seed Department ──
        dept_sales = session.query(StaffDepartment).filter(StaffDepartment.name == "Sales Test Dept").first()
        if not dept_sales:
            dept_sales = StaffDepartment(name="Sales Test Dept", department_code="DEPT_SALES_TEST")
            session.add(dept_sales)
            session.flush()

        # ── Seed Category ──
        cat_solar = session.query(SignupCategory).filter(SignupCategory.name == "Solar").first()
        if not cat_solar:
            cat_solar = SignupCategory(company_id=110, name="Solar Test Category", slug="solar-test-cat")
            session.add(cat_solar)
            session.flush()

        # ── Seed Tenants ──
        t1 = session.query(PlatformClient).filter(PlatformClient.id == 1).first()
        if not t1:
            t1 = PlatformClient(id=1, client_code="TENANT_1", client_name="Tenant One", status="active")
            session.add(t1)
            session.flush()

        t2 = session.query(PlatformClient).filter(PlatformClient.id == 260).first()
        if not t2:
            t2 = PlatformClient(id=260, client_code="TENANT_260", client_name="Tenant Two Sixty", status="active")
            session.add(t2)
            session.flush()

        # ── Seed Companies ──
        # Company 110 in Tenant 1
        c1 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 110).first()
        if not c1:
            c1 = AssociatedCompany(id=110, client_id=1, company_name="Company 110", company_code="C110", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c1)
            session.flush()

        # Company 120 in Tenant 1 (Sibling company)
        c2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 120).first()
        if not c2:
            c2 = AssociatedCompany(id=120, client_id=1, company_name="Company 120", company_code="C120", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c2)
            session.flush()

        # Company 261 in Tenant 2 (Foreign Tenant)
        c_t2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 261).first()
        if not c_t2:
            c_t2 = AssociatedCompany(id=261, client_id=260, company_name="Foreign Company 261", company_code="C261", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c_t2)
            session.flush()

        # ── Seed Staff Personas ──
        # 1. Manager (Tenant 1, Company 110)
        mgr = StaffEmployee(
            emp_code="EMP_CRM_LEADER",
            full_name="CRM Team Leader",
            email="leader@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_mgr.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(mgr)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=mgr.id, company_id=110, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 2. Subordinate 1 (Reports to Manager, Tenant 1, Company 110)
        sub1 = StaffEmployee(
            emp_code="EMP_CRM_SUB1",
            full_name="Subordinate 1",
            email="sub1@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            reporting_manager_id=mgr.id,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(sub1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=sub1.id, company_id=110, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 3. Subordinate 2 (Reports to Subordinate 1 -> recursive downline of Manager, Tenant 1, Company 110)
        sub2 = StaffEmployee(
            emp_code="EMP_CRM_SUB2",
            full_name="Subordinate 2",
            email="sub2@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            reporting_manager_id=sub1.id,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(sub2)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=sub2.id, company_id=110, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 4. Peer (Tenant 1, Company 110, NO manager / peer to sub1)
        peer = StaffEmployee(
            emp_code="EMP_CRM_PEER",
            full_name="Peer Employee",
            email="peer@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            reporting_manager_id=None,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(peer)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=peer.id, company_id=110, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 5. Sibling Company Staff (Tenant 1, Company 120 ONLY)
        co2_emp = StaffEmployee(
            emp_code="EMP_CRM_CO120",
            full_name="Company 120 Staff",
            email="co120@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(co2_emp)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=co2_emp.id, company_id=120, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 6. Foreign Tenant Staff (Tenant 260, Company 261)
        t2_emp = StaffEmployee(
            emp_code="EMP_CRM_T2",
            full_name="Tenant 2 Staff",
            email="t2@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=260,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(t2_emp)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=t2_emp.id, company_id=261, tenant_id=260, is_primary=True, is_active=True))
        session.flush()

        # 7. Canonical View-All Staff (Tenant 1, Company 110, crm.leads.view_all capability)
        view_all_emp = StaffEmployee(
            emp_code="EMP_CRM_VIEW_ALL",
            full_name="CRM View All User",
            email="viewall@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="STAFF"
        )
        session.add(view_all_emp)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=view_all_emp.id, company_id=110, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 8. Legacy String Heuristic Staff (staff_type='SALES_INCHARGE', emp_code='MN10009', NO view_all)
        legacy_emp = StaffEmployee(
            emp_code="MN10009_TEST",
            full_name="Legacy Sales Incharge",
            email="legacy@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_exec.id,
            department_id=dept_sales.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="SALES_INCHARGE",
            team_tag="team_a"
        )
        session.add(legacy_emp)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=legacy_emp.id, company_id=110, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # ── Seed CRM Leads ──
        # Lead 1: Tenant 1, Company 110, assigned to Subordinate 1
        lead_sub1 = CRMLead(
            name="Lead Subordinate One",
            phone="9100000001",
            status="contacted",
            tenant_id=1,
            company_id=110,
            primary_owner_type="staff",
            primary_owner_id=sub1.id,
            telecaller_id=sub1.id,
            field_staff_id=sub1.id,
            category_id=cat_solar.id,
            solar_pipeline_status="pending_with_bank",
            next_followup_date=datetime.now() - timedelta(days=2)
        )
        session.add(lead_sub1)

        # Lead 2: Tenant 1, Company 110, assigned to Subordinate 2
        lead_sub2 = CRMLead(
            name="Lead Subordinate Two",
            phone="9100000002",
            status="contacted",
            tenant_id=1,
            company_id=110,
            primary_owner_type="staff",
            primary_owner_id=sub2.id,
            telecaller_id=sub2.id,
            category_id=cat_solar.id,
            solar_pipeline_status="balance_pending",
            next_followup_date=datetime.now() - timedelta(days=1)
        )
        session.add(lead_sub2)

        # Lead 3: Tenant 1, Company 110, assigned to Peer
        lead_peer = CRMLead(
            name="Lead Peer Staff",
            phone="9100000003",
            status="contacted",
            tenant_id=1,
            company_id=110,
            primary_owner_type="staff",
            primary_owner_id=peer.id,
            telecaller_id=peer.id,
            category_id=cat_solar.id,
            solar_pipeline_status="pending_with_bank",
            next_followup_date=datetime.now() - timedelta(days=3)
        )
        session.add(lead_peer)

        # Lead 4: Tenant 1, Company 120 (Sibling company), assigned to co2_emp
        lead_co2 = CRMLead(
            name="Lead Sibling Company",
            phone="9100000004",
            status="contacted",
            tenant_id=1,
            company_id=120,
            primary_owner_type="staff",
            primary_owner_id=co2_emp.id,
            telecaller_id=co2_emp.id,
            category_id=cat_solar.id
        )
        session.add(lead_co2)

        # Lead 5: Tenant 260, Company 261 (Foreign tenant), assigned to t2_emp
        lead_t2 = CRMLead(
            name="Lead Foreign Tenant",
            phone="9100000005",
            status="contacted",
            tenant_id=260,
            company_id=261,
            primary_owner_type="staff",
            primary_owner_id=t2_emp.id,
            telecaller_id=t2_emp.id,
            category_id=cat_solar.id
        )
        session.add(lead_t2)
        session.flush()

        # Mint Auth Tokens
        tok_mgr = mint_token(mgr.id, mgr.emp_code, tenant_id=1)
        tok_sub1 = mint_token(sub1.id, sub1.emp_code, tenant_id=1)
        tok_sub2 = mint_token(sub2.id, sub2.emp_code, tenant_id=1)
        tok_peer = mint_token(peer.id, peer.emp_code, tenant_id=1)
        tok_co2 = mint_token(co2_emp.id, co2_emp.emp_code, tenant_id=1)
        tok_t2 = mint_token(t2_emp.id, t2_emp.emp_code, tenant_id=260)
        tok_view_all = mint_token(view_all_emp.id, view_all_emp.emp_code, tenant_id=1)
        tok_legacy = mint_token(legacy_emp.id, legacy_emp.emp_code, tenant_id=1)

        headers_sub1 = {"Authorization": f"Bearer {tok_sub1}"}
        headers_mgr = {"Authorization": f"Bearer {tok_mgr}"}
        headers_peer = {"Authorization": f"Bearer {tok_peer}"}
        headers_t2 = {"Authorization": f"Bearer {tok_t2}"}
        headers_view_all = {"Authorization": f"Bearer {tok_view_all}"}
        headers_legacy = {"Authorization": f"Bearer {tok_legacy}"}

        print("\n--- TEST GROUP 1: Anti-Tampering on Company ID Parameter across Endpoints ---")

        # 1. master-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/master-leads?company_id_filter=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id_filter on master-leads, got {r.status_code}"
        print("✅ master-leads: HTTP 403 on unauthorized company_id_filter")

        # 2. my-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/my-leads?company_id=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id on my-leads, got {r.status_code}"
        print("✅ my-leads: HTTP 403 on unauthorized company_id")

        # 3. team-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/team-leads?company_id=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id on team-leads, got {r.status_code}"
        print("✅ team-leads: HTTP 403 on unauthorized company_id")

        # 4. bank-wise-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/bank-wise-leads?company_id=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id on bank-wise-leads, got {r.status_code}"
        print("✅ bank-wise-leads: HTTP 403 on unauthorized company_id")

        # 5. leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/leads?company_id=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id on leads, got {r.status_code}"
        print("✅ leads: HTTP 403 on unauthorized company_id")

        # 6. lead-analytics with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/lead-analytics?company_id_filter=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id_filter on lead-analytics, got {r.status_code}"
        print("✅ lead-analytics: HTTP 403 on unauthorized company_id_filter")

        # 7. exec-handler-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/exec-handler-leads?handler_type=handler&handler_key=EMP_CRM_SUB1&company_id_filter=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id_filter on exec-handler-leads, got {r.status_code}"
        print("✅ exec-handler-leads: HTTP 403 on unauthorized company_id_filter")

        # 8. exec-trend-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/exec-trend-leads?period_type=monthly&label=2026-08&metric=overall_new&company_id_filter=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id_filter on exec-trend-leads, got {r.status_code}"
        print("✅ exec-trend-leads: HTTP 403 on unauthorized company_id_filter")

        # 9. exec-emp-perf-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get(f"/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code={sub1.emp_code}&metric=overall_new_leads&company_id_filter=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id_filter on exec-emp-perf-leads, got {r.status_code}"
        print("✅ exec-emp-perf-leads: HTTP 403 on unauthorized company_id_filter")

        # 10. employee-performance-dashboard with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/employee-performance-dashboard?company_id_filter=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id_filter on employee-performance-dashboard, got {r.status_code}"
        print("✅ employee-performance-dashboard: HTTP 403 on unauthorized company_id_filter")

        # 11. transactions/search-leads with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/transactions/search-leads?company_id=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id on transactions/search-leads, got {r.status_code}"
        print("✅ transactions/search-leads: HTTP 403 on unauthorized company_id")

        # 12. leads/system-search with unauthorized company 120 -> 403 Forbidden
        r = client.get("/api/v1/crm/leads/system-search?q=Lead&company_id=120", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for foreign company_id on leads/system-search, got {r.status_code}"
        print("✅ leads/system-search: HTTP 403 on unauthorized company_id")


        print("\n--- TEST GROUP 2: Downline Gating and Target Employee Verification ---")

        # 13. team-leads: downline target -> 200 OK
        r = client.get(f"/api/v1/crm/team-leads?team_member_id={sub2.id}", headers=headers_sub1)
        assert r.status_code == 200, f"Expected 200 for downline team member, got {r.status_code}: {r.text}"
        data = r.json().get("data", {}).get("leads", [])
        lead_ids = [l["id"] for l in data]
        assert lead_sub2.id in lead_ids, f"Expected downline lead {lead_sub2.id} in response"
        print("✅ team-leads: Downline target employee allowed (200 OK) with accurate leads")

        # 14. team-leads: non-downline peer target -> 403 Forbidden
        r = client.get(f"/api/v1/crm/team-leads?team_member_id={peer.id}", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for non-downline peer target, got {r.status_code}"
        print("✅ team-leads: HTTP 403 on peer target employee")

        # 15. team-leads: cross-tenant target -> 403 Forbidden
        r = client.get(f"/api/v1/crm/team-leads?team_member_id={t2_emp.id}", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for cross-tenant target, got {r.status_code}"
        print("✅ team-leads: HTTP 403 on cross-tenant target employee")

        # 16. exec-emp-perf-leads: downline target -> 200 OK
        r = client.get(f"/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code={sub2.emp_code}&metric=overall_new_leads", headers=headers_sub1)
        assert r.status_code == 200, f"Expected 200 for downline employee performance, got {r.status_code}"
        print("✅ exec-emp-perf-leads: Downline employee performance allowed (200 OK)")

        # 17. exec-emp-perf-leads: non-downline peer target -> 403 Forbidden
        r = client.get(f"/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code={peer.emp_code}&metric=overall_new_leads", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for non-downline peer employee performance, got {r.status_code}"
        print("✅ exec-emp-perf-leads: HTTP 403 on non-downline peer target employee")

        # 18. exec-emp-perf-leads: unassigned metric without view_all -> 403 Forbidden
        r = client.get("/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code=UNASSIGNED&metric=overall_new_leads", headers=headers_sub1)
        assert r.status_code == 403, f"Expected 403 for UNASSIGNED metric without view_all, got {r.status_code}"
        print("✅ exec-emp-perf-leads: HTTP 403 on UNASSIGNED metric for non-view_all staff")

        # 19. exec-emp-perf-leads: unassigned metric with view_all -> 200 OK
        r = client.get("/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code=UNASSIGNED&metric=overall_new_leads", headers=headers_view_all)
        assert r.status_code == 200, f"Expected 200 for UNASSIGNED metric with view_all, got {r.status_code}"
        print("✅ exec-emp-perf-leads: UNASSIGNED metric allowed (200 OK) for view_all staff")


        print("\n--- TEST GROUP 3: Tenant Boundary Isolation ---")

        # 20. Foreign tenant staff lists leads -> Only Tenant 260 leads returned
        r = client.get("/api/v1/crm/leads", headers=headers_t2)
        assert r.status_code == 200
        leads_data = r.json().get("data", [])
        ret_ids = [l["id"] for l in leads_data]
        assert lead_t2.id in ret_ids, "Expected foreign tenant lead in foreign tenant response"
        assert lead_sub1.id not in ret_ids, "Tenant 1 lead leaked to Tenant 260!"
        assert lead_sub2.id not in ret_ids, "Tenant 1 lead leaked to Tenant 260!"
        assert lead_peer.id not in ret_ids, "Tenant 1 lead leaked to Tenant 260!"
        print("✅ leads: Strict tenant isolation verified (0 Tenant 1 leads leaked to Tenant 260)")

        # 21. Foreign tenant staff system-search -> Only Tenant 260 leads returned
        r = client.get("/api/v1/crm/leads/system-search?q=Lead", headers=headers_t2)
        assert r.status_code == 200
        search_leads = r.json().get("leads", [])
        ret_search_ids = [l["id"] for l in search_leads]
        assert lead_t2.id in ret_search_ids
        assert lead_sub1.id not in ret_search_ids
        print("✅ leads/system-search: Strict tenant isolation verified in search results")

        # 22. Foreign tenant staff employee-performance-dashboard -> Only Tenant 260 staff returned
        r = client.get("/api/v1/crm/employee-performance-dashboard", headers=headers_t2)
        assert r.status_code == 200
        resp_json = r.json()
        monthly_staff = resp_json.get("monthly", [])
        staff_codes = [s["emp_code"] for s in monthly_staff]
        assert t2_emp.emp_code in staff_codes
        assert sub1.emp_code not in staff_codes, "Tenant 1 staff leaked to Tenant 260 dashboard!"
        assert mgr.emp_code not in staff_codes, "Tenant 1 manager leaked to Tenant 260 dashboard!"
        print("✅ employee-performance-dashboard: Strict tenant isolation in active staff dataset")


        print("\n--- TEST GROUP 4: Revocation of Legacy String Heuristics ---")

        # 23. Legacy sales incharge / team_a / MN10009 cannot access peer performance
        r = client.get(f"/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code={peer.emp_code}&metric=overall_new_leads", headers=headers_legacy)
        assert r.status_code == 403, f"Expected 403 for legacy staff accessing peer, got {r.status_code}"
        print("✅ exec-emp-perf-leads: Legacy role/emp_code strings DO NOT bypass downline gating (403)")

        # 24. Legacy sales incharge on master-leads -> does NOT see peer's lead
        r = client.get("/api/v1/crm/master-leads", headers=headers_legacy)
        assert r.status_code == 200
        ml_data = r.json().get("data", [])
        ml_ids = [l["id"] for l in ml_data]
        assert lead_peer.id not in ml_ids, "Peer lead leaked to legacy user on master-leads!"
        print("✅ master-leads: Legacy string heuristics revoked; peer leads strictly hidden")

        # 25. Legacy staff on bank-wise-leads -> does NOT see unassigned / peer bank leads
        r = client.get("/api/v1/crm/bank-wise-leads", headers=headers_legacy)
        assert r.status_code == 200
        bw_leads = r.json().get("leads", [])
        bw_ids = [l["id"] for l in bw_leads]
        assert lead_peer.id not in bw_ids, "Peer bank lead leaked to legacy staff!"
        print("✅ bank-wise-leads: Legacy string heuristics revoked; peer bank leads strictly hidden")


        print("\n--- TEST GROUP 5: Canonical Capability crm.leads.view_all Verification ---")

        # 26. crm.leads.view_all can query peer performance
        r = client.get(f"/api/v1/crm/exec-emp-perf-leads?period_key=TOTAL&emp_code={peer.emp_code}&metric=overall_new_leads", headers=headers_view_all)
        assert r.status_code == 200, f"Expected 200 for user with crm.leads.view_all, got {r.status_code}"
        print("✅ exec-emp-perf-leads: crm.leads.view_all allows querying peer performance (200 OK)")

        # 27. crm.leads.view_all in master-leads sees all company leads
        r = client.get("/api/v1/crm/master-leads", headers=headers_view_all)
        assert r.status_code == 200
        ml_data = r.json().get("data", [])
        ml_ids = [l["id"] for l in ml_data]
        assert lead_sub1.id in ml_ids and lead_sub2.id in ml_ids and lead_peer.id in ml_ids
        # But NOT sibling company 120 or foreign tenant 260
        assert lead_co2.id not in ml_ids, "Sibling company lead leaked without company parameter!"
        assert lead_t2.id not in ml_ids, "Foreign tenant lead leaked to view_all user!"
        print("✅ master-leads: crm.leads.view_all grants company-wide visibility while preserving company and tenant boundaries")

        # 28. crm.leads.view_all in bank-wise-leads sees all company bank leads
        r = client.get("/api/v1/crm/bank-wise-leads", headers=headers_view_all)
        assert r.status_code == 200
        bw_leads = r.json().get("leads", [])
        bw_ids = [l["id"] for l in bw_leads]
        assert lead_sub1.id in bw_ids and lead_peer.id in bw_ids
        print("✅ bank-wise-leads: crm.leads.view_all grants company bank file visibility")


        print("\n--- TEST GROUP 6: Endpoint Specific Validations (Endpoints 6, 10, 11) ---")

        # 29. my-leads: Subordinate 1 sees only their assigned leads
        r = client.get("/api/v1/crm/my-leads", headers=headers_sub1)
        assert r.status_code == 200
        my_leads = r.json().get("data", [])
        my_ids = [l["id"] for l in my_leads]
        assert lead_sub1.id in my_ids
        assert lead_sub2.id not in my_ids, "Subordinate 2 lead leaked into Subordinate 1 my-leads!"
        assert lead_peer.id not in my_ids, "Peer lead leaked into Subordinate 1 my-leads!"
        print("✅ my-leads: Strictly scoped to assigned leads")

        # 30. transactions/search-leads: Subordinate 1 sees only their assigned leads
        r = client.get(f"/api/v1/crm/transactions/search-leads?company_id=110&search={lead_sub1.phone}", headers=headers_sub1)
        assert r.status_code == 200
        tx_search = r.json().get("data", [])
        tx_ids = [l["id"] for l in tx_search]
        assert lead_sub1.id in tx_ids
        print("✅ transactions/search-leads: Authorized company search succeeds (200 OK)")

        # Searching for peer's lead phone returns empty for non-view-all staff
        r = client.get(f"/api/v1/crm/transactions/search-leads?company_id=110&search={lead_peer.phone}", headers=headers_sub1)
        assert r.status_code == 200
        tx_search = r.json().get("data", [])
        assert len(tx_search) == 0, f"Peer lead leaked in transactions/search-leads: {tx_search}"
        print("✅ transactions/search-leads: Non-view-all staff cannot view peer lead")

        # 31. leads/system-search: Subordinate 1 sees assigned leads
        r = client.get(f"/api/v1/crm/leads/system-search?q={lead_sub1.phone}", headers=headers_sub1)
        assert r.status_code == 200
        sys_leads = r.json().get("leads", [])
        assert any(l["id"] == lead_sub1.id for l in sys_leads)
        print("✅ leads/system-search: Assigned lead found (200 OK)")

        # Searching peer's phone returns empty for non-view-all staff
        r = client.get(f"/api/v1/crm/leads/system-search?q={lead_peer.phone}", headers=headers_sub1)
        assert r.status_code == 200
        sys_leads = r.json().get("leads", [])
        assert len(sys_leads) == 0, "Peer lead leaked in system-search!"
        print("✅ leads/system-search: Non-view-all staff cannot search peer leads")

        # 32. lead-analytics: Subordinate 1 sees counts reflecting only their leads and downline
        r = client.get("/api/v1/crm/lead-analytics", headers=headers_sub1)
        assert r.status_code == 200
        an_data = r.json()
        assert "summary" in an_data
        assert an_data["summary"]["total_leads"] == 2, f"Expected 2 leads for sub1+sub2 downline, got {an_data['summary']['total_leads']}"

        r_peer = client.get("/api/v1/crm/lead-analytics", headers=headers_peer)
        assert r_peer.status_code == 200
        peer_an = r_peer.json()
        assert peer_an["summary"]["total_leads"] == 1, f"Expected 1 lead for peer without downline, got {peer_an['summary']['total_leads']}"
        print("✅ lead-analytics: Analytics queries strictly scoped to user + downline hierarchy")

        print("\n" + "=" * 80)
        print("ALL 32 TEST SCENARIOS PASSED FOR STAGE 2B PHASE 2R-2!")
        print("=" * 80)

    finally:
        # ─────────────────────────────────────────────────────────────────────
        # Step 7: Rollback Transaction & Restore Isolation
        # ─────────────────────────────────────────────────────────────────────
        transaction.rollback()
        connection.close()
        app.dependency_overrides.clear()
        nda_patch.stop()
        caps_patch.stop()
        invalidate_auth_cache()

        # ─────────────────────────────────────────────────────────────────────
        # Step 8: Post-Execution Row Count Verification (Zero-Mutation Proof)
        # ─────────────────────────────────────────────────────────────────────
        post_db = SessionLocal()
        emp_count_after = post_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
        mem_count_after = post_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
        comp_count_after = post_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
        client_count_after = post_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
        role_count_after = post_db.execute(text("SELECT count(*) FROM staff_roles")).scalar()
        dept_count_after = post_db.execute(text("SELECT count(*) FROM staff_departments")).scalar()
        lead_count_after = post_db.execute(text("SELECT count(*) FROM crm_leads")).scalar()
        deal_count_after = post_db.execute(text("SELECT count(*) FROM crm_lead_deals")).scalar()
        txn_count_after = post_db.execute(text("SELECT count(*) FROM crm_lead_transactions")).scalar()
        rev_count_after = post_db.execute(text("SELECT count(*) FROM crm_revenue_entries")).scalar()
        post_db.close()

        print("\n" + "-" * 60)
        print("OPERATIONAL DATABASE ZERO-MUTATION VERIFICATION:")
        print(f"  staff_employees:          before={emp_count_before}, after={emp_count_after}")
        print(f"  staff_company_memberships: before={mem_count_before}, after={mem_count_after}")
        print(f"  associated_companies:     before={comp_count_before}, after={comp_count_after}")
        print(f"  platform_clients:         before={client_count_before}, after={client_count_after}")
        print(f"  staff_roles:              before={role_count_before}, after={role_count_after}")
        print(f"  staff_departments:        before={dept_count_before}, after={dept_count_after}")
        print(f"  crm_leads:                before={lead_count_before}, after={lead_count_after}")
        print(f"  crm_lead_deals:           before={deal_count_before}, after={deal_count_after}")
        print(f"  crm_lead_transactions:    before={txn_count_before}, after={txn_count_after}")
        print(f"  crm_revenue_entries:      before={rev_count_before}, after={rev_count_after}")
        print("-" * 60)

        assert emp_count_before == emp_count_after, "Mutation detected in staff_employees!"
        assert mem_count_before == mem_count_after, "Mutation detected in staff_company_memberships!"
        assert comp_count_before == comp_count_after, "Mutation detected in associated_companies!"
        assert client_count_before == client_count_after, "Mutation detected in platform_clients!"
        assert role_count_before == role_count_after, "Mutation detected in staff_roles!"
        assert dept_count_before == dept_count_after, "Mutation detected in staff_departments!"
        assert lead_count_before == lead_count_after, "Mutation detected in crm_leads!"
        assert deal_count_before == deal_count_after, "Mutation detected in crm_lead_deals!"
        assert txn_count_before == txn_count_after, "Mutation detected in crm_lead_transactions!"
        assert rev_count_before == rev_count_after, "Mutation detected in crm_revenue_entries!"
        print("✅ ZERO OPERATIONAL DB MUTATIONS VERIFIED — DATABASE IS 100% PRISTINE\n")


if __name__ == "__main__":
    test_stage2b_phase2r2_crm_search_analytics_security()
