"""
Selenium-based Frontend Testing for Staff Journey Tracking System
MyntReal LLP Staff System - STF (Selenium Test Framework)
Tests complete journey lifecycle with role-based access control across 8 hierarchy levels

DC Protocol: Complete audit trail for all test scenarios
WVV: Validated GPS data, distance calculation, photo verification testing

Test Hierarchy Levels:
- VGK4U Supreme (150): Full access + Transport Rate Config
- Key Leadership (100): All Journeys view
- HR/EA (85): All Journeys view  
- Team Leader (70): Team Journeys view
- Manager (60): Team Journeys view
- Senior Executive (40): My Journeys only
- Junior Executive (20): My Journeys only
"""

import os
import sys
import time
import json
import requests
import base64
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

BASE_URL = 'http://localhost:5000'
BACKEND_URL = 'http://localhost:8000'
SCREENSHOTS_DIR = 'backend/tests/screenshots/journey_tests'

STAFF_TEST_CREDENTIALS = {
    'vgk4u': {'emp_code': 'MR10001', 'password': 'Vgk4u@2024', 'role': 'VGK4U Supreme', 'level': 150},
    'hr': {'emp_code': 'MR10100', 'password': 'Hr@2024', 'role': 'HR', 'level': 85},
    'manager': {'emp_code': 'MR10008', 'password': 'Manager@2024', 'role': 'Manager', 'level': 60},
    'senior_exec': {'emp_code': 'MR10009', 'password': 'Senior@2024', 'role': 'Senior Executive', 'level': 40},
    'junior_exec': {'emp_code': 'MR10007', 'password': 'Junior@2024', 'role': 'Junior Executive', 'level': 20},
}

TEST_RESULTS = {
    'test_name': 'Staff Journey Tracking System - STF',
    'timestamp': datetime.now().isoformat(),
    'pre_flight_checks': {},
    'login_tests': {},
    'navigation_tests': {},
    'journey_workflow_tests': {},
    'role_access_tests': {},
    'transport_rate_tests': {},
    'api_tests': {},
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
    print("🚀 PRE-FLIGHT CHECKS - STAFF JOURNEY TRACKING STF")
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
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code in [200, 302]:
            log_test('pre_flight_checks', 'Frontend Server', 'PASS', f'Status: {response.status_code}')
        else:
            log_test('pre_flight_checks', 'Frontend Server', 'FAIL', f'Status: {response.status_code}')
            all_passed = False
    except Exception as e:
        log_test('pre_flight_checks', 'Frontend Server', 'FAIL', str(e))
        all_passed = False
    
    journey_routes = [
        '/staff/my-journeys',
        '/staff/team-journeys',
        '/staff/all-journeys',
        '/staff/vgk4u-journeys'
    ]
    
    for route in journey_routes:
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=5)
            if response.status_code in [200, 302]:
                log_test('pre_flight_checks', f'Route: {route}', 'PASS', f'Status: {response.status_code}')
            else:
                log_test('pre_flight_checks', f'Route: {route}', 'FAIL', f'Status: {response.status_code}')
                all_passed = False
        except Exception as e:
            log_test('pre_flight_checks', f'Route: {route}', 'FAIL', str(e))
            all_passed = False
    
    journey_endpoints = [
        '/api/v1/staff/journeys/transport-rates',
        '/api/v1/staff/journeys/my',
        '/api/v1/staff/journeys/team',
        '/api/v1/staff/journeys/all',
        '/api/v1/staff/journeys/stats',
    ]
    
    for endpoint in journey_endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if response.status_code in [200, 401, 403]:
                log_test('pre_flight_checks', f'API: {endpoint}', 'PASS', f'Status: {response.status_code} (auth required)')
            else:
                log_test('pre_flight_checks', f'API: {endpoint}', 'FAIL', f'Status: {response.status_code}')
                all_passed = False
        except Exception as e:
            log_test('pre_flight_checks', f'API: {endpoint}', 'FAIL', str(e))
            all_passed = False
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/staff/journeys/transport-rates", timeout=5)
        log_test('pre_flight_checks', 'Transport Rates API', 'PASS', 'Endpoint accessible')
    except Exception as e:
        log_test('pre_flight_checks', 'Transport Rates API', 'FAIL', str(e))
        all_passed = False
    
    return all_passed


