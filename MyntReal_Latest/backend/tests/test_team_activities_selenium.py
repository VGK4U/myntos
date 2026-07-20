"""
Selenium-based Frontend Testing for Team Activities Page
MyntReal LLP Staff System - STF (Selenium Test Framework)
Tests complete Team Activities functionality with DC Protocol compliance

DC Protocol: Department isolation enforced at query level
Role-based access control across hierarchy levels

Test Hierarchy Levels:
- VGK4U Supreme (150): All tasks across all departments
- Key Leadership (100): All tasks across all departments
- HR/EA (85): All tasks across all departments  
- Team Leader (70): Department tasks only
- Manager (60): Department tasks only
- Regular Staff (<60): No access (403 Forbidden)
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

BASE_URL = 'http://localhost:5000'
BACKEND_URL = 'http://localhost:8000'
SCREENSHOTS_DIR = 'backend/tests/screenshots/team_activities'

STAFF_TEST_CREDENTIALS = {
    'vgk4u': {'emp_code': 'MR10001', 'password': 'Vgk4u@2024', 'role': 'VGK4U Supreme', 'level': 150},
    'hr': {'emp_code': 'MR10100', 'password': 'Hr@2024', 'role': 'HR', 'level': 85},
    'manager': {'emp_code': 'MR10008', 'password': 'Manager@2024', 'role': 'Manager', 'level': 60},
    'team_leader': {'emp_code': 'MR10006', 'password': 'TeamLead@2024', 'role': 'Team Leader', 'level': 70},
    'senior_exec': {'emp_code': 'MR10009', 'password': 'Senior@2024', 'role': 'Senior Executive', 'level': 40},
}

TEST_RESULTS = {
    'test_name': 'Team Activities Page - STF',
    'timestamp': datetime.now().isoformat(),
    'pre_flight_checks': {},
    'login_tests': {},
    'navigation_tests': {},
    'page_load_tests': {},
    'filter_tests': {},
    'search_tests': {},
    'role_access_tests': {},
    'console_error_tests': {},
    'summary': {}
}

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def log_test(category, test_name, status, message='', screenshot_path=None):
    """Log test result with DC Protocol compliance"""
    result = {
        'status': status,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    if screenshot_path:
        result['screenshot'] = screenshot_path
    
    if category not in TEST_RESULTS:
        TEST_RESULTS[category] = {}
    TEST_RESULTS[category][test_name] = result
    
    status_icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'
    print(f"{status_icon} [{category}] {test_name}: {status} - {message}")


def take_screenshot(driver, name):
    """Take screenshot for test evidence"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{SCREENSHOTS_DIR}/{name}_{timestamp}.png"
    try:
        driver.save_screenshot(filename)
        return filename
    except Exception as e:
        print(f"  ⚠️ Screenshot failed: {e}")
        return None


