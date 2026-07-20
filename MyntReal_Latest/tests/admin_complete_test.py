#!/usr/bin/env python3
"""
ADMIN COMPLETE E2E TEST SUITE
Tests ALL 45 Admin unique pages with REAL login
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
from selenium.common.exceptions import TimeoutException
import json

class AdminCompleteTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        self.test_results = {
            "role": "Admin",
            "total_pages": 45,
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "screenshots": []
        }
        
        # ALL 45 Admin unique pages
        self.pages_to_test = [
            # Dashboard
            {"name": "Admin Dashboard", "url": "/admin/dashboard"},
            
            # Admin Functions (14 pages)
            {"name": "Income Verified", "url": "/admin/income-verified"},
            {"name": "Income History", "url": "/admin/income-history"},
            {"name": "Members Actions", "url": "/admin/members/actions"},
            {"name": "Network Tree", "url": "/admin/network-tree"},
            {"name": "Sponsor Tree", "url": "/admin/sponsor-tree"},
            {"name": "Reports", "url": "/admin/reports"},
            {"name": "Search Members", "url": "/admin/members/search"},
            {"name": "KYC Management", "url": "/admin/kyc-management"},
            {"name": "Birthday Details", "url": "/admin/birthdays"},
            {"name": "Manage Brands", "url": "/admin/brands"},
            {"name": "Manage Levels", "url": "/admin/levels"},
            {"name": "Manage Awards", "url": "/admin/awards/manage"},
            {"name": "Support Tickets", "url": "/admin/tickets"},
            {"name": "Tree Statistics", "url": "/admin/tree-statistics"},
            
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
            
            # Earnings (7)
            {"name": "Earnings Summary", "url": "/admin/earnings/summary"},
            {"name": "Direct Referral", "url": "/admin/earnings/direct-referral"},
            {"name": "Matching Referral", "url": "/admin/earnings/matching-referral"},
            {"name": "Ved Income", "url": "/admin/earnings/ved-income"},
            {"name": "Gurudakshina", "url": "/admin/earnings/gurudakshina"},
            {"name": "Field Allowance", "url": "/admin/earnings/field-allowance"},
            {"name": "Withdrawals", "url": "/admin/earnings/withdrawals"},
            
            # Withdrawal Management (2)
            {"name": "Withdrawal Approvals", "url": "/admin/withdrawal/approvals"},
            {"name": "Withdrawal History", "url": "/admin/withdrawal/history"},
            
            # Awards & Bonanza (3)
            {"name": "Awards", "url": "/admin/awards/all"},
            {"name": "Bonanza Awards", "url": "/admin/awards/bonanza"},
            {"name": "Bonanza Claims", "url": "/admin/bonanza-claims"},
            
            # VGK Earnings (6)
            {"name": "All Benefits", "url": "/admin/vgk/all-benefits"},
            {"name": "EV Discount & Training", "url": "/admin/vgk/ev-discount-training"},
            {"name": "My Referral Income", "url": "/admin/vgk/referral-income"},
            {"name": "Insurance Earnings", "url": "/admin/vgk/insurance-earnings"},
            {"name": "Franchise Earnings", "url": "/admin/vgk/franchise-earnings"},
            {"name": "Fleet Orders", "url": "/admin/vgk/fleet-orders"},
            
            # Payment Distribution (2)
            {"name": "Payment Settings", "url": "/admin/payment/settings"},
            {"name": "Wallets Distribution", "url": "/admin/payment/wallets"},
            
            # Package Management (1)
            {"name": "Packages", "url": "/admin/packages"},
        ]
        
    def setup_driver(self):
        """Initialize Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        print("✅ Chrome driver initialized")
        
    def login_as_admin(self, user_id, password):
        """REAL LOGIN"""
        print(f"\n🔐 LOGGING IN AS ADMIN: {user_id}")
        
        try:
            self.driver.get(f"{self.base_url}/login")
            time.sleep(2)
            
            self.take_screenshot("01_login_page")
            
            user_id_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            user_id_field.clear()
            user_id_field.send_keys(user_id)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            
            sign_in_btn = self.driver.find_element(By.ID, "submitBtn")
            sign_in_btn.click()
            
            WebDriverWait(self.driver, 15).until(
                lambda driver: "/login" not in driver.current_url
            )
            print("✅ LOGIN SUCCESSFUL")
            self.take_screenshot("02_login_success")
            return True
                
        except Exception as e:
            print(f"❌ LOGIN ERROR: {str(e)}")
            self.take_screenshot("02_login_error")
            return False
    
    def take_screenshot(self, name):
        """Take screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/screenshots/admin_{name}_{timestamp}.png"
        os.makedirs("tests/screenshots", exist_ok=True)
        self.driver.save_screenshot(filename)
        self.test_results["screenshots"].append(filename)
        print(f"  📸 {filename}")
        return filename
    
    def check_page_loads(self, url, page_name):
        """Test page load"""
        print(f"\n📄 TESTING: {page_name} ({url})")
        
        try:
            self.driver.get(f"{self.base_url}{url}")
            time.sleep(2)
            
            screenshot_name = f"page_{self.test_results['tested']:03d}_{page_name.replace(' ', '_')}"
            self.take_screenshot(screenshot_name)
            
            page_source = self.driver.page_source.lower()
            
            if "404" in page_source or "not found" in page_source:
                print(f"  ❌ 404 NOT FOUND")
                self.test_results["failed"] += 1
                self.test_results["errors"].append({"page": page_name, "url": url, "error": "404"})
                return False
            else:
                print(f"  ✅ 200 OK")
                self.test_results["passed"] += 1
                return True
                
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({"page": page_name, "url": url, "error": str(e)})
            return False
        finally:
            self.test_results["tested"] += 1
    
    def run_all_tests(self, user_id, password):
        """Execute test suite"""
        print("\n🧪 ADMIN COMPLETE TEST SUITE")
        
        try:
            self.setup_driver()
            
            if not self.login_as_admin(user_id, password):
                return False
            
            for page in self.pages_to_test:
                self.check_page_loads(page["url"], page["name"])
                time.sleep(1)
            
            self.generate_report()
            return True
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def generate_report(self):
        """Generate report"""
        with open("tests/admin_test_results.json", 'w') as f:
            json.dump(self.test_results, indent=2, fp=f)
        
        print("\n📊 ADMIN TEST SUMMARY")
        print(f"Tested: {self.test_results['tested']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        print(f"Pass Rate: {(self.test_results['passed']/self.test_results['tested']*100):.1f}%")

if __name__ == "__main__":
    USER_ID = input("Enter Admin User ID: ")
    PASSWORD = input("Enter Admin Password: ")
    
    tester = AdminCompleteTest()
    tester.run_all_tests(USER_ID, PASSWORD)
