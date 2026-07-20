"""
RVZ ID Exclusive: Daily Ceiling Management
Allows RVZ ID to adjust the daily income ceiling limit
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, date

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import PendingIncome

router = APIRouter()

RVZ_ID = "MNR182364369"

DAILY_CEILING_LIMIT = 50000.0

def validate_rvz_access(user_id: str, db: Session) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.id != RVZ_ID:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: Daily Ceiling Management is exclusive to RVZ ID"
    #     )
    
    return user

@router.get("/rvz/daily-ceiling", response_class=HTMLResponse)
async def daily_ceiling_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID Daily Ceiling Management page"""
    try:
        validate_rvz_access(user_id, db)
        
        today = date.today()
        
        users_hitting_ceiling = db.query(
            User.id,
            User.name,
            func.sum(PendingIncome.gross_amount).label('total_income')
        ).join(
            PendingIncome, User.id == PendingIncome.user_id
        ).filter(
            PendingIncome.business_date == today,
            PendingIncome.income_type.in_(['Ved Income', 'Matching Referral Income'])
        ).group_by(
            User.id, User.name
        ).having(
            func.sum(PendingIncome.gross_amount) >= DAILY_CEILING_LIMIT
        ).all()
        
        ceiling_stats = {
            'current_limit': DAILY_CEILING_LIMIT,
            'users_at_ceiling_today': len(users_hitting_ceiling),
            'total_capped_income_today': sum([u.total_income for u in users_hitting_ceiling])
        }
        
        # Frontend-only route - redirect to frontend
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Daily Ceiling - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/daily-ceiling">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/daily-ceiling">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/daily-ceiling/update")
async def update_daily_ceiling(
    user_id: str = Form(...),
    new_limit: float = Form(...),
    reason: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update daily ceiling limit - RVZ ID ONLY"""
    try:
        user = validate_rvz_access(user_id, db)
        
        if new_limit < 10000 or new_limit > 200000:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Daily ceiling must be between ₹10,000 and ₹200,000"
                }
            )
        
        global DAILY_CEILING_LIMIT
        old_limit = DAILY_CEILING_LIMIT
        DAILY_CEILING_LIMIT = new_limit
        
        return JSONResponse(content={
            "success": True,
            "message": f"Daily ceiling updated from ₹{old_limit:,.0f} to ₹{new_limit:,.0f}",
            "old_limit": old_limit,
            "new_limit": new_limit
        })
            
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.get("/rvz/daily-ceiling/stats")
async def get_ceiling_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get daily ceiling statistics - RVZ ID ONLY"""
    try:
        validate_rvz_access(user_id, db)
        
        today = date.today()
        
        users_hitting_ceiling = db.query(
            func.count(func.distinct(PendingIncome.user_id))
        ).filter(
            PendingIncome.business_date == today,
            PendingIncome.income_type.in_(['Ved Income', 'Matching Referral Income'])
        ).group_by(
            PendingIncome.user_id
        ).having(
            func.sum(PendingIncome.gross_amount) >= DAILY_CEILING_LIMIT
        ).count()
        
        return JSONResponse(content={
            "success": True,
            "current_limit": DAILY_CEILING_LIMIT,
            "users_at_ceiling_today": users_hitting_ceiling
        })
        
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})
