"""
MYNTOS — SAAS LAUNCH READINESS: PHASE 3
Focused Verification Test Suite: Tenant Admin Provisioning Architectural Fix

Verifies:
1. provision_tenant_admin() atomically creates:
   - PlatformClient
   - AssociatedCompany
   - StaffRole
   - StaffEmployee
   - StaffCompanyMembership
2. Membership attributes:
   - staff_id = newly created admin.id
   - company_id = newly created AssociatedCompany.id
   - tenant_id = PlatformClient.id
   - is_primary = True
   - is_active = True
3. Auth resolution:
   - resolve_staff_memberships() returns ([company.id], company.id)
   - resolve_active_company() cleanly resolves without HTTP 403
4. Elimination of previous 403 defect:
   - Verify that with membership present, operational company access succeeds
   - Verify that without membership, access would fail-closed with 403
5. Transactional atomicity:
   - Transaction rollback leaves no orphaned client/company/employee/membership
6. Idempotency:
   - Calling provision_tenant_admin() twice preserves existing admin & membership
7. Cross-tenant isolation:
   - Newly provisioned admin cannot access another tenant's company
8. Operational database protection:
   - All tests run in isolated transactions with complete rollback.
   - Database baseline counts remain unchanged.
"""

import os
import unittest
from datetime import date
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.platform_b2b import PlatformClient
from app.models.staff_accounts import AssociatedCompany
from app.models.staff import StaffEmployee, StaffRole, StaffCompanyMembership
from app.services.platform_b2b_billing import provision_tenant_admin
from app.services.auth_context_service import resolve_staff_memberships, resolve_active_company

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/myntreal_dev")


