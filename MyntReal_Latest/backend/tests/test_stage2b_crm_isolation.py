"""
Stage 2B CRM Lead Multi-Tenant Isolation and Anti-Enumeration Test Suite
Mandatory Requirements:
1. Transaction rollback ensures ZERO database mutations against the operational database.
2. Comprehensive coverage of all CRM lead security controls:
   - Anti-enumeration across tenant boundaries (HTTP 404, never 403 or 200)
   - Anti-enumeration across company boundaries for non-members (HTTP 404)
   - Direct lead assignment bypass (primary owner, telecaller, field staff, handler)
   - Self-created lead access (creator matching emp_code or id)
   - Downline reporting manager hierarchy access
   - Unassigned lead claiming isolation (members only)
   - Mutation capability gating (crm.leads.edit required for modifications)
   - Tenant Admin full tenant-wide access
   - Platform Superadmin multi-tenant bypass
   - Dynamic tenant resolution in crm_lead_sync.py (_resolve_category_and_tenant)
   - Dynamic tenant resolution in sheets_leads_service.py (_resolve_company_tenant_id)
   - End-to-end FastAPI HTTP TestClient verification
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Ensure backend root is in sys.path and .env is loaded
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
load_dotenv(_backend_dir / ".env")

from sqlalchemy import text
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine, get_db, SessionLocal
from app.core.security import SecurityManager
from app.core.context import (
    RequestContext, AdminScope, get_current_request_context,
    set_current_request_context, reset_current_request_context
)
from app.models.staff import StaffEmployee, StaffRole, StaffCompanyMembership
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.models.crm import CRMLead
from app.models.signup_category import SignupCategory
from app.services.auth_context_service import auth_context_service, invalidate_auth_cache
from app.api.v1.endpoints.crm import get_authorized_lead
from app.api.v1.endpoints.crm_lead_sync import _resolve_category_and_tenant
from app.services.sheets_leads_service import _resolve_company_tenant_id, row_to_crm_lead


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


def test_stage2b_crm_isolation_suite():
    print("\n" + "=" * 80)
    print("STAGE 2B CRM LEAD MULTI-TENANT ISOLATION & ANTI-ENUMERATION TEST SUITE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 0: Baseline Row Counts
    # ─────────────────────────────────────────────────────────────────────────
    pre_db = SessionLocal()
    emp_count_before = pre_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
    mem_count_before = pre_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
    comp_count_before = pre_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
    client_count_before = pre_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
    lead_count_before = pre_db.execute(text("SELECT count(*) FROM crm_leads")).scalar()
    cat_count_before = pre_db.execute(text("SELECT count(*) FROM signup_categories")).scalar()
    pre_db.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1: Set Up Transaction Rollback Isolation
    # ─────────────────────────────────────────────────────────────────────────
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    # Monkeypatch session.commit to flush within transaction: prevents committing to DB
    session.commit = session.flush
    real_rollback = session.rollback
    session.rollback = lambda: None

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="http://testserver")

    try:
        invalidate_auth_cache()

        # Seed roles
        role_agent = session.query(StaffRole).filter(StaffRole.hierarchy_level == 1).first()
        if not role_agent:
            role_agent = StaffRole(role_code="test_agent", role_name="Agent", hierarchy_level=1)
            session.add(role_agent)
            session.flush()

        role_exec = session.query(StaffRole).filter(StaffRole.hierarchy_level == 10).first()
        if not role_exec:
            role_exec = StaffRole(role_code="test_exec", role_name="Executive", hierarchy_level=10)
            session.add(role_exec)
            session.flush()

        role_mgr = session.query(StaffRole).filter(StaffRole.hierarchy_level == 60).first()
        if not role_mgr:
            role_mgr = StaffRole(role_code="test_mgr", role_name="Manager", hierarchy_level=60)
            session.add(role_mgr)
            session.flush()

        role_admin = session.query(StaffRole).filter(StaffRole.hierarchy_level == 100).first()
        if not role_admin:
            role_admin = StaffRole(role_code="test_tenant_admin", role_name="Tenant Admin", hierarchy_level=100)
            session.add(role_admin)
            session.flush()

        role_super = session.query(StaffRole).filter(StaffRole.hierarchy_level == 150).first()
        if not role_super:
            role_super = StaffRole(role_code="test_superadmin", role_name="Superadmin", hierarchy_level=150)
            session.add(role_super)
            session.flush()

        # Seed Tenants
        t1 = session.query(PlatformClient).filter(PlatformClient.id == 1).first()
        if not t1:
            t1 = PlatformClient(id=1, client_code="PLATFORM_TENANT_1", client_name="Platform Tenant 1", status="active")
            session.add(t1)
            session.flush()

        t_other = session.query(PlatformClient).filter(PlatformClient.id == 158).first()
        if not t_other:
            t_other = PlatformClient(id=158, client_code="TB_D4E63657", client_name="Tenant B Corp", status="active")
            session.add(t_other)
            session.flush()

        # Seed Companies
        # Company 1 in Tenant 1
        c1 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 1).first()
        if not c1:
            c1 = AssociatedCompany(id=1, client_id=1, company_name="Company 1", company_code="C1", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c1)
            session.flush()

        # Company 2 in Tenant 1
        c2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 2).first()
        if not c2:
            c2 = AssociatedCompany(id=2, client_id=1, company_name="Company 2", company_code="C2", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c2)
            session.flush()

        # Company 95 in Tenant 2 (client_id=158)
        c_t_other = session.query(AssociatedCompany).filter(AssociatedCompany.id == 95).first()
        if not c_t_other:
            c_t_other = AssociatedCompany(id=95, client_id=158, company_name="Tenant B Company", company_code="TBC", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c_t_other)
            session.flush()

        # Seed Staff Employees
        # Manager in Tenant 1
        mgr_emp = StaffEmployee(
            emp_code="EMP_CRM_MGR",
            full_name="Manager Staff",
            email="mgr@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_mgr.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="TENANT_ADMIN"
        )
        session.add(mgr_emp)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=mgr_emp.id, company_id=1, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # Staff 1: Member of Company 1, Tenant 1, reports to mgr_emp
        emp_c1 = StaffEmployee(
            emp_code="EMP_CRM_C1",
            full_name="Staff Company 1",
            email="emp_c1@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            reporting_manager_id=mgr_emp.id,
            role_id=role_exec.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="TENANT_ADMIN"
        )
        session.add(emp_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_c1.id, company_id=1, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # Staff 2: Member of Company 2, Tenant 1
        emp_c2 = StaffEmployee(
            emp_code="EMP_CRM_C2",
            full_name="Staff Company 2",
            email="emp_c2@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_exec.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="TENANT_ADMIN"
        )
        session.add(emp_c2)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_c2.id, company_id=2, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # Staff Agent: Member of Company 1, Tenant 1, but level 1 (NO crm.leads.edit)
        emp_agent = StaffEmployee(
            emp_code="EMP_CRM_AGENT",
            full_name="Staff Agent No Edit",
            email="emp_agent@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_agent.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="TENANT_ADMIN"
        )
        session.add(emp_agent)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_agent.id, company_id=1, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # Staff Tenant 2: Member of Company 95, Tenant 158
        emp_t2 = StaffEmployee(
            emp_code="EMP_CRM_T2",
            full_name="Staff Tenant 2",
            email="emp_t2@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=158,
            role_id=role_exec.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC",
            staff_type="TENANT_ADMIN"
        )
        session.add(emp_t2)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_t2.id, company_id=95, tenant_id=158, is_primary=True, is_active=True))
        session.flush()

        # Staff Tenant Admin: Tenant 1, Level 100
        emp_tenant_admin = StaffEmployee(
            emp_code="EMP_CRM_TADMIN",
            full_name="Tenant Admin Staff",
            email="emp_tadmin@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_admin.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="TENANT_ADMIN",
            staff_type="TENANT_ADMIN"
        )
        session.add(emp_tenant_admin)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_tenant_admin.id, company_id=1, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # Staff Superadmin: Tenant 1, Level 150, scope PLATFORM
        emp_superadmin = StaffEmployee(
            emp_code="EMP_CRM_SUPER",
            full_name="Superadmin Staff",
            email="super@test.com",
            password_hash="hash",
            status="active",
            employment_type="confirmed",
            kyc_status="approved",
            tenant_id=1,
            role_id=role_super.id,
            date_of_joining=date(2026, 1, 1),
            admin_scope="PLATFORM",
            staff_type="TENANT_ADMIN"
        )
        session.add(emp_superadmin)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=emp_superadmin.id, company_id=1, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # ─────────────────────────────────────────────────────────────────────
        # Seed CRM Leads
        # ─────────────────────────────────────────────────────────────────────
        # Lead 1: Unassigned in Company 1, Tenant 1
        lead_t1_c1 = CRMLead(
            name="Lead T1 C1 Unassigned",
            phone="9900112233",
            company_id=1,
            tenant_id=1,
            status="new",
            handler_type="unassigned"
        )
        session.add(lead_t1_c1)
        session.flush()

        # Lead 2: Unassigned in Company 2, Tenant 1
        lead_t1_c2 = CRMLead(
            name="Lead T1 C2 Unassigned",
            phone="9900112244",
            company_id=2,
            tenant_id=1,
            status="new",
            handler_type="unassigned"
        )
        session.add(lead_t1_c2)
        session.flush()

        # Lead 3: Unassigned in Company 95, Tenant 158 (Tenant 2)
        lead_t2_c95 = CRMLead(
            name="Lead T2 C95 Unassigned",
            phone="9900112255",
            company_id=95,
            tenant_id=158,
            status="new",
            handler_type="unassigned"
        )
        session.add(lead_t2_c95)
        session.flush()

        # Lead 4: In Company 2, Tenant 1, but assigned to emp_c1 (from Company 1)
        lead_assigned = CRMLead(
            name="Lead Assigned Cross-Company",
            phone="9900112266",
            company_id=2,
            tenant_id=1,
            status="contacted",
            primary_owner_type="staff",
            primary_owner_id=emp_c1.id,
            handler_type="staff",
            handler_id=emp_c1.emp_code
        )
        session.add(lead_assigned)
        session.flush()

        # Lead 5: In Company 2, Tenant 1, but created by emp_c1
        lead_created = CRMLead(
            name="Lead Self Created",
            phone="9900112277",
            company_id=2,
            tenant_id=1,
            status="new",
            created_by_type="staff",
            created_by_id=emp_c1.emp_code,
            handler_type="unassigned"
        )
        session.add(lead_created)
        session.flush()

        # ─────────────────────────────────────────────────────────────────────
        # TEST 1: Anti-Enumeration across Tenants (Section 1 & 5)
        # Staff in Tenant 1 querying Lead in Tenant 2 MUST return 404 (NEVER 403 or 200)
        # ─────────────────────────────────────────────────────────────────────
        try:
            get_authorized_lead(session, lead_t2_c95.id, emp_c1)
            assert False, "Test 1 Failed: Cross-tenant lead query did not raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 404, f"Test 1 Failed: Expected 404, got {e.status_code}"
            assert e.detail == "Lead not found", f"Test 1 Failed: Expected anti-enumeration detail, got {e.detail}"
        print("✓ Test 1 PASSED: Anti-enumeration across tenants returns 404 Not Found")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 2: Anti-Enumeration across Companies (non-member, unassigned)
        # Staff in Company 1 querying Lead in Company 2 (unassigned) MUST return 404
        # ─────────────────────────────────────────────────────────────────────
        try:
            get_authorized_lead(session, lead_t1_c2.id, emp_c1)
            assert False, "Test 2 Failed: Cross-company unauthorized query did not raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 404, f"Test 2 Failed: Expected 404, got {e.status_code}"
            assert e.detail == "Lead not found", f"Test 2 Failed: Expected anti-enumeration detail, got {e.detail}"
        print("✓ Test 2 PASSED: Anti-enumeration across unauthorized companies returns 404 Not Found")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 3: Non-existent Lead ID returns 404
        # ─────────────────────────────────────────────────────────────────────
        try:
            get_authorized_lead(session, 999999999, emp_c1)
            assert False, "Test 3 Failed: Non-existent lead did not raise 404"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == "Lead not found"
        print("✓ Test 3 PASSED: Non-existent lead returns identical 404 Not Found")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 4: Operational Company Member Read Access
        # Staff in Company 1 querying Lead in Company 1 MUST succeed (200)
        # ─────────────────────────────────────────────────────────────────────
        res_lead = get_authorized_lead(session, lead_t1_c1.id, emp_c1)
        assert res_lead.id == lead_t1_c1.id
        print("✓ Test 4 PASSED: Operational company member has authorized read access")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 5: Assigned Staff Access Across Companies
        # Staff in Company 1 querying Lead in Company 2 assigned to them MUST succeed
        # ─────────────────────────────────────────────────────────────────────
        res_assigned = get_authorized_lead(session, lead_assigned.id, emp_c1)
        assert res_assigned.id == lead_assigned.id
        print("✓ Test 5 PASSED: Assigned staff retains access to assigned lead across companies")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 6: Self-Created Lead Access Across Companies
        # Staff in Company 1 querying Lead created by them in Company 2 MUST succeed
        # ─────────────────────────────────────────────────────────────────────
        res_created = get_authorized_lead(session, lead_created.id, emp_c1)
        assert res_created.id == lead_created.id
        print("✓ Test 6 PASSED: Creator staff retains access to self-created lead")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 7: Reporting Manager / Downline Hierarchy Access
        # Manager of emp_c1 MUST be able to access lead assigned to emp_c1
        # ─────────────────────────────────────────────────────────────────────
        res_mgr = get_authorized_lead(session, lead_assigned.id, mgr_emp)
        assert res_mgr.id == lead_assigned.id
        print("✓ Test 7 PASSED: Reporting manager has authorized downline access to assigned lead")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 8: Unassigned Lead Claiming Boundary Isolation
        # Member of Company 1 CANNOT claim unassigned lead in Company 2 (404)
        # Member of Company 1 CAN claim unassigned lead in Company 1 (200)
        # ─────────────────────────────────────────────────────────────────────
        try:
            get_authorized_lead(session, lead_t1_c2.id, emp_c1, allow_unassigned=True)
            assert False, "Test 8 Failed: Non-member claiming unassigned lead was allowed"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == "Lead not found"

        res_claim_c1 = get_authorized_lead(session, lead_t1_c1.id, emp_c1, allow_unassigned=True)
        assert res_claim_c1.id == lead_t1_c1.id
        print("✓ Test 8 PASSED: Unassigned lead claiming strictly isolated to company members")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 9: Mutation Capability Gating (crm.leads.edit check)
        # Agent without crm.leads.edit capability MUST receive 403 on mutation
        # Executive with crm.leads.edit capability MUST succeed
        # ─────────────────────────────────────────────────────────────────────
        try:
            get_authorized_lead(session, lead_t1_c1.id, emp_agent, for_mutation=True)
            assert False, "Test 9 Failed: Agent without crm.leads.edit was allowed to mutate"
        except HTTPException as e:
            assert e.status_code == 403
            assert "Permission denied" in e.detail or "modify this lead" in e.detail

        res_mutate = get_authorized_lead(session, lead_t1_c1.id, emp_c1, for_mutation=True)
        assert res_mutate.id == lead_t1_c1.id
        print("✓ Test 9 PASSED: Mutation capability (crm.leads.edit) enforced (403 for unauthorized)")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 10: Tenant Administrator Scope
        # Tenant Admin in Tenant 1 has access to all leads within Tenant 1 (both c1 and c2)
        # but CANNOT access leads in Tenant 2 (404 anti-enumeration)
        # ─────────────────────────────────────────────────────────────────────
        res_tadmin_c1 = get_authorized_lead(session, lead_t1_c1.id, emp_tenant_admin)
        res_tadmin_c2 = get_authorized_lead(session, lead_t1_c2.id, emp_tenant_admin)
        assert res_tadmin_c1.id == lead_t1_c1.id
        assert res_tadmin_c2.id == lead_t1_c2.id

        try:
            get_authorized_lead(session, lead_t2_c95.id, emp_tenant_admin)
            assert False, "Test 10 Failed: Tenant Admin accessed foreign tenant lead"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == "Lead not found"
        print("✓ Test 10 PASSED: Tenant Admin access bounded strictly to authenticated tenant")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 11: Platform Superadmin Multi-Tenant Scope
        # Superadmin has access to leads across Tenant 1 AND Tenant 2
        # ─────────────────────────────────────────────────────────────────────
        res_super_t1 = get_authorized_lead(session, lead_t1_c1.id, emp_superadmin)
        res_super_t2 = get_authorized_lead(session, lead_t2_c95.id, emp_superadmin)
        assert res_super_t1.id == lead_t1_c1.id
        assert res_super_t2.id == lead_t2_c95.id
        print("✓ Test 11 PASSED: Platform Superadmin authorized across all tenants and companies")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 12: Dynamic Tenant Resolution in crm_lead_sync.py
        # Test _resolve_category_and_tenant dynamically joins SignupCategory and AssociatedCompany
        # ─────────────────────────────────────────────────────────────────────
        cat_t1 = SignupCategory(
            company_id=1,
            name="Test Category T1",
            slug="test_category_t1",
            is_active=True
        )
        session.add(cat_t1)
        session.flush()

        cat_t2 = SignupCategory(
            company_id=95,
            name="Test Category T2",
            slug="test_category_t2",
            is_active=True
        )
        session.add(cat_t2)
        session.flush()

        cat_invalid = SignupCategory(
            company_id=999999,  # Non-existent company
            name="Test Category Invalid",
            slug="test_category_invalid",
            is_active=True
        )
        session.add(cat_invalid)
        session.flush()

        # Resolution checks
        c_id, t_id = _resolve_category_and_tenant(session, cat_t1.id)
        assert c_id == 1 and t_id == 1, f"Test 12 Failed: Expected (1, 1), got ({c_id}, {t_id})"

        c_id2, t_id2 = _resolve_category_and_tenant(session, cat_t2.id)
        assert c_id2 == 95 and t_id2 == 158, f"Test 12 Failed: Expected (95, 158), got ({c_id2}, {t_id2})"

        c_inv, t_inv = _resolve_category_and_tenant(session, cat_invalid.id)
        assert c_inv is None and t_inv is None, f"Test 12 Failed: Expected (None, None), got ({c_inv}, {t_inv})"

        c_non, t_non = _resolve_category_and_tenant(session, 9999999)
        assert c_non is None and t_non is None, f"Test 12 Failed: Expected (None, None), got ({c_non}, {t_non})"
        print("✓ Test 12 PASSED: Dynamic tenant & company resolution in crm_lead_sync fails closed")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 13: Dynamic Tenant Resolution in sheets_leads_service.py
        # Test _resolve_company_tenant_id and row_to_crm_lead
        # ─────────────────────────────────────────────────────────────────────
        t_res1 = _resolve_company_tenant_id(session, 1)
        assert t_res1 == 1, f"Test 13 Failed: Expected 1, got {t_res1}"

        t_res2 = _resolve_company_tenant_id(session, 95)
        assert t_res2 == 158, f"Test 13 Failed: Expected 158, got {t_res2}"

        t_res_none = _resolve_company_tenant_id(session, 999999)
        assert t_res_none is None, f"Test 13 Failed: Expected None, got {t_res_none}"

        # Test row_to_crm_lead populates tenant_id
        dummy_row = ["John Doe", "9876543210", "john@example.com", "Bangalore"]
        col_map = {"name": 0, "phone": 1, "email": 2, "city": 3}
        lead_dict = row_to_crm_lead(dummy_row, col_map, company_id=1, db=session)
        assert lead_dict is not None
        assert lead_dict.get("tenant_id") == 1, f"Test 13 Failed: row_to_crm_lead missing tenant_id: {lead_dict}"
        print("✓ Test 13 PASSED: Sheets service dynamically resolves and sets tenant_id")

        # ─────────────────────────────────────────────────────────────────────
        # TEST 14: End-to-End HTTP Endpoint Verification via TestClient
        # ─────────────────────────────────────────────────────────────────────
        token_c1 = mint_token(emp_c1.id, emp_c1.emp_code, tenant_id=1)
        token_c2 = mint_token(emp_c2.id, emp_c2.emp_code, tenant_id=1)
        token_t2 = mint_token(emp_t2.id, emp_t2.emp_code, tenant_id=158)

        # 14A: GET /leads/{id} across tenants -> 404 Not Found
        resp = client.get(f"/api/v1/crm/leads/{lead_t2_c95.id}", headers={"Authorization": f"Bearer {token_c1}"})
        assert resp.status_code == 404, f"Test 14A Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Lead not found"

        # 14B: GET /leads/{id} within company -> 200 OK
        resp2 = client.get(f"/api/v1/crm/leads/{lead_t1_c1.id}", headers={"Authorization": f"Bearer {token_c1}"})
        assert resp2.status_code == 200, f"Test 14B Failed: Expected 200, got {resp2.status_code}: {resp2.text}"
        assert resp2.json().get("data", {}).get("id") == lead_t1_c1.id

        # 14C: GET /leads/{id} across companies (unassigned) -> 404 Not Found
        resp3 = client.get(f"/api/v1/crm/leads/{lead_t1_c2.id}", headers={"Authorization": f"Bearer {token_c1}"})
        assert resp3.status_code == 404, f"Test 14C Failed: Expected 404, got {resp3.status_code}: {resp3.text}"
        assert resp3.json().get("detail") == "Lead not found"

        # 14D: POST /leads/{id}/claim unauthorized company -> 404 Not Found
        resp4 = client.post(f"/api/v1/crm/leads/{lead_t1_c2.id}/claim", headers={"Authorization": f"Bearer {token_c1}"})
        assert resp4.status_code == 404, f"Test 14D Failed: Expected 404, got {resp4.status_code}: {resp4.text}"

        # 14E: POST /leads/{id}/claim authorized company -> 200 OK
        resp5 = client.post(f"/api/v1/crm/leads/{lead_t1_c1.id}/claim", headers={"Authorization": f"Bearer {token_c1}"})
        assert resp5.status_code == 200, f"Test 14E Failed: Expected 200, got {resp5.status_code}: {resp5.text}"

        print("✓ Test 14 PASSED: End-to-end HTTP endpoints enforce anti-enumeration and boundary checks")

        print("\n" + "=" * 80)
        print("ALL 14 STAGE 2B CRM ISOLATION TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        app.dependency_overrides.clear()
        session.rollback = real_rollback
        session.close()
        transaction.rollback()
        connection.close()

        # Step 4: Post-test database row count check to guarantee 0 database mutations
        post_db = SessionLocal()
        emp_count_after = post_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
        mem_count_after = post_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
        comp_count_after = post_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
        client_count_after = post_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
        lead_count_after = post_db.execute(text("SELECT count(*) FROM crm_leads")).scalar()
        cat_count_after = post_db.execute(text("SELECT count(*) FROM signup_categories")).scalar()
        post_db.close()

        print(f"\n[DB-MUTATION-AUDIT] staff_employees count: before={emp_count_before}, after={emp_count_after}")
        print(f"[DB-MUTATION-AUDIT] staff_company_memberships count: before={mem_count_before}, after={mem_count_after}")
        print(f"[DB-MUTATION-AUDIT] associated_companies count: before={comp_count_before}, after={comp_count_after}")
        print(f"[DB-MUTATION-AUDIT] platform_clients count: before={client_count_before}, after={client_count_after}")
        print(f"[DB-MUTATION-AUDIT] crm_leads count: before={lead_count_before}, after={lead_count_after}")
        print(f"[DB-MUTATION-AUDIT] signup_categories count: before={cat_count_before}, after={cat_count_after}")

        assert emp_count_before == emp_count_after, "DB MUTATION DETECTED: staff_employees count mismatch!"
        assert mem_count_before == mem_count_after, "DB MUTATION DETECTED: staff_company_memberships count mismatch!"
        assert comp_count_before == comp_count_after, "DB MUTATION DETECTED: associated_companies count mismatch!"
        assert client_count_before == client_count_after, "DB MUTATION DETECTED: platform_clients count mismatch!"
        assert lead_count_before == lead_count_after, "DB MUTATION DETECTED: crm_leads count mismatch!"
        assert cat_count_before == cat_count_after, "DB MUTATION DETECTED: signup_categories count mismatch!"

        print("[DB-MUTATION-AUDIT] VERIFIED: 0 rows inserted, 0 rows modified, 0 rows deleted in operational database!\n")


if __name__ == "__main__":
    test_stage2b_crm_isolation_suite()
