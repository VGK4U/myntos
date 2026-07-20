"""
Admin Endpoints - Complete Implementation
Handles all administrative operations for the MNR Reference system
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
import os

from app.core.database import get_db
from app.core.rbac import require_admin, require_super_admin, require_finance_admin, require_admin_hybrid, require_super_admin_hybrid
from app.core.security import require_staff_with_page_access
from app.models.user import User
from app.models.transaction import Transaction
from app.models.coupon import Coupon, PINPurchaseRequest
from app.models.withdrawal import WithdrawalRequest
from app.models.ticket import ServiceTicket
from app.models.kyc_document import KYCDocument
from app.models.api_response import success_response, error_response
from app.core.audit import AuditLogger
from app.models.base import get_indian_time

router = APIRouter()

# ===== ADMIN DASHBOARDS =====

@router.get("/admin/accounts-dashboard")
async def accounts_admin_dashboard(
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Admin accounts dashboard - Main admin overview"""
    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(
            User.account_status == 'Active'
        ).scalar() or 0
        
        pending_withdrawals = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.transaction_type == 'Withdrawal Request',
                Transaction.status == 'Pending'
            )
        ).scalar() or 0
        
        pending_pin_requests = db.query(func.count(PINPurchaseRequest.id)).filter(
            PINPurchaseRequest.status == 'Pending'
        ).scalar() or 0
        
        pending_tickets = 0
        
        total_wallet_balance = db.query(func.sum(User.wallet_balance)).scalar() or 0
        
        pending_withdrawal_amount = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Withdrawal Request',
                Transaction.status == 'Pending'
            )
        ).scalar() or 0
        
        dashboard_data = {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users
            },
            "pending_items": {
                "withdrawals": pending_withdrawals,
                "pin_requests": pending_pin_requests,
                "tickets": pending_tickets,
                "total": pending_withdrawals + pending_pin_requests + pending_tickets
            },
            "financial": {
                "total_wallet_balance": float(total_wallet_balance),
                "pending_withdrawals": float(pending_withdrawal_amount)
            }
        }
        
        return success_response(
            message="Admin dashboard data retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/revenue-dashboard")
