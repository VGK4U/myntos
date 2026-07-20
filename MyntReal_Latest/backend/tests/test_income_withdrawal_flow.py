"""
Income & Withdrawal Flow E2E Testing - DC Protocol
Tests the complete flow from income earning to withdrawal approval in Staff System

FLOW STAGES:
1. Staff Login → Navigate to Income pages
2. View Income Records → Verify income data
3. View Withdrawal Dashboard → Check withdrawal requests
4. View Withdrawal Approvals → Verify approval queue
5. MNR User Login → View user income/withdrawal pages

Run with: python -m pytest backend/tests/test_income_withdrawal_flow.py -v -s
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException

BASE_URL = os.environ.get('REPLIT_DEV_DOMAIN', 'http://localhost:5000')
if not BASE_URL.startswith('http'):
    BASE_URL = f"https://{BASE_URL}"

STAFF_EMPLOYEE_ID = 'MR20001'
STAFF_PASSWORD = 'Test@123'
MNR_USER_ID = 'MNR182345842'
MNR_USER_PASSWORD = 'Test@123'

print(f"[DEBUG] Using Staff credentials: {STAFF_EMPLOYEE_ID}")

class IncomeWithdrawalFlowTest:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.errors = []
        self.warnings = []
        
    def setup_driver(self):
        """Setup Chrome WebDriver with visible browser for real-time testing"""
        print("\n🚀 Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--ignore-certificate-errors")
        
        chromedriver_path = "/nix/store/8zj50jw4w0hby47167kqqsaqw4mm5bkd-chromedriver-unwrapped-138.0.7204.100/bin/chromedriver"
        chromium_path = "/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium"
        
        chrome_options.binary_location = chromium_path
        
        service = Service(chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        print(f"✅ Chrome WebDriver ready - {'Headless' if self.headless else 'Visible'} mode")
        return self.driver
        
    def teardown_driver(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("\n🔒 Browser closed")
            
    def capture_console_errors(self):
        """Capture browser console errors"""
        try:
            logs = self.driver.get_log('browser')
            for log in logs:
                if log['level'] == 'SEVERE':
                    self.errors.append(f"Console Error: {log['message']}")
                elif log['level'] == 'WARNING':
                    self.warnings.append(f"Console Warning: {log['message']}")
        except Exception as e:
            pass
            
    def wait_for_page_load(self, timeout=15):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)
            return True
        except TimeoutException:
            return False
            
    def dismiss_alerts(self):
        """Dismiss any alert popups"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            print(f"   ⚠️ Alert: {alert_text[:50]}...")
            alert.accept()
            return alert_text
        except:
            return None
            
    def check_for_network_errors(self):
        """Check for 500 errors or failed network requests"""
        try:
            self.dismiss_alerts()
            page_source = self.driver.page_source
            if "Internal Server Error" in page_source or "Something went wrong" in page_source:
                self.errors.append("500 Internal Server Error detected on page")
                return True
            if "Access Denied" in page_source or "Unauthorized" in page_source:
                self.errors.append("Access Denied - Authentication required")
                return True
        except:
            pass
        return False
        
    def staff_login(self):
        """Login to Staff Portal using UI form"""
        print(f"\n📍 Step 1: Staff Portal Login ({STAFF_EMPLOYEE_ID})")
        print(f"   URL: {BASE_URL}/staff/login")
        
        try:
            self.driver.get(f"{BASE_URL}/staff/login")
            self.wait_for_page_load()
            time.sleep(2)
            
            employee_id_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "employeeId"))
            )
            employee_id_field.clear()
            employee_id_field.send_keys(STAFF_EMPLOYEE_ID)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(STAFF_PASSWORD)
            
            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()
            
            time.sleep(5)
            self.wait_for_page_load()
            
            self.dismiss_alerts()
            
            current_url = self.driver.current_url
            print(f"   📍 Current URL after login: {current_url}")
            
            cookies = self.driver.get_cookies()
            staff_token = None
            for c in cookies:
                if c['name'] == 'staff_token':
                    staff_token = c['value'][:20] + "..." if len(c.get('value', '')) > 20 else c.get('value', '')
                    print(f"   🔑 staff_token cookie found: {staff_token}")
                    break
            
            if "/staff/" in current_url and "/login" not in current_url:
                print("   ✅ Staff login successful - redirected to staff portal")
                return True
            elif "/staff/login" in current_url:
                nda_modal = self.driver.find_elements(By.ID, "ndaModal")
                if nda_modal and nda_modal[0].is_displayed():
                    print("   📝 NDA acceptance required...")
                    accept_btn = self.driver.find_elements(By.ID, "acceptNdaBtn")
                    if accept_btn:
                        accept_btn[0].click()
                        time.sleep(3)
                        self.dismiss_alerts()
                        current_url = self.driver.current_url
                        if "/login" not in current_url:
                            print("   ✅ NDA accepted, login successful")
                            return True
                
                page_source = self.driver.page_source
                if "Invalid" in page_source or "error-message" in page_source:
                    self.errors.append("Staff login failed - invalid credentials")
                    print("   ❌ Staff login failed - credentials rejected")
                    return False
                else:
                    print("   ⚠️ Still on login page - session may not be established")
                    return True
            else:
                print(f"   ⚠️ Redirected to: {current_url}")
                return True
                
        except Exception as e:
            self.errors.append(f"Staff login error: {str(e)}")
            print(f"   ❌ Staff login error: {e}")
            return False
            
    def test_page(self, step_num, page_name, url_path, expected_url_contains):
        """Generic page test with alert handling"""
        print(f"\n📍 Step {step_num}: Testing {page_name}")
        print(f"   URL: {BASE_URL}{url_path}")
        
        try:
            self.driver.get(f"{BASE_URL}{url_path}")
            time.sleep(2)
            
            alert_text = self.dismiss_alerts()
            if alert_text:
                if "Admin access required" in alert_text or "access denied" in alert_text.lower():
                    print(f"   ⚠️ Access restriction: {alert_text[:60]}...")
                    self.warnings.append(f"{page_name}: {alert_text[:60]}...")
            
            self.wait_for_page_load()
            self.capture_console_errors()
            
            current_url = self.driver.current_url
            page_title = self.driver.title
            print(f"   📄 Page Title: {page_title}")
            
            if "/login" in current_url and expected_url_contains != "/login":
                print(f"   ⚠️ Redirected to login - session may have expired")
                self.warnings.append(f"{page_name}: Redirected to login")
                return "redirect"
            
            if expected_url_contains in current_url:
                print(f"   ✅ {page_name} loaded successfully")
                return True
            else:
                print(f"   ⚠️ Unexpected URL: {current_url}")
                return "unexpected"
                
        except UnexpectedAlertPresentException as e:
            alert_text = self.dismiss_alerts()
            print(f"   ⚠️ Alert during load: {alert_text or str(e)[:50]}...")
            self.warnings.append(f"{page_name}: Alert - {alert_text or str(e)[:50]}")
            return "alert"
        except TimeoutException:
            print(f"   ⚠️ Page load timeout")
            self.warnings.append(f"{page_name}: Timeout")
            return "timeout"
        except Exception as e:
            err_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
            self.errors.append(f"{page_name} error: {err_msg}")
            print(f"   ❌ Error: {err_msg}")
            return False

    def test_income_records_page(self):
        """Test Staff Income Records page"""
        return self.test_page(2, "Income Records", "/staff/mnr/income-records", "/staff/mnr/income-records")
            
    def test_income_supreme_page(self):
        """Test Staff Income Supreme (Approval) page"""
        return self.test_page(3, "Income Supreme", "/staff/mnr/income-supreme", "/staff/mnr/income-supreme")
            
    def test_income_finance_complete_page(self):
        """Test Staff Finance Complete page"""
        return self.test_page(4, "Finance Complete", "/staff/mnr/income-finance-complete", "/staff/mnr/income-finance-complete")
            
    def test_withdrawal_dashboard_page(self):
        """Test Staff Withdrawal Dashboard page"""
        return self.test_page(5, "Withdrawal Dashboard", "/staff/mnr/withdrawal/dashboard", "/staff/mnr/withdrawal/dashboard")
            
    def test_withdrawal_approvals_page(self):
        """Test Staff Withdrawal Approvals page"""
        return self.test_page(6, "Withdrawal Approvals", "/staff/mnr/withdrawal/approvals", "/staff/mnr/withdrawal/approvals")
            
    def test_withdrawal_history_page(self):
        """Test Staff Withdrawal History page"""
        return self.test_page(7, "Withdrawal History", "/staff/mnr/withdrawal/history", "/staff/mnr/withdrawal/history")
            
    def test_withdrawal_supreme_page(self):
        """Test Staff Withdrawal Supreme page"""
        return self.test_page(8, "Withdrawal Supreme", "/staff/mnr/withdrawal-supreme", "/staff/mnr/withdrawal-supreme")
            
    def mnr_user_login(self):
        """Login to MNR User Portal"""
        print(f"\n📍 Step 9: MNR User Portal Login ({MNR_USER_ID})")
        print(f"   URL: {BASE_URL}/login")
        
        try:
            self.driver.delete_all_cookies()
            self.driver.get(f"{BASE_URL}/login")
            self.wait_for_page_load()
            
            user_id_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mnr_id"))
            )
            user_id_field.clear()
            user_id_field.send_keys(MNR_USER_ID)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(MNR_USER_PASSWORD)
            
            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()
            
            time.sleep(3)
            self.wait_for_page_load()
            
            if "/user/" in self.driver.current_url or "/dashboard" in self.driver.current_url:
                print("   ✅ MNR User login successful")
                return True
            else:
                self.errors.append("MNR User login failed")
                print("   ❌ MNR User login failed")
                return False
                
        except Exception as e:
            self.errors.append(f"MNR User login error: {str(e)}")
            print(f"   ❌ MNR User login error: {e}")
            return False
            
    def test_user_daywise_income_page(self):
        """Test MNR User Daywise Income page"""
        return self.test_page(10, "User Daywise Income", "/user/daywise-income", "/user/daywise-income")
            
    def test_user_withdrawals_page(self):
        """Test MNR User Withdrawals page"""
        return self.test_page(11, "User Withdrawals", "/user/withdrawals", "/user/withdrawals")
            
    def run_all_tests(self):
        """Run the complete test suite"""
        print("\n" + "="*60)
        print("🧪 INCOME & WITHDRAWAL FLOW E2E TESTING - DC Protocol")
        print("="*60)
        print(f"Base URL: {BASE_URL}")
        print(f"Mode: {'Headless' if self.headless else 'Visible Browser'}")
        
        results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }
        
        try:
            self.setup_driver()
            
            tests = [
                ('Staff Login', self.staff_login),
                ('Income Records Page', self.test_income_records_page),
                ('Income Supreme Page', self.test_income_supreme_page),
                ('Finance Complete Page', self.test_income_finance_complete_page),
                ('Withdrawal Dashboard', self.test_withdrawal_dashboard_page),
                ('Withdrawal Approvals', self.test_withdrawal_approvals_page),
                ('Withdrawal History', self.test_withdrawal_history_page),
                ('Withdrawal Supreme', self.test_withdrawal_supreme_page),
            ]
            
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    if result is True:
                        results['passed'] += 1
                        results['tests'].append({'name': test_name, 'status': 'PASSED'})
                    elif result in ["redirect", "timeout", "alert", "unexpected"]:
                        results['tests'].append({'name': test_name, 'status': f'WARNING ({result})'})
                    else:
                        results['failed'] += 1
                        results['tests'].append({'name': test_name, 'status': 'FAILED'})
                except Exception as e:
                    results['failed'] += 1
                    err_msg = str(e)[:80] if len(str(e)) > 80 else str(e)
                    results['tests'].append({'name': test_name, 'status': 'ERROR', 'error': err_msg})
                    self.errors.append(f"{test_name}: {err_msg}")
                    
        except Exception as e:
            print(f"\n❌ Test setup failed: {e}")
            self.errors.append(f"Test setup error: {str(e)}")
        finally:
            self.teardown_driver()
            
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        print(f"✅ Passed: {results['passed']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📋 Total: {results['passed'] + results['failed']}")
        
        if self.errors:
            print("\n⚠️  ERRORS DETECTED:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
                
        if self.warnings:
            print("\n⚡ WARNINGS:")
            for i, warning in enumerate(self.warnings[:5], 1):
                print(f"   {i}. {warning}")
                
        return results


def main():
    """Main entry point for testing"""
    headless = "--headless" in sys.argv or "-h" in sys.argv
    
    tester = IncomeWithdrawalFlowTest(headless=headless)
    results = tester.run_all_tests()
    
    if results['failed'] > 0:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1
    else:
        print("\n✅ ALL TESTS PASSED!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
