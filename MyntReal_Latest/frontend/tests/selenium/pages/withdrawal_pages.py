"""
DC Protocol: Withdrawal Flow Page Objects
Staff Portal Withdrawal Management Pages
"""

import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class WithdrawalDashboardPage(BasePage):
    """Staff Withdrawal Dashboard Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    STATS_CARDS = (By.CSS_SELECTOR, ".stats-card, .dashboard-card, .card")
    CHARTS = (By.CSS_SELECTOR, "canvas, .chart-container")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/withdrawal/dashboard")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Withdrawal Dashboard page...")
        
        self.dismiss_alert()
        
        if not self.verify_page_loaded(expected_url_contains="/staff/mnr/withdrawal/dashboard"):
            return False
            
        if self.is_element_visible(*self.PAGE_HEADER):
            print(f"   ✅ Page loaded: {self.get_title()}")
            return True
            
        return False


class WithdrawalApprovalsPage(BasePage):
    """Staff Withdrawal Approvals Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    APPROVALS_TABLE = (By.CSS_SELECTOR, "table, .approvals-table")
    APPROVE_BUTTONS = (By.CSS_SELECTOR, ".btn-approve, button[data-action='approve']")
    REJECT_BUTTONS = (By.CSS_SELECTOR, ".btn-reject, button[data-action='reject']")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/withdrawal/approvals")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Withdrawal Approvals page...")
        
        self.dismiss_alert()
        
        if not self.verify_page_loaded(expected_url_contains="/staff/mnr/withdrawal/approvals"):
            return False
            
        if self.is_element_visible(*self.PAGE_HEADER):
            print(f"   ✅ Page loaded: {self.get_title()}")
            return True
            
        return False


class WithdrawalHistoryPage(BasePage):
    """Staff Withdrawal History Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    HISTORY_TABLE = (By.CSS_SELECTOR, "table, .history-table")
    FILTERS = (By.CSS_SELECTOR, ".filters, .filter-section")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/withdrawal/history")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Withdrawal History page...")
        
        self.dismiss_alert()
        
        if not self.verify_page_loaded(expected_url_contains="/staff/mnr/withdrawal/history"):
            return False
            
        if self.is_element_visible(*self.PAGE_HEADER):
            print(f"   ✅ Page loaded: {self.get_title()}")
            return True
            
        return False


class WithdrawalSupremePage(BasePage):
    """Staff Withdrawal Supreme (VGK4U Skip Approval) Page"""
    
    PAGE_HEADER = (By.CSS_SELECTOR, ".page-header, h1, h2")
    SUPREME_TABLE = (By.CSS_SELECTOR, "table, .supreme-table")
    
    def __init__(self, driver: WebDriver):
        super().__init__(driver, "/staff/mnr/withdrawal-supreme")
        
    def verify_loaded(self) -> bool:
        """Verify the page loaded correctly"""
        print("   📋 Verifying Withdrawal Supreme page...")
        
        self.dismiss_alert()
        
        current_url = self.get_current_url()
        
        if "/login" in current_url:
            print("   ⚠️ Redirected to login - VGK4U Supreme permission required")
            return True
            
        if "/staff/mnr/withdrawal-supreme" in current_url:
            print(f"   ✅ Page loaded: {self.get_title()}")
            return True
            
        return False
