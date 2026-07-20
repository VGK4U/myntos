#!/usr/bin/env python3
"""
DC Protocol Phase 1.3: Trigger Test
Test that materialized views auto-refresh on data changes

Purpose: Verify triggers work correctly by inserting, updating, deleting
         test records and checking view updates.

Author: DC Protocol Implementation Team
Date: November 2, 2025
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text
from app.core.database import get_db
from app.models.base import get_indian_time

def test_earning_wallet_triggers(db):
    """Test that earning wallet view refreshes on pending_income changes"""
    
    test_user_id = 'TEST001'  # Max 12 chars
    
    print("=" * 70)
    print("TEST 1: EARNING WALLET TRIGGERS")
    print("=" * 70)
    
    try:
        # Cleanup any existing test data
        db.execute(text("""
            DELETE FROM pending_income WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.commit()
        
        # Step 1: Insert a pending income record
        print("\n1. Inserting pending income (₹1,000)...")
        db.execute(text("""
            INSERT INTO pending_income (
                user_id, income_type, net_amount, verification_status,
                gross_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
                gurudakshina_deduction, admin_deduction, tds_deduction,
                pairs_matched, left_points_consumed, right_points_consumed,
                business_date, calculation_timestamp, created_at, updated_at
            ) VALUES (
                :user_id, 'Test Income', 1000.0, 'Pending',
                1000.0, 1000.0, 0.0,
                0.0, 0.0, 0.0,
                0, 0, 0,
                :timestamp, :timestamp, :timestamp, :timestamp
            )
        """), {"user_id": test_user_id, "timestamp": get_indian_time()})
        db.commit()
        
        # Check view updated
        result = db.execute(text("""
            SELECT earning_wallet FROM user_earning_wallet_balance
            WHERE user_id = :user_id
        """), {"user_id": test_user_id}).first()
        
        if result and result[0] == 1000.0:
            print("   ✅ View updated! Earning wallet = ₹1,000")
        else:
            print(f"   ❌ View NOT updated. Expected ₹1,000, got {result[0] if result else 'NULL'}")
            return False
        
        # Step 2: Update to paid status (should remove from earning view)
        print("\n2. Updating status to 'Finance Paid'...")
        db.execute(text("""
            UPDATE pending_income
            SET verification_status = 'Finance Paid'
            WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.commit()
        
        # Check view updated (should be gone from earning view)
        result = db.execute(text("""
            SELECT earning_wallet FROM user_earning_wallet_balance
            WHERE user_id = :user_id
        """), {"user_id": test_user_id}).first()
        
        if not result:
            print("   ✅ View updated! User removed from earning view (status is paid)")
        else:
            print(f"   ❌ View NOT updated. User still in earning view with ₹{result[0]}")
            return False
        
        # Step 3: Delete the record
        print("\n3. Deleting test record...")
        db.execute(text("""
            DELETE FROM pending_income WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.commit()
        
        print("   ✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        db.rollback()
        return False

def test_withdrawable_wallet_triggers(db):
    """Test that withdrawable wallet view refreshes on pending_income and withdrawal changes"""
    
    test_user_id = 'TEST002'  # Max 12 chars
    
    print("\n" + "=" * 70)
    print("TEST 2: WITHDRAWABLE WALLET TRIGGERS")
    print("=" * 70)
    
    try:
        # Cleanup any existing test data
        db.execute(text("""
            DELETE FROM pending_income WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.execute(text("""
            DELETE FROM withdrawal_request WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.commit()
        
        # Step 1: Insert paid income
        print("\n1. Inserting paid income (₹2,000)...")
        db.execute(text("""
            INSERT INTO pending_income (
                user_id, income_type, net_amount, verification_status,
                gross_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
                gurudakshina_deduction, admin_deduction, tds_deduction,
                pairs_matched, left_points_consumed, right_points_consumed,
                business_date, calculation_timestamp, created_at, updated_at
            ) VALUES (
                :user_id, 'Test Income', 2000.0, 'Finance Paid',
                2000.0, 2000.0, 0.0,
                0.0, 0.0, 0.0,
                0, 0, 0,
                :timestamp, :timestamp, :timestamp, :timestamp
            )
        """), {"user_id": test_user_id, "timestamp": get_indian_time()})
        db.commit()
        
        # Check view updated
        result = db.execute(text("""
            SELECT withdrawable_wallet, total_earned, total_withdrawn
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """), {"user_id": test_user_id}).first()
        
        if result and result[0] == 2000.0 and result[1] == 2000.0 and result[2] == 0.0:
            print(f"   ✅ View updated! Withdrawable = ₹2,000 (earned ₹2,000, withdrawn ₹0)")
        else:
            print(f"   ❌ View NOT updated. Expected ₹2,000, got {result}")
            return False
        
        # Step 2: Insert a withdrawal
        print("\n2. Inserting withdrawal (₹500)...")
        db.execute(text("""
            INSERT INTO withdrawal_request (
                user_id, amount_requested, final_payout, status,
                request_date, processing_fee, bank_charges
            ) VALUES (
                :user_id, 500.0, 500.0, 'Completed',
                :timestamp, 0.0, 0.0
            )
        """), {"user_id": test_user_id, "timestamp": get_indian_time()})
        db.commit()
        
        # Check view updated
        result = db.execute(text("""
            SELECT withdrawable_wallet, total_earned, total_withdrawn
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """), {"user_id": test_user_id}).first()
        
        if result and result[0] == 1500.0 and result[1] == 2000.0 and result[2] == 500.0:
            print(f"   ✅ View updated! Withdrawable = ₹1,500 (earned ₹2,000, withdrawn ₹500)")
        else:
            print(f"   ❌ View NOT updated. Expected ₹1,500, got {result}")
            return False
        
        # Step 3: Update withdrawal status
        print("\n3. Updating withdrawal status to 'Pending' (incomplete)...")
        db.execute(text("""
            UPDATE withdrawal_request
            SET status = 'Pending'
            WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.commit()
        
        # Check view updated (withdrawal should not count anymore)
        result = db.execute(text("""
            SELECT withdrawable_wallet, total_earned, total_withdrawn
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """), {"user_id": test_user_id}).first()
        
        if result and result[0] == 2000.0 and result[1] == 2000.0 and result[2] == 0.0:
            print(f"   ✅ View updated! Withdrawable = ₹2,000 (withdrawal status changed to pending)")
        else:
            print(f"   ❌ View NOT updated. Expected ₹2,000, got {result}")
            return False
        
        # Cleanup
        print("\n4. Cleaning up test data...")
        db.execute(text("""
            DELETE FROM pending_income WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.execute(text("""
            DELETE FROM withdrawal_request WHERE user_id = :user_id
        """), {"user_id": test_user_id})
        db.commit()
        
        print("   ✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        db.rollback()
        return False

def main():
    print("=" * 70)
    print("DC PROTOCOL PHASE 1.3: MATERIALIZED VIEW TRIGGER TESTS")
    print("=" * 70)
    print()
    
    db = next(get_db())
    
    try:
        # Test earning wallet triggers
        test1_pass = test_earning_wallet_triggers(db)
        
        # Test withdrawable wallet triggers
        test2_pass = test_withdrawable_wallet_triggers(db)
        
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Test 1 (Earning Wallet Triggers): {'✅ PASS' if test1_pass else '❌ FAIL'}")
        print(f"Test 2 (Withdrawable Wallet Triggers): {'✅ PASS' if test2_pass else '❌ FAIL'}")
        print()
        
        if test1_pass and test2_pass:
            print("🎉 ALL TRIGGERS WORKING CORRECTLY!")
            print("✅ Materialized views auto-refresh on data changes")
            return 0
        else:
            print("❌ SOME TRIGGERS FAILED - Review logs above")
            return 1
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        return 1
    
    finally:
        db.close()

if __name__ == '__main__':
    sys.exit(main())
