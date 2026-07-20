"""
Gift-Wise Status API Endpoints
DC Protocol compliant aggregation across all award types (Direct, Matching, Bonanza)
Finance Admin and RVZ Supreme ONLY access
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user, RoleChecker
from app.models.user import User
from app.services.award_processing_service import AwardProcessingService

router = APIRouter()

# Custom role checker: Finance Admin, RVZ ID, and VGK4U staff ONLY
require_finance_or_rvz = RoleChecker(["Finance Admin", "RVZ ID", "VGK4U"])

# AWARDS RESET DATE - Oct 21, 2025 Reset Logic (DC Protocol)
# Only awards from users activated ON or AFTER this date are shown
AWARDS_RESET_DATE = date(2025, 10, 21)


class GiftWiseStatusResponse(BaseModel):
    """Response model for gift-wise aggregated data (PROCUREMENT PIPELINE ONLY)"""
    gift_name: str
    award_type_breakdown: str  # e.g., "Direct: 5, Matching: 3, Bonanza: 2"
    won_people: int  # Unique users who qualified (rejected awards excluded)
    claimed_people: int  # Unique users who received (Delivered)
    total_count: int  # Total awards for this gift (rejected excluded)
    pending_approval: int  # Count in Pending Approval status
    admin_approved: int  # Count in Admin Approved status
    ordered: int  # Count in Procurement Pending status
    dispatched: int  # Count in Processed for Dispatch status
    delivered: int  # Count in Delivered status
    budget: float  # Total budgeted amount
    actual_spent: float  # Total actual cost paid
    variance: float  # Budget - Actual
    variance_percent: float  # ((Budget - Actual) / Budget) * 100
    average_cost_config: float  # Average budgeted cost from config


class GiftWiseStatusSummary(BaseModel):
    """Summary totals across all gifts"""
    total_won: int
    total_claimed: int
    total_budget: float
    total_spent: float
    total_variance: float


def normalize_status_sql() -> str:
    """
    DC Protocol: SQL CASE statement to normalize legacy statuses
    Mirrors frontend normalizeDCProtocolStatus() function
    """
    return """
    CASE processed_status
        WHEN 'Super Admin Approved' THEN 'Procurement Pending'
        WHEN 'RVZ Approved' THEN 'Procurement Pending'
        WHEN 'Purchased - Pending Delivery' THEN 'Processed for Dispatch'
        WHEN 'Finance Processed' THEN 'Processed for Dispatch'
        WHEN 'Delivered - Completed' THEN 'Delivered'
        WHEN 'RVZ Rejected' THEN 'Rejected'
        ELSE processed_status
    END
    """


@router.get("/gift-wise-status", response_model=Dict[str, Any])
async def get_gift_wise_status(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    award_types: Optional[str] = Query(None, description="Comma-separated award types: direct,matching,bonanza,bonanza_mnr2"),
    statuses: Optional[str] = Query(None, description="Comma-separated statuses"),
    package_tier: Optional[str] = Query(None, description="Package tier filter: Platinum,Gold,Silver"),
    search_gift: Optional[str] = Query(None, description="Search by gift name"),
    current_user: User = Depends(require_finance_or_rvz),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get gift-wise aggregated status across all award types
    
    DC Protocol Compliance:
    - REUSES AwardProcessingService.get_pending_awards_for_super_admin() for filtering
    - Applies _is_award_dynamically_achieved() logic (Oct 21 reset) like Awards Approval Queue
    - Aggregates already-filtered awards to ensure data matches Awards Approval Queue exactly
    
    Access: Finance Admin and RVZ Supreme ONLY
    """
    
    # DC PROTOCOL: Use Awards Approval Queue service to get filtered awards
    service = AwardProcessingService(db)
    
    # Parse status filter (match Awards Approval Queue parameter format)
    status_filter_list = statuses.split(',') if statuses else None
    
    # Fetch ALL awards using EXACT same logic as Awards Approval Queue
    # This includes _is_award_dynamically_achieved() filtering
    result = service.get_pending_awards_for_super_admin(
        award_type=None,  # Get all types
        status_filter=status_filter_list,
        skip=0,
        limit=10000  # High limit to get all awards for aggregation
    )
    
    # Extract data (service returns nested under 'data' key)
    data = result.get('data', {})
    all_awards = (
        data.get('direct_awards', []) + 
        data.get('matching_awards', []) + 
        data.get('bonanza_awards', [])
    )
    
    # Apply additional filters (date, gift name search, etc.)
    filtered_awards = []
    for award in all_awards:
        # Date filters
        if start_date and award.get('achieved_at'):
            if award['achieved_at'][:10] < start_date:
                continue
        if end_date and award.get('achieved_at'):
            if award['achieved_at'][:10] > end_date:
                continue
        
        # Gift name search
        if search_gift:
            gift_name = award.get('award_description') or award.get('award_name', '')
            if search_gift.lower() not in gift_name.lower():
                continue
        
        filtered_awards.append(award)
    
    # Aggregate by gift name
    from collections import defaultdict
    
    gift_aggregates = defaultdict(lambda: {
        'award_types': set(),
        'won_users': set(),
        'claimed_users': set(),
        'total_count': 0,
        'pending_approval': 0,
        'admin_approved': 0,
        'ready_for_procurement': 0,  # DC Protocol: Procurement Pending
        'ordered': 0,  # DC Protocol: Processed for Dispatch
        'dispatched': 0,  # DC Protocol: Dispatched
        'delivered': 0,
        'budget': 0.0,
        'actual_spent': 0.0
    })
    
    for award in filtered_awards:
        gift_name = award.get('award_description') or award.get('award_name', 'Unknown')
        award_type = award.get('award_type', 'unknown')
        status = award.get('processed_status', '')
        user_id = award.get('user_id')
        budgeted = award.get('budgeted_amount', 0)
        actual = award.get('actual_cost_paid', 0)
        
        # DC PROTOCOL: Use EXACT database status values - NO legacy normalization
        # This ensures all 3 pages show identical data from the database
        # Rejected awards should already be filtered by AwardProcessingService
        if status == 'Rejected' or 'Reject' in status:
            continue
        
        agg = gift_aggregates[gift_name]
        agg['award_types'].add(award_type)
        agg['won_users'].add(user_id)
        if status == 'Delivered':
            agg['claimed_users'].add(user_id)
        agg['total_count'] += 1
        
        # Status breakdown (DC Protocol)
        if status == 'Pending Approval':
            agg['pending_approval'] += 1
        elif status == 'Admin Approved':
            agg['admin_approved'] += 1
        elif status == 'Procurement Pending':
            agg['ready_for_procurement'] += 1  # RVZ Approved (waiting procurement)
        elif status == 'Processed for Dispatch':
            agg['ordered'] += 1  # Ordered (procurement complete, waiting dispatch)
        elif status == 'Dispatched':
            agg['dispatched'] += 1  # Dispatched (shipped, in transit)
        elif status == 'Delivered':
            agg['delivered'] += 1
        
        agg['budget'] += float(budgeted or 0)
        agg['actual_spent'] += float(actual or 0)
    
    # Format response
    gifts = []
    total_budget = 0.0
    total_spent = 0.0
    
    for gift_name, agg in sorted(gift_aggregates.items()):
        award_type_breakdown = ', '.join(f"{t}: {agg['total_count']}" for t in sorted(agg['award_types']))
        variance = agg['budget'] - agg['actual_spent']
        variance_percent = (variance / agg['budget'] * 100) if agg['budget'] > 0 else 0
        avg_config_price = agg['budget'] / agg['total_count'] if agg['total_count'] > 0 else 0
        
        # Calculate pending to order (awards not yet in procurement)
        pending_to_order = agg['total_count'] - agg['ready_for_procurement'] - agg['ordered'] - agg['dispatched'] - agg['delivered']
        
        gifts.append({
            'gift_name': gift_name,
            'award_type_breakdown': award_type_breakdown,
            'won_people': len(agg['won_users']),
            'claimed_people': len(agg['claimed_users']),
            'total_count': agg['total_count'],
            'pending_approval': agg['pending_approval'],
            'admin_approved': agg['admin_approved'],
            'pending_to_order': pending_to_order,
            'ready_for_procurement': agg['ready_for_procurement'],  # DC Protocol: RVZ Approved
            'ordered': agg['ordered'],  # DC Protocol: Ordered
            'dispatched': agg['dispatched'],  # DC Protocol: Dispatched
            'delivered': agg['delivered'],
            'budget': round(agg['budget'], 2),
            'actual_spent': round(agg['actual_spent'], 2),
            'variance': round(variance, 2),
            'variance_percent': round(variance_percent, 2),
            'average_cost_config': round(avg_config_price, 2)
        })
        
        total_budget += agg['budget']
        total_spent += agg['actual_spent']
    
    # Calculate totals
    all_won_users = set()
    all_claimed_users = set()
    for agg in gift_aggregates.values():
        all_won_users.update(agg['won_users'])
        all_claimed_users.update(agg['claimed_users'])
    
    return {
        "success": True,
        "data": {
            "gifts": gifts,
            "totals": {
                "total_won": len(all_won_users),
                "total_claimed": len(all_claimed_users),
                "total_budget": round(total_budget, 2),
                "total_spent": round(total_spent, 2),
                "total_variance": round(total_budget - total_spent, 2)
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/gift-wise-status-old-sql", response_model=Dict[str, Any])
async def get_gift_wise_status_old_sql(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    award_types: Optional[str] = Query(None, description="Comma-separated award types: direct,matching,bonanza,bonanza_mnr2"),
    statuses: Optional[str] = Query(None, description="Comma-separated statuses"),
    package_tier: Optional[str] = Query(None, description="Package tier filter: Platinum,Gold,Silver"),
    search_gift: Optional[str] = Query(None, description="Search by gift name"),
    current_user: User = Depends(require_finance_or_rvz),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    OLD SQL-BASED VERSION (DEPRECATED - DOES NOT MATCH AWARDS APPROVAL QUEUE)
    
    This version uses pure SQL aggregation without dynamic achievement filtering.
    Kept for reference but should not be used.
    """
    
    # Build filter conditions for OUTER query (CTE filtering)
    # All filters are applied AFTER the UNION ALL to avoid column name conflicts
    cte_filters = []
    params = {}
    
    # Date filters
    if start_date:
        cte_filters.append("achieved_at >= :start_date")
        params['start_date'] = start_date
    
    if end_date:
        cte_filters.append("achieved_at <= :end_date")
        params['end_date'] = end_date
    
    # Award type filter
    if award_types:
        types_list = [t.strip() for t in award_types.split(',')]
        cte_filters.append(f"award_type IN ({','.join([':type' + str(i) for i, _ in enumerate(types_list)])})")
        for i, t in enumerate(types_list):
            params[f'type{i}'] = t
    
    # Status filter (applied after normalization)
    if statuses:
        status_list = [s.strip() for s in statuses.split(',')]
        cte_filters.append(f"normalized_status IN ({','.join([':status' + str(i) for i, _ in enumerate(status_list)])})")
        for i, s in enumerate(status_list):
            params[f'status{i}'] = s
    
    # Package tier filter
    if package_tier:
        cte_filters.append("package_name = :package_tier")
        params['package_tier'] = package_tier
    
    # Gift name search
    if search_gift:
        cte_filters.append("LOWER(gift_name) LIKE :search_gift")
        params['search_gift'] = f"%{search_gift.lower()}%"
    
    # Build WHERE clause for CTE outer query
    # ALWAYS exclude rejected awards from this procurement pipeline page
    cte_filters.insert(0, "normalized_status != 'Rejected'")
    cte_where_clause = "WHERE " + " AND ".join(cte_filters)
    
    # DC Protocol: UNION ALL query across all 3 award tables with SQL-level status normalization
    # CRITICAL FIX: All filters applied in outer query to avoid column name conflicts
    # PROCUREMENT PIPELINE ONLY: Rejected awards completely excluded
    # DC PROTOCOL COMPLIANCE: Legacy pre-Oct 21 awards permanently hidden from all roles
    query = text(f"""
    WITH normalized_awards AS (
        -- Direct Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            dat.award_description as gift_name,
            'direct' as award_type,
            uap.processed_status,
            {normalize_status_sql()} as normalized_status,
            COALESCE(uap.budgeted_amount, dat.actual_price, 0) as budgeted_amount,
            COALESCE(uap.actual_cost_paid, 0) as actual_cost_paid,
            uap.user_id,
            uap.achieved_at,
            dat.actual_price as config_price
        FROM user_award_progress uap
        LEFT JOIN direct_award_tier dat ON uap.award_tier_id = dat.id
        WHERE (uap.is_legacy_pre_reset = false OR uap.is_legacy_pre_reset IS NULL)
        
        UNION ALL
        
        -- Matching Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            mat.award_description as gift_name,
            'matching' as award_type,
            umap.processed_status,
            {normalize_status_sql()} as normalized_status,
            COALESCE(umap.budgeted_amount, mat.actual_price, 0) as budgeted_amount,
            COALESCE(umap.actual_cost_paid, 0) as actual_cost_paid,
            umap.user_id,
            umap.achievement_date as achieved_at,
            mat.actual_price as config_price
        FROM user_matching_award_progress umap
        LEFT JOIN matching_award_tier mat ON umap.matching_award_tier_id = mat.id
        WHERE (umap.is_legacy_pre_reset = false OR umap.is_legacy_pre_reset IS NULL)
        
        UNION ALL
        
        -- Bonanza Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            COALESCE(
                NULLIF(dbh.award_name, ''),
                CASE WHEN dbh.reward_type = 'cash' 
                    THEN '₹' || CAST(COALESCE(dbh.reward_value_claimed, 0) AS INTEGER) || ' Cash'
                    ELSE dbh.reward_type
                END
            ) as gift_name,
            'bonanza' as award_type,
            dbh.processed_status,
            {normalize_status_sql()} as normalized_status,
            COALESCE(dbh.budgeted_amount, dbh.reward_value_claimed, 0) as budgeted_amount,
            COALESCE(dbh.actual_cost_paid, 0) as actual_cost_paid,
            dbh.user_id,
            dbh.claimed_at as achieved_at,
            COALESCE(dbh.budgeted_amount, dbh.reward_value_claimed, 0) as config_price
        FROM dynamic_bonanza_history dbh
        WHERE (dbh.is_legacy_pre_reset = false OR dbh.is_legacy_pre_reset IS NULL)
    ),
    filtered_awards AS (
        SELECT *,
            COUNT(*) OVER (PARTITION BY gift_name, award_type) as award_count
        FROM normalized_awards
        {cte_where_clause}
    )
    SELECT 
        gift_name,
        -- Award type breakdown
        STRING_AGG(DISTINCT award_type || ': ' || award_count, ', ') as award_type_breakdown,
        -- User metrics (Rejected awards already filtered out in CTE)
        COUNT(DISTINCT user_id) as won_people,
        COUNT(DISTINCT CASE WHEN normalized_status = 'Delivered' THEN user_id END) as claimed_people,
        COUNT(*) as total_count,
        -- Status breakdown (Procurement Pipeline Only - NO rejected column)
        COUNT(CASE WHEN normalized_status = 'Pending Approval' THEN 1 END) as pending_approval,
        COUNT(CASE WHEN normalized_status = 'Admin Approved' THEN 1 END) as admin_approved,
        COUNT(CASE WHEN normalized_status = 'Procurement Pending' THEN 1 END) as ordered,
        COUNT(CASE WHEN normalized_status = 'Processed for Dispatch' THEN 1 END) as dispatched,
        COUNT(CASE WHEN normalized_status = 'Delivered' THEN 1 END) as delivered,
        -- Financial metrics
        SUM(budgeted_amount) as budget,
        SUM(actual_cost_paid) as actual_spent,
        SUM(budgeted_amount) - SUM(actual_cost_paid) as variance,
        CASE 
            WHEN SUM(budgeted_amount) > 0 
            THEN ((SUM(budgeted_amount) - SUM(actual_cost_paid)) / SUM(budgeted_amount) * 100)
            ELSE 0 
        END as variance_percent,
        AVG(config_price) as average_cost_config
    FROM filtered_awards
    GROUP BY gift_name
    ORDER BY total_count DESC, gift_name
    """)
    
    # Execute query
    result = db.execute(query, params)
    rows = result.fetchall()
    
    # Convert to response format
    gifts = []
    total_budget = 0.0
    total_spent = 0.0
    
    for row in rows:
        gift_data = {
            "gift_name": row[0] or "Unknown Gift",
            "award_type_breakdown": row[1] or "",
            "won_people": row[2] or 0,
            "claimed_people": row[3] or 0,
            "total_count": row[4] or 0,
            "pending_approval": row[5] or 0,
            "admin_approved": row[6] or 0,
            "ordered": row[7] or 0,
            "dispatched": row[8] or 0,
            "delivered": row[9] or 0,
            "budget": float(row[10] or 0),
            "actual_spent": float(row[11] or 0),
            "variance": float(row[12] or 0),
            "variance_percent": round(float(row[13] or 0), 2),
            "average_cost_config": float(row[14] or 0)
        }
        gifts.append(gift_data)
        
        # Accumulate financial totals (per-gift sums are additive)
        total_budget += gift_data["budget"]
        total_spent += gift_data["actual_spent"]
    
    # DC PROTOCOL FIX: Calculate DISTINCT user counts across ALL filtered awards
    # Cannot sum per-gift counts because users may win multiple gifts
    # DC PROTOCOL COMPLIANCE: Legacy pre-Oct 21 awards permanently hidden from all roles
    totals_query = text(f"""
    WITH normalized_awards AS (
        -- Direct Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            uap.user_id,
            {normalize_status_sql()} as normalized_status,
            uap.achieved_at,
            dat.award_description as gift_name,
            'direct' as award_type
        FROM user_award_progress uap
        LEFT JOIN direct_award_tier dat ON uap.award_tier_id = dat.id
        WHERE (uap.is_legacy_pre_reset = false OR uap.is_legacy_pre_reset IS NULL)
        
        UNION ALL
        
        -- Matching Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            umap.user_id,
            {normalize_status_sql()} as normalized_status,
            umap.achievement_date as achieved_at,
            mat.award_description as gift_name,
            'matching' as award_type
        FROM user_matching_award_progress umap
        LEFT JOIN matching_award_tier mat ON umap.matching_award_tier_id = mat.id
        WHERE (umap.is_legacy_pre_reset = false OR umap.is_legacy_pre_reset IS NULL)
        
        UNION ALL
        
        -- Bonanza Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            dbh.user_id,
            {normalize_status_sql()} as normalized_status,
            dbh.claimed_at as achieved_at,
            COALESCE(
                NULLIF(dbh.award_name, ''),
                CASE WHEN dbh.reward_type = 'cash' 
                    THEN '₹' || CAST(COALESCE(dbh.reward_value_claimed, 0) AS INTEGER) || ' Cash'
                    ELSE dbh.reward_type
                END
            ) as gift_name,
            'bonanza' as award_type
        FROM dynamic_bonanza_history dbh
        WHERE (dbh.is_legacy_pre_reset = false OR dbh.is_legacy_pre_reset IS NULL)
    )
    SELECT 
        COUNT(DISTINCT user_id) as total_won,
        COUNT(DISTINCT CASE WHEN normalized_status = 'Delivered' THEN user_id END) as total_claimed
    FROM normalized_awards
    {cte_where_clause}
    """)
    
    totals_result = db.execute(totals_query, params)
    totals_row = totals_result.fetchone()
    
    return {
        "success": True,
        "data": {
            "gifts": gifts,
            "totals": {
                "total_won": totals_row[0] or 0,
                "total_claimed": totals_row[1] or 0,
                "total_budget": round(total_budget, 2),
                "total_spent": round(total_spent, 2),
                "total_variance": round(total_budget - total_spent, 2)
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/gift-wise-status/{gift_name}/details")
async def get_gift_details(
    gift_name: str,
    statuses: Optional[str] = Query(None, description="Comma-separated statuses to filter"),
    current_user: User = Depends(require_finance_or_rvz),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed award records for a specific gift (drill-down source data)
    
    DC Protocol: Reuses AwardProcessingService to match main Gift-Wise Status filtering
    PROCUREMENT PIPELINE ONLY: Shows only awards matching selected statuses
    Access: Finance Admin and RVZ Supreme ONLY
    """
    
    # DC PROTOCOL: Use same service as main endpoint to ensure consistency
    service = AwardProcessingService(db)
    
    # Parse status filter
    status_filter_list = statuses.split(',') if statuses else ['Procurement Pending', 'Processed for Dispatch']
    
    # Fetch awards using same filtering logic
    result = service.get_pending_awards_for_super_admin(
        award_type=None,
        status_filter=status_filter_list,
        skip=0,
        limit=10000
    )
    
    # Extract and filter by gift name
    data = result.get('data', {})
    all_awards = (
        data.get('direct_awards', []) + 
        data.get('matching_awards', []) + 
        data.get('bonanza_awards', [])
    )
    
    # Filter for this specific gift
    filtered_awards = [
        award for award in all_awards 
        if (award.get('award_description') or award.get('award_name', '')) == gift_name
    ]
    
    # Format for frontend
    details = []
    for award in filtered_awards:
        status = award.get('processed_status', '')
        # Normalize status
        if status in ['Super Admin Approved', 'RVZ Approved']:
            status = 'Procurement Pending'
        elif status in ['Purchased - Pending Delivery', 'Finance Processed']:
            status = 'Processed for Dispatch'
        elif status == 'Delivered - Completed':
            status = 'Delivered'
        
        details.append({
            "user_id": award.get('user_id'),
            "award_type": award.get('award_type', 'unknown').capitalize(),
            "status": status,
            "budgeted_amount": float(award.get('budgeted_amount') or 0),
            "actual_cost_paid": float(award.get('actual_cost_paid') or 0),
            "achieved_at": award.get('achieved_at'),
            "user_name": award.get('user_name')
        })
    
    return {
        "success": True,
        "gift_name": gift_name,
        "total_records": len(details),
        "details": details
    }


@router.get("/gift-wise-status/{gift_name}/details-old-sql")
async def get_gift_details_old_sql(
    gift_name: str,
    current_user: User = Depends(require_finance_or_rvz),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    OLD SQL-BASED DETAILS (DEPRECATED - DOES NOT FILTER BY DYNAMIC ACHIEVEMENT)
    """
    
    # DC Protocol: Two-stage CTE - UNION ALL then filter by gift_name in outer query
    # DC PROTOCOL COMPLIANCE: Legacy pre-Oct 21 awards permanently hidden from all roles
    query = text(f"""
    WITH all_awards AS (
        -- Direct Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            dat.award_description as gift_name,
            uap.user_id,
            'Direct' as award_type,
            uap.processed_status,
            COALESCE(uap.budgeted_amount, dat.actual_price, 0) as budgeted_amount,
            COALESCE(uap.actual_cost_paid, 0) as actual_cost_paid,
            uap.achieved_at,
            u.name as user_name
        FROM user_award_progress uap
        LEFT JOIN direct_award_tier dat ON uap.award_tier_id = dat.id
        LEFT JOIN "user" u ON uap.user_id = u.id
        WHERE (uap.is_legacy_pre_reset = false OR uap.is_legacy_pre_reset IS NULL)
        
        UNION ALL
        
        -- Matching Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            mat.award_description as gift_name,
            umap.user_id,
            'Matching' as award_type,
            umap.processed_status,
            COALESCE(umap.budgeted_amount, mat.actual_price, 0) as budgeted_amount,
            COALESCE(umap.actual_cost_paid, 0) as actual_cost_paid,
            umap.achievement_date as achieved_at,
            u.name as user_name
        FROM user_matching_award_progress umap
        LEFT JOIN matching_award_tier mat ON umap.matching_award_tier_id = mat.id
        LEFT JOIN "user" u ON umap.user_id = u.id
        WHERE (umap.is_legacy_pre_reset = false OR umap.is_legacy_pre_reset IS NULL)
        
        UNION ALL
        
        -- Bonanza Awards (DC PROTOCOL: Filter out legacy pre-Oct 21 awards)
        SELECT 
            dbh.reward_type as gift_name,
            dbh.user_id,
            'Bonanza' as award_type,
            dbh.processed_status,
            COALESCE(dbh.budgeted_amount, dbh.reward_value_claimed, 0) as budgeted_amount,
            COALESCE(dbh.actual_cost_paid, 0) as actual_cost_paid,
            dbh.claimed_at as achieved_at,
            u.name as user_name
        FROM dynamic_bonanza_history dbh
        LEFT JOIN "user" u ON dbh.user_id = u.id
        WHERE (dbh.is_legacy_pre_reset = false OR dbh.is_legacy_pre_reset IS NULL)
    )
    SELECT 
        user_id,
        award_type,
        {normalize_status_sql()} as status,
        budgeted_amount,
        actual_cost_paid,
        achieved_at,
        user_name
    FROM all_awards
    WHERE gift_name = :gift_name
        AND processed_status NOT IN ('Rejected', 'RVZ Rejected')
    ORDER BY achieved_at DESC
    """)
    
    result = db.execute(query, {"gift_name": gift_name})
    rows = result.fetchall()
    
    details = []
    for row in rows:
        details.append({
            "user_id": row[0],
            "award_type": row[1],
            "status": row[2],
            "budgeted_amount": float(row[3] or 0),
            "actual_cost_paid": float(row[4] or 0),
            "achieved_at": row[5].isoformat() if row[5] else None,
            "user_name": row[6]
        })
    
    return {
        "success": True,
        "gift_name": gift_name,
        "total_records": len(details),
        "details": details
    }
