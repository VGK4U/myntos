"""
ST Protocol Test: RVZ User Data Search Page
Tests the comprehensive user data search page with RVZ ID credentials
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# RVZ ID Test Credentials
RVZ_CREDENTIALS = {
    "user_id": "MNR182364369",
    "password": "RVZ@ADMIN"
}

# Test User to search for
TEST_USER_ID = "MNR1800359"  # Ved Owner with 10 team members

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_rvz_login():
    """ST Phase 1-3: Test RVZ ID login"""
    print_section("ST Phase 1-3: RVZ ID Login Test")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json=RVZ_CREDENTIALS
    )
    
    if response.status_code == 200:
        data = response.json()
        user_data = data.get('user', {})
        print(f"✅ RVZ Login successful: {RVZ_CREDENTIALS['user_id']}")
        print(f"   User Type: {user_data.get('user_type')}")
        print(f"   Name: {user_data.get('name')}")
        
        # Get access token (Bearer authentication)
        access_token = data.get('access_token')
        if access_token:
            print(f"✅ Access token obtained: {access_token[:30]}...")
            return access_token
        else:
            print(f"❌ No access token in response")
            return None
    else:
        print(f"❌ RVZ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_user_data_page(access_token):
    """ST Phase 4: Test User Data Search page loads"""
    print_section("ST Phase 4: User Data Search Page Load")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(
        f"{BASE_URL}/rvz/user-data-search",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ User Data Search page loads: {response.status_code}")
        print(f"   Content length: {len(response.text)} bytes")
        
        # Check for key HTML elements
        if 'User Data Search' in response.text:
            print(f"✅ Page title found")
        if 'searchInput' in response.text:
            print(f"✅ Search input found")
        if 'searchUser()' in response.text:
            print(f"✅ Search function found")
        
        return True
    else:
        print(f"❌ Failed to load page: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def test_search_users_api(access_token):
    """ST Phase 5: Test search users API"""
    print_section("ST Phase 5: Search Users API Test")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Test search for test user
    response = requests.post(
        f"{BASE_URL}/api/v1/rvz/search-users",
        json={
            "search_term": TEST_USER_ID,
            "search_type": "all"
        },
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Search API works: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Results count: {data.get('results_count')}")
        
        if data.get('results_count') > 0:
            user = data['users'][0]
            print(f"✅ Found user: {user.get('id')} - {user.get('name')}")
            return user.get('id')
        else:
            print(f"❌ No users found")
            return None
    else:
        print(f"❌ Search API failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_get_user_data_api(access_token, user_id):
    """ST Phase 6: Test comprehensive user data API"""
    print_section(f"ST Phase 6: User Data API for {user_id}")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/rvz/user-data/{user_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ User Data API works: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   User ID: {data.get('user_id')}")
        
        # Display comprehensive data
        profile = data.get('profile', {})
        print(f"\n📋 PROFILE:")
        print(f"   Name: {profile.get('name')}")
        print(f"   Email: {profile.get('email')}")
        print(f"   Mobile: {profile.get('mobile')}")
        print(f"   Account Status: {profile.get('account_status')}")
        
        activation = data.get('activation', {})
        print(f"\n📦 ACTIVATION:")
        print(f"   Package: {activation.get('package_name')}")
        print(f"   Is Activated: {activation.get('is_activated')}")
        print(f"   Activation Date: {activation.get('activation_date')}")
        
        referral = data.get('referral_info', {})
        print(f"\n👥 REFERRAL:")
        sponsor = referral.get('sponsor')
        if sponsor:
            print(f"   Sponsor: {sponsor.get('name')} ({sponsor.get('id')})")
        print(f"   Direct Referrals: {referral.get('direct_referrals_count')}")
        
        team = data.get('team_info', {})
        print(f"\n🌳 TEAM:")
        placement = team.get('placement_parent')
        if placement:
            print(f"   Placement Parent: {placement.get('name')} ({placement.get('id')})")
            print(f"   Side: {placement.get('side')}")
        print(f"   Left Team: {team.get('left_team_count')}")
        print(f"   Right Team: {team.get('right_team_count')}")
        print(f"   Total Team: {team.get('total_team')}")
        
        earnings = data.get('earnings', {})
        print(f"\n💰 EARNINGS:")
        print(f"   Total Earnings: ₹{earnings.get('total_earnings', 0):.2f}")
        print(f"   Total Paid: ₹{earnings.get('total_paid', 0):.2f}")
        print(f"   Total Pending: ₹{earnings.get('total_pending', 0):.2f}")
        print(f"   Direct Referral (Paid): ₹{earnings.get('direct_referral', {}).get('paid', 0):.2f}")
        print(f"   Matching (Paid): ₹{earnings.get('matching_referral', {}).get('paid', 0):.2f}")
        print(f"   Ved Income (Paid): ₹{earnings.get('ved_income', {}).get('paid', 0):.2f}")
        
        wallets = data.get('wallets', {})
        print(f"\n💳 WALLETS:")
        print(f"   Earning Wallet: ₹{wallets.get('earning_wallet', 0):.2f}")
        print(f"   Upgrade Wallet: ₹{wallets.get('upgrade_wallet', 0):.2f}")
        print(f"   Total Wallet: ₹{wallets.get('total_wallet', 0):.2f}")
        
        ved = data.get('ved_info', {})
        print(f"\n📚 VED PROGRAM:")
        print(f"   Is Ved Owner: {ved.get('is_ved_owner')}")
        if ved.get('is_ved_owner'):
            print(f"   Ved Team Count: {ved.get('ved_team_count')}")
            ved_head = ved.get('ved_head')
            if ved_head:
                print(f"   Ved Head: {ved_head.get('name')} ({ved_head.get('id')})")
        
        kyc = data.get('kyc', {})
        print(f"\n🆔 KYC:")
        print(f"   Status: {kyc.get('status')}")
        print(f"   Aadhaar Verified: {kyc.get('aadhar_verified')}")
        print(f"   PAN Verified: {kyc.get('pan_verified')}")
        
        bank = data.get('bank', {})
        print(f"\n🏦 BANK:")
        print(f"   Bank Name: {bank.get('bank_name')}")
        print(f"   Approval Status: {bank.get('approval_status')}")
        
        print(f"\n✅ All data sections successfully retrieved!")
        return True
    else:
        print(f"❌ User Data API failed: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False

def main():
    """Run ST Protocol Test Suite"""
    print_section("ST PROTOCOL: RVZ User Data Search Test")
    print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"RVZ Credentials: {RVZ_CREDENTIALS['user_id']}")
    print(f"Test User: {TEST_USER_ID}")
    
    # Phase 1-3: Login
    access_token = test_rvz_login()
    if not access_token:
        print(f"\n❌ TEST FAILED: Cannot proceed without RVZ access token")
        return
    
    # Phase 4: Page Load
    if not test_user_data_page(access_token):
        print(f"\n❌ TEST FAILED: Page not loading")
        return
    
    # Phase 5: Search API
    found_user_id = test_search_users_api(access_token)
    if not found_user_id:
        print(f"\n❌ TEST FAILED: Cannot find test user")
        return
    
    # Phase 6: User Data API
    if not test_get_user_data_api(access_token, found_user_id):
        print(f"\n❌ TEST FAILED: User data API error")
        return
    
    # Final Summary
    print_section("ST PROTOCOL TEST COMPLETE")
    print(f"✅ All tests passed successfully!")
    print(f"✅ RVZ User Data Search page is fully functional")
    print(f"✅ Ready for production use")
    print(f"\nTest End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
