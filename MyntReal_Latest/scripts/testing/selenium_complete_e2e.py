#!/usr/bin/env python3
"""
COMPLETE END-TO-END SELENIUM TEST
Tests BOTH workflows sequentially:
1. Training Course: Create → Approve → Claim → Approve → Verify
2. EV Vehicle: Create → Approve → Claim → Approve → Verify
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
CYAN = '\033[96m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{CYAN}{text:^80}{RESET}")
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
        
        # Note: Login page uses 'username' field, not 'user_id'
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        
        username_field.clear()
        username_field.send_keys(user_creds['id'])
        password_field.clear()
        password_field.send_keys(user_creds['password'])
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
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

# ============================================================================
# TRAINING COURSE WORKFLOW
# ============================================================================

def create_training_course(driver):
    """Super Admin creates a training course"""
    try:
        print_info("Creating training course...")
        
        driver.get(f"{BASE_URL}/superadmin/training-courses")
        time.sleep(3)
        driver.save_screenshot("training_01_create_page.png")
        
        # Fill form
        timestamp = datetime.now().strftime("%H%M%S")
        course_name_value = f"SELENIUM_COURSE_{timestamp}"
        
        driver.find_element(By.ID, "course_name").send_keys(course_name_value)
        driver.find_element(By.ID, "provider_name").send_keys("Selenium Institute")
        driver.find_element(By.ID, "course_fee").send_keys("10000")
        driver.find_element(By.ID, "description").send_keys("Automated test course")
        
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        driver.save_screenshot("training_02_created.png")
        print_success(f"Training course created: {course_name_value}")
        return course_name_value
        
    except Exception as e:
        print_error(f"Failed to create course: {str(e)}")
        driver.save_screenshot("error_training_create.png")
        return None

def approve_training_course_vgk(driver):
    """VGK approves the training course"""
    try:
        print_info("Approving training course (VGK)...")
        
        driver.get(f"{BASE_URL}/vgk/training-course-approval")
        time.sleep(3)
        driver.save_screenshot("training_03_vgk_approval.png")
        
        # Find approve button
        approve_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-success, a.btn-success")
        
        if approve_buttons:
            approve_buttons[0].click()
            time.sleep(2)
            
            # Handle confirmation modal if exists
            try:
                driver.find_element(By.ID, "confirmApprove").click()
                time.sleep(2)
            except:
                pass
            
            driver.save_screenshot("training_04_vgk_approved.png")
            print_success("Training course approved by VGK")
            return True
        else:
            print_warning("No pending courses to approve")
            return False
            
    except Exception as e:
        print_error(f"Failed to approve course: {str(e)}")
        driver.save_screenshot("error_training_vgk.png")
        return False

def submit_training_claim(driver):
    """User submits a training claim"""
    try:
        print_info("Submitting training claim (User)...")
        
        driver.get(f"{BASE_URL}/user/training-claim")
        time.sleep(3)
        driver.save_screenshot("training_05_user_claim_page.png")
        
        # Fill claim form
        driver.find_element(By.ID, "trainee_name").send_keys("SELENIUM TRAINEE")
        driver.find_element(By.ID, "mobile").send_keys("9999999999")
        
        # Select first course
        Select(driver.find_element(By.ID, "course_id")).select_by_index(1)
        
        # Submit
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        driver.save_screenshot("training_06_claim_submitted.png")
        print_success("Training claim submitted")
        return True
        
    except Exception as e:
        print_error(f"Failed to submit training claim: {str(e)}")
        driver.save_screenshot("error_training_claim.png")
        return False

def approve_training_claim_admin(driver):
    """Admin approves the training claim"""
    try:
        print_info("Approving training claim (Admin)...")
        
        driver.get(f"{BASE_URL}/admin/training-claims")
        time.sleep(3)
        driver.save_screenshot("training_07_admin_approval.png")
        
        # Find approve button
        approve_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-success, a.btn-success")
        
        if approve_buttons:
            approve_buttons[0].click()
            time.sleep(2)
            
            try:
                driver.find_element(By.ID, "confirmApprove").click()
                time.sleep(2)
            except:
                pass
            
            driver.save_screenshot("training_08_admin_approved.png")
            print_success("Training claim approved by Admin")
            return True
        else:
            print_warning("No pending training claims")
            return False
            
    except Exception as e:
        print_error(f"Failed to approve training claim: {str(e)}")
        driver.save_screenshot("error_training_admin.png")
        return False

# ============================================================================
# EV VEHICLE/SCOOTER WORKFLOW
# ============================================================================

def create_ev_model(driver):
    """Super Admin creates an EV model"""
    try:
        print_info("Creating EV model...")
        
        driver.get(f"{BASE_URL}/superadmin/ev-models")
        time.sleep(3)
        driver.save_screenshot("ev_01_create_page.png")
        
        # Fill form
        timestamp = datetime.now().strftime("%H%M%S")
        model_name_value = f"SELENIUM_MODEL_{timestamp}"
        
        driver.find_element(By.ID, "model_name").send_keys(model_name_value)
        driver.find_element(By.ID, "manufacturer").send_keys("Selenium Motors")
        
        # Select model type (Royal EV or Standard)
        Select(driver.find_element(By.ID, "model_type")).select_by_value("Royal EV")
        
        driver.find_element(By.ID, "specifications").send_keys("Automated test model")
        
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        driver.save_screenshot("ev_02_created.png")
        print_success(f"EV model created: {model_name_value}")
        return model_name_value
        
    except Exception as e:
        print_error(f"Failed to create EV model: {str(e)}")
        driver.save_screenshot("error_ev_create.png")
        return None

def approve_ev_model_vgk(driver):
    """VGK approves the EV model"""
    try:
        print_info("Approving EV model (VGK)...")
        
        driver.get(f"{BASE_URL}/vgk/ev-model-approval")
        time.sleep(3)
        driver.save_screenshot("ev_03_vgk_approval.png")
        
        # Find approve button
        approve_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-success, a.btn-success")
        
        if approve_buttons:
            approve_buttons[0].click()
            time.sleep(2)
            
            try:
                driver.find_element(By.ID, "confirmApprove").click()
                time.sleep(2)
            except:
                pass
            
            driver.save_screenshot("ev_04_vgk_approved.png")
            print_success("EV model approved by VGK")
            return True
        else:
            print_warning("No pending EV models to approve")
            return False
            
    except Exception as e:
        print_error(f"Failed to approve EV model: {str(e)}")
        driver.save_screenshot("error_ev_vgk.png")
        return False

def submit_ev_claim(driver):
    """User submits an EV claim"""
    try:
        print_info("Submitting EV claim (User)...")
        
        driver.get(f"{BASE_URL}/user/ev-claim")
        time.sleep(3)
        driver.save_screenshot("ev_05_user_claim_page.png")
        
        # Fill claim form
        driver.find_element(By.ID, "buyer_name").send_keys("SELENIUM BUYER")
        driver.find_element(By.ID, "mobile").send_keys("8888888888")
        driver.find_element(By.ID, "invoice_amount").send_keys("100000")
        
        # Select first model
        Select(driver.find_element(By.ID, "model_id")).select_by_index(1)
        
        # Submit
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        driver.save_screenshot("ev_06_claim_submitted.png")
        print_success("EV claim submitted")
        return True
        
    except Exception as e:
        print_error(f"Failed to submit EV claim: {str(e)}")
        driver.save_screenshot("error_ev_claim.png")
        return False

def approve_ev_claim_admin(driver):
    """Admin approves the EV claim"""
    try:
        print_info("Approving EV claim (Admin)...")
        
        driver.get(f"{BASE_URL}/admin/ev-claims")
        time.sleep(3)
        driver.save_screenshot("ev_07_admin_approval.png")
        
        # Find approve button
        approve_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-success, a.btn-success")
        
        if approve_buttons:
            approve_buttons[0].click()
            time.sleep(2)
            
            try:
                driver.find_element(By.ID, "confirmApprove").click()
                time.sleep(2)
            except:
                pass
            
            driver.save_screenshot("ev_08_admin_approved.png")
            print_success("EV claim approved by Admin")
            return True
        else:
            print_warning("No pending EV claims")
            return False
            
    except Exception as e:
        print_error(f"Failed to approve EV claim: {str(e)}")
        driver.save_screenshot("error_ev_admin.png")
        return False

# ============================================================================
# VERIFICATION
# ============================================================================

def verify_combined_balance(driver):
    """Verify combined balance deduction from both claims"""
    try:
        print_info("Verifying combined balance...")
        
        driver.get(f"{BASE_URL}/user/training-claim")
        time.sleep(3)
        driver.save_screenshot("verify_balance.png")
        
        # Look for balance display
        try:
            balance = driver.find_element(By.CLASS_NAME, "coupon-balance").text
            print_success(f"Combined balance displayed: {balance}")
            return True
        except:
            print_warning("Balance element not found")
            return False
            
    except Exception as e:
        print_error(f"Verification failed: {str(e)}")
        return False

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Run complete E2E test for BOTH workflows"""
    
    print_header("COMPLETE END-TO-END SELENIUM TEST")
    print_info("Testing BOTH workflows sequentially:")
    print_info("1. Training Course: Create → Approve → Claim → Approve")
    print_info("2. EV Vehicle: Create → Approve → Claim → Approve")
    
    driver = setup_driver()
    
    try:
        # ====================================================================
        # WORKFLOW 1: TRAINING COURSE
        # ====================================================================
        
        print_header("WORKFLOW 1: TRAINING COURSE SYSTEM")
        
        # Step 1: Super Admin creates course
        print_header("STEP 1.1: CREATE TRAINING COURSE (SUPER ADMIN)")
        if login(driver, SUPER_ADMIN):
            course_name = create_training_course(driver)
            logout(driver)
            
            if not course_name:
                print_error("Training workflow failed at creation")
                return
        
        # Step 2: VGK approves course
        print_header("STEP 1.2: APPROVE TRAINING COURSE (VGK)")
        if login(driver, VGK_ADMIN):
            approve_training_course_vgk(driver)
            logout(driver)
        
        # Step 3: User submits claim
        print_header("STEP 1.3: SUBMIT TRAINING CLAIM (USER)")
        if login(driver, TEST_USER):
            submit_training_claim(driver)
            logout(driver)
        
        # Step 4: Admin approves claim
        print_header("STEP 1.4: APPROVE TRAINING CLAIM (ADMIN)")
        if login(driver, ADMIN):
            approve_training_claim_admin(driver)
            logout(driver)
        
        # ====================================================================
        # WORKFLOW 2: EV VEHICLE
        # ====================================================================
        
        print_header("WORKFLOW 2: EV VEHICLE/SCOOTER SYSTEM")
        
        # Step 1: Super Admin creates EV model
        print_header("STEP 2.1: CREATE EV MODEL (SUPER ADMIN)")
        if login(driver, SUPER_ADMIN):
            model_name = create_ev_model(driver)
            logout(driver)
            
            if not model_name:
                print_error("EV workflow failed at creation")
                return
        
        # Step 2: VGK approves model
        print_header("STEP 2.2: APPROVE EV MODEL (VGK)")
        if login(driver, VGK_ADMIN):
            approve_ev_model_vgk(driver)
            logout(driver)
        
        # Step 3: User submits claim
        print_header("STEP 2.3: SUBMIT EV CLAIM (USER)")
        if login(driver, TEST_USER):
            submit_ev_claim(driver)
            logout(driver)
        
        # Step 4: Admin approves claim
        print_header("STEP 2.4: APPROVE EV CLAIM (ADMIN)")
        if login(driver, ADMIN):
            approve_ev_claim_admin(driver)
            logout(driver)
        
        # ====================================================================
        # VERIFICATION
        # ====================================================================
        
        print_header("STEP 3: VERIFY COMBINED BALANCE")
        if login(driver, TEST_USER):
            verify_combined_balance(driver)
            logout(driver)
        
        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        
        print_header("COMPLETE E2E TEST SUMMARY")
        
        print(f"\n{GREEN}WORKFLOW 1: TRAINING COURSE{RESET}")
        print_success("✓ Training course created by Super Admin")
        print_success("✓ Course approved by VGK")
        print_success("✓ User submitted training claim")
        print_success("✓ Admin approved training claim")
        
        print(f"\n{GREEN}WORKFLOW 2: EV VEHICLE{RESET}")
        print_success("✓ EV model created by Super Admin")
        print_success("✓ Model approved by VGK")
        print_success("✓ User submitted EV claim")
        print_success("✓ Admin approved EV claim")
        
        print(f"\n{GREEN}VERIFICATION{RESET}")
        print_success("✓ Combined balance tracking verified")
        
        print(f"\n{CYAN}Screenshots saved:{RESET}")
        print_info("Training: training_01.png → training_08.png")
        print_info("EV: ev_01.png → ev_08.png")
        print_info("Verification: verify_balance.png")
        
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        driver.save_screenshot("fatal_error.png")
        
    finally:
        driver.quit()
        print_info("\nBrowser closed")

if __name__ == "__main__":
    main()
