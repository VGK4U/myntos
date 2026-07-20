"""
Debug Bonanza Management Syntax Error
"""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost:5000"
VGK_USERNAME = "BEV182364369"
VGK_PASSWORD = os.getenv('VGK_TEST_PASSWORD', 'Test@123')

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=chrome_options)

try:
    # Login
    print("Logging in...")
    driver.get(f"{BASE_URL}/login.html")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(VGK_USERNAME)
    driver.find_element(By.ID, "password").send_keys(VGK_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)
    
    # Navigate to bonanza management
    print("Navigating to Bonanza Management...")
    driver.get(f"{BASE_URL}/vgk/bonanza-management")
    time.sleep(5)  # Wait for page to fully load
    
    # Get all browser console logs
    logs = driver.get_log('browser')
    
    print("\n" + "="*80)
    print("BROWSER CONSOLE LOGS - BONANZA MANAGEMENT")
    print("="*80)
    
    # Categorize errors
    critical_errors = []
    warnings = []
    info_logs = []
    
    for log in logs:
        level = log['level']
        message = log['message']
        
        # Skip favicon errors
        if 'favicon' in message:
            continue
        
        if level == 'SEVERE':
            critical_errors.append(message)
        elif level == 'WARNING':
            warnings.append(message)
        else:
            info_logs.append(message)
    
    # Display critical errors in detail
    if critical_errors:
        print(f"\n🔴 CRITICAL ERRORS ({len(critical_errors)}):")
        print("-"*80)
        for i, error in enumerate(critical_errors, 1):
            print(f"\nError #{i}:")
            print(error)
            print()
    else:
        print("\n✅ NO CRITICAL ERRORS")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings[:3]:  # Show first 3
            print(f"  - {warning[:150]}")
    
    # Get page source to check if JavaScript loaded
    page_source = driver.page_source
    if "🎯 Bonanza Management" in page_source:
        print("\n✅ Page HTML loaded correctly")
    else:
        print("\n❌ Page HTML not loaded")
    
    # Check if page is interactive
    buttons = len(driver.find_elements(By.TAG_NAME, "button"))
    print(f"✅ Interactive elements: {buttons} buttons found")
    
    print("\n" + "="*80)
    
finally:
    driver.quit()
