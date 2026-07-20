"""
MyntReal & Zynova Incentive System API Endpoints
DC Protocol: All endpoints enforce company-wise data segregation
Supports MNR Points system, category-based incentives, and VGK4U hierarchical structure
Created: December 28, 2025
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, case
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models import (
    User, MNRPointsBalance, MNRPointsTransaction, MyntRealIncentive,
    ZynovaMember, ZynovaIncentive, MyntRealIncentiveRate,
    SignupCategory, AssociatedCompany
)
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead, CRMLeadTransaction
from app.models.transaction import PendingIncome
from decimal import Decimal

import pytz

router = APIRouter()


def get_indian_time():
    """Get current datetime in Indian Standard Time"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


def get_company_id_from_staff(staff: StaffEmployee) -> int:
    """Derive company_id from staff employee - DC Protocol compliant"""
    return staff.base_company_id or 1


def get_company_id_from_user(db: Session, user: User) -> int:
    """Derive company_id from MNR user - DC Protocol compliant"""
    if hasattr(user, 'company_id') and user.company_id:
        return user.company_id
    company = db.query(AssociatedCompany).first()
    return company.id if company else 1

# DC Protocol (Dec 28, 2025): Receipt number generator for MNR Points
# Format: MNR + 2-digit sequence + last 4 digits of MNR ID
# Example: MNR030525 (sequence 03, MNR ID ends with 0525)
def generate_receipt_number(db: Session, user_id: str) -> str:
    """
    Generate unique receipt number for MNR Points allocation
    Format: MNR{sequence:02d}{last4digits}
    Sequence starts from 01 for allocations from Dec 1, 2025
    """
    # Get count of existing receipts (allocations since Dec 1, 2025)
    dec_1_2025 = datetime(2025, 12, 1, 0, 0, 0)
    existing_count = db.query(func.count(MNRPointsBalance.id)).filter(
        MNRPointsBalance.receipt_no.isnot(None),
        MNRPointsBalance.created_at >= dec_1_2025
    ).scalar() or 0
    
    # Next sequence number (starting from 01)
    sequence = existing_count + 1
    
    # Get last 4 digits of MNR ID
    last_4 = user_id[-4:] if len(user_id) >= 4 else user_id.zfill(4)
    
    # Generate receipt number: MNR + sequence (2 digits) + last 4 of MNR ID
    receipt_no = f"MNR{sequence:02d}{last_4}"
    
    return receipt_no


def calculate_expiry_date(activation_date: datetime = None) -> datetime:
    """
    Calculate points expiry date - 24 months from activation
    DC Protocol: Points expire 24 months from allocation
    """
    base_date = activation_date or get_indian_time()
    return base_date + timedelta(days=730)  # ~24 months


# DC Protocol (Feb 8, 2026): Points allocation doubled - based on coupon type
# Platinum: 30,000 | Diamond: 15,000 | Star: 2,000 | Loyal: 2,000 | No coupon: 1,000
# DC Protocol (Feb 18, 2026): Welcome Coupon always gets 15,000 points (not 30,000)
def get_points_for_package(user: User) -> tuple:
    """
    Get points allocation based on user's package type and coupon status.
    Returns: (points, package_name, is_coupon_paid)
    
    Rules (DC Protocol Feb 8, 2026 - Doubled):
    - Welcome Coupon: Always 15,000 points regardless of package_points
    - Platinum (package_points >= 1.0): 30,000 points
    - Diamond (package_points >= 0.5): 15,000 points
    - Star/Loyal (package_points > 0): 2,000 points
    - No coupon (coupon_status not in ['Active', 'Activated']): 1,000 points (default)
    """
    is_coupon_paid = user.coupon_status in ('Active', 'Activated')
    package_points = user.package_points if user.package_points else 0
    is_welcome_coupon = getattr(user, 'is_welcome_coupon', False)
    
    if not is_coupon_paid:
        return (1000, 'Default', False)
    
    if is_welcome_coupon:
        return (15000, 'Welcome Coupon', True)
    
    if package_points >= 1.0:
        return (30000, 'Platinum', True)
    elif package_points >= 0.5:
        return (15000, 'Diamond', True)
    elif package_points > 0:
        return (2000, 'Star/Loyal', True)
    else:
        return (1000, 'Default', True)




class PointsAdjustRequest(BaseModel):
    user_id: str = Field(..., description="MNR User ID")
    amount: float = Field(..., description="Amount to adjust (positive for credit, negative for debit)")
    description: str = Field(..., description="Reason for adjustment")


class PointsBalanceResponse(BaseModel):
    user_id: str
    initial_points: float
    current_balance: float
    total_consumed: float
    total_credited: float


