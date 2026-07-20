"""
Award Price Management System - Admin requests, Finance Admin approves
Complete price change workflow with approval and history tracking
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.models.award_price_change import AwardPriceChangeRequest
from app.models.awards import DirectAwardTier, MatchingAwardTier
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/award-price-management", tags=["Award Price Management"])


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


class PriceChangeRequest(BaseModel):
    award_type: str  # 'direct' or 'matching'
    award_tier_id: int
    new_price: float
    change_reason: str


class PriceChangeApproval(BaseModel):
    approval_notes: Optional[str] = None


@router.post("/request")
async def request_price_change(
    data: PriceChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RVZ ID requests a price change for an award
    RVZ ID ONLY access
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Validate award type
    if data.award_type not in ['direct', 'matching']:
        raise HTTPException(status_code=400, detail="Invalid award type. Must be 'direct' or 'matching'")
    
    # Get current award tier
    if data.award_type == 'direct':
        award_tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == data.award_tier_id).first()
    else:
        award_tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == data.award_tier_id).first()
    
    if not award_tier:
        raise HTTPException(status_code=404, detail="Award tier not found")
    
    # Check if there's already a pending request for this award
    existing_request = db.query(AwardPriceChangeRequest).filter(
        and_(
            AwardPriceChangeRequest.award_type == data.award_type,
            AwardPriceChangeRequest.award_tier_id == data.award_tier_id,
            AwardPriceChangeRequest.status == 'pending'
        )
    ).first()
    
    if existing_request:
        raise HTTPException(status_code=400, detail="There is already a pending price change request for this award")
    
    # Create price change request
    price_request = AwardPriceChangeRequest(
        award_type=data.award_type,
        award_tier_id=data.award_tier_id,
        award_name=award_tier.award_name,
        current_price=award_tier.actual_price or 0,
        new_price=data.new_price,
        change_reason=data.change_reason,
        requested_by_id=current_user.id,
        status='pending'
    )
    
    db.add(price_request)
    db.commit()
    db.refresh(price_request)
    
    return {
        "success": True,
        "message": "Price change request submitted successfully",
        "request_id": price_request.id
    }


@router.get("/pending")
async def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finance Admin views pending price change requests
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Finance Admin access required")
    
    pending_requests = db.query(AwardPriceChangeRequest).filter(
        AwardPriceChangeRequest.status == 'pending'
    ).order_by(desc(AwardPriceChangeRequest.requested_at)).all()
    
    return {
        "success": True,
        "pending_requests": [
            {
                "id": req.id,
                "award_type": req.award_type,
                "award_tier_id": req.award_tier_id,
                "award_name": req.award_name,
                "current_price": float(req.current_price),
                "new_price": float(req.new_price),
                "change_reason": req.change_reason,
                "requested_by_id": req.requested_by_id,
                "requested_at": req.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                "status": req.status
            }
            for req in pending_requests
        ]
    }


@router.post("/approve/{request_id}")
async def approve_price_change(
    request_id: int,
    data: PriceChangeApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finance Admin approves price change and updates award tier
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Finance Admin access required")
    
    # Get the price change request
    price_request = db.query(AwardPriceChangeRequest).filter(
        AwardPriceChangeRequest.id == request_id
    ).first()
    
    if not price_request:
        raise HTTPException(status_code=404, detail="Price change request not found")
    
    if price_request.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Request already {price_request.status}")
    
    # Get the award tier
    if price_request.award_type == 'direct':
        award_tier = db.query(DirectAwardTier).filter(
            DirectAwardTier.id == price_request.award_tier_id
        ).first()
    else:
        award_tier = db.query(MatchingAwardTier).filter(
            MatchingAwardTier.id == price_request.award_tier_id
        ).first()
    
    if not award_tier:
        raise HTTPException(status_code=404, detail="Award tier not found")
    
    # Update award tier price
    award_tier.actual_price = price_request.new_price
    award_tier.price_last_updated_at = datetime.utcnow()
    award_tier.price_last_updated_by = _resolve_actor_id(current_user)
    award_tier.last_updated_by = _resolve_actor_id(current_user)
    award_tier.last_updated_at = datetime.utcnow()
    
    # Update price change request
    price_request.status = 'approved'
    price_request.approved_by_id = _resolve_actor_id(current_user)
    price_request.approved_at = datetime.utcnow()
    price_request.approval_notes = data.approval_notes
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Price change approved successfully. {award_tier.award_name} price updated to ₹{price_request.new_price}"
    }


@router.post("/reject/{request_id}")
async def reject_price_change(
    request_id: int,
    data: PriceChangeApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finance Admin rejects price change request
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Finance Admin access required")
    
    # Get the price change request
    price_request = db.query(AwardPriceChangeRequest).filter(
        AwardPriceChangeRequest.id == request_id
    ).first()
    
    if not price_request:
        raise HTTPException(status_code=404, detail="Price change request not found")
    
    if price_request.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Request already {price_request.status}")
    
    # Update price change request
    price_request.status = 'rejected'
    price_request.approved_by_id = _resolve_actor_id(current_user)
    price_request.approved_at = datetime.utcnow()
    price_request.approval_notes = data.approval_notes or "Rejected by Finance Admin"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Price change request rejected"
    }


@router.get("/history")
async def get_price_change_history(
    award_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get price change history with filters
    RVZ ID and Finance Admin can view history
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="RVZ ID or Finance Admin access required")
    
    query = db.query(AwardPriceChangeRequest)
    
    if award_type:
        query = query.filter(AwardPriceChangeRequest.award_type == award_type)
    
    if status:
        query = query.filter(AwardPriceChangeRequest.status == status)
    
    history = query.order_by(desc(AwardPriceChangeRequest.requested_at)).all()
    
    return {
        "success": True,
        "history": [
            {
                "id": req.id,
                "award_type": req.award_type,
                "award_tier_id": req.award_tier_id,
                "award_name": req.award_name,
                "current_price": float(req.current_price),
                "new_price": float(req.new_price),
                "change_reason": req.change_reason,
                "requested_by_id": req.requested_by_id,
                "requested_at": req.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                "status": req.status,
                "approved_by_id": req.approved_by_id,
                "approved_at": req.approved_at.strftime('%Y-%m-%d %H:%M:%S') if req.approved_at else None,
                "approval_notes": req.approval_notes
            }
            for req in history
        ]
    }


@router.get("/award-tiers")
async def get_award_tiers(
    award_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all award tiers of a specific type
    RVZ ID and Finance Admin can view tiers
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="RVZ ID or Finance Admin access required")
    
    if award_type == 'direct':
        tiers = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required).all()
        return {
            "success": True,
            "award_tiers": [
                {
                    "id": tier.id,
                    "award_name": tier.award_name,
                    "award_description": tier.award_description,
                    "referral_count": tier.referral_count,
                    "actual_price": float(tier.actual_price) if tier.actual_price else 0,
                    "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                    "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                    "price_last_updated_at": tier.price_last_updated_at.strftime('%Y-%m-%d %H:%M:%S') if tier.price_last_updated_at else None,
                    "price_last_updated_by": tier.price_last_updated_by
                }
                for tier in tiers
            ]
        }
    elif award_type == 'matching':
        tiers = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required).all()
        return {
            "success": True,
            "award_tiers": [
                {
                    "id": tier.id,
                    "award_name": tier.award_name,
                    "award_description": tier.award_description,
                    "match_count": tier.match_count,
                    "actual_price": float(tier.actual_price) if tier.actual_price else 0,
                    "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                    "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                    "price_last_updated_at": tier.price_last_updated_at.strftime('%Y-%m-%d %H:%M:%S') if tier.price_last_updated_at else None,
                    "price_last_updated_by": tier.price_last_updated_by
                }
                for tier in tiers
            ]
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid award type. Must be 'direct' or 'matching'")
