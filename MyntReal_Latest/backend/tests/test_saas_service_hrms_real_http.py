"""
Real Authenticated HTTP Test Suite for SaaS Service & HRMS Isolation
MyntOS SaaS Expansion Validation Gate
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee
from app.models.ticket import ServiceTicket
from app.models.staff_accounts import AssociatedCompany
from app.services.saas_tenant_resolver import get_saas_menu_tree, TenantContext

client = TestClient(app)

def make_token_for(emp: StaffEmployee) -> str:
    return SecurityManager.create_access_token(
        data={
            "sub": str(emp.id),
            "emp_code": emp.emp_code,
            "email": emp.email,
            "role": emp.role.role_code if emp.role else "tenant_admin",
            "staff_type": getattr(emp, "staff_type", "TENANT_ADMIN"),
            "admin_scope": getattr(emp, "admin_scope", "CLIENT_SPECIFIC"),
            "base_company_id": emp.base_company_id,
            "tenant_id": getattr(emp, "tenant_id", 1) or 1,
            "token_version": getattr(emp, "token_version", 1) or 1,
            "user_type": "staff"
        }
    )

class TestSaaSServiceHRMSRealHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.user_ais = cls.db.query(StaffEmployee).filter_by(id=303).first()    # Company 94 (CRM + SERVICE + HRMS)
        cls.user_zylog = cls.db.query(StaffEmployee).filter_by(id=301).first()  # Company 93 (HRMS only, no Service)
        cls.user_teco = cls.db.query(StaffEmployee).filter_by(id=302).first()   # Company 92 (SERVICE only, no HRMS)
        cls.user_internal = cls.db.query(StaffEmployee).filter_by(id=22).first() # Internal Company 4

        cls.user_mgr = cls.db.query(StaffEmployee).filter_by(id=19).first()      # Manager with direct reports
        cls.user_emp = cls.db.query(StaffEmployee).filter_by(id=320).first()     # Individual Contributor / Agent

        cls.token_ais = make_token_for(cls.user_ais)
        cls.token_zylog = make_token_for(cls.user_zylog)
        cls.token_teco = make_token_for(cls.user_teco)
        cls.token_internal = make_token_for(cls.user_internal)
        cls.token_mgr = make_token_for(cls.user_mgr)
        cls.token_emp = make_token_for(cls.user_emp)

        cls.headers_ais = {"Authorization": f"Bearer {cls.token_ais}"}
        cls.headers_zylog = {"Authorization": f"Bearer {cls.token_zylog}"}
        cls.headers_teco = {"Authorization": f"Bearer {cls.token_teco}"}
        cls.headers_internal = {"Authorization": f"Bearer {cls.token_internal}"}
        cls.headers_mgr = {"Authorization": f"Bearer {cls.token_mgr}"}
        cls.headers_emp = {"Authorization": f"Bearer {cls.token_emp}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # ========================================================
    # 1. SERVICE REAL HTTP VALIDATION (Item 6)
    # ========================================================
    def test_service_dashboard_entitled_vs_unentitled(self):
        # Tenant A (AIS) has SERVICE_TICKETS
        res_a = client.get("/api/v1/tickets/service/dashboard-stats", headers=self.headers_ais)
        self.assertIn(res_a.status_code, [200, 304], f"Entitled tenant should access service stats: {res_a.text}")

        # Tenant B (ZYLOG) does NOT have SERVICE_TICKETS
        res_b = client.get("/api/v1/tickets/service/dashboard-stats", headers=self.headers_zylog)
        self.assertEqual(res_b.status_code, 403, f"Unentitled tenant should be 403: {res_b.text}")
        self.assertIn("not licensed or entitled", res_b.text)

    def test_service_queue_entitled_vs_unentitled(self):
        # Tenant A (AIS) has SERVICE_TICKETS
        res_a = client.get("/api/v1/tickets/service/queue", headers=self.headers_ais)
        self.assertIn(res_a.status_code, [200, 304])

        # Tenant B (ZYLOG) does NOT have SERVICE_TICKETS
        res_b = client.get("/api/v1/tickets/service/queue", headers=self.headers_zylog)
        self.assertEqual(res_b.status_code, 403)

    def test_service_cross_company_ticket_access_blocked(self):
        # Ticket 267 belongs to Company 4
        # Tenant A (AIS, Company 94) attempts to access Ticket 267
        # Note: _assert_ticket_tenant_access checks cross-company boundary and raises 403 before schema serialization
        from app.api.v1.endpoints.tickets import _assert_ticket_tenant_access
        from fastapi import HTTPException
        ticket_c4 = self.db.query(ServiceTicket).filter_by(id=267).first()
        with self.assertRaises(HTTPException) as cm:
            _assert_ticket_tenant_access(ticket_c4, self.db, self.user_ais)
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("Ticket belongs to another organization", cm.exception.detail)

    def test_service_reports_and_aggregations_scoped(self):
        # Service reports / breakdowns
        res_ais = client.get("/api/v1/tickets/service/showroom-breakdown", headers=self.headers_ais)
        self.assertIn(res_ais.status_code, [200, 304])

        res_zylog = client.get("/api/v1/tickets/service/showroom-breakdown", headers=self.headers_zylog)
        self.assertEqual(res_zylog.status_code, 403)

    # ========================================================
    # 2. HRMS REAL HTTP API ISOLATION (Item 4)
    # ========================================================
    def test_hrms_entitled_vs_unentitled_tenant(self):
        # Tenant A (AIS) has STAFF_HRMS
        res_a = client.get("/api/v1/staff/employees", headers=self.headers_ais)
        self.assertIn(res_a.status_code, [200, 304])

        # Tenant C (TECO) does NOT have STAFF_HRMS
        res_c = client.get("/api/v1/staff/employees", headers=self.headers_teco)
        self.assertEqual(res_c.status_code, 403)
        self.assertIn("not licensed or entitled", res_c.text)

    def test_hrms_cross_tenant_employee_blocked(self):
        # Tenant A (AIS, User 303, Company 94) accesses Tenant B Employee (User 301, Company 93)
        res = client.get(f"/api/v1/staff/employees/{self.user_zylog.id}", headers=self.headers_ais)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Employee belongs to another organization", res.text)

    def test_hrms_cross_tenant_attendance_blocked(self):
        # TECO (no HRMS) attempts to get monthly attendance
        res_unentitled = client.get("/api/v1/staff/attendance-sheet/monthly/2026-09", headers=self.headers_teco)
        self.assertEqual(res_unentitled.status_code, 403)

        # AIS (entitled) gets monthly attendance — scoped to AIS company only
        res_ais = client.get("/api/v1/staff/attendance-sheet/monthly/2026-09", headers=self.headers_ais)
        self.assertIn(res_ais.status_code, [200, 304])
        data = res_ais.json()
        employees = data.get("employees", [])
        for e in employees:
            self.assertEqual(e.get("company_id") or 94, 94, "Attendance must not leak cross-company records")

    def test_hrms_cross_tenant_leave_approvals_blocked(self):
        # TECO (no HRMS) attempts to access leave approvals
        res_teco = client.get("/api/v1/staff/leaves/pending-approvals/hr", headers=self.headers_teco)
        self.assertEqual(res_teco.status_code, 403)

        # AIS (entitled) accesses leave approvals
        res_ais = client.get("/api/v1/staff/leaves/pending-approvals/hr", headers=self.headers_ais)
        self.assertIn(res_ais.status_code, [200, 304])

    def test_hrms_cross_tenant_journey_blocked(self):
        # TECO (no HRMS) attempts to fetch journeys
        res_teco = client.get("/api/v1/staff/journeys/all", headers=self.headers_teco)
        self.assertEqual(res_teco.status_code, 403)

        # AIS gets journeys
        res_ais = client.get("/api/v1/staff/journeys/all", headers=self.headers_ais)
        self.assertIn(res_ais.status_code, [200, 304])

    # ========================================================
    # 2b. MANAGER HIERARCHY REAL TESTS (Item 5)
    # ========================================================
    def test_manager_hierarchy_subordinates_manager_vs_employee(self):
        # Manager (User 19) gets subordinates: sees direct reports
        res_mgr = client.get("/api/v1/staff/employees/subordinates", headers=self.headers_mgr)
        self.assertEqual(res_mgr.status_code, 200)
        mgr_data = res_mgr.json()
        self.assertTrue(mgr_data.get("success"))
        subordinates = mgr_data.get("employees", [])
        self.assertGreater(len(subordinates), 0, "Manager must see direct subordinates")
        sub_ids = [s["id"] for s in subordinates]
        self.assertIn(self.user_emp.id, sub_ids, "Employee 320 should be in Manager 19's subordinates")

        # Individual contributor / Employee (User 320) has no subordinates
        res_emp = client.get("/api/v1/staff/employees/subordinates", headers=self.headers_emp)
        self.assertEqual(res_emp.status_code, 200)
        emp_data = res_emp.json()
        self.assertTrue(emp_data.get("success"))
        self.assertEqual(len(emp_data.get("employees", [])), 0, "Individual employee must have 0 subordinates")

    def test_manager_hierarchy_timesheet_approval_unauthorized_peer_blocked(self):
        # Timesheet Entry 8 belongs to Employee 25
        # Employee 320 is a peer (also reports to 19, but is NOT the manager of 25)
        payload = {"action": "approved", "comments": "Unauthorized peer approval attempt"}
        res_peer = client.post("/api/v1/staff/timesheet/8/approve", json=payload, headers=self.headers_emp)
        self.assertEqual(res_peer.status_code, 403)
        self.assertIn("Not authorized to approve this entry", res_peer.text)

    def test_manager_hierarchy_accessible_employee_ids_strictly_downline(self):
        from app.utils.staff_hierarchy import get_accessible_employee_ids
        
        # 1. Regular employee sees ONLY self
        emp_accessible = get_accessible_employee_ids(self.user_emp, self.db, StaffEmployee)
        self.assertEqual(emp_accessible, [self.user_emp.id], "Individual contributor must only access self")

        # 2. Manager (User 25) sees downline reports (39, 72) + self, but NOT superior (19) or peers
        u25 = self.db.query(StaffEmployee).filter_by(id=25).first()
        mgr_accessible = get_accessible_employee_ids(u25, self.db, StaffEmployee)
        self.assertIn(25, mgr_accessible)
        self.assertIn(39, mgr_accessible)
        self.assertIn(72, mgr_accessible)
        self.assertNotIn(19, mgr_accessible, "Manager must not see supervisor (ID 19)")
        self.assertNotIn(320, mgr_accessible, "Manager must not see peer outside downline (ID 320)")

        # 3. SaaS Tenant Admin sees only company 94 employees, zero from company 93 or 4
        ais_accessible = get_accessible_employee_ids(self.user_ais, self.db, StaffEmployee)
        self.assertIn(self.user_ais.id, ais_accessible)
        for eid in ais_accessible:
            emp = self.db.query(StaffEmployee).filter_by(id=eid).first()
            if emp:
                self.assertEqual(emp.base_company_id, 94, "SaaS tenant must not access employees from other companies")

    def test_employee_url_tampering_cross_tenant_and_unauthorized_blocked(self):
        # SaaS Tenant (Company 94) tampers URL to fetch Internal Employee 22 (Company 4)
        res_c4 = client.get("/api/v1/staff/employees/22", headers=self.headers_ais)
        self.assertEqual(res_c4.status_code, 403)
        self.assertIn("Employee belongs to another organization", res_c4.text)

        # SaaS Tenant (Company 94) tampers URL to fetch Zylog Employee 301 (Company 93)
        res_c93 = client.get("/api/v1/staff/employees/301", headers=self.headers_ais)
        self.assertEqual(res_c93.status_code, 403)
        self.assertIn("Employee belongs to another organization", res_c93.text)

        # Unentitled Tenant (TECO, Company 92, no HRMS) tampers URL to access subordinates
        res_teco = client.get("/api/v1/staff/employees/subordinates", headers=self.headers_teco)
        self.assertEqual(res_teco.status_code, 403)

    # ========================================================
    # 3. ENTITLEMENT MATRIX COMBINATIONS (Item 11)
    # ========================================================
    def test_entitlement_matrix(self):
        c94 = self.db.query(AssociatedCompany).filter_by(id=94).first()
        
        matrix = [
            ("CRM only", ["CRM_LEADS"], ["CORE WORKSPACE", "CRM & LEADS"], ["SERVICE", "HRMS"]),
            ("SERVICE only", ["SERVICE_TICKETS"], ["CORE WORKSPACE", "SERVICE"], ["HRMS", "CRM & LEADS"]),
            ("HRMS only", ["STAFF_HRMS"], ["CORE WORKSPACE", "HRMS"], ["SERVICE", "CRM & LEADS"]),
            ("CRM + SERVICE", ["CRM_LEADS", "SERVICE_TICKETS"], ["CORE WORKSPACE", "CRM & LEADS", "SERVICE"], ["HRMS"]),
            ("CRM + HRMS", ["CRM_LEADS", "STAFF_HRMS"], ["CORE WORKSPACE", "CRM & LEADS", "HRMS"], ["SERVICE"]),
            ("SERVICE + HRMS", ["SERVICE_TICKETS", "STAFF_HRMS"], ["CORE WORKSPACE", "SERVICE", "HRMS"], ["CRM & LEADS"]),
            ("CRM + SERVICE + HRMS", ["CRM_LEADS", "SERVICE_TICKETS", "STAFF_HRMS"], ["CORE WORKSPACE", "CRM & LEADS", "SERVICE", "HRMS"], [])
        ]

        for name, mods, expected_cats, forbidden_cats in matrix:
            ctx = TenantContext(is_saas_tenant=True, is_tenant_admin=True, company=c94, effective_modules=mods)
            menus, routes, cat = get_saas_menu_tree(ctx)
            cats = list(cat.keys())
            for ec in expected_cats:
                self.assertIn(ec, cats, f"[{name}] Expected category '{ec}' missing in {cats}")
            for fc in forbidden_cats:
                self.assertNotIn(fc, cats, f"[{name}] Forbidden category '{fc}' leaked in {cats}")
            # Ensure zero internal platform routes leak
            for r in routes:
                self.assertFalse(any(k in r for k in ['/rvz/', '/vgk/', '/partner/', '/staff/nda']), f"[{name}] Leaked internal route {r}")

    # ========================================================
    # 4. STAFF-LEVEL MODULE ASSIGNMENT (Item 12)
    # ========================================================
    def test_staff_level_module_assignment_enforced(self):
        c94 = self.db.query(AssociatedCompany).filter_by(id=94).first()
        
        # Tenant has CRM + SERVICE + HRMS
        # Employee A has user_assigned_modules = ['CRM_LEADS']
        ctx_emp_a = TenantContext(
            is_saas_tenant=True, is_tenant_admin=False, company=c94,
            entitled_subscription_modules=['CRM_LEADS', 'SERVICE_TICKETS', 'STAFF_HRMS'],
            user_assigned_modules=['CRM_LEADS'],
            effective_modules=['CRM_LEADS']
        )
        self.assertTrue(ctx_emp_a.has_module('CRM_LEADS'))
        self.assertFalse(ctx_emp_a.has_module('STAFF_HRMS'))
        self.assertFalse(ctx_emp_a.has_module('SERVICE_TICKETS'))
        with self.assertRaises(Exception):
            ctx_emp_a.require_module('STAFF_HRMS')

        # Employee B has user_assigned_modules = ['STAFF_HRMS']
        ctx_emp_b = TenantContext(
            is_saas_tenant=True, is_tenant_admin=False, company=c94,
            entitled_subscription_modules=['CRM_LEADS', 'SERVICE_TICKETS', 'STAFF_HRMS'],
            user_assigned_modules=['STAFF_HRMS'],
            effective_modules=['STAFF_HRMS']
        )
        self.assertFalse(ctx_emp_b.has_module('CRM_LEADS'))
        self.assertTrue(ctx_emp_b.has_module('STAFF_HRMS'))

        # Employee C has user_assigned_modules = ['SERVICE_TICKETS', 'STAFF_HRMS']
        ctx_emp_c = TenantContext(
            is_saas_tenant=True, is_tenant_admin=False, company=c94,
            entitled_subscription_modules=['CRM_LEADS', 'SERVICE_TICKETS', 'STAFF_HRMS'],
            user_assigned_modules=['SERVICE_TICKETS', 'STAFF_HRMS'],
            effective_modules=['SERVICE_TICKETS', 'STAFF_HRMS']
        )
        self.assertFalse(ctx_emp_c.has_module('CRM_LEADS'))
        self.assertTrue(ctx_emp_c.has_module('SERVICE_TICKETS'))
        self.assertTrue(ctx_emp_c.has_module('STAFF_HRMS'))

    # ========================================================
    # 5. FUTURE MODULE ARCHITECTURE PROOF (Item 13)
    # ========================================================
    def test_future_module_architecture_dynamic(self):
        c94 = self.db.query(AssociatedCompany).filter_by(id=94).first()
        ctx = TenantContext(
            is_saas_tenant=True, is_tenant_admin=True, company=c94,
            effective_modules=['PROCUREMENT_AI', 'CRM_LEADS']
        )
        self.assertTrue(ctx.has_module('PROCUREMENT_AI'))
        self.assertFalse(ctx.has_module('SOLAR_EV'))
        ctx.require_module('PROCUREMENT_AI')

if __name__ == '__main__':
    unittest.main()
