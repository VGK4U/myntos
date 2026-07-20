"""
DC Protocol: Login Page Objects for Staff and MNR User Authentication
"""

import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class StaffLoginPage(BasePage):
    """Staff Portal Login Page"""
    
    EMPLOYEE_ID_INPUT = (By.ID, "employeeId")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.XPATH, "//button[@type='submit']")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".error-message, .alert-danger")
    NDA_MODAL = (By.ID, "ndaModal")
    NDA_ACCEPT_BTN = (By.ID, "acceptNdaBtn")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/login")
        
    def login(self, employee_id: str, password: str) -> bool:
        """
        Perform staff login with credentials
        Returns True if login successful
        """
        print(f"   🔐 Logging in as Staff: {employee_id}")
        
        self.navigate()
        time.sleep(1)
        
        if not self.type_text(*self.EMPLOYEE_ID_INPUT, employee_id):
            print("   ❌ Failed to enter employee ID")
            return False
            
        if not self.type_text(*self.PASSWORD_INPUT, password):
            print("   ❌ Failed to enter password")
            return False
            
        if not self.click(*self.LOGIN_BUTTON):
            print("   ❌ Failed to click login button")
            return False
            
        time.sleep(3)
        self.wait_for_load()
        
        self.dismiss_alert()
        
        if self.is_element_visible(*self.NDA_MODAL, timeout=2):
            print("   📝 NDA acceptance required...")
            if self.click(*self.NDA_ACCEPT_BTN):
                print("   ✅ NDA accepted")
                time.sleep(2)
                self.dismiss_alert()
        
        current_url = self.get_current_url()
        
        if "/staff/" in current_url and "/login" not in current_url:
            print("   ✅ Staff login successful")
            return True
            
        if self.is_element_visible(*self.ERROR_MESSAGE, timeout=2):
            error_text = self.get_text(*self.ERROR_MESSAGE)
            print(f"   ❌ Login error: {error_text}")
            return False
            
        print(f"   ⚠️ Login status uncertain - URL: {current_url}")
        return "/login" not in current_url


class MNRUserLoginPage(BasePage):
    """MNR User Portal Login Page"""
    
    MNR_ID_INPUT = (By.ID, "mnr_id")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.XPATH, "//button[@type='submit']")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".error-message, .alert-danger")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/login")
        
    def login(self, mnr_id: str, password: str) -> bool:
        """
        Perform MNR user login with credentials
        Returns True if login successful
        """
        print(f"   🔐 Logging in as MNR User: {mnr_id}")
        
        self.navigate()
        time.sleep(1)
        
        if not self.type_text(*self.MNR_ID_INPUT, mnr_id):
            print("   ❌ Failed to enter MNR ID")
            return False
            
        if not self.type_text(*self.PASSWORD_INPUT, password):
            print("   ❌ Failed to enter password")
            return False
            
        if not self.click(*self.LOGIN_BUTTON):
            print("   ❌ Failed to click login button")
            return False
            
        time.sleep(3)
        self.wait_for_load()
        
        self.dismiss_alert()
        
        current_url = self.get_current_url()
        
        if "/user/" in current_url or "/dashboard" in current_url:
            print("   ✅ MNR User login successful")
            return True
            
        if self.is_element_visible(*self.ERROR_MESSAGE, timeout=2):
            error_text = self.get_text(*self.ERROR_MESSAGE)
            print(f"   ❌ Login error: {error_text}")
            return False
            
        print(f"   ⚠️ Login status uncertain - URL: {current_url}")
        return "/login" not in current_url
