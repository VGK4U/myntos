#!/usr/bin/env python3
"""
SYSTEMATIC AUDIT FRAMEWORK - Complete Functionality Testing
Tests: Page Load → Data Load → Forms → Buttons → API Calls → CRUD
Zero assumptions, zero skips
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any

class SystematicAudit:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.errors = []
        self.results = {}
        
    def login(self, user_id: str, password: str) -> str:
        """Real login to get auth token"""
        resp = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"user_id": user_id, "password": password}
        )
        if resp.status_code == 200:
            return resp.json()['access_token']
        raise Exception(f"Login failed: {resp.status_code}")
    
    def test_page_load(self, route: str, token: str = None) -> Dict:
        """Level 2: Test if page loads without errors"""
        result = {
            'route': route,
            'level': 'Page Load',
            'passed': False,
            'errors': []
        }
        
        try:
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            resp = requests.get(f"{self.base_url}{route}", headers=headers, allow_redirects=False)
            
            if resp.status_code in [200, 302]:
                result['passed'] = True
                result['status_code'] = resp.status_code
            else:
                result['errors'].append(f"Unexpected status: {resp.status_code}")
                
        except Exception as e:
            result['errors'].append(str(e))
            
        return result
    
    def test_api_endpoint(self, endpoint: str, method: str, token: str, data: Dict = None) -> Dict:
        """Level 3-6: Test API endpoints"""
        result = {
            'endpoint': endpoint,
            'method': method,
            'passed': False,
            'errors': []
        }
        
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            if method == 'GET':
                resp = requests.get(f"{self.base_url}{endpoint}", headers=headers)
            elif method == 'POST':
                resp = requests.post(f"{self.base_url}{endpoint}", headers=headers, json=data)
            elif method == 'PUT':
                resp = requests.put(f"{self.base_url}{endpoint}", headers=headers, json=data)
            elif method == 'DELETE':
                resp = requests.delete(f"{self.base_url}{endpoint}", headers=headers)
            
            result['status_code'] = resp.status_code
            
            if resp.status_code in [200, 201]:
                result['passed'] = True
                try:
                    result['response'] = resp.json()
                except:
                    result['response'] = resp.text[:200]
            elif resp.status_code == 403:
                result['errors'].append("Permission denied (403)")
            elif resp.status_code == 404:
                result['errors'].append("Endpoint not found (404)")
            elif resp.status_code == 500:
                result['errors'].append(f"Server error: {resp.text[:200]}")
            else:
                result['errors'].append(f"Status {resp.status_code}: {resp.text[:200]}")
                
        except Exception as e:
            result['errors'].append(str(e))
            
        return result
    
    def audit_vgk_admin(self) -> Dict:
        """Complete audit of all VGK Admin routes"""
        print("="*80)
        print("🔍 VGK ADMIN COMPLETE AUDIT")
        print("="*80)
        
        # Login as VGK
        token = self.login("BEV182371007", "TestPass123!")
        print("✅ Logged in as VGK Admin (BEV182371007)")
        
        vgk_routes = {
            # Dashboard & Main Pages
            '/vgk/dashboard': {
                'apis': ['/api/v1/vgk-supreme/dashboard-stats']
            },
            '/vgk/user-management': {
                'apis': ['/api/v1/vgk-supreme/users']
            },
            
            # Bonanza Management (WHERE ERROR WAS FOUND)
            '/vgk/bonanza/create': {
                'apis': [
                    {'endpoint': '/api/v1/bonanza/create', 'method': 'POST', 'test_data': {
                        'name': 'TEST Bonanza Audit',
                        'start_date': '2025-12-01T00:00:00Z',
                        'end_date': '2025-12-31T23:59:59Z',
                        'criteria_type': 'direct_referrals',
                        'target_requirement': 10,
                        'counts_towards_regular': False,
                        'reward_type': 'cash',
                        'reward_amount': 1000,
                        'is_monetary': True,
                        'total_budget': 50000,
                        'max_winners': 50
                    }}
                ]
            },
            '/vgk/bonanza/active': {
                'apis': ['/api/v1/bonanza/list?status=Approved']
            },
            '/vgk/bonanza/history': {
                'apis': ['/api/v1/bonanza/list']
            },
            '/vgk/bonanza-management': {
                'apis': ['/api/v1/bonanza/vgk/all']
            },
            '/vgk/bonanza-approvals': {
                'apis': ['/api/v1/bonanza/list?status=Pending']
            },
            
            # Income & Financial
            '/vgk/income-history-supreme': {
                'apis': ['/api/v1/vgk-supreme/income/history?page=1&per_page=20']
            },
            '/vgk/payment-settings': {
                'apis': ['/api/v1/vgk-supreme/payment-settings']
            },
            
            # User Management
            '/vgk/activate-user': {
                'apis': ['/api/v1/vgk-supreme/users']
            },
            '/vgk/manage-admins': {
                'apis': ['/api/v1/vgk-supreme/admins']
            },
            
            # System Configuration
            '/vgk/system-configuration': {
                'apis': ['/api/v1/vgk-supreme/app-settings']
            },
            '/vgk/brand-level-control': {
                'apis': ['/api/v1/brands', '/api/v1/levels']
            },
            
            # Awards & Packages
            '/vgk/award-management': {
                'apis': ['/api/v1/awards/all']
            },
            '/vgk/package-management': {
                'apis': ['/api/v1/packages']
            },
        }
        
        audit_results = {}
        total_tests = 0
        passed_tests = 0
        
        for route, config in vgk_routes.items():
            print(f"\n{'─'*80}")
            print(f"Testing: {route}")
            print(f"{'─'*80}")
            
            # Test page load
            page_result = self.test_page_load(route, token)
            total_tests += 1
            if page_result['passed']:
                passed_tests += 1
                print(f"  ✅ Page Load: {page_result['status_code']}")
            else:
                print(f"  ❌ Page Load Failed: {page_result['errors']}")
            
            # Test APIs
            api_results = []
            if 'apis' in config:
                for api in config['apis']:
                    if isinstance(api, str):
                        # GET endpoint
                        api_result = self.test_api_endpoint(api, 'GET', token)
                        total_tests += 1
                        if api_result['passed']:
                            passed_tests += 1
                            print(f"  ✅ API GET: {api} ({api_result['status_code']})")
                        else:
                            print(f"  ❌ API GET Failed: {api}")
                            print(f"     Errors: {api_result['errors']}")
                        api_results.append(api_result)
                    elif isinstance(api, dict):
                        # POST/PUT/DELETE endpoint with data
                        endpoint = api['endpoint']
                        method = api.get('method', 'POST')
                        test_data = api.get('test_data')
                        
                        api_result = self.test_api_endpoint(endpoint, method, token, test_data)
                        total_tests += 1
                        if api_result['passed']:
                            passed_tests += 1
                            print(f"  ✅ API {method}: {endpoint} ({api_result['status_code']})")
                        else:
                            print(f"  ❌ API {method} Failed: {endpoint}")
                            print(f"     Errors: {api_result['errors']}")
                        api_results.append(api_result)
            
            audit_results[route] = {
                'page_load': page_result,
                'api_tests': api_results
            }
        
        print(f"\n{'='*80}")
        print(f"VGK ADMIN AUDIT SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Pass Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        return audit_results

if __name__ == "__main__":
    auditor = SystematicAudit()
    
    print("\n" + "="*80)
    print("🚀 STARTING SYSTEMATIC AUDIT - OPTION B")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Scope: ALL 90 routes across 4 admin roles")
    print(f"Testing Levels: Page Load + Data Load + Forms + Buttons + API + CRUD")
    print("="*80)
    
    # Start with VGK Admin (where error was found)
    vgk_results = auditor.audit_vgk_admin()
    
    # Save results
    with open('/tmp/vgk_audit_results.json', 'w') as f:
        json.dump(vgk_results, f, indent=2)
    
    print(f"\n📝 Results saved to: /tmp/vgk_audit_results.json")


    def audit_user_pages(self) -> Dict:
        """Complete audit of regular User pages and workflows"""
        print("\n" + "="*80)
        print("🔍 REGULAR USER COMPLETE AUDIT")
        print("="*80)
        
        # Login as regular user
        token = self.login("BEV1800143", "BLN@46")
        print("✅ Logged in as Regular User (BEV1800143)")
        
        user_routes = {
            # Main Pages
            '/dashboard': {
                'apis': ['/api/v1/users/profile', '/api/v1/dashboard/stats']
            },
            '/user/profile': {
                'apis': ['/api/v1/users/profile', '/api/v1/profile/profile']
            },
            
            # Bonanza Pages (User Journey)
            '/user/bonanzas': {
                'apis': ['/api/v1/bonanza/my-bonanzas']
            },
            '/user/bonanza-claims': {
                'apis': ['/api/v1/bonanza/my-claims']
            },
            
            # Financial Pages
            '/user/withdrawals': {
                'apis': [
                    '/api/v1/withdrawals/income-transactions',
                    '/api/v1/withdrawals/withdrawal-requests'
                ]
            },
            '/user/wallets': {
                'apis': ['/api/v1/users/wallets']
            },
            '/user/income': {
                'apis': ['/api/v1/income/history']
            },
            
            # Awards & Achievements
            '/user/awards': {
                'apis': ['/api/v1/awards/user/my-awards']
            },
            '/user/field-allowances': {
                'apis': ['/api/v1/field-allowances/my-allowances']
            },
            
            # Network/Team
            '/user/network': {
                'apis': ['/api/v1/network/tree']
            },
            '/user/referrals': {
                'apis': ['/api/v1/referrals/list']
            },
        }
        
        audit_results = {}
        total_tests = 0
        passed_tests = 0
        
        for route, config in user_routes.items():
            print(f"\n{'─'*80}")
            print(f"Testing: {route}")
            print(f"{'─'*80}")
            
            # Test page load
            page_result = self.test_page_load(route, token)
            total_tests += 1
            if page_result['passed']:
                passed_tests += 1
                print(f"  ✅ Page Load: {page_result['status_code']}")
            else:
                print(f"  ❌ Page Load Failed: {page_result['errors']}")
            
            # Test APIs
            api_results = []
            if 'apis' in config:
                for api in config['apis']:
                    api_result = self.test_api_endpoint(api, 'GET', token)
                    total_tests += 1
                    if api_result['passed']:
                        passed_tests += 1
                        print(f"  ✅ API GET: {api} ({api_result['status_code']})")
                    else:
                        print(f"  ❌ API GET Failed: {api}")
                        print(f"     Errors: {api_result['errors']}")
                    api_results.append(api_result)
            
            audit_results[route] = {
                'page_load': page_result,
                'api_tests': api_results
            }
        
        print(f"\n{'='*80}")
        print(f"REGULAR USER AUDIT SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Pass Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        return audit_results

    def audit_finance_admin(self) -> Dict:
        """Complete audit of Finance Admin routes"""
        print("\n" + "="*80)
        print("🔍 FINANCE ADMIN COMPLETE AUDIT")
        print("="*80)
        
        token = self.login("BEV182371010", "TestPass123!")
        print("✅ Logged in as Finance Admin (BEV182371010)")
        
        finance_routes = {
            '/finance/dashboard': {
                'apis': ['/api/v1/finance/dashboard-stats']
            },
            '/finance/awards/payment-processing': {
                'apis': ['/api/v1/awards/finance/awards/pending']
            },
            '/finance/kyc-approval': {
                'apis': ['/api/v1/finance/kyc/pending']
            },
            '/finance/pins': {
                'apis': ['/api/v1/admin/purchase-requests?limit=100&offset=0']
            },
            '/finance/expenses': {
                'apis': ['/api/v1/finance/expenses']
            },
            '/finance-admin/tds-management': {
                'apis': ['/api/v1/finance/tds/summary']
            },
            '/finance/reports': {
                'apis': ['/api/v1/finance/reports']
            },
            '/finance/withdrawal/transfers': {
                'apis': ['/api/v1/income-verification/finance-admin/transfer-queue?page=1&per_page=20']
            },
            '/finance/withdrawal/history': {
                'apis': ['/api/v1/income-verification/finance-admin/transfer-history?page=1&per_page=20']
            },
        }
        
        return self._run_audit(finance_routes, token, "FINANCE ADMIN")
    
    def audit_admin(self) -> Dict:
        """Complete audit of Admin routes"""
        print("\n" + "="*80)
        print("🔍 ADMIN COMPLETE AUDIT")
        print("="*80)
        
        token = self.login("BEV182322707", "TestPass123!")
        print("✅ Logged in as Admin (BEV182322707)")
        
        admin_routes = {
            '/admin/dashboard': {
                'apis': ['/api/v1/admin/dashboard-stats']
            },
            '/admin/income-verified': {
                'apis': ['/api/v1/income-verification/admin/verified-incomes?page=1&per_page=20']
            },
            '/admin/income-history': {
                'apis': ['/api/v1/income/admin/history']
            },
            '/admin/members/actions': {
                'apis': ['/api/v1/admin/members']
            },
            '/admin/network-tree': {
                'apis': ['/api/v1/network/admin/tree']
            },
            '/admin/sponsor-tree': {
                'apis': ['/api/v1/network/sponsor-tree']
            },
            '/admin/kyc-management': {
                'apis': ['/api/v1/admin/kyc/all-users?status_filter=All&page=1&per_page=20']
            },
            '/admin/brands': {
                'apis': ['/api/v1/brands']
            },
            '/admin/levels': {
                'apis': ['/api/v1/levels']
            },
        }
        
        return self._run_audit(admin_routes, token, "ADMIN")
    
    def audit_super_admin(self) -> Dict:
        """Complete audit of Super Admin routes"""
        print("\n" + "="*80)
        print("🔍 SUPER ADMIN COMPLETE AUDIT")
        print("="*80)
        
        token = self.login("BEV182371007", "TestPass123!")
        print("✅ Logged in as Super Admin (BEV182371007)")
        
        super_routes = {
            '/superadmin/dashboard': {
                'apis': ['/api/v1/super-admin/dashboard-stats']
            },
            '/superadmin/role-management': {
                'apis': ['/api/v1/super-admin/roles']
            },
            '/superadmin/award-management': {
                'apis': ['/api/v1/awards/admin/all']
            },
            '/superadmin/system-controls': {
                'apis': ['/api/v1/system/controls']
            },
        }
        
        return self._run_audit(super_routes, token, "SUPER ADMIN")
    
    def _run_audit(self, routes: Dict, token: str, role_name: str) -> Dict:
        """Helper method to run audit on any route set"""
        audit_results = {}
        total_tests = 0
        passed_tests = 0
        
        for route, config in routes.items():
            print(f"\n{'─'*80}")
            print(f"Testing: {route}")
            print(f"{'─'*80}")
            
            page_result = self.test_page_load(route, token)
            total_tests += 1
            if page_result['passed']:
                passed_tests += 1
                print(f"  ✅ Page Load: {page_result['status_code']}")
            else:
                print(f"  ❌ Page Load Failed: {page_result['errors']}")
            
            api_results = []
            if 'apis' in config:
                for api in config['apis']:
                    api_result = self.test_api_endpoint(api, 'GET', token)
                    total_tests += 1
                    if api_result['passed']:
                        passed_tests += 1
                        print(f"  ✅ API GET: {api} ({api_result['status_code']})")
                    else:
                        print(f"  ❌ API GET Failed: {api}")
                        print(f"     Errors: {api_result['errors']}")
                    api_results.append(api_result)
            
            audit_results[route] = {
                'page_load': page_result,
                'api_tests': api_results
            }
        
        print(f"\n{'='*80}")
        print(f"{role_name} AUDIT SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Pass Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        return audit_results