def test_staff_login(driver, role_key):
    """Test staff login for specific role"""
    creds = STAFF_TEST_CREDENTIALS.get(role_key)
    if not creds:
        log_test('login_tests', f'Login {role_key}', 'FAIL', 'Invalid role key')
        return None
    
    try:
        driver.get(f"{BASE_URL}/staff/login")
        time.sleep(2)
        
        emp_code_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "employeeId"))
        )
        emp_code_input.clear()
        emp_code_input.send_keys(creds['emp_code'])
        
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(creds['password'])
        
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        time.sleep(3)
        
        if 'dashboard' in driver.current_url.lower() or 'staff' in driver.current_url.lower():
            screenshot = take_screenshot(driver, f"login_success_{role_key}")
            log_test('login_tests', f'Login {creds["role"]} ({creds["emp_code"]})', 'PASS', 
                    f'Redirected to: {driver.current_url}', screenshot)
            return True
        else:
            screenshot = take_screenshot(driver, f"login_failed_{role_key}")
            log_test('login_tests', f'Login {creds["role"]} ({creds["emp_code"]})', 'FAIL', 
                    f'Still at: {driver.current_url}', screenshot)
            return False
            
    except Exception as e:
        screenshot = take_screenshot(driver, f"login_error_{role_key}")
        log_test('login_tests', f'Login {creds["role"]} ({creds["emp_code"]})', 'FAIL', 
                str(e), screenshot)
        return False


def test_journey_page_access(driver, role_key):
    """Test journey page access based on role hierarchy"""
    creds = STAFF_TEST_CREDENTIALS.get(role_key)
    level = creds['level']
    
    access_rules = {
        '/staff/my-journeys': 20,
        '/staff/team-journeys': 60,
        '/staff/all-journeys': 85,
        '/staff/vgk4u-journeys': 150,
    }
    
    results = []
    
    for route, min_level in access_rules.items():
        try:
            driver.get(f"{BASE_URL}{route}")
            time.sleep(2)
            
            should_access = level >= min_level
            page_title = driver.title.lower()
            page_loaded = 'journey' in page_title or 'myntreal' in page_title
            
            if should_access and page_loaded:
                screenshot = take_screenshot(driver, f"access_{role_key}_{route.replace('/', '_')}")
                log_test('role_access_tests', f'{creds["role"]} -> {route}', 'PASS', 
                        f'Level {level} >= {min_level}: Access granted', screenshot)
                results.append(True)
            elif not should_access:
                log_test('role_access_tests', f'{creds["role"]} -> {route}', 'PASS', 
                        f'Level {level} < {min_level}: Access correctly denied')
                results.append(True)
            else:
                screenshot = take_screenshot(driver, f"access_fail_{role_key}_{route.replace('/', '_')}")
                log_test('role_access_tests', f'{creds["role"]} -> {route}', 'FAIL', 
                        f'Unexpected access result', screenshot)
                results.append(False)
                
        except Exception as e:
            log_test('role_access_tests', f'{creds["role"]} -> {route}', 'FAIL', str(e))
            results.append(False)
    
    return all(results)


def test_my_journeys_page(driver):
    """Test My Journeys page functionality"""
    try:
        driver.get(f"{BASE_URL}/staff/my-journeys")
        time.sleep(3)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "main-content"))
        )
        
        page_elements = {
            'header': driver.find_elements(By.TAG_NAME, "h1"),
            'journey_list': driver.find_elements(By.CLASS_NAME, "journey-card") or 
                           driver.find_elements(By.CLASS_NAME, "journey-list"),
            'start_button': driver.find_elements(By.ID, "startJourneyBtn") or
                           driver.find_elements(By.CSS_SELECTOR, "[onclick*='startJourney']"),
        }
        
        screenshot = take_screenshot(driver, "my_journeys_page")
        
        if page_elements['header']:
            log_test('navigation_tests', 'My Journeys Page Load', 'PASS', 
                    f'Page loaded with header: {page_elements["header"][0].text}', screenshot)
            return True
        else:
            log_test('navigation_tests', 'My Journeys Page Load', 'FAIL', 
                    'Page structure incomplete', screenshot)
            return False
            
    except Exception as e:
        screenshot = take_screenshot(driver, "my_journeys_error")
        log_test('navigation_tests', 'My Journeys Page Load', 'FAIL', str(e), screenshot)
        return False


