#!/usr/bin/env python3
"""
DC Protocol: Sync Stored Wallets to Computed Values

Purpose: Update stored earning_wallet and withdrawable_wallet to match
         computed values from RFC v4.1 formulas. This achieves 100%
         reconciliation before DC Protocol cutover.

Author: DC Protocol Implementation Team
Date: November 2, 2025
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text
from app.core.database import get_db

def sync_wallets(db, dry_run: bool = True):
    """Sync all stored wallets to match computed values"""
    
    update_query = text("""
        WITH computed_earning AS (
            SELECT 
                user_id,
                COALESCE(SUM(net_amount), 0.0) as earning
            FROM pending_income
            WHERE verification_status IN ('Pending', 'Admin Verified', 
                                         'Super Admin Verified', 'Super Admin Approved')
            GROUP BY user_id
        ),
        computed_withdrawable AS (
            SELECT 
                COALESCE(e.user_id, w.user_id) as user_id,
                COALESCE(e.earned, 0.0) - COALESCE(w.withdrawn, 0.0) as withdrawable
            FROM (
                SELECT user_id, SUM(net_amount) as earned
                FROM pending_income
                WHERE verification_status IN ('Finance Paid', 'Accounts Paid')
                GROUP BY user_id
            ) e
            FULL OUTER JOIN (
                SELECT user_id, SUM(final_payout) as withdrawn
                FROM withdrawal_request
                WHERE status IN ('Bank Sent', 'Completed')
                GROUP BY user_id
            ) w ON e.user_id = w.user_id
        )
        UPDATE "user" u
        SET 
            earning_wallet = COALESCE(ce.earning, 0.0),
            withdrawable_wallet = GREATEST(COALESCE(cw.withdrawable, 0.0), 0.0)
        FROM computed_earning ce
        FULL OUTER JOIN computed_withdrawable cw ON ce.user_id = cw.user_id
        WHERE u.id = COALESCE(ce.user_id, cw.user_id)
        AND (
            ABS(u.earning_wallet - COALESCE(ce.earning, 0.0)) > 0.01
            OR ABS(u.withdrawable_wallet - GREATEST(COALESCE(cw.withdrawable, 0.0), 0.0)) > 0.01
        )
    """)
    
    if dry_run:
        # Get count of users that would be updated
        count_query = text("""
            WITH computed_earning AS (
                SELECT 
                    user_id,
                    COALESCE(SUM(net_amount), 0.0) as earning
                FROM pending_income
                WHERE verification_status IN ('Pending', 'Admin Verified', 
                                             'Super Admin Verified', 'Super Admin Approved')
                GROUP BY user_id
            ),
            computed_withdrawable AS (
                SELECT 
                    COALESCE(e.user_id, w.user_id) as user_id,
                    COALESCE(e.earned, 0.0) - COALESCE(w.withdrawn, 0.0) as withdrawable
                FROM (
                    SELECT user_id, SUM(net_amount) as earned
                    FROM pending_income
                    WHERE verification_status IN ('Finance Paid', 'Accounts Paid')
                    GROUP BY user_id
                ) e
                FULL OUTER JOIN (
                    SELECT user_id, SUM(final_payout) as withdrawn
                    FROM withdrawal_request
                    WHERE status IN ('Bank Sent', 'Completed')
                    GROUP BY user_id
                ) w ON e.user_id = w.user_id
            )
            SELECT COUNT(*)
            FROM "user" u
            LEFT JOIN computed_earning ce ON u.id = ce.user_id
            LEFT JOIN computed_withdrawable cw ON u.id = cw.user_id
            WHERE (
                ABS(u.earning_wallet - COALESCE(ce.earning, 0.0)) > 0.01
                OR ABS(u.withdrawable_wallet - GREATEST(COALESCE(cw.withdrawable, 0.0), 0.0)) > 0.01
            )
        """)
        
        count = db.execute(count_query).scalar()
        return count
    else:
        result = db.execute(update_query)
        return result.rowcount

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync stored wallets to computed values')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be updated without making changes (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually update the wallets (use with caution!)')
    
    args = parser.parse_args()
    
    if args.execute:
        dry_run = False
        print("=" * 70)
        print("⚠️  LIVE MODE - WILL UPDATE WALLET BALANCES")
        print("=" * 70)
        response = input("Are you sure you want to sync all wallet balances? (yes/no): ")
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
        count = sync_wallets(db, dry_run)
        
        if dry_run:
            print(f"\n✓ Would update {count} users' wallet balances")
            print("\nTo execute, run with --execute flag")
        else:
            db.commit()
            print(f"\n✓ Successfully updated {count} users' wallet balances")
            print("\nNext step: Re-run reconciliation to verify 100% match")
        
        return 0
    
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        return 1
    
    finally:
        db.close()

if __name__ == '__main__':
    sys.exit(main())