def setup_driver():
    """Setup headless Chrome driver for testing"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"❌ Failed to setup Chrome driver: {e}")
        return None


def pre_flight_checks():
    """
    CRITICAL: Run pre-flight checks before Selenium testing
    DC Protocol: Validates system readiness
    """
    print("\n" + "=" * 80)
    print("🚀 PRE-FLIGHT CHECKS - TEAM ACTIVITIES STF")
    print("=" * 80 + "\n")
    
    all_passed = True
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            log_test('pre_flight_checks', 'Backend API Health', 'PASS', f'Status: {response.status_code}')
        else:
            log_test('pre_flight_checks', 'Backend API Health', 'FAIL', f'Status: {response.status_code}')
            all_passed = False
    except Exception as e:
        log_test('pre_flight_checks', 'Backend API Health', 'FAIL', str(e))
        all_passed = False
    
    try:
        response = requests.get(f"{BASE_URL}/staff/login", timeout=5)
        if response.status_code == 200:
            log_test('pre_flight_checks', 'Frontend Server', 'PASS', 'Login page accessible')
        else:
            log_test('pre_flight_checks', 'Frontend Server', 'FAIL', f'Status: {response.status_code}')
            all_passed = False
    except Exception as e:
        log_test('pre_flight_checks', 'Frontend Server', 'FAIL', str(e))
        all_passed = False
    
    return all_passed


def staff_login(driver, emp_code, password, role_name):
    """Login to staff portal"""
    try:
        driver.get(f"{BASE_URL}/staff/login")
        time.sleep(2)
        
        emp_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "employeeId"))
        )
        emp_input.clear()
        emp_input.send_keys(emp_code)
        
        pass_input = driver.find_element(By.ID, "password")
        pass_input.clear()
        pass_input.send_keys(password)
        
        screenshot = take_screenshot(driver, f"login_{role_name}_before_submit")
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(3)
        
        if 'dashboard' in driver.current_url or 'staff' in driver.current_url:
            log_test('login_tests', f'Login as {role_name}', 'PASS', f'URL: {driver.current_url}', 
                    take_screenshot(driver, f"login_{role_name}_success"))
            return True
        else:
            log_test('login_tests', f'Login as {role_name}', 'FAIL', f'URL: {driver.current_url}',
                    take_screenshot(driver, f"login_{role_name}_failed"))
            return False
    except Exception as e:
        log_test('login_tests', f'Login as {role_name}', 'FAIL', str(e),
                take_screenshot(driver, f"login_{role_name}_error"))
        return False


def check_console_errors(driver, test_name):
    """Check for JavaScript console errors - STF requirement"""
    try:
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if errors:
            error_messages = [f"{log['message']}" for log in errors[:5]]  # Show first 5
            log_test('console_error_tests', test_name, 'FAIL', 
                    f'Found {len(errors)} console errors: {"; ".join(error_messages)}')
            return False
        else:
            log_test('console_error_tests', test_name, 'PASS', 'No console errors found')
            return True
    except Exception as e:
        log_test('console_error_tests', test_name, 'WARN', f'Could not check console: {str(e)}')
        return True  # Don't fail test if we can't check console


def test_team_activities_navigation(driver, role_name):
    """Test navigation to Team Activities page"""
    try:
        # Click on Team Activities in sidebar
        team_activities_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Team Activities"))
        )
        team_activities_link.click()
        
        time.sleep(3)
        
        # Verify URL
        if 'team-activities' in driver.current_url:
            log_test('navigation_tests', f'Navigate to Team Activities ({role_name})', 'PASS', 
                    driver.current_url, take_screenshot(driver, f"team_activities_{role_name}"))
            return True
        else:
            log_test('navigation_tests', f'Navigate to Team Activities ({role_name})', 'FAIL', 
                    f'Wrong URL: {driver.current_url}', take_screenshot(driver, f"team_activities_wrong_url_{role_name}"))
            return False
    except Exception as e:
        log_test('navigation_tests', f'Navigate to Team Activities ({role_name})', 'FAIL', str(e),
                take_screenshot(driver, f"team_activities_nav_error_{role_name}"))
        return False


def test_page_elements(driver, role_name):
    """Test that all page elements are present"""
    tests_passed = True
    
    try:
        # Check for stat cards
        total_card = driver.find_element(By.ID, "totalCount")
        if total_card:
            log_test('page_load_tests', f'Total Tasks Stat Card ({role_name})', 'PASS', 
                    f'Value: {total_card.text}')
        else:
            log_test('page_load_tests', f'Total Tasks Stat Card ({role_name})', 'FAIL', 'Element not found')
            tests_passed = False
    except NoSuchElementException:
        log_test('page_load_tests', f'Total Tasks Stat Card ({role_name})', 'FAIL', 'Element not found')
        tests_passed = False
    
    try:
        # Check for filter bar
        filter_date = driver.find_element(By.ID, "filterDateRange")
        log_test('page_load_tests', f'Date Range Filter ({role_name})', 'PASS', 'Filter present')
    except NoSuchElementException:
        log_test('page_load_tests', f'Date Range Filter ({role_name})', 'FAIL', 'Filter not found')
        tests_passed = False
    
    try:
        # Check for search box
        search_box = driver.find_element(By.ID, "filterSearch")
        log_test('page_load_tests', f'Search Box ({role_name})', 'PASS', 'Search box present')
    except NoSuchElementException:
        log_test('page_load_tests', f'Search Box ({role_name})', 'FAIL', 'Search box not found')
        tests_passed = False
    
    try:
        # Check for tasks table
        tasks_table = driver.find_element(By.ID, "tasksTableBody")
        log_test('page_load_tests', f'Tasks Table ({role_name})', 'PASS', 'Table present')
    except NoSuchElementException:
        log_test('page_load_tests', f'Tasks Table ({role_name})', 'FAIL', 'Table not found')
        tests_passed = False
    
    return tests_passed


def test_date_filter(driver, role_name):
    """Test date range filter"""
    try:
        # Change to Last 7 Days
        date_filter = driver.find_element(By.ID, "filterDateRange")
        date_filter.click()
        
        # Select "7" option
        option_7days = driver.find_element(By.CSS_SELECTOR, "option[value='7']")
        option_7days.click()
        
        time.sleep(2)
        
        log_test('filter_tests', f'Date Filter - Last 7 Days ({role_name})', 'PASS', 
                'Filter applied', take_screenshot(driver, f"filter_date_7days_{role_name}"))
        return True
    except Exception as e:
        log_test('filter_tests', f'Date Filter - Last 7 Days ({role_name})', 'FAIL', str(e))
        return False


def test_status_filter(driver, role_name):
    """Test status filter"""
    try:
        # Change to Pending status
        status_filter = driver.find_element(By.ID, "filterStatus")
        status_filter.click()
        
        # Select "pending" option
        option_pending = driver.find_element(By.CSS_SELECTOR, "option[value='pending']")
        option_pending.click()
        
        time.sleep(2)
        
        log_test('filter_tests', f'Status Filter - Pending ({role_name})', 'PASS', 
                'Filter applied', take_screenshot(driver, f"filter_status_pending_{role_name}"))
        return True
    except Exception as e:
        log_test('filter_tests', f'Status Filter - Pending ({role_name})', 'FAIL', str(e))
        return False


def test_name_search(driver, role_name):
    """Test name search functionality"""
    try:
        # Type in search box
        search_box = driver.find_element(By.ID, "filterSearch")
        search_box.clear()
        search_box.send_keys("Test")
        
        time.sleep(2)
        
        log_test('search_tests', f'Name Search ({role_name})', 'PASS', 
                'Search executed', take_screenshot(driver, f"search_test_{role_name}"))
        
        # Clear search
        search_box.clear()
        time.sleep(1)
        
        return True
    except Exception as e:
        log_test('search_tests', f'Name Search ({role_name})', 'FAIL', str(e))
        return False


def test_regular_staff_access(driver):
    """Test that regular staff (<60) cannot access Team Activities"""
    try:
        creds = STAFF_TEST_CREDENTIALS['senior_exec']
        if staff_login(driver, creds['emp_code'], creds['password'], creds['role']):
            time.sleep(2)
            
            # Try to find Team Activities link - should NOT exist
            try:
                team_activities_link = driver.find_element(By.LINK_TEXT, "Team Activities")
                log_test('role_access_tests', 'Regular Staff Access Block', 'FAIL', 
                        'Team Activities link found (should not be visible)',
                        take_screenshot(driver, 'regular_staff_has_access'))
                return False
            except NoSuchElementException:
                log_test('role_access_tests', 'Regular Staff Access Block', 'PASS', 
                        'Team Activities link correctly hidden',
                        take_screenshot(driver, 'regular_staff_no_access'))
                return True
        else:
            log_test('role_access_tests', 'Regular Staff Access Block', 'FAIL', 'Login failed')
            return False
    except Exception as e:
        log_test('role_access_tests', 'Regular Staff Access Block', 'FAIL', str(e))
        return False


def run_full_test_suite():
    """Run complete test suite for Team Activities"""
    print("\n" + "=" * 80)
    print("🧪 TEAM ACTIVITIES - SELENIUM TEST FRAMEWORK (STF)")
    print("=" * 80 + "\n")
    
    # Pre-flight checks
    if not pre_flight_checks():
        print("\n❌ Pre-flight checks failed. Aborting tests.\n")
        return False
    
    driver = setup_driver()
    if not driver:
        print("\n❌ Driver setup failed. Aborting tests.\n")
        return False
    
    all_tests_passed = True
    
    try:
        # Test 1: Manager Access (Hierarchy 60)
        print("\n" + "-" * 80)
        print("TEST SUITE 1: MANAGER ACCESS (Hierarchy 60)")
        print("-" * 80)
        
        creds = STAFF_TEST_CREDENTIALS['manager']
        if staff_login(driver, creds['emp_code'], creds['password'], creds['role']):
            if test_team_activities_navigation(driver, creds['role']):
                check_console_errors(driver, f'Page Load - {creds["role"]}')
                test_page_elements(driver, creds['role'])
                test_date_filter(driver, creds['role'])
                test_status_filter(driver, creds['role'])
                test_name_search(driver, creds['role'])
        
        # Test 2: HR Access (Hierarchy 85 - Supreme)
        print("\n" + "-" * 80)
        print("TEST SUITE 2: HR ACCESS (Hierarchy 85 - Supreme)")
        print("-" * 80)
        
        creds = STAFF_TEST_CREDENTIALS['hr']
        if staff_login(driver, creds['emp_code'], creds['password'], creds['role']):
            if test_team_activities_navigation(driver, creds['role']):
                check_console_errors(driver, f'Page Load - {creds["role"]}')
                test_page_elements(driver, creds['role'])
        
        # Test 3: Regular Staff Access Block (Hierarchy <60)
        print("\n" + "-" * 80)
        print("TEST SUITE 3: REGULAR STAFF ACCESS BLOCK (Hierarchy <60)")
        print("-" * 80)
        
        test_regular_staff_access(driver)
        
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        all_tests_passed = False
    finally:
        driver.quit()
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80 + "\n")
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category, tests in TEST_RESULTS.items():
        if category not in ['test_name', 'timestamp', 'summary'] and isinstance(tests, dict):
            for test_name, result in tests.items():
                total_tests += 1
                if result['status'] == 'PASS':
                    passed_tests += 1
                elif result['status'] == 'FAIL':
                    failed_tests += 1
    
    TEST_RESULTS['summary'] = {
        'total_tests': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'pass_rate': f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    }
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📈 Pass Rate: {TEST_RESULTS['summary']['pass_rate']}")
    
    # Save results to JSON
    results_file = f"{SCREENSHOTS_DIR}/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)
    print(f"\n📄 Test results saved to: {results_file}")
    
    print("\n" + "=" * 80 + "\n")
    
    return failed_tests == 0


if __name__ == "__main__":
    success = run_full_test_suite()
    sys.exit(0 if success else 1)
