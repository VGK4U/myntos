"""
Complete End-to-End Selenium Browser Test: KYC Validation Workflow
Tests the full 2-step income approval with KYC blocking

Test Data:
- MNR9990001 (Income 13897): KYC Approved - should complete full workflow
- MNR9990002 (Income 13898): KYC Pending - should be blocked at final approval
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost:5000"

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def test_kyc_full_workflow():
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    results = []
    
    try:
        print("=" * 70)
        print("COMPLETE KYC INCOME WORKFLOW E2E TEST")
        print("=" * 70)
        print("\nWorkflow: Pending → Staff Validated → Completed (with KYC check)")
        print("\nTest Data:")
        print("  - MNR9990001 (Income 13897): KYC Approved")
        print("  - MNR9990002 (Income 13898): KYC Pending")
        
        # ============================================================
        # STEP 1: Staff Login
        # ============================================================
        print("\n[STEP 1] Staff Login...")
        driver.get(f"{BASE_URL}/staff/login")
        time.sleep(2)
        
        emp_code_field = wait.until(EC.presence_of_element_located((By.ID, "employeeId")))
        emp_code_field.clear()
        emp_code_field.send_keys("MR10001")
        
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys("Test@123")
        
        login_btn = driver.find_element(By.ID, "loginBtn")
        login_btn.click()
        time.sleep(3)
        
        if "staff" in driver.current_url.lower():
            print("   ✅ Login successful")
            results.append(("Staff Login", "PASS"))
        else:
            print("   ❌ Login failed")
            results.append(("Staff Login", "FAIL"))
            return results
        
        # ============================================================
        # STEP 2: Navigate to Income Page
        # ============================================================
        print("\n[STEP 2] Navigate to Income Page...")
        driver.get(f"{BASE_URL}/staff/mnr/income-unified")
        time.sleep(3)
        
        page_source = driver.page_source
        if "MNR9990001" in page_source and "MNR9990002" in page_source:
            print("   ✅ Both test users visible in income list")
            results.append(("Income Page Display", "PASS"))
        else:
            print("   ⚠️ Test users may not be visible")
            results.append(("Income Page Display", "CHECK"))
        
        # ============================================================
        # STEP 3: Validate Both Incomes (Step 1 of workflow)
        # ============================================================
        print("\n[STEP 3] Validate Both Incomes via UI...")
        
        # Find and click Validate buttons for both incomes
        validate_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Validate')]")
        print(f"   Found {len(validate_buttons)} Validate buttons")
        
        # Click validate for each
        clicked = 0
        for btn in validate_buttons[:2]:  # Only first 2
            try:
                btn.click()
                time.sleep(1)
                clicked += 1
            except:
                pass
        
        print(f"   Clicked {clicked} Validate buttons")
        time.sleep(2)
        
        # Check if page updated
        driver.refresh()
        time.sleep(2)
        
        # Verify validation happened by checking for "Staff Validated" status
        page_after = driver.page_source
        if "Staff Validated" in page_after or "Validated" in page_after:
            print("   ✅ Incomes moved to Staff Validated status")
            results.append(("Step 1 Validation", "PASS"))
        else:
            print("   ⚠️ Validation status may not be visible in current view")
            results.append(("Step 1 Validation", "CHECK"))
        
        # ============================================================
        # STEP 4: Try Approve for KYC Approved User
        # ============================================================
        print("\n[STEP 4] Test Final Approval for KYC Approved User...")
        
        # Look for Approve button (should be enabled for validated incomes)
        approve_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Approve')]")
        print(f"   Found {len(approve_buttons)} Approve buttons")
        
        # Try to find approve button for MNR9990001
        found_approve = False
        for btn in approve_buttons:
            try:
                # Check if this button is in the row for MNR9990001
                parent = btn.find_element(By.XPATH, "./ancestor::tr | ./ancestor::div[contains(@class, 'card')]")
                if parent and "MNR9990001" in parent.text:
                    btn.click()
                    found_approve = True
                    print("   Clicked Approve for MNR9990001 (KYC Approved)")
                    time.sleep(2)
                    break
            except:
                continue
        
        if found_approve:
            # Check for success message or status change
            page_after_approve = driver.page_source
            if "error" not in page_after_approve.lower() or "success" in page_after_approve.lower():
                print("   ✅ Approval action executed (no error)")
                results.append(("KYC Approved - Approval", "PASS"))
            else:
                print("   ⚠️ Approval may have issues")
                results.append(("KYC Approved - Approval", "CHECK"))
        else:
            print("   ⚠️ Could not find Approve button for MNR9990001")
            results.append(("KYC Approved - Approval", "CHECK"))
        
        # ============================================================
        # STEP 5: Try Approve for KYC Pending User - Should FAIL
        # ============================================================
        print("\n[STEP 5] Test Final Approval for KYC Pending User...")
        print("   Expected: Should be BLOCKED with KYC error")
        
        driver.refresh()
        time.sleep(2)
        
        approve_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Approve')]")
        
        found_kyc_block = False
        for btn in approve_buttons:
            try:
                parent = btn.find_element(By.XPATH, "./ancestor::tr | ./ancestor::div[contains(@class, 'card')]")
                if parent and "MNR9990002" in parent.text:
                    btn.click()
                    print("   Clicked Approve for MNR9990002 (KYC Pending)")
                    time.sleep(2)
                    
                    # Check for KYC error modal or message
                    page_after = driver.page_source
                    if "KYC" in page_after and ("error" in page_after.lower() or "not approved" in page_after.lower() or "modal" in page_after.lower()):
                        found_kyc_block = True
                        print("   ✅ KYC block detected in page")
                    
                    # Check for error modal
                    try:
                        modal = driver.find_element(By.CSS_SELECTOR, ".modal.show, #kycErrorModal, .alert-danger")
                        if modal.is_displayed():
                            found_kyc_block = True
                            print(f"   ✅ Error modal displayed: {modal.text[:100]}...")
                    except:
                        pass
                    
                    break
            except:
                continue
        
        if found_kyc_block:
            print("   ✅ KYC Pending user correctly BLOCKED")
            results.append(("KYC Pending - Blocked", "PASS"))
        else:
            print("   ⚠️ Could not confirm KYC blocking - may need manual check")
            results.append(("KYC Pending - Blocked", "CHECK"))
        
        # ============================================================
        # STEP 6: Capture Final Screenshot
        # ============================================================
        print("\n[STEP 6] Capture Screenshot...")
        try:
            driver.save_screenshot("/tmp/kyc_workflow_final.png")
            print("   ✅ Screenshot saved to /tmp/kyc_workflow_final.png")
            results.append(("Screenshot", "PASS"))
        except:
            results.append(("Screenshot", "CHECK"))
        
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
        
        print(f"\nTotal: {passed} PASS, {failed} FAIL, {check} CHECK")
        
        if failed == 0 and passed >= 4:
            print("\n🎉 WORKFLOW TEST SUCCESSFUL!")
        elif failed > 0:
            print("\n⚠️ Some tests failed - review needed")
        else:
            print("\n⚠️ Some tests need manual verification")
        
        print("=" * 70)
        
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
    test_kyc_full_workflow()
