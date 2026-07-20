"""
RVZ ID Endpoints - Auto-generated scaffold
Total endpoints: 28
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.core.database import get_db
from app.core.rbac import require_rvz_id
from app.models.user import User
import html

router = APIRouter()


@router.get("/rvz/admin-portal")
async def rvz_admin_portal(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/admin-portal
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_admin_portal
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/admin-portal",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/control-center")
async def rvz_control_center(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/control-center
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_control_center
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/control-center",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/popup-control")
async def rvz_popup_control_get(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    RVZ ID - Popup Control Page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js (line 6805)
    Backend only provides API endpoints for popup operations
    Direct backend access not supported - use frontend on port 5000
    """
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Popup Control - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/popup-control">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/popup-control">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/rvz/popup-control/create")
async def rvz_popup_control_create(
    user_id: str,
    title: str = Form(...),
    content: str = Form(...),
    target_page: str = Form(...),
    popup_type: str = Form("General"),
    popup_size: str = Form("Medium"),
    auto_close_seconds: int = Form(None),
    background_color: str = Form("#007bff"),
    text_color: str = Form("#ffffff"),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Create new popup message"""
    from app.models.banner import PopupMessage
    from datetime import datetime
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    try:
        new_popup = PopupMessage(
            title=title,
            content=content,
            target_page=target_page,
            popup_type=popup_type,
            popup_size=popup_size,
            auto_close_seconds=auto_close_seconds,
            background_color=background_color,
            text_color=text_color,
            is_active=is_active,
            status='Approved' if is_active else 'Draft',
            created_by=user_id,
            created_date=datetime.utcnow(),
            approved_by=user_id if is_active else None,
            approved_date=datetime.utcnow() if is_active else None
        )
        
        db.add(new_popup)
        db.commit()
        
        return {"success": True, "message": "Popup created successfully", "popup_id": new_popup.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}

@router.post("/rvz/popup-control/toggle")
async def rvz_popup_control_toggle(
    user_id: str,
    popup_id: int = Form(...),
    is_active: bool = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Toggle popup active status"""
    from app.models.banner import PopupMessage
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        return {"success": False, "message": "Popup not found"}
    
    popup.is_active = is_active
    popup.status = 'Approved' if is_active else 'Draft'
    db.commit()
    
    return {"success": True, "message": f"Popup {'activated' if is_active else 'deactivated'} successfully"}

@router.post("/rvz/popup-control/delete")
async def rvz_popup_control_delete(
    user_id: str,
    popup_id: int = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Delete popup message"""
    from app.models.banner import PopupMessage
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    popup = db.query(PopupMessage).filter(PopupMessage.id == popup_id).first()
    if not popup:
        return {"success": False, "message": "Popup not found"}
    
    db.delete(popup)
    db.commit()
    
    return {"success": True, "message": "Popup deleted successfully"}

@router.get("/rvz/calculation-management")
async def rvz_calculation_management_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/calculation-management
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_calculation_management
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/calculation-management",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/calculation-management")
async def rvz_calculation_management_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/calculation-management
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_calculation_management
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/calculation-management",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/coupon-popup-control")
async def rvz_coupon_popup_control_redirect_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/coupon-popup-control
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_coupon_popup_control_redirect
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/coupon-popup-control",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/coupon-popup-control")
async def rvz_coupon_popup_control_redirect_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/coupon-popup-control
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_coupon_popup_control_redirect
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/coupon-popup-control",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/company-earnings")
async def rvz_company_earnings_get(
    request: Request,
    user_id: str,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Company Earnings Dashboard with Complete Workflow"""
    from pathlib import Path
    from datetime import datetime, timedelta
    from decimal import Decimal
    from app.core.constants import ADMIN_DEDUCTION_RATE, TDS_DEDUCTION_RATE, TOTAL_DEDUCTION_RATE, NET_PAYOUT_RATE
    from app.models.transaction import Transaction, CompanyEarnings, Expense, DailyCostCalculation
    from sqlalchemy import func, and_
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Load templates
    TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "templates"
    
    # Date range setup
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_dt = datetime.now() - timedelta(days=30)
        start_date = start_dt.strftime("%Y-%m-%d")
    
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # ========== INCOME CALCULATIONS ==========
    
    # 1. Direct Referral Income
    direct_income = db.query(
        func.coalesce(func.sum(Transaction.amount), 0).label('total')
    ).filter(
        and_(
            Transaction.transaction_type == 'Direct Referral',
            Transaction.timestamp >= start_dt,
            Transaction.timestamp <= end_dt
        )
    ).scalar() or Decimal('0.00')
    
    # 2. Matching Referral Income
    matching_income = db.query(
        func.coalesce(func.sum(Transaction.amount), 0).label('total')
    ).filter(
        and_(
            Transaction.transaction_type == 'Matching Referral',
            Transaction.timestamp >= start_dt,
            Transaction.timestamp <= end_dt
        )
    ).scalar() or Decimal('0.00')
    
    # 3. Ved Income
    ved_income = db.query(
        func.coalesce(func.sum(Transaction.amount), 0).label('total')
    ).filter(
        and_(
            Transaction.transaction_type == 'Ved Income',
            Transaction.timestamp >= start_dt,
            Transaction.timestamp <= end_dt
        )
    ).scalar() or Decimal('0.00')
    
    # 4. Guru Dakshina
    guru_dakshina = db.query(
        func.coalesce(func.sum(Transaction.amount), 0).label('total')
    ).filter(
        and_(
            Transaction.transaction_type == 'Guru Dakshina',
            Transaction.timestamp >= start_dt,
            Transaction.timestamp <= end_dt
        )
    ).scalar() or Decimal('0.00')
    
    # Total Gross Income Paid to Users
    total_gross_income = direct_income + matching_income + ved_income + guru_dakshina
    
    # ========== DEDUCTIONS (Company Earnings) ==========
    
    # Admin Deduction: 8% of all income
    admin_deduction = total_gross_income * Decimal('0.08')
    
    # TDS Deduction: 2% of all income
    tds_deduction = total_gross_income * Decimal('0.02')
    
    # Total Standard Deductions (10%)
    total_standard_deductions = admin_deduction + tds_deduction
    
    # ========== CEILING EXCESS EARNINGS ==========
    
    # Company earnings from daily ceiling excess (₹50,000 limit)
    ceiling_earnings = db.query(
        func.coalesce(func.sum(CompanyEarnings.excess_amount), 0).label('total')
    ).filter(
        and_(
            CompanyEarnings.ceiling_date >= start_dt.date(),
            CompanyEarnings.ceiling_date <= end_dt.date()
        )
    ).scalar() or Decimal('0.00')
    
    # ========== TOTAL COMPANY REVENUE ==========
    
    total_company_revenue = total_standard_deductions + ceiling_earnings
    
    # ========== COMPANY PAYOUTS/EXPENSES ==========
    
    # 1. Regular Operational Expenses
    expenses = db.query(Expense).filter(
        and_(
            Expense.expense_date >= start_dt.date(),
            Expense.expense_date <= end_dt.date(),
            Expense.status == 'approved',
            Expense.is_deleted == False
        )
    ).all()
    
    expense_by_category = {}
    total_regular_expenses = Decimal('0.00')
    
    for expense in expenses:
        category = expense.category
        amount = Decimal(str(expense.amount))
        
        if category not in expense_by_category:
            expense_by_category[category] = Decimal('0.00')
        
        expense_by_category[category] += amount
        total_regular_expenses += amount
    
    # 2-8. Additional Expense Types (TO BE IMPLEMENTED)
    # These will be populated as we integrate additional payout systems
    direct_awards_paid = Decimal('0.00')
    matching_awards_paid = Decimal('0.00')
    total_awards_paid = Decimal('0.00')
    standard_allowance_paid = Decimal('0.00')
    car_allowance_paid = Decimal('0.00')
    total_field_allowances = Decimal('0.00')
    bonanza_rewards_paid = Decimal('0.00')
    withdrawals_paid = Decimal('0.00')
    ev_discounts_given = Decimal('0.00')
    training_discounts = Decimal('0.00')
    
    # TOTAL COMPANY EXPENSES (All Payouts)
    total_expenses = (
        total_regular_expenses +
        total_awards_paid +
        total_field_allowances +
        bonanza_rewards_paid +
        withdrawals_paid +
        ev_discounts_given +
        training_discounts
    )
    
    # ========== NET COMPANY PROFIT ==========
    
    net_company_profit = total_company_revenue - total_expenses
    
    # ========== USER-WISE TOP EARNERS ==========
    
    top_earners = db.query(
        Transaction.referrer_id,
        User.name,
        func.sum(Transaction.amount).label('total_earned')
    ).join(
        User, Transaction.referrer_id == User.id
    ).filter(
        and_(
            Transaction.timestamp >= start_dt,
            Transaction.timestamp <= end_dt
        )
    ).group_by(
        Transaction.referrer_id,
        User.name
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(10).all()
    
    # ========== INCOME TYPE BREAKDOWN ==========
    
    income_breakdown = [
        {
            'type': 'Direct Referral',
            'gross_amount': float(direct_income),
            'admin_deduction': float(direct_income * ADMIN_DEDUCTION_RATE),
            'tds_deduction': float(direct_income * TDS_DEDUCTION_RATE),
            'net_to_users': float(direct_income * NET_PAYOUT_RATE),
            'company_share': float(direct_income * TOTAL_DEDUCTION_RATE)
        },
        {
            'type': 'Matching Referral',
            'gross_amount': float(matching_income),
            'admin_deduction': float(matching_income * ADMIN_DEDUCTION_RATE),
            'tds_deduction': float(matching_income * TDS_DEDUCTION_RATE),
            'net_to_users': float(matching_income * NET_PAYOUT_RATE),
            'company_share': float(matching_income * TOTAL_DEDUCTION_RATE)
        },
        {
            'type': 'Ved Income',
            'gross_amount': float(ved_income),
            'admin_deduction': float(ved_income * ADMIN_DEDUCTION_RATE),
            'tds_deduction': float(ved_income * TDS_DEDUCTION_RATE),
            'net_to_users': float(ved_income * NET_PAYOUT_RATE),
            'company_share': float(ved_income * TOTAL_DEDUCTION_RATE)
        },
        {
            'type': 'Guru Dakshina',
            'gross_amount': float(guru_dakshina),
            'admin_deduction': float(guru_dakshina * ADMIN_DEDUCTION_RATE),
            'tds_deduction': float(guru_dakshina * TDS_DEDUCTION_RATE),
            'net_to_users': float(guru_dakshina * NET_PAYOUT_RATE),
            'company_share': float(guru_dakshina * TOTAL_DEDUCTION_RATE)
        }
    ]
    
    # Frontend-only route - redirect to frontend
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Company Earnings - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/company-earnings">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/company-earnings">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.get("/rvz/create-user-testing")
async def rvz_create_user_testing_get(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    RVZ ID - Create Test Users Page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for test user generation
    Direct backend access not supported - use frontend on port 5000
    """
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Test Users - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/create-user-testing">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/create-user-testing">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/rvz/create-user-testing/generate")
async def rvz_create_user_testing_generate(
    user_id: str,
    count: int = Form(...),
    prefix: str = Form("TEST"),
    referrer_id: str = Form(None),
    package_status: str = Form("Inactive"),
    create_tree: bool = Form(False),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Generate test users"""
    from app.models.user import User
    from werkzeug.security import generate_password_hash
    import random
    import string
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    if count > 100:
        return {"success": False, "message": "Maximum 100 users at a time"}
    
    created_users = []
    current_referrer = referrer_id or RVZ_ID
    
    try:
        for i in range(count):
            # Generate unique MNR ID
            mnr_id = f"MNR{random.randint(100000000, 999999999)}"
            while db.query(User).filter(User.id == mnr_id).first():
                mnr_id = f"MNR{random.randint(100000000, 999999999)}"
            
            # Create test user
            test_user = User(
                id=mnr_id,
                first_name=f"{prefix}{i+1:03d}",
                last_name="User",
                email=f"{prefix.lower()}{i+1:03d}@test.local",
                password=generate_password_hash("Test@123"),
                referral_id=current_referrer,
                coupon_status=package_status,
                user_type="User"
            )
            
            db.add(test_user)
            created_users.append(mnr_id)
            
            # If create_tree, next user refers to this one
            if create_tree:
                current_referrer = mnr_id
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully created {count} test users",
            "users_created": count,
            "first_user_id": created_users[0] if created_users else None,
            "last_user_id": created_users[-1] if created_users else None
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error creating test users: {str(e)}"}

@router.post("/rvz/create-user-testing")
async def rvz_create_user_testing_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/create-user-testing
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_create_user_testing
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/create-user-testing",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/user-activation-control")
async def rvz_user_activation_control_get(
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - User Activation Control Page"""
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Get inactive and active users for the UI
    inactive_users = db.query(User).filter(User.coupon_status == 'Inactive').limit(100).all()
    active_users = db.query(User).filter(User.coupon_status == 'Active').limit(100).all()
    
    # Build escaped table rows for inactive users
    inactive_rows = ''.join([f'''
        <tr>
            <td>{html.escape(str(user.id))}</td>
            <td>{html.escape(user.name or '')}</td>
            <td>
                <button class="btn btn-sm btn-success" onclick='activateUser({html.escape(repr(str(user.id)))}, {html.escape(repr(user.name or ''))})'>
                    Activate
                </button>
            </td>
        </tr>
    ''' for user in inactive_users])
    
    # Build escaped table rows for active users
    active_rows = ''.join([f'''
        <tr>
            <td>{html.escape(str(user.id))}</td>
            <td>{html.escape(user.name or '')}</td>
            <td><span class="badge bg-success">Active</span></td>
        </tr>
    ''' for user in active_users[:20]])
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ User Activation Control</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>🎯 RVZ User Activation Control</h2>
        <p class="text-muted">Activate users without PIN requirement</p>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-warning">
                        <h5>📝 Inactive Users ({len(inactive_users)})</h5>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {inactive_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5>✅ Active Users ({len(active_users)})</h5>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {active_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
    
    <script>
    async function activateUser(userId, userName) {{
        if (!confirm(`Activate user ${{userName}} (${{userId}})?`)) return;
        
        try {{
            const response = await fetch('/api/v1/rvz/user-activation/activate', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                credentials: 'include',
                body: JSON.stringify({{
                    user_id: userId,
                    activate_without_pin: true,
                    reason: 'RVZ manual activation'
                }})
            }});
            
            const data = await response.json();
            
            if (response.ok) {{
                alert(`✅ ${{data.message}}`);
                window.location.reload();
            }} else {{
                alert(`❌ Error: ${{data.detail || 'Activation failed'}}`);
            }}
        }} catch (error) {{
            alert(`❌ Error: ${{error.message}}`);
        }}
    }}
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/rvz/user-activation-control")
async def rvz_user_activation_control_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/user-activation-control
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_user_activation_control
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/user-activation-control",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/brand-level-management")
async def rvz_brand_level_management_get(
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Brand/Level Management Page"""
    
    # Decode JWT token from user_id parameter
    from app.core.security import SecurityManager
    try:
        payload = SecurityManager.verify_token(user_id)
        if not payload:
            raise HTTPException(status_code=403, detail="Invalid token")
        actual_user_id = payload.get("sub")
        if not actual_user_id:
            raise HTTPException(status_code=403, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if actual_user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    recent_users = db.query(User).order_by(User.registration_date.desc()).limit(30).all()
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Brand/Level Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>🏆 RVZ Brand/Level Management</h2>
        <p class="text-muted">Update user brands and levels</p>
        
        <div class="row mt-4">
            <div class="col-md-5">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5>📝 Update Brand/Level</h5>
                    </div>
                    <div class="card-body">
                        <form id="brandLevelForm">
                            <div class="mb-3">
                                <label class="form-label">User ID</label>
                                <input type="text" class="form-control" id="userId" placeholder="MNR182364369" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Brand</label>
                                <input type="text" class="form-control" id="brand" placeholder="Enter brand name">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Level</label>
                                <select class="form-control" id="level">
                                    <option value="">Select Level</option>
                                    <option value="Bronze">Bronze</option>
                                    <option value="Silver">Silver</option>
                                    <option value="Gold">Gold</option>
                                    <option value="Platinum">Platinum</option>
                                    <option value="Diamond">Diamond</option>
                                    <option value="Executive">Executive</option>
                                    <option value="Premium">Premium</option>
                                    <option value="Elite">Elite</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Reason</label>
                                <input type="text" class="form-control" id="reason" value="RVZ brand/level update">
                            </div>
                            <button type="submit" class="btn btn-primary">Update</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-7">
                <div class="card">
                    <div class="card-header bg-secondary text-white">
                        <h5>👥 Recent Users</h5>
                    </div>
                    <div class="card-body" style="max-height: 500px; overflow-y: auto;">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Brand</th>
                                    <th>Level</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f'''
                                <tr>
                                    <td>{user.id}</td>
                                    <td>{user.name}</td>
                                    <td>{getattr(user, 'brand', 'N/A')}</td>
                                    <td>{getattr(user, 'level', 'N/A')}</td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary" onclick="selectUser('{user.id}', '{getattr(user, 'brand', '')}', '{getattr(user, 'level', '')}')">
                                            Select
                                        </button>
                                    </td>
                                </tr>
                                ''' for user in recent_users])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
    
    <script>
    function selectUser(userId, brand, level) {{
        document.getElementById('userId').value = userId;
        document.getElementById('brand').value = brand || '';
        document.getElementById('level').value = level || '';
    }}
    
    document.getElementById('brandLevelForm').addEventListener('submit', async (e) => {{
        e.preventDefault();
        
        const userId = document.getElementById('userId').value;
        const brand = document.getElementById('brand').value;
        const level = document.getElementById('level').value;
        const reason = document.getElementById('reason').value;
        
        if (!brand && !level) {{
            alert('Please enter at least Brand or Level');
            return;
        }}
        
        if (!confirm(`Update brand/level for user ${{userId}}?`)) return;
        
        try {{
            const response = await fetch('/api/v1/rvz/brand-level/update', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                }},
                body: JSON.stringify({{
                    user_id: userId,
                    brand: brand || undefined,
                    level: level || undefined,
                    reason: reason
                }})
            }});
            
            const data = await response.json();
            
            if (response.ok) {{
                alert(`✅ ${{data.message}}`);
                document.getElementById('brandLevelForm').reset();
                window.location.reload();
            }} else {{
                alert(`❌ Error: ${{data.detail || 'Update failed'}}`);
            }}
        }} catch (error) {{
            alert(`❌ Error: ${{error.message}}`);
        }}
    }});
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/rvz/brand-level-management")
async def rvz_brand_level_management_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/brand-level-management
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_brand_level_management
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/brand-level-management",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/reactivate-reassign")
async def rvz_reactivate_reassign_get(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    RVZ ID - Reactivate & Reassign Users Page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for reactivation/reassignment
    Direct backend access not supported - use frontend on port 5000
    """
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reactivate & Reassign - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/reactivate-reassign">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/reactivate-reassign">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/rvz/reactivate-reassign/reactivate")
async def rvz_reactivate_reassign_reactivate(
    user_id: str,
    target_user_id: str = Form(..., alias="user_id"),
    reason: str = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Reactivate user"""
    from app.models.user import User
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Find user
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        return {"success": False, "message": "User not found"}
    
    # Reactivate
    target_user.coupon_status = "Active"
    db.commit()
    
    return {"success": True, "message": f"User {target_user_id} reactivated successfully"}

@router.post("/rvz/reactivate-reassign/reassign")
async def rvz_reactivate_reassign_reassign(
    user_id: str,
    target_user_id: str = Form(..., alias="user_id"),
    new_referrer_id: str = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Reassign user's referrer"""
    from app.models.user import User
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Find users
    target_user = db.query(User).filter(User.id == target_user_id).first()
    new_referrer = db.query(User).filter(User.id == new_referrer_id).first()
    
    if not target_user:
        return {"success": False, "message": "Target user not found"}
    if not new_referrer:
        return {"success": False, "message": "New referrer not found"}
    
    # Reassign
    target_user.referral_id = new_referrer_id
    db.commit()
    
    return {"success": True, "message": f"User {target_user_id} reassigned to {new_referrer_id}"}

@router.post("/rvz/reactivate-reassign")
async def rvz_reactivate_reassign_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/reactivate-reassign
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reactivate_reassign
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reactivate-reassign",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/user-update-approvals")
async def rvz_user_update_approvals_get(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    RVZ ID - User Update Approvals Page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for approval operations
    Direct backend access not supported - use frontend on port 5000
    """
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Update Approvals - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/user-update-approvals">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/user-update-approvals">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/rvz/user-update-approvals/approve")
async def rvz_user_update_approvals_approve(
    user_id: str,
    update_id: int = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Approve user update"""
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Would approve the update in database
    return {"success": True, "message": "Update approved successfully"}

@router.post("/rvz/user-update-approvals/reject")
async def rvz_user_update_approvals_reject(
    user_id: str,
    update_id: int = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Reject user update"""
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Would reject the update in database
    return {"success": True, "message": "Update rejected"}

@router.post("/rvz/user-update-approvals")
async def rvz_user_update_approvals_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/user-update-approvals
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_user_update_approvals
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/user-update-approvals",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/payments-trigger")
async def rvz_payments_trigger_get(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    RVZ ID - Payments Trigger Page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for payment processing
    Direct backend access not supported - use frontend on port 5000
    """
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payments Trigger - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/payments-trigger">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/payments-trigger">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/rvz/payments-trigger/execute")
async def rvz_payments_trigger_execute(
    user_id: str,
    trigger_type: str = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ ID - Execute payment processing trigger"""
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # This would trigger actual income processing
    # For now, return success message
    messages = {
        "daily_income": "Daily income processing triggered successfully",
        "wallet_transfer": "Wallet transfer processing triggered successfully",
        "withdrawal_requests": "Withdrawal request generation triggered successfully"
    }
    
    return {
        "success": True,
        "message": messages.get(trigger_type, "Payment processing triggered"),
        "records_processed": 0,
        "trigger_type": trigger_type
    }

@router.post("/rvz/payments-trigger")
async def rvz_payments_trigger_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/payments-trigger
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_payments_trigger
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/payments-trigger",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/reset-awards")
async def rvz_reset_awards_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/reset-awards
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_awards
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-awards",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/reset-awards")
async def rvz_reset_awards_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/reset-awards
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_awards
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-awards",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/reset-users")
async def rvz_reset_users_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/reset-users
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_users
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-users",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/reset-users")
async def rvz_reset_users_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/reset-users
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_users
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-users",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/reset-center")
async def rvz_reset_center_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/reset-center
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_center
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-center",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/reset-center")
async def rvz_reset_center_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/reset-center
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_center
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-center",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/reset-earnings")
async def rvz_reset_earnings_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/reset-earnings
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_earnings
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-earnings",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/reset-earnings")
async def rvz_reset_earnings_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/reset-earnings
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_reset_earnings
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/reset-earnings",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/migrate-users")
async def rvz_migrate_users_get(
    user_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/migrate-users
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_migrate_users
    """
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/migrate-users",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/migrate-users")
async def rvz_migrate_users_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/migrate-users
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_migrate_users
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/migrate-users",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/download-migration-template")
async def download_migration_template(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/download-migration-template
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::download_migration_template
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/download-migration-template",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/download-create-user-template")
async def download_create_user_template(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/download-create-user-template
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::download_create_user_template
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/download-create-user-template",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/password-management")
async def rvz_password_management_get(
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Password Management Page"""
    
    # Get system stats
    total_users = db.query(User).count()
    recent_users = db.query(User).order_by(User.registration_date.desc()).limit(20).all()
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Password Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>🔐 RVZ Password Management</h2>
        <p class="text-muted">Reset passwords for users in the system</p>
        
        <div class="alert alert-info">
            <strong>Total Users:</strong> {total_users}
        </div>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5>🔑 Individual Password Reset</h5>
                    </div>
                    <div class="card-body">
                        <form id="individualResetForm">
                            <div class="mb-3">
                                <label class="form-label">User ID</label>
                                <input type="text" class="form-control" id="userId" placeholder="e.g., MNR182364369" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">New Password</label>
                                <input type="text" class="form-control" id="newPassword" placeholder="Enter new password" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Reason</label>
                                <input type="text" class="form-control" id="reason" placeholder="RVZ password reset" value="RVZ password reset">
                            </div>
                            <button type="submit" class="btn btn-primary">Reset Password</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-secondary text-white">
                        <h5>📋 Recent Users</h5>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f'''
                                <tr>
                                    <td>{user.id}</td>
                                    <td>{user.name}</td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary" onclick="fillUserId('{user.id}')">
                                            Select
                                        </button>
                                    </td>
                                </tr>
                                ''' for user in recent_users])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
    
    <script>
    function fillUserId(userId) {{
        document.getElementById('userId').value = userId;
    }}
    
    document.getElementById('individualResetForm').addEventListener('submit', async (e) => {{
        e.preventDefault();
        
        const userId = document.getElementById('userId').value;
        const newPassword = document.getElementById('newPassword').value;
        const reason = document.getElementById('reason').value;
        
        if (!confirm(`Reset password for user ${{userId}}?`)) return;
        
        try {{
            const response = await fetch('/api/v1/rvz/password-reset', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                }},
                body: JSON.stringify({{
                    user_id: userId,
                    new_password: newPassword,
                    reason: reason
                }})
            }});
            
            const data = await response.json();
            
            if (response.ok) {{
                alert(`✅ ${{data.message}}`);
                document.getElementById('individualResetForm').reset();
            }} else {{
                alert(`❌ Error: ${{data.detail || 'Password reset failed'}}`);
            }}
        }} catch (error) {{
            alert(`❌ Error: ${{error.message}}`);
        }}
    }});
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/rvz/password-management")
async def rvz_password_management_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/password-management
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_password_management
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/password-management",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/bulk-user-edit")
async def rvz_bulk_user_edit_get(
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Bulk User Edit Page"""
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Bulk User Edit</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container-fluid mt-4">
        <h2>✏️ RVZ Bulk User Edit</h2>
        <p class="text-muted">Search, filter, and edit multiple users</p>
        
        <div class="card mt-4">
            <div class="card-header bg-primary text-white">
                <h5>🔍 Search & Filter Users</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label">Search Term</label>
                        <input type="text" class="form-control" id="searchTerm" placeholder="User ID, Name, or Email">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">User Type</label>
                        <select class="form-control" id="userType">
                            <option value="">All</option>
                            <option value="User">User</option>
                            <option value="Admin">Admin</option>
                            <option value="RVZ ID">RVZ ID</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Account Status</label>
                        <select class="form-control" id="accountStatus">
                            <option value="">All</option>
                            <option value="Active">Active</option>
                            <option value="Inactive">Inactive</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">&nbsp;</label>
                        <button class="btn btn-primary w-100" onclick="searchUsers()">Search</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="resultsSection" class="mt-4" style="display: none;">
            <div class="card">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Search Results</h5>
                    <span id="resultCount" class="badge bg-light text-dark">0 users</span>
                </div>
                <div class="card-body">
                    <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                        <table class="table table-sm table-hover">
                            <thead class="sticky-top bg-white">
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Status</th>
                                    <th>KYC</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="resultsTable">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
    
    <!-- Edit Modal -->
    <div class="modal fade" id="editModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit User</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="hidden" id="editUserId">
                    <div class="mb-3">
                        <label class="form-label">Field to Edit</label>
                        <select class="form-control" id="editField">
                            <option value="kyc_status">KYC Status</option>
                            <option value="account_status">Account Status</option>
                            <option value="coupon_status">Coupon Status</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">New Value</label>
                        <input type="text" class="form-control" id="editValue" placeholder="Enter new value">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Reason</label>
                        <input type="text" class="form-control" id="editReason" value="RVZ bulk edit">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveEdit()">Save Changes</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    let editModal;
    
    document.addEventListener('DOMContentLoaded', function() {
        editModal = new bootstrap.Modal(document.getElementById('editModal'));
    });
    
    async function searchUsers() {
        const searchTerm = document.getElementById('searchTerm').value;
        const userType = document.getElementById('userType').value;
        const accountStatus = document.getElementById('accountStatus').value;
        
        try {
            const response = await fetch('/api/v1/rvz/bulk-edit/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                },
                body: JSON.stringify({
                    search_term: searchTerm || undefined,
                    search_fields: ['id', 'name', 'email'],
                    user_type: userType || undefined,
                    account_status: accountStatus || undefined,
                    page: 1,
                    page_size: 50,
                    sort_by: 'id',
                    sort_order: 'asc'
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                displayResults(data.users, data.pagination.total_count);
            } else {
                alert('Error: ' + (data.detail || 'Search failed'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }
    
    function displayResults(users, totalCount) {
        const resultsSection = document.getElementById('resultsSection');
        const resultsTable = document.getElementById('resultsTable');
        const resultCount = document.getElementById('resultCount');
        
        resultCount.textContent = totalCount + ' users';
        
        if (users.length === 0) {
            resultsTable.innerHTML = '<tr><td colspan="6" class="text-center">No users found</td></tr>';
        } else {
            resultsTable.innerHTML = users.map(user => `
                <tr>
                    <td>${user.id}</td>
                    <td>${user.name}</td>
                    <td>${user.email}</td>
                    <td><span class="badge bg-${user.account_status === 'Active' ? 'success' : 'secondary'}">${user.account_status}</span></td>
                    <td>${user.kyc_status}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="openEditModal('${user.id}', '${user.name}')">
                            Edit
                        </button>
                    </td>
                </tr>
            `).join('');
        }
        
        resultsSection.style.display = 'block';
    }
    
    function openEditModal(userId, userName) {
        document.getElementById('editUserId').value = userId;
        document.getElementById('editField').value = 'kyc_status';
        document.getElementById('editValue').value = '';
        editModal.show();
    }
    
    async function saveEdit() {
        const userId = document.getElementById('editUserId').value;
        const field = document.getElementById('editField').value;
        const value = document.getElementById('editValue').value;
        const reason = document.getElementById('editReason').value;
        
        if (!value) {
            alert('Please enter a new value');
            return;
        }
        
        try {
            const response = await fetch('/api/v1/rvz/bulk-edit/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                },
                body: JSON.stringify({
                    user_updates: [{
                        user_id: userId,
                        field_name: field,
                        new_value: value
                    }],
                    reason: reason
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert('✅ User updated successfully!');
                editModal.hide();
                searchUsers(); // Refresh results
            } else {
                alert('❌ Error: ' + (data.detail || 'Update failed'));
            }
        } catch (error) {
            alert('❌ Error: ' + error.message);
        }
    }
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/rvz/bulk-user-edit")
async def rvz_bulk_user_edit_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/bulk-user-edit
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_bulk_user_edit
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/bulk-user-edit",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/my-profile")
async def rvz_user_profile_get(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/my-profile
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_user_profile
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/my-profile",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/rvz/my-profile")
async def rvz_user_profile_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/my-profile
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_user_profile
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/my-profile",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/change-user-password")
async def rvz_change_user_password_get(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Change User Password Page"""
    from pathlib import Path
    from app.core.security import SecurityManager
    
    # Validate RVZ access - extract user ID from JWT token if needed
    actual_user_id = user_id
    
    # Check if user_id is a JWT token and extract the actual user ID
    if user_id and (user_id.startswith('eyJ') or len(user_id) > 20):
        try:
            payload = SecurityManager.verify_token(user_id)
            if payload and payload.get('sub'):
                actual_user_id = payload['sub']
        except:
            pass
    
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if actual_user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    # Load templates
    TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "templates"
    
    # Placeholder for recent resets (would come from audit log table)
    recent_resets = []
    
    # Frontend-only route - redirect to frontend
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Change User Password - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/password-change">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/password-change">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# Removed duplicate POST endpoints - use /api/v1/rvz/password/* endpoints instead

@router.get("/rvz/add-packages")
async def rvz_add_packages_get(
    user_id: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Package Assignment Page"""
    
    # Validate RVZ access
    RVZ_ID = "MNR182364369"
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_id != RVZ_ID:
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Package Assignment</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>📦 RVZ Package Assignment</h2>
        <p class="text-muted">Bulk assign packages to users</p>
        
        <div class="card mt-4">
            <div class="card-header bg-primary text-white">
                <h5>📝 Assign Packages</h5>
            </div>
            <div class="card-body">
                <form id="packageAssignmentForm">
                    <div class="mb-3">
                        <label class="form-label">User IDs (one per line)</label>
                        <textarea class="form-control" id="userIds" rows="5" placeholder="MNR182364370&#10;MNR182364371&#10;MNR182364372" required></textarea>
                        <small class="text-muted">Enter one User ID per line</small>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Package Type</label>
                        <select class="form-control" id="packageType" required>
                            <option value="">Select Package Type</option>
                            <option value="Active">Active</option>
                            <option value="Inactive">Inactive</option>
                            <option value="Premium">Premium</option>
                            <option value="Basic">Basic</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Reason</label>
                        <input type="text" class="form-control" id="reason" placeholder="RVZ package assignment" value="RVZ package assignment">
                    </div>
                    <button type="submit" class="btn btn-primary">Assign Packages</button>
                </form>
                
                <div id="result" class="mt-3" style="display: none;">
                    <div class="alert" id="resultAlert"></div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
    
    <script>
    document.getElementById('packageAssignmentForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const userIdsText = document.getElementById('userIds').value;
        const packageType = document.getElementById('packageType').value;
        const reason = document.getElementById('reason').value;
        
        // Parse user IDs
        const userIds = userIdsText.split('\\n').map(id => id.trim()).filter(id => id);
        
        if (userIds.length === 0) {
            alert('Please enter at least one User ID');
            return;
        }
        
        if (!confirm(`Assign ${packageType} package to ${userIds.length} users?`)) return;
        
        // Build user-package pairs
        const userPackagePairs = userIds.map(userId => ({
            user_id: userId,
            package_type: packageType
        }));
        
        try {
            const response = await fetch('/api/v1/rvz/packages/bulk-assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                },
                body: JSON.stringify({
                    user_package_pairs: userPackagePairs,
                    reason: reason
                })
            });
            
            const data = await response.json();
            
            const resultDiv = document.getElementById('result');
            const resultAlert = document.getElementById('resultAlert');
            
            if (response.ok) {
                resultAlert.className = 'alert alert-success';
                resultAlert.innerHTML = `✅ ${data.message}<br><small>Assigned: ${data.assigned_count}/${data.total_count}</small>`;
                document.getElementById('packageAssignmentForm').reset();
            } else {
                resultAlert.className = 'alert alert-danger';
                resultAlert.innerHTML = `❌ Error: ${data.detail || 'Package assignment failed'}`;
            }
            
            resultDiv.style.display = 'block';
        } catch (error) {
            const resultDiv = document.getElementById('result');
            const resultAlert = document.getElementById('resultAlert');
            resultAlert.className = 'alert alert-danger';
            resultAlert.innerHTML = `❌ Error: ${error.message}`;
            resultDiv.style.display = 'block';
        }
    });
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/rvz/add-packages")
async def rvz_add_packages_post(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - POST /rvz/add-packages
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_add_packages
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/add-packages",
        "method": "POST",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/add-packages/preview/{operation_key}")
async def rvz_add_packages_preview(
    operation_key: str,
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/add-packages/preview/<operation_key>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_add_packages_preview
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/add-packages/preview/<operation_key>",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/add-packages/results/{operation_key}")
async def rvz_add_packages_results(
    operation_key: str,
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/add-packages/results/<operation_key>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_add_packages_results
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/add-packages/results/<operation_key>",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz/dashboard")
async def rvz_unified_management_system(
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - Unified Master Dashboard with all features merged"""
    
    from app.models.transaction import Transaction
    from sqlalchemy import func
    
    # Get comprehensive system stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.activation_date.isnot(None)).count()
    inactive_users = total_users - active_users
    admin_users = db.query(User).filter(User.user_type.in_(['ADMIN', 'SUPER ADMIN', 'FINANCE ADMIN', 'RVZ ID'])).count()
    
    # Financial stats
    total_transactions = db.query(Transaction).count()
    total_earnings = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type.in_(['Direct Referral', 'Matching Referral', 'Ved', 'Guru Dakshina', 'Field Allowance'])
    ).scalar() or 0
    
    # System health (simple check)
    system_health = "100%" if total_users > 0 else "0%"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Supreme Admin Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        .feature-card {{ cursor: pointer; transition: transform 0.2s; }}
        .feature-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
        .stat-card {{ 
            border-left: 4px solid; 
            padding: 1.5rem;
            border-radius: 0.5rem;
            background: white;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            transition: all 0.15s ease-in-out;
        }}
        .stat-card:hover {{
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container-fluid mt-4">
        <!-- RVZ Master Alert Banner -->
        <div class="alert alert-danger mb-4" style="border: 2px solid #dc3545; background: linear-gradient(135deg, #dc3545, #b02a37);">
            <div class="d-flex align-items-center text-white">
                <i class="bi bi-crown-fill me-3" style="font-size: 1.8rem; color: #ffd700;"></i>
                <div>
                    <strong style="font-size: 1.2rem;">RVZ ID Master Control</strong><br>
                    <small>Supreme authority with unlimited system access. All actions are audited and logged.</small>
                    <br><small>Welcome, {current_user.name} ({current_user.id})</small>
                </div>
            </div>
        </div>
        
        <!-- Master System Overview Stats -->
        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="stat-card" style="border-left: 4px solid #dc3545;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-danger">{total_users}</h3>
                            <p class="mb-0">Total Users</p>
                        </div>
                        <i class="bi bi-people-fill text-danger" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stat-card" style="border-left: 4px solid #6f42c1;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-primary">{admin_users}</h3>
                            <p class="mb-0">Admin Users</p>
                        </div>
                        <i class="bi bi-shield-check text-primary" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stat-card" style="border-left: 4px solid #28a745;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-success">{active_users}</h3>
                            <p class="mb-0">Active Users</p>
                        </div>
                        <i class="bi bi-check-circle-fill text-success" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stat-card" style="border-left: 4px solid #17a2b8;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-info">{system_health}</h3>
                            <p class="mb-0">System Status</p>
                        </div>
                        <i class="bi bi-activity text-info" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Financial Overview -->
        <div class="row mb-4">
            <div class="col-md-4 mb-3">
                <div class="stat-card" style="border-left: 4px solid #198754;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-success">{total_transactions}</h3>
                            <p class="mb-0">Total Transactions</p>
                        </div>
                        <i class="bi bi-graph-up text-success" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-3">
                <div class="stat-card" style="border-left: 4px solid #0dcaf0;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-info">₹{total_earnings:,.2f}</h3>
                            <p class="mb-0">Total Earnings</p>
                        </div>
                        <i class="bi bi-cash-stack text-info" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-3">
                <div class="stat-card" style="border-left: 4px solid #fd7e14;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1 text-warning">{inactive_users}</h3>
                            <p class="mb-0">Inactive Users</p>
                        </div>
                        <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <h4 class="mb-3">🛠️ RVZ Features</h4>
        
        <div class="row">
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/user-activation-control'">
                    <div class="card-body text-center">
                        <h3>🎯</h3>
                        <h6>User Activation Control</h6>
                        <small class="text-muted">Activate users without PIN</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/password-management'">
                    <div class="card-body text-center">
                        <h3>🔐</h3>
                        <h6>Password Management</h6>
                        <small class="text-muted">Reset user passwords</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/add-packages'">
                    <div class="card-body text-center">
                        <h3>📦</h3>
                        <h6>Package Assignment</h6>
                        <small class="text-muted">Assign packages to users</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/brand-level-management'">
                    <div class="card-body text-center">
                        <h3>🏆</h3>
                        <h6>Brand/Level Management</h6>
                        <small class="text-muted">Update user brands and levels</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/bulk-user-edit'">
                    <div class="card-body text-center">
                        <h3>✏️</h3>
                        <h6>Bulk User Edit</h6>
                        <small class="text-muted">Edit multiple users</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/user-data-search'">
                    <div class="card-body text-center">
                        <h3>🔍</h3>
                        <h6>User Data Search</h6>
                        <small class="text-muted">Comprehensive user information</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/my-profile'">
                    <div class="card-body text-center">
                        <h3>👤</h3>
                        <h6>My Profile</h6>
                        <small class="text-muted">RVZ account settings</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/popup-control'">
                    <div class="card-body text-center">
                        <h3>🔔</h3>
                        <h6>Popup Control</h6>
                        <small class="text-muted">Manage system popups</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/payments-trigger'">
                    <div class="card-body text-center">
                        <h3>💰</h3>
                        <h6>Payment Triggers</h6>
                        <small class="text-muted">Manual payment processing</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/terms-conditions-management'">
                    <div class="card-body text-center">
                        <h3>📜</h3>
                        <h6>Terms & Conditions</h6>
                        <small class="text-muted">Manage T&C content</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card bg-danger bg-opacity-10 border-danger" onclick="location.href='/rvz/user-management?user_id={current_user.id}'">
                    <div class="card-body text-center">
                        <h3>🗑️</h3>
                        <h6 class="text-danger">User Management</h6>
                        <small class="text-muted">Delete users (single/bulk)</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/reset-users'">
                    <div class="card-body text-center">
                        <h3>🔄</h3>
                        <h6>Reset Users</h6>
                        <small class="text-muted">Reset user data</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/reset-earnings'">
                    <div class="card-body text-center">
                        <h3>💸</h3>
                        <h6>Reset Earnings</h6>
                        <small class="text-muted">Reset earnings data</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card feature-card" onclick="location.href='/rvz/migrate-users'">
                    <div class="card-body text-center">
                        <h3>📥</h3>
                        <h6>Migrate Users</h6>
                        <small class="text-muted">Import/migrate users</small>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-4 mb-4">
            <a href="/login" class="btn btn-danger">Logout</a>
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/rvz/user-data-search")
async def rvz_user_data_search_page(
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """RVZ ID - User Data Search Page"""
    import os
    
    # Get absolute path to project root, then to HTML file
    # This file is at: backend/app/api/v1/endpoints/scaffolds/rvz_id_routes.py
    # Go up 7 levels to reach /home/runner/workspace/
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))))
    html_path = os.path.join(project_root, "frontend", "templates", "rvz", "user_data_search.html")
    
    try:
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"User Data Search page not found at {html_path}"
        )

@router.get("/rvz/admin")
async def rvz_admin_portal_redirect(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz/admin
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_admin_portal_redirect
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz/admin",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/rvz-control")
async def rvz_control_center_redirect(
    
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID - GET /rvz-control
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::rvz_control_center_redirect
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/rvz-control",
        "method": "GET",
        "role_required": "RVZ ID",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

