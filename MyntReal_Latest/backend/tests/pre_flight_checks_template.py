"""
Frontend Testing Pre-Flight Checks Template
MNR EV Reference Program

MANDATORY: Run this BEFORE any Selenium/browser automation testing
"""

import requests
import sys

# Configuration
BASE_URL = 'http://localhost:5000'
BACKEND_URL = 'http://localhost:8000'

# Test credentials to verify
TEST_CREDENTIALS = {
    'rvz_id': {'mnr_id': 'MNR182364369', 'password': 'RVZ@ADMIN'},
    'super_admin': {'mnr_id': 'MNR182371007', 'password': 'Super@123admin'},
    'finance_admin': {'mnr_id': 'MNR182371010', 'password': 'Fintech@123'},
    'admin': {'mnr_id': 'MNR182322707', 'password': 'System@admin'},
    'test_user': {'mnr_id': 'MNR1800346', 'password': '123456'}
}

def check_phase_1_infrastructure():
    """Phase 1: Infrastructure Health"""
    print("\n" + "="*60)
    print("PHASE 1: Infrastructure Health")
    print("="*60)
    
    # Backend API
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Backend API: PASS ({response.status_code})")
        else:
            print(f"❌ Backend API: FAIL ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Backend API: FAIL - {str(e)}")
        return False
    
    # Frontend Server
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code in [200, 302]:
            print(f"✅ Frontend Server: PASS ({response.status_code})")
        else:
            print(f"❌ Frontend Server: FAIL ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Frontend Server: FAIL - {str(e)}")
        return False
    
    return True


def check_phase_2_routes():
    """Phase 2: Route Validation"""
    print("\n" + "="*60)
    print("PHASE 2: Route Validation")
    print("="*60)
    
    routes = [
        '/admin/dashboard',
        '/super-admin/dashboard',
        '/finance/dashboard',
        '/rvz/dashboard'
    ]
    
    all_passed = True
    for route in routes:
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=5)
            if response.status_code in [200, 302]:
                print(f"✅ {route}: PASS ({response.status_code})")
            elif response.status_code == 404:
                print(f"❌ {route}: FAIL - Route missing (404)")
                all_passed = False
            else:
                print(f"⚠️  {route}: WARN ({response.status_code})")
        except Exception as e:
            print(f"❌ {route}: FAIL - {str(e)}")
            all_passed = False
    
    return all_passed


def check_phase_3_login():
    """Phase 3: Login Endpoint Validation"""
    print("\n" + "="*60)
    print("PHASE 3: Login Endpoint")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={'mnr_id': 'TEST', 'password': 'TEST'},
            timeout=5
        )
        
        # 400/401/422 are all acceptable (endpoint works, just wrong creds)
        if response.status_code in [400, 401, 422]:
            print(f"✅ Login Endpoint: PASS ({response.status_code} - endpoint works)")
            return True
        elif response.status_code == 404:
            print(f"❌ Login Endpoint: FAIL - Endpoint missing (404)")
            return False
        else:
            print(f"⚠️  Login Endpoint: WARN ({response.status_code})")
            return True
    except Exception as e:
        print(f"❌ Login Endpoint: FAIL - {str(e)}")
        return False


def check_phase_4_credentials():
    """Phase 4: Test Credentials (informational only)"""
    print("\n" + "="*60)
    print("PHASE 4: Test Credentials")
    print("="*60)
    print("\nℹ️  Please manually verify these credentials work:")
    print("   (Login via browser and confirm dashboard loads)\n")
    
    for role, creds in TEST_CREDENTIALS.items():
        print(f"   {role.upper():15} {creds['mnr_id']:15} {creds['password']}")
    
    print("\n✅ Credentials documented (manual verification required)")
    return True


def check_phase_5_feature_specific(feature_name="awards"):
    """Phase 5: Feature-Specific Checks"""
    print("\n" + "="*60)
    print(f"PHASE 5: {feature_name.upper()} Feature Checks")
    print("="*60)
    
    # Check API endpoints exist (should return 401, not 404)
    endpoints = [
        f'/api/v1/awards/admin/awards/pending',
        f'/api/v1/awards/super-admin/awards/pending',
        f'/api/v1/awards/finance/awards/pending',
        f'/api/v1/awards/rvz/awards/oversight'
    ]
    
    all_passed = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if response.status_code == 401:
                print(f"✅ {endpoint}: EXISTS (401 - auth required)")
            elif response.status_code == 404:
                print(f"❌ {endpoint}: MISSING (404)")
                all_passed = False
            else:
                print(f"⚠️  {endpoint}: WARN ({response.status_code})")
        except Exception as e:
            print(f"❌ {endpoint}: FAIL - {str(e)}")
            all_passed = False
    
    return all_passed


def main():
    """Run all pre-flight checks"""
    print("\n" + "🚀"*30)
    print("FRONTEND TESTING PRE-FLIGHT CHECKS")
    print("🚀"*30)
    
    results = {
        'Phase 1: Infrastructure': check_phase_1_infrastructure(),
        'Phase 2: Routes': check_phase_2_routes(),
        'Phase 3: Login': check_phase_3_login(),
        'Phase 4: Credentials': check_phase_4_credentials(),
        'Phase 5: Feature-Specific': check_phase_5_feature_specific()
    }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for phase, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {phase}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ ALL PRE-FLIGHT CHECKS PASSED")
        print("🚀 Ready to run Selenium tests!")
        print("="*60 + "\n")
        sys.exit(0)
    else:
        print("❌ PRE-FLIGHT CHECKS FAILED")
        print("⚠️  Fix infrastructure issues before running Selenium tests")
        print("="*60 + "\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
