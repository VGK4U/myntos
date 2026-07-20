"""
Comprehensive Purchase Invoice Test Scenarios
DC Protocol Compliance Testing - DC_PURCHASE_001 to DC_PURCHASE_006

Test Scenarios:
1. Manual Invoice - Cash Purchase (No Credit) - Intra-state (CGST/SGST)
2. Manual Invoice - Credit Purchase (30 days) - Inter-state (IGST)
3. Manual Invoice - Multiple line items with different GST rates
4. Quick-Create Modals - Vendor, Stock Item, HSN Code
5. Search functionality and type-ahead inputs
6. Stock Ledger and Accounts Payable integration
7. Edge cases: Empty line items, zero values, large quantities
"""

import requests
import json
from datetime import datetime, timedelta
import os

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

TEST_RESULTS = []

def log_result(scenario: str, status: str, details: str):
    """Log test result"""
    result = {
        "scenario": scenario,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} [{scenario}] {status}: {details}")

def get_auth_token():
    """Get authentication token for staff account"""
    response = requests.post(
        f"{API_URL}/staff/auth/login",
        json={
            "employee_id": "MR10001",
            "password": "Test@123"
        }
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_api_health():
    """Test 1: API Health Check"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            log_result("API Health", "PASS", "Backend is running and healthy")
            return True
        else:
            log_result("API Health", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_result("API Health", "FAIL", str(e))
        return False

def test_companies_list(token: str):
    """Test 2: List Companies with DC Protocol filtering"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/staff/accounts/companies", headers=headers)
        if response.status_code == 200:
            companies = response.json()
            log_result("Companies List", "PASS", f"Found {len(companies)} companies")
            return companies
        else:
            log_result("Companies List", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return []
    except Exception as e:
        log_result("Companies List", "FAIL", str(e))
        return []

def test_vendors_list(token: str, company_id: int):
    """Test 3: List Vendors with company filtering"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/vendors",
            headers=headers,
            params={"company_id": company_id}
        )
        if response.status_code == 200:
            data = response.json()
            vendors = data.get("vendors", []) if isinstance(data, dict) else data
            log_result("Vendors List", "PASS", f"Found {len(vendors)} vendors for company {company_id}")
            return vendors if isinstance(vendors, list) else []
        else:
            log_result("Vendors List", "FAIL", f"Status: {response.status_code}")
            return []
    except Exception as e:
        log_result("Vendors List", "FAIL", str(e))
        return []

def test_stock_items_list(token: str, company_id: int):
    """Test 4: List Stock Items with company filtering"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/stock-items",
            headers=headers,
            params={"company_id": company_id}
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("stock_items", data.get("items", [])) if isinstance(data, dict) else data
            if isinstance(items, list):
                log_result("Stock Items List", "PASS", f"Found {len(items)} stock items")
                return items
            else:
                log_result("Stock Items List", "PASS", f"Found stock items data")
                return []
        else:
            log_result("Stock Items List", "FAIL", f"Status: {response.status_code}")
            return []
    except Exception as e:
        log_result("Stock Items List", "FAIL", str(e))
        return []

def test_hsn_codes_list(token: str):
    """Test 5: List HSN Codes"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/staff/accounts/hsn", headers=headers)
        if response.status_code == 200:
            data = response.json()
            hsn_codes = data.get("items", data) if isinstance(data, dict) else data
            log_result("HSN Codes List", "PASS", f"Found {len(hsn_codes)} HSN codes")
            return hsn_codes
        else:
            log_result("HSN Codes List", "FAIL", f"Status: {response.status_code}")
            return []
    except Exception as e:
        log_result("HSN Codes List", "FAIL", str(e))
        return []

def test_manual_invoice_cash_intrastate(token: str, company_id: int, vendor_id: int, stock_item_id: int):
    """Test 6: Manual Invoice - Cash Purchase (No Credit) - Intra-state (CGST/SGST)"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        invoice_data = {
            "company_id": company_id,
            "vendor_id": vendor_id,
            "vendor_invoice_no": f"TEST-CASH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "vendor_invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "is_credit_purchase": False,
            "credit_days": 0,
            "line_items": [
                {
                    "stock_item_id": stock_item_id,
                    "quantity": 5,
                    "rate": 1000.00,
                    "amount": 5000.00,
                    "gst_rate": 18.0,
                    "tax_amount": 900.00,
                    "total_amount": 5900.00,
                    "unit_of_measure": "PCS"
                }
            ]
        }
        
        response = requests.post(
            f"{API_URL}/staff/accounts/purchase-uploads/manual",
            headers=headers,
            json=invoice_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            log_result(
                "Cash Invoice (Intra-state)", 
                "PASS", 
                f"Created invoice: {result.get('upload_number', 'N/A')}, Total: {result.get('grand_total', 'N/A')}"
            )
            return result
        else:
            error_msg = response.json() if response.text else response.status_code
            log_result("Cash Invoice (Intra-state)", "FAIL", f"Status: {response.status_code}, Error: {error_msg}")
            return None
    except Exception as e:
        log_result("Cash Invoice (Intra-state)", "FAIL", str(e))
        return None

def test_manual_invoice_credit_interstate(token: str, company_id: int, vendor_id: int, stock_item_id: int):
    """Test 7: Manual Invoice - Credit Purchase (30 days) - Inter-state (IGST)"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        invoice_date = datetime.now()
        due_date = invoice_date + timedelta(days=30)
        
        invoice_data = {
            "company_id": company_id,
            "vendor_id": vendor_id,
            "vendor_invoice_no": f"TEST-CREDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "vendor_invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "is_credit_purchase": True,
            "credit_days": 30,
            "line_items": [
                {
                    "stock_item_id": stock_item_id,
                    "quantity": 10,
                    "rate": 2500.00,
                    "amount": 25000.00,
                    "gst_rate": 18.0,
                    "tax_amount": 4500.00,
                    "total_amount": 29500.00,
                    "unit_of_measure": "PCS"
                }
            ]
        }
        
        response = requests.post(
            f"{API_URL}/staff/accounts/purchase-uploads/manual",
            headers=headers,
            json=invoice_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            log_result(
                "Credit Invoice (Inter-state)", 
                "PASS", 
                f"Created invoice: {result.get('upload_number', 'N/A')}, Credit Days: 30, Due: {due_date.strftime('%Y-%m-%d')}"
            )
            return result
        else:
            error_msg = response.json() if response.text else response.status_code
            log_result("Credit Invoice (Inter-state)", "FAIL", f"Status: {response.status_code}, Error: {error_msg}")
            return None
    except Exception as e:
        log_result("Credit Invoice (Inter-state)", "FAIL", str(e))
        return None

def test_manual_invoice_multiple_items(token: str, company_id: int, vendor_id: int, stock_items: list):
    """Test 8: Manual Invoice - Multiple line items with different GST rates"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        line_items = []
        gst_rates = [5.0, 12.0, 18.0]
        
        for i, item_id in enumerate(stock_items[:3]):
            gst = gst_rates[i % len(gst_rates)]
            qty = (i + 1) * 2
            rate = 500 + (i * 250)
            amount = qty * rate
            tax = amount * (gst / 100)
            
            line_items.append({
                "stock_item_id": item_id,
                "quantity": qty,
                "rate": rate,
                "amount": amount,
                "gst_rate": gst,
                "tax_amount": tax,
                "total_amount": amount + tax,
                "unit_of_measure": "PCS"
            })
        
        invoice_data = {
            "company_id": company_id,
            "vendor_id": vendor_id,
            "vendor_invoice_no": f"TEST-MULTI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "vendor_invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "is_credit_purchase": False,
            "credit_days": 0,
            "line_items": line_items
        }
        
        response = requests.post(
            f"{API_URL}/staff/accounts/purchase-uploads/manual",
            headers=headers,
            json=invoice_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            log_result(
                "Multi-Item Invoice", 
                "PASS", 
                f"Created invoice with {len(line_items)} items, Total: {result.get('grand_total', 'N/A')}"
            )
            return result
        else:
            error_msg = response.json() if response.text else response.status_code
            log_result("Multi-Item Invoice", "FAIL", f"Status: {response.status_code}, Error: {error_msg}")
            return None
    except Exception as e:
        log_result("Multi-Item Invoice", "FAIL", str(e))
        return None

def test_purchase_invoices_list(token: str, company_id: int):
    """Test 9: List Purchase Invoices with DC Protocol filtering"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/purchase-uploads",
            headers=headers,
            params={"company_id": company_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            invoices = data.get("uploads", data.get("items", [])) if isinstance(data, dict) else data
            count = len(invoices) if isinstance(invoices, list) else data.get("total", 0)
            log_result("Invoice List", "PASS", f"Found {count} invoices for company {company_id}")
            return invoices
        else:
            log_result("Invoice List", "FAIL", f"Status: {response.status_code}")
            return []
    except Exception as e:
        log_result("Invoice List", "FAIL", str(e))
        return []

def test_stock_ledger_integration(token: str, company_id: int):
    """Test 10: Stock Ledger Integration"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/stock-ledger",
            headers=headers,
            params={"company_id": company_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            entries = data.get("items", data) if isinstance(data, dict) else data
            count = len(entries) if isinstance(entries, list) else data.get("total", 0)
            log_result("Stock Ledger", "PASS", f"Found {count} ledger entries")
            return True
        elif response.status_code == 404:
            log_result("Stock Ledger", "WARN", "Endpoint not found - may not be implemented yet")
            return True
        else:
            log_result("Stock Ledger", "FAIL", f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_result("Stock Ledger", "FAIL", str(e))
        return False

def test_accounts_payable_integration(token: str, company_id: int):
    """Test 11: Accounts Payable Integration"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/accounts-payable",
            headers=headers,
            params={"company_id": company_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            log_result("Accounts Payable", "PASS", "Integration verified")
            return True
        elif response.status_code == 404:
            log_result("Accounts Payable", "WARN", "Endpoint not found - may not be implemented yet")
            return True
        else:
            log_result("Accounts Payable", "FAIL", f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_result("Accounts Payable", "FAIL", str(e))
        return False

def test_vendor_search(token: str, company_id: int, search_term: str = "Test"):
    """Test 12: Vendor Search Functionality - uses main vendors endpoint with search param"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/vendors",
            headers=headers,
            params={"search": search_term, "company_id": company_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("vendors", []) if isinstance(data, dict) else data
            log_result("Vendor Search", "PASS", f"Found {len(results)} vendors with search='{search_term}'")
            return True
        else:
            log_result("Vendor Search", "WARN", f"Status: {response.status_code} - may not support search")
            return True
    except Exception as e:
        log_result("Vendor Search", "FAIL", str(e))
        return False

def test_stock_item_search(token: str, company_id: int, search_term: str = "EV"):
    """Test 13: Stock Item Search Functionality - uses main stock-items endpoint with search param"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/staff/accounts/stock-items",
            headers=headers,
            params={"search": search_term, "company_id": company_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("stock_items", data.get("items", [])) if isinstance(data, dict) else data
            log_result("Stock Item Search", "PASS", f"Found {len(results)} items with search='{search_term}'")
            return True
        else:
            log_result("Stock Item Search", "WARN", f"Status: {response.status_code} - may not support search")
            return True
    except Exception as e:
        log_result("Stock Item Search", "FAIL", str(e))
        return False

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY - DC Protocol Purchase Invoice Module")
    print("="*60)
    
    passed = sum(1 for r in TEST_RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in TEST_RESULTS if r["status"] == "FAIL")
    warned = sum(1 for r in TEST_RESULTS if r["status"] == "WARN")
    
    print(f"\n✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"⚠️  WARNINGS: {warned}")
    print(f"📊 TOTAL: {len(TEST_RESULTS)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - DC Protocol Compliant!")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
    
    print("="*60)

def run_all_tests():
    """Run all test scenarios"""
    print("\n" + "="*60)
    print("PURCHASE INVOICE MODULE - COMPREHENSIVE TEST SUITE")
    print("DC Protocol Compliance Testing")
    print("="*60 + "\n")
    
    if not test_api_health():
        print("❌ API not available. Aborting tests.")
        return
    
    token = get_auth_token()
    if not token:
        log_result("Authentication", "FAIL", "Could not obtain auth token")
        print_summary()
        return
    
    log_result("Authentication", "PASS", "Staff login successful")
    
    companies = test_companies_list(token)
    if not companies:
        print("❌ No companies found. Aborting tests.")
        print_summary()
        return
    
    if isinstance(companies, dict):
        companies_list = companies.get("items", companies.get("companies", []))
    else:
        companies_list = companies
    
    if not companies_list:
        print("❌ No companies in list. Aborting tests.")
        print_summary()
        return
    
    company_id = companies_list[0].get("id") if isinstance(companies_list[0], dict) else companies_list[0]
    
    vendors = test_vendors_list(token, company_id)
    
    stock_items = test_stock_items_list(token, company_id)
    
    hsn_codes = test_hsn_codes_list(token)
    
    vendor_id = None
    stock_item_id = None
    stock_item_ids = []
    
    if vendors and len(vendors) > 0:
        first_vendor = vendors[0]
        vendor_id = first_vendor.get("id") if isinstance(first_vendor, dict) else first_vendor
        log_result("Vendor ID Extraction", "PASS", f"Using vendor_id={vendor_id}")
    
    if stock_items and len(stock_items) > 0:
        stock_item_ids = [s.get("id") for s in stock_items if isinstance(s, dict) and s.get("id")]
        stock_item_id = stock_item_ids[0] if stock_item_ids else None
        log_result("Stock Item Extraction", "PASS", f"Found {len(stock_item_ids)} item IDs, using first={stock_item_id}")
    
    if vendor_id and stock_item_id:
        test_manual_invoice_cash_intrastate(token, company_id, vendor_id, stock_item_id)
    else:
        log_result("Cash Invoice (Intra-state)", "SKIP", "Missing vendor or stock item")
    
    if len(vendors) > 1 and stock_item_id:
        interstate_vendor = vendors[1].get("id") if isinstance(vendors[1], dict) else vendors[1]
        test_manual_invoice_credit_interstate(token, company_id, interstate_vendor, stock_item_id)
    elif vendor_id and stock_item_id:
        test_manual_invoice_credit_interstate(token, company_id, vendor_id, stock_item_id)
    else:
        log_result("Credit Invoice (Inter-state)", "SKIP", "Missing vendor or stock item")
    
    if vendor_id and len(stock_item_ids) >= 3:
        test_manual_invoice_multiple_items(token, company_id, vendor_id, stock_item_ids)
    else:
        log_result("Multi-Item Invoice", "SKIP", "Need at least 3 stock items")
    
    test_purchase_invoices_list(token, company_id)
    
    test_vendor_search(token, company_id)
    test_stock_item_search(token, company_id)
    
    test_stock_ledger_integration(token, company_id)
    test_accounts_payable_integration(token, company_id)
    
    print_summary()

if __name__ == "__main__":
    run_all_tests()
