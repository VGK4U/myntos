"""
RVZ Awards Configuration API - Master Data Management
DC Protocol Compliant: Single source of truth for award/bonanza definitions
Manages: Direct Award Tiers, Matching Award Tiers, Bonanza Campaigns
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import logging

from app.core.database import get_db
from app.core.security import get_current_rvz_user_hybrid
from app.models.awards import DirectAwardTier, MatchingAwardTier, UserAwardProgress, UserMatchingAwardProgress
from app.models.bonanza import Bonanza  # DC Protocol: BonanzaProgress deprecated
from app.models.user import User
from app.models.base import get_indian_time
from app.constants.award_statuses import AwardStatus

logger = logging.getLogger(__name__)

PRODUCTION_START_DATE = date(2025, 10, 21)


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)

router = APIRouter(prefix="/rvz/awards-config", tags=["RVZ Awards Configuration"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DirectAwardTierUpdate(BaseModel):
    award_name: Optional[str] = None
    award_description: Optional[str] = None
    price_range_from: Optional[Decimal] = None
    price_range_to: Optional[Decimal] = None
    actual_price: Optional[Decimal] = None
    cumulative_required: Optional[int] = None
    required_count: Optional[int] = None
    update_reason: Optional[str] = None  # Audit trail


class MatchingAwardTierUpdate(BaseModel):
    award_name: Optional[str] = None
    award_description: Optional[str] = None
    price_range_from: Optional[Decimal] = None
    price_range_to: Optional[Decimal] = None
    actual_price: Optional[Decimal] = None
    cumulative_required: Optional[int] = None
    required_count: Optional[int] = None
    update_reason: Optional[str] = None


class BonanzaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    start_date: datetime
    end_date: datetime
    criteria_type: str = Field(..., pattern="^(direct_referral|matching_points)$")
    target_requirement: int = Field(..., gt=0)
    reward_type: str = Field(..., pattern="^(cash|bonus|award|gift)$")
    reward_amount: Optional[Decimal] = None
    reward_text: Optional[str] = None
    award_name: Optional[str] = None
    is_monetary: bool = True
    total_budget: Optional[Decimal] = None
    max_winners: int = Field(default=50, gt=0)
    price_range_from: Optional[Decimal] = None
    price_range_to: Optional[Decimal] = None
    actual_price: Optional[Decimal] = None
    linked_award_type: Optional[str] = None
    linked_award_tier_id: Optional[int] = None
    reduced_target: Optional[int] = None
    counts_towards_regular: bool = False
    consume_achievements: bool = False


class BonanzaUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    criteria_type: Optional[str] = None
    target_requirement: Optional[int] = None
    reward_type: Optional[str] = None
    reward_amount: Optional[Decimal] = None
    reward_text: Optional[str] = None
    award_name: Optional[str] = None
    is_monetary: Optional[bool] = None
    total_budget: Optional[Decimal] = None
    max_winners: Optional[int] = None
    price_range_from: Optional[Decimal] = None
    price_range_to: Optional[Decimal] = None
    actual_price: Optional[Decimal] = None
    linked_award_type: Optional[str] = None
    linked_award_tier_id: Optional[int] = None
    reduced_target: Optional[int] = None
    counts_towards_regular: Optional[bool] = None
    consume_achievements: Optional[bool] = None
    status: Optional[str] = None
    update_reason: Optional[str] = None


# ============================================================================
# DIRECT AWARD TIERS ENDPOINTS
# ============================================================================

@router.get("/direct-tiers")
async def list_direct_award_tiers(
    user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    price_min: Optional[Decimal] = Query(None),
    price_max: Optional[Decimal] = Query(None),
    sort_by: str = Query("cumulative_required", pattern="^(cumulative_required|referral_count|actual_price|award_name|id)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    List all Direct Award Tiers with dynamic filters
    RVZ ID access only
    """
    try:
        # Build query with filters
        query = db.query(DirectAwardTier)
        
        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    DirectAwardTier.award_name.ilike(search_term),
                    DirectAwardTier.award_description.ilike(search_term)
                )
            )
        
        # Price range filters
        if price_min is not None:
            query = query.filter(DirectAwardTier.actual_price >= price_min)
        if price_max is not None:
            query = query.filter(DirectAwardTier.actual_price <= price_max)
        
        # Total count
        total_count = query.count()
        
        # Sorting
        sort_column = getattr(DirectAwardTier, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        offset = (page - 1) * page_size
        tiers = query.offset(offset).limit(page_size).all()
        
        achievers_counts = {}
        pending_counts = {}
        completed_counts = {}
        post_reset_filter = or_(
            UserAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            and_(
                UserAwardProgress.achievement_date.is_(None),
                UserAwardProgress.processed_status != 'Pending'
            )
        )
        non_pending_filter = UserAwardProgress.processed_status != 'Pending'
        for tier in tiers:
            tier_base = and_(
                UserAwardProgress.award_tier_id == tier.id,
                post_reset_filter,
                non_pending_filter
            )

            achievers_count = db.query(func.count(func.distinct(UserAwardProgress.user_id)))\
                .filter(tier_base)\
                .scalar() or 0
            achievers_counts[tier.id] = achievers_count

            completed_count = db.query(func.count(func.distinct(UserAwardProgress.user_id)))\
                .filter(
                    tier_base,
                    UserAwardProgress.processed_status == AwardStatus.DELIVERED.value
                )\
                .scalar() or 0
            completed_counts[tier.id] = completed_count

            pending_not_delivered = db.query(func.count(func.distinct(UserAwardProgress.user_id)))\
                .filter(
                    tier_base,
                    UserAwardProgress.processed_status != AwardStatus.DELIVERED.value,
                    UserAwardProgress.processed_status != AwardStatus.REJECTED.value
                )\
                .scalar() or 0
            pending_counts[tier.id] = pending_not_delivered
        
        # Format response
        tiers_data = []
        for tier in tiers:
            tiers_data.append({
                "id": tier.id,
                "referral_count": tier.referral_count,
                "award_name": tier.award_name,
                "award_description": tier.award_description,
                "award_item_name": tier.award_description,  # Item name (Smart Watch, Fridge, etc.)
                "achievers_count": achievers_counts.get(tier.id, 0),
                "pending_count": pending_counts.get(tier.id, 0),
                "completed_count": completed_counts.get(tier.id, 0),
                "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                "actual_price": float(tier.actual_price) if tier.actual_price else None,
                "cumulative_required": tier.cumulative_required,
                "price_last_updated_at": tier.price_last_updated_at.isoformat() if tier.price_last_updated_at else None,
                "price_last_updated_by": tier.price_last_updated_by,
                "last_updated_by": tier.last_updated_by,
                "last_updated_at": tier.last_updated_at.isoformat() if tier.last_updated_at else None,
                "created_at": tier.created_at.isoformat() if tier.created_at else None
            })
        
        return JSONResponse({
            "success": True,
            "data": tiers_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing direct award tiers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/direct-tiers/{tier_id}")
async def get_direct_award_tier(
    tier_id: int,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """Get single Direct Award Tier details"""
    try:
        tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == tier_id).first()
        if not tier:
            raise HTTPException(status_code=404, detail="Direct Award Tier not found")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": tier.id,
                "referral_count": tier.referral_count,
                "award_name": tier.award_name,
                "award_description": tier.award_description,
                "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                "actual_price": float(tier.actual_price) if tier.actual_price else None,
                "cumulative_required": tier.cumulative_required,
                "price_last_updated_at": tier.price_last_updated_at.isoformat() if tier.price_last_updated_at else None,
                "price_last_updated_by": tier.price_last_updated_by,
                "last_updated_by": tier.last_updated_by,
                "last_updated_at": tier.last_updated_at.isoformat() if tier.last_updated_at else None,
                "created_at": tier.created_at.isoformat() if tier.created_at else None
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting direct award tier: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/direct-tiers/{tier_id}")
async def update_direct_award_tier(
    tier_id: int,
    update_data: DirectAwardTierUpdate,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Update Direct Award Tier with cascade logic.
    When a tier's required_count changes, all subsequent tiers' cumulative values shift accordingly.
    """
    try:
        tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == tier_id).first()
        if not tier:
            raise HTTPException(status_code=404, detail="Direct Award Tier not found")

        achieved_count = db.query(func.count(UserAwardProgress.id)).filter(
            UserAwardProgress.award_tier_id == tier_id,
            UserAwardProgress.status == 'Achieved'
        ).scalar() or 0

        price_changed = False
        old_price = tier.actual_price

        if update_data.award_name is not None:
            tier.award_name = update_data.award_name
        if update_data.award_description is not None:
            tier.award_description = update_data.award_description
        if update_data.price_range_from is not None:
            tier.price_range_from = update_data.price_range_from
        if update_data.price_range_to is not None:
            tier.price_range_to = update_data.price_range_to

        if tier.price_range_to is not None:
            calculated_price = tier.price_range_to
            if calculated_price != tier.actual_price:
                price_changed = True
                tier.actual_price = calculated_price
                tier.price_last_updated_at = get_indian_time()
                tier.price_last_updated_by = _resolve_actor_id(current_user)

        old_cumulative = tier.cumulative_required
        cumulative_diff = 0

        if update_data.cumulative_required is not None and update_data.cumulative_required != old_cumulative:
            if update_data.cumulative_required < 1:
                raise HTTPException(status_code=400, detail="Cumulative required must be at least 1")
            cumulative_diff = update_data.cumulative_required - old_cumulative
            tier.cumulative_required = update_data.cumulative_required

            subsequent_tiers = db.query(DirectAwardTier).filter(
                DirectAwardTier.id != tier_id,
                DirectAwardTier.cumulative_required > old_cumulative
            ).all()
            for st in subsequent_tiers:
                new_cum = st.cumulative_required + cumulative_diff
                if new_cum < 1:
                    new_cum = 1
                st.cumulative_required = new_cum

        tier.last_updated_by = current_user.id
        tier.last_updated_at = get_indian_time()
        db.flush()

        all_tiers = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required.asc()).all()
        prev_cumulative = 0
        for t in all_tiers:
            direct_val = t.cumulative_required - prev_cumulative
            if direct_val < 1:
                direct_val = 1
            t.referral_count = direct_val
            prev_cumulative = t.cumulative_required

        db.commit()
        db.refresh(tier)

        cascaded_tiers = []
        if cumulative_diff != 0:
            refreshed = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required.asc()).all()
            for rt in refreshed:
                cascaded_tiers.append({
                    "id": rt.id,
                    "award_name": rt.award_name,
                    "referral_count": rt.referral_count,
                    "cumulative_required": rt.cumulative_required
                })

        logger.info(f"Direct Award Tier {tier_id} updated by RVZ {current_user.id}. Price changed: {price_changed} (₹{old_price} → ₹{tier.actual_price}). Cascade diff: {cumulative_diff}. Achieved users: {achieved_count}. Reason: {update_data.update_reason or 'Not provided'}")

        return JSONResponse({
            "success": True,
            "message": "Direct Award Tier updated successfully" + (f" (cascade applied to {len(cascaded_tiers)-1} subsequent tiers)" if cumulative_diff != 0 else ""),
            "price_changed": price_changed,
            "old_price": float(old_price) if old_price else None,
            "new_price": float(tier.actual_price) if tier.actual_price else None,
            "achieved_count": achieved_count,
            "cascade_applied": cumulative_diff != 0,
            "cascaded_tiers": cascaded_tiers,
            "data": {
                "id": tier.id,
                "award_name": tier.award_name,
                "referral_count": tier.referral_count,
                "cumulative_required": tier.cumulative_required,
                "actual_price": float(tier.actual_price) if tier.actual_price else None
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating direct award tier: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MATCHING AWARD TIERS ENDPOINTS
# ============================================================================

@router.get("/matching-tiers")
async def list_matching_award_tiers(
    user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    price_min: Optional[Decimal] = Query(None),
    price_max: Optional[Decimal] = Query(None),
    sort_by: str = Query("cumulative_required", pattern="^(cumulative_required|match_count|actual_price|award_name|id)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    List all Matching Award Tiers with dynamic filters
    RVZ ID access only
    """
    try:
        # Build query with filters
        query = db.query(MatchingAwardTier)
        
        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    MatchingAwardTier.award_name.ilike(search_term),
                    MatchingAwardTier.award_description.ilike(search_term)
                )
            )
        
        # Price range filters
        if price_min is not None:
            query = query.filter(MatchingAwardTier.actual_price >= price_min)
        if price_max is not None:
            query = query.filter(MatchingAwardTier.actual_price <= price_max)
        
        # Total count
        total_count = query.count()
        
        # Sorting
        sort_column = getattr(MatchingAwardTier, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        offset = (page - 1) * page_size
        tiers = query.offset(offset).limit(page_size).all()
        
        achievers_counts = {}
        pending_counts = {}
        completed_counts = {}
        post_reset_filter = or_(
            UserMatchingAwardProgress.achievement_date >= PRODUCTION_START_DATE,
            and_(
                UserMatchingAwardProgress.achievement_date.is_(None),
                UserMatchingAwardProgress.processed_status != 'Pending'
            )
        )
        non_pending_filter = UserMatchingAwardProgress.processed_status != 'Pending'
        for tier in tiers:
            tier_base = and_(
                UserMatchingAwardProgress.matching_award_tier_id == tier.id,
                post_reset_filter,
                non_pending_filter
            )

            achievers_count = db.query(func.count(func.distinct(UserMatchingAwardProgress.user_id)))\
                .filter(tier_base)\
                .scalar() or 0
            achievers_counts[tier.id] = achievers_count

            completed_count = db.query(func.count(func.distinct(UserMatchingAwardProgress.user_id)))\
                .filter(
                    tier_base,
                    UserMatchingAwardProgress.processed_status == AwardStatus.DELIVERED.value
                )\
                .scalar() or 0
            completed_counts[tier.id] = completed_count

            pending_not_delivered = db.query(func.count(func.distinct(UserMatchingAwardProgress.user_id)))\
                .filter(
                    tier_base,
                    UserMatchingAwardProgress.processed_status != AwardStatus.DELIVERED.value,
                    UserMatchingAwardProgress.processed_status != AwardStatus.REJECTED.value
                )\
                .scalar() or 0
            pending_counts[tier.id] = pending_not_delivered
        
        # Format response
        tiers_data = []
        for tier in tiers:
            tiers_data.append({
                "id": tier.id,
                "match_count": tier.match_count,
                "award_name": tier.award_name,
                "award_description": tier.award_description,
                "award_item_name": tier.award_description,  # Item name (Smart Watch, Fridge, etc.)
                "achievers_count": achievers_counts.get(tier.id, 0),
                "pending_count": pending_counts.get(tier.id, 0),
                "completed_count": completed_counts.get(tier.id, 0),
                "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                "actual_price": float(tier.actual_price) if tier.actual_price else None,
                "cumulative_required": tier.cumulative_required,
                "price_last_updated_at": tier.price_last_updated_at.isoformat() if tier.price_last_updated_at else None,
                "price_last_updated_by": tier.price_last_updated_by,
                "last_updated_by": tier.last_updated_by,
                "last_updated_at": tier.last_updated_at.isoformat() if tier.last_updated_at else None,
                "created_at": tier.created_at.isoformat() if tier.created_at else None
            })
        
        return JSONResponse({
            "success": True,
            "data": tiers_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing matching award tiers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matching-tiers/{tier_id}")
async def get_matching_award_tier(
    tier_id: int,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """Get single Matching Award Tier details"""
    try:
        tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == tier_id).first()
        if not tier:
            raise HTTPException(status_code=404, detail="Matching Award Tier not found")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": tier.id,
                "match_count": tier.match_count,
                "award_name": tier.award_name,
                "award_description": tier.award_description,
                "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                "actual_price": float(tier.actual_price) if tier.actual_price else None,
                "cumulative_required": tier.cumulative_required,
                "price_last_updated_at": tier.price_last_updated_at.isoformat() if tier.price_last_updated_at else None,
                "price_last_updated_by": tier.price_last_updated_by,
                "last_updated_by": tier.last_updated_by,
                "last_updated_at": tier.last_updated_at.isoformat() if tier.last_updated_at else None,
                "created_at": tier.created_at.isoformat() if tier.created_at else None
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting matching award tier: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/matching-tiers/{tier_id}")
async def update_matching_award_tier(
    tier_id: int,
    update_data: MatchingAwardTierUpdate,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Update Matching Award Tier with cascade logic.
    When a tier's required_count changes, all subsequent tiers' cumulative values shift accordingly.
    """
    try:
        tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == tier_id).first()
        if not tier:
            raise HTTPException(status_code=404, detail="Matching Award Tier not found")

        achieved_count = db.query(func.count(UserMatchingAwardProgress.id)).filter(
            UserMatchingAwardProgress.matching_award_tier_id == tier_id,
            UserMatchingAwardProgress.status == 'Achieved'
        ).scalar() or 0

        price_changed = False
        old_price = tier.actual_price

        if update_data.award_name is not None:
            tier.award_name = update_data.award_name
        if update_data.award_description is not None:
            tier.award_description = update_data.award_description
        if update_data.price_range_from is not None:
            tier.price_range_from = update_data.price_range_from
        if update_data.price_range_to is not None:
            tier.price_range_to = update_data.price_range_to

        if tier.price_range_to is not None:
            calculated_price = tier.price_range_to
            if calculated_price != tier.actual_price:
                price_changed = True
                tier.actual_price = calculated_price
                tier.price_last_updated_at = get_indian_time()
                tier.price_last_updated_by = _resolve_actor_id(current_user)

        old_cumulative = tier.cumulative_required
        cumulative_diff = 0

        if update_data.cumulative_required is not None and update_data.cumulative_required != old_cumulative:
            if update_data.cumulative_required < 1:
                raise HTTPException(status_code=400, detail="Cumulative required must be at least 1")
            cumulative_diff = update_data.cumulative_required - old_cumulative
            tier.cumulative_required = update_data.cumulative_required

            subsequent_tiers = db.query(MatchingAwardTier).filter(
                MatchingAwardTier.id != tier_id,
                MatchingAwardTier.cumulative_required > old_cumulative
            ).all()
            for st in subsequent_tiers:
                new_cum = st.cumulative_required + cumulative_diff
                if new_cum < 1:
                    new_cum = 1
                st.cumulative_required = new_cum

        tier.last_updated_by = current_user.id
        tier.last_updated_at = get_indian_time()
        db.flush()

        all_tiers = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required.asc()).all()
        prev_cumulative = 0
        for t in all_tiers:
            direct_val = t.cumulative_required - prev_cumulative
            if direct_val < 1:
                direct_val = 1
            t.match_count = direct_val
            prev_cumulative = t.cumulative_required

        db.commit()
        db.refresh(tier)

        cascaded_tiers = []
        if cumulative_diff != 0:
            refreshed = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required.asc()).all()
            for rt in refreshed:
                cascaded_tiers.append({
                    "id": rt.id,
                    "award_name": rt.award_name,
                    "match_count": rt.match_count,
                    "cumulative_required": rt.cumulative_required
                })

        logger.info(f"Matching Award Tier {tier_id} updated by RVZ {current_user.id}. Price changed: {price_changed} (₹{old_price} → ₹{tier.actual_price}). Cascade diff: {cumulative_diff}. Achieved users: {achieved_count}. Reason: {update_data.update_reason or 'Not provided'}")

        return JSONResponse({
            "success": True,
            "message": "Matching Award Tier updated successfully" + (f" (cascade applied to {len(cascaded_tiers)-1} subsequent tiers)" if cumulative_diff != 0 else ""),
            "price_changed": price_changed,
            "old_price": float(old_price) if old_price else None,
            "new_price": float(tier.actual_price) if tier.actual_price else None,
            "achieved_count": achieved_count,
            "cascade_applied": cumulative_diff != 0,
            "cascaded_tiers": cascaded_tiers,
            "data": {
                "id": tier.id,
                "award_name": tier.award_name,
                "match_count": tier.match_count,
                "cumulative_required": tier.cumulative_required,
                "actual_price": float(tier.actual_price) if tier.actual_price else None
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating matching award tier: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BONANZA ENDPOINTS
# ============================================================================

@router.get("/bonanzas")
async def list_bonanzas(
    user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    reward_type: Optional[str] = Query(None),
    start_date_from: Optional[date] = Query(None),
    start_date_to: Optional[date] = Query(None),
    price_min: Optional[Decimal] = Query(None),
    price_max: Optional[Decimal] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|start_date|name|actual_price|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    List all Bonanzas with dynamic filters
    RVZ ID access only - excludes soft-deleted bonanzas
    """
    try:
        # Build query with filters
        query = db.query(Bonanza).filter(Bonanza.is_deleted == False)
        
        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Bonanza.name.ilike(search_term),
                    Bonanza.reward_text.ilike(search_term),
                    Bonanza.award_name.ilike(search_term)
                )
            )
        
        # Status filter
        if status:
            query = query.filter(Bonanza.status == status)
        
        # Reward type filter
        if reward_type:
            query = query.filter(Bonanza.reward_type == reward_type)
        
        # Date range filters
        if start_date_from:
            query = query.filter(Bonanza.start_date >= start_date_from)
        if start_date_to:
            query = query.filter(Bonanza.start_date <= start_date_to)
        
        # Price range filters
        if price_min is not None:
            query = query.filter(Bonanza.actual_price >= price_min)
        if price_max is not None:
            query = query.filter(Bonanza.actual_price <= price_max)
        
        # Total count
        total_count = query.count()
        
        # Sorting
        sort_column = getattr(Bonanza, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        offset = (page - 1) * page_size
        bonanzas = query.offset(offset).limit(page_size).all()
        
        # DC Protocol: Get achievers count from DynamicBonanzaHistory (single source of truth)
        from app.models.bonanza import DynamicBonanzaHistory
        achievers_counts = {}
        for bonanza in bonanzas:
            achievers_count = db.query(func.count(func.distinct(DynamicBonanzaHistory.user_id)))\
                .filter(
                    DynamicBonanzaHistory.bonanza_id == bonanza.id,
                    DynamicBonanzaHistory.processed_status.in_(['Processed for Dispatch', 'Delivered'])
                )\
                .scalar() or 0
            achievers_counts[bonanza.id] = achievers_count
        
        # Format response
        bonanzas_data = []
        current_date = get_indian_time().date()
        
        for bonanza in bonanzas:
            # DC Protocol: Calculate date-based display status
            # RVZ Supreme Authority: bonanza.status = 'Approved' (internal)
            # Display status: Based on date comparison (In Progress/Lapsed/Future)
            if bonanza.start_date and bonanza.end_date:
                # Convert datetime to date for comparison (handle both date and datetime types)
                start_date = bonanza.start_date.date() if hasattr(bonanza.start_date, 'date') else bonanza.start_date
                end_date = bonanza.end_date.date() if hasattr(bonanza.end_date, 'date') else bonanza.end_date
                
                if current_date < start_date:
                    display_status = "Future"
                elif start_date <= current_date <= end_date:
                    display_status = "In Progress"
                else:  # current_date > end_date
                    display_status = "Lapsed"
            else:
                display_status = bonanza.status  # Fallback to DB status if dates missing
            
            bonanzas_data.append({
                "id": bonanza.id,
                "name": bonanza.name,
                "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
                "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
                "criteria_type": bonanza.criteria_type,
                "target_requirement": bonanza.target_requirement,
                "reward_type": bonanza.reward_type,
                "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
                "reward_text": bonanza.reward_text,
                "award_name": bonanza.award_name,
                "is_monetary": bonanza.is_monetary,
                "status": display_status,  # Date-based display status
                "approval_status": bonanza.status,  # Internal approval status (Approved by RVZ)
                "total_budget": float(bonanza.total_budget) if bonanza.total_budget else None,
                "current_spending": float(bonanza.current_spending) if bonanza.current_spending else None,
                "max_winners": bonanza.max_winners,
                "current_winners": bonanza.current_winners,
                "achievers_count": achievers_counts.get(bonanza.id, 0),
                "price_range_from": float(bonanza.price_range_from) if bonanza.price_range_from else None,
                "price_range_to": float(bonanza.price_range_to) if bonanza.price_range_to else None,
                "actual_price": float(bonanza.actual_price) if bonanza.actual_price else None,
                "linked_award_type": bonanza.linked_award_type,
                "linked_award_tier_id": bonanza.linked_award_tier_id,
                "reduced_target": bonanza.reduced_target,
                "created_at": bonanza.created_at.isoformat() if bonanza.created_at else None,
                "created_by": bonanza.created_by,
                "approved_by": bonanza.approved_by,
                "approved_date": bonanza.approved_date.isoformat() if bonanza.approved_date else None
            })
        
        return JSONResponse({
            "success": True,
            "data": bonanzas_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing bonanzas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bonanzas/{bonanza_id}")
async def get_bonanza(
    bonanza_id: int,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """Get single Bonanza details"""
    try:
        bonanza = db.query(Bonanza).filter(
            Bonanza.id == bonanza_id,
            Bonanza.is_deleted == False
        ).first()
        
        if not bonanza:
            raise HTTPException(status_code=404, detail="Bonanza not found")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": bonanza.id,
                "name": bonanza.name,
                "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
                "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
                "criteria_type": bonanza.criteria_type,
                "target_requirement": bonanza.target_requirement,
                "reward_type": bonanza.reward_type,
                "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
                "reward_text": bonanza.reward_text,
                "award_name": bonanza.award_name,
                "is_monetary": bonanza.is_monetary,
                "status": bonanza.status,
                "total_budget": float(bonanza.total_budget) if bonanza.total_budget else None,
                "current_spending": float(bonanza.current_spending) if bonanza.current_spending else None,
                "max_winners": bonanza.max_winners,
                "current_winners": bonanza.current_winners,
                "price_range_from": float(bonanza.price_range_from) if bonanza.price_range_from else None,
                "price_range_to": float(bonanza.price_range_to) if bonanza.price_range_to else None,
                "actual_price": float(bonanza.actual_price) if bonanza.actual_price else None,
                "linked_award_type": bonanza.linked_award_type,
                "linked_award_tier_id": bonanza.linked_award_tier_id,
                "reduced_target": bonanza.reduced_target,
                "counts_towards_regular": bonanza.counts_towards_regular,
                "consume_achievements": bonanza.consume_achievements,
                "created_at": bonanza.created_at.isoformat() if bonanza.created_at else None,
                "created_by": bonanza.created_by,
                "approved_by": bonanza.approved_by,
                "approved_date": bonanza.approved_date.isoformat() if bonanza.approved_date else None,
                "updated_at": bonanza.updated_at.isoformat() if bonanza.updated_at else None
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bonanza: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bonanzas")
async def create_bonanza(
    bonanza_data: BonanzaCreate,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Create new Bonanza campaign
    RVZ ID only
    """
    try:
        # Validate linked award if specified
        if bonanza_data.linked_award_tier_id:
            if bonanza_data.linked_award_type == "direct":
                award_exists = db.query(DirectAwardTier).filter(
                    DirectAwardTier.id == bonanza_data.linked_award_tier_id
                ).first()
                if not award_exists:
                    raise HTTPException(status_code=400, detail="Linked direct award tier not found")
            elif bonanza_data.linked_award_type == "matching":
                award_exists = db.query(MatchingAwardTier).filter(
                    MatchingAwardTier.id == bonanza_data.linked_award_tier_id
                ).first()
                if not award_exists:
                    raise HTTPException(status_code=400, detail="Linked matching award tier not found")
        
        # Create bonanza
        new_bonanza = Bonanza(
            name=bonanza_data.name,
            start_date=bonanza_data.start_date,
            end_date=bonanza_data.end_date,
            criteria_type=bonanza_data.criteria_type,
            target_requirement=bonanza_data.target_requirement,
            reward_type=bonanza_data.reward_type,
            reward_amount=bonanza_data.reward_amount,
            reward_text=bonanza_data.reward_text,
            award_name=bonanza_data.award_name,
            is_monetary=bonanza_data.is_monetary,
            total_budget=bonanza_data.total_budget,
            max_winners=bonanza_data.max_winners,
            price_range_from=bonanza_data.price_range_from or Decimal('0.00'),
            price_range_to=bonanza_data.price_range_to or Decimal('0.00'),
            actual_price=bonanza_data.actual_price or Decimal('0.00'),
            linked_award_type=bonanza_data.linked_award_type,
            linked_award_tier_id=bonanza_data.linked_award_tier_id,
            reduced_target=bonanza_data.reduced_target,
            counts_towards_regular=bonanza_data.counts_towards_regular,
            consume_achievements=bonanza_data.consume_achievements,
            status='Approved',  # RVZ Supreme Authority: Auto-approved when RVZ creates
            created_by=_resolve_actor_id(current_user),
            approved_by=_resolve_actor_id(current_user),  # RVZ approval is final
            approved_date=get_indian_time(),
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        
        db.add(new_bonanza)
        db.commit()
        db.refresh(new_bonanza)
        
        logger.info(f"Bonanza '{bonanza_data.name}' created and auto-approved by RVZ {current_user.id}")
        
        return JSONResponse({
            "success": True,
            "message": "Bonanza created successfully",
            "data": {
                "id": new_bonanza.id,
                "name": new_bonanza.name,
                "status": new_bonanza.status
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bonanza: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bonanzas/{bonanza_id}")
async def update_bonanza(
    bonanza_id: int,
    update_data: BonanzaUpdate,
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Update Bonanza campaign
    RVZ ID only
    """
    try:
        bonanza = db.query(Bonanza).filter(
            Bonanza.id == bonanza_id,
            Bonanza.is_deleted == False
        ).first()
        
        if not bonanza:
            raise HTTPException(status_code=404, detail="Bonanza not found")
        
        # Track price change
        price_changed = False
        old_price = bonanza.actual_price
        
        # Update fields
        if update_data.name is not None:
            bonanza.name = update_data.name
        if update_data.start_date is not None:
            bonanza.start_date = update_data.start_date
        if update_data.end_date is not None:
            bonanza.end_date = update_data.end_date
        if update_data.criteria_type is not None:
            bonanza.criteria_type = update_data.criteria_type
        if update_data.target_requirement is not None:
            bonanza.target_requirement = update_data.target_requirement
        if update_data.reward_type is not None:
            bonanza.reward_type = update_data.reward_type
        if update_data.reward_amount is not None:
            bonanza.reward_amount = update_data.reward_amount
        if update_data.reward_text is not None:
            bonanza.reward_text = update_data.reward_text
        if update_data.award_name is not None:
            bonanza.award_name = update_data.award_name
        if update_data.is_monetary is not None:
            bonanza.is_monetary = update_data.is_monetary
        if update_data.total_budget is not None:
            bonanza.total_budget = update_data.total_budget
        if update_data.max_winners is not None:
            bonanza.max_winners = update_data.max_winners
        if update_data.price_range_from is not None:
            bonanza.price_range_from = update_data.price_range_from
        if update_data.price_range_to is not None:
            bonanza.price_range_to = update_data.price_range_to
        if update_data.actual_price is not None:
            if update_data.actual_price != bonanza.actual_price:
                price_changed = True
                bonanza.actual_price = update_data.actual_price
                bonanza.price_last_updated_at = get_indian_time()
                bonanza.price_last_updated_by = _resolve_actor_id(current_user)
        if update_data.linked_award_type is not None:
            bonanza.linked_award_type = update_data.linked_award_type
        if update_data.linked_award_tier_id is not None:
            bonanza.linked_award_tier_id = update_data.linked_award_tier_id
        if update_data.reduced_target is not None:
            bonanza.reduced_target = update_data.reduced_target
        if update_data.counts_towards_regular is not None:
            bonanza.counts_towards_regular = update_data.counts_towards_regular
        if update_data.consume_achievements is not None:
            bonanza.consume_achievements = update_data.consume_achievements
        if update_data.status is not None:
            bonanza.status = update_data.status
        
        # RVZ Supreme Authority: Any update by RVZ = auto-approved (final)
        bonanza.status = 'Approved'
        bonanza.approved_by = _resolve_actor_id(current_user)
        bonanza.approved_date = get_indian_time()
        bonanza.updated_at = get_indian_time()
        
        db.commit()
        db.refresh(bonanza)
        
        logger.info(f"Bonanza {bonanza_id} updated and auto-approved by RVZ {current_user.id}. Price changed: {price_changed}. Reason: {update_data.update_reason or 'Not provided'}")
        
        return JSONResponse({
            "success": True,
            "message": "Bonanza updated successfully",
            "price_changed": price_changed,
            "old_price": float(old_price) if old_price else None,
            "new_price": float(bonanza.actual_price) if bonanza.actual_price else None,
            "data": {
                "id": bonanza.id,
                "name": bonanza.name,
                "status": bonanza.status
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating bonanza: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bonanzas/{bonanza_id}")
async def soft_delete_bonanza(
    bonanza_id: int,
    user_id: str = Query(None),
    deletion_reason: str = Query(..., min_length=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Soft delete Bonanza (RVZ only)
    DC Protocol: Preserves referential integrity
    """
    try:
        bonanza = db.query(Bonanza).filter(
            Bonanza.id == bonanza_id,
            Bonanza.is_deleted == False
        ).first()
        
        if not bonanza:
            raise HTTPException(status_code=404, detail="Bonanza not found")
        
        # Soft delete
        bonanza.is_deleted = True
        bonanza.deleted_at = get_indian_time()
        bonanza.deleted_by = _resolve_actor_id(current_user)
        bonanza.deletion_reason = deletion_reason
        bonanza.updated_at = get_indian_time()
        
        db.commit()
        
        logger.info(f"Bonanza {bonanza_id} soft-deleted by RVZ {current_user.id}. Reason: {deletion_reason}")
        
        return JSONResponse({
            "success": True,
            "message": f"Bonanza '{bonanza.name}' deleted successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting bonanza: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DROPDOWN DATA ENDPOINTS (For Bonanza Award Linking)
# ============================================================================

@router.get("/awards-dropdown")
async def get_awards_for_dropdown(
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Get all Direct and Matching awards for dropdown selection
    Used when creating/editing bonanzas with award linking
    """
    try:
        # Get all direct award tiers
        direct_tiers = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required).all()
        direct_awards = [{
            "id": tier.id,
            "type": "direct",
            "name": f"{tier.award_name} ({tier.referral_count} refs)",
            "referral_count": tier.referral_count,
            "award_name": tier.award_name,
            "actual_price": float(tier.actual_price) if tier.actual_price else 0
        } for tier in direct_tiers]
        
        # Get all matching award tiers
        matching_tiers = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required).all()
        matching_awards = [{
            "id": tier.id,
            "type": "matching",
            "name": f"{tier.award_name} ({tier.match_count} matches)",
            "match_count": tier.match_count,
            "award_name": tier.award_name,
            "actual_price": float(tier.actual_price) if tier.actual_price else 0
        } for tier in matching_tiers]
        
        return JSONResponse({
            "success": True,
            "data": {
                "direct_awards": direct_awards,
                "matching_awards": matching_awards
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching awards dropdown: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS & SUMMARY
# ============================================================================

@router.get("/summary")
async def get_awards_config_summary(
    user_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Get overall awards configuration summary
    Cost statistics, totals, budget tracking
    """
    try:
        # Direct awards stats
        direct_count = db.query(func.count(DirectAwardTier.id)).scalar() or 0
        direct_total_cost = db.query(func.sum(DirectAwardTier.actual_price)).scalar() or Decimal('0.00')
        direct_avg_cost = db.query(func.avg(DirectAwardTier.actual_price)).scalar() or Decimal('0.00')
        
        # Matching awards stats
        matching_count = db.query(func.count(MatchingAwardTier.id)).scalar() or 0
        matching_total_cost = db.query(func.sum(MatchingAwardTier.actual_price)).scalar() or Decimal('0.00')
        matching_avg_cost = db.query(func.avg(MatchingAwardTier.actual_price)).scalar() or Decimal('0.00')
        
        # Bonanza stats
        bonanza_total = db.query(func.count(Bonanza.id)).filter(Bonanza.is_deleted == False).scalar() or 0
        bonanza_active = db.query(func.count(Bonanza.id)).filter(
            Bonanza.is_deleted == False,
            Bonanza.status == 'Approved'
        ).scalar() or 0
        bonanza_total_budget = db.query(func.sum(Bonanza.total_budget)).filter(
            Bonanza.is_deleted == False
        ).scalar() or Decimal('0.00')
        bonanza_total_spending = db.query(func.sum(Bonanza.current_spending)).filter(
            Bonanza.is_deleted == False
        ).scalar() or Decimal('0.00')
        
        return JSONResponse({
            "success": True,
            "data": {
                "direct_awards": {
                    "total_tiers": direct_count,
                    "total_budgeted_cost": float(direct_total_cost),
                    "average_cost": float(direct_avg_cost)
                },
                "matching_awards": {
                    "total_tiers": matching_count,
                    "total_budgeted_cost": float(matching_total_cost),
                    "average_cost": float(matching_avg_cost)
                },
                "bonanzas": {
                    "total_campaigns": bonanza_total,
                    "active_campaigns": bonanza_active,
                    "total_budget_allocated": float(bonanza_total_budget),
                    "total_spending": float(bonanza_total_spending),
                    "budget_remaining": float(bonanza_total_budget - bonanza_total_spending)
                },
                "overall": {
                    "total_award_types": direct_count + matching_count + bonanza_total,
                    "total_budgeted_amount": float(direct_total_cost + matching_total_cost + bonanza_total_budget)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
