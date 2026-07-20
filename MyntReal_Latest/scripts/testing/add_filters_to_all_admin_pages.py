#!/usr/bin/env python3
"""
Add complete filter set to ALL admin pages to match user pages
"""

# Filter HTML that matches user page filters
ADMIN_FILTERS_HTML = '''
        <!-- Advanced Filters (matching user pages) -->
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
                            <option value="Pending">Pending</option>
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
        // Advanced filter handlers
        function resetAdvancedFilters() {
            document.getElementById('startDateFilter').value = '';
            document.getElementById('endDateFilter').value = '';
            document.getElementById('packageFilter').value = '';
            document.getElementById('statusFilter').value = '';
            document.getElementById('couponFilter').value = '';
            loadData(); // Reload with reset filters
        }
        
        // Apply filters when changed
        ['startDateFilter', 'endDateFilter', 'packageFilter', 'statusFilter', 'couponFilter'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', loadData);
        });
        
        function getFilterParams() {
            const params = new URLSearchParams();
            const startDate = document.getElementById('startDateFilter')?.value;
            const endDate = document.getElementById('endDateFilter')?.value;
            const pkg = document.getElementById('packageFilter')?.value;
            const status = document.getElementById('statusFilter')?.value;
            const coupon = document.getElementById('couponFilter')?.value;
            
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            if (pkg) params.append('package', pkg);
            if (status) params.append('status', status);
            if (coupon) params.append('coupon_status', coupon);
            
            return params.toString();
        }
'''

print("Filter HTML and JS ready to add to all 23 admin pages")
print("\nAdmin pages need:")
print("1. User ID filter (already added)")
print("2. Advanced filters (Date, Package, Status, Coupon) - MISSING")
print("\nWill add to:")
print("- All Members, Direct Referrals, Picture View, Ved Team")
print("- All Earnings pages")
print("- All Awards pages")
print("- All VGK Earnings pages")
print("- All Coupon pages")
