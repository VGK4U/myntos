"""
Stage 2B Phase 2R-1: Financial RBAC & Child-Resource IDOR Security Test Suite
OPTION B — STRICT CAPABILITY ENFORCEMENT VERIFICATION

Mandatory Coverage:
1. Canonical Financial Authorization Gate:
   - Tenant admin with canonical authority (Level 100) -> ALLOWED (200)
   - Platform superadmin (Level 150, PLATFORM scope, Master Tenant 1) -> ALLOWED (200)
   - Employee with explicit canonical finance.approve capability -> ALLOWED (200)
2. Revocation of Legacy String Heuristics (Option B Verification):
   - Ordinary CRM employee (sales_c1, level 10) -> DENIED (403)
   - Employee with legacy "FINANCE" staff_type without capability -> DENIED (403)
   - Employee with legacy "ACCOUNT" staff_type without capability -> DENIED (403)
   - Employee with legacy finance/accounts role (role_code="accounts", level 10) without capability -> DENIED (403)
   - Employee with finance/accounts department (dept_name="Accounts", level 10) without capability -> DENIED (403)
3. Fail-Closed Two-Tier Architecture & Anti-Enumeration:
   - Cross-company financial employee -> Tier 1 DENIED (404, never 403 or 200)
   - Cross-tenant financial employee -> Tier 1 DENIED (404, never 403 or 200)
   - Non-existent IDs -> Identical HTTP 404
4. Input Validation & Company Binding:
   - Mismatched company_id query params -> DENIED (400)
   - Deal company_id strictly bound to parent lead company
   - Cross-lead deal binding on transactions -> DENIED (400)
   - Forged tenant_id -> DENIED (401/403/404)
5. Execution Side-Effects Verification:
   - Zero side-effects executed on authorization or validation failure
   - Receipts upload handler never invoked on failure
6. Zero DB Mutation Guarantee:
   - Transaction rollback ensures operational database is never modified.
   - Row counts for all operational tables verified before and after test execution.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import io
from unittest.mock import patch, AsyncMock
from dotenv import load_dotenv

# Ensure backend root is in sys.path and .env is loaded
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
from app.services.universal_upload_service import UniversalUploadService


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


def test_stage2b_phase2r1_financial_child_security():
    print("\n" + "=" * 80)
    print("STAGE 2B PHASE 2R-1: OPTION B STRICT CAPABILITY ENFORCEMENT & CHILD IDOR")
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

    # Prevent committing to DB during tests; keep all writes in transaction
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

    nda_patch = patch("app.api.v1.endpoints.staff_auth.check_all_pending_agreements", return_value=(False, None, None))
    nda_patch.start()

    # Capability resolution hook for explicit canonical capability test
    orig_resolve_caps = acs.resolve_staff_capabilities
    def custom_resolve_staff_capabilities(db, staff, active_company_id, admin_scope):
        caps = orig_resolve_caps(db, staff, active_company_id, admin_scope)
        if getattr(staff, "emp_code", "") == "EMP_FINANCE_CAP":
            return set(caps) | {"finance.approve"}
        return caps

    caps_patch = patch.object(acs, "resolve_staff_capabilities", side_effect=custom_resolve_staff_capabilities)
    caps_patch.start()

    try:
        invalidate_auth_cache()

        # ── Seed Roles ──
        role_sales = session.query(StaffRole).filter(StaffRole.role_code == "test_sales_exec").first()
        if not role_sales:
            role_sales = StaffRole(role_code="test_sales_exec", role_name="Sales Executive", hierarchy_level=10)
            session.add(role_sales)
            session.flush()

        role_finance = session.query(StaffRole).filter(StaffRole.role_code == "test_finance_staff").first()
        if not role_finance:
            role_finance = StaffRole(role_code="test_finance_staff", role_name="Finance Officer", hierarchy_level=10)
            session.add(role_finance)
            session.flush()

        role_accounts = session.query(StaffRole).filter(StaffRole.role_code == "accounts").first()
        if role_accounts:
            role_accounts.hierarchy_level = 10
        else:
            role_accounts = StaffRole(role_code="accounts", role_name="Accounts Executive", hierarchy_level=10)
            session.add(role_accounts)
        session.flush()

        role_admin = session.query(StaffRole).filter(StaffRole.role_code == "test_admin_r1").first()
        if not role_admin:
            role_admin = StaffRole(role_code="test_admin_r1", role_name="Admin R1", hierarchy_level=100)
            session.add(role_admin)
            session.flush()

        role_superadmin = session.query(StaffRole).filter(StaffRole.role_code == "test_superadmin_r1").first()
        if not role_superadmin:
            role_superadmin = StaffRole(role_code="test_superadmin_r1", role_name="Platform Superadmin", hierarchy_level=150)
            session.add(role_superadmin)
            session.flush()

        # ── Seed Department ──
        dept_accounts = session.query(StaffDepartment).filter(StaffDepartment.name == "Test Accounts Dept").first()
        if not dept_accounts:
            dept_accounts = StaffDepartment(name="Test Accounts Dept", department_code="DEPT_TEST_ACC")
            session.add(dept_accounts)
            session.flush()

        # ── Seed Tenants ──
        t1 = session.query(PlatformClient).filter(PlatformClient.id == 1).first()
        if not t1:
            t1 = PlatformClient(id=1, client_code="TENANT_1", client_name="Tenant One", status="active")
            session.add(t1)
            session.flush()

        t2 = session.query(PlatformClient).filter(PlatformClient.id == 250).first()
        if not t2:
            t2 = PlatformClient(id=250, client_code="TENANT_2", client_name="Tenant Two", status="active")
            session.add(t2)
            session.flush()

        # ── Seed Companies ──
        c1 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 101).first()
        if not c1:
            c1 = AssociatedCompany(id=101, client_id=1, company_name="Test Alpha", company_code="TA", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c1)
            session.flush()

        c2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 102).first()
        if not c2:
            c2 = AssociatedCompany(id=102, client_id=1, company_name="Test Beta", company_code="TB", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c2)
            session.flush()

        c_t2 = session.query(AssociatedCompany).filter(AssociatedCompany.id == 201).first()
        if not c_t2:
            c_t2 = AssociatedCompany(id=201, client_id=250, company_name="Test Gamma", company_code="TG", is_active=True, licensed_modules=["CRM_LEADS"])
            session.add(c_t2)
            session.flush()

        # Seed Signup Category
        cat = session.query(SignupCategory).filter(SignupCategory.id == 101).first()
        if not cat:
            cat = SignupCategory(id=101, company_id=101, name="Category Alpha", slug="cat_alpha", is_active=True)
            session.add(cat)
            session.flush()

        # ─────────────────────────────────────────────────────────────────────
        # Seed Staff Personas for Option B Architecture Verification
        # ─────────────────────────────────────────────────────────────────────
        # 1. Ordinary Sales Staff (Company 101, Tenant 1) - has crm.leads.edit (level 10), NOT finance
        sales_c1 = StaffEmployee(
            emp_code="EMP_SALES_C1", full_name="Sales Executive C1", email="sales_c1@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_sales.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="OFFICE"
        )
        session.add(sales_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=sales_c1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 2. Tenant Admin (Company 101, Tenant 1) - hierarchy_level=100 (Canonical Tenant Authority)
        admin_t1 = StaffEmployee(
            emp_code="EMP_ADMIN_T1", full_name="Tenant Admin T1", email="admin_t1@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_admin.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="TENANT_ADMIN"
        )
        session.add(admin_t1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=admin_t1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 3. Platform Superadmin (Master Tenant 1, Level 150, admin_scope=PLATFORM) (Canonical Platform Authority)
        superadmin_t1 = StaffEmployee(
            emp_code="EMP_SUPERADMIN_T1", full_name="Platform Superadmin", email="superadmin@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_superadmin.id, date_of_joining=date(2026, 1, 1),
            admin_scope="PLATFORM", staff_type="OFFICE"
        )
        session.add(superadmin_t1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=superadmin_t1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 4. Employee with explicit canonical finance.approve capability (Level 10 with capability)
        finance_cap_c1 = StaffEmployee(
            emp_code="EMP_FINANCE_CAP", full_name="Finance Cap Officer", email="finance_cap@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_finance.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="OFFICE"
        )
        session.add(finance_cap_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=finance_cap_c1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 5. Legacy "FINANCE" staff_type (Level 10, no canonical finance.approve)
        legacy_finance_c1 = StaffEmployee(
            emp_code="EMP_LEGACY_FIN", full_name="Legacy Finance Staff", email="legacy_fin@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_finance.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="FINANCE"
        )
        session.add(legacy_finance_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=legacy_finance_c1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 6. Legacy "ACCOUNT" staff_type (Level 10, no canonical finance.approve)
        legacy_account_c1 = StaffEmployee(
            emp_code="EMP_LEGACY_ACC", full_name="Legacy Account Staff", email="legacy_acc@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_finance.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="ACCOUNT"
        )
        session.add(legacy_account_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=legacy_account_c1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 7. Legacy "accounts" role code (role_code="accounts", Level 10, no canonical finance.approve)
        legacy_role_c1 = StaffEmployee(
            emp_code="EMP_LEGACY_ROLE", full_name="Legacy Accounts Role Staff", email="legacy_role@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_accounts.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="OFFICE"
        )
        session.add(legacy_role_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=legacy_role_c1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 8. Legacy "Accounts" Department (dept name="Test Accounts Dept", Level 10, no canonical finance.approve)
        legacy_dept_c1 = StaffEmployee(
            emp_code="EMP_LEGACY_DEPT", full_name="Legacy Accounts Dept Staff", email="legacy_dept@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_sales.id, department_id=dept_accounts.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="OFFICE"
        )
        session.add(legacy_dept_c1)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=legacy_dept_c1.id, company_id=101, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 9. Foreign Company Financial Staff (Company 102, Tenant 1) - same tenant, different company
        staff_c2 = StaffEmployee(
            emp_code="EMP_STAFF_C2", full_name="Staff Company 102", email="staff_c2@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=1, role_id=role_finance.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="FINANCE"
        )
        session.add(staff_c2)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=staff_c2.id, company_id=102, tenant_id=1, is_primary=True, is_active=True))
        session.flush()

        # 10. Foreign Tenant Financial Staff (Company 201, Tenant 250) - completely different tenant
        staff_t2 = StaffEmployee(
            emp_code="EMP_STAFF_T2", full_name="Staff Tenant 2", email="staff_t2@test.com",
            password_hash="hash", status="active", employment_type="confirmed", kyc_status="approved",
            tenant_id=250, role_id=role_finance.id, date_of_joining=date(2026, 1, 1),
            admin_scope="CLIENT_SPECIFIC", staff_type="FINANCE"
        )
        session.add(staff_t2)
        session.flush()
        session.add(StaffCompanyMembership(staff_id=staff_t2.id, company_id=201, tenant_id=250, is_primary=True, is_active=True))
        session.flush()

        # ── Seed CRM Lead & Child Entities in Company 101, Tenant 1 ──
        lead_c1 = CRMLead(
            tenant_id=1,
            company_id=101,
            name="Lead Target Alpha",
            phone="9199990001",
            email="lead_alpha@test.com",
            status="in_progress",
            deal_value_total=100000.0,
            deal_value_received=0.0,
            deal_value_balance=100000.0
        )
        session.add(lead_c1)
        session.flush()

        lead_c1_other = CRMLead(
            tenant_id=1,
            company_id=101,
            name="Lead Target Beta",
            phone="9199990002",
            email="lead_beta@test.com",
            status="in_progress"
        )
        session.add(lead_c1_other)
        session.flush()

        deal_c1 = CRMLeadDeal(
            lead_id=lead_c1.id,
            company_id=101,
            revenue_category_id=101,
            deal_code="DEAL_TEST_001",
            deal_value_total=100000.0,
            deal_value_received=0.0,
            deal_value_balance=100000.0,
            status="active"
        )
        session.add(deal_c1)
        session.flush()

        deal_other = CRMLeadDeal(
            lead_id=lead_c1_other.id,
            company_id=101,
            revenue_category_id=101,
            deal_code="DEAL_OTHER_002",
            deal_value_total=50000.0,
            deal_value_received=0.0,
            deal_value_balance=50000.0,
            status="active"
        )
        session.add(deal_other)
        session.flush()

        # Transactions on lead_c1
        # txn_pending_1: for validation testing
        txn_pending_1 = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 1, 10, 0), amount=25000.0,
            transaction_type="partial", payment_mode="bank_transfer", validation_status="pending"
        )
        session.add(txn_pending_1)

        # txn_pending_2: for superadmin validation testing
        txn_pending_2 = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 1, 11, 0), amount=15000.0,
            transaction_type="partial", payment_mode="upi", validation_status="pending"
        )
        session.add(txn_pending_2)

        # txn_pending_3: for finance_cap capability validation testing
        txn_pending_3 = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 1, 12, 0), amount=20000.0,
            transaction_type="partial", payment_mode="cheque", validation_status="pending"
        )
        session.add(txn_pending_3)

        # txn_review_1: for finance review testing (admin)
        txn_review_1 = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 2, 10, 0), amount=12000.0,
            transaction_type="partial", payment_mode="upi", validation_status="pending"
        )
        session.add(txn_review_1)

        # txn_review_2: for finance review testing (superadmin)
        txn_review_2 = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 2, 11, 0), amount=14000.0,
            transaction_type="partial", payment_mode="upi", validation_status="pending"
        )
        session.add(txn_review_2)

        # txn_review_3: for finance review testing (finance_cap)
        txn_review_3 = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 2, 12, 0), amount=16000.0,
            transaction_type="partial", payment_mode="upi", validation_status="pending"
        )
        session.add(txn_review_3)

        # txn_validated: Already validated transaction
        txn_validated = CRMLeadTransaction(
            company_id=101, lead_id=lead_c1.id, deal_id=deal_c1.id,
            transaction_date=datetime(2026, 3, 3, 10, 0), amount=10000.0,
            transaction_type="partial", payment_mode="cash", validation_status="validated"
        )
        session.add(txn_validated)
        session.flush()

        # Revenue Entries on lead_c1
        rev_entry_1 = CRMRevenueEntry(
            company_id=101, lead_id=lead_c1.id, amount_total=100000.0,
            amount_received=25000.0, amount_balance=75000.0, approval_status="pending"
        )
        session.add(rev_entry_1)

        rev_entry_2 = CRMRevenueEntry(
            company_id=101, lead_id=lead_c1.id, amount_total=80000.0,
            amount_received=20000.0, amount_balance=60000.0, approval_status="pending"
        )
        session.add(rev_entry_2)

        rev_entry_3 = CRMRevenueEntry(
            company_id=101, lead_id=lead_c1.id, amount_total=50000.0,
            amount_received=10000.0, amount_balance=40000.0, approval_status="pending"
        )
        session.add(rev_entry_3)
        session.flush()

        # Mint JWT Tokens
        token_sales = mint_token(sales_c1.id, sales_c1.emp_code, tenant_id=1)
        token_admin = mint_token(admin_t1.id, admin_t1.emp_code, tenant_id=1)
        token_superadmin = mint_token(superadmin_t1.id, superadmin_t1.emp_code, tenant_id=1)
        token_finance_cap = mint_token(finance_cap_c1.id, finance_cap_c1.emp_code, tenant_id=1)

        token_legacy_fin = mint_token(legacy_finance_c1.id, legacy_finance_c1.emp_code, tenant_id=1)
        token_legacy_acc = mint_token(legacy_account_c1.id, legacy_account_c1.emp_code, tenant_id=1)
        token_legacy_role = mint_token(legacy_role_c1.id, legacy_role_c1.emp_code, tenant_id=1)
        token_legacy_dept = mint_token(legacy_dept_c1.id, legacy_dept_c1.emp_code, tenant_id=1)

        token_c2 = mint_token(staff_c2.id, staff_c2.emp_code, tenant_id=1)
        token_t2 = mint_token(staff_t2.id, staff_t2.emp_code, tenant_id=250)

        headers_sales = {"Authorization": f"Bearer {token_sales}"}
        headers_admin = {"Authorization": f"Bearer {token_admin}"}
        headers_superadmin = {"Authorization": f"Bearer {token_superadmin}"}
        headers_finance_cap = {"Authorization": f"Bearer {token_finance_cap}"}

        headers_legacy_fin = {"Authorization": f"Bearer {token_legacy_fin}"}
        headers_legacy_acc = {"Authorization": f"Bearer {token_legacy_acc}"}
        headers_legacy_role = {"Authorization": f"Bearer {token_legacy_role}"}
        headers_legacy_dept = {"Authorization": f"Bearer {token_legacy_dept}"}

        headers_c2 = {"Authorization": f"Bearer {token_c2}"}
        headers_t2 = {"Authorization": f"Bearer {token_t2}"}

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 1: update_lead_deal (PUT /api/v1/crm/deals/{deal_id})
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 1: update_lead_deal ---")

        # 1A: Authorized staff within Company 101 -> 200 OK
        resp = client.put(
            f"/api/v1/crm/deals/{deal_c1.id}?company_id=101",
            json={"deal_value_total": 120000.0, "notes": "Updated by authorized sales staff"},
            headers=headers_sales
        )
        assert resp.status_code == 200, f"1A Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("deal", {}).get("deal_value_total") == 120000.0
        print("✓ 1A Passed: Authorized company staff successfully updated deal (HTTP 200)")

        # 1B: Deal company_id strictly bound to parent lead company (overrides spoofed body company_id)
        resp = client.put(
            f"/api/v1/crm/deals/{deal_c1.id}?company_id=101",
            json={"company_id": 999, "notes": "Spoof attempt"},
            headers=headers_sales
        )
        assert resp.status_code == 200
        assert resp.json().get("deal", {}).get("company_id") == 101, "1B Failed: Deal company_id was mutated!"
        print("✓ 1B Passed: Deal company_id immutable and bound to parent lead (HTTP 200)")

        # 1C: Caller sends mismatched company_id query parameter -> 400 Bad Request
        resp = client.put(
            f"/api/v1/crm/deals/{deal_c1.id}?company_id=102",
            json={"notes": "Mismatched company"},
            headers=headers_sales
        )
        assert resp.status_code == 400, f"1C Failed: Expected 400, got {resp.status_code}"
        assert "mismatch" in resp.json().get("detail", "").lower()
        print("✓ 1C Passed: Mismatched company_id rejected with HTTP 400")

        # 1D: Foreign company caller (Company 102) -> 404 Not Found (Anti-enumeration)
        resp = client.put(
            f"/api/v1/crm/deals/{deal_c1.id}?company_id=102",
            json={"notes": "Cross-company attack"},
            headers=headers_c2
        )
        assert resp.status_code == 404, f"1D Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Deal not found"
        print("✓ 1D Passed: Cross-company deal update rejected with HTTP 404 (Anti-enumeration)")

        # 1E: Cross-tenant caller (Tenant 2) -> 404 Not Found (Anti-enumeration)
        resp = client.put(
            f"/api/v1/crm/deals/{deal_c1.id}?company_id=101",
            json={"notes": "Cross-tenant attack"},
            headers=headers_t2
        )
        assert resp.status_code == 404, f"1E Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Deal not found"
        print("✓ 1E Passed: Cross-tenant deal update rejected with HTTP 404 (Anti-enumeration)")

        # 1F: Non-existent deal ID (999999) -> 404 Not Found (Matches 1D and 1E exactly)
        resp = client.put(
            "/api/v1/crm/deals/999999?company_id=101",
            json={"notes": "Non-existent"},
            headers=headers_sales
        )
        assert resp.status_code == 404
        assert resp.json().get("detail") == "Deal not found"
        print("✓ 1F Passed: Non-existent deal ID yields identical HTTP 404")

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 2: update_transaction (PUT /api/v1/crm/transactions/{txn_id})
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 2: update_transaction ---")

        # 2A: Authorized staff within Company 101 -> 200 OK
        resp = client.put(
            f"/api/v1/crm/transactions/{txn_pending_1.id}?company_id=101",
            json={"amount": 30000.0, "notes": "Updated pending txn"},
            headers=headers_sales
        )
        assert resp.status_code == 200, f"2A Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("amount") == 30000.0
        print("✓ 2A Passed: Authorized company staff updated transaction (HTTP 200)")

        # 2B: Mismatched company_id query parameter -> 400 Bad Request
        resp = client.put(
            f"/api/v1/crm/transactions/{txn_pending_1.id}?company_id=102",
            json={"amount": 35000.0},
            headers=headers_sales
        )
        assert resp.status_code == 400, f"2B Failed: Expected 400, got {resp.status_code}"
        print("✓ 2B Passed: Mismatched company_id rejected with HTTP 400")

        # 2C: Cross-company caller (Company 102) -> 404 Not Found (Anti-enumeration)
        resp = client.put(
            f"/api/v1/crm/transactions/{txn_pending_1.id}?company_id=101",
            json={"amount": 99999.0},
            headers=headers_c2
        )
        assert resp.status_code == 404, f"2C Failed: Expected 404, got {resp.status_code}"
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 2C Passed: Cross-company transaction update rejected with HTTP 404 (Anti-enumeration)")

        # 2D: Cross-tenant caller (Tenant 2) -> 404 Not Found (Anti-enumeration)
        resp = client.put(
            f"/api/v1/crm/transactions/{txn_pending_1.id}?company_id=101",
            json={"amount": 99999.0},
            headers=headers_t2
        )
        assert resp.status_code == 404, f"2D Failed: Expected 404, got {resp.status_code}"
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 2D Passed: Cross-tenant transaction update rejected with HTTP 404 (Anti-enumeration)")

        # 2E: Attempt to edit already validated transaction -> 400 Bad Request
        resp = client.put(
            f"/api/v1/crm/transactions/{txn_validated.id}?company_id=101",
            json={"amount": 99999.0},
            headers=headers_sales
        )
        assert resp.status_code == 400, f"2E Failed: Expected 400, got {resp.status_code}"
        assert "cannot edit a validated transaction" in resp.json().get("detail", "").lower()
        print("✓ 2E Passed: Editing validated transaction blocked with HTTP 400")

        # 2F: Cross-lead deal binding rejected -> 400 Bad Request
        resp = client.put(
            f"/api/v1/crm/transactions/{txn_pending_1.id}?company_id=101",
            json={"deal_id": deal_other.id},
            headers=headers_sales
        )
        assert resp.status_code == 400, f"2F Failed: Expected 400, got {resp.status_code}"
        assert "deal does not belong to this lead" in resp.json().get("detail", "").lower()
        print("✓ 2F Passed: Cross-lead deal injection rejected with HTTP 400")

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 3: upload_transaction_receipt (POST /transactions/{id}/upload-receipt)
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 3: upload_transaction_receipt ---")

        fake_upload = AsyncMock(return_value={"file_name": "receipt_test.pdf", "file_path": "crm_receipts/receipt_test.pdf"})
        with patch.object(UniversalUploadService, "handle_upload", fake_upload):
            # 3A: Authorized staff within Company 101 -> 200 OK
            dummy_file = io.BytesIO(b"%PDF-1.4 test receipt file content")
            resp = client.post(
                f"/api/v1/crm/transactions/{txn_pending_1.id}/upload-receipt?company_id=101",
                files={"receipt": ("receipt.pdf", dummy_file, "application/pdf")},
                headers=headers_sales
            )
            assert resp.status_code == 200, f"3A Failed: Expected 200, got {resp.status_code}: {resp.text}"
            assert resp.json().get("success") is True
            assert fake_upload.called, "3A Failed: handle_upload was not called for authorized user"
            fake_upload.reset_mock()
            print("✓ 3A Passed: Authorized staff uploaded transaction receipt (HTTP 200)")

            # 3B: Cross-company caller (Company 102) -> 404 Not Found (Anti-enumeration)
            dummy_file = io.BytesIO(b"%PDF-1.4 test receipt file content")
            resp = client.post(
                f"/api/v1/crm/transactions/{txn_pending_1.id}/upload-receipt?company_id=101",
                files={"receipt": ("receipt.pdf", dummy_file, "application/pdf")},
                headers=headers_c2
            )
            assert resp.status_code == 404, f"3B Failed: Expected 404, got {resp.status_code}"
            assert resp.json().get("detail") == "Transaction not found"
            assert not fake_upload.called, "3B Security Violation: handle_upload called before authorization check!"
            print("✓ 3B Passed: Cross-company receipt upload blocked at HTTP 404 before file processing")

            # 3C: Cross-tenant caller (Tenant 2) -> 404 Not Found
            dummy_file = io.BytesIO(b"%PDF-1.4 test receipt file content")
            resp = client.post(
                f"/api/v1/crm/transactions/{txn_pending_1.id}/upload-receipt?company_id=101",
                files={"receipt": ("receipt.pdf", dummy_file, "application/pdf")},
                headers=headers_t2
            )
            assert resp.status_code == 404
            assert resp.json().get("detail") == "Transaction not found"
            assert not fake_upload.called, "3C Security Violation: handle_upload called for cross-tenant request!"
            print("✓ 3C Passed: Cross-tenant receipt upload blocked at HTTP 404 before file processing")

            # 3D: Company mismatch -> 400 Bad Request
            dummy_file = io.BytesIO(b"%PDF-1.4 test receipt file content")
            resp = client.post(
                f"/api/v1/crm/transactions/{txn_pending_1.id}/upload-receipt?company_id=102",
                files={"receipt": ("receipt.pdf", dummy_file, "application/pdf")},
                headers=headers_sales
            )
            assert resp.status_code == 400
            assert not fake_upload.called
            print("✓ 3D Passed: Mismatched company_id rejected with HTTP 400 before upload")

            # 3E: Upload to already validated transaction -> 400 Bad Request
            dummy_file = io.BytesIO(b"%PDF-1.4 test receipt file content")
            resp = client.post(
                f"/api/v1/crm/transactions/{txn_validated.id}/upload-receipt?company_id=101",
                files={"receipt": ("receipt.pdf", dummy_file, "application/pdf")},
                headers=headers_sales
            )
            assert resp.status_code == 400
            assert "cannot update a validated transaction" in resp.json().get("detail", "").lower()
            assert not fake_upload.called
            print("✓ 3E Passed: Validated transaction receipt upload blocked with HTTP 400")

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 4: validate_transaction (PATCH /transactions/{id}/validate)
        # Option B Strict Capability Enforcement Matrix
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 4: validate_transaction (Option B Strict Enforcement) ---")

        # 4.1 Ordinary staff with crm.leads.edit (non-finance) -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_sales
        )
        assert resp.status_code == 403, f"4.1 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 4.1 Passed: Ordinary CRM staff (level 10) rejected with HTTP 403")

        # 4.2 Legacy "FINANCE" staff_type without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_legacy_fin
        )
        assert resp.status_code == 403, f"4.2 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 4.2 Passed: Legacy 'FINANCE' staff_type without capability rejected with HTTP 403")

        # 4.3 Legacy "ACCOUNT" staff_type without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_legacy_acc
        )
        assert resp.status_code == 403, f"4.3 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 4.3 Passed: Legacy 'ACCOUNT' staff_type without capability rejected with HTTP 403")

        # 4.4 Legacy role_code="accounts" without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_legacy_role
        )
        assert resp.status_code == 403, f"4.4 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 4.4 Passed: Legacy role_code='accounts' without capability rejected with HTTP 403")

        # 4.5 Legacy department name containing 'account' without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_legacy_dept
        )
        assert resp.status_code == 403, f"4.5 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 4.5 Passed: Legacy department without capability rejected with HTTP 403")

        # 4.6 Cross-company finance staff (Company 102) -> 404 Not Found (Tier 1 Gate before Tier 2)
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_c2
        )
        assert resp.status_code == 404, f"4.6 Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 4.6 Passed: Cross-company financial staff blocked at Tier 1 with HTTP 404 (Anti-enumeration)")

        # 4.7 Cross-tenant finance staff (Tenant 2) -> 404 Not Found (Tier 1 Gate)
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_t2
        )
        assert resp.status_code == 404, f"4.7 Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 4.7 Passed: Cross-tenant financial staff blocked at Tier 1 with HTTP 404 (Anti-enumeration)")

        # 4.8 Mismatched company_id query parameter -> 400 Bad Request
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=102",
            json={"action": "validate"},
            headers=headers_admin
        )
        assert resp.status_code == 400, f"4.8 Failed: Expected 400, got {resp.status_code}"
        print("✓ 4.8 Passed: Mismatched company_id rejected with HTTP 400")

        # 4.9 Non-existent transaction ID -> 404 Not Found
        resp = client.patch(
            "/api/v1/crm/transactions/999999/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_admin
        )
        assert resp.status_code == 404
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 4.9 Passed: Non-existent transaction ID yields identical HTTP 404")

        # 4.10 Verify side effects did NOT execute during any failed attempt
        session.refresh(txn_pending_1)
        assert txn_pending_1.validation_status == "pending", "Side-effect failure: txn_pending_1 status modified!"
        assert txn_pending_1.validated_at is None, "Side-effect failure: txn_pending_1 validated_at populated!"
        assert txn_pending_1.validated_by_id is None, "Side-effect failure: txn_pending_1 validated_by_id populated!"
        print("✓ 4.10 Passed: Zero side-effects verified across all failed validation attempts")

        # 4.11 Tenant Admin with canonical authority (Level 100) -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_admin
        )
        assert resp.status_code == 200, f"4.11 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("validation_status") == "validated"
        print("✓ 4.11 Passed: Tenant Admin with canonical authority validated transaction (HTTP 200)")

        # 4.12 Platform Superadmin (Level 150, PLATFORM scope) -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_2.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_superadmin
        )
        assert resp.status_code == 200, f"4.12 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("validation_status") == "validated"
        print("✓ 4.12 Passed: Platform Superadmin validated transaction (HTTP 200)")

        # 4.13 Employee with explicit canonical finance.approve capability -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_3.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_finance_cap
        )
        assert resp.status_code == 200, f"4.13 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("validation_status") == "validated"
        print("✓ 4.13 Passed: Employee with explicit canonical finance.approve capability validated transaction (HTTP 200)")

        # 4.14 Attempt to validate already validated transaction -> 400 Bad Request
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_1.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_admin
        )
        assert resp.status_code == 400, f"4.14 Failed: Expected 400, got {resp.status_code}"
        print("✓ 4.14 Passed: Validating already validated transaction rejected with HTTP 400")

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 5: finance_review_transaction (PATCH /transactions/{id}/finance-review)
        # Option B Strict Capability Enforcement Matrix
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 5: finance_review_transaction (Option B Strict Enforcement) ---")

        # 5.1 Ordinary CRM staff (level 10) -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Ordinary staff attack"},
            headers=headers_sales
        )
        assert resp.status_code == 403, f"5.1 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 5.1 Passed: Ordinary CRM staff rejected with HTTP 403")

        # 5.2 Legacy "FINANCE" staff_type without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Legacy finance attack"},
            headers=headers_legacy_fin
        )
        assert resp.status_code == 403, f"5.2 Failed: Expected 403, got {resp.status_code}"
        print("✓ 5.2 Passed: Legacy 'FINANCE' staff_type without capability rejected with HTTP 403")

        # 5.3 Legacy "ACCOUNT" staff_type without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Legacy account attack"},
            headers=headers_legacy_acc
        )
        assert resp.status_code == 403, f"5.3 Failed: Expected 403, got {resp.status_code}"
        print("✓ 5.3 Passed: Legacy 'ACCOUNT' staff_type without capability rejected with HTTP 403")

        # 5.4 Legacy role_code="accounts" without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Legacy role attack"},
            headers=headers_legacy_role
        )
        assert resp.status_code == 403, f"5.4 Failed: Expected 403, got {resp.status_code}"
        print("✓ 5.4 Passed: Legacy role_code='accounts' without capability rejected with HTTP 403")

        # 5.5 Legacy department name containing 'account' without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Legacy dept attack"},
            headers=headers_legacy_dept
        )
        assert resp.status_code == 403, f"5.5 Failed: Expected 403, got {resp.status_code}"
        print("✓ 5.5 Passed: Legacy department without capability rejected with HTTP 403")

        # 5.6 Cross-company finance staff (Company 102) -> 404 Not Found (Tier 1 Gate)
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Cross-company attack"},
            headers=headers_c2
        )
        assert resp.status_code == 404, f"5.6 Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 5.6 Passed: Cross-company finance review blocked at Tier 1 with HTTP 404 (Anti-enumeration)")

        # 5.7 Cross-tenant finance staff (Tenant 2) -> 404 Not Found (Tier 1 Gate)
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Cross-tenant attack"},
            headers=headers_t2
        )
        assert resp.status_code == 404, f"5.7 Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 5.7 Passed: Cross-tenant finance review blocked at Tier 1 with HTTP 404 (Anti-enumeration)")

        # 5.8 Mismatched company_id query parameter -> 400 Bad Request
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=102",
            json={"action": "reject", "rejection_reason": "Company mismatch"},
            headers=headers_admin
        )
        assert resp.status_code == 400, f"5.8 Failed: Expected 400, got {resp.status_code}"
        print("✓ 5.8 Passed: Mismatched company_id rejected with HTTP 400")

        # 5.9 Non-existent transaction ID -> 404 Not Found
        resp = client.patch(
            "/api/v1/crm/transactions/999999/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Non-existent"},
            headers=headers_admin
        )
        assert resp.status_code == 404
        assert resp.json().get("detail") == "Transaction not found"
        print("✓ 5.9 Passed: Non-existent transaction ID yields identical HTTP 404")

        # 5.10 Verify side effects did NOT execute during any failed attempt
        session.refresh(txn_review_1)
        assert txn_review_1.validation_status == "pending", "Side-effect failure: txn_review_1 status modified!"
        assert txn_review_1.validated_at is None, "Side-effect failure: txn_review_1 reviewed_at populated!"
        assert txn_review_1.validated_by_id is None, "Side-effect failure: txn_review_1 reviewed_by populated!"
        print("✓ 5.10 Passed: Zero side-effects verified across all failed review attempts")

        # 5.11 Tenant Admin with canonical authority (action='reject') -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_1.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Invalid payment proof", "finance_notes": "Reviewed and rejected by Admin"},
            headers=headers_admin
        )
        assert resp.status_code == 200, f"5.11 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("validation_status") == "rejected"
        print("✓ 5.11 Passed: Tenant Admin with canonical authority rejected transaction (HTTP 200)")

        # 5.12 Platform Superadmin (action='reject') -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_2.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Suspicious transaction", "finance_notes": "Reviewed by Superadmin"},
            headers=headers_superadmin
        )
        assert resp.status_code == 200, f"5.12 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("validation_status") == "rejected"
        print("✓ 5.12 Passed: Platform Superadmin successfully reviewed transaction (HTTP 200)")

        # 5.13 Employee with explicit canonical finance.approve capability -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_review_3.id}/finance-review?company_id=101",
            json={"action": "reject", "rejection_reason": "Duplicate transaction", "finance_notes": "Reviewed by Finance Cap Officer"},
            headers=headers_finance_cap
        )
        assert resp.status_code == 200, f"5.13 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("validation_status") == "rejected"
        print("✓ 5.13 Passed: Employee with explicit canonical finance.approve capability reviewed transaction (HTTP 200)")

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 6: approve_or_reject_revenue (PATCH /revenue/{id}/approve)
        # Option B Strict Capability Enforcement Matrix
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 6: approve_or_reject_revenue (Option B Strict Enforcement) ---")

        # 6.1 Ordinary CRM staff (level 10) -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_sales
        )
        assert resp.status_code == 403, f"6.1 Failed: Expected 403, got {resp.status_code}: {resp.text}"
        assert "finance or admin staff" in resp.json().get("detail", "").lower()
        print("✓ 6.1 Passed: Ordinary CRM staff rejected with HTTP 403")

        # 6.2 Legacy "FINANCE" staff_type without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_legacy_fin
        )
        assert resp.status_code == 403, f"6.2 Failed: Expected 403, got {resp.status_code}"
        print("✓ 6.2 Passed: Legacy 'FINANCE' staff_type without capability rejected with HTTP 403")

        # 6.3 Legacy "ACCOUNT" staff_type without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_legacy_acc
        )
        assert resp.status_code == 403, f"6.3 Failed: Expected 403, got {resp.status_code}"
        print("✓ 6.3 Passed: Legacy 'ACCOUNT' staff_type without capability rejected with HTTP 403")

        # 6.4 Legacy role_code="accounts" without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_legacy_role
        )
        assert resp.status_code == 403, f"6.4 Failed: Expected 403, got {resp.status_code}"
        print("✓ 6.4 Passed: Legacy role_code='accounts' without capability rejected with HTTP 403")

        # 6.5 Legacy department name containing 'account' without capability -> 403 Forbidden
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_legacy_dept
        )
        assert resp.status_code == 403, f"6.5 Failed: Expected 403, got {resp.status_code}"
        print("✓ 6.5 Passed: Legacy department without capability rejected with HTTP 403")

        # 6.6 Cross-company finance staff (Company 102) -> 404 Not Found (Tier 1 Gate)
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_c2
        )
        assert resp.status_code == 404, f"6.6 Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Revenue entry not found"
        print("✓ 6.6 Passed: Cross-company revenue approval blocked at Tier 1 with HTTP 404 (Anti-enumeration)")

        # 6.7 Cross-tenant finance staff (Tenant 2) -> 404 Not Found (Tier 1 Gate)
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_t2
        )
        assert resp.status_code == 404, f"6.7 Failed: Expected 404, got {resp.status_code}: {resp.text}"
        assert resp.json().get("detail") == "Revenue entry not found"
        print("✓ 6.7 Passed: Cross-tenant revenue approval blocked at Tier 1 with HTTP 404 (Anti-enumeration)")

        # 6.8 Mismatched company_id query parameter -> 400 Bad Request
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=102",
            json={"action": "approve"},
            headers=headers_admin
        )
        assert resp.status_code == 400, f"6.8 Failed: Expected 400, got {resp.status_code}"
        print("✓ 6.8 Passed: Mismatched company_id rejected with HTTP 400")

        # 6.9 Non-existent revenue entry ID -> 404 Not Found
        resp = client.patch(
            "/api/v1/crm/revenue/999999/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_admin
        )
        assert resp.status_code == 404
        assert resp.json().get("detail") == "Revenue entry not found"
        print("✓ 6.9 Passed: Non-existent revenue entry ID yields identical HTTP 404")

        # 6.10 Verify side effects did NOT execute during any failed attempt
        session.refresh(rev_entry_1)
        assert rev_entry_1.approval_status == "pending", "Side-effect failure: rev_entry_1 status modified!"
        assert rev_entry_1.approved_at is None, "Side-effect failure: rev_entry_1 approved_at populated!"
        assert rev_entry_1.approved_by_id is None, "Side-effect failure: rev_entry_1 approved_by populated!"
        print("✓ 6.10 Passed: Zero side-effects verified across all failed revenue approval attempts")

        # 6.11 Tenant Admin with canonical authority (action='approve') -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_admin
        )
        assert resp.status_code == 200, f"6.11 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("approval_status") == "approved"
        print("✓ 6.11 Passed: Tenant Admin with canonical authority successfully approved revenue entry (HTTP 200)")

        # 6.12 Platform Superadmin (action='approve') -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_2.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_superadmin
        )
        assert resp.status_code == 200, f"6.12 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("approval_status") == "approved"
        print("✓ 6.12 Passed: Platform Superadmin successfully approved revenue entry (HTTP 200)")

        # 6.13 Employee with explicit canonical finance.approve capability -> 200 OK
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_3.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_finance_cap
        )
        assert resp.status_code == 200, f"6.13 Failed: Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json().get("data", {}).get("approval_status") == "approved"
        print("✓ 6.13 Passed: Employee with explicit canonical finance.approve capability approved revenue entry (HTTP 200)")

        # 6.14 Attempt to process already approved revenue entry -> 400 Bad Request
        resp = client.patch(
            f"/api/v1/crm/revenue/{rev_entry_1.id}/approve?company_id=101",
            json={"action": "approve"},
            headers=headers_admin
        )
        assert resp.status_code == 400, f"6.14 Failed: Expected 400, got {resp.status_code}"
        print("✓ 6.14 Passed: Processing already approved revenue entry rejected with HTTP 400")

        # ─────────────────────────────────────────────────────────────────────
        # OPERATION 7: Forged Tenant Token Protection
        # ─────────────────────────────────────────────────────────────────────
        print("\n--- Testing 7: Forged Tenant Isolation ---")
        # 7A: Forged token with non-existent identity / tenant -> 401 Unauthorized
        token_forged_tenant = mint_token(99999, "EMP_FORGED", tenant_id=99999)
        headers_forged = {"Authorization": f"Bearer {token_forged_tenant}"}
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_2.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_forged
        )
        assert resp.status_code == 401, f"7A Failed: Expected 401, got {resp.status_code}"
        print(f"✓ 7A Passed: Forged non-existent tenant token rejected with HTTP 401")

        # 7B: Valid foreign tenant token attacking Tenant 1 resource -> 404 Not Found (Anti-enumeration)
        resp = client.patch(
            f"/api/v1/crm/transactions/{txn_pending_2.id}/validate?company_id=101",
            json={"action": "validate"},
            headers=headers_t2
        )
        assert resp.status_code == 404, f"7B Failed: Expected 404, got {resp.status_code}"
        print(f"✓ 7B Passed: Cross-tenant attack rejected with HTTP 404 (Anti-enumeration)")

        print("\n" + "=" * 80)
        print("ALL 13 CANONICAL & CHILD-RESOURCE SECURITY SCENARIOS FULLY VERIFIED!")
        print("=" * 80)

    finally:
        caps_patch.stop()
        nda_patch.stop()
        app.dependency_overrides.clear()
        session.rollback = real_rollback
        session.close()
        transaction.rollback()
        connection.close()

        # ─────────────────────────────────────────────────────────────────────
        # Step 8: Zero Operational Database Mutation Audit
        # ─────────────────────────────────────────────────────────────────────
        post_db = SessionLocal()
        emp_count_after = post_db.execute(text("SELECT count(*) FROM staff_employees")).scalar()
        mem_count_after = post_db.execute(text("SELECT count(*) FROM staff_company_memberships")).scalar()
        comp_count_after = post_db.execute(text("SELECT count(*) FROM associated_companies")).scalar()
        client_count_after = post_db.execute(text("SELECT count(*) FROM platform_clients")).scalar()
        lead_count_after = post_db.execute(text("SELECT count(*) FROM crm_leads")).scalar()
        deal_count_after = post_db.execute(text("SELECT count(*) FROM crm_lead_deals")).scalar()
        txn_count_after = post_db.execute(text("SELECT count(*) FROM crm_lead_transactions")).scalar()
        rev_count_after = post_db.execute(text("SELECT count(*) FROM crm_revenue_entries")).scalar()
        post_db.close()

        print(f"\n[DB-MUTATION-AUDIT] staff_employees: before={emp_count_before}, after={emp_count_after}")
        print(f"[DB-MUTATION-AUDIT] staff_company_memberships: before={mem_count_before}, after={mem_count_after}")
        print(f"[DB-MUTATION-AUDIT] associated_companies: before={comp_count_before}, after={comp_count_after}")
        print(f"[DB-MUTATION-AUDIT] platform_clients: before={client_count_before}, after={client_count_after}")
        print(f"[DB-MUTATION-AUDIT] crm_leads: before={lead_count_before}, after={lead_count_after}")
        print(f"[DB-MUTATION-AUDIT] crm_lead_deals: before={deal_count_before}, after={deal_count_after}")
        print(f"[DB-MUTATION-AUDIT] crm_lead_transactions: before={txn_count_before}, after={txn_count_after}")
        print(f"[DB-MUTATION-AUDIT] crm_revenue_entries: before={rev_count_before}, after={rev_count_after}")

        assert emp_count_before == emp_count_after, "DB MUTATION DETECTED: staff_employees count mismatch!"
        assert mem_count_before == mem_count_after, "DB MUTATION DETECTED: staff_company_memberships count mismatch!"
        assert comp_count_before == comp_count_after, "DB MUTATION DETECTED: associated_companies count mismatch!"
        assert client_count_before == client_count_after, "DB MUTATION DETECTED: platform_clients count mismatch!"
        assert lead_count_before == lead_count_after, "DB MUTATION DETECTED: crm_leads count mismatch!"
        assert deal_count_before == deal_count_after, "DB MUTATION DETECTED: crm_lead_deals count mismatch!"
        assert txn_count_before == txn_count_after, "DB MUTATION DETECTED: crm_lead_transactions count mismatch!"
        assert rev_count_before == rev_count_after, "DB MUTATION DETECTED: crm_revenue_entries count mismatch!"

        print("[DB-MUTATION-AUDIT] ZERO MUTATION VERIFIED: Operational database remains 100% pristine!\n")


if __name__ == "__main__":
    test_stage2b_phase2r1_financial_child_security()
