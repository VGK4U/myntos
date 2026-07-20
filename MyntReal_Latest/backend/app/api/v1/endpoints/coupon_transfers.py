"""
Coupon Transfer API endpoints
Handles user-to-user and admin coupon transfers with approval workflows
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.rbac import require_user, require_admin, require_super_admin
from app.models.user import User
from app.models.coupon import Coupon, EnhancedCoupon
from app.models.coupon_transfer import CouponTransfer
from app.models.api_response import success_response, error_response
from pydantic import BaseModel

router = APIRouter()

# ==================== Pydantic Schemas ====================

class UserToUserTransferRequest(BaseModel):
    to_user_id: str
    coupon_id: Optional[int] = None
    enhanced_coupon_id: Optional[int] = None
    transfer_reason: Optional[str] = None

class AdminTransferRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    coupon_id: Optional[int] = None
    enhanced_coupon_id: Optional[int] = None
    transfer_reason: Optional[str] = None
    admin_notes: Optional[str] = None

class TransferApprovalRequest(BaseModel):
    transfer_id: int
    action: str  # 'approve' or 'reject'
    notes: Optional[str] = None

# ==================== Helper Functions ====================

def get_user_available_coupons(db: Session, user_id: str):
    """Get list of unused coupons owned by a user"""
    # Legacy coupons - check for both 'Active' and 'Unused' status
    legacy_coupons = db.query(Coupon).filter(
        Coupon.owner_id == user_id,
        or_(Coupon.status == 'Active', Coupon.status == 'Unused')
    ).all()
    
    # Enhanced coupons - disabled as table doesn't exist in current schema
    enhanced_coupons = []
    
    return {
        'legacy': legacy_coupons,
        'enhanced': enhanced_coupons
    }

def validate_transfer_eligibility(db: Session, from_user_id: str, to_user_id: str):
    """Validate that both users exist and are active"""
    from_user = db.query(User).filter(User.id == from_user_id).first()
    to_user = db.query(User).filter(User.id == to_user_id).first()
    
    if not from_user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Source user {from_user_id} not found"
        )
    
    if not to_user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Destination user {to_user_id} not found"
        )
    
    # Check if users are active
    if from_user.account_status != 'Active':
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Source user {from_user_id} is not active"
        )
    
    if to_user.account_status != 'Active':
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Destination user {to_user_id} is not active"
        )
    
    return from_user, to_user

# ==================== User Endpoints ====================

@router.get("/my-available-coupons")
async def get_my_available_coupons(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get list of coupons available for transfer by current user"""
    try:
        coupons = get_user_available_coupons(db, str(current_user.id))
        
        legacy_list = [
            {
                "id": c.id,
                "type": "legacy",
                "package_type": c.coupon_type,
                "status": c.status
            }
            for c in coupons['legacy']
        ]
        
        enhanced_list = [
            {
                "id": c.id,
                "type": "enhanced",
                "package_tier": c.package_tier,
                "package_value": float(c.package_value),
                "coupon_code": c.coupon_code,
                "status": c.status
            }
            for c in coupons['enhanced']
        ]
        
        return success_response(
            message=f"Found {len(legacy_list) + len(enhanced_list)} available coupons",
            data={
                "legacy_coupons": legacy_list,
                "enhanced_coupons": enhanced_list
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/user-to-user")
async def transfer_coupon_user_to_user(
    request_data: UserToUserTransferRequest = Body(...),
    request: Request = None,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    User-to-user coupon transfer (INSTANT - No approval required)
    Active users can transfer their unused coupons to other active users
    """
    try:
        # Validate users
        from_user, to_user = validate_transfer_eligibility(
            db, str(current_user.id), request_data.to_user_id
        )
        
        # Check if coupon exists and belongs to sender
        coupon = None
        package_type = None
        
        if request_data.coupon_id:
            coupon = db.query(Coupon).filter(
                Coupon.id == request_data.coupon_id,
                Coupon.owner_id == str(current_user.id),
                or_(Coupon.status == 'Active', Coupon.status == 'Unused')
            ).first()
            
            if not coupon:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Coupon not found or not available for transfer"
                )
            package_type = coupon.coupon_type
        
        elif request_data.enhanced_coupon_id:
            coupon = db.query(EnhancedCoupon).filter(
                EnhancedCoupon.id == request_data.enhanced_coupon_id,
                EnhancedCoupon.user_id == str(current_user.id),
                EnhancedCoupon.status == 'Issued'
            ).first()
            
            if not coupon:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Enhanced coupon not found or not available for transfer"
                )
            package_type = coupon.package_tier
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Either coupon_id or enhanced_coupon_id must be provided"
            )
        
        # Create transfer record
        transfer = CouponTransfer(
            from_user_id=str(current_user.id),
            to_user_id=request_data.to_user_id,
            coupon_id=request_data.coupon_id,
            enhanced_coupon_id=request_data.enhanced_coupon_id,
            package_type=package_type,
            transfer_type='user_to_user',
            initiated_by_id=str(current_user.id),
            status='Completed',  # Instant completion for user-to-user
            requires_approval=False,
            transfer_reason=request_data.transfer_reason,
            completed_at=datetime.now(),
            ip_address=request.client.host if request.client else None
        )
        
        db.add(transfer)
        
        # Update coupon ownership
        if request_data.coupon_id:
            coupon.owner_id = request_data.to_user_id
            coupon.status = 'Active'  # Keep as Active for new owner
        else:
            coupon.user_id = request_data.to_user_id
            coupon.status = 'Issued'
            coupon.transferred_from_id = str(current_user.id)
            coupon.transfer_date = datetime.now()
            coupon.transfer_reason = request_data.transfer_reason
        
        db.commit()
        db.refresh(transfer)
        
        return success_response(
            message=f"Coupon transferred successfully to {to_user.name}",
            data={
                "transfer_id": transfer.id,
                "from_user": f"{from_user.name} ({from_user.id})",
                "to_user": f"{to_user.name} ({to_user.id})",
                "package_type": package_type,
                "status": transfer.status,
                "completed_at": transfer.completed_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer failed: {str(e)}"
        )

@router.get("/my-transfer-history")
async def get_my_transfer_history(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get transfer history for current user (sent and received)"""
    try:
        transfers = db.query(CouponTransfer).filter(
            or_(
                CouponTransfer.from_user_id == str(current_user.id),
                CouponTransfer.to_user_id == str(current_user.id)
            )
        ).order_by(CouponTransfer.transfer_date.desc()).all()
        
        transfer_list = []
        for t in transfers:
            from_user = db.query(User).filter(User.id == t.from_user_id).first()
            to_user = db.query(User).filter(User.id == t.to_user_id).first()
            
            transfer_list.append({
                "id": t.id,
                "from_user_id": t.from_user_id,
                "from_user_name": from_user.name if from_user else "Unknown",
                "to_user_id": t.to_user_id,
                "to_user_name": to_user.name if to_user else "Unknown",
                "package_type": t.package_type,
                "transfer_type": t.transfer_type,
                "status": t.status,
                "transfer_date": t.transfer_date.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "transfer_reason": t.transfer_reason,
                "direction": "sent" if t.from_user_id == str(current_user.id) else "received"
            })
        
        return success_response(
            message=f"Found {len(transfer_list)} transfers",
            data={"transfers": transfer_list}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ==================== Admin Endpoints ====================

@router.get("/admin/user-coupons/{user_id}")
async def get_user_coupons_for_admin(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to get available coupons for any user
    Allows admins to see which coupons a user has available for transfer
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        coupons = get_user_available_coupons(db, user_id)
        
        legacy_list = [
            {
                "id": c.id,
                "type": "legacy",
                "package_type": c.coupon_type,
                "status": c.status
            }
            for c in coupons['legacy']
        ]
        
        enhanced_list = [
            {
                "id": c.id,
                "type": "enhanced",
                "package_tier": c.package_tier,
                "package_value": float(c.package_value),
                "coupon_code": c.coupon_code,
                "status": c.status
            }
            for c in coupons['enhanced']
        ]
        
        return success_response(
            message=f"Found {len(legacy_list) + len(enhanced_list)} available coupons for user {user.name}",
            data={
                "user_id": user_id,
                "user_name": user.name,
                "legacy_coupons": legacy_list,
                "enhanced_coupons": enhanced_list
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/admin-transfer")
async def admin_initiated_transfer(
    request_data: AdminTransferRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin-initiated coupon transfer
    Requires Super Admin approval before completion
    """
    try:
        # Validate users
        from_user, to_user = validate_transfer_eligibility(
            db, request_data.from_user_id, request_data.to_user_id
        )
        
        # Check if coupon exists
        coupon = None
        package_type = None
        
        if request_data.coupon_id:
            coupon = db.query(Coupon).filter(
                Coupon.id == request_data.coupon_id,
                Coupon.owner_id == request_data.from_user_id,
                Coupon.status == 'Unused'
            ).first()
            
            if not coupon:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Coupon not found or not available for transfer"
                )
            package_type = coupon.coupon_type
        
        elif request_data.enhanced_coupon_id:
            coupon = db.query(EnhancedCoupon).filter(
                EnhancedCoupon.id == request_data.enhanced_coupon_id,
                EnhancedCoupon.user_id == request_data.from_user_id,
                EnhancedCoupon.status == 'Issued'
            ).first()
            
            if not coupon:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Enhanced coupon not found or not available for transfer"
                )
            package_type = coupon.package_tier
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Either coupon_id or enhanced_coupon_id must be provided"
            )
        
        # Create transfer record (PENDING Super Admin approval)
        transfer = CouponTransfer(
            from_user_id=request_data.from_user_id,
            to_user_id=request_data.to_user_id,
            coupon_id=request_data.coupon_id,
            enhanced_coupon_id=request_data.enhanced_coupon_id,
            package_type=package_type,
            transfer_type='admin_transfer',
            initiated_by_id=str(current_user.id),
            status='Pending',  # Requires Super Admin approval
            requires_approval=True,
            transfer_reason=request_data.transfer_reason,
            admin_notes=request_data.admin_notes,
            ip_address=request.client.host if request.client else None
        )
        
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        
        return success_response(
            message=f"Transfer request created. Pending Super Admin approval.",
            data={
                "transfer_id": transfer.id,
                "from_user": f"{from_user.name} ({from_user.id})",
                "to_user": f"{to_user.name} ({to_user.id})",
                "package_type": package_type,
                "status": transfer.status,
                "requires_approval": True,
                "initiated_by": f"{current_user.name} ({current_user.id})"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer request creation failed: {str(e)}"
        )

@router.get("/all-transfers")
async def get_all_transfers(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all coupon transfers (Admin view)"""
    try:
        query = db.query(CouponTransfer)
        
        if status_filter:
            query = query.filter(CouponTransfer.status == status_filter)
        
        transfers = query.order_by(CouponTransfer.transfer_date.desc()).all()
        
        transfer_list = []
        for t in transfers:
            from_user = db.query(User).filter(User.id == t.from_user_id).first()
            to_user = db.query(User).filter(User.id == t.to_user_id).first()
            initiated_by = db.query(User).filter(User.id == t.initiated_by_id).first()
            
            transfer_list.append({
                "id": t.id,
                "from_user_id": t.from_user_id,
                "from_user_name": from_user.name if from_user else "Unknown",
                "to_user_id": t.to_user_id,
                "to_user_name": to_user.name if to_user else "Unknown",
                "package_type": t.package_type,
                "transfer_type": t.transfer_type,
                "status": t.status,
                "requires_approval": t.requires_approval,
                "initiated_by": initiated_by.name if initiated_by else "Unknown",
                "transfer_date": t.transfer_date.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "transfer_reason": t.transfer_reason,
                "admin_notes": t.admin_notes
            })
        
        return success_response(
            message=f"Found {len(transfer_list)} transfers",
            data={"transfers": transfer_list}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ==================== Super Admin Endpoints ====================

@router.get("/pending-approvals")
async def get_pending_approvals(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get all pending transfer requests requiring Super Admin approval"""
    try:
        pending_transfers = db.query(CouponTransfer).filter(
            CouponTransfer.status == 'Pending',
            CouponTransfer.requires_approval == True
        ).order_by(CouponTransfer.transfer_date.asc()).all()
        
        transfer_list = []
        for t in pending_transfers:
            from_user = db.query(User).filter(User.id == t.from_user_id).first()
            to_user = db.query(User).filter(User.id == t.to_user_id).first()
            initiated_by = db.query(User).filter(User.id == t.initiated_by_id).first()
            
            transfer_list.append({
                "id": t.id,
                "from_user_id": t.from_user_id,
                "from_user_name": from_user.name if from_user else "Unknown",
                "to_user_id": t.to_user_id,
                "to_user_name": to_user.name if to_user else "Unknown",
                "package_type": t.package_type,
                "transfer_type": t.transfer_type,
                "initiated_by_id": t.initiated_by_id,
                "initiated_by_name": initiated_by.name if initiated_by else "Unknown",
                "transfer_date": t.transfer_date.isoformat(),
                "transfer_reason": t.transfer_reason,
                "admin_notes": t.admin_notes
            })
        
        return success_response(
            message=f"Found {len(transfer_list)} pending approvals",
            data={"pending_transfers": transfer_list}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/approve-reject")
async def approve_or_reject_transfer(
    approval_data: TransferApprovalRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Super Admin approves or rejects admin-initiated transfer
    On approval, the coupon ownership is transferred
    """
    try:
        # Get transfer record
        transfer = db.query(CouponTransfer).filter(
            CouponTransfer.id == approval_data.transfer_id,
            CouponTransfer.status == 'Pending'
        ).first()
        
        if not transfer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Transfer request not found or already processed"
            )
        
        if approval_data.action == 'approve':
            # Approve and execute transfer
            transfer.status = 'Completed'
            transfer.approved_by_id = str(current_user.id)
            transfer.approved_at = datetime.now()
            transfer.approval_notes = approval_data.notes
            transfer.completed_at = datetime.now()
            
            # Transfer coupon ownership
            if transfer.coupon_id:
                coupon = db.query(Coupon).filter(Coupon.id == transfer.coupon_id).first()
                if coupon:
                    coupon.owner_id = transfer.to_user_id
                    coupon.status = 'Unused'
            
            elif transfer.enhanced_coupon_id:
                coupon = db.query(EnhancedCoupon).filter(
                    EnhancedCoupon.id == transfer.enhanced_coupon_id
                ).first()
                if coupon:
                    coupon.user_id = transfer.to_user_id
                    coupon.status = 'Issued'
                    coupon.transferred_from_id = transfer.from_user_id
                    coupon.transfer_date = datetime.now()
                    coupon.transfer_reason = transfer.transfer_reason
            
            db.commit()
            
            return success_response(
                message="Transfer approved and completed successfully",
                data={
                    "transfer_id": transfer.id,
                    "status": transfer.status,
                    "approved_by": current_user.name,
                    "approved_at": transfer.approved_at.isoformat()
                }
            )
            
        elif approval_data.action == 'reject':
            # Reject transfer
            transfer.status = 'Rejected'
            transfer.rejected_by_id = str(current_user.id)
            transfer.rejected_at = datetime.now()
            transfer.rejection_reason = approval_data.notes
            
            db.commit()
            
            return success_response(
                message="Transfer rejected",
                data={
                    "transfer_id": transfer.id,
                    "status": transfer.status,
                    "rejected_by": current_user.name,
                    "rejected_at": transfer.rejected_at.isoformat(),
                    "rejection_reason": transfer.rejection_reason
                }
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Must be 'approve' or 'reject'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval/Rejection failed: {str(e)}"
        )
