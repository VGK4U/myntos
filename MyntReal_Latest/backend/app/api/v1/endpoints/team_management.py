"""
Team Management API Endpoints for FastAPI
Handles binary tree visualization, team statistics, and placement operations
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, require_admin
from app.models.user import User
from app.models.base import get_indian_time
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService
from app.services.award_service import AwardService

router = APIRouter()

@router.get("/user/{user_id}/binary-tree")
async def get_user_binary_tree(
    user_id: str,
    levels: int = Query(default=5, ge=1, le=10, description="Number of levels to display"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's binary tree structure with team members
    Preserves Flask binary tree visualization
    """
    # Validate access - users can view any tree, admins can also view any
    # Note: This matches dashboard behavior where users can see downline data
    pass  # Allow all authenticated users
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Get binary tree structure
    team_tree = reference_service.get_team_tree(user_id, levels)
    
    # Get FULL downline counts from cache (same as dashboard)
    from app.services.leg_metrics_cache_service import LegMetricsCacheService
    cache_service = LegMetricsCacheService(db)
    cached_metrics = cache_service.get_user_metrics(user_id)
    
    # If no cache, create on-demand
    if not cached_metrics:
        cached_metrics = cache_service.refresh_user_metrics(user_id, source='on_demand')
    
    # Use cached FULL downline counts (matches dashboard exactly)
    if cached_metrics:
        team_counts = {
            "left_count": cached_metrics.left_team_count,  # FULL left downline
            "right_count": cached_metrics.right_team_count,  # FULL right downline
            "total_count": cached_metrics.left_team_count + cached_metrics.right_team_count,
            "left_active_count": cached_metrics.left_active_count or 0,  # Active in left leg
            "right_active_count": cached_metrics.right_active_count or 0  # Active in right leg
        }
    else:
        # Fallback if cache fails
        team_counts = {"left_count": 0, "right_count": 0, "total_count": 0, "left_active_count": 0, "right_active_count": 0}
    
    return {
        "success": True,
        "tree_data": {
            "root_user": {
                "user_id": user_id,
                "name": target_user.name,
                "package_type": getattr(target_user, 'current_package_type', 'none')
            },
            "binary_tree": team_tree,
            "team_statistics": team_counts,  # Now uses FULL downline counts!
            "tree_levels": levels,
            "generated_at": get_indian_time().isoformat()
        }
    }

@router.get("/user/{user_id}/team-counts")
async def get_user_team_counts(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed team count statistics
    Preserves Flask team counting logic
    """
    # Validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Verify user exists
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Get team counts (ALL members)
    team_counts_all = reference_service.get_team_counts(user_id, active_only=False)
    
    # Get ACTIVE team counts
    team_counts_active = reference_service.get_team_counts(user_id, active_only=True)
    
    # Get direct referrals count
    direct_referrals = db.query(User).filter(User.referrer_id == user_id).count()
    
    # Calculate matching pairs for binary income (using ALL members - old logic)
    matching_pairs = min(team_counts_all["left_count"], team_counts_all["right_count"])
    carry_forward = {
        "left": team_counts_all["left_count"] - matching_pairs,
        "right": team_counts_all["right_count"] - matching_pairs
    }
    
    # Calculate effective matching referrals count (from scheduler logic)
    from app.core.scheduler import calculate_effective_matching_count
    matching_result = calculate_effective_matching_count(db, user_id)
    
    return {
        "success": True,
        "team_statistics": {
            "user_id": user_id,
            "binary_tree": team_counts_all,  # Total counts (all members)
            "binary_tree_active": {
                "left_count": team_counts_active["left_count"],
                "right_count": team_counts_active["right_count"],
                "total_count": team_counts_active["total_count"]
            },
            "direct_referrals": direct_referrals,
            "matching_calculation": {
                "matching_pairs": matching_pairs,
                "carry_forward": carry_forward
            },
            "matching_referrals_count": matching_result["effective_count"],  # NEW: Effective matching count
            "team_balance": {
                "left_percentage": (team_counts_all["left_count"] / max(team_counts_all["total_count"], 1)) * 100,
                "right_percentage": (team_counts_all["right_count"] / max(team_counts_all["total_count"], 1)) * 100,
                "is_balanced": abs(team_counts_all["left_count"] - team_counts_all["right_count"]) <= 5
            }
        }
    }

@router.get("/user/{user_id}/team-hierarchy")
async def get_user_team_hierarchy(
    user_id: str,
    levels: int = Query(default=3, ge=1, le=5, description="Number of levels to include"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's team hierarchy with member details
    Preserves Flask team hierarchy display
    """
    # Validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_service = UserService(db)
    
    # Get team hierarchy
    team_hierarchy = user_service.get_user_team_list(user_id, levels)
    
    if "error" in team_hierarchy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=team_hierarchy["error"]
        )
    
    return {
        "success": True,
        "team_hierarchy": team_hierarchy
    }

