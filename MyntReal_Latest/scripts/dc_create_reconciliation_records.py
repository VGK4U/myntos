#!/usr/bin/env python3
"""
DC Protocol: Create Reconciliation Records
Generate pending_income records to zero out negative balances

Purpose: For users who withdrew more than recorded earnings (due to manual VGK 
         adjustments), create reconciliation records to match withdrawals.

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

def get_users_with_negative_balances(db):
    """Get all users with negative computed withdrawable balance"""
    
    query = text("""
        WITH earned AS (
            SELECT 
                user_id,
                COALESCE(SUM(net_amount), 0.0) as total_earned
            FROM pending_income
            WHERE verification_status IN ('Finance Paid', 'Accounts Paid')
            GROUP BY user_id
        ),
        withdrawn AS (
            SELECT 
                user_id,
                COALESCE(SUM(final_payout), 0.0) as total_withdrawn
            FROM withdrawal_request
            WHERE status IN ('Bank Sent', 'Completed')
            GROUP BY user_id
        ),
        balances AS (
            SELECT 
                COALESCE(e.user_id, w.user_id) as user_id,
                COALESCE(e.total_earned, 0.0) as earned,
                COALESCE(w.total_withdrawn, 0.0) as withdrawn,
                COALESCE(e.total_earned, 0.0) - COALESCE(w.total_withdrawn, 0.0) as balance
            FROM earned e
            FULL OUTER JOIN withdrawn w ON e.user_id = w.user_id
        )
        SELECT user_id, earned, withdrawn, balance
        FROM balances
        WHERE balance < -0.01  -- Negative balance (allowing 1 paisa tolerance)
        ORDER BY balance ASC
    """)
    
    results = db.execute(query).fetchall()
    
    return [
        {
            'user_id': row[0],
            'earned': float(row[1]),
            'withdrawn': float(row[2]),
            'balance': float(row[3]),
            'shortage': abs(float(row[3]))  # Positive amount needed
        }
        for row in results
    ]

def create_reconciliation_record(db, user_id: str, amount: Decimal, dry_run: bool = True):
    """Create a reconciliation pending_income record"""
    
    if dry_run:
        print(f"  [DRY RUN] Would create: {user_id} → ₹{amount}")
        return None
    
    insert_query = text("""
        INSERT INTO pending_income (
            user_id,
            income_type,
            gross_amount,
            gurudakshina_deduction,
            admin_deduction,
            tds_deduction,
            net_amount,
            withdrawal_wallet_amount,
            upgraded_wallet_amount,
            pairs_matched,
            left_points_consumed,
            right_points_consumed,
            business_date,
            calculation_timestamp,
            verification_status,
            notes,
            created_at,
            updated_at
        ) VALUES (
            :user_id,
            'Manual Adjustment - DC Reconciliation',
            :amount,
            0.0,
            0.0,
            0.0,
            :amount,
            :amount,
            0.0,
            0,
            0,
            0,
            :business_date,
            :timestamp,
            'Finance Paid',
            :notes,
            :timestamp,
            :timestamp
        )
        RETURNING id
    """)
    
    now = get_indian_time()
    
    result = db.execute(insert_query, {
        'user_id': user_id,
        'amount': float(amount),
        'business_date': now,
        'timestamp': now,
        'notes': 'DC Protocol reconciliation record - Created to match historical manual VGK adjustments not recorded in ledger. This balances withdrawals to earnings.'
    })
    
    record_id = result.first()[0]
    return record_id

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Create reconciliation records for negative balances')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be created without making changes (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually create the records (use with caution!)')
    
    args = parser.parse_args()
    
    if args.execute:
        dry_run = False
        print("=" * 70)
        print("⚠️  LIVE MODE - WILL CREATE RECORDS IN DATABASE")
        print("=" * 70)
        response = input("Are you sure you want to create reconciliation records? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return 1
    else:
        dry_run = True
        print("=" * 70)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 70)
    
    db = next(get_db())
    
    try:
        # Get users with negative balances
        users = get_users_with_negative_balances(db)
        
        print(f"\nFound {len(users)} users with negative balances")
        print(f"Total shortage: ₹{sum(u['shortage'] for u in users):,.2f}")
        print()
        
        if not users:
            print("✓ No negative balances found - no reconciliation needed")
            return 0
        
        # Create reconciliation records
        created_count = 0
        total_amount = Decimal('0.0')
        
        for user in users:
            user_id = user['user_id']
            shortage = Decimal(str(user['shortage']))
            
            print(f"\n{user_id}:")
            print(f"  Earned:    ₹{user['earned']:,.2f}")
            print(f"  Withdrawn: ₹{user['withdrawn']:,.2f}")
            print(f"  Balance:   ₹{user['balance']:,.2f}")
            print(f"  Shortage:  ₹{shortage:,.2f}")
            
            record_id = create_reconciliation_record(db, user_id, shortage, dry_run)
            
            if record_id:
                print(f"  ✓ Created reconciliation record ID: {record_id}")
                created_count += 1
                total_amount += shortage
            elif not dry_run:
                print(f"  ✗ Failed to create record")
        
        if not dry_run:
            db.commit()
            print()
            print("=" * 70)
            print("RECONCILIATION RECORDS CREATED")
            print("=" * 70)
            print(f"Total records created: {created_count}")
            print(f"Total amount: ₹{total_amount:,.2f}")
            print()
            print("Next steps:")
            print("1. Re-run reconciliation analysis to verify 100% match")
            print("2. Proceed to Phase 1.3 (Materialized Views)")
        else:
            print()
            print("=" * 70)
            print("DRY RUN COMPLETE - No changes made")
            print("=" * 70)
            print(f"Would create {len(users)} reconciliation records")
            print(f"Total amount: ₹{sum(u['shortage'] for u in users):,.2f}")
            print()
            print("To execute, run with --execute flag")
        
        return 0
    
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        return 1
    
    finally:
        db.close()

if __name__ == '__main__':
    sys.exit(main())
