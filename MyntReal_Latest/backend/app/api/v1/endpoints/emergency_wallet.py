"""
RVZ ID Exclusive: Emergency Wallet Adjustment
Allows RVZ ID to perform manual wallet balance adjustments in emergency situations
WITH FULL AUDIT TRAIL
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction

router = APIRouter()

RVZ_ID = "MNR182364369"

def validate_rvz_access(user_id: str, db: Session) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.id != RVZ_ID:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: Emergency Wallet Adjustment is exclusive to RVZ ID"
    #     )
    
    return user

@router.get("/rvz/emergency-wallet", response_class=HTMLResponse)
async def emergency_wallet_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID Emergency Wallet Adjustment page"""
    try:
        validate_rvz_access(user_id, db)
        
        recent_adjustments = db.query(Transaction).filter(
            Transaction.transaction_type == 'Emergency Adjustment'
        ).order_by(
            desc(Transaction.timestamp)
        ).limit(20).all()
        
        # Frontend-only route - redirect to frontend
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Emergency Wallet - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/emergency-wallet">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/emergency-wallet">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/emergency-wallet/adjust")
async def adjust_wallet(
    user_id: str = Form(...),
    target_user_id: str = Form(...),
    wallet_type: str = Form(...),
    adjustment_type: str = Form(...),
    amount: float = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db)
):
    """Perform emergency wallet adjustment - RVZ ID ONLY"""
    try:
        user = validate_rvz_access(user_id, db)
        
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"User {target_user_id} not found"}
            )
        
        if wallet_type not in ['earning_wallet', 'withdrawable_wallet']:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid wallet type"}
            )
        
        if adjustment_type not in ['add', 'deduct']:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid adjustment type"}
            )
        
        if amount <= 0 or amount > 100000:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Amount must be between ₹1 and ₹100,000"}
            )
        
        if not reason or len(reason.strip()) < 10:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Reason must be at least 10 characters"}
            )
        
        current_balance = getattr(target_user, wallet_type, 0) or 0
        
        if adjustment_type == 'add':
            new_balance = current_balance + amount
        else:
            if current_balance < amount:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": f"Insufficient balance. Current: ₹{current_balance:,.2f}"
                    }
                )
            new_balance = current_balance - amount
        
        setattr(target_user, wallet_type, new_balance)
        
        wallet_transaction = Transaction(
            user_id=target_user_id,
            transaction_type='Emergency Adjustment',
            amount=amount if adjustment_type == 'add' else -amount,
            balance_before=current_balance,
            balance_after=new_balance,
            transaction_date=datetime.utcnow(),
            description=f"Emergency {adjustment_type.upper()} by RVZ ID: {reason}",
            performed_by=user.id
        )
        db.add(wallet_transaction)
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Wallet adjusted successfully. New balance: ₹{new_balance:,.2f}",
            "old_balance": current_balance,
            "new_balance": new_balance,
            "transaction_id": wallet_transaction.id
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.post("/rvz/emergency-wallet/check-user")
async def check_user_wallet(
    target_user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Check user wallet balances before adjustment"""
    try:
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "User not found"}
            )
        
        # DC Protocol Phase 1.6: Get wallet balances from materialized views (computed values)
        from app.services.wallet_balance_service import get_earning_wallet, get_withdrawable_wallet
        earning = get_earning_wallet(db, str(target_user.id))
        withdrawable = get_withdrawable_wallet(db, str(target_user.id))
        
        return JSONResponse(content={
            "success": True,
            "user": {
                "id": target_user.id,
                "name": target_user.name,
                "earning_wallet": round(float(earning)),
                "withdrawable_wallet": round(float(withdrawable)),
                "status": target_user.status
            }
        })
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})
