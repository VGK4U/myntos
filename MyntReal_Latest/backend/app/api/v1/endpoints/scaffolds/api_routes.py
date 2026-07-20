"""
API Endpoints - Auto-generated scaffold
Total endpoints: 33
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
from app.core.database import get_db
from app.core.rbac import require_user
from app.models.user import User
from app.models.coupon import Coupon
from app.models.transaction import PendingIncome
from app.models.base import get_indian_time
from app.constants import PACKAGE_SYSTEM, COUPON_PACKAGE_MAP, INCOME_RATES

router = APIRouter()

class ApplyPINRequest(BaseModel):
    """Request model for applying/activating a PIN"""
    member_id: str
    pin_id: int
    otp: str
    applicant_id: str

@router.get("/api/admin/daily-cost-calculation")
async def api_daily_cost_calculation(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/admin/daily-cost-calculation
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_daily_cost_calculation
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/admin/daily-cost-calculation",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/admin/company-revenue")
async def api_company_revenue(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/admin/company-revenue
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_company_revenue
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/admin/company-revenue",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/admin/cost-trend")
async def api_cost_trend(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/admin/cost-trend
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_cost_trend
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/admin/cost-trend",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/transaction-history")
async def api_transaction_history(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/transaction-history
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_transaction_history
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/transaction-history",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/consolidated-report")
async def api_consolidated_report_redirect(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/consolidated-report
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_consolidated_report_redirect
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/consolidated-report",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/admin/consolidated-report")
async def api_admin_consolidated_report(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/admin/consolidated-report
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_admin_consolidated_report
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/admin/consolidated-report",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/current-user")
async def api_current_user(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/current-user
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_current_user
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/current-user",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/pin-purchase-request/{request_id}")
async def api_pin_purchase_request_details(
    request_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/pin-purchase-request/<int:request_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_pin_purchase_request_details
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/pin-purchase-request/<int:request_id>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/team-data")
async def api_team_data(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/team-data
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_team_data
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/team-data",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/export-team")
async def api_export_team(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/export-team
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_export_team
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/export-team",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/bonanza/{bonanza_id}/details")
async def api_bonanza_details(
    bonanza_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/bonanza/<int:bonanza_id>/details
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_bonanza_details
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/bonanza/<int:bonanza_id>/details",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/coupons/generate")
async def api_generate_coupon(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/coupons/generate
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_generate_coupon
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/coupons/generate",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/coupons/redeem")
async def api_redeem_coupon(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/coupons/redeem
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_redeem_coupon
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/coupons/redeem",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/coupons/status/{coupon_code}")
async def api_coupon_status(
    coupon_code: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/coupons/status/<coupon_code>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_coupon_status
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/coupons/status/<coupon_code>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/coupons/approve")
async def api_approve_coupon(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/coupons/approve
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_approve_coupon
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/coupons/approve",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/redeem-coupon-ev")
async def api_redeem_coupon_ev(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/redeem-coupon-ev
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_redeem_coupon_ev
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/redeem-coupon-ev",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/redeem-coupon-training")
async def api_redeem_coupon_training(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/redeem-coupon-training
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_redeem_coupon_training
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/redeem-coupon-training",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/coupon-history/{coupon_id}")
async def api_coupon_history(
    coupon_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/coupon-history/<coupon_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_coupon_history
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/coupon-history/<coupon_id>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/admin/earnings-data")
async def api_admin_earnings_data(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/admin/earnings-data
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_admin_earnings_data
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/admin/earnings-data",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/create-ticket")
async def api_create_ticket(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/create-ticket
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_create_ticket
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/create-ticket",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/ticket/attachment/{attachment_id}/download")
async def download_ticket_attachment(
    attachment_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/ticket/attachment/<int:attachment_id>/download
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::download_ticket_attachment
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/ticket/attachment/<int:attachment_id>/download",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/accessible-members")
async def api_accessible_members(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/accessible-members
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_accessible_members
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/accessible-members",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/lookup-member/{member_id}")
async def api_lookup_member(
    member_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/lookup-member/<member_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_lookup_member
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/lookup-member/<member_id>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/lookup-referrer/{referrer_id}")
async def api_lookup_referrer(
    referrer_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/lookup-referrer/<referrer_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_lookup_referrer
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/lookup-referrer/<referrer_id>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/available-pins/{member_id}")
async def api_available_pins(
    member_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/available-pins/<member_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_available_pins
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/available-pins/<member_id>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/get-pin-details/{pin_number}")
async def api_get_pin_details(
    pin_number: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/get-pin-details/<pin_number>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_get_pin_details
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/get-pin-details/<pin_number>",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/send-pin-otp")
async def api_send_pin_otp(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - POST /api/send-pin-otp
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_send_pin_otp
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/send-pin-otp",
        "method": "POST",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/api/apply-pin")
async def api_apply_pin(
    request: ApplyPINRequest = Body(...),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    NEW 4-Package System: Apply/Activate PIN with staged verification
    
    Flow:
    1. Validate PIN and user
    2. Set package_points based on package type
    3. Increment referrer's referral_bonus_count
    4. Create PendingIncome (displayed immediately, paid after verification)
    5. Mark PIN as used
    """
    try:
        # Find target member
        target_member = db.query(User).filter(User.id == request.member_id).first()
        if not target_member:
            raise HTTPException(status_code=404, detail="Target member not found")
        
        # DC Protocol (Dec 22, 2025): Validate mobile uniqueness before activation
        from app.services.user_service import UserService
        user_service = UserService(db)
        mobile_check = user_service.ensure_unique_active_mobile(target_member.phone_number, request.member_id)
        if not mobile_check.get("success"):
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": mobile_check.get("error", "Mobile number validation failed"),
                    "requires_mobile_update": True
                }
            )
        
        # Find and validate coupon/PIN
        coupon = db.query(Coupon).filter(
            Coupon.id == request.pin_id,
            Coupon.status == 'Active'
        ).first()
        
        if not coupon:
            raise HTTPException(status_code=404, detail="PIN not found or not available")
        
        # Get package configuration
        package_type_str = coupon.package_type  # '15000', '7500', '1000', '500'
        package_name = COUPON_PACKAGE_MAP.get(package_type_str)
        if not package_name or package_name not in PACKAGE_SYSTEM:
            raise HTTPException(status_code=400, detail=f"Invalid package type: {package_type_str}")
        
        config = PACKAGE_SYSTEM[package_name]
        
        # Update target member package_points
        target_member.package_points = config['points']
        
        # CRITICAL: Set activation_date on user
        activation_time = get_indian_time()
        target_member.activation_date = activation_time
        target_member.coupon_status = 'Activated'
        
        # Mark coupon as used
        coupon.status = 'Redeemed'
        coupon.activation_date = activation_time
        
        # DC Protocol (Feb 2026): ALL income (Direct Referral, Guru Dakshina, Ved Income)
        # is generated by midnight scheduler ONLY. No real-time income creation at activation.
        # The midnight scheduler will pick up this activation via activation_date check.
        
        db.commit()
        
        return {
            "success": True,
            "message": f"PIN successfully activated for {target_member.name}!",
            "data": {
                "member_id": target_member.id,
                "package_points": target_member.package_points,
                "package_type": config['display_name']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating PIN: {str(e)}"
        )

@router.get("/api/search-users")
async def api_search_users(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/search-users
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_search_users
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/search-users",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/banner-data")
async def banner_data(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/banner-data
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::banner_data
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/banner-data",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/api/earnings-data")
async def api_earnings_data(
    user_id: str = None,
    period: int = 30,
    category: str = "all",
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/earnings-data
    Returns earnings transaction data from the transaction table
    """
    from sqlalchemy import and_, func
    from app.models.transaction import Transaction
    from datetime import datetime, timedelta
    
    # Get transactions for the user
    query = db.query(Transaction).filter(Transaction.referrer_id == current_user.id)
    
    # Apply time period filter
    if period:
        start_date = datetime.now() - timedelta(days=int(period))
        query = query.filter(Transaction.timestamp >= start_date)
    
    # Apply category filter
    if category and category != "all":
        category_map = {
            "direct": "Direct Referral",
            "matching": "Matching Referral",
            "ved": "Ved Income",
            "guru": "Guru Dakshina"
        }
        if category in category_map:
            query = query.filter(Transaction.transaction_type == category_map[category])
    
    transactions = query.order_by(Transaction.timestamp.desc()).all()
    
    # Format transactions for display
    transaction_list = []
    for txn in transactions:
        transaction_list.append({
            "id": txn.id,
            "date": txn.timestamp.strftime("%Y-%m-%d"),
            "type": txn.transaction_type,
            "amount": float(txn.amount),
            "referred_user": txn.referred_user_id
        })
    
    return {
        "success": True,
        "transactions": transaction_list,
        "total": len(transaction_list)
    }

@router.get("/api/earnings-chart-data")
async def api_earnings_chart_data(
    user_id: str = None,
    period: int = 30,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/earnings-chart-data
    Returns earnings chart data aggregated by date and type
    """
    from sqlalchemy import and_, func
    from app.models.transaction import Transaction
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Get transactions for the user
    start_date = datetime.now() - timedelta(days=int(period))
    transactions = db.query(Transaction).filter(
        and_(
            Transaction.referrer_id == current_user.id,
            Transaction.timestamp >= start_date
        )
    ).order_by(Transaction.timestamp).all()
    
    # Aggregate data by date and type
    daily_data = defaultdict(lambda: {
        "direct_referral": 0,
        "matching_income": 0,
        "ved_income": 0,
        "guru_dakshina": 0
    })
    
    for txn in transactions:
        date_key = txn.timestamp.strftime("%Y-%m-%d")
        
        if txn.transaction_type == "Direct Referral":
            daily_data[date_key]["direct_referral"] += float(txn.amount)
        elif txn.transaction_type == "Matching Referral":
            daily_data[date_key]["matching_income"] += float(txn.amount)
        elif txn.transaction_type == "Ved Income":
            daily_data[date_key]["ved_income"] += float(txn.amount)
        elif txn.transaction_type == "Guru Dakshina":
            daily_data[date_key]["guru_dakshina"] += float(txn.amount)
    
    # Generate date labels
    labels = []
    direct_referral = []
    matching_income = []
    ved_income = []
    guru_dakshina = []
    
    for i in range(int(period)):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(date)
        
        data = daily_data.get(date, {
            "direct_referral": 0,
            "matching_income": 0,
            "ved_income": 0,
            "guru_dakshina": 0
        })
        
        direct_referral.append(data["direct_referral"])
        matching_income.append(data["matching_income"])
        ved_income.append(data["ved_income"])
        guru_dakshina.append(data["guru_dakshina"])
    
    return {
        "success": True,
        "labels": labels,
        "direct_referral": direct_referral,
        "matching_income": matching_income,
        "ved_income": ved_income,
        "guru_dakshina": guru_dakshina
    }

@router.get("/api/expense-upload-permissions")
async def api_expense_upload_permissions(
    
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    API - GET /api/expense-upload-permissions
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::api_expense_upload_permissions
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/api/expense-upload-permissions",
        "method": "GET",
        "role_required": "API",
        "error_code": "NOT_IMPLEMENTED"
    }
    )
