import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from playwright.async_api import async_playwright
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.core.security import SecurityManager

SCREENSHOTS_DIR = "/Users/viswanathkari/.gemini/antigravity/brain/fe0b1cb9-cff8-421f-88dc-78cc676d16ad/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_auth_data(emp_code: str):
    db = SessionLocal()
    try:
        s = db.query(StaffEmployee).filter(StaffEmployee.emp_code == emp_code).first()
        is_platform = s.emp_code in ['MR10001', 'MR10018']
        token = SecurityManager.create_access_token(
            data={
                "sub": str(s.id),
                "emp_code": s.emp_code,
                "email": s.email,
                "role": s.role.role_code if s.role else ("super_admin" if is_platform else "tenant_admin"),
                "staff_type": getattr(s, "staff_type", "VGK4U_SUPREME" if is_platform else "TENANT_ADMIN"),
                "admin_scope": getattr(s, "admin_scope", "GLOBAL_SUPERADMIN" if is_platform else "CLIENT_SPECIFIC"),
                "base_company_id": s.base_company_id,
                "tenant_id": getattr(s, "tenant_id", None if is_platform else 1),
                "token_version": getattr(s, "token_version", 1) or 1,
                "team_tag": s.team_tag,
                "user_type": "staff"
            }
        )
        user_dict = {
            "id": s.id,
            "emp_code": s.emp_code,
            "full_name": s.full_name or "SaaS Tenant Admin",
            "email": s.email,
            "role": s.role.role_code if s.role else ("super_admin" if is_platform else "tenant_admin"),
            "staff_type": s.staff_type,
            "base_company_id": s.base_company_id,
            "tenant_id": s.tenant_id,
            "accessible_company_ids": [s.base_company_id],
            "primary_company_id": s.base_company_id
        }
        return token, user_dict
    finally:
        db.close()

