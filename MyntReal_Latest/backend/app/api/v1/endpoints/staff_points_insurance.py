"""
Staff MNR Points & Insurance Management API
DC Protocol Feb 2026: Unified management of MNR points and accidental insurance

Features:
- Points Management: Credit, Debit, View History with benefit categories
- Insurance Management: CRUD operations, eligibility check, issue insurance

Eligibility Rules:
- New users (activated >= Feb 3, 2026): Auto-eligible for insurance
- Old users (activated < Feb 3, 2026): Need 2 direct referrals activated after Feb 3, 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text as sa_text
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.user import User
from app.models.myntreal_incentive import (
    MNRPointsBalance, 
    MNRPointsTransaction, 
    MNRAccidentalInsurance,
    PointsBenefitCategory
)
from app.models.ved_team import VedTeamMember
from app.models.user_leg_metrics import UserLegMetrics
from app.models.transaction import PendingIncome
import pytz

router = APIRouter()

INSURANCE_ELIGIBILITY_DATE = datetime(2026, 2, 3, 0, 0, 0)
REQUIRED_REFERRALS_FOR_OLD_USERS = 2
DEFAULT_COMPANY_ID = 1


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class PointsAdjustmentRequest(BaseModel):
    user_id: str
    transaction_type: str
    amount: float
    benefit_category: str
    description: Optional[str] = None


class InsuranceIssueRequest(BaseModel):
    user_id: str
    policy_number: str
    insurer_name: str
    insured_date: str
    expiry_date: str
    notes: Optional[str] = None


class InsuranceUpdateRequest(BaseModel):
    policy_number: Optional[str] = None
    insurer_name: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("/benefit-categories")
async def get_benefit_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Get all active benefit categories for points transactions"""
    categories = db.query(PointsBenefitCategory).filter(
        PointsBenefitCategory.is_active == True
    ).order_by(PointsBenefitCategory.display_order).all()
    
    if not categories:
        default_categories = [
            {"code": "VGK_REAL_DREAMS", "name": "VGK Real Dreams", "order": 1},
            {"code": "VGK_CARE", "name": "VGK Care", "order": 2},
            {"code": "EV_PURCHASE", "name": "EV Purchase", "order": 3},
            {"code": "SOLAR_SERVICES", "name": "Solar Services", "order": 4},
            {"code": "MANUAL_CREDIT", "name": "Manual Credit", "order": 5},
            {"code": "MANUAL_DEBIT", "name": "Manual Debit", "order": 6},
            {"code": "REFUND", "name": "Refund", "order": 7},
            {"code": "OTHER", "name": "Other", "order": 99},
        ]
        return {"success": True, "categories": default_categories}
    
    return {
        "success": True,
        "categories": [c.to_dict() for c in categories]
    }


@router.post("/adjust-points")
async def adjust_points(
    data: PointsAdjustmentRequest = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Adjust points for an MNR user (credit or debit)"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == data.user_id
    ).first()
    
    if not balance:
        raise HTTPException(status_code=404, detail="User has no points balance record")
    
    # Validate benefit_category
    ALLOWED_CATEGORIES = ['VGK_REAL_DREAMS', 'VGK_CARE', 'EV_PURCHASE', 'SOLAR_SERVICES', 'MANUAL_CREDIT', 'MANUAL_DEBIT', 'REFUND', 'OTHER']
    if data.benefit_category and data.benefit_category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid benefit category. Allowed: {', '.join(ALLOWED_CATEGORIES)}")

    if data.transaction_type not in ['credit', 'debit']:
        raise HTTPException(status_code=400, detail="Invalid transaction type. Use 'credit' or 'debit'")
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    if data.transaction_type == 'debit' and balance.current_balance < data.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance. Current: {balance.current_balance}, Requested: {data.amount}"
        )
    
    old_balance = balance.current_balance
    
    if data.transaction_type == 'credit':
        balance.current_balance += data.amount
        balance.total_credited += data.amount
    else:
        balance.current_balance -= data.amount
        balance.total_consumed += data.amount
    
    transaction = MNRPointsTransaction(
        company_id=balance.company_id,
        user_id=data.user_id,
        transaction_type=data.transaction_type,
        amount=data.amount if data.transaction_type == 'credit' else -data.amount,
        balance_after=balance.current_balance,
        benefit_category=data.benefit_category,
        description=data.description or f"Staff adjustment: {data.benefit_category}",
        created_by_id=current_user.get('emp_code') or current_user.get('id'),
        created_by_type='staff'
    )
    
    db.add(transaction)
    db.commit()
    
    return {
        "success": True,
        "message": f"Points {'credited' if data.transaction_type == 'credit' else 'debited'} successfully",
        "old_balance": old_balance,
        "new_balance": balance.current_balance,
        "transaction_id": transaction.id
    }


