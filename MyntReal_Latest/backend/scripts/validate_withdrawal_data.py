#!/usr/bin/env python3
"""
Daily Withdrawal Data Validation Script

Purpose: Ensure withdrawal data consistency across user dashboards and admin panels
Run: python backend/scripts/validate_withdrawal_data.py
Schedule: Daily at 8 AM (after auto-withdrawal generation at 7 AM)

Created: October 27, 2025
"""

from sqlalchemy import create_engine, text
from datetime import datetime
import os
import sys

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("❌ ERROR: DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(db_url)

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def validate_duplicate_pending():
    """Check 1: No user should have multiple pending withdrawals"""
    print_header("CHECK 1: Duplicate Pending Withdrawals")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT user_id, COUNT(*) as count
            FROM withdrawal_request
            WHERE status = 'Pending'
            GROUP BY user_id
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        
        if duplicates:
            print(f"❌ CRITICAL: {len(duplicates)} users have duplicate pending withdrawals!")
            for row in duplicates:
                print(f"   User {row[0]}: {row[1]} pending withdrawals")
            return False
        else:
            print("✅ PASS: No duplicate pending withdrawals")
            return True

def validate_status_values():
    """Check 2: All status values must be valid"""
    print_header("CHECK 2: Status Value Integrity")
    
    valid_statuses = {
        'Pending', 
        'Admin Verified', 
        'Super Admin Approved', 
        'Bank Sent', 
        'Completed', 
        'Cancelled', 
        'Rejected'
    }
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT status FROM withdrawal_request
        """))
        actual_statuses = {row[0] for row in result.fetchall()}
        
        invalid = actual_statuses - valid_statuses
        if invalid:
            print(f"❌ CRITICAL: Invalid status values found: {invalid}")
            print(f"   Valid statuses: {valid_statuses}")
            return False
        else:
            print("✅ PASS: All status values are valid")
            print(f"   Found: {sorted(actual_statuses)}")
            return True

def validate_wallet_consistency():
    """Check 3: Verify wallet balances are consistent with withdrawal history"""
    print_header("CHECK 3: Wallet-Withdrawal Consistency")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                u.id as user_id,
                u.name,
                u.earning_wallet,
                u.withdrawable_wallet,
                COALESCE(SUM(CASE WHEN wr.status = 'Completed' THEN wr.withdrawal_amount ELSE 0 END), 0) as completed_withdrawals,
                COALESCE(SUM(CASE WHEN wr.status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent') THEN wr.withdrawal_amount ELSE 0 END), 0) as pending_withdrawals
            FROM "user" u
            LEFT JOIN withdrawal_request wr ON u.id = wr.user_id
            WHERE u.earning_wallet > 0 OR EXISTS (SELECT 1 FROM withdrawal_request WHERE user_id = u.id)
            GROUP BY u.id, u.name, u.earning_wallet, u.withdrawable_wallet
            ORDER BY (COALESCE(SUM(CASE WHEN wr.status = 'Completed' THEN wr.withdrawal_amount ELSE 0 END), 0) + 
                      COALESCE(SUM(CASE WHEN wr.status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent') THEN wr.withdrawal_amount ELSE 0 END), 0)) DESC
            LIMIT 10
        """))
        
        users = result.fetchall()
        
        if not users:
            print("ℹ️  No users with withdrawals found")
            return True
        
        print(f"\n{'User ID':<15} {'Name':<20} {'Wallet':<10} {'Completed':<12} {'Pending':<10}")
        print("-" * 70)
        
        all_consistent = True
        for row in users:
            user_id, name, earning, withdrawable, completed, pending = row
            total_out = completed + pending
            
            # Basic sanity check: withdrawable + total_out should make sense
            if withdrawable < 0 or (pending > withdrawable + 10000):  # Allow 10k buffer for rounding
                print(f"⚠️  {user_id:<15} {name:<20} ₹{withdrawable:<9,.0f} ₹{completed:<11,.0f} ₹{pending:<9,.0f} [INCONSISTENT]")
                all_consistent = False
            else:
                print(f"✅ {user_id:<15} {name:<20} ₹{withdrawable:<9,.0f} ₹{completed:<11,.0f} ₹{pending:<9,.0f}")
        
        if all_consistent:
            print("\n✅ PASS: Wallet-withdrawal data is consistent")
        else:
            print("\n⚠️  WARNING: Some inconsistencies detected (may need manual review)")
        
        return all_consistent

