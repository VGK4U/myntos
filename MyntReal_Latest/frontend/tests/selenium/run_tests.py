#!/usr/bin/env python3
"""
DC Protocol: Frontend Selenium Test Runner
Visible Browser Testing with Strict Error Handling

Usage:
    python run_tests.py                    # Run with visible browser
    python run_tests.py --headless         # Run in headless mode
    python run_tests.py --vnc              # Run with VNC desktop output
    python run_tests.py --test login       # Run specific test
    python run_tests.py --suite income     # Run specific test suite
"""

import os
import sys
import argparse
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TEST_CREDENTIALS, BASE_URL, CRM_TEST_DATA
from utils.browser_manager import BrowserManager
from utils.error_handler import ErrorHandler, ErrorSeverity
from utils.test_runner import TestRunner, TestStatus

from pages.login_page import StaffLoginPage, MNRUserLoginPage
from pages.income_pages import IncomeRecordsPage, IncomeSupremePage, FinanceCompletePage
from pages.withdrawal_pages import (
    WithdrawalDashboardPage, WithdrawalApprovalsPage, 
    WithdrawalHistoryPage, WithdrawalSupremePage
)
from pages.crm_pages import CRMLeadsPage, PartnerLeadsPage, MNRLeadsPage


class FrontendTestSuite:
    """
    DC Protocol: Comprehensive Frontend Test Suite
    With strict error handling and real-time monitoring
    """
    
    def __init__(self, headless: bool = False, vnc_mode: bool = False):
        self.headless = headless
        self.vnc_mode = vnc_mode
        self.runner: TestRunner = None
        self.browser: BrowserManager = None
        self.error_handler: ErrorHandler = None
        
    def setup(self):
        """Initialize test infrastructure"""
        self.browser = BrowserManager(headless=self.headless, vnc_mode=self.vnc_mode)
        self.browser.setup()
        self.error_handler = ErrorHandler(self.browser)
        
    def teardown(self):
        """Cleanup test infrastructure"""
        if self.browser:
            self.browser.cleanup()
            
    def test_staff_login(self):
        """Test staff portal login"""
        login_page = StaffLoginPage(self.browser.driver)
        creds = TEST_CREDENTIALS['staff']
        
        success = login_page.login(creds['employee_id'], creds['password'])
        
        if not success:
            raise AssertionError("Staff login failed")
            
        time.sleep(1)
        self.browser.capture_console_logs()
        
    def test_income_records_page(self):
        """Test Income Records page loading"""
        page = IncomeRecordsPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Income Records page failed to load correctly")
            
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
        
    def test_income_supreme_page(self):
        """Test Income Supreme page loading"""
        page = IncomeSupremePage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Income Supreme page failed to load correctly")
            
        self.browser.capture_console_logs()
        
    def test_finance_complete_page(self):
        """Test Finance Complete page loading"""
        page = FinanceCompletePage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Finance Complete page failed to load correctly")
            
        self.browser.capture_console_logs()
        
    def test_withdrawal_dashboard_page(self):
        """Test Withdrawal Dashboard page loading"""
        page = WithdrawalDashboardPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Withdrawal Dashboard page failed to load correctly")
            
        self.browser.capture_console_logs()
        
    def test_withdrawal_approvals_page(self):
        """Test Withdrawal Approvals page loading"""
        page = WithdrawalApprovalsPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Withdrawal Approvals page failed to load correctly")
            
        self.browser.capture_console_logs()
        
    def test_withdrawal_history_page(self):
        """Test Withdrawal History page loading"""
        page = WithdrawalHistoryPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Withdrawal History page failed to load correctly")
            
        self.browser.capture_console_logs()
        
    def test_withdrawal_supreme_page(self):
        """Test Withdrawal Supreme page loading"""
        page = WithdrawalSupremePage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Withdrawal Supreme page failed to load correctly")
            
        self.browser.capture_console_logs()
    
    # ========== CRM LEAD MANAGEMENT TESTS (DC Protocol Dec 31, 2025) ==========
    
    def test_crm_leads_page_load(self):
        """Test CRM Leads page loading"""
        page = CRMLeadsPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("CRM Leads page failed to load correctly")
        
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
    
    def test_crm_company_selector(self):
        """Test CRM company selector functionality (reuses page state)"""
        page = CRMLeadsPage(self.browser.driver)
        
        selected = page.get_selected_company()
        if not selected:
            raise AssertionError("No company selected by default")
        
        print(f"   📋 Current company: {selected}")
        self.browser.capture_console_logs()
    
    def test_crm_all_companies_mode(self):
        """Test 'All Companies' aggregation mode (reuses page state)"""
        page = CRMLeadsPage(self.browser.driver)
        
        if not page.select_all_companies():
            raise AssertionError("Failed to select 'All Companies' option")
        
        time.sleep(3)
        stats = page.get_dashboard_stats()
        print(f"   📊 All Companies Stats: Total={stats['total']}, New={stats['new']}, Won={stats['won']}")
        
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
    
    def test_crm_leads_table_display(self):
        """Test leads table displays correctly (reuses page state)"""
        page = CRMLeadsPage(self.browser.driver)
        
        leads_count = page.get_leads_count()
        is_empty = page.is_empty_state_visible()
        
        print(f"   📋 Leads in table: {leads_count}")
        self.browser.capture_console_logs()
    
    def test_crm_add_lead_modal(self):
        """Test Add Lead modal functionality (reuses page state)"""
        page = CRMLeadsPage(self.browser.driver)
        
        if not page.click_add_lead():
            raise AssertionError("Failed to click Add Lead button")
        
        time.sleep(1)
        if not page.is_lead_modal_open():
            raise AssertionError("Add Lead modal did not open")
        
        self.browser.driver.find_element("css selector", "button.btn-close").click()
        time.sleep(0.5)
        self.browser.capture_console_logs()
    
    def test_crm_view_lead_modal(self):
        """Test viewing lead details modal"""
        page = CRMLeadsPage(self.browser.driver)
        
        if page.get_leads_count() == 0:
            print("   ⏭️ Skipped: No leads in database to view")
            return
        
        if not page.click_first_lead_row():
            raise AssertionError("Failed to click first lead row")
        
        time.sleep(1)
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
    
    def test_crm_edit_lead_modal(self):
        """Test editing lead modal opens correctly"""
        page = CRMLeadsPage(self.browser.driver)
        
        if page.get_leads_count() == 0:
            print("   ⏭️ Skipped: No leads in database to edit")
            return
        
        if not page.click_edit_first_lead():
            raise AssertionError("Failed to click edit button")
        
        time.sleep(1)
        if not page.is_lead_modal_open():
            raise AssertionError("Edit modal did not open")
        
        self.browser.driver.find_element("css selector", "button.btn-close").click()
        time.sleep(0.5)
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
    
    def test_crm_vgk_delete_visibility(self):
        """Test VGK-only delete button visibility"""
        page = CRMLeadsPage(self.browser.driver)
        
        if page.get_leads_count() == 0:
            print("   ⏭️ Skipped: No leads in database to check delete button")
            return
        
        delete_visible = page.is_delete_button_visible()
        print(f"   🗑️ Delete button visible: {delete_visible} (VGK user should see it)")
        
        if not delete_visible:
            raise AssertionError("VGK user should see delete button but it's not visible")
        
        self.browser.capture_console_logs()
    
    def test_crm_lead_save(self):
        """Test saving a lead (edit existing)"""
        page = CRMLeadsPage(self.browser.driver)
        
        if page.get_leads_count() == 0:
            print("   ⏭️ Skipped: No leads in database to save")
            return
        
        if not page.click_edit_first_lead():
            raise AssertionError("Failed to open edit modal")
        
        time.sleep(1)
        
        if not page.save_lead():
            raise AssertionError("Failed to click save button")
        
        time.sleep(2)
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
        
        if self.browser.has_critical_errors():
            raise AssertionError("Critical errors detected during lead save")
    
    def run_crm_test_suite(self):
        """
        Run complete CRM Lead Management test suite
        DC Protocol: Dec 31, 2025
        """
        print("\n" + "="*70)
        print("🧪 CRM LEAD MANAGEMENT - VISIBLE BROWSER TEST")
        print("="*70)
        print(f"   Mode: {'Headless' if self.headless else 'VISIBLE BROWSER'}")
        print(f"   Base URL: {BASE_URL}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        tests = [
            ("Staff Login", self.test_staff_login),
            ("CRM Leads Page Load", self.test_crm_leads_page_load),
            ("CRM Company Selector", self.test_crm_company_selector),
            ("CRM All Companies Mode", self.test_crm_all_companies_mode),
            ("CRM Leads Table Display", self.test_crm_leads_table_display),
            ("CRM Add Lead Modal", self.test_crm_add_lead_modal),
            ("CRM View Lead Modal", self.test_crm_view_lead_modal),
            ("CRM Edit Lead Modal", self.test_crm_edit_lead_modal),
            ("CRM VGK Delete Visibility", self.test_crm_vgk_delete_visibility),
            ("CRM Lead Save", self.test_crm_lead_save),
        ]
        
        return self._run_test_list("CRM LEAD MANAGEMENT", tests)
    
    # ==================== MNR LEADS TESTS ====================
    
    def test_mnr_login(self):
        """Test MNR user login"""
        from frontend.tests.selenium.pages.crm_pages import MNRLeadsPage
        
        self.browser.driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        try:
            username_field = self.browser.driver.find_element(By.ID, "username")
            password_field = self.browser.driver.find_element(By.ID, "password")
            submit_btn = self.browser.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            
            mnr_username = os.environ.get('TEST_USER_MNR_ID', 'MNR182345842')
            mnr_password = os.environ.get('TEST_USER_PASSWORD', 'Test@123')
            
            username_field.clear()
            username_field.send_keys(mnr_username)
            password_field.clear()
            password_field.send_keys(mnr_password)
            submit_btn.click()
            
            time.sleep(3)
            
            if "/dashboard" in self.browser.driver.current_url or "/user/" in self.browser.driver.current_url:
                print(f"   ✅ MNR Login successful: {mnr_username}")
            else:
                raise AssertionError(f"MNR Login failed - URL: {self.browser.driver.current_url}")
                
        except Exception as e:
            raise AssertionError(f"MNR Login error: {e}")
    
    def test_mnr_leads_page_load(self):
        """Test MNR leads page loads correctly"""
        from frontend.tests.selenium.pages.crm_pages import MNRLeadsPage
        
        page = MNRLeadsPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("MNR Leads page failed to load")
        
        print(f"   ✅ MNR Leads page loaded")
        self.browser.capture_console_logs()
    
    def test_mnr_add_lead_modal(self):
        """Test MNR Add Lead modal with company selector"""
        from frontend.tests.selenium.pages.crm_pages import MNRLeadsPage
        
        page = MNRLeadsPage(self.browser.driver)
        
        if not page.click_add_lead():
            raise AssertionError("Failed to click Add Lead button")
        
        time.sleep(1)
        
        if not page.is_lead_modal_open():
            raise AssertionError("Add Lead modal did not open")
        
        if page.is_company_selector_in_form():
            print("   ✅ Company selector present in form (DC Protocol verified)")
        else:
            print("   ⚠️ Company selector not visible in form")
        
        self.browser.driver.find_element(By.CSS_SELECTOR, "button.btn-close").click()
        time.sleep(0.5)
    
    def test_mnr_view_lead(self):
        """Test MNR view lead with company_id context"""
        from frontend.tests.selenium.pages.crm_pages import MNRLeadsPage
        
        page = MNRLeadsPage(self.browser.driver)
        
        if page.get_leads_count() == 0:
            print("   ⏭️ Skipped: No leads assigned to MNR user")
            return
        
        if not page.click_view_first_lead():
            raise AssertionError("Failed to click view button")
        
        time.sleep(1)
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
    
    def run_mnr_test_suite(self):
        """Run MNR Leads test suite"""
        print("\n" + "="*70)
        print("🧪 MNR LEADS PAGE TEST SUITE")
        print("="*70)
        
        tests = [
            ("MNR Login", self.test_mnr_login),
            ("MNR Leads Page Load", self.test_mnr_leads_page_load),
            ("MNR Add Lead Modal", self.test_mnr_add_lead_modal),
            ("MNR View Lead", self.test_mnr_view_lead),
        ]
        
        return self._run_test_list("MNR LEADS", tests)
    
    # ==================== PARTNER LEADS TESTS ====================
    
    def test_partner_login(self):
        """Test Partner login"""
        from frontend.tests.selenium.pages.crm_pages import PartnerLeadsPage
        
        self.browser.driver.get(f"{BASE_URL}/partner-login")
        time.sleep(2)
        
        try:
            username_field = self.browser.driver.find_element(By.ID, "partner_code")
            password_field = self.browser.driver.find_element(By.ID, "password")
            submit_btn = self.browser.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            
            partner_code = os.environ.get('TEST_PARTNER_CODE', 'DLR001')
            partner_password = os.environ.get('TEST_PARTNER_PASSWORD', 'Test@123')
            
            username_field.clear()
            username_field.send_keys(partner_code)
            password_field.clear()
            password_field.send_keys(partner_password)
            submit_btn.click()
            
            time.sleep(3)
            
            if "/partner/" in self.browser.driver.current_url:
                print(f"   ✅ Partner Login successful: {partner_code}")
            else:
                raise AssertionError(f"Partner Login failed - URL: {self.browser.driver.current_url}")
                
        except Exception as e:
            raise AssertionError(f"Partner Login error: {e}")
    
    def test_partner_leads_page_load(self):
        """Test Partner leads page loads correctly"""
        from frontend.tests.selenium.pages.crm_pages import PartnerLeadsPage
        
        page = PartnerLeadsPage(self.browser.driver)
        page.navigate()
        
        if not page.verify_loaded():
            raise AssertionError("Partner Leads page failed to load")
        
        print(f"   ✅ Partner Leads page loaded")
        self.browser.capture_console_logs()
    
    def test_partner_add_lead_modal(self):
        """Test Partner Add Lead modal with company selector"""
        from frontend.tests.selenium.pages.crm_pages import PartnerLeadsPage
        
        page = PartnerLeadsPage(self.browser.driver)
        
        if not page.click_add_lead():
            raise AssertionError("Failed to click Add Lead button")
        
        time.sleep(1)
        
        if not page.is_lead_modal_open():
            raise AssertionError("Add Lead modal did not open")
        
        if page.is_company_selector_in_form():
            print("   ✅ Company selector present in form (DC Protocol verified)")
        else:
            print("   ⚠️ Company selector not visible in form")
        
        self.browser.driver.find_element(By.CSS_SELECTOR, "button.btn-close").click()
        time.sleep(0.5)
    
    def test_partner_view_lead(self):
        """Test Partner view lead with company_id context"""
        from frontend.tests.selenium.pages.crm_pages import PartnerLeadsPage
        
        page = PartnerLeadsPage(self.browser.driver)
        
        if page.get_leads_count() == 0:
            print("   ⏭️ Skipped: No leads assigned to Partner user")
            return
        
        if not page.click_view_first_lead():
            raise AssertionError("Failed to click view button")
        
        time.sleep(1)
        self.browser.capture_console_logs()
        self.browser.capture_network_errors()
    
    def run_partner_test_suite(self):
        """Run Partner Leads test suite"""
        print("\n" + "="*70)
        print("🧪 PARTNER LEADS PAGE TEST SUITE")
        print("="*70)
        
        tests = [
            ("Partner Login", self.test_partner_login),
            ("Partner Leads Page Load", self.test_partner_leads_page_load),
            ("Partner Add Lead Modal", self.test_partner_add_lead_modal),
            ("Partner View Lead", self.test_partner_view_lead),
        ]
        
        return self._run_test_list("PARTNER LEADS", tests)
    
    def _run_test_list(self, suite_name: str, tests: list) -> dict:
        """Generic test runner for any test list"""
        results = {
            'passed': 0,
            'failed': 0,
            'blocked': 0,
            'tests': []
        }
        
        try:
            self.setup()
            
            for i, (test_name, test_func) in enumerate(tests, 1):
                print(f"\n[{i}/{len(tests)}] Running: {test_name}")
                
                try:
                    test_func()
                    
                    self.browser.dismiss_alert()
                    
                    errors = self.error_handler.run_all_detections()
                    critical_errors = [e for e in errors if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]]
                    
                    if critical_errors:
                        results['failed'] += 1
                        results['tests'].append({
                            'name': test_name,
                            'status': 'FAILED',
                            'errors': [e.message for e in critical_errors[:3]]
                        })
                        
                        print(f"   ❌ FAILED: {len(critical_errors)} error(s) detected")
                        self.browser.take_screenshot(f"FAIL_{test_name.replace(' ', '_')}")
                        
                        self.error_handler.print_error_report()
                        
                        print("\n⛔ EXECUTION STOPPED - Fix required")
                        
                        for remaining in tests[i:]:
                            results['blocked'] += 1
                            results['tests'].append({
                                'name': remaining[0],
                                'status': 'BLOCKED'
                            })
                        break
                    else:
                        results['passed'] += 1
                        results['tests'].append({
                            'name': test_name,
                            'status': 'PASSED'
                        })
                        print(f"   ✅ PASSED")
                        
                    self.error_handler.clear_errors()
                    
                except AssertionError as e:
                    results['failed'] += 1
                    results['tests'].append({
                        'name': test_name,
                        'status': 'FAILED',
                        'error': str(e)
                    })
                    print(f"   ❌ ASSERTION FAILED: {e}")
                    self.browser.take_screenshot(f"ASSERT_{test_name.replace(' ', '_')}")
                    
                except Exception as e:
                    results['failed'] += 1
                    results['tests'].append({
                        'name': test_name,
                        'status': 'ERROR',
                        'error': str(e)[:100]
                    })
                    print(f"   ❌ ERROR: {str(e)[:80]}")
                    
        except Exception as e:
            print(f"\n❌ SETUP ERROR: {e}")
            
        finally:
            self.teardown()
            
        self._print_summary(results)
        
        return results
        
    def run_full_income_withdrawal_flow(self):
        """
        Run complete Income -> Withdrawal flow test suite
        With strict DC Protocol error handling
        """
        print("\n" + "="*70)
        print("🧪 INCOME & WITHDRAWAL FLOW - VISIBLE BROWSER TEST")
        print("="*70)
        print(f"   Mode: {'Headless' if self.headless else 'VISIBLE BROWSER'}")
        print(f"   Base URL: {BASE_URL}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        tests = [
            ("Staff Login", self.test_staff_login),
            ("Income Records Page", self.test_income_records_page),
            ("Income Supreme Page", self.test_income_supreme_page),
            ("Finance Complete Page", self.test_finance_complete_page),
            ("Withdrawal Dashboard", self.test_withdrawal_dashboard_page),
            ("Withdrawal Approvals", self.test_withdrawal_approvals_page),
            ("Withdrawal History", self.test_withdrawal_history_page),
            ("Withdrawal Supreme", self.test_withdrawal_supreme_page),
        ]
        
        results = {
            'passed': 0,
            'failed': 0,
            'blocked': 0,
            'tests': []
        }
        
        try:
            self.setup()
            
            for i, (test_name, test_func) in enumerate(tests, 1):
                print(f"\n[{i}/{len(tests)}] Running: {test_name}")
                
                try:
                    test_func()
                    
                    self.browser.dismiss_alert()
                    
                    errors = self.error_handler.run_all_detections()
                    critical_errors = [e for e in errors if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]]
                    
                    if critical_errors:
                        results['failed'] += 1
                        results['tests'].append({
                            'name': test_name,
                            'status': 'FAILED',
                            'errors': [e.message for e in critical_errors[:3]]
                        })
                        
                        print(f"   ❌ FAILED: {len(critical_errors)} error(s) detected")
                        self.browser.take_screenshot(f"FAIL_{test_name.replace(' ', '_')}")
                        
                        self.error_handler.print_error_report()
                        
                        print("\n⛔ EXECUTION STOPPED - Fix required")
                        
                        for remaining in tests[i:]:
                            results['blocked'] += 1
                            results['tests'].append({
                                'name': remaining[0],
                                'status': 'BLOCKED'
                            })
                        break
                    else:
                        results['passed'] += 1
                        results['tests'].append({
                            'name': test_name,
                            'status': 'PASSED'
                        })
                        print(f"   ✅ PASSED")
                        
                    self.error_handler.clear_errors()
                    
                except AssertionError as e:
                    results['failed'] += 1
                    results['tests'].append({
                        'name': test_name,
                        'status': 'FAILED',
                        'error': str(e)
                    })
                    print(f"   ❌ ASSERTION FAILED: {e}")
                    self.browser.take_screenshot(f"ASSERT_{test_name.replace(' ', '_')}")
                    
                except Exception as e:
                    results['failed'] += 1
                    results['tests'].append({
                        'name': test_name,
                        'status': 'ERROR',
                        'error': str(e)[:100]
                    })
                    print(f"   ❌ ERROR: {str(e)[:80]}")
                    
        except Exception as e:
            print(f"\n❌ SETUP ERROR: {e}")
            
        finally:
            self.teardown()
            
        self._print_summary(results)
        
        return results
        
    def _print_summary(self, results: dict):
        """Print test execution summary"""
        print("\n" + "="*70)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*70)
        print(f"   ✅ Passed: {results['passed']}")
        print(f"   ❌ Failed: {results['failed']}")
        print(f"   ⏸️ Blocked: {results['blocked']}")
        total = results['passed'] + results['failed'] + results['blocked']
        print(f"   📋 Total: {total}")
        print("="*70)
        
        if results['failed'] > 0:
            print("\n⚠️ FAILED TESTS REQUIRE ATTENTION:")
            for test in results['tests']:
                if test['status'] in ['FAILED', 'ERROR']:
                    print(f"   ❌ {test['name']}")
                    if 'errors' in test:
                        for err in test['errors'][:2]:
                            print(f"      - {err[:60]}")
            print("\n⛔ Fix all errors and re-run validation")
        elif results['blocked'] > 0:
            print("\n⚠️ Some tests were blocked due to earlier failures")
        else:
            print("\n✅ ALL TESTS PASSED - No errors detected")
            
        print("="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DC Protocol: Frontend Selenium Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--headless', '-H',
        action='store_true',
        help='Run in headless mode (invisible browser)'
    )
    
    parser.add_argument(
        '--vnc',
        action='store_true', 
        help='Run with VNC desktop output'
    )
    
    parser.add_argument(
        '--test', '-t',
        type=str,
        help='Run specific test by name'
    )
    
    parser.add_argument(
        '--suite', '-s',
        type=str,
        choices=['income', 'withdrawal', 'crm', 'mnr', 'partner', 'leads', 'all'],
        default='all',
        help='Run specific test suite (income, withdrawal, crm, mnr, partner, leads=all CRM suites, all)'
    )
    
    args = parser.parse_args()
    
    suite = FrontendTestSuite(
        headless=args.headless,
        vnc_mode=args.vnc
    )
    
    all_results = {'passed': 0, 'failed': 0, 'blocked': 0}
    
    if args.suite == 'crm':
        results = suite.run_crm_test_suite()
    elif args.suite == 'mnr':
        results = suite.run_mnr_test_suite()
    elif args.suite == 'partner':
        results = suite.run_partner_test_suite()
    elif args.suite == 'leads':
        results1 = suite.run_crm_test_suite()
        all_results['passed'] += results1['passed']
        all_results['failed'] += results1['failed']
        all_results['blocked'] += results1['blocked']
        
        suite2 = FrontendTestSuite(headless=args.headless, vnc_mode=args.vnc)
        results2 = suite2.run_mnr_test_suite()
        all_results['passed'] += results2['passed']
        all_results['failed'] += results2['failed']
        all_results['blocked'] += results2['blocked']
        
        suite3 = FrontendTestSuite(headless=args.headless, vnc_mode=args.vnc)
        results3 = suite3.run_partner_test_suite()
        all_results['passed'] += results3['passed']
        all_results['failed'] += results3['failed']
        all_results['blocked'] += results3['blocked']
        
        print("\n" + "="*70)
        print("📊 LEADS TEST SUMMARY - CRM + MNR + PARTNER")
        print("="*70)
        print(f"   ✅ Total Passed: {all_results['passed']}")
        print(f"   ❌ Total Failed: {all_results['failed']}")
        print(f"   ⏸️ Total Blocked: {all_results['blocked']}")
        print("="*70)
        results = all_results
    elif args.suite == 'income' or args.suite == 'withdrawal':
        results = suite.run_full_income_withdrawal_flow()
    else:
        print("\n" + "="*70)
        print("🧪 RUNNING ALL TEST SUITES")
        print("="*70)
        
        results1 = suite.run_full_income_withdrawal_flow()
        all_results['passed'] += results1['passed']
        all_results['failed'] += results1['failed']
        all_results['blocked'] += results1['blocked']
        
        suite2 = FrontendTestSuite(headless=args.headless, vnc_mode=args.vnc)
        results2 = suite2.run_crm_test_suite()
        all_results['passed'] += results2['passed']
        all_results['failed'] += results2['failed']
        all_results['blocked'] += results2['blocked']
        
        suite3 = FrontendTestSuite(headless=args.headless, vnc_mode=args.vnc)
        results3 = suite3.run_mnr_test_suite()
        all_results['passed'] += results3['passed']
        all_results['failed'] += results3['failed']
        all_results['blocked'] += results3['blocked']
        
        suite4 = FrontendTestSuite(headless=args.headless, vnc_mode=args.vnc)
        results4 = suite4.run_partner_test_suite()
        all_results['passed'] += results4['passed']
        all_results['failed'] += results4['failed']
        all_results['blocked'] += results4['blocked']
        
        print("\n" + "="*70)
        print("📊 OVERALL SUMMARY - ALL SUITES")
        print("="*70)
        print(f"   ✅ Total Passed: {all_results['passed']}")
        print(f"   ❌ Total Failed: {all_results['failed']}")
        print(f"   ⏸️ Total Blocked: {all_results['blocked']}")
        print("="*70)
        
        results = all_results
    
    if results['failed'] > 0 or results['blocked'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
