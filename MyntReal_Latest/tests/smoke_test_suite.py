#!/usr/bin/env python3
"""
Comprehensive Smoke Test Suite for EV Reference Program
Tests critical workflows before code quality improvements
"""
import requests
import time
import json
from datetime import datetime

class EVProgramSmokeTests:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'tests': []
        }
    
    def log_test(self, test_name, status, details=""):
        """Log test results"""
        self.results['total_tests'] += 1
        if status == "PASS":
            self.results['passed'] += 1
            print(f"✅ {test_name}: PASS")
        else:
            self.results['failed'] += 1
            print(f"❌ {test_name}: FAIL - {details}")
        
        self.results['tests'].append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_application_startup(self):
        """Test basic application accessibility"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.log_test("Application Startup", "PASS")
                return True
            else:
                self.log_test("Application Startup", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Application Startup", "FAIL", str(e))
            return False
    
    def test_login_page_accessibility(self):
        """Test login page loads correctly"""
        try:
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code == 200 and "csrf_token" in response.text:
                self.log_test("Login Page Accessibility", "PASS")
                return True
            else:
                self.log_test("Login Page Accessibility", "FAIL", "Missing CSRF token or wrong status")
                return False
        except Exception as e:
            self.log_test("Login Page Accessibility", "FAIL", str(e))
            return False
    
    def test_csrf_token_generation(self):
        """Test CSRF token is properly generated"""
        try:
            response = self.session.get(f"{self.base_url}/login")
            if 'name="csrf_token"' in response.text:
                self.log_test("CSRF Token Generation", "PASS")
                return True
            else:
                self.log_test("CSRF Token Generation", "FAIL", "No CSRF token found in form")
                return False
        except Exception as e:
            self.log_test("CSRF Token Generation", "FAIL", str(e))
            return False
    
    def test_invalid_login_protection(self):
        """Test invalid login attempts are handled gracefully"""
        try:
            # Get CSRF token first
            response = self.session.get(f"{self.base_url}/login")
            csrf_token = self._extract_csrf_token(response.text)
            
            if not csrf_token:
                self.log_test("Invalid Login Protection", "FAIL", "Could not extract CSRF token")
                return False
            
            # Test invalid login
            login_data = {
                'user_id': 'INVALID123',
                'password': 'wrongpassword',
                'csrf_token': csrf_token
            }
            
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            # Should not redirect (200) and show login form again
            if response.status_code == 200:
                self.log_test("Invalid Login Protection", "PASS")
                return True
            else:
                self.log_test("Invalid Login Protection", "FAIL", f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Invalid Login Protection", "FAIL", str(e))
            return False
    
    def test_admin_route_protection(self):
        """Test admin routes require authentication"""
        try:
            response = self.session.get(f"{self.base_url}/admin")
            # Should get 404 or redirect when not authenticated
            if response.status_code in [404, 302]:
                self.log_test("Admin Route Protection", "PASS")
                return True
            else:
                self.log_test("Admin Route Protection", "FAIL", f"Unprotected admin access: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Route Protection", "FAIL", str(e))
            return False
    
    def test_static_resource_loading(self):
        """Test static resources are accessible"""
        try:
            # Test if Bootstrap CSS loads (common static resource)
            response = self.session.get(f"{self.base_url}/")
            if "bootstrap" in response.text.lower():
                self.log_test("Static Resource Loading", "PASS")
                return True
            else:
                self.log_test("Static Resource Loading", "FAIL", "Bootstrap CSS not found")
                return False
        except Exception as e:
            self.log_test("Static Resource Loading", "FAIL", str(e))
            return False
    
    def _extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML form"""
        try:
            import re
            pattern = r'name="csrf_token"[^>]*value="([^"]*)"'
            match = re.search(pattern, html_content)
            return match.group(1) if match else None
        except:
            return None
    
    def run_all_tests(self):
        """Run complete smoke test suite"""
        print("🚀 Starting EV Reference Program Smoke Tests...")
        print("=" * 60)
        
        tests = [
            self.test_application_startup,
            self.test_login_page_accessibility,
            self.test_csrf_token_generation,
            self.test_invalid_login_protection,
            self.test_admin_route_protection,
            self.test_static_resource_loading
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(0.5)  # Small delay between tests
            except Exception as e:
                self.log_test(test.__name__, "FAIL", f"Exception: {e}")
        
        print("\n" + "=" * 60)
        print(f"🎯 SMOKE TEST RESULTS:")
        print(f"   Total Tests: {self.results['total_tests']}")
        print(f"   Passed: {self.results['passed']}")
        print(f"   Failed: {self.results['failed']}")
        
        success_rate = (self.results['passed'] / self.results['total_tests']) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.results['failed'] == 0:
            print("🎉 ALL SMOKE TESTS PASSED! Application is stable for code quality improvements.")
            return True
        else:
            print("⚠️  Some tests failed. Fix these issues before making code changes.")
            return False

if __name__ == "__main__":
    smoke_tests = EVProgramSmokeTests()
    success = smoke_tests.run_all_tests()
    
    # Save results to file
    with open('smoke_test_results.json', 'w') as f:
        json.dump(smoke_tests.results, f, indent=2)
    
    exit(0 if success else 1)
