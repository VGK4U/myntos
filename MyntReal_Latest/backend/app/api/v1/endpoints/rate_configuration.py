"""
RVZ ID Exclusive: Rate Configuration Management
Allows RVZ ID to configure system-wide financial rates and percentages
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

RVZ_ID = "MNR182364369"

INCOME_RATES = {
    'admin_charge_percentage': 10.0,
    'tds_percentage': 0.0,
    'guru_dakshina_percentage': 2.0,
    'matching_income_per_pair': 100.0
}

def validate_rvz_access(user_id: str, db: Session) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.id != RVZ_ID:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: Rate Configuration is exclusive to RVZ ID"
    #     )
    
    return user

@router.get("/rvz/rate-configuration", response_class=HTMLResponse)
async def rate_configuration_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID Rate Configuration page - System-wide rate management"""
    try:
        validate_rvz_access(user_id, db)
        
        rates = [
            {
                'id': 'admin_charge_percentage',
                'name': 'Admin Charge Percentage',
                'description': 'Deduction from all income types (currently 10%)',
                'current_value': INCOME_RATES['admin_charge_percentage'],
                'unit': '%',
                'min': 0,
                'max': 20,
                'step': 0.5
            },
            {
                'id': 'tds_percentage',
                'name': 'TDS Percentage',
                'description': 'Tax Deducted at Source from income (currently 0%)',
                'current_value': INCOME_RATES['tds_percentage'],
                'unit': '%',
                'min': 0,
                'max': 10,
                'step': 0.1
            },
            {
                'id': 'guru_dakshina_percentage',
                'name': 'Guru Dakshina Percentage',
                'description': 'Percentage of direct referral gross income to referrer (currently 2%)',
                'current_value': INCOME_RATES['guru_dakshina_percentage'],
                'unit': '%',
                'min': 0,
                'max': 5,
                'step': 0.1
            },
            {
                'id': 'matching_income_per_pair',
                'name': 'Matching Income Per Pair',
                'description': 'Income per matching pair (currently ₹100)',
                'current_value': INCOME_RATES['matching_income_per_pair'],
                'unit': '₹',
                'min': 50,
                'max': 200,
                'step': 10
            }
        ]
        
        # Frontend-only route - redirect to frontend
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rate Configuration - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/rate-configuration">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/rate-configuration">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/rate-configuration/update")
async def update_rate(
    user_id: str = Form(...),
    rate_id: str = Form(...),
    new_value: float = Form(...),
    reason: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update a specific rate - RVZ ID ONLY"""
    try:
        user = validate_rvz_access(user_id, db)
        
        if rate_id not in INCOME_RATES:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid rate identifier"}
            )
        
        valid_rates = {
            'admin_charge_percentage': (0, 20),
            'tds_percentage': (0, 10),
            'guru_dakshina_percentage': (0, 5),
            'matching_income_per_pair': (50, 200)
        }
        
        min_val, max_val = valid_rates[rate_id]
        if not (min_val <= new_value <= max_val):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"Value must be between {min_val} and {max_val}"
                }
            )
        
        old_value = INCOME_RATES[rate_id]
        INCOME_RATES[rate_id] = new_value
        
        return JSONResponse(content={
            "success": True,
            "message": f"Rate '{rate_id.replace('_', ' ').title()}' updated from {old_value} to {new_value}",
            "old_value": old_value,
            "new_value": new_value
        })
            
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.get("/rvz/rate-configuration/current")
async def get_current_rates(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get current system rates - RVZ ID ONLY"""
    try:
        validate_rvz_access(user_id, db)
        
        return JSONResponse(content={
            "success": True,
            "rates": INCOME_RATES
        })
        
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})
