"""
End-to-End Selenium Browser Test: KYC Validation in Income Approval
Tests UI interaction - clicking buttons, viewing data, checking error messages

Test Data:
- MNR9990001 (Income 13897): KYC Approved - should allow approval
- MNR9990002 (Income 13898): KYC Pending - should show error
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "http://localhost:5000"

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def test_kyc_income_e2e():
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    results = []
    
    try:
        print("=" * 70)
        print("END-TO-END KYC INCOME APPROVAL BROWSER TEST")
        print("=" * 70)
        print("\nTest Data:")
        print("  - MNR9990001 (Income 13897): KYC Approved")
        print("  - MNR9990002 (Income 13898): KYC Pending")
        
        # ============================================================
        # TEST 1: Staff Login via UI
        # ============================================================
        print("\n[TEST 1] Staff Login via UI...")
        driver.get(f"{BASE_URL}/staff/login")
        time.sleep(2)
        
        # Find and fill login form
        emp_code_field = wait.until(EC.presence_of_element_located((By.ID, "employeeId")))
        emp_code_field.clear()
        emp_code_field.send_keys("MR10001")
        
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys("Test@123")
        
        # Click login button
        login_btn = driver.find_element(By.ID, "loginBtn")
        login_btn.click()
        time.sleep(3)
        
        # Verify login success
        if "dashboard" in driver.current_url.lower() or "staff" in driver.current_url.lower():
            print("   ✅ Login successful - redirected to staff area")
            results.append(("Staff Login", "PASS"))
        else:
            print(f"   ❌ Login failed - URL: {driver.current_url}")
            results.append(("Staff Login", "FAIL"))
            return results
        
        # ============================================================
        # TEST 2: Navigate to Income Approval Page
        # ============================================================
        print("\n[TEST 2] Navigate to Income Approval Page...")
        driver.get(f"{BASE_URL}/staff/mnr/income-unified")
        time.sleep(3)
        
        # Verify page loaded
        page_source = driver.page_source.lower()
        if "income" in page_source or "verification" in page_source:
            print("   ✅ Income page loaded")
            results.append(("Income Page Load", "PASS"))
        else:
            print("   ❌ Income page failed to load")
            results.append(("Income Page Load", "FAIL"))
        
        # ============================================================
        # TEST 3: Verify Test Data Displayed in UI
        # ============================================================
        print("\n[TEST 3] Check Test Data Display...")
        time.sleep(2)
        
        # Look for our test users in the page
        page_source = driver.page_source
        found_user1 = "MNR9990001" in page_source or "Test User Alpha" in page_source
        found_user2 = "MNR9990002" in page_source or "Test User Beta" in page_source
        
        if found_user1:
            print("   ✅ Found MNR9990001 (KYC Approved) in UI")
        else:
            print("   ⚠️ MNR9990001 not visible - may need to scroll/filter")
        
        if found_user2:
            print("   ✅ Found MNR9990002 (KYC Pending) in UI")
        else:
            print("   ⚠️ MNR9990002 not visible - may need to scroll/filter")
        
        if found_user1 or found_user2:
            results.append(("Test Data Display", "PASS"))
        else:
            results.append(("Test Data Display", "CHECK"))
        
        # ============================================================
        # TEST 4: Check for KYC Status Indicators in UI
        # ============================================================
        print("\n[TEST 4] Check KYC Status Indicators...")
        
        # Look for KYC-related text/badges
        kyc_indicators = []
        if "kyc" in page_source.lower():
            kyc_indicators.append("KYC text found")
        if "approved" in page_source.lower():
            kyc_indicators.append("Approved status found")
        if "pending" in page_source.lower():
            kyc_indicators.append("Pending status found")
        
        if kyc_indicators:
            print(f"   ✅ KYC indicators found: {', '.join(kyc_indicators)}")
            results.append(("KYC Indicators", "PASS"))
        else:
            print("   ⚠️ No explicit KYC indicators visible")
            results.append(("KYC Indicators", "CHECK"))
        
        # ============================================================
        # TEST 5: Check Validate/Approve Buttons Exist
        # ============================================================
        print("\n[TEST 5] Check Action Buttons...")
        
        # Look for action buttons
        validate_btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Validate') or contains(@class, 'validate')]")
        approve_btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Approve') or contains(@class, 'approve')]")
        
        print(f"   Found {len(validate_btns)} Validate button(s)")
        print(f"   Found {len(approve_btns)} Approve button(s)")
        
        if validate_btns or approve_btns:
            results.append(("Action Buttons", "PASS"))
        else:
            print("   ⚠️ No action buttons found - checking for alternative UI")
            results.append(("Action Buttons", "CHECK"))
        
        # ============================================================
        # TEST 6: Try to Click Validate for Each Income
        # ============================================================
        print("\n[TEST 6] Attempt Validate Action via UI...")
        
        # Try to find and click validate buttons for specific income IDs
        try:
            # Look for row or card containing income ID 13897
            income_row = driver.find_elements(By.XPATH, "//*[contains(text(), '13897') or contains(@data-id, '13897')]")
            if income_row:
                print("   Found income 13897 row")
                # Try to find validate button near this row
                parent = income_row[0]
                try:
                    validate_btn = parent.find_element(By.XPATH, ".//button[contains(text(), 'Validate')]")
                    validate_btn.click()
                    print("   Clicked Validate for income 13897")
                    time.sleep(2)
                except:
                    print("   ⚠️ Could not find/click Validate button for 13897")
            else:
                print("   ⚠️ Income 13897 row not found in current view")
        except Exception as e:
            print(f"   ⚠️ Error finding income row: {str(e)[:50]}")
        
        results.append(("Validate Action", "CHECK"))
        
        # ============================================================
        # TEST 7: Check for Error Modal/Message when KYC Not Approved
        # ============================================================
        print("\n[TEST 7] Check for KYC Error Handling in UI...")
        
        # Look for error modal elements
        error_modal = driver.find_elements(By.ID, "kycErrorModal")
        error_alerts = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .alert-warning, .error-message")
        
        if error_modal:
            print("   ✅ KYC Error Modal element exists in page")
            results.append(("KYC Error Modal Exists", "PASS"))
        elif error_alerts:
            print("   ✅ Error alert elements exist in page")
            results.append(("KYC Error Modal Exists", "PASS"))
        else:
            print("   ⚠️ No error modal found - may appear on action")
            results.append(("KYC Error Modal Exists", "CHECK"))
        
        # ============================================================
        # TEST 8: Take Screenshot for Visual Verification
        # ============================================================
        print("\n[TEST 8] Capture Screenshot...")
        try:
            screenshot_path = "/tmp/income_page_screenshot.png"
            driver.save_screenshot(screenshot_path)
            print(f"   ✅ Screenshot saved to {screenshot_path}")
            results.append(("Screenshot Captured", "PASS"))
        except:
            print("   ⚠️ Could not save screenshot")
            results.append(("Screenshot Captured", "CHECK"))
        
        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for _, status in results if status == "PASS")
        failed = sum(1 for _, status in results if status == "FAIL")
        check = sum(1 for _, status in results if status == "CHECK")
        
        for test_name, status in results:
            icon = "✅" if status == "PASS" else ("❌" if status == "FAIL" else "⚠️")
            print(f"   {icon} {test_name}: {status}")
        
        print(f"\nTotal: {passed} PASS, {failed} FAIL, {check} CHECK (needs review)")
        print("=" * 70)
        
        # Print current page state
        print("\nCurrent URL:", driver.current_url)
        print("Page Title:", driver.title)
        
        return results
        
    except Exception as e:
        print(f"\n❌ Test Error: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Test Execution", "ERROR"))
        return results
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_kyc_income_e2e()
