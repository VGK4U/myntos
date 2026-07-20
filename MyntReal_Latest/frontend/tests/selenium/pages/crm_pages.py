"""
DC Protocol: CRM Lead Management Page Objects
Comprehensive test coverage for Universal CRM system
"""

import time
from typing import Optional, List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from pages.base_page import BasePage
from config.settings import BASE_URL


class CRMLeadsPage(BasePage):
    """
    DC Protocol: Universal CRM Leads Page (rvz_crm_leads.html)
    Staff portal - VGK/EA and other staff roles
    """
    
    URL = f"{BASE_URL}/rvz/crm-leads"
    
    SELECTORS = {
        'company_selector': '#companySelector',
        'add_lead_btn': 'button[onclick="openAddModal()"]',
        'leads_table': '#leadsTableBody',
        'lead_row': '#leadsTableBody tr',
        'empty_state': '#emptyState',
        'dashboard_stats': '.stat-card',
        'stat_total': '.stat-card:nth-child(1) .stat-value',
        'stat_new': '.stat-card:nth-child(2) .stat-value',
        'stat_won': '.stat-card:nth-child(3) .stat-value',
        'lead_modal': '#leadModal',
        'lead_form': '#leadForm',
        'lead_name': '#leadName',
        'lead_phone': '#leadPhone',
        'lead_email': '#leadEmail',
        'lead_category': '#leadCategory',
        'lead_status': '#leadStatus',
        'lead_priority': '#leadPriority',
        'lead_pincode': '#leadPincode',
        'lead_form_company': '#leadFormCompany',
        'save_lead_btn': '#saveLeadBtn',
        'view_modal': '#viewLeadModal',
        'view_lead_name': '#detailLeadName',
        'delete_btn': '.btn-outline-danger.icon-btn',
        'edit_btn': '.btn-outline-primary.icon-btn',
        'filter_status': '#filterStatus',
        'filter_priority': '#filterPriority',
        'search_input': '#searchInput',
        'pagination': '#paginationContainer',
        'toast': '.toast',
        'loading_spinner': '.loading-spinner',
    }
    
    def navigate(self):
        """Navigate to CRM Leads page"""
        self.driver.get(self.URL)
        self.wait_for_load()
        time.sleep(2)
        
    def verify_loaded(self) -> bool:
        """Verify page is fully loaded"""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.SELECTORS['company_selector']))
            )
            return True
        except TimeoutException:
            return False
    
    def get_selected_company(self) -> str:
        """Get currently selected company"""
        try:
            select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['company_selector']))
            return select.first_selected_option.text
        except:
            return ""
    
    def select_company(self, company_name: str) -> bool:
        """Select a company from dropdown"""
        try:
            select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['company_selector']))
            select.select_by_visible_text(company_name)
            time.sleep(2)
            return True
        except:
            return False
    
    def select_all_companies(self) -> bool:
        """Select 'All Companies' option"""
        try:
            select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['company_selector']))
            select.select_by_value('all')
            time.sleep(2)
            return True
        except:
            return False
    
    def get_dashboard_stats(self) -> Dict[str, int]:
        """Get dashboard statistics"""
        stats = {}
        try:
            stats['total'] = int(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['stat_total']).text or '0')
            stats['new'] = int(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['stat_new']).text or '0')
            stats['won'] = int(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['stat_won']).text or '0')
        except:
            stats = {'total': 0, 'new': 0, 'won': 0}
        return stats
    
    def get_leads_count(self) -> int:
        """Get number of leads in table"""
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['lead_row'])
            return len(rows)
        except:
            return 0
    
    def is_empty_state_visible(self) -> bool:
        """Check if empty state is displayed"""
        try:
            empty = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['empty_state'])
            return empty.is_displayed()
        except:
            return False
    
    def click_add_lead(self) -> bool:
        """Click Add Lead button"""
        try:
            btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTORS['add_lead_btn']))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.5)
            btn.click()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"   ❌ Add Lead click error: {e}")
            return False
    
    def is_lead_modal_open(self) -> bool:
        """Check if lead modal is open"""
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_modal'])
            return 'show' in modal.get_attribute('class')
        except:
            return False
    
    def fill_lead_form(self, lead_data: Dict[str, Any]) -> bool:
        """Fill out the lead form"""
        try:
            if 'name' in lead_data:
                name_input = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_name'])
                name_input.clear()
                name_input.send_keys(lead_data['name'])
            
            if 'phone' in lead_data:
                phone_input = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_phone'])
                phone_input.clear()
                phone_input.send_keys(lead_data['phone'])
            
            if 'email' in lead_data:
                email_input = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_email'])
                email_input.clear()
                email_input.send_keys(lead_data['email'])
            
            if 'pincode' in lead_data:
                pincode_input = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_pincode'])
                pincode_input.clear()
                pincode_input.send_keys(lead_data['pincode'])
            
            if 'category' in lead_data:
                category_select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_category']))
                category_select.select_by_visible_text(lead_data['category'])
            
            if 'status' in lead_data:
                status_select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_status']))
                status_select.select_by_value(lead_data['status'])
            
            if 'priority' in lead_data:
                priority_select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_priority']))
                priority_select.select_by_value(lead_data['priority'])
            
            if 'company_id' in lead_data:
                company_select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_form_company']))
                company_select.select_by_value(str(lead_data['company_id']))
            
            return True
        except Exception as e:
            print(f"   ❌ Fill form error: {e}")
            return False
    
    def save_lead(self) -> bool:
        """Click save lead button"""
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['save_lead_btn'])
            btn.click()
            time.sleep(2)
            return True
        except:
            return False
    
    def click_first_lead_row(self) -> bool:
        """Click on first lead row to view details"""
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['lead_row'])
            if rows:
                rows[0].click()
                time.sleep(1)
                return True
            return False
        except:
            return False
    
    def click_edit_first_lead(self) -> bool:
        """Click edit button on first lead"""
        try:
            edit_btns = self.driver.find_elements(By.CSS_SELECTOR, f"{self.SELECTORS['lead_row']} {self.SELECTORS['edit_btn']}")
            if edit_btns:
                edit_btns[0].click()
                time.sleep(1)
                return True
            return False
        except:
            return False
    
    def is_delete_button_visible(self) -> bool:
        """Check if delete button is visible on first lead"""
        try:
            delete_btns = self.driver.find_elements(By.CSS_SELECTOR, f"{self.SELECTORS['lead_row']} {self.SELECTORS['delete_btn']}")
            return len(delete_btns) > 0
        except:
            return False
    
    def click_delete_first_lead(self) -> bool:
        """Click delete button on first lead"""
        try:
            delete_btns = self.driver.find_elements(By.CSS_SELECTOR, f"{self.SELECTORS['lead_row']} {self.SELECTORS['delete_btn']}")
            if delete_btns:
                delete_btns[0].click()
                time.sleep(1)
                return True
            return False
        except:
            return False
    
    def confirm_delete_alert(self) -> bool:
        """Confirm delete in browser alert"""
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
            time.sleep(1)
            return True
        except:
            return False
    
    def dismiss_delete_alert(self) -> bool:
        """Dismiss delete alert"""
        try:
            alert = self.driver.switch_to.alert
            alert.dismiss()
            return True
        except:
            return False
    
    def get_toast_message(self) -> str:
        """Get toast notification message"""
        try:
            toast = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.SELECTORS['toast']))
            )
            return toast.text
        except:
            return ""
    
    def search_leads(self, query: str) -> bool:
        """Search for leads"""
        try:
            search = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['search_input'])
            search.clear()
            search.send_keys(query)
            search.send_keys(Keys.RETURN)
            time.sleep(1)
            return True
        except:
            return False
    
    def filter_by_status(self, status: str) -> bool:
        """Filter leads by status"""
        try:
            select = Select(self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['filter_status']))
            select.select_by_value(status)
            time.sleep(1)
            return True
        except:
            return False


