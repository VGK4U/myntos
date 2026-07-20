"""
DC Protocol: Base Page Object for Selenium Tests
Common functionality shared across all page objects
"""

import time
from typing import Optional, List, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config.settings import BASE_URL


class BasePage:
    """Base class for all page objects"""
    
    def __init__(self, driver: WebDriver, path: str = ""):
        self.driver = driver
        self.path = path
        self.url = f"{BASE_URL}{path}"
        self.wait = WebDriverWait(driver, 10)
        
    def navigate(self):
        """Navigate to the page"""
        print(f"   📍 Navigating to: {self.url}")
        self.driver.get(self.url)
        self.wait_for_load()
        return self
        
    def wait_for_load(self, timeout: int = 10):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            print("   ⚠️ Page load timeout")
            
    def get_current_url(self) -> str:
        """Get current page URL"""
        return self.driver.current_url
        
    def get_title(self) -> str:
        """Get page title"""
        return self.driver.title
        
    def find_element(self, by: By, value: str, timeout: int = 10) -> Optional[WebElement]:
        """Find element with wait"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
            
    def find_elements(self, by: By, value: str) -> List[WebElement]:
        """Find multiple elements"""
        try:
            return self.driver.find_elements(by, value)
        except:
            return []
            
    def click(self, by: By, value: str, timeout: int = 10) -> bool:
        """Click an element"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            return True
        except:
            return False
            
    def type_text(self, by: By, value: str, text: str, clear: bool = True) -> bool:
        """Type text into an input field"""
        try:
            element = self.find_element(by, value)
            if element:
                if clear:
                    element.clear()
                element.send_keys(text)
                return True
            return False
        except:
            return False
            
    def is_element_visible(self, by: By, value: str, timeout: int = 5) -> bool:
        """Check if element is visible"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except:
            return False
            
    def get_text(self, by: By, value: str) -> str:
        """Get element text"""
        element = self.find_element(by, value)
        return element.text if element else ""
        
    def wait_for_element(self, by: By, value: str, timeout: int = 10) -> Optional[WebElement]:
        """Wait for specific element to appear"""
        return self.find_element(by, value, timeout)
        
    def dismiss_alert(self) -> Optional[str]:
        """Dismiss any alert and return its text"""
        try:
            alert = self.driver.switch_to.alert
            text = alert.text
            alert.accept()
            return text
        except:
            return None
            
    def scroll_to_element(self, element: WebElement):
        """Scroll element into view"""
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)
        
    def take_screenshot(self, name: str) -> str:
        """Take screenshot of current page"""
        from config.settings import SCREENSHOTS_DIR
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOTS_DIR, filename)
        self.driver.save_screenshot(filepath)
        return filepath
        
    def verify_page_loaded(self, expected_title_contains: str = None, expected_url_contains: str = None) -> bool:
        """Verify the page loaded correctly"""
        self.wait_for_load()
        
        if expected_title_contains:
            if expected_title_contains.lower() not in self.get_title().lower():
                print(f"   ⚠️ Title mismatch: expected '{expected_title_contains}', got '{self.get_title()}'")
                return False
                
        if expected_url_contains:
            if expected_url_contains not in self.get_current_url():
                print(f"   ⚠️ URL mismatch: expected '{expected_url_contains}' in URL")
                return False
                
        return True
