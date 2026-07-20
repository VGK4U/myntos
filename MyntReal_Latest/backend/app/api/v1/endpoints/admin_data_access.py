"""
Admin Data Access API Endpoints for FastAPI
Allows admins to view any user's team and earnings data
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_user_hybrid, get_current_admin_user_hybrid
from app.models.user import User
from app.models.transaction import Transaction
from app.models.base import get_indian_time
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService

router = APIRouter()

@router.get("/users/{user_id}/team")
async def get_user_team_data(
    user_id: str,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin endpoint to get user's team data including direct referrals and binary tree
    """
    user_service = UserService(db)
    reference_service = ReferenceService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get direct referrals
    direct_referrals = db.query(User).filter(User.referrer_id == user_id).all()
    
    # Get team counts (binary tree)
    team_counts_all = reference_service.get_team_counts(user_id, active_only=False)
    team_counts_active = reference_service.get_team_counts(user_id, active_only=True)
    
    # Format direct referrals data
    direct_referrals_data = []
    for ref in direct_referrals:
        direct_referrals_data.append({
            "user_id": ref.id,
            "name": ref.name,
            "full_name": f"{ref.name} {ref.last_name}" if hasattr(ref, 'last_name') and ref.last_name else ref.name,
            "phone": getattr(ref, 'phone', 'N/A'),
            "email": getattr(ref, 'email', 'N/A'),
            "package": getattr(ref, 'current_package_type', 'Not Activated'),
            "package_type": getattr(ref, 'current_package_type', 'Not Activated'),
            "activation_date": ref.activation_date.isoformat() if hasattr(ref, 'activation_date') and ref.activation_date else None,
            "is_active": bool(ref.activation_date),
            "status": "Active" if ref.activation_date else "Inactive"
        })
    
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "user_name": target_user.name,
            "direct_referrals": direct_referrals_data,
            "direct_referrals_count": len(direct_referrals),
            "binary_tree": {
                "all": team_counts_all,
                "active": team_counts_active
            },
            "team_counts": {
                "total_direct": len(direct_referrals),
                "total_team": team_counts_all.get("total_count", 0),
                "active_team": team_counts_active.get("total_count", 0)
            }
        }
    }