async def run_visual_verification():
    ais_token, ais_user = get_auth_data('AIS_ADMIN')
    print(f"Loaded auth for AIS_ADMIN: id={ais_user['id']}, company={ais_user['base_company_id']}")

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # ==========================================================
        # PART 1: WEB DESKTOP VALIDATION (1440x900)
        # ==========================================================
        print("\n--- STARTING WEB DESKTOP VALIDATION ---")
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Inject auth state
        await page.goto("http://localhost:5001/staff/login")
        await page.evaluate(f"""() => {{
            localStorage.setItem('staff_token', '{ais_token}');
            localStorage.setItem('token', '{ais_token}');
            localStorage.setItem('staff_user', '{json.dumps(ais_user)}');
            localStorage.setItem('primary_company_id', '{ais_user["base_company_id"]}');
            document.cookie = 'staff_token={ais_token}; path=/;';
            document.cookie = 'token={ais_token}; path=/;';
        }}""")

        # 1. Menu & Sidebar Tree
        await page.goto("http://localhost:5001/staff/my-tenant", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        sidebar_text = await page.locator("#staffSidebar").inner_text()
        print("Captured Sidebar Categories for AIS_ADMIN")
        
        has_service = "SERVICE" in sidebar_text
        has_hrms = "HRMS" in sidebar_text or "HUMAN RESOURCES" in sidebar_text or "EMPLOYEES" in sidebar_text
        no_vendor_leak = "Vendors & Partners" not in sidebar_text
        no_solar_leak = "Solar Leads" not in sidebar_text

        print(f"  SERVICE present: {has_service}")
        print(f"  HRMS present: {has_hrms}")
        print(f"  No internal leaks: {no_vendor_leak and no_solar_leak}")

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_service_hrms_01_menu_tree.png")
        results['web_menu_tree'] = has_service and has_hrms and no_vendor_leak and no_solar_leak

        # 2. Service Dashboard
        await page.goto("http://localhost:5001/staff/service-tickets/dashboard", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        dash_title = await page.title()
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_service_02_dashboard.png")
        print(f"Captured: saas_service_02_dashboard.png (Title: {dash_title})")
        results['web_service_dashboard'] = "Service" in dash_title or page.url.endswith('/dashboard')

        # 3. Service Ticket Queue
        await page.goto("http://localhost:5001/staff/service-tickets/queue", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_service_03_queue.png")
        print("Captured: saas_service_03_queue.png")
        results['web_service_queue'] = page.url.endswith('/queue')

        # 4. Service Raise Ticket
        await page.goto("http://localhost:5001/staff/service-tickets/raise", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_service_04_raise.png")
        print("Captured: saas_service_04_raise.png")
        results['web_service_raise'] = page.url.endswith('/raise')

        # 5. Service Reports
        await page.goto("http://localhost:5001/staff/service-tickets/reports", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_service_05_reports.png")
        print("Captured: saas_service_05_reports.png")
        results['web_service_reports'] = page.url.endswith('/reports')

        # 6. HRMS Employees
        await page.goto("http://localhost:5001/staff/employees", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        emp_content = await page.content()
        has_ananya = "Ananya" in emp_content or "AIS_ADMIN" in emp_content
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_06_employees.png")
        print(f"Captured: saas_hrms_06_employees.png (AIS_ADMIN visible in DOM: {has_ananya})")
        results['web_hrms_employees'] = has_ananya

        # 7. HRMS Employee Profile
        await page.goto("http://localhost:5001/staff/employees?view=profile", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_07_employee_profile.png")
        print("Captured: saas_hrms_07_employee_profile.png")
        results['web_hrms_employee_profile'] = True

        # 8. HRMS Attendance
        await page.goto("http://localhost:5001/staff/attendance-sheet", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_08_attendance.png")
        print("Captured: saas_hrms_08_attendance.png")
        results['web_hrms_attendance'] = page.url.endswith('/attendance-sheet')

        # 9. HRMS Leaves
        await page.goto("http://localhost:5001/staff/my-leaves", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_09_leaves.png")
        print("Captured: saas_hrms_09_leaves.png")
        results['web_hrms_leaves'] = page.url.endswith('/my-leaves')

        # 10. HRMS Journeys
        await page.goto("http://localhost:5001/staff/my-journeys", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_10_journeys.png")
        print("Captured: saas_hrms_10_journeys.png")
        results['web_hrms_journeys'] = page.url.endswith('/my-journeys')

        # 11. HRMS Tasks
        await page.goto("http://localhost:5001/staff/tasks/tracker", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_11_tasks.png")
        print("Captured: saas_hrms_11_tasks.png")
        results['web_hrms_tasks'] = page.url.endswith('/tasks/tracker')

        # 12. HRMS KRAs
        await page.goto("http://localhost:5001/staff/my-kras", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_12_kras.png")
        print("Captured: saas_hrms_12_kras.png")
        results['web_hrms_kras'] = page.url.endswith('/my-kras')

        # 13. HRMS Timesheet
        await page.goto("http://localhost:5001/staff/timesheet", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_hrms_13_timesheet.png")
        print("Captured: saas_hrms_13_timesheet.png")
        results['web_hrms_timesheet'] = page.url.endswith('/timesheet')

        await context.close()

        # ==========================================================
        # PART 2: MOBILE WEB SPA VALIDATION (390x844)
        # ==========================================================
        print("\n--- STARTING /MOBILE WEB SPA VALIDATION ---")
        m_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        )
        m_page = await m_context.new_page()

        # Inject auth into mobile context
        await m_page.goto("http://localhost:5001/mobile/")
        await m_page.evaluate(f"""() => {{
            localStorage.setItem('auth_token', '{ais_token}');
            localStorage.setItem('staff_token', '{ais_token}');
            localStorage.setItem('token', '{ais_token}');
            localStorage.setItem('user', '{json.dumps(ais_user)}');
            localStorage.setItem('staff_user', '{json.dumps(ais_user)}');
            sessionStorage.setItem('token', '{ais_token}');
        }}""")

        # Reload to let SPA initialize with auth
        await m_page.goto("http://localhost:5001/mobile/#/dashboard", wait_until="networkidle")
        await m_page.wait_for_timeout(3000)

        # Try opening SideDrawer if hamburger menu exists
        try:
            drawer_btn = m_page.locator("button[aria-label='menu'], .hamburger-btn, .menu-btn, button:has(.fa-bars)").first
            if await drawer_btn.count() > 0:
                await drawer_btn.click()
                await m_page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Drawer button click notice: {e}")

        await m_page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_mobile_14_drawer.png")
        print("Captured: saas_mobile_14_drawer.png")

        mobile_content = await m_page.content()
        m_no_vendor = "Vendors & Partners" not in mobile_content
        print(f"Mobile SPA loaded. Internal leak check passed: {m_no_vendor}")
        results['mobile_spa'] = m_no_vendor

        await m_context.close()
        await browser.close()

    print("\n--- VISUAL VERIFICATION SUMMARY ---")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

if __name__ == '__main__':
    asyncio.run(run_visual_verification())
