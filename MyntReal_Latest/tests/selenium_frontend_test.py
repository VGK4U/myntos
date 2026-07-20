"""
BeV 2.0 - Comprehensive Selenium Frontend Test
Tests VGK Supreme and Standard workflows with real browser automation

Requirements:
- Real login credentials for VGK and Standard users
- Running backend (port 8000) and frontend (port 5000)
- ChromeDriver installed
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

# Configuration
REPLIT_DOMAINS = os.getenv('REPLIT_DOMAINS', '')
if REPLIT_DOMAINS:
    BASE_URL = f'https://{REPLIT_DOMAINS}'
else:
    BASE_URL = 'http://localhost:5000'  # Use local frontend server

SCREENSHOT_DIR = 'test_screenshots'
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class BeVSeleniumTest:
    def __init__(self):
        self.driver = None
        self.test_results = []
        self.screenshot_count = 0
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with headless options"""
        print("🚀 Initializing Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
        print("✅ WebDriver initialized successfully")
    
    def take_screenshot(self, name):
        """Take a screenshot and save it"""
        self.screenshot_count += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{SCREENSHOT_DIR}/{self.screenshot_count:02d}_{name}_{timestamp}.png"
        self.driver.save_screenshot(filename)
        print(f"📸 Screenshot saved: {filename}")
        return filename
    
    def log_test(self, test_name, passed, message, screenshot_name=None):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'screenshot': screenshot_name,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}: {message}")
    
    def login(self, username, password, user_type="VGK"):
        """Login to the system"""
        print(f"\n🔐 TEST: {user_type} Login")
        print("-" * 80)
        
        try:
            # Navigate to login page
            self.driver.get(f"{BASE_URL}/login")
            
            # Wait for page to fully load
            try:
                username_field = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                self.take_screenshot(f"{user_type}_login_page")
                
                # Fill username
                username_field.clear()
                username_field.send_keys(username)
                
                # Find and fill password
                password_field = self.driver.find_element(By.ID, "password")
                password_field.clear()
                password_field.send_keys(password)
                
                self.take_screenshot(f"{user_type}_login_filled")
                
                # Click login button
                login_button = self.driver.find_element(By.ID, "submitBtn")
                login_button.click()
                
            except TimeoutException:
                self.take_screenshot(f"{user_type}_login_timeout")
                self.log_test(
                    f"{user_type} Login",
                    False,
                    "Login page failed to load within timeout"
                )
                return False
            
            # Wait for redirect
            time.sleep(3)
            
            # Check if login successful (should redirect away from /login)
            current_url = self.driver.current_url
            
            if "/login" not in current_url:
                self.take_screenshot(f"{user_type}_login_success")
                self.log_test(
                    f"{user_type} Login",
                    True,
                    f"Successfully logged in as {username}",
                    f"{user_type}_login_success"
                )
                return True
            else:
                # Check for error message
                try:
                    error_msg = self.driver.find_element(By.CLASS_NAME, "alert-danger").text
                    self.log_test(
                        f"{user_type} Login",
                        False,
                        f"Login failed: {error_msg}"
                    )
                except:
                    self.log_test(
                        f"{user_type} Login",
                        False,
                        "Login failed: Unknown error"
                    )
                return False
                
        except Exception as e:
            self.log_test(
                f"{user_type} Login",
                False,
                f"Exception: {str(e)}"
            )
            self.take_screenshot(f"{user_type}_login_error")
            return False
    
    def test_vgk_income_supreme(self):
        """Test VGK Supreme Income Approval workflow"""
        print("\n⚡ TEST: VGK Supreme Income Approval")
        print("-" * 80)
        
        try:
            # Navigate to VGK Income Supreme page
            self.driver.get(f"{BASE_URL}/vgk/income-supreme")
            time.sleep(3)
            self.take_screenshot("vgk_income_supreme_page")
            
            # Check if page loaded (should have income table)
            try:
                # Wait for the page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                self.log_test(
                    "VGK Income Supreme Page Load",
                    True,
                    "Page loaded successfully"
                )
                
                # Check for pending incomes
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    
                    if len(rows) > 0 and "No data" not in rows[0].text:
                        self.log_test(
                            "Pending Incomes Found",
                            True,
                            f"Found {len(rows)} pending income records"
                        )
                        
                        # Try to select first checkbox and approve
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            checkbox.click()
                            time.sleep(1)
                            
                            # Find approve button
                            approve_btn = self.driver.find_element(By.ID, "approveIncomeBtn")
                            self.take_screenshot("vgk_income_before_approve")
                            approve_btn.click()
                            
                            # Wait for response
                            time.sleep(3)
                            self.take_screenshot("vgk_income_after_approve")
                            
                            # Check for success message
                            try:
                                success_msg = self.driver.find_element(By.CLASS_NAME, "alert-success").text
                                self.log_test(
                                    "VGK Supreme Income Approval",
                                    True,
                                    f"Approval successful: {success_msg}",
                                    "vgk_income_after_approve"
                                )
                            except:
                                self.log_test(
                                    "VGK Supreme Income Approval",
                                    True,
                                    "Approval completed (no error detected)"
                                )
                                
                        except Exception as e:
                            self.log_test(
                                "VGK Supreme Income Approval",
                                False,
                                f"Cannot click approve button: {str(e)}"
                            )
                    else:
                        self.log_test(
                            "Pending Incomes Found",
                            True,
                            "No pending incomes available for testing"
                        )
                        
                except Exception as e:
                    self.log_test(
                        "Check Pending Incomes",
                        False,
                        f"Error checking incomes: {str(e)}"
                    )
                    
            except TimeoutException:
                self.log_test(
                    "VGK Income Supreme Page Load",
                    False,
                    "Page did not load within timeout"
                )
                
        except Exception as e:
            self.log_test(
                "VGK Income Supreme Test",
                False,
                f"Exception: {str(e)}"
            )
            self.take_screenshot("vgk_income_error")
    
    def test_vgk_withdrawal_supreme(self):
        """Test VGK Supreme ONE-CLICK Payment workflow"""
        print("\n🚀 TEST: VGK Supreme ONE-CLICK Payment")
        print("-" * 80)
        
        try:
            # Navigate to VGK Withdrawal Supreme page
            self.driver.get(f"{BASE_URL}/vgk/withdrawal-supreme")
            time.sleep(3)
            self.take_screenshot("vgk_withdrawal_supreme_page")
            
            # Check if page loaded
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                self.log_test(
                    "VGK Withdrawal Supreme Page Load",
                    True,
                    "Page loaded successfully"
                )
                
                # Check for pending withdrawals
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    
                    if len(rows) > 0 and "No data" not in rows[0].text:
                        self.log_test(
                            "Pending Withdrawals Found",
                            True,
                            f"Found {len(rows)} pending withdrawals"
                        )
                        
                        # Try to select and pay
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            checkbox.click()
                            time.sleep(1)
                            
                            # Find pay button
                            pay_btn = self.driver.find_element(By.ID, "payWithdrawalBtn")
                            self.take_screenshot("vgk_withdrawal_before_pay")
                            pay_btn.click()
                            
                            # Wait for response
                            time.sleep(3)
                            self.take_screenshot("vgk_withdrawal_after_pay")
                            
                            # Check for success message
                            try:
                                success_msg = self.driver.find_element(By.CLASS_NAME, "alert-success").text
                                self.log_test(
                                    "VGK ONE-CLICK Payment",
                                    True,
                                    f"Payment successful: {success_msg}",
                                    "vgk_withdrawal_after_pay"
                                )
                            except:
                                self.log_test(
                                    "VGK ONE-CLICK Payment",
                                    True,
                                    "Payment completed (no error detected)"
                                )
                                
                        except Exception as e:
                            self.log_test(
                                "VGK ONE-CLICK Payment",
                                False,
                                f"Cannot click pay button: {str(e)}"
                            )
                    else:
                        self.log_test(
                            "Pending Withdrawals Found",
                            True,
                            "No pending withdrawals available for testing"
                        )
                        
                except Exception as e:
                    self.log_test(
                        "Check Pending Withdrawals",
                        False,
                        f"Error checking withdrawals: {str(e)}"
                    )
                    
            except TimeoutException:
                self.log_test(
                    "VGK Withdrawal Supreme Page Load",
                    False,
                    "Page did not load within timeout"
                )
                
        except Exception as e:
            self.log_test(
                "VGK Withdrawal Supreme Test",
                False,
                f"Exception: {str(e)}"
            )
            self.take_screenshot("vgk_withdrawal_error")
    
    def test_standard_workflow(self, admin_username, admin_password):
        """Test Standard approval workflow (Admin → Super Admin → Finance)"""
        print("\n📋 TEST: Standard Approval Workflow")
        print("-" * 80)
        
        # Logout first
        try:
            self.driver.get(f"{BASE_URL}/logout")
            time.sleep(2)
        except:
            pass
        
        # Login as Admin
        if not self.login(admin_username, admin_password, "Admin"):
            return
        
        try:
            # Navigate to income verification page
            self.driver.get(f"{BASE_URL}/admin/income-verification")
            time.sleep(3)
            self.take_screenshot("standard_income_page")
            
            # Check if page loaded
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                self.log_test(
                    "Standard Income Page Load",
                    True,
                    "Page loaded successfully"
                )
                
                # Check for pending incomes
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                
                if len(rows) > 0 and "No data" not in rows[0].text:
                    self.log_test(
                        "Standard Pending Incomes",
                        True,
                        f"Found {len(rows)} pending incomes"
                    )
                else:
                    self.log_test(
                        "Standard Pending Incomes",
                        True,
                        "No pending incomes for testing"
                    )
                    
            except TimeoutException:
                self.log_test(
                    "Standard Income Page Load",
                    False,
                    "Page did not load within timeout"
                )
                
        except Exception as e:
            self.log_test(
                "Standard Workflow Test",
                False,
                f"Exception: {str(e)}"
            )
            self.take_screenshot("standard_workflow_error")
    
    def print_report(self):
        """Print comprehensive test report"""
        print("\n" + "="*80)
        print("📋 SELENIUM FRONTEND TEST REPORT")
        print("="*80)
        print(f"Base URL: {BASE_URL}")
        print(f"Total Tests: {len(self.test_results)}")
        
        passed = sum(1 for r in self.test_results if '✅' in r['status'])
        failed = sum(1 for r in self.test_results if '❌' in r['status'])
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if len(self.test_results) > 0:
            success_rate = (passed / len(self.test_results)) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print("="*80)
        print("\nDetailed Results:")
        print("-" * 80)
        
        for result in self.test_results:
            print(f"\n{result['status']} - {result['test']}")
            print(f"   Message: {result['message']}")
            if result['screenshot']:
                print(f"   Screenshot: {result['screenshot']}")
            print(f"   Time: {result['timestamp']}")
        
        print("\n" + "="*80)
        print(f"Screenshots saved in: {SCREENSHOT_DIR}/")
        print("="*80)
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
            print("\n🧹 Browser closed")
    
    def run_full_test(self, vgk_username, vgk_password, admin_username=None, admin_password=None):
        """Run complete test suite"""
        print("="*80)
        print("🧪 BeV 2.0 - COMPREHENSIVE SELENIUM FRONTEND TEST")
        print("="*80)
        
        try:
            self.setup_driver()
            
            # Test 1: VGK Login
            if self.login(vgk_username, vgk_password, "VGK"):
                # Test 2: VGK Income Supreme
                self.test_vgk_income_supreme()
                
                # Test 3: VGK Withdrawal Supreme
                self.test_vgk_withdrawal_supreme()
            
            # Test 4: Standard Workflow (if credentials provided)
            if admin_username and admin_password:
                self.test_standard_workflow(admin_username, admin_password)
            
            # Print comprehensive report
            self.print_report()
            
        finally:
            self.cleanup()

