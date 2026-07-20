"""
MNR Receipt Download API
DC Protocol (Jan 2026)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.staff import StaffEmployee
from app.core.security import get_current_user, get_current_user_hybrid
from app.utils.receipt_generator import generate_membership_receipt

router = APIRouter()


@router.get("/membership-receipt")
async def download_membership_receipt(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download membership activation receipt PDF.
    Only available for activated members.
    """
    # Check if user is activated
    if current_user.coupon_status != "Activated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receipt only available for activated members"
        )
    
    # DC Protocol (Jan 2026): Welcome Coupon users cannot download/print receipts
    if getattr(current_user, 'is_welcome_coupon', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receipt download is not available for Welcome Coupon (Exception Coupon) members"
        )
    
    # Prepare receipt data
    activation_date = current_user.activation_date or current_user.created_at
    payment_date = activation_date  # Assuming payment = activation
    
    # Calculate expiry (24 months from activation)
    if activation_date:
        from dateutil.relativedelta import relativedelta
        expiry_date = activation_date + relativedelta(months=24)
        expiry_str = expiry_date.strftime('%d %B %Y')
        activation_str = activation_date.strftime('%d %B %Y')
        payment_str = payment_date.strftime('%d %B %Y') if payment_date else activation_str
    else:
        expiry_str = "24 months from activation"
        activation_str = "N/A"
        payment_str = "N/A"
    
    # Generate receipt number based on user ID (which is the MNR ID)
    user_id = str(current_user.id) if current_user.id else "UNKNOWN"
    receipt_number = f"MNR-RCP-{user_id[-6:]}"
    
    # Package amount and points - calculate based on package_points multiplier
    # DC Protocol (Feb 2026): Default 30000 points for all activated users
    # package_points is a multiplier (1.0 = Platinum = 30000 points, 0.5 = 15000 points)
    from app.constants import DEFAULT_COUPON_POINTS
    
    points = DEFAULT_COUPON_POINTS  # Default 30000
    
    # Calculate points from package_points multiplier
    if hasattr(current_user, 'package_points') and current_user.package_points:
        # package_points is a fraction/multiplier (e.g., 1.0, 0.5)
        points = int(current_user.package_points * DEFAULT_COUPON_POINTS)
    
    amount = points  # Amount = Points credited
    
    receipt_data = {
        "member_name": current_user.name or "N/A",
        "mnr_id": str(current_user.id) if current_user.id else "N/A",
        "payment_date": payment_str,
        "activation_date": activation_str,
        "amount_paid": amount,
        "points_credited": points,
        "receipt_number": receipt_number,
        "expiry_date": expiry_str
    }
    
    # Generate PDF
    pdf_buffer = generate_membership_receipt(receipt_data)
    
    # Return as downloadable PDF
    filename = f"MNR_Receipt_{current_user.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/membership-receipt/{mnr_id}")
async def download_membership_receipt_by_id(
    mnr_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Download membership receipt for a specific user (staff + MNR user access).
    """
    is_staff = isinstance(current_user, StaffEmployee) or getattr(current_user, 'is_staff', False) or getattr(current_user, 'role', '') in ['admin', 'superadmin', 'staff']
    
    if not is_staff and str(current_user.id) != mnr_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this receipt"
        )
    
    # Find the target user
    target_user = db.query(User).filter(User.id == mnr_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if target_user.coupon_status != "Activated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receipt only available for activated members"
        )
    
    # DC Protocol (Jan 2026): Welcome Coupon users cannot download/print receipts
    if getattr(target_user, 'is_welcome_coupon', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receipt download is not available for Welcome Coupon (Exception Coupon) members"
        )
    
    # Prepare receipt data
    activation_date = target_user.activation_date or target_user.created_at
    
    if activation_date:
        from dateutil.relativedelta import relativedelta
        expiry_date = activation_date + relativedelta(months=24)
        expiry_str = expiry_date.strftime('%d %B %Y')
        activation_str = activation_date.strftime('%d %B %Y')
        payment_str = activation_str
    else:
        expiry_str = "24 months from activation"
        activation_str = "N/A"
        payment_str = "N/A"
    
    receipt_number = getattr(target_user, 'points_receipt_number', None) or f"MNR-RCP-{mnr_id[-6:]}"
    
    # DC Protocol (Feb 2026): Calculate points from package_points multiplier
    from app.constants import DEFAULT_COUPON_POINTS
    points = DEFAULT_COUPON_POINTS  # Default 30000
    if hasattr(target_user, 'package_points') and target_user.package_points:
        points = int(target_user.package_points * DEFAULT_COUPON_POINTS)
    amount = points
    
    receipt_data = {
        "member_name": target_user.name or "N/A",
        "mnr_id": str(target_user.id) if target_user.id else "N/A",
        "payment_date": payment_str,
        "activation_date": activation_str,
        "amount_paid": amount,
        "points_credited": points,
        "receipt_number": receipt_number,
        "expiry_date": expiry_str
    }
    
    pdf_buffer = generate_membership_receipt(receipt_data)
    filename = f"MNR_Receipt_{mnr_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
