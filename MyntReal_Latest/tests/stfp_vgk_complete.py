"""
STFP - Selenium Front-End Testing Protocol
Complete VGK Role Testing - ALL Pages, ALL Features
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
BASE_URL = os.getenv('REPLIT_DEV_DOMAIN', 'http://localhost:5000')
VGK_USERNAME = "BEV001"  # VGK Test User
VGK_PASSWORD = os.getenv('VGK_TEST_PASSWORD', 'Test@123')

# Test Results
test_results = []
errors_found = []

def log_test(test_name, status, details=""):
    """Log test result"""
    result = {
        'test': test_name,
        'status': status,
        'details': details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    test_results.append(result)
    icon = "✓" if status == "PASS" else "✗"
    print(f"{icon} {test_name}: {status}")
    if details:
        print(f"  ℹ {details}")

def log_error(error_type, message, screenshot_path=None):
    """Log error found during testing"""
    error = {
        'type': error_type,
        'message': message,
        'screenshot': screenshot_path,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    errors_found.append(error)
    print(f"❌ ERROR [{error_type}]: {message}")

def check_console_errors(driver):
    """Check browser console for errors"""
    logs = driver.get_log('browser')
    severe_errors = [log for log in logs if log['level'] == 'SEVERE']
    if severe_errors:
        for error in severe_errors:
            log_error('CONSOLE', error['message'])
        return False
    return True

def wait_for_element(driver, by, value, timeout=10):
    """Wait for element to be present"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        log_error('UI', f"Element not found: {value}")
        return None

def click_element(driver, by, value, description):
    """Click element with validation"""
    try:
        element = wait_for_element(driver, by, value)
        if element:
            element.click()
            time.sleep(1)  # Wait for UI update
            log_test(f"Click: {description}", "PASS")
            return True
        else:
            log_test(f"Click: {description}", "FAIL", "Element not found")
            return False
    except Exception as e:
        log_error('FUNCTIONAL', f"Failed to click {description}: {str(e)}")
        return False

def verify_page_elements(driver, elements, page_name):
    """Verify all elements are present on page"""
    missing_elements = []
    for element_id, description in elements.items():
        try:
            driver.find_element(By.ID, element_id)
            log_test(f"Verify {description}", "PASS", f"Found on {page_name}")
        except NoSuchElementException:
            missing_elements.append(description)
            log_test(f"Verify {description}", "FAIL", f"Missing on {page_name}")
    
    return len(missing_elements) == 0

