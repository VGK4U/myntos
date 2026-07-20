#!/usr/bin/env python3
"""
KYC Activation - End-to-End Selenium Test (ST Protocol)
========================================================
Tests complete user workflow from login to KYC data persistence
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_USER_ID = "BEV1800143"
TEST_PASSWORD = "test123"
TEST_AADHAAR = "123456789012"
TEST_PAN = "ABCDE1234F"

class KYCE2ETest:
    def __init__(self):
        self.driver = None
        self.test_results = []
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with headless options"""
        print("\n🚀 INITIALIZING SELENIUM WEBDRIVER")
        print("=" * 70)
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            print("✅ WebDriver initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize WebDriver: {str(e)}")
            return False
    
    def log_step(self, step_num, description, status, details=""):
        """Log test step with status"""
        status_icon = "✅" if status else "❌"
        result = {
            "step": step_num,
            "description": description,
            "status": status,
            "details": details
        }
        self.test_results.append(result)
        
        print(f"\n{status_icon} STEP {step_num}: {description}")
        if details:
            print(f"   {details}")
    
    def test_step_1_login(self):
        """Step 1: Navigate to login page and authenticate"""
        try:
            print(f"\n📋 Navigating to: {BASE_URL}")
            self.driver.get(BASE_URL)
            time.sleep(2)
            
            # Check if we're on login page
            current_url = self.driver.current_url
            print(f"   Current URL: {current_url}")
            
            # Find and fill login form
            bev_id_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "bevId"))
            )
            password_input = self.driver.find_element(By.ID, "password")
            
            print(f"   Entering BEV ID: {TEST_USER_ID}")
            bev_id_input.clear()
            bev_id_input.send_keys(TEST_USER_ID)
            
            print(f"   Entering Password: {'*' * len(TEST_PASSWORD)}")
            password_input.clear()
            password_input.send_keys(TEST_PASSWORD)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            print("   Clicking Sign In button...")
            login_button.click()
            
            # Wait for redirect (either to dashboard or user-home)
            time.sleep(3)
            current_url = self.driver.current_url
            
            if "dashboard" in current_url or "user-home" in current_url:
                self.log_step(1, "Login", True, f"Successfully logged in, redirected to: {current_url}")
                return True
            else:
                self.log_step(1, "Login", False, f"Failed to redirect after login. Current URL: {current_url}")
                return False
                
        except TimeoutException as e:
            self.log_step(1, "Login", False, f"Timeout finding login elements: {str(e)}")
            return False
        except Exception as e:
            self.log_step(1, "Login", False, f"Error during login: {str(e)}")
            return False
    
    def test_step_2_navigate_to_kyc(self):
        """Step 2: Navigate to Profile Edit KYC section"""
        try:
            kyc_url = f"{BASE_URL}/profile-edit?section=kyc"
            print(f"\n📋 Navigating to KYC form: {kyc_url}")
            self.driver.get(kyc_url)
            time.sleep(2)
            
            # Wait for KYC form to load
            aadhaar_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "kycAadhaar"))
            )
            pan_input = self.driver.find_element(By.ID, "kycPan")
            
            # Check if fields are empty (cleared for test)
            aadhaar_value = aadhaar_input.get_attribute("value") or ""
            pan_value = pan_input.get_attribute("value") or ""
            
            print(f"   Aadhaar field value: '{aadhaar_value}' (expected: empty)")
            print(f"   PAN field value: '{pan_value}' (expected: empty)")
            
            self.log_step(2, "Navigate to KYC Form", True, 
                         f"KYC form loaded successfully, fields ready for input")
            return True
            
        except TimeoutException:
            self.log_step(2, "Navigate to KYC Form", False, "Timeout loading KYC form fields")
            return False
        except Exception as e:
            self.log_step(2, "Navigate to KYC Form", False, f"Error: {str(e)}")
            return False
    
    def test_step_3_fill_kyc_data(self):
        """Step 3: Fill in Aadhaar and PAN numbers"""
        try:
            print(f"\n📋 Filling KYC data...")
            
            aadhaar_input = self.driver.find_element(By.ID, "kycAadhaar")
            pan_input = self.driver.find_element(By.ID, "kycPan")
            
            print(f"   Entering Aadhaar: {TEST_AADHAAR}")
            aadhaar_input.clear()
            aadhaar_input.send_keys(TEST_AADHAAR)
            
            print(f"   Entering PAN: {TEST_PAN}")
            pan_input.clear()
            pan_input.send_keys(TEST_PAN)
            
            # Verify values were entered
            aadhaar_value = aadhaar_input.get_attribute("value")
            pan_value = pan_input.get_attribute("value")
            
            if aadhaar_value == TEST_AADHAAR and pan_value == TEST_PAN:
                self.log_step(3, "Fill KYC Data", True, 
                             f"Aadhaar: {aadhaar_value}, PAN: {pan_value}")
                return True
            else:
                self.log_step(3, "Fill KYC Data", False, 
                             f"Values mismatch - Aadhaar: {aadhaar_value}, PAN: {pan_value}")
                return False
                
        except Exception as e:
            self.log_step(3, "Fill KYC Data", False, f"Error: {str(e)}")
            return False
    
    def test_step_4_submit_form(self):
        """Step 4: Submit KYC form and wait for success message"""
        try:
            print(f"\n📋 Submitting KYC form...")
            
            # Find and click save button
            save_button = self.driver.find_element(By.ID, "saveKYCBtn")
            print("   Clicking Save Changes button...")
            save_button.click()
            
            # Wait for success message alert
            time.sleep(2)
            
            try:
                alert_div = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success, .alert"))
                )
                alert_text = alert_div.text
                print(f"   Success message: {alert_text}")
                
                if "successfully" in alert_text.lower():
                    self.log_step(4, "Submit Form", True, f"Success message: {alert_text}")
                    return True
                else:
                    self.log_step(4, "Submit Form", False, f"Unexpected message: {alert_text}")
                    return False
                    
            except TimeoutException:
                # Check for error messages
                try:
                    error_div = self.driver.find_element(By.CSS_SELECTOR, ".alert-danger")
                    error_text = error_div.text
                    self.log_step(4, "Submit Form", False, f"Error message: {error_text}")
                    return False
                except:
                    self.log_step(4, "Submit Form", False, "No success or error message found")
                    return False
                    
        except Exception as e:
            self.log_step(4, "Submit Form", False, f"Error: {str(e)}")
            return False
    
    def test_step_5_verify_redirect(self):
        """Step 5: Verify automatic redirect to /profile-view"""
        try:
            print(f"\n📋 Waiting for redirect to /profile-view...")
            
            # Wait up to 5 seconds for redirect
            WebDriverWait(self.driver, 5).until(
                EC.url_contains("/profile-view")
            )
            
            current_url = self.driver.current_url
            print(f"   Current URL: {current_url}")
            
            if "/profile-view" in current_url:
                self.log_step(5, "Redirect to Profile View", True, 
                             f"Successfully redirected to: {current_url}")
                return True
            else:
                self.log_step(5, "Redirect to Profile View", False, 
                             f"Did not redirect. Current URL: {current_url}")
                return False
                
        except TimeoutException:
            current_url = self.driver.current_url
            self.log_step(5, "Redirect to Profile View", False, 
                         f"Timeout waiting for redirect. Still at: {current_url}")
            return False
        except Exception as e:
            self.log_step(5, "Redirect to Profile View", False, f"Error: {str(e)}")
            return False
    
    def test_step_6_verify_data_display(self):
        """Step 6: Verify KYC data displays correctly on profile view"""
        try:
            print(f"\n📋 Verifying data display on profile view...")
            time.sleep(2)
            
            # Look for KYC data in the page
            page_source = self.driver.page_source
            
            aadhaar_displayed = TEST_AADHAAR in page_source
            pan_displayed = TEST_PAN in page_source
            
            print(f"   Searching for Aadhaar ({TEST_AADHAAR}): {'✅ FOUND' if aadhaar_displayed else '❌ NOT FOUND'}")
            print(f"   Searching for PAN ({TEST_PAN}): {'✅ FOUND' if pan_displayed else '❌ NOT FOUND'}")
            
            if aadhaar_displayed and pan_displayed:
                self.log_step(6, "Verify Data Display", True, 
                             f"Both Aadhaar and PAN displayed correctly")
                return True
            else:
                missing = []
                if not aadhaar_displayed:
                    missing.append("Aadhaar")
                if not pan_displayed:
                    missing.append("PAN")
                
                self.log_step(6, "Verify Data Display", False, 
                             f"Missing: {', '.join(missing)}")
                return False
                
        except Exception as e:
            self.log_step(6, "Verify Data Display", False, f"Error: {str(e)}")
            return False
    
    def test_step_7_verify_persistence(self):
        """Step 7: Hard refresh and verify data persists (DC Protocol)"""
        try:
            print(f"\n📋 Testing data persistence with hard refresh...")
            
            # Hard refresh the page
            print("   Executing hard refresh (Ctrl+Shift+R equivalent)...")
            self.driver.refresh()
            time.sleep(3)
            
            # Re-check for data
            page_source = self.driver.page_source
            
            aadhaar_persisted = TEST_AADHAAR in page_source
            pan_persisted = TEST_PAN in page_source
            
            print(f"   After refresh - Aadhaar: {'✅ PERSISTED' if aadhaar_persisted else '❌ LOST'}")
            print(f"   After refresh - PAN: {'✅ PERSISTED' if pan_persisted else '❌ LOST'}")
            
            if aadhaar_persisted and pan_persisted:
                self.log_step(7, "Verify Persistence (DC Protocol)", True, 
                             "Data persisted after hard refresh - DC Protocol PASS")
                return True
            else:
                self.log_step(7, "Verify Persistence (DC Protocol)", False, 
                             "Data rolled back after refresh - DC Protocol FAIL")
                return False
                
        except Exception as e:
            self.log_step(7, "Verify Persistence (DC Protocol)", False, f"Error: {str(e)}")
            return False
    
    def test_step_8_database_verification(self):
        """Step 8: Verify data in database"""
        try:
            print(f"\n📋 Verifying data in database...")
            
            # Import database modules
            sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
            from app.core.database import SessionLocal
            from app.models.user import User
            
            db = SessionLocal()
            user = db.query(User).filter(User.id == TEST_USER_ID).first()
            
            if user:
                db_aadhaar = user.aadhaar_number
                db_pan = user.pan_number
                
                print(f"   Database Aadhaar: {db_aadhaar}")
                print(f"   Database PAN: {db_pan}")
                
                if db_aadhaar == TEST_AADHAAR and db_pan == TEST_PAN:
                    self.log_step(8, "Database Verification", True, 
                                 f"Database contains correct values: {db_aadhaar}, {db_pan}")
                    db.close()
                    return True
                else:
                    self.log_step(8, "Database Verification", False, 
                                 f"Database values mismatch: {db_aadhaar}, {db_pan}")
                    db.close()
                    return False
            else:
                self.log_step(8, "Database Verification", False, "User not found in database")
                db.close()
                return False
                
        except Exception as e:
            self.log_step(8, "Database Verification", False, f"Error: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in self.test_results if r["status"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status_icon = "✅" if result["status"] else "❌"
            print(f"{status_icon} Step {result['step']}: {result['description']}")
            if result["details"]:
                print(f"   └─ {result['details']}")
        
        print("\n" + "=" * 70)
        print(f"🎯 FINAL RESULT: {passed}/{total} steps passed")
        
        if passed == total:
            print("✅ ALL TESTS PASSED - KYC ACTIVATION WORKING CORRECTLY")
            print("✅ DC Protocol: Single source of truth maintained")
            print("✅ Frontend redirect fix verified")
            print("✅ Database persistence confirmed")
            return True
        else:
            print(f"❌ {total - passed} TEST(S) FAILED")
            return False
    
    def run_all_tests(self):
        """Execute complete test suite"""
        print("\n" + "=" * 70)
        print("🧪 KYC ACTIVATION - END-TO-END SELENIUM TEST (ST PROTOCOL)")
        print("=" * 70)
        print(f"Test User: {TEST_USER_ID}")
        print(f"Base URL: {BASE_URL}")
        print(f"Test Data: Aadhaar={TEST_AADHAAR}, PAN={TEST_PAN}")
        print("=" * 70)
        
        if not self.setup_driver():
            print("❌ Failed to initialize WebDriver. Test aborted.")
            return False
        
        try:
            # Run all test steps in sequence
            if not self.test_step_1_login():
                print("⚠️ Login failed - skipping remaining tests")
                return False
            
            if not self.test_step_2_navigate_to_kyc():
                print("⚠️ Navigation failed - skipping remaining tests")
                return False
            
            if not self.test_step_3_fill_kyc_data():
                print("⚠️ Data entry failed - skipping remaining tests")
                return False
            
            if not self.test_step_4_submit_form():
                print("⚠️ Form submission failed - skipping remaining tests")
                return False
            
            self.test_step_5_verify_redirect()  # Continue even if redirect fails
            self.test_step_6_verify_data_display()
            self.test_step_7_verify_persistence()
            self.test_step_8_database_verification()
            
            return self.print_summary()
            
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if self.driver:
                print("\n🔚 Closing WebDriver...")
                self.driver.quit()


if __name__ == "__main__":
    test = KYCE2ETest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