@router.get("/points/me", summary="Get current user's MNR points balance")
async def get_my_points_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's MNR points balance
    DC Protocol: Uses MNR session priority for dual-login scenarios
    Includes member data for payment slip and expiry calculation
    
    Updated Jan 12, 2026: Added is_coupon_paid, expected_points, package_name
    - Receipt only available when coupon is paid (coupon_status='Active' or 'Activated')
    - Points based on package: Platinum=30000, Diamond=15000, Star/Loyal=2000, Default=1000
    """
    points_balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == current_user.id
    ).first()
    
    # DC Protocol (Jan 12, 2026): Get points based on coupon type
    expected_points, package_name, is_coupon_paid = get_points_for_package(current_user)
    
    is_welcome_coupon = getattr(current_user, 'is_welcome_coupon', False)
    
    member_data = {
        "name": current_user.name,
        "mnr_id": current_user.id,
        "activation_date": current_user.activation_date.isoformat() if current_user.activation_date else None,
        "coupon_purchase_date": current_user.coupon_status_changed_at.isoformat() if getattr(current_user, 'coupon_status_changed_at', None) else None,
        "coupon_status": current_user.coupon_status,
        "is_coupon_paid": is_coupon_paid,
        "package_name": package_name,
        "expected_points": expected_points,
        "is_welcome_coupon": is_welcome_coupon
    }
    
    if not points_balance:
        return {
            "success": True,
            "data": {
                "user_id": current_user.id,
                "initial_points": expected_points,
                "current_balance": expected_points if is_coupon_paid else 0,
                "total_consumed": 0,
                "total_credited": 0,
                "receipt_no": None,
                "expiry_date": None,
                "is_initialized": False,
                "is_coupon_paid": is_coupon_paid,
                "is_welcome_coupon": is_welcome_coupon,
                "receipt_downloadable": is_coupon_paid and not is_welcome_coupon,
                "package_name": package_name,
                "member": member_data
            }
        }
    
    return {
        "success": True,
        "data": {
            "user_id": points_balance.user_id,
            "initial_points": points_balance.initial_points if not is_welcome_coupon else expected_points,
            "current_balance": points_balance.current_balance,
            "total_consumed": points_balance.total_consumed,
            "total_credited": points_balance.total_credited,
            "receipt_no": points_balance.receipt_no if is_coupon_paid and not is_welcome_coupon else None,
            "expiry_date": points_balance.expiry_date.isoformat() if points_balance.expiry_date else None,
            "is_initialized": True,
            "is_coupon_paid": is_coupon_paid,
            "is_welcome_coupon": is_welcome_coupon,
            "receipt_downloadable": is_coupon_paid and not is_welcome_coupon,
            "package_name": package_name,
            "member": member_data
        }
    }


@router.get("/points/me/history", summary="Get current user's points transaction history")
async def get_my_points_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's MNR points transaction history
    DC Protocol: Uses MNR session priority for dual-login scenarios
    """
    query = db.query(MNRPointsTransaction).filter(
        MNRPointsTransaction.user_id == current_user.id
    ).order_by(MNRPointsTransaction.created_at.desc())
    
    total = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()
    
    transaction_list = []
    for txn in transactions:
        category_name = None
        if txn.category_id:
            cat = db.query(SignupCategory).filter(SignupCategory.id == txn.category_id).first()
            if cat:
                category_name = cat.name
        
        _txn_labels = {
            "initial_allocation": "Points Allocation",
            "consumption": "Points Used",
            "refund": "Points Refund",
            "credit": "Reference Bonus",
            "reference_bonus": "Reference Bonus",
            "debit": "Debit",
            "realignment": "Balance Realignment",
            "realignment_credit": "Realignment Credit",
            "discount_used": "VGK Discount Used",
            "admin_credit": "Admin Credit",
            "admin_debit": "Admin Debit",
        }
        transaction_list.append({
            "id": txn.id,
            "transaction_type": txn.transaction_type,
            "display_label": _txn_labels.get(txn.transaction_type, txn.transaction_type.replace("_", " ").title()),
            "amount": txn.amount,
            "balance_after": txn.balance_after,
            "category_id": txn.category_id,
            "category_name": category_name,
            "lead_id": txn.lead_id,
            "description": txn.description,
            "created_at": txn.created_at.isoformat() if txn.created_at else None
        })
    
    return {
        "success": True,
        "data": transaction_list,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/points/all", summary="List all users with points (Staff/Admin only)")
async def list_all_points_balances(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    kyc_status: Optional[str] = Query(None, description="Filter by KYC status: Pending, Submitted, Approved, Rejected"),
    package_type: Optional[str] = Query(None, description="Filter by package: Platinum, Diamond, Star, Loyal"),
    coupon_status: Optional[str] = Query(None, description="Filter by coupon status: Active, Activated, Inactive"),
    activation_status: Optional[str] = Query(None, description="Filter by activation: activated, not_activated"),
    reg_start: Optional[str] = Query(None, description="Registration date start (YYYY-MM-DD)"),
    reg_end: Optional[str] = Query(None, description="Registration date end (YYYY-MM-DD)"),
    act_start: Optional[str] = Query(None, description="Activation date start (YYYY-MM-DD)"),
    act_end: Optional[str] = Query(None, description="Activation date end (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query(None, description="Sort field: user_name, mnr_id, registration_date, activation_date, total_allocated, current_balance, total_consumed"),
    sort_dir: Optional[str] = Query("asc", description="Sort direction: asc or desc"),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all users with their MNR points balances
    DC Protocol: Staff access with pagination and enhanced filters
    """
    query = db.query(MNRPointsBalance, User).join(
        User, MNRPointsBalance.user_id == User.id
    )
    
    if search:
        search_term = search.strip()
        query = query.filter(
            or_(
                func.upper(User.id).like(func.upper(f"%{search_term}%")),
                func.upper(User.name).like(func.upper(f"%{search_term}%"))
            )
        )
    
    if kyc_status:
        query = query.filter(func.lower(User.kyc_status) == kyc_status.lower())
    
    if package_type:
        pt = package_type.lower()
        if pt == 'platinum':
            query = query.filter(User.package_points >= 1.0)
        elif pt == 'diamond':
            query = query.filter(User.package_points >= 0.5, User.package_points < 1.0)
        elif pt in ('star', 'loyal'):
            query = query.filter(or_(User.package_points < 0.5, User.package_points == None))
    
    if coupon_status:
        query = query.filter(func.lower(User.coupon_status) == coupon_status.lower())
    
    if activation_status:
        if activation_status == 'activated':
            query = query.filter(User.account_status == 'activated')
        elif activation_status == 'not_activated':
            query = query.filter(or_(User.account_status != 'activated', User.account_status.is_(None)))

    if reg_start:
        try:
            query = query.filter(User.registration_date >= datetime.strptime(reg_start, '%Y-%m-%d'))
        except ValueError:
            pass
    if reg_end:
        try:
            query = query.filter(User.registration_date <= datetime.strptime(reg_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    if act_start:
        try:
            query = query.filter(User.activation_date >= datetime.strptime(act_start, '%Y-%m-%d'))
        except ValueError:
            pass
    if act_end:
        try:
            query = query.filter(User.activation_date <= datetime.strptime(act_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    
    total = query.count()
    
    sort_column_map = {
        'user_name': User.name,
        'mnr_id': User.id,
        'registration_date': User.registration_date,
        'activation_date': User.activation_date,
        'total_allocated': MNRPointsBalance.initial_points,
        'current_balance': MNRPointsBalance.current_balance,
        'total_consumed': MNRPointsBalance.total_consumed,
        'receipt_no': MNRPointsBalance.receipt_no,
    }
    order_col = sort_column_map.get(sort_by, User.name)
    if sort_dir and sort_dir.lower() == 'desc':
        order_col = order_col.desc()
    
    results = query.order_by(order_col).offset((page - 1) * per_page).limit(per_page).all()
    
    agg_result = db.query(
        func.sum(MNRPointsBalance.initial_points),
        func.sum(MNRPointsBalance.current_balance),
        func.sum(MNRPointsBalance.total_consumed)
    ).first()
    agg_allocated = float(agg_result[0] or 0) if agg_result else 0
    agg_balance = float(agg_result[1] or 0) if agg_result else 0
    agg_consumed = float(agg_result[2] or 0) if agg_result else 0
    
    data = []
    for balance, user in results:
        if not balance or not user:
            continue
        expected_points, package_name, is_coupon_paid = get_points_for_package(user)
        
        data.append({
            "user_id": user.id,
            "mnr_id": user.id,
            "user_name": user.name,
            "mobile": getattr(user, 'mobile', None),
            "initial_points": balance.initial_points,
            "total_allocated": balance.initial_points,
            "current_balance": balance.current_balance,
            "total_consumed": balance.total_consumed,
            "total_credited": balance.total_credited,
            "receipt_no": balance.receipt_no if is_coupon_paid else None,
            "expiry_date": balance.expiry_date.isoformat() if balance.expiry_date else None,
            "updated_at": balance.updated_at.isoformat() if hasattr(balance, 'updated_at') and balance.updated_at else None,
            "activation_date": user.activation_date.isoformat() if user.activation_date else None,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "kyc_status": getattr(user, 'kyc_status', 'Pending') or 'Pending',
            "is_coupon_paid": is_coupon_paid,
            "package_name": package_name,
            "coupon_status": user.coupon_status
        })
    
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        },
        "aggregate_stats": {
            "total_allocated": agg_allocated,
            "total_balance": agg_balance,
            "total_consumed": agg_consumed
        }
    }


@router.get("/points/{user_id}", summary="Get a user's MNR points balance (Staff/Admin only)")
async def get_user_points_balance(
    user_id: str,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get a specific user's MNR points balance
    DC Protocol: Staff access with company validation
    
    Updated Jan 12, 2026: Uses coupon-based points allocation
    - Receipt only shown when coupon is paid (coupon_status='Active')
    - Points based on package: Platinum=30000, Diamond=15000, Star/Loyal=2000, Default=1000
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol (Jan 12, 2026): Get points based on coupon type
    expected_points, package_name, is_coupon_paid = get_points_for_package(user)
    is_welcome_coupon = getattr(user, 'is_welcome_coupon', False)
    
    points_balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == user_id
    ).first()
    
    if not points_balance:
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "user_name": user.name,
                "initial_points": expected_points,
                "current_balance": expected_points if is_coupon_paid else 0,
                "total_consumed": 0,
                "total_credited": 0,
                "is_initialized": False,
                "is_coupon_paid": is_coupon_paid,
                "is_welcome_coupon": is_welcome_coupon,
                "receipt_downloadable": is_coupon_paid and not is_welcome_coupon,
                "package_name": package_name,
                "coupon_status": user.coupon_status
            }
        }
    
    return {
        "success": True,
        "data": {
            "user_id": points_balance.user_id,
            "user_name": user.name,
            "initial_points": points_balance.initial_points if not is_welcome_coupon else expected_points,
            "current_balance": points_balance.current_balance,
            "total_consumed": points_balance.total_consumed,
            "total_credited": points_balance.total_credited,
            "receipt_no": points_balance.receipt_no if is_coupon_paid and not is_welcome_coupon else None,
            "expiry_date": points_balance.expiry_date.isoformat() if points_balance.expiry_date else None,
            "is_initialized": True,
            "is_coupon_paid": is_coupon_paid,
            "is_welcome_coupon": is_welcome_coupon,
            "receipt_downloadable": is_coupon_paid and not is_welcome_coupon,
            "package_name": package_name,
            "coupon_status": user.coupon_status
        }
    }


@router.get("/points/{user_id}/history", summary="Get a user's points history (Staff/Admin only)")
async def get_user_points_history(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get a specific user's MNR points transaction history
    DC Protocol: Staff access with company validation
    """
    query = db.query(MNRPointsTransaction).filter(
        MNRPointsTransaction.user_id == user_id
    ).order_by(MNRPointsTransaction.created_at.desc())
    
    total = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()
    
    transaction_list = []
    for txn in transactions:
        category_name = None
        if txn.category_id:
            cat = db.query(SignupCategory).filter(SignupCategory.id == txn.category_id).first()
            if cat:
                category_name = cat.name
        
        transaction_list.append({
            "id": txn.id,
            "transaction_type": txn.transaction_type,
            "amount": txn.amount,
            "balance_after": txn.balance_after,
            "category_id": txn.category_id,
            "category_name": category_name,
            "lead_id": txn.lead_id,
            "description": txn.description,
            "created_by_id": txn.created_by_id,
            "created_by_type": txn.created_by_type,
            "created_at": txn.created_at.isoformat() if txn.created_at else None
        })
    
    return {
        "success": True,
        "data": transaction_list,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.post("/points/initialize/{user_id}", summary="Initialize points balance for a user")
async def initialize_user_points(
    user_id: str,
    initial_points: float = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Initialize MNR points balance for a user
    DC Protocol: Staff access with VGK/Finance role check
    Updated Dec 28, 2025: Generates receipt number and expiry date
    
    Updated Jan 12, 2026: Points based on coupon type
    - Platinum: 30,000 | Diamond: 15,000 | Star/Loyal: 2,000 | Default: 1,000
    - Receipt number only generated when coupon is paid (coupon_status='Active')
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = db.query(MNRPointsBalance).filter(MNRPointsBalance.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Points balance already initialized for this user")
    
    company_id = get_company_id_from_staff(current_staff)
    
    # DC Protocol (Jan 12, 2026): Get points based on coupon type
    expected_points, package_name, is_coupon_paid = get_points_for_package(user)
    
    # Use provided initial_points if staff override, otherwise use expected_points
    final_points = initial_points if initial_points is not None else expected_points
    
    # Only generate receipt if coupon is paid
    receipt_no = generate_receipt_number(db, user_id) if is_coupon_paid else None
    expiry_date = calculate_expiry_date(user.activation_date if hasattr(user, 'activation_date') else None)
    
    points_balance = MNRPointsBalance(
        company_id=company_id,
        user_id=user_id,
        initial_points=final_points,
        current_balance=final_points,
        total_consumed=0,
        total_credited=0,
        receipt_no=receipt_no,
        expiry_date=expiry_date
    )
    db.add(points_balance)
    
    # Always create transaction entry
    description = f"Initial allocation of {final_points} MNR points ({package_name} package)"
    if receipt_no:
        description += f" (Receipt: {receipt_no})"
    
    txn = MNRPointsTransaction(
        company_id=company_id,
        user_id=user_id,
        transaction_type="initial_allocation",
        amount=final_points,
        balance_after=final_points,
        description=description,
        created_by_id=str(current_staff.id),
        created_by_type="staff"
    )
    db.add(txn)
    
    db.commit()
    
    result_data = points_balance.to_dict()
    result_data['is_coupon_paid'] = is_coupon_paid
    result_data['package_name'] = package_name
    
    return {
        "success": True,
        "message": f"Initialized {final_points} MNR points for user {user_id} ({package_name} package)" + (f" (Receipt: {receipt_no})" if receipt_no else " (No receipt - coupon not paid)"),
        "data": result_data
    }


@router.post("/points/adjust", summary="Manually adjust user's points balance (VGK/Finance only)")
async def adjust_user_points(
    request: PointsAdjustRequest = Body(...),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Manually adjust a user's MNR points balance (credit or debit)
    DC Protocol: VGK/Finance only with audit trail
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    points_balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == request.user_id
    ).first()
    
    company_id = get_company_id_from_staff(current_staff)
    
    if not points_balance:
        # DC Protocol (Jan 12, 2026): Use coupon-based points allocation
        expected_points, package_name, is_coupon_paid = get_points_for_package(user)
        receipt_no = generate_receipt_number(db, request.user_id) if is_coupon_paid else None
        
        points_balance = MNRPointsBalance(
            company_id=company_id,
            user_id=request.user_id,
            initial_points=expected_points,
            current_balance=expected_points,
            total_consumed=0,
            total_credited=0,
            receipt_no=receipt_no
        )
        db.add(points_balance)
        db.flush()
        
        description = f"Auto-initialized {expected_points} points ({package_name} package)"
        if receipt_no:
            description += f" (Receipt: {receipt_no})"
        
        init_txn = MNRPointsTransaction(
            company_id=company_id,
            user_id=request.user_id,
            transaction_type="initial_allocation",
            amount=expected_points,
            balance_after=expected_points,
            description=description,
            created_by_id=str(current_staff.id),
            created_by_type="staff"
        )
        db.add(init_txn)
    
    new_balance = points_balance.current_balance + request.amount
    
    if new_balance < 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance. Current: {points_balance.current_balance}, Requested debit: {abs(request.amount)}"
        )
    
    transaction_type = "credit" if request.amount > 0 else "debit"
    
    points_balance.current_balance = new_balance
    if request.amount > 0:
        points_balance.total_credited += request.amount
    else:
        points_balance.total_consumed += abs(request.amount)
    
    txn = MNRPointsTransaction(
        company_id=company_id,
        user_id=request.user_id,
        transaction_type=transaction_type,
        amount=request.amount,
        balance_after=new_balance,
        description=request.description,
        created_by_id=str(current_staff.id),
        created_by_type="staff"
    )
    db.add(txn)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Points adjusted successfully. New balance: {new_balance}",
        "data": {
            "user_id": request.user_id,
            "adjustment": request.amount,
            "new_balance": new_balance,
            "transaction_type": transaction_type
        }
    }


@router.post("/points/initialize-all", summary="Bulk initialize points for all active users (VGK only)")
async def bulk_initialize_points(
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Bulk initialize MNR points for ALL active users who don't have points yet
    DC Protocol: VGK/Finance access only
    
    Updated Jan 12, 2026: Uses coupon-based points allocation
    - Platinum: 30,000 | Diamond: 15,000 | Star/Loyal: 2,000 | Default: 1,000
    - Receipt only generated when coupon is paid (coupon_status='Active')
    """
    company_id = get_company_id_from_staff(current_staff)
    
    existing_user_ids = db.query(MNRPointsBalance.user_id).all()
    existing_ids = {uid[0] for uid in existing_user_ids}
    
    active_users = db.query(User).filter(
        User.activation_date.isnot(None),
        ~User.id.in_(existing_ids) if existing_ids else True
    ).all()
    
    if not active_users:
        return {
            "success": True,
            "message": "All active users already have points initialized",
            "initialized_count": 0,
            "stats": {}
        }
    
    initialized_count = 0
    stats = {"Platinum": 0, "Diamond": 0, "Star/Loyal": 0, "Default": 0}
    
    for user in active_users:
        # DC Protocol (Jan 12, 2026): Use coupon-based points allocation
        expected_points, package_name, is_coupon_paid = get_points_for_package(user)
        receipt_no = generate_receipt_number(db, user.id) if is_coupon_paid else None
        expiry_date = calculate_expiry_date(user.activation_date)
        
        points_balance = MNRPointsBalance(
            company_id=company_id,
            user_id=user.id,
            initial_points=expected_points,
            current_balance=expected_points,
            total_consumed=0,
            total_credited=0,
            receipt_no=receipt_no,
            expiry_date=expiry_date
        )
        db.add(points_balance)
        db.flush()
        
        description = f"Bulk allocation of {int(expected_points)} MNR points ({package_name} package)"
        if receipt_no:
            description += f" (Receipt: {receipt_no})"
        
        txn = MNRPointsTransaction(
            company_id=company_id,
            user_id=user.id,
            transaction_type="initial_allocation",
            amount=expected_points,
            balance_after=expected_points,
            description=description,
            created_by_id=str(current_staff.id),
            created_by_type="staff"
        )
        db.add(txn)
        initialized_count += 1
        stats[package_name] = stats.get(package_name, 0) + 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Initialized points for {initialized_count} active users based on coupon type",
        "initialized_count": initialized_count,
        "stats": stats
    }


@router.post("/points/backfill-receipts", summary="Backfill receipt numbers for existing records (Admin only)")
async def backfill_receipt_numbers(
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Backfill receipt numbers for existing MNR points records
    DC Protocol: Admin-only with batch processing to prevent timeout
    
    Updated Jan 12, 2026: Only generates receipts for users with coupon paid
    Users without coupon payment will have their receipt_no cleared
    """
    total_count = db.query(MNRPointsBalance).count()
    if total_count == 0:
        return {
            "success": True,
            "message": "No records to process",
            "updated_count": 0,
            "stats": {}
        }
    
    updated_count = 0
    stats = {"receipts_added": 0, "receipts_cleared": 0, "unchanged": 0}
    BATCH_SIZE = 50
    processed = 0
    
    while processed < total_count:
        records = db.query(MNRPointsBalance, User).join(
            User, MNRPointsBalance.user_id == User.id
        ).order_by(MNRPointsBalance.id).offset(processed).limit(BATCH_SIZE).all()
        
        if not records:
            break
        
        for record, user in records:
            if not user:
                continue
            
            expected_points, package_name, is_coupon_paid = get_points_for_package(user)
            expiry_date = calculate_expiry_date(user.activation_date if user.activation_date else record.created_at)
            
            if is_coupon_paid:
                if not record.receipt_no:
                    record.receipt_no = generate_receipt_number(db, record.user_id)
                    stats["receipts_added"] += 1
                    updated_count += 1
                else:
                    stats["unchanged"] += 1
            else:
                if record.receipt_no:
                    record.receipt_no = None
                    stats["receipts_cleared"] += 1
                    updated_count += 1
                else:
                    stats["unchanged"] += 1
            
            record.expiry_date = expiry_date
        
        db.commit()
        processed += len(records)
    
    return {
        "success": True,
        "message": f"Processed {processed} records, updated {updated_count}",
        "updated_count": updated_count,
        "stats": stats
    }


@router.post("/points/realign-balances", summary="Realign all points balances with coupon-based rules (Admin only)")
async def realign_points_balances(
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Realign all existing MNR points balances with coupon-based allocation rules
    DC Protocol: VGK/Admin-only - Updates initial_points based on coupon type
    
    WARNING: This will update initial_points values for existing records
    - Platinum: 30,000 | Diamond: 15,000 | Star/Loyal: 2,000 | Default: 1,000
    - Receipt only retained when coupon is paid (coupon_status='Active')
    """
    company_id = get_company_id_from_staff(current_staff)
    
    records = db.query(MNRPointsBalance).all()
    
    if not records:
        return {
            "success": True,
            "message": "No records to realign",
            "realigned_count": 0,
            "stats": {}
        }
    
    realigned_count = 0
    stats = {"Platinum": 0, "Diamond": 0, "Star/Loyal": 0, "Default": 0, "unchanged": 0}
    adjustments = []
    
    for record in records:
        user = db.query(User).filter(User.id == record.user_id).first()
        if not user:
            continue
        
        expected_points, package_name, is_coupon_paid = get_points_for_package(user)
        old_initial = record.initial_points
        
        if record.initial_points != expected_points:
            record.initial_points = expected_points
            natural_balance = expected_points + record.total_credited - record.total_consumed
            
            if natural_balance < 0:
                overshoot_credit = abs(natural_balance)
                record.total_credited += overshoot_credit
                record.current_balance = 0
                
                overshoot_txn = MNRPointsTransaction(
                    company_id=company_id,
                    user_id=user.id,
                    transaction_type="realignment_credit",
                    amount=overshoot_credit,
                    balance_after=0,
                    description=f"Realignment write-off credit: {package_name} package (consumed more than new tier allows)",
                    created_by_id=str(current_staff.id),
                    created_by_type="staff"
                )
                db.add(overshoot_txn)
            else:
                record.current_balance = natural_balance
            
            if is_coupon_paid:
                if not record.receipt_no:
                    record.receipt_no = generate_receipt_number(db, record.user_id)
            else:
                record.receipt_no = None
            
            txn = MNRPointsTransaction(
                company_id=company_id,
                user_id=user.id,
                transaction_type="realignment",
                amount=expected_points - old_initial,
                balance_after=record.current_balance,
                description=f"Realignment: {package_name} package ({int(old_initial)} -> {int(expected_points)} points)",
                created_by_id=str(current_staff.id),
                created_by_type="staff"
            )
            db.add(txn)
            
            adjustments.append({
                "user_id": user.id,
                "old_points": old_initial,
                "new_points": expected_points,
                "package": package_name,
                "adjustment": expected_points - old_initial
            })
            
            realigned_count += 1
            stats[package_name] = stats.get(package_name, 0) + 1
        else:
            stats["unchanged"] += 1
        
        db.flush()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Realigned {realigned_count} records based on coupon type",
        "realigned_count": realigned_count,
        "stats": stats,
        "sample_adjustments": adjustments[:10]
    }


@router.get("/incentive-rates", summary="Get all incentive rate configurations")
async def get_incentive_rates(
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all MyntReal incentive rate configurations
    DC Protocol: Staff access
    """
    query = db.query(MyntRealIncentiveRate)
    
    if company_id:
        query = query.filter(MyntRealIncentiveRate.company_id == company_id)
    
    rates = query.filter(MyntRealIncentiveRate.is_active == True).all()
    
    return {
        "success": True,
        "data": [rate.to_dict() for rate in rates]
    }


@router.get("/my-incentives", summary="Get current user's MyntReal incentives")
async def get_my_incentives(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's MyntReal incentives
    DC Protocol: Uses MNR session priority for dual-login scenarios
    """
    query = db.query(MyntRealIncentive).filter(
        or_(
            MyntRealIncentive.mnr_id == current_user.id,
            MyntRealIncentive.guru_id == current_user.id,
            MyntRealIncentive.adiguru_id == current_user.id
        )
    )
    
    if status_filter:
        query = query.filter(MyntRealIncentive.status == status_filter)
    
    total = query.count()
    incentives = query.order_by(MyntRealIncentive.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    data = []
    for inc in incentives:
        role = "promoter"
        amount = inc.mnr_amount or 0
        if inc.guru_id == current_user.id:
            role = "guru"
            amount = inc.guru_amount or 0
        elif inc.adiguru_id == current_user.id:
            role = "adi_guru"
            amount = inc.adiguru_amount or 0
        
        lead = db.query(CRMLead).filter(CRMLead.id == inc.lead_id).first()
        lead_name = lead.name if lead else "Unknown"
        
        category = db.query(SignupCategory).filter(SignupCategory.id == inc.category_id).first()
        category_name = category.name if category else "Unknown"
        
        data.append({
            "id": inc.id,
            "lead_id": inc.lead_id,
            "lead_name": lead_name,
            "category_name": category_name,
            "revenue_amount": inc.revenue_amount,
            "role": role,
            "your_incentive": amount,
            "calculation_mode": inc.calculation_mode,
            "points_consumed": inc.points_consumed,
            "status": inc.status,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        })
    
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/my-zynova-incentives", summary="Get current user's VGK4U incentives")
async def get_my_zynova_incentives(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's Zynova incentives (Insurance/Real Estate/Training)
    DC Protocol: Uses MNR session priority for dual-login scenarios
    """
    query = db.query(ZynovaIncentive).filter(
        or_(
            ZynovaIncentive.promoter_id == current_user.id,
            ZynovaIncentive.team_leader_id == current_user.id,
            ZynovaIncentive.zonal_manager_id == current_user.id,
            ZynovaIncentive.director_id == current_user.id
        )
    )
    
    if status_filter:
        query = query.filter(ZynovaIncentive.status == status_filter)
    
    total = query.count()
    incentives = query.order_by(ZynovaIncentive.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    data = []
    for inc in incentives:
        role = "promoter"
        amount = inc.promoter_amount or 0
        if inc.team_leader_id == current_user.id:
            role = "team_leader"
            amount = inc.team_leader_amount or 0
        elif inc.zonal_manager_id == current_user.id:
            role = "zonal_manager"
            amount = inc.zonal_manager_amount or 0
        elif inc.director_id == current_user.id:
            role = "director"
            amount = inc.director_amount or 0
        
        lead = db.query(CRMLead).filter(CRMLead.id == inc.lead_id).first()
        lead_name = lead.name if lead else "Unknown"
        
        data.append({
            "id": inc.id,
            "lead_id": inc.lead_id,
            "lead_name": lead_name,
            "category": inc.category_slug,
            "revenue_amount": inc.revenue_amount,
            "role": role,
            "your_incentive": amount,
            "status": inc.status,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        })
    
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/zynova/my-membership", summary="Get current user's Zynova membership status")
async def get_my_zynova_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's Zynova membership and role
    DC Protocol: Uses MNR session priority for dual-login scenarios
    """
    membership = db.query(ZynovaMember).filter(
        ZynovaMember.user_id == current_user.id,
        ZynovaMember.is_active == True
    ).first()
    
    if not membership:
        return {
            "success": True,
            "data": {
                "is_member": False,
                "message": "You are not yet a Zynova member. Generate ₹1,00,000 revenue in Insurance/Real Estate/Training to become a Team Leader."
            }
        }
    
    team_count = db.query(ZynovaMember).filter(
        ZynovaMember.parent_id == membership.id,
        ZynovaMember.is_active == True
    ).count()
    
    return {
        "success": True,
        "data": {
            "is_member": True,
            "role": membership.role,
            "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
            "role_promoted_at": membership.role_promoted_at.isoformat() if membership.role_promoted_at else None,
            "promotion_deadline": membership.promotion_deadline.isoformat() if membership.promotion_deadline else None,
            "revenue_since_role_start": membership.revenue_since_role_start,
            "total_revenue": membership.total_revenue,
            "team_revenue": membership.team_revenue,
            "team_count": team_count
        }
    }


@router.get("/earnings-summary", summary="Get combined earnings summary for current user")
async def get_earnings_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get combined earnings summary from MyntReal and Zynova systems
    DC Protocol: Uses MNR session priority for dual-login scenarios
    """
    myntreal_total = db.query(func.sum(MyntRealIncentive.mnr_amount)).filter(
        MyntRealIncentive.mnr_id == current_user.id,
        MyntRealIncentive.status == "approved"
    ).scalar() or 0
    
    myntreal_guru = db.query(func.sum(MyntRealIncentive.guru_amount)).filter(
        MyntRealIncentive.guru_id == current_user.id,
        MyntRealIncentive.status == "approved"
    ).scalar() or 0
    
    myntreal_adiguru = db.query(func.sum(MyntRealIncentive.adiguru_amount)).filter(
        MyntRealIncentive.adiguru_id == current_user.id,
        MyntRealIncentive.status == "approved"
    ).scalar() or 0
    
    zynova_promoter = db.query(func.sum(ZynovaIncentive.promoter_amount)).filter(
        ZynovaIncentive.promoter_id == current_user.id,
        ZynovaIncentive.status == "approved"
    ).scalar() or 0
    
    zynova_tl = db.query(func.sum(ZynovaIncentive.team_leader_amount)).filter(
        ZynovaIncentive.team_leader_id == current_user.id,
        ZynovaIncentive.status == "approved"
    ).scalar() or 0
    
    zynova_zm = db.query(func.sum(ZynovaIncentive.zonal_manager_amount)).filter(
        ZynovaIncentive.zonal_manager_id == current_user.id,
        ZynovaIncentive.status == "approved"
    ).scalar() or 0
    
    zynova_director = db.query(func.sum(ZynovaIncentive.director_amount)).filter(
        ZynovaIncentive.director_id == current_user.id,
        ZynovaIncentive.status == "approved"
    ).scalar() or 0
    
    points_balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == current_user.id
    ).first()
    
    return {
        "success": True,
        "data": {
            "myntreal": {
                "promoter_earnings": myntreal_total,
                "guru_earnings": myntreal_guru,
                "adiguru_earnings": myntreal_adiguru,
                "total": myntreal_total + myntreal_guru + myntreal_adiguru
            },
            "zynova": {
                "promoter_earnings": zynova_promoter,
                "team_leader_earnings": zynova_tl,
                "zonal_manager_earnings": zynova_zm,
                "director_earnings": zynova_director,
                "total": zynova_promoter + zynova_tl + zynova_zm + zynova_director
            },
            "points": {
                "current_balance": points_balance.current_balance if points_balance else 0,
                "total_consumed": points_balance.total_consumed if points_balance else 0
            },
            "grand_total": (
                myntreal_total + myntreal_guru + myntreal_adiguru +
                zynova_promoter + zynova_tl + zynova_zm + zynova_director
            )
        }
    }


class IncentiveCalculationRequest(BaseModel):
    lead_id: int = Field(..., description="CRM Lead ID")
    transaction_id: int = Field(..., description="CRM Lead Transaction ID")


def get_category_incentive_config(category_slug: str) -> dict:
    """Get incentive configuration for a category based on MyntReal rules"""
    category_configs = {
        "ev-b2c": {
            "points_limit": 15000,
            "first_threshold": 7500,
            "percentage_after_points": 5.0,
            "has_guru_adiguru": True,
            "guru_percentage": 2.0,
            "adiguru_percentage": 10.0,
            "system": "myntreal"
        },
        "ev-franchise": {
            "first_percentage": 2.0,
            "repeat_percentage": 1.0,
            "has_guru_adiguru": False,
            "system": "myntreal"
        },
        "solar": {
            "points_limit": 15000,
            "percentage_after_points": 5.0,
            "has_guru_adiguru": True,
            "guru_percentage": 2.0,
            "adiguru_percentage": 10.0,
            "system": "myntreal"
        },
        "training": {
            "points_limit": 7500,
            "percentage_after_points": 5.0,
            "has_guru_adiguru": False,
            "system": "myntreal"
        },
        "insurance": {
            "promoter_percentage": 50.0,
            "team_leader_percentage": 10.0,
            "zonal_manager_percentage": 10.0,
            "director_percentage": 5.0,
            "system": "zynova"
        },
        "real-estate": {
            "promoter_percentage": 50.0,
            "team_leader_percentage": 10.0,
            "zonal_manager_percentage": 10.0,
            "director_percentage": 5.0,
            "system": "zynova"
        }
    }
    return category_configs.get(category_slug, {
        "percentage": 5.0,
        "has_guru_adiguru": False,
        "system": "myntreal"
    })


def get_user_hierarchy(db: Session, user_id: str) -> dict:
    """Get user's Guru (referrer) and Adi Guru (referrer's referrer) from ved_team_member"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"guru_id": None, "adiguru_id": None}
    
    guru_id = None
    adiguru_id = None
    
    if user.bev_referrer_id:
        guru_id = user.bev_referrer_id
        guru = db.query(User).filter(User.id == guru_id).first()
        if guru and guru.bev_referrer_id:
            adiguru_id = guru.bev_referrer_id
    
    return {"guru_id": guru_id, "adiguru_id": adiguru_id}


def calculate_myntreal_incentive(
    db: Session,
    user_id: str,
    category_slug: str,
    revenue_amount: float,
    is_first_transaction: bool = True
) -> dict:
    """Calculate MyntReal incentive based on category rules and points balance"""
    config = get_category_incentive_config(category_slug)
    
    if config.get("system") != "myntreal":
        return {"error": f"Category {category_slug} uses Zynova system"}
    
    points_balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == user_id
    ).first()
    
    current_points = points_balance.current_balance if points_balance else 0
    
    result = {
        "calculation_mode": "percentage",
        "points_consumed": 0,
        "mnr_amount": 0,
        "guru_amount": 0,
        "adiguru_amount": 0
    }
    
    if category_slug == "ev-franchise":
        rate = config.get("first_percentage", 2.0) if is_first_transaction else config.get("repeat_percentage", 1.0)
        result["mnr_amount"] = revenue_amount * (rate / 100)
        result["calculation_mode"] = "percentage"
    else:
        points_limit = config.get("points_limit", 15000)
        
        if current_points > 0:
            points_to_use = min(current_points, revenue_amount)
            result["points_consumed"] = points_to_use
            result["mnr_amount"] = points_to_use
            result["calculation_mode"] = "points"
            
            remaining_revenue = revenue_amount - points_to_use
            if remaining_revenue > 0:
                percentage_rate = config.get("percentage_after_points", 5.0)
                result["mnr_amount"] += remaining_revenue * (percentage_rate / 100)
                result["calculation_mode"] = "hybrid"
        else:
            percentage_rate = config.get("percentage_after_points", 5.0)
            result["mnr_amount"] = revenue_amount * (percentage_rate / 100)
            result["calculation_mode"] = "percentage"
    
    if config.get("has_guru_adiguru", False) and result["mnr_amount"] > 0:
        hierarchy = get_user_hierarchy(db, user_id)
        
        if hierarchy["guru_id"]:
            guru_rate = config.get("guru_percentage", 2.0)
            result["guru_amount"] = result["mnr_amount"] * (guru_rate / 100)
            result["guru_id"] = hierarchy["guru_id"]
        
        if hierarchy["adiguru_id"]:
            adiguru_rate = config.get("adiguru_percentage", 10.0)
            result["adiguru_amount"] = result["guru_amount"] * (adiguru_rate / 100) if result["guru_amount"] > 0 else 0
            result["adiguru_id"] = hierarchy["adiguru_id"]
    
    return result


def create_incentive_for_validated_transaction(
    db: Session,
    lead: CRMLead,
    transaction: CRMLeadTransaction,
    company_id: int,
    validated_by_id: int = None
) -> dict:
    """
    Create MyntReal or Zynova incentive for a validated transaction.
    Called automatically when a transaction is validated via CRM.
    DC Protocol: company_id required for data segregation.
    
    Returns dict with success status and created incentive details.
    """
    from app.models.signup_category import SignupCategory
    
    # Check if incentive already exists for this transaction
    existing_myntreal = db.query(MyntRealIncentive).filter(
        MyntRealIncentive.transaction_id == transaction.id
    ).first()
    
    existing_zynova = db.query(ZynovaIncentive).filter(
        ZynovaIncentive.transaction_id == transaction.id
    ).first()
    
    if existing_myntreal or existing_zynova:
        return {
            "success": False,
            "message": "Incentive already exists for this transaction",
            "system": "myntreal" if existing_myntreal else "zynova"
        }
    
    # Get category configuration
    category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first()
    category_slug = category.slug if category else "unknown"
    
    # Find MNR handler for the lead
    mnr_id = None
    for handler in (lead.handlers or []):
        if handler.get("type") == "mnr" or handler.get("handler_type") == "mnr":
            mnr_id = handler.get("handler_id")
            break
    
    if not mnr_id:
        return {
            "success": False,
            "message": "No MNR handler found for this lead - incentive not created",
            "system": None
        }
    
    config = get_category_incentive_config(category_slug)
    revenue = transaction.amount or 0
    
    if config.get("system") == "zynova":
        # Zynova incentive creation
        promoter_member = db.query(ZynovaMember).filter(
            ZynovaMember.user_id == mnr_id,
            ZynovaMember.is_active == True
        ).first()
        
        promoter_rate = config.get("promoter_percentage", 50.0)
        promoter_amount = revenue * (promoter_rate / 100)
        
        tl_id = None
        zm_id = None
        director_id = None
        tl_amount = 0
        zm_amount = 0
        director_amount = 0
        
        # Traverse hierarchy for upline earnings - walk up the full chain
        # promoter → team_leader → zonal_manager → director
        if promoter_member:
            current_member = promoter_member
            visited_ids = set()
            max_depth = 10  # Safety limit
            
            while current_member and current_member.parent_id and len(visited_ids) < max_depth:
                if current_member.parent_id in visited_ids:
                    break  # Prevent infinite loop
                visited_ids.add(current_member.id)
                
                parent = db.query(ZynovaMember).filter(
                    ZynovaMember.id == current_member.parent_id,
                    ZynovaMember.is_active == True
                ).first()
                
                if not parent:
                    break
                
                # Assign incentive based on role (only first match per role)
                if parent.role == "team_leader" and not tl_id:
                    tl_id = parent.user_id
                    tl_amount = revenue * (config.get("team_leader_percentage", 10.0) / 100)
                elif parent.role == "zonal_manager" and not zm_id:
                    zm_id = parent.user_id
                    zm_amount = revenue * (config.get("zonal_manager_percentage", 10.0) / 100)
                elif parent.role == "director" and not director_id:
                    director_id = parent.user_id
                    director_amount = revenue * (config.get("director_percentage", 5.0) / 100)
                
                # Move up the hierarchy
                current_member = parent
        
        zynova_incentive = ZynovaIncentive(
            company_id=company_id,
            lead_id=lead.id,
            transaction_id=transaction.id,
            category_slug=category_slug,
            promoter_id=mnr_id,
            team_leader_id=tl_id,
            zonal_manager_id=zm_id,
            director_id=director_id,
            revenue_amount=revenue,
            promoter_amount=promoter_amount,
            team_leader_amount=tl_amount,
            zonal_manager_amount=zm_amount,
            director_amount=director_amount,
            status="pending"
        )
        db.add(zynova_incentive)
        
        # Update promoter's total revenue
        if promoter_member:
            promoter_member.total_revenue = (promoter_member.total_revenue or 0) + revenue
            promoter_member.revenue_since_role_start = (promoter_member.revenue_since_role_start or 0) + revenue
            
            # Update team revenue for all upline members
            current_member = promoter_member
            upline_visited = set()
            while current_member and current_member.parent_id and len(upline_visited) < 10:
                if current_member.parent_id in upline_visited:
                    break
                upline_visited.add(current_member.id)
                
                parent_member = db.query(ZynovaMember).filter(
                    ZynovaMember.id == current_member.parent_id
                ).first()
                if parent_member:
                    parent_member.team_revenue = (parent_member.team_revenue or 0) + revenue
                    current_member = parent_member
                else:
                    break
        
        db.flush()
        
        return {
            "success": True,
            "message": "Zynova incentive created successfully",
            "system": "zynova",
            "incentive_id": zynova_incentive.id,
            "revenue_amount": revenue,
            "promoter_amount": promoter_amount,
            "team_leader_amount": tl_amount,
            "zonal_manager_amount": zm_amount,
            "director_amount": director_amount
        }
    else:
        # MyntReal incentive creation
        previous_count = db.query(CRMLeadTransaction).filter(
            CRMLeadTransaction.lead_id == lead.id,
            CRMLeadTransaction.id < transaction.id,
            CRMLeadTransaction.validation_status == "validated"
        ).count()
        is_first = previous_count == 0
        
        calc_result = calculate_myntreal_incentive(
            db=db,
            user_id=mnr_id,
            category_slug=category_slug,
            revenue_amount=revenue,
            is_first_transaction=is_first
        )
        
        if "error" in calc_result:
            return {
                "success": False,
                "message": calc_result["error"],
                "system": "myntreal"
            }
        
        # Handle points consumption
        if calc_result["points_consumed"] > 0:
            points_balance = db.query(MNRPointsBalance).filter(
                MNRPointsBalance.user_id == mnr_id
            ).first()
            
            if points_balance:
                points_balance.current_balance -= calc_result["points_consumed"]
                points_balance.total_consumed += calc_result["points_consumed"]
                
                points_txn = MNRPointsTransaction(
                    company_id=company_id,
                    user_id=mnr_id,
                    transaction_type="consumption",
                    amount=-calc_result["points_consumed"],
                    balance_after=points_balance.current_balance,
                    category_id=lead.category_id,
                    lead_id=lead.id,
                    description=f"Points consumed for {category_slug} lead #{lead.id}",
                    created_by_id=str(validated_by_id) if validated_by_id else None,
                    created_by_type="staff"
                )
                db.add(points_txn)
        
        # Create MyntReal incentive record
        myntreal_incentive = MyntRealIncentive(
            company_id=company_id,
            user_id=mnr_id,
            category_id=lead.category_id,
            lead_id=lead.id,
            transaction_id=transaction.id,
            calculation_mode=calc_result.get("calculation_mode", "percentage"),
            revenue_amount=revenue,
            points_consumed=calc_result.get("points_consumed", 0),
            mnr_amount=calc_result.get("mnr_amount", 0),
            guru_id=calc_result.get("guru_id"),
            guru_amount=calc_result.get("guru_amount", 0),
            adiguru_id=calc_result.get("adiguru_id"),
            adiguru_amount=calc_result.get("adiguru_amount", 0),
            status="pending"
        )
        db.add(myntreal_incentive)
        db.flush()
        
        return {
            "success": True,
            "message": "MyntReal incentive created successfully",
            "system": "myntreal",
            "incentive_id": myntreal_incentive.id,
            "revenue_amount": revenue,
            "mnr_amount": calc_result.get("mnr_amount", 0),
            "guru_amount": calc_result.get("guru_amount", 0),
            "adiguru_amount": calc_result.get("adiguru_amount", 0)
        }


@router.post("/calculate-incentive", summary="Calculate and create incentive for validated transaction")
async def calculate_and_create_incentive(
    request: IncentiveCalculationRequest = Body(...),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Calculate and create MyntReal/Zynova incentive when a CRM transaction is validated
    DC Protocol: Finance/VGK staff access with audit trail
    """
    lead = db.query(CRMLead).filter(CRMLead.id == request.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    transaction = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.id == request.transaction_id,
        CRMLeadTransaction.lead_id == request.lead_id
    ).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.finance_status != "validated":
        raise HTTPException(
            status_code=400, 
            detail="Transaction must be validated by Finance before incentive calculation"
        )
    
    existing = db.query(MyntRealIncentive).filter(
        MyntRealIncentive.transaction_id == request.transaction_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Incentive already exists for this transaction"
        )
    
    category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first()
    category_slug = category.slug if category else "unknown"
    
    mnr_id = None
    for handler in lead.handlers or []:
        if handler.get("type") == "mnr" or handler.get("handler_type") == "mnr":
            mnr_id = handler.get("handler_id")
            break
    
    if not mnr_id:
        raise HTTPException(
            status_code=400, 
            detail="No MNR handler found for this lead"
        )
    
    config = get_category_incentive_config(category_slug)
    
    if config.get("system") == "zynova":
        promoter_member = db.query(ZynovaMember).filter(
            ZynovaMember.user_id == mnr_id,
            ZynovaMember.is_active == True
        ).first()
        
        promoter_rate = config.get("promoter_percentage", 50.0)
        revenue = transaction.amount or 0
        
        promoter_amount = revenue * (promoter_rate / 100)
        tl_amount = 0
        zm_amount = 0
        director_amount = 0
        
        tl_id = None
        zm_id = None
        director_id = None
        
        if promoter_member and promoter_member.parent_id:
            parent = db.query(ZynovaMember).filter(
                ZynovaMember.id == promoter_member.parent_id
            ).first()
            if parent and parent.role in ["team_leader", "zonal_manager", "director"]:
                if parent.role == "team_leader":
                    tl_id = parent.user_id
                    tl_amount = revenue * (config.get("team_leader_percentage", 10.0) / 100)
                elif parent.role == "zonal_manager":
                    zm_id = parent.user_id
                    zm_amount = revenue * (config.get("zonal_manager_percentage", 10.0) / 100)
                elif parent.role == "director":
                    director_id = parent.user_id
                    director_amount = revenue * (config.get("director_percentage", 5.0) / 100)
        
        company_id = get_company_id_from_staff(current_staff)
        
        zynova_incentive = ZynovaIncentive(
            company_id=company_id,
            lead_id=lead.id,
            transaction_id=transaction.id,
            category_slug=category_slug,
            promoter_id=mnr_id,
            team_leader_id=tl_id,
            zonal_manager_id=zm_id,
            director_id=director_id,
            revenue_amount=revenue,
            promoter_amount=promoter_amount,
            team_leader_amount=tl_amount,
            zonal_manager_amount=zm_amount,
            director_amount=director_amount,
            status="pending"
        )
        db.add(zynova_incentive)
        
        if promoter_member:
            promoter_member.total_revenue = (promoter_member.total_revenue or 0) + revenue
            promoter_member.revenue_since_role_start = (promoter_member.revenue_since_role_start or 0) + revenue
        
        db.commit()
        
        return {
            "success": True,
            "message": "Zynova incentive created successfully",
            "data": {
                "incentive_id": zynova_incentive.id,
                "system": "zynova",
                "category": category_slug,
                "revenue_amount": revenue,
                "promoter_amount": promoter_amount,
                "team_leader_amount": tl_amount,
                "zonal_manager_amount": zm_amount,
                "director_amount": director_amount
            }
        }
    else:
        previous_count = db.query(CRMLeadTransaction).filter(
            CRMLeadTransaction.lead_id == lead.id,
            CRMLeadTransaction.id < transaction.id,
            CRMLeadTransaction.finance_status == "validated"
        ).count()
        is_first = previous_count == 0
        
        revenue = transaction.amount or 0
        calc_result = calculate_myntreal_incentive(
            db=db,
            user_id=mnr_id,
            category_slug=category_slug,
            revenue_amount=revenue,
            is_first_transaction=is_first
        )
        
        if "error" in calc_result:
            raise HTTPException(status_code=400, detail=calc_result["error"])
        
        if calc_result["points_consumed"] > 0:
            points_balance = db.query(MNRPointsBalance).filter(
                MNRPointsBalance.user_id == mnr_id
            ).first()
            
            if points_balance:
                points_balance.current_balance -= calc_result["points_consumed"]
                points_balance.total_consumed += calc_result["points_consumed"]
                
                company_id = get_company_id_from_staff(current_staff)
                
                points_txn = MNRPointsTransaction(
                    company_id=company_id,
                    user_id=mnr_id,
                    transaction_type="consumption",
                    amount=-calc_result["points_consumed"],
                    balance_after=points_balance.current_balance,
                    category_id=lead.category_id,
                    lead_id=lead.id,
                    description=f"Points consumed for {category_slug} lead #{lead.id}",
                    created_by_id=str(current_staff.id),
                    created_by_type="staff"
                )
                db.add(points_txn)
        
        company_id = get_company_id_from_staff(current_staff)
        
        incentive = MyntRealIncentive(
            company_id=company_id,
            lead_id=lead.id,
            transaction_id=transaction.id,
            category_id=lead.category_id,
            mnr_id=mnr_id,
            guru_id=calc_result.get("guru_id"),
            adiguru_id=calc_result.get("adiguru_id"),
            revenue_amount=revenue,
            calculation_mode=calc_result["calculation_mode"],
            points_consumed=calc_result["points_consumed"],
            mnr_amount=calc_result["mnr_amount"],
            guru_amount=calc_result.get("guru_amount", 0),
            adiguru_amount=calc_result.get("adiguru_amount", 0),
            status="pending"
        )
        db.add(incentive)
        
        db.commit()
        
        return {
            "success": True,
            "message": "MyntReal incentive created successfully",
            "data": {
                "incentive_id": incentive.id,
                "system": "myntreal",
                "category": category_slug,
                "revenue_amount": revenue,
                "calculation_mode": calc_result["calculation_mode"],
                "points_consumed": calc_result["points_consumed"],
                "mnr_amount": calc_result["mnr_amount"],
                "guru_amount": calc_result.get("guru_amount", 0),
                "adiguru_amount": calc_result.get("adiguru_amount", 0)
            }
        }


@router.get("/incentives/all", summary="List all MyntReal incentives (Staff/Admin only)")
async def list_all_incentives(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all MyntReal incentives with pagination and filters
    DC Protocol: Staff access with company validation
    """
    query = db.query(MyntRealIncentive)
    
    if status_filter:
        query = query.filter(MyntRealIncentive.status == status_filter)
    
    if category_id:
        query = query.filter(MyntRealIncentive.category_id == category_id)
    
    total = query.count()
    incentives = query.order_by(MyntRealIncentive.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    data = []
    for inc in incentives:
        lead = db.query(CRMLead).filter(CRMLead.id == inc.lead_id).first()
        mnr_user = db.query(User).filter(User.id == inc.mnr_id).first()
        category = db.query(SignupCategory).filter(SignupCategory.id == inc.category_id).first()
        
        data.append({
            "id": inc.id,
            "lead_id": inc.lead_id,
            "lead_name": lead.name if lead else None,
            "mnr_id": inc.mnr_id,
            "mnr_name": mnr_user.name if mnr_user else None,
            "category_name": category.name if category else None,
            "revenue_amount": inc.revenue_amount,
            "calculation_mode": inc.calculation_mode,
            "points_consumed": inc.points_consumed,
            "mnr_amount": inc.mnr_amount,
            "guru_amount": inc.guru_amount,
            "adiguru_amount": inc.adiguru_amount,
            "status": inc.status,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        })
    
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/incentives/{incentive_id}", summary="Get single MyntReal incentive details")
async def get_incentive_details(
    incentive_id: int,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get detailed information about a single MyntReal incentive
    DC Protocol: Staff access
    """
    inc = db.query(MyntRealIncentive).filter(MyntRealIncentive.id == incentive_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incentive not found")
    
    lead = db.query(CRMLead).filter(CRMLead.id == inc.lead_id).first()
    mnr_user = db.query(User).filter(User.id == inc.mnr_id).first()
    guru_user = db.query(User).filter(User.id == inc.guru_id).first() if inc.guru_id else None
    adiguru_user = db.query(User).filter(User.id == inc.adiguru_id).first() if inc.adiguru_id else None
    category = db.query(SignupCategory).filter(SignupCategory.id == inc.category_id).first()
    
    return {
        "success": True,
        "data": {
            "id": inc.id,
            "lead_id": inc.lead_id,
            "lead_name": lead.name if lead else None,
            "mnr_id": inc.mnr_id,
            "user_name": mnr_user.name if mnr_user else None,
            "guru_id": inc.guru_id,
            "guru_name": guru_user.name if guru_user else None,
            "adiguru_id": inc.adiguru_id,
            "adiguru_name": adiguru_user.name if adiguru_user else None,
            "category": category.name if category else None,
            "category_slug": category.slug if category else None,
            "revenue_amount": inc.revenue_amount,
            "calculation_mode": inc.calculation_mode,
            "points_consumed": inc.points_consumed,
            "mnr_amount": inc.mnr_amount,
            "guru_amount": inc.guru_amount,
            "adiguru_amount": inc.adiguru_amount,
            "status": inc.status,
            "rejection_reason": inc.rejection_reason,
            "approved_by": inc.approved_by,
            "approved_at": inc.approved_at.isoformat() if inc.approved_at else None,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        }
    }


@router.put("/incentives/{incentive_id}/approve", summary="Approve MyntReal incentive")
async def approve_incentive(
    incentive_id: int,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve a pending MyntReal incentive
    DC Protocol: VGK/Finance staff access
    """
    incentive = db.query(MyntRealIncentive).filter(MyntRealIncentive.id == incentive_id).first()
    if not incentive:
        raise HTTPException(status_code=404, detail="Incentive not found")
    
    if incentive.status != "pending":
        raise HTTPException(status_code=400, detail=f"Incentive is already {incentive.status}")
    
    incentive.status = "approved"
    incentive.approved_by = str(current_staff.id)
    incentive.approved_at = get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Incentive approved successfully",
        "data": {"id": incentive.id, "status": incentive.status}
    }


@router.put("/incentives/{incentive_id}/reject", summary="Reject MyntReal incentive")
async def reject_incentive(
    incentive_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reject a pending MyntReal incentive with reason
    DC Protocol: VGK/Finance staff access
    """
    incentive = db.query(MyntRealIncentive).filter(MyntRealIncentive.id == incentive_id).first()
    if not incentive:
        raise HTTPException(status_code=404, detail="Incentive not found")
    
    if incentive.status != "pending":
        raise HTTPException(status_code=400, detail=f"Incentive is already {incentive.status}")
    
    if incentive.points_consumed and incentive.points_consumed > 0:
        points_balance = db.query(MNRPointsBalance).filter(
            MNRPointsBalance.user_id == incentive.mnr_id
        ).first()
        
        if points_balance:
            points_balance.current_balance += incentive.points_consumed
            points_balance.total_consumed -= incentive.points_consumed
            
            company_id = get_company_id_from_staff(current_staff)
            
            refund_txn = MNRPointsTransaction(
                company_id=company_id,
                user_id=incentive.mnr_id,
                transaction_type="refund",
                amount=incentive.points_consumed,
                balance_after=points_balance.current_balance,
                lead_id=incentive.lead_id,
                description=f"Points refunded - Incentive #{incentive.id} rejected: {reason}",
                created_by_id=str(current_staff.id),
                created_by_type="staff"
            )
            db.add(refund_txn)
    
    incentive.status = "rejected"
    incentive.rejection_reason = reason
    
    db.commit()
    
    return {
        "success": True,
        "message": "Incentive rejected and points refunded",
        "data": {"id": incentive.id, "status": incentive.status}
    }


class ZynovaMemberCreateRequest(BaseModel):
    user_id: str = Field(..., description="MNR User ID to add as Zynova member")
    role: str = Field("promoter", description="Initial role: promoter, team_leader, zonal_manager, director")
    parent_id: Optional[int] = Field(None, description="Parent Zynova member ID for hierarchy")


class ZynovaRoleUpdateRequest(BaseModel):
    new_role: str = Field(..., description="New role: team_leader, zonal_manager, director")
    reason: str = Field("", description="Reason for role change")


ZYNOVA_PROMOTION_TARGETS = {
    "promoter": {"self_revenue": 0, "team_revenue": 0, "next_role": "team_leader"},
    "team_leader": {"self_revenue": 100000, "team_revenue": 0, "next_role": "zonal_manager"},
    "zonal_manager": {"self_revenue": 500000, "team_revenue": 500000, "next_role": "director"},
    "director": {"self_revenue": 1000000, "team_revenue": 1000000, "next_role": None}
}


@router.post("/zynova/members", summary="Add a Zynova member (Staff/Admin only)")
async def add_zynova_member(
    request: ZynovaMemberCreateRequest = Body(...),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Add a new Zynova member to the hierarchy
    DC Protocol: VGK/Finance staff access
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = db.query(ZynovaMember).filter(
        ZynovaMember.user_id == request.user_id,
        ZynovaMember.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already an active Zynova member")
    
    valid_roles = ["promoter", "team_leader", "zonal_manager", "director"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    parent = None
    if request.parent_id:
        parent = db.query(ZynovaMember).filter(ZynovaMember.id == request.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent member not found")
    
    company_id = get_company_id_from_staff(current_staff)
    
    promotion_deadline = get_indian_time() + timedelta(days=180)
    
    member = ZynovaMember(
        company_id=company_id,
        user_id=request.user_id,
        role=request.role,
        parent_id=request.parent_id,
        joined_at=get_indian_time(),
        role_promoted_at=get_indian_time() if request.role != "promoter" else None,
        promotion_deadline=promotion_deadline,
        revenue_since_role_start=0,
        total_revenue=0,
        team_revenue=0,
        is_active=True
    )
    db.add(member)
    db.commit()
    
    return {
        "success": True,
        "message": f"Zynova member added as {request.role}",
        "data": {
            "id": member.id,
            "user_id": member.user_id,
            "role": member.role,
            "promotion_deadline": promotion_deadline.isoformat()
        }
    }


@router.get("/zynova/members", summary="List all Zynova members (Staff/Admin only)")
async def list_zynova_members(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_transactions: bool = Query(False, description="Include transaction details for expandable view"),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all Zynova members with pagination, filters, and income breakdown
    DC Protocol: Staff access
    Returns income_pending, income_approved, income_disbursed, income_total for each member
    Optionally includes transaction-wise details when include_transactions=true
    """
    query = db.query(ZynovaMember, User).join(
        User, ZynovaMember.user_id == User.id
    ).filter(ZynovaMember.is_active == True)
    
    if role:
        query = query.filter(ZynovaMember.role == role)
    
    if search:
        query = query.filter(
            or_(
                User.id.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    results = query.order_by(ZynovaMember.joined_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    data = []
    for member, user in results:
        parent_name = None
        if member.parent_id:
            parent = db.query(ZynovaMember, User).join(
                User, ZynovaMember.user_id == User.id
            ).filter(ZynovaMember.id == member.parent_id).first()
            if parent:
                parent_name = parent[1].name
        
        team_count = db.query(ZynovaMember).filter(
            ZynovaMember.parent_id == member.id,
            ZynovaMember.is_active == True
        ).count()
        
        incentive_query = db.query(ZynovaIncentive).filter(
            or_(
                ZynovaIncentive.promoter_id == member.user_id,
                ZynovaIncentive.team_leader_id == member.user_id,
                ZynovaIncentive.zonal_manager_id == member.user_id,
                ZynovaIncentive.director_id == member.user_id
            )
        )
        
        if category:
            incentive_query = incentive_query.filter(ZynovaIncentive.category_slug == category)
        
        all_incentives = incentive_query.all()
        
        income_pending = 0
        income_approved = 0
        income_disbursed = 0
        transactions_by_status = {"pending": [], "approved": [], "disbursed": []}
        
        for inc in all_incentives:
            amount = 0
            if inc.promoter_id == member.user_id:
                amount = inc.promoter_amount or 0
            elif inc.team_leader_id == member.user_id:
                amount = inc.team_leader_amount or 0
            elif inc.zonal_manager_id == member.user_id:
                amount = inc.zonal_manager_amount or 0
            elif inc.director_id == member.user_id:
                amount = inc.director_amount or 0
            
            transaction_info = {
                "id": inc.id,
                "category": inc.category_slug,
                "lead_id": inc.lead_id,
                "revenue_amount": inc.revenue_amount,
                "incentive_amount": amount,
                "status": inc.status,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
                "approved_at": inc.approved_at.isoformat() if inc.approved_at else None
            }
            
            if inc.status == 'pending':
                income_pending += amount
                transactions_by_status["pending"].append(transaction_info)
            elif inc.status == 'approved':
                income_approved += amount
                transactions_by_status["approved"].append(transaction_info)
            elif inc.status == 'disbursed':
                income_disbursed += amount
                transactions_by_status["disbursed"].append(transaction_info)
        
        income_total = income_pending + income_approved + income_disbursed
        
        member_data = {
            "id": member.id,
            "user_id": user.id,
            "user_name": user.name,
            "role": member.role,
            "real_estate_role": member.real_estate_role or member.role or 'promoter',
            "real_estate_role_display": format_role_display(member.real_estate_role or member.role or 'promoter', 'real_estate'),
            "insurance_role": member.insurance_role or member.role or 'promoter',
            "insurance_role_display": format_role_display(member.insurance_role or member.role or 'promoter', 'insurance'),
            "parent_name": parent_name,
            "team_count": team_count,
            "total_revenue": member.total_revenue or 0,
            "team_revenue": member.team_revenue or 0,
            "real_estate_revenue": member.real_estate_revenue_total or 0,
            "insurance_revenue": member.insurance_revenue_total or 0,
            "income_pending": income_pending,
            "income_approved": income_approved,
            "income_disbursed": income_disbursed,
            "income_total": income_total,
            "transaction_counts": {
                "pending": len(transactions_by_status["pending"]),
                "approved": len(transactions_by_status["approved"]),
                "disbursed": len(transactions_by_status["disbursed"])
            },
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "promotion_deadline": member.promotion_deadline.isoformat() if member.promotion_deadline else None
        }
        
        if include_transactions:
            member_data["transactions"] = transactions_by_status
        
        data.append(member_data)
    
    available_categories = db.query(ZynovaIncentive.category_slug).distinct().all()
    categories = [c[0] for c in available_categories if c[0]]
    
    return {
        "success": True,
        "data": data,
        "filters": {
            "categories": categories,
            "roles": ["promoter", "team_leader", "zonal_manager", "director"]
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/zynova/members/hierarchy", summary="Get Zynova hierarchy tree structure")
async def get_zynova_hierarchy(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get the complete Zynova hierarchy as a nested tree structure with income breakdown
    DC Protocol: Staff access with company validation
    Shows: Director → Zonal Managers → Team Leaders → Promoters
    Includes income_pending, income_approved, income_disbursed for each member
    """
    all_members = db.query(ZynovaMember, User).join(
        User, ZynovaMember.user_id == User.id
    ).filter(ZynovaMember.is_active == True).all()
    
    member_income_map = {}
    for member, user in all_members:
        incentive_query = db.query(ZynovaIncentive).filter(
            or_(
                ZynovaIncentive.promoter_id == member.user_id,
                ZynovaIncentive.team_leader_id == member.user_id,
                ZynovaIncentive.zonal_manager_id == member.user_id,
                ZynovaIncentive.director_id == member.user_id
            )
        )
        
        if category:
            incentive_query = incentive_query.filter(ZynovaIncentive.category_slug == category)
        
        all_incentives = incentive_query.all()
        
        income_pending = 0
        income_approved = 0
        income_disbursed = 0
        transaction_counts = {"pending": 0, "approved": 0, "disbursed": 0}
        
        for inc in all_incentives:
            amount = 0
            if inc.promoter_id == member.user_id:
                amount = inc.promoter_amount or 0
            elif inc.team_leader_id == member.user_id:
                amount = inc.team_leader_amount or 0
            elif inc.zonal_manager_id == member.user_id:
                amount = inc.zonal_manager_amount or 0
            elif inc.director_id == member.user_id:
                amount = inc.director_amount or 0
            
            if inc.status == 'pending':
                income_pending += amount
                transaction_counts["pending"] += 1
            elif inc.status == 'approved':
                income_approved += amount
                transaction_counts["approved"] += 1
            elif inc.status == 'disbursed':
                income_disbursed += amount
                transaction_counts["disbursed"] += 1
        
        member_income_map[member.user_id] = {
            "income_pending": income_pending,
            "income_approved": income_approved,
            "income_disbursed": income_disbursed,
            "income_total": income_pending + income_approved + income_disbursed,
            "transaction_counts": transaction_counts
        }
    
    member_map = {}
    for member, user in all_members:
        income_data = member_income_map.get(member.user_id, {})
        member_map[member.id] = {
            "id": member.id,
            "user_id": member.user_id,
            "user_name": user.name,
            "role": member.role,
            "parent_id": member.parent_id,
            "total_revenue": member.total_revenue or 0,
            "team_revenue": member.team_revenue or 0,
            "income_pending": income_data.get("income_pending", 0),
            "income_approved": income_data.get("income_approved", 0),
            "income_disbursed": income_data.get("income_disbursed", 0),
            "income_total": income_data.get("income_total", 0),
            "transaction_counts": income_data.get("transaction_counts", {"pending": 0, "approved": 0, "disbursed": 0}),
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "children": []
        }
    
    root_members = []
    for member_id, member_data in member_map.items():
        parent_id = member_data["parent_id"]
        if parent_id and parent_id in member_map:
            member_map[parent_id]["children"].append(member_data)
        else:
            root_members.append(member_data)
    
    def sort_by_role(members):
        role_order = {"director": 0, "zonal_manager": 1, "team_leader": 2, "promoter": 3}
        members.sort(key=lambda x: (role_order.get(x["role"], 4), x["user_name"] or ""))
        for m in members:
            if m["children"]:
                sort_by_role(m["children"])
        return members
    
    sorted_hierarchy = sort_by_role(root_members)
    
    stats = {"director": 0, "zonal_manager": 0, "team_leader": 0, "promoter": 0}
    income_totals = {"pending": 0, "approved": 0, "disbursed": 0, "total": 0}
    for member, user in all_members:
        if member.role in stats:
            stats[member.role] += 1
        income_data = member_income_map.get(member.user_id, {})
        income_totals["pending"] += income_data.get("income_pending", 0)
        income_totals["approved"] += income_data.get("income_approved", 0)
        income_totals["disbursed"] += income_data.get("income_disbursed", 0)
        income_totals["total"] += income_data.get("income_total", 0)
    
    available_categories = db.query(ZynovaIncentive.category_slug).distinct().all()
    categories = [c[0] for c in available_categories if c[0]]
    
    return {
        "success": True,
        "data": {
            "hierarchy": sorted_hierarchy,
            "stats": stats,
            "income_totals": income_totals,
            "total_members": len(all_members)
        },
        "filters": {
            "categories": categories
        }
    }


@router.get("/zynova/members/{member_id}", summary="Get Zynova member details")
async def get_zynova_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get detailed information about a Zynova member including segment-specific data
    DC Protocol: Staff access with enhanced segment details
    Updated: December 2025 - Added segment-specific roles, uplines, and status info
    """
    member = db.query(ZynovaMember).filter(ZynovaMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    user = db.query(User).filter(User.id == member.user_id).first()
    
    # DC Protocol (Dec 31, 2025): Enhanced member details with MNR history and lead summary
    # Get MNR user dates (created_at, activation_date)
    mnr_created_at = user.created_at if user and hasattr(user, 'created_at') else None
    mnr_activated_at = user.activation_date if user and hasattr(user, 'activation_date') else None
    
    # Get lead summary per segment using CRMLead mnr_handler_id
    # DC Protocol: Join with SignupCategory to filter by slug (CRMLead has category_id FK)
    re_lead_summary = db.query(
        func.count(CRMLead.id).label('total_leads'),
        func.count(case((CRMLead.status == 'converted', 1))).label('converted_leads'),
        func.sum(case((CRMLead.status == 'converted', CRMLead.deal_value_total), else_=0)).label('total_deal_value'),
        func.min(case((CRMLead.status == 'converted', CRMLead.updated_at))).label('first_converted_at')
    ).outerjoin(
        SignupCategory, CRMLead.category_id == SignupCategory.id
    ).filter(
        CRMLead.mnr_handler_id == member.user_id,
        SignupCategory.slug.in_(['real-estate', 'real_estate'])
    ).first()
    
    ins_lead_summary = db.query(
        func.count(CRMLead.id).label('total_leads'),
        func.count(case((CRMLead.status == 'converted', 1))).label('converted_leads'),
        func.sum(case((CRMLead.status == 'converted', CRMLead.deal_value_total), else_=0)).label('total_deal_value'),
        func.min(case((CRMLead.status == 'converted', CRMLead.updated_at))).label('first_converted_at')
    ).outerjoin(
        SignupCategory, CRMLead.category_id == SignupCategory.id
    ).filter(
        CRMLead.mnr_handler_id == member.user_id,
        SignupCategory.slug.in_(['insurance'])
    ).first()
    
    # Get first lead assignment date per segment
    re_first_lead = db.query(func.min(CRMLead.created_at)).outerjoin(
        SignupCategory, CRMLead.category_id == SignupCategory.id
    ).filter(
        CRMLead.mnr_handler_id == member.user_id,
        SignupCategory.slug.in_(['real-estate', 'real_estate'])
    ).scalar()
    
    ins_first_lead = db.query(func.min(CRMLead.created_at)).outerjoin(
        SignupCategory, CRMLead.category_id == SignupCategory.id
    ).filter(
        CRMLead.mnr_handler_id == member.user_id,
        SignupCategory.slug.in_(['insurance'])
    ).scalar()
    
    # Legacy parent info
    parent_info = None
    if member.parent_id:
        parent = db.query(ZynovaMember, User).join(
            User, ZynovaMember.user_id == User.id
        ).filter(ZynovaMember.id == member.parent_id).first()
        if parent:
            parent_info = {"id": parent[0].id, "name": parent[1].name, "role": parent[0].role}
    
    # Real Estate upline
    re_upline_info = None
    if member.real_estate_upline_id:
        re_upline = db.query(ZynovaMember, User).join(
            User, ZynovaMember.user_id == User.id
        ).filter(ZynovaMember.id == member.real_estate_upline_id).first()
        if re_upline:
            re_upline_info = {"id": re_upline[0].id, "name": re_upline[1].name, "role": re_upline[0].real_estate_role}
    
    # Insurance upline
    ins_upline_info = None
    if member.insurance_upline_id:
        ins_upline = db.query(ZynovaMember, User).join(
            User, ZynovaMember.user_id == User.id
        ).filter(ZynovaMember.id == member.insurance_upline_id).first()
        if ins_upline:
            ins_upline_info = {"id": ins_upline[0].id, "name": ins_upline[1].name, "role": ins_upline[0].insurance_role}
    
    # Team counts per segment
    re_team_count = db.query(ZynovaMember).filter(
        ZynovaMember.real_estate_upline_id == member_id,
        ZynovaMember.is_active == True
    ).count()
    
    ins_team_count = db.query(ZynovaMember).filter(
        ZynovaMember.insurance_upline_id == member_id,
        ZynovaMember.is_active == True
    ).count()
    
    # Legacy team
    team = db.query(ZynovaMember, User).join(
        User, ZynovaMember.user_id == User.id
    ).filter(
        ZynovaMember.parent_id == member_id,
        ZynovaMember.is_active == True
    ).all()
    
    team_list = [{"id": m.id, "name": u.name, "role": m.role} for m, u in team]
    
    # Get incentive summaries per segment
    re_incentives = db.query(
        func.sum(case((ZynovaIncentive.status == 'pending', ZynovaIncentive.promoter_amount), else_=0)).label('pending'),
        func.sum(case((ZynovaIncentive.status == 'approved', ZynovaIncentive.promoter_amount), else_=0)).label('approved'),
        func.sum(case((ZynovaIncentive.disbursed_at.isnot(None), ZynovaIncentive.promoter_amount), else_=0)).label('disbursed')
    ).filter(
        or_(
            ZynovaIncentive.promoter_id == member.user_id,
            ZynovaIncentive.team_leader_id == member.user_id,
            ZynovaIncentive.zonal_manager_id == member.user_id,
            ZynovaIncentive.director_id == member.user_id
        ),
        ZynovaIncentive.category_slug.in_(['real-estate', 'real_estate'])
    ).first()
    
    ins_incentives = db.query(
        func.sum(case((ZynovaIncentive.status == 'pending', ZynovaIncentive.promoter_amount), else_=0)).label('pending'),
        func.sum(case((ZynovaIncentive.status == 'approved', ZynovaIncentive.promoter_amount), else_=0)).label('approved'),
        func.sum(case((ZynovaIncentive.disbursed_at.isnot(None), ZynovaIncentive.promoter_amount), else_=0)).label('disbursed')
    ).filter(
        or_(
            ZynovaIncentive.promoter_id == member.user_id,
            ZynovaIncentive.team_leader_id == member.user_id,
            ZynovaIncentive.zonal_manager_id == member.user_id,
            ZynovaIncentive.director_id == member.user_id
        ),
        ZynovaIncentive.category_slug.in_(['insurance'])
    ).first()
    
    targets = ZYNOVA_PROMOTION_TARGETS.get(member.role, {})
    promotion_eligible = False
    if targets.get("next_role"):
        self_revenue = member.revenue_since_role_start or 0
        team_revenue = member.team_revenue or 0
        if self_revenue >= targets.get("self_revenue", 0) and team_revenue >= targets.get("team_revenue", 0):
            promotion_eligible = True
    
    return {
        "success": True,
        "data": {
            "id": member.id,
            "user_id": member.user_id,
            "user_name": user.name if user else None,
            "user_mobile": user.phone_number if user else None,
            "user_email": user.email if user else None,
            "is_active": member.is_active,
            "deactivation_reason": member.deactivation_reason,
            "deactivation_date": member.deactivation_date.isoformat() if member.deactivation_date else None,
            "role": member.role,
            "parent": parent_info,
            "team": team_list,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "role_promoted_at": member.role_promoted_at.isoformat() if member.role_promoted_at else None,
            "promotion_deadline": member.promotion_deadline.isoformat() if member.promotion_deadline else None,
            "revenue_since_role_start": member.revenue_since_role_start or 0,
            "total_revenue": member.total_revenue or 0,
            "team_revenue": member.team_revenue or 0,
            "promotion_eligible": promotion_eligible,
            "next_role": targets.get("next_role"),
            "promotion_targets": targets,
            # DC Protocol (Dec 31, 2025): Enhanced MNR history
            "mnr_created_at": mnr_created_at.isoformat() if mnr_created_at else None,
            "mnr_activated_at": mnr_activated_at.isoformat() if mnr_activated_at else None,
            "real_estate": {
                "role": member.real_estate_role,
                "role_display": format_role_display(member.real_estate_role, 'real_estate') if member.real_estate_role else None,
                "upline": re_upline_info,
                "self_revenue": member.real_estate_revenue_total or 0,
                "team_revenue": member.real_estate_team_revenue or 0,
                "team_count": re_team_count,
                "promoted_at": member.real_estate_promoted_at.isoformat() if member.real_estate_promoted_at else None,
                "promotion_deadline": member.real_estate_promotion_deadline.isoformat() if member.real_estate_promotion_deadline else None,
                "earnings": {
                    "pending": float(re_incentives.pending or 0) if re_incentives else 0,
                    "approved": float(re_incentives.approved or 0) if re_incentives else 0,
                    "disbursed": float(re_incentives.disbursed or 0) if re_incentives else 0
                },
                # DC Protocol (Dec 31, 2025): Lead summary for segment
                "leads": {
                    "total": int(re_lead_summary.total_leads or 0) if re_lead_summary else 0,
                    "converted": int(re_lead_summary.converted_leads or 0) if re_lead_summary else 0,
                    "conversion_rate": round((int(re_lead_summary.converted_leads or 0) / int(re_lead_summary.total_leads or 1)) * 100, 1) if re_lead_summary and re_lead_summary.total_leads else 0,
                    "total_deal_value": float(re_lead_summary.total_deal_value or 0) if re_lead_summary else 0,
                    "first_lead_at": re_first_lead.isoformat() if re_first_lead else None,
                    "first_converted_at": re_lead_summary.first_converted_at.isoformat() if re_lead_summary and re_lead_summary.first_converted_at else None
                }
            },
            "insurance": {
                "role": member.insurance_role,
                "role_display": format_role_display(member.insurance_role, 'insurance') if member.insurance_role else None,
                "upline": ins_upline_info,
                "self_revenue": member.insurance_revenue_total or 0,
                "team_revenue": member.insurance_team_revenue or 0,
                "team_count": ins_team_count,
                "promoted_at": member.insurance_promoted_at.isoformat() if member.insurance_promoted_at else None,
                "promotion_deadline": member.insurance_promotion_deadline.isoformat() if member.insurance_promotion_deadline else None,
                "earnings": {
                    "pending": float(ins_incentives.pending or 0) if ins_incentives else 0,
                    "approved": float(ins_incentives.approved or 0) if ins_incentives else 0,
                    "disbursed": float(ins_incentives.disbursed or 0) if ins_incentives else 0
                },
                # DC Protocol (Dec 31, 2025): Lead summary for segment
                "leads": {
                    "total": int(ins_lead_summary.total_leads or 0) if ins_lead_summary else 0,
                    "converted": int(ins_lead_summary.converted_leads or 0) if ins_lead_summary else 0,
                    "conversion_rate": round((int(ins_lead_summary.converted_leads or 0) / int(ins_lead_summary.total_leads or 1)) * 100, 1) if ins_lead_summary and ins_lead_summary.total_leads else 0,
                    "total_deal_value": float(ins_lead_summary.total_deal_value or 0) if ins_lead_summary else 0,
                    "first_lead_at": ins_first_lead.isoformat() if ins_first_lead else None,
                    "first_converted_at": ins_lead_summary.first_converted_at.isoformat() if ins_lead_summary and ins_lead_summary.first_converted_at else None
                }
            }
        }
    }


@router.put("/zynova/members/{member_id}/role", summary="Update Zynova member role (Staff/Admin only)")
async def update_zynova_role(
    member_id: int,
    request: ZynovaRoleUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update a Zynova member's role (promotion/demotion)
    DC Protocol: VGK/Finance staff access with audit
    """
    member = db.query(ZynovaMember).filter(ZynovaMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    valid_roles = ["promoter", "team_leader", "zonal_manager", "director"]
    if request.new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    old_role = member.role
    member.role = request.new_role
    member.role_promoted_at = get_indian_time()
    member.revenue_since_role_start = 0
    member.promotion_deadline = get_indian_time() + timedelta(days=180)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Role updated from {old_role} to {request.new_role}",
        "data": {
            "id": member.id,
            "old_role": old_role,
            "new_role": request.new_role,
            "reason": request.reason
        }
    }


@router.delete("/zynova/members/{member_id}", summary="Deactivate Zynova member (Staff/Admin only)")
async def deactivate_zynova_member(
    member_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Deactivate a Zynova member
    DC Protocol: VGK/Finance staff access with audit
    """
    member = db.query(ZynovaMember).filter(ZynovaMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if not member.is_active:
        raise HTTPException(status_code=400, detail="Member is already deactivated")
    
    member.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": "Zynova member deactivated",
        "data": {"id": member.id, "reason": reason}
    }


@router.get("/zynova/incentives/all", summary="List all Zynova incentives (Staff/Admin only)")
async def list_all_zynova_incentives(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all Zynova incentives with pagination and filters
    DC Protocol: Staff access
    """
    query = db.query(ZynovaIncentive)
    
    if status_filter:
        query = query.filter(ZynovaIncentive.status == status_filter)
    
    if category:
        query = query.filter(ZynovaIncentive.category_slug == category)
    
    total = query.count()
    incentives = query.order_by(ZynovaIncentive.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    data = []
    for inc in incentives:
        lead = db.query(CRMLead).filter(CRMLead.id == inc.lead_id).first()
        promoter = db.query(User).filter(User.id == inc.promoter_id).first()
        
        data.append({
            "id": inc.id,
            "lead_id": inc.lead_id,
            "lead_name": lead.name if lead else None,
            "category_slug": inc.category_slug,
            "promoter_id": inc.promoter_id,
            "promoter_name": promoter.name if promoter else None,
            "revenue_amount": inc.revenue_amount,
            "promoter_amount": inc.promoter_amount,
            "team_leader_amount": inc.team_leader_amount,
            "zonal_manager_amount": inc.zonal_manager_amount,
            "director_amount": inc.director_amount,
            "status": inc.status,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        })
    
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/zynova/incentives/{incentive_id}", summary="Get single Zynova incentive details")
async def get_zynova_incentive_details(
    incentive_id: int,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get detailed information about a single Zynova incentive
    DC Protocol: Staff access
    """
    inc = db.query(ZynovaIncentive).filter(ZynovaIncentive.id == incentive_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incentive not found")
    
    lead = db.query(CRMLead).filter(CRMLead.id == inc.lead_id).first()
    promoter = db.query(User).filter(User.id == inc.promoter_id).first() if inc.promoter_id else None
    team_leader = db.query(User).filter(User.id == inc.team_leader_id).first() if inc.team_leader_id else None
    zonal_manager = db.query(User).filter(User.id == inc.zonal_manager_id).first() if inc.zonal_manager_id else None
    director = db.query(User).filter(User.id == inc.director_id).first() if inc.director_id else None
    
    return {
        "success": True,
        "data": {
            "id": inc.id,
            "lead_id": inc.lead_id,
            "lead_name": lead.name if lead else None,
            "category_slug": inc.category_slug,
            "promoter_id": inc.promoter_id,
            "promoter_name": promoter.name if promoter else None,
            "team_leader_id": inc.team_leader_id,
            "team_leader_name": team_leader.name if team_leader else None,
            "zonal_manager_id": inc.zonal_manager_id,
            "zonal_manager_name": zonal_manager.name if zonal_manager else None,
            "director_id": inc.director_id,
            "director_name": director.name if director else None,
            "revenue_amount": inc.revenue_amount,
            "promoter_amount": inc.promoter_amount,
            "team_leader_amount": inc.team_leader_amount,
            "zonal_manager_amount": inc.zonal_manager_amount,
            "director_amount": inc.director_amount,
            "status": inc.status,
            "rejection_reason": getattr(inc, 'rejection_reason', None),
            "approved_by": inc.approved_by,
            "approved_at": inc.approved_at.isoformat() if inc.approved_at else None,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        }
    }


@router.put("/zynova/incentives/{incentive_id}/approve", summary="Approve Zynova incentive")
async def approve_zynova_incentive(
    incentive_id: int,
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve a pending Zynova incentive and credit to earning wallet
    DC Protocol: VGK/Finance staff access
    Integration: Creates PendingIncome entries (same as MNR/MyntReal) for wallet credit
    """
    incentive = db.query(ZynovaIncentive).filter(ZynovaIncentive.id == incentive_id).first()
    if not incentive:
        raise HTTPException(status_code=404, detail="Incentive not found")
    
    if incentive.status != "pending":
        raise HTTPException(status_code=400, detail=f"Incentive is already {incentive.status}")
    
    incentive.status = "approved"
    incentive.approved_by_id = current_staff.id
    incentive.approved_at = get_indian_time()
    
    pending_income_ids = []
    beneficiaries = [
        ("promoter", incentive.promoter_id, incentive.promoter_amount),
        ("team_leader", incentive.team_leader_id, incentive.team_leader_amount),
        ("zonal_manager", incentive.zonal_manager_id, incentive.zonal_manager_amount),
        ("director", incentive.director_id, incentive.director_amount)
    ]
    
    for role_type, user_id, amount in beneficiaries:
        if user_id and amount and amount > 0:
            gross_amount = Decimal(str(amount))
            admin_deduction = gross_amount * Decimal('0.08')
            tds_deduction = gross_amount * Decimal('0.02')
            net_amount = gross_amount - admin_deduction - tds_deduction
            
            pending_income = PendingIncome(
                user_id=user_id,
                income_type=f"Zynova {role_type.replace('_', ' ').title()} Income",
                gross_amount=gross_amount,
                gurudakshina_deduction=Decimal('0'),
                admin_deduction=admin_deduction,
                tds_deduction=tds_deduction,
                net_amount=net_amount,
                withdrawal_wallet_amount=net_amount,
                upgraded_wallet_amount=Decimal('0'),
                pairs_matched=0,
                left_points_consumed=0,
                right_points_consumed=0,
                business_date=get_indian_time(),
                calculation_timestamp=get_indian_time(),
                status='approved',
                approved_at=get_indian_time(),
                approved_by=str(current_staff.id)
            )
            db.add(pending_income)
            db.flush()
            pending_income_ids.append(pending_income.id)
    
    if pending_income_ids:
        incentive.pending_income_id = pending_income_ids[0]
    
    db.commit()
    
    return {
        "success": True,
        "message": "Zynova incentive approved and credited to earning wallets",
        "data": {
            "id": incentive.id,
            "status": incentive.status,
            "pending_income_count": len(pending_income_ids)
        }
    }


@router.put("/zynova/incentives/{incentive_id}/reject", summary="Reject Zynova incentive")
async def reject_zynova_incentive(
    incentive_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reject a pending Zynova incentive with reason
    DC Protocol: VGK/Finance staff access
    """
    incentive = db.query(ZynovaIncentive).filter(ZynovaIncentive.id == incentive_id).first()
    if not incentive:
        raise HTTPException(status_code=404, detail="Incentive not found")
    
    if incentive.status != "pending":
        raise HTTPException(status_code=400, detail=f"Incentive is already {incentive.status}")
    
    incentive.status = "rejected"
    if hasattr(incentive, 'rejection_reason'):
        incentive.rejection_reason = reason
    
    db.commit()
    
    return {
        "success": True,
        "message": "Zynova incentive rejected",
        "data": {"id": incentive.id, "status": incentive.status, "reason": reason}
    }


# ============================================================================
# VGK SEGMENT-SPECIFIC ENDPOINTS (VGK Care Insurance / VGK Real Dreams Real Estate)
# Added: December 28, 2025
# DC Protocol: Segment-specific Zynova endpoints for dual program support
# ============================================================================

from app.models.myntreal_incentive import (
    ZYNOVA_INSURANCE_PROMOTION_TARGETS,
    ZYNOVA_REAL_ESTATE_PROMOTION_TARGETS,
    ZYNOVA_DEFAULT_ACTIVATION_DEADLINE
)


def get_promotion_progress(current_revenue: float, target: float) -> dict:
    """Calculate promotion progress percentage and status"""
    if target <= 0:
        return {"progress": 100, "remaining": 0, "status": "eligible"}
    progress = min((current_revenue / target) * 100, 100)
    remaining = max(target - current_revenue, 0)
    status = "eligible" if progress >= 100 else "in_progress"
    return {"progress": round(progress, 2), "remaining": remaining, "status": status}


def get_next_role(current_role: str) -> str:
    """Get the next role in the hierarchy"""
    role_order = ['promoter', 'team_leader', 'zonal_manager', 'director']
    try:
        current_idx = role_order.index(current_role.lower())
        if current_idx < len(role_order) - 1:
            return role_order[current_idx + 1]
        return None  # Already at highest level
    except ValueError:
        return 'team_leader'  # Default next role


def format_role_display(role: str, segment: str = None) -> str:
    """Format role for display with optional segment prefix (ZR/ZC)
    ZR = Zynova Real Dreams (Real Estate)
    ZC = Zynova Care (Insurance)
    """
    role_map = {
        'promoter': 'Promoter',
        'team_leader': 'Team Leader',
        'zonal_manager': 'Zonal Manager',
        'director': 'Director'
    }
    base_role = role_map.get(role.lower(), role.title()) if role else 'Promoter'
    
    if segment == 'real_estate':
        return f"ZR {base_role}"
    elif segment == 'insurance':
        return f"ZC {base_role}"
    return base_role


@router.get("/zynova/real-estate/me", summary="Get user's VGK Real Dreams (Real Estate) program data")
async def get_my_real_estate_zynova(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's VGK Real Dreams (Real Estate) Zynova program data
    Includes role, progress to next promotion, team data, and earnings
    DC Protocol: Uses MNR session priority
    """
    membership = db.query(ZynovaMember).filter(
        ZynovaMember.user_id == current_user.id,
        ZynovaMember.is_active == True
    ).first()
    
    if not membership:
        return {
            "success": True,
            "data": {
                "is_member": False,
                "segment": "real_estate",
                "segment_name": "VGK Real Dreams",
                "message": "You are not yet a Zynova member in the Real Estate program."
            }
        }
    
    current_role = membership.real_estate_role or 'promoter'
    next_role = get_next_role(current_role)
    
    # Get promotion targets for next role
    promotion_target = ZYNOVA_REAL_ESTATE_PROMOTION_TARGETS.get(next_role, {}) if next_role else None
    target_amount = promotion_target.get('revenue_target', 0) if promotion_target else 0
    
    # Calculate progress
    current_revenue = membership.real_estate_revenue_total or 0
    progress_data = get_promotion_progress(current_revenue, target_amount)
    
    # Get team count (Real Estate segment)
    team_count = db.query(ZynovaMember).filter(
        ZynovaMember.real_estate_upline_id == membership.id,
        ZynovaMember.is_active == True
    ).count()
    
    # Get Real Estate incentives for this user
    re_incentives = db.query(ZynovaIncentive).filter(
        or_(
            ZynovaIncentive.promoter_id == current_user.id,
            ZynovaIncentive.team_leader_id == current_user.id,
            ZynovaIncentive.zonal_manager_id == current_user.id,
            ZynovaIncentive.director_id == current_user.id
        ),
        ZynovaIncentive.category_slug.in_(['real-estate', 'real_estate'])
    ).all()
    
    # Calculate earnings by status
    pending_amount = sum(getattr(i, 'promoter_amount', 0) or 0 for i in re_incentives if i.status == 'pending')
    approved_amount = sum(getattr(i, 'promoter_amount', 0) or 0 for i in re_incentives if i.status == 'approved')
    disbursed_amount = sum(getattr(i, 'promoter_amount', 0) or 0 for i in re_incentives if i.disbursed_at is not None)
    
    return {
        "success": True,
        "data": {
            "is_member": True,
            "segment": "real_estate",
            "segment_name": "VGK Real Dreams",
            "user_id": current_user.id,
            "user_name": current_user.name,
            "current_role": current_role,
            "current_role_display": format_role_display(current_role, 'real_estate'),
            "next_role": next_role,
            "next_role_display": format_role_display(next_role, 'real_estate') if next_role else None,
            "self_revenue": current_revenue,
            "team_revenue": membership.real_estate_team_revenue or 0,
            "total_revenue": current_revenue + (membership.real_estate_team_revenue or 0),
            "promotion_target": target_amount,
            "promotion_progress": progress_data,
            "promotion_deadline": membership.real_estate_promotion_deadline.isoformat() if membership.real_estate_promotion_deadline else None,
            "team_count": team_count,
            "earnings": {
                "pending": pending_amount,
                "approved": approved_amount,
                "disbursed": disbursed_amount,
                "total": pending_amount + approved_amount + disbursed_amount
            },
            "incentive_count": len(re_incentives),
            "upline_id": membership.real_estate_upline_id
        }
    }


@router.get("/zynova/insurance/me", summary="Get user's VGK Care (Insurance) program data")
async def get_my_insurance_zynova(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's VGK Care (Insurance) Zynova program data
    Includes role, progress to next promotion, team data, and earnings
    DC Protocol: Uses MNR session priority
    """
    membership = db.query(ZynovaMember).filter(
        ZynovaMember.user_id == current_user.id,
        ZynovaMember.is_active == True
    ).first()
    
    if not membership:
        return {
            "success": True,
            "data": {
                "is_member": False,
                "segment": "insurance",
                "segment_name": "VGK Care",
                "message": "You are not yet a Zynova member in the Insurance program."
            }
        }
    
    current_role = membership.insurance_role or 'promoter'
    next_role = get_next_role(current_role)
    
    # Get promotion targets for next role
    promotion_target = ZYNOVA_INSURANCE_PROMOTION_TARGETS.get(next_role, {}) if next_role else None
    target_amount = promotion_target.get('revenue_target', 0) if promotion_target else 0
    
    # Calculate progress
    current_revenue = membership.insurance_revenue_total or 0
    progress_data = get_promotion_progress(current_revenue, target_amount)
    
    # Get team count (Insurance segment)
    team_count = db.query(ZynovaMember).filter(
        ZynovaMember.insurance_upline_id == membership.id,
        ZynovaMember.is_active == True
    ).count()
    
    # Get Insurance incentives for this user
    ins_incentives = db.query(ZynovaIncentive).filter(
        or_(
            ZynovaIncentive.promoter_id == current_user.id,
            ZynovaIncentive.team_leader_id == current_user.id,
            ZynovaIncentive.zonal_manager_id == current_user.id,
            ZynovaIncentive.director_id == current_user.id
        ),
        ZynovaIncentive.category_slug == 'insurance'
    ).all()
    
    # Calculate earnings by status
    pending_amount = sum(getattr(i, 'promoter_amount', 0) or 0 for i in ins_incentives if i.status == 'pending')
    approved_amount = sum(getattr(i, 'promoter_amount', 0) or 0 for i in ins_incentives if i.status == 'approved')
    disbursed_amount = sum(getattr(i, 'promoter_amount', 0) or 0 for i in ins_incentives if i.disbursed_at is not None)
    
    return {
        "success": True,
        "data": {
            "is_member": True,
            "segment": "insurance",
            "segment_name": "VGK Care",
            "user_id": current_user.id,
            "user_name": current_user.name,
            "current_role": current_role,
            "current_role_display": format_role_display(current_role, 'insurance'),
            "next_role": next_role,
            "next_role_display": format_role_display(next_role, 'insurance') if next_role else None,
            "self_revenue": current_revenue,
            "team_revenue": membership.insurance_team_revenue or 0,
            "total_revenue": current_revenue + (membership.insurance_team_revenue or 0),
            "promotion_target": target_amount,
            "promotion_progress": progress_data,
            "promotion_deadline": membership.insurance_promotion_deadline.isoformat() if membership.insurance_promotion_deadline else None,
            "team_count": team_count,
            "earnings": {
                "pending": pending_amount,
                "approved": approved_amount,
                "disbursed": disbursed_amount,
                "total": pending_amount + approved_amount + disbursed_amount
            },
            "incentive_count": len(ins_incentives),
            "upline_id": membership.insurance_upline_id
        }
    }


@router.get("/zynova/training/me", summary="Get user's EVolution Training Center (ETC) program data")
async def get_my_training_zynova(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's EVolution Training Center (ETC) program data
    Fetches training leads where user is MNR handler or creator
    DC Protocol: Uses MNR session priority
    """
    from app.models.signup_category import SignupCategory
    
    user_id = current_user.id
    user_id_str = str(user_id)
    
    training_category = db.query(SignupCategory).filter(
        SignupCategory.slug.in_(['training', 'etc', 'evolution-tc'])
    ).first()
    
    category_id = training_category.id if training_category else None
    
    query = db.query(CRMLead).filter(
        or_(
            CRMLead.mnr_handler_id == user_id,
            and_(
                CRMLead.created_by_type == 'member',
                CRMLead.created_by_id == user_id_str
            )
        )
    )
    
    if category_id:
        query = query.filter(CRMLead.category_id == category_id)
    else:
        query = query.filter(
            or_(
                CRMLead.category_id.is_(None),
                CRMLead.category_id == category_id
            )
        )
    
    leads = query.order_by(CRMLead.created_at.desc()).limit(100).all()
    
    if not leads:
        return {
            "success": True,
            "data": {
                "is_member": True,
                "segment": "training",
                "segment_name": "EVolution Training Center",
                "user_id": user_id,
                "user_name": current_user.name,
                "leads": [],
                "summary": {
                    "total_leads": 0,
                    "won_deals": 0,
                    "in_progress": 0,
                    "points_utilized": 0,
                    "total_earnings": 0
                }
            }
        }
    
    won_statuses = ['won', 'closed', 'completed']
    won_leads = [l for l in leads if (l.status or '').lower() in won_statuses]
    in_progress_leads = [l for l in leads if (l.status or '').lower() == 'in_progress']
    
    total_points = sum(getattr(l, 'points_used', 0) or 0 for l in leads)
    total_earnings = sum(getattr(l, 'estimated_value', 0) or 0 for l in won_leads)
    
    leads_data = []
    for lead in leads:
        category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first() if lead.category_id else None
        leads_data.append({
            "id": lead.id,
            "name": lead.name,
            "phone": lead.phone,
            "email": lead.email,
            "course_name": lead.requirements or lead.looking_for or (category.name if category else None),
            "status": lead.status or 'new',
            "priority": lead.priority,
            "points_used": getattr(lead, 'points_used', 0) or 0,
            "earnings": getattr(lead, 'estimated_value', 0) or 0 if (lead.status or '').lower() in won_statuses else 0,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "last_followup": lead.last_followup_at.isoformat() if lead.last_followup_at else None
        })
    
    return {
        "success": True,
        "data": {
            "is_member": True,
            "segment": "training",
            "segment_name": "EVolution Training Center",
            "user_id": user_id,
            "user_name": current_user.name,
            "leads": leads_data,
            "summary": {
                "total_leads": len(leads),
                "won_deals": len(won_leads),
                "in_progress": len(in_progress_leads),
                "points_utilized": total_points,
                "total_earnings": total_earnings
            }
        }
    }


@router.get("/zynova/real-estate/team", summary="Get user's VGK Real Dreams team hierarchy")
async def get_my_real_estate_team(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's VGK Real Dreams (Real Estate) team hierarchy
    DC Protocol: Uses MNR session priority
    """
    membership = db.query(ZynovaMember).filter(
        ZynovaMember.user_id == current_user.id,
        ZynovaMember.is_active == True
    ).first()
    
    if not membership:
        return {"success": True, "data": {"team": [], "count": 0}}
    
    # Get direct team members in Real Estate segment
    team_members = db.query(ZynovaMember).filter(
        ZynovaMember.real_estate_upline_id == membership.id,
        ZynovaMember.is_active == True
    ).all()
    
    team_list = []
    for member in team_members:
        user = db.query(User).filter(User.id == member.user_id).first()
        team_list.append({
            "member_id": member.id,
            "user_id": member.user_id,
            "name": user.full_name if user else "Unknown",
            "role": member.real_estate_role,
            "role_display": format_role_display(member.real_estate_role, 'real_estate'),
            "self_revenue": member.real_estate_revenue_total or 0,
            "team_revenue": member.real_estate_team_revenue or 0,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None
        })
    
    return {
        "success": True,
        "data": {
            "team": team_list,
            "count": len(team_list)
        }
    }


@router.get("/zynova/insurance/team", summary="Get user's VGK Care team hierarchy")
async def get_my_insurance_team(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get the current user's VGK Care (Insurance) team hierarchy
    DC Protocol: Uses MNR session priority
    """
    membership = db.query(ZynovaMember).filter(
        ZynovaMember.user_id == current_user.id,
        ZynovaMember.is_active == True
    ).first()
    
    if not membership:
        return {"success": True, "data": {"team": [], "count": 0}}
    
    # Get direct team members in Insurance segment
    team_members = db.query(ZynovaMember).filter(
        ZynovaMember.insurance_upline_id == membership.id,
        ZynovaMember.is_active == True
    ).all()
    
    team_list = []
    for member in team_members:
        user = db.query(User).filter(User.id == member.user_id).first()
        team_list.append({
            "member_id": member.id,
            "user_id": member.user_id,
            "name": user.name if user else "Unknown",
            "role": member.insurance_role,
            "role_display": format_role_display(member.insurance_role, 'insurance'),
            "self_revenue": member.insurance_revenue_total or 0,
            "team_revenue": member.insurance_team_revenue or 0,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None
        })
    
    return {
        "success": True,
        "data": {
            "team": team_list,
            "count": len(team_list)
        }
    }


class ZynovaStatusChangeRequest(BaseModel):
    """Request model for changing Zynova member status"""
    is_active: bool = Field(..., description="New status: True=Active, False=Deactivated")
    reason: str = Field(..., min_length=10, max_length=500, description="Mandatory reason for status change")


@router.patch("/zynova/members/{member_id}/status", summary="Change Zynova member status (Activate/Deactivate)")
async def change_zynova_member_status(
    member_id: int,
    request: ZynovaStatusChangeRequest = Body(...),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Activate or Deactivate a Zynova member with mandatory reason
    DC Protocol: VGK/Finance staff access with audit trail
    Business Rule: When deactivated, incomes are calculated but held (not disbursed)
    """
    member = db.query(ZynovaMember).filter(ZynovaMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    old_status = member.is_active
    new_status = request.is_active
    
    if old_status == new_status:
        status_text = "active" if new_status else "deactivated"
        return {
            "success": False,
            "message": f"Member is already {status_text}. No change made."
        }
    
    member.is_active = new_status
    
    incentives_held = 0
    incentives_restored = 0
    
    if not new_status:
        member.deactivation_reason = request.reason
        member.deactivation_date = get_indian_time()
        member.deactivated_by_id = current_staff.id
        member.reactivation_date = None
        member.reactivated_by_id = None
        
        pending_incentives = db.query(ZynovaIncentive).filter(
            ZynovaIncentive.zynova_member_id == member.id,
            ZynovaIncentive.status.in_(['pending', 'approved']),
            ZynovaIncentive.disbursed_at.is_(None)
        ).all()
        
        for incentive in pending_incentives:
            incentive.previous_status = incentive.status
            incentive.status = 'on_hold'
            incentive.status_changed_at = get_indian_time()
            incentive.status_changed_reason = f"Member deactivated: {request.reason}"
            incentives_held += 1
    else:
        member.reactivation_date = get_indian_time()
        member.reactivated_by_id = current_staff.id
        
        held_incentives = db.query(ZynovaIncentive).filter(
            ZynovaIncentive.zynova_member_id == member.id,
            ZynovaIncentive.status == 'on_hold'
        ).all()
        
        for incentive in held_incentives:
            if incentive.previous_status:
                incentive.status = incentive.previous_status
            else:
                incentive.status = 'pending'
            incentive.previous_status = None
            incentive.status_changed_at = get_indian_time()
            incentive.status_changed_reason = f"Member reactivated: {request.reason}"
            incentives_restored += 1
    
    db.commit()
    db.refresh(member)
    
    user = db.query(User).filter(User.id == member.user_id).first()
    action = "activated" if new_status else "deactivated"
    incentive_msg = f" ({incentives_restored} incentives restored)" if incentives_restored else (f" ({incentives_held} incentives put on hold)" if incentives_held else "")
    
    return {
        "success": True,
        "message": f"Member {user.name if user else member.user_id} has been {action} successfully.{incentive_msg}",
        "data": {
            "id": member.id,
            "user_id": member.user_id,
            "user_name": user.name if user else None,
            "is_active": member.is_active,
            "reason": request.reason,
            "updated_at": member.updated_at.isoformat() if member.updated_at else None,
            "deactivation_date": member.deactivation_date.isoformat() if member.deactivation_date else None,
            "reactivation_date": member.reactivation_date.isoformat() if member.reactivation_date else None
        }
    }


class ZynovaMemberEditRequest(BaseModel):
    """Request model for editing Zynova member details"""
    real_estate_role: Optional[str] = Field(None, description="Real Estate segment role")
    insurance_role: Optional[str] = Field(None, description="Insurance segment role")
    real_estate_upline_id: Optional[int] = Field(None, description="Real Estate upline member ID")
    insurance_upline_id: Optional[int] = Field(None, description="Insurance upline member ID")
    real_estate_promotion_deadline: Optional[str] = Field(None, description="Real Estate promotion deadline (ISO format)")
    insurance_promotion_deadline: Optional[str] = Field(None, description="Insurance promotion deadline (ISO format)")


@router.put("/zynova/members/{member_id}", summary="Update Zynova member details (Staff/Admin only)")
async def update_zynova_member(
    member_id: int,
    request: ZynovaMemberEditRequest = Body(...),
    db: Session = Depends(get_db),
    current_staff: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update a Zynova member's segment-specific details (roles, uplines, deadlines)
    DC Protocol: VGK/Finance staff access with audit
    """
    member = db.query(ZynovaMember).filter(ZynovaMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    valid_roles = ["promoter", "team_leader", "zonal_manager", "director"]
    changes = []
    
    if request.real_estate_role is not None:
        if request.real_estate_role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid Real Estate role. Must be one of: {valid_roles}")
        old_role = member.real_estate_role
        if old_role != request.real_estate_role:
            member.real_estate_role = request.real_estate_role
            member.real_estate_promoted_at = get_indian_time()
            member.real_estate_promotion_deadline = get_indian_time() + timedelta(days=180)
            changes.append(f"Real Estate role: {old_role} -> {request.real_estate_role}")
    
    if request.insurance_role is not None:
        if request.insurance_role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid Insurance role. Must be one of: {valid_roles}")
        old_role = member.insurance_role
        if old_role != request.insurance_role:
            member.insurance_role = request.insurance_role
            member.insurance_promoted_at = get_indian_time()
            member.insurance_promotion_deadline = get_indian_time() + timedelta(days=180)
            changes.append(f"Insurance role: {old_role} -> {request.insurance_role}")
    
    if request.real_estate_upline_id is not None:
        if request.real_estate_upline_id != member.real_estate_upline_id:
            if request.real_estate_upline_id > 0:
                upline = db.query(ZynovaMember).filter(ZynovaMember.id == request.real_estate_upline_id).first()
                if not upline:
                    raise HTTPException(status_code=400, detail="Real Estate upline member not found")
            member.real_estate_upline_id = request.real_estate_upline_id if request.real_estate_upline_id > 0 else None
            changes.append("Real Estate upline updated")
    
    if request.insurance_upline_id is not None:
        if request.insurance_upline_id != member.insurance_upline_id:
            if request.insurance_upline_id > 0:
                upline = db.query(ZynovaMember).filter(ZynovaMember.id == request.insurance_upline_id).first()
                if not upline:
                    raise HTTPException(status_code=400, detail="Insurance upline member not found")
            member.insurance_upline_id = request.insurance_upline_id if request.insurance_upline_id > 0 else None
            changes.append("Insurance upline updated")
    
    if request.real_estate_promotion_deadline:
        try:
            deadline = datetime.fromisoformat(request.real_estate_promotion_deadline.replace('Z', '+00:00'))
            member.real_estate_promotion_deadline = deadline
            changes.append("Real Estate promotion deadline updated")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Real Estate promotion deadline format")
    
    if request.insurance_promotion_deadline:
        try:
            deadline = datetime.fromisoformat(request.insurance_promotion_deadline.replace('Z', '+00:00'))
            member.insurance_promotion_deadline = deadline
            changes.append("Insurance promotion deadline updated")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Insurance promotion deadline format")
    
    if not changes:
        return {"success": True, "message": "No changes made", "data": member.to_dict()}
    
    db.commit()
    db.refresh(member)
    
    user = db.query(User).filter(User.id == member.user_id).first()
    
    return {
        "success": True,
        "message": f"Member updated successfully. Changes: {', '.join(changes)}",
        "data": {
            "id": member.id,
            "user_id": member.user_id,
            "user_name": user.name if user else None,
            "real_estate_role": member.real_estate_role,
            "real_estate_role_display": format_role_display(member.real_estate_role, 'real_estate'),
            "insurance_role": member.insurance_role,
            "insurance_role_display": format_role_display(member.insurance_role, 'insurance'),
            "real_estate_upline_id": member.real_estate_upline_id,
            "insurance_upline_id": member.insurance_upline_id,
            "real_estate_promotion_deadline": member.real_estate_promotion_deadline.isoformat() if member.real_estate_promotion_deadline else None,
            "insurance_promotion_deadline": member.insurance_promotion_deadline.isoformat() if member.insurance_promotion_deadline else None,
            "updated_at": member.updated_at.isoformat() if member.updated_at else None
        }
    }
