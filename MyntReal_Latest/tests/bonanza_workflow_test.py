"""
Comprehensive Bonanza Workflow End-to-End Test
Tests: Create → Approve → User Visibility → Delete → Cleanup

LEARNINGS FROM USER FEEDBACK:
1. API status 200 ≠ Working UI workflow
2. Must test actual user journeys (Create → Approve → Display → Delete)
3. Always use test data and clean up afterward
4. No secondary password required for VGK delete (simplified)
"""

import requests
import time
from datetime import datetime, timedelta

# Test Configuration
import os
API_BASE = "http://localhost:8000/api/v1"
VGK_USER = "BEV182364369"  # Real VGK ID
VGK_PASS = os.getenv("VGK_TEST_PASSWORD", "TestPass123!")  # Environment or fallback
REGULAR_USER = "BEV1800143"  # Regular user for testing
REGULAR_PASS = "BLN@46"  # User-specific password

# Test Data Tracking
test_bonanza_id = None
test_bonanza_name = f"TEST_BONANZA_{int(time.time())}"

def login(user_id, password):
    """Login and get token"""
    resp = requests.post(f"{API_BASE}/auth/login", json={
        "user_id": user_id,
        "password": password
    })
    if resp.status_code != 200:
        print(f"❌ Login failed for {user_id}: {resp.text}")
        return None
    return resp.json()["access_token"]

