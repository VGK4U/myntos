#!/usr/bin/env python3
"""
Staff Reimbursement Claims API Test
DC Protocol Compliant - Tests claim creation and approval workflow
"""

import requests
from datetime import datetime, timedelta
from decimal import Decimal

BASE_URL = "http://localhost:5000"

GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{CYAN}{text:^80}{RESET}")
    print(f"{'='*80}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}► {text}{RESET}")

def login(employee_id, password):
    """Login and return token"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/staff/auth/login",
        json={"employee_id": employee_id, "password": password}
    )
    if resp.status_code == 200:
        data = resp.json()
        if data.get('access_token'):
            return data['access_token']
    return None

def get_companies(token):
    """Get assigned companies"""
    resp = requests.get(
        f"{BASE_URL}/api/v1/staff/reimbursements/my-assigned-companies",
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code == 200:
        return resp.json().get('companies', [])
    return []

def get_categories(token):
    """Get expense categories"""
    resp = requests.get(
        f"{BASE_URL}/api/v1/staff/reimbursements/expense-categories",
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code == 200:
        return resp.json().get('categories', [])
    return []

def create_claim(token, company_id, claim_data):
    """Create a reimbursement claim with expense item"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/staff/reimbursements/claims",
        headers={"Authorization": f"Bearer {token}"},
        json=claim_data
    )
    return resp

def submit_claim(token, claim_id):
    """Submit claim for approval"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/staff/reimbursements/claims/{claim_id}/submit",
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp

def approve_claim(token, claim_id, stage="manager"):
    """Approve claim at specified stage"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/staff/reimbursements/claims/{claim_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"remarks": f"Approved by test - {stage} stage"}
    )
    return resp

def run_test():
    print_header("STAFF REIMBURSEMENT CLAIMS API TEST")
    
    employee_id = "PW-STAFF-001"
    password = "PwStaff@2024"
    
    print_info(f"Logging in as {employee_id}...")
    token = login(employee_id, password)
    if not token:
        print_error("Login failed!")
        return False
    print_success("Login successful")
    
    print_info("Fetching assigned companies...")
    companies = get_companies(token)
    if not companies:
        print_error("No companies assigned")
        return False
    print_success(f"Found {len(companies)} companies: {[c['company_name'] for c in companies[:3]]}")
    company_id = companies[0]['id']
    
    print_info("Fetching expense categories...")
    categories = get_categories(token)
    if not categories:
        print_error("No expense categories found")
        return False
    print_success(f"Found {len(categories)} main categories")
    
    main_cat = categories[0]
    sub_cat = main_cat.get('sub_categories', [{}])[0] if main_cat.get('sub_categories') else {}
    
    print_header("CREATING TEST CLAIMS")
    
    test_claims = [
        {
            "company_id": company_id,
            "claim_title": f"Travel Expenses - {datetime.now().strftime('%H%M%S')}",
            "claim_description": "Client meeting travel expenses",
            "is_travel_claim": True,
            "travel_mode": "CAR",
            "travel_from": "Office",
            "travel_to": "Client Site",
            "distance_km": 45.5,
            "claim_period_from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "claim_period_to": datetime.now().strftime("%Y-%m-%d"),
            "items": [{
                "main_category_id": main_cat.get('id'),
                "sub_category_id": sub_cat.get('id') if sub_cat else None,
                "description": "Fuel and toll expenses",
                "expense_date": datetime.now().strftime("%Y-%m-%d"),
                "amount": 2500.00,
                "vendor_name": "Shell Petrol",
                "bill_number": "SH-2024-001",
                "gst_applicable": True,
                "gst_amount": 350.00
            }]
        },
        {
            "company_id": company_id,
            "claim_title": f"Office Supplies - {datetime.now().strftime('%H%M%S')}",
            "claim_description": "Stationery purchase",
            "is_travel_claim": False,
            "claim_period_from": datetime.now().strftime("%Y-%m-%d"),
            "claim_period_to": datetime.now().strftime("%Y-%m-%d"),
            "items": [{
                "main_category_id": main_cat.get('id'),
                "sub_category_id": sub_cat.get('id') if sub_cat else None,
                "description": "Printer paper and pens",
                "expense_date": datetime.now().strftime("%Y-%m-%d"),
                "amount": 1200.00,
                "vendor_name": "Office Store",
                "bill_number": "OFF-2024-123"
            }]
        },
        {
            "company_id": company_id,
            "claim_title": f"Team Lunch - {datetime.now().strftime('%H%M%S')}",
            "claim_description": "Project celebration lunch",
            "is_travel_claim": False,
            "claim_period_from": datetime.now().strftime("%Y-%m-%d"),
            "claim_period_to": datetime.now().strftime("%Y-%m-%d"),
            "items": [{
                "main_category_id": main_cat.get('id'),
                "sub_category_id": sub_cat.get('id') if sub_cat else None,
                "description": "Team lunch for project completion",
                "expense_date": datetime.now().strftime("%Y-%m-%d"),
                "amount": 3500.00,
                "vendor_name": "Restaurant XYZ",
                "bill_number": "REST-001",
                "gst_applicable": True,
                "gst_amount": 500.00
            }]
        }
    ]
    
    created_claims = []
    
    for i, claim_data in enumerate(test_claims):
        print_info(f"Creating claim {i+1}: {claim_data['claim_title']}")
        resp = create_claim(token, company_id, claim_data)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            if data.get('success'):
                claim_obj = data.get('claim', {})
                claim_id = claim_obj.get('id')
                created_claims.append(claim_id)
                print_success(f"Claim created with ID: {claim_id}, Number: {claim_obj.get('claim_number')}")
            else:
                print_error(f"Create failed: {data.get('message', data)}")
        else:
            print_error(f"HTTP {resp.status_code}: {resp.text[:200]}")
    
    print_header("SUBMITTING CLAIMS FOR APPROVAL")
    
    submitted_claims = []
    for claim_id in created_claims:
        print_info(f"Submitting claim {claim_id}...")
        resp = submit_claim(token, claim_id)
        if resp.status_code == 200:
            print_success(f"Claim {claim_id} submitted")
            submitted_claims.append(claim_id)
        else:
            print_error(f"Submit failed: {resp.status_code} - {resp.text[:100]}")
    
    print_header("APPROVING CLAIMS")
    
    for claim_id in submitted_claims[:2]:
        print_info(f"Approving claim {claim_id}...")
        resp = approve_claim(token, claim_id)
        if resp.status_code == 200:
            print_success(f"Claim {claim_id} approved")
        else:
            print_error(f"Approve failed: {resp.status_code} - {resp.text[:100]}")
    
    print_header("TEST SUMMARY")
    print_success(f"Claims Created: {len(created_claims)}")
    print_success(f"Claims Submitted: {len(submitted_claims)}")
    print_success("API Test Completed!")
    
    return True

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)
