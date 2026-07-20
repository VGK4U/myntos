"""
FAST Awards API - Optimized for instant loading
Bypasses complex recursive queries for 36+ hour loading issue fix
"""

from typing import Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, asc
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.awards import DirectAwardTier, UserAwardProgress, MatchingAwardTier, UserMatchingAwardProgress
from app.models.transaction import PendingIncome
from app.services.award_service import AwardService
from app.services.award_sync_service import sync_user_award_statuses

router = APIRouter(prefix="/awards-fast", tags=["Fast Awards"])

_STATUS_MAP = {
    "Pending Approval": "Pending",
    "Admin Approved": "Approved",
    "Procurement Pending": "Processed",
    "Processed for Dispatch": "Processed",
    "Dispatched": "Processed",
    "Delivered": "Completed",
    "Rejected": "Rejected",
}

def _simplify_status(raw: str) -> str:
    return _STATUS_MAP.get(raw, raw if raw in ("Pending", "Approved", "Processed", "Completed", "Rejected") else "Pending")

def _get_last_updated(existing) -> str:
    if not existing:
        return None
    from datetime import datetime, date
    candidates = []
    for attr in ('received_date', 'delivered_at', 'admin_approved_at', 'dispatch_date', 'achievement_date', 'processed_date'):
        val = getattr(existing, attr, None)
        if val is not None:
            if isinstance(val, datetime):
                candidates.append(val)
            elif isinstance(val, date):
                candidates.append(datetime(val.year, val.month, val.day))
    if not candidates:
        return None
    latest = max(candidates)
    return latest.isoformat()


