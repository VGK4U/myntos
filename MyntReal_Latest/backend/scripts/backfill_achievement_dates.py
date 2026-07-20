"""
DC PROTOCOL BACKFILL SCRIPT - Nov 11, 2025
Backfill achievement_date from achieved_at for existing direct awards

PROBLEM:
- Old scheduler set achieved_at but NOT achievement_date
- New approval queues filter on achievement_date (DC Protocol)
- Awards with NULL achievement_date don't appear in queue

SOLUTION:
- Copy achieved_at → achievement_date for all NULL records
- Idempotent: Only updates NULL achievement_date
- Preserves existing non-NULL achievement_date values
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill_direct_award_achievement_dates():
    """
    Backfill achievement_date from achieved_at for UserAwardProgress records
    DC PROTOCOL: achievement_date is the authoritative field
    """
    db = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("DC PROTOCOL BACKFILL: Direct Award achievement_date")
        logger.info("=" * 80)
        
        # Count records needing backfill
        count_query = text("""
            SELECT COUNT(*) as total
            FROM user_award_progress
            WHERE achievement_date IS NULL
            AND achieved_at IS NOT NULL
        """)
        
        result = db.execute(count_query).fetchone()
        total_to_update = result[0]
        
        logger.info(f"📊 Found {total_to_update} direct awards with NULL achievement_date")
        
        if total_to_update == 0:
            logger.info("✅ No records need backfilling. All direct awards have achievement_date set.")
            return 0
        
        # Show sample before update
        sample_query = text("""
            SELECT user_id, award_tier_id, achieved_at, achievement_date
            FROM user_award_progress
            WHERE achievement_date IS NULL
            AND achieved_at IS NOT NULL
            LIMIT 5
        """)
        
        samples = db.execute(sample_query).fetchall()
        logger.info("\n📋 Sample records to update:")
        for sample in samples:
            logger.info(f"  User: {sample[0]}, Tier: {sample[1]}, achieved_at: {sample[2]}, achievement_date: {sample[3]}")
        
        # Perform backfill
        update_query = text("""
            UPDATE user_award_progress
            SET achievement_date = achieved_at
            WHERE achievement_date IS NULL
            AND achieved_at IS NOT NULL
        """)
        
        result = db.execute(update_query)
        db.commit()
        
        updated_count = result.rowcount
        
        logger.info(f"\n✅ BACKFILL COMPLETE: Updated {updated_count} direct award records")
        logger.info("   achievement_date now populated from achieved_at")
        logger.info("   Awards will now appear in approval queue")
        
        # Verify no NULL achievement_date with non-NULL achieved_at remain
        verify_query = text("""
            SELECT COUNT(*) as remaining
            FROM user_award_progress
            WHERE achievement_date IS NULL
            AND achieved_at IS NOT NULL
        """)
        
        verify_result = db.execute(verify_query).fetchone()
        remaining = verify_result[0]
        
        if remaining == 0:
            logger.info(f"\n✅ VERIFICATION PASSED: 0 records remain with NULL achievement_date")
        else:
            logger.warning(f"\n⚠️  VERIFICATION WARNING: {remaining} records still have NULL achievement_date")
        
        return updated_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during backfill: {e}")
        raise
    finally:
        db.close()

def backfill_matching_award_achievement_dates():
    """
    Verify matching awards have achievement_date set
    (Matching awards should already have this field set correctly)
    """
    db = SessionLocal()
    
    try:
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION: Matching Award achievement_date")
        logger.info("=" * 80)
        
        count_query = text("""
            SELECT COUNT(*) as total
            FROM user_matching_award_progress
            WHERE achievement_date IS NULL
        """)
        
        result = db.execute(count_query).fetchone()
        total_null = result[0]
        
        if total_null == 0:
            logger.info("✅ All matching awards have achievement_date set (correct)")
        else:
            logger.warning(f"⚠️  {total_null} matching awards have NULL achievement_date")
            logger.warning("   Matching awards should be created with achievement_date by scheduler")
        
        return total_null
        
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("\n🚀 Starting DC Protocol achievement_date backfill...")
    logger.info("   This script is IDEMPOTENT - safe to run multiple times\n")
    
    try:
        # Backfill direct awards
        direct_updated = backfill_direct_award_achievement_dates()
        
        # Verify matching awards
        matching_null = backfill_matching_award_achievement_dates()
        
        logger.info("\n" + "=" * 80)
        logger.info("BACKFILL SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Direct Awards Updated: {direct_updated}")
        logger.info(f"Matching Awards with NULL: {matching_null}")
        logger.info("\n✅ DC PROTOCOL BACKFILL COMPLETE!")
        logger.info("   Awards will now appear in RVZ Approval Queue\n")
        
    except Exception as e:
        logger.error(f"\n❌ BACKFILL FAILED: {e}")
        sys.exit(1)
