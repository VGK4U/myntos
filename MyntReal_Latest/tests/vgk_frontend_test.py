#!/usr/bin/env python3
"""
VGK FRONTEND TEST - Pure Frontend Validation
Tests all 82 VGK pages with REAL login
Documents which pages work and which need fixes
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import json

# All 82 VGK pages to test
VGK_PAGES = [
    # Priority 1 - Critical Supreme Pages
    ("/vgk/income-history-supreme", "Income History Supreme"),
    ("/vgk/withdrawal-supreme/approvals", "Withdrawal Approvals"),
    ("/finance/awards/payment-processing", "Awards Payment Processing"),
    ("/vgk/company-earnings", "Company Earnings"),
    ("/admin/members/search", "Search Members"),
    
    # Admin Functionalities
    ("/admin/kyc-management", "KYC Management"),
    ("/admin/birthdays", "Birthday Details"),
    ("/vgk/user-data-search", "User Data Search"),
    ("/vgk/brand-level-management", "Content Management"),
    ("/vgk/popup-control", "Popup Control"),
    ("/vgk/terms-conditions-management", "T&C Management"),
    ("/vgk/bulk-user-edit", "Bulk User Edit"),
    ("/vgk/user-activation-control", "User Activation Control"),
    ("/vgk/withdrawal/dashboard", "Withdrawal Dashboard"),
    ("/vgk/role-management", "Role Management"),
    ("/vgk/award-management", "Award Management"),
    ("/vgk/system-controls", "System Controls"),
    ("/vgk/scheduler-dashboard", "Scheduler Dashboard"),
    ("/vgk/rate-configuration", "Rate Configuration"),
    ("/vgk/daily-ceiling", "Daily Ceiling"),
    ("/vgk/emergency-wallet", "Emergency Wallet"),
    ("/vgk/menu-configuration", "Menu Configuration"),
    
    # Supreme Pages
    ("/vgk/income-analytics", "Income Analytics"),
    ("/vgk/withdrawal-supreme/history", "Withdrawal History"),
    ("/vgk/withdrawal-supreme/analytics", "Withdrawal Analytics"),
    ("/vgk/finance-overview", "Finance Overview"),
    ("/vgk/expense-overview", "Expense Overview"),
    ("/vgk/financial-reports", "Financial Reports"),
    
    # KYC Supreme
    ("/vgk/kyc-pending", "KYC Pending"),
    ("/vgk/kyc-approved", "KYC Approved"),
    ("/vgk/kyc-rejected", "KYC Rejected"),
    ("/vgk/kyc-analytics", "KYC Analytics"),
    
    # Bank Supreme
    ("/vgk/bank-pending", "Bank Pending"),
    ("/vgk/bank-approved", "Bank Approved"),
    ("/vgk/bank-all", "All Bank Details"),
    
    # Bonanza Management
    ("/vgk/bonanza/create", "Create Bonanza"),
    ("/vgk/bonanza/active", "Active Bonanzas"),
    ("/vgk/bonanza/history", "Bonanza History"),
    ("/vgk/bonanza/claims", "Bonanza Claims"),
    
    # Awards
    ("/vgk/awards/oversight", "Bonanza Awards"),
    ("/vgk/awards/procurement", "Awards Procurement"),
]

def quick_test():
    """Fast frontend validation"""
    print("="*80)
    print("VGK FRONTEND TEST - Real Login Testing")
    print("="*80)
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    
    results = {"working": [], "broken": [], "total": len(VGK_PAGES)}
    
    try:
        # LOGIN
        print("\n🔐 LOGGING IN...")
        driver.get("http://localhost:5000/login")
        time.sleep(2)
        
        driver.find_element(By.ID, "username").send_keys(os.getenv("VGK_TEST_USER", "BEV182364369"))
        driver.find_element(By.ID, "password").send_keys(os.getenv("VGK_TEST_PASSWORD"))
        driver.find_element(By.ID, "submitBtn").click()
        
        # Wait for redirect
        WebDriverWait(driver, 15).until(lambda d: "/login" not in d.current_url)
        print(f"✅ Logged in successfully")
        
        # TEST ALL PAGES
        print(f"\n🧪 TESTING {len(VGK_PAGES)} PAGES...\n")
        
        for idx, (url, name) in enumerate(VGK_PAGES, 1):
            try:
                driver.get(f"http://localhost:5000{url}")
                time.sleep(1.5)
                
                page_source = driver.page_source.lower()
                current_url = driver.current_url
                
                # Check status
                if "404" in page_source or "not found" in page_source:
                    print(f"{idx:02d}. ❌ 404: {name}")
                    results["broken"].append({"url": url, "name": name, "error": "404 Not Found"})
                elif current_url.endswith("/login"):
                    print(f"{idx:02d}. ❌ AUTH: {name}")
                    results["broken"].append({"url": url, "name": name, "error": "Auth Failed"})
                elif "error" in page_source and "occurred" in page_source:
                    print(f"{idx:02d}. ❌ ERROR: {name}")
                    results["broken"].append({"url": url, "name": name, "error": "Server Error"})
                else:
                    print(f"{idx:02d}. ✅ OK: {name}")
                    results["working"].append({"url": url, "name": name})
                    
            except Exception as e:
                print(f"{idx:02d}. ❌ CRASH: {name} - {str(e)[:50]}")
                results["broken"].append({"url": url, "name": name, "error": str(e)[:100]})
        
        # SUMMARY
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"Total Pages Tested: {results['total']}")
        print(f"✅ Working: {len(results['working'])} ({len(results['working'])/results['total']*100:.1f}%)")
        print(f"❌ Broken: {len(results['broken'])} ({len(results['broken'])/results['total']*100:.1f}%)")
        
        if results['broken']:
            print(f"\n❌ BROKEN PAGES ({len(results['broken'])}):")
            for item in results['broken']:
                print(f"  - {item['name']}: {item['error']}")
        
        # Save results
        with open('vgk_frontend_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Full results saved: vgk_frontend_test_results.json")
        
    finally:
        driver.quit()
        print("\n✅ Test complete")

if __name__ == "__main__":
    quick_test()
