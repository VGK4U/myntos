"""
Stage 2B Phase 2R-3A: Phone Duplicate & Existence Isolation Test Suite

Exercises and verifies the phone duplicate resolution mechanisms across CRM:
1. GET /api/v1/crm/leads/check-duplicate
2. POST /api/v1/crm/leads
3. POST /api/v1/crm/unified-my-leads
4. Direct _resolve_phone_duplicate helper isolation invariants

Authoritative Business & Security Rules Verified:
A. Same tenant + same company:
   - Matching phone treated as duplicate (check-duplicate returns True, POST routes return 409 Conflict).
   - Minimal/sanitized PII in error and pre-flight payloads.
B. Same tenant + different company:
   - Sibling company phone is NOT treated as a duplicate.
   - Lead creation succeeds without 409 Conflict.
C. Same tenant + unauthorized company:
   - Completely invisible to caller.
   - HTTP 403 Forbidden raised on foreign/unauthorized company parameter tampering.
D. Different tenant:
   - Completely invisible. Same phone in foreign tenant never blocks creation.
E. Zero DB mutations:
   - Operational database verified 100% PRISTINE via pre/post row count assertions.
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
from app.models.crm import CRMLead
from app.api.v1.endpoints.crm import _resolve_phone_duplicate
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


def test_stage2b_phase2r3a_phone_duplicate_security():
    print("\n" + "=" * 80)
    print("STAGE 2B PHASE 2R-3A: PHONE DUPLICATE & EXISTENCE ISOLATION SECURITY SUITE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 0: Baseline Row Counts (Operational DB Read-Only Gate)
    # ─────────────────────────────────────────────────────────────────────────
    pre_db = SessionLocal()
    table_names = [
        'staff_employees',
        'staff_company_memberships',
        'associated_companies',
        'platform_clients',
        'staff_roles',
        'staff_departments',
        'crm_leads',
        'crm_lead_deals',
        'crm_lead_transactions',
        'crm_revenue_entries',
        'crm_lead_sync_configs',
        'lead_sync_configs',
        'facebook_pages',
        'meta_form_mappings'
    ]
    counts_before = {}
    for t in table_names:
        counts_before[t] = pre_db.execute(text(f"SELECT count(*) FROM {t}")).scalar()
    pre_db.close()

    print("\n[STEP 0] Baseline Row Counts:")
    for t, c in counts_before.items():
        print(f"  {t:30}: {c}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Transaction Rollback Isolation Setup
    # ─────────────────────────────────────────────────────────────────────────
    connection = engine.connect()
    transaction = connection.begin()
    # Temporarily drop legacy global unique index inside transaction so same-phone across sibling companies can be exercised
    # Transaction rollback will restore the index completely
    connection.execute(text("DROP INDEX IF EXISTS ux_crm_leads_phone"))
    session = SessionLocal(bind=connection)

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
        # ─────────────────────────────────────────────────────────────────────
        # Step 2: Test Fixture Provisioning
        # ─────────────────────────────────────────────────────────────────────
        # Tenant 2 Client
        t2_client = PlatformClient(
            id=9920,
            client_code="PH2R3A_T2_CLIENT",
            client_name="Phase 2R-3A Tenant 2 Corp",
            status="active"
        )
        session.add(t2_client)
        session.flush()

        # Companies:
        # Co 1 (Tenant 1)
        # Co 2 (Tenant 1)
        # Co 9920 (Tenant 2)
        co_t2 = AssociatedCompany(
            id=9920,
            company_code="CO_T2_9920",
            company_name="Tenant 2 Operations LLC",
            company_type="SUBSIDIARY",
            client_id=9920,
            is_active=True
        )
        session.add(co_t2)
        session.flush()

        # Staff Role
        role_standard = session.query(StaffRole).first()
        role_id_t1 = role_standard.id if role_standard else 1

        # Staff Personas:
        # 1. emp_t1_c1: Tenant 1, member of Company 1 ONLY
        emp_t1_c1 = StaffEmployee(
            id=9921,
            emp_code="EMP_T1_C1_ONLY",
            first_name="Alice",
            last_name="T1C1",
            full_name="Alice T1C1",
            email="alice.t1c1@test.org",
            password_hash="test_pwd_hash",
            date_of_joining=date(2026, 1, 1),
            kyc_status="approved",
            employment_type="confirmed",
            tenant_id=1,
            base_company_id=1,
            staff_type="INTERNAL",
            status="active",
            is_deleted=False,
            role_id=role_id_t1
        )
        session.add(emp_t1_c1)
        session.flush()

        mem_t1_c1 = StaffCompanyMembership(
            staff_id=emp_t1_c1.id,
            company_id=1,
            tenant_id=1,
            role_id=role_id_t1,
            is_primary=True,
            is_active=True
        )
        session.add(mem_t1_c1)
        session.flush()

        # 2. emp_t1_multi: Tenant 1, member of Company 1 AND Company 2
        emp_t1_multi = StaffEmployee(
            id=9922,
            emp_code="EMP_T1_MULTI",
            first_name="Bob",
            last_name="T1Multi",
            full_name="Bob T1Multi",
            email="bob.t1multi@test.org",
            password_hash="test_pwd_hash",
            date_of_joining=date(2026, 1, 1),
            kyc_status="approved",
            employment_type="confirmed",
            tenant_id=1,
            base_company_id=1,
            staff_type="INTERNAL",
            status="active",
            is_deleted=False,
            role_id=role_id_t1
        )
        session.add(emp_t1_multi)
        session.flush()

        mem_t1_m1 = StaffCompanyMembership(staff_id=emp_t1_multi.id, company_id=1, tenant_id=1, role_id=role_id_t1, is_primary=True, is_active=True)
        mem_t1_m2 = StaffCompanyMembership(staff_id=emp_t1_multi.id, company_id=2, tenant_id=1, role_id=role_id_t1, is_primary=False, is_active=True)
        session.add_all([mem_t1_m1, mem_t1_m2])
        session.flush()

        # 3. emp_t2: Tenant 2, member of Company 9920
        emp_t2 = StaffEmployee(
            id=9923,
            emp_code="EMP_T2_USER",
            first_name="Carol",
            last_name="T2User",
            full_name="Carol T2User",
            email="carol.t2@test.org",
            password_hash="test_pwd_hash",
            date_of_joining=date(2026, 1, 1),
            kyc_status="approved",
            employment_type="confirmed",
            tenant_id=9920,
            base_company_id=9920,
            staff_type="INTERNAL",
            status="active",
            is_deleted=False,
            role_id=role_id_t1
        )
        session.add(emp_t2)
        session.flush()

        mem_t2 = StaffCompanyMembership(staff_id=emp_t2.id, company_id=9920, tenant_id=9920, role_id=role_id_t1, is_primary=True, is_active=True)
        session.add(mem_t2)
        session.flush()

        # Inactive owner for inactive-owner test in Tenant 1, Company 1
        emp_t1_inactive = StaffEmployee(
            id=9924,
            emp_code="EMP_T1_INACTIVE",
            first_name="Dan",
            last_name="Inactive",
            full_name="Dan Inactive",
            email="dan.inactive@test.org",
            password_hash="test_pwd_hash",
            date_of_joining=date(2026, 1, 1),
            kyc_status="approved",
            employment_type="confirmed",
            tenant_id=1,
            base_company_id=1,
            staff_type="INTERNAL",
            status="inactive",
            is_deleted=False,
            role_id=role_id_t1
        )
        session.add(emp_t1_inactive)
        session.flush()

        # Seed CRM Leads:
        # A. Lead in Tenant 1, Company 1 (phone: 9876511111, active owner)
        lead_t1_c1 = CRMLead(
            id=99201,
            tenant_id=1,
            company_id=1,
            name="Lead T1 C1 Active",
            phone="9876511111",
            alternate_phone="9876511112",
            status="in_progress",
            primary_owner_type="staff",
            primary_owner_id=emp_t1_c1.id,
            handler_type="staff",
            handler_id=emp_t1_c1.emp_code
        )
        # B. Lead in Tenant 1, Company 1 with INACTIVE owner (phone: 9876511113)
        lead_t1_c1_inact = CRMLead(
            id=99202,
            tenant_id=1,
            company_id=1,
            name="Lead T1 C1 Inactive Owner",
            phone="9876511113",
            status="new",
            primary_owner_type="staff",
            primary_owner_id=emp_t1_inactive.id
        )
        # C. Lead in Tenant 1, Company 2 (Sibling Company) (phone: 9876522222 and 9876522223)
        lead_t1_c2 = CRMLead(
            id=99203,
            tenant_id=1,
            company_id=2,
            name="Lead T1 Sibling C2",
            phone="9876522222",
            status="new"
        )
        lead_t1_c2_b = CRMLead(
            id=99205,
            tenant_id=1,
            company_id=2,
            name="Lead T1 Sibling C2 B",
            phone="9876522223",
            status="new"
        )
        # D. Lead in Tenant 2, Company 9920 (Foreign Tenant) (phone: 9876599999 and 9876599998)
        lead_t2_c99 = CRMLead(
            id=99204,
            tenant_id=9920,
            company_id=9920,
            name="Lead T2 Foreign Tenant",
            phone="9876599999",
            status="new"
        )
        lead_t2_c99_b = CRMLead(
            id=99206,
            tenant_id=9920,
            company_id=9920,
            name="Lead T2 Foreign Tenant B",
            phone="9876599998",
            status="new"
        )
        session.add_all([lead_t1_c1, lead_t1_c1_inact, lead_t1_c2, lead_t1_c2_b, lead_t2_c99, lead_t2_c99_b])
        session.flush()

        # Tokens & Headers
        token_t1_c1 = mint_token(emp_t1_c1.id, emp_t1_c1.emp_code, tenant_id=1)
        headers_t1_c1 = {"Authorization": f"Bearer {token_t1_c1}"}

        token_t1_multi = mint_token(emp_t1_multi.id, emp_t1_multi.emp_code, tenant_id=1)
        headers_t1_multi = {"Authorization": f"Bearer {token_t1_multi}"}

        token_t2 = mint_token(emp_t2.id, emp_t2.emp_code, tenant_id=9920)
        headers_t2 = {"Authorization": f"Bearer {token_t2}"}

        invalidate_auth_cache()

        print("\n[STEP 2] Test Fixtures Initialized Successfully.")

        # ─────────────────────────────────────────────────────────────────────
        # Step 3: Direct Helper Unit Security Tests (_resolve_phone_duplicate)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 3] Testing _resolve_phone_duplicate Direct Helper Security Invariants...")

        # 3.1 Same tenant + same company match
        existing, owner, owner_active = _resolve_phone_duplicate("9876511111", None, session, tenant_id=1, company_id=1)
        assert existing is not None and existing.id == 99201, "Expected lead 99201 to be found"
        assert owner is not None and owner.id == emp_t1_c1.id, "Expected owner to match emp_t1_c1"
        assert owner_active is True, "Expected owner_active to be True"
        print("  ✓ 3.1 Same tenant + same company duplicate resolved correctly.")

        # 3.2 Alternate phone match
        existing, _, _ = _resolve_phone_duplicate(None, "9876511112", session, tenant_id=1, company_id=1)
        assert existing is not None and existing.id == 99201, "Expected lead 99201 via alternate_phone"
        print("  ✓ 3.2 Alternate phone duplicate resolved correctly.")

        # 3.3 Same tenant + sibling company (DO NOT treat as duplicate)
        existing, _, _ = _resolve_phone_duplicate("9876522222", None, session, tenant_id=1, company_id=1)
        assert existing is None, "Sibling company phone must NOT be duplicate for Company 1"
        existing_c2, _, _ = _resolve_phone_duplicate("9876522222", None, session, tenant_id=1, company_id=2)
        assert existing_c2 is not None and existing_c2.id == 99203, "Sibling company phone matches within Company 2"
        print("  ✓ 3.3 Sibling company phone isolation verified (isolated by company_id).")

        # 3.4 Cross-tenant isolation (foreign tenant lead completely invisible)
        existing, _, _ = _resolve_phone_duplicate("9876599999", None, session, tenant_id=1, company_id=1)
        assert existing is None, "Foreign tenant phone must NOT match in Tenant 1"
        existing_t2, _, _ = _resolve_phone_duplicate("9876599999", None, session, tenant_id=9920, company_id=9920)
        assert existing_t2 is not None and existing_t2.id == 99204, "Foreign tenant phone matches within Tenant 2"
        print("  ✓ 3.4 Cross-tenant isolation verified (isolated by tenant_id).")

        # 3.5 Inactive owner resolution
        existing, owner, owner_active = _resolve_phone_duplicate("9876511113", None, session, tenant_id=1, company_id=1)
        assert existing is not None and existing.id == 99202
        assert owner is not None and owner.id == emp_t1_inactive.id
        assert owner_active is False, "Expected owner_active to be False for inactive staff"
        print("  ✓ 3.5 Inactive owner detected correctly.")

        # 3.6 Unscoped safety guard (None tenant or company returns None safely)
        existing, _, _ = _resolve_phone_duplicate("9876511111", None, session, tenant_id=None, company_id=1)
        assert existing is None, "Must not query when tenant_id is None"
        existing, _, _ = _resolve_phone_duplicate("9876511111", None, session, tenant_id=1, company_id=None)
        assert existing is None, "Must not query when company_id is None"
        print("  ✓ 3.6 Unscoped safety guard verified.")

        # ─────────────────────────────────────────────────────────────────────
        # Step 4: GET /api/v1/crm/leads/check-duplicate Security Invariants
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 4] Testing GET /api/v1/crm/leads/check-duplicate...")

        # 4.1 Fresh phone in authorized company -> duplicate: False
        r = client.get("/api/v1/crm/leads/check-duplicate?phone=9000011111&company_id=1", headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json() == {"duplicate": False}, f"Expected duplicate: False, got {r.json()}"
        print("  ✓ 4.1 Fresh phone returns duplicate: False.")

        # 4.2 Same tenant + same company duplicate -> duplicate: True with sanitized lead & owner info
        r = client.get("/api/v1/crm/leads/check-duplicate?phone=9876511111&company_id=1", headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["duplicate"] is True, f"Expected duplicate: True, got {data}"
        assert data["lead"]["id"] == 99201
        assert data["lead"]["name"] == "Lead T1 C1 Active"
        assert data["lead"]["company_id"] == 1
        assert data["owner"]["id"] == emp_t1_c1.id
        assert data["owner_active"] is True
        # Privacy verification: verify sensitive internal fields are NOT present
        assert "password" not in str(data)
        assert "salary" not in str(data)
        print("  ✓ 4.2 Same-company duplicate returns duplicate: True with sanitized details.")

        # 4.3 Same tenant + sibling company phone -> duplicate: False for Company 1
        r = client.get("/api/v1/crm/leads/check-duplicate?phone=9876522222&company_id=1", headers=headers_t1_c1)
        assert r.status_code == 200
        assert r.json() == {"duplicate": False}, f"Sibling company phone must return duplicate: False for Company 1, got {r.json()}"
        print("  ✓ 4.3 Sibling company phone is NOT duplicate in Company 1.")

        # 4.4 Cross-tenant phone -> duplicate: False
        r = client.get("/api/v1/crm/leads/check-duplicate?phone=9876599999&company_id=1", headers=headers_t1_c1)
        assert r.status_code == 200
        assert r.json() == {"duplicate": False}, f"Cross-tenant phone must return duplicate: False, got {r.json()}"
        print("  ✓ 4.4 Cross-tenant phone is completely invisible (duplicate: False).")

        # 4.5 Unauthorized company tampering -> HTTP 403 Forbidden
        # emp_t1_c1 is NOT a member of Company 2
        r = client.get("/api/v1/crm/leads/check-duplicate?phone=9876522222&company_id=2", headers=headers_t1_c1)
        assert r.status_code == 403, f"Expected 403 Forbidden for unauthorized company_id=2, got {r.status_code}: {r.text}"
        print("  ✓ 4.5 Anti-tampering: HTTP 403 on unauthorized company_id.")

        # 4.6 Foreign tenant company tampering -> HTTP 403 Forbidden
        r = client.get("/api/v1/crm/leads/check-duplicate?phone=9876599999&company_id=9920", headers=headers_t1_c1)
        assert r.status_code == 403, f"Expected 403 Forbidden for foreign company_id=9920, got {r.status_code}: {r.text}"
        print("  ✓ 4.6 Anti-tampering: HTTP 403 on foreign tenant company_id.")

        # ─────────────────────────────────────────────────────────────────────
        # Step 5: POST /api/v1/crm/leads Duplicate Security Invariants
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 5] Testing POST /api/v1/crm/leads...")

        # 5.1 Fresh phone in authorized company -> 200 OK
        lead_payload_fresh = {
            "name": "New Fresh Lead",
            "phone": "9000022222",
            "status": "new"
        }
        r = client.post("/api/v1/crm/leads?company_id=1", json=lead_payload_fresh, headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("success") is True
        print("  ✓ 5.1 Fresh lead creation succeeded.")

        # 5.2 Same tenant + same company duplicate -> HTTP 409 Conflict
        lead_payload_dup = {
            "name": "Duplicate Lead Attempt",
            "phone": "9876511111",
            "status": "new"
        }
        r = client.post("/api/v1/crm/leads?company_id=1", json=lead_payload_dup, headers=headers_t1_c1)
        assert r.status_code == 409, f"Expected 409 Conflict, got {r.status_code}: {r.text}"
        err = r.json()
        assert err["detail"]["type"] == "duplicate_lead"
        assert err["detail"]["lead_id"] == 99201
        print("  ✓ 5.2 Same-company duplicate correctly blocked with HTTP 409 Conflict.")

        # 5.3 Same tenant + sibling company phone -> 200 OK (CREATION PERMITTED!)
        # Phone 9876522222 exists in Company 2. Creating in Company 1 must NOT be blocked!
        lead_payload_sibling = {
            "name": "Permitted Sibling Lead",
            "phone": "9876522222",
            "status": "new"
        }
        r = client.post("/api/v1/crm/leads?company_id=1", json=lead_payload_sibling, headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200 OK (creation allowed in sibling company), got {r.status_code}: {r.text}"
        assert r.json().get("success") is True
        created_data = r.json().get("data")
        assert created_data["phone"] == "9876522222"
        assert created_data["company_id"] == 1
        print("  ✓ 5.3 Sibling company duplicate creation permitted (Rule B verified).")

        # 5.4 Cross-tenant phone -> 200 OK (CREATION PERMITTED!)
        # Phone 9876599999 exists in Tenant 2. Creating in Tenant 1 must NOT be blocked!
        lead_payload_cross_tenant = {
            "name": "Permitted Cross-Tenant Lead",
            "phone": "9876599999",
            "status": "new"
        }
        r = client.post("/api/v1/crm/leads?company_id=1", json=lead_payload_cross_tenant, headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200 OK (creation allowed across tenants), got {r.status_code}: {r.text}"
        assert r.json().get("success") is True
        assert r.json().get("data")["company_id"] == 1
        print("  ✓ 5.4 Cross-tenant duplicate creation permitted (Rule D verified).")

        # 5.5 Anti-tampering on unauthorized company -> HTTP 403 Forbidden
        r = client.post("/api/v1/crm/leads?company_id=2", json=lead_payload_fresh, headers=headers_t1_c1)
        assert r.status_code == 403, f"Expected 403 Forbidden for company_id=2, got {r.status_code}: {r.text}"
        print("  ✓ 5.5 Anti-tampering: HTTP 403 on POST /leads with unauthorized company.")

        # ─────────────────────────────────────────────────────────────────────
        # Step 6: POST /api/v1/crm/unified-my-leads Duplicate Security Invariants
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 6] Testing POST /api/v1/crm/unified-my-leads...")

        # 6.1 Fresh phone in authorized company -> 200 OK
        unified_payload_fresh = {
            "name": "Unified Fresh Lead",
            "phone": "9000033333",
            "company_id": 1,
            "status": "new"
        }
        r = client.post("/api/v1/crm/unified-my-leads", json=unified_payload_fresh, headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("success") is True
        print("  ✓ 6.1 Unified fresh lead creation succeeded.")

        # 6.2 Same tenant + same company duplicate -> HTTP 409 Conflict
        unified_payload_dup = {
            "name": "Unified Duplicate Lead",
            "phone": "9876511111",
            "company_id": 1,
            "status": "new"
        }
        r = client.post("/api/v1/crm/unified-my-leads", json=unified_payload_dup, headers=headers_t1_c1)
        assert r.status_code == 409, f"Expected 409 Conflict, got {r.status_code}: {r.text}"
        assert r.json()["detail"]["type"] == "duplicate_lead"
        print("  ✓ 6.2 Unified same-company duplicate blocked with HTTP 409 Conflict.")

        # 6.3 Same tenant + sibling company phone -> 200 OK (CREATION PERMITTED!)
        unified_payload_sibling = {
            "name": "Unified Sibling Lead",
            "phone": "9876522223",
            "company_id": 1,
            "status": "new"
        }
        r = client.post("/api/v1/crm/unified-my-leads", json=unified_payload_sibling, headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}: {r.text}"
        assert r.json().get("success") is True
        print("  ✓ 6.3 Unified sibling company duplicate creation permitted.")

        # 6.4 Cross-tenant phone -> 200 OK (CREATION PERMITTED!)
        unified_payload_cross_tenant = {
            "name": "Unified Cross-Tenant Lead",
            "phone": "9876599998",
            "company_id": 1,
            "status": "new"
        }
        r = client.post("/api/v1/crm/unified-my-leads", json=unified_payload_cross_tenant, headers=headers_t1_c1)
        assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}: {r.text}"
        assert r.json().get("success") is True
        print("  ✓ 6.4 Unified cross-tenant duplicate creation permitted.")

        # 6.5 Anti-tampering on unauthorized company -> HTTP 403 Forbidden
        unified_payload_unauth = {
            "name": "Unified Tampering Lead",
            "phone": "9000044444",
            "company_id": 2,
            "status": "new"
        }
        r = client.post("/api/v1/crm/unified-my-leads", json=unified_payload_unauth, headers=headers_t1_c1)
        assert r.status_code == 403, f"Expected 403 Forbidden, got {r.status_code}: {r.text}"
        print("  ✓ 6.5 Anti-tampering: HTTP 403 on POST /unified-my-leads with unauthorized company.")

        print("\n" + "=" * 80)
        print("ALL BATCH 2R-3A PHONE DUPLICATE SECURITY TESTS PASSED PERFECTLY!")
        print("=" * 80)

    finally:
        nda_patch.stop()
        # Clean up dependency override
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 7: Post-Test Row Count Verification (Zero DB Mutations Assertion)
    # ─────────────────────────────────────────────────────────────────────────
    post_db = SessionLocal()
    counts_after = {}
    for t in table_names:
        counts_after[t] = post_db.execute(text(f"SELECT count(*) FROM {t}")).scalar()
    post_db.close()

    print("\n[STEP 7] Verifying Operational DB Row Counts (Zero Mutations):")
    all_matched = True
    for t in table_names:
        before = counts_before[t]
        after = counts_after[t]
        delta = after - before
        status_str = "MATCHED (PRISTINE)" if delta == 0 else f"MUTATED (delta={delta:+d})"
        if delta != 0:
            all_matched = False
        print(f"  {t:30}: before={before:5d}, after={after:5d} -> {status_str}")

    assert all_matched, "DATABASE MUTATION DETECTED! Test did not leave operational DB pristine."
    print("\n[SUCCESS] Operational database is 100% UNMUTATED and PRISTINE.\n")


if __name__ == "__main__":
    test_stage2b_phase2r3a_phone_duplicate_security()
