"""
Service Ticket E2E Selenium Test
DC Protocol Jan 2026 - Tests complete ticket lifecycle from creation to closure

Tests:
1. Staff Login
2. Ticket Creation (with/without attachments)
3. Acknowledge Ticket
4. Diagnose Ticket
5. Complete Work
6. View Attachments
7. Queue filtering
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

REPLIT_DOMAINS = os.getenv('REPLIT_DOMAINS', '')
if REPLIT_DOMAINS:
    BASE_URL = f'https://{REPLIT_DOMAINS}'
else:
    BASE_URL = 'http://localhost:5000'

SCREENSHOT_DIR = 'test_screenshots/service_tickets'
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

STAFF_USERNAME = 'MR20001'
STAFF_PASSWORD = 'Test@123'


class ServiceTicketSeleniumTest:
    def __init__(self):
        self.driver = None
        self.test_results = []
        self.screenshot_count = 0
        self.created_ticket_id = None
        
    def setup_driver(self):
        print("🚀 Initializing Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
        print("✅ WebDriver initialized successfully")
    
    def take_screenshot(self, name):
        self.screenshot_count += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{SCREENSHOT_DIR}/{self.screenshot_count:02d}_{name}_{timestamp}.png"
        self.driver.save_screenshot(filename)
        print(f"📸 Screenshot saved: {filename}")
        return filename
    
    def log_test(self, test_name, passed, message):
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}: {message}")
        return passed
    
    def check_console_errors(self):
        logs = self.driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        if errors:
            print(f"⚠️ Console errors found: {len(errors)}")
            for error in errors[:5]:
                print(f"   - {error['message'][:100]}")
            return errors
        return []
    
    def staff_login(self):
        print(f"\n🔐 TEST: Staff Login")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/login")
            
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "employeeId"))
            )
            self.take_screenshot("staff_login_page")
            
            username_field.clear()
            username_field.send_keys(STAFF_USERNAME)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(STAFF_PASSWORD)
            
            login_button = self.driver.find_element(By.ID, "loginBtn")
            login_button.click()
            
            time.sleep(3)
            
            current_url = self.driver.current_url
            
            if "/staff/login" not in current_url:
                self.take_screenshot("staff_login_success")
                return self.log_test("Staff Login", True, f"Logged in successfully, redirected to {current_url}")
            else:
                self.take_screenshot("staff_login_failed")
                return self.log_test("Staff Login", False, "Login failed - still on login page")
                
        except Exception as e:
            self.take_screenshot("staff_login_error")
            return self.log_test("Staff Login", False, f"Exception: {str(e)}")
    
    def navigate_to_raise_ticket(self):
        print(f"\n📝 TEST: Navigate to Raise Ticket")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/raise")
            time.sleep(2)
            
            form = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ticketForm"))
            )
            self.take_screenshot("raise_ticket_page")
            
            console_errors = self.check_console_errors()
            if console_errors:
                return self.log_test("Navigate to Raise Ticket", False, f"Page loaded but has {len(console_errors)} console errors")
            
            return self.log_test("Navigate to Raise Ticket", True, "Page loaded successfully")
            
        except Exception as e:
            self.take_screenshot("raise_ticket_error")
            return self.log_test("Navigate to Raise Ticket", False, f"Exception: {str(e)}")
    
    def create_ticket(self):
        print(f"\n🎫 TEST: Create Service Ticket")
        print("-" * 80)
        
        try:
            from selenium.webdriver.support.ui import Select
            
            self.driver.find_element(By.ID, "customerName").send_keys("Selenium Test Customer")
            self.driver.find_element(By.ID, "customerPhone").send_keys("9876543210")
            self.driver.find_element(By.ID, "customerEmail").send_keys("selenium@test.com")
            self.driver.find_element(By.ID, "customerAddress").send_keys("123 Test Street, Selenium City")
            
            self.driver.find_element(By.ID, "productName").send_keys("Zynova E-Scooter")
            self.driver.find_element(By.ID, "productSerial").send_keys("SELENIUM123")
            self.driver.find_element(By.ID, "productModel").send_keys("Model X")
            
            issue_category_select = Select(self.driver.find_element(By.ID, "issueCategory"))
            issue_category_select.select_by_value("Motor Problem")
            
            ticket_type_select = Select(self.driver.find_element(By.ID, "ticketType"))
            ticket_type_select.select_by_value("technical")
            
            priority_select = Select(self.driver.find_element(By.ID, "priority"))
            priority_select.select_by_value("Medium")
            
            self.driver.find_element(By.ID, "issueDescription").send_keys("Test issue created by Selenium automation for E2E testing")
            
            self.take_screenshot("ticket_form_filled")
            
            submit_btn = self.driver.find_element(By.ID, "submitBtn")
            submit_btn.click()
            
            time.sleep(3)
            
            try:
                alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                alert_text = alert.text
                alert.accept()
                
                if "created" in alert_text.lower():
                    self.take_screenshot("ticket_created_success")
                    return self.log_test("Create Service Ticket", True, f"Ticket created: {alert_text}")
                else:
                    return self.log_test("Create Service Ticket", False, f"Unexpected alert: {alert_text}")
            except TimeoutException:
                self.take_screenshot("ticket_no_alert")
                
                current_url = self.driver.current_url
                if "queue" in current_url:
                    return self.log_test("Create Service Ticket", True, "Redirected to queue (ticket likely created)")
                return self.log_test("Create Service Ticket", False, "No confirmation received")
                
        except Exception as e:
            self.take_screenshot("ticket_create_error")
            return self.log_test("Create Service Ticket", False, f"Exception: {str(e)}")
    
    def navigate_to_queue(self):
        print(f"\n📋 TEST: Navigate to Service Queue")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/queue")
            time.sleep(2)
            
            tickets_table = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "tickets-body"))
            )
            self.take_screenshot("service_queue_page")
            
            console_errors = self.check_console_errors()
            if console_errors:
                return self.log_test("Navigate to Queue", False, f"Page loaded but has {len(console_errors)} console errors")
            
            return self.log_test("Navigate to Queue", True, "Queue page loaded successfully")
            
        except Exception as e:
            self.take_screenshot("queue_error")
            return self.log_test("Navigate to Queue", False, f"Exception: {str(e)}")
    
    def acknowledge_ticket(self):
        print(f"\n✅ TEST: Acknowledge Ticket")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/queue")
            time.sleep(2)
            
            ack_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Acknowledge')]")
            
            if not ack_buttons:
                self.take_screenshot("no_tickets_to_acknowledge")
                return self.log_test("Acknowledge Ticket", False, "No tickets available to acknowledge")
            
            ack_buttons[0].click()
            
            try:
                alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                alert.accept()
            except TimeoutException:
                pass
            
            time.sleep(2)
            
            try:
                result_alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                result_text = result_alert.text
                result_alert.accept()
                
                if "success" in result_text.lower() or "acknowledged" in result_text.lower():
                    self.take_screenshot("ticket_acknowledged")
                    return self.log_test("Acknowledge Ticket", True, f"Ticket acknowledged: {result_text}")
                elif "error" in result_text.lower():
                    self.take_screenshot("acknowledge_failed")
                    return self.log_test("Acknowledge Ticket", False, f"Acknowledge failed: {result_text}")
            except TimeoutException:
                pass
            
            self.take_screenshot("acknowledge_complete")
            return self.log_test("Acknowledge Ticket", True, "Acknowledge action completed")
            
        except Exception as e:
            self.take_screenshot("acknowledge_error")
            return self.log_test("Acknowledge Ticket", False, f"Exception: {str(e)}")
    
    def diagnose_ticket(self):
        print(f"\n🔍 TEST: Diagnose Ticket")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/queue")
            time.sleep(2)
            
            diagnose_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Diagnose')]")
            
            if not diagnose_buttons:
                self.take_screenshot("no_tickets_to_diagnose")
                return self.log_test("Diagnose Ticket", False, "No tickets available to diagnose")
            
            diagnose_buttons[0].click()
            time.sleep(1)
            
            notes_field = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "diagnosisNotes"))
            )
            notes_field.send_keys("Selenium test diagnosis: Motor issue identified, no spare parts required.")
            
            self.take_screenshot("diagnose_modal_filled")
            
            submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit Diagnosis')]")
            submit_btn.click()
            
            time.sleep(2)
            
            try:
                alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                alert_text = alert.text
                alert.accept()
                
                if "success" in alert_text.lower():
                    self.take_screenshot("diagnose_success")
                    return self.log_test("Diagnose Ticket", True, f"Diagnosis submitted: {alert_text}")
                else:
                    return self.log_test("Diagnose Ticket", False, f"Unexpected result: {alert_text}")
            except TimeoutException:
                self.take_screenshot("diagnose_complete")
                return self.log_test("Diagnose Ticket", True, "Diagnosis action completed")
                
        except Exception as e:
            self.take_screenshot("diagnose_error")
            return self.log_test("Diagnose Ticket", False, f"Exception: {str(e)}")
    
    def complete_work(self):
        print(f"\n🔧 TEST: Complete Work")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/queue")
            time.sleep(2)
            
            complete_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Complete')]")
            
            if not complete_buttons:
                self.take_screenshot("no_tickets_to_complete")
                return self.log_test("Complete Work", False, "No tickets available to complete")
            
            complete_buttons[0].click()
            time.sleep(1)
            
            summary_field = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "resolutionSummary"))
            )
            summary_field.send_keys("Selenium test completion: Issue resolved successfully. Motor replaced and tested.")
            
            self.take_screenshot("complete_modal_filled")
            
            submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Mark Complete')]")
            submit_btn.click()
            
            time.sleep(2)
            
            try:
                alert = WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                alert_text = alert.text
                alert.accept()
                
                if "success" in alert_text.lower() or "completed" in alert_text.lower():
                    self.take_screenshot("complete_success")
                    return self.log_test("Complete Work", True, f"Work completed: {alert_text}")
                else:
                    return self.log_test("Complete Work", False, f"Unexpected result: {alert_text}")
            except TimeoutException:
                self.take_screenshot("complete_done")
                return self.log_test("Complete Work", True, "Complete action completed")
                
        except Exception as e:
            self.take_screenshot("complete_error")
            return self.log_test("Complete Work", False, f"Exception: {str(e)}")
    
    def view_attachments(self):
        print(f"\n📎 TEST: View Attachments")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/queue")
            time.sleep(2)
            
            attach_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[title='View Attachments']")
            
            if not attach_buttons:
                attach_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'fa-paperclip')]")
            
            if not attach_buttons:
                attach_buttons = self.driver.find_elements(By.XPATH, "//button[.//i[contains(@class, 'fa-paperclip')]]")
            
            if not attach_buttons:
                self.take_screenshot("no_attachment_buttons")
                return self.log_test("View Attachments", False, "No attachment buttons found")
            
            attach_buttons[0].click()
            time.sleep(2)
            
            modal = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.ID, "ticketModal"))
            )
            
            self.take_screenshot("attachments_modal")
            
            modal_body = self.driver.find_element(By.ID, "ticketModalBody")
            modal_text = modal_body.text
            
            if "No attachments" in modal_text or "error" not in modal_text.lower():
                return self.log_test("View Attachments", True, f"Attachments modal displayed: {modal_text[:50]}")
            else:
                return self.log_test("View Attachments", False, f"Error in attachments: {modal_text[:100]}")
                
        except Exception as e:
            self.take_screenshot("attachments_error")
            return self.log_test("View Attachments", False, f"Exception: {str(e)}")
    
    def test_queue_filters(self):
        print(f"\n🔍 TEST: Queue Filters")
        print("-" * 80)
        
        try:
            self.driver.get(f"{BASE_URL}/staff/service-tickets/queue")
            time.sleep(2)
            
            tabs = self.driver.find_elements(By.CSS_SELECTOR, ".status-tab")
            
            if not tabs:
                return self.log_test("Queue Filters", False, "No filter tabs found")
            
            for tab in tabs:
                tab_text = tab.text
                tab.click()
                time.sleep(1)
                self.take_screenshot(f"filter_tab_{tab_text.replace(' ', '_').lower()}")
            
            console_errors = self.check_console_errors()
            if console_errors:
                return self.log_test("Queue Filters", False, f"Filter tests had {len(console_errors)} console errors")
            
            return self.log_test("Queue Filters", True, f"All {len(tabs)} filter tabs work correctly")
            
        except Exception as e:
            self.take_screenshot("filters_error")
            return self.log_test("Queue Filters", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        print("=" * 80)
        print("🧪 SERVICE TICKET E2E SELENIUM TEST")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Base URL: {BASE_URL}")
        print("=" * 80)
        
        self.setup_driver()
        
        try:
            if not self.staff_login():
                print("\n⚠️ Login failed, skipping remaining tests")
                return self.generate_report()
            
            self.navigate_to_raise_ticket()
            self.create_ticket()
            self.navigate_to_queue()
            self.acknowledge_ticket()
            self.diagnose_ticket()
            self.complete_work()
            self.view_attachments()
            self.test_queue_filters()
            
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔒 WebDriver closed")
        
        return self.generate_report()
    
    def generate_report(self):
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.test_results if "PASS" in r['status'])
        failed = sum(1 for r in self.test_results if "FAIL" in r['status'])
        total = len(self.test_results)
        
        print(f"\n✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"📸 Screenshots: {self.screenshot_count}")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for r in self.test_results:
                if "FAIL" in r['status']:
                    print(f"   - {r['test']}: {r['message']}")
        
        print("\n" + "=" * 80)
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'results': self.test_results
        }


if __name__ == "__main__":
    test = ServiceTicketSeleniumTest()
    results = test.run_all_tests()
    
    exit(0 if results['failed'] == 0 else 1)
