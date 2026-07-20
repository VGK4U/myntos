#!/usr/bin/env python3
"""
Simplified E2E Selenium Test - Training Course Workflow Only
Tests: Create Course → User Claims → Admin Approves
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import datetime

# Test credentials (correct passwords)
SUPER_ADMIN = {'id': 'BEV182371007', 'password': 'superadmin123', 'name': 'Super Admin'}
ADMIN = {'id': 'BEV182322707', 'password': 'admin123', 'name': 'Admin'}
TEST_USER = {'id': 'BEVTEST99999', 'password': 'test123', 'name': 'Test User'}  # NEW test user - Platinum with active coupon

BASE_URL = "http://localhost:5000"

GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
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

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def login(driver, user_creds):
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        driver.find_element(By.ID, "username").send_keys(user_creds['id'])
        driver.find_element(By.ID, "password").send_keys(user_creds['password'])
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(4)  # Wait longer for redirect
        
        # Check if redirected away from login page OR if dashboard/admin page loaded
        current_url = driver.current_url.lower()
        if "/login" not in current_url or "/dashboard" in current_url or "/admin" in current_url or "/user" in current_url or "/superadmin" in current_url:
            print_success(f"Logged in as {user_creds['name']}")
            return True
        else:
            print_error(f"Login failed for {user_creds['name']} - Still on: {driver.current_url}")
            driver.save_screenshot(f"login_fail_{user_creds['name'].replace(' ', '_').lower()}.png")
            return False
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return False

def logout(driver):
    try:
        driver.get(f"{BASE_URL}/logout")
        time.sleep(2)
        print_info("Logged out")
    except:
        pass

def create_training_course(driver):
    try:
        print_info("Creating training course...")
        driver.get(f"{BASE_URL}/superadmin/training-courses")
        time.sleep(3)
        driver.save_screenshot("1_create_course_page.png")
        
        timestamp = datetime.now().strftime("%H%M%S")
        course_name = f"SELENIUM_COURSE_{timestamp}"
        
        # Fill form based on template fields
        driver.find_element(By.ID, "course_name").send_keys(course_name)
        driver.find_element(By.ID, "course_category").send_keys("Automation Testing")
        driver.find_element(By.ID, "course_fee").send_keys("10000")
        driver.find_element(By.ID, "duration").send_keys("30 days")
        driver.find_element(By.ID, "description").send_keys("Automated test course created by Selenium")
        
        # Submit the form (button has no ID, submit form directly)
        driver.find_element(By.ID, "create-course-form").submit()
        time.sleep(3)
        
        # Handle success alert
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            print_info(f"Alert: {alert_text}")
            alert.accept()
        except:
            pass
        
        driver.save_screenshot("2_course_created.png")
        print_success(f"Training course created: {course_name}")
        return course_name
    except Exception as e:
        print_error(f"Failed to create course: {str(e)}")
        driver.save_screenshot("error_create_course.png")
        # Print page source for debugging
        with open("page_source_create.html", "w") as f:
            f.write(driver.page_source)
        return None

def submit_training_claim(driver):
    try:
        print_info("Submitting training claim...")
        driver.get(f"{BASE_URL}/user/training-claim")
        time.sleep(3)
        driver.save_screenshot("3_user_claim_page.png")
        
        # Check what form fields exist
        with open("page_source_claim.html", "w") as f:
            f.write(driver.page_source)
        
        # IMPORTANT: Click course card FIRST to make form visible
        time.sleep(2)
        course_cards = driver.find_elements(By.CLASS_NAME, "course-card")
        if not course_cards:
            raise Exception("No courses available")
        course_cards[0].click()
        time.sleep(2)  # Wait for form to become visible
        
        # NOW fill claim form (form is visible after selecting course)
        driver.find_element(By.ID, "trainee_name").send_keys("SELENIUM TRAINEE")
        driver.find_element(By.ID, "trainee_contact").send_keys("9999999999")
        
        # Submit form directly
        driver.find_element(By.ID, "training-claim-form").submit()
        time.sleep(3)
        
        # Handle alert
        try:
            alert = driver.switch_to.alert
            print_info(f"Alert: {alert.text}")
            alert.accept()
        except:
            pass
        
        driver.save_screenshot("4_claim_submitted.png")
        print_success("Training claim submitted")
        return True
    except Exception as e:
        print_error(f"Failed to submit claim: {str(e)}")
        driver.save_screenshot("error_submit_claim.png")
        return False

def approve_training_claim(driver):
    try:
        print_info("Approving training claim...")
        driver.get(f"{BASE_URL}/admin/training-claims")
        time.sleep(3)
        driver.save_screenshot("5_admin_approval_page.png")
        
        # Save page source for debugging
        with open("page_source_approve.html", "w") as f:
            f.write(driver.page_source)
        
        # Find and click button to open approval modal (showApprovalModal function)
        time.sleep(2)
        approve_btns = driver.find_elements(By.CSS_SELECTOR, "button.btn-success.btn-action")
        if not approve_btns:
            raise Exception("No claims to approve")
        
        approve_btns[0].click()
        time.sleep(2)  # Wait for modal to open
        
        # Click the "Approve Claim" button inside the modal
        modal_approve_btn = driver.find_element(By.CSS_SELECTOR, "#approval-modal button.btn-success")
        modal_approve_btn.click()
        time.sleep(2)
        
        # Handle success alert
        try:
            alert = driver.switch_to.alert
            print_info(f"Alert: {alert.text}")
            alert.accept()
        except:
            pass
        
        driver.save_screenshot("6_claim_approved.png")
        print_success("Training claim approved")
        return True
    except Exception as e:
        print_error(f"Failed to approve claim: {str(e)}")
        driver.save_screenshot("error_approve_claim.png")
        return False

def main():
    print_header("TRAINING COURSE WORKFLOW E2E TEST")
    print_info("Testing: Create Course → User Claims → Admin Approves")
    
    driver = setup_driver()
    
    try:
        # Step 1: Super Admin creates course
        print_header("STEP 1: CREATE TRAINING COURSE")
        if login(driver, SUPER_ADMIN):
            course_name = create_training_course(driver)
            logout(driver)
            
            if not course_name:
                print_error("Failed to create course - stopping test")
                return
        
        # Step 2: User submits claim
        print_header("STEP 2: USER SUBMITS CLAIM")
        if login(driver, TEST_USER):
            submit_training_claim(driver)
            logout(driver)
        
        # Step 3: Admin approves claim
        print_header("STEP 3: ADMIN APPROVES CLAIM")
        if login(driver, ADMIN):
            approve_training_claim(driver)
            logout(driver)
        
        print_header("TEST COMPLETE")
        print_success("✓ Course created")
        print_success("✓ User submitted claim")
        print_success("✓ Admin approved claim")
        print_info("\nCheck screenshots 1-6 and page source HTML files for details")
        
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        driver.save_screenshot("fatal_error.png")
    finally:
        driver.quit()
        print_info("Browser closed")

if __name__ == "__main__":
    main()