class PartnerLeadsPage(BasePage):
    """
    DC Protocol: Partner My Leads Page (partner_my_leads.html)
    Partner portal - Official Partners
    """
    
    URL = f"{BASE_URL}/partner/my-leads"
    
    SELECTORS = {
        'leads_container': '#leadsContainer',
        'lead_cards': '.lead-card',
        'add_lead_btn': 'button[onclick="openAddModal()"]',
        'lead_modal': '#leadModal',
        'lead_form_company': '#leadCompany',
        'save_lead_btn': '#saveLeadBtn',
        'view_btn': '.btn-outline-primary[onclick*="viewLead"]',
        'edit_btn': '.btn-outline-success[onclick*="editLead"]',
        'empty_state': '#emptyState',
    }
    
    def navigate(self):
        """Navigate to Partner Leads page"""
        self.driver.get(self.URL)
        self.wait_for_load()
        time.sleep(2)
    
    def verify_loaded(self) -> bool:
        """Verify page is fully loaded"""
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            return False
    
    def get_leads_count(self) -> int:
        """Get number of leads displayed"""
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['lead_cards'])
            return len(cards)
        except:
            return 0
    
    def click_add_lead(self) -> bool:
        """Click Add Lead button"""
        try:
            btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTORS['add_lead_btn']))
            )
            btn.click()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"   ❌ Add Lead click error: {e}")
            return False
    
    def is_lead_modal_open(self) -> bool:
        """Check if lead modal is open"""
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_modal'])
            return 'show' in modal.get_attribute('class')
        except:
            return False
    
    def is_company_selector_in_form(self) -> bool:
        """Check if company selector exists in form"""
        try:
            select = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_form_company'])
            return select.is_displayed()
        except:
            return False
    
    def click_view_first_lead(self) -> bool:
        """Click view button on first lead"""
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['view_btn'])
            if btns:
                btns[0].click()
                time.sleep(1)
                return True
            return False
        except:
            return False


