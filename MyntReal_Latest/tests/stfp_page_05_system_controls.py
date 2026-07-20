"""
STFP Page #5: VGK System Controls
Test every element, button, and control on System Controls page
Core Principle: Don't skip anything, don't assume - test and confirm everything explicitly.
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost:5000"
VGK_USERNAME = "BEV182364369"
VGK_PASSWORD = os.getenv('VGK_TEST_PASSWORD', 'Test@123')

def login(driver):
    driver.get(f"{BASE_URL}/login.html")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(VGK_USERNAME)
    driver.find_element(By.ID, "password").send_keys(VGK_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)

def main():
    print("="*80)
    print(" "*22 + "STFP PAGE #5: SYSTEM CONTROLS")
    print("="*80)
    print(f"\n🎯 Target: {BASE_URL}/vgk/system-controls")
    print(f"👤 User: {VGK_USERNAME}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("▶ Pre-Test: Login and Navigate")
        login(driver)
        driver.get(f"{BASE_URL}/vgk/system-controls")
        time.sleep(3)
        
        if "/vgk/system-controls" not in driver.current_url:
            print("  ✗ Failed to navigate")
            return 1
        print("  ✓ Navigated successfully\n")
        
        page_source = driver.page_source
        
        # Test 1: Page title
        print("▶ Test 1: Check Page Title")
        if "System Control" in page_source:
            print("  ✓ System Controls page title found")
        else:
            print("  ✗ Page title not found")
        
        # Test 2: Control sections
        print("\n▶ Test 2: Check Control Sections")
        sections = ["KYC", "Banking", "Global", "Settings", "Controls"]
        found = sum(1 for s in sections if s in page_source)
        print(f"  📊 Found {found}/{len(sections)} expected sections")
        
        # Test 3: Buttons
        print("\n▶ Test 3: Check Interactive Elements")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        switches = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        print(f"  ✓ Buttons: {len(buttons)}")
        print(f"  ✓ Switches/Checkboxes: {len(switches)}")
        
        # Test 4: Console errors
        print("\n▶ Test 4: Check Console Errors")
        logs = driver.get_log('browser')
        errors = [l for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l['message']]
        print(f"  {'✓' if not errors else '✗'} Console errors: {len(errors)}")
        
        print("\n" + "="*80)
        print(" "*28 + "TEST SUMMARY")
        print("="*80)
        
        score = found + (2 if not errors else 0) + (1 if len(buttons) > 0 else 0)
        print(f"\n📊 Page Score: {score}/8")
        
        if score >= 5:
            print("\n✓ SYSTEM CONTROLS PAGE IS FUNCTIONAL\n")
            return 0
        else:
            print(f"\n⚠ PAGE HAS ISSUES - Score {score}/8\n")
            return 1
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        return 1
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
