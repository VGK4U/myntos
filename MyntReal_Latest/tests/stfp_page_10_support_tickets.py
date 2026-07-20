"""STFP Page #10: Support Tickets - Complete Testing"""
import time, os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost:5000"
VGK_USERNAME = "BEV182364369"
VGK_PASSWORD = os.getenv('VGK_TEST_PASSWORD', 'Test@123')

def login(driver):
    driver.get(f"{BASE_URL}/login.html")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(VGK_USERNAME)
    driver.find_element(By.ID, "password").send_keys(VGK_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)

def main():
    print("="*80)
    print(" "*21 + "STFP PAGE #10: SUPPORT TICKETS")
    print("="*80)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        login(driver)
        driver.get(f"{BASE_URL}/admin/tickets")
        time.sleep(3)
        
        page_source = driver.page_source
        logs = driver.get_log('browser')
        errors = [l for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l['message']]
        
        print(f"\n✓ Page loaded: {'/tickets' in driver.current_url}")
        print(f"✓ Title present: {'Ticket' in page_source or 'Support' in page_source}")
        print(f"{'✓' if not errors else '✗'} Console errors: {len(errors)}")
        if errors:
            for e in errors[:2]:
                print(f"  - {e['message'][:100]}")
        
        return 0 if not errors else 1
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return 1
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
