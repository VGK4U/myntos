"""
FULL AWARD STATUS RESET SCRIPT
Resets ALL awards to "Pending Approval" status with data cleanup

IMPORTANT: This preserves October 21st reset logic by NOT touching:
- achievement_date (used for Oct 21 filtering)
- claimed_date (used for bonanza filtering)
- Award amounts, points, tier info

This script WILL reset:
- processed_status → "Pending Approval"
- All procurement fields → NULL
- All delivery tracking → NULL
- Creates audit log entries

Author: MNR Development Team
Date: Nov 11, 2025
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

from app.core.config import settings
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, AwardAuditLog
from app.models.bonanza import DynamicBonanzaHistory
from app.constants.award_statuses import AwardStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def reset_direct_awards(db):
    """Reset all direct awards to Pending Approval"""
    logger.info("=" * 60)
    logger.info("RESETTING DIRECT AWARDS TO PENDING APPROVAL")
    logger.info("=" * 60)
    
    awards = db.query(UserAwardProgress).all()
    reset_count = 0
    
    for award in awards:
        original_status = award.processed_status
        
        # Only reset if not already Pending Approval
        if original_status != AwardStatus.PENDING_APPROVAL:
            logger.info(f"Direct Award #{award.id} (User: {award.user_id}): '{original_status}' → 'Pending Approval'")
            
            # Reset status
            award.processed_status = AwardStatus.PENDING_APPROVAL
            
            # Clear procurement data
            award.actual_cost_paid = None
            award.vendor_name = None
            award.purchase_date = None
            award.invoice_number = None
            award.tax_amount = None
            award.transport_charges = None
            award.cost_variance = None
            award.cost_variance_reason = None
            
            # Clear delivery tracking
            award.dispatch_date = None
            award.received_date = None
            award.delivery_notes = None
            award.courier_service = None
            award.tracking_number = None
            
            # PRESERVE these fields (Oct 21 logic):
            # - achievement_date (already exists, don't touch)
            # - gift_name, tier, amount (award details)
            # - user_id, award_type (relationships)
            
            # Create audit log
            audit_log = AwardAuditLog(
                entity_type='direct_award',
                entity_id=award.id,
                action='full_reset',
                old_status=original_status,
                new_status=AwardStatus.PENDING_APPROVAL,
                actor_role='System',
                actor_id='SYSTEM_RESET',
                notes=f'Full reset to Pending Approval - User requested reset while preserving Oct 21 logic',
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            reset_count += 1
    
    db.commit()
    logger.info(f"✅ Reset {reset_count} direct awards to Pending Approval")
    return reset_count


def reset_matching_awards(db):
    """Reset all matching awards to Pending Approval"""
    logger.info("=" * 60)
    logger.info("RESETTING MATCHING AWARDS TO PENDING APPROVAL")
    logger.info("=" * 60)
    
    awards = db.query(UserMatchingAwardProgress).all()
    reset_count = 0
    
    for award in awards:
        original_status = award.processed_status
        
        # Only reset if not already Pending Approval
        if original_status != AwardStatus.PENDING_APPROVAL:
            logger.info(f"Matching Award #{award.id} (User: {award.user_id}): '{original_status}' → 'Pending Approval'")
            
            # Reset status
            award.processed_status = AwardStatus.PENDING_APPROVAL
            
            # Clear procurement data
            award.actual_cost_paid = None
            award.vendor_name = None
            award.purchase_date = None
            award.invoice_number = None
            award.tax_amount = None
            award.transport_charges = None
            award.cost_variance = None
            award.cost_variance_reason = None
            
            # Clear delivery tracking
            award.dispatch_date = None
            award.received_date = None
            award.delivery_notes = None
            award.courier_service = None
            award.tracking_number = None
            
            # PRESERVE these fields (Oct 21 logic):
            # - achievement_date (already exists, don't touch)
            # - gift_name, tier, amount (award details)
            # - user_id, award_type (relationships)
            
            # Create audit log
            audit_log = AwardAuditLog(
                entity_type='matching_award',
                entity_id=award.id,
                action='full_reset',
                old_status=original_status,
                new_status=AwardStatus.PENDING_APPROVAL,
                actor_role='System',
                actor_id='SYSTEM_RESET',
                notes=f'Full reset to Pending Approval - User requested reset while preserving Oct 21 logic',
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            reset_count += 1
    
    db.commit()
    logger.info(f"✅ Reset {reset_count} matching awards to Pending Approval")
    return reset_count


def reset_bonanza_awards(db):
    """Reset all bonanza awards to Pending Approval"""
    logger.info("=" * 60)
    logger.info("RESETTING BONANZA AWARDS TO PENDING APPROVAL")
    logger.info("=" * 60)
    
    awards = db.query(DynamicBonanzaHistory).all()
    reset_count = 0
    
    for award in awards:
        original_status = award.processed_status
        
        # Only reset if not already Pending Approval
        if original_status != AwardStatus.PENDING_APPROVAL:
            logger.info(f"Bonanza Award #{award.id} (User: {award.user_id}): '{original_status}' → 'Pending Approval'")
            
            # Reset status
            award.processed_status = AwardStatus.PENDING_APPROVAL
            
            # Clear procurement data
            award.actual_cost_paid = None
            award.vendor_name = None
            award.purchase_date = None
            award.invoice_number = None
            award.tax_amount = None
            award.transport_charges = None
            award.cost_variance = None
            award.cost_variance_reason = None
            
            # Clear delivery tracking
            award.dispatch_date = None
            award.received_date = None
            award.delivery_notes = None
            award.courier_service = None
            award.tracking_number = None
            
            # PRESERVE these fields (Oct 21 logic):
            # - claimed_date (used for Oct 21 bonanza filtering)
            # - reward_name, tier (award details)
            # - user_id (relationships)
            
            # Create audit log
            audit_log = AwardAuditLog(
                entity_type='bonanza',
                entity_id=award.id,
                action='full_reset',
                old_status=original_status,
                new_status=AwardStatus.PENDING_APPROVAL,
                actor_role='System',
                actor_id='SYSTEM_RESET',
                notes=f'Full reset to Pending Approval - User requested reset while preserving Oct 21 logic',
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            reset_count += 1
    
    db.commit()
    logger.info(f"✅ Reset {reset_count} bonanza awards to Pending Approval")
    return reset_count


def verify_reset(db):
    """Verify all awards are now at Pending Approval"""
    logger.info("=" * 60)
    logger.info("VERIFICATION")
    logger.info("=" * 60)
    
    # Count non-pending awards
    direct_non_pending = db.query(UserAwardProgress).filter(
        UserAwardProgress.processed_status != AwardStatus.PENDING_APPROVAL
    ).count()
    
    matching_non_pending = db.query(UserMatchingAwardProgress).filter(
        UserMatchingAwardProgress.processed_status != AwardStatus.PENDING_APPROVAL
    ).count()
    
    bonanza_non_pending = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.processed_status != AwardStatus.PENDING_APPROVAL
    ).count()
    
    total_non_pending = direct_non_pending + matching_non_pending + bonanza_non_pending
    
    # Count total awards
    total_direct = db.query(UserAwardProgress).count()
    total_matching = db.query(UserMatchingAwardProgress).count()
    total_bonanza = db.query(DynamicBonanzaHistory).count()
    total_awards = total_direct + total_matching + total_bonanza
    
    logger.info(f"Direct Awards: {total_direct - direct_non_pending}/{total_direct} at Pending Approval")
    logger.info(f"Matching Awards: {total_matching - matching_non_pending}/{total_matching} at Pending Approval")
    logger.info(f"Bonanza Awards: {total_bonanza - bonanza_non_pending}/{total_bonanza} at Pending Approval")
    logger.info("")
    
    if total_non_pending == 0:
        logger.info(f"✅ ALL {total_awards} awards are now at 'Pending Approval'!")
        return True
    else:
        logger.error(f"❌ Found {total_non_pending} awards NOT at Pending Approval")
        return False


def main():
    """Run the full reset script"""
    logger.info("🚀 FULL AWARD STATUS RESET TO PENDING APPROVAL")
    logger.info("⚠️  Preserving October 21st reset logic (date fields intact)")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
    logger.info("")
    
    db = SessionLocal()
    
    try:
        # Reset each award type
        direct_count = reset_direct_awards(db)
        matching_count = reset_matching_awards(db)
        bonanza_count = reset_bonanza_awards(db)
        
        total_reset = direct_count + matching_count + bonanza_count
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"📊 RESET SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Direct Awards Reset: {direct_count}")
        logger.info(f"Matching Awards Reset: {matching_count}")
        logger.info(f"Bonanza Awards Reset: {bonanza_count}")
        logger.info(f"Total Awards Reset: {total_reset}")
        logger.info("")
        
        # Verify
        if verify_reset(db):
            logger.info("✅ Reset completed successfully!")
            logger.info("✅ October 21st reset logic preserved (achievement_date/claimed_date intact)")
            return 0
        else:
            logger.error("❌ Reset verification failed!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Reset failed with error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
