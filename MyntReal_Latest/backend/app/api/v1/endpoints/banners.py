"""
Banner and Communication System API Endpoints
Handles TOP Performers, Custom Banners, Image Banners, Popups, Terms & Conditions
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, get_current_admin_user, get_current_super_admin_user, get_banner_creator_user, get_banner_creator_user_hybrid
from app.core.audience_resolver import normalize_audience, audience_label, VGK_TEAM_CATEGORY, is_vgk4u_enabled  # DC_AUDIENCE_001 (audit #35 follow-up)
from app.models.user import User
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner  # DC_AUDIENCE_001 — VGK4U birthdays source


def set_creator_fields(data_dict: dict, current_user) -> dict:
    """
    DC Protocol Feb 2026: Set appropriate creator fields based on user type.
    Staff users use created_by_staff_id (INT), MNR users use created_by (VARCHAR).
    """
    if isinstance(current_user, StaffEmployee):
        data_dict['created_by'] = None
        data_dict['created_by_staff_id'] = current_user.id
    else:
        data_dict['created_by'] = current_user.id
        data_dict['created_by_staff_id'] = None
    return data_dict
from app.models.banner import Banner, CustomBanner, BannerSkippedUser, PopupMessage, UserCouponAcceptance, EmailTemplate, BirthdayMessage, BirthdaySkippedUser
from app.schemas.banner import (
    # Banner schemas
    BannerCreate, BannerUpdate, BannerApproval, BannerResponse,
    # Custom Banner schemas
    CustomBannerCreate, CustomBannerUpdate, CustomBannerResponse,
    # TOP Performers schemas
    TopPerformersResponse, BannerSkipUserRequest, BannerSkippedUserResponse,
    # Popup schemas
    PopupMessageCreate, PopupMessageUpdate, PopupMessageApproval, PopupMessageResponse,
    # Coupon Acceptance schemas
    CouponAcceptanceCheck, CouponAcceptanceCheckResponse, CouponAcceptanceRecord, CouponAcceptanceResponse,
    # Email schemas
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse, SendEmailRequest, SendEmailResponse
)
from app.services.banner_service import BannerService

router = APIRouter(prefix="/banners", tags=["Banners & Communication"])

# IST Timezone constant
IST = pytz.timezone('Asia/Kolkata')


# ===== TOP PERFORMERS BANNER ENDPOINTS =====

@router.get("/top-performers", response_model=TopPerformersResponse)
async def get_top_performers(
    limit: int = 7,
    exclude_skipped: bool = True,
    audience: Optional[str] = Query(None, regex="^(mnr|vgk4u|both)$"),  # DC_AUDIENCE_001 — 'mnr' | 'vgk4u' | 'both' (default mnr/None for byte-identical pre-A1 behaviour)
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get top earners for banner display based on LATEST earning day.
    Only shows users with > ₹1,000 GROSS earnings on the latest day.

    DC_AUDIENCE_001 (audit #35 follow-up, Phase A1) + Task #33 Phase 1:
    - ``audience`` omitted (None) returns the pre-A1 MNR PendingIncome
      leaderboard with byte-identical response shape (zero behaviour change).
    - ``audience='mnr'`` returns the same MNR leaderboard (with audience tag).
    - ``audience='vgk4u'`` returns a separate VGK4U leaderboard via
      ``audience_resolver.vgk4u_top_earners`` (vgk_team_income_entries CONFIRMED).
      Falls back to ``BannerService.calculate_top_earners_vgk4u`` if the
      resolver helper is unavailable.
    - ``audience='both'`` merges MNR + VGK4U (each row tagged with its origin).
    """
    aud = normalize_audience(audience) if audience is not None else 'mnr'

    # DC_VGK4U_SEC_001 (rebase merge): scope VGK4U leaderboard by current_user's company_id.
    from app.core.audience_resolver import resolve_company_id_from_user
    company_id = resolve_company_id_from_user(current_user, db)

    if aud == 'vgk4u':
        # Prefer the new audience_resolver helper (Task #33). Falls back to
        # BannerService.calculate_top_earners_vgk4u (Phase A1) if absent.
        try:
            from app.core.audience_resolver import vgk4u_top_earners
            top_earners = vgk4u_top_earners(db, limit=limit, company_id=company_id)
        except Exception:
            top_earners = BannerService.calculate_top_earners_vgk4u(
                db, limit=limit, exclude_skipped=exclude_skipped
            )
        # VGK4U skip table TBD in later phase.
        skipped_count = 0
    elif aud == 'both':
        from app.core.audience_resolver import vgk4u_top_earners
        mnr_rows = BannerService.calculate_top_earners(
            db, limit=limit, exclude_skipped=exclude_skipped
        )
        for r in mnr_rows:
            r.setdefault('audience', 'mnr')
        vgk_rows = vgk4u_top_earners(db, limit=limit, company_id=company_id)
        top_earners = mnr_rows + vgk_rows
        skipped_count = db.query(BannerSkippedUser).filter(
            BannerSkippedUser.is_active == True
        ).count()
    else:
        top_earners = BannerService.calculate_top_earners(
            db, limit=limit, exclude_skipped=exclude_skipped
        )
        skipped_count = db.query(BannerSkippedUser).filter(
            BannerSkippedUser.is_active == True
        ).count()


    # Get latest earning date from first performer (all have same date)
    latest_date = top_earners[0]['latest_earning_date'] if top_earners else None

    # Strict backward compat: response shape is identical to pre-A1 when no
    # ``audience`` param is passed (TopPerformersResponse model controls keys).
    return {
        "top_performers": top_earners,
        "total_count": len(top_earners),
        "excluded_count": skipped_count,
        "latest_earning_date": latest_date,
    }