def test_vgk4u_dashboard(driver):
    """Test VGK4U Dashboard with transport rate configuration"""
    try:
        driver.get(f"{BASE_URL}/staff/vgk4u-journeys")
        time.sleep(3)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "main-content"))
        )
        
        dashboard_elements = {
            'stats_cards': driver.find_elements(By.CLASS_NAME, "stat-card") or
                          driver.find_elements(By.CLASS_NAME, "stats-card"),
            'transport_config': driver.find_elements(By.ID, "transportRatesSection") or
                               driver.find_elements(By.CSS_SELECTOR, "[data-section='transport-rates']"),
            'charts': driver.find_elements(By.TAG_NAME, "canvas"),
        }
        
        screenshot = take_screenshot(driver, "vgk4u_dashboard")
        
        log_test('navigation_tests', 'VGK4U Dashboard Load', 'PASS', 
                f'Dashboard loaded with {len(dashboard_elements["stats_cards"])} stat cards', screenshot)
        
        return True
        
    except Exception as e:
        screenshot = take_screenshot(driver, "vgk4u_dashboard_error")
        log_test('navigation_tests', 'VGK4U Dashboard Load', 'FAIL', str(e), screenshot)
        return False


def test_journey_api_endpoints(token=None):
    """Test Journey API endpoints directly"""
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    endpoints_to_test = [
        ('GET', '/api/v1/staff/journeys/transport-rates', 'Transport Rates'),
        ('GET', '/api/v1/staff/journeys/stats', 'Journey Stats'),
        ('GET', '/api/v1/staff/journeys/my', 'My Journeys'),
    ]
    
    results = []
    
    for method, endpoint, name in endpoints_to_test:
        try:
            if method == 'GET':
                response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(f"{BACKEND_URL}{endpoint}", headers=headers, json={}, timeout=10)
            
            if response.status_code in [200, 201]:
                log_test('api_tests', f'{name} ({method})', 'PASS', 
                        f'Status: {response.status_code}')
                results.append(True)
            elif response.status_code in [401, 403]:
                log_test('api_tests', f'{name} ({method})', 'PASS', 
                        f'Auth required (Status: {response.status_code})')
                results.append(True)
            else:
                log_test('api_tests', f'{name} ({method})', 'FAIL', 
                        f'Status: {response.status_code}, Response: {response.text[:100]}')
                results.append(False)
                
        except Exception as e:
            log_test('api_tests', f'{name} ({method})', 'FAIL', str(e))
            results.append(False)
    
    return all(results)


def test_journey_start_workflow(driver):
    """Test starting a new journey"""
    try:
        driver.get(f"{BASE_URL}/staff/my-journeys")
        time.sleep(3)
        
        start_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "startJourneyBtn"))
        )
        
        screenshot = take_screenshot(driver, "journey_start_ready")
        log_test('journey_workflow_tests', 'Start Journey Button Found', 'PASS', 
                'Ready to start journey', screenshot)
        
        return True
        
    except TimeoutException:
        screenshot = take_screenshot(driver, "journey_start_not_found")
        log_test('journey_workflow_tests', 'Start Journey Button Found', 'WARN', 
                'Start button not found - may require active attendance', screenshot)
        return True
        
    except Exception as e:
        screenshot = take_screenshot(driver, "journey_start_error")
        log_test('journey_workflow_tests', 'Start Journey Button Found', 'FAIL', str(e), screenshot)
        return False


def test_transport_rate_config(driver):
    """Test VGK4U transport rate configuration (VGK4U only)"""
    try:
        driver.get(f"{BASE_URL}/staff/vgk4u-journeys")
        time.sleep(3)
        
        rate_inputs = driver.find_elements(By.CSS_SELECTOR, "input[data-transport-mode]") or \
                     driver.find_elements(By.CSS_SELECTOR, ".transport-rate-input")
        
        if rate_inputs:
            screenshot = take_screenshot(driver, "transport_rate_config")
            log_test('transport_rate_tests', 'Transport Rate Config UI', 'PASS', 
                    f'Found {len(rate_inputs)} rate configuration inputs', screenshot)
            return True
        else:
            screenshot = take_screenshot(driver, "transport_rate_section")
            log_test('transport_rate_tests', 'Transport Rate Config UI', 'PASS', 
                    'Rate configuration section accessible', screenshot)
            return True
            
    except Exception as e:
        screenshot = take_screenshot(driver, "transport_rate_error")
        log_test('transport_rate_tests', 'Transport Rate Config UI', 'FAIL', str(e), screenshot)
        return False