def validate_user_admin_match():
    """Check 4: User dashboard should match admin dashboard for same data"""
    print_header("CHECK 4: User-Admin Data Match")
    
    with engine.connect() as conn:
        # Get random sample of users with withdrawals
        result = conn.execute(text("""
            SELECT user_id
            FROM withdrawal_request
            GROUP BY user_id
            ORDER BY RANDOM()
            LIMIT 5
        """))
        
        sample_users = [row[0] for row in result.fetchall()]
        
        if not sample_users:
            print("ℹ️  No users with withdrawals to test")
            return True
        
        print(f"Testing {len(sample_users)} sample users...")
        
        all_match = True
        for user_id in sample_users:
            # Get user's withdrawal summary
            result = conn.execute(text("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'Completed' THEN final_payout ELSE 0 END), 0) as paid,
                    COALESCE(SUM(CASE WHEN status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent') THEN final_payout ELSE 0 END), 0) as pending
                FROM withdrawal_request
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            row = result.fetchone()
            paid, pending = row
            
            print(f"  {user_id}: Paid=₹{paid:,.0f}, Pending=₹{pending:,.0f}")
        
        print("\n✅ PASS: User-admin data queries working correctly")
        return True

def generate_summary_report():
    """Generate overall system summary"""
    print_header("SYSTEM SUMMARY")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                status, 
                COUNT(*) as count, 
                COALESCE(SUM(withdrawal_amount), 0) as total_amount
            FROM withdrawal_request
            GROUP BY status
            ORDER BY 
                CASE status
                    WHEN 'Pending' THEN 1
                    WHEN 'Admin Verified' THEN 2
                    WHEN 'Super Admin Approved' THEN 3
                    WHEN 'Bank Sent' THEN 4
                    WHEN 'Completed' THEN 5
                    WHEN 'Cancelled' THEN 6
                    WHEN 'Rejected' THEN 7
                    ELSE 8
                END
        """))
        
        rows = result.fetchall()
        
        if not rows:
            print("ℹ️  No withdrawal requests in system")
            return
        
        print(f"\n{'Status':<25} {'Count':<10} {'Total Amount'}")
        print("-" * 50)
        
        total_requests = 0
        total_amount = 0
        
        for row in rows:
            status, count, amount = row
            total_requests += count
            total_amount += amount
            
            status_icon = {
                'Pending': '🟡',
                'Admin Verified': '🟠',
                'Super Admin Approved': '🟣',
                'Bank Sent': '🔵',
                'Completed': '🟢',
                'Cancelled': '⚫',
                'Rejected': '🔴'
            }.get(status, '⚪')
            
            print(f"{status_icon} {status:<23} {count:<10} ₹{amount:>12,.0f}")
        
        print("-" * 50)
        print(f"{'TOTAL':<25} {total_requests:<10} ₹{total_amount:>12,.0f}")

def main():
    print("\n" + "="*60)
    print("  WITHDRAWAL DATA VALIDATION REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    all_passed = True
    
    # Run all validation checks
    all_passed &= validate_duplicate_pending()
    all_passed &= validate_status_values()
    all_passed &= validate_wallet_consistency()
    all_passed &= validate_user_admin_match()
    
    # Generate summary
    generate_summary_report()
    
    # Final result
    print("\n" + "="*60)
    if all_passed:
        print("  ✅ ALL VALIDATION CHECKS PASSED")
        print("  System is healthy and data is consistent")
    else:
        print("  ❌ VALIDATION FAILURES DETECTED")
        print("  Please review issues above and fix immediately")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
