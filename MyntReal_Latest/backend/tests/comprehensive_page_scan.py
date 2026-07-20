"""
COMPREHENSIVE PAGE SCANNER
Tests all role pages via frontend UI to identify broken pages
Following Frontend Testing Thumb Rule - Phase 1-5 checks
"""

import requests
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:5000"
API_BASE = "http://localhost:8000"

# Test credentials for each role
TEST_CREDENTIALS = {
    "USER": {"mnr_id": "MNR1800346", "password": "123456"},
    "ADMIN": {"mnr_id": "MNR182322707", "password": "System@admin"},
    "SUPER_ADMIN": {"mnr_id": "MNR182371007", "password": "Super@123admin"},
    "FINANCE": {"mnr_id": "MNR182371010", "password": "Fintech@123"},
    "RVZ": {"mnr_id": "MNR182364369", "password": "RVZ@ADMIN"}
}

# Pages to test for each role
PAGES_TO_TEST = {
    "PUBLIC": [
        "/login",
        "/signup",
        "/",
    ],
    "USER": [
        "/dashboard",
        "/user/dashboard",
        "/user/profile",
        "/user/edit-profile",
        "/user/team",
        "/user/team-tree",
        "/user/direct-referrals",
        "/user/matching-referrals",
        "/user/awards",
        "/user/field-allowances",
        "/user/earnings",
        "/user/withdraw",
        "/user/withdrawal-history",
        "/user/transactions",
        "/user/coupons",
        "/user/purchase-coupon",
        "/user/benefits",
        "/user/kyc",
        "/user/support",
        "/user/support/create",
    ],
    "ADMIN": [
        "/admin/dashboard",
        "/admin/users",
        "/admin/user-management",
        "/admin/create-member",
        "/admin/activate-package",
        "/admin/awards",
        "/admin/awards/pending",
        "/admin/field-allowances",
        "/admin/bonanza",
        "/admin/coupons",
        "/admin/coupon-assignment",
        "/admin/benefits",
        "/admin/withdrawals",
        "/admin/reports",
        "/admin/support",
    ],
    "SUPER_ADMIN": [
        "/super-admin/dashboard",
        "/super-admin/users",
        "/super-admin/awards",
        "/super-admin/awards/pending",
        "/super-admin/field-allowances",
        "/super-admin/bonanza",
        "/super-admin/coupons",
        "/super-admin/benefits",
        "/super-admin/withdrawals",
        "/super-admin/system-config",
        "/super-admin/reports",
    ],
    "FINANCE": [
        "/finance/dashboard",
        "/finance/awards",
        "/finance/awards/pending",
        "/finance/field-allowances",
        "/finance/withdrawals",
        "/finance/withdrawal-requests",
        "/finance/expenses",
        "/finance/reports",
    ],
    "RVZ": [
        "/rvz/dashboard",
        "/rvz/users",
        "/rvz/awards",
        "/rvz/earnings",
        "/rvz/reports",
        "/rvz/system-reset",
        "/rvz/popup-control",
        "/rvz/terms-control",
        "/rvz/testing",
    ]
}

def test_page(url: str) -> Tuple[int, str]:
    """Test a page and return status code and status"""
    try:
        response = requests.get(url, timeout=5, allow_redirects=False)
        status_code = response.status_code
        
        if status_code == 200:
            # Check if it's an error page or "under development"
            content = response.text.lower()
            if "error" in content and "500" in content:
                return (status_code, "⚠️  ERROR PAGE")
            elif "under development" in content or "coming soon" in content:
                return (status_code, "⚠️  UNDER DEV")
            elif "404" in content or "not found" in content:
                return (status_code, "⚠️  404 PAGE")
            else:
                return (status_code, "✅ OK")
        elif status_code == 302:
            return (status_code, "✅ REDIRECT")
        elif status_code == 401:
            return (status_code, "✅ AUTH REQ")
        elif status_code == 404:
            return (status_code, "❌ 404")
        elif status_code == 500:
            return (status_code, "❌ 500")
        else:
            return (status_code, f"⚠️  {status_code}")
    except Exception as e:
        return (0, f"❌ ERROR: {str(e)[:30]}")

