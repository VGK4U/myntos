#!/usr/bin/env python3
"""
Batch update ALL admin pages with user filter + advanced filters
"""
import os
import re

# Filter HTML components to inject
ADVANCED_FILTERS_HTML = '''
        <!-- Advanced Filters -->
        <div class="card mb-4">
            <div class="card-header bg-secondary text-white">
                <i class="fas fa-sliders-h"></i> Advanced Filters
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-md-2">
                        <label class="form-label">Start Date</label>
                        <input type="date" class="form-control" id="startDateFilter">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">End Date</label>
                        <input type="date" class="form-control" id="endDateFilter">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Package</label>
                        <select class="form-select" id="packageFilter">
                            <option value="">All</option>
                            <option value="Platinum">Platinum</option>
                            <option value="Diamond">Diamond</option>
                            <option value="Blue">Blue</option>
                            <option value="Loyal">Loyal</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Status</label>
                        <select class="form-select" id="statusFilter">
                            <option value="">All</option>
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Coupon Status</label>
                        <select class="form-select" id="couponFilter">
                            <option value="">All</option>
                            <option value="Purchased">Purchased</option>
                            <option value="Assigned">Assigned</option>
                            <option value="Activated">Activated</option>
                        </select>
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button class="btn btn-outline-secondary w-100" onclick="resetAdvancedFilters()">
                            <i class="fas fa-redo"></i> Reset
                        </button>
                    </div>
                </div>
            </div>
        </div>
'''

# Pages to update and their specifications
PAGES_TO_UPDATE = {
    # Direct Referrals (fix endpoint)
    'frontend/admin_members_direct.html': {
        'endpoint': '/api/v1/users/team/direct-referrals',
        'needs_advanced_filters': True
    },
    
    # Earnings pages
    'frontend/admin_earnings_summary_new.html': {
        'endpoint': '/api/v1/users/earnings-overview', 
        'needs_advanced_filters': True
    },
    'frontend/admin_earnings_direct.html': {
        'endpoint': '/api/v1/users/income/direct_referral',
        'needs_advanced_filters': True
    },
    'frontend/admin_earnings_matching.html': {
        'endpoint': '/api/v1/users/income/matching_referral',
        'needs_advanced_filters': True
    },
    'frontend/admin_earnings_ved.html': {
        'endpoint': '/api/v1/users/income/ved_income',
        'needs_advanced_filters': True
    },
    'frontend/admin_earnings_gurudakshina.html': {
        'endpoint': '/api/v1/users/income/guru_dakshina',
        'needs_advanced_filters': True
    },
    'frontend/admin_earnings_field_allowance.html': {
        'endpoint': '/api/v1/users/income/field_allowance',
        'needs_advanced_filters': True
    },
    'frontend/admin_earnings_withdrawals.html': {
        'endpoint': '/api/v1/users/withdrawals',
        'needs_advanced_filters': True
    },
}

print("=" * 60)
print("BATCH UPDATE ADMIN PAGES")
print("=" * 60)
print(f"\nPages to update: {len(PAGES_TO_UPDATE)}")

for page_path, config in PAGES_TO_UPDATE.items():
    if os.path.exists(page_path):
        print(f"✓ {page_path}")
        print(f"  - Endpoint: {config['endpoint']}")
        print(f"  - Advanced Filters: {config['needs_advanced_filters']}")
    else:
        print(f"✗ {page_path} (NOT FOUND)")

print("\n" + "=" * 60)
print("READY TO UPDATE")
print("=" * 60)
