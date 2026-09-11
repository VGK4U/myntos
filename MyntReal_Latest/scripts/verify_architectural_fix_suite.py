import asyncio
import time
import json
import urllib.request
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:5001"
API_BASE = "http://localhost:8000"

TEST_WORKFLOWS = [
    {"name": "Homepage", "url": f"{BASE_URL}/"},
    {"name": "/hub", "url": f"{BASE_URL}/hub"},
    {"name": "/mobile", "url": f"{BASE_URL}/mobile"},
    {"name": "Staff Login", "url": f"{BASE_URL}/staff/login"},
    {"name": "Progress", "url": f"{BASE_URL}/staff/crm/lead-progress"},
    {"name": "Staff Leads", "url": f"{BASE_URL}/staff/crm/leads"},
    {"name": "Vendors", "url": f"{BASE_URL}/staff/accounts/vendors"},
    {"name": "Parties", "url": f"{BASE_URL}/staff/accounts/parties"},
    {"name": "Estimations", "url": f"{BASE_URL}/staff/accounts/estimations"},
    {"name": "Timesheet", "url": f"{BASE_URL}/staff/timesheet"},
    {"name": "Tasks", "url": f"{BASE_URL}/staff/tasks/assigned-to-me"},
    {"name": "Expense Entries", "url": f"{BASE_URL}/staff/accounts/expense-entries"},
]

PUBLIC_APIS = [
    {"name": "Public Announcements", "url": f"{API_BASE}/api/v1/feedback/public/announcements?limit=10"},
    {"name": "Public Active Headers", "url": f"{API_BASE}/api/v1/community-services/public/active-headers"},
    {"name": "Public Hub Partners", "url": f"{API_BASE}/api/v1/hub/partners"},
]

async def run_workflow_suite():
    print("==================================================")
    print("STARTING PLAYWRIGHT REAL CHROMIUM VERIFICATION SUITE")
    print("==================================================")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Test Repeated Staff Login (5 cycles)
        login_timings = []
        for cycle in range(1, 6):
            context = await browser.new_context()
            page = await context.new_page()
            
            t0 = time.time()
            response = await page.goto(f"{BASE_URL}/staff/login", wait_until="networkidle", timeout=10000)
            status = response.status if response else 0
            dur = round((time.time() - t0) * 1000, 2)
            
            title = await page.title()
            has_emp_input = await page.locator("input#employee_id, input[name='employee_id'], input[type='text']").count() > 0
            
            error_text = ""
            error_el = page.locator(".alert-danger, .error-message, .error-banner, #errorMessage")
            if await error_el.count() > 0:
                error_text = await error_el.first.inner_text()
                
            login_timings.append({
                "cycle": cycle,
                "status": status,
                "duration_ms": dur,
                "title": title,
                "has_form": has_emp_input,
                "error": error_text
            })
            print(f"Cycle {cycle} Staff Login: Status {status}, Duration: {dur:6.1f}ms, Title: '{title}', Form: {has_emp_input}, Error: '{error_text}'")
            await context.close()

        # 2. Test All Critical Routes (each with isolated context)
        print("--------------------------------------------------")
        print("TESTING ALL CRITICAL WORKFLOW PAGES")
        print("--------------------------------------------------")
        route_results = []
        for wf in TEST_WORKFLOWS:
            context = await browser.new_context()
            page = await context.new_page()
            t0 = time.time()
            try:
                resp = await page.goto(wf["url"], wait_until="domcontentloaded", timeout=10000)
                status = resp.status if resp else 0
                dur = round((time.time() - t0) * 1000, 2)
                title = await page.title()
                route_results.append({
                    "name": wf["name"],
                    "url": wf["url"],
                    "status": status,
                    "duration_ms": dur,
                    "title": title,
                    "success": 200 <= status < 400
                })
                print(f"Workflow [{wf['name']:15}]: Status {status}, Duration {dur:6.1f}ms, Title: '{title}'")
            except Exception as e:
                dur = round((time.time() - t0) * 1000, 2)
                route_results.append({
                    "name": wf["name"],
                    "url": wf["url"],
                    "status": 0,
                    "duration_ms": dur,
                    "error": str(e),
                    "success": False
                })
                print(f"Workflow [{wf['name']:15}]: FAILED with error: {e}")
            finally:
                await context.close()

        await browser.close()

    # 3. Test Public APIs
    print("--------------------------------------------------")
    print("TESTING PUBLIC API ENDPOINTS")
    print("--------------------------------------------------")
    api_results = []
    for endpoint in PUBLIC_APIS:
        t0 = time.time()
        try:
            req = urllib.request.Request(endpoint["url"])
            with urllib.request.urlopen(req, timeout=5) as res:
                status = res.status
                body = res.read().decode('utf-8')
                dur = round((time.time() - t0) * 1000, 2)
                api_results.append({
                    "name": endpoint["name"],
                    "url": endpoint["url"],
                    "status": status,
                    "duration_ms": dur,
                    "success": 200 <= status < 400
                })
                print(f"API [{endpoint['name']:23}]: Status {status}, Duration {dur:6.1f}ms, Body length: {len(body)}")
        except Exception as e:
            dur = round((time.time() - t0) * 1000, 2)
            api_results.append({
                "name": endpoint["name"],
                "url": endpoint["url"],
                "status": 0,
                "duration_ms": dur,
                "error": str(e),
                "success": False
            })
            print(f"API [{endpoint['name']:23}]: FAILED with error: {e}")

    report = {
        "login_test": login_timings,
        "route_test": route_results,
        "api_test": api_results,
        "all_passed": (
            all(r["success"] for r in route_results) and 
            all(l["status"] == 200 and not l["error"] for l in login_timings) and
            all(a["success"] for a in api_results)
        )
    }
    
    with open("/Users/viswanathkari/.gemini/antigravity/brain/1c1ea9af-52ca-4436-b550-0a790b1f545a/scratch/architectural_fix_verification.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print("==================================================")
    print(f"ALL TESTS COMPLETE. ALL PASSED: {report['all_passed']}")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_workflow_suite())
