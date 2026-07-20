"""
Award Management API Endpoints for FastAPI
Handles Direct Awards, Matching Awards, and Bonanza campaign management
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, require_admin, require_finance_admin
from app.models.user import User
from app.models.awards import DirectAwardTier, MatchingAwardTier
from app.services.award_service import AwardService
from app.services.reference_service import ReferenceService

router = APIRouter()


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


class CreateDirectAwardTier(BaseModel):
    award_name: str
    award_description: str
    referral_count: int
    price_range_from: Optional[float] = None
    price_range_to: Optional[float] = None
    actual_price: Optional[float] = None
    cumulative_required: int = 0


class UpdateDirectAwardTier(BaseModel):
    award_name: Optional[str] = None
    award_description: Optional[str] = None
    referral_count: Optional[int] = None
    price_range_from: Optional[float] = None
    price_range_to: Optional[float] = None
    actual_price: Optional[float] = None
    cumulative_required: Optional[int] = None


class CreateMatchingAwardTier(BaseModel):
    award_name: str
    award_description: str
    match_count: int
    price_range_from: Optional[float] = None
    price_range_to: Optional[float] = None
    actual_price: Optional[float] = None
    cumulative_required: int = 0


class UpdateMatchingAwardTier(BaseModel):
    award_name: Optional[str] = None
    award_description: Optional[str] = None
    match_count: Optional[int] = None
    price_range_from: Optional[float] = None
    price_range_to: Optional[float] = None
    actual_price: Optional[float] = None
    cumulative_required: Optional[int] = None

@router.get("/user/{user_id}/direct-awards")
async def get_user_direct_awards(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's direct award progression and achievements - OPTIMIZED VERSION
    Uses fast queries without recursive tree traversal
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    award_service = AwardService(db)
    
    # Use version that bypasses slow recursive queries
    direct_progress = award_service.get_user_direct_award_progress(user_id)
    
    if "error" in direct_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=direct_progress["error"]
        )
    
    return {
        "success": True,
        "direct_awards": direct_progress.get("tier_progress", []),
        "user_info": {
            "user_id": direct_progress.get("user_id"),
            "current_direct_referrals": direct_progress.get("current_direct_referrals", 0)
        }
    }

@router.get("/user/{user_id}/matching-awards")
async def get_user_matching_awards(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's matching award progression - OPTIMIZED VERSION
    Uses fast queries for instant loading
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    award_service = AwardService(db)
    
    # Use version for instant loading
    matching_progress = award_service.get_user_matching_award_progress(user_id)
    
    if "error" in matching_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=matching_progress["error"]
        )
    
    return {
        "success": True,
        "matching_awards": matching_progress.get("tier_progress", []),
        "user_info": {
            "user_id": matching_progress.get("user_id"),
            "lifetime_matching_count": matching_progress.get("lifetime_matching_count", 0),
            "qualification_met": matching_progress.get("qualification_met", False)
        }
    }

@router.post("/user/{user_id}/update-award-progress")
async def update_user_award_progress(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update user's award progress and process new achievements
    Admin-only functionality preserving Flask award processing
    """
    award_service = AwardService(db)
    
    # Update direct award progress
    progress_result = award_service.update_direct_award_progress(user_id)
    
    if "error" in progress_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=progress_result["error"]
        )
    
    return {
        "success": True,
        "update_result": progress_result,
        "updated_by": current_user.id
    }

