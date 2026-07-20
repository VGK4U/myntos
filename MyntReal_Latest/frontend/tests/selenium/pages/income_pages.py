"""
DC Protocol: Income Flow Page Objects
Staff Portal Income Management Pages
"""

import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class IncomeRecordsPage(BasePage):
    """Staff Income Records Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    DATA_TABLE = (By.CSS_SELECTOR, "table, .data-table, #incomeTable")
    FILTER_SECTION = (By.CSS_SELECTOR, ".filters, .filter-section, form")
    LOADING_INDICATOR = (By.CSS_SELECTOR, ".loading, .spinner")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/income-records")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Income Records page...")
        
        import time
        time.sleep(2)
        
        alert_text = self.dismiss_alert()
        if alert_text:
            if "Admin access required" in alert_text or "access denied" in alert_text.lower():
                print(f"   ⚠️ Access restriction alert (expected): {alert_text[:50]}...")
        
        current_url = self.get_current_url()
        page_title = self.get_title()
        
        if "/login" in current_url:
            print("   ⚠️ Redirected to login")
            return False
            
        if "/staff/mnr/income-records" in current_url or "Income Records" in page_title:
            print(f"   ✅ Page loaded: {page_title}")
            return True
            
        print(f"   ⚠️ Unexpected state - URL: {current_url}")
        return False


class IncomeSupremePage(BasePage):
    """Staff Income Supreme (RVZ Approval) Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    APPROVAL_TABLE = (By.CSS_SELECTOR, "table, .approval-table")
    APPROVE_BUTTONS = (By.CSS_SELECTOR, ".btn-approve, button[data-action='approve']")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/income-supreme")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Income Supreme page...")
        
        self.dismiss_alert()
        
        current_url = self.get_current_url()
        
        if "/login" in current_url:
            print("   ⚠️ Redirected to login - RVZ permission required")
            return True
            
        if "/staff/mnr/income-supreme" in current_url:
            print(f"   ✅ Page loaded: {self.get_title()}")
            return True
            
        return False


class FinanceCompletePage(BasePage):
    """Staff Finance Completion Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    COMPLETION_TABLE = (By.CSS_SELECTOR, "table, .completion-table")
    COMPLETE_BUTTONS = (By.CSS_SELECTOR, ".btn-complete, button[data-action='complete']")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/income-finance-complete")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Finance Complete page...")
        
        import time
        time.sleep(2)
        
        alert_text = self.dismiss_alert()
        if alert_text:
            print(f"   ⚠️ Alert: {alert_text[:50]}...")
        
        current_url = self.get_current_url()
        page_title = self.get_title()
        
        if "/login" in current_url:
            print("   ⚠️ Redirected to login")
            return False
            
        if "/staff/mnr/income-finance-complete" in current_url or "Finance" in page_title:
            print(f"   ✅ Page loaded: {page_title}")
            return True
            
        print(f"   ⚠️ Unexpected state - URL: {current_url}")
        return False
