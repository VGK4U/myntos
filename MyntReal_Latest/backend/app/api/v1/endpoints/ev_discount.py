"""
EV Discount Coupon API Endpoints
Handles EV purchase coupon redemption and management
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, get_current_admin_user
from app.models.user import User
from app.models.ev_discount import (
    EV, Purchase, EVRedemptionRequest, CouponBenefit,
    ReferralIncome, FranchisePurchase, InsurancePolicy, FleetOrder
)
from app.models.training_course import TrainingCourse
from app.services.ev_benefit_service import EVBenefitService
from app.schemas.ev_discount import (
    EVCreate, EVResponse, PurchaseCreate, PurchaseResponse,
    EVRedemptionCreate, EVRedemptionResponse, RedemptionApproval,
    TrainingCourseCreate, TrainingCourseResponse, EVDashboardStats, UserEVStats
)
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

router = APIRouter(prefix="/ev-discount", tags=["EV Discount Coupons"])


# ===== USER ENDPOINTS =====

@router.get("/ev-models", response_model=List[EVResponse])
async def get_available_ev_models(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get all available EV models for purchase"""
    query = db.query(EV).filter(EV.is_available == True)
    
    if category:
        query = query.filter(EV.category == category)
    
    ev_models = query.all()
    return ev_models


@router.get("/my-coupons")
async def get_my_ev_coupons(
    audience: Optional[str] = None,  # DC_AUDIENCE_001 — Task #37
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's available EV discount coupons (audience-aware).

    Task #37: branches on ``audience='vgk4u'`` to surface VGK4U-issued EV
    discount coupons from ``vgk_coupon_ledger`` (transaction_type IN
    ('purchase_credit','admin_credit','transfer_in')). The MNR branch
    keeps the legacy placeholder until the EnhancedCoupon integration
    lands.
    """
    from app.core.audience_resolver import normalize_audience, audience_label
    from app.models.staff_accounts import OfficialPartner
    from sqlalchemy import text as sa_text

    aud = normalize_audience(audience) if audience is not None else 'mnr'
    items: list = []

    if aud in ('vgk4u', 'both'):
        # DC RBAC guard — VGK4U coupon ledger is partner-restricted; reject
        # MNR users that try to enumerate it via the audience parameter.
        from app.models.staff import StaffEmployee as _Staff
        if not isinstance(current_user, (_Staff, OfficialPartner)):
            from fastapi import HTTPException, status as _st
            raise HTTPException(
                status_code=_st.HTTP_403_FORBIDDEN,
                detail="VGK4U data is restricted to staff and VGK partner accounts.",
            )
        import logging as _logging
        _log = _logging.getLogger(__name__)
        partner_id = current_user.id if isinstance(current_user, OfficialPartner) else None
        # For Staff callers, scope ledger rows to partners belonging to the
        # caller's company so we don't surface other companies' coupon data.
        # vgk_coupon_ledger has no company_id, so we filter via the
        # official_partners.company_id join.
        staff_company_id: Optional[int] = None
        if isinstance(current_user, _Staff):
            staff_company_id = getattr(current_user, "company_id", None)
        try:
            # DC Protocol: only credit-side ledger rows represent
            # *available* coupons issued to the member.
            sql = """
                SELECT l.id, l.transaction_type, l.quantity, l.notes, l.created_at,
                       p.partner_code
                  FROM vgk_coupon_ledger l
                  LEFT JOIN official_partners p ON p.id = l.partner_id
                 WHERE l.transaction_type IN
                       ('purchase_credit','admin_credit','transfer_in')
                   {pid}
                   {cid}
                 ORDER BY l.created_at DESC
                 LIMIT 200
            """.format(
                pid="AND l.partner_id = :pid" if partner_id else "",
                cid="AND p.company_id = :cid" if staff_company_id else "",
            )
            params: dict = {}
            if partner_id:
                params["pid"] = partner_id
            if staff_company_id:
                params["cid"] = staff_company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "code": f"VGK-CPN-{r[0]}",
                    "coupon_code": f"VGK-CPN-{r[0]}",
                    "discount": int(r[2] or 0),
                    "amount": int(r[2] or 0),
                    "transaction_type": r[1],
                    "status": r[1],
                    "notes": r[3],
                    "created_at": r[4].isoformat() if r[4] else None,
                    "partner_code": r[5],
                    "audience": "vgk4u",
                })
        except Exception as e:
            _log.warning(f"[VGK4U-MY-COUPONS] vgk_coupon_ledger query failed: {e}")

    # MNR branch is a placeholder until the EnhancedCoupon integration
    # lands. For audience='both' we still return the merged envelope below
    # so the VGK4U items aren't dropped; once EnhancedCoupon is wired the
    # MNR rows will be appended to ``items`` here.
    if aud == 'mnr':
        return {
            "available_coupons": [],
            "message": "Connect to EnhancedCoupon model to fetch user coupons"
        }
    return {
        "success": True,
        "audience": aud,
        "audience_label": audience_label(aud),
        "items": items,
        "coupons": items,
        "available_coupons": items,
        "count": len(items),
    }


@router.post("/redeem", response_model=EVRedemptionResponse)
async def redeem_ev_coupon(
    redemption: EVRedemptionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Redeem coupon for EV purchase or training"""
    
    # Generate unique request ID
    request_id = f"EVRED-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Validate coupon exists and belongs to user (placeholder - needs EnhancedCoupon integration)
    # For now, create redemption request
    
    new_redemption = EVRedemptionRequest(
        request_id=request_id,
        user_id=current_user.id,
        enhanced_coupon_id=0,  # Placeholder - need to lookup actual coupon
        coupon_code=redemption.coupon_code,
        ev_model=redemption.ev_model,
        redemption_type=redemption.redemption_type,
        redemption_amount=Decimal('15000'),  # Placeholder - get from coupon
        course_name=redemption.course_name,
        course_fee=redemption.course_fee,
        training_benefit_amount=redemption.course_fee * Decimal('0.2') if redemption.course_fee else None,
        status='Pending',
        admin_claim_status='pending',
        request_date=datetime.utcnow()
    )
    
    db.add(new_redemption)
    db.commit()
    db.refresh(new_redemption)
    
    return new_redemption


@router.get("/my-redemptions", response_model=List[EVRedemptionResponse])
async def get_my_redemptions(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's EV coupon redemption history"""
    query = db.query(EVRedemptionRequest).filter(
        EVRedemptionRequest.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(EVRedemptionRequest.status == status_filter)
    
    redemptions = query.order_by(EVRedemptionRequest.request_date.desc()).all()
    return redemptions


@router.get("/my-purchases", response_model=List[PurchaseResponse])
async def get_my_purchases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's EV purchase history"""
    purchases = db.query(Purchase).filter(
        Purchase.user_id == current_user.id
    ).order_by(Purchase.purchase_date.desc()).all()
    
    return purchases


@router.get("/training-courses", response_model=List[TrainingCourseResponse])
async def get_training_courses(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get available training courses for coupon redemption"""
    query = db.query(TrainingCourse)
    
    if active_only:
        query = query.filter(TrainingCourse.is_active == True)
    
    courses = query.all()
    return courses


@router.get("/my-stats")
async def get_my_ev_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's EV coupon statistics"""
    
    # Count redemptions
    total_redemptions = db.query(func.count(EVRedemptionRequest.id)).filter(
        EVRedemptionRequest.user_id == current_user.id
    ).scalar()
    
    pending_redemptions = db.query(func.count(EVRedemptionRequest.id)).filter(
        and_(
            EVRedemptionRequest.user_id == current_user.id,
            EVRedemptionRequest.status == 'Pending'
        )
    ).scalar()
    
    # Total discount received
    total_discount = db.query(func.coalesce(func.sum(Purchase.discount_amount), 0)).filter(
        Purchase.user_id == current_user.id
    ).scalar()
    
    return {
        "total_redemptions": total_redemptions,
        "pending_redemptions": pending_redemptions,
        "approved_redemptions": total_redemptions - pending_redemptions,
        "total_discount_received": float(total_discount) if total_discount else 0.0,
        "available_coupons": 0  # Placeholder - integrate with EnhancedCoupon
    }


# ===== ADMIN ENDPOINTS =====

@router.get("/admin/redemptions", response_model=List[EVRedemptionResponse])
async def get_all_redemptions(
    status_filter: Optional[str] = None,
    redemption_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all EV redemption requests (Admin)"""
    query = db.query(EVRedemptionRequest)
    
    if status_filter:
        query = query.filter(EVRedemptionRequest.status == status_filter)
    
    if redemption_type:
        query = query.filter(EVRedemptionRequest.redemption_type == redemption_type)
    
    redemptions = query.order_by(
        EVRedemptionRequest.request_date.desc()
    ).offset(offset).limit(limit).all()
    
    return redemptions


@router.post("/admin/redemptions/{redemption_id}/process")
async def process_redemption(
    redemption_id: int,
    approval: RedemptionApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Approve or reject EV redemption request (Admin)"""
    
    redemption = db.query(EVRedemptionRequest).filter(
        EVRedemptionRequest.id == redemption_id
    ).first()
    
    if not redemption:
        raise HTTPException(status_code=404, detail="Redemption request not found")
    
    if redemption.status != 'Pending':
        raise HTTPException(
            status_code=400,
            detail=f"Cannot process redemption in {redemption.status} status"
        )
    
    if approval.action == 'approve':
        redemption.status = 'Approved'
        redemption.admin_claim_status = 'approved'
        
        # Create purchase record if EV redemption
        if redemption.redemption_type == 'ev':
            # Find EV model
            ev = db.query(EV).filter(EV.model == redemption.ev_model).first()
            if ev:
                purchase = Purchase(
                    user_id=redemption.user_id,
                    ev_id=ev.id,
                    amount_redeemed=int(redemption.redemption_amount),
                    original_price=ev.price,
                    discount_amount=int(redemption.redemption_amount),
                    final_price=ev.price - int(redemption.redemption_amount),
                    enhanced_coupon_id=redemption.enhanced_coupon_id,
                    coupon_code=redemption.coupon_code,
                    status='Approved',
                    verified_by_admin_id=current_user.id,
                    verification_date=datetime.utcnow()
                )
                db.add(purchase)
        
        message = "Redemption approved successfully"
    else:
        redemption.status = 'Rejected'
        redemption.admin_claim_status = 'rejected'
        redemption.rejection_reason = approval.rejection_reason
        message = "Redemption rejected"
    
    redemption.processed_by_admin_id = current_user.id
    redemption.processed_date = datetime.utcnow()
    redemption.admin_notes = approval.admin_notes
    
    db.commit()
    db.refresh(redemption)
    
    return {
        "success": True,
        "message": message,
        "redemption": redemption
    }


@router.post("/admin/ev-models", response_model=EVResponse)
async def create_ev_model(
    ev_data: EVCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create new EV model (Admin)"""
    
    new_ev = EV(**ev_data.dict())
    db.add(new_ev)
    db.commit()
    db.refresh(new_ev)
    
    return new_ev


@router.put("/admin/ev-models/{ev_id}", response_model=EVResponse)
async def update_ev_model(
    ev_id: int,
    ev_data: EVCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update EV model (Admin)"""
    
    ev = db.query(EV).filter(EV.id == ev_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="EV model not found")
    
    for key, value in ev_data.dict().items():
        setattr(ev, key, value)
    
    ev.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ev)
    
    return ev


@router.get("/admin/ev-discount-stats")
async def get_admin_ev_discount_stats(
    audience: Optional[str] = Query(None, regex="^(mnr|vgk4u|both)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get EV discount system statistics (Admin).
    DC Protocol (Task #33): audience param OPTIONAL — when omitted, response
    is identical to the pre-Task-#33 contract.

    [DC_T33_SHARED_DATA_001] VGK4U EV discount data lives in the SAME
    EV / Purchase / EVRedemptionRequest tables as MNR. The audience flag
    is a UI-routing hint; the underlying counts are the canonical shared
    dataset for every audience value.
    """
    total_ev_models = db.query(func.count(EV.id)).scalar()
    available_ev_models = db.query(func.count(EV.id)).filter(EV.is_available == True).scalar()
    total_purchases = db.query(func.count(Purchase.id)).scalar()
    pending_redemptions = db.query(func.count(EVRedemptionRequest.id)).filter(
        EVRedemptionRequest.status == 'Pending'
    ).scalar()
    
    total_discount = db.query(func.coalesce(func.sum(Purchase.discount_amount), 0)).scalar()
    
    return {
        "total_ev_models": total_ev_models,
        "available_ev_models": available_ev_models,
        "total_purchases": total_purchases,
        "pending_redemptions": pending_redemptions,
        "total_discount_given": float(total_discount) if total_discount else 0.0
    }


@router.post("/admin/training-courses", response_model=TrainingCourseResponse)
async def create_training_course(
    course_data: TrainingCourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create new training course (Admin)"""
    
    new_course = TrainingCourse(**course_data.dict())
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    return new_course


@router.get("/admin/purchases", response_model=List[PurchaseResponse])
async def get_all_purchases(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all EV purchases (Admin)"""
    query = db.query(Purchase)
    
    if status_filter:
        query = query.filter(Purchase.status == status_filter)
    
    purchases = query.order_by(Purchase.purchase_date.desc()).offset(offset).limit(limit).all()
    return purchases


# ===== BENEFIT TRACKING ENDPOINTS =====

@router.get("/my-benefits")
async def get_my_benefits(
    benefit_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's benefit summary across all types"""
    return EVBenefitService.get_user_benefit_summary(db, current_user.id)


@router.get("/my-referral-income")
async def get_my_referral_income(
    status: Optional[str] = None,
    referral_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's referral income across EV/Insurance/Franchise/Fleet"""
    query = db.query(ReferralIncome).filter(
        ReferralIncome.earner_user_id == current_user.id
    )
    
    if status:
        query = query.filter(ReferralIncome.status == status)
    
    if referral_type:
        query = query.filter(ReferralIncome.referral_type == referral_type)
    
    incomes = query.order_by(ReferralIncome.earned_date.desc()).all()
    
    return {
        "referral_incomes": [{
            "id": inc.id,
            "referral_code": inc.referral_code,
            "referral_type": inc.referral_type,
            "purchaser_id": inc.purchaser_user_id,
            "purchase_amount": float(inc.purchase_amount),
            "commission_rate": float(inc.commission_rate),
            "commission_amount": float(inc.commission_amount),
            "status": inc.status,
            "earned_date": inc.earned_date.isoformat() if inc.earned_date else None,
            "approved_date": inc.approved_date.isoformat() if inc.approved_date else None,
            "paid_date": inc.paid_date.isoformat() if inc.paid_date else None
        } for inc in incomes],
        "total_count": len(incomes),
        "total_commission": sum(float(inc.commission_amount) for inc in incomes),
        "pending_commission": sum(float(inc.commission_amount) for inc in incomes if inc.status == 'Pending'),
        "approved_commission": sum(float(inc.commission_amount) for inc in incomes if inc.status == 'Approved'),
        "paid_commission": sum(float(inc.commission_amount) for inc in incomes if inc.status == 'Paid')
    }


# ===== FRANCHISE PURCHASE ENDPOINTS =====

@router.post("/franchise/purchase")
async def create_franchise_purchase(
    franchise_name: str,
    vehicle_model: str,
    vehicle_count: int,
    unit_price: float,
    gst_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create franchise EV purchase order"""
    
    franchise = EVBenefitService.create_franchise_purchase(
        db=db,
        franchisee_user_id=current_user.id,
        franchise_name=franchise_name,
        vehicle_model=vehicle_model,
        vehicle_count=vehicle_count,
        unit_price=Decimal(str(unit_price)),
        gst_number=gst_number
    )
    
    return {
        "success": True,
        "franchise_code": franchise.franchise_code,
        "message": f"Franchise purchase created successfully for {vehicle_count} units",
        "total_amount": float(franchise.total_amount),
        "commission_tier": franchise.commission_tier,
        "expected_commission": float(franchise.total_commission),
        "status": franchise.status
    }


@router.get("/franchise/my-purchases")
async def get_my_franchise_purchases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's franchise purchases"""
    purchases = db.query(FranchisePurchase).filter(
        FranchisePurchase.franchisee_user_id == current_user.id
    ).order_by(FranchisePurchase.order_date.desc()).all()
    
    return {
        "franchise_purchases": [{
            "id": p.id,
            "franchise_code": p.franchise_code,
            "franchise_name": p.franchise_name,
            "vehicle_model": p.vehicle_model,
            "vehicle_count": p.vehicle_count,
            "unit_price": float(p.unit_price),
            "total_amount": float(p.total_amount),
            "commission_tier": p.commission_tier,
            "commission_rate": float(p.commission_rate) if p.commission_rate else 0,
            "total_commission": float(p.total_commission) if p.total_commission else 0,
            "status": p.status,
            "order_date": p.order_date.isoformat() if p.order_date else None
        } for p in purchases]
    }


# ===== INSURANCE POLICY ENDPOINTS =====

@router.post("/insurance/policy")
async def create_insurance_policy(
    vehicle_registration: str,
    insurance_provider: str,
    policy_type: str,
    coverage_amount: float,
    premium_amount: float,
    policy_start_date: str,
    policy_end_date: str,
    referred_by_user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create insurance policy with optional referral"""
    
    policy = EVBenefitService.create_insurance_policy(
        db=db,
        user_id=current_user.id,
        vehicle_registration=vehicle_registration,
        insurance_provider=insurance_provider,
        policy_type=policy_type,
        coverage_amount=Decimal(str(coverage_amount)),
        premium_amount=Decimal(str(premium_amount)),
        policy_start_date=datetime.fromisoformat(policy_start_date),
        policy_end_date=datetime.fromisoformat(policy_end_date),
        referred_by_user_id=referred_by_user_id
    )
    
    return {
        "success": True,
        "policy_number": policy.policy_number,
        "message": "Insurance policy created successfully",
        "premium_amount": float(policy.premium_amount),
        "commission_to_referrer": float(policy.commission_amount) if policy.commission_amount else 0,
        "status": policy.status
    }


@router.get("/insurance/my-policies")
async def get_my_insurance_policies(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's insurance policies"""
    policies = db.query(InsurancePolicy).filter(
        InsurancePolicy.user_id == current_user.id
    ).order_by(InsurancePolicy.issue_date.desc()).all()
    
    return {
        "insurance_policies": [{
            "id": p.id,
            "policy_number": p.policy_number,
            "vehicle_registration": p.vehicle_registration,
            "insurance_provider": p.insurance_provider,
            "policy_type": p.policy_type,
            "coverage_amount": float(p.coverage_amount),
            "premium_amount": float(p.premium_amount),
            "policy_start_date": p.policy_start_date.isoformat() if p.policy_start_date else None,
            "policy_end_date": p.policy_end_date.isoformat() if p.policy_end_date else None,
            "status": p.status
        } for p in policies]
    }


# ===== FLEET ORDER ENDPOINTS =====

@router.post("/fleet/order")
async def create_fleet_order(
    company_name: str,
    gst_number: str,
    vehicle_model: str,
    quantity: int,
    unit_price: float,
    negotiated_discount: float = 0,
    primary_referrer_id: Optional[str] = None,
    secondary_referrer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create fleet/bulk EV order"""
    
    fleet_order = EVBenefitService.create_fleet_order(
        db=db,
        company_name=company_name,
        contact_person_user_id=current_user.id,
        gst_number=gst_number,
        vehicle_model=vehicle_model,
        quantity=quantity,
        unit_price=Decimal(str(unit_price)),
        negotiated_discount=Decimal(str(negotiated_discount)),
        primary_referrer_id=primary_referrer_id,
        secondary_referrer_id=secondary_referrer_id
    )
    
    return {
        "success": True,
        "fleet_order_number": fleet_order.fleet_order_number,
        "message": f"Fleet order created for {quantity} units",
        "total_order_value": float(fleet_order.total_order_value),
        "final_order_value": float(fleet_order.final_order_value),
        "tier_level": fleet_order.tier_level,
        "total_commission_pool": float(fleet_order.total_commission_pool),
        "status": fleet_order.status
    }


@router.get("/fleet/my-orders")
async def get_my_fleet_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get user's fleet orders"""
    orders = db.query(FleetOrder).filter(
        FleetOrder.contact_person_user_id == current_user.id
    ).order_by(FleetOrder.order_date.desc()).all()
    
    return {
        "fleet_orders": [{
            "id": o.id,
            "fleet_order_number": o.fleet_order_number,
            "company_name": o.company_name,
            "vehicle_model": o.vehicle_model,
            "quantity": o.quantity,
            "unit_price": float(o.unit_price),
            "total_order_value": float(o.total_order_value),
            "final_order_value": float(o.final_order_value),
            "tier_level": o.tier_level,
            "total_commission_pool": float(o.total_commission_pool) if o.total_commission_pool else 0,
            "status": o.status,
            "order_date": o.order_date.isoformat() if o.order_date else None
        } for o in orders]
    }


# ===== ADMIN BENEFIT MANAGEMENT =====

@router.get("/admin/benefit-analytics")
async def get_benefit_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get system-wide benefit analytics (Admin)"""
    return EVBenefitService.get_admin_benefit_analytics(db)


@router.post("/admin/approve-referral-income/{income_id}")
async def approve_referral_income(
    income_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Approve referral income (Admin)"""
    
    income = db.query(ReferralIncome).filter(ReferralIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Referral income not found")
    
    if income.status != 'Pending':
        raise HTTPException(status_code=400, detail=f"Cannot approve income with status: {income.status}")
    
    income.status = 'Approved'
    income.approved_by = current_user.id
    income.approved_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Referral income ₹{income.commission_amount} approved",
        "income_id": income.id,
        "referral_code": income.referral_code
    }


@router.get("/admin/franchise-purchases")
async def get_all_franchise_purchases(
    status_filter: Optional[str] = None,
    audience: Optional[str] = Query(None, regex="^(mnr|vgk4u|both)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all franchise purchases (Admin).
    DC Protocol (Task #33): audience param OPTIONAL — when omitted, response
    is identical to the pre-Task-#33 contract.

    [DC_T33_SHARED_DATA_001] VGK4U franchise purchases live in the SAME
    FranchisePurchase table as MNR. The audience flag is a UI-routing
    hint; the underlying query returns the canonical shared dataset for
    every audience value.
    """
    query = db.query(FranchisePurchase)
    
    if status_filter:
        query = query.filter(FranchisePurchase.status == status_filter)
    
    purchases = query.order_by(FranchisePurchase.order_date.desc()).all()
    
    return {
        "franchise_purchases": [{
            "id": p.id,
            "franchise_code": p.franchise_code,
            "franchisee_user_id": p.franchisee_user_id,
            "franchise_name": p.franchise_name,
            "vehicle_model": p.vehicle_model,
            "vehicle_count": p.vehicle_count,
            "total_amount": float(p.total_amount),
            "commission_tier": p.commission_tier,
            "total_commission": float(p.total_commission) if p.total_commission else 0,
            "status": p.status,
            "order_date": p.order_date.isoformat() if p.order_date else None
        } for p in purchases],
        "total_count": len(purchases)
    }


@router.post("/admin/approve-franchise/{franchise_id}")
async def approve_franchise_purchase(
    franchise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Approve franchise purchase (Admin)"""
    
    franchise = db.query(FranchisePurchase).filter(FranchisePurchase.id == franchise_id).first()
    if not franchise:
        raise HTTPException(status_code=404, detail="Franchise purchase not found")
    
    if franchise.status != 'Pending':
        raise HTTPException(status_code=400, detail=f"Cannot approve purchase with status: {franchise.status}")
    
    franchise.status = 'Approved'
    franchise.approval_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Franchise purchase {franchise.franchise_code} approved",
        "franchise_id": franchise.id
    }


@router.get("/admin/fleet-orders")
async def get_all_fleet_orders(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all fleet orders (Admin)"""
    query = db.query(FleetOrder)
    
    if status_filter:
        query = query.filter(FleetOrder.status == status_filter)
    
    orders = query.order_by(FleetOrder.order_date.desc()).all()
    
    return {
        "fleet_orders": [{
            "id": o.id,
            "fleet_order_number": o.fleet_order_number,
            "company_name": o.company_name,
            "contact_person_user_id": o.contact_person_user_id,
            "vehicle_model": o.vehicle_model,
            "quantity": o.quantity,
            "final_order_value": float(o.final_order_value),
            "tier_level": o.tier_level,
            "total_commission_pool": float(o.total_commission_pool) if o.total_commission_pool else 0,
            "status": o.status,
            "order_date": o.order_date.isoformat() if o.order_date else None
        } for o in orders],
        "total_count": len(orders)
    }
