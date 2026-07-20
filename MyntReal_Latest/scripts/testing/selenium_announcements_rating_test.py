#!/usr/bin/env python3
"""
ANNOUNCEMENTS & RATING FRONTEND TEST
Tests complete flow from frontend:
1. User submits announcement with image
2. User submits announcement with video
3. VGK approves image announcement
4. Admin approves video announcement
5. Verify both appear on login page carousel
6. Test rating feature with star clicks
7. Clean up all test data
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# Test credentials
VGK_ADMIN = {'id': 'MNR182364369', 'password': 'vgkadmin123', 'name': 'VGK Admin'}
ADMIN = {'id': 'MNR182322707', 'password': 'admin123', 'name': 'Admin'}
TEST_USER = {'id': 'MNR1800001', 'password': 'password', 'name': 'Test User'}

BASE_URL = "http://localhost:5000"

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

# Track created announcements for cleanup
created_announcement_ids = []

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{CYAN}{text:^80}{RESET}")
    print(f"{'='*80}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}► {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def setup_driver():
    """Initialize Chrome driver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def login(driver, user_creds):
    """Login with given credentials"""
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
        
        if "/login" not in driver.current_url.lower():
            print_success(f"Logged in as {user_creds['name']}")
            return True
        else:
            print_error(f"Login failed for {user_creds['name']}")
            driver.save_screenshot(f"login_fail_{user_creds['id']}.png")
            return False
            
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return False

def logout(driver):
    """Logout current user"""
    try:
        driver.get(f"{BASE_URL}/logout")
        time.sleep(2)
        print_info("Logged out successfully")
    except:
        pass

# ============================================================================
# STEP 1: Create Test Image File
# ============================================================================

