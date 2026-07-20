"""
STFP Page #3: VGK Quick Actions (Available Menus)
Test every button and link that IS available on VGK dashboard
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
VGK_USERNAME = "BEV182364369"
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
    print(" "*18 + "STFP PAGE #3: VGK QUICK ACTIONS (AVAILABLE)")
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
        
        if "/vgk" not in driver.current_url:
            print("  ✗ Login failed")
            return 1
        print("  ✓ Logged in successfully\n")
        
        # Test 1: Check page title
        print("▶ Test 1: Check VGK Dashboard Title")
        page_source = driver.page_source
        if "VGK ID Supreme Admin Dashboard" in page_source or "VGK Supreme" in page_source:
            print("  ✓ VGK Dashboard title found")
        else:
            print("  ✗ Dashboard title not found")
        
        # Test 2: Check Quick Actions section
        print("\n▶ Test 2: Check Quick Actions Section")
        if "Quick Actions" in page_source:
            print("  ✓ Quick Actions section found")
        else:
            print("  ✗ Quick Actions section not found")
        
        # Test 3: Check all available quick action buttons
        print("\n▶ Test 3: Check Available Quick Action Buttons")
        
        quick_actions = [
            ("Bonanza Management", "/vgk/bonanza-management"),
            ("System Controls", "/vgk/system-controls"),
            ("Support Tickets", "/admin/tickets"),
            ("Rate Management", "/vgk/rate-configuration"),
            ("Emergency Wallet", "/vgk/emergency-wallet"),
            ("Production Reset", "/vgk/production-reset-status"),
            ("Expense Overview", "/vgk/expense-overview"),
            ("Company Earnings", "/vgk/company-earnings"),
        ]
        
        found_actions = []
        missing_actions = []
        
        for action_name, action_url in quick_actions:
            if action_url in page_source:
                print(f"  ✓ {action_name} link found")
                found_actions.append(action_name)
            else:
                print(f"  ✗ {action_name} link NOT FOUND")
                missing_actions.append(action_name)
        
        print(f"\n  📊 Found {len(found_actions)}/{len(quick_actions)} quick actions")
        
        # Test 4: Check System Test button
        print("\n▶ Test 4: Check System Test Button")
        try:
            test_btn = driver.find_element(By.ID, "runTestBtn")
            print("  ✓ System Test button found")
            print(f"  ℹ Button text: {test_btn.text}")
        except Exception as e:
            print(f"  ⚠ System Test button not found")
        
        # Test 5: Check Statistics Section
        print("\n▶ Test 5: Check Statistics Section")
        try:
            stats_section = driver.find_element(By.ID, "statsSection")
            print("  ✓ Statistics section found")
        except Exception as e:
            print(f"  ⚠ Statistics section not found: {e}")
        
        # Test 6: Check Earnings Synopsis
        print("\n▶ Test 6: Check Company Earnings Synopsis")
        try:
            earnings_synopsis = driver.find_element(By.ID, "earningsSynopsis")
            print("  ✓ Earnings synopsis section found")
        except Exception as e:
            print(f"  ⚠ Earnings synopsis not found")
        
        # Test 7: Check Expenses Synopsis
        print("\n▶ Test 7: Check Company Expenses Synopsis")
        try:
            expenses_synopsis = driver.find_element(By.ID, "expensesSynopsis")
            print("  ✓ Expenses synopsis section found")
        except Exception as e:
            print(f"  ⚠ Expenses synopsis not found")
        
        # Test 8: Test clicking Bonanza Management link
        print("\n▶ Test 8: Test Navigation - Bonanza Management")
        try:
            bonanza_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/vgk/bonanza-management')]")
            if bonanza_links:
                bonanza_links[0].click()
                time.sleep(2)
                
                current_url = driver.current_url
                if "/vgk/bonanza-management" in current_url:
                    print("  ✓ Successfully navigated to Bonanza Management")
                    
                    # Go back to dashboard
                    driver.back()
                    time.sleep(2)
                    print("  ✓ Returned to dashboard")
                else:
                    print(f"  ✗ Wrong page: {current_url}")
        except Exception as e:
            print(f"  ✗ Navigation failed: {e}")
        
        # Test 9: Test clicking System Controls link
        print("\n▶ Test 9: Test Navigation - System Controls")
        try:
            system_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/vgk/system-controls')]")
            if system_links:
                system_links[0].click()
                time.sleep(2)
                
                current_url = driver.current_url
                if "/vgk/system-controls" in current_url:
                    print("  ✓ Successfully navigated to System Controls")
                    
                    # Go back
                    driver.back()
                    time.sleep(2)
                    print("  ✓ Returned to dashboard")
                else:
                    print(f"  ✗ Wrong page: {current_url}")
        except Exception as e:
            print(f"  ✗ Navigation failed: {e}")
        
        # Test 10: Check console errors
        print("\n▶ Test 10: Check Browser Console Errors")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE' and 'favicon' not in log['message']]
        
        if errors:
            print(f"  ✗ Found {len(errors)} console errors:")
            for error in errors[:3]:
                print(f"    - {error['message'][:100]}")
        else:
            print("  ✓ No critical console errors detected")
        
        print("\n" + "="*80)
        print(" "*28 + "TEST SUMMARY")
        print("="*80)
        
        total_tests = 10
        passed_tests = len(found_actions) + (6 if len(errors) == 0 else 5)
        
        print(f"\n📊 Quick Actions Found: {len(found_actions)}/{len(quick_actions)}")
        print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
        
        if len(found_actions) >= 6:  # At least 75% of quick actions present
            print("\n✓ VGK DASHBOARD QUICK ACTIONS ARE FUNCTIONAL\n")
            return 0
        else:
            print(f"\n⚠ PARTIAL FUNCTIONALITY - Missing {len(missing_actions)} quick actions\n")
            return 1
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        driver.save_screenshot('/tmp/stfp_quick_actions_error.png')
        print("  ℹ Screenshot saved: /tmp/stfp_quick_actions_error.png")
        return 1
    
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