def scan_all_pages():
    """Scan all pages and categorize issues"""
    
    print("=" * 80)
    print("🔍 COMPREHENSIVE PAGE SCANNER - Frontend UI Testing")
    print("=" * 80)
    print()
    
    all_issues = []
    total_pages = 0
    broken_pages = 0
    
    for role, pages in PAGES_TO_TEST.items():
        print(f"\n{'=' * 80}")
        print(f"📋 TESTING {role} ROLE ({len(pages)} pages)")
        print(f"{'=' * 80}")
        
        for page in pages:
            url = BASE_URL + page
            status_code, status = test_page(url)
            total_pages += 1
            
            # Determine if broken
            is_broken = "❌" in status or "⚠️" in status
            if is_broken:
                broken_pages += 1
                all_issues.append({
                    "role": role,
                    "page": page,
                    "status_code": status_code,
                    "status": status
                })
            
            # Color coding
            icon = "❌" if "❌" in status else ("⚠️" if "⚠️" in status else "✅")
            print(f"{icon} {page:45} → {status_code:3} {status}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SCAN SUMMARY")
    print("=" * 80)
    print(f"Total Pages Tested: {total_pages}")
    print(f"Broken/Issues Found: {broken_pages}")
    print(f"Working Pages: {total_pages - broken_pages}")
    print()
    
    if all_issues:
        print("\n" + "=" * 80)
        print("🚨 ISSUES FOUND - NEED FIXING")
        print("=" * 80)
        
        # Group by issue type
        errors_404 = [i for i in all_issues if "404" in i["status"]]
        errors_500 = [i for i in all_issues if "500" in i["status"]]
        under_dev = [i for i in all_issues if "UNDER DEV" in i["status"]]
        error_pages = [i for i in all_issues if "ERROR PAGE" in i["status"]]
        other = [i for i in all_issues if i not in errors_404 + errors_500 + under_dev + error_pages]
        
        if errors_404:
            print(f"\n❌ 404 NOT FOUND ({len(errors_404)} pages):")
            for issue in errors_404:
                print(f"   {issue['role']:15} → {issue['page']}")
        
        if errors_500:
            print(f"\n❌ 500 SERVER ERROR ({len(errors_500)} pages):")
            for issue in errors_500:
                print(f"   {issue['role']:15} → {issue['page']}")
        
        if under_dev:
            print(f"\n⚠️  UNDER DEVELOPMENT ({len(under_dev)} pages):")
            for issue in under_dev:
                print(f"   {issue['role']:15} → {issue['page']}")
        
        if error_pages:
            print(f"\n⚠️  ERROR PAGES ({len(error_pages)} pages):")
            for issue in error_pages:
                print(f"   {issue['role']:15} → {issue['page']}")
        
        if other:
            print(f"\n⚠️  OTHER ISSUES ({len(other)} pages):")
            for issue in other:
                print(f"   {issue['role']:15} → {issue['page']} ({issue['status']})")
    else:
        print("\n✅ ALL PAGES WORKING!")
    
    print("\n" + "=" * 80)
    return all_issues

if __name__ == "__main__":
    issues = scan_all_pages()
    
    # Save to file
    with open("backend/tests/page_scan_results.txt", "w") as f:
        f.write("COMPREHENSIVE PAGE SCAN RESULTS\n")
        f.write("=" * 80 + "\n\n")
        for issue in issues:
            f.write(f"{issue['role']:15} | {issue['page']:45} | {issue['status_code']} {issue['status']}\n")
    
    print(f"\n💾 Results saved to: backend/tests/page_scan_results.txt")
    print(f"\n✅ Scan complete! Found {len(issues)} issues to fix.")
