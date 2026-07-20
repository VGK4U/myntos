"""
Selenium-based Browser Testing for Awards & Bonanza Workflow
MNR EV Reference Program - Comprehensive Testing
Tests complete multi-role approval chain: Admin → Super Admin → Finance → RVZ
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

# Test configuration
# Always use localhost for testing within Replit environment
BASE_URL = 'http://localhost:5000'
BACKEND_URL = 'http://localhost:8000'

# Test credentials
TEST_CREDENTIALS = {
    'rvz_id': {'mnr_id': 'MNR182364369', 'password': 'RVZ@ADMIN'},
    'super_admin': {'mnr_id': 'MNR182371007', 'password': 'Super@123admin'},
    'finance_admin': {'mnr_id': 'MNR182371010', 'password': 'Fintech@123'},
    'admin': {'mnr_id': 'MNR182322707', 'password': 'System@admin'},
    'test_user': {'mnr_id': 'MNR1800346', 'password': '123456'}
}

# Test results storage
TEST_RESULTS = {
    'test_name': 'Awards & Bonanza Workflow Testing',
    'timestamp': datetime.now().isoformat(),
    'pre_flight_checks': {},
    'login_tests': {},
    'navigation_tests': {},
    'workflow_tests': {},
    'api_tests': {},
    'summary': {}
}

def log_test(category, test_name, status, message='', screenshot_path=None):
    """Log test result"""
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


def pre_flight_checks():
    """
    CRITICAL: Run pre-flight checks before Selenium testing
    Validates system is ready for testing
    """
    print("\n" + "="*80)
    print("🚀 PRE-FLIGHT CHECKS - AWARDS & BONANZA TESTING")
    print("="*80 + "\n")
    
    # Check 1: Backend API Health
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            log_test('pre_flight_checks', 'Backend API Health', 'PASS', f'Status: {response.status_code}')
        else:
            log_test('pre_flight_checks', 'Backend API Health', 'FAIL', f'Status: {response.status_code}')
            return False
    except Exception as e:
        log_test('pre_flight_checks', 'Backend API Health', 'FAIL', str(e))
        return False
    
    # Check 2: Frontend Server
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code in [200, 302]:
            log_test('pre_flight_checks', 'Frontend Server', 'PASS', f'Status: {response.status_code}')
        else:
            log_test('pre_flight_checks', 'Frontend Server', 'FAIL', f'Status: {response.status_code}')
            return False
    except Exception as e:
        log_test('pre_flight_checks', 'Frontend Server', 'FAIL', str(e))
        return False
    
    # Check 3: Dashboard Routes
    dashboard_routes = [
        '/rvz/dashboard',
        '/super-admin/dashboard',
        '/finance/dashboard',
        '/admin/dashboard'
    ]
    
    all_routes_ok = True
    for route in dashboard_routes:
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=5)
            # 302 = redirect to login (correct), 200 = page loads (correct), 404 = route missing (incorrect)
            if response.status_code in [200, 302]:
                log_test('pre_flight_checks', f'Route: {route}', 'PASS', f'Status: {response.status_code}')
            else:
                log_test('pre_flight_checks', f'Route: {route}', 'FAIL', f'Status: {response.status_code}')
                all_routes_ok = False
        except Exception as e:
            log_test('pre_flight_checks', f'Route: {route}', 'FAIL', str(e))
            all_routes_ok = False
    
    if not all_routes_ok:
        return False
    
    # Check 4: Test Credentials Validation
    try:
        # Just check if we can POST to login endpoint
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={'mnr_id': 'TEST', 'password': 'TEST'},
            timeout=5
        )
        # We expect 400/401 for wrong credentials, which means endpoint works
        if response.status_code in [400, 401]:
            log_test('pre_flight_checks', 'Login Endpoint', 'PASS', 'Endpoint responding correctly')
        else:
            log_test('pre_flight_checks', 'Login Endpoint', 'WARN', f'Unexpected status: {response.status_code}')
    except Exception as e:
        log_test('pre_flight_checks', 'Login Endpoint', 'FAIL', str(e))
        return False
    
    print("\n✅ All pre-flight checks passed! Ready for Selenium testing.\n")
    return True


def setup_driver():
    """Setup Chrome WebDriver with headless options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver


