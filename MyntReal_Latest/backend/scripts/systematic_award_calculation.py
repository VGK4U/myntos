"""
DC PROTOCOL SYSTEMATIC AWARD CALCULATION - Nov 11, 2025
Calculate and set achievement_date for ALL eligible users based on actual post-Oct 21 referrals

PROPER APPROACH:
- Calculate from source data (User table activations after Oct 21)
- Apply bonanza deductions (if any)
- Determine eligible tiers for each user
- Set achievement_date for all qualified awards
- Idempotent: Only updates NULL achievement_date where user qualifies

OCTOBER 21 RESET LOGIC:
- Users activated BEFORE Oct 21: Only count referrals activated ON/AFTER Oct 21
- Users activated ON/AFTER Oct 21: Count all referrals (normal)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal
from datetime import datetime, date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWARDS_RESET_DATE = date(2025, 10, 21)

def calculate_direct_awards_systematically():
    """
    Systematically calculate and set achievement_date for ALL eligible direct award winners
    """
    db = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("SYSTEMATIC DIRECT AWARDS CALCULATION")
        logger.info("=" * 80)
        
        # Get all direct award tiers
        tiers_query = text("""
            SELECT id, referral_count, cumulative_required, award_name, award_description
            FROM direct_award_tier
            ORDER BY cumulative_required ASC
        """)
        
        tiers = db.execute(tiers_query).fetchall()
        logger.info(f"📊 Found {len(tiers)} direct award tiers")
        
        # Get all users
        users_query = text("""
            SELECT id, activation_date
            FROM "user"
            WHERE account_status = 'Active'
            AND coupon_status IN ('Activated', 'Active')
        """)
        
        users = db.execute(users_query).fetchall()
        logger.info(f"📊 Processing {len(users)} active users")
        
        total_awards_set = 0
        
        for user in users:
            user_id = user[0]
            user_activation_date = user[1].date() if user[1] else None
            
            # Determine referral cutoff date based on Oct 21 reset
            if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
                # Pre-Oct 21 user: Only count referrals ON/AFTER Oct 21
                referral_filter = f"AND activation_date >= '{AWARDS_RESET_DATE}'"
            else:
                # Post-Oct 21 user: Count all referrals
                referral_filter = ""
            
            # Count post-Oct 21 referrals for this user
            referral_query = text(f"""
                SELECT COALESCE(SUM(package_points), 0) as total_points
                FROM "user"
                WHERE referrer_id = :user_id
                AND coupon_status = 'Activated'
                {referral_filter}
            """)
            
            result = db.execute(referral_query, {"user_id": user_id}).fetchone()
            total_points = float(result[0])
            
            # Get bonanza deductions
            bonanza_query = text("""
                SELECT COALESCE(SUM(deduction_amount_direct), 0) as total_deduction
                FROM dynamic_bonanza_history
                WHERE user_id = :user_id
                AND deduction_applied_to_direct_awards = true
                AND processed_at IS NOT NULL
            """)
            
            bonanza_result = db.execute(bonanza_query, {"user_id": user_id}).fetchone()
            bonanza_deduction = float(bonanza_result[0])
            
            # Calculate net available points
            net_points = max(0, total_points - bonanza_deduction)
            
            # Determine which tiers user qualifies for
            for tier in tiers:
                tier_id = tier[0]
                cumulative_required = tier[2]
                
                if net_points >= cumulative_required:
                    # User qualifies! Check if achievement_date is already set
                    check_query = text("""
                        SELECT id, achievement_date
                        FROM user_award_progress
                        WHERE user_id = :user_id
                        AND award_tier_id = :tier_id
                    """)
                    
                    existing = db.execute(check_query, {
                        "user_id": user_id,
                        "tier_id": tier_id
                    }).fetchone()
                    
                    if existing and existing[1] is None:
                        # Record exists but achievement_date is NULL - SET IT!
                        update_query = text("""
                            UPDATE user_award_progress
                            SET achievement_date = NOW(),
                                achieved_at = NOW(),
                                status = 'Achieved',
                                is_eligible = true,
                                effective_progress_count = :net_points
                            WHERE user_id = :user_id
                            AND award_tier_id = :tier_id
                            AND achievement_date IS NULL
                        """)
                        
                        db.execute(update_query, {
                            "user_id": user_id,
                            "tier_id": tier_id,
                            "net_points": net_points
                        })
                        
                        total_awards_set += 1
                        logger.info(f"✅ Set achievement for {user_id} - Tier {tier_id} (Net points: {net_points})")
                    
                    elif not existing:
                        # No record exists - CREATE IT!
                        create_query = text("""
                            INSERT INTO user_award_progress (
                                user_id, award_tier_id, achievement_date, achieved_at,
                                status, is_eligible, effective_progress_count, processed_status
                            ) VALUES (
                                :user_id, :tier_id, NOW(), NOW(),
                                'Achieved', true, :net_points, 'Pending Approval'
                            )
                        """)
                        
                        db.execute(create_query, {
                            "user_id": user_id,
                            "tier_id": tier_id,
                            "net_points": net_points
                        })
                        
                        total_awards_set += 1
                        logger.info(f"✅ Created award for {user_id} - Tier {tier_id} (Net points: {net_points})")
        
        db.commit()
        
        logger.info(f"\n✅ SYSTEMATIC CALCULATION COMPLETE")
        logger.info(f"   Total awards set/created: {total_awards_set}")
        
        return total_awards_set
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during systematic calculation: {e}")
        raise
    finally:
        db.close()

def calculate_matching_awards_systematically():
    """
    Systematically calculate and set achievement_date for ALL eligible matching award winners
    """
    db = SessionLocal()
    
    try:
        logger.info("\n" + "=" * 80)
        logger.info("SYSTEMATIC MATCHING AWARDS CALCULATION")
        logger.info("=" * 80)
        
        # Import matching calculation function
        from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
        from app.services.award_service import AwardService
        
        # Get all matching award tiers
        tiers_query = text("""
            SELECT id, match_count, cumulative_required, award_name, award_description
            FROM matching_award_tier
            ORDER BY cumulative_required ASC
        """)
        
        tiers = db.execute(tiers_query).fetchall()
        logger.info(f"📊 Found {len(tiers)} matching award tiers")
        
        # Get all users
        users_query = text("""
            SELECT id, activation_date
            FROM "user"
            WHERE account_status = 'Active'
            AND coupon_status IN ('Activated', 'Active')
        """)
        
        users = db.execute(users_query).fetchall()
        logger.info(f"📊 Processing {len(users)} active users")
        
        total_awards_set = 0
        award_service = AwardService(db)
        
        for user in users:
            user_id = user[0]
            user_activation_date = user[1].date() if user[1] else None
            
            # Determine if we need to apply the reset filter
            if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
                # Pre-Oct 21 user: Only count users activated ON or AFTER Oct 21
                reset_date_str = AWARDS_RESET_DATE.isoformat()
                matching_result = get_matching_pairs_with_reset_logic_sql(db, user_id, reset_date_str)
            else:
                # Post-Oct 21 user: Count all users (no reset filter)
                matching_result = get_matching_pairs_with_reset_logic_sql(db, user_id, None)
            
            total_matching = matching_result['matching_pairs']
            
            # Get bonanza deductions
            bonanza_deduction_data = award_service.get_bonanza_deduction(user_id, 'matching')
            bonanza_deduction = bonanza_deduction_data.get('total_deduction', 0)
            
            # Calculate net available matching pairs
            net_matching = max(0, total_matching - bonanza_deduction)
            
            # Determine which tiers user qualifies for
            for tier in tiers:
                tier_id = tier[0]
                cumulative_required = tier[2]
                
                if net_matching >= cumulative_required:
                    # User qualifies! Check if achievement_date is already set
                    check_query = text("""
                        SELECT id, achievement_date
                        FROM user_matching_award_progress
                        WHERE user_id = :user_id
                        AND matching_award_tier_id = :tier_id
                    """)
                    
                    existing = db.execute(check_query, {
                        "user_id": user_id,
                        "tier_id": tier_id
                    }).fetchone()
                    
                    if existing and existing[1] is None:
                        # Record exists but achievement_date is NULL - SET IT!
                        update_query = text("""
                            UPDATE user_matching_award_progress
                            SET achievement_date = NOW(),
                                status = 'Achieved',
                                is_eligible = true,
                                effective_matching_count = :net_matching
                            WHERE user_id = :user_id
                            AND matching_award_tier_id = :tier_id
                            AND achievement_date IS NULL
                        """)
                        
                        db.execute(update_query, {
                            "user_id": user_id,
                            "tier_id": tier_id,
                            "net_matching": net_matching
                        })
                        
                        total_awards_set += 1
                        logger.info(f"✅ Set achievement for {user_id} - Matching Tier {tier_id} (Net pairs: {net_matching})")
                    
                    elif not existing:
                        # No record exists - CREATE IT!
                        create_query = text("""
                            INSERT INTO user_matching_award_progress (
                                user_id, matching_award_tier_id, achievement_date,
                                status, is_eligible, effective_matching_count, processed_status
                            ) VALUES (
                                :user_id, :tier_id, NOW(),
                                'Achieved', true, :net_matching, 'Pending Approval'
                            )
                        """)
                        
                        db.execute(create_query, {
                            "user_id": user_id,
                            "tier_id": tier_id,
                            "net_matching": net_matching
                        })
                        
                        total_awards_set += 1
                        logger.info(f"✅ Created award for {user_id} - Matching Tier {tier_id} (Net pairs: {net_matching})")
        
        db.commit()
        
        logger.info(f"\n✅ SYSTEMATIC CALCULATION COMPLETE")
        logger.info(f"   Total matching awards set/created: {total_awards_set}")
        
        return total_awards_set
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during systematic matching calculation: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("\n🚀 Starting SYSTEMATIC award calculation for all eligible users...")
    logger.info("   October 21 Reset Logic: Only counting post-reset activations\n")
    
    try:
        # Calculate direct awards
        direct_total = calculate_direct_awards_systematically()
        
        # Calculate matching awards
        matching_total = calculate_matching_awards_systematically()
        
        logger.info("\n" + "=" * 80)
        logger.info("SYSTEMATIC CALCULATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Direct Awards Set/Created: {direct_total}")
        logger.info(f"Matching Awards Set/Created: {matching_total}")
        logger.info(f"TOTAL: {direct_total + matching_total}")
        logger.info("\n✅ ALL eligible users now have achievement_date set!")
        logger.info("   Awards will appear in RVZ Approval Queue\n")
        
    except Exception as e:
        logger.error(f"\n❌ SYSTEMATIC CALCULATION FAILED: {e}")
        sys.exit(1)
