#!/usr/bin/env python3
"""
Admin Frontend Testing Script
Tests all Admin role pages systematically with real login
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os

# Admin credentials
ADMIN_USER = "BEV182322707"
ADMIN_PASSWORD = "TestPass123!"
BASE_URL = "http://localhost:5000"

# All Admin pages to test (from admin.html template)
ADMIN_PAGES = [
    # Dashboard
    "/admin/dashboard",
    
    # Member Management
    "/admin/members/all",
    "/admin/members/search",
    "/admin/members/tree-view",
    "/admin/members/activation-report",
    
    # Income Management
    "/admin/income/history",
    "/admin/income/analytics",
    "/admin/income/user-summary",
    
    # Withdrawal Management
    "/admin/withdrawals/pending",
    "/admin/withdrawals/approved",
    "/admin/withdrawals/rejected",
    "/admin/withdrawals/report",
    
    # KYC Management
    "/admin/kyc/pending",
    "/admin/kyc/approved",
    "/admin/kyc/rejected",
    "/admin/kyc/all-users",
    
    # Bank Details
    "/admin/bank/pending",
    "/admin/bank/approved",
    "/admin/bank/all",
    
    # Awards & Bonanza
    "/admin/awards/active",
    "/admin/awards/history",
    "/admin/bonanza/active",
    "/admin/bonanza/claims",
    "/admin/bonanza/history",
    
    # Reports
    "/admin/reports/daily",
    "/admin/reports/monthly",
    "/admin/reports/custom",
    
    # Birthday Management
    "/admin/birthdays/today",
    "/admin/birthdays/tomorrow",
    "/admin/birthdays/week",
    
    # Settings
    "/admin/settings/profile",
    "/admin/settings/notifications",
]

def setup_driver():
    """Setup Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    return webdriver.Chrome(options=options)

def login(driver):
    """Login with Admin credentials"""
    print(f"\n{'='*60}")
    print("LOGGING IN AS ADMIN")
    print(f"{'='*60}")
    
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    
    # Fill login form
    user_input = driver.find_element(By.ID, "username")
    pass_input = driver.find_element(By.ID, "password")
    
    user_input.send_keys(ADMIN_USER)
    pass_input.send_keys(ADMIN_PASSWORD)
    
    # Submit
    login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_btn.click()
    
    time.sleep(3)
    
    # Check if logged in
    current_url = driver.current_url
    print(f"✅ Login submitted, current URL: {current_url}")
    
    if "/login" in current_url:
        print("❌ Login failed - still on login page")
        return False
    
    print("✅ Login successful")
    return True

def test_page(driver, page_path):
    """Test a single page"""
    full_url = f"{BASE_URL}{page_path}"
    
    try:
        driver.get(full_url)
        time.sleep(1.5)
        
        current_url = driver.current_url
        page_source = driver.page_source
        
        # Check for redirect to login (means route doesn't exist or auth failed)
        if "/login" in current_url:
            print(f"❌ REDIRECTED TO LOGIN: {page_path}")
            return "REDIRECT_LOGIN"
        
        # Check for 404 in page source
        if "404" in page_source or "Not Found" in page_source:
            print(f"❌ 404 NOT FOUND: {page_path}")
            return "404"
        
        # Check if page loaded (has some content)
        if len(page_source) < 500:
            print(f"⚠️  MINIMAL CONTENT: {page_path} ({len(page_source)} bytes)")
            return "MINIMAL"
        
        print(f"✅ LOADED: {page_path}")
        return "SUCCESS"
        
    except TimeoutException:
        print(f"⏱️  TIMEOUT: {page_path}")
        return "TIMEOUT"
    except Exception as e:
        print(f"❌ ERROR: {page_path} - {str(e)[:50]}")
        return "ERROR"

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("ADMIN FRONTEND TESTING - SYSTEMATIC PAGE TEST")
    print("="*60)
    print(f"Total pages to test: {len(ADMIN_PAGES)}")
    
    driver = setup_driver()
    
    try:
        # Login first
        if not login(driver):
            print("\n❌ Login failed - cannot proceed with testing")
            return
        
        # Test all pages
        results = {
            "SUCCESS": [],
            "404": [],
            "REDIRECT_LOGIN": [],
            "MINIMAL": [],
            "TIMEOUT": [],
            "ERROR": []
        }
        
        print(f"\n{'='*60}")
        print("TESTING ALL ADMIN PAGES")
        print(f"{'='*60}\n")
        
        for idx, page in enumerate(ADMIN_PAGES, 1):
            print(f"[{idx}/{len(ADMIN_PAGES)}] ", end="")
            result = test_page(driver, page)
            results[result].append(page)
            time.sleep(0.5)  # Small delay between requests
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST RESULTS SUMMARY")
        print(f"{'='*60}\n")
        
        print(f"✅ WORKING PAGES: {len(results['SUCCESS'])}")
        for page in results['SUCCESS']:
            print(f"   {page}")
        
        print(f"\n❌ 404 NOT FOUND: {len(results['404'])}")
        for page in results['404']:
            print(f"   {page}")
        
        print(f"\n🔒 REDIRECT TO LOGIN: {len(results['REDIRECT_LOGIN'])}")
        for page in results['REDIRECT_LOGIN']:
            print(f"   {page}")
        
        print(f"\n⚠️  MINIMAL CONTENT: {len(results['MINIMAL'])}")
        for page in results['MINIMAL']:
            print(f"   {page}")
        
        print(f"\n⏱️  TIMEOUT: {len(results['TIMEOUT'])}")
        for page in results['TIMEOUT']:
            print(f"   {page}")
        
        print(f"\n❌ ERROR: {len(results['ERROR'])}")
        for page in results['ERROR']:
            print(f"   {page}")
        
        # Final stats
        total_tested = len(ADMIN_PAGES)
        working = len(results['SUCCESS'])
        broken = len(results['404']) + len(results['REDIRECT_LOGIN']) + len(results['ERROR'])
        
        print(f"\n{'='*60}")
        print(f"FINAL STATS: {working}/{total_tested} working ({working*100//total_tested}%)")
        print(f"BROKEN PAGES: {broken}")
        print(f"{'='*60}\n")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
