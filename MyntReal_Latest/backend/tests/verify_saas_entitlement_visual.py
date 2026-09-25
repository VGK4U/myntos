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

async def run_visual_verification():
    teso_token, teso_user = get_auth_data('TESO_ADMIN')
    mr_token, mr_user = get_auth_data('MR10001')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. SaaS Tenant: Core Workspace + Clean Sidebar Hierarchy
        await page.goto("http://localhost:5001/staff/login")
        await page.evaluate(f"""() => {{
            localStorage.setItem('staff_token', '{teso_token}');
            localStorage.setItem('token', '{teso_token}');
            localStorage.setItem('staff_user', '{json.dumps(teso_user)}');
            localStorage.setItem('primary_company_id', '127');
            document.cookie = 'staff_token={teso_token}; path=/;';
            document.cookie = 'token={teso_token}; path=/;';
        }}""")

        await page.goto("http://localhost:5001/staff/my-tenant", wait_until="networkidle")
        await page.wait_for_timeout(2500)

        # Inspect sidebar text content
        sidebar_text = await page.locator("#staffSidebar").inner_text()
        print("--- SIDEBAR CONTENT FOR SAAS TENANT ---")
        print(sidebar_text)
        print("---------------------------------------")

        assert "CORE WORKSPACE" in sidebar_text
        assert "CRM & LEADS" in sidebar_text
        assert "WORKFLOWS" in sidebar_text
        assert "Vendors & Partners" not in sidebar_text, "Vendors & Partners must NOT appear for SaaS tenant"
        assert "Solar Leads" not in sidebar_text, "Solar Leads must NOT appear for SaaS tenant"
        assert "EV B2B Leads" not in sidebar_text, "EV B2B Leads must NOT appear for SaaS tenant"

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_entitlement_01_core_workspace_sidebar.png")
        print("Captured: saas_entitlement_01_core_workspace_sidebar.png")

        # 2. Executive Dashboard (Clean Workflow Dashboard)
        await page.goto("http://localhost:5001/staff/executive-dashboard", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        sub_text = await page.locator(".page-banner p").inner_text()
        print(f"Executive Dashboard Subtitle: {sub_text}")

        # Check segment dropdown
        cat_options = await page.locator("#dashCategory option").all_inner_texts()
        print(f"Executive Dashboard Segment Options: {cat_options}")
        assert "EV B2B" not in cat_options, "EV B2B must not be hardcoded in SaaS executive dashboard"

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_entitlement_02_executive_dashboard_clean.png")
        print("Captured: saas_entitlement_02_executive_dashboard_clean.png")

        # 3. Category-wise Leads (Dynamic Segment Tabs)
        await page.goto("http://localhost:5001/staff/mnr-leads", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        tab_nav_text = await page.locator("#tabNav").inner_text()
        print(f"Category-wise Leads Tabs: {tab_nav_text}")
        assert "Real Dreams" not in tab_nav_text, "Real Dreams must not be in SaaS Category Leads tabs"

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_entitlement_03_category_leads_clean.png")
        print("Captured: saas_entitlement_03_category_leads_clean.png")

        # 4. Direct URL Guard: Try navigating to /staff/solar-vendors
        print("Testing Direct URL guard for /staff/solar-vendors...")
        await page.goto("http://localhost:5001/staff/solar-vendors", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        current_url = page.url
        print(f"Current URL after trying to access /staff/solar-vendors: {current_url}")
        assert "/staff/my-tenant" in current_url or "/staff/solar-vendors" not in current_url, "Unauthorized direct URL must be redirected"

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_entitlement_04_direct_url_vendor_guard.png")
        print("Captured: saas_entitlement_04_direct_url_vendor_guard.png")

        # 5. Internal Platform Employee (MR10001) - Full Navigation Untouched
        await page.evaluate(f"""() => {{
            localStorage.setItem('staff_token', '{mr_token}');
            localStorage.setItem('token', '{mr_token}');
            localStorage.setItem('staff_user', '{json.dumps(mr_user)}');
            localStorage.setItem('primary_company_id', '1');
            document.cookie = 'staff_token={mr_token}; path=/;';
            document.cookie = 'token={mr_token}; path=/;';
        }}""")

        await page.goto("http://localhost:5001/staff/dashboard", wait_until="networkidle")
        await page.wait_for_timeout(2500)

        mr_sidebar = await page.locator("#staffSidebar").inner_text()
        print("--- INTERNAL PLATFORM SIDEBAR ---")
        print(mr_sidebar[:500])
        print("---------------------------------")

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_entitlement_05_internal_platform_unaffected.png")
        print("Captured: saas_entitlement_05_internal_platform_unaffected.png")

        await browser.close()
        print("Visual verification complete!")

if __name__ == '__main__':
    asyncio.run(run_visual_verification())