class TestPhase3TenantAdminProvisioning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL, poolclass=NullPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

        with cls.engine.connect() as conn:
            cls.baseline_leads = conn.execute(text("SELECT COUNT(*) FROM crm_leads")).scalar()
            cls.baseline_phones = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phones")).scalar()
            cls.baseline_companies = conn.execute(text("SELECT COUNT(*) FROM associated_companies")).scalar()
            cls.baseline_employees = conn.execute(text("SELECT COUNT(*) FROM staff_employees")).scalar()
            cls.baseline_memberships = conn.execute(text("SELECT COUNT(*) FROM staff_company_memberships")).scalar()
            cls.baseline_clients = conn.execute(text("SELECT COUNT(*) FROM platform_clients")).scalar()

    @classmethod
    def tearDownClass(cls):
        with cls.engine.connect() as conn:
            current_leads = conn.execute(text("SELECT COUNT(*) FROM crm_leads")).scalar()
            current_phones = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phones")).scalar()
            current_companies = conn.execute(text("SELECT COUNT(*) FROM associated_companies")).scalar()
            current_employees = conn.execute(text("SELECT COUNT(*) FROM staff_employees")).scalar()
            current_memberships = conn.execute(text("SELECT COUNT(*) FROM staff_company_memberships")).scalar()
            current_clients = conn.execute(text("SELECT COUNT(*) FROM platform_clients")).scalar()

            assert current_leads == cls.baseline_leads, f"Lead count mutated! {current_leads} vs {cls.baseline_leads}"
            assert current_phones == cls.baseline_phones, f"Phone count mutated! {current_phones} vs {cls.baseline_phones}"
            assert current_companies == cls.baseline_companies, f"Company count mutated! {current_companies} vs {cls.baseline_companies}"
            assert current_employees == cls.baseline_employees, f"Employee count mutated! {current_employees} vs {cls.baseline_employees}"
            assert current_memberships == cls.baseline_memberships, f"Membership count mutated! {current_memberships} vs {cls.baseline_memberships}"
            assert current_clients == cls.baseline_clients, f"Client count mutated! {current_clients} vs {cls.baseline_clients}"

    def setUp(self):
        self.session = self.SessionLocal()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def _create_mock_client(self, code_suffix="T999", name="Test Corp Alpha"):
        client = PlatformClient(
            client_code=f"TC_{code_suffix}",
            client_name=name,
            contact_name="Test Admin",
            contact_email=f"admin_{code_suffix.lower()}@testcorp.com",
            contact_phone="+919876543210",
            billing_currency="INR",
            status="pending",
            is_internal=False,
        )
        self.session.add(client)
        self.session.flush()
        return client

    def test_01_provision_creates_all_entities_including_membership(self):
        """1. Successful tenant-admin provisioning creates Client, Company, Role, Employee, and Membership."""
        client = self._create_mock_client(code_suffix="T01", name="Alpha Realtors")
        res = provision_tenant_admin(self.session, client)

        self.assertEqual(res["status"], "provisioned")
        self.assertIn("employee_id", res)
        self.assertIn("membership_id", res)

        # Verify AssociatedCompany
        comp = self.session.query(AssociatedCompany).filter_by(client_id=client.id).first()
        self.assertIsNotNone(comp)
        self.assertEqual(comp.company_name, "Alpha Realtors")

        # Verify StaffEmployee
        emp = self.session.query(StaffEmployee).filter_by(id=res["employee_id"]).first()
        self.assertIsNotNone(emp)
        self.assertEqual(emp.base_company_id, comp.id)
        self.assertEqual(emp.status, "active")
        self.assertEqual(emp.tenant_id, client.id)

        # Verify StaffRole
        role = self.session.query(StaffRole).filter_by(id=emp.role_id).first()
        self.assertIsNotNone(role)
        self.assertEqual(role.role_code, "tenant_admin")

        # Verify Authoritative StaffCompanyMembership
        mem = self.session.query(StaffCompanyMembership).filter_by(id=res["membership_id"]).first()
        self.assertIsNotNone(mem)
        self.assertEqual(mem.staff_id, emp.id)
        self.assertEqual(mem.company_id, comp.id)
        self.assertEqual(mem.tenant_id, client.id)
        self.assertTrue(mem.is_primary)
        self.assertTrue(mem.is_active)

    def test_02_membership_has_correct_composite_attributes(self):
        """2. Membership has correct staff_id, company_id, tenant_id, is_primary=True, is_active=True."""
        client = self._create_mock_client(code_suffix="T02", name="Beta Properties")
        res = provision_tenant_admin(self.session, client)

        mem = self.session.query(StaffCompanyMembership).filter_by(
            staff_id=res["employee_id"],
            company_id=self.session.query(AssociatedCompany).filter_by(client_id=client.id).first().id,
        ).first()

        self.assertIsNotNone(mem)
        self.assertEqual(mem.tenant_id, client.id)
        self.assertIs(mem.is_primary, True)
        self.assertIs(mem.is_active, True)
        self.assertIsNotNone(mem.role_id)

    def test_03_provisioned_admin_resolves_auth_context(self):
        """3. Newly provisioned admin can successfully authenticate and resolve tenant_id, active_company_id, accessible_company_ids."""
        client = self._create_mock_client(code_suffix="T03", name="Gamma Realty")
        res = provision_tenant_admin(self.session, client)
        comp = self.session.query(AssociatedCompany).filter_by(client_id=client.id).first()

        # AuthContextService membership resolution
        accessible_ids, primary_id = resolve_staff_memberships(
            self.session,
            staff_id=res["employee_id"],
            tenant_id=client.id
        )

        self.assertEqual(accessible_ids, [comp.id])
        self.assertEqual(primary_id, comp.id)

        # Active company resolution (default)
        active_cid = resolve_active_company(
            requested_company_id=None,
            accessible_company_ids=accessible_ids,
            primary_company_id=primary_id,
        )
        self.assertEqual(active_cid, comp.id)

        # Active company resolution (explicit requested_company_id matching)
        active_cid_explicit = resolve_active_company(
            requested_company_id=comp.id,
            accessible_company_ids=accessible_ids,
            primary_company_id=primary_id,
            tenant_id=client.id,
            db=self.session,
        )
        self.assertEqual(active_cid_explicit, comp.id)

    def test_04_newly_provisioned_admin_does_not_receive_403(self):
        """4. Newly provisioned admin does NOT receive the previous 403 caused by missing membership."""
        client = self._create_mock_client(code_suffix="T04", name="Delta Estates")
        res = provision_tenant_admin(self.session, client)
        comp = self.session.query(AssociatedCompany).filter_by(client_id=client.id).first()

        accessible_ids, primary_id = resolve_staff_memberships(
            self.session,
            staff_id=res["employee_id"],
            tenant_id=client.id
        )

        # Must not raise HTTPException(403)
        try:
            cid = resolve_active_company(
                requested_company_id=None,
                accessible_company_ids=accessible_ids,
                primary_company_id=primary_id,
            )
            self.assertEqual(cid, comp.id)
        except HTTPException as e:
            self.fail(f"resolve_active_company unexpectedly raised HTTP {e.status_code}: {e.detail}")

    def test_05_missing_membership_regression_verification(self):
        """5. Proves that if membership is absent, auth correctly fails-closed with 403 (defending the architecture)."""
        client = self._create_mock_client(code_suffix="T05", name="Epsilon Holdings")
        res = provision_tenant_admin(self.session, client)

        # Manually delete membership to simulate the previous broken architecture state
        self.session.query(StaffCompanyMembership).filter_by(id=res["membership_id"]).delete()
        self.session.flush()

        # Verify fail-closed behavior: resolve_staff_memberships returns empty list
        accessible_ids, primary_id = resolve_staff_memberships(
            self.session,
            staff_id=res["employee_id"],
            tenant_id=client.id
        )
        self.assertEqual(accessible_ids, [])
        self.assertIsNone(primary_id)

        # Verify resolve_active_company raises HTTP 403
        with self.assertRaises(HTTPException) as ctx:
            resolve_active_company(
                requested_company_id=None,
                accessible_company_ids=accessible_ids,
                primary_company_id=primary_id,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("No operational company access", ctx.exception.detail)

    def test_06_provisioning_failure_atomicity_and_rollback(self):
        """6. Provisioning failure rolls back membership, company, and employee transaction appropriately."""
        # Create a savepoint / subtransaction
        sub_tx = self.session.begin_nested()
        client = self._create_mock_client(code_suffix="T06", name="Zeta Infrastructure")
        res = provision_tenant_admin(self.session, client)
        emp_id = res["employee_id"]
        mem_id = res["membership_id"]

        # Confirm entities exist inside transaction
        self.assertIsNotNone(self.session.query(StaffEmployee).filter_by(id=emp_id).first())
        self.assertIsNotNone(self.session.query(StaffCompanyMembership).filter_by(id=mem_id).first())

        # Simulate failure and rollback
        sub_tx.rollback()

        # Confirm rollback cleanly removed all entities
        self.assertIsNone(self.session.query(StaffEmployee).filter_by(id=emp_id).first())
        self.assertIsNone(self.session.query(StaffCompanyMembership).filter_by(id=mem_id).first())
        self.assertIsNone(self.session.query(PlatformClient).filter_by(client_code="TC_T06").first())

    def test_07_idempotent_reprovisioning_preserves_membership(self):
        """7. Reprovisioning an existing tenant admin preserves membership without duplicating."""
        client = self._create_mock_client(code_suffix="T07", name="Eta Investments")
        res1 = provision_tenant_admin(self.session, client)
        self.assertEqual(res1["status"], "provisioned")

        # Second call for the same client
        res2 = provision_tenant_admin(self.session, client)
        self.assertEqual(res2["status"], "already_exists")
        self.assertEqual(res2["employee_id"], res1["employee_id"])
        self.assertEqual(res2["membership_id"], res1["membership_id"])

        # Confirm exactly 1 membership row exists
        mems = self.session.query(StaffCompanyMembership).filter_by(
            staff_id=res1["employee_id"]
        ).all()
        self.assertEqual(len(mems), 1)

    def test_08_cross_tenant_isolation_remains_intact(self):
        """8. Cross-tenant access is strictly denied (cannot access other tenant companies)."""
        client = self._create_mock_client(code_suffix="T08", name="Theta Commercial")
        res = provision_tenant_admin(self.session, client)

        accessible_ids, primary_id = resolve_staff_memberships(
            self.session,
            staff_id=res["employee_id"],
            tenant_id=client.id
        )

        # Attempt to access Company #1 (Tenant #1 / Mynt Real)
        with self.assertRaises(HTTPException) as ctx:
            resolve_active_company(
                requested_company_id=1,
                accessible_company_ids=accessible_ids,
                primary_company_id=primary_id,
                tenant_id=client.id,
                db=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access denied to requested company #1", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
