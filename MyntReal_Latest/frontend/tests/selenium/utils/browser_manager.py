"""
DC Protocol: Browser Manager for Visible Chrome Testing
Real-time browser execution with console log capture and network monitoring
"""

import os
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    UnexpectedAlertPresentException,
    WebDriverException
)

from config.settings import (
    BASE_URL, CHROMIUM_PATH, CHROMEDRIVER_PATH, BROWSER_CONFIG,
    SCREENSHOTS_DIR, LOGS_DIR
)


class BrowserManager:
    """
    DC Protocol: Manages Chrome browser instance with real-time visibility
    Handles console logs, network errors, and runtime monitoring
    """
    
    def __init__(self, headless: bool = False, vnc_mode: bool = False):
        self.headless = headless
        self.vnc_mode = vnc_mode
        self.driver: Optional[webdriver.Chrome] = None
        self.console_logs: List[Dict] = []
        self.network_errors: List[Dict] = []
        self.runtime_errors: List[Dict] = []
        self.warnings: List[str] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def setup(self) -> webdriver.Chrome:
        """Initialize Chrome browser with visible mode configuration"""
        print("\n" + "="*60)
        print("🚀 SELENIUM BROWSER MANAGER - DC Protocol")
        print("="*60)
        
        options = Options()
        options.binary_location = CHROMIUM_PATH
        
        if self.headless:
            print("   Mode: HEADLESS (invisible)")
            options.add_argument("--headless=new")
        elif self.vnc_mode:
            print("   Mode: VNC (visible via VNC desktop)")
        else:
            print("   Mode: VISIBLE BROWSER (real-time viewing)")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={BROWSER_CONFIG['window_size'][0]},{BROWSER_CONFIG['window_size'][1]}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        options.set_capability("goog:loggingPrefs", {
            "browser": "ALL",
            "performance": "ALL"
        })
        
        service = Service(CHROMEDRIVER_PATH)
        
        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(BROWSER_CONFIG['implicit_wait'])
            self.driver.set_page_load_timeout(BROWSER_CONFIG['page_load_timeout'])
            self.driver.set_script_timeout(BROWSER_CONFIG['script_timeout'])
            
            print(f"   ✅ Chrome browser started successfully")
            print(f"   📍 Session ID: {self.session_id}")
            print(f"   🌐 Base URL: {BASE_URL}")
            print("="*60 + "\n")
            
            return self.driver
            
        except WebDriverException as e:
            print(f"   ❌ Failed to start Chrome: {e}")
            raise
    
    def capture_console_logs(self) -> List[Dict]:
        """Capture all browser console logs"""
        if not self.driver:
            return []
            
        try:
            logs = self.driver.get_log('browser')
            for log in logs:
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'level': log.get('level', 'UNKNOWN'),
                    'message': log.get('message', ''),
                    'source': log.get('source', ''),
                }
                
                self.console_logs.append(log_entry)
                
                if log.get('level') == 'SEVERE':
                    self.runtime_errors.append(log_entry)
                    print(f"   ❌ CONSOLE ERROR: {log_entry['message'][:100]}")
                elif log.get('level') == 'WARNING':
                    self.warnings.append(log_entry['message'])
                    
            return logs
        except Exception as e:
            return []
    
    def capture_network_errors(self) -> List[Dict]:
        """Capture network errors from performance logs"""
        if not self.driver:
            return []
            
        try:
            logs = self.driver.get_log('performance')
            for log in logs:
                try:
                    message = json.loads(log.get('message', '{}'))
                    method = message.get('message', {}).get('method', '')
                    
                    if method == 'Network.responseReceived':
                        response = message.get('message', {}).get('params', {}).get('response', {})
                        status = response.get('status', 200)
                        url = response.get('url', '')
                        
                        if status >= 400:
                            error_entry = {
                                'timestamp': datetime.now().isoformat(),
                                'status': status,
                                'url': url,
                                'type': 'HTTP_ERROR'
                            }
                            self.network_errors.append(error_entry)
                            print(f"   ⚠️ NETWORK ERROR [{status}]: {url[:80]}")
                            
                except json.JSONDecodeError:
                    pass
                    
            return self.network_errors
        except Exception as e:
            return []
    
    def dismiss_alert(self) -> Optional[str]:
        """Dismiss any alert popup and return its text"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            print(f"   ⚠️ Alert dismissed: {alert_text[:60]}...")
            return alert_text
        except:
            return None
    
    def wait_for_page_load(self, timeout: int = 10):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            print("   ⚠️ Page load timeout")
    
    def take_screenshot(self, name: str) -> str:
        """Take screenshot and save to reports directory"""
        if not self.driver:
            return ""
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOTS_DIR, filename)
        
        try:
            self.driver.save_screenshot(filepath)
            print(f"   📸 Screenshot saved: {filename}")
            return filepath
        except Exception as e:
            print(f"   ❌ Screenshot failed: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """Get current browser URL"""
        return self.driver.current_url if self.driver else ""
    
    def get_page_title(self) -> str:
        """Get current page title"""
        return self.driver.title if self.driver else ""
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors were detected"""
        return len(self.runtime_errors) > 0 or len(self.network_errors) > 0
    
    def get_error_summary(self) -> Dict:
        """Get summary of all detected errors"""
        return {
            'console_logs': len(self.console_logs),
            'runtime_errors': len(self.runtime_errors),
            'network_errors': len(self.network_errors),
            'warnings': len(self.warnings),
            'has_critical': self.has_critical_errors()
        }
    
    def save_logs(self):
        """Save all captured logs to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        log_data = {
            'session_id': self.session_id,
            'timestamp': timestamp,
            'console_logs': self.console_logs,
            'runtime_errors': self.runtime_errors,
            'network_errors': self.network_errors,
            'warnings': self.warnings,
            'summary': self.get_error_summary()
        }
        
        log_file = os.path.join(LOGS_DIR, f"session_{self.session_id}.json")
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"   📋 Logs saved: session_{self.session_id}.json")
        return log_file
    
    def cleanup(self):
        """Close browser and cleanup resources"""
        if self.driver:
            try:
                self.save_logs()
                self.driver.quit()
                print("\n🔒 Browser closed successfully")
            except Exception as e:
                print(f"   ⚠️ Cleanup warning: {e}")
            finally:
                self.driver = None
