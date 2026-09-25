import asyncio
import json
import os
from playwright.async_api import async_playwright
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.core.security import SecurityManager

SCREENSHOTS_DIR = "/Users/viswanathkari/.gemini/antigravity/brain/fe0b1cb9-cff8-421f-88dc-78cc676d16ad/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_teso_auth():
    db = SessionLocal()
    try:
        s = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()
        token = SecurityManager.create_access_token(
            data={
                "sub": str(s.id),
                "emp_code": s.emp_code,
                "email": s.email,
                "role": s.role.role_code if s.role else "admin",
                "staff_type": getattr(s, "staff_type", "TENANT_ADMIN"),
                "admin_scope": getattr(s, "admin_scope", "CLIENT_SPECIFIC"),
                "base_company_id": s.base_company_id,
                "tenant_id": getattr(s, "tenant_id", 190) or 190,
                "token_version": getattr(s, "token_version", 1) or 1,
                "team_tag": s.team_tag,
                "user_type": "staff"
            }
        )
        user_dict = {
            "id": s.id,
            "emp_code": s.emp_code,
            "full_name": s.full_name or "Test Solar Admin",
            "email": s.email,
            "role": s.role.role_code if s.role else "admin",
            "staff_type": s.staff_type,
            "base_company_id": s.base_company_id,
            "tenant_id": s.tenant_id,
            "accessible_company_ids": [127],
            "primary_company_id": 127
        }
        return token, user_dict
    finally:
        db.close()

async def run_visual_verification():
    token, user_dict = get_teso_auth()
    print(f"Generated token for TESO_ADMIN (Tenant 190, Company 127)")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        page.on("console", lambda msg: print(f"[BROWSER CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}"))
        page.on("response", lambda res: print(f"[RESP {res.status}] {res.url}") if res.status >= 400 else None)
        page.on("requestfailed", lambda req: print(f"[REQ FAILED] {req.url}: {req.failure}"))

        await context.add_cookies([
            {"name": "staff_token", "value": token, "domain": "localhost", "path": "/"},
            {"name": "token", "value": token, "domain": "localhost", "path": "/"}
        ])

        # Set localStorage before page load
        await page.goto("http://localhost:5001/staff/saas-crm-settings")
        await page.evaluate(f"""() => {{
            localStorage.setItem('staff_token', '{token}');
            localStorage.setItem('token', '{token}');
            localStorage.setItem('staff_user', '{json.dumps(user_dict)}');
            localStorage.setItem('primary_company_id', '127');
            document.cookie = 'staff_token={token}; path=/;';
            document.cookie = 'token={token}; path=/;';
        }}""")
        
        # 1. Reload CRM Settings page
        await page.goto("http://localhost:5001/staff/saas-crm-settings", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Verify sidebar and header
        sidebar_visible = await page.is_visible("#staffSidebar")
        header_visible = (await page.is_visible(".top-header")) or (await page.is_visible("#headerContainer"))
        print(f"CRM Setup Shell: Sidebar visible={sidebar_visible}, Header visible={header_visible}")
        assert sidebar_visible, "StaffSidebar must be visible"
        assert header_visible, "Header must be visible"

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_crm_setup_tab1_settings.png")
        print("Captured: saas_crm_setup_tab1_settings.png")

        # 2. Switch to Segments Tab (Tab 3)
        await page.click("#tabBtn_segments")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_crm_setup_tab3_segments_table.png")
        print("Captured: saas_crm_setup_tab3_segments_table.png")

        # 3. Open Add Segment Modal
        await page.click("button[onclick='openAddSegmentModal()']")
        await page.wait_for_timeout(1000)
        
        modal_vendor_visible = await page.is_visible("#seg_vendor_company_id")
        modal_staff_visible = await page.is_visible("#segStaffCheckboxesList")
        print(f"Segment Modal: Vendor selector visible={modal_vendor_visible}, Staff checkboxes visible={modal_staff_visible}")
        assert modal_vendor_visible, "Vendor legal entity dropdown must be present"
        assert modal_staff_visible, "Default routing staff list must be present"

        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_crm_setup_segment_modal_with_vendor_and_staff.png")
        print("Captured: saas_crm_setup_segment_modal_with_vendor_and_staff.png")

        # 4. Navigate to CRM Dashboard -> Tab 3 Call Tracking & Logs
        await page.goto("http://localhost:5001/staff_crm_dashboard.html", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Click Call Tracking Tab
        await page.click("button[data-tab='calls']")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_crm_dashboard_call_tracking_tenant_scoped.png")
        print("Captured: saas_crm_dashboard_call_tracking_tenant_scoped.png")

        # 5. Navigate to Staff Leads -> Open Add Lead Modal
        await page.goto("http://localhost:5001/staff_leads.html", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        add_lead_btn = page.locator("button[data-bs-target='#leadModal'], button[onclick='openAddModal()']").first
        if await add_lead_btn.count() > 0:
            await add_lead_btn.click()
            await page.wait_for_timeout(1500)
            
            # Select category
            cat_options = await page.locator("#leadCategory option").all_inner_texts()
            print(f"Lead categories available: {cat_options}")
            if len(cat_options) > 1:
                # Select first real category
                await page.select_option("#leadCategory", index=1)
                await page.wait_for_timeout(1500)

            await page.screenshot(path=f"{SCREENSHOTS_DIR}/saas_crm_lead_creation_modal_with_segment_routing.png")
            print("Captured: saas_crm_lead_creation_modal_with_segment_routing.png")

        await browser.close()
        print("All visual verification tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_visual_verification())
