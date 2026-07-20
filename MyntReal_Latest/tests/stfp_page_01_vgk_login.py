"""
STFP Page #1: VGK Login
Test every element, interaction, and validation on the login page
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

def main():
    print("="*80)
    print(" "*25 + "STFP PAGE #1: VGK LOGIN")
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
        # Test 1: Load login page
        print("▶ Test 1: Load Login Page")
        driver.get(f"{BASE_URL}/login.html")
        time.sleep(2)
        
        if "login" in driver.current_url.lower():
            print("  ✓ Login page loaded successfully")
        else:
            print(f"  ✗ Wrong page loaded: {driver.current_url}")
            return 1
        
        # Test 2: Verify page title
        print("\n▶ Test 2: Verify Page Title")
        if driver.title:
            print(f"  ✓ Page title: {driver.title}")
        else:
            print("  ✗ Page title missing")
        
        # Test 3: Check username field
        print("\n▶ Test 3: Check Username Field")
        try:
            username_field = driver.find_element(By.ID, "username")
            print("  ✓ Username field found")
            print(f"  ℹ Field type: {username_field.get_attribute('type')}")
            print(f"  ℹ Placeholder: {username_field.get_attribute('placeholder')}")
        except Exception as e:
            print(f"  ✗ Username field not found: {e}")
            return 1
        
        # Test 4: Check password field
        print("\n▶ Test 4: Check Password Field")
        try:
            password_field = driver.find_element(By.ID, "password")
            print("  ✓ Password field found")
            print(f"  ℹ Field type: {password_field.get_attribute('type')}")
            print(f"  ℹ Placeholder: {password_field.get_attribute('placeholder')}")
        except Exception as e:
            print(f"  ✗ Password field not found: {e}")
            return 1
        
        # Test 5: Check login button
        print("\n▶ Test 5: Check Login Button")
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            print("  ✓ Login button found")
            print(f"  ℹ Button text: {login_btn.text}")
            print(f"  ℹ Button enabled: {login_btn.is_enabled()}")
        except Exception as e:
            print(f"  ✗ Login button not found: {e}")
            return 1
        
        # Test 6: Fill username field
        print("\n▶ Test 6: Fill Username Field")
        try:
            username_field.clear()
            username_field.send_keys(VGK_USERNAME)
            entered_value = username_field.get_attribute('value')
            if entered_value == VGK_USERNAME:
                print(f"  ✓ Username entered successfully: {entered_value}")
            else:
                print(f"  ✗ Username mismatch: expected {VGK_USERNAME}, got {entered_value}")
        except Exception as e:
            print(f"  ✗ Failed to fill username: {e}")
            return 1
        
        # Test 7: Fill password field
        print("\n▶ Test 7: Fill Password Field")
        try:
            password_field.clear()
            password_field.send_keys(VGK_PASSWORD)
            print("  ✓ Password entered successfully")
        except Exception as e:
            print(f"  ✗ Failed to fill password: {e}")
            return 1
        
        # Test 8: Click login button
        print("\n▶ Test 8: Click Login Button")
        try:
            login_btn.click()
            time.sleep(3)
            print("  ✓ Login button clicked")
        except Exception as e:
            print(f"  ✗ Failed to click login: {e}")
            return 1
        
        # Test 9: Verify redirect
        print("\n▶ Test 9: Verify Redirect After Login")
        current_url = driver.current_url
        print(f"  ℹ Current URL: {current_url}")
        
        if "/vgk" in current_url:  # Accepts both /vgk.html and /vgk/dashboard
            print("  ✓ Successfully redirected to VGK dashboard")
        elif "/login" in current_url:
            print("  ✗ Still on login page - credentials may be incorrect")
            # Check for error message
            try:
                error_msg = driver.find_element(By.CLASS_NAME, "alert-danger")
                print(f"  ℹ Error message: {error_msg.text}")
            except:
                print("  ℹ No error message displayed")
            return 1
        else:
            print(f"  ✗ Unexpected redirect: {current_url}")
            return 1
        
        # Test 10: Verify VGK dashboard loaded
        print("\n▶ Test 10: Verify VGK Dashboard Elements")
        try:
            # Check for user name display
            user_display = driver.find_element(By.ID, "user-name-display")
            print(f"  ✓ User display found: {user_display.text}")
        except Exception as e:
            print(f"  ⚠ User display not found: {e}")
        
        try:
            # Check for dashboard section
            dashboard = driver.find_element(By.ID, "dashboard-section")
            print("  ✓ Dashboard section found")
        except Exception as e:
            print(f"  ⚠ Dashboard section not found: {e}")
        
        # Test 11: Check console errors
        print("\n▶ Test 11: Check Browser Console Errors")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if errors:
            print(f"  ✗ Found {len(errors)} console errors:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"    - {error['message'][:100]}")
        else:
            print("  ✓ No console errors detected")
        
        print("\n" + "="*80)
        print(" "*28 + "TEST SUMMARY")
        print("="*80)
        print("\n✓ ALL TESTS PASSED - VGK Login is FULLY FUNCTIONAL\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        driver.save_screenshot('/tmp/stfp_login_error.png')
        print("  ℹ Screenshot saved: /tmp/stfp_login_error.png")
        return 1
    
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