@router.get("/transaction-history/{user_id}")
async def get_transaction_history(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Get points transaction history for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    query = db.query(MNRPointsTransaction).filter(
        MNRPointsTransaction.user_id == user_id
    ).order_by(MNRPointsTransaction.created_at.desc())
    
    total = query.count()
    transactions = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "user_id": user_id,
        "user_name": user.name,
        "total": total,
        "transactions": [t.to_dict() for t in transactions]
    }


@router.get("/insurance/eligibility/{user_id}")
async def check_insurance_eligibility(
    user_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Check if a user is eligible for accidental insurance"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.coupon_status not in ('Active', 'Activated'):
        return {
            "success": True,
            "eligible": False,
            "reason": "User is not an activated (paid) member",
            "eligibility_type": None
        }
    
    existing = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.user_id == user_id,
        MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
    ).first()
    
    if existing:
        return {
            "success": True,
            "eligible": False,
            "reason": "User already has active insurance",
            "eligibility_type": None,
            "existing_insurance": existing.to_dict()
        }
    
    is_welcome_coupon = getattr(user, 'is_welcome_coupon', False)
    activation_date = user.activation_date or user.coupon_status_changed_at
    
    if not is_welcome_coupon and activation_date and activation_date >= INSURANCE_ELIGIBILITY_DATE:
        return {
            "success": True,
            "eligible": True,
            "eligibility_type": "new_activation",
            "reason": f"Activated on/after Feb 3, 2026 ({activation_date.strftime('%d %b %Y')})",
            "referrals_needed": 0,
            "referrals_count": 0
        }
    
    referral_count = db.query(func.count(User.id)).filter(
        User.referrer_id == user_id,
        User.coupon_status.in_(['Active', 'Activated']),
        User.is_welcome_coupon.is_(False),
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date == None,
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    ).scalar() or 0
    
    if is_welcome_coupon:
        WELCOME_COUPON_REFERRALS = 2
        if referral_count >= WELCOME_COUPON_REFERRALS:
            return {
                "success": True,
                "eligible": True,
                "eligibility_type": "welcome_coupon_qualified",
                "reason": f"Welcome Coupon user with {referral_count} qualifying referrals",
                "referrals_needed": 0,
                "referrals_count": referral_count
            }
        return {
            "success": True,
            "eligible": False,
            "eligibility_type": "welcome_coupon_pending",
            "reason": f"Welcome Coupon user needs {WELCOME_COUPON_REFERRALS - referral_count} more non-Welcome Coupon referral(s)",
            "referrals_needed": WELCOME_COUPON_REFERRALS - referral_count,
            "referrals_count": referral_count
        }
    
    if referral_count >= REQUIRED_REFERRALS_FOR_OLD_USERS:
        return {
            "success": True,
            "eligible": True,
            "eligibility_type": "referral_unlock",
            "reason": f"Has {referral_count} direct referrals activated after Feb 3, 2026",
            "referrals_needed": 0,
            "referrals_count": referral_count
        }
    
    return {
        "success": True,
        "eligible": False,
        "eligibility_type": "referral_pending",
        "reason": f"Need {REQUIRED_REFERRALS_FOR_OLD_USERS - referral_count} more direct referral(s) activated after Feb 3, 2026",
        "referrals_needed": REQUIRED_REFERRALS_FOR_OLD_USERS - referral_count,
        "referrals_count": referral_count
    }


