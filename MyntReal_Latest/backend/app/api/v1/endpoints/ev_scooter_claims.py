"""
EV Scooter Coupon Claim API Endpoints
Complete tracking of claims, balances, and claim history
Super Admin creates models → RVZ approves → Users claim
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_user_hybrid
from app.models.user import User
from app.models.ev_model import EVModel
from app.models.ev_coupon_claim import EVCouponClaim
from app.models.coupon import EnhancedCoupon
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/ev-scooter", tags=["EV Scooter Claims"])


# ============= PYDANTIC SCHEMAS =============

class EVModelCreate(BaseModel):
    model_name: str
    variant_name: Optional[str] = None
    manufacturer: str = "Royal EV"
    base_price: float
    max_discount_percentage: float
    description: Optional[str] = None
    specifications: Optional[str] = None
    display_order: int = 0

class EVModelUpdate(BaseModel):
    model_name: Optional[str] = None
    variant_name: Optional[str] = None
    manufacturer: Optional[str] = None
    base_price: Optional[float] = None
    max_discount_percentage: Optional[float] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class EVClaimCreate(BaseModel):
    ev_model_id: int
    coupon_id: int
    customer_name: str
    customer_contact: str
    delivery_address: str
    payment_reference: Optional[str] = None

class ClaimApproval(BaseModel):
    claim_id: int
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None
    dealer_showroom: Optional[str] = None
    dealer_contact: Optional[str] = None


# ============= SUPER ADMIN ENDPOINTS (Model Management) =============

@router.post("/models/create")
async def create_ev_model(
    model_data: EVModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Super Admin creates new EV model (requires RVZ approval)"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only Super Admin can create EV models"
    #     )
    
    # Check for duplicate model+variant
    existing = db.query(EVModel).filter(
        EVModel.model_name == model_data.model_name,
        EVModel.variant_name == model_data.variant_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_data.model_name}' variant '{model_data.variant_name}' already exists"
        )
    
    # RVZ can directly approve their own creations
    approval_status = "Approved" if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else "Pending"
    
    new_model = EVModel(
        **model_data.dict(),
        created_by_user_id=current_user.id,
        approval_status=approval_status,
        approved_by_user_id=current_user.id if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else None,
        approved_at=datetime.now() if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else None
    )
    
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    
    return {
        "success": True,
        "message": f"EV model created successfully ({approval_status})",
        "model": {
            "id": new_model.id,
            "model_name": new_model.model_name,
            "variant_name": new_model.variant_name,
            "approval_status": new_model.approval_status
        }
    }


@router.put("/models/{model_id}/update")
async def update_ev_model(
    model_id: int,
    model_data: EVModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Super Admin updates EV model (requires re-approval if changed)"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only Super Admin can update EV models"
    #     )
    
    model = db.query(EVModel).filter(EVModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    
    # Update fields
    update_data = model_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model, key, value)
    
    # Reset approval if Super Admin makes changes (RVZ can directly approve)
    if (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')) == 'Super Admin' and model.approval_status == 'Approved':
        model.approval_status = 'Pending'
        model.approved_by_user_id = None
        model.approved_at = None
    
    db.commit()
    db.refresh(model)
    
    return {"success": True, "message": "Model updated successfully", "model": model}


@router.get("/models/all")
async def get_all_ev_models(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all EV models (Admin/Super Admin/RVZ only)"""
    
    query = db.query(EVModel).order_by(EVModel.display_order, EVModel.model_name)
    
    if status_filter:
        query = query.filter(EVModel.approval_status == status_filter)
    
    models = query.all()
    
    return {
        "success": True,
        "total": len(models),
        "models": [
            {
                "id": m.id,
                "model_name": m.model_name,
                "variant_name": m.variant_name,
                "manufacturer": m.manufacturer,
                "base_price": m.base_price,
                "max_discount_percentage": m.max_discount_percentage,
                "approval_status": m.approval_status,
                "is_active": m.is_active,
                "created_by": m.created_by.name if m.created_by else None,
                "approved_by": m.approved_by.name if m.approved_by else None
            }
            for m in models
        ]
    }


# ============= RVZ ENDPOINTS (Approval) =============

