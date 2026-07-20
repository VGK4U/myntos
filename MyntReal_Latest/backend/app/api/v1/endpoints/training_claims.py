"""
Training Course Claim API Endpoints
Complete tracking with combined EV+Training balance
Super Admin/RVZ creates courses → RVZ approves → Users claim
Platinum 20%, Diamond 10% (no cap), Bonus allowed
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_user_hybrid, get_current_admin_user_hybrid
from app.models.user import User
from app.models.training_course import TrainingCourse
from app.models.training_claim import TrainingClaim
from app.models.ev_coupon_claim import EVCouponClaim
from app.models.coupon import EnhancedCoupon
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import os

router = APIRouter(prefix="/training", tags=["Training Course Claims"])

# ============= PYDANTIC SCHEMAS =============

class TrainingCourseCreate(BaseModel):
    course_name: str
    course_category: Optional[str] = None
    course_fee: float
    duration: Optional[str] = None
    trainer_name: Optional[str] = None
    trainer_contact: Optional[str] = None
    description: Optional[str] = None
    syllabus: Optional[str] = None
    display_order: int = 0

class TrainingCourseUpdate(BaseModel):
    course_name: Optional[str] = None
    course_category: Optional[str] = None
    course_fee: Optional[float] = None
    duration: Optional[str] = None
    trainer_name: Optional[str] = None
    trainer_contact: Optional[str] = None
    description: Optional[str] = None
    syllabus: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class TrainingClaimCreate(BaseModel):
    training_course_id: int
    coupon_id: int
    trainee_name: str
    trainee_contact: str
    trainee_email: Optional[str] = None
    payment_reference: Optional[str] = None

class ClaimApproval(BaseModel):
    claim_id: int
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None
    institute_name: Optional[str] = None
    institute_contact: Optional[str] = None


# ============= SUPER ADMIN/RVZ ENDPOINTS (Course Management) =============

@router.post("/courses/create")
async def create_training_course(
    course_data: TrainingCourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Super Admin/RVZ creates new training course (requires RVZ approval if Super Admin creates)"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only Super Admin or RVZ can create training courses"
    #     )
    
    # RVZ can directly approve their own creations
    approval_status = "Approved" if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else "Pending"
    
    new_course = TrainingCourse(
        **course_data.dict(),
        created_by_user_id=current_user.id,
        approval_status=approval_status,
        approved_by_user_id=current_user.id if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else None,
        approved_at=datetime.now() if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else None
    )
    
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    return {
        "success": True,
        "message": f"Training course created successfully ({approval_status})",
        "course": {
            "id": new_course.id,
            "course_name": new_course.course_name,
            "course_fee": new_course.course_fee,
            "approval_status": new_course.approval_status
        }
    }


@router.put("/courses/{course_id}/update")
async def update_training_course(
    course_id: int,
    course_data: TrainingCourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Super Admin/RVZ updates training course"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only Super Admin or RVZ can update courses"
    #     )
    
    course = db.query(TrainingCourse).filter(TrainingCourse.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    # Update fields
    update_data = course_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(course, key, value)
    
    # Reset approval if Super Admin makes changes
    if (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')) == 'Super Admin' and course.approval_status == 'Approved':
        course.approval_status = 'Pending'
        course.approved_by_user_id = None
        course.approved_at = None
    
    db.commit()
    db.refresh(course)
    
    return {"success": True, "message": "Course updated successfully"}


@router.get("/courses/all")
async def get_all_courses(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Get all training courses (Admin/Super Admin/RVZ only)"""
    
    query = db.query(TrainingCourse).order_by(TrainingCourse.display_order, TrainingCourse.course_name)
    
    if status_filter:
        query = query.filter(TrainingCourse.approval_status == status_filter)
    
    courses = query.all()
    
    return {
        "success": True,
        "total": len(courses),
        "courses": [
            {
                "id": c.id,
                "course_name": c.course_name,
                "course_category": c.course_category,
                "course_fee": c.course_fee,
                "duration": c.duration,
                "trainer_name": c.trainer_name,
                "approval_status": c.approval_status,
                "is_active": c.is_active,
                "created_by": c.created_by.name if c.created_by else None,
                "approved_by": c.approved_by.name if c.approved_by else None
            }
            for c in courses
        ]
    }


# ============= RVZ ENDPOINTS (Approval) =============