@router.post("/top-performers/skip")
async def skip_user_from_banner(
    request: BannerSkipUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Skip user from top earners banner (Admin only)"""
    result = BannerService.skip_user_from_banner(
        db,
        user_id=request.user_id,
        skipped_by=current_user.id,
        reason=request.reason
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/top-performers/reactivate/{user_id}")
async def reactivate_user_for_banner(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Reactivate skipped user for top earners banner (Admin only)"""
    result = BannerService.reactivate_user_for_banner(db, user_id=user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/top-performers/skipped", response_model=List[BannerSkippedUserResponse])
async def get_skipped_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Get all skipped users (Admin only)"""
    skipped_users = db.query(BannerSkippedUser).filter(
        BannerSkippedUser.is_active == True
    ).all()
    
    return skipped_users


# ===== CUSTOM BANNER ENDPOINTS =====

@router.get("/custom", response_model=List[CustomBannerResponse])
async def get_custom_banners(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get custom banners"""
    query = db.query(CustomBanner)
    
    if active_only:
        query = query.filter(CustomBanner.is_active == True)
    
    banners = query.order_by(
        CustomBanner.priority.asc(),
        CustomBanner.display_order.asc()
    ).all()
    
    return banners


@router.get("/custom/{banner_id}", response_model=CustomBannerResponse)
async def get_custom_banner_by_id(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get single custom banner by ID"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    return banner


@router.post("/custom", response_model=CustomBannerResponse, )
async def create_custom_banner(
    banner: CustomBannerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Create custom banner - Staff: Active immediately, Staff: May need review"""
    banner_data = banner.dict()
    set_creator_fields(banner_data, current_user)  # DC Protocol Feb 2026: Handle staff vs MNR users
    
    # DC Protocol Feb 2026: Staff creates as active immediately
    if isinstance(current_user, StaffEmployee):
        banner_data['is_active'] = True
    
    new_banner = CustomBanner(**banner_data)
    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)
    
    return new_banner


@router.put("/custom/{banner_id}", response_model=CustomBannerResponse, )
async def update_custom_banner(
    banner_id: int,
    banner_update: CustomBannerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Update custom banner (Admin only)"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # Update fields
    for key, value in banner_update.dict(exclude_unset=True).items():
        setattr(banner, key, value)
    
    banner.updated_at = datetime.utcnow()
    banner.updated_by = current_user.id
    
    db.commit()
    db.refresh(banner)
    
    return banner


@router.post("/custom/{banner_id}/toggle", )
async def toggle_custom_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Toggle custom banner active status (Admin only)"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.is_active = not banner.is_active
    banner.updated_at = datetime.utcnow()
    banner.updated_by = current_user.id
    
    db.commit()
    
    return {"success": True, "is_active": banner.is_active, "message": f"Banner {'activated' if banner.is_active else 'deactivated'}"}


@router.delete("/custom/{banner_id}", )
async def delete_custom_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Delete custom banner (Admin only)"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    db.delete(banner)
    db.commit()
    
    return {"success": True, "message": "Banner deleted successfully"}


# ===== IMAGE BANNER ENDPOINTS =====

@router.get("/image", response_model=List[BannerResponse])
async def get_image_banners(
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get image banners"""
    query = db.query(Banner)
    
    if status_filter:
        query = query.filter(Banner.status == status_filter)
    
    banners = query.order_by(Banner.display_order.asc()).all()
    return banners


@router.get("/image/{banner_id}", response_model=BannerResponse)
async def get_image_banner_by_id(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get single image banner by ID"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    return banner


@router.post("/image", response_model=BannerResponse, )
async def create_image_banner(
    banner: BannerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Create image banner - Staff: Active immediately, Staff: Pending approval"""
    banner_data = banner.dict()
    set_creator_fields(banner_data, current_user)  # DC Protocol Feb 2026: Handle staff vs MNR users
    
    # DC Protocol Feb 2026: Staff creates as Active (no approval), Staff needs approval
    initial_status = "Active" if isinstance(current_user, StaffEmployee) else "Pending"
    new_banner = Banner(**banner_data, status=initial_status)
    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)
    
    return new_banner


@router.put("/image/{banner_id}", response_model=BannerResponse, )
async def update_image_banner(
    banner_id: int,
    banner_update: BannerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Update image banner (Admin only)"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    for key, value in banner_update.dict(exclude_unset=True).items():
        setattr(banner, key, value)
    
    db.commit()
    db.refresh(banner)
    
    return banner


@router.post("/image/{banner_id}/approve", )
async def approve_image_banner(
    banner_id: int,
    approval: BannerApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user)
):
    """Approve or reject image banner (Super Admin/RVZ ID only)"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    if approval.status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'Approved' or 'Rejected'")
    
    banner.status = "Active" if approval.status == "Approved" else "Rejected"
    banner.approved_by = approval.approved_by
    banner.approved_date = datetime.utcnow()
    
    db.commit()
    
    return {"success": True, "status": banner.status, "message": f"Banner {approval.status.lower()}"}


@router.post("/image/{banner_id}/toggle", )
async def toggle_image_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Toggle image banner status between Active/Stopped - DC Protocol Feb 2026
    
    Staff users can toggle any banner directly.
    Staff: Only banners that have been approved (Active or Stopped status) can be toggled.
    """
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # DC Protocol Feb 2026: Staff can toggle any banner, Staff restricted to approved
    if not isinstance(current_user, StaffEmployee):
        if banner.status not in ['Active', 'Stopped']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot toggle banner with status '{banner.status}'. Only Active or Stopped banners can be toggled. Pending/Rejected banners must go through approval first."
            )
    
    # Toggle between Active and Stopped (or set to Active if Pending/Rejected for staff)
    if banner.status == 'Active':
        banner.status = 'Stopped'
        action = 'paused'
    else:
        banner.status = 'Active'
        action = 'resumed'
    
    db.commit()
    
    return {"success": True, "status": banner.status, "message": f"Banner {action} successfully"}


@router.delete("/image/{banner_id}", )
async def delete_image_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Delete image banner (Admin only)"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    db.delete(banner)
    db.commit()
    
    return {"success": True, "message": "Banner deleted successfully"}


# ===== POPUP MESSAGE ENDPOINTS =====

@router.get("/popups", response_model=List[PopupMessageResponse])
async def get_popups(
    target_page: str = None,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get popup messages"""
    query = db.query(PopupMessage)
    
    if target_page:
        query = query.filter(PopupMessage.target_page == target_page)
    if status_filter:
        query = query.filter(PopupMessage.status == status_filter)
    
    popups = query.order_by(PopupMessage.priority.asc()).all()
    return popups


@router.get("/popups/{popup_id}", response_model=PopupMessageResponse)
async def get_popup_by_id(
    popup_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get single popup message by ID"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    return popup


@router.post("/popups", response_model=PopupMessageResponse, )
async def create_popup(
    popup: PopupMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Create popup message - Staff: Active immediately, Staff: Pending approval"""
    popup_data = popup.dict()
    set_creator_fields(popup_data, current_user)  # DC Protocol Feb 2026: Handle staff vs MNR users
    
    # DC Protocol Feb 2026: Staff creates as Active (no approval), Staff needs approval
    if isinstance(current_user, StaffEmployee):
        popup_data['status'] = 'Active'
        popup_data['is_active'] = True
    
    new_popup = PopupMessage(**popup_data)
    db.add(new_popup)
    db.commit()
    db.refresh(new_popup)
    
    return new_popup


@router.put("/popups/{popup_id}", response_model=PopupMessageResponse, )
async def update_popup(
    popup_id: int,
    popup_update: PopupMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Update popup message (Admin only)"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    for key, value in popup_update.dict(exclude_unset=True).items():
        setattr(popup, key, value)
    
    db.commit()
    db.refresh(popup)
    
    return popup


@router.post("/popups/{popup_id}/approve", )
async def approve_popup(
    popup_id: int,
    approval: PopupMessageApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user)
):
    """Approve or reject popup message (Super Admin/RVZ ID only)"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    if approval.status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'Approved' or 'Rejected'")
    
    popup.status = approval.status
    popup.approved_by = approval.approved_by
    popup.approved_date = datetime.utcnow()
    
    if approval.status == "Approved":
        popup.is_active = True
    elif approval.rejection_reason:
        popup.rejection_reason = approval.rejection_reason
    
    db.commit()
    
    return {"success": True, "status": popup.status, "message": f"Popup {approval.status.lower()}"}


@router.post("/popups/{popup_id}/toggle", )
async def toggle_popup(
    popup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Toggle popup message active status - DC Protocol Feb 2026
    
    Staff users can toggle any popup directly.
    Staff: Only popups that have been approved (Active, Approved, or Inactive status) can be toggled.
    """
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    # DC Protocol Feb 2026: Staff can toggle any popup, Staff restricted to approved
    if not isinstance(current_user, StaffEmployee):
        allowed_statuses = ['Active', 'Approved', 'Inactive']
        if popup.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot toggle popup with status '{popup.status}'. Only Active/Approved/Inactive popups can be toggled. Draft/Pending/Rejected popups must go through approval first."
            )
    
    # Toggle is_active and update status accordingly
    popup.is_active = not popup.is_active
    if popup.is_active:
        popup.status = 'Active'
        action = 'resumed'
    else:
        popup.status = 'Inactive'
        action = 'paused'
    
    db.commit()
    
    return {"success": True, "is_active": popup.is_active, "status": popup.status, "message": f"Popup {action} successfully"}


@router.delete("/popups/{popup_id}", )
async def delete_popup(
    popup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Delete popup message (Admin only)"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    db.delete(popup)
    db.commit()
    
    return {"success": True, "message": "Popup deleted successfully"}


# ===== TERMS & CONDITIONS POPUP ENDPOINTS =====

@router.post("/coupon-acceptance/check", response_model=CouponAcceptanceCheckResponse)
async def check_coupon_acceptance(
    data: CouponAcceptanceCheck = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Check if user should see coupon T&C popup"""
    result = BannerService.check_coupon_acceptance(db, user_id=data.user_id)
    return result


@router.post("/coupon-acceptance/record", response_model=CouponAcceptanceResponse)
async def record_coupon_acceptance(
    acceptance: CouponAcceptanceRecord = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Record user's coupon T&C acceptance"""
    # Get IP address from request (with defensive guard)
    ip_address = request.client.host if request and request.client else "Unknown"
    user_agent = request.headers.get("user-agent", "Unknown") if request else "Unknown"
    
    result = BannerService.record_coupon_acceptance(
        db,
        user_id=acceptance.user_id,
        attempt_number=acceptance.login_attempt_number,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


# ===== PUBLIC BANNER DATA ENDPOINT =====

@router.get("/dashboard-data")
async def get_dashboard_banner_data(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get all banner data for user dashboard"""
    # Get TOP performers
    top_performers = BannerService.calculate_top_earners(db, limit=5, exclude_skipped=True)
    
    # Get active custom banners
    custom_banners = BannerService.get_active_custom_banners(db)
    
    # Get active image banners
    image_banners = BannerService.get_active_image_banners(db)
    
    # Get active popup messages
    popup_messages = db.query(PopupMessage).filter(
        PopupMessage.status.in_(["Active", "Approved"])
    ).order_by(PopupMessage.priority.asc()).all()
    
    # Check T&C popup (only for MNR users, skip for staff)
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        tc_popup = {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
    else:
        tc_popup = BannerService.check_coupon_acceptance(db, user_id=current_user.id)
    
    return {
        "top_performers": top_performers[:5],
        "custom_banners": [
            {
                "id": b.id,
                "title": b.title,
                "content": b.content,
                "background_color": b.background_color,
                "text_color": b.text_color,
                "banner_type": b.banner_type,
                "priority": b.priority
            }
            for b in custom_banners
        ],
        "image_banners": [
            {
                "id": b.id,
                "title": b.title,
                "image_content": b.image_content,
                "text_content": b.text_content,
                "banner_type": b.banner_type
            }
            for b in image_banners
        ],
        "popup_messages": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "priority": p.priority,
                "banner_type": "popup"
            }
            for p in popup_messages
        ],
        "tc_popup": tc_popup
    }


# ===== BIRTHDAY BANNER ENDPOINTS =====

@router.get("/birthday-today")
async def get_birthday_banner(
    exclude_skipped: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get today's birthday banner with rotating message and birthday users
    Shows: Daily rotating message + users celebrating birthday TODAY (name + location only, NO age)
    DC Protocol: All data from user table only
    Admin Control: Excludes skipped users (like top performers)
    IST Timezone: Uses Indian Standard Time (UTC+5:30) for birthday checks
    """
    from sqlalchemy import extract, func, and_
    from datetime import datetime
    import pytz
    
    # Get today's date in IST (UTC+5:30)
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    
    # Get skipped user IDs (like top performers)
    skipped_user_ids = []
    if exclude_skipped:
        skipped_users = db.query(BirthdaySkippedUser.user_id).filter(
            BirthdaySkippedUser.is_active == True
        ).all()
        skipped_user_ids = [u.user_id for u in skipped_users]
    
    # Get users with birthdays today (DC Protocol - user table only)
    # DC Protocol (Jan 31, 2026): Exclude Suspended/Inactive users from birthday list
    query = db.query(User).filter(
        extract('month', User.actual_date_of_birth) == today.month,
        extract('day', User.actual_date_of_birth) == today.day,
        User.actual_date_of_birth.isnot(None),
        User.account_status == 'Active'
    )
    
    # Exclude skipped users
    if skipped_user_ids:
        query = query.filter(User.id.notin_(skipped_user_ids))
    
    birthday_users = query.all()
    
    # Get daily rotating birthday message
    # Rotate based on day of year to ensure new message each day
    day_of_year = today.timetuple().tm_yday
    
    active_messages = db.query(BirthdayMessage).filter(
        BirthdayMessage.is_active == True
    ).order_by(BirthdayMessage.display_order).all()
    
    if not active_messages:
        daily_message = "🎉 Happy Birthday! Wishing you a day filled with happiness and joy!"
    else:
        # Rotate through messages based on day of year
        message_index = day_of_year % len(active_messages)
        daily_message = active_messages[message_index].message
    
    # Format user data (NAME and LOCATION only - NO age)
    # DC Protocol: All data from user table only
    users_data = [
        {
            "user_id": user.id,
            "name": user.name,
            "city": user.city or "Unknown",
            "state": user.state or "",
            "location": f"{user.city or 'Unknown'}, {user.state or 'IN'}",
            "has_photo": False  # No photo field in user table - show initials instead
        }
        for user in birthday_users
    ]
    
    return {
        "success": True,
        "has_birthdays": len(birthday_users) > 0,
        "message": daily_message,
        "users": users_data,
        "total_count": len(birthday_users),
        "date": today.isoformat()
    }


# ===== BIRTHDAY DASHBOARD FILTERS (ADMIN) =====
#
# Auth scope: all four endpoints below require ``get_banner_creator_user_hybrid``
# (staff-only). They are admin-dashboard tools, not member-portal endpoints.
# Member-facing birthday widgets must use a member-allowed route (TBD in a
# later phase). Mobile pages that consume these endpoints are intended for
# staff use as well.
#
# DC_AUDIENCE_001 (audit #35 follow-up, Phase A1):
# All four endpoints accept an optional ``audience`` query param
# (``mnr`` | ``vgk4u`` | ``both``). When the caller does not pass ``audience``
# the response is byte-for-byte identical to the pre-A1 behaviour — no new
# keys are introduced and no per-item fields are added. Strict backward
# compatibility is preserved for every existing client.

def _mnr_birthday_rows(db: Session, target_date, only_active: bool = True) -> List[dict]:
    """
    Build MNR birthday rows for a single date.

    ``only_active`` mirrors the pre-A1 per-endpoint filter intent:
      - ``today`` / ``yesterday`` excluded Suspended/Inactive (DC Protocol Jan 31, 2026).
      - ``tomorrow`` / ``next-7-days`` did NOT apply that filter.
    Default ``True`` matches the most common case; the next-7-days and
    tomorrow handlers pass ``only_active=False`` to preserve byte-identical
    pre-A1 behaviour.
    """
    filters = [
        User.actual_date_of_birth.isnot(None),
        extract('month', User.actual_date_of_birth) == target_date.month,
        extract('day', User.actual_date_of_birth) == target_date.day,
    ]
    if only_active:
        filters.append(User.account_status == 'Active')
    users = db.query(User).filter(*filters).all()
    return [
        {
            "user_id": user.id,
            "name": user.name,
            "location": f"{user.city or 'Unknown'}, {user.state or 'IN'}",
            "birthday_date": user.actual_date_of_birth.isoformat(),
            "has_photo": bool(user.kyc_photo_path) if hasattr(user, 'kyc_photo_path') else False,
        }
        for user in users
    ]


def _vgk_birthday_rows(db: Session, target_date, company_id: Optional[int] = None) -> List[dict]:
    """
    Build VGK4U birthday rows for a single date.

    DC_VGK4U_SEC_001 (rebase merge): when ``company_id`` is supplied the rows
    are scoped via ``audience_resolver.vgk4u_birthday_users`` (joins through
    PartnerCompanySegment). When ``company_id`` is None, falls back to the
    direct OfficialPartner query (super-admin / global view).

    Returns ``[]`` and logs a warning on any failure (e.g. the column is
    absent on older DBs) — never raises.

    Master-switch gated: returns ``[]`` immediately when the global
    ``vgk4u_enabled`` SystemControl flag is off.

    Rebase note (Task #33 Phase 1): the parallel branch shipped a
    ``_vgk4u_birthday_payload`` helper backed by
    ``audience_resolver.vgk4u_birthday_users``. Both produce the same shape;
    we keep this helper as the canonical entry point and now route the
    company-scoped path through the same resolver helper.
    """
    try:
        if not is_vgk4u_enabled(db):
            return []
        dob_col = getattr(OfficialPartner, 'dob_actual', None)
        if dob_col is None:
            return []
        if company_id is not None:
            from app.core.audience_resolver import vgk4u_birthday_users
            partners = vgk4u_birthday_users(
                db, target_date, dob_field='dob_actual', company_id=company_id
            )
        else:
            partners = db.query(OfficialPartner).filter(
                OfficialPartner.category == VGK_TEAM_CATEGORY,
                OfficialPartner.is_active == True,
                dob_col.isnot(None),
                extract('month', dob_col) == target_date.month,
                extract('day', dob_col) == target_date.day,
            ).all()
        return [
            {
                "user_id": p.partner_code,
                "name": p.partner_name,
                "location": f"{p.city or 'Unknown'}, {p.state or 'IN'}",
                "birthday_date": getattr(p, 'dob_actual').isoformat(),
                "has_photo": bool(getattr(p, 'logo_path', None)),
            }
            for p in partners
        ]
    except Exception as exc:
        logger.warning(f"[DC_AUDIENCE_001] VGK4U birthday branch failed safely: {exc}")
        return []


def _build_birthday_rows(
    db: Session,
    target_date,
    audience_param: Optional[str],
    only_active: bool = True,
    current_user=None,
) -> tuple:
    """
    Centralised audience-aware row builder.

    Returns ``(rows, aud_or_none)`` where ``aud_or_none`` is the normalised
    audience value when the caller explicitly passed the ``audience`` query
    param, or ``None`` when they did not. Callers use ``aud_or_none`` to
    decide whether to emit the new ``audience`` / ``audience_label`` envelope
    keys (preserving strict backward compatibility).

    ``only_active`` is forwarded to the MNR path so each endpoint can preserve
    its pre-A1 active-status filter behaviour (today/yesterday filter Active;
    tomorrow/next-7-days do not).

    DC_VGK4U_SEC_001 (rebase merge): ``current_user`` is forwarded to the
    VGK4U branch so company_id scoping is applied via
    ``resolve_company_id_from_user`` — preventing cross-company VGK4U exposure.
    """
    company_id: Optional[int] = None
    if current_user is not None:
        try:
            from app.core.audience_resolver import resolve_company_id_from_user
            company_id = resolve_company_id_from_user(current_user, db)
        except Exception:
            company_id = None

    if audience_param is None:
        # Pre-A1 default path — MNR only, no per-item annotation.
        return _mnr_birthday_rows(db, target_date, only_active=only_active), None

    aud = normalize_audience(audience_param)
    rows: List[dict] = []
    if aud in ("mnr", "both"):
        rows.extend(
            {**r, "audience": "mnr"}
            for r in _mnr_birthday_rows(db, target_date, only_active=only_active)
        )
    if aud in ("vgk4u", "both"):
        rows.extend(
            {**r, "audience": "vgk4u"}
            for r in _vgk_birthday_rows(db, target_date, company_id=company_id)
        )
    return rows, aud


def _audience_envelope(payload: dict, aud_or_none: Optional[str]) -> dict:
    """Add audience envelope keys only when the caller explicitly passed the param."""
    if aud_or_none is not None:
        payload["audience"] = aud_or_none
        payload["audience_label"] = audience_label(aud_or_none)
    return payload


@router.get("/admin/birthdays/yesterday")
async def get_yesterday_birthdays(
    audience: Optional[str] = None,  # DC_AUDIENCE_001
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Get yesterday's birthdays for admin dashboard (audience-aware)."""
    today = datetime.now(IST).date()
    yesterday = today - timedelta(days=1)
    rows, aud_or_none = _build_birthday_rows(db, yesterday, audience, current_user=current_user)
    return _audience_envelope({
        "success": True,
        "filter": "yesterday",
        "date": yesterday.isoformat(),
        "users": rows,
        "total_count": len(rows),
    }, aud_or_none)


@router.get("/admin/birthdays/today")
async def get_today_birthdays_admin(
    audience: Optional[str] = None,  # DC_AUDIENCE_001
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Get today's birthdays for admin dashboard (audience-aware)."""
    today = datetime.now(IST).date()
    rows, aud_or_none = _build_birthday_rows(db, today, audience, current_user=current_user)
    return _audience_envelope({
        "success": True,
        "filter": "today",
        "date": today.isoformat(),
        "users": rows,
        "total_count": len(rows),
    }, aud_or_none)


@router.get("/admin/birthdays/tomorrow")
async def get_tomorrow_birthdays(
    audience: Optional[str] = None,  # DC_AUDIENCE_001
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Get tomorrow's birthdays for admin dashboard (audience-aware).

    Pre-A1 parity: the tomorrow endpoint historically did NOT exclude
    Suspended/Inactive users — ``only_active=False`` preserves that.
    """
    today = datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)
    rows, aud_or_none = _build_birthday_rows(db, tomorrow, audience, only_active=False, current_user=current_user)
    return _audience_envelope({
        "success": True,
        "filter": "tomorrow",
        "date": tomorrow.isoformat(),
        "users": rows,
        "total_count": len(rows),
    }, aud_or_none)


@router.get("/admin/birthdays/next-7-days")
async def get_next_week_birthdays(
    audience: Optional[str] = None,  # DC_AUDIENCE_001
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Get birthdays for next 7 days for admin dashboard (audience-aware).

    Pre-A1 parity: the next-7-days endpoint historically did NOT exclude
    Suspended/Inactive users — ``only_active=False`` preserves that.
    """
    today = datetime.now(IST).date()
    users_data: List[dict] = []
    aud_or_none: Optional[str] = None

    for i in range(1, 8):
        check_date = today + timedelta(days=i)
        rows, aud_or_none = _build_birthday_rows(db, check_date, audience, only_active=False, current_user=current_user)
        users_data.extend(rows)

    # Sort by date (matches pre-A1 ordering).
    users_data.sort(key=lambda x: datetime.fromisoformat(x['birthday_date']).replace(year=today.year))

    return _audience_envelope({
        "success": True,
        "filter": "next-7-days",
        "date_range": {
            "start": (today + timedelta(days=1)).isoformat(),
            "end": (today + timedelta(days=7)).isoformat(),
        },
        "users": users_data,
        "total_count": len(users_data),
    }, aud_or_none)


# ===== BIRTHDAY MESSAGE MANAGEMENT (ADMIN) =====

@router.get("/birthday-messages")
async def get_birthday_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Get all birthday messages (Admin only)"""
    messages = db.query(BirthdayMessage).order_by(
        BirthdayMessage.display_order.asc()
    ).all()
    
    return {
        "success": True,
        "messages": [
            {
                "id": msg.id,
                "message": msg.message,
                "is_active": msg.is_active,
                "display_order": msg.display_order,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    }


class BirthdayMessageCreate(BaseModel):
    message: str
    is_active: bool = True
    display_order: int = 0

@router.post("/birthday-messages")
async def create_birthday_message(
    data: BirthdayMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Create new birthday message (Admin only)"""
    new_message = BirthdayMessage(
        message=data.message,
        is_active=data.is_active,
        display_order=data.display_order,
        created_by=current_user.id
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return {
        "success": True,
        "message": "Birthday message created successfully",
        "data": {
            "id": new_message.id,
            "message": new_message.message,
            "is_active": new_message.is_active
        }
    }


class BirthdayMessageUpdate(BaseModel):
    message: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

@router.put("/birthday-messages/{message_id}")
async def update_birthday_message(
    message_id: int,
    data: BirthdayMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Update birthday message (Admin only)"""
    message = db.query(BirthdayMessage).filter(BirthdayMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Birthday message not found")
    
    if data.message is not None:
        message.message = data.message
    if data.is_active is not None:
        message.is_active = data.is_active
    if data.display_order is not None:
        message.display_order = data.display_order
    
    message.updated_by = current_user.id
    message.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Birthday message updated successfully"
    }


@router.delete("/birthday-messages/{message_id}")
async def delete_birthday_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Delete birthday message (Admin only)"""
    message = db.query(BirthdayMessage).filter(BirthdayMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Birthday message not found")
    
    db.delete(message)
    db.commit()
    
    return {
        "success": True,
        "message": "Birthday message deleted successfully"
    }


# ===== BIRTHDAY BANNER SKIP/REACTIVATE (LIKE TOP PERFORMERS) =====

class BirthdaySkipUserRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None

@router.post("/birthday-banner/skip")
async def skip_user_from_birthday_banner(
    request: BirthdaySkipUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """
    Skip user from birthday banner (Admin only)
    Similar to top performers skip functionality
    """
    # Check if user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already skipped
    existing = db.query(BirthdaySkippedUser).filter(
        BirthdaySkippedUser.user_id == request.user_id,
        BirthdaySkippedUser.is_active == True
    ).first()
    
    if existing:
        return {
            "success": False,
            "message": f"User {request.user_id} is already skipped from birthday banner"
        }
    
    # Create skip record
    skip_record = BirthdaySkippedUser(
        user_id=request.user_id,
        skipped_by=current_user.id,
        reason=request.reason
    )
    
    db.add(skip_record)
    db.commit()
    
    return {
        "success": True,
        "message": f"User {request.user_id} skipped from birthday banner successfully"
    }


@router.post("/birthday-banner/reactivate/{user_id}")
async def reactivate_user_for_birthday_banner(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """
    Reactivate skipped user for birthday banner (Admin only)
    Similar to top performers reactivate functionality
    """
    skip_record = db.query(BirthdaySkippedUser).filter(
        BirthdaySkippedUser.user_id == user_id,
        BirthdaySkippedUser.is_active == True
    ).first()
    
    if not skip_record:
        return {
            "success": False,
            "message": f"User {user_id} is not currently skipped"
        }
    
    # Deactivate skip record
    skip_record.is_active = False
    skip_record.reactivated_at = datetime.utcnow()
    skip_record.reactivated_by = current_user.id
    
    db.commit()
    
    return {
        "success": True,
        "message": f"User {user_id} reactivated for birthday banner successfully"
    }


@router.get("/birthday-banner/skipped")
async def get_skipped_birthday_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """
    Get all skipped birthday users (Admin only)
    Similar to top performers skipped list
    """
    skipped_records = db.query(BirthdaySkippedUser).filter(
        BirthdaySkippedUser.is_active == True
    ).all()
    
    result = []
    for record in skipped_records:
        user = db.query(User).filter(User.id == record.user_id).first()
        if user:
            result.append({
                "user_id": user.id,
                "name": user.name,
                "reason": record.reason,
                "skipped_by": record.skipped_by,
                "skipped_at": record.skipped_at.isoformat() if record.skipped_at else None
            })
    
    return {
        "success": True,
        "skipped_users": result,
        "total_count": len(result)
    }



# ===== CUSTOM BANNER ACTION ENDPOINTS =====

@router.post("/custom/{banner_id}/approve")
async def approve_custom_banner(
    banner_id: int,
    approval: BannerApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user)
):
    """Approve or reject custom banner (Super Admin/RVZ ID only)"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    if approval.status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'Approved' or 'Rejected'")
    
    banner.status = "Active" if approval.status == "Approved" else "Rejected"
    banner.approved_by = approval.approved_by
    banner.approved_date = datetime.utcnow()
    banner.is_active = approval.status == "Approved"
    
    db.commit()
    
    return {"success": True, "status": banner.status, "message": f"Banner {approval.status.lower()}"}


@router.post("/custom/{banner_id}/reject")
async def reject_custom_banner(
    banner_id: int,
    rejection: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user)
):
    """Reject custom banner with reason"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Rejected"
    banner.approved_by = current_user.id
    banner.approved_date = datetime.utcnow()
    banner.is_active = False
    
    db.commit()
    
    return {"success": True, "status": "Rejected", "message": "Banner rejected"}


@router.post("/custom/{banner_id}/pause")
async def pause_custom_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Pause active custom banner"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Paused"
    banner.updated_at = datetime.utcnow()
    banner.updated_by = current_user.id
    
    db.commit()
    
    return {"success": True, "status": "Paused", "message": "Banner paused"}


@router.post("/custom/{banner_id}/resume")
async def resume_custom_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Resume paused custom banner"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Active"
    banner.updated_at = datetime.utcnow()
    banner.updated_by = current_user.id
    
    db.commit()
    
    return {"success": True, "status": "Active", "message": "Banner resumed"}


@router.post("/custom/{banner_id}/stop")
async def stop_custom_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Stop custom banner permanently"""
    banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Stopped"
    banner.updated_at = datetime.utcnow()
    banner.updated_by = current_user.id
    banner.is_active = False
    
    db.commit()
    
    return {"success": True, "status": "Stopped", "message": "Banner stopped"}


# ===== IMAGE BANNER ACTION ENDPOINTS =====

@router.post("/image/{banner_id}/reject")
async def reject_image_banner(
    banner_id: int,
    rejection: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user)
):
    """Reject image banner"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Rejected"
    banner.approved_by = current_user.id
    banner.approved_date = datetime.utcnow()
    
    db.commit()
    
    return {"success": True, "status": "Rejected", "message": "Banner rejected"}


@router.post("/image/{banner_id}/pause")
async def pause_image_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Pause active image banner"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Paused"
    
    db.commit()
    
    return {"success": True, "status": "Paused", "message": "Banner paused"}


@router.post("/image/{banner_id}/resume")
async def resume_image_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Resume paused image banner"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Active"
    
    db.commit()
    
    return {"success": True, "status": "Active", "message": "Banner resumed"}


@router.post("/image/{banner_id}/stop")
async def stop_image_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Stop image banner permanently"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.status = "Stopped"
    
    db.commit()
    
    return {"success": True, "status": "Stopped", "message": "Banner stopped"}


# ===== POPUP MESSAGE ACTION ENDPOINTS =====

@router.post("/popups/{popup_id}/reject")
async def reject_popup(
    popup_id: int,
    rejection: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user)
):
    """Reject popup message"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    popup.status = "Rejected"
    popup.approved_by = current_user.id
    popup.approved_date = datetime.utcnow()
    popup.is_active = False
    
    db.commit()
    
    return {"success": True, "status": "Rejected", "message": "Popup rejected"}


@router.post("/popups/{popup_id}/pause")
async def pause_popup(
    popup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Pause active popup"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    popup.status = "Paused"
    
    db.commit()
    
    return {"success": True, "status": "Paused", "message": "Popup paused"}


@router.post("/popups/{popup_id}/resume")
async def resume_popup(
    popup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Resume paused popup"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    popup.status = "Approved"
    popup.is_active = True
    
    db.commit()
    
    return {"success": True, "status": "Approved", "message": "Popup resumed"}


@router.post("/popups/{popup_id}/stop")
async def stop_popup(
    popup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Stop popup permanently"""
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        raise HTTPException(status_code=404, detail="Popup not found")
    
    popup.status = "Stopped"
    popup.is_active = False
    
    db.commit()
    
    return {"success": True, "status": "Stopped", "message": "Popup stopped"}


# ===== BIRTHDAY MESSAGE ACTION ENDPOINTS =====

@router.post("/birthday-messages/{message_id}/pause")
async def pause_birthday_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Pause active birthday message"""
    message = db.query(BirthdayMessage).filter(BirthdayMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Birthday message not found")
    
    message.is_active = False
    
    db.commit()
    
    return {"success": True, "status": "Paused", "message": "Birthday message paused"}


@router.post("/birthday-messages/{message_id}/resume")
async def resume_birthday_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_banner_creator_user_hybrid)
):
    """Resume paused birthday message"""
    message = db.query(BirthdayMessage).filter(BirthdayMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Birthday message not found")
    
    message.is_active = True
    
    db.commit()
    
    return {"success": True, "status": "Active", "message": "Birthday message resumed"}


# ===== BANNER TRACKING ENDPOINT =====

@router.post("/track")
async def track_banner_event(
    tracking: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Lightweight client-side event tracking
    Records view/click events in banner_metrics (daily aggregation)
    Updates total counters on main banner record
    DC Protocol: Real analytics data, no mocks
    """
    try:
        from app.models.banner import BannerMetrics, Banner, CustomBanner, PopupMessage
        from datetime import date, datetime
        
        banner_id = tracking.get("banner_id")
        banner_type = tracking.get("banner_type")  # image, custom, popup, birthday
        event = tracking.get("event")  # view or click
        
        if not all([banner_id, banner_type, event]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        if event not in ["view", "click"]:
            raise HTTPException(status_code=400, detail="Event must be view or click")
        
        today = date.today()
        
        # Get or create daily metrics record
        metric = db.query(BannerMetrics).filter(
            BannerMetrics.banner_id == banner_id,
            BannerMetrics.banner_type == banner_type,
            BannerMetrics.metric_date == today
        ).first()
        
        if not metric:
            metric = BannerMetrics(
                banner_id=banner_id,
                banner_type=banner_type,
                metric_date=today,
                views=0,
                clicks=0,
                impressions=0
            )
            db.add(metric)
        
        # Update daily metrics
        if event == "view":
            metric.views += 1
            metric.impressions += 1
        elif event == "click":
            metric.clicks += 1
        
        # Update cached totals on main banner table
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "custom":
            banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            banner = None
        
        if banner:
            if event == "view":
                banner.total_views += 1
                banner.last_viewed_at = datetime.utcnow()
            elif event == "click":
                banner.total_clicks += 1
        
        db.commit()
        
        return {
            "success": True,
            "banner_id": banner_id,
            "banner_type": banner_type,
            "event": event,
            "recorded": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Banner tracking error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

