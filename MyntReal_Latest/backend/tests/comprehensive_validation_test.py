"""
Comprehensive End-to-End Validation Testing System
Tests all forms, endpoints, and validations across the entire MNR 2.0 Reference System
"""

import requests
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sys

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ComprehensiveValidator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_result(self, category: str, test_name: str, status: str, details: str = ""):
        """Log test result"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
            print(f"{Colors.OKGREEN}✅ PASS{Colors.ENDC} | {category} | {test_name}")
        else:
            self.failed_tests += 1
            print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} | {category} | {test_name}")
            if details:
                print(f"   {Colors.WARNING}└─ {details}{Colors.ENDC}")
        
        self.results.append({
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_api_health(self):
        """Test API health and basic connectivity"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}TESTING: API HEALTH & CONNECTIVITY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_result("API Health", "Health Check Endpoint", "PASS", f"Message: {data.get('message')}")
            else:
                self.log_result("API Health", "Health Check Endpoint", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("API Health", "Health Check Endpoint", "FAIL", str(e))
    
    def test_user_registration_validations(self):
        """Test all user registration validation scenarios"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}TESTING: USER REGISTRATION VALIDATIONS{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        import random
        import time
        timestamp = int(time.time() * 1000)
        rand_id = random.randint(1000, 9999)
        
        test_cases = [
            {
                "name": "Valid registration with 'name' field",
                "data": {
                    "name": f"Test User {rand_id}",
                    "email": f"testuser{timestamp}a@example.com",
                    "password": "Test123456",
                    "phone_number": f"98765{timestamp % 100000:05d}",
                    "sponsor_id": "MNR1800018",
                    "position": "Left"
                },
                "expected_status": 200,
                "should_pass": True
            },
            {
                "name": "Valid registration with 'first_name' and 'last_name'",
                "data": {
                    "first_name": "Test",
                    "last_name": f"User {rand_id + 1}",
                    "email": f"testuser{timestamp}b@example.com",
                    "password": "Test123456",
                    "mobile": f"98765{(timestamp + 1) % 100000:05d}",
                    "sponsor_id": "MNR1800018",
                    "position": "Right"
                },
                "expected_status": 200,
                "should_pass": True
            },
            {
                "name": "Missing name fields (should fail)",
                "data": {
                    "email": "testuser3@example.com",
                    "password": "Test123456",
                    "phone_number": "9876543212",
                    "sponsor_id": "MNR1800018",
                    "position": "Left"
                },
                "expected_status": 400,
                "should_pass": False
            },
            {
                "name": "Single word name (should fail - new requirement)",
                "data": {
                    "name": "Madonna",
                    "password": "Test123456",
                    "phone_number": "9876543299",
                    "sponsor_id": "MNR1800018",
                    "position": "Left"
                },
                "expected_status": 400,
                "should_pass": False
            },
            {
                "name": "Invalid sponsor ID (should fail)",
                "data": {
                    "name": "Test User Four",
                    "email": "testuser4@example.com",
                    "password": "Test123456",
                    "phone_number": "9876543213",
                    "sponsor_id": "INVALID123",
                    "position": "Left"
                },
                "expected_status": 400,
                "should_pass": False
            },
            {
                "name": "Invalid position value (should fail)",
                "data": {
                    "name": "Test User Five",
                    "email": "testuser5@example.com",
                    "password": "Test123456",
                    "phone_number": "9876543214",
                    "sponsor_id": "MNR1800018",
                    "position": "Center"
                },
                "expected_status": 400,
                "should_pass": False
            },
            {
                "name": "Missing password (should fail)",
                "data": {
                    "name": "Test User Six",
                    "email": "testuser6@example.com",
                    "phone_number": "9876543215",
                    "sponsor_id": "MNR1800018",
                    "position": "Left"
                },
                "expected_status": 422,
                "should_pass": False
            }
        ]
        
        for test_case in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/v1/user/register",
                    json=test_case["data"],
                    timeout=15
                )
                
                if test_case["should_pass"]:
                    if response.status_code == test_case["expected_status"]:
                        self.log_result("User Registration", test_case["name"], "PASS")
                    else:
                        error_detail = response.json().get('detail', 'Unknown error') if response.text else 'No response'
                        self.log_result("User Registration", test_case["name"], "FAIL", 
                                      f"Expected {test_case['expected_status']}, got {response.status_code}: {error_detail}")
                else:
                    if response.status_code == test_case["expected_status"]:
                        self.log_result("User Registration", test_case["name"], "PASS", "Correctly rejected invalid data")
                    else:
                        self.log_result("User Registration", test_case["name"], "FAIL", 
                                      f"Expected {test_case['expected_status']}, got {response.status_code}")
            except Exception as e:
                self.log_result("User Registration", test_case["name"], "FAIL", str(e))
    
    def test_admin_endpoints(self):
        """Test admin endpoint accessibility and responses"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}TESTING: ADMIN ENDPOINTS{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        admin_endpoints = [
            ("/admin/dashboard", "Admin Dashboard HTML"),
            ("/super-admin/dashboard", "Super Admin Dashboard HTML"),
            ("/finance/dashboard", "Finance Admin Dashboard HTML"),
            ("/rvz/dashboard", "RVZ ID Dashboard HTML"),
            ("/api/v1/admin/dashboard-stats", "Admin Dashboard Stats API")
        ]
        
        for endpoint, description in admin_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                
                if endpoint.endswith("/dashboard"):
                    if response.status_code in [200, 401, 403]:
                        if response.status_code == 200:
                            self.log_result("Admin Endpoints", description, "PASS", "Accessible (HTML served)")
                        else:
                            self.log_result("Admin Endpoints", description, "PASS", "Protected (Auth required)")
                    else:
                        self.log_result("Admin Endpoints", description, "FAIL", f"Status: {response.status_code}")
                else:
                    if response.status_code in [200, 401, 403]:
                        self.log_result("Admin Endpoints", description, "PASS", f"Status: {response.status_code}")
                    else:
                        self.log_result("Admin Endpoints", description, "FAIL", f"Unexpected status: {response.status_code}")
            except Exception as e:
                self.log_result("Admin Endpoints", description, "FAIL", str(e))
    
    def test_terminology_compliance(self):
        """Test that 'Reference System' terminology is used instead of 'MLM'"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}TESTING: TERMINOLOGY COMPLIANCE (Reference System vs MLM){Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                message = data.get('message', '')
                
                if 'Reference System' in message and 'MLM' not in message:
                    self.log_result("Terminology", "Health Check Message", "PASS", f"Uses 'Reference System': {message}")
                elif 'MLM' in message:
                    self.log_result("Terminology", "Health Check Message", "FAIL", f"Still uses 'MLM': {message}")
                else:
                    self.log_result("Terminology", "Health Check Message", "FAIL", "No clear terminology found")
        except Exception as e:
            self.log_result("Terminology", "Health Check Message", "FAIL", str(e))
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}COMPREHENSIVE VALIDATION TEST REPORT{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}Total Tests Run:{Colors.ENDC} {self.total_tests}")
        print(f"{Colors.OKGREEN}Passed:{Colors.ENDC} {self.passed_tests}")
        print(f"{Colors.FAIL}Failed:{Colors.ENDC} {self.failed_tests}")
        
        if self.total_tests > 0:
            pass_rate = (self.passed_tests / self.total_tests) * 100
            print(f"{Colors.BOLD}Pass Rate:{Colors.ENDC} {pass_rate:.2f}%")
        
        if self.failed_tests > 0:
            print(f"\n{Colors.WARNING}FAILED TESTS:{Colors.ENDC}")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['category']}: {result['test_name']}")
                    if result['details']:
                        print(f"    Details: {result['details']}")
        
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        with open('/tmp/validation_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': self.total_tests,
                    'passed': self.passed_tests,
                    'failed': self.failed_tests,
                    'pass_rate': (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
                },
                'results': self.results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"{Colors.OKGREEN}✅ Detailed report saved to: /tmp/validation_report.json{Colors.ENDC}\n")
        
        return self.failed_tests == 0

def main():
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  MNR 2.0 Reference System - Comprehensive Validation Test Suite  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print(f"{Colors.ENDC}\n")
    
    validator = ComprehensiveValidator()
    
    validator.test_api_health()
    validator.test_terminology_compliance()
    validator.test_user_registration_validations()
    validator.test_admin_endpoints()
    
    success = validator.generate_report()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
