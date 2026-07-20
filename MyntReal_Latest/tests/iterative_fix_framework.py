#!/usr/bin/env python3
"""
ITERATIVE FIX-TEST-VERIFY FRAMEWORK
Process: Fix → Test → If broken → Expert → Fix → Test → Repeat until fixed
Don't move to next issue until current issue is 100% resolved
"""

import requests
import json
from datetime import datetime
from typing import Dict, List

class IterativeFixFramework:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.current_issue = None
        self.fix_attempts = 0
        self.max_attempts = 3
        
    def login(self, user_id: str, password: str) -> str:
        """Real login"""
        resp = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"user_id": user_id, "password": password}
        )
        if resp.status_code == 200:
            return resp.json()['access_token']
        raise Exception(f"Login failed: {resp.status_code}")
    
    def test_api(self, endpoint: str, method: str, token: str, data: Dict = None) -> Dict:
        """Test single API endpoint"""
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                resp = requests.get(f"{self.base_url}{endpoint}", headers=headers)
            elif method == 'POST':
                resp = requests.post(f"{self.base_url}{endpoint}", headers=headers, json=data)
            
            return {
                'passed': resp.status_code in [200, 201],
                'status_code': resp.status_code,
                'response': resp.json() if resp.status_code in [200, 201] else resp.text[:200],
                'error': None if resp.status_code in [200, 201] else f"Status {resp.status_code}"
            }
        except Exception as e:
            return {
                'passed': False,
                'status_code': None,
                'response': None,
                'error': str(e)
            }
    
    def verify_fix(self, issue_id: str, test_func) -> bool:
        """Verify if an issue has been fixed"""
        print(f"\n🔍 VERIFYING FIX: {issue_id}")
        print("─" * 80)
        
        result = test_func()
        
        if result['passed']:
            print(f"✅ VERIFIED: Issue {issue_id} is FIXED")
            return True
        else:
            print(f"❌ STILL BROKEN: Issue {issue_id}")
            print(f"   Error: {result.get('error', 'Unknown')}")
            return False

if __name__ == "__main__":
    framework = IterativeFixFramework()
    
    print("="*80)
    print("🔁 ITERATIVE FIX-TEST-VERIFY FRAMEWORK")
    print("="*80)
    print("Process: Fix → Test → Expert (if needed) → Repeat until 100% fixed")
    print("="*80)
    
    # Example: Test bonanza creation issue
    print("\n\n█ ISSUE #1: Bonanza Creation Returns 409 Duplicate Error")
    print("█"*80)
    
    token = framework.login("BEV182371007", "TestPass123!")
    
    def test_bonanza_creation():
        return framework.test_api(
            '/api/v1/bonanza/create',
            'POST',
            token,
            {
                'name': f'Test Bonanza {datetime.now().timestamp()}',
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
            }
        )
    
    # Initial test
    print("\n🧪 Initial Test:")
    is_fixed = framework.verify_fix("BONANZA_CREATE_409", test_bonanza_creation)
    
    if not is_fixed:
        print("\n⚠️  Issue NOT fixed - needs investigation and fix")
        print("📝 Next: Architect will analyze and provide fix guidance")

