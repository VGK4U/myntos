"""
Recalculate ALL user metrics and set baselines to 0 for production reset
Run this on PRODUCTION database to fix all imported users
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.services.leg_metrics_cache_service import LegMetricsCacheService
from sqlalchemy import text

def recalculate_all_metrics():
    db = next(get_db())
    service = LegMetricsCacheService(db)
    
    try:
        # Get all users with metrics
        result = db.execute(text("""
            SELECT user_id FROM user_leg_metrics
            ORDER BY user_id
        """)).fetchall()
        
        user_ids = [row[0] for row in result]
        total = len(user_ids)
        
        print(f"🔄 Recalculating metrics for {total} users...")
        
        # Recalculate each user's metrics
        for i, user_id in enumerate(user_ids, 1):
            try:
                service.refresh_user_metrics(user_id)
                if i % 50 == 0:
                    print(f"   ✓ Processed {i}/{total} users...")
            except Exception as e:
                print(f"   ⚠️ Error for {user_id}: {e}")
                continue
        
        db.commit()
        print(f"✅ Recalculated metrics for {total} users")
        
        # Now set all baselines to 0 for production reset
        print(f"\n🔄 Setting baselines to 0 for production reset...")
        db.execute(text("""
            UPDATE user_leg_metrics
            SET 
                snapshot_left_active = 0,
                snapshot_right_active = 0,
                snapshot_matching_count = 0,
                snapshot_left_team = 0,
                snapshot_right_team = 0,
                snapshot_direct_referrals = 0,
                snapshot_active_direct_referrals = 0,
                snapshot_ved_total = 0,
                snapshot_ved_active = 0,
                last_snapshot_at = CURRENT_TIMESTAMP
        """))
        
        db.commit()
        print(f"✅ Set baselines to 0 for all users")
        
        # Show sample results
        print(f"\n📊 Sample results:")
        sample = db.execute(text("""
            SELECT 
                user_id,
                right_active_count,
                effective_matching_count,
                snapshot_right_active,
                snapshot_matching_count
            FROM user_leg_metrics
            WHERE user_id IN ('MNR1800143', 'MNR1800142', 'MNR1800001')
            ORDER BY user_id
        """)).fetchall()
        
        for row in sample:
            display_right = row[1] - row[3]
            display_matching = row[2] - row[4]
            print(f"   {row[0]}: Right={row[1]} (display={display_right}), Matching={row[2]} (display={display_matching})")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("PRODUCTION METRICS RECALCULATION & RESET")
    print("=" * 60)
    recalculate_all_metrics()
    print("\n✅ COMPLETE! All users now have:")
    print("   - Correctly calculated metrics based on placement tree")
    print("   - Baselines set to 0 (dashboard shows actual values)")
    print("=" * 60)
