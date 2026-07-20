"""
STGF (Staff Test GUI Framework) - KRA Update Flow Testing
DC Protocol: Write → Verify → Validate
Testing: Click icon → Update status → Verify reflection
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class KRAUpdateSTGF:
    def __init__(self):
        self.driver = None
        self.base_url = "http://localhost:5000"
        self.results = {
            "dc_phase1_write": False,
            "dc_phase2_verify": False,
            "dc_phase3_validate": False,
            "errors": []
        }
    
    def setup(self):
        """Initialize Selenium WebDriver"""
        print("\n[STGF-INIT] Setting up Selenium WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        print("[STGF-INIT] ✅ WebDriver initialized")
    
    def navigate_to_kra_sheet(self):
        """DC-PHASE1-WRITE: Navigate to KRA tracking sheet"""
        print("\n[DC-PHASE1-WRITE] Navigating to KRA tracking sheet...")
        self.driver.get(f"{self.base_url}/staff/my-kras")
        time.sleep(2)
        
        # Wait for page to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "kra-tracking-section"))
            )
            print("[DC-PHASE1-WRITE] ✅ KRA tracking sheet loaded")
            self.results["dc_phase1_write"] = True
            return True
        except Exception as e:
            self.results["errors"].append(f"Page load failed: {str(e)}")
            print(f"[DC-PHASE1-WRITE] ❌ Failed to load: {e}")
            return False
    
    def find_first_pending_icon(self):
        """DC-PHASE2-VERIFY: Find first yellow pending (⏳) icon"""
        print("\n[DC-PHASE2-VERIFY] Finding first pending icon...")
        try:
            # Get all yellow icons (pending status)
            pending_icons = self.driver.find_elements(
                By.XPATH, 
                "//span[@title='Pending (⏳)'] | //i[@data-status='pending']"
            )
            
            if not pending_icons:
                # Fallback: find any yellow badge
                pending_icons = self.driver.find_elements(
                    By.XPATH,
                    "//span[contains(@class, 'badge') and contains(text(), '⏳')]"
                )
            
            if not pending_icons:
                # Last fallback: get the first cell in the tracking grid
                cells = self.driver.find_elements(
                    By.XPATH,
                    "//table[@class='table table-sm table-fixed']//td//span[@data-instance-id]"
                )
                
                if cells:
                    pending_icons = [c for c in cells if '⏳' in c.text or 'pending' in c.get_attribute('data-status').lower()]
            
            if pending_icons:
                target_icon = pending_icons[0]
                # Get surrounding context
                parent_row = target_icon.find_element(By.XPATH, "ancestor::tr")
                kra_name = parent_row.find_element(By.XPATH, ".//td[1]").text
                instance_id = target_icon.get_attribute("data-instance-id")
                
                print(f"[DC-PHASE2-VERIFY] ✅ Found pending icon:")
                print(f"  - KRA: {kra_name}")
                print(f"  - Instance ID: {instance_id}")
                print(f"  - Current Status: Pending (⏳)")
                
                self.results["dc_phase2_verify"] = True
                return target_icon, instance_id, kra_name
            else:
                self.results["errors"].append("No pending icons found")
                print("[DC-PHASE2-VERIFY] ❌ No pending icons found in table")
                return None, None, None
        
        except Exception as e:
            self.results["errors"].append(f"Finding icon failed: {str(e)}")
            print(f"[DC-PHASE2-VERIFY] ❌ Error finding icon: {e}")
            return None, None, None
    
    def click_and_update_status(self, icon, target_status="completed"):
        """DC-PHASE1-WRITE: Click icon and update status in modal"""
        print(f"\n[DC-PHASE1-WRITE] Clicking icon and updating to '{target_status}'...")
        try:
            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", icon)
            time.sleep(0.5)
            
            # Click the icon
            icon.click()
            print("[DC-PHASE1-WRITE] ✅ Icon clicked")
            
            # Wait for modal
            modal = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "statusModalLabel"))
            )
            print("[DC-PHASE1-WRITE] ✅ Modal appeared")
            
            # Select new status from dropdown
            status_select = self.driver.find_element(By.ID, "statusSelect")
            status_select.click()
            time.sleep(0.3)
            
            # Find and click the option
            option_xpath = f"//option[contains(text(), '{target_status.title()}')]"
            option = self.driver.find_element(By.XPATH, option_xpath)
            option.click()
            print(f"[DC-PHASE1-WRITE] ✅ Selected status: {target_status}")
            
            # Click update button
            update_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Update')]")
            update_btn.click()
            print("[DC-PHASE1-WRITE] ✅ Update button clicked")
            
            # Wait for success alert
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
            )
            print("[DC-PHASE1-WRITE] ✅ Success alert shown - Backend accepted update")
            
            # Close alert
            time.sleep(1)
            return True
        
        except Exception as e:
            self.results["errors"].append(f"Update failed: {str(e)}")
            print(f"[DC-PHASE1-WRITE] ❌ Update error: {e}")
            return False
    
    def verify_status_changed_in_dom(self, instance_id, new_status="completed"):
        """DC-PHASE2-VERIFY: Check if DOM reflects the change (before page refresh)"""
        print(f"\n[DC-PHASE2-VERIFY] Checking DOM for status change...")
        try:
            # Wait for page to settle
            time.sleep(1)
            
            # Find the icon element
            icon_element = self.driver.find_element(
                By.XPATH,
                f"//span[@data-instance-id='{instance_id}']"
            )
            
            current_html = icon_element.get_attribute("innerHTML")
            current_title = icon_element.get_attribute("title")
            
            print(f"[DC-PHASE2-VERIFY] Icon HTML: {current_html}")
            print(f"[DC-PHASE2-VERIFY] Icon Title: {current_title}")
            
            # Check if it changed
            if "completed" in current_html.lower() or "✅" in current_title:
                print(f"[DC-PHASE2-VERIFY] ✅ DOM updated to show: Completed")
                return True
            else:
                print(f"[DC-PHASE2-VERIFY] ❌ DOM still shows old status")
                return False
        
        except Exception as e:
            self.results["errors"].append(f"DOM verification failed: {str(e)}")
            print(f"[DC-PHASE2-VERIFY] ⚠️ DOM check error: {e}")
            return False
    
    def refresh_and_validate(self, instance_id):
        """DC-PHASE3-VALIDATE: Refresh page and verify update persisted"""
        print(f"\n[DC-PHASE3-VALIDATE] Refreshing page to validate persistence...")
        try:
            self.driver.refresh()
            time.sleep(2)
            
            # Wait for table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "kra-tracking-section"))
            )
            print("[DC-PHASE3-VALIDATE] ✅ Page reloaded")
            
            # Find the instance and check status
            icon_element = self.driver.find_element(
                By.XPATH,
                f"//span[@data-instance-id='{instance_id}']"
            )
            
            final_html = icon_element.get_attribute("innerHTML")
            final_title = icon_element.get_attribute("title")
            
            print(f"[DC-PHASE3-VALIDATE] Final Icon HTML: {final_html}")
            print(f"[DC-PHASE3-VALIDATE] Final Icon Title: {final_title}")
            
            if "completed" in final_html.lower() or "✅" in final_title:
                print(f"[DC-PHASE3-VALIDATE] ✅ Update persisted after refresh!")
                self.results["dc_phase3_validate"] = True
                return True
            else:
                print(f"[DC-PHASE3-VALIDATE] ❌ Update NOT persisted - Still showing old status")
                self.results["errors"].append("Update did not persist after refresh")
                return False
        
        except Exception as e:
            self.results["errors"].append(f"Validation failed: {str(e)}")
            print(f"[DC-PHASE3-VALIDATE] ❌ Validation error: {e}")
            return False
    
    def run_full_test(self):
        """Execute complete DC protocol test"""
        print("\n" + "="*70)
        print("STGF: KRA Update Flow Test - DC Protocol Compliance")
        print("="*70)
        
        try:
            self.setup()
            
            if not self.navigate_to_kra_sheet():
                return False
            
            icon, instance_id, kra_name = self.find_first_pending_icon()
            if not icon:
                return False
            
            if not self.click_and_update_status(icon, "completed"):
                return False
            
            dom_updated = self.verify_status_changed_in_dom(instance_id, "completed")
            
            if not self.refresh_and_validate(instance_id):
                return False
            
            print("\n" + "="*70)
            print("STGF TEST RESULTS")
            print("="*70)
            print(f"✅ DC-PHASE1-WRITE (Backend Accept): {self.results['dc_phase1_write']}")
            print(f"{'⚠️' if dom_updated else '❌'} DC-PHASE2-VERIFY (Frontend Update): {dom_updated}")
            print(f"{'✅' if self.results['dc_phase3_validate'] else '❌'} DC-PHASE3-VALIDATE (Persistence): {self.results['dc_phase3_validate']}")
            
            if self.results["errors"]:
                print("\n⚠️ ERRORS ENCOUNTERED:")
                for err in self.results["errors"]:
                    print(f"  - {err}")
            
            return all([
                self.results["dc_phase1_write"],
                dom_updated,
                self.results["dc_phase3_validate"]
            ])
        
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    test = KRAUpdateSTGF()
    success = test.run_full_test()
    exit(0 if success else 1)
