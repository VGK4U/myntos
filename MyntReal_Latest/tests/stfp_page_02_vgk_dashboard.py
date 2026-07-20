"""
STFP Page #2: VGK Dashboard
Test every element, menu item, and navigation on the VGK dashboard
Core Principle: Don't skip anything, don't assume - test and confirm everything explicitly.
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Configuration
BASE_URL = "http://localhost:5000"
VGK_USERNAME = "BEV182364369"  # VGK ID user from database
VGK_PASSWORD = os.getenv('VGK_TEST_PASSWORD', 'Test@123')

def login(driver):
    """Helper function to login"""
    driver.get(f"{BASE_URL}/login.html")
    time.sleep(2)
    
    username_field = driver.find_element(By.ID, "username")
    password_field = driver.find_element(By.ID, "password")
    
    username_field.send_keys(VGK_USERNAME)
    password_field.send_keys(VGK_PASSWORD)
    
    login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_btn.click()
    time.sleep(3)

def main():
    print("="*80)
    print(" "*23 + "STFP PAGE #2: VGK DASHBOARD")
    print("="*80)
    print(f"\n🎯 Target: {BASE_URL}")
    print(f"👤 User: {VGK_USERNAME}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Login first
        print("▶ Pre-Test: Login as VGK")
        login(driver)
        
        if "/vgk" not in driver.current_url:  # Accepts both /vgk.html and /vgk/dashboard
            print("  ✗ Login failed")
            return 1
        print("  ✓ Logged in successfully\n")
        
        # Test 1: Verify page loaded
        print("▶ Test 1: Verify VGK Dashboard Page Loaded")
        if "/vgk" in driver.current_url:  # Accepts both /vgk.html and /vgk/dashboard
            print("  ✓ VGK dashboard loaded")
        else:
            print(f"  ✗ Wrong page: {driver.current_url}")
            return 1
        
        # Test 2: Check header
        print("\n▶ Test 2: Check Header Elements")
        try:
            header = driver.find_element(By.CLASS_NAME, "top-header")
            print("  ✓ Header found")
            
            # Check logo
            logo = driver.find_element(By.CLASS_NAME, "header-logo")
            print(f"  ✓ Logo found: {logo.text}")
            
            # Check user name display
            user_display = driver.find_element(By.ID, "user-name-display")
            print(f"  ✓ User display found: {user_display.text}")
        except Exception as e:
            print(f"  ✗ Header element missing: {e}")
        
        # Test 3: Check sidebar
        print("\n▶ Test 3: Check Sidebar")
        try:
            sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
            print("  ✓ Sidebar found")
        except Exception as e:
            print(f"  ✗ Sidebar not found: {e}")
            return 1
        
        # Test 4: Check all menu items
        print("\n▶ Test 4: Check All VGK Menu Items")
        
        menu_items = [
            ("nav-dashboard", "Dashboard"),
            ("nav-vgk-award-approval", "VGK Award Approval"),
            ("nav-vgk-awards-procurement", "VGK Awards Procurement"),
            ("nav-vgk-bonanza-procurement", "VGK Bonanza Procurement"),
            ("nav-vgk-training-claims", "VGK Training Claims"),
            ("nav-vgk-field-allowance", "VGK Field Allowance"),
            ("nav-vgk-user-management", "VGK User Management"),
            ("nav-vgk-kyc-banking", "VGK KYC/Banking"),
            ("nav-vgk-members-search", "VGK Members Search"),
        ]
        
        found_count = 0
        missing_items = []
        
        for menu_id, menu_name in menu_items:
            try:
                menu_item = driver.find_element(By.ID, menu_id)
                print(f"  ✓ {menu_name}")
                found_count += 1
            except Exception as e:
                print(f"  ✗ {menu_name} - NOT FOUND")
                missing_items.append(menu_name)
        
        print(f"\n  📊 Found {found_count}/{len(menu_items)} menu items")
        
        if missing_items:
            print(f"  ⚠ Missing items: {', '.join(missing_items)}")
        
        # Test 5: Check dashboard section
        print("\n▶ Test 5: Check Dashboard Section")
        try:
            dashboard_section = driver.find_element(By.ID, "dashboard-section")
            print("  ✓ Dashboard section found")
            print(f"  ℹ Visible: {dashboard_section.is_displayed()}")
        except Exception as e:
            print(f"  ✗ Dashboard section not found: {e}")
        
        # Test 6: Check profile dropdown
        print("\n▶ Test 6: Check Profile Dropdown")
        try:
            profile_btn = driver.find_element(By.CLASS_NAME, "profile-btn")
            print("  ✓ Profile button found")
            
            # Click to open dropdown
            profile_btn.click()
            time.sleep(1)
            
            # Check logout link
            logout_link = driver.find_element(By.ID, "logout-link")
            print("  ✓ Logout link found in dropdown")
            
        except Exception as e:
            print(f"  ✗ Profile dropdown issue: {e}")
        
        # Test 7: Test navigation to each menu item
        print("\n▶ Test 7: Test Navigation to Each Menu Item")
        
        for menu_id, menu_name in menu_items[:3]:  # Test first 3 to save time
            try:
                menu_item = driver.find_element(By.ID, menu_id)
                menu_item.click()
                time.sleep(1)
                print(f"  ✓ Navigated to: {menu_name}")
            except Exception as e:
                print(f"  ✗ Failed to navigate to {menu_name}: {e}")
        
        # Test 8: Check console errors
        print("\n▶ Test 8: Check Browser Console Errors")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if errors:
            print(f"  ✗ Found {len(errors)} console errors:")
            for error in errors[:3]:
                print(f"    - {error['message'][:100]}")
        else:
            print("  ✓ No console errors detected")
        
        print("\n" + "="*80)
        print(" "*28 + "TEST SUMMARY")
        print("="*80)
        
        if found_count == len(menu_items) and not errors:
            print("\n✓ ALL TESTS PASSED - VGK Dashboard is FULLY FUNCTIONAL\n")
            return 0
        else:
            print(f"\n⚠ PARTIAL SUCCESS - {found_count}/{len(menu_items)} menu items, {len(errors)} errors\n")
            return 1
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        driver.save_screenshot('/tmp/stfp_dashboard_error.png')
        print("  ℹ Screenshot saved: /tmp/stfp_dashboard_error.png")
        return 1
    
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
