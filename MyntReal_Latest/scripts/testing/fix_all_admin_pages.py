#!/usr/bin/env python3
"""
Comprehensive fix for ALL admin filter pages
Maps each admin page to the correct user/admin API endpoint
"""

# Complete mapping: admin page → API endpoint
API_MAPPING = {
    # Members Module (use admin APIs with user_id)
    'admin_members_all.html': {
        'api': '/users/${userId}/team/downline',
        'data_key': 'all_members',
        'description': 'All team members (full downline)'
    },
    'admin_members_direct.html': {
        'api': '/users/${userId}/team',
        'data_key': 'direct_referrals', 
        'description': 'Direct referrals only'
    },
    'admin_members_ved.html': {
        'api': '/users/${userId}/team/downline',
        'data_key': 'downline',
        'filter': 'is_ved_member',
        'description': 'Ved team members (filtered from downline)'
    },
    'admin_members_picture.html': {
        'api': '/users/${userId}/team/downline',
        'data_key': 'downline',
        'description': 'Binary tree structure'
    },
    
    # Earnings Module  
    'admin_earnings_summary_new.html': {
        'api': '/users/${userId}/earnings-overview',
        'data_key': 'summary',
        'description': 'Earnings overview'
    },
    'admin_earnings_direct.html': {
        'api': '/users/${userId}/income/direct-referral',
        'data_key': 'records',
        'description': 'Direct referral income'
    },
    'admin_earnings_matching.html': {
        'api': '/users/${userId}/income/matching-referral',
        'data_key': 'records',
        'description': 'Matching referral income'
    },
    'admin_earnings_ved.html': {
        'api': '/users/${userId}/income/ved-income',
        'data_key': 'records',
        'description': 'Ved income'
    },
    'admin_earnings_gurudakshina.html': {
        'api': '/users/${userId}/income/guru-dakshina',
        'data_key': 'records',
        'description': 'Guru Dakshina income'
    },
    'admin_earnings_field_allowance.html': {
        'api': '/users/field-allowances?user_id=${userId}',
        'data_key': 'records',
        'description': 'Field allowance'
    },
    'admin_earnings_withdrawals.html': {
        'api': '/users/withdrawal-requests?user_id=${userId}',
        'data_key': 'records',
        'description': 'Withdrawal requests'
    },
    
    # Awards & Bonanza (stub pages - use user data format)
    'admin_awards_all.html': {
        'api': 'USER_API',  # Special: needs proxy to user awards
        'user_api': '/users/awards',
        'description': 'User awards (needs proxy)'
    },
    'admin_awards_bonanza.html': {
        'api': 'USER_API',
        'user_api': '/users/awards/bonanza/active', 
        'description': 'Bonanza campaigns (needs proxy)'
    },
}

print("""
╔══════════════════════════════════════════════════════════════╗
║         ADMIN PAGES → USER API MAPPING                       ║
╚══════════════════════════════════════════════════════════════╝

STRATEGY:
1. Admin pages with filter call ADMIN APIs: /api/v1/users/{user_id}/...
2. These return SAME data format as user APIs
3. Display format matches user pages, colors match admin theme

MAPPED PAGES:
""")

for page, config in API_MAPPING.items():
    api = config.get('api', config.get('user_api', 'N/A'))
    print(f"  ✅ {page:<40} → {api}")

print(f"\n📊 Total: {len(API_MAPPING)} pages mapped")
print("\n" + "="*70)
print("Next: Update each page's fetch() call to use correct API endpoint")
print("="*70)