@router.post("/courses/{course_id}/approve")
async def approve_training_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ approves training course"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only RVZ ID can approve courses"
    #     )
    
    course = db.query(TrainingCourse).filter(TrainingCourse.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    course.approval_status = 'Approved'
    course.approved_by_user_id = current_user.id
    course.approved_at = datetime.now()
    course.is_active = True
    
    db.commit()
    
    return {"success": True, "message": "Course approved successfully"}


@router.post("/courses/{course_id}/reject")
async def reject_training_course(
    course_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ rejects training course"""
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only RVZ ID can reject courses"
    #     )
    
    course = db.query(TrainingCourse).filter(TrainingCourse.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    
    course.approval_status = 'Rejected'
    course.rejection_reason = reason
    course.is_active = False
    
    db.commit()
    
    return {"success": True, "message": "Course rejected"}


# ============= USER ENDPOINTS (Claim Submission) =============

@router.get("/courses/approved")
async def get_approved_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """Get approved training courses for users"""
    
    courses = db.query(TrainingCourse).filter(
        TrainingCourse.approval_status == 'Approved',
        TrainingCourse.is_active == True
    ).order_by(TrainingCourse.display_order, TrainingCourse.course_name).all()
    
    return {
        "success": True,
        "courses": [
            {
                "id": c.id,
                "course_name": c.course_name,
                "course_category": c.course_category,
                "course_fee": c.course_fee,
                "duration": c.duration,
                "trainer_name": c.trainer_name,
                "description": c.description,
                "syllabus": c.syllabus
            }
            for c in courses
        ]
    }


@router.get("/my-combined-balance")
async def get_combined_coupon_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """Get combined EV+Training coupon balance"""
    
    # Get all active coupons
    coupons = db.query(EnhancedCoupon).filter(
        EnhancedCoupon.user_id == current_user.id,
        EnhancedCoupon.status.in_(['Active', 'Partially Used'])
    ).all()
    
    coupon_data = []
    
    for coupon in coupons:
        package = coupon.package_name
        
        # Determine discount amounts based on package
        if package == 'Platinum':
            ev_discount = 15000
            training_discount_pct = 20
        elif package == 'Diamond':
            ev_discount = 7500
            training_discount_pct = 10
        else:
            ev_discount = 0
            training_discount_pct = 0
        
        # Count EV claims for this coupon
        ev_claims = db.query(EVCouponClaim).filter(
            EVCouponClaim.coupon_id == coupon.id,
            EVCouponClaim.claim_status.in_(['Pending', 'Admin Approved', 'Dealer Confirmed', 'Delivered'])
        ).all()
        
        ev_claims_count = len(ev_claims)
        ev_total_used = sum(c.discount_amount for c in ev_claims)
        
        # Count Training claims for this coupon
        training_claims = db.query(TrainingClaim).filter(
            TrainingClaim.coupon_id == coupon.id,
            TrainingClaim.claim_status.in_(['Pending', 'Admin Approved', 'Institute Confirmed', 'Completed'])
        ).all()
        
        training_total_used = sum(c.discount_amount for c in training_claims)
        training_bonus = sum(c.bonus_amount for c in training_claims if c.is_bonus)
        
        # Calculate total used and balance
        total_coupon_value = ev_discount  # Base coupon value
        total_used = ev_total_used + training_total_used
        balance = total_coupon_value - total_used
        
        # If balance negative, it's all bonus (allowed only for training)
        if balance < 0:
            bonus_used = abs(balance)
            balance = 0
        else:
            bonus_used = 0
        
        coupon_data.append({
            "coupon_id": coupon.id,
            "coupon_code": coupon.coupon_code,
            "package": package,
            "total_coupon_value": total_coupon_value,
            "ev_claims": ev_claims_count,
            "ev_used": ev_total_used,
            "training_claims": len(training_claims),
            "training_used": training_total_used,
            "training_discount_pct": training_discount_pct,
            "total_used": total_used,
            "balance": balance,
            "bonus_used": bonus_used + training_bonus,
            "has_balance": balance > 0
        })
    
    return {
        "success": True,
        "user_id": current_user.id,
        "user_name": current_user.name,
        "total_coupons": len(coupon_data),
        "coupons": coupon_data
    }


@router.post("/claim/submit")
async def submit_training_claim(
    claim_data: TrainingClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """User submits training course claim"""
    
    # Validate eligibility
    if current_user.coupon_status != 'Active':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have an active package to claim training discount"
        )
    
    # TEMPORARY: KYC check disabled - skip for now (November 2, 2025)
    # if current_user.kyc_status != 'Approved':
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="KYC must be approved to claim training discount"
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
    
    # Validate training course
    course = db.query(TrainingCourse).filter(
        TrainingCourse.id == claim_data.training_course_id,
        TrainingCourse.approval_status == 'Approved',
        TrainingCourse.is_active == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training course not found or not approved"
        )
    
    # Calculate discount based on package
    package = coupon.package_name
    if package == 'Platinum':
        discount_pct = 20
        coupon_value = 15000
    elif package == 'Diamond':
        discount_pct = 10
        coupon_value = 7500
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Platinum and Diamond packages can claim training discounts"
        )
    
    discount_amount = course.course_fee * (discount_pct / 100)
    
    # Check existing usage (EV + Training)
    ev_used = db.query(func.sum(EVCouponClaim.discount_amount)).filter(
        EVCouponClaim.coupon_id == claim_data.coupon_id,
        EVCouponClaim.claim_status.in_(['Pending', 'Admin Approved', 'Dealer Confirmed', 'Delivered'])
    ).scalar() or 0
    
    training_used = db.query(func.sum(TrainingClaim.discount_amount)).filter(
        TrainingClaim.coupon_id == claim_data.coupon_id,
        TrainingClaim.claim_status.in_(['Pending', 'Admin Approved', 'Institute Confirmed', 'Completed'])
    ).scalar() or 0
    
    total_used = ev_used + training_used
    balance = coupon_value - total_used
    
    # Determine if this is bonus usage
    is_bonus = False
    bonus_amount = 0
    
    if balance < discount_amount:
        # This claim exceeds balance - allowed only for training
        is_bonus = True
        if balance > 0:
            bonus_amount = discount_amount - balance
        else:
            bonus_amount = discount_amount
    
    # Create claim
    new_claim = TrainingClaim(
        user_id=current_user.id,
        coupon_id=claim_data.coupon_id,
        training_course_id=claim_data.training_course_id,
        trainee_name=claim_data.trainee_name,
        trainee_contact=claim_data.trainee_contact,
        trainee_email=claim_data.trainee_email,
        payment_reference=claim_data.payment_reference,
        course_fee_at_claim=course.course_fee,
        discount_percentage=discount_pct,
        discount_amount=discount_amount,
        is_bonus=is_bonus,
        bonus_amount=bonus_amount,
        claim_status='Pending',
        package_at_claim=package,
        created_by_admin=False,
        created_by_user_id=current_user.id
    )
    
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    
    return {
        "success": True,
        "message": "Training claim submitted successfully",
        "claim_id": new_claim.id,
        "discount_amount": discount_amount,
        "discount_percentage": discount_pct,
        "is_bonus": is_bonus,
        "bonus_amount": bonus_amount,
        "status": "Pending Admin Approval"
    }


@router.get("/my-claims")
async def get_my_training_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """Get user's training claim history"""
    
    claims = db.query(TrainingClaim).filter(
        TrainingClaim.user_id == current_user.id
    ).order_by(desc(TrainingClaim.created_at)).all()
    
    return {
        "success": True,
        "total_claims": len(claims),
        "claims": [
            {
                "id": c.id,
                "course_name": c.training_course.course_name if c.training_course else "N/A",
                "course_fee": c.course_fee_at_claim,
                "discount_percentage": c.discount_percentage,
                "discount_amount": c.discount_amount,
                "is_bonus": c.is_bonus,
                "bonus_amount": c.bonus_amount,
                "claim_status": c.claim_status,
                "trainee_name": c.trainee_name,
                "institute_name": c.institute_name,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "approved_at": c.approved_at.isoformat() if c.approved_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None
            }
            for c in claims
        ]
    }


# ============= ADMIN ENDPOINTS (Claim Approval) =============

@router.get("/claims/pending")
async def get_pending_training_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Admin/Super Admin get pending training claims"""
    
    claims = db.query(TrainingClaim).filter(
        TrainingClaim.claim_status == 'Pending'
    ).order_by(TrainingClaim.created_at).all()
    
    return {
        "success": True,
        "total_pending": len(claims),
        "claims": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "user_name": c.user.name if c.user else "N/A",
                "course_name": c.training_course.course_name if c.training_course else "N/A",
                "trainee_name": c.trainee_name,
                "trainee_contact": c.trainee_contact,
                "course_fee": c.course_fee_at_claim,
                "discount_percentage": c.discount_percentage,
                "discount_amount": c.discount_amount,
                "is_bonus": c.is_bonus,
                "bonus_amount": c.bonus_amount,
                "package": c.package_at_claim,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in claims
        ]
    }


@router.post("/claims/approve")
async def approve_training_claim(
    approval: ClaimApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Admin/Super Admin approve or reject training claim"""
    
    claim = db.query(TrainingClaim).filter(
        TrainingClaim.id == approval.claim_id
    ).first()
    
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    
    if approval.action == "approve":
        claim.claim_status = 'Admin Approved'
        claim.approved_by_user_id = current_user.id
        claim.approved_at = datetime.now()
        
        if approval.institute_name:
            claim.institute_name = approval.institute_name
        if approval.institute_contact:
            claim.institute_contact = approval.institute_contact
            claim.claim_status = 'Institute Confirmed'
            claim.assigned_to_institute_at = datetime.now()
        
        db.commit()
        return {"success": True, "message": "Training claim approved successfully"}
    
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
        return {"success": True, "message": "Training claim rejected"}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'approve' or 'reject'"
        )


@router.get("/claims/all")
async def get_all_training_claims(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Get all training claims with filters"""
    
    query = db.query(TrainingClaim).order_by(desc(TrainingClaim.created_at))
    
    if status_filter:
        query = query.filter(TrainingClaim.claim_status == status_filter)
    
    claims = query.all()
    
    return {
        "success": True,
        "total": len(claims),
        "claims": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "user_name": c.user.name if c.user else "N/A",
                "course_name": c.training_course.course_name if c.training_course else "N/A",
                "discount_amount": c.discount_amount,
                "is_bonus": c.is_bonus,
                "claim_status": c.claim_status,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in claims
        ]
    }


@router.get("/statistics")
async def get_training_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """Get overall training claim statistics"""
    
    total_claims = db.query(TrainingClaim).count()
    pending_claims = db.query(TrainingClaim).filter(
        TrainingClaim.claim_status == 'Pending'
    ).count()
    approved_claims = db.query(TrainingClaim).filter(
        TrainingClaim.claim_status.in_(['Admin Approved', 'Institute Confirmed', 'Completed'])
    ).count()
    rejected_claims = db.query(TrainingClaim).filter(
        TrainingClaim.claim_status == 'Rejected'
    ).count()
    
    total_discount = db.query(func.sum(TrainingClaim.discount_amount)).filter(
        TrainingClaim.claim_status.in_(['Admin Approved', 'Institute Confirmed', 'Completed'])
    ).scalar() or 0
    
    total_bonus = db.query(func.sum(TrainingClaim.bonus_amount)).filter(
        TrainingClaim.is_bonus == True,
        TrainingClaim.claim_status.in_(['Admin Approved', 'Institute Confirmed', 'Completed'])
    ).scalar() or 0
    
    return {
        "success": True,
        "statistics": {
            "total_claims": total_claims,
            "pending_claims": pending_claims,
            "approved_claims": approved_claims,
            "rejected_claims": rejected_claims,
            "total_discount_approved": float(total_discount),
            "total_bonus_given": float(total_bonus)
        }
    }


# ============= HTML TEMPLATE ROUTES =============

@router.get("/manage-courses", response_class=HTMLResponse)
async def training_courses_management_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Training Course Management page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for training course management
    Direct backend access not supported - use frontend on port 5000
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not user or user.user_type not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only Super Admin or RVZ ID can access this page"
    #     )
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Training Course Management - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/training/manage-courses">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/training/manage-courses">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/claim", response_class=HTMLResponse)
async def user_training_claim_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    User Training Course Claim page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for training course operations
    Direct backend access not supported - use frontend on port 5000
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Training Course Claim - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/training/claim">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/training/claim">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/admin/claims", response_class=HTMLResponse)
async def admin_training_claims_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin Training Claims Management page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for training claims approval
    Direct backend access not supported - use frontend on port 5000
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not user or user.user_type not in ['Admin', 'Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only Admin, Super Admin, or RVZ ID can access this page"
    #     )
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Training Claims Management - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/training/admin/claims">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/training/admin/claims">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