@router.get("/user/{user_id}/direct")
async def get_user_direct_awards_fast(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    OPTIMIZED: Get direct awards instantly without slow recursive queries
    Shows achievements dynamically based on current referral counts
    """
    # Validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # DC Protocol Feb 2026: Auto-sync award statuses before loading
    try:
        sync_user_award_statuses(db, user_id)
    except Exception as e:
        logger.warning(f"[AWARD-SYNC] Sync failed for {user_id}, continuing: {e}")

    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # User doesn't exist - return empty
        tiers = db.query(DirectAwardTier).order_by(asc(DirectAwardTier.cumulative_required)).all()
        progress_data = []
        for tier in tiers:
            progress_data.append({
                "tier_info": {
                    "id": tier.id,
                    "referral_count": tier.referral_count,
                    "cumulative_required": tier.cumulative_required,
                    "rank_name": tier.award_name,
                    "award_item": tier.award_description,
                    "actual_price": float(tier.actual_price) if tier.actual_price else 0
                },
                "current_direct_count": 0,
                "lifetime_referral_count": 0,
                "total_package_points": 0.0,
                "effective_points": 0.0,
                "bonanza_deductions": 0,
                "progress_percentage": 0.0,
                "achieved": False,
                "achievement_date": None
            })
        
        return {
            "success": True,
            "direct_awards": progress_data,
            "user_info": {
                "user_id": user_id,
                "current_direct_referrals": 0,
                "total_package_points": 0.0
            }
        }
    
    # OCTOBER 21ST RESET LOGIC: Pre-Oct 21st users start fresh from Oct 21, 2025
    # Users activated before Oct 21: Only count referrals activated ON or AFTER Oct 21, 2025
    # Users activated on/after Oct 21: Count all referrals (normal)
    AWARDS_RESET_DATE = date(2025, 10, 21)
    
    user_activation_date = user.activation_date.date() if isinstance(user.activation_date, datetime) else user.activation_date
    
    # Determine cutoff date for counting referrals
    if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
        # Pre-Oct 20th user: Reset to 0, only count referrals activated AFTER Oct 20
        referral_cutoff_date = AWARDS_RESET_DATE
    else:
        # Post-Oct 20th user: Count all referrals (no cutoff)
        referral_cutoff_date = None
    
    # Count referrals with date filtering
    # DC Protocol: Exclude Welcome Coupon AND Star/Loyal (package_points=0) users from award achievement counting
    if referral_cutoff_date:
        total_points_achievement = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0,
            User.activation_date >= referral_cutoff_date
        ).scalar() or 0.0
        
        total_points_display = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0,
            User.activation_date >= referral_cutoff_date
        ).scalar() or 0.0
        
        direct_count_display = db.query(func.count(User.id)).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0,
            User.activation_date >= referral_cutoff_date
        ).scalar() or 0
    else:
        total_points_achievement = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0
        ).scalar() or 0.0
        
        total_points_display = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0
        ).scalar() or 0.0
        
        direct_count_display = db.query(func.count(User.id)).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0
        ).scalar() or 0
    
    # Get bonanza deductions for direct awards
    award_service = AwardService(db)
    bonanza_deduction_data = award_service.get_bonanza_deduction(user_id, 'direct')
    total_bonanza_deductions = bonanza_deduction_data.get('total_deduction', 0)
    
    # DC Protocol: UNIVERSAL ELIGIBILITY CHECK (aligned with award_service/management page)
    # Achievement requires BOTH: sufficient points AND eligibility criteria
    eligibility = award_service.check_universal_eligibility(user_id)
    is_eligible_for_awards = eligibility.get('is_eligible', False)
    
    # Get all tiers
    tiers = db.query(DirectAwardTier).order_by(asc(DirectAwardTier.cumulative_required)).all()
    
    # Get user's achieved awards
    progress_records = db.query(UserAwardProgress).filter(
        UserAwardProgress.user_id == user_id
    ).all()
    
    progress_data = []
    previous_cumulative = 0
    
    for tier in tiers:
        existing = next((p for p in progress_records if p.award_tier_id == tier.id), None)
        
        # Calculate tier's point requirement
        tier_point_requirement = tier.cumulative_required - previous_cumulative
        
        # Apply bonanza deductions to achievement calculation
        effective_points_for_achievement = max(0, total_points_achievement - total_bonanza_deductions)
        effective_points_for_display = max(0, total_points_display - total_bonanza_deductions)
        
        # HYBRID CALCULATION: Award is achieved if EITHER:
        # 1. Current referrals meet requirement (dynamic) AND eligibility, OR
        # 2. Database record exists with achieved status (persistent)
        # This prevents achievement loss due to reversals/corrections
        # 
        # DC Protocol: Achievement requires BOTH sufficient points AND universal eligibility
        # (aligned with award_service/management page structure)
        # 
        # OCTOBER 21 RESET FIX: For pre-Oct 21 users, ONLY use dynamic calculation
        # Database records from before reset are stale and should be ignored
        dynamically_achieved = (effective_points_for_achievement >= tier.cumulative_required) and is_eligible_for_awards
        
        if referral_cutoff_date:
            achieved = dynamically_achieved
        else:
            database_achieved = (existing is not None 
                                and existing.achievement_date is not None 
                                and existing.effective_progress_count >= tier.cumulative_required
                                and is_eligible_for_awards)
            achieved = dynamically_achieved or database_achieved
        
        # DISPLAY PROGRESS: Show current progress toward THIS tier
        current_tier_points_display = max(0, effective_points_for_display - previous_cumulative)
        
        # Calculate progress as referral count equivalent for DISPLAY
        if tier_point_requirement > 0:
            progress_percentage = min(100.0, (current_tier_points_display / tier_point_requirement) * 100)
            display_progress = int((progress_percentage / 100.0) * tier.referral_count)
        else:
            display_progress = 0
        
        progress_data.append({
            "tier_info": {
                "id": tier.id,
                "referral_count": tier.referral_count,
                "cumulative_required": tier.cumulative_required,
                "rank_name": tier.award_name,
                "award_item": tier.award_description,
                "actual_price": float(tier.actual_price) if tier.actual_price else 0
            },
            "current_direct_count": display_progress,
            "lifetime_referral_count": direct_count_display,
            "total_package_points": float(total_points_display),
            "effective_points": float(effective_points_for_display),
            "bonanza_deductions": total_bonanza_deductions,
            "bonanza_details": bonanza_deduction_data.get('deduction_details', []),
            "progress_percentage": min(100.0, (current_tier_points_display / tier_point_requirement * 100)) if tier_point_requirement > 0 else 0.0,
            "achieved": achieved,  # Hybrid: dynamic OR database record
            "achievement_date": existing.achievement_date.isoformat() if existing and existing.achievement_date else None,
            # DC PROTOCOL: Status only applies to ACHIEVED awards
            # Non-achieved awards must always show "Pending" regardless of DB processed_status
            "processed_status": (existing.processed_status if existing else "Pending") if achieved else "Pending",
            "simplified_status": _simplify_status(existing.processed_status if existing else "Pending") if achieved else "Pending",
            "admin_approved_by": existing.admin_approved_by if existing else None,
            "admin_approved_at": existing.admin_approved_at.isoformat() if existing and existing.admin_approved_at else None,
            # DC PROTOCOL: Include delivery tracking fields
            "dispatch_date": existing.dispatch_date.isoformat() if existing and existing.dispatch_date else None,
            "received_date": existing.received_date.isoformat() if existing and existing.received_date else None,
            "delivery_notes": existing.delivery_notes if existing else None,
            # Simplified: single last_updated date (most recent status change)
            # Only show for achieved awards to avoid stale dates from legacy records
            "last_updated": _get_last_updated(existing) if achieved else None
        })
        
        previous_cumulative = tier.cumulative_required
    
    return {
        "success": True,
        "direct_awards": progress_data,
        "user_info": {
            "user_id": user_id,
            "current_direct_referrals": direct_count_display,  # Display: 0 for old data
            "total_package_points": float(total_points_display)  # Display: 0 for old data
        }
    }


@router.get("/user/{user_id}/matching")
async def get_user_matching_awards_fast(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    OPTIMIZED: Get matching awards instantly
    Shows achievements dynamically based on current matching pairs
    """
    # Validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # User doesn't exist - return empty
        tiers = db.query(MatchingAwardTier).order_by(asc(MatchingAwardTier.cumulative_required)).all()
        progress_data = []
        for tier in tiers:
            progress_data.append({
                "tier_info": {
                    "id": tier.id,
                    "required_matching_pairs": tier.match_count,
                    "cumulative_required": tier.cumulative_required,
                    "rank_name": tier.award_name,
                    "award_item": tier.award_description,
                    "achievement_bonus": float(tier.actual_price) if tier.actual_price else 0
                },
                "current_matching_count": 0,
                "lifetime_matching_count": 0,
                "effective_remaining": 0,
                "bonanza_deductions": 0,
                "achieved": False,
                "achievement_date": None
            })
        
        return {
            "success": True,
            "matching_awards": progress_data,
            "user_info": {
                "user_id": user_id,
                "lifetime_matching_count": 0,
                "qualification_met": False
            }
        }
    
    # OCTOBER 21ST RESET LOGIC: Pre-Oct 21st users start fresh from Oct 21, 2025
    # Users activated before Oct 21: Only count users activated AFTER Oct 21, 2025
    # Users activated on/after Oct 21: Count all users (normal)
    from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
    
    AWARDS_RESET_DATE = date(2025, 10, 21)
    user_activation_date = user.activation_date.date() if isinstance(user.activation_date, datetime) else user.activation_date
    
    # Determine if we need to apply the reset filter
    if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
        # Pre-Oct 20th user: Only count users activated ON or AFTER Oct 20
        reset_date_str = AWARDS_RESET_DATE.isoformat()
        matching_result = get_matching_pairs_with_reset_logic_sql(db, user_id, reset_date_str)
    else:
        # Post-Oct 20th user: Count all users (no reset filter)
        matching_result = get_matching_pairs_with_reset_logic_sql(db, user_id, None)
    
    # Use the calculated matching pairs
    lifetime_matching_achievement = matching_result['matching_pairs']
    lifetime_matching_display = matching_result['matching_pairs']
    
    # Get bonanza deductions for matching awards
    award_service = AwardService(db)
    bonanza_deduction_data = award_service.get_bonanza_deduction(user_id, 'matching')
    total_bonanza_deductions = bonanza_deduction_data.get('total_deduction', 0)
    
    # DC Protocol: UNIVERSAL ELIGIBILITY CHECK (aligned with award_service/management page)
    # Achievement requires BOTH: sufficient matching pairs AND eligibility criteria
    eligibility = award_service.check_universal_eligibility(user_id)
    is_eligible_for_awards = eligibility.get('is_eligible', False)
    
    # Get all tiers
    tiers = db.query(MatchingAwardTier).order_by(asc(MatchingAwardTier.cumulative_required)).all()
    
    # Get user's achieved awards
    progress_records = db.query(UserMatchingAwardProgress).filter(
        UserMatchingAwardProgress.user_id == user_id
    ).all()
    
    progress_data = []
    previous_cumulative = 0
    
    for tier in tiers:
        existing = next((p for p in progress_records if p.matching_award_tier_id == tier.id), None)
        
        # Apply bonanza deductions to achievement calculation
        effective_matching_for_achievement = max(0, lifetime_matching_achievement - total_bonanza_deductions)
        effective_matching_for_display = max(0, lifetime_matching_display - total_bonanza_deductions)
        
        # HYBRID CALCULATION: Award is achieved if EITHER:
        # 1. Current matching pairs meet requirement (dynamic) AND eligibility, OR
        # 2. Database record exists with achieved status (persistent)
        # This prevents achievement loss due to ledger adjustments/corrections
        # 
        # DC Protocol: Achievement requires BOTH sufficient matching pairs AND universal eligibility
        # (aligned with award_service/management page structure)
        # 
        # OCTOBER 21 RESET FIX: For pre-Oct 21 users, ONLY use dynamic calculation
        # Database records from before reset are stale and should be ignored
        dynamically_achieved = (effective_matching_for_achievement >= tier.cumulative_required) and is_eligible_for_awards
        
        # Determine if we applied reset filter (same logic as direct awards)
        reset_filter_applied = user_activation_date and user_activation_date < AWARDS_RESET_DATE
        
        if reset_filter_applied:
            achieved = dynamically_achieved
        else:
            database_achieved = (existing is not None 
                                and existing.achievement_date is not None
                                and hasattr(existing, 'effective_matching_count')
                                and existing.effective_matching_count >= tier.cumulative_required
                                and is_eligible_for_awards)
            achieved = dynamically_achieved or database_achieved
        
        # DISPLAY PROGRESS: Calculate using effective pairs after deductions
        incremental_display = max(0, effective_matching_for_display - previous_cumulative)
        display_progress = min(incremental_display, tier.match_count)
        
        progress_data.append({
            "tier_info": {
                "id": tier.id,
                "required_matching_pairs": tier.match_count,
                "cumulative_required": tier.cumulative_required,
                "rank_name": tier.award_name,
                "award_item": tier.award_description,
                "achievement_bonus": float(tier.actual_price) if tier.actual_price else 0
            },
            "current_matching_count": display_progress,
            "lifetime_matching_count": lifetime_matching_display,
            "effective_remaining": effective_matching_for_display,
            "bonanza_deductions": total_bonanza_deductions,
            "bonanza_details": bonanza_deduction_data.get('deduction_details', []),
            "achieved": achieved,  # Hybrid: dynamic OR database record
            "achievement_date": existing.achievement_date.isoformat() if existing and existing.achievement_date else None,
            # DC PROTOCOL: Status only applies to ACHIEVED awards
            # Non-achieved awards must always show "Pending" regardless of DB processed_status
            "processed_status": (existing.processed_status if existing else "Pending") if achieved else "Pending",
            "simplified_status": _simplify_status(existing.processed_status if existing else "Pending") if achieved else "Pending",
            "admin_approved_by": existing.admin_approved_by if existing else None,
            "admin_approved_at": existing.admin_approved_at.isoformat() if existing and existing.admin_approved_at else None,
            # DC PROTOCOL: Include delivery tracking fields
            "dispatch_date": existing.dispatch_date.isoformat() if existing and existing.dispatch_date else None,
            "received_date": existing.received_date.isoformat() if existing and existing.received_date else None,
            "delivery_notes": existing.delivery_notes if existing else None,
            # Simplified: single last_updated date (most recent status change)
            # Only show for achieved awards to avoid stale dates from legacy records
            "last_updated": _get_last_updated(existing) if achieved else None
        })
        
        previous_cumulative = tier.cumulative_required
    
    return {
        "success": True,
        "matching_awards": progress_data,
        "user_info": {
            "user_id": user_id,
            "lifetime_matching_count": lifetime_matching_display,  # Display: 0 for old data
            "qualification_met": lifetime_matching_display > 0  # Display: 0 for old data
        }
    }


@router.get("/unified")
async def get_unified_awards(
    award_type: str = None,
    processed_status: str = None,
    user_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC PROTOCOL: Unified awards view - Single source of truth for all award reporting
    Queries unified_awards_view that unions Direct, Matching, and Bonanza awards
    
    Supports filtering by:
    - award_type: 'direct', 'matching', 'bonanza', or None for all
    - processed_status: Any valid status value
    - user_id: Specific user or None for all (admin-only)
    
    Returns unified schema with common procurement/delivery fields
    """
    from sqlalchemy import text
    
    # Build query
    query_parts = ["SELECT * FROM unified_awards_view WHERE 1=1"]
    params = {}
    
    # Filter by award type
    if award_type:
        if award_type not in ['direct', 'matching', 'bonanza']:
            raise HTTPException(status_code=400, detail="Invalid award_type. Must be: direct, matching, or bonanza")
        query_parts.append("AND award_type = :award_type")
        params['award_type'] = award_type
    
    # Filter by processed_status
    if processed_status:
        query_parts.append("AND processed_status = :processed_status")
        params['processed_status'] = processed_status
    
    # Filter by user_id
    if user_id:
        # Validate access
        # DC Protocol: Menu-based access control - any authenticated staff has full access
        if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
            raise HTTPException(status_code=403, detail="Access denied")
        query_parts.append("AND user_id = :user_id")
        params['user_id'] = user_id
    else:
        # No user_id filter - admin-only for security
        # DC Protocol: Menu-based access control - page assignment = full access
        # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
        #     raise HTTPException(status_code=403, detail="Admin access required for global award queries")
        pass
    
    # Add ordering
    query_parts.append("ORDER BY created_at DESC LIMIT 1000")
    
    # Execute query
    final_query = " ".join(query_parts)
    result = db.execute(text(final_query), params)
    
    # Convert to list of dicts
    columns = result.keys()
    awards = []
    for row in result:
        award_dict = dict(zip(columns, row))
        # Convert dates to ISO format for JSON serialization
        for key in ['dispatch_date', 'received_date', 'created_at', 'delivered_at', 'processed_at']:
            if key in award_dict and award_dict[key]:
                award_dict[key] = award_dict[key].isoformat() if hasattr(award_dict[key], 'isoformat') else str(award_dict[key])
        for key in ['admin_approved_at', 'super_admin_decision_at', 'finance_processed_at', 'rvz_action_at']:
            if key in award_dict and award_dict[key]:
                award_dict[key] = award_dict[key].isoformat() if hasattr(award_dict[key], 'isoformat') else str(award_dict[key])
        # Convert numeric fields
        for key in ['budgeted_amount', 'actual_cost_paid', 'cost_variance', 'handling_charges', 'gst_amount', 'tax_amount', 'transport_charges']:
            if key in award_dict and award_dict[key]:
                award_dict[key] = float(award_dict[key])
        awards.append(award_dict)
    
    return {
        "success": True,
        "count": len(awards),
        "awards": awards,
        "filters_applied": {
            "award_type": award_type,
            "processed_status": processed_status,
            "user_id": user_id
        },
        "dc_protocol": {
            "single_source_of_truth": "unified_awards_view",
            "instant_propagation": "View reflects underlying table changes immediately",
            "supported_award_types": ["direct", "matching", "bonanza"]
        }
    }