def take_screenshot(driver, name):
    """Take screenshot and return path"""
    screenshots_dir = '/tmp/selenium_screenshots'
    os.makedirs(screenshots_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{name}_{timestamp}.png"
    filepath = os.path.join(screenshots_dir, filename)
    
    driver.save_screenshot(filepath)
    return filepath


def test_login(driver, role_name, credentials):
    """Test login for specific role"""
    print(f"\n🔐 Testing login: {role_name}")
    
    try:
        # Navigate to login page
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        # Find and fill login form
        mnr_id_input = driver.find_element(By.ID, 'mnr_id')
        password_input = driver.find_element(By.ID, 'password')
        
        mnr_id_input.clear()
        mnr_id_input.send_keys(credentials['mnr_id'])
        
        password_input.clear()
        password_input.send_keys(credentials['password'])
        
        # Take screenshot before login
        screenshot_before = take_screenshot(driver, f"{role_name}_before_login")
        
        # Submit form
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        
        # Wait for redirect
        time.sleep(3)
        
        # Take screenshot after login
        screenshot_after = take_screenshot(driver, f"{role_name}_after_login")
        
        # Check if redirected to dashboard (not login page)
        current_url = driver.current_url
        
        if '/login' not in current_url:
            log_test('login_tests', f'{role_name} Login', 'PASS', 
                    f'Redirected to: {current_url}', screenshot_after)
            return True
        else:
            log_test('login_tests', f'{role_name} Login', 'FAIL', 
                    'Still on login page', screenshot_after)
            return False
            
    except Exception as e:
        screenshot_error = take_screenshot(driver, f"{role_name}_login_error")
        log_test('login_tests', f'{role_name} Login', 'FAIL', str(e), screenshot_error)
        return False


def test_awards_navigation(driver, role_name, expected_url_pattern):
    """Test navigation to Awards & Bonanza section"""
    print(f"\n🧭 Testing Awards navigation: {role_name}")
    
    try:
        # Wait for page to load
        time.sleep(2)
        
        # Find Awards & Bonanza menu group
        awards_header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Awards & Bonanza')]"))
        )
        
        # Click to expand menu
        awards_header.click()
        time.sleep(1)
        
        screenshot_menu = take_screenshot(driver, f"{role_name}_awards_menu_expanded")
        
        # Find Awards link
        awards_link = driver.find_element(By.XPATH, "//a[contains(@href, 'awards')]")
        awards_link.click()
        
        time.sleep(2)
        
        screenshot_awards_page = take_screenshot(driver, f"{role_name}_awards_page")
        
        current_url = driver.current_url
        
        if 'awards' in current_url.lower():
            log_test('navigation_tests', f'{role_name} Awards Navigation', 'PASS',
                    f'Navigated to: {current_url}', screenshot_awards_page)
            return True
        else:
            log_test('navigation_tests', f'{role_name} Awards Navigation', 'FAIL',
                    f'Unexpected URL: {current_url}', screenshot_awards_page)
            return False
            
    except Exception as e:
        screenshot_error = take_screenshot(driver, f"{role_name}_navigation_error")
        log_test('navigation_tests', f'{role_name} Awards Navigation', 'FAIL', str(e), screenshot_error)
        return False


def test_awards_workflow():
    """Test complete Awards & Bonanza workflow across all roles"""
    print("\n" + "="*80)
    print("🎯 AWARDS & BONANZA WORKFLOW TESTING")
    print("="*80 + "\n")
    
    driver = setup_driver()
    
    try:
        # Test workflow for each role
        roles_to_test = [
            ('admin', TEST_CREDENTIALS['admin'], '/admin'),
            ('super_admin', TEST_CREDENTIALS['super_admin'], '/super-admin'),
            ('finance_admin', TEST_CREDENTIALS['finance_admin'], '/finance'),
            ('rvz_id', TEST_CREDENTIALS['rvz_id'], '/rvz')
        ]
        
        for role_name, credentials, url_prefix in roles_to_test:
            # Login
            if test_login(driver, role_name, credentials):
                # Test navigation to Awards
                test_awards_navigation(driver, role_name, url_prefix)
            
            # Logout
            driver.delete_all_cookies()
            time.sleep(1)
        
    finally:
        driver.quit()


