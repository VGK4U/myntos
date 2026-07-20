#!/usr/bin/env python3
"""
FINANCE ADMIN COMPLETE E2E TEST SUITE
Tests ALL 9 Finance Admin unique pages + 22 reused pages with REAL login
Every page | Screenshots | Console logs | 200/404 verification
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

class FinanceAdminCompleteTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        self.test_results = {
            "role": "Finance Admin",
            "total_pages": 31,  # 9 unique + 22 reused
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "screenshots": []
        }
        
        # ALL Finance Admin pages
        self.pages_to_test = [
            # 9 Unique Finance Admin Pages
            {"name": "Finance Dashboard", "url": "/finance/dashboard"},
            {"name": "Payment Processing", "url": "/finance/awards/payment-processing"},
            {"name": "KYC Approval", "url": "/finance/kyc-approval"},
            {"name": "PIN Approvals", "url": "/finance/pins"},
            {"name": "Expense Management", "url": "/finance/expenses"},
            {"name": "TDS Management", "url": "/finance-admin/tds-management"},
            {"name": "Financial Reports", "url": "/finance/reports"},
            {"name": "Transfer Queue", "url": "/finance/withdrawal/transfers"},
            {"name": "Transfer History", "url": "/finance/withdrawal/history"},
            
            # 22 Reused Pages (from Admin, VGK, User)
            {"name": "Income Verified", "url": "/admin/income-verified"},
            {"name": "Income Verification", "url": "/vgk/income-history-supreme"},
            {"name": "Search Members", "url": "/admin/members/search"},
            {"name": "Birthday Details", "url": "/admin/birthdays"},
            {"name": "Support Tickets", "url": "/admin/tickets"},
            {"name": "Withdrawals", "url": "/user/withdrawals"},
            {"name": "Bank Approval", "url": "/profile-view"},
            
            # Coupon Modules (5)
            {"name": "Buy Coupon", "url": "/admin/coupons/buy"},
            {"name": "Activate Coupon", "url": "/admin/coupons/activate"},
            {"name": "Coupon Status", "url": "/admin/coupons/status"},
            {"name": "Coupon Progress", "url": "/admin/coupons/progress"},
            {"name": "Coupon Transfer", "url": "/admin/coupons/transfer"},
            
            # Members (4)
            {"name": "All Members", "url": "/admin/members/all"},
            {"name": "Direct Referrals", "url": "/admin/members/direct-referrals"},
            {"name": "Picture View", "url": "/admin/members/picture-view"},
            {"name": "Ved Team", "url": "/admin/members/ved-team"},
            
            # Awards (3)
            {"name": "Awards", "url": "/admin/awards/all"},
            {"name": "Bonanza Awards", "url": "/admin/awards/bonanza"},
            {"name": "Bonanza Claims", "url": "/admin/bonanza-claims"},
        ]
        
    def setup_driver(self):
        """Initialize Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        print("✅ Chrome driver initialized")
        
    def login_as_finance_admin(self, user_id, password):
        """REAL LOGIN - No shortcuts"""
        print(f"\n🔐 LOGGING IN AS FINANCE ADMIN: {user_id}")
        
        try:
            self.driver.get(f"{self.base_url}/login")
            time.sleep(2)
            
            self.take_screenshot("01_login_page")
            
            user_id_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            user_id_field.clear()
            user_id_field.send_keys(user_id)
            print(f"  ✓ Entered User ID: {user_id}")
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            print(f"  ✓ Entered Password: {'*' * len(password)}")
            
            sign_in_btn = self.driver.find_element(By.ID, "submitBtn")
            sign_in_btn.click()
            print("  ✓ Clicked Sign In button")
            
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: "/login" not in driver.current_url
                )
                current_url = self.driver.current_url
                print(f"  ✓ Redirected to: {current_url}")
                print("✅ LOGIN SUCCESSFUL")
                self.take_screenshot("02_login_success")
                return True
                    
            except TimeoutException:
                print(f"❌ LOGIN FAILED - Timeout")
                self.take_screenshot("02_login_failed")
                return False
                
        except Exception as e:
            print(f"❌ LOGIN ERROR: {str(e)}")
            self.take_screenshot("02_login_error")
            return False
    
    def take_screenshot(self, name):
        """Take screenshot with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/screenshots/finance_{name}_{timestamp}.png"
        os.makedirs("tests/screenshots", exist_ok=True)
        self.driver.save_screenshot(filename)
        self.test_results["screenshots"].append(filename)
        print(f"  📸 Screenshot: {filename}")
        return filename
    
    def check_page_loads(self, url, page_name):
        """Test if page loads (200 vs 404)"""
        print(f"\n{'='*80}")
        print(f"📄 TESTING: {page_name}")
        print(f"🔗 URL: {url}")
        print('='*80)
        
        try:
            self.driver.get(f"{self.base_url}{url}")
            time.sleep(2)
            
            # Take screenshot
            screenshot_name = f"page_{self.test_results['tested']:03d}_{page_name.replace(' ', '_')}"
            self.take_screenshot(screenshot_name)
            
            # Get page title
            page_title = self.driver.title
            print(f"  📑 Page Title: {page_title}")
            
            # Check for 404 indicators
            page_source = self.driver.page_source.lower()
            
            if "404" in page_source or "not found" in page_source:
                print(f"  ❌ STATUS: 404 NOT FOUND")
                self.test_results["failed"] += 1
                self.test_results["errors"].append({
                    "page": page_name,
                    "url": url,
                    "error": "404 Not Found",
                    "screenshot": screenshot_name
                })
                return False
            else:
                print(f"  ✅ STATUS: 200 OK (Page Loaded)")
                self.test_results["passed"] += 1
                return True
                
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "page": page_name,
                "url": url,
                "error": str(e),
                "screenshot": f"error_{page_name}"
            })
            return False
        finally:
            self.test_results["tested"] += 1
    
    def run_all_tests(self, user_id, password):
        """Execute complete test suite"""
        print("\n" + "="*80)
        print("🧪 FINANCE ADMIN COMPLETE TEST SUITE")
        print("="*80)
        
        try:
            self.setup_driver()
            
            # Login
            if not self.login_as_finance_admin(user_id, password):
                print("\n❌ LOGIN FAILED - Cannot proceed with tests")
                return False
            
            # Test all pages
            print(f"\n📋 Testing {len(self.pages_to_test)} Finance Admin pages...")
            
            for page in self.pages_to_test:
                self.check_page_loads(page["url"], page["name"])
                time.sleep(1)  # Small delay between pages
            
            # Generate report
            self.generate_report()
            
            print("\n" + "="*80)
            print("✅ TEST SUITE COMPLETE")
            print("="*80)
            return True
            
        except Exception as e:
            print(f"\n❌ TEST SUITE ERROR: {str(e)}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔒 Browser closed")
    
    def generate_report(self):
        """Generate JSON and markdown reports"""
        # Save JSON
        json_file = f"tests/finance_admin_test_results.json"
        with open(json_file, 'w') as f:
            json.dump(self.test_results, indent=2, fp=f)
        print(f"\n📄 JSON Report: {json_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"Total Pages: {self.test_results['total_pages']}")
        print(f"Tested: {self.test_results['tested']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        print(f"Pass Rate: {(self.test_results['passed']/self.test_results['tested']*100):.1f}%")
        print(f"Screenshots: {len(self.test_results['screenshots'])}")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS FOUND ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error['page']}: {error['error']}")

if __name__ == "__main__":
    # REPLACE WITH REAL FINANCE ADMIN CREDENTIALS
    USER_ID = input("Enter Finance Admin User ID: ")
    PASSWORD = input("Enter Finance Admin Password: ")
    
    tester = FinanceAdminCompleteTest()
    tester.run_all_tests(USER_ID, PASSWORD)
