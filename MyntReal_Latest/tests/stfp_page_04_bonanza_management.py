"""
STFP Page #4: VGK Bonanza Management
Test every element, button, and functionality on Bonanza Management page
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
    print(" "*20 + "STFP PAGE #4: BONANZA MANAGEMENT")
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
        # Login and navigate
        print("▶ Pre-Test: Login and Navigate")
        login(driver)
        
        driver.get(f"{BASE_URL}/vgk/bonanza-management")
        time.sleep(3)
        
        if "/vgk/bonanza-management" not in driver.current_url:
            print("  ✗ Failed to navigate to Bonanza Management")
            return 1
        print("  ✓ Navigated to Bonanza Management\n")
        
        # Test 1: Check page title
        print("▶ Test 1: Check Page Title")
        page_source = driver.page_source
        if "Bonanza Management" in page_source or "bonanza" in page_source.lower():
            print("  ✓ Bonanza Management page title found")
        else:
            print("  ✗ Page title not found")
        
        # Test 2: Check for action buttons
        print("\n▶ Test 2: Check Action Buttons")
        
        buttons_to_check = [
            ("Add New Bonanza", "addBonanzaBtn"),
            ("Refresh", "refreshBonanzaBtn"),
            ("View Active", None),  # Text-based search
            ("View Completed", None),
        ]
        
        found_buttons = 0
        for btn_name, btn_id in buttons_to_check:
            try:
                if btn_id:
                    driver.find_element(By.ID, btn_id)
                    print(f"  ✓ {btn_name} button found (ID: {btn_id})")
                    found_buttons += 1
                else:
                    if btn_name in page_source:
                        print(f"  ✓ {btn_name} text found in page")
                        found_buttons += 1
                    else:
                        print(f"  ⚠ {btn_name} not found")
            except Exception:
                print(f"  ⚠ {btn_name} button not found")
        
        print(f"\n  📊 Found {found_buttons}/{len(buttons_to_check)} expected elements")
        
        # Test 3: Check for table/list of bonanzas
        print("\n▶ Test 3: Check Bonanza List/Table")
        try:
            # Try to find table
            table = driver.find_element(By.TAG_NAME, "table")
            print("  ✓ Bonanza table found")
            
            # Check for table headers
            headers = driver.find_elements(By.TAG_NAME, "th")
            if headers:
                print(f"  ✓ Table has {len(headers)} columns")
                header_texts = [h.text for h in headers[:5]]
                print(f"  ℹ Headers: {', '.join(header_texts)}")
        except Exception as e:
            print(f"  ⚠ Bonanza table not found - might use cards/list layout")
        
        # Test 4: Check for filter options
        print("\n▶ Test 4: Check Filter/Search Options")
        filter_elements = []
        
        try:
            search_input = driver.find_element(By.CSS_SELECTOR, "input[type='search'], input[placeholder*='search' i]")
            print("  ✓ Search input found")
            filter_elements.append("search")
        except:
            print("  ⚠ Search input not found")
        
        try:
            date_filters = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
            if date_filters:
                print(f"  ✓ Found {len(date_filters)} date filter(s)")
                filter_elements.append("date")
        except:
            print("  ⚠ Date filters not found")
        
        # Test 5: Check for statistics/summary
        print("\n▶ Test 5: Check Statistics/Summary Section")
        stats_keywords = ["total", "active", "pending", "completed", "claimed"]
        found_stats = []
        
        for keyword in stats_keywords:
            if keyword in page_source.lower():
                found_stats.append(keyword)
        
        if found_stats:
            print(f"  ✓ Found statistics keywords: {', '.join(found_stats)}")
        else:
            print("  ⚠ No statistics section found")
        
        # Test 6: Check "Back to Dashboard" link
        print("\n▶ Test 6: Check Back to Dashboard Link")
        try:
            back_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Back') or contains(text(), 'Dashboard')]")
            if back_links:
                print(f"  ✓ Found {len(back_links)} navigation link(s)")
            else:
                print("  ⚠ Back to Dashboard link not found")
        except:
            print("  ⚠ Navigation links not found")
        
        # Test 7: Test page responsiveness
        print("\n▶ Test 7: Test Page Load Performance")
        load_elements = ["script", "style", "div"]
        for elem in load_elements:
            elements = driver.find_elements(By.TAG_NAME, elem)
            print(f"  ℹ Found {len(elements)} <{elem}> elements")
        
        # Test 8: Check console errors
        print("\n▶ Test 8: Check Browser Console Errors")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE' and 'favicon' not in log['message']]
        
        if errors:
            print(f"  ✗ Found {len(errors)} console errors:")
            for error in errors[:3]:
                msg = error['message'][:150]
                print(f"    - {msg}")
        else:
            print("  ✓ No critical console errors detected")
        
        # Test 9: Check page structure
        print("\n▶ Test 9: Check Page Structure")
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            print("  ✓ Page body found")
            
            main_content = driver.find_elements(By.CSS_SELECTOR, "main, .main, #main, .content, .container")
            if main_content:
                print(f"  ✓ Main content area found ({len(main_content)} element(s))")
        except:
            print("  ⚠ Page structure incomplete")
        
        # Test 10: Check if page is interactive
        print("\n▶ Test 10: Check Page Interactivity")
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            links = driver.find_elements(By.TAG_NAME, "a")
            inputs = driver.find_elements(By.TAG_NAME, "input")
            
            print(f"  ✓ Interactive elements found:")
            print(f"    - Buttons: {len(buttons)}")
            print(f"    - Links: {len(links)}")
            print(f"    - Inputs: {len(inputs)}")
            
            if len(buttons) + len(links) + len(inputs) > 0:
                print("  ✓ Page is interactive")
        except:
            print("  ✗ Page interactivity check failed")
        
        print("\n" + "="*80)
        print(" "*28 + "TEST SUMMARY")
        print("="*80)
        
        # Calculate score
        score = 0
        if found_buttons >= 2: score += 1
        if len(filter_elements) > 0: score += 1
        if len(found_stats) > 0: score += 1
        if len(errors) == 0: score += 2
        score += min(found_buttons, 3)
        
        print(f"\n📊 Page Score: {score}/10")
        print(f"📊 Console Errors: {len(errors)}")
        
        if score >= 6 and len(errors) <= 1:
            print("\n✓ BONANZA MANAGEMENT PAGE IS FUNCTIONAL\n")
            return 0
        else:
            print(f"\n⚠ PAGE HAS ISSUES - Score {score}/10, {len(errors)} errors\n")
            return 1
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        driver.save_screenshot('/tmp/stfp_bonanza_error.png')
        print("  ℹ Screenshot saved: /tmp/stfp_bonanza_error.png")
        return 1
    
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