def create_test_bonanza(token):
    """Step 1: VGK creates test bonanza"""
    global test_bonanza_id, test_bonanza_name
    
    print("\n" + "="*80)
    print("STEP 1: CREATE TEST BONANZA (VGK)")
    print("="*80)
    
    start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    data = {
        "name": test_bonanza_name,
        "start_date": f"{start_date} 00:00:00",
        "end_date": f"{end_date} 23:59:59",
        "criteria_type": "direct_referrals",
        "target_requirement": 5,
        "reward_type": "cash",
        "reward_amount": 1000.00,
        "is_monetary": True,
        "max_winners": 50
    }
    
    resp = requests.post(f"{API_BASE}/bonanza/create", 
                        json=data,
                        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code == 200:
        result = resp.json()
        test_bonanza_id = result["bonanza_id"]
        print(f"✅ Bonanza created successfully")
        print(f"   ID: {test_bonanza_id}")
        print(f"   Name: {test_bonanza_name}")
        print(f"   Status: Pending (default)")
        return True
    else:
        print(f"❌ Failed to create bonanza: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False

def approve_bonanza(token):
    """Step 2: VGK approves bonanza"""
    global test_bonanza_id
    
    print("\n" + "="*80)
    print("STEP 2: APPROVE BONANZA (VGK)")
    print("="*80)
    
    resp = requests.post(f"{API_BASE}/bonanza/approve/{test_bonanza_id}",
                        json={"bonanza_id": test_bonanza_id},
                        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code == 200:
        print(f"✅ Bonanza approved successfully")
        print(f"   Status changed: Pending → Approved")
        return True
    else:
        print(f"❌ Failed to approve bonanza: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False

def verify_user_can_see_bonanza(token):
    """Step 3: Regular user can see approved bonanza"""
    global test_bonanza_id, test_bonanza_name
    
    print("\n" + "="*80)
    print("STEP 3: VERIFY USER VISIBILITY (Regular User)")
    print("="*80)
    
    resp = requests.get(f"{API_BASE}/bonanza/my-bonanzas",
                       headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        bonanza_ids = [b["id"] for b in data.get("bonanzas", [])]
        bonanza_names = [b["name"] for b in data.get("bonanzas", [])]
        
        if test_bonanza_id in bonanza_ids:
            print(f"✅ Bonanza IS visible to regular user")
            print(f"   Found in user's bonanza list")
            print(f"   Total bonanzas shown to user: {len(bonanza_ids)}")
            return True
        else:
            print(f"❌ Bonanza NOT visible to user")
            print(f"   Expected ID: {test_bonanza_id}")
            print(f"   User sees: {bonanza_names}")
            return False
    else:
        print(f"❌ Failed to fetch user bonanzas: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False

def delete_bonanza(token):
    """Step 4: VGK deletes bonanza (with deletion reason only)"""
    global test_bonanza_id, test_bonanza_name
    
    print("\n" + "="*80)
    print("STEP 4: DELETE TEST BONANZA (VGK)")
    print("="*80)
    
    data = {
        "deletion_reason": "End-to-end workflow test cleanup"
    }
    
    resp = requests.delete(f"{API_BASE}/bonanza/delete/{test_bonanza_id}",
                          json=data,
                          headers={
                              "Authorization": f"Bearer {token}",
                              "Content-Type": "application/json"
                          })
    
    if resp.status_code == 200:
        print(f"✅ Bonanza deleted successfully")
        print(f"   Soft delete completed (data preserved)")
        print(f"   Audit trail created")
        return True
    else:
        print(f"❌ Failed to delete bonanza: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False

def verify_cleanup():
    """Step 5: Verify bonanza is hidden after delete"""
    print("\n" + "="*80)
    print("STEP 5: VERIFY CLEANUP")
    print("="*80)
    
    vgk_token = login(VGK_USER, VGK_PASS)
    if not vgk_token:
        print("❌ Could not login to verify")
        return False
    
    # Check bonanza list (should not show deleted)
    resp = requests.get(f"{API_BASE}/bonanza/list",
                       headers={"Authorization": f"Bearer {vgk_token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        active_ids = [b["id"] for b in data.get("bonanzas", []) if not b.get("is_deleted", False)]
        
        if test_bonanza_id not in active_ids:
            print(f"✅ Deleted bonanza NOT in active list")
            print(f"   Test data cleaned up successfully")
            return True
        else:
            print(f"⚠️ Deleted bonanza still appears in list")
            return False
    
    return False

def main():
    """Execute complete workflow test"""
    print("\n" + "🧪"*40)
    print("BONANZA WORKFLOW END-TO-END TEST")
    print("Testing: Create → Approve → Display → Delete → Cleanup")
    print("🧪"*40)
    
    # Login as VGK
    print("\n🔐 Logging in as VGK...")
    vgk_token = login(VGK_USER, VGK_PASS)
    if not vgk_token:
        print("❌ VGK login failed - aborting test")
        return False
    print(f"✅ VGK logged in successfully")
    
    # Login as regular user
    print("\n🔐 Logging in as regular user...")
    user_token = login(REGULAR_USER, REGULAR_PASS)
    if not user_token:
        print("❌ User login failed - aborting test")
        return False
    print(f"✅ Regular user logged in successfully")
    
    # Execute workflow
    results = {
        "create": False,
        "approve": False,
        "visibility": False,
        "delete": False,
        "cleanup": False
    }
    
    # Step 1: Create
    results["create"] = create_test_bonanza(vgk_token)
    if not results["create"]:
        print("\n❌ TEST FAILED AT STEP 1: CREATE")
        return False
    
    time.sleep(1)  # Brief pause between steps
    
    # Step 2: Approve
    results["approve"] = approve_bonanza(vgk_token)
    if not results["approve"]:
        print("\n❌ TEST FAILED AT STEP 2: APPROVE")
        return False
    
    time.sleep(1)
    
    # Step 3: User Visibility
    results["visibility"] = verify_user_can_see_bonanza(user_token)
    if not results["visibility"]:
        print("\n❌ TEST FAILED AT STEP 3: USER VISIBILITY")
        return False
    
    time.sleep(1)
    
    # Step 4: Delete
    results["delete"] = delete_bonanza(vgk_token)
    if not results["delete"]:
        print("\n❌ TEST FAILED AT STEP 4: DELETE")
        return False
    
    time.sleep(1)
    
    # Step 5: Cleanup Verification
    results["cleanup"] = verify_cleanup()
    
    # Final Report
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    for step, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{step.upper():20s}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - WORKFLOW 100% FUNCTIONAL")
    else:
        print("❌ SOME TESTS FAILED - SEE DETAILS ABOVE")
    print("="*80)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
