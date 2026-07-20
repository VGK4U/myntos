#!/usr/bin/env python3
"""
Complete Test User Deletion Script
Deletes test users and bonanza users with all their related data
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

# All users to delete
USERS_TO_DELETE = [
    'BEV182335987', 'BEV182356628',  # Test users
    'BEV1800897', 'BEV1800898', 'BEV1800899', 'BEV1800900', 'BEV1800901',
    'BEV1800902', 'BEV1800903', 'BEV1800904', 'BEV1800905', 'BEV1800906',
    'BEV1800907', 'BEV1800908', 'BEV1800909', 'BEV1800910', 'BEV1800911',
    'BEV1800912', 'BEV1800913', 'BEV1800914', 'BEV1800915', 'BEV1800916',
    'BEV1800917', 'BEV1800918', 'BEV1800919', 'BEV1800920', 'BEV1800921',
    'BEV1800922', 'BEV1800923', 'BEV1800924', 'BEV1800925', 'BEV1800926',
    'BEV1800927', 'BEV1800928', 'BEV1800929', 'BEV1800930', 'BEV1800931',
    'BEV1800932', 'BEV1800933', 'BEV1800934', 'BEV1800935', 'BEV1800936',
    'BEV1800937', 'BEV1800938', 'BEV1800939', 'BEV1800940', 'BEV1800941',
    'BEV1800942', 'BEV1800943'
]

def delete_users():
    """Delete all test users and their related data"""
    
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print(f"🗑️  Deleting {len(USERS_TO_DELETE)} users and all related data...")
        
        user_ids_str = "'" + "','".join(USERS_TO_DELETE) + "'"
        
        # Step 1: Delete from all related tables in correct order
        tables_to_clean = [
            ('placement_log', 'new_user_id'),
            ('placement_log', 'sponsor_user_id'),
            ('placement_log', 'target_parent_id'),
            ('placement_request', 'new_user_id'),
            ('placement_request', 'sponsor_user_id'),
            ('placement_request', 'target_parent_id'),
            ('placement', 'child_id'),
            ('placement', 'parent_id'),
            ('direct_referral_income', 'referrer_id'),
            ('direct_referral_income', 'referred_user_id'),
            ('matching_referral_income', 'user_id'),
            ('ved_income', 'ved_member_id'),
            ('ved_income', 'ved_owner_id'),
            ('ved_income', 'new_member_id'),
            ('transaction', 'user_id'),
            ('transaction', 'referred_user_id'),
            ('transaction', 'referrer_id'),
            ('pending_income', 'user_id'),
            ('withdrawal_request', 'user_id'),
            ('coupon', 'owner_id'),
            ('coupon_activation_attempt', 'user_id'),
            ('coupon_purchase_request', 'user_id'),
            ('ticket', 'user_id'),
            ('ticket_response', 'user_id'),
            ('ev_coupon_application', 'user_id'),
            ('ev_coupon_benefit_transaction', 'user_id'),
            ('bonanza_progress', 'user_id'),
            ('bonanza_transaction', 'user_id'),
            ('user_leg_metrics', 'user_id'),
        ]
        
        for table, column in tables_to_clean:
            try:
                query = text(f'DELETE FROM "{table}" WHERE {column} IN ({user_ids_str})')
                result = db.execute(query)
                db.commit()
                if result.rowcount > 0:
                    print(f"   ✅ Deleted {result.rowcount} rows from {table} ({column})")
            except Exception as e:
                # Table might not exist, skip it
                db.rollback()
                pass
        
        # Step 2: Update user table references
        print("\n📝 Clearing user table references...")
        update_queries = [
            f"UPDATE \"user\" SET referrer_id = NULL WHERE referrer_id IN ({user_ids_str})",
            f"UPDATE \"user\" SET position_id = NULL WHERE position_id IN ({user_ids_str})",
            f"UPDATE \"user\" SET ved_owner_id = NULL WHERE ved_owner_id IN ({user_ids_str})",
        ]
        
        for query_str in update_queries:
            result = db.execute(text(query_str))
            db.commit()
            if result.rowcount > 0:
                print(f"   ✅ Updated {result.rowcount} user references")
        
        # Step 3: Delete the users
        print("\n🗑️  Deleting users...")
        delete_query = text(f'DELETE FROM "user" WHERE id IN ({user_ids_str})')
        result = db.execute(delete_query)
        db.commit()
        print(f"   ✅ Deleted {result.rowcount} users")
        
        # Verify
        verify_query = text(f'SELECT COUNT(*) FROM "user" WHERE id IN ({user_ids_str})')
        remaining = db.execute(verify_query).scalar()
        
        if remaining == 0:
            print("\n✅ SUCCESS! All users deleted successfully")
        else:
            print(f"\n⚠️  WARNING: {remaining} users still remain")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 BeV 2.0 Test User Deletion")
    print("=" * 70)
    delete_users()
    print("\n" + "=" * 70)
    print("✅ Deletion Complete!")
    print("=" * 70)
