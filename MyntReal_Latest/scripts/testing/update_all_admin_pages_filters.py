#!/usr/bin/env python3
"""
Update ALL 23+ admin pages with user filter + advanced filters
"""
import os
import re

# Filter HTML components
USER_FILTER_HTML = '''
        <!-- User Filter Component -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <i class="fas fa-filter"></i> Filter by User ID
            </div>
            <div class="card-body">
                <form id="userFilterForm" class="row g-3">
                    <div class="col-md-8">
                        <label for="userIdInput" class="form-label">Enter User ID (BeV ID)</label>
                        <input type="text" class="form-control" id="userIdInput" placeholder="e.g., BEV1800143">
                    </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <button type="submit" class="btn btn-primary w-100">
                            <i class="fas fa-search"></i> Apply Filter
                        </button>
                    </div>
                </form>
                <div id="filterInfo" class="mt-3" style="display: none;">
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle"></i> 
                        Showing data for: <strong id="filteredUserId"></strong>
                        <button type="button" class="btn btn-sm btn-outline-secondary ms-2" onclick="clearUserFilter()">
                            <i class="fas fa-times"></i> Clear Filter
                        </button>
                    </div>
                </div>
            </div>
        </div>
'''

ADVANCED_FILTER_HTML = '''
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

FILTER_JS = '''
        // User filter handlers
        const urlParams = new URLSearchParams(window.location.search);
        const filteredUserId = urlParams.get('user_id');

        if (filteredUserId) {
            document.getElementById('userIdInput').value = filteredUserId;
            document.getElementById('filteredUserId').textContent = filteredUserId;
            document.getElementById('filterInfo').style.display = 'block';
        }

        document.getElementById('userFilterForm')?.addEventListener('submit', function(e) {
            e.preventDefault();
            const userId = document.getElementById('userIdInput').value.trim();
            const currentUrl = new URL(window.location.href);
            if (userId) {
                currentUrl.searchParams.set('user_id', userId);
            } else {
                currentUrl.searchParams.delete('user_id');
            }
            window.location.href = currentUrl.toString();
        });

        function clearUserFilter() {
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.delete('user_id');
            window.location.href = currentUrl.toString();
        }

        // Advanced filter handlers
        function resetAdvancedFilters() {
            document.getElementById('startDateFilter').value = '';
            document.getElementById('endDateFilter').value = '';
            document.getElementById('packageFilter').value = '';
            document.getElementById('statusFilter').value = '';
            document.getElementById('couponFilter').value = '';
            loadData();
        }
        
        ['startDateFilter', 'endDateFilter', 'packageFilter', 'statusFilter', 'couponFilter'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', loadData);
        });
        
        function getFilterParams() {
            const params = new URLSearchParams();
            const userId = filteredUserId || window.currentUserId;
            if (userId) params.append('user_id', userId);
            
            const startDate = document.getElementById('startDateFilter')?.value;
            const endDate = document.getElementById('endDateFilter')?.value;
            const pkg = document.getElementById('packageFilter')?.value;
            const status = document.getElementById('statusFilter')?.value;
            const coupon = document.getElementById('couponFilter')?.value;
            
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            if (pkg) params.append('package', pkg);
            if (status) params.append('status_filter', status);
            if (coupon) params.append('coupon_status', coupon);
            
            return params.toString();
        }
'''

# VGK Earnings pages to update
VGK_PAGES = [
    'frontend/admin_vgk_all-benefits.html',
    'frontend/admin_vgk_ev-discount-training.html',
    'frontend/admin_vgk_referral-income.html',
    'frontend/admin_vgk_insurance-earnings.html',
    'frontend/admin_vgk_franchise-earnings.html',
    'frontend/admin_vgk_fleet-orders.html'
]

print("Pages to update with filters:")
for page in VGK_PAGES:
    if os.path.exists(page):
        print(f"  ✓ {page}")
    else:
        print(f"  ✗ {page} (NOT FOUND)")

print("\nFilter components ready to add:")
print("1. User ID filter")
print("2. Advanced filters (Date, Package, Status, Coupon)")
print("3. Filter JavaScript handlers")