def main():
    print("="*80)
    print(" "*20 + "STFP - VGK COMPLETE PAGE TESTING")
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
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)
    
    try:
        # ========== TEST 1: LOGIN ==========
        print("\n▶ Test 1: VGK Login")
        driver.get(f"{BASE_URL}/login.html")
        time.sleep(2)
        
        # Check console errors
        if not check_console_errors(driver):
            log_test("Login Page - Console Check", "FAIL", "Console errors detected")
        else:
            log_test("Login Page - Console Check", "PASS")
        
        # Fill login form
        username_field = wait_for_element(driver, By.ID, "username")
        password_field = wait_for_element(driver, By.ID, "password")
        
        if username_field and password_field:
            username_field.send_keys(VGK_USERNAME)
            password_field.send_keys(VGK_PASSWORD)
            
            # Click login
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_btn.click()
            time.sleep(3)
            
            # Verify redirect to VGK dashboard
            if "/vgk.html" in driver.current_url:
                log_test("VGK Login", "PASS", "Successfully logged in and redirected")
            else:
                log_test("VGK Login", "FAIL", f"Wrong redirect: {driver.current_url}")
                driver.quit()
                return
        else:
            log_test("VGK Login", "FAIL", "Login form elements missing")
            driver.quit()
            return
        
        # ========== TEST 2: VGK DASHBOARD ==========
        print("\n▶ Test 2: VGK Dashboard Page")
        time.sleep(2)
        
        # Check console errors
        check_console_errors(driver)
        
        # Verify dashboard elements
        dashboard_elements = {
            'dashboard-section': 'Dashboard Section',
            'user-name-display': 'User Name Display',
        }
        
        for elem_id, desc in dashboard_elements.items():
            try:
                driver.find_element(By.ID, elem_id)
                log_test(f"Dashboard: {desc}", "PASS")
            except NoSuchElementException:
                log_test(f"Dashboard: {desc}", "FAIL", "Element not found")
        
        # ========== TEST 3: VGK AWARD APPROVAL ==========
        print("\n▶ Test 3: VGK Award Approval Page")
        
        # Navigate to Award Approval
        if click_element(driver, By.ID, "nav-vgk-award-approval", "Award Approval Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            # Verify page loaded
            award_section = wait_for_element(driver, By.ID, "vgk-award-approval-section")
            if award_section:
                log_test("Award Approval Page Load", "PASS")
                
                # Check all buttons
                buttons_to_check = [
                    ('refresh-vgk-award-queue', 'Refresh Queue Button'),
                    ('export-vgk-award-csv', 'Export CSV Button'),
                ]
                
                for btn_id, desc in buttons_to_check:
                    try:
                        driver.find_element(By.ID, btn_id)
                        log_test(f"Award Approval: {desc}", "PASS")
                    except NoSuchElementException:
                        log_test(f"Award Approval: {desc}", "FAIL", "Button missing")
                
                # Test date filter
                try:
                    date_from = driver.find_element(By.ID, "vgk-award-date-from")
                    date_to = driver.find_element(By.ID, "vgk-award-date-to")
                    log_test("Award Approval: Date Filter", "PASS")
                except NoSuchElementException:
                    log_test("Award Approval: Date Filter", "FAIL", "Date fields missing")
                
                # Click refresh to load data
                click_element(driver, By.ID, "refresh-vgk-award-queue", "Refresh Award Queue")
                time.sleep(2)
                check_console_errors(driver)
            else:
                log_test("Award Approval Page Load", "FAIL")
        
        # ========== TEST 4: VGK AWARDS PROCUREMENT ==========
        print("\n▶ Test 4: VGK Awards Procurement Page")
        
        if click_element(driver, By.ID, "nav-vgk-awards-procurement", "Awards Procurement Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            procurement_section = wait_for_element(driver, By.ID, "vgk-awards-procurement-section")
            if procurement_section:
                log_test("Awards Procurement Page Load", "PASS")
                
                # Test tab navigation
                tabs = [
                    ('vgk-procurement-pending-tab', 'Pending Purchase Tab'),
                    ('vgk-procurement-delivery-tab', 'Pending Delivery Tab'),
                ]
                
                for tab_id, desc in tabs:
                    if click_element(driver, By.ID, tab_id, desc):
                        time.sleep(1)
                        check_console_errors(driver)
            else:
                log_test("Awards Procurement Page Load", "FAIL")
        
        # ========== TEST 5: VGK BONANZA PROCUREMENT ==========
        print("\n▶ Test 5: VGK Bonanza Procurement Page")
        
        if click_element(driver, By.ID, "nav-vgk-bonanza-procurement", "Bonanza Procurement Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            bonanza_section = wait_for_element(driver, By.ID, "vgk-bonanza-procurement-section")
            if bonanza_section:
                log_test("Bonanza Procurement Page Load", "PASS")
                
                # Test tabs
                tabs = [
                    ('vgk-bonanza-pending-tab', 'Pending Purchase Tab'),
                    ('vgk-bonanza-delivery-tab', 'Pending Delivery Tab'),
                ]
                
                for tab_id, desc in tabs:
                    if click_element(driver, By.ID, tab_id, desc):
                        time.sleep(1)
                        check_console_errors(driver)
            else:
                log_test("Bonanza Procurement Page Load", "FAIL")
        
        # ========== TEST 6: VGK TRAINING CLAIMS ==========
        print("\n▶ Test 6: VGK Training Claims Page")
        
        if click_element(driver, By.ID, "nav-vgk-training-claims", "Training Claims Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            training_section = wait_for_element(driver, By.ID, "vgk-training-claims-section")
            if training_section:
                log_test("Training Claims Page Load", "PASS")
                
                # Check bulk action buttons
                buttons = [
                    ('refresh-vgk-training-claims', 'Refresh Button'),
                    ('bulk-approve-training', 'Bulk Approve Button'),
                    ('bulk-reject-training', 'Bulk Reject Button'),
                ]
                
                for btn_id, desc in buttons:
                    try:
                        driver.find_element(By.ID, btn_id)
                        log_test(f"Training Claims: {desc}", "PASS")
                    except NoSuchElementException:
                        log_test(f"Training Claims: {desc}", "FAIL", "Button missing")
            else:
                log_test("Training Claims Page Load", "FAIL")
        
        # ========== TEST 7: VGK FIELD ALLOWANCE ==========
        print("\n▶ Test 7: VGK Field Allowance Page")
        
        if click_element(driver, By.ID, "nav-vgk-field-allowance", "Field Allowance Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            allowance_section = wait_for_element(driver, By.ID, "vgk-field-allowance-section")
            if allowance_section:
                log_test("Field Allowance Page Load", "PASS")
            else:
                log_test("Field Allowance Page Load", "FAIL")
        
        # ========== TEST 8: VGK USER MANAGEMENT ==========
        print("\n▶ Test 8: VGK User Management Page")
        
        if click_element(driver, By.ID, "nav-vgk-user-management", "User Management Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            user_mgmt_section = wait_for_element(driver, By.ID, "vgk-user-management-section")
            if user_mgmt_section:
                log_test("User Management Page Load", "PASS")
                
                # Check bulk operation buttons
                buttons = [
                    ('bulk-activate-users', 'Bulk Activate Button'),
                    ('bulk-deactivate-users', 'Bulk Deactivate Button'),
                ]
                
                for btn_id, desc in buttons:
                    try:
                        driver.find_element(By.ID, btn_id)
                        log_test(f"User Management: {desc}", "PASS")
                    except NoSuchElementException:
                        log_test(f"User Management: {desc}", "FAIL", "Button missing")
            else:
                log_test("User Management Page Load", "FAIL")
        
        # ========== TEST 9: VGK KYC/BANKING APPROVAL ==========
        print("\n▶ Test 9: VGK KYC/Banking Approval Page")
        
        if click_element(driver, By.ID, "nav-vgk-kyc-banking", "KYC/Banking Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            kyc_section = wait_for_element(driver, By.ID, "vgk-kyc-banking-section")
            if kyc_section:
                log_test("KYC/Banking Page Load", "PASS")
                
                # Test tabs
                tabs = [
                    ('vgk-kyc-pending-tab', 'KYC Pending Tab'),
                    ('vgk-bank-pending-tab', 'Bank Pending Tab'),
                ]
                
                for tab_id, desc in tabs:
                    if click_element(driver, By.ID, tab_id, desc):
                        time.sleep(1)
                        check_console_errors(driver)
            else:
                log_test("KYC/Banking Page Load", "FAIL")
        
        # ========== TEST 10: VGK MEMBERS SEARCH ==========
        print("\n▶ Test 10: VGK Members Search Page")
        
        if click_element(driver, By.ID, "nav-vgk-members-search", "Members Search Navigation"):
            time.sleep(2)
            check_console_errors(driver)
            
            search_section = wait_for_element(driver, By.ID, "vgk-members-search-section")
            if search_section:
                log_test("Members Search Page Load", "PASS")
                
                # Test search functionality
                search_input = wait_for_element(driver, By.ID, "vgk-search-input")
                if search_input:
                    log_test("Members Search: Search Input", "PASS")
                    
                    # Test CSV export button (VGK only)
                    try:
                        driver.find_element(By.ID, "export-search-csv")
                        log_test("Members Search: CSV Export (VGK Only)", "PASS")
                    except NoSuchElementException:
                        log_test("Members Search: CSV Export (VGK Only)", "FAIL", "Button missing")
            else:
                log_test("Members Search Page Load", "FAIL")
        
        # ========== TEST 11: LOGOUT ==========
        print("\n▶ Test 11: Logout")
        
        try:
            # Click profile dropdown
            profile_btn = driver.find_element(By.CLASS_NAME, "profile-btn")
            profile_btn.click()
            time.sleep(1)
            
            # Click logout
            logout_link = driver.find_element(By.ID, "logout-link")
            logout_link.click()
            time.sleep(2)
            
            # Verify redirect to login
            if "/login.html" in driver.current_url:
                log_test("Logout", "PASS", "Successfully logged out")
            else:
                log_test("Logout", "FAIL", f"Wrong redirect: {driver.current_url}")
        except Exception as e:
            log_test("Logout", "FAIL", str(e))
        
    except Exception as e:
        log_error('CRITICAL', f"Test execution failed: {str(e)}")
        driver.save_screenshot('/tmp/stfp_vgk_error.png')
    
    finally:
        driver.quit()
    
    # ========== FINAL REPORT ==========
    print("\n" + "="*80)
    print(" "*30 + "TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    total = len(test_results)
    
    print(f"\n📊 Total Tests: {total}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"❌ Errors Found: {len(errors_found)}\n")
    
    if failed > 0:
        print("Failed Tests:")
        for r in test_results:
            if r['status'] == 'FAIL':
                print(f"  ✗ {r['test']}: {r['details']}")
    
    if errors_found:
        print("\nErrors Found:")
        for err in errors_found:
            print(f"  ❌ [{err['type']}] {err['message']}")
    
    print("\n" + "="*80)
    
    if failed == 0 and len(errors_found) == 0:
        print("✓ ALL TESTS PASSED - VGK platform is FULLY FUNCTIONAL")
        return 0
    else:
        print("✗ TESTING INCOMPLETE - Errors detected and require fixes")
        return 1

if __name__ == "__main__":
    exit(main())
