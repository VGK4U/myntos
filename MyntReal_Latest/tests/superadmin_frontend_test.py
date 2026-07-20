#!/usr/bin/env python3
"""
Super Admin Frontend Routes Test
Tests all Super Admin menu items with real authentication
User: BEV182371007
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# Test Configuration
SUPER_ADMIN_USER = "BEV182371007"
SUPER_ADMIN_PASS = "TestPass123!"
BASE_URL = "http://localhost:5000"

# Super Admin Routes to Test
ROUTES_TO_TEST = {
    "Dashboard": "/superadmin/dashboard",
    "Withdrawal Approvals": "/superadmin/withdrawal/approvals",
    "Withdrawal History": "/superadmin/withdrawal/history",
    "Awards Approval Queue": "/superadmin/awards/approval-queue",
    "Global Config": "/superadmin/global-config",
    "System Health": "/superadmin/system-health",
    "Red ID Oversight": "/superadmin/red-id-oversight",
    "Placement Approvals": "/superadmin/placement-approvals",
    "Log Reports": "/superadmin/log-reports",
}

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=chrome_options)

def login(driver):
    """Login with Super Admin credentials"""
    print(f"\n🔐 Logging in as {SUPER_ADMIN_USER}...")
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    
    try:
        # Find and fill login form
        user_id_field = driver.find_element(By.NAME, "user_id")
        password_field = driver.find_element(By.NAME, "password")
        
        user_id_field.clear()
        user_id_field.send_keys(SUPER_ADMIN_USER)
        
        password_field.clear()
        password_field.send_keys(SUPER_ADMIN_PASS)
        
        # Click sign in button
        sign_in_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        sign_in_btn.click()
        
        time.sleep(3)
        
        current_url = driver.current_url
        if "login" not in current_url:
            print(f"   ✅ Login successful - redirected to {current_url}")
            return True
        else:
            print(f"   ❌ Login failed - still on login page")
            return False
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False

def test_route(driver, name, path):
    """Test a single route"""
    try:
        full_url = f"{BASE_URL}{path}"
        driver.get(full_url)
        time.sleep(2)
        
        current_url = driver.current_url
        page_source = driver.page_source
        
        # Check if redirected to login
        if "login" in current_url.lower():
            return {"status": "REDIRECT", "message": "Redirected to login (no access)"}
        
        # Check if page loaded successfully
        if "404" in page_source or "Page not found" in page_source:
            return {"status": "404", "message": "Page not found (route missing)"}
        
        # Check for Super Admin indicators
        if "Super Admin" in page_source or "superadmin" in page_source.lower():
            return {"status": "SUCCESS", "message": "Page loaded successfully"}
        
        # Page loaded but unclear
        return {"status": "UNKNOWN", "message": f"Page loaded but unclear: {current_url[:50]}"}
        
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:100]}

def main():
    print("=" * 70)
    print("SUPER ADMIN FRONTEND ROUTES TEST")
    print("=" * 70)
    print(f"User: {SUPER_ADMIN_USER}")
    print(f"Routes to test: {len(ROUTES_TO_TEST)}")
    print("=" * 70)
    
    driver = setup_driver()
    results = {}
    
    try:
        # Login first
        if not login(driver):
            print("\n❌ Login failed - cannot proceed with tests")
            return
        
        # Test each route
        print(f"\n📋 Testing {len(ROUTES_TO_TEST)} Super Admin routes...")
        print("-" * 70)
        
        for name, path in ROUTES_TO_TEST.items():
            print(f"\nTesting: {name}")
            print(f"  Path: {path}")
            
            result = test_route(driver, name, path)
            results[name] = result
            
            status_emoji = {
                "SUCCESS": "✅",
                "404": "❌",
                "REDIRECT": "🔒",
                "UNKNOWN": "⚠️",
                "ERROR": "💥"
            }.get(result["status"], "❓")
            
            print(f"  {status_emoji} {result['status']}: {result['message']}")
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        success_count = sum(1 for r in results.values() if r["status"] == "SUCCESS")
        redirect_count = sum(1 for r in results.values() if r["status"] == "REDIRECT")
        error_count = sum(1 for r in results.values() if r["status"] in ["404", "ERROR"])
        
        print(f"✅ Successful: {success_count}/{len(ROUTES_TO_TEST)}")
        print(f"🔒 Redirected: {redirect_count}/{len(ROUTES_TO_TEST)}")
        print(f"❌ Errors/404: {error_count}/{len(ROUTES_TO_TEST)}")
        
        print("\n" + "=" * 70)
        
        if success_count == len(ROUTES_TO_TEST):
            print("🎉 ALL TESTS PASSED - All routes working!")
        elif redirect_count == len(ROUTES_TO_TEST):
            print("🔒 ALL REDIRECTED - User may not have Super Admin role")
        else:
            print("⚠️  MIXED RESULTS - Some routes need attention")
        
        print("=" * 70)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
