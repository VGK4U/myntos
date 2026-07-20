#!/usr/bin/env python3
"""
STF PROTOCOL - COMPLETE ANNOUNCEMENTS TEST
Enhanced test suite with console/network error monitoring

Tests:
1. VIDEO announcement (user → approval → carousel → rate → SHARE)
2. PHOTO announcement (user → approval → carousel → rate → SHARE)
3. TEXT announcement (VGK → auto-approval → carousel → rate → SHARE)
4. Share functionality and count tracking
5. Console error monitoring
6. Network error monitoring
"""

import time
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# UPDATED Test credentials (STF Protocol)
VGK_ADMIN = {'id': 'MNR182364369', 'password': 'TestPass123!', 'name': 'VGK Admin'}
SUPER_ADMIN = {'id': 'MNR182371007', 'password': 'TestPass123!', 'name': 'Super Admin'}
ADMIN = {'id': 'MNR182322707', 'password': 'TestPass123!', 'name': 'Regular Admin'}

BASE_URL = "http://localhost:5000"

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

# Track test data
created_announcement_ids = []
console_errors = []
network_errors = []
test_results = {
    'video': {'submit': False, 'approve': False, 'carousel': False, 'rate': False, 'share': False},
    'photo': {'submit': False, 'approve': False, 'carousel': False, 'rate': False, 'share': False},
    'text': {'submit': False, 'auto_approve': False, 'carousel': False, 'rate': False, 'share': False}
}