@router.post("/placement/auto-place")
async def auto_place_new_user(
    new_user_id: str,
    sponsor_id: str,
    preferred_position: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Auto-place a new user in the binary tree
    Admin-only functionality preserving Flask placement logic
    """
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Verify users exist
    new_user = user_service.get_user_by_id(new_user_id)
    sponsor = user_service.get_user_by_id(sponsor_id)
    
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New user not found."
        )
    
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sponsor user not found."
        )
    
    # Check if user is already placed
    existing_placement = reference_service.get_user_placement_as_child(new_user_id)
    if existing_placement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already placed in the binary tree."
        )
    
    # Validate preferred position
    if preferred_position and preferred_position.lower() not in ['left', 'right']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preferred position must be 'left' or 'right'."
        )
    
    # Perform auto-placement
    try:
        placement_result = reference_service.auto_place_user(
            new_user_id, 
            sponsor_id, 
            preferred_position.lower() if preferred_position else None
        )
        
        if not placement_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to place user in binary tree."
            )
        
        return {
            "success": True,
            "message": "User successfully placed in binary tree",
            "placement_details": placement_result["placement"],
            "performed_by": current_user.id
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Placement failed: {str(e)}"
        )

@router.get("/user/{user_id}/team-performance")
async def get_team_performance_metrics(
    user_id: str,
    period: Optional[str] = Query(default=None, description="Period in YYYY-MM format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive team performance metrics
    Preserves Flask team performance analysis
    """
    # Validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from datetime import datetime
    
    if not period:
        period = datetime.now().strftime("%Y-%m")
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    award_service = AwardService(db)
    
    # Get user info
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Get comprehensive income data
    income_summary = reference_service.get_comprehensive_income_summary(user_id, period)
    
    # Get team statistics
    team_counts = reference_service.get_team_counts(user_id)
    
    # Get award progress
    award_progress = award_service.get_user_award_summary(user_id)
    
    # Calculate performance metrics
    direct_referrals = db.query(User).filter(User.referrer_id == user_id).count()
    
    performance_metrics = {
        "team_growth": {
            "total_team_size": team_counts["total_count"],
            "left_team": team_counts["left_count"],
            "right_team": team_counts["right_count"],
            "direct_referrals": direct_referrals,
            "team_balance_ratio": team_counts["left_count"] / max(team_counts["right_count"], 1)
        },
        "income_performance": income_summary,
        "achievement_status": {
            "direct_awards": award_progress.get("achievement_summary", {}).get("direct_award_achievements", 0),
            "matching_awards": award_progress.get("achievement_summary", {}).get("matching_award_achievements", 0),
            "total_bonuses": award_progress.get("achievement_summary", {}).get("total_achievement_bonuses", 0)
        },
        "period": period,
        "performance_score": min(100, (
            (team_counts["total_count"] * 2) +
            (income_summary["total_monthly_income"] / 100) +
            (award_progress.get("achievement_summary", {}).get("total_achievements", 0) * 10)
        ))
    }
    
    return {
        "success": True,
        "performance_data": performance_metrics
    }

@router.get("/user/{user_id}/placement-history")
async def get_user_placement_history(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's placement history and details
    Preserves Flask placement tracking
    """
    # Validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from app.models.placement import PlacementLog
    
    reference_service = ReferenceService(db)
    user_service = UserService(db)
    
    # Get user's current placement
    current_placement = reference_service.get_user_placement_as_child(user_id)
    
    # Get placement logs
    placement_logs = db.query(PlacementLog).filter(
        PlacementLog.new_user_id == user_id
    ).order_by(PlacementLog.timestamp.desc()).limit(10).all()
    
    # Get parent user info if placed
    parent_info = None
    if current_placement:
        parent_user = user_service.get_user_by_id(current_placement.parent_id)
        if parent_user:
            parent_info = {
                "user_id": parent_user.id,
                "name": parent_user.name,
                "position": current_placement.side
            }
    
    placement_history = []
    for log in placement_logs:
        parent_user = user_service.get_user_by_id(log.target_parent_id) if log.target_parent_id else None
        placement_history.append({
            "placement_date": log.timestamp.isoformat(),
            "parent_id": log.target_parent_id,
            "parent_name": parent_user.name if parent_user else "Unknown",
            "position": log.side,
            "method": log.action,  # Using action field instead of placement_method
            "sponsor_id": log.sponsor_user_id
        })
    
    return {
        "success": True,
        "placement_data": {
            "user_id": user_id,
            "current_placement": {
                "is_placed": current_placement is not None,
                "parent_info": parent_info,
                "placement_date": current_placement.placed_at.isoformat() if current_placement else None,
                "status": current_placement.status if current_placement else None
            },
            "placement_history": placement_history
        }
    }

@router.get("/team/search")
async def search_team_members(
    query: str = Query(..., min_length=2, description="Search query for team members"),
    user_id: Optional[str] = Query(default=None, description="Search within specific user's team"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for team members across the binary tree
    Preserves Flask team search functionality
    """
    # If searching within specific user's team, validate access
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if user_id and current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_service = UserService(db)
    
    # Perform search
    search_results = user_service.search_users(query, limit=50)
    
    # If searching within specific team, filter results
    if user_id:
        reference_service = ReferenceService(db)
        team_tree = reference_service.get_team_tree(user_id, levels=10)
        
        # Extract all user IDs from the tree (simplified)
        def extract_user_ids(tree_node):
            user_ids = [tree_node["user_id"]]
            if tree_node["children"]["left"]:
                user_ids.extend(extract_user_ids(tree_node["children"]["left"]))
            if tree_node["children"]["right"]:
                user_ids.extend(extract_user_ids(tree_node["children"]["right"]))
            return user_ids
        
        team_user_ids = extract_user_ids(team_tree)
        search_results = [user for user in search_results if user["id"] in team_user_ids]
    
    return {
        "success": True,
        "search_results": {
            "query": query,
            "team_filter": user_id,
            "results": search_results,
            "result_count": len(search_results)
        }
    }