@router.get("/users/{user_id}/team/downline")
async def get_user_downline(
    user_id: str,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin endpoint to get user's complete downline for Ved team or other analysis
    """
    user_service = UserService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get all downline members - COMBINED referral + placement trees with deduplication
    collected_ids = set()
    all_downline = []
    
    # 1. Get referral tree (sponsor-based) recursively
    def traverse_referral_tree(parent_id: str):
        children = db.query(User).filter(User.referrer_id == parent_id).all()
        for child in children:
            if child.id not in collected_ids:
                collected_ids.add(child.id)
                all_downline.append(child)
                traverse_referral_tree(child.id)  # Recurse
    
    # 2. Get placement tree (binary tree) recursively
    def traverse_placement_tree(parent_id: str):
        placements = db.query(User).filter(User.position_id == parent_id).all()
        for placement in placements:
            if placement.id not in collected_ids:
                collected_ids.add(placement.id)
                all_downline.append(placement)
                traverse_placement_tree(placement.id)  # Recurse
    
    # Execute both traversals
    traverse_referral_tree(user_id)
    traverse_placement_tree(user_id)
    
    downline_members = all_downline
    
    # Format downline data
    downline_data = []
    for member in downline_members:
        downline_data.append({
            "user_id": member.id,
            "id": member.id,
            "name": member.name,
            "full_name": f"{member.name} {member.last_name}" if hasattr(member, 'last_name') and member.last_name else member.name,
            "package": getattr(member, 'current_package_type', 'Not Activated'),
            "package_type": getattr(member, 'current_package_type', 'Not Activated'),
            "is_active": bool(member.activation_date),
            "activation_date": member.activation_date.isoformat() if hasattr(member, 'activation_date') and member.activation_date else None,
            "is_ved_member": getattr(member, 'current_package_type', '') == 'Platinum',
            "ved_status": "Active" if getattr(member, 'current_package_type', '') == 'Platinum' else "Inactive"
        })
    
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "all_members": downline_data,
            "downline": downline_data,
            "total_count": len(downline_data)
        }
    }

@router.get("/users/{user_id}/earnings-overview")
async def get_user_earnings_overview(
    user_id: str,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin endpoint to get user's earnings overview
    DC Protocol: Uses WalletService.get_earnings_summary() for consistent data
    """
    from app.services.wallet_service import WalletService
    user_service = UserService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # DC Protocol: Use SINGLE SOURCE OF TRUTH - WalletService.get_earnings_summary()
    # This uses calculated Ved Income (not database records)
    wallet_service = WalletService(db)
    earnings_summary = wallet_service.get_earnings_summary(user_id)
    
    # Calculate total earnings from summary
    total_earnings = earnings_summary.get('total_gross_earnings', 0)
    
    # Format earnings by type (matches Transaction table format for backward compatibility)
    earnings_by_type = {
        "Direct Referral": {
            "amount": earnings_summary.get('direct_referral_total', 0),
            "count": earnings_summary.get('direct_referral_count', 0)
        },
        "Matching Referral": {
            "amount": earnings_summary.get('matching_referral_total', 0),
            "count": earnings_summary.get('matching_referral_count', 0)
        },
        "Ved Income": {
            "amount": earnings_summary.get('ved_income_total', 0),
            "count": earnings_summary.get('ved_income_count', 0)
        },
        "Guru Dakshina": {
            "amount": earnings_summary.get('guru_dakshina_total', 0),
            "count": earnings_summary.get('guru_dakshina_count', 0)
        }
    }
    
    # Get wallet balances
    earning_wallet = float(getattr(target_user, 'earning_wallet', 0))
    withdrawable_wallet = float(getattr(target_user, 'withdrawable_wallet', 0))
    
    # Get recent income/transaction records
    recent_income = db.query(Transaction).filter(
        Transaction.referrer_id == user_id
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    
    recent_income_data = []
    for income in recent_income:
        recent_income_data.append({
            "id": income.id,
            "type": income.transaction_type,
            "income_type": income.transaction_type,
            "amount": float(income.amount),
            "status": "approved",  # Transactions are auto-approved
            "date": income.timestamp.isoformat() if income.timestamp else None,
            "description": f"{income.transaction_type} from {income.referred_user_id}"
        })
    
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "user_name": target_user.name,
            "total_earnings": total_earnings,
            "earnings_by_type": earnings_by_type,
            "wallets": {
                "earning_wallet": earning_wallet,
                "withdrawable_wallet": withdrawable_wallet,
                "total": earning_wallet + withdrawable_wallet
            },
            "recent_income": recent_income_data,
            "summary": {
                "direct_referral": earnings_summary.get('direct_referral_total', 0),
                "matching_referral": earnings_summary.get('matching_referral_total', 0),
                "ved_income": earnings_summary.get('ved_income_total', 0),  # CALCULATED Ved Income
                "guru_dakshina": earnings_summary.get('guru_dakshina_total', 0),
                "field_allowance": 0,  # Not in earnings_summary
                "bonanza": 0  # Not in earnings_summary
            }
        }
    }

