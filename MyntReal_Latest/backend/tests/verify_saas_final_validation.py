import asyncio
import json
import os
import sys
import datetime
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from playwright.async_api import async_playwright
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.models.crm import CRMLead
from app.models.signup_category import SignupCategory
from app.models.crm_handler import CRMLeadHandler, CRMLeadHandlerMember
from app.core.security import SecurityManager
from app.services.saas_tenant_resolver import resolve_tenant_context
from app.api.v1.endpoints.saas_crm_setup import _sync_handler_routing, SegmentCreateSchema, create_tenant_segment

SCREENSHOTS_DIR = "/Users/viswanathkari/.gemini/antigravity/brain/fe0b1cb9-cff8-421f-88dc-78cc676d16ad/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_auth_data(emp_code: str):
    db = SessionLocal()
    try:
        s = db.query(StaffEmployee).filter(StaffEmployee.emp_code == emp_code).first()
        is_platform = emp_code in ['MR10001', 'MR10018']
        token = SecurityManager.create_access_token(
            data={
                "sub": str(s.id),
                "emp_code": s.emp_code,
                "email": s.email,
                "role": s.role.role_code if s.role else ("super_admin" if is_platform else "admin"),
                "staff_type": getattr(s, "staff_type", "VGK4U_SUPREME" if is_platform else "TENANT_ADMIN"),
                "admin_scope": getattr(s, "admin_scope", "GLOBAL_SUPERADMIN" if is_platform else "CLIENT_SPECIFIC"),
                "base_company_id": s.base_company_id,
                "tenant_id": getattr(s, "tenant_id", None if is_platform else 190),
                "token_version": getattr(s, "token_version", 1) or 1,
                "team_tag": s.team_tag,
                "user_type": "staff"
            }
        )
        user_dict = {
            "id": s.id,
            "emp_code": s.emp_code,
            "full_name": s.full_name or ("Platform Super Admin" if is_platform else "Test Solar Admin"),
            "email": s.email,
            "role": s.role.role_code if s.role else ("super_admin" if is_platform else "admin"),
            "staff_type": s.staff_type,
            "base_company_id": s.base_company_id,
            "tenant_id": None if is_platform else s.tenant_id,
            "accessible_company_ids": [1, 2, 3, 4] if is_platform else [127],
            "primary_company_id": 1 if is_platform else 127
        }
        return token, user_dict
    finally:
        db.close()


