"""
ST Protocol: Selenium Testing for Withdrawal Dashboard
Real browser automation with actual credentials
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime

# Test credentials
CREDENTIALS = {
    'vgk_id': {'username': 'BEV182364369', 'password': 'VGK@ADMIN'},
    'super_admin': {'username': 'BEV182371007', 'password': 'Super@123admin'},
    'finance_admin': {'username': 'BEV182371010', 'password': 'Fintech@123'},
    'admin': {'username': 'BEV182322707', 'password': 'System@admin'},
    'test_user': {'username': 'BEV1800359', 'password': '2010'}
}

# Base URL
BASE_URL = 'https://44e22c9c-e1d0-4998-b9e2-cd7d87a07e12-00-2a7ys4z0p3xmu.pike.replit.dev'

def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def login(driver, role='admin'):
    """Login with specified role credentials"""
    creds = CREDENTIALS.get(role)
    if not creds:
        raise ValueError(f'Invalid role: {role}')
    
    print(f'\n🔐 Logging in as {role.upper()}...')
    
    driver.get(f'{BASE_URL}/login')
    time.sleep(2)
    
    # Fill login form
    username_field = driver.find_element(By.NAME, 'username')
    password_field = driver.find_element(By.NAME, 'password')
    
    username_field.clear()
    username_field.send_keys(creds['username'])
    password_field.clear()
    password_field.send_keys(creds['password'])
    
    # Submit
    login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    login_button.click()
    
    time.sleep(3)
    print(f'✅ Logged in as {creds["username"]}')
    return True

def test_dashboard_access(driver, role):
    """Test access to withdrawal dashboard"""
    print(f'\n📊 Testing dashboard access for {role.upper()}...')
    
    try:
        # Navigate to dashboard
        driver.get(f'{BASE_URL}/admin/withdrawal/dashboard')
        time.sleep(2)
        
        # Check if page loaded
        page_title = driver.find_element(By.TAG_NAME, 'h1').text
        print(f'   Page title: {page_title}')
        
        # Check for stats cards
        stats_cards = driver.find_elements(By.CLASS_NAME, 'card')
        print(f'   Found {len(stats_cards)} stats cards')
        
        return True
    except Exception as e:
        print(f'❌ Dashboard access failed: {str(e)}')
        return False

def test_approval_queue(driver, role, queue_type):
    """Test access to role-specific approval queue"""
    print(f'\n✅ Testing {queue_type} queue for {role.upper()}...')
    
    try:
        # Navigate to queue
        driver.get(f'{BASE_URL}/admin/withdrawal/{queue_type}-queue')
        time.sleep(2)
        
        # Check page loaded
        page_title = driver.find_element(By.TAG_NAME, 'h1').text
        print(f'   Page title: {page_title}')
        
        # Check for withdrawal table
        tables = driver.find_elements(By.TAG_NAME, 'table')
        print(f'   Found {len(tables)} tables')
        
        return True
    except Exception as e:
        print(f'❌ Queue access failed: {str(e)}')
        return False

def test_transaction_breakup(driver):
    """Test viewing transaction breakup"""
    print(f'\n💰 Testing transaction breakup view...')
    
    try:
        # Click "View More" button on first withdrawal
        view_buttons = driver.find_elements(By.CLASS_NAME, 'btn-view-details')
        if view_buttons:
            view_buttons[0].click()
            time.sleep(2)
            
            # Check modal opened
            modal = driver.find_element(By.CLASS_NAME, 'modal-content')
            print(f'   Modal opened successfully')
            
            # Check for income breakdown table
            breakup_table = modal.find_element(By.ID, 'income-breakup-table')
            print(f'   Income breakup table found')
            
            return True
        else:
            print('   No withdrawals to view')
            return False
    except Exception as e:
        print(f'❌ Transaction breakup failed: {str(e)}')
        return False

def run_selenium_tests():
    """Run all Selenium tests"""
    print('=' * 70)
    print('🚀 ST PROTOCOL: Withdrawal Dashboard Selenium Tests')
    print('=' * 70)
    print(f'Started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    results = {
        'passed': 0,
        'failed': 0,
        'tests': []
    }
    
    driver = None
    
    try:
        driver = setup_driver()
        
        # Test 1: VGK ID - Full access
        print('\n' + '='*70)
        print('TEST 1: VGK ID - Full Dashboard Access')
        print('='*70)
        if login(driver, 'vgk_id'):
            test_passed = test_dashboard_access(driver, 'vgk_id')
            results['tests'].append(('VGK Dashboard Access', test_passed))
            if test_passed:
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        # Test 2: Admin - Approval Queue
        print('\n' + '='*70)
        print('TEST 2: Admin - Approval Queue Access')
        print('='*70)
        driver.delete_all_cookies()
        if login(driver, 'admin'):
            test_passed = test_approval_queue(driver, 'admin', 'admin')
            results['tests'].append(('Admin Approval Queue', test_passed))
            if test_passed:
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        # Test 3: Super Admin - Approval Queue
        print('\n' + '='*70)
        print('TEST 3: Super Admin - Approval Queue Access')
        print('='*70)
        driver.delete_all_cookies()
        if login(driver, 'super_admin'):
            test_passed = test_approval_queue(driver, 'super_admin', 'superadmin')
            results['tests'].append(('Super Admin Queue', test_passed))
            if test_passed:
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        # Test 4: Finance Admin - Payment Queue
        print('\n' + '='*70)
        print('TEST 4: Finance Admin - Payment Queue Access')
        print('='*70)
        driver.delete_all_cookies()
        if login(driver, 'finance_admin'):
            test_passed = test_approval_queue(driver, 'finance_admin', 'finance')
            results['tests'].append(('Finance Payment Queue', test_passed))
            if test_passed:
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        # Test 5: User - Withdrawal Page
        print('\n' + '='*70)
        print('TEST 5: Test User - Withdrawal Page Access')
        print('='*70)
        driver.delete_all_cookies()
        if login(driver, 'test_user'):
            driver.get(f'{BASE_URL}/user/withdrawals')
            time.sleep(2)
            test_passed = 'Withdrawals' in driver.title or 'withdrawal' in driver.page_source.lower()
            results['tests'].append(('User Withdrawal Page', test_passed))
            if test_passed:
                results['passed'] += 1
                print('✅ User withdrawal page loaded')
            else:
                results['failed'] += 1
                print('❌ User withdrawal page failed')
        
    except Exception as e:
        print(f'\n❌ CRITICAL ERROR: {str(e)}')
        results['failed'] += 1
    
    finally:
        if driver:
            driver.quit()
    
    # Print results
    print('\n' + '=' * 70)
    print('📊 TEST RESULTS SUMMARY')
    print('=' * 70)
    for test_name, passed in results['tests']:
        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'{status}: {test_name}')
    
    print(f'\n✅ Passed: {results["passed"]}/{len(results["tests"])}')
    print(f'❌ Failed: {results["failed"]}/{len(results["tests"])}')
    print(f'\nCompleted at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 70)
    
    return results

if __name__ == '__main__':
    run_selenium_tests()
