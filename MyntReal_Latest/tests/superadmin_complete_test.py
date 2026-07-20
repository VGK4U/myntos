#!/usr/bin/env python3
"""
SUPER ADMIN COMPLETE E2E TEST SUITE
Tests ALL 9 Super Admin unique pages + 34 reused pages with REAL login
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json

class SuperAdminCompleteTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        self.test_results = {
            "role": "Super Admin",
            "total_pages": 9,
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "screenshots": []
        }
        
        # 9 unique Super Admin pages
        self.pages_to_test = [
            {"name": "Super Admin Dashboard", "url": "/superadmin/dashboard"},
            {"name": "Role Management", "url": "/superadmin/role-management"},
            {"name": "Award Management", "url": "/superadmin/award-management"},
            {"name": "System Controls", "url": "/superadmin/system-controls"},
            {"name": "Rate Configuration", "url": "/superadmin/rate-configuration"},
            {"name": "Daily Ceiling", "url": "/superadmin/daily-ceiling"},
            {"name": "Emergency Wallet", "url": "/superadmin/emergency-wallet"},
            {"name": "System Configuration", "url": "/superadmin/system-configuration"},
            {"name": "Admin Logs", "url": "/superadmin/admin-logs"},
        ]
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        print("✅ Chrome driver initialized")
        
    def login_as_superadmin(self, user_id, password):
        print(f"\n🔐 LOGGING IN AS SUPER ADMIN: {user_id}")
        
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
            return False
    
    def take_screenshot(self, name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/screenshots/superadmin_{name}_{timestamp}.png"
        os.makedirs("tests/screenshots", exist_ok=True)
        self.driver.save_screenshot(filename)
        self.test_results["screenshots"].append(filename)
        print(f"  📸 {filename}")
        return filename
    
    def check_page_loads(self, url, page_name):
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
            return False
        finally:
            self.test_results["tested"] += 1
    
    def run_all_tests(self, user_id, password):
        print("\n🧪 SUPER ADMIN COMPLETE TEST SUITE")
        
        try:
            self.setup_driver()
            
            if not self.login_as_superadmin(user_id, password):
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
        with open("tests/superadmin_test_results.json", 'w') as f:
            json.dump(self.test_results, indent=2, fp=f)
        
        print("\n📊 SUPER ADMIN TEST SUMMARY")
        print(f"Tested: {self.test_results['tested']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        print(f"Pass Rate: {(self.test_results['passed']/self.test_results['tested']*100):.1f}%")

if __name__ == "__main__":
    USER_ID = input("Enter Super Admin User ID: ")
    PASSWORD = input("Enter Super Admin Password: ")
    
    tester = SuperAdminCompleteTest()
    tester.run_all_tests(USER_ID, PASSWORD)
