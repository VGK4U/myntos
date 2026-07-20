"""
Finance Admin Endpoints - Auto-generated scaffold
Total endpoints: 2
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, Dict, Any
import io
import csv
from app.core.database import get_db
from app.core.rbac import require_finance_admin
from app.models.user import User
from app.models.coupon import PINPurchaseRequest
from app.models.transaction import Transaction
from app.models.base import get_indian_time

router = APIRouter()


@router.get("/finance/dashboard", response_class=HTMLResponse)
async def finance_dashboard(
    request: Request,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    Finance Admin Dashboard - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js (line 17156)
    Backend only provides API endpoints via /api/v1/admin/dashboard-stats
    Direct backend access not supported - use frontend on port 5000
    """
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Finance Dashboard - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/finance/dashboard">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This dashboard is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/finance/dashboard">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/accounts-admin/bonanza-approvals")
async def accounts_admin_bonanza_approvals(
    
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Finance Admin - GET /accounts-admin/bonanza-approvals
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::accounts_admin_bonanza_approvals
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/accounts-admin/bonanza-approvals",
        "method": "GET",
        "role_required": "Finance Admin",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/accounts-admin/approve-bonanza/{bonanza_id}")
async def accounts_admin_approve_bonanza_get(
    bonanza_id: str,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Finance Admin - GET /accounts-admin/approve-bonanza/<int:bonanza_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::accounts_admin_approve_bonanza
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/accounts-admin/approve-bonanza/<int:bonanza_id>",
        "method": "GET",
        "role_required": "Finance Admin",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.post("/accounts-admin/approve-bonanza/{bonanza_id}")
async def accounts_admin_approve_bonanza_post(
    bonanza_id: str,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Finance Admin - POST /accounts-admin/approve-bonanza/<int:bonanza_id>
    
    Status: NOT IMPLEMENTED
    TODO: Migrate logic from Flask app.py::accounts_admin_approve_bonanza
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
        "success": False,
        "message": "Endpoint not yet implemented - Migration in progress",
        "endpoint": "/accounts-admin/approve-bonanza/<int:bonanza_id>",
        "method": "POST",
        "role_required": "Finance Admin",
        "error_code": "NOT_IMPLEMENTED"
    }
    )

@router.get("/finance/pin-general.csv")
async def finance_pin_general_csv(
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """Export PIN purchase requests to CSV for Finance Admin"""
    try:
        # Get all PIN purchase requests
        requests = db.query(PINPurchaseRequest).join(
            User, PINPurchaseRequest.user_id == User.id
        ).order_by(PINPurchaseRequest.request_date.desc()).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Request ID', 'User ID', 'User Name', 'User Email', 
            'Package Type', 'Quantity', 'Total Amount', 'Transaction ID',
            'Status', 'Request Date', 'Super Admin Approved By', 
            'Super Admin Approved Date', 'Finance Validated By', 
            'Finance Validated Date', 'Rejection Reason'
        ])
        
        # Write data rows
        for req in requests:
            user = db.query(User).filter(User.id == req.user_id).first()
            
            total_amount_val = req.total_amount
            writer.writerow([
                req.id,
                req.user_id,
                user.name if user else 'Unknown',
                user.email if user else 'Unknown',
                req.package_type or '',
                req.quantity or 0,
                float(total_amount_val) if total_amount_val is not None else 0.0,
                req.transaction_id or '',
                req.status or '',
                req.request_date.isoformat() if req.request_date is not None else '',
                req.superadmin_approved_by or '',
                req.superadmin_approved_date.isoformat() if req.superadmin_approved_date is not None else '',
                req.finance_validated_by or '',
                req.finance_validated_date.isoformat() if req.finance_validated_date is not None else '',
                req.rejection_reason or ''
            ])
        
        # Prepare response
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pin_purchase_requests.csv"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {str(e)}"
        )