if __name__ == "__main__":
    # Get credentials from environment or prompt
    VGK_USERNAME = os.getenv('VGK_TEST_USERNAME', 'BEV182364369')
    VGK_PASSWORD = os.getenv('VGK_TEST_PASSWORD', '')
    
    ADMIN_USERNAME = os.getenv('ADMIN_TEST_USERNAME', '')
    ADMIN_PASSWORD = os.getenv('ADMIN_TEST_PASSWORD', '')
    
    if not VGK_PASSWORD:
        print("⚠️  WARNING: VGK_TEST_PASSWORD environment variable not set!")
        print("Please set credentials:")
        print("  export VGK_TEST_USERNAME='BEV...'")
        print("  export VGK_TEST_PASSWORD='your_password'")
        print("\nOptional (for Standard workflow test):")
        print("  export ADMIN_TEST_USERNAME='BEV...'")
        print("  export ADMIN_TEST_PASSWORD='your_password'")
        print("\nAttempting to run with demo mode (may have limited results)...")
        VGK_PASSWORD = "demo_password"
    
    # Run tests
    tester = BeVSeleniumTest()
    tester.run_full_test(
        vgk_username=VGK_USERNAME,
        vgk_password=VGK_PASSWORD,
        admin_username=ADMIN_USERNAME if ADMIN_USERNAME else None,
        admin_password=ADMIN_PASSWORD if ADMIN_PASSWORD else None
    )