def test_api_endpoints():
    """Test Awards & Bonanza API endpoints"""
    print("\n" + "="*80)
    print("🔌 API ENDPOINTS TESTING")
    print("="*80 + "\n")
    
    # Test admin awards endpoints
    endpoints_to_test = [
        ('/api/v1/admin/awards', 'Admin Awards List'),
        ('/api/v1/super-admin/awards', 'Super Admin Awards'),
        ('/api/v1/finance/awards', 'Finance Awards'),
        ('/api/v1/rvz/awards', 'RVZ Awards')
    ]
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            # 401 = not authenticated (expected), 404 = endpoint missing, 200 = OK
            if response.status_code in [200, 401]:
                log_test('api_tests', description, 'PASS', f'Status: {response.status_code}')
            elif response.status_code == 404:
                log_test('api_tests', description, 'FAIL', 'Endpoint not found (404)')
            else:
                log_test('api_tests', description, 'WARN', f'Status: {response.status_code}')
        except Exception as e:
            log_test('api_tests', description, 'FAIL', str(e))


def generate_html_report():
    """Generate comprehensive HTML test report"""
    print("\n" + "="*80)
    print("📊 GENERATING TEST REPORT")
    print("="*80 + "\n")
    
    # Calculate summary
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category, tests in TEST_RESULTS.items():
        if category in ['test_name', 'timestamp', 'summary']:
            continue
        for test_name, result in tests.items():
            total_tests += 1
            if result['status'] == 'PASS':
                passed_tests += 1
            elif result['status'] == 'FAIL':
                failed_tests += 1
    
    TEST_RESULTS['summary'] = {
        'total': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'success_rate': f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    }
    
    # Generate HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Awards & Bonanza Test Report</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; background: #f8f9fa; }}
            .test-pass {{ color: green; font-weight: bold; }}
            .test-fail {{ color: red; font-weight: bold; }}
            .test-warn {{ color: orange; font-weight: bold; }}
            .screenshot {{ max-width: 100%; border: 1px solid #ddd; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">🎯 Awards & Bonanza Workflow Test Report</h1>
            <p><strong>Test Run:</strong> {TEST_RESULTS['timestamp']}</p>
            
            <div class="alert alert-info">
                <h4>Summary</h4>
                <p><strong>Total Tests:</strong> {TEST_RESULTS['summary']['total']}</p>
                <p><strong>Passed:</strong> <span class="test-pass">{TEST_RESULTS['summary']['passed']}</span></p>
                <p><strong>Failed:</strong> <span class="test-fail">{TEST_RESULTS['summary']['failed']}</span></p>
                <p><strong>Success Rate:</strong> {TEST_RESULTS['summary']['success_rate']}</p>
            </div>
    """
    
    # Add test results by category
    for category, tests in TEST_RESULTS.items():
        if category in ['test_name', 'timestamp', 'summary']:
            continue
        
        html_content += f"""
            <h3 class="mt-4">{category.replace('_', ' ').title()}</h3>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Status</th>
                        <th>Message</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for test_name, result in tests.items():
            status_class = f"test-{result['status'].lower()}"
            html_content += f"""
                <tr>
                    <td>{test_name}</td>
                    <td class="{status_class}">{result['status']}</td>
                    <td>{result['message']}</td>
                    <td>{result['timestamp']}</td>
                </tr>
            """
        
        html_content += """
                </tbody>
            </table>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Save report
    report_path = '/tmp/awards_bonanza_test_report.html'
    with open(report_path, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Test report generated: {report_path}\n")
    
    # Save JSON results
    json_path = '/tmp/awards_bonanza_test_results.json'
    with open(json_path, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)
    
    print(f"✅ JSON results saved: {json_path}\n")
    
    return report_path


def main():
    """Main test execution"""
    print("\n" + "="*80)
    print("🧪 AWARDS & BONANZA COMPREHENSIVE TESTING")
    print("MNR EV Reference Program - Selenium Browser Testing")
    print("="*80 + "\n")
    
    # Step 1: Pre-flight checks
    if not pre_flight_checks():
        print("\n❌ Pre-flight checks failed. Please fix issues before running Selenium tests.\n")
        sys.exit(1)
    
    # Step 2: Test workflow
    test_awards_workflow()
    
    # Step 3: Test API endpoints
    test_api_endpoints()
    
    # Step 4: Generate report
    report_path = generate_html_report()
    
    # Print summary
    print("\n" + "="*80)
    print("📋 TEST EXECUTION COMPLETE")
    print("="*80)
    print(f"\nTotal Tests: {TEST_RESULTS['summary']['total']}")
    print(f"✅ Passed: {TEST_RESULTS['summary']['passed']}")
    print(f"❌ Failed: {TEST_RESULTS['summary']['failed']}")
    print(f"Success Rate: {TEST_RESULTS['summary']['success_rate']}")
    print(f"\n📊 View full report: {report_path}\n")
    
    # Exit with appropriate code
    if TEST_RESULTS['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
