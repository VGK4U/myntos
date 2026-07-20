"""
Admin PIN Management endpoints for FastAPI
Real database operations for PIN purchase requests, status, and overview
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, Integer, String
from typing import Dict, Any, List, Optional, cast
from datetime import datetime, timedelta
from pydantic import BaseModel
from decimal import Decimal
import random

from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_super_admin_user, get_current_user_hybrid
from app.models.staff import StaffEmployee
from app.models.user import User
from app.models.coupon import Coupon, PINPurchaseRequest
from app.models.transaction import Transaction
from app.models.base import get_indian_time

router = APIRouter()

# Helper functions for type-safe value extraction
def safe_decimal_to_float(value: Optional[Decimal]) -> float:
    """Safely convert Decimal to float"""
    return float(value) if value is not None else 0.0

def safe_int(value: Optional[int]) -> int:
    """Safely convert to int"""
    return int(value) if value is not None else 0

def safe_str(value: Optional[str]) -> str:
    """Safely convert to str"""
    return str(value) if value is not None else ""

def generate_pin_code(package_type: str) -> str:
    """
    Generate 15-digit PIN code based on package type
    Format: 
    - Platinum (15000): 615XXXXXXXXXXXX
    - Diamond (7500): 607XXXXXXXXXXXX
    """
    # Determine prefix based on package type
    if package_type == "15000":
        prefix = "615"
    elif package_type == "7500":
        prefix = "607"
    else:
        # Fallback for other package types
        prefix = "600"
    
    # Generate 12 random digits for the remaining part
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(12)])
    
    return prefix + random_digits

class ApprovalRequest(BaseModel):
    action: str  # 'approve' or 'reject'
    notes: Optional[str] = ""
    rejection_reason: Optional[str] = ""

@router.get("/purchase-requests")
async def get_pin_purchase_requests(
    status: Optional[str] = Query(None, description="Filter by status: Pending, Approved by Admin, Approved, Rejected, All"),
    pin_type_filter: Optional[str] = Query(None, description="Filter by package type: 500, 1000, 7500, 15000"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get PIN purchase requests for admin review
    Real database query with filtering and pagination
    """
    try:
        # Build query with filters
        query = db.query(PINPurchaseRequest).join(User, PINPurchaseRequest.user_id == User.id)
        
        # Apply status filter (ignore "All")
        if status and status != 'All':
            query = query.filter(PINPurchaseRequest.status == status)
        
        if pin_type_filter:
            query = query.filter(PINPurchaseRequest.package_type == pin_type_filter)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Get requests with pagination, ordered by request date
        requests = query.order_by(desc(PINPurchaseRequest.request_date)).offset(offset).limit(limit).all()
        
        requests_data = []
        user_ids = list(set(req.user_id for req in requests))
        users_map = {}
        if user_ids:
            users_list = db.query(User).filter(User.id.in_(user_ids)).all()
            users_map = {u.id: u for u in users_list}

        staff_ids = set()
        for req in requests:
            if req.superadmin_approved_by:
                staff_ids.add(req.superadmin_approved_by)
            if req.finance_validated_by:
                staff_ids.add(req.finance_validated_by)
            if req.rejected_by:
                staff_ids.add(req.rejected_by)
        staff_names = {}
        if staff_ids:
            staff_list = db.query(StaffEmployee).filter(StaffEmployee.emp_code.in_(list(staff_ids))).all()
            staff_names = {s.emp_code: s.name for s in staff_list}
            mnr_list = db.query(User.id, User.name).filter(User.id.in_(list(staff_ids))).all()
            for u in mnr_list:
                if u.id not in staff_names:
                    staff_names[u.id] = u.name

        for req in requests:
            user = users_map.get(req.user_id)

            admin_notes_list = []
            if req.superadmin_notes:
                approved_by_name = staff_names.get(req.superadmin_approved_by, req.superadmin_approved_by) if req.superadmin_approved_by else 'Staff'
                admin_notes_list.append(f"Staff ({approved_by_name}): {req.superadmin_notes}")
            if req.finance_admin_notes:
                validated_by_name = staff_names.get(req.finance_validated_by, req.finance_validated_by) if req.finance_validated_by else 'Staff'
                admin_notes_list.append(f"Staff ({validated_by_name}): {req.finance_admin_notes}")
            if req.rejection_reason:
                rejected_by_name = staff_names.get(req.rejected_by, req.rejected_by) if req.rejected_by else 'Staff'
                admin_notes_list.append(f"Rejected by {rejected_by_name}: {req.rejection_reason}")

            payment_url = None
            payment_path = req.payment_screenshot_path
            if payment_path is not None:
                path_str = str(payment_path)
                if path_str:
                    if path_str.startswith('/storage/'):
                        payment_url = path_str
                    elif path_str.startswith('/'):
                        payment_url = f"/storage{path_str}"
                    else:
                        payment_url = f"/storage/{path_str}"

            approved_by_name = staff_names.get(req.superadmin_approved_by, req.superadmin_approved_by) if req.superadmin_approved_by else None
            validated_by_name = staff_names.get(req.finance_validated_by, req.finance_validated_by) if req.finance_validated_by else None
            rejected_by_name = staff_names.get(req.rejected_by, req.rejected_by) if req.rejected_by else None

            requests_data.append({
                "id": req.id,
                "user_id": req.user_id,
                "user_name": user.name if user else "Unknown",
                "user_email": user.email if user else "Unknown",
                "package_type": req.package_type,
                "quantity": req.quantity,
                "total_amount": safe_decimal_to_float(cast(Optional[Decimal], req.total_amount)),
                "transaction_id": req.transaction_id,
                "payment_proof_url": payment_url,
                "status": req.status,
                "requested_at": req.request_date.isoformat() if req.request_date is not None else None,
                "admin_notes": " | ".join(admin_notes_list) if admin_notes_list else "",
                "approved_by": approved_by_name,
                "approved_by_id": req.superadmin_approved_by,
                "approved_date": req.superadmin_approved_date.isoformat() if req.superadmin_approved_date is not None else None,
                "validated_by": validated_by_name,
                "validated_by_id": req.finance_validated_by,
                "validated_date": req.finance_validated_date.isoformat() if req.finance_validated_date is not None else None,
                "rejected_by": rejected_by_name,
                "rejected_by_id": req.rejected_by,
                "rejected_date": req.rejected_date.isoformat() if req.rejected_date is not None else None,
                "completed_date": req.completed_date.isoformat() if req.completed_date is not None else None
            })

        pending_amount_result = db.query(func.sum(PINPurchaseRequest.total_amount)).filter(PINPurchaseRequest.status == 'Pending').scalar()
        fulfilled_count = db.query(PINPurchaseRequest).filter(PINPurchaseRequest.status == 'Fulfilled').count()
        stats = {
            "total_requests": total_count,
            "pending_count": db.query(PINPurchaseRequest).filter(PINPurchaseRequest.status == 'Pending').count(),
            "approved_count": db.query(PINPurchaseRequest).filter(PINPurchaseRequest.status.in_(['Approved', 'Fulfilled'])).count(),
            "rejected_count": db.query(PINPurchaseRequest).filter(PINPurchaseRequest.status == 'Rejected').count(),
            "fulfilled_count": fulfilled_count,
            "total_pending_amount": float(pending_amount_result) if pending_amount_result else 0.0
        }
        
        return {
            "success": True,
            "data": {
                "requests": requests_data,
                "stats": stats,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_next": (offset + limit) < total_count
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch PIN requests: {str(e)}"
        )

@router.get("/purchase-requests/{request_id}")
async def get_pin_purchase_request_detail(
    request_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get single PIN purchase request details
    DC Protocol Feb 2026: Staff-only, with detailed audit trail
    """
    try:
        pin_request = db.query(PINPurchaseRequest).filter(PINPurchaseRequest.id == request_id).first()
        if not pin_request:
            raise HTTPException(status_code=404, detail="PIN request not found")
        
        user = db.query(User).filter(User.id == pin_request.user_id).first()
        
        def resolve_staff_name(staff_id):
            if not staff_id:
                return None
            staff = db.query(StaffEmployee).filter(StaffEmployee.emp_code == staff_id).first()
            if staff:
                return f"{staff.name} ({staff.emp_code})"
            mnr_user = db.query(User).filter(User.id == staff_id).first()
            if mnr_user:
                return f"{mnr_user.name} ({staff_id})"
            return staff_id

        admin_notes_list = []
        if pin_request.superadmin_notes:
            name = resolve_staff_name(pin_request.superadmin_approved_by) or 'Staff'
            admin_notes_list.append(f"Staff {name}: {pin_request.superadmin_notes}")
        if pin_request.finance_admin_notes:
            name = resolve_staff_name(pin_request.finance_validated_by) or 'Staff'
            admin_notes_list.append(f"Staff {name}: {pin_request.finance_admin_notes}")
        if pin_request.rejection_reason:
            name = resolve_staff_name(pin_request.rejected_by) or 'Staff'
            admin_notes_list.append(f"Rejected by {name}: {pin_request.rejection_reason}")

        payment_url = None
        payment_path = pin_request.payment_screenshot_path
        if payment_path is not None:
            path_str = str(payment_path)
            if path_str:
                if path_str.startswith('/storage/'):
                    payment_url = path_str
                elif path_str.startswith('/'):
                    payment_url = f"/storage{path_str}"
                else:
                    payment_url = f"/storage/{path_str}"

        audit_trail = []
        audit_trail.append({
            "action": "Requested",
            "by": f"{user.name} ({pin_request.user_id})" if user else pin_request.user_id,
            "date": pin_request.request_date.isoformat() if pin_request.request_date else None
        })
        if pin_request.superadmin_approved_by:
            audit_trail.append({
                "action": "Approved",
                "by": resolve_staff_name(pin_request.superadmin_approved_by),
                "date": pin_request.superadmin_approved_date.isoformat() if pin_request.superadmin_approved_date else None,
                "notes": pin_request.superadmin_notes
            })
        if pin_request.finance_validated_by:
            audit_trail.append({
                "action": "Validated & PINs Generated",
                "by": resolve_staff_name(pin_request.finance_validated_by),
                "date": pin_request.finance_validated_date.isoformat() if pin_request.finance_validated_date else None,
                "notes": pin_request.finance_admin_notes
            })
        if pin_request.completed_date:
            audit_trail.append({
                "action": "Completed",
                "by": "System",
                "date": pin_request.completed_date.isoformat()
            })
        if pin_request.rejected_by:
            audit_trail.append({
                "action": "Rejected",
                "by": resolve_staff_name(pin_request.rejected_by),
                "date": pin_request.rejected_date.isoformat() if pin_request.rejected_date else None,
                "notes": pin_request.rejection_reason
            })

        can_approve = pin_request.status in ('Pending', 'Approved by Admin')

        request_data = {
            "id": pin_request.id,
            "user_id": pin_request.user_id,
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "Unknown",
            "package_type": pin_request.package_type,
            "quantity": pin_request.quantity,
            "total_amount": safe_decimal_to_float(cast(Optional[Decimal], pin_request.total_amount)),
            "transaction_id": pin_request.transaction_id,
            "payment_proof_url": payment_url,
            "status": pin_request.status,
            "requested_at": pin_request.request_date.isoformat() if pin_request.request_date is not None else None,
            "admin_notes": " | ".join(admin_notes_list) if admin_notes_list else "",
            "can_approve": can_approve,
            "audit_trail": audit_trail
        }
        
        return {
            "success": True,
            "data": {
                "request": request_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch PIN request: {str(e)}"
        )

@router.post("/purchase-requests/{request_id}/approve-admin")
async def staff_approve_pin_request(
    request_id: int,
    approval_data: ApprovalRequest,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol Feb 2026: Staff-only single-step PIN approval.
    Any Staff with page access can approve/reject and generate PINs directly.
    """
    try:
        pin_request = db.query(PINPurchaseRequest).filter(PINPurchaseRequest.id == request_id).first()
        if not pin_request:
            raise HTTPException(status_code=404, detail="PIN request not found")
        
        status_val: Optional[str] = cast(Optional[str], pin_request.status)
        if status_val in ('Fulfilled', 'Approved'):
            raise HTTPException(status_code=400, detail="Request already processed and PINs generated")
        if status_val == 'Rejected':
            raise HTTPException(status_code=400, detail="Request already rejected")
        if status_val not in ('Pending', 'Approved by Admin'):
            raise HTTPException(status_code=400, detail=f"Cannot process request with status: {status_val}")
        
        staff_id = getattr(current_user, 'emp_code', None) or str(current_user.id)
        staff_name = getattr(current_user, 'name', 'Staff')
        now = get_indian_time()
        
        if approval_data.action == 'approve':
            setattr(pin_request, 'status', 'Fulfilled')
            setattr(pin_request, 'superadmin_approved_date', now)
            setattr(pin_request, 'superadmin_approved_by', staff_id)
            setattr(pin_request, 'finance_validated_date', now)
            setattr(pin_request, 'finance_validated_by', staff_id)
            setattr(pin_request, 'completed_date', now)
            notes_text = approval_data.notes or ""
            setattr(pin_request, 'superadmin_notes', f"Staff auto-approved purchase by {staff_id} (Staff ID: {current_user.id}) via Menu Access Control. {notes_text}".strip())
            if notes_text:
                setattr(pin_request, 'finance_admin_notes', notes_text)
            
            coupons_created = []
            quantity = safe_int(cast(Optional[int], pin_request.quantity))
            package_type_str = str(pin_request.package_type)
            
            for i in range(quantity):
                pin_code = generate_pin_code(package_type_str)
                while db.query(Coupon).filter(Coupon.id == int(pin_code)).first():
                    pin_code = generate_pin_code(package_type_str)
                
                new_coupon = Coupon(
                    id=int(pin_code),
                    owner_id=pin_request.user_id,
                    coupon_type=pin_request.package_type,
                    status='Active',
                    assignment_status='Assigned',
                    assignment_status_changed_at=now
                )
                db.add(new_coupon)
                coupons_created.append(pin_code)
            
            message = f"PIN request approved by Staff {staff_name} ({staff_id}). {len(coupons_created)} PINs generated."
            
        elif approval_data.action == 'reject':
            setattr(pin_request, 'status', 'Rejected')
            setattr(pin_request, 'rejected_date', now)
            setattr(pin_request, 'rejected_by', staff_id)
            rejection_reason = approval_data.rejection_reason or approval_data.notes or "No reason provided"
            setattr(pin_request, 'rejection_reason', rejection_reason)
            
            message = f"PIN request rejected by Staff {staff_name} ({staff_id})"
            coupons_created = []
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
        db.commit()
        
        return {
            "success": True,
            "message": message,
            "data": {
                "request_id": request_id,
                "status": pin_request.status,
                "coupons_generated": len(coupons_created) if approval_data.action == 'approve' else 0,
                "processed_by": staff_name,
                "processed_by_id": staff_id,
                "processed_at": now.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PIN approval: {str(e)}"
        )

@router.post("/purchase-requests/{request_id}/approve-finance-admin")
async def staff_approve_pin_finance_compat(
    request_id: int,
    approval_data: ApprovalRequest,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """DC Protocol Feb 2026: Compatibility redirect to unified Staff approval."""
    return await staff_approve_pin_request(request_id, approval_data, current_user, db)

@router.post("/purchase-requests/{request_id}/approve-finance-direct")
async def staff_approve_pin_direct_compat(
    request_id: int,
    approval_data: ApprovalRequest,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """DC Protocol Feb 2026: Compatibility redirect to unified Staff approval."""
    return await staff_approve_pin_request(request_id, approval_data, current_user, db)

@router.get("/pins-status")
async def get_pins_status_by_user(
    search: Optional[str] = Query(None, description="Search by user name, ID, or email"),
    balance_filter: Optional[str] = Query(None, description="Filter by balance range"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get PIN status for all users with real database aggregation
    """
    try:
        # Build user query with search
        user_query = db.query(User)
        if search:
            search_term = f"%{search}%"
            user_query = user_query.filter(
                (User.name.ilike(search_term)) |
                (User.id.ilike(search_term)) |
                (User.email.ilike(search_term))
            )
        
        total_users = user_query.count()
        users = user_query.offset(offset).limit(limit).all()
        
        # Get PIN data for each user
        user_pin_data = []
        for user in users:
            # Get user's coupons by type
            coupon_stats = db.query(
                Coupon.coupon_type,
                func.count(Coupon.id).label('count')
            ).filter(
                Coupon.owner_id == user.id
            ).group_by(Coupon.coupon_type).all()
            
            # Build coupon breakdown
            pin_breakdown = {
                '500': {'purchased': 0, 'activated': 0, 'available': 0},
                '1000': {'purchased': 0, 'activated': 0, 'available': 0},
                '7500': {'purchased': 0, 'activated': 0, 'available': 0},
                '15000': {'purchased': 0, 'activated': 0, 'available': 0}
            }
            
            total_pins = 0
            total_value = 0
            
            for package_type, count in coupon_stats:
                if package_type in pin_breakdown:
                    pin_breakdown[package_type]['purchased'] = count
                    total_pins += count
                    total_value += count * int(package_type)
            
            # Get activated coupons
            activated_stats = db.query(
                Coupon.coupon_type,
                func.count(Coupon.id).label('count')
            ).filter(
                and_(
                    Coupon.owner_id == user.id,
                    Coupon.status == 'Redeemed'
                )
            ).group_by(Coupon.coupon_type).all()
            
            for package_type, count in activated_stats:
                if package_type in pin_breakdown:
                    pin_breakdown[package_type]['activated'] = count
                    pin_breakdown[package_type]['available'] = pin_breakdown[package_type]['purchased'] - count
            
            # Get last PIN activity
            last_activity = db.query(Coupon).filter(
                Coupon.owner_id == user.id
            ).order_by(desc(Coupon.created_at)).first()
            
            registration_date = user.registration_date
            user_pin_data.append({
                "user_id": user.id,
                "user_name": user.name,
                "email": user.email,
                "registration_date": registration_date.isoformat() if registration_date is not None else None,
                "total_pins_purchased": total_pins,
                "total_pins_activated": sum(pin_breakdown[pt]['activated'] for pt in pin_breakdown),
                "available_pins": sum(pin_breakdown[pt]['available'] for pt in pin_breakdown),
                "pin_breakdown": pin_breakdown,
                "total_pin_value": total_value,
                "last_pin_activity": last_activity.created_at.isoformat() if last_activity is not None else None
            })
        
        # Calculate overall statistics
        overall_stats = {
            "total_users": total_users,
            "total_pins": sum(user['total_pins_purchased'] for user in user_pin_data),
            "total_activated": sum(user['total_pins_activated'] for user in user_pin_data),
            "total_value": sum(user['total_pin_value'] for user in user_pin_data),
            "active_users": len([u for u in user_pin_data if u['available_pins'] > 0])
        }
        
        return {
            "success": True,
            "users": user_pin_data,
            "pagination": {
                "total": total_users,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_users
            },
            "statistics": overall_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch PIN status: {str(e)}"
        )

@router.get("/pins-overview")
async def get_pins_system_overview(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive PIN system overview with real analytics
    """
    try:
        # Overall PIN statistics
        total_pins = db.query(func.count(Coupon.id)).scalar() or 0
        total_activated = db.query(func.count(Coupon.id)).filter(Coupon.status == 'Redeemed').scalar() or 0
        total_available = total_pins - total_activated
        
        # Revenue calculation - use coupon_type field
        revenue_result = db.query(
            func.sum(func.cast(Coupon.coupon_type, Integer))
        ).scalar()
        total_revenue = float(revenue_result) if revenue_result else 0.0
        
        # PIN type breakdown
        pin_breakdown = {}
        package_types = ['500', '1000', '7500', '15000']
        
        for package_type in package_types:
            purchased = db.query(func.count(Coupon.id)).filter(Coupon.coupon_type == package_type).scalar() or 0
            activated = db.query(func.count(Coupon.id)).filter(
                and_(Coupon.coupon_type == package_type, Coupon.status == 'Redeemed')
            ).scalar() or 0
            
            pin_breakdown[package_type] = {
                "purchased": purchased,
                "activated": activated,
                "available": purchased - activated,
                "revenue": purchased * int(package_type)
            }
        
        # Recent activity (today's transactions)
        today = datetime.now().date()
        daily_purchases = db.query(func.count(Coupon.id)).filter(
            func.date(Coupon.created_at) == today
        ).scalar() or 0
        
        daily_activations = db.query(func.count(Coupon.id)).filter(
            and_(
                Coupon.status == 'Redeemed',
                Coupon.activated_at.isnot(None),
                func.date(Coupon.activated_at) == today
            )
        ).scalar() or 0
        
        # Get recent transactions
        recent_transactions = db.query(Coupon).order_by(desc(Coupon.created_at)).limit(10).all()
        transactions_data = []
        
        for coupon in recent_transactions:
            user = db.query(User).filter(User.id == coupon.owner_id).first()
            status_val: Optional[str] = cast(Optional[str], coupon.status)
            transaction_type = 'activation' if status_val == 'Redeemed' else 'purchase'
            
            coupon_type_str: Optional[str] = cast(Optional[str], coupon.coupon_type)
            amount_value = None
            if coupon_type_str and transaction_type == 'purchase':
                try:
                    amount_value = float(coupon_type_str)
                except (ValueError, TypeError):
                    amount_value = None
            
            transactions_data.append({
                "id": str(coupon.id),
                "type": transaction_type,
                "user_id": coupon.owner_id,
                "user_name": user.name if user else "Unknown",
                "pin_type": coupon_type_str,
                "quantity": 1,
                "amount": amount_value,
                "timestamp": coupon.created_at.isoformat()
            })
        
        # Top users by PIN count
        top_users = db.query(
            User.id,
            User.name,
            func.count(Coupon.id).label('pin_count')
        ).join(Coupon, User.id == Coupon.owner_id).group_by(
            User.id, User.name
        ).order_by(desc('pin_count')).limit(5).all()
        
        top_users_data = [
            {
                "user_id": user.id,
                "user_name": user.name,
                "total_pins": user.pin_count,
                "total_value": 0
            }
            for user in top_users
        ]
        
        return {
            "success": True,
            "overview": {
                "total_pins_purchased": total_pins,
                "total_pins_activated": total_activated,
                "total_pins_available": total_available,
                "total_revenue": float(total_revenue),
                "pin_type_breakdown": pin_breakdown,
                "recent_activity": {
                    "daily_purchases": daily_purchases,
                    "daily_activations": daily_activations,
                    "daily_transfers": 0
                },
                "top_users": top_users_data,
                "recent_transactions": transactions_data,
                "generated_at": get_indian_time().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch PIN overview: {str(e)}"
        )

@router.get("/unused-coupons")
async def get_unused_coupons(
    search: Optional[str] = Query(None, description="Search coupon code"),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get list of unused coupons for assignment
    """
    try:
        query = db.query(Coupon).filter(
            Coupon.status == 'Active'
        )
        
        if search:
            query = query.filter(Coupon.id.like(f'%{search}%'))
        
        coupons = query.order_by(Coupon.id).limit(limit).all()
        
        coupons_data = []
        for c in coupons:
            coupon_type_str: Optional[str] = cast(Optional[str], c.coupon_type)
            amount_val = 0.0
            if coupon_type_str:
                try:
                    amount_val = float(coupon_type_str)
                except (ValueError, TypeError):
                    amount_val = 0.0
            
            coupons_data.append({
                "id": str(c.id),
                "coupon_code": str(c.id),
                "coupon_type": coupon_type_str,
                "amount": amount_val,
                "created_at": c.created_at.isoformat() if c.created_at else None
            })
        
        return {
            "success": True,
            "coupons": coupons_data,
            "total": len(coupons_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unused coupons: {str(e)}"
        )

@router.get("/search-users")
async def search_users_for_assignment(
    search: str = Query(..., description="Search by name, email, or MNR ID"),
    limit: int = Query(20, ge=1, le=50),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search users for coupon assignment
    """
    try:
        query = db.query(User).filter(
            and_(
                User.account_status == 'Active',
                func.or_(
                    User.name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.id.ilike(f'%{search}%')
                )
            )
        )
        
        users = query.order_by(User.name).limit(limit).all()
        
        users_data = [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "phone_number": u.phone_number
            }
            for u in users
        ]
        
        return {
            "success": True,
            "users": users_data,
            "total": len(users_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search users: {str(e)}"
        )

@router.post("/assign-coupon")
async def assign_coupon_to_user(
    coupon_code: str,
    user_id: str,
    notes: Optional[str] = "",
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Assign coupon to user (Admin/Super Admin only)
    """
    try:
        # Get coupon by ID
        try:
            coupon_id = int(coupon_code)
            coupon = db.query(Coupon).filter(
                and_(
                    Coupon.id == coupon_id,
                    Coupon.status == 'Active'
                )
            ).first()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid coupon code")
        
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found or already used")
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Assign coupon using setattr for SQLAlchemy
        setattr(coupon, 'owner_id', user_id)
        setattr(coupon, 'status', 'Active')
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Coupon {coupon_code} assigned to {user.name} successfully",
            "data": {
                "coupon_code": coupon_code,
                "user_id": user_id,
                "user_name": user.name,
                "coupon_type": coupon.coupon_type,
                "assigned_at": get_indian_time().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign coupon: {str(e)}"
        )

# ===== STAR / LOYAL COUPON ASSIGNMENT (Admin & Super Admin) =====

class StarLoyalPurchaseRequest(BaseModel):
    package_type: str  # '1000' (Star/Blue) or '500' (Loyal)
    target_user_id: str
    quantity: int = 1
    payment_method: str
    transaction_id: str
    payment_details: str

@router.post("/star-loyal/purchase-request")
async def admin_request_star_loyal_purchase(
    request_data: StarLoyalPurchaseRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin/Super Admin can purchase Star (₹1,000) or Loyal (₹500) coupons for users
    Requires Finance Admin approval workflow
    RESTRICTED: Admin and Super Admin only (not regular users)
    """
    try:
        from app.core.audit import AuditLogger
        from decimal import Decimal
        
        # Validate package type (only Star/Loyal allowed)
        if request_data.package_type not in ['1000', '500']:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid package type. Only Star (1000) and Loyal (500) allowed."
            )
        
        # Validate target user exists
        target_user = db.query(User).filter(User.id == request_data.target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Target user {request_data.target_user_id} not found"
            )
        
        # Calculate amount
        package_cost = Decimal(request_data.package_type)
        total_amount = package_cost * request_data.quantity
        
        # Create purchase request
        new_request = PINPurchaseRequest(
            user_id=request_data.target_user_id,  # Package goes to target user
            package_type=request_data.package_type,
            package_value=int(package_cost),
            quantity=request_data.quantity,
            total_amount=total_amount,
            payment_method=request_data.payment_method,
            transaction_id=request_data.transaction_id,
            payment_amount=total_amount,
            payment_details=request_data.payment_details,
            request_date=get_indian_time(),
            status='Pending',
            superadmin_notes=f"Star/Loyal purchase by {getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')} {current_user.name} ({current_user.id})"
        )
        
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        # Log audit
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='STAR_LOYAL_PURCHASE_REQUEST',
            resource_type='PINPurchaseRequest',
            resource_id=str(new_request.id),
            details={
                "package_type": request_data.package_type,
                "target_user_id": request_data.target_user_id,
                "target_user_name": target_user.name,
                "quantity": request_data.quantity,
                "total_amount": float(total_amount),
                "requester": current_user.id
            }
        )
        
        package_name = "Star (Blue)" if request_data.package_type == '1000' else "Loyal"
        
        return {
            "success": True,
            "message": f"{package_name} coupon purchase request submitted. Awaiting Finance Admin approval.",
            "data": {
                "request_id": new_request.id,
                "package_type": request_data.package_type,
                "package_name": package_name,
                "target_user_id": request_data.target_user_id,
                "target_user_name": target_user.name,
                "quantity": request_data.quantity,
                "total_amount": float(total_amount),
                "status": "Pending",
                "created_at": new_request.request_date.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Star/Loyal purchase request: {str(e)}"
        )


@router.get("/coupons/all")
async def get_all_coupons(
    status_filter: Optional[str] = Query(None, description="Filter by status: Active, Used, Pending, All"),
    coupon_type: Optional[str] = Query(None, description="Filter by coupon type: 500, 1000, 7500, 15000"),
    owner_id: Optional[str] = Query(None, description="Filter by owner user ID"),
    used_by: Optional[str] = Query(None, description="Filter by member applied (user who used the coupon)"),
    date_from: Optional[str] = Query(None, description="Filter activated from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter activated to date (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query("id", description="Sort by field: id, owner_id, coupon_type, status, activated_at"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    search: Optional[str] = Query(None, description="Search by coupon ID or owner name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all coupons system-wide with filters and sorting
    DC Protocol Jan 2026: Comprehensive coupon status view
    """
    try:
        # Build base query with user join for owner info
        query = db.query(Coupon).outerjoin(User, Coupon.owner_id == User.id)
        
        # Apply filters
        if status_filter and status_filter != 'All':
            query = query.filter(Coupon.status == status_filter)
        
        if coupon_type:
            query = query.filter(Coupon.coupon_type == coupon_type)
        
        if owner_id:
            query = query.filter(Coupon.owner_id == owner_id)
        
        if used_by:
            # Search in assignment or activation context
            query = query.filter(Coupon.assignment_status.ilike(f"%{used_by}%"))
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Coupon.activated_at >= from_date)
            except:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Coupon.activated_at <= to_date)
            except:
                pass
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (func.cast(Coupon.id, String).ilike(search_term)) |
                (Coupon.owner_id.ilike(search_term)) |
                (User.name.ilike(search_term))
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply sorting
        sort_column = getattr(Coupon, sort_by, Coupon.id)
        if sort_order.lower() == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Apply pagination - use separate query for Coupon with User name
        coupons = query.offset(offset).limit(limit).all()
        
        # Batch fetch owner names to avoid N+1
        owner_ids = [c.owner_id for c in coupons if c.owner_id]
        owner_map = {}
        if owner_ids:
            owners = db.query(User.id, User.name).filter(User.id.in_(owner_ids)).all()
            owner_map = {o.id: o.name for o in owners}
        
        # Format response
        coupons_data = []
        for coupon in coupons:
            coupons_data.append({
                "id": coupon.id,
                "owner_id": coupon.owner_id,
                "owner_name": owner_map.get(coupon.owner_id, "N/A"),
                "coupon_type": coupon.coupon_type,
                "status": coupon.status,
                "activated_at": coupon.activated_at.isoformat() if coupon.activated_at else None,
                "assignment_status": coupon.assignment_status,
                "assignment_changed_at": coupon.assignment_status_changed_at.isoformat() if coupon.assignment_status_changed_at else None
            })
        
        # Calculate stats
        stats = {
            "total_coupons": total_count,
            "active_count": db.query(Coupon).filter(Coupon.status == 'Active').count(),
            "used_count": db.query(Coupon).filter(Coupon.status == 'Used').count(),
            "pending_count": db.query(Coupon).filter(Coupon.status == 'Pending').count()
        }
        
        return {
            "success": True,
            "data": {
                "coupons": coupons_data,
                "stats": stats,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "data": {"coupons": [], "stats": {}, "pagination": {}}
        }
