"""
Test Staff MNR Pages Integration
DC Protocol (Dec 28, 2025)
Tests all MNR pages accessible from Staff Portal
"""
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://127.0.0.1:5000"
STAFF_EMPLOYEE_ID = os.environ.get('TEST_STAFF_EMPLOYEE_ID', 'MR10001')
STAFF_PASSWORD = os.environ.get('TEST_STAFF_PASSWORD', 'password')

MNR_PAGES = [
    ('/staff/mnr/users', 'All Users'),
    ('/staff/mnr/user-status', 'User Status'),
    ('/staff/mnr/withdrawal/approvals', 'Withdrawal Approvals'),
    ('/staff/mnr/withdrawal/history', 'Withdrawal History'),
    ('/staff/mnr/kyc-management', 'KYC Management'),
    ('/staff/mnr/bank-pending', 'Bank Pending'),
    ('/staff/mnr/bank-all', 'All Bank Details'),
    ('/staff/mnr/announcements/view', 'Announcements'),
    ('/staff/mnr/feedback/pending', 'Pending Announcements'),
    ('/staff/mnr/announcement/create', 'Create Announcement'),
    ('/staff/mnr/banners-management', 'Banners'),
    ('/staff/mnr/popups', 'Popups'),
    ('/staff/mnr/pin-review', 'PIN Review'),
    ('/staff/mnr/password-reset', 'Password Reset'),
    ('/staff/mnr/reports', 'Reports'),
    ('/staff/mnr/emergency-wallet', 'Emergency Wallet'),
    ('/staff/accounts/expense-categories', 'Expense Categories'),
    ('/staff/mnr/log-reports', 'Log Reports'),
    ('/staff/mnr/tickets-management', 'Tickets Management'),
    ('/staff/mnr/tickets-assigned', 'Assigned Tickets'),
]

def setup_driver():
    """Setup Chrome WebDriver with headless options"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver

def login_staff(driver):
    """Login as staff user"""
    print(f"\n[LOGIN] Logging in as {STAFF_EMPLOYEE_ID}...")
    driver.get(f"{BASE_URL}/staff/login")
    time.sleep(2)
    
    try:
        employee_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "employee_id"))
        )
        employee_input.clear()
        employee_input.send_keys(STAFF_EMPLOYEE_ID)
        
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(STAFF_PASSWORD)
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(3)
        
        if '/staff/dashboard' in driver.current_url or '/staff/' in driver.current_url:
            print("[LOGIN] ✓ Staff login successful")
            return True
        else:
            print(f"[LOGIN] ✗ Login failed - current URL: {driver.current_url}")
            return False
    except Exception as e:
        print(f"[LOGIN] ✗ Error during login: {e}")
        return False

def test_mnr_page(driver, path, title):
    """Test a single MNR page"""
    url = f"{BASE_URL}{path}"
    print(f"\n[TEST] Testing: {title} ({path})")
    
    try:
        driver.get(url)
        time.sleep(2)
        
        errors = []
        
        if '/staff/login' in driver.current_url:
            errors.append("Redirected to login (auth failed)")
            return False, errors
        
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE' and 'favicon' not in log['message'].lower()]
        if js_errors:
            for err in js_errors[:3]:
                errors.append(f"JS Error: {err['message'][:100]}")
        
        page_source = driver.page_source.lower()
        if 'coming soon' in page_source:
            errors.append("Page shows 'Coming Soon'")
        
        if 'page not found' in page_source or '404' in driver.title.lower():
            errors.append("Page not found (404)")
        
        sidebar = driver.find_elements(By.ID, "staffSidebar")
        if not sidebar:
            errors.append("Staff sidebar not found")
        
        main_content = driver.find_elements(By.ID, "mainContent")
        if not main_content:
            errors.append("Main content container not found")
        
        if errors:
            print(f"[TEST] ✗ {title}: {'; '.join(errors)}")
            return False, errors
        else:
            print(f"[TEST] ✓ {title}: OK")
            return True, []
            
    except Exception as e:
        print(f"[TEST] ✗ {title}: Exception - {str(e)[:100]}")
        return False, [str(e)]

def main():
    """Main test runner"""
    print("=" * 60)
    print("Staff MNR Pages Integration Test")
    print("=" * 60)
    
    driver = setup_driver()
    results = {'passed': 0, 'failed': 0, 'errors': []}
    
    try:
        if not login_staff(driver):
            print("\n[FATAL] Cannot proceed without staff login")
            return
        
        for path, title in MNR_PAGES:
            passed, errors = test_mnr_page(driver, path, title)
            if passed:
                results['passed'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'page': title, 'path': path, 'errors': errors})
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed: {results['passed']}/{len(MNR_PAGES)}")
        print(f"Failed: {results['failed']}/{len(MNR_PAGES)}")
        
        if results['errors']:
            print("\nFailed Pages:")
            for err in results['errors']:
                print(f"  - {err['page']} ({err['path']})")
                for e in err['errors']:
                    print(f"      {e}")
        
    finally:
        driver.quit()
        print("\n[CLEANUP] Browser closed")

if __name__ == "__main__":
    main()