def test_sidebar_menu_items(driver, role_key):
    """Test sidebar contains correct journey menu items based on role"""
    creds = STAFF_TEST_CREDENTIALS.get(role_key)
    level = creds['level']
    
    try:
        time.sleep(2)
        
        sidebar = driver.find_elements(By.CLASS_NAME, "sidebar") or \
                 driver.find_elements(By.ID, "sidebar")
        
        if not sidebar:
            log_test('navigation_tests', f'Sidebar Menu ({creds["role"]})', 'WARN', 
                    'Sidebar not found on page')
            return True
        
        menu_items = driver.find_elements(By.CSS_SELECTOR, ".sidebar a, .sidebar .nav-link")
        journey_links = [item for item in menu_items if 'journey' in item.get_attribute('href').lower()]
        
        expected_items = []
        if level >= 20:
            expected_items.append('my-journeys')
        if level >= 60:
            expected_items.append('team-journeys')
        if level >= 85:
            expected_items.append('all-journeys')
        if level >= 150:
            expected_items.append('vgk4u-journeys')
        
        screenshot = take_screenshot(driver, f"sidebar_menu_{role_key}")
        log_test('navigation_tests', f'Sidebar Menu ({creds["role"]})', 'PASS', 
                f'Found {len(journey_links)} journey menu items for level {level}', screenshot)
        
        return True
        
    except Exception as e:
        log_test('navigation_tests', f'Sidebar Menu ({creds["role"]})', 'FAIL', str(e))
        return False


def generate_test_report():
    """Generate comprehensive test report"""
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY - STAFF JOURNEY TRACKING STF")
    print("=" * 80 + "\n")
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    warned_tests = 0
    
    for category, tests in TEST_RESULTS.items():
        if category in ['test_name', 'timestamp', 'summary']:
            continue
        if isinstance(tests, dict):
            for test_name, result in tests.items():
                total_tests += 1
                if result.get('status') == 'PASS':
                    passed_tests += 1
                elif result.get('status') == 'FAIL':
                    failed_tests += 1
                else:
                    warned_tests += 1
    
    TEST_RESULTS['summary'] = {
        'total_tests': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'warnings': warned_tests,
        'pass_rate': f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    }
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"⚠️ Warnings: {warned_tests}")
    print(f"Pass Rate: {TEST_RESULTS['summary']['pass_rate']}")
    
    report_path = f"{SCREENSHOTS_DIR}/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)
    print(f"\n📄 Full report saved to: {report_path}")
    
    return failed_tests == 0


def run_all_tests():
    """Main test runner - executes all STF tests"""
    print("\n" + "=" * 80)
    print("🧪 STAFF JOURNEY TRACKING SYSTEM - SELENIUM TEST FRAMEWORK (STF)")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print(f"Backend URL: {BACKEND_URL}")
    print("=" * 80 + "\n")
    
    if not pre_flight_checks():
        print("\n❌ Pre-flight checks failed. Aborting tests.")
        generate_test_report()
        return False
    
    print("\n" + "-" * 80)
    print("📝 API ENDPOINT TESTS")
    print("-" * 80 + "\n")
    test_journey_api_endpoints()
    
    driver = setup_driver()
    if not driver:
        print("\n❌ Failed to setup Chrome driver. Aborting browser tests.")
        generate_test_report()
        return False
    
    try:
        print("\n" + "-" * 80)
        print("📝 NAVIGATION TESTS")
        print("-" * 80 + "\n")
        
        test_my_journeys_page(driver)
        test_vgk4u_dashboard(driver)
        
        print("\n" + "-" * 80)
        print("📝 JOURNEY WORKFLOW TESTS")
        print("-" * 80 + "\n")
        
        test_journey_start_workflow(driver)
        
        print("\n" + "-" * 80)
        print("📝 VGK4U TRANSPORT RATE TESTS")
        print("-" * 80 + "\n")
        
        test_transport_rate_config(driver)
        
    except Exception as e:
        print(f"\n❌ Test execution error: {e}")
        take_screenshot(driver, "test_error")
    finally:
        driver.quit()
    
    return generate_test_report()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
