#!/usr/bin/env python3
"""Check for JavaScript errors on bonanza page"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    return driver

driver = setup_driver()

# Login
driver.get("http://localhost:5000/login")
time.sleep(1)

username = driver.find_element(By.ID, "username")
password = driver.find_element(By.ID, "password")
username.send_keys("BEV182371007")
password.send_keys("superadmin123")
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
time.sleep(2)

# Go to bonanza page
driver.get("http://localhost:5000/superadmin/bonanza")
time.sleep(2)

# Get console logs
logs = driver.get_log('browser')

print("\n" + "="*80)
print("JAVASCRIPT CONSOLE ERRORS CHECK")
print("="*80 + "\n")

js_errors = [log for log in logs if log['level'] == 'SEVERE']

if js_errors:
    print(f"❌ Found {len(js_errors)} JavaScript errors:\n")
    for i, error in enumerate(js_errors, 1):
        print(f"Error {i}:")
        print(f"  Message: {error['message']}")
        print(f"  Source: {error.get('source', 'unknown')}")
        print()
else:
    print("✅ No JavaScript errors found!")

# Check for syntax errors specifically
syntax_errors = [log for log in logs if 'SyntaxError' in log['message']]
if syntax_errors:
    print(f"\n⚠️  SYNTAX ERRORS DETECTED ({len(syntax_errors)}):")
    for error in syntax_errors:
        print(f"  {error['message']}")

driver.quit()
