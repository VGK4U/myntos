"""
RVZ Awards Regeneration Endpoint
Regenerates all matching awards using correct post-Oct 21 calculations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rvz_protection import verify_rvz_access
from app.models.user import User
from app.models.awards import UserMatchingAwardProgress, MatchingAwardTier
from app.core.scheduler import calculate_effective_matching_count
from app.services.leg_metrics_cache_service import LegMetricsCacheService

router = APIRouter(prefix="/rvz/awards-regenerate", tags=["RVZ Awards Management"])
logger = logging.getLogger(__name__)

AWARDS_RESET_DATE = date(2025, 10, 21)


@router.post("/regenerate-all-matching-awards")
def regenerate_all_matching_awards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ONLY: Regenerate all matching awards using correct post-Oct 21 calculations
    
    This endpoint:
    1. Cancels ALL existing matching award records (stale data from Nov 3 scheduler)
    2. Recalculates post-Oct 21 matching achievements for ALL users
    3. Creates new matching award records for eligible users
    4. Refreshes user_leg_metrics cache with correct data
    
    CRITICAL FIX: Addresses bug where awards used pre-Oct 21 data instead of post-reset data
    """
    # RVZ authorization
    verify_rvz_access(current_user, "Awards Regeneration")
    
    logger.info(f"🔄 RVZ {current_user.id} initiated matching awards regeneration")
    
    try:
        # STEP 1: Cancel ALL existing matching award records
        logger.info("📋 Step 1/4: Cancelling all existing matching award records...")
        
        existing_awards = db.query(UserMatchingAwardProgress).filter(
            UserMatchingAwardProgress.award_status.in_(['pending', 'approved', 'rejected'])
        ).all()
        
        cancelled_count = 0
        for award in existing_awards:
            award.award_status = 'cancelled'
            award.processed_status = 'Cancelled'
            award.admin_notes = (
                f"{award.admin_notes}\n" if award.admin_notes else ""
            ) + f"REGENERATION (2025-11-08): Cancelled for full system regeneration with correct post-Oct 21 logic."
            cancelled_count += 1
        
        db.commit()
        logger.info(f"✅ Cancelled {cancelled_count} existing matching awards")
        
        # STEP 2: Get all matching award tiers
        logger.info("📋 Step 2/4: Loading matching award tiers...")
        
        tiers = db.query(MatchingAwardTier).order_by(
            MatchingAwardTier.cumulative_required
        ).all()
        
        if not tiers:
            raise HTTPException(status_code=500, detail="No matching award tiers found in database")
        
        logger.info(f"✅ Loaded {len(tiers)} matching award tiers")
        
        # STEP 3: Calculate and create awards for ALL active users
        logger.info("📋 Step 3/4: Recalculating matching achievements for all users...")
        
        active_users = db.query(User).filter(
            User.activation_date.isnot(None),
            User.package_points > 0
        ).all()
        
        logger.info(f"✅ Found {len(active_users)} active users to process")
        
        awards_created = 0
        users_with_awards = 0
        cache_refreshed = 0
        
        cache_service = LegMetricsCacheService(db)
        
        for user in active_users:
            # Calculate post-Oct 21 matching achievement (NOW USES CORRECTED FUNCTION!)
            matching_result = calculate_effective_matching_count(db, user.id)
            
            effective_pairs = int(matching_result['effective_count'])
            left_points = matching_result['left_points']
            right_points = matching_result['right_points']
            
            # Skip users with 0 matching pairs
            if effective_pairs <= 0:
                continue
            
            # Find highest tier user qualifies for
            highest_tier = None
            for tier in tiers:
                if effective_pairs >= tier.match_count:
                    highest_tier = tier
                else:
                    break  # Tiers are sorted, so we can stop
            
            if highest_tier:
                # Check if award already exists for this tier (shouldn't, but safety check)
                existing = db.query(UserMatchingAwardProgress).filter(
                    UserMatchingAwardProgress.user_id == user.id,
                    UserMatchingAwardProgress.matching_award_tier_id == highest_tier.id,
                    UserMatchingAwardProgress.award_status != 'cancelled'
                ).first()
                
                if not existing:
                    # DC PROTOCOL: Check if this is a legacy award
                    from app.services.award_processing_service import AwardProcessingService
                    award_service = AwardProcessingService(db)
                    is_legacy = award_service._check_is_legacy_award(user.id)
                    
                    # Create new award record
                    new_award = UserMatchingAwardProgress(
                        user_id=user.id,
                        matching_award_tier_id=highest_tier.id,
                        current_matches=effective_pairs,
                        award_status='pending',
                        processed_status='Pending',
                        is_legacy_pre_reset=is_legacy,  # DC PROTOCOL: Mark legacy awards
                        admin_notes=f"REGENERATED (2025-11-08): Created with correct post-Oct 21 calculation. Left: {left_points}, Right: {right_points}, Effective: {effective_pairs}"
                    )
                    db.add(new_award)
                    awards_created += 1
                    users_with_awards += 1
            
            # Refresh cache for this user (NOW USES CORRECTED CALCULATION!)
            cache_service.refresh_user_metrics(user.id, source='rvz_regeneration')
            cache_refreshed += 1
            
            # Commit every 100 users to avoid memory issues
            if cache_refreshed % 100 == 0:
                db.commit()
                logger.info(f"   Progress: {cache_refreshed}/{len(active_users)} users processed...")
        
        db.commit()
        
        logger.info("✅ Step 3/4 complete")
        logger.info(f"   📊 Awards created: {awards_created}")
        logger.info(f"   👥 Users with awards: {users_with_awards}")
        logger.info(f"   💾 Caches refreshed: {cache_refreshed}")
        
        # STEP 4: Summary statistics
        logger.info("📋 Step 4/4: Generating summary statistics...")
        
        final_pending = db.query(UserMatchingAwardProgress).filter(
            UserMatchingAwardProgress.award_status == 'pending'
        ).count()
        
        final_cancelled = db.query(UserMatchingAwardProgress).filter(
            UserMatchingAwardProgress.award_status == 'cancelled'
        ).count()
        
        logger.info("✅ REGENERATION COMPLETE!")
        
        return {
            "success": True,
            "message": "All matching awards regenerated with correct post-Oct 21 calculations",
            "regeneration_summary": {
                "awards_cancelled": cancelled_count,
                "awards_created": awards_created,
                "users_with_new_awards": users_with_awards,
                "caches_refreshed": cache_refreshed,
                "total_active_users": len(active_users)
            },
            "final_status": {
                "pending_awards": final_pending,
                "cancelled_awards": final_cancelled
            },
            "reset_date": str(AWARDS_RESET_DATE),
            "executed_by": current_user.id,
            "executed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Awards regeneration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")