async def run_final_validation():
    print("=" * 70)
    print("MYNTOS FINAL SAAS CRM + WORKFLOWS ENTITLEMENT VALIDATION")
    print("=" * 70)

    db = SessionLocal()
    teso_token, teso_user = get_auth_data('TESO_ADMIN')
    mr_token, mr_user = get_auth_data('MR10001')

    comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == 127).first()
    original_modules = list(comp.licensed_modules or ['CRM_LEADS', 'SOLAR_EV'])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Helper to set auth state safely without staff_login.html redirect races
        async def set_auth(token, user):
            if "localhost:5001" not in page.url or page.url == "about:blank":
                await page.goto("http://localhost:5001/favicon.ico")
            await context.clear_cookies()
            await context.add_cookies([{
                'name': 'staff_token',
                'value': token,
                'domain': 'localhost',
                'path': '/'
            }])
            await page.evaluate('''([token, user]) => {
                localStorage.setItem('staff_token', token);
                localStorage.setItem('staff_user', JSON.stringify(user));
                sessionStorage.clear();
            }''', [token, user])

        # -------------------------------------------------------------
        # 1. RESOLVE STAFF & USERS ROUTE CONSISTENCY
        # -------------------------------------------------------------
        print("\n--- [1] Staff & Users Route Consistency ---")
        await set_auth(teso_token, teso_user)
        # Check canonical route /staff/tenant-users
        resp1 = await page.goto("http://localhost:5001/staff/tenant-users")
        assert resp1.status == 200, f"Expected 200 for canonical /staff/tenant-users, got {resp1.status}"
        print("✓ Canonical /staff/tenant-users returned 200 OK")

        # Check compatibility redirect /staff/my-tenant/users
        resp2 = await page.goto("http://localhost:5001/staff/my-tenant/users")
        current_url = page.url
        assert "/staff/tenant-users" in current_url, f"Expected redirect to /staff/tenant-users, got {current_url}"
        print(f"✓ Compatibility /staff/my-tenant/users redirected to: {current_url}")

        # -------------------------------------------------------------
        # 2 & 3. FOUR-COMBINATION ENTITLEMENT TEST MATRIX
        # -------------------------------------------------------------
        print("\n--- [2 & 3] Four-Combination Entitlement Test Matrix ---")
        
        # COMBINATION A: CRM ONLY
        print("\n--- Combination A: CRM ONLY ---")
        comp.licensed_modules = ['CRM_LEADS']
        db.commit()
        await set_auth(teso_token, teso_user)
        await page.goto("http://localhost:5001/staff/crm/dashboard")
        await page.wait_for_timeout(1500)
        sidebar_text_a = await page.evaluate("() => document.getElementById('staffSidebar') ? document.getElementById('staffSidebar').innerText : ''")
        print("Sidebar Text (CRM Only):\n" + sidebar_text_a.strip())
        assert "CORE WORKSPACE" in sidebar_text_a
        assert "Company Profile" in sidebar_text_a
        assert "Staff & Users" in sidebar_text_a
        assert "CRM / Workflow Setup" in sidebar_text_a
        assert "CRM & LEADS" in sidebar_text_a
        assert "CRM Dashboard" in sidebar_text_a
        assert "My Leads" in sidebar_text_a
        assert "Staff Leads" in sidebar_text_a
        assert "WORKFLOWS" not in sidebar_text_a
        assert "Executive Dashboard" not in sidebar_text_a
        assert "Category-wise Leads" not in sidebar_text_a
        assert "Vendors & Partners" not in sidebar_text_a
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "entitlement_matrix_a_crm_only.png"))
        print("✓ Combination A Verified (CRM Only)")

        # COMBINATION B: WORKFLOWS ONLY
        print("\n--- Combination B: WORKFLOWS ONLY ---")
        comp.licensed_modules = ['SOLAR_EV']
        db.commit()
        await set_auth(teso_token, teso_user)
        await page.goto("http://localhost:5001/staff/executive-dashboard")
        await page.wait_for_timeout(1500)
        sidebar_text_b = await page.evaluate("() => document.getElementById('staffSidebar') ? document.getElementById('staffSidebar').innerText : ''")
        print("Sidebar Text (Workflows Only):\n" + sidebar_text_b.strip())
        assert "CORE WORKSPACE" in sidebar_text_b
        assert "Company Profile" in sidebar_text_b
        assert "Staff & Users" in sidebar_text_b
        assert "CRM / Workflow Setup" in sidebar_text_b
        assert "WORKFLOWS" in sidebar_text_b
        assert "Executive Dashboard" in sidebar_text_b
        assert "Category-wise Leads" in sidebar_text_b
        assert "CRM & LEADS" not in sidebar_text_b
        assert "CRM Dashboard" not in sidebar_text_b
        assert "Vendors & Partners" not in sidebar_text_b
        assert "SOLAR_EV" not in sidebar_text_b
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "entitlement_matrix_b_workflows_only.png"))
        print("✓ Combination B Verified (Workflows Only)")

        # COMBINATION C: CRM + WORKFLOWS
        print("\n--- Combination C: CRM + WORKFLOWS ---")
        comp.licensed_modules = ['CRM_LEADS', 'SOLAR_EV']
        db.commit()
        await set_auth(teso_token, teso_user)
        await page.goto("http://localhost:5001/staff/crm/dashboard")
        await page.wait_for_timeout(1500)
        sidebar_text_c = await page.evaluate("() => document.getElementById('staffSidebar') ? document.getElementById('staffSidebar').innerText : ''")
        print("Sidebar Text (CRM + Workflows):\n" + sidebar_text_c.strip())
        assert "CORE WORKSPACE" in sidebar_text_c
        assert "CRM & LEADS" in sidebar_text_c
        assert "CRM Dashboard" in sidebar_text_c
        assert "My Leads" in sidebar_text_c
        assert "Staff Leads" in sidebar_text_c
        assert "WORKFLOWS" in sidebar_text_c
        assert "Executive Dashboard" in sidebar_text_c
        assert "Category-wise Leads" in sidebar_text_c
        assert "Vendors & Partners" not in sidebar_text_c
        assert "SOLAR_EV" not in sidebar_text_c
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "entitlement_matrix_c_crm_plus_workflows.png"))
        print("✓ Combination C Verified (CRM + Workflows)")

        # COMBINATION D: CRM + WORKFLOWS + ANOTHER MODULE (ACCOUNTS_GST)
        print("\n--- Combination D: CRM + WORKFLOWS + ACCOUNTS_GST ---")
        comp.licensed_modules = ['CRM_LEADS', 'SOLAR_EV', 'ACCOUNTS_GST']
        db.commit()
        await set_auth(teso_token, teso_user)
        await page.goto("http://localhost:5001/staff/crm/dashboard")
        await page.wait_for_timeout(1500)
        sidebar_text_d = await page.evaluate("() => document.getElementById('staffSidebar') ? document.getElementById('staffSidebar').innerText : ''")
        print("Sidebar Text (CRM + Workflows + ACCOUNTS_GST):\n" + sidebar_text_d.strip())
        assert "CORE WORKSPACE" in sidebar_text_d
        assert "CRM & LEADS" in sidebar_text_d
        assert "WORKFLOWS" in sidebar_text_d
        assert "ACCOUNTS & GST" in sidebar_text_d
        assert "Expense Entries" in sidebar_text_d
        # Crucial check: Internal platform sections must NOT leak!
        internal_banned = ["STAFF DASHBOARD", "HR", "PROGRESS", "META ADS", "BUSINESS PARTNERS", "INTERNAL", "ZYNOVA"]
        for b in internal_banned:
            assert b not in sidebar_text_d, f"Internal section '{b}' leaked into SaaS tenant sidebar!"
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "entitlement_matrix_d_crm_wf_accounts.png"))
        print("✓ Combination D Verified (CRM + Workflows + Accounts, No Internal Leaks)")

        # -------------------------------------------------------------
        # 4. DIRECT URL SECURITY MATRIX
        # -------------------------------------------------------------
        print("\n--- [4] Direct URL Security Matrix ---")
        # Test Case 1: CRM-Only Tenant Direct Access
        comp.licensed_modules = ['CRM_LEADS']
        db.commit()
        await set_auth(teso_token, teso_user)

        # ALLOW: CRM pages
        for p_allow in ['/staff/crm/dashboard', '/staff/my-leads', '/staff/leads']:
            await page.goto(f"http://localhost:5001{p_allow}")
            await page.wait_for_timeout(1000)
            assert p_allow in page.url, f"Expected {p_allow} to be ALLOWED, but navigated to {page.url}"
            print(f"  ✓ ALLOWED (CRM-only): {p_allow}")

        # DENY: Workflow pages
        for p_deny in ['/staff/executive-dashboard', '/staff/mnr-leads', '/staff/category-leads']:
            await page.goto(f"http://localhost:5001{p_deny}")
            await page.wait_for_timeout(1000)
            assert "/staff/my-tenant" in page.url, f"Expected {p_deny} to be DENIED and redirect to /staff/my-tenant, got {page.url}"
            print(f"  ✓ DENIED & REDIRECTED (CRM-only): {p_deny} -> {page.url}")

        # Test Case 2: Workflow-Only Tenant Direct Access
        comp.licensed_modules = ['SOLAR_EV']
        db.commit()
        await set_auth(teso_token, teso_user)

        # ALLOW: Workflow pages
        for p_allow in ['/staff/executive-dashboard', '/staff/mnr-leads']:
            await page.goto(f"http://localhost:5001{p_allow}")
            await page.wait_for_timeout(1000)
            assert p_allow in page.url, f"Expected {p_allow} to be ALLOWED, but navigated to {page.url}"
            print(f"  ✓ ALLOWED (Workflow-only): {p_allow}")

        # DENY: CRM pages
        for p_deny in ['/staff/crm/dashboard', '/staff/my-leads', '/staff/leads']:
            await page.goto(f"http://localhost:5001{p_deny}")
            await page.wait_for_timeout(1000)
            assert "/staff/my-tenant" in page.url, f"Expected {p_deny} to be DENIED and redirect to /staff/my-tenant, got {page.url}"
            print(f"  ✓ DENIED & REDIRECTED (Workflow-only): {p_deny} -> {page.url}")

        # Core pages remain accessible in both cases
        for p_core in ['/staff/my-tenant', '/staff/tenant-users', '/staff/saas-crm-settings']:
            await page.goto(f"http://localhost:5001{p_core}")
            await page.wait_for_timeout(1000)
            assert p_core in page.url, f"Expected core page {p_core} to remain accessible, got {page.url}"
            print(f"  ✓ CORE PAGE ACCESSIBLE: {p_core}")

        # Restore modules to CRM + Workflows
        comp.licensed_modules = ['CRM_LEADS', 'SOLAR_EV']
        db.commit()

        # -------------------------------------------------------------
        # 7. DYNAMIC SEGMENTS ON CATEGORY-WISE LEADS
        # -------------------------------------------------------------
        print("\n--- [7] Dynamic Segments on Category-wise Leads ---")
        await set_auth(teso_token, teso_user)
        # Create disposable test segments
        ts = datetime.datetime.now().strftime("%H%M%S")
        seg_names = [f"Residential Solar {ts}", f"Commercial Solar {ts}", f"Service {ts}"]
        created_cats = []
        for sname in seg_names:
            c = SignupCategory(
                company_id=127,
                name=sname,
                slug=sname.lower().replace(" ", "-"),
                is_active=True
            )
            db.add(c)
            db.flush()
            created_cats.append(c)
        db.commit()

        # Verify Category-wise Leads displays those segments
        await page.goto("http://localhost:5001/staff/mnr-leads")
        await page.wait_for_timeout(1500)
        tabs_text = await page.evaluate("() => document.getElementById('tabNav') ? document.getElementById('tabNav').innerText : ''")
        for sname in seg_names:
            assert sname in tabs_text, f"Segment '{sname}' was not found in Category-wise Leads tabs!"
        print(f"✓ Initial dynamic segments confirmed: {seg_names}")

        # Add EV Fleet
        ev_cat = SignupCategory(
            company_id=127,
            name=f"EV Fleet {ts}",
            slug=f"ev-fleet-{ts}",
            is_active=True
        )
        db.add(ev_cat)
        db.commit()

        # Reload Category-wise Leads - EV Fleet must appear automatically!
        await page.reload()
        await page.wait_for_timeout(1500)
        tabs_text = await page.evaluate("() => document.getElementById('tabNav') ? document.getElementById('tabNav').innerText : ''")
        assert f"EV Fleet {ts}" in tabs_text, "EV Fleet did not appear automatically!"
        print(f"✓ EV Fleet {ts} appeared automatically without code deployment!")

        # Add Insurance Leads
        ins_cat = SignupCategory(
            company_id=127,
            name=f"Insurance Leads {ts}",
            slug=f"insurance-leads-{ts}",
            is_active=True
        )
        db.add(ins_cat)
        db.commit()

        # Reload Category-wise Leads - Insurance Leads must appear automatically!
        await page.reload()
        await page.wait_for_timeout(1500)
        tabs_text = await page.evaluate("() => document.getElementById('tabNav') ? document.getElementById('tabNav').innerText : ''")
        assert f"Insurance Leads {ts}" in tabs_text, "Insurance Leads did not appear automatically!"
        print(f"✓ Insurance Leads {ts} appeared automatically without code deployment!")

        # Verify platform-only categories do NOT appear
        platform_banned = ["Real Dreams", "EV B2B", "Solar Leads"]
        for pb in platform_banned:
            assert pb not in tabs_text, f"Platform category '{pb}' leaked into Category-wise Leads tabs!"
        print("✓ Verified platform-only categories do NOT leak into tenant tabs.")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dynamic_category_leads_verified.png"))

        # -------------------------------------------------------------
        # 8. EXECUTIVE DASHBOARD DYNAMIC SEGMENTS
        # -------------------------------------------------------------
        print("\n--- [8] Executive Dashboard Dynamic Segments ---")
        await page.goto("http://localhost:5001/staff/executive-dashboard")
        await page.wait_for_timeout(1500)
        dash_options = await page.evaluate('''() => {
            const sel = document.getElementById('dashCategory');
            return sel ? Array.from(sel.options).map(o => o.text) : [];
        }''')
        print(f"Executive Dashboard Category Options: {dash_options}")
        assert f"Residential Solar {ts}" in dash_options
        assert f"Commercial Solar {ts}" in dash_options
        print("✓ Executive Dashboard dynamically differentiates tenant segments.")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "executive_dashboard_dynamic_segments.png"))

        # -------------------------------------------------------------
        # 9. STAFF SEGMENT ROUTING & WEIGHTED ROUND-ROBIN
        # -------------------------------------------------------------
        print("\n--- [9] Staff Segment Routing & Weighted Round-Robin ---")
        admin_staff = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()
        # Find 4 test staff members of company 127
        staff_pool = db.query(StaffEmployee).filter(
            StaffEmployee.base_company_id == 127,
            StaffEmployee.status == 'active',
            StaffEmployee.emp_code != 'TESO_ADMIN'
        ).limit(4).all()
        assert len(staff_pool) >= 4, "Need at least 4 active non-admin staff members for company 127"
        
        staff_a, staff_b, staff_c, staff_d = staff_pool[0], staff_pool[1], staff_pool[2], staff_pool[3]
        print(f"Segment A Pool: Staff A ({staff_a.emp_code}, weight:1), Staff B ({staff_b.emp_code}, weight:2)")
        print(f"Segment B Pool: Staff C ({staff_c.emp_code}, weight:1), Staff D ({staff_d.emp_code}, weight:1)")

        # Create Segment A and Segment B
        seg_a = SignupCategory(
            company_id=127,
            name=f"Segment Alpha {ts}",
            slug=f"segment-alpha-{ts}",
            is_active=True
        )
        seg_b = SignupCategory(
            company_id=127,
            name=f"Segment Beta {ts}",
            slug=f"segment-beta-{ts}",
            is_active=True
        )
        db.add_all([seg_a, seg_b])
        db.commit()

        # Configure Routing Pools
        from app.api.v1.endpoints.saas_crm_setup import StaffAssignmentItem
        _sync_handler_routing(db, 127, seg_a.id, [
            StaffAssignmentItem(employee_id=staff_a.id, assignment_weight=1),
            StaffAssignmentItem(employee_id=staff_b.id, assignment_weight=2)
        ], admin_staff.id)
        _sync_handler_routing(db, 127, seg_b.id, [
            StaffAssignmentItem(employee_id=staff_c.id, assignment_weight=1),
            StaffAssignmentItem(employee_id=staff_d.id, assignment_weight=1)
        ], admin_staff.id)
        db.commit()

        # Create 10 leads for Segment A via API/Service
        from app.api.v1.endpoints.crm import LeadCreate, create_lead
        admin_staff = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()

        leads_a = []
        for i in range(10):
            ld = LeadCreate(
                name=f"Lead Alpha {i+1} {ts}",
                phone=f"91{int(datetime.datetime.now().timestamp()) % 100000000:08d}{i}",
                category_id=seg_a.id,
                company_id=127,
                status="new",
                source="Website"
            )
            res = create_lead(lead_data=ld, company_id=127, db=db, current_employee=admin_staff)
            leads_a.append(res)

        # Create 10 leads for Segment B
        leads_b = []
        for i in range(10):
            ld = LeadCreate(
                name=f"Lead Beta {i+1} {ts}",
                phone=f"92{int(datetime.datetime.now().timestamp()) % 100000000:08d}{i}",
                category_id=seg_b.id,
                company_id=127,
                status="new",
                source="Website"
            )
            res = create_lead(lead_data=ld, company_id=127, db=db, current_employee=admin_staff)
            leads_b.append(res)

        # Verify assignments in DB
        db.commit()
        assigned_a = [l['data']['primary_owner_id'] for l in leads_a]
        assigned_b = [l['data']['primary_owner_id'] for l in leads_b]

        print(f"Segment A Assigned Owners: {assigned_a}")
        print(f"Segment B Assigned Owners: {assigned_b}")

        # Check: Segment A leads routed ONLY to Staff A or Staff B
        for oid in assigned_a:
            assert oid in [staff_a.id, staff_b.id], f"Segment A lead routed to {oid} outside pool [A, B]!"
        assert staff_a.id in assigned_a, "Staff A received zero leads!"
        assert staff_b.id in assigned_a, "Staff B received zero leads!"
        # Since Staff B has weight 2 and Staff A has weight 1, Staff B should have >= Staff A leads
        count_a = assigned_a.count(staff_a.id)
        count_b = assigned_a.count(staff_b.id)
        print(f"Segment A lead count distribution: Staff A (weight 1) = {count_a}, Staff B (weight 2) = {count_b}")
        assert count_b >= count_a, f"Expected Staff B (weight 2) to receive >= Staff A (weight 1), got B={count_b}, A={count_a}"
        print("✓ Segment A Routing & Weighted Round-Robin Demonstrated!")

        # Check: Segment B leads routed ONLY to Staff C or Staff D
        for oid in assigned_b:
            assert oid in [staff_c.id, staff_d.id], f"Segment B lead routed to {oid} outside pool [C, D]!"
        assert staff_c.id in assigned_b, "Staff C received zero leads!"
        assert staff_d.id in assigned_b, "Staff D received zero leads!"
        print("✓ Segment B Routing Verified (Strict isolation to Staff C & Staff D)")

        # Verify frontend preselection doesn't defeat routing
        await page.goto("http://localhost:5001/staff/leads")
        await page.wait_for_timeout(1000)
        # Open create lead modal
        await page.click("button:has-text('Add Lead'), button:has-text('New Lead'), #btnAddLead")
        await page.wait_for_timeout(500)
        # Select Segment Alpha
        await page.select_option("#leadCategory", str(seg_a.id))
        await page.wait_for_timeout(500)
        # Check that primary owner search is NOT forced with an explicit owner ID
        owner_val = await page.evaluate("() => document.getElementById('leadPrimaryOwnerId') ? document.getElementById('leadPrimaryOwnerId').value : ''")
        note_txt = await page.evaluate("() => document.getElementById('primaryOwnerNote') ? document.getElementById('primaryOwnerNote').innerText : ''")
        print(f"Frontend Modal Primary Owner Value: '{owner_val}', Note: '{note_txt}'")
        assert owner_val == '', f"Frontend preselection forced ownerId '{owner_val}', which defeats backend weighted routing!"
        assert "Auto-assigned by Company Segment Pool" in note_txt or "Segment Alpha" in note_txt
        print("✓ Frontend preselection does NOT defeat backend weighted round-robin!")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "frontend_lead_modal_weighted_routing.png"))

        # -------------------------------------------------------------
        # 10. INTERNAL PLATFORM REGRESSION (MR10001)
        # -------------------------------------------------------------
        print("\n--- [10] Internal Platform Regression (MR10001) ---")
        await set_auth(mr_token, mr_user)
        await page.goto("http://localhost:5001/staff/progress")
        await page.wait_for_timeout(1500)
        mr_sidebar = await page.evaluate("() => document.getElementById('staffSidebar') ? document.getElementById('staffSidebar').innerText : ''")
        print("MR10001 Sidebar Sample:\n" + "\n".join(mr_sidebar.split("\n")[:30]))
        assert "Progress" in mr_sidebar
        assert "Task Planner" in mr_sidebar
        assert "CORE WORKSPACE" in mr_sidebar
        assert "HR" in mr_sidebar
        assert "STAFF DASHBOARD" in mr_sidebar
        assert "Employees" in mr_sidebar
        print("✓ Platform Admin MR10001 retains all internal systems (Zero Regression)")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mr10001_platform_retained.png"))

        await browser.close()

    db.close()
    print("\n" + "=" * 70)
    print("ALL VALIDATION SUITES COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == '__main__':
    asyncio.run(run_final_validation())
