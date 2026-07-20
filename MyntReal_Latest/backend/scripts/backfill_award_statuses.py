"""
DC Protocol: Award Status Backfill Script
Ensures all awards have valid DC Protocol statuses and proper starting state

This script:
1. Normalizes any legacy status values to DC Protocol values
2. Ensures newly created awards without explicit status get 'Pending Approval'
3. Is idempotent and safe to run multiple times
4. Creates audit log entries for all changes

Author: MNR Development Team
Date: Nov 11, 2025
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

from app.core.config import settings
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, AwardAuditLog
from app.models.bonanza import DynamicBonanzaHistory
from app.constants.award_statuses import AwardStatus, normalize_status, is_valid_dc_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def backfill_direct_awards(db):
    """Backfill direct awards with normalized statuses"""
    logger.info("=" * 60)
    logger.info("BACKFILLING DIRECT AWARDS")
    logger.info("=" * 60)
    
    awards = db.query(UserAwardProgress).all()
    updated_count = 0
    
    for award in awards:
        original_status = award.processed_status
        normalized_status = normalize_status(original_status) if original_status else AwardStatus.PENDING_APPROVAL
        
        if original_status != normalized_status or not is_valid_dc_status(original_status or ""):
            logger.info(f"Direct Award #{award.id}: '{original_status}' → '{normalized_status}'")
            
            award.processed_status = normalized_status
            
            # Create audit log
            audit_log = AwardAuditLog(
                entity_type='direct_award',
                entity_id=award.id,
                action='status_normalized',
                old_status=original_status,
                new_status=normalized_status,
                actor_role='System',
                actor_id='SYSTEM',
                notes=f'DC Protocol backfill: Normalized legacy status',
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            updated_count += 1
    
    db.commit()
    logger.info(f"✅ Updated {updated_count} direct awards")
    return updated_count


def backfill_matching_awards(db):
    """Backfill matching awards with normalized statuses"""
    logger.info("=" * 60)
    logger.info("BACKFILLING MATCHING AWARDS")
    logger.info("=" * 60)
    
    awards = db.query(UserMatchingAwardProgress).all()
    updated_count = 0
    
    for award in awards:
        original_status = award.processed_status
        normalized_status = normalize_status(original_status) if original_status else AwardStatus.PENDING_APPROVAL
        
        if original_status != normalized_status or not is_valid_dc_status(original_status or ""):
            logger.info(f"Matching Award #{award.id}: '{original_status}' → '{normalized_status}'")
            
            award.processed_status = normalized_status
            
            # Create audit log
            audit_log = AwardAuditLog(
                entity_type='matching_award',
                entity_id=award.id,
                action='status_normalized',
                old_status=original_status,
                new_status=normalized_status,
                actor_role='System',
                actor_id='SYSTEM',
                notes=f'DC Protocol backfill: Normalized legacy status',
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            updated_count += 1
    
    db.commit()
    logger.info(f"✅ Updated {updated_count} matching awards")
    return updated_count


def backfill_bonanza_awards(db):
    """Backfill bonanza awards with normalized statuses"""
    logger.info("=" * 60)
    logger.info("BACKFILLING BONANZA AWARDS")
    logger.info("=" * 60)
    
    awards = db.query(DynamicBonanzaHistory).all()
    updated_count = 0
    
    for award in awards:
        original_status = award.processed_status
        normalized_status = normalize_status(original_status) if original_status else AwardStatus.PENDING_APPROVAL
        
        if original_status != normalized_status or not is_valid_dc_status(original_status or ""):
            logger.info(f"Bonanza Award #{award.id}: '{original_status}' → '{normalized_status}'")
            
            award.processed_status = normalized_status
            
            # Create audit log
            audit_log = AwardAuditLog(
                entity_type='bonanza',
                entity_id=award.id,
                action='status_normalized',
                old_status=original_status,
                new_status=normalized_status,
                actor_role='System',
                actor_id='SYSTEM',
                notes=f'DC Protocol backfill: Normalized legacy status',
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            updated_count += 1
    
    db.commit()
    logger.info(f"✅ Updated {updated_count} bonanza awards")
    return updated_count


def verify_backfill(db):
    """Verify all awards have valid DC Protocol statuses"""
    logger.info("=" * 60)
    logger.info("VERIFICATION")
    logger.info("=" * 60)
    
    # Check direct awards
    direct_invalid = db.query(UserAwardProgress).filter(
        ~UserAwardProgress.processed_status.in_([s.value for s in AwardStatus])
    ).count()
    
    # Check matching awards
    matching_invalid = db.query(UserMatchingAwardProgress).filter(
        ~UserMatchingAwardProgress.processed_status.in_([s.value for s in AwardStatus])
    ).count()
    
    # Check bonanza
    bonanza_invalid = db.query(DynamicBonanzaHistory).filter(
        ~DynamicBonanzaHistory.processed_status.in_([s.value for s in AwardStatus])
    ).count()
    
    total_invalid = direct_invalid + matching_invalid + bonanza_invalid
    
    if total_invalid == 0:
        logger.info("✅ All awards have valid DC Protocol statuses!")
    else:
        logger.error(f"❌ Found {total_invalid} awards with invalid statuses")
        logger.error(f"   Direct: {direct_invalid}, Matching: {matching_invalid}, Bonanza: {bonanza_invalid}")
    
    return total_invalid == 0


def main():
    """Run the backfill script"""
    logger.info("🚀 Starting DC Protocol Award Status Backfill")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
    logger.info("")
    
    db = SessionLocal()
    
    try:
        # Backfill each award type
        direct_count = backfill_direct_awards(db)
        matching_count = backfill_matching_awards(db)
        bonanza_count = backfill_bonanza_awards(db)
        
        total_updated = direct_count + matching_count + bonanza_count
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"📊 BACKFILL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Direct Awards Updated: {direct_count}")
        logger.info(f"Matching Awards Updated: {matching_count}")
        logger.info(f"Bonanza Awards Updated: {bonanza_count}")
        logger.info(f"Total Awards Updated: {total_updated}")
        logger.info("")
        
        # Verify
        if verify_backfill(db):
            logger.info("✅ Backfill completed successfully!")
            return 0
        else:
            logger.error("❌ Backfill verification failed!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Backfill failed with error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