class MNRLeadsPage(BasePage):
    """
    DC Protocol: MNR User My Leads Page (user_my_leads.html)
    MNR portal - MNR Members
    """
    
    URL = f"{BASE_URL}/user/my-leads"
    
    SELECTORS = {
        'leads_container': '#leadsContainer',
        'lead_cards': '.lead-card',
        'add_lead_btn': 'button[onclick="openAddModal()"]',
        'lead_modal': '#leadModal',
        'lead_form_company': '#leadCompany',
        'save_lead_btn': '#saveLeadBtn',
        'view_btn': '.btn-outline-primary[onclick*="viewLead"]',
        'edit_btn': '.btn-outline-success[onclick*="editLead"]',
        'empty_state': '#emptyState',
    }
    
    def navigate(self):
        """Navigate to MNR Leads page"""
        self.driver.get(self.URL)
        self.wait_for_load()
        time.sleep(2)
    
    def verify_loaded(self) -> bool:
        """Verify page is fully loaded"""
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            return False
    
    def get_leads_count(self) -> int:
        """Get number of visible leads"""
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['lead_cards'])
            return len(cards)
        except:
            return 0
    
    def is_empty_state_visible(self) -> bool:
        """Check if empty state is displayed"""
        try:
            empty = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['empty_state'])
            return empty.is_displayed()
        except:
            return False
    
    def click_add_lead(self) -> bool:
        """Click Add Lead button"""
        try:
            btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTORS['add_lead_btn']))
            )
            btn.click()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"   ❌ Add Lead click error: {e}")
            return False
    
    def is_lead_modal_open(self) -> bool:
        """Check if lead modal is open"""
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_modal'])
            return 'show' in modal.get_attribute('class')
        except:
            return False
    
    def is_company_selector_in_form(self) -> bool:
        """Check if company selector exists in form"""
        try:
            select = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['lead_form_company'])
            return select.is_displayed()
        except:
            return False
    
    def click_view_first_lead(self) -> bool:
        """Click view button on first lead"""
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['view_btn'])
            if btns:
                btns[0].click()
                time.sleep(1)
                return True
            return False
        except:
            return False