@router.get("/insurance/eligible-users")
async def get_eligible_users(
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, description="all, eligible, issued, pending"),
    kyc_status: Optional[str] = Query(None, description="Filter by KYC: Pending, Submitted, Approved, Rejected"),
    eligibility_filter: Optional[str] = Query(None, description="Filter: new_activation, referral_unlock, referral_pending"),
    activation_status: Optional[str] = Query(None, description="Filter by activation: activated, not_activated"),
    package_filter: Optional[str] = Query(None, description="Filter by package: Platinum, Diamond, Star"),
    reg_start: Optional[str] = Query(None, description="Registration date start (YYYY-MM-DD)"),
    reg_end: Optional[str] = Query(None, description="Registration date end (YYYY-MM-DD)"),
    act_start: Optional[str] = Query(None, description="Activation date start (YYYY-MM-DD)"),
    act_end: Optional[str] = Query(None, description="Activation date end (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Get list of users with their insurance eligibility status (optimized batch queries)"""
    from sqlalchemy.orm import aliased
    
    query = db.query(User).filter(User.coupon_status.in_(['Active', 'Activated']))
    
    if search:
        query = query.filter(
            or_(
                User.id.ilike(f'%{search}%'),
                User.name.ilike(f'%{search}%')
            )
        )
    
    if kyc_status:
        query = query.filter(func.lower(User.kyc_status) == kyc_status.lower())
    
    if activation_status:
        if activation_status == 'activated':
            query = query.filter(User.account_status == 'activated')
        elif activation_status == 'not_activated':
            query = query.filter(or_(User.account_status != 'activated', User.account_status.is_(None)))

    if package_filter:
        pf = package_filter.lower()
        if pf == 'platinum':
            query = query.filter(User.package_points >= 1.0)
        elif pf == 'diamond':
            query = query.filter(User.package_points >= 0.5, User.package_points < 1.0)
        elif pf in ('star', 'star / loyal'):
            query = query.filter(or_(User.package_points < 0.5, User.package_points == None))

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
    users = query.order_by(User.activation_date.desc().nullslast()).offset(offset).limit(limit).all()
    
    if not users:
        return {"success": True, "total": total, "results": []}
    
    user_ids = [u.id for u in users]
    
    insurance_records = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.user_id.in_(user_ids)
    ).all()
    insurance_map = {}
    for ins in insurance_records:
        if ins.user_id not in insurance_map:
            insurance_map[ins.user_id] = ins
    
    Referral = aliased(User)
    referral_counts_rows = db.query(
        Referral.referrer_id,
        func.count(Referral.id)
    ).filter(
        Referral.referrer_id.in_(user_ids),
        Referral.coupon_status.in_(['Active', 'Activated']),
        Referral.is_welcome_coupon.is_(False),
        or_(
            Referral.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                Referral.activation_date == None,
                Referral.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    ).group_by(Referral.referrer_id).all()
    referral_map = {row[0]: row[1] for row in referral_counts_rows}
    
    WELCOME_COUPON_REFERRALS_NEEDED = 2
    
    results = []
    for user in users:
        existing = insurance_map.get(user.id)
        activation_date = user.activation_date or user.coupon_status_changed_at
        is_wc = getattr(user, 'is_welcome_coupon', False)
        is_new_activation = (not is_wc) and activation_date and activation_date >= INSURANCE_ELIGIBILITY_DATE
        
        if is_wc:
            referral_count = referral_map.get(user.id, 0)
            if referral_count >= WELCOME_COUPON_REFERRALS_NEEDED:
                eligibility_type = "welcome_coupon_qualified"
                is_eligible = True
            else:
                eligibility_type = "welcome_coupon_pending"
                is_eligible = False
        elif is_new_activation:
            referral_count = 0
            eligibility_type = "new_activation"
            is_eligible = True
        elif referral_map.get(user.id, 0) >= REQUIRED_REFERRALS_FOR_OLD_USERS:
            referral_count = referral_map.get(user.id, 0)
            eligibility_type = "referral_unlock"
            is_eligible = True
        else:
            referral_count = referral_map.get(user.id, 0)
            eligibility_type = "referral_pending"
            is_eligible = False
        
        insurance_status = existing.status if existing else ("Eligible" if is_eligible else "Not Eligible")
        
        if status_filter:
            if status_filter == 'eligible' and not (is_eligible and not existing):
                continue
            elif status_filter == 'issued' and not (existing and existing.status in ['Active', 'Issued']):
                continue
            elif status_filter == 'pending' and not (not is_eligible and not existing):
                continue
        
        if eligibility_filter and eligibility_filter != eligibility_type:
            continue
        
        referrals_needed = 0
        if is_wc:
            referrals_needed = max(0, WELCOME_COUPON_REFERRALS_NEEDED - referral_count)
        elif not is_new_activation:
            referrals_needed = max(0, REQUIRED_REFERRALS_FOR_OLD_USERS - referral_count)
        
        results.append({
            "user_id": user.id,
            "user_name": user.name,
            "activation_date": activation_date.isoformat() if activation_date else None,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "kyc_status": getattr(user, 'kyc_status', 'Pending') or 'Pending',
            "eligibility_type": eligibility_type,
            "is_eligible": is_eligible,
            "is_welcome_coupon": is_wc,
            "referrals_count": referral_count,
            "referrals_needed": referrals_needed,
            "insurance_status": insurance_status,
            "insurance": existing.to_dict() if existing else None
        })
    
    all_active_count = db.query(func.count(User.id)).filter(
        User.coupon_status.in_(['Active', 'Activated'])
    ).scalar() or 0

    issued_agg = db.query(
        func.count(MNRAccidentalInsurance.id),
        func.coalesce(func.sum(MNRAccidentalInsurance.insured_amount), 0)
    ).filter(
        MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
    ).first()
    total_issued = issued_agg[0] if issued_agg else 0
    total_issued_amount = float(issued_agg[1]) if issued_agg else 0

    eligible_not_issued = len([r for r in results if r.get('is_eligible') and not r.get('insurance')])
    budget_required = (eligible_not_issued + total_issued) * 500

    return {
        "success": True,
        "total": total,
        "results": results,
        "summary": {
            "total_active_members": all_active_count,
            "total_issued": total_issued,
            "total_issued_amount": total_issued_amount,
            "eligible_pending": eligible_not_issued,
            "budget_required": budget_required
        }
    }


@router.post("/insurance/issue")
async def issue_insurance(
    data: InsuranceIssueRequest = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Issue accidental insurance to an eligible user"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.user_id == data.user_id,
        MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already has active insurance")
    
    activation_date = user.activation_date or user.coupon_status_changed_at
    is_wc_issue = getattr(user, 'is_welcome_coupon', False)
    is_new_activation = (not is_wc_issue) and activation_date and activation_date >= INSURANCE_ELIGIBILITY_DATE
    
    referral_count = 0
    WELCOME_COUPON_REFERRALS = 2
    if is_wc_issue:
        referral_count = db.query(func.count(User.id)).filter(
            User.referrer_id == user.id,
            User.coupon_status.in_(['Active', 'Activated']),
            User.is_welcome_coupon.is_(False),
            or_(
                User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
                and_(
                    User.activation_date == None,
                    User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
                )
            )
        ).scalar() or 0
        if referral_count >= WELCOME_COUPON_REFERRALS:
            eligibility_type = "welcome_coupon_qualified"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Welcome Coupon user needs {WELCOME_COUPON_REFERRALS - referral_count} more non-Welcome Coupon referral(s) for insurance"
            )
    elif is_new_activation:
        eligibility_type = "new_activation"
    else:
        referral_count = db.query(func.count(User.id)).filter(
            User.referrer_id == user.id,
            User.coupon_status.in_(['Active', 'Activated']),
            User.is_welcome_coupon.is_(False),
            or_(
                User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
                and_(
                    User.activation_date == None,
                    User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
                )
            )
        ).scalar() or 0
        
        if referral_count >= REQUIRED_REFERRALS_FOR_OLD_USERS:
            eligibility_type = "referral_unlock"
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"User not eligible. Needs {REQUIRED_REFERRALS_FOR_OLD_USERS - referral_count} more referral(s)"
            )
    
    try:
        insured_date = datetime.fromisoformat(data.insured_date.replace('Z', '+00:00')).replace(tzinfo=None)
        expiry_date = datetime.fromisoformat(data.expiry_date.replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        try:
            insured_date = datetime.strptime(data.insured_date[:10], '%Y-%m-%d')
            expiry_date = datetime.strptime(data.expiry_date[:10], '%Y-%m-%d')
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    insurance = MNRAccidentalInsurance(
        user_id=data.user_id,
        policy_number=data.policy_number,
        insurer_name=data.insurer_name,
        insured_amount=500000,
        insured_date=insured_date,
        expiry_date=expiry_date,
        eligibility_type=eligibility_type,
        eligibility_met_at=get_indian_time(),
        referral_count_at_eligibility=referral_count,
        status='Issued',
        issued_by_id=current_user.get('emp_code') or current_user.get('id'),
        issued_by_type='staff',
        issued_at=get_indian_time(),
        notes=data.notes
    )
    
    db.add(insurance)
    db.commit()
    
    return {
        "success": True,
        "message": "Insurance issued successfully",
        "insurance": insurance.to_dict()
    }


@router.put("/insurance/{insurance_id}")
async def update_insurance(
    insurance_id: int,
    data: InsuranceUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Update insurance details"""
    insurance = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.id == insurance_id
    ).first()
    
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    if data.policy_number is not None:
        insurance.policy_number = data.policy_number
    if data.insurer_name is not None:
        insurance.insurer_name = data.insurer_name
    if data.expiry_date is not None:
        try:
            insurance.expiry_date = datetime.fromisoformat(data.expiry_date.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            try:
                insurance.expiry_date = datetime.strptime(data.expiry_date[:10], '%Y-%m-%d')
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid expiry date format")
    if data.notes is not None:
        insurance.notes = data.notes
    
    db.commit()
    
    return {
        "success": True,
        "message": "Insurance updated successfully",
        "insurance": insurance.to_dict()
    }


@router.get("/insurance/user/{user_id}")
async def get_user_insurance(
    user_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """Get insurance details for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    insurance = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.user_id == user_id
    ).order_by(MNRAccidentalInsurance.created_at.desc()).first()
    
    return {
        "success": True,
        "user_id": user_id,
        "user_name": user.name,
        "insurance": insurance.to_dict() if insurance else None
    }


@router.get("/user/insurance-status")
async def get_user_insurance_status_public(
    db: Session = Depends(get_db)
):
    """
    Public endpoint for MNR user to check their own insurance status
    (For banner display on user dashboard)
    """
    from app.core.security import get_current_user
    from fastapi import Request
    return {"success": False, "message": "Use /api/v1/user/my-insurance-status instead"}


@router.get("/ved-details/{mnr_id}")
async def get_ved_details(
    mnr_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    Ved Details Tab: For a searched MNR ID, returns all Ved Owners sitting in their
    binary downline — showing their eligibility, group side (A/B), ved heads, ved team
    members, nested ved owners, and exactly where/why income is lost.

    DC Protocol: Single source of truth via ved_team_member + placement + user tables.
    No schema changes. Read-only.
    Performance: All data fetched in batch phases — zero N+1 SQL in any loop.
    Caps: depth ≤ 15 levels, max 50 ved owners returned (truncated=true if more exist).
    """

    mnr_id = mnr_id.strip().upper()

    user = db.query(User).filter(User.id == mnr_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"MNR ID {mnr_id} not found")

    def fmt_date(d):
        return d.strftime('%Y-%m-%d') if d else None

    def get_package_label(points):
        p = float(points or 0)
        if p >= 1.0: return "Platinum"
        if p >= 0.5: return "Diamond"
        if p > 0:   return "Blue"
        return "Loyal"

    def get_key_eligibility(m):
        if not m:
            return "Ineligible"
        if m.has_left_direct and m.has_right_direct:
            return "Eligible"
        if m.has_left_direct or m.has_right_direct:
            return "Partial"
        return "Ineligible"

    def get_group_status(m):
        if not m:
            return "None"
        if m.has_left_direct and m.has_right_direct:
            return "Both Active"
        if m.has_left_direct:
            return "Only Left (A)"
        if m.has_right_direct:
            return "Only Right (B)"
        return "None"

    def compute_income_loss(owner_activated, pkg_pts, first_match_ok, key_elig, group_status, heads_data):
        if not owner_activated:
            return "Not Activated"
        if pkg_pts == 0:
            return "Zero Package (Blue/Loyal)"
        if not first_match_ok:
            return "First Matching Not Achieved"
        if key_elig == "Ineligible":
            return "No Group Eligibility (Need Both Sides)"
        if key_elig == "Partial":
            return f"Partial Eligibility — {group_status}"
        if heads_data and any(not h["head_activated"] for h in heads_data):
            return "Ved Head Not Activated"
        return "Eligible"

    # ── Phase 1: Searched user metrics ─────────────────────────────────────────
    metrics_self        = db.query(UserLegMetrics).filter(UserLegMetrics.user_id == mnr_id).first()
    self_activated      = user.activation_date is not None and float(user.package_points or 0) > 0
    self_first_match_ok = bool(metrics_self.first_match_achieved) if metrics_self else False
    self_key_elig       = get_key_eligibility(metrics_self)

    searched_user_data = {
        "mnr_id":                   user.id,
        "name":                     user.name,
        "status":                   "Active" if self_activated else "Inactive",
        "activated_date":           fmt_date(user.activation_date),
        "registered_date":          fmt_date(user.registration_date),
        "package_type":             get_package_label(user.package_points),
        "package_points":           float(user.package_points or 0),
        "kyc_status":               user.kyc_status,
        "coupon_status":            user.coupon_status,
        "is_ved_head":              bool(user.is_ved),
        "ved_owner_id":             user.ved_owner_id,
        "key_eligibility":          self_key_elig,
        "group_status":             get_group_status(metrics_self),
        "eligible_for_ved_income":  self_activated and self_first_match_ok and self_key_elig == "Eligible",
        "total_direct_referrals":   metrics_self.total_direct_referrals if metrics_self else 0,
        "active_direct_referrals":  metrics_self.active_direct_referrals if metrics_self else 0,
        "ved_team_total":           metrics_self.ved_team_total if metrics_self else 0,
        "ved_team_active":          metrics_self.ved_team_active if metrics_self else 0,
        "left_points":              float(metrics_self.left_points) if metrics_self else 0,
        "right_points":             float(metrics_self.right_points) if metrics_self else 0,
    }

    # ── Phase 2: Downline — depth ≤ 15, cap at 50 ved owners ───────────────────
    VED_OWNER_LIMIT = 50
    downline_q = sa_text("""
        WITH RECURSIVE downline AS (
            SELECT p.child_id,
                   p.side AS group_side,
                   1      AS depth
            FROM   placement p
            WHERE  p.parent_id = :mnr_id

            UNION ALL

            SELECT p.child_id,
                   d.group_side,
                   d.depth + 1
            FROM   downline d
            JOIN   placement p ON p.parent_id = d.child_id
            WHERE  d.depth < 15
        ),
        deduped AS (
            SELECT DISTINCT ON (child_id) child_id, group_side, depth
            FROM   downline
            ORDER  BY child_id, depth ASC
        )
        SELECT d.child_id, d.group_side, d.depth
        FROM   deduped d
        WHERE  EXISTS (
            SELECT 1 FROM ved_team_member vtm
            WHERE  vtm.ved_owner_id = d.child_id AND vtm.is_active = true
        )
        ORDER  BY d.depth, d.child_id
        LIMIT  :lim
    """)
    downline_rows = db.execute(downline_q, {"mnr_id": mnr_id, "lim": VED_OWNER_LIMIT + 1}).fetchall()

    truncated = len(downline_rows) > VED_OWNER_LIMIT
    if truncated:
        downline_rows = downline_rows[:VED_OWNER_LIMIT]

    owner_user_ids = [r[0] for r in downline_rows]

    if not owner_user_ids:
        return {
            "success":       True,
            "searched_user": searched_user_data,
            "ved_owners":    [],
            "summary": {
                "total_ved_owners": 0, "group_a_count": 0, "group_b_count": 0,
                "eligible_count": 0, "income_loss_count": 0, "income_earned_count": 0,
                "total_ved_members": 0, "activated_members": 0, "nested_ved_owners": 0,
            },
            "truncated": False,
        }

    # ── Phase 3: Batch load owners, metrics, income ─────────────────────────────
    owner_users_map   = {ou.id: ou for ou in
                         db.query(User).filter(User.id.in_(owner_user_ids)).all()}
    owner_metrics_map = {om.user_id: om for om in
                         db.query(UserLegMetrics).filter(UserLegMetrics.user_id.in_(owner_user_ids)).all()}

    owner_income_map: dict = {}
    for pi in (
        db.query(PendingIncome)
        .filter(
            PendingIncome.user_id.in_(owner_user_ids),
            PendingIncome.income_type == "Ved Income"
        )
        .order_by(PendingIncome.business_date.desc())
        .limit(500)
        .all()
    ):
        owner_income_map.setdefault(pi.user_id, []).append(pi)

    # ── Phase 3b: Batch load ved_income_block_log for all owners ────────────────
    block_log_rows = db.execute(sa_text("""
        SELECT ved_owner_id, income_block_reason,
               income_block_first_tagged_at, income_block_last_updated_at
        FROM   ved_income_block_log
        WHERE  ved_owner_id = ANY(:ids)
    """), {"ids": owner_user_ids}).fetchall()
    block_log_map = {r[0]: r for r in block_log_rows}

    # ── Phase 4: Batch load ALL VedTeamMember rows for all owners at once ───────
    all_vtm_rows = db.query(VedTeamMember).filter(
        VedTeamMember.ved_owner_id.in_(owner_user_ids),
        VedTeamMember.is_active == True
    ).all()

    vtm_by_owner: dict = {}
    for vr in all_vtm_rows:
        vtm_by_owner.setdefault(vr.ved_owner_id, []).append(vr)

    all_member_ids_global = list({vr.member_id  for vr in all_vtm_rows})
    all_head_ids_global   = list({vr.ved_head_id for vr in all_vtm_rows})

    # ── Phase 5: Batch load all member users ────────────────────────────────────
    member_users_map_global: dict = {}
    if all_member_ids_global:
        for mu in db.query(User).filter(User.id.in_(all_member_ids_global)).all():
            member_users_map_global[mu.id] = mu

    # ── Phase 6: Batch resolve nested ved owner IDs ─────────────────────────────
    nested_ved_owner_ids_global: set = set()
    if all_member_ids_global:
        nested_ved_owner_ids_global = {
            r[0] for r in
            db.query(VedTeamMember.ved_owner_id).filter(
                VedTeamMember.ved_owner_id.in_(all_member_ids_global),
                VedTeamMember.is_active == True
            ).distinct().all()
        }

    # ── Phase 7: Batch load all head users + metrics ────────────────────────────
    head_users_map_global:   dict = {}
    head_metrics_map_global: dict = {}
    if all_head_ids_global:
        for hu in db.query(User).filter(User.id.in_(all_head_ids_global)).all():
            head_users_map_global[hu.id] = hu
        for hm in db.query(UserLegMetrics).filter(UserLegMetrics.user_id.in_(all_head_ids_global)).all():
            head_metrics_map_global[hm.user_id] = hm

    # ── Phase 8: Batch resolve all (owner → head) placement sides in ONE query ──
    # Replaces N×M individual recursive CTEs that were crashing the backend.
    # Single CTE fans out from every owner_id, captures the initial branch side,
    # then filters to only the target head_ids — giving (root_id, head_id) → side.
    side_map: dict = {}
    if owner_user_ids and all_head_ids_global:
        side_rows = db.execute(sa_text("""
            WITH RECURSIVE path AS (
                SELECT p.parent_id AS root_id,
                       p.child_id,
                       p.side,
                       1 AS depth
                FROM   placement p
                WHERE  p.parent_id = ANY(:owners)
                UNION ALL
                SELECT path.root_id,
                       p.child_id,
                       path.side,
                       path.depth + 1
                FROM   placement p
                JOIN   path ON p.parent_id = path.child_id
                WHERE  path.depth < 15
            )
            SELECT DISTINCT ON (root_id, child_id)
                   root_id, child_id, side
            FROM   path
            WHERE  child_id = ANY(:heads)
            ORDER  BY root_id, child_id, depth ASC
        """), {"owners": owner_user_ids, "heads": all_head_ids_global}).fetchall()
        side_map = {(r[0], r[1]): r[2] for r in side_rows}

    # Batch owner placement sides (replaces per-owner individual SELECT calls)
    placement_side_map: dict = {}
    if owner_user_ids:
        for r in db.execute(
            sa_text("SELECT child_id, side FROM placement WHERE child_id = ANY(:ids)"),
            {"ids": owner_user_ids}
        ).fetchall():
            placement_side_map[r[0]] = r[1]

    # ── Phase 9: Pure-Python assembly — zero SQL inside this loop ───────────────
    ved_owners = []
    for row in downline_rows:
        owner_id   = row[0]
        group_side = row[1]
        depth      = row[2]

        owner = owner_users_map.get(owner_id)
        if not owner:
            continue

        om               = owner_metrics_map.get(owner_id)
        o_activated      = owner.activation_date is not None and float(owner.package_points or 0) > 0
        o_pkg_pts        = float(owner.package_points or 0)
        o_kyc            = owner.kyc_status
        o_first_match_ok = bool(om.first_match_achieved) if om else False
        o_key_elig       = get_key_eligibility(om)
        o_grp_status     = get_group_status(om)

        owner_income_records     = owner_income_map.get(owner_id, [])
        owner_ved_income_count   = len(owner_income_records)
        owner_ved_income_created = owner_ved_income_count > 0
        owner_ved_income_total   = float(sum(r.net_amount for r in owner_income_records))
        ved_income_history = [
            {
                "id":              r.id,
                "business_date":   r.business_date.strftime("%Y-%m-%d") if r.business_date else None,
                "gross_amount":    float(r.gross_amount or 0),
                "net_amount":      float(r.net_amount or 0),
                "related_user_id": r.related_user_id,
                "status":          r.verification_status,
            }
            for r in owner_income_records[:20]
        ]

        vtm_rows = vtm_by_owner.get(owner_id, [])
        unique_heads: dict = {}
        for vr in vtm_rows:
            unique_heads.setdefault(vr.ved_head_id, []).append(vr)

        heads_data              = []
        total_ved_members_all   = 0
        activated_members_all   = 0
        nested_ved_owners_count = 0

        for vh_id, vh_members in unique_heads.items():
            vh = head_users_map_global.get(vh_id)
            if not vh:
                continue
            vh_m    = head_metrics_map_global.get(vh_id)
            vh_act  = vh.activation_date is not None and float(vh.package_points or 0) > 0
            vh_side = side_map.get((owner_id, vh_id))

            member_list = []
            total_this  = 0
            active_this = 0

            for vr in vh_members:
                mu = member_users_map_global.get(vr.member_id)
                if not mu:
                    continue
                total_this += 1
                m_act = mu.activation_date is not None and float(mu.package_points or 0) > 0
                if m_act:
                    active_this += 1

                pkg_pts_m = float(mu.package_points or 0)
                if m_act:
                    if not vh_act:
                        income_txt = "Missed — Head Not Active"
                    elif not o_activated:
                        income_txt = "Missed — Owner Not Active"
                    elif o_key_elig == "Ineligible":
                        income_txt = "Blocked — No Eligibility"
                    elif not o_first_match_ok:
                        income_txt = "Blocked — First Matching Not Achieved"
                    elif pkg_pts_m >= 1.0:
                        income_txt = "₹1,000"
                    elif pkg_pts_m >= 0.5:
                        income_txt = "₹500"
                    else:
                        income_txt = "₹0 — Blue/Loyal"
                else:
                    income_txt = "Not Activated"

                member_list.append({
                    "member_id":        vr.member_id,
                    "name":             mu.name,
                    "level":            vr.level,
                    "side":             vr.position or "-",
                    "parent_id":        vr.parent_id,
                    "package":          get_package_label(mu.package_points) if m_act else "—",
                    "package_points":   pkg_pts_m,
                    "activated":        m_act,
                    "activated_date":   fmt_date(mu.activation_date),
                    "registered_date":  fmt_date(mu.registration_date),
                    "kyc_status":       mu.kyc_status,
                    "coupon_status":    mu.coupon_status,
                    "is_ved_owner":     vr.member_id in nested_ved_owner_ids_global,
                    "income_triggered": income_txt,
                })

            nested_in_this_head = sum(
                1 for vr in vh_members if vr.member_id in nested_ved_owner_ids_global
            )

            total_ved_members_all   += total_this
            activated_members_all   += active_this
            nested_ved_owners_count += nested_in_this_head

            heads_data.append({
                "ved_head_id":               vh_id,
                "ved_head_name":             vh.name,
                "head_activated":            vh_act,
                "activated_date":            fmt_date(vh.activation_date),
                "registered_date":           fmt_date(vh.registration_date),
                "package":                   get_package_label(vh.package_points),
                "package_points":            float(vh.package_points or 0),
                "kyc_status":                vh.kyc_status,
                "group_side_in_tree":        vh_side,
                "group_side_of_owner_label": "Group A" if vh_side == "left" else ("Group B" if vh_side == "right" else "—"),
                "key_eligibility":           get_key_eligibility(vh_m),
                "group_status":              get_group_status(vh_m),
                "total_members":             total_this,
                "activated_members":         active_this,
                "nested_ved_owners":         nested_in_this_head,
                "members":                   member_list,
            })

        income_loss_reason = compute_income_loss(
            o_activated, o_pkg_pts, o_first_match_ok, o_key_elig, o_grp_status, heads_data
        )
        heads_all_active = all(h["head_activated"] for h in heads_data) if heads_data else False
        is_eligible = (
            o_activated and o_first_match_ok
            and o_key_elig == "Eligible" and heads_all_active
        )

        # DC Protocol Feb 2026: Persist block reason — tag once (first_tagged), refresh on every load
        existing_log = block_log_map.get(owner_id)
        income_block_first_tagged_at = None
        income_block_last_updated_at = None
        if income_loss_reason != "Eligible" and not owner_ved_income_created:
            try:
                db.execute(sa_text("""
                    INSERT INTO ved_income_block_log
                        (ved_owner_id, income_block_reason,
                         income_block_first_tagged_at, income_block_last_updated_at)
                    VALUES
                        (:oid, :reason, NOW(), NOW())
                    ON CONFLICT (ved_owner_id) DO UPDATE SET
                        income_block_reason      = EXCLUDED.income_block_reason,
                        income_block_last_updated_at = NOW()
                """), {"oid": owner_id, "reason": income_loss_reason})
                db.commit()
                # Refresh local values from updated row
                refreshed = db.execute(sa_text("""
                    SELECT income_block_first_tagged_at, income_block_last_updated_at
                    FROM   ved_income_block_log
                    WHERE  ved_owner_id = :oid
                """), {"oid": owner_id}).fetchone()
                if refreshed:
                    income_block_first_tagged_at = refreshed[0].isoformat() if refreshed[0] else None
                    income_block_last_updated_at = refreshed[1].isoformat() if refreshed[1] else None
            except Exception:
                pass  # Non-blocking — page still renders if upsert fails
        elif existing_log:
            income_block_first_tagged_at = existing_log[2].isoformat() if existing_log[2] else None
            income_block_last_updated_at = existing_log[3].isoformat() if existing_log[3] else None

        ved_owners.append({
            "owner_id":               owner_id,
            "owner_name":             owner.name,
            "depth_from_searched":    depth,
            "group_side_label":       "Group A" if group_side == "left" else "Group B",
            "group_side_raw":         group_side,
            "owner_placement_side":   placement_side_map.get(owner_id),
            "eligible":               is_eligible,
            "income_loss_reason":     income_loss_reason,
            "income_block_first_tagged_at": income_block_first_tagged_at,
            "income_block_last_updated_at": income_block_last_updated_at,
            "registered_date":        fmt_date(owner.registration_date),
            "activated_date":         fmt_date(owner.activation_date),
            "package":                get_package_label(owner.package_points),
            "package_points":         o_pkg_pts,
            "kyc_status":             o_kyc,
            "coupon_status":          owner.coupon_status,
            "key_eligibility":        o_key_elig,
            "group_status":           o_grp_status,
            "is_ved_head_themselves": bool(owner.is_ved),
            "ved_owner_of":           owner.ved_owner_id,
            "metrics": {
                "left_points":             float(om.left_points) if om else 0,
                "right_points":            float(om.right_points) if om else 0,
                "left_active_count":       om.left_active_count if om else 0,
                "right_active_count":      om.right_active_count if om else 0,
                "total_direct_referrals":  om.total_direct_referrals if om else 0,
                "active_direct_referrals": om.active_direct_referrals if om else 0,
            },
            "ved_heads":                heads_data,
            "total_ved_members":        total_ved_members_all,
            "activated_ved_members":    activated_members_all,
            "nested_ved_owners":        nested_ved_owners_count,
            "owner_ved_income_created": owner_ved_income_created,
            "owner_ved_income_count":   owner_ved_income_count,
            "owner_ved_income_total":   owner_ved_income_total,
            "ved_income_history":       ved_income_history,
        })

    summary = {
        "total_ved_owners":    len(ved_owners),
        "group_a_count":       sum(1 for v in ved_owners if v["group_side_raw"] == "left"),
        "group_b_count":       sum(1 for v in ved_owners if v["group_side_raw"] == "right"),
        "eligible_count":      sum(1 for v in ved_owners if v["eligible"]),
        "income_loss_count":   sum(1 for v in ved_owners if not v["eligible"] and not v["owner_ved_income_created"]),
        "income_earned_count": sum(1 for v in ved_owners if v["owner_ved_income_created"]),
        "total_ved_members":   sum(v["total_ved_members"] for v in ved_owners),
        "activated_members":   sum(v["activated_ved_members"] for v in ved_owners),
        "nested_ved_owners":   sum(v["nested_ved_owners"] for v in ved_owners),
    }

    return {
        "success":       True,
        "searched_user": searched_user_data,
        "ved_owners":    ved_owners,
        "summary":       summary,
        "truncated":     truncated,
    }