@router.get("/users/{user_id}/income/{income_type}")
async def get_user_income_by_type(
    user_id: str,
    income_type: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin endpoint to get user's income by specific type with pagination
    Uses PendingIncome table to match what users see
    """
    from app.models.transaction import PendingIncome
    user_service = UserService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Map income type variations to match PendingIncome.income_type
    income_type_map = {
        "Direct Referral": "Direct Referral",
        "Matching Referral": "Matching Referral",
        "Ved Income": "Ved Income",
        "Guru Dakshina": "Guru Dakshina",
        "Field Allowance": "Field Allowance"
    }
    
    db_income_type = income_type_map.get(income_type, income_type)
    
    # Get total count from PendingIncome
    total_count = db.query(func.count(PendingIncome.id)).filter(
        PendingIncome.user_id == str(target_user.id),
        PendingIncome.income_type == db_income_type
    ).scalar() or 0
    
    # Get paginated income records from PendingIncome (same as user sees)
    offset = (page - 1) * per_page
    income_records = db.query(PendingIncome).filter(
        PendingIncome.user_id == str(target_user.id),
        PendingIncome.income_type == db_income_type
    ).order_by(PendingIncome.calculation_timestamp.desc()).offset(offset).limit(per_page).all()
    
    # Calculate total amount
    total_amount = db.query(func.sum(PendingIncome.gross_amount)).filter(
        PendingIncome.user_id == str(target_user.id),
        PendingIncome.income_type == db_income_type
    ).scalar() or 0
    
    # Format income data to match user earnings format
    earnings_list = []
    for inc in income_records:
        # Format description based on income type
        if db_income_type == 'Direct Referral':
            description = f"Direct Referral - {getattr(inc, 'verification_status', 'Pending')}"
        elif db_income_type == 'Matching Referral':
            description = f"{getattr(inc, 'pairs_matched', 0)} pairs matched - {getattr(inc, 'verification_status', 'Pending')}"
        elif db_income_type == 'Ved Income':
            description = f"Ved Income - {getattr(inc, 'verification_status', 'Pending')}"
        elif db_income_type == 'Guru Dakshina':
            description = f"Guru Dakshina - {getattr(inc, 'verification_status', 'Pending')}"
        else:
            description = f"{db_income_type} - {getattr(inc, 'verification_status', 'Pending')}"
            
        earnings_list.append({
            "amount": float(getattr(inc, 'gross_amount', 0) or 0),
            "created_at": getattr(inc, 'calculation_timestamp', datetime.now()).isoformat(),
            "description": description,
            "status": getattr(inc, 'verification_status', 'Pending')
        })
    
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "income_type": income_type,
            "earnings": earnings_list,
            "total": float(total_amount or 0),
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page
        }
    }

@router.get("/users/{user_id}/direct-referral-income")
async def get_user_direct_referral_income(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Admin endpoint for direct referral income"""
    return await get_user_income_by_type(user_id, "Direct Referral", page, per_page, current_user, db)

@router.get("/users/{user_id}/matching-referral-income")
async def get_user_matching_referral_income(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Admin endpoint for matching referral income"""
    return await get_user_income_by_type(user_id, "Matching Referral", page, per_page, current_user, db)

@router.get("/users/{user_id}/ved-income")
async def get_user_ved_income(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin endpoint for Ved income
    DC Protocol: Uses CALCULATED Ved Income (not database records)
    """
    from app.services.reference_service import ReferenceService
    from app.services.user_service import UserService
    
    user_service = UserService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # DC Protocol: Use CALCULATED Ved Income (all activated Ved Team members)
    reference_service = ReferenceService(db)
    ved_income_data = reference_service.calculate_ved_income(user_id, "1970-01")  # Lifetime data
    
    # Get activations list
    activations = ved_income_data.get('activations_under_ved', []) if ved_income_data else []
    total_count = len(activations)
    total_amount = float(ved_income_data.get('ved_amount', 0)) if ved_income_data else 0
    
    # Apply pagination
    offset = (page - 1) * per_page
    paginated_activations = activations[offset:offset + per_page]
    
    # Format earnings list
    earnings_list = []
    for activation in paginated_activations:
        earnings_list.append({
            "amount": float(activation.get('ved_income', 0)),
            "created_at": activation.get('activation_date', ''),
            "description": f"Ved Income from {activation.get('user_name', '')} ({activation.get('user_id', '')})",
            "status": "Calculated"  # Not stored in database, calculated on-the-fly
        })
    
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "income_type": "Ved Income",
            "earnings": earnings_list,
            "total": total_amount,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page if total_count > 0 else 0
        }
    }

@router.get("/users/{user_id}/guru-dakshina")
async def get_user_guru_dakshina(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Admin endpoint for Guru Dakshina income"""
    return await get_user_income_by_type(user_id, "Guru Dakshina", page, per_page, current_user, db)

@router.get("/users/withdrawal-requests")
async def get_user_withdrawal_requests(
    user_id: str = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Admin endpoint for withdrawal requests"""
    from app.models.withdrawal import Withdrawal
    
    query = db.query(Withdrawal)
    if user_id:
        query = query.filter(Withdrawal.user_id == user_id)
    
    total_count = query.count()
    offset = (page - 1) * per_page
    records = query.order_by(Withdrawal.created_at.desc()).offset(offset).limit(per_page).all()
    
    data = []
    for record in records:
        data.append({
            "id": record.id,
            "user_id": record.user_id,
            "amount": float(record.amount),
            "status": record.status,
            "request_date": record.created_at.isoformat() if record.created_at else None,
            "approval_date": record.approval_date.isoformat() if hasattr(record, 'approval_date') and record.approval_date else None
        })
    
    return {
        "status": "success",
        "data": {
            "records": data,
            "total_count": total_count,
            "page": page,
            "per_page": per_page
        }
    }