@router.get("/awards/direct-tiers")
async def get_direct_award_tiers(
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all available direct award tiers
    Public information for all authenticated users
    """
    award_service = AwardService(db)
    
    # Get direct award tiers
    tiers = award_service.get_direct_award_tiers()
    
    return {
        "success": True,
        "direct_award_tiers": tiers
    }

@router.get("/awards/matching-tiers")
async def get_matching_award_tiers(
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all available matching award tiers
    Public information for all authenticated users
    """
    award_service = AwardService(db)
    
    # Get matching award tiers
    tiers = award_service.get_matching_award_tiers()
    
    return {
        "success": True,
        "matching_award_tiers": tiers
    }

@router.get("/bonanza/active")
async def get_active_bonanzas(
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all active bonanza campaigns
    Public information for all authenticated users
    """
    award_service = AwardService(db)
    
    # Get active bonanzas
    active_bonanzas = award_service.get_active_bonanzas()
    
    return {
        "success": True,
        "active_bonanzas": active_bonanzas,
        "campaign_count": len(active_bonanzas)
    }

@router.get("/bonanza/{bonanza_id}/user/{user_id}")
async def get_user_bonanza_progress(
    bonanza_id: int,
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's progress in specific bonanza campaign
    Preserves Flask bonanza participation tracking
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    award_service = AwardService(db)
    
    # Get bonanza progress
    progress = award_service.get_user_bonanza_progress(user_id, bonanza_id)
    
    if "error" in progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=progress["error"]
        )
    
    return {
        "success": True,
        "bonanza_progress": progress
    }

@router.get("/admin/award-analytics")
async def get_award_analytics(
    audience: Optional[str] = Query(None, regex="^(mnr|vgk4u|both)$"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive award analytics for admin dashboard.
    DC Protocol (Task #33): audience param OPTIONAL — when omitted, response
    is identical to the pre-Task-#33 contract.

    [DC_T33_SHARED_DATA_001] VGK4U uses the SAME UserAwardProgress and
    UserMatchingAwardProgress tables as MNR (see exploration: distinction
    is by referral activation date, not by separate storage). The
    audience='vgk4u' / 'both' branches therefore fall through to the same
    real query path. The audience tab in the UI controls labelling and
    company-scoped row visibility; the underlying data shape is identical.
    """
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from sqlalchemy import func, case

    # Get direct award statistics
    direct_stats = db.query(
        UserAwardProgress.award_tier_id,
        func.count(UserAwardProgress.id).label('total_users'),
        func.sum(case((UserAwardProgress.achievement_date.isnot(None), 1), else_=0)).label('achieved_users')
    ).group_by(UserAwardProgress.award_tier_id).all()
    
    # Get matching award statistics
    matching_stats = db.query(
        UserMatchingAwardProgress.matching_award_tier_id,
        func.count(UserMatchingAwardProgress.id).label('total_users'),
        func.sum(case((UserMatchingAwardProgress.achievement_date.isnot(None), 1), else_=0)).label('achieved_users')
    ).group_by(UserMatchingAwardProgress.matching_award_tier_id).all()
    
    # Format statistics
    direct_analytics = []
    for stat in direct_stats:
        direct_analytics.append({
            "tier_id": stat.award_tier_id,
            "total_users": stat.total_users,
            "achieved_users": stat.achieved_users,
            "achievement_rate": (stat.achieved_users / stat.total_users * 100) if stat.total_users > 0 else 0
        })
    
    matching_analytics = []
    for stat in matching_stats:
        matching_analytics.append({
            "tier_id": stat.matching_award_tier_id,
            "total_users": stat.total_users,
            "achieved_users": stat.achieved_users,
            "achievement_rate": (stat.achieved_users / stat.total_users * 100) if stat.total_users > 0 else 0
        })
    
    return {
        "success": True,
        "award_analytics": {
            "direct_awards": direct_analytics,
            "matching_awards": matching_analytics,
            "total_direct_achievements": sum(stat["achieved_users"] for stat in direct_analytics),
            "total_matching_achievements": sum(stat["achieved_users"] for stat in matching_analytics)
        }
    }

@router.get("/admin/bonanza-management")
async def get_bonanza_management_data(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get bonanza management data for admin panel
    Admin-only functionality
    """
    from app.models.bonanza import DynamicBonanza, DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
    from sqlalchemy import func, desc
    
    # Get all bonanzas with statistics
    bonanzas = db.query(DynamicBonanza).order_by(desc(DynamicBonanza.created_at)).limit(20).all()
    
    bonanza_list = []
    for bonanza in bonanzas:
        # DC Protocol: Get participation statistics from DynamicBonanzaHistory
        participation_stats = db.query(
            func.count(DynamicBonanzaHistory.id).label('total_participants'),
            func.count(DynamicBonanzaHistory.id).filter(DynamicBonanzaHistory.campaign_completed == True).label('completed_participants'),
            func.sum(DynamicBonanzaHistory.reward_value_claimed).label('total_rewards')
        ).filter(DynamicBonanzaHistory.bonanza_id == bonanza.id).first()
        
        bonanza_data = {
            "id": bonanza.id,
            "campaign_name": bonanza.campaign_name,
            "campaign_code": bonanza.campaign_code,
            "status": bonanza.status,
            "start_date": bonanza.start_date.isoformat(),
            "end_date": bonanza.end_date.isoformat(),
            "total_reward_pool": float(bonanza.total_reward_pool),
            "created_by": bonanza.created_by_id,
            "statistics": {
                "total_participants": participation_stats.total_participants if participation_stats else 0,
                "completed_participants": participation_stats.completed_participants if participation_stats else 0,
                "total_rewards_distributed": float(participation_stats.total_rewards) if participation_stats and participation_stats.total_rewards else 0.0
            }
        }
        bonanza_list.append(bonanza_data)
    
    return {
        "success": True,
        "bonanza_management": {
            "bonanzas": bonanza_list,
            "total_campaigns": len(bonanza_list)
        }
    }

@router.get("/leaderboard/direct-awards")
async def get_direct_awards_leaderboard(
    limit: int = Query(default=50, ge=1, le=100, description="Number of top performers to show"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get leaderboard for direct award achievements
    Public leaderboard for motivation
    """
    from app.models.awards import UserAwardProgress
    from app.services.user_service import UserService
    from sqlalchemy import func, desc
    
    user_service = UserService(db)
    
    # Get top performers by total achievement bonuses
    top_performers = db.query(
        UserAwardProgress.user_id,
        func.count(UserAwardProgress.id).filter(UserAwardProgress.achieved == True).label('achievements_count'),
        func.sum(UserAwardProgress.bonus_amount_paid).label('total_bonuses')
    ).filter(
        UserAwardProgress.achieved == True
    ).group_by(
        UserAwardProgress.user_id
    ).order_by(
        desc('achievements_count'),
        desc('total_bonuses')
    ).limit(limit).all()
    
    # Format leaderboard
    leaderboard = []
    for rank, performer in enumerate(top_performers, 1):
        user = user_service.get_user_by_id(performer.user_id)
        if user:
            leaderboard.append({
                "rank": rank,
                "user_id": performer.user_id,
                "user_name": user.name,
                "achievements_count": performer.achievements_count,
                "total_bonuses": float(performer.total_bonuses or 0),
                "user_type": user.user_type
            })
    
    return {
        "success": True,
        "direct_awards_leaderboard": leaderboard,
        "leaderboard_size": len(leaderboard)
    }

@router.get("/leaderboard/matching-awards")
async def get_matching_awards_leaderboard(
    limit: int = Query(default=50, ge=1, le=100, description="Number of top performers to show"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get leaderboard for matching award achievements
    Public leaderboard for motivation
    """
    from app.models.awards import UserMatchingAwardProgress
    from app.services.user_service import UserService
    from sqlalchemy import func, desc
    
    user_service = UserService(db)
    
    # Get top performers by matching achievements
    top_performers = db.query(
        UserMatchingAwardProgress.user_id,
        func.count(UserMatchingAwardProgress.id).filter(UserMatchingAwardProgress.achieved == True).label('achievements_count'),
        func.sum(UserMatchingAwardProgress.total_bonuses_received).label('total_bonuses'),
        func.max(UserMatchingAwardProgress.current_matching_count).label('max_matching_pairs')
    ).filter(
        UserMatchingAwardProgress.achieved == True
    ).group_by(
        UserMatchingAwardProgress.user_id
    ).order_by(
        desc('achievements_count'),
        desc('max_matching_pairs'),
        desc('total_bonuses')
    ).limit(limit).all()
    
    # Format leaderboard
    leaderboard = []
    for rank, performer in enumerate(top_performers, 1):
        user = user_service.get_user_by_id(performer.user_id)
        if user:
            leaderboard.append({
                "rank": rank,
                "user_id": performer.user_id,
                "user_name": user.name,
                "achievements_count": performer.achievements_count,
                "max_matching_pairs": performer.max_matching_pairs,
                "total_bonuses": float(performer.total_bonuses or 0),
                "user_type": user.user_type
            })
    
    return {
        "success": True,
        "matching_awards_leaderboard": leaderboard,
        "leaderboard_size": len(leaderboard)
    }

@router.get("/user/{user_id}/achievement-summary")
async def get_user_achievement_summary(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive achievement summary for user
    Combines direct awards, matching awards, and bonanza achievements
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    award_service = AwardService(db)
    
    # Get comprehensive award summary
    award_summary = award_service.get_user_award_summary(user_id)
    
    if "error" in award_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=award_summary["error"]
        )
    
    return {
        "success": True,
        "achievement_summary": award_summary
    }


@router.post("/admin/awards/direct-tiers")
async def create_direct_award_tier(
    data: CreateDirectAwardTier,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
) -> Dict[str, Any]:
    """
    Create a new direct award tier
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    existing_tier = db.query(DirectAwardTier).filter(
        DirectAwardTier.referral_count == data.referral_count
    ).first()
    
    if existing_tier:
        raise HTTPException(
            status_code=400, 
            detail=f"Direct award tier with {data.referral_count} referrals already exists"
        )
    
    new_tier = DirectAwardTier(
        award_name=data.award_name,
        award_description=data.award_description,
        referral_count=data.referral_count,
        price_range_from=data.price_range_from,
        price_range_to=data.price_range_to,
        actual_price=data.actual_price,
        cumulative_required=data.cumulative_required,
        created_at=datetime.utcnow(),
        last_updated_by=_resolve_actor_id(current_user),
        last_updated_at=datetime.utcnow()
    )
    
    db.add(new_tier)
    db.commit()
    db.refresh(new_tier)
    
    return {
        "success": True,
        "message": f"Direct award tier '{data.award_name}' created successfully",
        "tier_id": new_tier.id
    }


@router.put("/admin/awards/direct-tiers/{tier_id}")
async def update_direct_award_tier(
    tier_id: int,
    data: UpdateDirectAwardTier,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
) -> Dict[str, Any]:
    """
    Update an existing direct award tier
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == tier_id).first()
    
    if not tier:
        raise HTTPException(status_code=404, detail="Direct award tier not found")
    
    if data.referral_count is not None:
        existing_tier = db.query(DirectAwardTier).filter(
            DirectAwardTier.referral_count == data.referral_count,
            DirectAwardTier.id != tier_id
        ).first()
        
        if existing_tier:
            raise HTTPException(
                status_code=400,
                detail=f"Another tier with {data.referral_count} referrals already exists"
            )
        tier.referral_count = data.referral_count
    
    if data.award_name is not None:
        tier.award_name = data.award_name
    if data.award_description is not None:
        tier.award_description = data.award_description
    if data.price_range_from is not None:
        tier.price_range_from = data.price_range_from
    if data.price_range_to is not None:
        tier.price_range_to = data.price_range_to
    if data.actual_price is not None:
        tier.actual_price = data.actual_price
        tier.price_last_updated_at = datetime.utcnow()
        tier.price_last_updated_by = _resolve_actor_id(current_user)
    if data.cumulative_required is not None:
        tier.cumulative_required = data.cumulative_required
    
    tier.last_updated_by = _resolve_actor_id(current_user)
    tier.last_updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tier)
    
    return {
        "success": True,
        "message": f"Direct award tier '{tier.award_name}' updated successfully"
    }


@router.delete("/admin/awards/direct-tiers/{tier_id}")
async def delete_direct_award_tier(
    tier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
) -> Dict[str, Any]:
    """
    Delete a direct award tier
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == tier_id).first()
    
    if not tier:
        raise HTTPException(status_code=404, detail="Direct award tier not found")
    
    tier_name = tier.award_name
    db.delete(tier)
    db.commit()
    
    return {
        "success": True,
        "message": f"Direct award tier '{tier_name}' deleted successfully"
    }


@router.post("/admin/awards/matching-tiers")
async def create_matching_award_tier(
    data: CreateMatchingAwardTier,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
) -> Dict[str, Any]:
    """
    Create a new matching award tier
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    existing_tier = db.query(MatchingAwardTier).filter(
        MatchingAwardTier.match_count == data.match_count
    ).first()
    
    if existing_tier:
        raise HTTPException(
            status_code=400,
            detail=f"Matching award tier with {data.match_count} matches already exists"
        )
    
    new_tier = MatchingAwardTier(
        award_name=data.award_name,
        award_description=data.award_description,
        match_count=data.match_count,
        price_range_from=data.price_range_from,
        price_range_to=data.price_range_to,
        actual_price=data.actual_price,
        cumulative_required=data.cumulative_required,
        created_at=datetime.utcnow(),
        last_updated_by=_resolve_actor_id(current_user),
        last_updated_at=datetime.utcnow()
    )
    
    db.add(new_tier)
    db.commit()
    db.refresh(new_tier)
    
    return {
        "success": True,
        "message": f"Matching award tier '{data.award_name}' created successfully",
        "tier_id": new_tier.id
    }


@router.put("/admin/awards/matching-tiers/{tier_id}")
async def update_matching_award_tier(
    tier_id: int,
    data: UpdateMatchingAwardTier,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
) -> Dict[str, Any]:
    """
    Update an existing matching award tier
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == tier_id).first()
    
    if not tier:
        raise HTTPException(status_code=404, detail="Matching award tier not found")
    
    if data.match_count is not None:
        existing_tier = db.query(MatchingAwardTier).filter(
            MatchingAwardTier.match_count == data.match_count,
            MatchingAwardTier.id != tier_id
        ).first()
        
        if existing_tier:
            raise HTTPException(
                status_code=400,
                detail=f"Another tier with {data.match_count} matches already exists"
            )
        tier.match_count = data.match_count
    
    if data.award_name is not None:
        tier.award_name = data.award_name
    if data.award_description is not None:
        tier.award_description = data.award_description
    if data.price_range_from is not None:
        tier.price_range_from = data.price_range_from
    if data.price_range_to is not None:
        tier.price_range_to = data.price_range_to
    if data.actual_price is not None:
        tier.actual_price = data.actual_price
        tier.price_last_updated_at = datetime.utcnow()
        tier.price_last_updated_by = _resolve_actor_id(current_user)
    if data.cumulative_required is not None:
        tier.cumulative_required = data.cumulative_required
    
    tier.last_updated_by = _resolve_actor_id(current_user)
    tier.last_updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tier)
    
    return {
        "success": True,
        "message": f"Matching award tier '{tier.award_name}' updated successfully"
    }


@router.delete("/admin/awards/matching-tiers/{tier_id}")
async def delete_matching_award_tier(
    tier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
) -> Dict[str, Any]:
    """
    Delete a matching award tier
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == tier_id).first()
    
    if not tier:
        raise HTTPException(status_code=404, detail="Matching award tier not found")
    
    tier_name = tier.award_name
    db.delete(tier)
    db.commit()
    
    return {
        "success": True,
        "message": f"Matching award tier '{tier_name}' deleted successfully"
    }