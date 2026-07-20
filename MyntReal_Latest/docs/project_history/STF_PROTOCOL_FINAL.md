# STF PROTOCOL (Selenium Test Frontend) - FINAL VERSION
**"Automate Browser Testing with Real User Logins"**

---

## 🎯 CORE PRINCIPLE

**Use Selenium WebDriver to automatically test frontend user flows in a REAL browser with REAL login credentials when fixing frontend issues.**

**Purpose:** Catch frontend bugs before users report them. Validate complete user journeys automatically.

**Integration:** STF Protocol is used AFTER fixes are implemented (WVV Phase 5) to validate frontend works with real user sessions.

---

## 📋 TABLE OF CONTENTS

1. [STF Overview](#stf-overview)
2. [When to Use STF](#when-to-use-stf)
3. [STF vs FT Protocol](#stf-vs-ft-protocol)
4. [Test User Credentials](#test-user-credentials)
5. [STF Test Structure](#stf-test-structure)
6. [Step-by-Step Process](#step-by-step-process)
7. [Real-World Test Examples](#real-world-test-examples)
8. [Integration with WVV + FT + DC](#integration-with-wvv--ft--dc)
9. [Checklists](#checklists)

---

## 🔍 STF OVERVIEW

### **What It Means**

**Selenium Test Frontend (STF):** Automated browser testing using Selenium WebDriver to test complete user flows with REAL login credentials.

### **What STF Tests**

```
✅ Login/logout flows
✅ Form submissions (withdrawal, PIN activation, profile updates)
✅ Navigation between pages
✅ JavaScript interactions (dropdowns, modals, buttons)
✅ Session persistence
✅ Error handling (404, 403, validation errors)
✅ Role-based access control
✅ Data persistence after page refresh
✅ Cross-page workflows (multi-step processes)
```

### **What STF Does NOT Test**

```
❌ Backend API logic (use API tests)
❌ Database structure (use DC Protocol)
❌ Server performance (use load tests)
❌ Manual UI/UX review (use FT Protocol)
```

---

## 📋 WHEN TO USE STF

### **Primary Use Cases**

**1. After Fixing Frontend Issues (WVV Phase 5)**
```
User reports: "Withdrawal button doesn't work"
→ Fix issue with WVV Protocol
→ Run STF test to validate fix
→ Automated test prevents regression
```

**2. Testing Complete User Journeys**
```
Critical flows that must work:
- User login → Dashboard → Withdrawal → Logout
- Admin login → User management → Password reset
- Finance login → Withdrawal approval → Payment
```

**3. Regression Testing After Major Changes**
```
Changed authentication system?
→ Run STF login tests for all roles
→ Ensure nothing broke
```

**4. Before Marking Features Complete**
```
Built new feature: PIN activation
→ Write STF test for complete flow
→ Ensure it works end-to-end
→ Mark feature DONE
```

---

## 🔄 STF VS FT PROTOCOL

### **Key Differences**

| Aspect | STF Protocol | FT Protocol |
|--------|--------------|-------------|
| **Execution** | Automated script (Selenium) | Manual testing (human) |
| **Speed** | Fast (seconds) | Slow (minutes) |
| **Repeatability** | Perfect (same every time) | Variable (human error) |
| **Coverage** | Narrow (specific flows) | Wide (exploratory) |
| **Evidence** | Auto-screenshots on failure | Manual screenshots |
| **When to Use** | Regression, CI/CD, validation | Initial feature testing, UI review |
| **Human Judgment** | None (follows script) | Yes (can spot UI issues) |

### **When to Use Which**

**Use FT Protocol (Manual Testing):**
- ✅ First time testing a new feature
- ✅ Visual design review
- ✅ Exploratory testing (finding unknown issues)
- ✅ Complex user workflows with judgment calls
- ✅ Cross-device/browser manual verification

**Use STF Protocol (Automated Testing):**
- ✅ Validating fix after issue resolved
- ✅ Regression testing (ensure old features still work)
- ✅ Repeated testing of same flow
- ✅ CI/CD pipeline integration
- ✅ Testing multiple user roles quickly

**Best Practice: FT First, Then STF**
```
1. FT Protocol: Manually test new feature
2. Write STF test: Automate the validated flow
3. Run STF test: On every code change
4. Prevent regressions: STF catches breaks early
```

---

## 🔑 TEST USER CREDENTIALS

### **Admin Test Accounts**

**IMPORTANT: Use these REAL admin accounts for STF testing. DO NOT use in production automation.**

```python
# STF Test Credentials (Real Production Accounts)
# Use ONLY for testing in development/staging environments

STF_ADMIN_CREDENTIALS = {
    "Super Admin": {
        "user_id": "BEV182371007",
        "password": "Super@123admin",
        "user_type": "Super Admin",
        "expected_dashboard": "/admin/dashboard",  # Adjust based on actual route
        "permissions": ["ALL"]  # Full system access
    },
    
    "Finance Admin": {
        "user_id": "BEV182371010",
        "password": "Fintech@123",
        "user_type": "Finance Admin",
        "expected_dashboard": "/finance/dashboard",  # Adjust based on actual route
        "permissions": ["view_financials", "approve_withdrawals", "view_reports"]
    },
    
    "Admin": {
        "user_id": "BEV182322707",
        "password": "System@admin",
        "user_type": "Admin",
        "expected_dashboard": "/admin/dashboard",
        "permissions": ["manage_users", "view_data", "reset_passwords"]
    },
    
    "RVZ ID": {
        "user_id": "BEV182364369",
        "password": "VGK@ADMIN",
        "user_type": "RVZ ID",
        "expected_dashboard": "/rvz/dashboard",  # Adjust based on actual route
        "permissions": ["view_vgk_data", "approve_pins", "manage_vgk"]
    }
}
```

### **Regular User Test Accounts**

```python
# Regular user for frontend flow testing
STF_USER_CREDENTIALS = {
    "Regular User": {
        "user_id": "BEV1800143",  # B.RAMALAXMI
        "password": "BLN@46",
        "user_type": "Member",
        "expected_dashboard": "/user/dashboard",
        "permissions": ["view_profile", "request_withdrawal", "activate_pin"]
    }
}
```

### **Security Notes**

```
⚠️ SECURITY RULES:
1. These are REAL production credentials
2. Use ONLY in development/staging environments
3. NEVER commit passwords to git (use environment variables)
4. NEVER run STF tests against production database
5. Rotate passwords if exposed publicly
6. Use separate test accounts for CI/CD pipelines
```

---

## 🏗️ STF TEST STRUCTURE

### **Standard Test File Structure**

```python
# tests/stf/test_admin_login.py

"""
STF Protocol: Admin Login Tests
Purpose: Validate all admin roles can login and access dashboards
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

# Test Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5000")
SCREENSHOT_DIR = "tests/stf/screenshots"

class STFBaseTest:
    """Base class for all STF tests"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        # Setup
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
        
        # Create screenshot directory
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        
        yield
        
        # Teardown
        self.driver.quit()
    
    def take_screenshot(self, name):
        """Capture screenshot with timestamp"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{SCREENSHOT_DIR}/{name}_{timestamp}.png"
        self.driver.save_screenshot(filename)
        return filename
    
    def login(self, user_id, password):
        """
        STF Protocol: Standard login flow
        Returns: True if successful, False otherwise
        """
        try:
            # Navigate to login page
            self.driver.get(f"{BASE_URL}/login")
            
            # Wait for login form
            user_id_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "user_id"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            login_button = self.driver.find_element(By.ID, "login-btn")
            
            # Enter credentials
            user_id_field.clear()
            user_id_field.send_keys(user_id)
            
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login
            login_button.click()
            
            # Wait for redirect (away from /login)
            self.wait.until(EC.url_contains("dashboard"))
            
            return True
            
        except TimeoutException:
            self.take_screenshot("login_failure")
            return False
        except Exception as e:
            self.take_screenshot("login_error")
            print(f"Login error: {str(e)}")
            return False


class TestAdminLogin(STFBaseTest):
    """STF Tests for Admin Login"""
    
    def test_super_admin_login(self):
        """
        STF Protocol: Test Super Admin login
        Expected: Login successful, redirect to admin dashboard
        """
        success = self.login("BEV182371007", "Super@123admin")
        assert success, "Super Admin login failed"
        
        # Verify dashboard loaded
        assert "dashboard" in self.driver.current_url.lower()
        
        # Verify user role displayed
        # (Adjust selector based on actual HTML)
        user_display = self.driver.find_element(By.CLASS_NAME, "user-role")
        assert "super admin" in user_display.text.lower()
    
    def test_finance_admin_login(self):
        """
        STF Protocol: Test Finance Admin login
        Expected: Login successful, redirect to finance dashboard
        """
        success = self.login("BEV182371010", "Fintech@123")
        assert success, "Finance Admin login failed"
        
        assert "dashboard" in self.driver.current_url.lower()
    
    def test_admin_login(self):
        """
        STF Protocol: Test Admin login
        Expected: Login successful, redirect to admin dashboard
        """
        success = self.login("BEV182322707", "System@admin")
        assert success, "Admin login failed"
        
        assert "dashboard" in self.driver.current_url.lower()
    
    def test_vgk_admin_login(self):
        """
        STF Protocol: Test RVZ ID login
        Expected: Login successful, redirect to VGK dashboard
        """
        success = self.login("BEV182364369", "VGK@ADMIN")
        assert success, "RVZ ID login failed"
        
        assert "dashboard" in self.driver.current_url.lower()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

---

## 📋 STEP-BY-STEP PROCESS

### **Phase 1: Setup**

**Step 1.1: Install Dependencies**

```bash
# Install Selenium and WebDriver
pip install selenium pytest

# Download ChromeDriver (match your Chrome version)
# Linux:
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
wget https://chromedriver.storage.googleapis.com/$(cat LATEST_RELEASE)/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/

# Or use webdriver-manager (automatic)
pip install webdriver-manager
```

**Step 1.2: Configure Test Environment**

```python
# tests/stf/config.py

import os

class STFConfig:
    """STF Protocol Configuration"""
    
    # Base URL (change for different environments)
    BASE_URL = os.getenv("STF_BASE_URL", "http://localhost:5000")
    
    # Timeouts
    DEFAULT_TIMEOUT = 10  # seconds
    PAGE_LOAD_TIMEOUT = 30  # seconds
    
    # Screenshots
    SCREENSHOT_DIR = "tests/stf/screenshots"
    SCREENSHOT_ON_FAILURE = True
    
    # Browser
    HEADLESS = os.getenv("STF_HEADLESS", "false").lower() == "true"
    BROWSER = os.getenv("STF_BROWSER", "chrome")  # chrome, firefox, safari
    
    # Credentials (loaded from environment for security)
    SUPER_ADMIN_ID = os.getenv("STF_SUPER_ADMIN_ID", "BEV182371007")
    SUPER_ADMIN_PASSWORD = os.getenv("STF_SUPER_ADMIN_PASSWORD", "Super@123admin")
```

**Step 1.3: Create Test Directory Structure**

```
tests/
├── stf/
│   ├── __init__.py
│   ├── config.py
│   ├── base.py (base test class)
│   ├── test_admin_login.py
│   ├── test_user_withdrawal.py
│   ├── test_pin_activation.py
│   ├── test_password_reset.py
│   └── screenshots/ (auto-created)
```

---

### **Phase 2: Write Test**

**Step 2.1: Identify User Flow**

```
Example: User Withdrawal Flow

1. Login as user (BEV1800143 / BLN@46)
2. Navigate to /user/withdrawals
3. Enter withdrawal amount (₹500)
4. Click "Request Withdrawal" button
5. Verify success message appears
6. Verify database has withdrawal record
7. Logout
```

**Step 2.2: Script the Flow**

```python
# tests/stf/test_user_withdrawal.py

"""
STF Protocol: User Withdrawal Flow Test
Purpose: Validate users can request withdrawals
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
from .base import STFBaseTest

class TestUserWithdrawal(STFBaseTest):
    """STF Tests for User Withdrawal"""
    
    def test_withdrawal_request_success(self):
        """
        STF Protocol: Test successful withdrawal request
        
        Flow:
        1. Login as regular user
        2. Navigate to withdrawals page
        3. Enter amount ₹500
        4. Submit request
        5. Verify success message
        6. Verify transaction created
        """
        # Step 1: Login
        success = self.login("BEV1800143", "BLN@46")
        assert success, "User login failed"
        
        # Step 2: Navigate to withdrawals
        self.driver.get(f"{self.base_url}/user/withdrawals")
        
        # Step 3: Wait for page load
        amount_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "withdrawal_amount"))
        )
        
        # Step 4: Enter amount
        amount_field.clear()
        amount_field.send_keys("500")
        
        # Step 5: Click submit
        submit_button = self.driver.find_element(By.ID, "submit_withdrawal")
        submit_button.click()
        
        # Step 6: Wait for success message
        try:
            success_message = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
            )
            assert "success" in success_message.text.lower()
            
        except Exception as e:
            self.take_screenshot("withdrawal_failed")
            raise AssertionError(f"Withdrawal failed: {str(e)}")
        
        # Step 7: Verify in database (optional, use DC Protocol)
        # This would require database connection
        
        # Step 8: Take success screenshot
        self.take_screenshot("withdrawal_success")
    
    def test_withdrawal_request_insufficient_balance(self):
        """
        STF Protocol: Test withdrawal with insufficient balance
        
        Expected: Error message shown, no transaction created
        """
        # Login
        self.login("BEV1800143", "BLN@46")
        
        # Navigate to withdrawals
        self.driver.get(f"{self.base_url}/user/withdrawals")
        
        # Enter very large amount (more than balance)
        amount_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "withdrawal_amount"))
        )
        amount_field.clear()
        amount_field.send_keys("999999999")
        
        # Submit
        submit_button = self.driver.find_element(By.ID, "submit_withdrawal")
        submit_button.click()
        
        # Verify error message
        error_message = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
        )
        assert "insufficient" in error_message.text.lower() or "balance" in error_message.text.lower()
        
        self.take_screenshot("withdrawal_insufficient_balance")
```

---

### **Phase 3: Run Test**

**Step 3.1: Execute Test**

```bash
# Run all STF tests
pytest tests/stf/ -v -s

# Run specific test file
pytest tests/stf/test_admin_login.py -v

# Run specific test function
pytest tests/stf/test_user_withdrawal.py::TestUserWithdrawal::test_withdrawal_request_success -v

# Run with HTML report
pytest tests/stf/ --html=report.html --self-contained-html
```

**Step 3.2: Monitor Execution**

```
Watch the browser:
- Browser opens automatically
- Actions execute (typing, clicking)
- Screenshots captured on failure
- Browser closes after test
```

---

### **Phase 4: Capture Evidence**

**Step 4.1: Screenshot on Failure**

```python
def test_example(self):
    try:
        # Test logic
        assert some_condition
    except AssertionError:
        # Auto-capture screenshot
        self.take_screenshot("test_failed")
        raise
```

**Step 4.2: Logs**

```python
import logging

logging.basicConfig(
    filename='tests/stf/stf_test.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_example(self):
    logging.info("Starting test: test_example")
    # Test logic
    logging.info("Test passed: test_example")
```

---

### **Phase 5: Validate**

**Step 5.1: Review Test Results**

```
PASSED tests/stf/test_admin_login.py::TestAdminLogin::test_super_admin_login ✅
PASSED tests/stf/test_admin_login.py::TestAdminLogin::test_finance_admin_login ✅
PASSED tests/stf/test_admin_login.py::TestAdminLogin::test_admin_login ✅
PASSED tests/stf/test_admin_login.py::TestAdminLogin::test_vgk_admin_login ✅
PASSED tests/stf/test_user_withdrawal.py::TestUserWithdrawal::test_withdrawal_request_success ✅

========================= 5 passed in 45.23s =========================
```

**Step 5.2: Check Screenshots**

```bash
# View captured screenshots
ls -lh tests/stf/screenshots/

# Screenshots created on failure:
# - login_failure_20251102_143025.png
# - withdrawal_failed_20251102_143156.png
```

---

## 📋 REAL-WORLD TEST EXAMPLES

### **Example 1: Admin Password Reset (Frontend)**

```python
# tests/stf/test_password_reset.py

"""
STF Protocol: Admin Password Reset Frontend Test
Purpose: Validate admin can reset user password via UI
"""

class TestPasswordReset(STFBaseTest):
    """STF Tests for Password Reset"""
    
    def test_admin_reset_user_password(self):
        """
        STF Protocol: Test admin resets user password
        
        Flow:
        1. Login as admin
        2. Navigate to users page
        3. Find test user
        4. Click reset password
        5. Verify success message
        6. Logout as admin
        7. Login as user with new password
        """
        # Step 1: Login as admin
        self.login("BEV182322707", "System@admin")
        
        # Step 2: Navigate to users management
        self.driver.get(f"{self.base_url}/admin/users")
        
        # Step 3: Search for user
        search_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "user_search"))
        )
        search_field.send_keys("BEV1800143")
        
        # Wait for search results
        time.sleep(1)
        
        # Step 4: Click reset password button
        reset_button = self.driver.find_element(
            By.CSS_SELECTOR, "button[data-action='reset-password'][data-user='BEV1800143']"
        )
        reset_button.click()
        
        # Step 5: Confirm reset
        confirm_button = self.wait.until(
            EC.element_to_be_clickable((By.ID, "confirm_reset"))
        )
        confirm_button.click()
        
        # Step 6: Verify success message
        success_message = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
        )
        assert "password reset" in success_message.text.lower()
        
        # Step 7: Logout admin
        logout_button = self.driver.find_element(By.ID, "logout-btn")
        logout_button.click()
        
        # Step 8: Login as user with temporary password
        # (Assuming temp password is "temp123")
        self.login("BEV1800143", "temp123")
        
        # Verify login successful
        assert "dashboard" in self.driver.current_url.lower()
        
        self.take_screenshot("password_reset_success")
```

---

### **Example 2: PIN Activation Dropdown Issue**

```python
# tests/stf/test_pin_activation.py

"""
STF Protocol: PIN Activation Dropdown Test
Purpose: Validate PIN dropdown loads and activation works
Issue: Previously reported - PIN dropdown empty (403 Forbidden)
"""

class TestPINActivation(STFBaseTest):
    """STF Tests for PIN Activation"""
    
    def test_pin_dropdown_loads(self):
        """
        STF Protocol: Test PIN dropdown loads correctly
        
        Flow:
        1. Login as user
        2. Navigate to activate coupon page
        3. Verify PIN dropdown loads
        4. Verify dropdown has options
        """
        # Step 1: Login
        self.login("BEV1800143", "BLN@46")
        
        # Step 2: Navigate to activate coupon
        self.driver.get(f"{self.base_url}/user/activate-coupon")
        
        # Step 3: Wait for PIN dropdown
        pin_dropdown = self.wait.until(
            EC.presence_of_element_located((By.ID, "pin_dropdown"))
        )
        
        # Step 4: Verify dropdown has options
        options = pin_dropdown.find_elements(By.TAG_NAME, "option")
        
        # Should have at least 2 options (1 placeholder + pins)
        assert len(options) >= 2, f"PIN dropdown empty: {len(options)} options found"
        
        self.take_screenshot("pin_dropdown_loaded")
    
    def test_pin_activation_success(self):
        """
        STF Protocol: Test complete PIN activation flow
        
        Flow:
        1. Login as user
        2. Navigate to activate coupon page
        3. Select PIN from dropdown
        4. Enter activation code
        5. Submit activation
        6. Verify success message
        """
        # Login
        self.login("BEV1800143", "BLN@46")
        
        # Navigate
        self.driver.get(f"{self.base_url}/user/activate-coupon")
        
        # Select PIN
        pin_dropdown = self.wait.until(
            EC.presence_of_element_located((By.ID, "pin_dropdown"))
        )
        
        # Select first available PIN (not placeholder)
        options = pin_dropdown.find_elements(By.TAG_NAME, "option")
        if len(options) > 1:
            options[1].click()  # Select first real option
        
        # Enter activation code (if required)
        # activation_code = self.driver.find_element(By.ID, "activation_code")
        # activation_code.send_keys("TEST123")
        
        # Submit
        submit_button = self.driver.find_element(By.ID, "activate_pin_btn")
        submit_button.click()
        
        # Verify success
        success_message = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        assert "activated" in success_message.text.lower()
        
        self.take_screenshot("pin_activation_success")
```

---

### **Example 3: Withdrawal Approval (Finance Admin)**

```python
# tests/stf/test_withdrawal_approval.py

"""
STF Protocol: Withdrawal Approval Test
Purpose: Validate Finance Admin can approve withdrawals
"""

class TestWithdrawalApproval(STFBaseTest):
    """STF Tests for Withdrawal Approval"""
    
    def test_finance_admin_approve_withdrawal(self):
        """
        STF Protocol: Test Finance Admin approves withdrawal
        
        Flow:
        1. Login as Finance Admin
        2. Navigate to withdrawal requests page
        3. Find pending withdrawal
        4. Click approve
        5. Verify status changes to approved
        """
        # Step 1: Login as Finance Admin
        self.login("BEV182371010", "Fintech@123")
        
        # Step 2: Navigate to withdrawals
        self.driver.get(f"{self.base_url}/finance/withdrawals")
        
        # Step 3: Wait for withdrawal table
        withdrawal_table = self.wait.until(
            EC.presence_of_element_located((By.ID, "withdrawal_requests_table"))
        )
        
        # Step 4: Find first pending withdrawal
        approve_buttons = self.driver.find_elements(
            By.CSS_SELECTOR, "button[data-action='approve']"
        )
        
        if approve_buttons:
            first_approve_button = approve_buttons[0]
            withdrawal_id = first_approve_button.get_attribute("data-withdrawal-id")
            
            # Click approve
            first_approve_button.click()
            
            # Confirm approval
            confirm_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "confirm_approval"))
            )
            confirm_button.click()
            
            # Step 5: Verify success
            success_message = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
            )
            assert "approved" in success_message.text.lower()
            
            self.take_screenshot("withdrawal_approved")
        else:
            self.take_screenshot("no_pending_withdrawals")
            pytest.skip("No pending withdrawals to approve")
```

---

## 🔄 INTEGRATION WITH WVV + FT + DC

### **How STF Fits in the Protocol Suite**

```
┌─────────────────────────────────────────────────────────────────┐
│ ISSUE REPORTED: "Withdrawal button doesn't work"               │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ WVV PROTOCOL (Working Validation with Verification)             │
│                                                                  │
│ Phase 1: Identify ALL issues                                    │
│ Phase 2: Root cause analysis (DC Protocol)                      │
│ Phase 3: Design solution                                        │
│ Phase 4: Implement + fix cascading issues                       │
│ Phase 5: End-to-end validation (FT Protocol)                    │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FT PROTOCOL (Frontend Testing) - Manual                         │
│                                                                  │
│ ✅ Smoke Test: Page loads                                       │
│ ✅ Functional Test: Feature works                               │
│ ✅ Edge Cases: Errors handled                                   │
│ ✅ Regression: Related features work                            │
│ ✅ Cross-Device: Mobile/desktop                                 │
│ ✅ Evidence: Screenshots captured                               │
│ ✅ Database: DC Protocol verification                           │
│ ✅ Logs: R Logs Protocol check                                  │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ STF PROTOCOL (Selenium Test Frontend) - Automated ✨           │
│                                                                  │
│ Purpose: Prevent regression, automate validation                │
│                                                                  │
│ 1. Write Selenium test for fixed flow                           │
│ 2. Run automated browser test                                   │
│ 3. Validate with REAL login credentials                         │
│ 4. Add to CI/CD pipeline                                        │
│ 5. Run on every code change                                     │
│                                                                  │
│ Result: Future changes won't break this flow ✅                │
└─────────────────────────────────────────────────────────────────┘
```

### **When to Use Each Protocol**

| Protocol | When to Use | Purpose |
|----------|-------------|---------|
| **WVV** | Issue reported | Identify ALL issues, fix with verification |
| **DC** | During WVV Phase 2 | Verify database reality, no assumptions |
| **FT** | During WVV Phase 5 | Manually validate fix works end-to-end |
| **STF** | After FT passes | Automate the validated flow to prevent regression |
| **R Logs** | During WVV & FT | Check backend/frontend/browser logs |

---

## 📋 CHECKLISTS

### **STF Quick Start Checklist**

```
SETUP (One-time):
[ ] Install Selenium: pip install selenium pytest
[ ] Install WebDriver (ChromeDriver)
[ ] Create test directory structure
[ ] Configure test environment (config.py)
[ ] Set up credentials (environment variables)

WRITE TEST:
[ ] Identify user flow to test
[ ] Create test file in tests/stf/
[ ] Inherit from STFBaseTest
[ ] Write test steps (login, navigate, interact, verify)
[ ] Add screenshots on failure
[ ] Add clear assertion messages

RUN TEST:
[ ] Run test: pytest tests/stf/test_file.py -v
[ ] Watch browser execution
[ ] Review test results
[ ] Check screenshots if failed
[ ] Fix any failures

MAINTAIN:
[ ] Update tests when UI changes
[ ] Add tests for new features
[ ] Remove tests for deprecated features
[ ] Run tests regularly (CI/CD)
```

---

### **STF Test Validation Checklist**

```
BEFORE MARKING TEST COMPLETE:

TEST QUALITY:
[ ] Test uses REAL login credentials
[ ] Test covers complete user flow (start to finish)
[ ] Test has clear assertions
[ ] Test captures screenshot on failure
[ ] Test cleans up after itself (logout, close browser)

TEST RELIABILITY:
[ ] Test passes consistently (run 3 times)
[ ] Test doesn't depend on external data
[ ] Test uses explicit waits (not sleep)
[ ] Test handles timeouts gracefully
[ ] Test takes <60 seconds to execute

INTEGRATION:
[ ] Test validates fix from WVV Protocol
[ ] Test complements FT Protocol (automates validated flow)
[ ] Test uses DC Protocol for data verification
[ ] Test checks logs if needed (R Logs Protocol)

DOCUMENTATION:
[ ] Test has clear docstring
[ ] Test purpose documented
[ ] Test flow documented step-by-step
[ ] Test credentials documented (which role)
```

---

## 🎯 STF PROTOCOL SUMMARY

### **Core Principles:**

1. **Automate Validated Flows**
   - Use STF AFTER FT Protocol validates the flow manually
   - Don't automate broken flows (fix first with WVV)

2. **Use Real Credentials**
   - Test with actual admin/user accounts
   - Validate role-based access control
   - Test real session handling

3. **Prevent Regressions**
   - Run STF tests on every code change
   - Catch breaks before they reach users
   - Build confidence in deployments

4. **Complement, Don't Replace**
   - STF complements FT (automated vs manual)
   - STF doesn't replace DC (frontend vs database)
   - STF works with WVV (validation step)

5. **Fast Feedback**
   - Tests run in seconds
   - Immediate results
   - Clear pass/fail

---

## ✅ FINAL CHECKLIST

**Before using STF Protocol:**

```
[ ] Issue fixed via WVV Protocol ✅
[ ] Fix validated via FT Protocol ✅
[ ] Database verified via DC Protocol ✅
[ ] Ready to automate the validated flow ✅

Then:
[ ] Write STF test for the flow
[ ] Run test to validate automation works
[ ] Add test to CI/CD pipeline
[ ] Run on every code change
```

**STF Success Criteria:**
```
✅ Test uses real login credentials
✅ Test covers complete user journey
✅ Test passes consistently
✅ Test provides clear failure evidence (screenshots)
✅ Test integrated with WVV + FT + DC protocols
```

---

**END OF STF PROTOCOL**

**Integration Summary:**
```
WVV Protocol → Identify & fix issues (complete validation)
  └─ DC Protocol → Verify database reality (no assumptions)
  └─ FT Protocol → Manual testing (see it working yourself)
      └─ STF Protocol → Automate validated flows (prevent regression)
          └─ R Logs Protocol → Check logs for errors
```

**Result: Complete, validated, automated testing workflow! ✅**
