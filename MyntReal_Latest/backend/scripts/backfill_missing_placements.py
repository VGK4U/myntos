"""
Backfill Script: Place activated users missing from binary tree
Fixes critical bug where admin bulk activation bypassed auto_place_user
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.placement import Placement, PlacementLog
from app.services.reference_service import ReferenceService
from app.models.base import get_indian_time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Connect to database
    engine = create_engine(os.getenv('DATABASE_URL'))
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        logger.info("=" * 80)
        logger.info("BACKFILL SCRIPT: Missing Binary Tree Placements")
        logger.info("=" * 80)
        
        # Find all activated users NOT in binary tree
        query = text("""
            SELECT u.id, u.name, u.activation_date, u.referrer_id, u.package_points
            FROM "user" u
            LEFT JOIN placement p ON u.id = p.child_id
            WHERE u.activation_date IS NOT NULL
            AND u.package_points > 0
            AND p.child_id IS NULL
            ORDER BY u.activation_date
        """)
        
        missing_users = db.execute(query).fetchall()
        
        if not missing_users:
            logger.info("✅ No missing placements found - all users properly placed!")
            return
        
        logger.info(f"\n🔍 Found {len(missing_users)} users missing binary tree placement:")
        for user in missing_users:
            logger.info(f"   - {user[0]} ({user[1]}) | Activated: {user[2]} | Referrer: {user[3]}")
        
        # Initialize ReferenceService
        ref_service = ReferenceService(db)
        
        # Process each user
        placements_created = 0
        for user_data in missing_users:
            user_id = user_data[0]
            user_name = user_data[1]
            referrer_id = user_data[3]
            
            try:
                logger.info(f"\n📍 Processing {user_id} ({user_name})...")
                
                # Check if already has placement (race condition check)
                existing = db.query(Placement).filter(Placement.child_id == user_id).first()
                if existing:
                    logger.warning(f"   ⚠️ Placement already exists - skipping")
                    continue
                
                # Use auto_place_user with their referrer as sponsor
                if not referrer_id:
                    logger.error(f"   ❌ No referrer_id - cannot determine placement sponsor")
                    continue
                
                # Auto-place under their referrer (sponsor)
                result = ref_service.auto_place_user(user_id, referrer_id)
                
                logger.info(f"   ✅ Placed: Parent={result['parent_id']}, Side={result['side']}")
                placements_created += 1
                
                # Update User.position field for Ved Income eligibility
                user_obj = db.query(User).filter(User.id == user_id).first()
                if user_obj:
                    user_obj.position = result['side'].upper()  # 'LEFT' or 'RIGHT'
                
                db.commit()
                
            except Exception as e:
                logger.error(f"   ❌ Error placing {user_id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"\n" + "=" * 80)
        logger.info(f"✅ BACKFILL COMPLETE: {placements_created}/{len(missing_users)} users placed")
        logger.info("=" * 80)
        
        # Refresh leg metrics cache for all affected users
        if placements_created > 0:
            logger.info("\n🔄 Refreshing leg metrics cache...")
            try:
                from app.services.leg_metrics_cache_service import LegMetricsCacheService
                cache_service = LegMetricsCacheService(db)
                
                for user_data in missing_users:
                    user_id = user_data[0]
                    cache_service.refresh_user_metrics(user_id, source='backfill_script')
                
                logger.info("✅ Cache refresh complete")
            except Exception as e:
                logger.error(f"⚠️ Cache refresh failed: {e}")
        
    except Exception as e:
        logger.error(f"❌ Backfill script failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