async def admin_revenue_dashboard(
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Revenue and earnings dashboard"""
    try:
        today = get_indian_time().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved', 
                    'Guru Dakshina', 'Field Allowance'
                ]),
                Transaction.timestamp >= today_start,
                Transaction.timestamp <= today_end
            )
        ).scalar() or 0
        
        month_start = today.replace(day=1)
        month_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved', 
                    'Guru Dakshina', 'Field Allowance'
                ]),
                Transaction.timestamp >= month_start
            )
        ).scalar() or 0
        
        earnings_by_type = {}
        for earning_type in ['Direct Referral', 'Matching Referral', 'Ved', 'Guru Dakshina', 'Field Allowance']:
            amount = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.transaction_type == earning_type,
                    Transaction.timestamp >= month_start
                )
            ).scalar() or 0
            earnings_by_type[earning_type] = float(amount)
        
        revenue_data = {
            "today": {
                "total_earnings": float(today_earnings)
            },
            "this_month": {
                "total_earnings": float(month_earnings),
                "breakdown": earnings_by_type
            }
        }
        
        return success_response(
            message="Revenue dashboard data retrieved successfully",
            data=revenue_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== WITHDRAWAL APPROVALS =====

@router.get("/admin/withdrawal-requests")
async def get_all_withdrawal_requests(
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get all withdrawal requests for admin review"""
    try:
        query = db.query(Transaction).filter(
            Transaction.transaction_type == 'Withdrawal Request'
        )
        
        if status_filter:
            query = query.filter(Transaction.status == status_filter)
        
        total = query.count()
        
        requests = query.order_by(
            Transaction.timestamp.desc()
        ).offset((page - 1) * limit).limit(limit).all()
        
        request_list = []
        for req in requests:
            user = db.query(User).filter(User.id == req.user_id).first()
            request_list.append({
                "id": str(req.id),
                "user_id": str(req.user_id),
                "user_name": user.name if user else "Unknown",
                "amount": float(abs(req.amount)),
                "status": getattr(req, 'status', 'Pending'),
                "request_date": req.timestamp.isoformat(),
                "bank_details": {
                    "account_number": getattr(user, 'bank_account_number', ''),
                    "ifsc_code": getattr(user, 'bank_ifsc_code', ''),
                    "bank_name": getattr(user, 'bank_name', '')
                } if user else {}
            })
        
        return success_response(
            message="Withdrawal requests retrieved successfully",
            data={
                "requests": request_list,
                "total": total,
                "page": page,
                "limit": limit
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

class WithdrawalApprovalRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None
    admin_notes: Optional[str] = None

@router.post("/admin/withdrawal-requests/{request_id}/approve")
async def approve_withdrawal_request(
    request_id: str,
    approval_data: WithdrawalApprovalRequest,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Phase 1.7: DEPRECATED ENDPOINT
    
    This endpoint is deprecated and should not be used.
    Please use the new withdrawal endpoints in withdrawal.py:
    - POST /api/v1/withdrawal/requests/{id}/update (for approval/rejection)
    
    This endpoint is kept for backward compatibility only and may be removed in future versions.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ DEPRECATED: /admin/withdrawal-requests/{request_id}/approve called by {current_user.id}. Please migrate to /api/v1/withdrawal/requests/{{id}}/update")
    
    try:
        from app.services.wallet_service import WalletService
        
        wallet_service = WalletService(db)
        
        if approval_data.approved:
            result = wallet_service.process_withdrawal(
                transaction_id=request_id,
                admin_id=str(current_user.id),
                approved=True
            )
        else:
            result = wallet_service.process_withdrawal(
                transaction_id=request_id,
                admin_id=str(current_user.id),
                approved=False,
                rejection_reason=approval_data.rejection_reason
            )
        
        if result.get('success'):
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action='WITHDRAWAL_APPROVAL' if approval_data.approved else 'WITHDRAWAL_REJECTION',
                resource_type='Transaction',
                resource_id=request_id,
                details={
                    "status": "approved" if approval_data.approved else "rejected",
                    "reason": approval_data.rejection_reason
                }
            )
            
            return success_response(
                message=result.get('message'),
                data=result.get('data', {})
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== PIN PURCHASE REQUEST APPROVALS =====

@router.get("/admin/pin-requests")
async def get_pin_purchase_requests(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get all PIN purchase requests"""
    try:
        query = db.query(PINPurchaseRequest)
        
        if status_filter:
            query = query.filter(PINPurchaseRequest.status == status_filter)
        
        requests = query.order_by(
            PINPurchaseRequest.request_date.desc()
        ).limit(100).all()
        
        request_list = []
        for req in requests:
            user = db.query(User).filter(User.id == req.user_id).first()
            request_list.append({
                "id": str(req.id),
                "user_id": str(req.user_id),
                "user_name": user.name if user else "Unknown",
                "package_type": req.requested_package_type,
                "quantity": req.quantity_requested,
                "total_amount": float(req.total_amount),
                "payment_method": req.payment_method,
                "status": req.status,
                "request_date": req.request_date.isoformat()
            })
        
        return success_response(
            message="PIN purchase requests retrieved successfully",
            data={"requests": request_list}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

class PinApprovalRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None

@router.post("/admin/pin-requests/{request_id}/approve")
async def approve_pin_request(
    request_id: int,
    approval_data: PinApprovalRequest,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Approve or reject PIN purchase request"""
    try:
        pin_request = db.query(PINPurchaseRequest).filter(
            PINPurchaseRequest.id == request_id
        ).first()
        
        if not pin_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PIN request not found"
            )
        
        if approval_data.approved:
            pin_request.status = 'Approved'
            pin_request.approved_date = get_indian_time()
            pin_request.approved_by_id = str(current_user.id)
            
        else:
            pin_request.status = 'Rejected'
            pin_request.rejection_reason = approval_data.rejection_reason
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='PIN_REQUEST_APPROVAL' if approval_data.approved else 'PIN_REQUEST_REJECTION',
            resource_type='PINPurchaseRequest',
            resource_id=str(request_id),
            details={
                "user_id": pin_request.user_id,
                "package_type": pin_request.requested_package_type,
                "quantity": pin_request.quantity_requested
            }
        )
        
        return success_response(
            message=f"PIN request {'approved' if approval_data.approved else 'rejected'} successfully",
            data={"request_id": str(pin_request.id), "status": pin_request.status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== USER MANAGEMENT =====

@router.get("/admin/users/autocomplete")
async def user_autocomplete_search(
    query: str = Query(..., min_length=1, description="Search query for MNR ID or name"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Autocomplete search for users by MNR ID or name - for admin filters"""
    try:
        search_query = db.query(User).filter(
            or_(
                User.id.ilike(f'%{query}%'),
                func.concat(User.first_name, ' ', User.last_name).ilike(f'%{query}%'),
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%')
            )
        ).order_by(User.id).limit(limit)
        
        users = search_query.all()
        
        user_list = [
            {
                "id": user.id,
                "mnr_id": user.id,
                "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                "display": f"{user.id} - {user.first_name or ''} {user.last_name or ''}".strip(),
                "package": user.package or "Not Activated"
            }
            for user in users
        ]
        
        return success_response(
            message="User autocomplete results",
            data={"users": user_list, "total": len(user_list)}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/users")
async def get_all_users(
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    user_type: Optional[str] = None,
    package_filter: Optional[str] = None,
    referrer_filter: Optional[str] = Query(None, description="Filter by referrer ID"),
    ved_owner_filter: Optional[str] = Query(None, description="Filter users who are Ved owners"),
    ved_head_filter: Optional[str] = Query(None, description="Filter users who are Ved heads"),
    date_from: Optional[str] = Query(None, description="Registration date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Registration date to (YYYY-MM-DD)"),
    activation_date_from: Optional[str] = Query(None, description="Activation date from (YYYY-MM-DD)"),
    activation_date_to: Optional[str] = Query(None, description="Activation date to (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query(None, description="Sort field: registration_date, activation_date, name, wallet_balance, total_referrals, total_earning, points_balance"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 29, 2025): Enhanced user list with additional fields and stats
    Get all users with filtering, sorting, and pagination
    New fields: registration_date, activation_date, package, referrer info, totals
    Filters: status, user_type, package, referrer, ved_owner, ved_head, date ranges
    Stats: Added/Activated last 3 days, Platinum/Diamond counts, Points totals
    """
    try:
        from app.models.myntreal_incentive import MNRPointsBalance
        from app.models.withdrawal import WithdrawalRequest
        from app.models.ved_team import VedTeamMember
        from sqlalchemy import case, literal_column
        from sqlalchemy.orm import aliased
        
        query = db.query(User)
        
        # Search filter
        if search:
            query = query.filter(
                or_(
                    User.id.ilike(f'%{search}%'),
                    User.name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.phone_number.ilike(f'%{search}%')
                )
            )
        
        # Status filter - based on activation_date presence (Activated/Not Activated)
        if status_filter:
            if status_filter.lower() == 'active':
                query = query.filter(User.activation_date.isnot(None))
            elif status_filter.lower() == 'inactive':
                query = query.filter(User.activation_date.is_(None))
            elif status_filter.lower() == 'suspended':
                query = query.filter(User.account_status == 'Suspended')
        
        # User type filter
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        # Package filter - map package name to package_points value
        if package_filter:
            package_points_map = {
                'Platinum': 1.0,
                'Diamond': 0.5,
                'Star/Loyal': 0.25,
                'Eligible': 0.0
            }
            if package_filter in package_points_map:
                points_value = package_points_map[package_filter]
                if package_filter == 'Platinum':
                    query = query.filter(User.package_points >= 1.0)
                elif package_filter == 'Diamond':
                    query = query.filter(and_(User.package_points >= 0.5, User.package_points < 1.0))
                elif package_filter == 'Star/Loyal':
                    query = query.filter(and_(User.package_points > 0, User.package_points < 0.5))
                else:  # Eligible
                    query = query.filter(or_(User.package_points == 0, User.package_points.is_(None)))
        
        # Referrer filter - get all users referred by a specific referrer
        if referrer_filter:
            query = query.filter(User.referrer_id == referrer_filter)
        
        # Ved Owner filter - get all users who are Ved owners
        if ved_owner_filter and ved_owner_filter.lower() == 'yes':
            ved_owner_ids = db.query(VedTeamMember.ved_owner_id).filter(
                VedTeamMember.is_active == True
            ).distinct().subquery()
            query = query.filter(User.id.in_(ved_owner_ids))
        
        # Ved Head filter - get all users who are Ved heads
        if ved_head_filter and ved_head_filter.lower() == 'yes':
            ved_head_ids = db.query(VedTeamMember.ved_head_id).filter(
                VedTeamMember.is_active == True
            ).distinct().subquery()
            query = query.filter(User.id.in_(ved_head_ids))
        
        # DC Protocol (Dec 29, 2025): Date range filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(User.registration_date >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(User.registration_date <= to_date)
            except ValueError:
                pass
        
        if activation_date_from:
            try:
                act_from = datetime.strptime(activation_date_from, '%Y-%m-%d')
                query = query.filter(User.activation_date >= act_from)
            except ValueError:
                pass
        
        if activation_date_to:
            try:
                act_to = datetime.strptime(activation_date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(User.activation_date <= act_to)
            except ValueError:
                pass
        
        total = query.count()
        
        # Sorting - handle both simple columns and computed columns
        simple_sort_mapping = {
            'registration_date': User.registration_date,
            'activation_date': User.activation_date,
            'name': User.name,
            'wallet_balance': User.wallet_balance,
            'created_at': User.registration_date,
            'id': User.id,
            'status': User.activation_date,
            'user_type': User.user_type,
            'package': User.package_points
        }
        
        # For computed columns, we need to use subqueries
        if sort_by in ['total_earning', 'total_referrals', 'active_referrals', 'pending_withdrawals', 'points_balance']:
            if sort_by == 'total_earning':
                # Subquery for total earnings
                earning_subq = db.query(
                    Transaction.referred_user_id.label('user_id'),
                    func.coalesce(func.sum(Transaction.amount), 0).label('total')
                ).filter(
                    Transaction.transaction_type.in_([
                        'Direct Referral', 'Matching Referral', 'Ved', 
                        'Guru Dakshina', 'Field Allowance'
                    ])
                ).group_by(Transaction.referred_user_id).subquery()
                
                query = query.outerjoin(earning_subq, User.id == earning_subq.c.user_id)
                sort_column = func.coalesce(earning_subq.c.total, 0)
                
            elif sort_by == 'total_referrals':
                # Subquery for referral counts
                referral_subq = db.query(
                    User.referrer_id.label('referrer_id'),
                    func.count(User.id).label('count')
                ).filter(User.referrer_id.isnot(None)).group_by(User.referrer_id).subquery()
                
                # Create alias for the main User table to avoid ambiguity
                query = query.outerjoin(referral_subq, User.id == referral_subq.c.referrer_id)
                sort_column = func.coalesce(referral_subq.c.count, 0)
                
            elif sort_by == 'active_referrals':
                # DC Protocol Feb 2026: Subquery for activated referral counts (applied coupons)
                from sqlalchemy.orm import aliased
                RefUser = aliased(User)
                active_ref_subq = db.query(
                    RefUser.referrer_id.label('referrer_id'),
                    func.count(RefUser.id).label('count')
                ).filter(
                    RefUser.referrer_id.isnot(None),
                    RefUser.activation_date.isnot(None)
                ).group_by(RefUser.referrer_id).subquery()
                
                query = query.outerjoin(active_ref_subq, User.id == active_ref_subq.c.referrer_id)
                sort_column = func.coalesce(active_ref_subq.c.count, 0)
                
            elif sort_by == 'pending_withdrawals':
                # Subquery for pending withdrawals
                pending_subq = db.query(
                    WithdrawalRequest.user_id.label('user_id'),
                    func.coalesce(func.sum(WithdrawalRequest.withdrawal_amount), 0).label('total')
                ).filter(WithdrawalRequest.status == 'Pending').group_by(WithdrawalRequest.user_id).subquery()
                
                query = query.outerjoin(pending_subq, User.id == pending_subq.c.user_id)
                sort_column = func.coalesce(pending_subq.c.total, 0)
                
            elif sort_by == 'points_balance':
                # Subquery for MNR points balance
                points_subq = db.query(
                    MNRPointsBalance.user_id.label('user_id'),
                    func.coalesce(MNRPointsBalance.current_balance, 0).label('balance')
                ).subquery()
                
                query = query.outerjoin(points_subq, User.id == points_subq.c.user_id)
                sort_column = func.coalesce(points_subq.c.balance, 0)
        else:
            # Simple column sorting
            sort_column = simple_sort_mapping.get(sort_by, User.registration_date)
        
        if sort_order and sort_order.lower() == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        users = query.offset((page - 1) * limit).limit(limit).all()
        
        # Get user IDs for batch queries
        user_ids = [user.id for user in users]
        
        # Batch query: Get referrer names
        referrer_ids = [user.referrer_id for user in users if user.referrer_id]
        referrer_map = {}
        if referrer_ids:
            referrers = db.query(User.id, User.name).filter(User.id.in_(referrer_ids)).all()
            referrer_map = {r.id: r.name for r in referrers}
        
        # Batch query: Get ved owner from ved_team_member table (single source of truth)
        ved_team_records = db.query(VedTeamMember.member_id, VedTeamMember.ved_owner_id).filter(
            VedTeamMember.member_id.in_(user_ids),
            VedTeamMember.is_active == True
        ).all()
        ved_owner_by_member = {v.member_id: v.ved_owner_id for v in ved_team_records}
        ved_owner_ids_unique = list(set(ved_owner_by_member.values()))
        ved_owner_map = {}
        if ved_owner_ids_unique:
            ved_owners = db.query(User.id, User.name).filter(User.id.in_(ved_owner_ids_unique)).all()
            ved_owner_map = {v.id: v.name for v in ved_owners}
        
        # Batch query: Get referral counts (total)
        referral_counts = db.query(
            User.referrer_id, func.count(User.id).label('count')
        ).filter(
            User.referrer_id.in_(user_ids)
        ).group_by(User.referrer_id).all()
        referral_count_map = {r.referrer_id: r.count for r in referral_counts}
        
        # Batch query: Get activated referral counts - only users who applied coupons (DC Protocol Feb 2026)
        active_referral_counts = db.query(
            User.referrer_id, func.count(User.id).label('count')
        ).filter(
            User.referrer_id.in_(user_ids),
            User.activation_date.isnot(None)
        ).group_by(User.referrer_id).all()
        active_referral_count_map = {r.referrer_id: r.count for r in active_referral_counts}
        
        # Batch query: Get total earnings
        earnings_query = db.query(
            Transaction.referred_user_id, 
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.referred_user_id.in_(user_ids),
            Transaction.transaction_type.in_([
                'Direct Referral', 'Matching Referral', 'Ved', 
                'Guru Dakshina', 'Field Allowance'
            ])
        ).group_by(Transaction.referred_user_id).all()
        earnings_map = {e.referred_user_id: float(e.total or 0) for e in earnings_query}
        
        # Batch query: Get pending withdrawals
        pending_withdrawals = db.query(
            WithdrawalRequest.user_id,
            func.sum(WithdrawalRequest.withdrawal_amount).label('total')
        ).filter(
            WithdrawalRequest.user_id.in_(user_ids),
            WithdrawalRequest.status == 'Pending'
        ).group_by(WithdrawalRequest.user_id).all()
        pending_map = {w.user_id: float(w.total or 0) for w in pending_withdrawals}
        
        # Batch query: Get MNR points balance
        points_query = db.query(
            MNRPointsBalance.user_id,
            MNRPointsBalance.current_balance
        ).filter(MNRPointsBalance.user_id.in_(user_ids)).all()
        points_map = {p.user_id: float(p.current_balance or 0) for p in points_query}
        
        # Batch query: Get placement sides for Group column
        from app.models.placement import Placement
        placement_query = db.query(
            Placement.child_id, Placement.side
        ).filter(Placement.child_id.in_(user_ids)).all()
        placement_map = {p.child_id: p.side for p in placement_query}
        
        # Build user list with enhanced data
        user_list = []
        for user in users:
            user_list.append({
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "status": user.account_status or ("Active" if user.activation_date else "Inactive"),
                "user_type": user.user_type,
                "wallet_balance": float(user.wallet_balance or 0),
                "coupon_status": user.coupon_status,
                "created_at": user.registration_date.isoformat() if user.registration_date else None,
                "registration_date": user.registration_date.strftime('%Y-%m-%d') if user.registration_date else None,
                "activation_date": user.activation_date.strftime('%Y-%m-%d') if user.activation_date else None,
                "package": user.get_package_type() if hasattr(user, 'get_package_type') else 'N/A',
                "side": placement_map.get(user.id),
                "referrer_id": user.referrer_id,
                "referrer_name": referrer_map.get(user.referrer_id) if user.referrer_id else None,
                "ved_owner_id": ved_owner_by_member.get(user.id, ''),
                "ved_owner_name": ved_owner_map.get(ved_owner_by_member.get(user.id, ''), '') or None,
                "total_referrals": referral_count_map.get(user.id, 0),
                "active_referrals": active_referral_count_map.get(user.id, 0),
                "total_earning": earnings_map.get(user.id, 0),
                "pending_withdrawals": pending_map.get(user.id, 0),
                "points_balance": points_map.get(user.id, 0)
            })
        
        # Get available packages for filter dropdown (static list based on package_points mapping)
        available_packages = ['Platinum', 'Diamond', 'Star/Loyal', 'Eligible']
        
        # Calculate statistics for total active/inactive counts (not just current page)
        active_count = db.query(func.count(User.id)).filter(
            or_(
                User.account_status == 'Active',
                and_(User.account_status.is_(None), User.activation_date.isnot(None))
            )
        ).scalar() or 0
        
        inactive_count = db.query(func.count(User.id)).filter(
            or_(
                User.account_status == 'Inactive',
                and_(User.account_status.is_(None), User.activation_date.is_(None))
            )
        ).scalar() or 0
        
        # This month registrations
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_count = db.query(func.count(User.id)).filter(
            User.registration_date >= current_month_start
        ).scalar() or 0
        
        # DC Protocol (Dec 29, 2025): New statistics
        three_days_ago = datetime.now() - timedelta(days=3)
        
        # Added in last 3 days (registered)
        added_last_3_days = db.query(func.count(User.id)).filter(
            User.registration_date >= three_days_ago
        ).scalar() or 0
        
        # Activated in last 3 days
        activated_last_3_days = db.query(func.count(User.id)).filter(
            User.activation_date >= three_days_ago
        ).scalar() or 0
        
        # Platinum package count (package_points >= 1.0)
        platinum_count = db.query(func.count(User.id)).filter(
            User.package_points >= 1.0
        ).scalar() or 0
        
        # Diamond package count (0.5 <= package_points < 1.0)
        diamond_count = db.query(func.count(User.id)).filter(
            and_(User.package_points >= 0.5, User.package_points < 1.0)
        ).scalar() or 0
        
        # MNR Points statistics (DC Protocol: use correct column names)
        # initial_points = allocated, total_consumed = utilized, current_balance = remaining
        total_points = db.query(func.coalesce(func.sum(MNRPointsBalance.current_balance), 0)).scalar() or 0
        total_allocated = db.query(func.coalesce(func.sum(MNRPointsBalance.initial_points), 0)).scalar() or 0
        total_utilized = db.query(func.coalesce(func.sum(MNRPointsBalance.total_consumed), 0)).scalar() or 0
        unutilized_points = float(total_allocated) - float(total_utilized)
        
        return success_response(
            message="Users retrieved successfully",
            data={
                "users": user_list,
                "total": total,
                "page": page,
                "limit": limit,
                "available_packages": available_packages,
                "stats": {
                    "active_count": active_count,
                    "inactive_count": inactive_count,
                    "this_month_count": this_month_count,
                    "added_last_3_days": added_last_3_days,
                    "activated_last_3_days": activated_last_3_days,
                    "platinum_count": platinum_count,
                    "diamond_count": diamond_count,
                    "total_points": float(total_points),
                    "total_allocated": float(total_allocated),
                    "total_utilized": float(total_utilized),
                    "unutilized_points": unutilized_points
                }
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        total_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.referred_user_id == user_id,
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved', 
                    'Guru Dakshina', 'Field Allowance'
                ])
            )
        ).scalar() or 0
        
        total_withdrawals = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.referred_user_id == user_id,
                Transaction.transaction_type == 'Payout',
                Transaction.amount < 0
            )
        ).scalar() or 0
        
        referrals_count = db.query(func.count(User.id)).filter(
            User.referrer_id == user_id
        ).scalar() or 0
        
        # DC Protocol (Dec 28, 2025): Get referrer name for display
        referrer_name = None
        if user.referrer_id:
            referrer = db.query(User).filter(User.id == user.referrer_id).first()
            referrer_name = referrer.name if referrer else None
        
        user_data = {
            "id": str(user.id),
            "personal_info": {
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
                "gender": user.gender
            },
            "account_info": {
                "status": user.account_status,
                "user_type": user.user_type,
                "coupon_status": user.coupon_status,
                "kyc_status": user.kyc_status,
                "package": getattr(user, 'package', None),
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "activation_date": user.activation_date.isoformat() if user.activation_date else None,
                "created_at": user.registration_date.isoformat() if user.registration_date else None
            },
            "financial": {
                "wallet_balance": float(user.wallet_balance or 0),
                "total_earnings": float(total_earnings),
                "total_withdrawals": float(total_withdrawals)
            },
            "network": {
                "referrer_id": user.referrer_id,
                "referrer_name": referrer_name,
                "referrals_count": referrals_count
            },
            "banking": {
                "bank_name": user.bank_name,
                "account_number": user.bank_account_number,
                "ifsc_code": user.bank_ifsc_code,
                "pan_number": user.pan_number
            }
        }
        
        return success_response(
            message="User details retrieved successfully",
            data=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.get("/admin/users/{user_id}/summary")
async def get_user_comprehensive_summary(
    user_id: str,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 28, 2025): Comprehensive user summary endpoint
    Returns all user data including referrals, incomes, VGK4U, MyntReal, MNR Points
    """
    try:
        from app.models.myntreal_incentive import MNRPointsBalance, ZynovaMember, ZynovaIncentive
        from app.models.withdrawal import WithdrawalRequest
        from app.models.ved_team import VedTeamMember
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get referrer info
        referrer_name = None
        if user.referrer_id:
            referrer = db.query(User).filter(User.id == user.referrer_id).first()
            referrer_name = referrer.name if referrer else None
        
        # Get direct referrals
        direct_referrals = db.query(User).filter(User.referrer_id == user_id).all()
        direct_referral_list = [{
            "id": r.id,
            "name": r.name,
            "status": "Active" if r.activation_date else "Inactive",
            "package": r.get_package_type() if hasattr(r, 'get_package_type') else 'N/A',
            "activation_date": r.activation_date.strftime('%Y-%m-%d') if r.activation_date else None
        } for r in direct_referrals]
        
        # Get income breakdown
        income_types = ['Direct Referral', 'Matching Referral', 'Ved', 'Guru Dakshina', 'Field Allowance']
        income_breakdown = {}
        total_income = 0
        for income_type in income_types:
            amount = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.referred_user_id == user_id,
                    Transaction.transaction_type == income_type
                )
            ).scalar() or 0
            income_breakdown[income_type] = float(amount)
            total_income += float(amount)
        
        # Get withdrawal history
        withdrawals = db.query(WithdrawalRequest).filter(
            WithdrawalRequest.user_id == user_id
        ).order_by(WithdrawalRequest.created_at.desc()).limit(10).all()
        
        withdrawal_history = [{
            "id": w.id,
            "amount": float(w.withdrawal_amount or 0),
            "status": w.status,
            "created_at": w.created_at.strftime('%Y-%m-%d') if w.created_at else None
        } for w in withdrawals]
        
        pending_withdrawal_amount = sum(float(w.withdrawal_amount or 0) for w in withdrawals if w.status == 'Pending')
        completed_withdrawal_amount = sum(float(w.withdrawal_amount or 0) for w in db.query(WithdrawalRequest).filter(
            WithdrawalRequest.user_id == user_id,
            WithdrawalRequest.status == 'Approved'
        ).all())
        
        # Get MNR Points
        points_record = db.query(MNRPointsBalance).filter(
            MNRPointsBalance.user_id == user_id
        ).first()
        
        mnr_points = {
            "initial_points": float(points_record.initial_points) if points_record else 0,
            "current_balance": float(points_record.current_balance) if points_record else 0,
            "total_consumed": float(points_record.total_consumed) if points_record else 0,
            "receipt_no": points_record.receipt_no if points_record else None,
            "expiry_date": points_record.expiry_date.strftime('%Y-%m-%d') if points_record and points_record.expiry_date else None
        }
        
        # Get Zynova membership
        zynova_member = db.query(ZynovaMember).filter(
            ZynovaMember.user_id == user_id
        ).first()
        
        zynova_status = None
        if zynova_member:
            zynova_status = {
                "member_id": zynova_member.id,
                "legacy_role": zynova_member.role,
                "real_estate": {
                    "role": zynova_member.real_estate_role or 'promoter',
                    "revenue_total": float(zynova_member.real_estate_revenue_total or 0),
                    "team_revenue": float(zynova_member.real_estate_team_revenue or 0),
                    "promoted_at": zynova_member.real_estate_promoted_at.strftime('%Y-%m-%d') if zynova_member.real_estate_promoted_at else None
                },
                "insurance": {
                    "role": zynova_member.insurance_role or 'promoter',
                    "revenue_total": float(zynova_member.insurance_revenue_total or 0),
                    "team_revenue": float(zynova_member.insurance_team_revenue or 0),
                    "promoted_at": zynova_member.insurance_promoted_at.strftime('%Y-%m-%d') if zynova_member.insurance_promoted_at else None
                },
                "joined_at": zynova_member.joined_at.strftime('%Y-%m-%d') if zynova_member.joined_at else None
            }
        
        # Get Zynova incentives earned (sum of promoter_amount for this user)
        zynova_incentives = db.query(func.sum(ZynovaIncentive.promoter_amount)).filter(
            ZynovaIncentive.promoter_id == user_id,
            ZynovaIncentive.status == 'approved'
        ).scalar() or 0
        
        # Get Ved Team info (is this user a Ved owner?)
        ved_team_count = db.query(func.count(VedTeamMember.id)).filter(
            VedTeamMember.ved_owner_id == user_id,
            VedTeamMember.is_active == True
        ).scalar() or 0
        
        # Build comprehensive summary
        summary = {
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "status": user.account_status,
                "user_type": user.user_type,
                "package": user.get_package_type() if hasattr(user, 'get_package_type') else 'N/A',
                "kyc_status": user.kyc_status,
                "bank_details_status": getattr(user, 'bank_details_status', None),
                "registration_date": user.registration_date.strftime('%Y-%m-%d') if user.registration_date else None,
                "activation_date": user.activation_date.strftime('%Y-%m-%d') if user.activation_date else None
            },
            "referrer": {
                "id": user.referrer_id,
                "name": referrer_name
            },
            "network": {
                "direct_referrals_count": len(direct_referrals),
                "direct_referrals": direct_referral_list[:10],  # Limit to 10 for display
                "ved_team_count": ved_team_count
            },
            "income": {
                "breakdown": income_breakdown,
                "total_income": total_income
            },
            "wallet": {
                "current_balance": float(user.wallet_balance or 0),
                "earning_wallet": float(getattr(user, 'earning_wallet', 0) or 0),
                "withdrawable_wallet": float(getattr(user, 'withdrawable_wallet', 0) or 0),
                "upgrade_wallet": float(getattr(user, 'upgrade_wallet', 0) or 0)
            },
            "withdrawals": {
                "pending_amount": pending_withdrawal_amount,
                "completed_amount": completed_withdrawal_amount,
                "recent_history": withdrawal_history
            },
            "mnr_points": mnr_points,
            "zynova": zynova_status,
            "zynova_incentives_earned": float(zynova_incentives),
            "banking": {
                "bank_name": user.bank_name,
                "account_number": user.bank_account_number,
                "ifsc_code": user.bank_ifsc_code,
                "pan_number": user.pan_number
            }
        }
        
        return success_response(
            message="User comprehensive summary retrieved successfully",
            data=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


class UserStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

@router.post("/admin/users/{user_id}/update-status")
async def update_user_status(
    user_id: str,
    status_data: UserStatusUpdate,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Update user account status"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_status = user.account_status
        user.account_status = status_data.status
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='USER_STATUS_UPDATE',
            resource_type='User',
            resource_id=user_id,
            details={
                "old_status": old_status,
                "new_status": status_data.status,
                "reason": status_data.reason
            }
        )
        
        return success_response(
            message="User status updated successfully",
            data={"user_id": user_id, "status": user.account_status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== KYC APPROVALS =====

@router.get("/admin/kyc/pending")
async def get_pending_kyc(
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get users with pending KYC verification"""
    try:
        pending_users = db.query(User).filter(
            User.kyc_status == 'Pending'
        ).order_by(User.registration_date.desc()).limit(100).all()
        
        user_list = [
            {
                "id": str(user.id),
                "user_id": user.user_id,
                "user_name": user.name,
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "pan_number": user.pan_number,
                "aadhaar_number": getattr(user, 'aadhar_number', ''),
                "kyc_status": user.kyc_status,
                "submitted_at": user.registration_date.isoformat() if user.registration_date else None,
                "document_type": "PAN/Aadhaar",
                "document_url": None,
                # Bank Details (DC Protocol - single source from user table, masked for security)
                "account_holder_name": user.account_holder_name,
                "account_number": f"****{user.account_number[-4:]}" if user.account_number and len(user.account_number) > 4 else user.account_number,
                "bank_name": user.bank_name,
                "ifsc_code": user.ifsc_code,
                "branch_name": user.branch_name,
                "bank_details_status": user.bank_details_status
            }
            for user in pending_users
        ]
        
        return success_response(
            message="Pending KYC requests retrieved successfully",
            data={"pending_kyc": user_list, "total": len(user_list)}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

class KYCApprovalRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None

@router.post("/admin/kyc/{user_id}/approve")
async def approve_kyc(
    user_id: str,
    approval_data: KYCApprovalRequest,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Approve or reject KYC verification"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if approval_data.approved:
            user.kyc_status = 'Approved'
            user.kyc_approved_date = get_indian_time()
            user.pan_verified = True
            user.aadhar_verified = True
            user.bank_verified = True
        else:
            user.kyc_status = 'Rejected'
            user.kyc_rejection_reason = approval_data.rejection_reason
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='KYC_APPROVAL' if approval_data.approved else 'KYC_REJECTION',
            resource_type='User',
            resource_id=user_id,
            details={
                "status": user.kyc_status,
                "reason": approval_data.rejection_reason
            }
        )
        
        return success_response(
            message=f"KYC {'approved' if approval_data.approved else 'rejected'} successfully",
            data={"user_id": user_id, "kyc_status": user.kyc_status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== GRANULAR KYC MANAGEMENT (DC Protocol - Individual Field Approvals) =====

@router.get("/admin/kyc/all-users")
async def get_all_users_kyc(
    status_filter: Optional[str] = None,  # Approved, Pending, Rejected, All
    search_user_id: Optional[str] = None,  # Search by User ID
    search_name: Optional[str] = None,  # Search by name
    search_phone: Optional[str] = None,  # Search by phone
    package_filter: Optional[str] = None,  # Filter by package type
    page: int = 1,
    per_page: int = 50,
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """Get all users with detailed KYC/Bank verification status (DC Protocol - user table only)"""
    try:
        query = db.query(User)
        
        # Apply status filter
        if status_filter and status_filter != 'All':
            query = query.filter(User.kyc_status == status_filter)
        
        # Apply search filters
        if search_user_id:
            query = query.filter(User.id.ilike(f'%{search_user_id}%'))
        
        if search_name:
            query = query.filter(User.name.ilike(f'%{search_name}%'))
        
        if search_phone:
            query = query.filter(User.phone_number.ilike(f'%{search_phone}%'))
        
        # Apply package filter
        if package_filter and package_filter != 'All':
            if package_filter == 'Platinum':
                query = query.filter(User.package_points >= 1.0)
            elif package_filter == 'Diamond':
                query = query.filter(and_(User.package_points >= 0.5, User.package_points < 1.0))
            elif package_filter == 'Blue/Loyal':
                query = query.filter(and_(User.package_points > 0, User.package_points < 0.5))
            elif package_filter == 'Eligible':
                query = query.filter(or_(User.package_points == 0.0, User.package_points.is_(None)))
        
        # Pagination
        total = query.count()
        users = query.order_by(User.registration_date.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # DC Protocol: Bulk query for documents to avoid N+1 problem
        user_ids = [user.id for user in users]
        
        all_docs = db.query(KYCDocument).filter(
            KYCDocument.owner_id.in_(user_ids),
            KYCDocument.is_current_version == True
        ).all()
        
        # Group documents by user_id
        user_documents = {}
        for doc in all_docs:
            if doc.owner_id not in user_documents:
                user_documents[doc.owner_id] = set()
            user_documents[doc.owner_id].add(doc.document_type)
        
        user_list = []
        for user in users:
            profile_status = _check_profile_completeness(user)
            user_list.append({
                "id": str(user.id),
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "kyc_status": user.kyc_status,
                "bank_details_status": user.bank_details_status,
                "submitted_at": user.registration_date.isoformat() if user.registration_date else None,
                # Profile Completeness (NEW - DC Protocol)
                "profile_complete": profile_status["is_complete"],
                "profile_completion_percentage": profile_status["completion_percentage"],
                "missing_profile_fields": profile_status["missing_fields"],
                # Individual KYC Verifications (DC Protocol - user table)
                "aadhaar_verified": user.aadhaar_verified,
                "pan_verified": user.pan_verified,
                "document_verified": user.document_verified,
                # Individual Bank Verifications (DC Protocol - user table)
                "account_holder_verified": user.account_holder_verified,
                "account_number_verified": user.account_number_verified,
                "ifsc_verified": user.ifsc_verified,
                "bank_name_verified": user.bank_name_verified,
                "branch_verified": user.branch_verified,
                # Approval Tracking - Who approved each field
                "aadhaar_verified_by": user.aadhaar_verified_by,
                "pan_verified_by": user.pan_verified_by,
                "document_verified_by": user.document_verified_by,
                "account_holder_verified_by": user.account_holder_verified_by,
                "account_number_verified_by": user.account_number_verified_by,
                "ifsc_verified_by": user.ifsc_verified_by,
                "bank_name_verified_by": user.bank_name_verified_by,
                "branch_verified_by": user.branch_verified_by,
                # Approval Timestamps - When each field was verified
                "aadhaar_verified_at": user.aadhaar_verified_at.isoformat() if user.aadhaar_verified_at else None,
                "pan_verified_at": user.pan_verified_at.isoformat() if user.pan_verified_at else None,
                "document_verified_at": user.document_verified_at.isoformat() if user.document_verified_at else None,
                "account_holder_verified_at": user.account_holder_verified_at.isoformat() if user.account_holder_verified_at else None,
                "account_number_verified_at": user.account_number_verified_at.isoformat() if user.account_number_verified_at else None,
                "ifsc_verified_at": user.ifsc_verified_at.isoformat() if user.ifsc_verified_at else None,
                "bank_name_verified_at": user.bank_name_verified_at.isoformat() if user.bank_name_verified_at else None,
                "branch_verified_at": user.branch_verified_at.isoformat() if user.branch_verified_at else None,
                # DC Protocol Feb 2026: Staff Validation Tracking (Step 1)
                "aadhaar_validated": getattr(user, 'aadhaar_validated', False),
                "pan_validated": getattr(user, 'pan_validated', False),
                "document_validated": getattr(user, 'document_validated', False),
                "account_holder_validated": getattr(user, 'account_holder_validated', False),
                "account_number_validated": getattr(user, 'account_number_validated', False),
                "ifsc_validated": getattr(user, 'ifsc_validated', False),
                "bank_name_validated": getattr(user, 'bank_name_validated', False),
                "branch_validated": getattr(user, 'branch_validated', False),
                # Actual field values (masked where needed)
                "aadhaar_number": user.aadhaar_number,
                "pan_number": user.pan_number,
                "account_holder_name": user.bank_account_holder,
                "account_number": f"****{user.bank_account_number[-4:]}" if user.bank_account_number and len(user.bank_account_number) > 4 else user.bank_account_number,
                "bank_name": user.bank_name,
                "ifsc_code": user.bank_ifsc_code,
                "branch_name": user.bank_branch_name,
                # DC Protocol Feb 2026: Personal details for edit mode
                "gender": user.gender,
                "actual_date_of_birth": user.actual_date_of_birth.strftime('%Y-%m-%d') if user.actual_date_of_birth else None,
                "dob_as_per_certificate": getattr(user, 'dob_as_per_certificate', None).strftime('%Y-%m-%d') if getattr(user, 'dob_as_per_certificate', None) else None,
                "phone_number": user.phone_number,
                # DC Protocol Feb 2026: Address details for edit mode
                "address_line1": user.address_line1,
                "address_line2": user.address_line2,
                "city": user.city,
                "state": user.state,
                "postal_code": user.postal_code,
                "country": user.country,
                # Document availability (DC Protocol - check individual document types)
                "has_aadhaar_document": ('aadhar_front' in user_documents.get(user.id, set()) or 'aadhar_back' in user_documents.get(user.id, set())),
                "has_pan_document": 'pan_card' in user_documents.get(user.id, set()),
                "has_bank_document": 'bank_passbook' in user_documents.get(user.id, set())
            })
        
        return success_response(
            message="Users retrieved successfully",
            data={
                "users": user_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

class FieldApprovalRequest(BaseModel):
    field_name: str  # aadhaar_verified, pan_verified, account_holder_verified, etc.
    approved: bool
    rejection_reason: Optional[str] = None

@router.get("/admin/kyc/users/{user_id}")
async def get_single_user_kyc(
    user_id: str,
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Get single user's KYC/Bank verification data (DC Protocol Feb 2026)
    Used for refreshing modal after approve/reject actions
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get documents for this user
        user_docs = db.query(KYCDocument).filter(
            KYCDocument.owner_id == user_id,
            KYCDocument.is_current_version == True
        ).all()
        
        doc_types = set(doc.document_type for doc in user_docs)
        
        profile_status = _check_profile_completeness(user)
        
        return {
            "id": str(user.id),
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone_number,
            "kyc_status": user.kyc_status,
            "bank_details_status": user.bank_details_status,
            "submitted_at": user.registration_date.isoformat() if user.registration_date else None,
            # Profile Completeness
            "profile_complete": profile_status["is_complete"],
            "profile_completion_percentage": profile_status["completion_percentage"],
            "missing_profile_fields": profile_status["missing_fields"],
            # Individual KYC Verifications
            "aadhaar_verified": user.aadhaar_verified,
            "pan_verified": user.pan_verified,
            "document_verified": user.document_verified,
            # Individual Bank Verifications
            "account_holder_verified": user.account_holder_verified,
            "account_number_verified": user.account_number_verified,
            "ifsc_verified": user.ifsc_verified,
            "bank_name_verified": user.bank_name_verified,
            "branch_verified": user.branch_verified,
            # Approval Tracking - Who approved/rejected each field
            "aadhaar_verified_by": user.aadhaar_verified_by,
            "pan_verified_by": user.pan_verified_by,
            "document_verified_by": user.document_verified_by,
            "account_holder_verified_by": user.account_holder_verified_by,
            "account_number_verified_by": user.account_number_verified_by,
            "ifsc_verified_by": user.ifsc_verified_by,
            "bank_name_verified_by": user.bank_name_verified_by,
            "branch_verified_by": user.branch_verified_by,
            # Approval Timestamps
            "aadhaar_verified_at": user.aadhaar_verified_at.isoformat() if user.aadhaar_verified_at else None,
            "pan_verified_at": user.pan_verified_at.isoformat() if user.pan_verified_at else None,
            "document_verified_at": user.document_verified_at.isoformat() if user.document_verified_at else None,
            "account_holder_verified_at": user.account_holder_verified_at.isoformat() if user.account_holder_verified_at else None,
            "account_number_verified_at": user.account_number_verified_at.isoformat() if user.account_number_verified_at else None,
            "ifsc_verified_at": user.ifsc_verified_at.isoformat() if user.ifsc_verified_at else None,
            "bank_name_verified_at": user.bank_name_verified_at.isoformat() if user.bank_name_verified_at else None,
            "branch_verified_at": user.branch_verified_at.isoformat() if user.branch_verified_at else None,
            # DC Protocol Feb 2026: Validation Tracking (Staff validates → Accounts approves)
            "aadhaar_validated": getattr(user, 'aadhaar_validated', False),
            "aadhaar_validated_by": getattr(user, 'aadhaar_validated_by', None),
            "aadhaar_validated_at": getattr(user, 'aadhaar_validated_at', None).isoformat() if getattr(user, 'aadhaar_validated_at', None) else None,
            "pan_validated": getattr(user, 'pan_validated', False),
            "pan_validated_by": getattr(user, 'pan_validated_by', None),
            "pan_validated_at": getattr(user, 'pan_validated_at', None).isoformat() if getattr(user, 'pan_validated_at', None) else None,
            "document_validated": getattr(user, 'document_validated', False),
            "document_validated_by": getattr(user, 'document_validated_by', None),
            "document_validated_at": getattr(user, 'document_validated_at', None).isoformat() if getattr(user, 'document_validated_at', None) else None,
            "account_holder_validated": getattr(user, 'account_holder_validated', False),
            "account_holder_validated_by": getattr(user, 'account_holder_validated_by', None),
            "account_holder_validated_at": getattr(user, 'account_holder_validated_at', None).isoformat() if getattr(user, 'account_holder_validated_at', None) else None,
            "account_number_validated": getattr(user, 'account_number_validated', False),
            "account_number_validated_by": getattr(user, 'account_number_validated_by', None),
            "account_number_validated_at": getattr(user, 'account_number_validated_at', None).isoformat() if getattr(user, 'account_number_validated_at', None) else None,
            "ifsc_validated": getattr(user, 'ifsc_validated', False),
            "ifsc_validated_by": getattr(user, 'ifsc_validated_by', None),
            "ifsc_validated_at": getattr(user, 'ifsc_validated_at', None).isoformat() if getattr(user, 'ifsc_validated_at', None) else None,
            "bank_name_validated": getattr(user, 'bank_name_validated', False),
            "bank_name_validated_by": getattr(user, 'bank_name_validated_by', None),
            "bank_name_validated_at": getattr(user, 'bank_name_validated_at', None).isoformat() if getattr(user, 'bank_name_validated_at', None) else None,
            "branch_validated": getattr(user, 'branch_validated', False),
            "branch_validated_by": getattr(user, 'branch_validated_by', None),
            "branch_validated_at": getattr(user, 'branch_validated_at', None).isoformat() if getattr(user, 'branch_validated_at', None) else None,
            # Actual field values
            "aadhaar_number": user.aadhaar_number,
            "pan_number": user.pan_number,
            "account_holder_name": user.bank_account_holder,
            "account_number": f"****{user.bank_account_number[-4:]}" if user.bank_account_number and len(user.bank_account_number) > 4 else user.bank_account_number,
            "bank_name": user.bank_name,
            "ifsc_code": user.bank_ifsc_code,
            "branch_name": user.bank_branch_name,
            # DC Protocol Feb 2026: Personal details for edit mode
            "gender": user.gender,
            "actual_date_of_birth": user.actual_date_of_birth.strftime('%Y-%m-%d') if user.actual_date_of_birth else None,
            "dob_as_per_certificate": getattr(user, 'dob_as_per_certificate', None).strftime('%Y-%m-%d') if getattr(user, 'dob_as_per_certificate', None) else None,
            "phone_number": user.phone_number,
            # DC Protocol Feb 2026: Address details for edit mode
            "address_line1": user.address_line1,
            "address_line2": user.address_line2,
            "city": user.city,
            "state": user.state,
            "postal_code": user.postal_code,
            # Document availability
            "has_aadhaar_document": ('aadhar_front' in doc_types or 'aadhar_back' in doc_types),
            "has_pan_document": 'pan_card' in doc_types,
            "has_bank_document": 'bank_passbook' in doc_types
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/admin/kyc/approve-field/{user_id}")
async def approve_kyc_field(
    user_id: str,
    approval_data: FieldApprovalRequest,
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Approve or reject individual KYC/Bank field (DC Protocol - Staff only)
    
    DC Protocol Feb 2026: Only specific staff roles can approve directly:
    - VGK Supreme, Accounts Team, Finance Admin, Super Admin
    Other staff must use validate-field endpoint first.
    """
    try:
        # DC Protocol Feb 2026: Staff-only approval - check for direct approval rights
        staff_type = getattr(current_user, 'staff_type', None) or ''
        staff_type_upper = staff_type.upper() if staff_type else ''
        
        # VGK4U has supreme/skip-level approval rights
        is_vgk4u = staff_type_upper == 'VGK4U'
        # Also check for Finance Admin or Super Admin in staff_type
        is_finance = 'finance' in staff_type.lower() if staff_type else False
        is_super_admin = 'super' in staff_type.lower() and 'admin' in staff_type.lower() if staff_type else False
        
        # DC Protocol Feb 2026: Check if staff is in Accounts department
        is_accounts = False
        dept = getattr(current_user, 'department', None)
        if dept:
            dept_name = getattr(dept, 'name', '') or ''
            is_accounts = 'accounts' in dept_name.lower()
        
        can_approve_directly = is_vgk4u or is_accounts or is_finance or is_super_admin
        
        # DC Protocol: Menu-based access control - page assignment = full access
        # if not can_approve_directly:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Only VGK4U, Finance Admin, or Super Admin can approve directly. Use validate-field for first-level validation."
        #     )
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Valid field names
        valid_fields = [
            'aadhaar_verified', 'pan_verified', 'document_verified',
            'account_holder_verified', 'account_number_verified', 
            'ifsc_verified', 'bank_name_verified', 'branch_verified'
        ]
        
        if approval_data.field_name not in valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field name. Must be one of: {', '.join(valid_fields)}"
            )
        
        # DC Protocol Feb 2026: Server-side enforcement of 2-level workflow
        # Field must be validated before it can be approved
        validated_field_name = approval_data.field_name.replace('_verified', '_validated')
        is_field_validated = getattr(user, validated_field_name, False)
        
        if not is_field_validated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field must be validated first. Use validate-field endpoint before approving."
            )
        
        # Update the specific field (DC Protocol - direct user table update)
        setattr(user, approval_data.field_name, approval_data.approved)
        
        # DC Protocol Feb 2026: Record who approved/rejected and when (for both actions)
        # This allows UI to distinguish between "pending" (never reviewed) and "rejected" (explicitly declined)
        approver_field = approval_data.field_name.replace('_verified', '_verified_by')
        timestamp_field = approval_data.field_name.replace('_verified', '_verified_at')
        
        # DC Protocol Feb 2026: Staff-only approval - use emp_code as approver ID
        approver_id = getattr(current_user, 'emp_code', 'Unknown')
        setattr(user, approver_field, approver_id)
        
        # Record timestamp
        setattr(user, timestamp_field, get_indian_time())
        
        # Update overall statuses based on all fields (triggers real-time wallet sync if approved)
        _update_overall_kyc_status(user, db)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='KYC_FIELD_APPROVAL',
            resource_type='User',
            resource_id=user_id,
            details={
                "field": approval_data.field_name,
                "approved": approval_data.approved,
                "reason": approval_data.rejection_reason,
                "overall_kyc_status": user.kyc_status,
                "overall_bank_status": user.bank_details_status
            }
        )
        
        return success_response(
            message=f"Field {approval_data.field_name} {'approved' if approval_data.approved else 'rejected'} successfully",
            data={
                "user_id": user_id,
                "field": approval_data.field_name,
                "approved": approval_data.approved,
                "kyc_status": user.kyc_status,
                "bank_details_status": user.bank_details_status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/admin/kyc/approve-all-fields/{user_id}")
async def approve_all_kyc_fields(
    user_id: str,
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Approve all KYC and Bank fields at once (DC Protocol - updates user table only)
    
    DC Protocol Feb 2026: Staff with page access can approve (Staff MNR pages)
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # DC Protocol Feb 2026: Get approver identifier (emp_code for staff, id for MNR users)
        approver_id = getattr(current_user, 'emp_code', None) or str(getattr(current_user, 'id', 'Unknown'))
        approval_time = get_indian_time()
        
        # Approve all KYC fields (DC Protocol - user table)
        user.aadhaar_verified = True
        user.aadhaar_verified_by = approver_id
        user.aadhaar_verified_at = approval_time
        user.pan_verified = True
        user.pan_verified_by = approver_id
        user.pan_verified_at = approval_time
        user.document_verified = True
        user.document_verified_by = approver_id
        user.document_verified_at = approval_time
        
        # Approve all Bank fields (DC Protocol - user table)
        user.account_holder_verified = True
        user.account_holder_verified_by = approver_id
        user.account_holder_verified_at = approval_time
        user.account_number_verified = True
        user.account_number_verified_by = approver_id
        user.account_number_verified_at = approval_time
        user.ifsc_verified = True
        user.ifsc_verified_by = approver_id
        user.ifsc_verified_at = approval_time
        user.bank_name_verified = True
        user.bank_name_verified_by = approver_id
        user.bank_name_verified_at = approval_time
        user.branch_verified = True
        user.branch_verified_by = approver_id
        user.branch_verified_at = approval_time
        
        # Update overall statuses (triggers real-time wallet sync if approved)
        _update_overall_kyc_status(user, db)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='KYC_ALL_FIELDS_APPROVED',
            resource_type='User',
            resource_id=user_id,
            details={
                "all_fields_approved": True,
                "kyc_status": user.kyc_status,
                "bank_details_status": user.bank_details_status
            }
        )
        
        return success_response(
            message="All KYC and Bank fields approved successfully",
            data={
                "user_id": user_id,
                "kyc_status": user.kyc_status,
                "bank_details_status": user.bank_details_status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# DC Protocol Feb 2026: Validation endpoint (Staff validates → Accounts approves)
@router.post("/admin/kyc/validate-field/{user_id}")
async def validate_kyc_field(
    user_id: str,
    validation_data: FieldApprovalRequest,
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Validate individual KYC/Bank field (first-level check by staff)
    
    DC Protocol Feb 2026: Separate validation from approval
    - Staff with page access can VALIDATE (first level)
    - Accounts/VGK Supreme can APPROVE directly (skip validation)
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Map field name to validation field
        field_mapping = {
            'aadhaar_verified': 'aadhaar_validated',
            'pan_verified': 'pan_validated',
            'document_verified': 'document_validated',
            'account_holder_verified': 'account_holder_validated',
            'account_number_verified': 'account_number_validated',
            'ifsc_verified': 'ifsc_validated',
            'bank_name_verified': 'bank_name_validated',
            'branch_verified': 'branch_validated'
        }
        
        if validation_data.field_name not in field_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field name. Must be one of: {', '.join(field_mapping.keys())}"
            )
        
        # Get the validation field name
        validated_field = field_mapping[validation_data.field_name]
        validated_by_field = validated_field.replace('_validated', '_validated_by')
        validated_at_field = validated_field.replace('_validated', '_validated_at')
        
        # Update validation status
        setattr(user, validated_field, validation_data.approved)
        
        # Record validator ID (use emp_code for staff)
        validator_id = getattr(current_user, 'emp_code', None) or str(getattr(current_user, 'id', 'Unknown'))
        setattr(user, validated_by_field, validator_id)
        setattr(user, validated_at_field, get_indian_time())
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='KYC_FIELD_VALIDATION',
            resource_type='User',
            resource_id=user_id,
            details={
                "field": validation_data.field_name,
                "validated": validation_data.approved,
                "reason": validation_data.rejection_reason
            }
        )
        
        return success_response(
            message=f"Field {validation_data.field_name} {'validated' if validation_data.approved else 'validation rejected'} successfully",
            data={
                "user_id": user_id,
                "field": validation_data.field_name,
                "validated": validation_data.approved
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/kyc/staff-role")
async def get_staff_kyc_role(
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Get current staff's role for KYC approval workflow
    
    DC Protocol Feb 2026: Determines button visibility
    - Accounts Team / VGK Supreme: can_approve = True (direct approval, skip validation)
    - Other Staff: can_validate = True (first-level validation only)
    """
    try:
        staff_type = getattr(current_user, 'staff_type', None) or ''
        emp_code = getattr(current_user, 'emp_code', None) or ''
        staff_type_upper = staff_type.upper() if staff_type else ''
        
        # DC Protocol Feb 2026: VGK4U has direct approval rights (skip validation)
        is_vgk4u = staff_type_upper == 'VGK4U'
        # Also check for Finance Admin or Super Admin roles
        is_finance = 'finance' in staff_type.lower() if staff_type else False
        is_super_admin = 'super' in staff_type.lower() and 'admin' in staff_type.lower() if staff_type else False
        
        # DC Protocol Feb 2026: Check if staff is in Accounts department
        is_accounts = False
        dept = getattr(current_user, 'department', None)
        if dept:
            dept_name = getattr(dept, 'name', '') or ''
            is_accounts = 'accounts' in dept_name.lower()
        
        can_approve_directly = is_vgk4u or is_accounts or is_finance or is_super_admin
        
        return success_response(
            message="Staff role retrieved",
            data={
                "emp_code": emp_code,
                "staff_type": staff_type,
                "can_approve": can_approve_directly,
                "can_validate": True,  # All staff with page access can validate
                "approval_level": "direct" if can_approve_directly else "validation"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

class UserKYCUpdateRequest(BaseModel):
    """Request to update MNR user KYC/Personal data by staff/admin"""
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_account_holder: Optional[str] = None
    bank_branch_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    actual_date_of_birth: Optional[str] = None
    date_of_birth_certificate: Optional[str] = None

@router.put("/admin/kyc/update-user/{user_id}")
async def update_user_kyc_data(
    user_id: str,
    update_data: UserKYCUpdateRequest = Body(...),
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Update MNR user KYC/Personal data (DC Protocol Feb 2026 - Staff/Admin editable)
    Allows staff to edit user profile, KYC, and bank details
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        changes = {}
        
        # Update Aadhaar if provided
        if update_data.aadhaar_number is not None:
            if update_data.aadhaar_number and len(update_data.aadhaar_number) != 12:
                raise HTTPException(status_code=400, detail="Aadhaar must be 12 digits")
            old_val = user.aadhaar_number
            user.aadhaar_number = update_data.aadhaar_number or None
            if old_val != user.aadhaar_number:
                changes['aadhaar_number'] = {'old': old_val, 'new': user.aadhaar_number}
        
        # Update PAN if provided
        if update_data.pan_number is not None:
            pan = update_data.pan_number.upper() if update_data.pan_number else None
            old_val = user.pan_number
            user.pan_number = pan
            if old_val != user.pan_number:
                changes['pan_number'] = {'old': old_val, 'new': user.pan_number}
        
        # Update phone number
        if update_data.phone_number is not None:
            old_val = user.phone_number
            user.phone_number = update_data.phone_number or None
            if old_val != user.phone_number:
                changes['phone_number'] = {'old': old_val, 'new': user.phone_number}
        
        # Update email
        if update_data.email is not None:
            old_val = user.email
            user.email = update_data.email or None
            if old_val != user.email:
                changes['email'] = {'old': old_val, 'new': user.email}
        
        # Update bank details
        if update_data.bank_name is not None:
            old_val = user.bank_name
            user.bank_name = update_data.bank_name or None
            if old_val != user.bank_name:
                changes['bank_name'] = {'old': old_val, 'new': user.bank_name}
        
        if update_data.bank_account_number is not None:
            old_val = user.bank_account_number
            user.bank_account_number = update_data.bank_account_number or None
            if old_val != user.bank_account_number:
                changes['bank_account_number'] = {'old': '****', 'new': '****'}
        
        if update_data.bank_ifsc_code is not None:
            old_val = user.bank_ifsc_code
            user.bank_ifsc_code = (update_data.bank_ifsc_code.upper() if update_data.bank_ifsc_code else None)
            if old_val != user.bank_ifsc_code:
                changes['bank_ifsc_code'] = {'old': old_val, 'new': user.bank_ifsc_code}
        
        if update_data.bank_account_holder is not None:
            old_val = user.bank_account_holder
            user.bank_account_holder = update_data.bank_account_holder or None
            if old_val != user.bank_account_holder:
                changes['bank_account_holder'] = {'old': old_val, 'new': user.bank_account_holder}
        
        if update_data.bank_branch_name is not None:
            old_val = user.bank_branch_name
            user.bank_branch_name = update_data.bank_branch_name or None
            if old_val != user.bank_branch_name:
                changes['bank_branch_name'] = {'old': old_val, 'new': user.bank_branch_name}
        
        # Update address fields
        if update_data.address_line1 is not None:
            user.address_line1 = update_data.address_line1 or None
        if update_data.address_line2 is not None:
            user.address_line2 = update_data.address_line2 or None
        if update_data.city is not None:
            user.city = update_data.city or None
        if update_data.state is not None:
            user.state = update_data.state or None
        if update_data.postal_code is not None:
            user.postal_code = update_data.postal_code or None
        if update_data.gender is not None:
            user.gender = update_data.gender or None
        if update_data.country is not None:
            user.country = update_data.country or None
        if update_data.actual_date_of_birth is not None:
            if update_data.actual_date_of_birth:
                try:
                    user.actual_date_of_birth = datetime.strptime(update_data.actual_date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format for actual_date_of_birth. Use YYYY-MM-DD.")
            else:
                user.actual_date_of_birth = None
        if update_data.date_of_birth_certificate is not None:
            if update_data.date_of_birth_certificate:
                try:
                    user.certificate_date_of_birth = datetime.strptime(update_data.date_of_birth_certificate, '%Y-%m-%d').date()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format for date_of_birth_certificate. Use YYYY-MM-DD.")
            else:
                user.certificate_date_of_birth = None
        
        user.profile_updated_at = datetime.now()
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='ADMIN_KYC_UPDATE',
            resource_type='User',
            resource_id=user_id,
            details={
                "changes": changes,
                "updated_by": getattr(current_user, 'emp_code', None) or str(getattr(current_user, 'id', 'Unknown')),
                "updated_by_type": getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', 'Unknown')
            }
        )
        
        return success_response(
            message="User KYC data updated successfully",
            data={
                "user_id": user_id,
                "changes_count": len(changes),
                "updated_by": current_user.id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# DC Protocol Feb 2026: Admin document upload on behalf of user
@router.post("/admin/kyc/upload-document/{user_id}")
async def admin_upload_kyc_document(
    user_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    Upload KYC document on behalf of user (DC Protocol Feb 2026)
    Staff can upload/replace documents for users through KYC Management
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Normalize document type
        document_type_mapping = {
            'aadhaar_front': 'aadhar_front',
            'aadhaar_back': 'aadhar_back',
            'aadhar_front': 'aadhar_front',
            'aadhar_back': 'aadhar_back',
            'pan_card': 'pan_card',
            'bank_passbook': 'bank_passbook',
            'passport_photo': 'passport_photo'
        }
        
        if document_type not in document_type_mapping:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")
        
        normalized_type = document_type_mapping[document_type]
        
        # Check for existing document
        existing_doc = db.query(KYCDocument).filter(
            and_(
                KYCDocument.owner_id == user_id,
                KYCDocument.document_type == normalized_type
            )
        ).first()
        
        # Import upload service
        from app.services.universal_upload_service import UniversalUploadService
        from app.services.object_storage import storage_service
        
        # DC Protocol Feb 2026: Size validation handled by UniversalUploadService.handle_upload()
        # which validates via validate_file_size() - no pre-read needed (avoids file consumption issue)
        
        # Delete old file if exists
        if existing_doc:
            if existing_doc.file_path:
                try:
                    storage_service.delete_file(existing_doc.file_path)
                except Exception:
                    pass
            if existing_doc.compressed_path:
                try:
                    storage_service.delete_file(existing_doc.compressed_path)
                except Exception:
                    pass
            doc_to_upload = existing_doc
            
            # DC Protocol Feb 2026: Reset user-level approval/validation when document replaced
            # Map document type to user field prefix
            field_prefix_map = {
                'aadhar_front': 'document',  # Aadhaar uses 'document' field
                'aadhar_back': 'document',
                'pan_card': 'document',
                'bank_passbook': 'document'
            }
            if normalized_type in field_prefix_map:
                # Reset approval status
                setattr(user, 'document_verified', False)
                setattr(user, 'document_verified_by', None)
                setattr(user, 'document_verified_at', None)
                # Reset validation status
                if hasattr(user, 'document_validated'):
                    setattr(user, 'document_validated', False)
                    setattr(user, 'document_validated_by', None)
                    setattr(user, 'document_validated_at', None)
        else:
            # Create new document record
            doc_to_upload = KYCDocument(
                owner_id=user_id,
                document_type=normalized_type,
                file_path='pending_upload',
                file_name='pending',
                original_filename=file.filename,
                file_size=1,  # DC Protocol: Placeholder to pass positive_file_size constraint, updated after upload
                mime_type='application/octet-stream',
                processing_status='pending',
                status='Pending',
                is_current_version=True,
                version=1
            )
            db.add(doc_to_upload)
            db.flush()  # Get ID
        
        # Upload file using universal upload service (handle_upload is correct method)
        upload_result = await UniversalUploadService.handle_upload(
            file=file,
            table_name='kyc_document',
            record_id=doc_to_upload.id,
            uploaded_by_id=getattr(current_user, 'id', 0),
            uploaded_by_type='staff',
            storage_dir='kyc_documents',
            db=db,
            emp_code=getattr(current_user, 'emp_code', None),
            allow_videos=False
        )
        
        # DC Protocol Feb 2026: Enforce 5MB limit for KYC documents (server-side enforcement)
        MAX_KYC_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        actual_file_size = upload_result.get('file_size', 0)
        if actual_file_size > MAX_KYC_FILE_SIZE:
            # Delete uploaded file and reject
            try:
                storage_service.delete_file(upload_result['file_path'])
            except Exception:
                pass
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"File size ({round(actual_file_size/(1024*1024), 2)}MB) exceeds maximum allowed size for KYC documents (5MB)"
            )
        
        # Update document record with upload results
        doc_to_upload.file_path = upload_result['file_path']
        doc_to_upload.file_name = upload_result.get('file_name', file.filename)
        doc_to_upload.original_filename = upload_result.get('original_filename', file.filename)
        doc_to_upload.file_size = upload_result.get('file_size', 0)
        doc_to_upload.mime_type = upload_result.get('file_type', file.content_type or 'application/octet-stream')
        doc_to_upload.processing_status = 'completed'
        doc_to_upload.status = 'Pending'  # Reset to pending for review
        doc_to_upload.uploaded_at = get_indian_time()
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='ADMIN_KYC_DOCUMENT_UPLOAD',
            resource_type='KYCDocument',
            resource_id=str(doc_to_upload.id),
            details={
                "user_id": user_id,
                "document_type": normalized_type,
                "filename": file.filename,
                "uploaded_by": getattr(current_user, 'emp_code', None) or str(current_user.id)
            }
        )
        
        return success_response(
            message=f"Document {normalized_type} uploaded successfully",
            data={
                "document_id": doc_to_upload.id,
                "document_type": normalized_type,
                "file_path": upload_result['file_path']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/kyc/view-document/{user_id}/{document_type}")
async def view_kyc_document(
    user_id: str,
    document_type: str,  # 'aadhaar', 'pan', 'bank'
    current_user = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    View uploaded KYC/Bank documents (DC Protocol Feb 2026 - paths from kyc_document table)
    Security: Staff with page access, validates user exists
    FIXED: Query kyc_document table instead of non-existent user table fields
    """
    try:
        # DC Protocol: Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Map frontend document type to database document_type format
        # DC Protocol Feb 2026: Support both generic types AND specific types
        # Frontend sends: 'aadhaar', 'pan', 'bank' OR specific: 'aadhaar_front', 'aadhaar_back'
        # Database has BOTH spellings: 'aadhar_front'/'aadhaar_front'
        document_type_map = {
            'aadhaar': ['aadhaar_front', 'aadhaar_back', 'aadhar_front', 'aadhar_back'],
            'aadhaar_front': ['aadhaar_front', 'aadhar_front'],
            'aadhaar_back': ['aadhaar_back', 'aadhar_back'],
            'pan': ['pan_card'],
            'bank': ['bank_passbook']
        }
        
        if document_type not in document_type_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document type. Must be 'aadhaar', 'pan', or 'bank'"
            )
        
        # DC Protocol: Query kyc_document table for the document
        # Priority: Latest Approved document, if none then latest Pending document
        possible_types = document_type_map[document_type]
        
        # First try to get Approved documents
        document = db.query(KYCDocument).filter(
            and_(
                KYCDocument.owner_id == user_id,
                KYCDocument.document_type.in_(possible_types),
                KYCDocument.status == 'Approved',
                KYCDocument.is_current_version == True
            )
        ).order_by(KYCDocument.uploaded_at.desc()).first()
        
        # If no Approved, get latest Pending document
        if not document:
            document = db.query(KYCDocument).filter(
                and_(
                    KYCDocument.owner_id == user_id,
                    KYCDocument.document_type.in_(possible_types),
                    KYCDocument.status == 'Pending',
                    KYCDocument.is_current_version == True
                )
            ).order_by(KYCDocument.uploaded_at.desc()).first()
        
        # If still no document, try ANY status (fallback)
        if not document:
            document = db.query(KYCDocument).filter(
                and_(
                    KYCDocument.owner_id == user_id,
                    KYCDocument.document_type.in_(possible_types),
                    KYCDocument.is_current_version == True
                )
            ).order_by(KYCDocument.uploaded_at.desc()).first()
        
        # DC Protocol Feb 2026: Final fallback - ignore is_current_version filter
        if not document:
            document = db.query(KYCDocument).filter(
                and_(
                    KYCDocument.owner_id == user_id,
                    KYCDocument.document_type.in_(possible_types)
                )
            ).order_by(KYCDocument.uploaded_at.desc()).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{document_type.upper()} document not uploaded"
            )
        
        # Get file path from kyc_document table (DC Protocol - single source of truth)
        document_path = document.file_path
        
        if not document_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{document_type.upper()} document path is missing"
            )
        
        # DC Protocol Feb 2026: Files are stored in Object Storage (OBJECT_STORAGE_THRESHOLD = 0)
        # Import storage service and download from Object Storage
        from app.services.object_storage import storage_service
        
        # Download from Object Storage
        file_data = storage_service.download_file(document_path)
        
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document file not found in storage: {document_path}"
            )
        
        # Log document access for audit trail (wrapped in try-catch to not block file viewing)
        try:
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action='KYC_DOCUMENT_VIEWED',
                resource_type='KYCDocument',
                resource_id=str(document.id),
                details={
                    "user_id": user_id,
                    "document_type": document_type,
                    "db_document_type": document.document_type,
                    "document_path": document_path,
                    "viewer_id": getattr(current_user, 'emp_code', None) or str(getattr(current_user, 'id', 'Unknown'))
                }
            )
        except Exception as audit_err:
            import logging
            logging.error(f"[DC-KYC-VIEW] Audit log failed (non-blocking): {audit_err}")
        
        # Return file from memory with proper content type
        from fastapi.responses import Response
        import unicodedata
        import re
        
        # DC Protocol Feb 2026: Sanitize filename to ASCII-safe for HTTP headers
        # Unicode characters like '\u202f' (Narrow No-Break Space from macOS) cause latin-1 encoding errors
        def sanitize_filename_for_header(filename: str) -> str:
            if not filename:
                return "document"
            # Normalize Unicode (NFKD decomposes special chars like narrow no-break space)
            normalized = unicodedata.normalize('NFKD', filename)
            # Keep only ASCII characters
            ascii_safe = normalized.encode('ascii', 'ignore').decode('ascii')
            # Replace multiple spaces with single space
            ascii_safe = re.sub(r'\s+', ' ', ascii_safe).strip()
            # Remove any characters that might break header parsing
            ascii_safe = re.sub(r'["\\\r\n]', '', ascii_safe)
            return ascii_safe or "document"
        
        raw_filename = document.original_filename or os.path.basename(document_path) or f"{document_type}_document"
        safe_filename = sanitize_filename_for_header(raw_filename)
        
        return Response(
            content=file_data,
            media_type=document.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"inline; filename=\"{safe_filename}\""
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logging.error(f"[DC-KYC-VIEW] Error viewing document: {str(e)}")
        logging.error(f"[DC-KYC-VIEW] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error viewing document: {str(e)}"
        )

def _check_profile_completeness(user: User) -> Dict[str, Any]:
    """
    Check if user profile is complete (DC Protocol - user table only)
    Returns: {
        "is_complete": bool,
        "missing_fields": List[str],
        "completion_percentage": int
    }
    """
    required_fields = {
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "gender": user.gender,
        "actual_date_of_birth": user.actual_date_of_birth,
        "address_line1": user.address_line1,
        "city": user.city,
        "state": user.state,
        "postal_code": user.postal_code,
        "country": user.country,
        "aadhaar_number": user.aadhaar_number,
        "pan_number": user.pan_number,
        "bank_account_holder": user.bank_account_holder,
        "bank_name": user.bank_name,
        "bank_account_number": user.bank_account_number,
        "bank_ifsc_code": user.bank_ifsc_code,
        "bank_branch_name": user.bank_branch_name
    }
    
    missing_fields = [field for field, value in required_fields.items() if not value]
    total_fields = len(required_fields)
    completed_fields = total_fields - len(missing_fields)
    completion_percentage = int((completed_fields / total_fields) * 100)
    
    return {
        "is_complete": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "completion_percentage": completion_percentage
    }

def _update_overall_kyc_status(user: User, db: Session = None):
    """
    Update overall KYC and Bank statuses based on individual field verifications (DC Protocol)
    NOW INCLUDES: 
    - Profile completeness check - KYC can only be approved if profile is 100% complete
    - REAL-TIME WALLET SYNC - Automatically sync wallet when KYC or Bank status becomes 'Approved'
    """
    # Store previous statuses to detect changes
    previous_kyc_status = user.kyc_status
    previous_bank_status = user.bank_details_status
    
    # Check profile completeness FIRST
    profile_status = _check_profile_completeness(user)
    
    # KYC Status: ALL KYC fields must be approved AND profile must be complete
    if user.aadhaar_verified and user.pan_verified and user.document_verified:
        if profile_status["is_complete"]:
            user.kyc_status = 'Approved'
        else:
            # Fields verified but profile incomplete - cannot approve
            user.kyc_status = 'Pending'
    elif not user.aadhaar_verified and not user.pan_verified and not user.document_verified:
        user.kyc_status = 'Pending'
    else:
        # Some approved, some not = Partially Approved (show as Pending)
        user.kyc_status = 'Pending'
    
    # Bank Status: ALL Bank fields must be approved AND profile must be complete
    if (user.account_holder_verified and user.account_number_verified and 
        user.ifsc_verified and user.bank_name_verified and user.branch_verified):
        if profile_status["is_complete"]:
            user.bank_details_status = 'Approved'
        else:
            # Fields verified but profile incomplete - cannot approve
            user.bank_details_status = 'Pending'
    elif (not user.account_holder_verified and not user.account_number_verified and 
          not user.ifsc_verified and not user.bank_name_verified and not user.branch_verified):
        user.bank_details_status = 'Pending'
    else:
        # Some approved, some not = Partially Approved (show as Pending)
        user.bank_details_status = 'Pending'
    
    # REAL-TIME WALLET SYNC: Trigger immediate sync if status just changed to 'Approved'
    if db is not None:
        kyc_newly_approved = (previous_kyc_status != 'Approved' and user.kyc_status == 'Approved')
        bank_newly_approved = (previous_bank_status != 'Approved' and user.bank_details_status == 'Approved')
        
        if kyc_newly_approved or bank_newly_approved:
            # Both KYC and Bank must be approved for wallet sync
            if user.kyc_status == 'Approved' and user.bank_details_status == 'Approved':
                # Trigger real-time wallet sync
                from app.services.wallet_sync_service import WalletSyncService
                from app.services.wallet_balance_service import get_earning_wallet
                from decimal import Decimal
                
                wallet_service = WalletSyncService(db)
                # DC Protocol Phase 1.6: Get earning balance from materialized view (computed value)
                earning_balance = get_earning_wallet(db, str(user.id))
                
                # Only sync if user has minimum balance (₹1,000)
                if earning_balance >= wallet_service.MINIMUM_TRANSFER_AMOUNT:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"🔥 REAL-TIME WALLET SYNC triggered for {user.id} - Earning wallet: ₹{earning_balance}")
                    
                    sync_result = wallet_service.sync_user_wallet_realtime(user)
                    
                    if sync_result['status'] == 'transferred':
                        logger.warning(f"✅ REAL-TIME SYNC SUCCESS: {user.id} - Transferred ₹{sync_result['amount']} to withdrawable wallet")
                    else:
                        logger.warning(f"⚠️ REAL-TIME SYNC RESULT: {user.id} - Status: {sync_result['status']}, Reason: {sync_result.get('reason', 'N/A')}")

# ===== PASSWORD RESET =====

class PasswordResetRequest(BaseModel):
    new_password: str

@router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    reset_data: PasswordResetRequest,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Admin reset user password"""
    try:
        from app.core.security import SecurityManager
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        new_hash = SecurityManager.get_password_hash(reset_data.new_password)
        user.password = new_hash
        user.force_password_change = True
        
        db.commit()
        db.refresh(user)
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='PASSWORD_RESET',
            resource_type='User',
            resource_id=user_id,
            details={"reset_by": str(current_user.id)}
        )
        
        return success_response(
            message="Password reset successfully",
            data={"user_id": user_id, "force_password_change": True}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== TEMPORARY PASSWORD (DC Protocol Feb 2026) =====

@router.post("/admin/users/{user_id}/generate-temp-password")
async def generate_temp_password(
    user_id: str,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Generate temporary password for a user.
    Sets 'Mnr@123' as temp password valid for 1 hour.
    During this period BOTH the user's original password AND the temp password work.
    Original password is NOT modified.
    """
    try:
        from app.core.security import SecurityManager
        from datetime import datetime, timedelta
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        temp_pwd = "Mnr@123"
        user.temp_password = SecurityManager.get_password_hash(temp_pwd)
        user.temp_password_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='TEMP_PASSWORD_GENERATED',
            resource_type='User',
            resource_id=user_id,
            details={
                "generated_by": str(current_user.id),
                "expires_at": user.temp_password_expires_at.isoformat()
            }
        )
        
        return success_response(
            message="Temporary password generated successfully",
            data={
                "user_id": user_id,
                "temp_password": temp_pwd,
                "expires_at": user.temp_password_expires_at.isoformat(),
                "duration": "1 hour",
                "note": "Both original and temporary passwords will work during this period"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== USER ACTIVATION/DEACTIVATION =====

@router.post("/admin/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Activate a user account"""
    try:
        from app.services.user_service import UserService
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # DC Protocol (Dec 22, 2025): Validate mobile uniqueness before activation
        user_service = UserService(db)
        mobile_check = user_service.ensure_unique_active_mobile(user.phone_number, user_id)
        if not mobile_check.get("success"):
            return {
                "success": False,
                "message": mobile_check.get("error", "Mobile number validation failed"),
                "requires_mobile_update": True
            }
        
        user.account_status = 'Active'
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='USER_ACTIVATED',
            resource_type='User',
            resource_id=user_id,
            details={"activated_by": str(current_user.id)}
        )
        
        return success_response(
            message=f"User {user_id} activated successfully",
            data={"user_id": user_id, "status": "Active"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Deactivate a user account"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.account_status = 'Inactive'
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='USER_DEACTIVATED',
            resource_type='User',
            resource_id=user_id,
            details={"deactivated_by": str(current_user.id)}
        )
        
        return success_response(
            message=f"User {user_id} deactivated successfully",
            data={"user_id": user_id, "status": "Inactive"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== REPORTS & EXPORTS =====

@router.get("/admin/reports/transactions")
async def get_transaction_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    transaction_type: Optional[str] = None,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Generate transaction report"""
    try:
        query = db.query(Transaction)
        
        if start_date and end_date:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            query = query.filter(Transaction.timestamp.between(start, end))
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        transactions = query.order_by(Transaction.timestamp.desc()).limit(1000).all()
        
        report_data = []
        total_amount = 0
        
        for txn in transactions:
            user = db.query(User).filter(User.id == txn.referred_user_id).first()
            amount = float(txn.amount or 0)
            total_amount += amount
            
            report_data.append({
                "transaction_id": str(txn.id),
                "user_id": str(txn.referred_user_id),
                "user_name": user.name if user else "Unknown",
                "transaction_type": txn.transaction_type,
                "amount": amount,
                "timestamp": txn.timestamp.isoformat(),
                "description": txn.description or ""
            })
        
        return success_response(
            message="Transaction report generated successfully",
            data={
                "transactions": report_data,
                "total_transactions": len(report_data),
                "total_amount": total_amount,
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "transaction_type": transaction_type
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/reports/earnings-summary")
async def get_earnings_summary_report(
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Generate earnings summary report"""
    try:
        # Get today's date range
        today = get_indian_time().date()
        month_start = today.replace(day=1)
        
        # Calculate earnings by type
        earnings_summary = {}
        
        for earning_type in ['Direct Referral', 'Matching Referral', 'Ved', 'Guru Dakshina', 'Field Allowance']:
            today_amount = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.transaction_type == earning_type,
                    func.date(Transaction.timestamp) == today
                )
            ).scalar() or 0
            
            month_amount = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.transaction_type == earning_type,
                    Transaction.timestamp >= month_start
                )
            ).scalar() or 0
            
            earnings_summary[earning_type] = {
                "today": float(today_amount),
                "this_month": float(month_amount)
            }
        
        # Get top earners this month
        top_earners = db.query(
            Transaction.referred_user_id,
            func.sum(Transaction.amount).label('total_earnings')
        ).filter(
            and_(
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved', 
                    'Guru Dakshina', 'Field Allowance'
                ]),
                Transaction.timestamp >= month_start
            )
        ).group_by(Transaction.referred_user_id).order_by(desc('total_earnings')).limit(10).all()
        
        top_earners_list = []
        for user_id, total in top_earners:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                top_earners_list.append({
                    "user_id": str(user_id),
                    "name": user.name,
                    "total_earnings": float(total)
                })
        
        return success_response(
            message="Earnings summary report generated successfully",
            data={
                "earnings_by_type": earnings_summary,
                "top_earners": top_earners_list
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/admin/reports/user-export")
async def export_users(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """
    Export users data
    RESTRICTED: Finance Admin, Super Admin, RVZ ID ONLY
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Export functionality is restricted to Finance Admin, Super Admin, and RVZ ID only"
    #     )
    
    try:
        query = db.query(User)
        
        if status_filter:
            query = query.filter(User.account_status == status_filter)
        
        users = query.limit(10000).all()
        
        export_data = [
            {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "status": user.account_status,
                "user_type": user.user_type,
                "coupon_status": user.coupon_status,
                "coupon_type": user.coupon_type,
                "wallet_balance": float(user.wallet_balance or 0),
                "kyc_status": user.kyc_status,
                "referrer_id": user.referrer_id,
                "created_at": user.registration_date.isoformat() if user.registration_date else None
            }
            for user in users
        ]
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='USER_DATA_EXPORT',
            resource_type='User',
            details={"total_users": len(export_data), "status_filter": status_filter}
        )
        
        return success_response(
            message="User data exported successfully",
            data={
                "users": export_data,
                "total": len(export_data),
                "export_date": get_indian_time().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== BULK OPERATIONS =====

class BulkStatusUpdate(BaseModel):
    user_ids: List[str]
    new_status: str
    reason: Optional[str] = None

@router.post("/admin/bulk/update-status")
async def bulk_update_status(
    update_data: BulkStatusUpdate,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Bulk update user status"""
    try:
        updated_count = 0
        
        for user_id in update_data.user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.account_status = update_data.new_status
                updated_count += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='BULK_STATUS_UPDATE',
            resource_type='User',
            details={
                "user_ids": update_data.user_ids,
                "new_status": update_data.new_status,
                "updated_count": updated_count,
                "reason": update_data.reason
            }
        )
        
        return success_response(
            message=f"Successfully updated {updated_count} users",
            data={"updated_count": updated_count, "total_requested": len(update_data.user_ids)}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== AWARD MANAGEMENT =====

@router.get("/admin/awards/overview")
async def get_awards_overview(
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get awards system overview"""
    try:
        from app.services.award_service import AwardService
        
        award_service = AwardService(db)
        overview = award_service.get_system_overview()
        
        return success_response(
            message="Awards overview retrieved successfully",
            data=overview
        )
        
    except Exception as e:
        return success_response(
            message="Awards system in development",
            data={"awards": []}
        )

@router.get("/admin/dashboard-stats")
async def get_admin_dashboard_stats(
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard statistics for Admin panel"""
    try:
        today = get_indian_time().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        month_start = today.replace(day=1)
        
        # User Statistics
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.account_status == 'Active').scalar() or 0
        inactive_users = db.query(func.count(User.id)).filter(User.account_status == 'Inactive').scalar() or 0
        users_today = db.query(func.count(User.id)).filter(
            and_(User.registration_date >= today_start, User.registration_date <= today_end)
        ).scalar() or 0
        users_this_month = db.query(func.count(User.id)).filter(
            User.registration_date >= month_start
        ).scalar() or 0
        
        # NO FINANCIAL DATA FOR ADMIN - Following DC Protocol
        # Admin dashboards show ONLY user statistics, no revenue/income data
        
        # KYC Statistics
        total_kyc = db.query(func.count(KYCDocument.id)).scalar() or 0
        pending_kyc = db.query(func.count(KYCDocument.id)).filter(KYCDocument.status == 'Pending').scalar() or 0
        approved_kyc = db.query(func.count(KYCDocument.id)).filter(KYCDocument.status == 'Approved').scalar() or 0
        rejected_kyc = db.query(func.count(KYCDocument.id)).filter(KYCDocument.status == 'Rejected').scalar() or 0
        kyc_today = db.query(func.count(KYCDocument.id)).filter(
            and_(KYCDocument.uploaded_at >= today_start, KYCDocument.uploaded_at <= today_end)
        ).scalar() or 0
        kyc_this_month = db.query(func.count(KYCDocument.id)).filter(
            KYCDocument.uploaded_at >= month_start
        ).scalar() or 0
        
        # NO WITHDRAWAL DATA FOR ADMIN - Following DC Protocol
        
        # Awards Pending Admin Approval (First Stage)
        from app.models.awards import UserAwardProgress
        from app.models.bonanza import DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
        awards_pending_admin = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.is_(None),
                UserAwardProgress.achieved_at.isnot(None)
            )
        ).scalar() or 0
        # DC Protocol: Query bonanza claims from DynamicBonanzaHistory
        bonanza_pending_admin = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.is_(None),
                DynamicBonanzaHistory.claimed_at.isnot(None)
            )
        ).scalar() or 0
        
        # Ticket Statistics
        total_tickets = db.query(func.count(ServiceTicket.id)).scalar() or 0
        open_tickets = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.status == 'Open').scalar() or 0
        in_progress_tickets = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.status == 'In Progress').scalar() or 0
        closed_tickets = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.status == 'Resolved').scalar() or 0
        tickets_today = db.query(func.count(ServiceTicket.id)).filter(
            and_(ServiceTicket.created_date >= today_start, ServiceTicket.created_date <= today_end)
        ).scalar() or 0
        tickets_this_month = db.query(func.count(ServiceTicket.id)).filter(
            ServiceTicket.created_date >= month_start
        ).scalar() or 0
        
        # Recent Activity - DC Protocol: Single source of truth from User table
        from sqlalchemy.orm import aliased
        Referrer = aliased(User)
        recent_users = db.query(User, Referrer.id.label('referrer_id'), Referrer.name.label('referrer_name')).outerjoin(
            Referrer, User.referrer_id == Referrer.id
        ).order_by(desc(User.registration_date)).limit(5).all()
        recent_kyc = db.query(KYCDocument).order_by(desc(KYCDocument.uploaded_at)).limit(5).all()
        recent_tickets = db.query(ServiceTicket).order_by(desc(ServiceTicket.created_date)).limit(5).all()
        
        dashboard_data = {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users,
                "today": users_today,
                "this_month": users_this_month
            },
            "user_stats": {
                "all_time": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": inactive_users
                },
                "today": {
                    "total_users": users_today,
                    "active_users": users_today
                },
                "this_month": {
                    "total_users": users_this_month,
                    "active_users": users_this_month
                }
            },
            "kyc_stats": {
                "total": total_kyc,
                "pending": pending_kyc,
                "approved": approved_kyc,
                "rejected": rejected_kyc
            },
            "kyc": {
                "total": total_kyc,
                "pending": pending_kyc,
                "approved": approved_kyc,
                "rejected": rejected_kyc,
                "today": kyc_today,
                "this_month": kyc_this_month
            },
            "awards": {
                "pending_admin_approval": awards_pending_admin + bonanza_pending_admin,
                "awards_pending": awards_pending_admin,
                "bonanza_pending": bonanza_pending_admin
            },
            "tickets": {
                "total": total_tickets,
                "open": open_tickets,
                "in_progress": in_progress_tickets,
                "closed": closed_tickets,
                "today": tickets_today,
                "this_month": tickets_this_month
            },
            "recent_activity": {
                "users": [
                    {
                        "id": u[0].id, 
                        "mnr_id": u[0].id, 
                        "name": u[0].name, 
                        "created_at": u[0].registration_date.isoformat() if u[0].registration_date else None,
                        "referrer_id": u[1] or "-",
                        "referrer_name": u[2] or "-"
                    }
                    for u in recent_users
                ],
                "kyc": [
                    {"id": k.id, "user_id": k.owner_id, "status": k.status, "created_at": k.uploaded_at.isoformat()}
                    for k in recent_kyc
                ],
                "tickets": [
                    {"id": t.id, "ticket_id": t.ticket_id, "subject": t.issue_category, "status": t.status, "created_at": t.created_date.isoformat()}
                    for t in recent_tickets
                ]
            }
        }
        
        return success_response(
            message="Admin dashboard statistics retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        # Log error server-side only (security: never expose traces to clients)
        print(f"❌ Dashboard Stats Error: {str(e)}")
        print(f"❌ Full Traceback:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard statistics. Please contact support if the issue persists."
        )

# ===== MANUAL INCOME CALCULATION (WV PROTOCOL) =====

class ManualIncomeCalculationRequest(BaseModel):
    target_date: str  # Format: "YYYY-MM-DD"

@router.post("/admin/manual-income-calculation")
async def trigger_manual_income_calculation(
    request: ManualIncomeCalculationRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Manually trigger income calculation for a specific date
    
    WV PROTOCOL: Deductions applied at income calculation stage ONLY
    DC PROTOCOL: Database is source of truth for all financial data
    
    Use Cases:
    - Recalculate missed income from system downtime
    - Fix income calculation errors for specific dates
    - Backfill historical data
    
    Security: Super Admin only (financial operation)
    """
    try:
        from datetime import date, datetime
        from app.core.scheduler import calculate_incomes_for_date_manual
        
        # Parse and validate date
        try:
            target_date = datetime.strptime(request.target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-01)"
            )
        
        # Validate date is not in future
        if target_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot calculate income for future dates"
            )
        
        # Trigger income calculation for specified date
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"🔧 MANUAL INCOME CALCULATION triggered by {current_user.id} for date: {target_date}")
        
        result = calculate_incomes_for_date_manual(target_date, triggered_by=current_user.id)
        
        # Log audit trail
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='MANUAL_INCOME_CALCULATION',
            resource_type='System',
            resource_id=str(target_date),
            details={
                "target_date": str(target_date),
                "total_incomes_created": result.get('total_incomes_created', 0),
                "total_users_affected": result.get('total_users_affected', 0),
                "status": result.get('status', 'unknown')
            }
        )
        
        return success_response(
            message=f"Income calculation completed for {target_date}",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Manual income calculation failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Income calculation failed: {str(e)}"
        )
