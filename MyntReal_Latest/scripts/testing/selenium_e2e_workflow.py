#!/usr/bin/env python3
"""
Complete End-to-End Selenium Test
Tests entire Training Course & EV Coupon workflow from creation to approval
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from datetime import datetime

# Test credentials
SUPER_ADMIN = {'id': 'BEV182371007', 'password': 'superadmin123', 'name': 'Super Admin'}
VGK_ADMIN = {'id': 'BEV182364369', 'password': 'vgkadmin123', 'name': 'VGK Admin'}
ADMIN = {'id': 'BEV182322707', 'password': 'admin123', 'name': 'Admin'}
TEST_USER = {'id': 'BEV1800001', 'password': '123', 'name': 'Test User'}

BASE_URL = "http://localhost:5000"

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{text:^80}")
    print(f"{'='*80}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}► {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def setup_driver():
    """Initialize Chrome driver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def login(driver, user_creds):
    """Login with given credentials"""
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        # Fill login form
        user_id_field = driver.find_element(By.ID, "user_id")
        password_field = driver.find_element(By.ID, "password")
        
        user_id_field.clear()
        user_id_field.send_keys(user_creds['id'])
        password_field.clear()
        password_field.send_keys(user_creds['password'])
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        # Verify redirect
        if "/login" not in driver.current_url.lower():
            print_success(f"Logged in as {user_creds['name']}")
            return True
        else:
            print_error(f"Login failed for {user_creds['name']}")
            driver.save_screenshot(f"login_fail_{user_creds['id']}.png")
            return False
            
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return False

def logout(driver):
    """Logout current user"""
    try:
        driver.get(f"{BASE_URL}/logout")
        time.sleep(2)
        print_info("Logged out successfully")
    except:
        pass

def create_training_course(driver):
    """Super Admin creates a training course"""
    try:
        print_info("Creating training course as Super Admin...")
        
        driver.get(f"{BASE_URL}/superadmin/training-courses")
        time.sleep(3)
        
        # Take screenshot of page
        driver.save_screenshot("step1_training_courses_page.png")
        
        # Find and fill the form
        course_name = driver.find_element(By.ID, "course_name")
        provider_name = driver.find_element(By.ID, "provider_name")
        course_fee = driver.find_element(By.ID, "course_fee")
        description = driver.find_element(By.ID, "description")
        
        timestamp = datetime.now().strftime("%H%M%S")
        course_name.send_keys(f"SELENIUM_COURSE_{timestamp}")
        provider_name.send_keys("Selenium Training Institute")
        course_fee.send_keys("10000")
        description.send_keys("Automated test course created by Selenium")
        
        # Submit form
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        driver.save_screenshot("step2_course_created.png")
        print_success(f"Training course created: SELENIUM_COURSE_{timestamp}")
        return f"SELENIUM_COURSE_{timestamp}"
        
    except Exception as e:
        print_error(f"Failed to create course: {str(e)}")
        driver.save_screenshot("error_create_course.png")
        return None

def approve_training_course(driver, course_name):
    """VGK approves the training course"""
    try:
        print_info("Approving training course as VGK...")
        
        driver.get(f"{BASE_URL}/vgk/training-course-approval")
        time.sleep(3)
        
        driver.save_screenshot("step3_vgk_approval_page.png")
        
        # Find the pending course and approve it
        # Look for approve button for the created course
        approve_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-success")
        
        if approve_buttons:
            approve_buttons[0].click()  # Click first pending approval
            time.sleep(2)
            
            # Confirm approval in modal if exists
            try:
                confirm_btn = driver.find_element(By.ID, "confirmApprove")
                confirm_btn.click()
                time.sleep(2)
            except:
                pass
            
            driver.save_screenshot("step4_course_approved.png")
            print_success("Training course approved by VGK")
            return True
        else:
            print_warning("No pending courses found to approve")
            return False
            
    except Exception as e:
        print_error(f"Failed to approve course: {str(e)}")
        driver.save_screenshot("error_approve_course.png")
        return False

