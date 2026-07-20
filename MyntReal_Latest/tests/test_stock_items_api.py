#!/usr/bin/env python3
"""
Stock Items API CRUD Tests
DC Protocol Compliant - Full End-to-End API Testing
Tests: CREATE, READ, UPDATE, DELETE with various scenarios
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:8001"
API_URL = f"{BASE_URL}/api/v1/staff/accounts"

def get_auth_token():
    """Get authentication token for testing"""
    response = requests.post(
        f"{BASE_URL}/api/v1/staff/auth/login",
        json={"employee_id": "MR10001", "password": "Test@123"}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    return None

def test_stock_items_crud():
    """Run comprehensive CRUD tests for Stock Items"""
    results = []
    test_item_code = f"TST{datetime.now().strftime('%H%M%S')}"
    created_item_id = None
    
    print("=" * 60)
    print("STOCK ITEMS API CRUD TEST SUITE")
    print("=" * 60)
    
    token = get_auth_token()
    if not token:
        print("CRITICAL: Failed to authenticate")
        return {"passed": 0, "failed": 1, "results": [{"test": "Authentication", "status": "FAIL"}]}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n[1] LIST STOCK ITEMS (READ)")
    try:
        resp = requests.get(f"{API_URL}/stock-items?include_summary=true", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("stock_items", [])
            print(f"    Status: {resp.status_code}")
            print(f"    Items found: {len(items)}")
            results.append({"test": "List Stock Items", "status": "PASS", "details": f"{len(items)} items"})
        else:
            print(f"    Status: {resp.status_code}")
            print(f"    Error: {resp.text[:200]}")
            results.append({"test": "List Stock Items", "status": "FAIL", "details": resp.text[:100]})
    except Exception as e:
        print(f"    Exception: {e}")
        results.append({"test": "List Stock Items", "status": "FAIL", "details": str(e)})
    
    print(f"\n[2] CREATE STOCK ITEM")
    try:
        payload = {
            "item_name": f"API Test Item {test_item_code}",
            "item_code": test_item_code,
            "item_category": "PRODUCT",
            "unit_of_measure": "PCS",
            "applicable_companies": [],
            "description": "Created via API test",
            "purchase_rate": 100.00,
            "selling_rate": 150.00,
            "reorder_level": 10
        }
        resp = requests.post(f"{API_URL}/stock-items", headers=headers, json=payload)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                created_item_id = data.get("stock_item", {}).get("id")
                print(f"    Created: {test_item_code} (ID: {created_item_id})")
                results.append({"test": "Create Stock Item", "status": "PASS", "details": f"ID: {created_item_id}"})
            else:
                print(f"    Message: {data.get('message')}")
                results.append({"test": "Create Stock Item", "status": "FAIL", "details": data.get("message")})
        else:
            print(f"    Error: {resp.text[:200]}")
            results.append({"test": "Create Stock Item", "status": "FAIL", "details": resp.text[:100]})
    except Exception as e:
        print(f"    Exception: {e}")
        results.append({"test": "Create Stock Item", "status": "FAIL", "details": str(e)})
    
    print(f"\n[3] CREATE DUPLICATE ITEM (should fail with 409)")
    try:
        payload = {
            "item_name": f"Duplicate Test {test_item_code}",
            "item_code": test_item_code,
            "item_category": "PRODUCT",
            "unit_of_measure": "PCS",
            "applicable_companies": [],
            "purchase_rate": 100.00,
            "selling_rate": 150.00
        }
        resp = requests.post(f"{API_URL}/stock-items", headers=headers, json=payload)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 409:
            data = resp.json()
            print(f"    Correctly rejected: {data.get('message', '')[:100]}")
            results.append({"test": "Duplicate Rejection", "status": "PASS", "details": "409 Conflict"})
        else:
            print(f"    Unexpected: {resp.text[:200]}")
            results.append({"test": "Duplicate Rejection", "status": "FAIL", "details": f"Expected 409, got {resp.status_code}"})
    except Exception as e:
        print(f"    Exception: {e}")
        results.append({"test": "Duplicate Rejection", "status": "FAIL", "details": str(e)})
    
    print(f"\n[4] UPDATE STOCK ITEM")
    if created_item_id:
        try:
            payload = {
                "item_name": f"Updated API Test Item {test_item_code}",
                "description": "Updated via API test",
                "selling_rate": 175.00
            }
            resp = requests.put(f"{API_URL}/stock-items/{created_item_id}", headers=headers, json=payload)
            print(f"    Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    print(f"    Updated: {data.get('stock_item', {}).get('item_name')}")
                    results.append({"test": "Update Stock Item", "status": "PASS", "details": "Updated successfully"})
                else:
                    print(f"    Message: {data.get('message')}")
                    results.append({"test": "Update Stock Item", "status": "FAIL", "details": data.get("message")})
            else:
                print(f"    Error: {resp.text[:200]}")
                results.append({"test": "Update Stock Item", "status": "FAIL", "details": resp.text[:100]})
        except Exception as e:
            print(f"    Exception: {e}")
            results.append({"test": "Update Stock Item", "status": "FAIL", "details": str(e)})
    else:
        print("    SKIPPED: No item to update")
        results.append({"test": "Update Stock Item", "status": "SKIP", "details": "No item created"})
    
    print(f"\n[5] GET SINGLE ITEM BY CODE")
    try:
        resp = requests.get(f"{API_URL}/stock-items/code/{test_item_code}", headers=headers)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            item = data.get("stock_item", {})
            print(f"    Found: {item.get('item_name')} (Rate: {item.get('selling_rate')})")
            results.append({"test": "Get Item By Code", "status": "PASS", "details": f"Found {test_item_code}"})
        else:
            print(f"    Error: {resp.text[:200]}")
            results.append({"test": "Get Item By Code", "status": "FAIL", "details": resp.text[:100]})
    except Exception as e:
        print(f"    Exception: {e}")
        results.append({"test": "Get Item By Code", "status": "FAIL", "details": str(e)})
    
    print(f"\n[6] DELETE (DEACTIVATE) STOCK ITEM")
    if created_item_id:
        try:
            resp = requests.delete(f"{API_URL}/stock-items/{created_item_id}", headers=headers)
            print(f"    Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    print(f"    Deactivated: ID {created_item_id}")
                    results.append({"test": "Delete Stock Item", "status": "PASS", "details": "Deactivated"})
                else:
                    print(f"    Message: {data.get('message')}")
                    results.append({"test": "Delete Stock Item", "status": "FAIL", "details": data.get("message")})
            else:
                print(f"    Error: {resp.text[:200]}")
                results.append({"test": "Delete Stock Item", "status": "FAIL", "details": resp.text[:100]})
        except Exception as e:
            print(f"    Exception: {e}")
            results.append({"test": "Delete Stock Item", "status": "FAIL", "details": str(e)})
    else:
        print("    SKIPPED: No item to delete")
        results.append({"test": "Delete Stock Item", "status": "SKIP", "details": "No item created"})
    
    print(f"\n[7] VERIFY DEACTIVATION (include_inactive)")
    try:
        resp = requests.get(f"{API_URL}/stock-items?include_inactive=true&search={test_item_code}", headers=headers)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("stock_items", [])
            if items:
                item = items[0]
                is_active = item.get("is_active", True)
                print(f"    Found: {item.get('item_code')} - is_active: {is_active}")
                if not is_active:
                    results.append({"test": "Verify Deactivation", "status": "PASS", "details": "Item is inactive"})
                else:
                    results.append({"test": "Verify Deactivation", "status": "FAIL", "details": "Item still active"})
            else:
                results.append({"test": "Verify Deactivation", "status": "PASS", "details": "Item not in active list"})
        else:
            results.append({"test": "Verify Deactivation", "status": "FAIL", "details": resp.text[:100]})
    except Exception as e:
        results.append({"test": "Verify Deactivation", "status": "FAIL", "details": str(e)})
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL" if r["status"] == "FAIL" else "SKIP"
        print(f"[{icon}] {r['test']}: {r.get('details', '')[:50]}")
    
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    return {"passed": passed, "failed": failed, "skipped": skipped, "results": results}


if __name__ == "__main__":
    summary = test_stock_items_crud()
    sys.exit(0 if summary["failed"] == 0 else 1)
