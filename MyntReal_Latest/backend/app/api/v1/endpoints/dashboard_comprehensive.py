"""
Comprehensive Dashboard API Endpoints for FastAPI
Preserves Flask dashboard functionality with real-time Reference System data
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, require_admin, require_finance_admin
from app.models.user import User
from app.services.dashboard_service import DashboardService
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService
from app.services.award_service import AwardService

router = APIRouter()

@router.get("/user/{user_id}/comprehensive")
async def get_user_comprehensive_dashboard(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive user dashboard with all 9 sections
    Preserves Flask dashboard structure with real-time Reference System data
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    dashboard_service = DashboardService(db)
    dashboard_data = dashboard_service.get_user_dashboard(user_id)
    
    if "error" in dashboard_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=dashboard_data["error"]
        )
    
    return {
        "success": True,
        "dashboard": dashboard_data,
        "access_level": "owner" if current_user.id == user_id else "admin"
    }

@router.get("/user/{user_id}/financial-summary")
async def get_user_financial_summary(
    user_id: str,
    month: Optional[str] = None,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed financial summary with all 4 income streams
    Preserves Flask financial calculation logic
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Get comprehensive income summary
    income_summary = reference_service.get_comprehensive_income_summary(user_id, month)
    
    # Get financial history
    financial_history = user_service.get_user_financial_history(user_id, limit=10)
    
    if "error" in income_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=income_summary["error"]
        )
    
    return {
        "success": True,
        "income_summary": income_summary,
        "recent_transactions": financial_history.get("transactions", []),
        "financial_totals": financial_history.get("summary", {})
    }

@router.get("/user/{user_id}/team-statistics")
async def get_user_team_statistics(
    user_id: str,
    include_tree: bool = False,
    tree_levels: int = 5,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive team statistics and binary tree data
    Preserves Flask team management functionality
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Get team counts
    team_counts = reference_service.get_team_counts(user_id)
    
    # Get team hierarchy if requested
    team_tree = None
    if include_tree:
        team_tree = reference_service.get_team_tree(user_id, tree_levels)
    
    # Get team member list
    team_list = user_service.get_user_team_list(user_id, levels=3)
    
    return {
        "success": True,
        "team_statistics": {
            "binary_tree_counts": team_counts,
            "team_tree": team_tree,
            "team_hierarchy": team_list.get("team_hierarchy", []),
            "direct_referral_count": len([member for level in team_list.get("team_hierarchy", []) if member.get("level") == 1])
        }
    }

@router.get("/user/{user_id}/award-progress")
async def get_user_award_progress(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive award progress for direct and matching awards
    Preserves Flask award system tracking
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    award_service = AwardService(db)
    
    # Get comprehensive award summary
    award_summary = award_service.get_user_award_summary(user_id)
    
    if "error" in award_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=award_summary["error"]
        )
    
    return {
        "success": True,
        "award_data": award_summary
    }

@router.get("/user/{user_id}/bonanza-status")
async def get_user_bonanza_status(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's bonanza campaign participation status
    Preserves Flask bonanza system functionality
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    award_service = AwardService(db)
    
    # Get active bonanzas
    active_bonanzas = award_service.get_active_bonanzas()
    
    # Get user progress in each active bonanza
    user_participations = []
    for bonanza in active_bonanzas:
        progress = award_service.get_user_bonanza_progress(user_id, bonanza["id"])
        if progress.get("enrolled", False):
            user_participations.append(progress)
    
    return {
        "success": True,
        "bonanza_data": {
            "active_bonanzas": active_bonanzas,
            "user_participations": user_participations,
            "participation_count": len(user_participations)
        }
    }

@router.get("/admin/system-dashboard")
async def get_admin_system_dashboard(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive admin dashboard with system-wide statistics
    Preserves Flask admin dashboard functionality
    """
    dashboard_service = DashboardService(db)
    admin_dashboard = dashboard_service.get_admin_dashboard(current_user.id)
    
    if "error" in admin_dashboard:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=admin_dashboard["error"]
        )
    
    return {
        "success": True,
        "admin_dashboard": admin_dashboard
    }

@router.get("/admin/user-analytics")
async def get_admin_user_analytics(
    month: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed user analytics for admin dashboard
    Preserves Flask admin analytics functionality
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    # Get user growth analytics
    user_service = UserService(db)
    
    # Search for recent users
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users = db.query(User).filter(
        User.registration_date >= thirty_days_ago
    ).count()
    
    # Get top performers
    dashboard_service = DashboardService(db)
    admin_data = dashboard_service.get_admin_dashboard(current_user.id)
    
    return {
        "success": True,
        "analytics": {
            "monthly_growth": recent_users,
            "period": month,
            "system_health": admin_data.get("admin_dashboard_sections", {}).get("system_statistics", {}),
            "financial_overview": admin_data.get("admin_dashboard_sections", {}).get("financial_overview", {}),
            "top_performers": admin_data.get("admin_dashboard_sections", {}).get("top_performers", {})
        }
    }

@router.get("/realtime/dashboard-summary/{user_id}")
async def get_realtime_dashboard_summary(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get real-time dashboard summary for quick updates
    Optimized for frequent polling from frontend
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    from datetime import datetime
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Get essential data only (optimized for speed)
    team_counts = reference_service.get_team_counts(user_id)
    current_month = datetime.now().strftime("%Y-%m")
    income_summary = reference_service.get_comprehensive_income_summary(user_id, current_month)
    
    user = user_service.get_user_by_id(user_id)
    
    return {
        "success": True,
        "summary": {
            "user_id": user_id,
            "user_name": user.name if user else "Unknown",
            "team_totals": {
                "left": team_counts["left_count"],
                "right": team_counts["right_count"],
                "total": team_counts["total_count"]
            },
            "monthly_income": income_summary["total_monthly_income"],
            "income_streams": {
                "direct": income_summary["income_streams"]["direct_referral"].get("total_income", 0),
                "matching": income_summary["income_streams"]["matching_referral"].get("total_income", 0),
                "ved": income_summary["income_streams"]["ved_income"].get("ved_amount", 0),
                "guru": income_summary["income_streams"]["guru_dakshina"].get("guru_dakshina_amount", 0)
            },
            "last_updated": datetime.now().isoformat()
        }
    }