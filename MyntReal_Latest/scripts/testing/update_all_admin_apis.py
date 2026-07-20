#!/usr/bin/env python3
"""
Update ALL admin pages to call correct APIs and match user data format
"""
import re
import os

# API endpoint updates for each page
API_UPDATES = {
    # Already fixed
    'frontend/admin_members_all.html': ('users/${userId}/team', 'users/${userId}/team/downline'),
    
    # Need to check and update these
    'frontend/admin_members_picture.html': None,  # Check current API
    'frontend/admin_earnings_summary_new.html': None,
    'frontend/admin_earnings_direct.html': None,
    'frontend/admin_earnings_matching.html': None,
    'frontend/admin_earnings_ved.html': None,
    'frontend/admin_earnings_gurudakshina.html': None,
    'frontend/admin_earnings_field_allowance.html': None,
    'frontend/admin_earnings_withdrawals.html': None,
}

def find_api_call(filepath):
    """Find the current API call in a file"""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find fetch() calls
    fetch_pattern = r'fetch\(`\${window\.BACKEND_URL}/(.*?)`'
    matches = re.findall(fetch_pattern, content)
    
    return matches[0] if matches else None

print("Scanning all admin pages for API calls...\n")

for filepath in API_UPDATES.keys():
    current_api = find_api_call(filepath)
    if current_api:
        print(f"✅ {filepath}")
        print(f"   Current API: {current_api}")
        print()
    else:
        print(f"❌ {filepath} - No API call found")
        print()