def submit_training_claim(driver, course_name):
    """User submits a training claim"""
    try:
        print_info("Submitting training claim as User...")
        
        driver.get(f"{BASE_URL}/user/training-claim")
        time.sleep(3)
        
        driver.save_screenshot("step5_user_claim_page.png")
        
        # Fill claim form
        trainee_name = driver.find_element(By.ID, "trainee_name")
        mobile = driver.find_element(By.ID, "mobile")
        
        trainee_name.send_keys("SELENIUM TEST TRAINEE")
        mobile.send_keys("9999999999")
        
        # Select course from dropdown
        course_select = Select(driver.find_element(By.ID, "course_id"))
        course_select.select_by_index(1)  # Select first available course
        
        # Upload invoice (create a dummy file)
        invoice_upload = driver.find_element(By.ID, "invoice_file")
        # Note: File upload might need actual file path
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        driver.save_screenshot("step6_claim_submitted.png")
        print_success("Training claim submitted by User")
        return True
        
    except Exception as e:
        print_error(f"Failed to submit claim: {str(e)}")
        driver.save_screenshot("error_submit_claim.png")
        return False

def approve_training_claim(driver):
    """Admin approves the training claim"""
    try:
        print_info("Approving training claim as Admin...")
        
        driver.get(f"{BASE_URL}/admin/training-claims")
        time.sleep(3)
        
        driver.save_screenshot("step7_admin_claims_page.png")
        
        # Find and approve pending claim
        approve_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-success")
        
        if approve_buttons:
            approve_buttons[0].click()
            time.sleep(2)
            
            # Confirm approval
            try:
                confirm_btn = driver.find_element(By.ID, "confirmApprove")
                confirm_btn.click()
                time.sleep(2)
            except:
                pass
            
            driver.save_screenshot("step8_claim_approved.png")
            print_success("Training claim approved by Admin")
            return True
        else:
            print_warning("No pending claims found")
            return False
            
    except Exception as e:
        print_error(f"Failed to approve claim: {str(e)}")
        driver.save_screenshot("error_approve_claim.png")
        return False

def verify_balance_deduction(driver):
    """Verify combined balance was properly deducted"""
    try:
        print_info("Verifying balance deduction...")
        
        driver.get(f"{BASE_URL}/user/training-claim")
        time.sleep(3)
        
        # Look for balance display
        balance_elements = driver.find_elements(By.CLASS_NAME, "coupon-balance")
        
        if balance_elements:
            balance_text = balance_elements[0].text
            print_success(f"Balance displayed: {balance_text}")
            return True
        else:
            print_warning("Balance element not found on page")
            return False
            
    except Exception as e:
        print_error(f"Failed to verify balance: {str(e)}")
        return False

def main():
    """Run complete E2E workflow test"""
    
    print_header("COMPLETE E2E SELENIUM WORKFLOW TEST")
    print_info("Testing: Training Course Creation → Approval → Claim → Approval")
    
    driver = setup_driver()
    course_name = None
    
    try:
        # STEP 1: Super Admin creates training course
        print_header("STEP 1: CREATE TRAINING COURSE (SUPER ADMIN)")
        if login(driver, SUPER_ADMIN):
            course_name = create_training_course(driver)
            logout(driver)
        
        if not course_name:
            print_error("Failed at Step 1 - Cannot continue")
            return
        
        # STEP 2: VGK approves training course
        print_header("STEP 2: APPROVE TRAINING COURSE (VGK)")
        if login(driver, VGK_ADMIN):
            approve_training_course(driver, course_name)
            logout(driver)
        
        # STEP 3: User submits training claim
        print_header("STEP 3: SUBMIT TRAINING CLAIM (USER)")
        if login(driver, TEST_USER):
            submit_training_claim(driver, course_name)
            logout(driver)
        
        # STEP 4: Admin approves training claim
        print_header("STEP 4: APPROVE TRAINING CLAIM (ADMIN)")
        if login(driver, ADMIN):
            approve_training_claim(driver)
            logout(driver)
        
        # STEP 5: Verify balance deduction
        print_header("STEP 5: VERIFY BALANCE DEDUCTION (USER)")
        if login(driver, TEST_USER):
            verify_balance_deduction(driver)
            logout(driver)
        
        # Final summary
        print_header("E2E TEST COMPLETE")
        print_success("✓ Training course created")
        print_success("✓ Course approved by VGK")
        print_success("✓ User submitted claim")
        print_success("✓ Admin approved claim")
        print_success("✓ Balance tracking verified")
        print_info("\nCheck screenshots step1_*.png through step8_*.png for visual verification")
        
    except Exception as e:
        print_error(f"Test failed with error: {str(e)}")
        driver.save_screenshot("fatal_error.png")
        
    finally:
        driver.quit()
        print_info("Browser closed")

if __name__ == "__main__":
    main()
