"""
ST Protocol: Real Browser Testing with Actual Admin Credentials
Tests all withdrawal dashboard pages with real logins
"""

import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

# Test credentials - REAL accounts
CREDENTIALS = {
    'vgk_id': {'username': 'BEV182364369', 'password': 'VGK@ADMIN', 'role': 'VGK ID'},
    'super_admin': {'username': 'BEV182371007', 'password': 'Super@123admin', 'role': 'Super Admin'},
    'finance_admin': {'username': 'BEV182371010', 'password': 'Fintech@123', 'role': 'Finance Admin'},
    'admin': {'username': 'BEV182322707', 'password': 'System@admin', 'role': 'Admin'}
}

# Frontend URL - Now proxies /admin/withdrawal/* to backend
# Single URL for everything (port 5000)
BASE_URL = 'http://localhost:5000'

def setup_driver():
    """Setup Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def login(driver, role):
    """Login with specified role"""
    creds = CREDENTIALS[role]
    print(f'\n🔐 Logging in as {role.upper()} ({creds["username"]})...')
    
    driver.get(f'{BASE_URL}/login')
    time.sleep(2)
    
    try:
        username_field = driver.find_element(By.NAME, 'username')
        password_field = driver.find_element(By.NAME, 'password')
        
        username_field.clear()
        username_field.send_keys(creds['username'])
        password_field.clear()
        password_field.send_keys(creds['password'])
        
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        
        time.sleep(3)
        
        # Verify login success
        if '/dashboard' in driver.current_url or '/admin' in driver.current_url:
            print(f'✅ Login successful as {creds["username"]}')
            return True
        else:
            print(f'❌ Login failed - Current URL: {driver.current_url}')
            return False
            
    except Exception as e:
        print(f'❌ Login error: {str(e)}')
        return False

def test_page_access(driver, url, page_name):
    """Test if a page loads successfully"""
    try:
        driver.get(url)
        time.sleep(2)
        
        # Check for error messages
        page_source = driver.page_source.lower()
        
        if '404' in page_source or 'not found' in page_source:
            print(f'   ❌ {page_name}: 404 Not Found')
            return False
        
        if '500' in page_source or 'internal server error' in page_source:
            print(f'   ❌ {page_name}: 500 Server Error')
            return False
        
        if 'error' in page_source and 'unexpected' in page_source:
            print(f'   ⚠️  {page_name}: Page loaded but contains errors')
            return False
        
        # Check if page has expected content
        if driver.find_elements(By.TAG_NAME, 'h1'):
            h1_text = driver.find_element(By.TAG_NAME, 'h1').text
            print(f'   ✅ {page_name}: Loaded successfully - "{h1_text}"')
            return True
        else:
            print(f'   ⚠️  {page_name}: Loaded but no H1 found')
            return True
            
    except Exception as e:
        print(f'   ❌ {page_name}: Error - {str(e)}')
        return False

def test_dashboard_navigation(driver, role):
    """Test all withdrawal dashboard pages for a specific role"""
    print(f'\n📊 Testing dashboard pages for {role.upper()}...')
    
    results = []
    
    # Test pages based on role
    pages_to_test = [
        (f'{BASE_URL}/admin/withdrawal/dashboard', 'Unified Dashboard'),
        (f'{BASE_URL}/admin/withdrawal/history', 'Withdrawal History')
    ]
    
    # Add role-specific pages
    if role in ['admin', 'vgk_id']:
        pages_to_test.append((f'{BASE_URL}/admin/withdrawal/admin-queue', 'Admin Approval Queue'))
    
    if role in ['super_admin', 'vgk_id']:
        pages_to_test.append((f'{BASE_URL}/admin/withdrawal/superadmin-queue', 'Super Admin Queue'))
    
    if role in ['finance_admin', 'vgk_id']:
        pages_to_test.append((f'{BASE_URL}/admin/withdrawal/finance-queue', 'Finance Payment Queue'))
        pages_to_test.append((f'{BASE_URL}/admin/withdrawal/batch-management', 'Batch Management'))
    
    # Test each page
    for url, page_name in pages_to_test:
        result = test_page_access(driver, url, page_name)
        results.append((page_name, result))
    
    return results

def run_comprehensive_tests():
    """Run all tests across all roles"""
    print('=' * 80)
    print('🚀 ST PROTOCOL: Comprehensive Withdrawal Dashboard Testing')
    print('   Testing with REAL admin credentials')
    print('=' * 80)
    print(f'Started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    all_results = {}
    driver = None
    
    try:
        driver = setup_driver()
        
        # Test each role
        for role in ['vgk_id', 'admin', 'super_admin', 'finance_admin']:
            print('\n' + '=' * 80)
            print(f'TESTING ROLE: {role.upper()}')
            print('=' * 80)
            
            # Clear cookies for fresh login
            driver.delete_all_cookies()
            
            # Login
            if not login(driver, role):
                print(f'❌ Login failed for {role}, skipping tests')
                all_results[role] = [('Login', False)]
                continue
            
            # Test dashboard pages
            results = test_dashboard_navigation(driver, role)
            all_results[role] = [('Login', True)] + results
        
    except Exception as e:
        print(f'\n❌ CRITICAL ERROR: {str(e)}')
    
    finally:
        if driver:
            driver.quit()
    
    # Print summary
    print('\n' + '=' * 80)
    print('📊 TEST RESULTS SUMMARY')
    print('=' * 80)
    
    total_tests = 0
    passed_tests = 0
    
    for role, results in all_results.items():
        print(f'\n{role.upper()}:')
        for test_name, passed in results:
            status = '✅ PASS' if passed else '❌ FAIL'
            print(f'  {status}: {test_name}')
            total_tests += 1
            if passed:
                passed_tests += 1
    
    print(f'\n📈 Overall: {passed_tests}/{total_tests} tests passed')
    print(f'   Pass rate: {(passed_tests/total_tests*100):.1f}%')
    print(f'\nCompleted at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 80)
    
    return all_results

if __name__ == '__main__':
    results = run_comprehensive_tests()
    
    # Exit with error code if any test failed
    failed = sum(1 for role_results in results.values() for _, passed in role_results if not passed)
    sys.exit(1 if failed > 0 else 0)