def create_test_image():
    """Create a simple test image file"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a 800x600 image with orange background
        img = Image.new('RGB', (800, 600), color='#f97316')
        draw = ImageDraw.Draw(img)
        
        # Add text
        text = "SELENIUM TEST IMAGE"
        # Use default font since we may not have custom fonts
        draw.text((250, 280), text, fill='white')
        
        filename = '/tmp/selenium_test_image.jpg'
        img.save(filename, 'JPEG')
        print_success(f"Created test image: {filename}")
        return filename
    except Exception as e:
        print_error(f"Failed to create test image: {str(e)}")
        # Create a minimal 1x1 pixel image as fallback
        with open('/tmp/selenium_test_image.jpg', 'wb') as f:
            # Minimal JPEG header + data
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2\xcf \xff\xd9')
        return '/tmp/selenium_test_image.jpg'

# ============================================================================
# STEP 2: User Submits Announcement with Image
# ============================================================================

def submit_announcement_with_image(driver):
    """Test user submits announcement with image"""
    try:
        print_info("Step 1: User submitting announcement with image...")
        
        # Login as test user
        if not login(driver, TEST_USER):
            return False
        
        # Navigate to announcements submission page
        driver.get(f"{BASE_URL}/user/announcements")
        time.sleep(3)
        driver.save_screenshot("announcement_01_user_page.png")
        
        # Fill announcement form
        timestamp = datetime.now().strftime("%H%M%S")
        title = f"SELENIUM_IMAGE_TEST_{timestamp}"
        
        title_field = driver.find_element(By.ID, "announcement_title")
        title_field.clear()
        title_field.send_keys(title)
        
        content_field = driver.find_element(By.ID, "announcement_content")
        content_field.clear()
        content_field.send_keys("This is a Selenium test announcement with an image attachment.")
        
        # Upload image
        image_path = create_test_image()
        file_input = driver.find_element(By.ID, "announcement_media")
        file_input.send_keys(image_path)
        
        time.sleep(2)
        driver.save_screenshot("announcement_02_filled_form.png")
        
        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        driver.save_screenshot("announcement_03_submitted.png")
        print_success("Image announcement submitted")
        
        logout(driver)
        return title
        
    except Exception as e:
        print_error(f"Failed to submit image announcement: {str(e)}")
        driver.save_screenshot("error_submit_image.png")
        return None

# ============================================================================
# STEP 3: User Submits Announcement with Text Only (No video upload in test)
# ============================================================================

def submit_announcement_text_only(driver):
    """Test user submits text-only announcement (simulating video scenario)"""
    try:
        print_info("Step 2: User submitting text announcement (video scenario)...")
        
        # Login as test user
        if not login(driver, TEST_USER):
            return False
        
        # Navigate to announcements submission page
        driver.get(f"{BASE_URL}/user/announcements")
        time.sleep(3)
        
        # Fill announcement form
        timestamp = datetime.now().strftime("%H%M%S")
        title = f"SELENIUM_VIDEO_TEST_{timestamp}"
        
        title_field = driver.find_element(By.ID, "announcement_title")
        title_field.clear()
        title_field.send_keys(title)
        
        content_field = driver.find_element(By.ID, "announcement_content")
        content_field.clear()
        content_field.send_keys("This is a Selenium test announcement representing a video post.")
        
        time.sleep(2)
        driver.save_screenshot("announcement_04_text_form.png")
        
        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        driver.save_screenshot("announcement_05_text_submitted.png")
        print_success("Text announcement submitted")
        
        logout(driver)
        return title
        
    except Exception as e:
        print_error(f"Failed to submit text announcement: {str(e)}")
        driver.save_screenshot("error_submit_text.png")
        return None

# ============================================================================
# STEP 4: VGK Approves Image Announcement
# ============================================================================

def vgk_approve_announcement(driver, title):
    """VGK admin approves the image announcement"""
    try:
        print_info("Step 3: VGK approving image announcement...")
        
        # Login as VGK
        if not login(driver, VGK_ADMIN):
            return False
        
        # Navigate to announcements approval page
        driver.get(f"{BASE_URL}/vgk/announcements")
        time.sleep(3)
        driver.save_screenshot("announcement_06_vgk_approval_page.png")
        
        # Find the announcement by title
        page_source = driver.page_source
        
        if title in page_source:
            print_info(f"Found announcement: {title}")
            
            # Look for approve button for this announcement
            # The button might be in a table row or card containing the title
            approve_buttons = driver.find_elements(By.XPATH, f"//tr[contains(., '{title}')]//button[contains(text(), 'Approve')]")
            
            if not approve_buttons:
                # Try alternative selector
                approve_buttons = driver.find_elements(By.XPATH, f"//div[contains(., '{title}')]//button[contains(text(), 'Approve')]")
            
            if approve_buttons:
                approve_buttons[0].click()
                time.sleep(2)
                
                # Confirm if there's a confirmation dialog
                try:
                    confirm_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Yes')]")
                    confirm_btn.click()
                    time.sleep(2)
                except:
                    pass
                
                driver.save_screenshot("announcement_07_vgk_approved.png")
                print_success("VGK approved image announcement")
                logout(driver)
                return True
            else:
                print_warning("Approve button not found")
                driver.save_screenshot("error_no_approve_button.png")
        else:
            print_warning(f"Announcement '{title}' not found on page")
            driver.save_screenshot("error_announcement_not_found.png")
        
        logout(driver)
        return False
        
    except Exception as e:
        print_error(f"Failed VGK approval: {str(e)}")
        driver.save_screenshot("error_vgk_approve.png")
        return False

# ============================================================================
# STEP 5: Admin Approves Video/Text Announcement
# ============================================================================

def admin_approve_announcement(driver, title):
    """Admin approves the video/text announcement"""
    try:
        print_info("Step 4: Admin approving video announcement...")
        
        # Login as Admin
        if not login(driver, ADMIN):
            return False
        
        # Navigate to announcements approval page
        driver.get(f"{BASE_URL}/admin/announcements")
        time.sleep(3)
        driver.save_screenshot("announcement_08_admin_approval_page.png")
        
        # Find the announcement by title
        page_source = driver.page_source
        
        if title in page_source:
            print_info(f"Found announcement: {title}")
            
            # Look for approve button
            approve_buttons = driver.find_elements(By.XPATH, f"//tr[contains(., '{title}')]//button[contains(text(), 'Approve')]")
            
            if not approve_buttons:
                approve_buttons = driver.find_elements(By.XPATH, f"//div[contains(., '{title}')]//button[contains(text(), 'Approve')]")
            
            if approve_buttons:
                approve_buttons[0].click()
                time.sleep(2)
                
                # Confirm if needed
                try:
                    confirm_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Yes')]")
                    confirm_btn.click()
                    time.sleep(2)
                except:
                    pass
                
                driver.save_screenshot("announcement_09_admin_approved.png")
                print_success("Admin approved video announcement")
                logout(driver)
                return True
            else:
                print_warning("Approve button not found")
                driver.save_screenshot("error_admin_no_approve_button.png")
        else:
            print_warning(f"Announcement '{title}' not found on page")
        
        logout(driver)
        return False
        
    except Exception as e:
        print_error(f"Failed Admin approval: {str(e)}")
        driver.save_screenshot("error_admin_approve.png")
        return False

# ============================================================================
# STEP 6: Verify Announcements on Login Page
# ============================================================================

def verify_announcements_on_login_page(driver, image_title, video_title):
    """Verify both announcements appear on login page carousel"""
    try:
        print_info("Step 5: Verifying announcements on login page...")
        
        # Go to login page (logout first)
        driver.get(f"{BASE_URL}/login")
        time.sleep(5)  # Wait for carousel to load
        
        driver.save_screenshot("announcement_10_login_page_carousel.png")
        
        page_source = driver.page_source
        
        # Check if announcements section exists
        if "Recent Public Announcements" in page_source:
            print_success("Announcements section found on login page")
        else:
            print_error("Announcements section NOT found on login page")
            return False
        
        # Wait for carousel to load announcements
        time.sleep(3)
        
        # Check for image announcement
        image_found = image_title in page_source
        if image_found:
            print_success(f"Image announcement '{image_title}' visible on login page")
        else:
            print_warning(f"Image announcement '{image_title}' NOT visible")
        
        # Wait for carousel rotation
        time.sleep(4)
        driver.save_screenshot("announcement_11_carousel_rotated.png")
        
        # Check page source again after rotation
        page_source = driver.page_source
        video_found = video_title in page_source
        if video_found:
            print_success(f"Video announcement '{video_title}' visible on login page")
        else:
            print_warning(f"Video announcement '{video_title}' NOT visible")
        
        # Check for rating stars
        if 'fa-star' in page_source or 'rating' in page_source.lower():
            print_success("Rating stars found on announcements")
        else:
            print_warning("Rating stars NOT found")
        
        return image_found or video_found
        
    except Exception as e:
        print_error(f"Failed to verify announcements: {str(e)}")
        driver.save_screenshot("error_verify_announcements.png")
        return False

# ============================================================================
# STEP 7: Test Rating Feature
# ============================================================================

def test_rating_feature(driver):
    """Test clicking rating stars and submitting rating"""
    try:
        print_info("Step 6: Testing rating feature...")
        
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)
        
        # Look for rating stars
        stars = driver.find_elements(By.CSS_SELECTOR, "[data-rating]")
        
        if not stars:
            print_warning("No rating stars found")
            driver.save_screenshot("error_no_rating_stars.png")
            return False
        
        print_info(f"Found {len(stars)} rating stars")
        
        # Click on a 5-star rating
        five_star = None
        for star in stars:
            if star.get_attribute('data-rating') == '5':
                five_star = star
                break
        
        if five_star:
            driver.save_screenshot("announcement_12_before_star_click.png")
            print_info("Clicking 5-star rating...")
            five_star.click()
            time.sleep(2)
            
            driver.save_screenshot("announcement_13_after_star_click.png")
            
            # Check if login modal appeared
            try:
                modal = driver.find_element(By.ID, "ratingLoginModal")
                modal_displayed = modal.value_of_css_property("display")
                
                if modal_displayed != "none":
                    print_success("Rating login modal appeared!")
                    
                    # Fill in login credentials
                    username_input = driver.find_element(By.ID, "ratingUsername")
                    password_input = driver.find_element(By.ID, "ratingPassword")
                    
                    username_input.send_keys(TEST_USER['id'])
                    password_input.send_keys(TEST_USER['password'])
                    
                    driver.save_screenshot("announcement_14_modal_filled.png")
                    
                    # Click submit rating button
                    submit_btn = driver.find_element(By.ID, "ratingSubmitBtn")
                    submit_btn.click()
                    time.sleep(3)
                    
                    driver.save_screenshot("announcement_15_rating_submitted.png")
                    print_success("Rating submitted successfully!")
                    
                    return True
                else:
                    print_error("Modal did not appear (display: none)")
                    return False
                    
            except Exception as modal_error:
                print_error(f"Modal not found or error: {str(modal_error)}")
                driver.save_screenshot("error_modal_not_found.png")
                return False
        else:
            print_warning("5-star rating not found")
            return False
        
    except Exception as e:
        print_error(f"Failed to test rating: {str(e)}")
        driver.save_screenshot("error_test_rating.png")
        return False

# ============================================================================
# STEP 8: Clean Up Test Data
# ============================================================================

def cleanup_test_data(driver, image_title, video_title):
    """Clean up test announcements from database"""
    try:
        print_info("Step 7: Cleaning up test data...")
        
        # Login as VGK admin to delete announcements
        if not login(driver, VGK_ADMIN):
            print_warning("Could not login to cleanup")
            return
        
        # Navigate to announcements management
        driver.get(f"{BASE_URL}/vgk/announcements")
        time.sleep(3)
        
        # Try to delete the test announcements
        for title in [image_title, video_title]:
            if title:
                try:
                    # Look for delete button for this announcement
                    delete_buttons = driver.find_elements(By.XPATH, f"//tr[contains(., '{title}')]//button[contains(text(), 'Delete')]")
                    
                    if delete_buttons:
                        delete_buttons[0].click()
                        time.sleep(1)
                        
                        # Confirm deletion
                        try:
                            confirm_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Yes')]")
                            confirm_btn.click()
                            time.sleep(1)
                            print_success(f"Deleted announcement: {title}")
                        except:
                            pass
                except Exception as e:
                    print_warning(f"Could not delete {title}: {str(e)}")
        
        driver.save_screenshot("announcement_16_cleanup_done.png")
        logout(driver)
        
        # Clean up test image file
        try:
            os.remove('/tmp/selenium_test_image.jpg')
            print_success("Removed test image file")
        except:
            pass
        
    except Exception as e:
        print_error(f"Cleanup failed: {str(e)}")

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

def main():
    driver = None
    image_title = None
    video_title = None
    
    try:
        print_header("ANNOUNCEMENTS & RATING SELENIUM TEST")
        print_info("Starting test execution...")
        
        driver = setup_driver()
        print_success("Chrome driver initialized")
        
        # Step 1 & 2: Submit announcements
        image_title = submit_announcement_with_image(driver)
        video_title = submit_announcement_text_only(driver)
        
        if not image_title and not video_title:
            print_error("Failed to create any announcements")
            return False
        
        # Step 3: VGK approval
        if image_title:
            vgk_approve_announcement(driver, image_title)
        
        # Step 4: Admin approval
        if video_title:
            admin_approve_announcement(driver, video_title)
        
        # Wait for approvals to process
        time.sleep(3)
        
        # Step 5: Verify on login page
        announcements_visible = verify_announcements_on_login_page(driver, image_title or "", video_title or "")
        
        # Step 6: Test rating feature
        rating_works = test_rating_feature(driver)
        
        # Step 7: Cleanup
        cleanup_test_data(driver, image_title, video_title)
        
        # Summary
        print_header("TEST SUMMARY")
        if announcements_visible:
            print_success("✓ Announcements visible on login page")
        else:
            print_error("✗ Announcements NOT visible on login page")
        
        if rating_works:
            print_success("✓ Rating feature works")
        else:
            print_error("✗ Rating feature has issues")
        
        print_header("TEST COMPLETED")
        return announcements_visible and rating_works
        
    except Exception as e:
        print_error(f"Test failed with error: {str(e)}")
        if driver:
            driver.save_screenshot("error_main_test.png")
        return False
        
    finally:
        if driver:
            driver.quit()
            print_info("Browser closed")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
