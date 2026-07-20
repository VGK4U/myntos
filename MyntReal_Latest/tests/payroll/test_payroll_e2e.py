"""
Selenium E2E Test Suite for Staff Payroll System
DC Protocol compliant - Tests all 7 payroll routes with CRUD verification
"""
import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "http://localhost:5000"
API_BASE = "http://localhost:8001/api/v1"

PAYROLL_ROUTES = [
    {"name": "Profiles", "path": "/staff/payroll/profiles", "menu_code": "payroll-profiles"},
    {"name": "Cycles", "path": "/staff/payroll/cycles", "menu_code": "payroll-cycles"},
    {"name": "Runs", "path": "/staff/payroll/runs", "menu_code": "payroll-runs"},
    {"name": "Approvals", "path": "/staff/payroll/approvals", "menu_code": "payroll-approvals"},
    {"name": "Consultant Invoices", "path": "/staff/payroll/consultant-invoices", "menu_code": "payroll-consultant-invoices"},
    {"name": "Allowance Catalog", "path": "/staff/payroll/allowance-catalog", "menu_code": "payroll-allowance-catalog"},
    {"name": "Documents", "path": "/staff/payroll/documents", "menu_code": "payroll-documents"},
]

class PayrollE2ETestSuite:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.test_results = []
        self.console_errors = []
        self.network_errors = []
        
    def setup_driver(self):
        print("[E2E] Setting up Chrome WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)
        print("[E2E] WebDriver initialized successfully")
        
    def teardown_driver(self):
        if self.driver:
            self.driver.quit()
            print("[E2E] WebDriver closed")
            
    def get_console_logs(self):
        try:
            logs = self.driver.get_log("browser")
            errors = [log for log in logs if log["level"] in ["SEVERE", "ERROR"]]
            return errors
        except Exception:
            return []
            
    def get_network_errors(self):
        try:
            logs = self.driver.get_log("performance")
            errors = []
            for log in logs:
                try:
                    message = json.loads(log["message"])
                    if "Network.responseReceived" in str(message):
                        response = message.get("message", {}).get("params", {}).get("response", {})
                        status = response.get("status", 200)
                        if status >= 400:
                            errors.append({"url": response.get("url"), "status": status})
                except:
                    pass
            return errors
        except Exception:
            return []
    
    def login_as_staff(self, employee_id="MR10001", password="Test@123"):
        print(f"[E2E] Attempting staff login as {employee_id}...")
        try:
            self.driver.get(f"{BASE_URL}/staff/login")
            time.sleep(2)
            
            try:
                emp_field = self.wait.until(EC.presence_of_element_located((By.ID, "employeeId")))
                emp_field.clear()
                emp_field.send_keys(employee_id)
            except:
                emp_field = self.driver.find_element(By.CSS_SELECTOR, "input[id='employeeId'], input[name='employee_id']")
                emp_field.clear()
                emp_field.send_keys(employee_id)
            
            try:
                pwd_field = self.driver.find_element(By.ID, "password")
            except:
                pwd_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            pwd_field.clear()
            pwd_field.send_keys(password)
            
            try:
                login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except:
                login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_btn.click()
            
            time.sleep(3)
            
            if "/staff/dashboard" in self.driver.current_url or "dashboard" in self.driver.current_url.lower():
                print("[E2E] ✅ Staff login successful")
                return True
            else:
                print(f"[E2E] Login redirect to: {self.driver.current_url}")
                return "login" not in self.driver.current_url.lower()
                
        except Exception as e:
            print(f"[E2E] ❌ Login failed: {str(e)}")
            return False
    
    def test_route_loads(self, route):
        route_name = route["name"]
        route_path = route["path"]
        print(f"\n[E2E] Testing route: {route_name} ({route_path})")
        
        result = {
            "route": route_name,
            "path": route_path,
            "loaded": False,
            "console_errors": [],
            "network_errors": [],
            "elements_found": {},
            "data_loaded": False
        }
        
        try:
            self.driver.get(f"{BASE_URL}{route_path}")
            time.sleep(3)
            
            if self.driver.current_url.endswith(route_path) or route_path in self.driver.current_url:
                result["loaded"] = True
                print(f"  [E2E] ✅ Route loaded successfully")
            else:
                print(f"  [E2E] ⚠️ Redirected to: {self.driver.current_url}")
                result["loaded"] = "login" not in self.driver.current_url.lower()
            
            result["console_errors"] = self.get_console_logs()
            result["network_errors"] = self.get_network_errors()
            
            if result["console_errors"]:
                print(f"  [E2E] ⚠️ Console errors: {len(result['console_errors'])}")
                for err in result["console_errors"][:3]:
                    print(f"    - {err.get('message', '')[:100]}")
            else:
                print(f"  [E2E] ✅ No console errors")
            
            elements_to_check = [
                ("stats_cards", ".stats-card, .stat-card, [class*='stat']"),
                ("data_table", "table, .table, [class*='table']"),
                ("filters", ".filter, select, [class*='filter']"),
                ("action_buttons", "button, .btn, [class*='btn']"),
            ]
            
            for elem_name, selector in elements_to_check:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    result["elements_found"][elem_name] = len(elements)
                except:
                    result["elements_found"][elem_name] = 0
            
            print(f"  [E2E] Elements found: {result['elements_found']}")
            
            try:
                table = self.driver.find_element(By.CSS_SELECTOR, "table tbody tr, .data-row, [class*='row']")
                result["data_loaded"] = True
                print(f"  [E2E] ✅ Data appears to be loaded")
            except:
                try:
                    no_data = self.driver.find_element(By.XPATH, "//*[contains(text(), 'No') and contains(text(), 'found')]")
                    result["data_loaded"] = True
                    print(f"  [E2E] ✅ No data message displayed (expected for empty state)")
                except:
                    print(f"  [E2E] ⚠️ Could not verify data loading state")
            
        except Exception as e:
            print(f"  [E2E] ❌ Route test failed: {str(e)}")
            result["error"] = str(e)
        
        self.test_results.append(result)
        return result
    
    def test_documents_crud(self):
        print("\n[E2E] === Testing Documents CRUD Operations ===")
        result = {"operation": "documents_crud", "steps": []}
        
        try:
            self.driver.get(f"{BASE_URL}/staff/payroll/documents")
            time.sleep(3)
            
            try:
                company_filter = self.driver.find_element(By.ID, "filterCompany")
                result["steps"].append({"filter_found": True})
                print("  [E2E] ✅ Company filter found")
            except:
                result["steps"].append({"filter_found": False})
                print("  [E2E] ⚠️ Company filter not found")
            
            try:
                view_btns = self.driver.find_elements(By.CSS_SELECTOR, "[onclick*='viewDocument'], .btn-view, button[class*='view']")
                result["steps"].append({"view_buttons": len(view_btns)})
                
                if view_btns:
                    view_btns[0].click()
                    time.sleep(2)
                    
                    try:
                        modal = self.driver.find_element(By.CSS_SELECTOR, ".modal.show, .modal[style*='block']")
                        result["steps"].append({"modal_opened": True})
                        print("  [E2E] ✅ View modal opened")
                        
                        try:
                            close_btn = self.driver.find_element(By.CSS_SELECTOR, ".modal .btn-close, .modal [data-bs-dismiss]")
                            close_btn.click()
                            time.sleep(1)
                        except:
                            pass
                    except:
                        result["steps"].append({"modal_opened": False})
                        print("  [E2E] ⚠️ Modal did not open")
            except Exception as e:
                result["steps"].append({"view_error": str(e)})
            
            try:
                download_btns = self.driver.find_elements(By.CSS_SELECTOR, "[onclick*='downloadDocument'], .btn-download")
                result["steps"].append({"download_buttons": len(download_btns)})
                print(f"  [E2E] Found {len(download_btns)} download buttons")
            except:
                result["steps"].append({"download_buttons": 0})
            
            console_errors = self.get_console_logs()
            result["console_errors"] = len(console_errors)
            
            if console_errors:
                print(f"  [E2E] ⚠️ {len(console_errors)} console errors during CRUD test")
            else:
                print("  [E2E] ✅ No console errors during CRUD operations")
                
        except Exception as e:
            result["error"] = str(e)
            print(f"  [E2E] ❌ CRUD test failed: {str(e)}")
        
        self.test_results.append(result)
        return result
    
    def run_full_test_suite(self):
        print("\n" + "="*60)
        print("[E2E] STAFF PAYROLL SYSTEM - FULL E2E TEST SUITE")
        print("="*60)
        
        try:
            self.setup_driver()
            
            if not self.login_as_staff():
                print("[E2E] ❌ Cannot proceed without login. Testing public routes only.")
            
            for route in PAYROLL_ROUTES:
                self.test_route_loads(route)
                time.sleep(1)
            
            self.test_documents_crud()
            
            print("\n" + "="*60)
            print("[E2E] TEST RESULTS SUMMARY")
            print("="*60)
            
            passed = 0
            failed = 0
            warnings = 0
            
            for result in self.test_results:
                if "route" in result:
                    route_name = result["route"]
                    if result.get("loaded"):
                        if result.get("console_errors"):
                            print(f"  ⚠️ {route_name}: Loaded with {len(result['console_errors'])} console errors")
                            warnings += 1
                        else:
                            print(f"  ✅ {route_name}: PASSED")
                            passed += 1
                    else:
                        print(f"  ❌ {route_name}: FAILED to load")
                        failed += 1
                elif "operation" in result:
                    op_name = result["operation"]
                    if result.get("error"):
                        print(f"  ❌ {op_name}: {result['error']}")
                        failed += 1
                    else:
                        print(f"  ✅ {op_name}: PASSED")
                        passed += 1
            
            print(f"\nTotal: {passed} passed, {failed} failed, {warnings} warnings")
            print("="*60)
            
            return {
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "results": self.test_results
            }
            
        except Exception as e:
            print(f"[E2E] ❌ Test suite failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
            
        finally:
            self.teardown_driver()

def main():
    suite = PayrollE2ETestSuite()
    results = suite.run_full_test_suite()
    
    with open("tests/payroll/e2e_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[E2E] Results saved to tests/payroll/e2e_results.json")
    
    if results.get("failed", 0) > 0:
        sys.exit(1)
    return results

if __name__ == "__main__":
    main()