@router.post("/models/{model_id}/approve")
async def approve_ev_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """RVZ approves EV model"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only RVZ ID can approve models"
    #     )
    
    model = db.query(EVModel).filter(EVModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    
    model.approval_status = 'Approved'
    model.approved_by_user_id = current_user.id
    model.approved_at = datetime.now()
    model.is_active = True
    
    db.commit()
    
    return {"success": True, "message": "Model approved successfully"}


@router.post("/models/{model_id}/reject")
async def reject_ev_model(
    model_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """RVZ rejects EV model"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only RVZ ID can reject models"
    #     )
    
    model = db.query(EVModel).filter(EVModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    
    model.approval_status = 'Rejected'
    model.rejection_reason = reason
    model.is_active = False
    
    db.commit()
    
    return {"success": True, "message": "Model rejected"}


# ============= USER ENDPOINTS (Claim Submission) =============

@router.get("/models/approved")
async def get_approved_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get approved EV models for users"""
    
    models = db.query(EVModel).filter(
        EVModel.approval_status == 'Approved',
        EVModel.is_active == True,
        EVModel.coupon_benefit_enabled == True
    ).order_by(EVModel.display_order, EVModel.model_name).all()
    
    return {
        "success": True,
        "models": [
            {
                "id": m.id,
                "model_name": m.model_name,
                "variant_name": m.variant_name,
                "manufacturer": m.manufacturer,
                "base_price": m.base_price,
                "max_discount_percentage": m.max_discount_percentage,
                "description": m.description,
                "image_url": m.image_url
            }
            for m in models
        ]
    }


@router.get("/my-coupons-balance")
async def get_my_coupon_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's coupon balance and claim tracking"""
    
    # Get all active coupons for user
    coupons = db.query(EnhancedCoupon).filter(
        EnhancedCoupon.user_id == current_user.id,
        EnhancedCoupon.status.in_(['Active', 'Partially Used'])
    ).all()
    
    coupon_data = []
    
    for coupon in coupons:
        # Count claims for this coupon
        total_claims = db.query(EVCouponClaim).filter(
            EVCouponClaim.coupon_id == coupon.id,
            EVCouponClaim.claim_status.in_(['Pending', 'Admin Approved', 'Dealer Confirmed', 'Delivered'])
        ).count()
        
        # Determine max claims based on package
        package = coupon.package_name
        if package == 'Platinum':
            max_claims = 1
            discount_per_claim = 15000
        elif package == 'Diamond':
            max_claims = 2
            discount_per_claim = 7500
        else:
            max_claims = 0
            discount_per_claim = 0
        
        remaining_claims = max(0, max_claims - total_claims)
        
        coupon_data.append({
            "coupon_id": coupon.id,
            "coupon_code": coupon.coupon_code,
            "package": package,
            "total_claims": total_claims,
            "max_claims": max_claims,
            "remaining_claims": remaining_claims,
            "discount_per_claim": discount_per_claim,
            "total_value_claimed": total_claims * discount_per_claim,
            "remaining_value": remaining_claims * discount_per_claim
        })
    
    return {
        "success": True,
        "user_id": current_user.id,
        "user_name": current_user.name,
        "total_coupons": len(coupon_data),
        "coupons": coupon_data
    }


@router.post("/claim/submit")
async def submit_ev_claim(
    claim_data: EVClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User submits EV scooter claim"""
    
    # Validate eligibility: Active package + KYC approved
    if current_user.coupon_status != 'Active':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have an active package to claim EV discount"
        )
    
    # TEMPORARY: KYC check disabled - skip for now (November 2, 2025)
    # if current_user.kyc_status != 'Approved':
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="KYC must be approved to claim EV discount"
    #     )
    
    # Validate coupon
    coupon = db.query(EnhancedCoupon).filter(
        EnhancedCoupon.id == claim_data.coupon_id,
        EnhancedCoupon.user_id == current_user.id,
        EnhancedCoupon.status.in_(['Active', 'Partially Used'])
    ).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valid coupon not found"
        )
    
    # Check claim limits
    existing_claims = db.query(EVCouponClaim).filter(
        EVCouponClaim.coupon_id == claim_data.coupon_id,
        EVCouponClaim.claim_status.in_(['Pending', 'Admin Approved', 'Dealer Confirmed', 'Delivered'])
    ).count()
    
    package = coupon.package_name
    max_claims = 1 if package == 'Platinum' else 2 if package == 'Diamond' else 0
    
    if existing_claims >= max_claims:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have already used all {max_claims} claim(s) for this coupon"
        )
    
    # Validate EV model
    ev_model = db.query(EVModel).filter(
        EVModel.id == claim_data.ev_model_id,
        EVModel.approval_status == 'Approved',
        EVModel.is_active == True
    ).first()
    
    if not ev_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EV model not found or not approved"
        )
    
    # Calculate discount amount
    if ev_model.max_discount_percentage == 100:
        # 100% benefit models (max ₹15k/₹7.5k)
        discount_amount = 15000 if package == 'Platinum' else 7500
    else:
        # 5% invoice models
        discount_amount = ev_model.base_price * (ev_model.max_discount_percentage / 100)
    
    # Create claim
    new_claim = EVCouponClaim(
        user_id=current_user.id,
        coupon_id=claim_data.coupon_id,
        ev_model_id=claim_data.ev_model_id,
        customer_name=claim_data.customer_name,
        customer_contact=claim_data.customer_contact,
        delivery_address=claim_data.delivery_address,
        payment_reference=claim_data.payment_reference,
        discount_amount=discount_amount,
        model_price_at_claim=ev_model.base_price,
        claim_status='Pending',
        package_at_claim=package,
        claim_number_for_coupon=existing_claims + 1,
        created_by_admin=False,
        created_by_user_id=current_user.id
    )
    
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    
    return {
        "success": True,
        "message": "Claim submitted successfully",
        "claim_id": new_claim.id,
        "discount_amount": discount_amount,
        "status": "Pending Admin Approval"
    }


@router.get("/my-claims")
async def get_my_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's claim history"""
    
    claims = db.query(EVCouponClaim).filter(
        EVCouponClaim.user_id == current_user.id
    ).order_by(desc(EVCouponClaim.created_at)).all()
    
    return {
        "success": True,
        "total_claims": len(claims),
        "claims": [
            {
                "id": c.id,
                "ev_model": c.ev_model.model_name if c.ev_model else "N/A",
                "variant": c.ev_model.variant_name if c.ev_model else None,
                "discount_amount": c.discount_amount,
                "claim_status": c.claim_status,
                "customer_name": c.customer_name,
                "dealer_showroom": c.dealer_showroom,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "approved_at": c.approved_at.isoformat() if c.approved_at else None,
                "delivered_at": c.delivered_at.isoformat() if c.delivered_at else None
            }
            for c in claims
        ]
    }


# ============= ADMIN ENDPOINTS (Claim Approval) =============

@router.get("/claims/pending")
async def get_pending_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Admin/Super Admin get pending claims"""
    
    claims = db.query(EVCouponClaim).filter(
        EVCouponClaim.claim_status == 'Pending'
    ).order_by(EVCouponClaim.created_at).all()
    
    return {
        "success": True,
        "total_pending": len(claims),
        "claims": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "user_name": c.user.name if c.user else "N/A",
                "ev_model": c.ev_model.model_name if c.ev_model else "N/A",
                "variant": c.ev_model.variant_name if c.ev_model else None,
                "customer_name": c.customer_name,
                "customer_contact": c.customer_contact,
                "discount_amount": c.discount_amount,
                "package": c.package_at_claim,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in claims
        ]
    }


@router.post("/claims/approve")
async def approve_claim(
    approval: ClaimApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Admin/Super Admin approve or reject claim"""
    
    claim = db.query(EVCouponClaim).filter(
        EVCouponClaim.id == approval.claim_id
    ).first()
    
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    
    if approval.action == "approve":
        claim.claim_status = 'Admin Approved'
        claim.approved_by_user_id = current_user.id
        claim.approved_at = datetime.now()
        
        if approval.dealer_showroom:
            claim.dealer_showroom = approval.dealer_showroom
        if approval.dealer_contact:
            claim.dealer_contact = approval.dealer_contact
            claim.claim_status = 'Dealer Confirmed'
            claim.assigned_to_dealer_at = datetime.now()
        
        db.commit()
        return {"success": True, "message": "Claim approved successfully"}
    
    elif approval.action == "reject":
        if not approval.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        
        claim.claim_status = 'Rejected'
        claim.rejection_reason = approval.rejection_reason
        claim.rejected_by_user_id = current_user.id
        claim.rejected_at = datetime.now()
        
        db.commit()
        return {"success": True, "message": "Claim rejected"}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'approve' or 'reject'"
        )


@router.get("/claims/all")
async def get_all_claims(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all claims with filters"""
    
    query = db.query(EVCouponClaim).order_by(desc(EVCouponClaim.created_at))
    
    if status_filter:
        query = query.filter(EVCouponClaim.claim_status == status_filter)
    
    claims = query.all()
    
    return {
        "success": True,
        "total": len(claims),
        "claims": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "user_name": c.user.name if c.user else "N/A",
                "ev_model": c.ev_model.model_name if c.ev_model else "N/A",
                "discount_amount": c.discount_amount,
                "claim_status": c.claim_status,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in claims
        ]
    }


@router.get("/statistics")
async def get_claim_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get overall claim statistics"""
    
    total_claims = db.query(EVCouponClaim).count()
    pending_claims = db.query(EVCouponClaim).filter(
        EVCouponClaim.claim_status == 'Pending'
    ).count()
    approved_claims = db.query(EVCouponClaim).filter(
        EVCouponClaim.claim_status.in_(['Admin Approved', 'Dealer Confirmed', 'Delivered'])
    ).count()
    rejected_claims = db.query(EVCouponClaim).filter(
        EVCouponClaim.claim_status == 'Rejected'
    ).count()
    
    total_discount = db.query(func.sum(EVCouponClaim.discount_amount)).filter(
        EVCouponClaim.claim_status.in_(['Admin Approved', 'Dealer Confirmed', 'Delivered'])
    ).scalar() or 0
    
    return {
        "success": True,
        "statistics": {
            "total_claims": total_claims,
            "pending_claims": pending_claims,
            "approved_claims": approved_claims,
            "rejected_claims": rejected_claims,
            "total_discount_approved": float(total_discount)
        }
    }