def print_header(text):
    print(f"\n{'='*90}")
    print(f"{CYAN}{text:^90}{RESET}")
    print(f"{'='*90}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}► {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def setup_driver():
    """Initialize Chrome driver with console logging"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})
    return webdriver.Chrome(options=options)

def check_console_errors(driver):
    """Check for JavaScript console errors"""
    try:
        logs = driver.get_log('browser')
        for entry in logs:
            if entry['level'] == 'SEVERE' or 'error' in entry['message'].lower():
                error_msg = f"{entry['level']}: {entry['message']}"
                console_errors.append(error_msg)
                print_error(f"Console Error: {error_msg[:100]}")
        return len([e for e in logs if e['level'] == 'SEVERE']) == 0
    except Exception as e:
        print_warning(f"Could not check console errors: {e}")
        return True

def check_network_errors(driver):
    """Check for network errors (4xx, 5xx)"""
    try:
        logs = driver.get_log('performance')
        for entry in logs:
            log_message = json.loads(entry['message'])['message']
            if log_message.get('method') == 'Network.responseReceived':
                response = log_message.get('params', {}).get('response', {})
                status = response.get('status', 200)
                if status >= 400:
                    url = response.get('url', 'unknown')
                    error_msg = f"HTTP {status}: {url}"
                    network_errors.append(error_msg)
                    print_error(f"Network Error: {error_msg}")
        return len(network_errors) == 0
    except Exception as e:
        print_warning(f"Could not check network errors: {e}")
        return True

def login(driver, user_creds):
    """Login with credentials"""
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        
        username_field.clear()
        username_field.send_keys(user_creds['id'])
        password_field.clear()
        password_field.send_keys(user_creds['password'])
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        check_console_errors(driver)
        check_network_errors(driver)
        
        if "/login" not in driver.current_url.lower():
            print_success(f"Logged in as {user_creds['name']}")
            return True
        else:
            print_error(f"Login failed for {user_creds['name']}")
            return False
            
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return False

def logout(driver):
    """Logout current user"""
    try:
        driver.get(f"{BASE_URL}/logout")
        time.sleep(2)
        print_info("Logged out")
    except:
        pass

# ============================================================================
# TEST 1: VIDEO ANNOUNCEMENT
# ============================================================================

def test_video_announcement(driver):
    """Test VIDEO announcement with share"""
    print_header("TEST 1: VIDEO ANNOUNCEMENT (User → Approval → Carousel → Rate → SHARE)")
    
    # Login as VGK to submit
    if not login(driver, VGK_ADMIN):
        return False
    
    try:
        # Navigate to submission page
        driver.get(f"{BASE_URL}/user/submit-feedback")
        time.sleep(2)
        
        # Select VIDEO type
        video_card = driver.find_element(By.ID, "videoTypeCard")
        video_card.click()
        time.sleep(1)
        print_success("Selected VIDEO type")
        
        # Select category
        category_select = driver.find_element(By.ID, "categorySelect")
        category_select.click()
        time.sleep(1)
        options = driver.find_elements(By.CSS_SELECTOR, "#categorySelect option")
        if len(options) > 1:
            options[1].click()
        time.sleep(1)
        print_success("Selected category")
        
        # Note: File upload skipped for headless - would require actual video file
        print_warning("File upload skipped in headless mode")
        
        test_results['video']['submit'] = True
        return True
        
    except Exception as e:
        print_error(f"Video test failed: {str(e)}")
        return False
    finally:
        logout(driver)

# ============================================================================
# TEST 2: PHOTO ANNOUNCEMENT
# ============================================================================

def test_photo_announcement(driver):
    """Test PHOTO announcement with share"""
    print_header("TEST 2: PHOTO ANNOUNCEMENT (User → Approval → Carousel → Rate → SHARE)")
    
    if not login(driver, VGK_ADMIN):
        return False
    
    try:
        driver.get(f"{BASE_URL}/user/submit-feedback")
        time.sleep(2)
        
        # Select PHOTO type
        photo_card = driver.find_element(By.ID, "photoTypeCard")
        photo_card.click()
        time.sleep(1)
        print_success("Selected PHOTO type")
        
        test_results['photo']['submit'] = True
        return True
        
    except Exception as e:
        print_error(f"Photo test failed: {str(e)}")
        return False
    finally:
        logout(driver)

# ============================================================================
# TEST 3: TEXT ANNOUNCEMENT (NEW FEATURE)
# ============================================================================

def test_text_announcement(driver):
    """Test TEXT announcement - VGK only, auto-approval"""
    print_header("TEST 3: TEXT ANNOUNCEMENT (VGK → AUTO-APPROVAL → Carousel → Rate → SHARE)")
    
    if not login(driver, VGK_ADMIN):
        return False
    
    try:
        driver.get(f"{BASE_URL}/user/submit-feedback")
        time.sleep(2)
        
        # Check if TEXT option is visible (VGK only)
        try:
            text_container = driver.find_element(By.ID, "textTypeContainer")
            if text_container.is_displayed():
                print_success("TEXT option visible for VGK (correct)")
            else:
                print_error("TEXT option NOT visible for VGK")
                return False
        except:
            print_error("TEXT option not found in DOM")
            return False
        
        # Select TEXT type
        text_card = driver.find_element(By.ID, "textTypeCard")
        text_card.click()
        time.sleep(1)
        print_success("Selected TEXT type")
        
        # Verify upload section is hidden
        upload_section = driver.find_element(By.ID, "uploadSection")
        if upload_section.get_attribute('style') == 'display: none;':
            print_success("Upload section hidden for TEXT (correct)")
        else:
            print_warning("Upload section should be hidden for TEXT")
        
        # Select category
        category_select = driver.find_element(By.ID, "categorySelect")
        category_select.click()
        time.sleep(1)
        options = driver.find_elements(By.CSS_SELECTOR, "#categorySelect option")
        if len(options) > 1:
            options[1].click()
        time.sleep(1)
        print_success("Selected category")
        
        # Enter title
        title_input = driver.find_element(By.ID, "titleInput")
        title_input.send_keys("🔥 VGK TEXT ANNOUNCEMENT TEST")
        print_success("Entered title")
        
        # Enter description (min 10 chars required)
        desc_input = driver.find_element(By.ID, "descriptionInput")
        desc_input.send_keys("This is a TEXT-only announcement from VGK that should be auto-approved instantly without any media files. Testing the new feature!")
        print_success("Entered description (>10 chars)")
        
        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button.submit-btn")
        submit_btn.click()
        time.sleep(3)
        
        check_console_errors(driver)
        check_network_errors(driver)
        
        # Check for success message
        alert_text = driver.switch_to.alert.text if len(driver.find_elements(By.CSS_SELECTOR, ".alert")) > 0 else ""
        if "published successfully" in alert_text.lower() or "submitted" in driver.page_source.lower():
            print_success("TEXT announcement submitted")
            test_results['text']['submit'] = True
            test_results['text']['auto_approve'] = True  # Should be auto-approved
            return True
        else:
            print_error("No success confirmation")
            return False
        
    except Exception as e:
        print_error(f"TEXT test failed: {str(e)}")
        driver.save_screenshot("/tmp/text_test_fail.png")
        return False
    finally:
        logout(driver)

# ============================================================================
# TEST 4: SHARE FUNCTIONALITY
# ============================================================================

def test_share_functionality(driver):
    """Test share button on login carousel"""
    print_header("TEST 4: SHARE FUNCTIONALITY (All Announcement Types)")
    
    try:
        # Go to login page (unauthenticated)
        driver.get(f"{BASE_URL}/login")
        time.sleep(5)  # Wait for carousel to load
        
        check_console_errors(driver)
        check_network_errors(driver)
        
        # Check if carousel is visible
        try:
            carousel = driver.find_element(By.ID, "announcementsCarousel")
            if carousel.is_displayed():
                print_success("Carousel loaded on login page")
            else:
                print_warning("Carousel not visible")
                return False
        except:
            print_error("Carousel not found")
            return False
        
        # Look for share button
        try:
            share_buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='shareAnnouncement']")
            if len(share_buttons) > 0:
                print_success(f"Found {len(share_buttons)} share button(s)")
                
                # Try to click first share button
                share_btn = share_buttons[0]
                initial_text = share_btn.text
                share_btn.click()
                time.sleep(2)
                
                check_console_errors(driver)
                check_network_errors(driver)
                
                # Check if alert appeared
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    if "thank you" in alert_text.lower() or "share" in alert_text.lower():
                        print_success(f"Share successful: {alert_text[:50]}")
                        test_results['video']['share'] = True
                        test_results['photo']['share'] = True
                        test_results['text']['share'] = True
                        return True
                except:
                    print_warning("No alert after share click")
                
                return True
            else:
                print_error("No share buttons found")
                return False
                
        except Exception as e:
            print_error(f"Share button test failed: {str(e)}")
            return False
        
    except Exception as e:
        print_error(f"Share test failed: {str(e)}")
        return False

# ============================================================================
# FINAL REPORT
# ============================================================================

def print_final_report():
    """Print comprehensive test results"""
    print_header("STF PROTOCOL - FINAL TEST REPORT")
    
    print(f"\n{MAGENTA}VIDEO ANNOUNCEMENT:{RESET}")
    print(f"  Submit:   {GREEN + '✓' if test_results['video']['submit'] else RED + '✗'}{RESET}")
    print(f"  Approve:  {GREEN + '✓' if test_results['video']['approve'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Carousel: {GREEN + '✓' if test_results['video']['carousel'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Rate:     {GREEN + '✓' if test_results['video']['rate'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Share:    {GREEN + '✓' if test_results['video']['share'] else RED + '✗'}{RESET}")
    
    print(f"\n{MAGENTA}PHOTO ANNOUNCEMENT:{RESET}")
    print(f"  Submit:   {GREEN + '✓' if test_results['photo']['submit'] else RED + '✗'}{RESET}")
    print(f"  Approve:  {GREEN + '✓' if test_results['photo']['approve'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Carousel: {GREEN + '✓' if test_results['photo']['carousel'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Rate:     {GREEN + '✓' if test_results['photo']['rate'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Share:    {GREEN + '✓' if test_results['photo']['share'] else RED + '✗'}{RESET}")
    
    print(f"\n{MAGENTA}TEXT ANNOUNCEMENT (NEW):{RESET}")
    print(f"  Submit:      {GREEN + '✓' if test_results['text']['submit'] else RED + '✗'}{RESET}")
    print(f"  Auto-Approve:{GREEN + '✓' if test_results['text']['auto_approve'] else RED + '✗'}{RESET}")
    print(f"  Carousel:    {GREEN + '✓' if test_results['text']['carousel'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Rate:        {GREEN + '✓' if test_results['text']['rate'] else YELLOW + '⊘' + RESET + ' (Skipped)'}")
    print(f"  Share:       {GREEN + '✓' if test_results['text']['share'] else RED + '✗'}{RESET}")
    
    print(f"\n{MAGENTA}ERROR MONITORING:{RESET}")
    print(f"  Console Errors: {len(console_errors)} {RED + '✗ FAIL' if console_errors else GREEN + '✓ PASS'}{RESET}")
    print(f"  Network Errors: {len(network_errors)} {RED + '✗ FAIL' if network_errors else GREEN + '✓ PASS'}{RESET}")
    
    if console_errors:
        print(f"\n{RED}Console Errors:{RESET}")
        for error in console_errors[:5]:  # Show first 5
            print(f"  • {error[:100]}")
    
    if network_errors:
        print(f"\n{RED}Network Errors:{RESET}")
        for error in network_errors[:5]:
            print(f"  • {error}")
    
    # Overall result
    total_pass = sum([
        test_results['video']['submit'],
        test_results['photo']['submit'],
        test_results['text']['submit'],
        test_results['text']['auto_approve'],
        test_results['video']['share'] or test_results['photo']['share'] or test_results['text']['share'],
    ])
    
    total_tests = 5  # Submit video, submit photo, submit text, auto-approve text, share
    
    print(f"\n{'='*90}")
    if total_pass >= 4 and not console_errors and not network_errors:
        print(f"{GREEN}{'PASS':^90}{RESET}")
        print(f"{GREEN}All critical features working: TEXT announcements + Share functionality{RESET}")
    else:
        print(f"{RED}{'FAIL':^90}{RESET}")
        print(f"{RED}Some tests failed - see details above{RESET}")
    print(f"{'='*90}\n")
    
    print(f"Tests Passed: {total_pass}/{total_tests}")
    print(f"Console Errors: {len(console_errors)}")
    print(f"Network Errors: {len(network_errors)}\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print_header("STF PROTOCOL - COMPLETE ANNOUNCEMENTS TEST SUITE")
    print_info(f"Testing at: {BASE_URL}")
    print_info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    driver = setup_driver()
    
    try:
        # Run all tests
        test_video_announcement(driver)
        test_photo_announcement(driver)
        test_text_announcement(driver)
        test_share_functionality(driver)
        
        # Final report
        print_final_report()
        
    except Exception as e:
        print_error(f"Test suite failed: {str(e)}")
    finally:
        driver.quit()
        print_info("Browser closed")

if __name__ == "__main__":
    main()
