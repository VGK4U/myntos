#!/usr/bin/env python3
"""
Fix filter component in ALL admin pages
Replaces fetch() with embedded HTML
"""

import re
import os

# Filter HTML to embed
FILTER_HTML = '''        <!-- User Filter Component -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <i class="fas fa-filter"></i> Filter by User ID
            </div>
            <div class="card-body">
                <form id="userFilterForm" class="row g-3">
                    <div class="col-md-8">
                        <label for="userIdInput" class="form-label">Enter User ID (BeV ID)</label>
                        <input type="text" class="form-control" id="userIdInput" 
                               placeholder="e.g., BEV182364369 or BEV1800143" 
                               pattern="BEV[0-9]{7,9}" 
                               title="Enter a valid BeV ID (10 or 12 digits: BEV1800143 or BEV182364369)">
                        <div class="form-text">Leave empty to view your own data</div>
                    </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <button type="submit" id="applyFilterBtn" class="btn btn-primary w-100">
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
        </div>'''

# Filter JavaScript to embed
FILTER_JS = '''        // Initialize filter if user_id is in URL
        if (filteredUserId) {
            const userInput = document.getElementById('userIdInput');
            const filterInfo = document.getElementById('filterInfo');
            const filteredUserIdSpan = document.getElementById('filteredUserId');
            
            if (userInput) userInput.value = filteredUserId;
            if (filteredUserIdSpan) filteredUserIdSpan.textContent = filteredUserId;
            if (filterInfo) filterInfo.style.display = 'block';
        }

        // Handle filter form submission
        document.getElementById('userFilterForm')?.addEventListener('submit', function(e) {
            e.preventDefault();
            const userId = document.getElementById('userIdInput').value.trim();
            
            if (userId) {
                // Validate format (10 or 12 digits: BEV + 7-9 digits)
                const bevIdPattern = /^BEV[0-9]{7,9}$/;
                if (!bevIdPattern.test(userId)) {
                    alert('Please enter a valid BeV ID (10 or 12 digits: BEV1800143 or BEV182364369)');
                    return;
                }
                
                // Update URL with user_id parameter
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.set('user_id', userId);
                window.location.href = currentUrl.toString();
            } else {
                // Remove user_id parameter if empty
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.delete('user_id');
                window.location.href = currentUrl.toString();
            }
        });

        // Clear filter function
        function clearUserFilter() {
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.delete('user_id');
            window.location.href = currentUrl.toString();
        }'''

# Files to fix
FILES = [
    'frontend/admin_earnings_field_allowance.html',
    'frontend/admin_earnings_gurudakshina.html',
    'frontend/admin_earnings_ved.html',
    'frontend/admin_earnings_matching.html',
    'frontend/admin_earnings_direct.html',
    'frontend/admin_members_ved.html',
    'frontend/admin_members_picture.html',
    'frontend/admin_vgk_insurance-earnings.html',
    'frontend/admin_vgk_referral-income.html',
    'frontend/admin_vgk_ev-discount-training.html',
    'frontend/admin_vgk_all-benefits.html',
    'frontend/admin_awards_bonanza.html',
    'frontend/admin_awards_all.html',
    'frontend/admin_earnings_withdrawals.html',
    'frontend/admin_coupons_activate.html',
    'frontend/admin_coupons_buy.html',
    'frontend/admin_vgk_fleet-orders.html',
    'frontend/admin_vgk_franchise-earnings.html',
    'frontend/admin_coupons_progress.html',
    'frontend/admin_coupons_status.html',
    'frontend/admin_coupons_transfer.html',
    'frontend/admin_earnings_summary_new.html'
]

def fix_file(filepath):
    """Fix a single file"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace HTML placeholder
    content = re.sub(
        r'<!-- User Filter Component -->\s*<div id="userFilterContainer"></div>',
        FILTER_HTML,
        content,
        flags=re.MULTILINE
    )
    
    # Replace fetch() JS with embedded JS
    fetch_pattern = r'''// Load user filter component\s*fetch\('/components/user_filter\.html'\)\s*\.then\(response => response\.text\(\)\)\s*\.then\(html => \{.*?\}\);'''
    
    content = re.sub(
        fetch_pattern,
        FILTER_JS,
        content,
        flags=re.DOTALL
    )
    
    # Also handle setTimeout pattern for filter initialization
    setTimeout_pattern = r'''fetch\('/components/user_filter\.html'\)[\s\S]*?setTimeout\(\(\) => \{[\s\S]*?\}, \d+\);[\s\S]*?\}\);'''
    
    content = re.sub(
        setTimeout_pattern,
        FILTER_JS,
        content,
        flags=re.DOTALL
    )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed: {filepath}")
    return True

def main():
    print("🔧 Fixing filter component in all admin pages...")
    print(f"📄 Total files to fix: {len(FILES)}\n")
    
    success = 0
    failed = 0
    
    for filepath in FILES:
        if fix_file(filepath):
            success += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully fixed: {success} files")
    if failed > 0:
        print(f"❌ Failed: {failed} files")
    print(f"{'='*60}")
    print("\n🎉 All admin filters should now work correctly!")

if __name__ == "__main__":
    main()
