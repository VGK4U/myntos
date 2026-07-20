"""
RVZ ID Exclusive: User Management
Delete users (single and bulk) with proper foreign key handling
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_rvz_id
from app.models.user import User

router = APIRouter()

@router.get("/rvz/user-management", response_class=HTMLResponse)
async def rvz_user_management_page(
    request: Request,
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    RVZ ID User Management page - Frontend-only route
    
    MIGRATION NOTE: This route is handled by frontend/static-server.js
    Backend only provides API endpoints for user management operations
    Direct backend access not supported - use frontend on port 5000
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Management - MNR</title>
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/rvz/user-management">
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>Redirecting to Frontend...</h2>
            <p>This page is now served by the frontend.</p>
            <p>If not redirected, <a href="http://127.0.0.1:5000/rvz/user-management">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
