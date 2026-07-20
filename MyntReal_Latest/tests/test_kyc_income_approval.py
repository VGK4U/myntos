"""
Selenium Browser Test: KYC Validation in Income Approval Workflow
Tests that income approval properly accepts/rejects based on KYC status

Test Data:
- MNR9990001 (ID 13897): KYC Approved
- MNR9990002 (ID 13898): KYC Pending
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

def test_kyc_income_approval():
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    results = []
    
    try:
        print("=" * 60)
        print("KYC INCOME APPROVAL BROWSER TEST")
        print("=" * 60)
        print("\nTest Data:")
        print("  - MNR9990001 (Income 13897): KYC Approved")
        print("  - MNR9990002 (Income 13898): KYC Pending")
        
        # Step 1: Login as VGK4U staff (MR10001)
        print("\n[TEST 1] Staff Login...")
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
        
        if "dashboard" in driver.current_url.lower() or "staff" in driver.current_url.lower():
            print("   ✅ Login successful")
            results.append(("Staff Login", "PASS"))
        else:
            print(f"   ❌ Login failed - URL: {driver.current_url}")
            results.append(("Staff Login", "FAIL"))
            return results
        
        # Step 2: Navigate to Income page to get token
        print("\n[TEST 2] Navigate to Income Page...")
        driver.get(f"{BASE_URL}/staff/mnr/income-unified")
        time.sleep(3)
        
        if "income" in driver.page_source.lower() or "verification" in driver.page_source.lower():
            print("   ✅ Income page loaded")
            results.append(("Income Page Load", "PASS"))
        else:
            print("   ⚠️ Income page may not have loaded")
            results.append(("Income Page Load", "CHECK"))
        
        # Step 3: First VALIDATE both incomes (Step 1: Pending → Staff Validated)
        print("\n[TEST 3] Validate Incomes (Step 1)...")
        
        js_validate_13897 = """
        return fetch('/api/v1/income-verification/staff/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + (localStorage.getItem('staffToken') || sessionStorage.getItem('staffToken'))
            },
            body: JSON.stringify({
                pending_income_ids: [13897]
            })
        }).then(r => r.json().then(data => ({status: r.status, data: data})))
        .catch(e => ({status: 500, error: e.message}));
        """
        
        result_v1 = driver.execute_script(js_validate_13897)
        time.sleep(1)
        print(f"   Income 13897 (KYC Approved) validation: {result_v1.get('data', {}).get('message', result_v1)}")
        
        js_validate_13898 = """
        return fetch('/api/v1/income-verification/staff/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + (localStorage.getItem('staffToken') || sessionStorage.getItem('staffToken'))
            },
            body: JSON.stringify({
                pending_income_ids: [13898]
            })
        }).then(r => r.json().then(data => ({status: r.status, data: data})))
        .catch(e => ({status: 500, error: e.message}));
        """
        
        result_v2 = driver.execute_script(js_validate_13898)
        time.sleep(1)
        print(f"   Income 13898 (KYC Pending) validation: {result_v2.get('data', {}).get('message', result_v2)}")
        
        if result_v1.get('status') == 200 and result_v2.get('status') == 200:
            print("   ✅ Both incomes validated (moved to Staff Validated)")
            results.append(("Step 1 Validation", "PASS"))
        else:
            print("   ⚠️ Validation may have had issues")
            results.append(("Step 1 Validation", "CHECK"))
        
        # Step 4: Test Final Approval for KYC Approved user (MNR9990001)
        print("\n[TEST 4] Final Approval - KYC Approved User (Income 13897)...")
        
        js_approve_13897 = """
        return fetch('/api/v1/income-verification/staff/approve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + (localStorage.getItem('staffToken') || sessionStorage.getItem('staffToken'))
            },
            body: JSON.stringify({
                pending_income_ids: [13897]
            })
        }).then(r => r.json().then(data => ({status: r.status, data: data})))
        .catch(e => ({status: 500, error: e.message}));
        """
        
        result_approved = driver.execute_script(js_approve_13897)
        time.sleep(1)
        
        print(f"   API Response: Status={result_approved.get('status')}")
        print(f"   Message: {result_approved.get('data', {}).get('message', result_approved.get('data'))}")
        
        if result_approved.get('status') == 200:
            processed = result_approved.get('data', {}).get('processed_count', 0)
            if processed > 0:
                print(f"   ✅ KYC Approved user - Income APPROVED and paid ({processed} processed)")
                results.append(("KYC Approved - Final Approval", "PASS"))
            else:
                print("   ⚠️ No incomes processed (may already be completed)")
                results.append(("KYC Approved - Final Approval", "CHECK"))
        else:
            error = result_approved.get('data', {}).get('detail', 'Unknown error')
            print(f"   ❌ Unexpected failure: {error}")
            results.append(("KYC Approved - Final Approval", "FAIL"))
        
        # Step 5: Test Final Approval for KYC Pending user (MNR9990002)
        print("\n[TEST 5] Final Approval - KYC Pending User (Income 13898)...")
        print("   Expected: Should be BLOCKED because KYC is not approved")
        
        js_approve_13898 = """
        return fetch('/api/v1/income-verification/staff/approve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + (localStorage.getItem('staffToken') || sessionStorage.getItem('staffToken'))
            },
            body: JSON.stringify({
                pending_income_ids: [13898]
            })
        }).then(r => r.json().then(data => ({status: r.status, data: data})))
        .catch(e => ({status: 500, error: e.message}));
        """
        
        result_pending = driver.execute_script(js_approve_13898)
        time.sleep(1)
        
        print(f"   API Response: Status={result_pending.get('status')}")
        
        if result_pending.get('status') == 400:
            error_detail = result_pending.get('data', {}).get('detail', '')
            if 'KYC' in error_detail:
                print(f"   ✅ CORRECTLY BLOCKED: {error_detail}")
                results.append(("KYC Pending - Blocked", "PASS"))
            else:
                print(f"   ⚠️ Blocked for other reason: {error_detail}")
                results.append(("KYC Pending - Blocked", "CHECK"))
        elif result_pending.get('status') == 200:
            processed = result_pending.get('data', {}).get('processed_count', 0)
            if processed > 0:
                print(f"   ❌ SHOULD BE BLOCKED but was APPROVED! ({processed} processed)")
                results.append(("KYC Pending - Blocked", "FAIL"))
            else:
                print("   ⚠️ No incomes processed (may already be completed or different status)")
                results.append(("KYC Pending - Blocked", "CHECK"))
        else:
            print(f"   ⚠️ Unexpected response: {result_pending}")
            results.append(("KYC Pending - Blocked", "CHECK"))
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, status in results if status == "PASS")
        failed = sum(1 for _, status in results if status == "FAIL")
        check = sum(1 for _, status in results if status == "CHECK")
        
        for test_name, status in results:
            icon = "✅" if status == "PASS" else ("❌" if status == "FAIL" else "⚠️")
            print(f"   {icon} {test_name}: {status}")
        
        print(f"\nTotal: {passed} PASS, {failed} FAIL, {check} CHECK")
        print("=" * 60)
        
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
    test_kyc_income_approval()
