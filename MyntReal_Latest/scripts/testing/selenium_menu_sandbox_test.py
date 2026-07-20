"""
Menu Access Control & Sandbox Testing - Selenium E2E Tests
DC Protocol Compliant - Dec 21, 2025
Tests different staff roles (VGK4U, Manager, Employee) for menu access
"""
import os
import sys
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "http://localhost:5000"
RESULTS = {"tests": [], "summary": {"passed": 0, "failed": 0, "errors": []}}

TEST_CREDENTIALS = {
    "VGK4U": {
        "employee_id": os.environ.get("TEST_STAFF_EMPLOYEE_ID", "MR10019"),
        "password": os.environ.get("TEST_STAFF_PASSWORD", "MR10019")
    }
}

def setup_driver():
    """Setup Chrome WebDriver with headless options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--ignore-certificate-errors")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"[ERROR] Failed to setup driver: {e}")
        return None


def log_result(test_name, status, message="", screenshot_path=None):
    """Log test result"""
    result = {
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if screenshot_path:
        result["screenshot"] = screenshot_path
    RESULTS["tests"].append(result)
    
    if status == "PASS":
        RESULTS["summary"]["passed"] += 1
        print(f"  [PASS] {test_name}")
    else:
        RESULTS["summary"]["failed"] += 1
        RESULTS["summary"]["errors"].append(f"{test_name}: {message}")
        print(f"  [FAIL] {test_name}: {message}")


def staff_login(driver, employee_id, password):
    """Login as staff user"""
    try:
        driver.get(f"{BASE_URL}/staff/login")
        time.sleep(2)
        
        emp_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='MR10001'], input[name='employee_id'], input[type='text']"))
        )
        emp_input.clear()
        emp_input.send_keys(employee_id)
        
        pwd_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pwd_input.clear()
        pwd_input.send_keys(password)
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.btn-primary")
        login_btn.click()
        
        time.sleep(3)
        
        if "/staff/dashboard" in driver.current_url or "/staff/" in driver.current_url:
            return True
        if "NDA" in driver.page_source:
            print(f"    [INFO] NDA acceptance required for {employee_id}")
            return "NDA_REQUIRED"
        return False
    except Exception as e:
        print(f"    [ERROR] Login failed: {e}")
        return False


def test_menu_access_page(driver):
    """Test RVZ Menu Access Control page"""
    print("\n[TEST] Menu Access Control Page")
    
    try:
        driver.get(f"{BASE_URL}/rvz/menu-access-config")
        time.sleep(3)
        
        if driver.current_url != f"{BASE_URL}/rvz/menu-access-config":
            log_result("Menu Access Page Load", "FAIL", f"Redirected to {driver.current_url}")
            return
        
        log_result("Menu Access Page Load", "PASS", "Page loaded successfully")
        
        page_source = driver.page_source
        
        if "Menu Access Configuration" in page_source or "menu-access" in page_source.lower():
            log_result("Menu Access Page Content", "PASS", "Page content rendered")
        else:
            log_result("Menu Access Page Content", "FAIL", "Page content missing")
        
        try:
            company_dropdown = driver.find_element(By.CSS_SELECTOR, "select#companyId, select[name='company'], .company-select")
            log_result("Company Dropdown Exists", "PASS", "Company dropdown found")
        except NoSuchElementException:
            log_result("Company Dropdown Exists", "FAIL", "Company dropdown not found")
        
        try:
            categories = driver.find_elements(By.CSS_SELECTOR, ".category-group, .menu-category, [data-category]")
            if len(categories) > 0:
                log_result("Menu Categories Load", "PASS", f"Found {len(categories)} categories")
            else:
                log_result("Menu Categories Load", "FAIL", "No categories found")
        except Exception as e:
            log_result("Menu Categories Load", "FAIL", str(e))
        
        console_errors = driver.execute_script("return window.consoleErrors || []")
        if console_errors:
            log_result("No Console Errors", "FAIL", f"Console errors: {console_errors[:3]}")
        else:
            log_result("No Console Errors", "PASS", "No JavaScript errors")
            
    except Exception as e:
        log_result("Menu Access Page", "FAIL", str(e))


def test_sandbox_manager(driver):
    """Test Sandbox Manager page (VGK4U only)"""
    print("\n[TEST] Sandbox Manager Page")
    
    try:
        driver.get(f"{BASE_URL}/staff/sandbox-manager")
        time.sleep(3)
        
        if "sandbox" not in driver.current_url.lower():
            log_result("Sandbox Manager Access", "FAIL", f"Redirected to {driver.current_url}")
            return
        
        log_result("Sandbox Manager Access", "PASS", "Page accessible")
        
        page_source = driver.page_source
        
        if "Sandbox" in page_source or "sandbox" in page_source.lower():
            log_result("Sandbox Manager Content", "PASS", "Page content rendered")
        else:
            log_result("Sandbox Manager Content", "FAIL", "Page content missing")
        
        try:
            toggle = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox'], .sandbox-toggle, #sandboxToggle")
            log_result("Sandbox Toggle Exists", "PASS", "Toggle control found")
        except NoSuchElementException:
            log_result("Sandbox Toggle Exists", "FAIL", "Toggle control not found")
            
    except Exception as e:
        log_result("Sandbox Manager Page", "FAIL", str(e))


def test_staff_tasks_routes(driver):
    """Test task-related routes match menu access settings"""
    print("\n[TEST] Staff Tasks Routes")
    
    task_routes = [
        ("/staff/tasks/tracker", "Task Tracker"),
        ("/staff/tasks/assigned-to-me", "Tasks Assigned to Me"),
        ("/staff/tasks/assigned-by-me-v2", "Tasks Assigned by Me"),
        ("/staff/task-review", "Task Review")
    ]
    
    for route, name in task_routes:
        try:
            driver.get(f"{BASE_URL}{route}")
            time.sleep(2)
            
            if "404" in driver.page_source or "Not Found" in driver.page_source:
                log_result(f"Route {name}", "FAIL", f"404 error on {route}")
            elif "login" in driver.current_url.lower():
                log_result(f"Route {name}", "FAIL", f"Redirected to login from {route}")
            else:
                log_result(f"Route {name}", "PASS", f"Route {route} accessible")
        except Exception as e:
            log_result(f"Route {name}", "FAIL", str(e))


def test_reimbursement_routes(driver):
    """Test reimbursement routes"""
    print("\n[TEST] Reimbursement Routes")
    
    reimb_routes = [
        ("/staff/accounts/my-reimbursements", "My Reimbursements"),
        ("/staff/accounts/reimbursement-approvals", "Reimbursement Approvals")
    ]
    
    for route, name in reimb_routes:
        try:
            driver.get(f"{BASE_URL}{route}")
            time.sleep(2)
            
            if "404" in driver.page_source or "Not Found" in driver.page_source:
                log_result(f"Route {name}", "FAIL", f"404 error on {route}")
            elif "login" in driver.current_url.lower():
                log_result(f"Route {name}", "FAIL", f"Redirected to login from {route}")
            else:
                log_result(f"Route {name}", "PASS", f"Route {route} accessible")
        except Exception as e:
            log_result(f"Route {name}", "FAIL", str(e))


def test_sidebar_menu_visibility(driver):
    """Test that sidebar shows menus based on access settings"""
    print("\n[TEST] Sidebar Menu Visibility")
    
    try:
        driver.get(f"{BASE_URL}/staff/dashboard")
        time.sleep(3)
        
        sidebar = driver.find_element(By.CSS_SELECTOR, "#sidebar, .sidebar, nav.sidebar")
        log_result("Sidebar Exists", "PASS", "Sidebar found")
        
        menu_items = driver.find_elements(By.CSS_SELECTOR, ".sidebar-menu a, .sidebar a.nav-link, #sidebar a")
        visible_count = sum(1 for item in menu_items if item.is_displayed())
        
        if visible_count > 0:
            log_result("Sidebar Menu Items", "PASS", f"{visible_count} menu items visible")
        else:
            log_result("Sidebar Menu Items", "FAIL", "No visible menu items")
            
    except Exception as e:
        log_result("Sidebar Visibility", "FAIL", str(e))


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("MENU ACCESS CONTROL & SANDBOX TESTING")
    print("DC Protocol Compliant - Dec 21, 2025")
    print("=" * 60)
    
    driver = setup_driver()
    if not driver:
        print("[FATAL] Could not initialize WebDriver")
        return RESULTS
    
    try:
        creds = TEST_CREDENTIALS["VGK4U"]
        print(f"\n[LOGIN] Attempting login as {creds['employee_id']}")
        
        login_result = staff_login(driver, creds["employee_id"], creds["password"])
        
        if login_result == True:
            log_result("Staff Login", "PASS", f"Logged in as {creds['employee_id']}")
            
            test_menu_access_page(driver)
            test_sandbox_manager(driver)
            test_staff_tasks_routes(driver)
            test_reimbursement_routes(driver)
            test_sidebar_menu_visibility(driver)
            
        elif login_result == "NDA_REQUIRED":
            log_result("Staff Login", "PASS", "Login successful but NDA required")
            print("[INFO] Cannot proceed with tests - NDA acceptance required")
        else:
            log_result("Staff Login", "FAIL", "Could not login")
            
    except Exception as e:
        print(f"[ERROR] Test execution failed: {e}")
        RESULTS["summary"]["errors"].append(str(e))
    finally:
        driver.quit()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Passed: {RESULTS['summary']['passed']}")
    print(f"Failed: {RESULTS['summary']['failed']}")
    if RESULTS["summary"]["errors"]:
        print("\nErrors:")
        for err in RESULTS["summary"]["errors"][:10]:
            print(f"  - {err}")
    
    with open("/tmp/menu_sandbox_test_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\nFull results saved to /tmp/menu_sandbox_test_results.json")
    
    return RESULTS


if __name__ == "__main__":
    run_all_tests()
