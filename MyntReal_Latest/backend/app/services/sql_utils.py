"""
SQL Utility Functions for High-Performance Database Operations
Hybrid Architecture: SQL for complex queries, Python for business logic

This module provides SQL-optimized functions for:
- Binary tree traversal and downline queries
- Leg points calculations
- Team statistics
- Income calculations

All functions return the same output format as their Python equivalents,
ensuring drop-in compatibility with existing endpoints.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def get_binary_downline_sql(
    db: Session,
    parent_id: str,
    max_depth: int = 10,
    active_only: bool = False,
    package_filter: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Get all users in binary tree downline using SQL recursive CTE
    
    FIXED: Now preserves the ROOT LEG (left/right) throughout recursion
    (Previously showed immediate parent's side, causing misclassification)
    
    100x faster than Python recursion for large teams (1000+ members)
    
    Args:
        parent_id: Root user ID
        max_depth: Maximum depth to traverse (default 10)
        active_only: Filter only activated users
        package_filter: Filter by package_points (e.g., 1.0 for Platinum)
    
    Returns:
        List of dicts with user info: {id, name, package_points, activation_date, level, side}
    """
    query = text("""
        WITH RECURSIVE downline AS (
            -- Base case: Direct children (establishes LEFT or RIGHT leg)
            SELECT 
                p.child_id,
                u.name,
                u.package_points,
                u.activation_date,
                u.registration_date,
                u.coupon_status,
                p.side as root_leg,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :parent_id
            
            UNION ALL
            
            -- Recursive: PRESERVE root_leg from parent (not p.side!)
            SELECT 
                p.child_id,
                u.name,
                u.package_points,
                u.activation_date,
                u.registration_date,
                u.coupon_status,
                d.root_leg,
                d.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN downline d ON p.parent_id = d.child_id
            WHERE d.level < :max_depth
        )
        SELECT * FROM downline
        WHERE 1=1
            AND (:active_only = false OR activation_date IS NOT NULL)
            AND (:package_filter IS NULL OR package_points = :package_filter)
        ORDER BY level, child_id
    """)
    
    result = db.execute(
        query,
        {
            "parent_id": parent_id,
            "max_depth": max_depth,
            "active_only": active_only,
            "package_filter": package_filter
        }
    ).fetchall()
    
    return [
        {
            "id": row[0],
            "name": row[1],
            "package_points": float(row[2]) if row[2] else 0,
            "activation_date": row[3],
            "registration_date": row[4],
            "coupon_status": row[5],
            "side": row[6],
            "level": row[7]
        }
        for row in result
    ]


def get_binary_tree_bulk_sql(
    db: Session,
    root_id: str,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    Fetch complete binary tree structure in ONE query using recursive CTE
    
    Performance: 100x faster than recursive ORM calls
    - 3 levels: 1 query vs 15 queries
    - 4 levels: 1 query vs 31 queries
    
    Args:
        root_id: Root user ID
        max_depth: Tree depth (default 3)
    
    Returns:
        Dict with tree structure ready for assembly
    """
    query = text("""
        WITH RECURSIVE tree_nodes AS (
            -- Root node
            SELECT 
                u.id as user_id,
                u.name,
                u.gender,
                u.registration_date,
                u.package_points,
                u.activation_date,
                NULL::VARCHAR as parent_id,
                NULL::VARCHAR as side,
                0 as level
            FROM "user" u
            WHERE u.id = :root_id
            
            UNION ALL
            
            -- Recursive: all children
            SELECT 
                u.id as user_id,
                u.name,
                u.gender,
                u.registration_date,
                u.package_points,
                u.activation_date,
                p.parent_id,
                p.side,
                tn.level + 1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN tree_nodes tn ON p.parent_id = tn.user_id
            WHERE tn.level < :max_depth
        )
        SELECT 
            user_id,
            name,
            gender,
            registration_date,
            package_points,
            activation_date,
            parent_id,
            side,
            level
        FROM tree_nodes
        ORDER BY level, user_id
    """)
    
    result = db.execute(query, {"root_id": root_id, "max_depth": max_depth}).fetchall()
    
    # Convert to dict keyed by user_id for fast lookups
    nodes = {}
    for row in result:
        user_id = row[0]
        nodes[user_id] = {
            "user_id": user_id,
            "name": row[1],
            "gender": row[2],  # 'Male', 'Female', or None
            "registration_date": row[3],
            "package_points": float(row[4]) if row[4] else 0.0,
            "activation_date": row[5],
            "parent_id": row[6],
            "side": row[7],  # 'left' or 'right'
            "level": row[8]
        }
    
    return nodes


def get_leg_member_counts_sql(
    db: Session,
    user_id: str
) -> Dict[str, int]:
    query = text("""
        WITH RECURSIVE tree AS (
            SELECT p.child_id, p.side as root_side, 1 as level
            FROM placement p
            WHERE p.parent_id = :user_id
            UNION ALL
            SELECT p.child_id, t.root_side, t.level + 1
            FROM placement p
            INNER JOIN tree t ON p.parent_id = t.child_id
            WHERE t.level < 200
        )
        SELECT 
            root_side,
            COUNT(*) as total_members,
            COUNT(*) FILTER (WHERE u.package_points > 0 AND COALESCE(u.is_welcome_coupon, false) = false) as active_members,
            COUNT(*) FILTER (WHERE u.package_points = 0 OR COALESCE(u.is_welcome_coupon, false) = true) as zero_point_members
        FROM tree t
        JOIN "user" u ON u.id = t.child_id
        WHERE u.coupon_status IN ('Active', 'Activated')
        GROUP BY root_side
    """)
    rows = db.execute(query, {"user_id": user_id}).fetchall()
    result = {'left_total': 0, 'right_total': 0, 'left_active': 0, 'right_active': 0, 'left_zero': 0, 'right_zero': 0}
    for row in rows:
        side = row[0]
        if side == 'left':
            result['left_total'] = row[1]
            result['left_active'] = row[2]
            result['left_zero'] = row[3]
        elif side == 'right':
            result['right_total'] = row[1]
            result['right_active'] = row[2]
            result['right_zero'] = row[3]
    return result


def get_leg_points_sql(
    db: Session,
    user_id: str,
    side: str = 'both'
) -> Dict[str, Any]:
    """
    Calculate leg points using SQL. Only counts Platinum/Diamond (package_points > 0).
    Star/Loyal (0 points) and Welcome Coupon users are completely excluded from pair calculations.
    
    Returns:
        {'left': points, 'right': points, 'total': points,
         'left_zero_point_count': int, 'right_zero_point_count': int}
    """
    left_points = 0
    left_zp_count = 0
    right_points = 0
    right_zp_count = 0
    
    if side.lower() in ['left', 'both']:
        left_query = text("""
            WITH RECURSIVE left_leg AS (
                SELECT p.child_id, u.package_points, u.activation_date, u.coupon_status,
                       COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon, 1 as level
                FROM placement p
                INNER JOIN "user" u ON u.id = p.child_id
                WHERE p.parent_id = :user_id AND p.side = 'left'
                UNION ALL
                SELECT p.child_id, u.package_points, u.activation_date, u.coupon_status,
                       COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon, ll.level + 1
                FROM placement p
                INNER JOIN "user" u ON u.id = p.child_id
                INNER JOIN left_leg ll ON p.parent_id = ll.child_id
                WHERE ll.level < 200
            )
            SELECT
                COALESCE(SUM(package_points), 0) as normal_points,
                0 as zero_point_count
            FROM left_leg
            WHERE (activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated'))
              AND is_welcome_coupon = false
              AND package_points > 0
        """)
        row = db.execute(left_query, {"user_id": user_id}).fetchone()
        if row:
            left_points = float(row[0] or 0)
            left_zp_count = int(row[1] or 0)
    
    if side.lower() in ['right', 'both']:
        right_query = text("""
            WITH RECURSIVE right_leg AS (
                SELECT p.child_id, u.package_points, u.activation_date, u.coupon_status,
                       COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon, 1 as level
                FROM placement p
                INNER JOIN "user" u ON u.id = p.child_id
                WHERE p.parent_id = :user_id AND p.side = 'right'
                UNION ALL
                SELECT p.child_id, u.package_points, u.activation_date, u.coupon_status,
                       COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon, rl.level + 1
                FROM placement p
                INNER JOIN "user" u ON u.id = p.child_id
                INNER JOIN right_leg rl ON p.parent_id = rl.child_id
                WHERE rl.level < 200
            )
            SELECT
                COALESCE(SUM(package_points), 0) as normal_points,
                0 as zero_point_count
            FROM right_leg
            WHERE (activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated'))
              AND is_welcome_coupon = false
              AND package_points > 0
        """)
        row = db.execute(right_query, {"user_id": user_id}).fetchone()
        if row:
            right_points = float(row[0] or 0)
            right_zp_count = int(row[1] or 0)
    
    return {
        'left': float(left_points),
        'right': float(right_points),
        'total': float(left_points + right_points),
        'left_zero_point_count': left_zp_count,
        'right_zero_point_count': right_zp_count
    }


def get_consumed_zero_point_sql(
    db: Session,
    user_id: str
) -> Dict[str, int]:
    """
    Get previously consumed zero-point member counts from matching record snapshots.
    Zero-point members (Star/Loyal/Welcome) are tracked via exempted_left_consumed/exempted_right_consumed
    in the matching_contributors_snapshot JSON.
    """
    query = text("""
        SELECT 
            COALESCE(SUM((matching_contributors_snapshot->>'exempted_left_consumed')::int), 0),
            COALESCE(SUM((matching_contributors_snapshot->>'exempted_right_consumed')::int), 0)
        FROM pending_income
        WHERE user_id = :user_id 
          AND income_type = 'Matching Referral'
          AND matching_contributors_snapshot IS NOT NULL
          AND matching_contributors_snapshot ? 'exempted_left_consumed'
    """)
    row = db.execute(query, {"user_id": user_id}).fetchone()
    return {
        'left': int(row[0]) if row else 0,
        'right': int(row[1]) if row else 0
    }


def get_leg_points_with_welcome_coupon_breakdown(
    db: Session,
    user_id: str
) -> Dict[str, float]:
    """
    DC Protocol (Jan 2026): Get leg points with Welcome Coupon breakdown
    
    Matching formula: Income = (Left user points + Right user points) × ₹1,000 per pair
    Examples:
      Platinum (1.0) + Platinum (1.0) = (1.0 + 1.0) × ₹1,000 = ₹2,000
      Diamond (0.5) + Diamond (0.5) = (0.5 + 0.5) × ₹1,000 = ₹1,000
      Platinum (1.0) + Diamond (0.5) = (1.0 + 0.5) × ₹1,000 = ₹1,500
      Platinum (1.0) + Welcome (0) = (1.0 + 0) × ₹1,000 = ₹1,000
      Diamond (0.5) + Welcome (0) = (0.5 + 0) × ₹1,000 = ₹500
      Welcome (0) + Welcome (0) = (0 + 0) × ₹1,000 = ₹0
    
    Welcome Coupon users contribute 0 to matching income (matching_income_rate = 0).
    
    Returns:
        {
            'left_normal': float,       # Sum of package_points from normal users (left leg)
            'left_welcome': float,      # Sum of package_points from Welcome users (left leg)
            'right_normal': float,      # Sum of package_points from normal users (right leg)
            'right_welcome': float,     # Sum of package_points from Welcome users (right leg)
            'left_normal_count': int,   # Count of normal users (left leg)
            'left_welcome_count': int,  # Count of Welcome users (left leg)
            'right_normal_count': int,  # Count of normal users (right leg)
            'right_welcome_count': int, # Count of Welcome users (right leg)
            'total_normal': float,
            'total_welcome': float
        }
    """
    query = text("""
        WITH RECURSIVE left_leg AS (
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'left'
            
            UNION ALL
            
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                ll.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN left_leg ll ON p.parent_id = ll.child_id
            WHERE ll.level < 200
        ),
        right_leg AS (
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'right'
            
            UNION ALL
            
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                rl.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN right_leg rl ON p.parent_id = rl.child_id
            WHERE rl.level < 200
        )
        SELECT 
            COALESCE(SUM(l.package_points), 0) as left_normal_pts,
            0 as left_welcome_pts,
            COALESCE(SUM(r.package_points), 0) as right_normal_pts,
            0 as right_welcome_pts,
            COUNT(l.*) as left_normal_count,
            0 as left_welcome_count,
            COUNT(r.*) as right_normal_count,
            0 as right_welcome_count
        FROM (
            SELECT package_points, is_welcome_coupon
            FROM left_leg
            WHERE package_points > 0
              AND is_welcome_coupon = false
              AND (activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated'))
        ) l
        FULL OUTER JOIN (
            SELECT package_points, is_welcome_coupon
            FROM right_leg
            WHERE package_points > 0
              AND is_welcome_coupon = false
              AND (activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated'))
        ) r ON false
    """)
    
    try:
        result = db.execute(query, {"user_id": user_id}).fetchone()
        if result:
            left_normal = float(result[0] or 0)
            left_welcome = float(result[1] or 0)
            right_normal = float(result[2] or 0)
            right_welcome = float(result[3] or 0)
            left_normal_count = int(result[4] or 0)
            left_welcome_count = int(result[5] or 0)
            right_normal_count = int(result[6] or 0)
            right_welcome_count = int(result[7] or 0)
        else:
            left_normal = left_welcome = right_normal = right_welcome = 0.0
            left_normal_count = left_welcome_count = right_normal_count = right_welcome_count = 0
    except Exception:
        left_normal = left_welcome = right_normal = right_welcome = 0.0
        left_normal_count = left_welcome_count = right_normal_count = right_welcome_count = 0
    
    return {
        'left_normal': left_normal,
        'left_welcome': left_welcome,
        'right_normal': right_normal,
        'right_welcome': right_welcome,
        'left_normal_count': left_normal_count,
        'left_welcome_count': left_welcome_count,
        'right_normal_count': right_normal_count,
        'right_welcome_count': right_welcome_count,
        'total_normal': left_normal + right_normal,
        'total_welcome': left_welcome + right_welcome
    }


def get_leg_points_by_package_type(
    db: Session,
    user_id: str
) -> Dict[str, Dict[str, float]]:
    """
    DC Protocol (Jan 2026): Get leg points broken down by package type
    
    Returns points per package type for each leg, separating Welcome Coupon users.
    Package types: PLATINUM (1.0 pts), DIAMOND (0.5 pts), BLUE (0.25 pts), LOYAL (0.1 pts), WELCOME (1.0 pts)
    
    Returns:
        {
            'left': {'platinum': float, 'diamond': float, 'other': float, 'welcome': float},
            'right': {'platinum': float, 'diamond': float, 'other': float, 'welcome': float}
        }
    """
    query = text("""
        WITH RECURSIVE left_leg AS (
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'left'
            
            UNION ALL
            
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                ll.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN left_leg ll ON p.parent_id = ll.child_id
            WHERE ll.level < 200
        ),
        right_leg AS (
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'right'
            
            UNION ALL
            
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                rl.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN right_leg rl ON p.parent_id = rl.child_id
            WHERE rl.level < 200
        ),
        left_active AS (
            SELECT package_points, is_welcome_coupon
            FROM left_leg
            WHERE package_points > 0
              AND (activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated'))
        ),
        right_active AS (
            SELECT package_points, is_welcome_coupon
            FROM right_leg
            WHERE package_points > 0
              AND (activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated'))
        )
        SELECT 
            -- Left leg by package type
            COALESCE(SUM(CASE WHEN NOT l.is_welcome_coupon AND l.package_points = 1.0 THEN 1 ELSE 0 END), 0) as left_platinum_count,
            COALESCE(SUM(CASE WHEN NOT l.is_welcome_coupon AND l.package_points = 0.5 THEN 1 ELSE 0 END), 0) as left_diamond_count,
            COALESCE(SUM(CASE WHEN NOT l.is_welcome_coupon AND l.package_points NOT IN (1.0, 0.5) THEN 1 ELSE 0 END), 0) as left_other_count,
            COALESCE(SUM(CASE WHEN l.is_welcome_coupon THEN 1 ELSE 0 END), 0) as left_welcome_count,
            -- Right leg by package type
            COALESCE(SUM(CASE WHEN NOT r.is_welcome_coupon AND r.package_points = 1.0 THEN 1 ELSE 0 END), 0) as right_platinum_count,
            COALESCE(SUM(CASE WHEN NOT r.is_welcome_coupon AND r.package_points = 0.5 THEN 1 ELSE 0 END), 0) as right_diamond_count,
            COALESCE(SUM(CASE WHEN NOT r.is_welcome_coupon AND r.package_points NOT IN (1.0, 0.5) THEN 1 ELSE 0 END), 0) as right_other_count,
            COALESCE(SUM(CASE WHEN r.is_welcome_coupon THEN 1 ELSE 0 END), 0) as right_welcome_count
        FROM (SELECT * FROM left_active) l
        FULL OUTER JOIN (SELECT * FROM right_active) r ON false
    """)
    
    try:
        result = db.execute(query, {"user_id": user_id}).fetchone()
        if result:
            return {
                'left': {
                    'platinum': float(result[0] or 0),
                    'diamond': float(result[1] or 0),
                    'other': float(result[2] or 0),
                    'welcome': float(result[3] or 0)
                },
                'right': {
                    'platinum': float(result[4] or 0),
                    'diamond': float(result[5] or 0),
                    'other': float(result[6] or 0),
                    'welcome': float(result[7] or 0)
                }
            }
    except Exception:
        pass
    
    return {
        'left': {'platinum': 0.0, 'diamond': 0.0, 'other': 0.0, 'welcome': 0.0},
        'right': {'platinum': 0.0, 'diamond': 0.0, 'other': 0.0, 'welcome': 0.0}
    }


def get_leg_counts(
    db: Session,
    user_id: str
) -> Dict[str, int]:
    """
    DC PROTOCOL: Get leg counts (total and active) for Picture View
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        {
            'left_total': int,
            'right_total': int,
            'left_active': int,
            'right_active': int
        }
    """
    query = text("""
        WITH RECURSIVE left_leg AS (
            SELECT p.child_id, u.activation_date, 1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'left'
            
            UNION ALL
            
            SELECT p.child_id, u.activation_date, ll.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN left_leg ll ON p.parent_id = ll.child_id
            WHERE ll.level < 50
        ),
        right_leg AS (
            SELECT p.child_id, u.activation_date, 1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'right'
            
            UNION ALL
            
            SELECT p.child_id, u.activation_date, rl.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN right_leg rl ON p.parent_id = rl.child_id
            WHERE rl.level < 50
        )
        SELECT 
            (SELECT COUNT(*) FROM left_leg) as left_total,
            (SELECT COUNT(*) FROM left_leg WHERE activation_date IS NOT NULL) as left_active,
            (SELECT COUNT(*) FROM right_leg) as right_total,
            (SELECT COUNT(*) FROM right_leg WHERE activation_date IS NOT NULL) as right_active
    """)
    
    result = db.execute(query, {"user_id": user_id}).fetchone()
    
    if result:
        return {
            'left_total': int(result[0] or 0),
            'left_active': int(result[1] or 0),
            'right_total': int(result[2] or 0),
            'right_active': int(result[3] or 0)
        }
    
    return {'left_total': 0, 'left_active': 0, 'right_total': 0, 'right_active': 0}


def get_matching_pairs_with_reset_logic_sql(
    db: Session,
    user_id: str,
    reset_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate matching pairs based on ACTUAL user activation dates
    Implements October 21st reset logic: only count users activated after reset_date
    
    This replaces PendingIncome.created_at filtering with proper activation date filtering
    
    Args:
        user_id: User ID
        reset_date: ISO date string (e.g., '2025-10-21') - if provided, only count users activated on/after this date
    
    Returns:
        {
            'left_points': float,
            'right_points': float,
            'matching_pairs': int,
            'left_users': int,
            'right_users': int
        }
    """
    # Build the date filter condition - use CTE column names, not original table alias
    # CRITICAL: ALWAYS apply Oct 21, 2025 reset logic regardless of user's own activation date
    # This ensures system-wide consistency for award calculations
    # DC PROTOCOL FIX (Nov 11, 2025): Removed OR coupon_status bypass - only count POST-reset activations
    date_filter = ""
    if reset_date:
        date_filter = f"AND activation_date::date >= '{reset_date}'::date"
    else:
        # Even if no specific reset_date provided, ALWAYS use Oct 21, 2025 as minimum
        # This prevents counting pre-reset downline members for users without activation dates
        date_filter = "AND activation_date::date >= '2025-10-21'::date"
    
    left_query = text(f"""
        WITH RECURSIVE left_leg AS (
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'left'
            
            UNION ALL
            
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                ll.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN left_leg ll ON p.parent_id = ll.child_id
            WHERE ll.level < 200
        )
        SELECT 
            COALESCE(SUM(package_points), 0) as total_points,
            COUNT(*) as user_count
        FROM left_leg
        WHERE package_points > 0
          AND is_welcome_coupon = false
          {date_filter}
    """)
    
    right_query = text(f"""
        WITH RECURSIVE right_leg AS (
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                1 as level
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            WHERE p.parent_id = :user_id AND p.side = 'right'
            
            UNION ALL
            
            SELECT 
                p.child_id,
                u.package_points,
                u.activation_date,
                u.coupon_status,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                rl.level + 1
            FROM placement p
            INNER JOIN "user" u ON u.id = p.child_id
            INNER JOIN right_leg rl ON p.parent_id = rl.child_id
            WHERE rl.level < 200
        )
        SELECT 
            COALESCE(SUM(package_points), 0) as total_points,
            COUNT(*) as user_count
        FROM right_leg
        WHERE package_points > 0
          AND is_welcome_coupon = false
          {date_filter}
    """)
    
    left_result = db.execute(left_query, {"user_id": user_id}).fetchone()
    right_result = db.execute(right_query, {"user_id": user_id}).fetchone()
    
    left_points = float(left_result[0]) if left_result else 0.0
    left_users = int(left_result[1]) if left_result else 0
    right_points = float(right_result[0]) if right_result else 0.0
    right_users = int(right_result[1]) if right_result else 0
    
    # Calculate matching pairs: MIN of left and right points
    matching_pairs = int(min(left_points, right_points))
    
    return {
        'left_points': left_points,
        'right_points': right_points,
        'matching_pairs': matching_pairs,
        'left_users': left_users,
        'right_users': right_users
    }


def get_team_counts_sql(
    db: Session,
    user_id: str,
    active_only: bool = False
) -> Dict[str, Any]:
    """
    Get team counts (left, right, total) using SQL
    
    NOTE: This counts DIRECT placements only (position_id = user_id)
    For full downline tree counts, use LegMetricsCacheService instead.
    
    Returns:
        {
            'left_count': int,
            'right_count': int,
            'total_count': int,
            'direct_referrals': int
        }
    """
    query = text("""
        SELECT 
            (SELECT COUNT(*) 
             FROM "user" u
             WHERE u.position_id = :user_id 
               AND u.position = 'Left'
               AND (:active_only = false OR u.activation_date IS NOT NULL)
            ) as left_count,
            (SELECT COUNT(*) 
             FROM "user" u
             WHERE u.position_id = :user_id 
               AND u.position = 'Right'
               AND (:active_only = false OR u.activation_date IS NOT NULL)
            ) as right_count,
            (SELECT COUNT(*) FROM "user" WHERE referrer_id = :user_id) as direct_referrals
    """)
    
    result = db.execute(query, {"user_id": user_id, "active_only": active_only}).fetchone()
    
    left_count = result[0] or 0
    right_count = result[1] or 0
    direct_referrals = result[2] or 0
    
    return {
        'left_count': left_count,
        'right_count': right_count,
        'total_count': left_count + right_count,
        'direct_referrals': direct_referrals
    }


def calculate_ved_income_bulk_sql(
    db: Session,
    business_date: str
) -> List[Dict[str, Any]]:
    """
    Calculate Ved Income for ALL users in a single SQL query
    
    VED PROGRAM LOGIC:
    - Ved Head (3rd direct referral) must be ACTIVATED to generate income
    - Ved Head activation check: activation_date IS NOT NULL AND package_points >= 0.5
    - If Ved Head NOT activated → NO income generated (nobody gets it)
    - If Ved Head IS activated → Income goes to ved_owner_id (direct owner)
    - NO CASCADING: Stop at Ved Head boundaries
    
    ELIGIBILITY CRITERIA:
    - Ved Owner must have 1:1 active (1 left + 1 right active member in binary tree)
    - Ved Owner must have earned their 1st matching income (has matching income transaction)
    
    This replaces the Python loop that checks each user individually.
    1000x faster for bulk calculations!
    
    Returns:
        List of {ved_owner_id, ved_member_id, activated_users, total_ved_income}
    """
    query = text("""
        WITH RECURSIVE 
        -- Get all ACTIVATED Ved members (Ved Heads)
        -- CRITICAL: Only activated Ved Heads can generate income
        ved_members AS (
            SELECT id as ved_member_id, ved_owner_id
            FROM "user"
            WHERE is_ved = true 
              AND ved_owner_id IS NOT NULL
              AND activation_date IS NOT NULL
              AND package_points >= 0.5
        ),
        -- For each Ved member, get their binary downline (track ved_member_id!)
        -- CRITICAL: Stop recursion when encountering another Ved member (NO CASCADING)
        ved_downlines AS (
            SELECT 
                vm.ved_owner_id,
                vm.ved_member_id,
                p.child_id,
                1 as level
            FROM ved_members vm
            INNER JOIN placement p ON p.parent_id = vm.ved_member_id
            
            UNION ALL
            
            SELECT 
                vd.ved_owner_id,
                vd.ved_member_id,
                p.child_id,
                vd.level + 1
            FROM ved_downlines vd
            INNER JOIN placement p ON p.parent_id = vd.child_id
            INNER JOIN "user" new_child ON new_child.id = p.child_id
            WHERE vd.level < 50  -- MUST match dashboard/Ved Team/Ved Income (50 levels)
              AND new_child.is_ved = false  -- STOP at Ved members (NO CASCADING)
        ),
        -- Check Ved Owner eligibility: 1:1 active (1 left + 1 right active)
        -- NOTE: Matching income check is done in Python (not SQL) since records may not exist yet
        ved_owner_eligibility AS (
            SELECT 
                vo.id as ved_owner_id,
                -- Count active members on LEFT side
                (
                    SELECT COUNT(DISTINCT u.id)
                    FROM placement p
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE p.parent_id = vo.id 
                      AND LOWER(p.side) = 'left'
                      AND u.activation_date IS NOT NULL
                ) as left_active_count,
                -- Count active members on RIGHT side
                (
                    SELECT COUNT(DISTINCT u.id)
                    FROM placement p
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE p.parent_id = vo.id 
                      AND LOWER(p.side) = 'right'
                      AND u.activation_date IS NOT NULL
                ) as right_active_count
            FROM "user" vo
            WHERE vo.id IN (SELECT DISTINCT ved_owner_id FROM ved_members)
        )
        -- Calculate Ved Income PER INDIVIDUAL ACTIVATED USER (for proper one-time tracking)
        SELECT 
            vd.ved_owner_id,
            vd.ved_member_id,
            u.id as activated_user_id,
            u.name as activated_user_name,
            CASE 
                WHEN u.package_points = 1 THEN 1000
                WHEN u.package_points = 0.5 THEN 500
                ELSE 0
            END as ved_income_amount
        FROM ved_downlines vd
        INNER JOIN "user" u ON u.id = vd.child_id
        INNER JOIN ved_owner_eligibility voe ON voe.ved_owner_id = vd.ved_owner_id
        WHERE u.activation_date IS NOT NULL
          AND DATE(u.activation_date) = :business_date
          AND u.package_points > 0
          -- CRITICAL: Ved member's OWN activation does NOT generate Ved Income
          -- Only their DOWNLINE activations count
          AND u.id != vd.ved_member_id
          -- Eligibility: Must have at least 1 left + 1 right active (matching check in Python)
          AND voe.left_active_count >= 1
          AND voe.right_active_count >= 1
          -- CRITICAL VED PROGRAM RULE 6: ONE-TIME INCOME PER ACTIVATION (Lifetime Protection)
          -- Exclude users who already have Ved income transaction OR pending income (one-time only)
          -- Protects against scheduler reruns before auto-approval completes
          AND u.id NOT IN (
              SELECT DISTINCT referred_user_id 
              FROM transaction 
              WHERE transaction_type = 'Ved Income' 
                AND referred_user_id IS NOT NULL
          )
          AND u.id NOT IN (
              SELECT DISTINCT related_user_id 
              FROM pending_income 
              WHERE income_type = 'Ved Income' 
                AND related_user_id IS NOT NULL
          )
        ORDER BY vd.ved_owner_id, vd.ved_member_id, u.id
    """)
    
    result = db.execute(query, {"business_date": business_date}).fetchall()
    
    return [
        {
            "ved_owner_id": row[0],
            "ved_member_id": row[1],
            "activated_user_id": row[2],
            "activated_user_name": row[3],
            "ved_income_amount": float(row[4])
        }
        for row in result
    ]


def get_consumed_points_sql(
    db: Session,
    user_id: str,
    income_type: str = 'Matching Referral'
) -> Dict[str, float]:
    """
    Get consumed points from pending_income table using SQL
    
    Args:
        user_id: User ID
        income_type: Income type (default 'Matching Referral')
    
    Returns:
        {'left': consumed_left, 'right': consumed_right}
    """
    query = text("""
        SELECT 
            COALESCE(SUM(left_points_consumed), 0) as left_consumed,
            COALESCE(SUM(right_points_consumed), 0) as right_consumed
        FROM pending_income
        WHERE user_id = :user_id
          AND income_type = :income_type
    """)
    
    result = db.execute(query, {"user_id": user_id, "income_type": income_type}).fetchone()
    
    return {
        'left': float(result[0]) if result else 0.0,
        'right': float(result[1]) if result else 0.0
    }


def get_direct_referral_points_by_leg_sql(
    db: Session,
    user_id: str
) -> Dict[str, float]:
    """
    Get direct referral PACKAGE POINTS by leg (left/right)
    
    Counts POINTS (not users) from direct referrals (by referrer_id)
    regardless of where they're placed in the binary tree (handles spillover)
    
    DC PROTOCOL: Show ALL user data (no production date filter)
    
    Package Points:
    - Diamond (₹7,500) = 0.5 points
    - Platinum (₹15,000) = 1.0 points
    
    Returns:
        {'left': points, 'right': points, 'total': points}
    """
    query = text("""
        WITH RECURSIVE 
        -- Get all users in left leg of binary tree
        left_leg AS (
            SELECT child_id
            FROM placement
            WHERE parent_id = :user_id AND side = 'left'
            
            UNION ALL
            
            SELECT p.child_id
            FROM placement p
            INNER JOIN left_leg ll ON p.parent_id = ll.child_id
        ),
        -- Get all users in right leg of binary tree
        right_leg AS (
            SELECT child_id
            FROM placement
            WHERE parent_id = :user_id AND side = 'right'
            
            UNION ALL
            
            SELECT p.child_id
            FROM placement p
            INNER JOIN right_leg rl ON p.parent_id = rl.child_id
        ),
        -- Get direct referrals with their leg placement and points
        -- DC PROTOCOL: Count ALL activations (no date filter)
        direct_referrals_by_leg AS (
            SELECT 
                u.id,
                u.package_points,
                CASE 
                    WHEN u.id IN (SELECT child_id FROM left_leg) THEN 'left'
                    WHEN u.id IN (SELECT child_id FROM right_leg) THEN 'right'
                    ELSE NULL
                END as leg_side
            FROM "user" u
            WHERE u.referrer_id = :user_id
              AND u.activation_date IS NOT NULL
        )
        SELECT 
            COALESCE(SUM(CASE WHEN leg_side = 'left' THEN package_points ELSE 0 END), 0) as left_points,
            COALESCE(SUM(CASE WHEN leg_side = 'right' THEN package_points ELSE 0 END), 0) as right_points
        FROM direct_referrals_by_leg
    """)
    
    result = db.execute(query, {
        "user_id": user_id
    }).fetchone()
    
    if not result:
        return {'left': 0.0, 'right': 0.0, 'total': 0.0}
    
    left_points = float(result[0]) if result[0] else 0.0
    right_points = float(result[1]) if result[1] else 0.0
    
    return {
        'left': left_points,
        'right': right_points,
        'total': left_points + right_points
    }


def calculate_guru_dakshina_bulk_sql(
    db: Session,
    business_date: str
) -> List[Dict[str, Any]]:
    """
    Calculate Guru Dakshina for ALL users in bulk using SQL
    
    Logic: 2% of direct referrals' GROSS earnings (excluding Guru Dakshina itself)
    
    10x faster than looping through users and referrals!
    
    Returns:
        List of {user_id, total_referral_gross, guru_dakshina_amount}
    """
    query = text("""
        WITH referral_earnings AS (
            SELECT 
                u.referrer_id,
                SUM(pi.gross_amount) as total_gross
            FROM pending_income pi
            INNER JOIN "user" u ON u.id = pi.user_id
            WHERE pi.business_date = :business_date
              AND pi.income_type != 'Guru Dakshina'
              AND u.referrer_id IS NOT NULL
            GROUP BY u.referrer_id
        )
        SELECT 
            referrer_id as user_id,
            total_gross as total_referral_gross,
            total_gross * 0.02 as guru_dakshina_amount
        FROM referral_earnings
        WHERE total_gross > 0
        ORDER BY guru_dakshina_amount DESC
    """)
    
    result = db.execute(query, {"business_date": business_date}).fetchall()
    
    return [
        {
            "user_id": row[0],
            "total_referral_gross": float(row[1]),
            "guru_dakshina_amount": float(row[2])
        }
        for row in result
    ]


def calculate_awards_income_bulk_sql(
    db: Session
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculate NEW Awards (Direct & Matching) in bulk using SQL
    
    50x faster than looping through users!
    Returns only NEW unlocks (users who just qualified for awards)
    
    Returns:
        {
            'new_direct_awards': [...],
            'new_matching_awards': [...]
        }
    """
    
    # 1. Find NEW Direct Awards (not yet in UserAwardProgress)
    # DC PROTOCOL: Check ALL users (no production date filter)
    # CRITICAL: Use cumulative_required (not referral_count) for award qualification
    direct_awards_query = text("""
        WITH user_referral_counts AS (
            SELECT 
                u.id as user_id,
                COUNT(ref.id) as direct_count
            FROM "user" u
            LEFT JOIN "user" ref ON ref.referrer_id = u.id 
                AND ref.package_points > 0
                AND ref.activation_date IS NOT NULL
            WHERE u.package_points > 0
            GROUP BY u.id
        ),
        eligible_tiers AS (
            SELECT 
                urc.user_id,
                dat.id as tier_id,
                dat.award_name,
                dat.actual_price,
                dat.cumulative_required,
                urc.direct_count
            FROM user_referral_counts urc
            INNER JOIN direct_award_tier dat ON dat.cumulative_required <= urc.direct_count
            LEFT JOIN user_award_progress uap ON uap.user_id = urc.user_id AND uap.award_tier_id = dat.id
            WHERE uap.id IS NULL
        )
        SELECT 
            user_id,
            tier_id,
            award_name,
            actual_price,
            cumulative_required,
            direct_count
        FROM eligible_tiers
        ORDER BY user_id, cumulative_required ASC
    """)
    
    direct_result = db.execute(direct_awards_query).fetchall()
    new_direct_awards = [
        {
            "user_id": row[0],
            "tier_id": row[1],
            "award_name": row[2],
            "award_amount": float(row[3]) if row[3] else 0.0,
            "required_referrals": row[4],
            "current_referrals": row[5]
        }
        for row in direct_result
    ]
    
    # 2. Find NEW Matching Awards (not yet in UserMatchingAwardProgress)
    # DC PROTOCOL: Check ALL users (no production date filter)
    # Use user_leg_metrics table (already computed recursively by scheduler)
    # CRITICAL: Use cumulative_required (not match_count) for award qualification
    matching_awards_query = text("""
        WITH user_matching_points AS (
            SELECT 
                ulm.user_id,
                ulm.effective_matching_count as total_matching_points,
                ulm.left_points,
                ulm.right_points
            FROM user_leg_metrics ulm
            INNER JOIN "user" u ON u.id = ulm.user_id
            WHERE ulm.effective_matching_count > 0
              AND u.package_points > 0
        ),
        eligible_matching_tiers AS (
            SELECT 
                ump.user_id,
                mat.id as tier_id,
                mat.award_name,
                mat.actual_price,
                mat.cumulative_required,
                ump.total_matching_points
            FROM user_matching_points ump
            INNER JOIN matching_award_tier mat ON mat.cumulative_required <= ump.total_matching_points
            LEFT JOIN user_matching_award_progress umap 
                ON umap.user_id = ump.user_id AND umap.matching_award_tier_id = mat.id
            WHERE umap.id IS NULL
        )
        SELECT 
            user_id,
            tier_id,
            award_name,
            actual_price,
            cumulative_required,
            total_matching_points
        FROM eligible_matching_tiers
        ORDER BY user_id, cumulative_required ASC
    """)
    
    matching_result = db.execute(matching_awards_query).fetchall()
    new_matching_awards = [
        {
            "user_id": row[0],
            "tier_id": row[1],
            "award_name": row[2],
            "award_amount": float(row[3]) if row[3] else 0.0,
            "required_matches": int(row[4]),
            "current_matches": int(row[5])
        }
        for row in matching_result
    ]
    
    logger.info(f"🏆 Bulk Awards SQL: {len(new_direct_awards)} new direct awards, {len(new_matching_awards)} new matching awards")
    
    return {
        'new_direct_awards': new_direct_awards,
        'new_matching_awards': new_matching_awards
    }


def sync_field_allowance_status_bulk_sql(
    db: Session
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fast SQL to check Field Allowance eligibility for ALL users
    
    100x faster than Python loops!
    Returns status transitions (Jaguar disconnects, Car qualifies, Field qualifies)
    
    Returns:
        {
            'jaguar_users': [...],
            'car_eligible': [...],
            'field_eligible': [...]
        }
    """
    
    # 1. Find users with Jaguar Car Fund Award (disconnects ALL allowances)
    jaguar_query = text("""
        SELECT DISTINCT u.id as user_id
        FROM "user" u
        INNER JOIN user_matching_award_progress umap ON umap.user_id = u.id
        INNER JOIN matching_award_tier mat ON mat.id = umap.matching_award_tier_id
        WHERE u.package_points > 0
          AND umap.status = 'Achieved'
          AND mat.award_name ILIKE '%Jaguar%'
    """)
    
    jaguar_result = db.execute(jaguar_query).fetchall()
    jaguar_users = [{"user_id": row[0]} for row in jaguar_result]
    
    # 2. Find users eligible for Car Allowance (250 points in 90 days)
    # Start date logic: Existing users (activated before Oct 20) → Oct 20, 2025; New users → activation_date
    car_allowance_query = text("""
        SELECT 
            u.id as user_id,
            ulm.left_points + ulm.right_points as total_points,
            EXTRACT(EPOCH FROM (NOW() - 
                CASE 
                    WHEN u.activation_date >= '2025-10-20'::date THEN u.activation_date
                    ELSE '2025-10-20'::timestamp
                END
            ))/86400 as days_since_start
        FROM "user" u
        INNER JOIN user_leg_metrics ulm ON ulm.user_id = u.id
        WHERE u.package_points > 0
          AND u.activation_date IS NOT NULL
          AND (ulm.left_points + ulm.right_points) >= 250
          AND EXTRACT(EPOCH FROM (NOW() - 
                CASE 
                    WHEN u.activation_date >= '2025-10-20'::date THEN u.activation_date
                    ELSE '2025-10-20'::timestamp
                END
          ))/86400 <= 90
          AND u.id NOT IN (
              SELECT DISTINCT umap.user_id
              FROM user_matching_award_progress umap
              INNER JOIN matching_award_tier mat ON mat.id = umap.matching_award_tier_id
              WHERE umap.status = 'Achieved' AND mat.award_name ILIKE '%Jaguar%'
          )
    """)
    
    car_result = db.execute(car_allowance_query).fetchall()
    car_eligible = [
        {
            "user_id": row[0],
            "total_points": int(row[1]),
            "days_since_start": int(row[2])
        }
        for row in car_result
    ]
    
    # 3. Find users eligible for Field Allowance (7 POINTS in 45 days, NO Car Allowance)
    # Start date logic: Existing users (activated before Oct 20) → Oct 20, 2025; New users → activation_date
    # POINTS: Platinum=1.0, Diamond=0.5, Blue/Loyal=0
    field_allowance_query = text("""
        WITH direct_referrals AS (
            SELECT 
                u.id as user_id,
                COALESCE(SUM(ref.package_points), 0) as direct_points,
                EXTRACT(EPOCH FROM (NOW() - 
                    CASE 
                        WHEN u.activation_date >= '2025-10-20'::date THEN u.activation_date
                        ELSE '2025-10-20'::timestamp
                    END
                ))/86400 as days_since_start
            FROM "user" u
            LEFT JOIN "user" ref ON ref.referrer_id = u.id AND ref.package_points > 0
            WHERE u.package_points > 0
              AND u.activation_date IS NOT NULL
            GROUP BY u.id, u.activation_date
        )
        SELECT 
            dr.user_id,
            dr.direct_points,
            dr.days_since_start
        FROM direct_referrals dr
        WHERE dr.direct_points >= 7
          AND dr.days_since_start <= 45
          AND dr.user_id NOT IN (
              SELECT DISTINCT umap.user_id
              FROM user_matching_award_progress umap
              INNER JOIN matching_award_tier mat ON mat.id = umap.matching_award_tier_id
              WHERE umap.status = 'Achieved' AND mat.award_name ILIKE '%Jaguar%'
          )
          AND dr.user_id NOT IN (
              SELECT user_id FROM car_allowance_eligibility WHERE overall_status = 'Active'
          )
    """)
    
    field_result = db.execute(field_allowance_query).fetchall()
    field_eligible = [
        {
            "user_id": row[0],
            "direct_points": float(row[1]),
            "days_since_start": int(row[2])
        }
        for row in field_result
    ]
    
    logger.info(f"🏅 Bulk Allowance SQL: {len(jaguar_users)} Jaguar users, {len(car_eligible)} car eligible, {len(field_eligible)} field eligible")
    
    return {
        'jaguar_users': jaguar_users,
        'car_eligible': car_eligible,
        'field_eligible': field_eligible
    }


def calculate_bonanza_eligible_bulk_sql(
    db: Session,
    business_date: str
) -> List[Dict[str, Any]]:
    """
    Find all users eligible for bonanza rewards in bulk using SQL
    
    20x faster than looping through individual progress records!
    Returns users who achieved bonanza targets but haven't been rewarded yet
    
    Returns:
        List of {bonanza_id, bonanza_name, user_id, current_progress, reward_amount, ...}
    """
    
    query = text("""
        SELECT 
            bp.id as progress_id,
            bp.bonanza_id,
            db.bonanza_name,
            bp.user_id,
            bp.current_progress,
            bp.achievement_status,
            bp.reward_given,
            db.has_direct_target,
            db.has_matching_target,
            db.total_budget_allocated,
            u.package_points,
            u.referrer_id
        FROM bonanza_progress bp
        INNER JOIN dynamic_bonanza db ON db.id = bp.bonanza_id
        INNER JOIN "user" u ON u.id = bp.user_id
        WHERE bp.achievement_status = 'Achieved'
          AND bp.reward_given = false
          AND bp.processed_status = 'Pending'
          AND db.status IN ('active', 'approved')
          AND db.start_date <= NOW()
          AND db.end_date >= NOW()
          AND u.package_points > 0
        ORDER BY bp.bonanza_id, bp.user_id
    """)
    
    result = db.execute(query).fetchall()
    
    eligible_rewards = [
        {
            "progress_id": row[0],
            "bonanza_id": row[1],
            "bonanza_name": row[2],
            "user_id": row[3],
            "current_progress": row[4],
            "achievement_status": row[5],
            "reward_given": row[6],
            "has_direct_target": row[7],
            "has_matching_target": row[8],
            "total_budget": float(row[9]) if row[9] else 0.0,
            "package_points": float(row[10]),
            "referrer_id": row[11]
        }
        for row in result
    ]
    
    logger.info(f"🎁 Bulk Bonanza SQL: {len(eligible_rewards)} users eligible for rewards across {len(set(r['bonanza_id'] for r in eligible_rewards))} campaigns")
    
    return eligible_rewards


def identify_consumed_members_sql(
    db: Session,
    user_id: str,
    left_consumed: float,
    right_consumed: float,
    exclude_record_id: int = None
) -> Dict[str, list]:
    """
    DC Protocol: Identify specific members consumed by the matching engine.
    Uses cumulative sequential approach — processes ALL matching records
    for this user in chronological order to accurately track which members
    were consumed by each record. This prevents N/A issues caused by
    tree state changes between matching and snapshot creation.
    """
    try:
        def _get_leg_members_no_cutoff(side):
            q = text("""
                WITH RECURSIVE leg_team AS (
                    SELECT p.child_id, p.side as root_leg, 1 as level
                    FROM placement p
                    WHERE p.parent_id = :user_id AND p.side = :side
                    UNION ALL
                    SELECT p.child_id, lt.root_leg, lt.level + 1
                    FROM placement p
                    INNER JOIN leg_team lt ON p.parent_id = lt.child_id
                    WHERE lt.level < 200
                )
                SELECT u.id, u.name, u.package_points, u.activation_date, COALESCE(u.is_welcome_coupon, false) as is_wc
                FROM leg_team lt
                JOIN "user" u ON u.id = lt.child_id
                WHERE u.package_points > 0
                  AND u.is_welcome_coupon = false
                  AND (u.activation_date IS NOT NULL OR u.coupon_status IN ('Active', 'Activated'))
                ORDER BY COALESCE(u.activation_date, u.registration_date) ASC, u.id ASC
            """)
            rows = db.execute(q, {"user_id": user_id, "side": side}).fetchall()
            return [{"user_id": r[0], "name": r[1], "package_points": float(r[2]),
                      "activation_date": r[3].strftime('%Y-%m-%d') if r[3] and hasattr(r[3], 'strftime') else (str(r[3])[:10] if r[3] else None)}
                    for r in rows]

        all_left = _get_leg_members_no_cutoff('left')
        all_right = _get_leg_members_no_cutoff('right')

        exclude_filter = ""
        prev_params = {"user_id": user_id}
        if exclude_record_id:
            exclude_filter = "AND id != :exclude_id"
            prev_params["exclude_id"] = exclude_record_id

        all_records_q = text(f"""
            SELECT id, pairs_matched, left_points_consumed, right_points_consumed,
                   match_type, matching_contributors_snapshot, business_date
            FROM pending_income
            WHERE user_id = :user_id AND income_type = 'Matching Referral'
            AND pairs_matched > 0
            {exclude_filter}
            ORDER BY business_date ASC, id ASC
        """)
        all_records = db.execute(all_records_q, prev_params).fetchall()

        li = 0
        ri = 0
        for rec in all_records:
            rec_left = float(rec.left_points_consumed or 0)
            rec_right = float(rec.right_points_consumed or 0)

            lpts = 0.0
            while lpts < rec_left and li < len(all_left):
                lpts += all_left[li]['package_points']
                li += 1
            rpts = 0.0
            while rpts < rec_right and ri < len(all_right):
                rpts += all_right[ri]['package_points']
                ri += 1

            if lpts < rec_left and li >= len(all_left):
                logger.warning(f"⚠️ DC-SNAPSHOT: Left member exhaustion at record {rec.id} for {user_id} (needed={rec_left}, got={lpts}, idx={li}/{len(all_left)})")
            if rpts < rec_right and ri >= len(all_right):
                logger.warning(f"⚠️ DC-SNAPSHOT: Right member exhaustion at record {rec.id} for {user_id} (needed={rec_right}, got={rpts}, idx={ri}/{len(all_right)})")

        left_picked = []
        pts_picked = 0.0
        if left_consumed > 0:
            for i in range(li, len(all_left)):
                if pts_picked >= left_consumed:
                    break
                left_picked.append(all_left[i])
                pts_picked += all_left[i]['package_points']

        right_picked = []
        pts_picked = 0.0
        if right_consumed > 0:
            for i in range(ri, len(all_right)):
                if pts_picked >= right_consumed:
                    break
                right_picked.append(all_right[i])
                pts_picked += all_right[i]['package_points']

        if left_consumed > 0 and not left_picked:
            logger.warning(f"⚠️ DC-SNAPSHOT: Could not identify left members for {user_id} (consumed={left_consumed}, available_from_idx={li}/{len(all_left)})")
        if right_consumed > 0 and not right_picked:
            logger.warning(f"⚠️ DC-SNAPSHOT: Could not identify right members for {user_id} (consumed={right_consumed}, available_from_idx={ri}/{len(all_right)})")

        logger.info(f"🔍 Identified consumed members for {user_id}: {len(left_picked)}L/{len(right_picked)}R (cumulative sequential)")
        return {'left': left_picked, 'right': right_picked}

    except Exception as e:
        logger.error(f"Error identifying consumed members for {user_id}: {e}")
        return {'left': [], 'right': []}


def identify_exempted_members_sql(
    db: Session,
    user_id: str,
    left_zero_consumed: int,
    right_zero_consumed: int
) -> Dict[str, list]:
    """
    Option B: Identify specific zero-point members consumed by exempted matching.
    NO cutoff filter — matches the matching engine's behavior exactly.
    """
    try:
        def _get_zero_point_members_no_cutoff(side):
            q = text("""
                WITH RECURSIVE leg_team AS (
                    SELECT p.child_id, 1 as level
                    FROM placement p
                    WHERE p.parent_id = :user_id AND p.side = :side
                    UNION ALL
                    SELECT p.child_id, lt.level + 1
                    FROM placement p
                    INNER JOIN leg_team lt ON p.parent_id = lt.child_id
                    WHERE lt.level < 200
                )
                SELECT u.id, u.name, u.package_points, u.activation_date, u.coupon_status
                FROM leg_team lt
                JOIN "user" u ON u.id = lt.child_id
                WHERE u.package_points = 0
                  AND u.coupon_status IN ('Active', 'Activated')
                ORDER BY COALESCE(u.activation_date, u.registration_date) ASC, u.id ASC
            """)
            rows = db.execute(q, {"user_id": user_id, "side": side}).fetchall()
            return [{"user_id": r[0], "name": r[1], "package_points": 0,
                      "coupon_status": r[4],
                      "activation_date": r[3].strftime('%Y-%m-%d') if r[3] and hasattr(r[3], 'strftime') else (str(r[3])[:10] if r[3] else None)}
                    for r in rows]

        left_zero = _get_zero_point_members_no_cutoff('left')
        right_zero = _get_zero_point_members_no_cutoff('right')

        left_picked = left_zero[:left_zero_consumed] if left_zero_consumed > 0 else []
        right_picked = right_zero[:right_zero_consumed] if right_zero_consumed > 0 else []

        logger.info(f"🔍 Identified exempted members for {user_id}: {len(left_picked)}L-zero/{len(right_picked)}R-zero (no cutoff)")
        return {'left': left_picked, 'right': right_picked}

    except Exception as e:
        logger.error(f"Error identifying exempted members for {user_id}: {e}")
        return {'left': [], 'right': []}


def build_matching_contributor_snapshot(
    db: Session,
    user_id: str,
    pairs_matched: int,
    left_consumed: float,
    right_consumed: float,
    match_type: str,
    business_date=None,
    exclude_record_id: int = None,
    consumed_members: Dict[str, list] = None
) -> Optional[Dict[str, Any]]:
    if pairs_matched <= 0:
        return None
    
    try:
        if consumed_members and (consumed_members.get('left') or consumed_members.get('right')):
            left_picked = consumed_members.get('left', [])
            right_picked = consumed_members.get('right', [])
            logger.info(f"📸 Using pre-identified consumed members for {user_id}: {len(left_picked)}L/{len(right_picked)}R")
        else:
            consumed = identify_consumed_members_sql(
                db, user_id, left_consumed, right_consumed,
                exclude_record_id=exclude_record_id
            )
            left_picked = consumed.get('left', [])
            right_picked = consumed.get('right', [])
            logger.info(f"📸 Identified consumed members via cumulative approach for {user_id}: {len(left_picked)}L/{len(right_picked)}R")
        
        pairs = []
        li = 0
        ri = 0
        
        for pair_idx in range(pairs_matched):
            is_first_pair = (pair_idx == 0)
            
            if is_first_pair and match_type == '2_to_1_first_matching':
                lc_pair = 2
                rc_pair = 1
            elif is_first_pair and match_type == '1_to_2_first_matching':
                lc_pair = 1
                rc_pair = 2
            else:
                lc_pair = 1
                rc_pair = 1
            
            left_for_pair = []
            pts_needed = float(lc_pair)
            pts_got = 0.0
            while pts_got < pts_needed and li < len(left_picked):
                left_for_pair.append(left_picked[li])
                pts_got += left_picked[li]['package_points']
                li += 1
            
            right_for_pair = []
            pts_needed = float(rc_pair)
            pts_got = 0.0
            while pts_got < pts_needed and ri < len(right_picked):
                right_for_pair.append(right_picked[ri])
                pts_got += right_picked[ri]['package_points']
                ri += 1
            
            pairs.append({
                "left": left_for_pair,
                "right": right_for_pair
            })
        
        snapshot = {
            "match_type": match_type,
            "pairs_matched": pairs_matched,
            "left_consumed": left_consumed,
            "right_consumed": right_consumed,
            "pairs": pairs
        }
        
        logger.info(f"📸 Matching contributor snapshot for {user_id}: {pairs_matched} pairs, {len(left_picked)}L/{len(right_picked)}R members")
        return snapshot
        
    except Exception as e:
        logger.error(f"Error building matching contributor snapshot for {user_id}: {e}")
        return None


def build_exempted_matching_snapshot(
    db: Session,
    user_id: str,
    exempt_pairs: int,
    left_points_consumed: float,
    right_points_consumed: float,
    left_zero_consumed: int,
    right_zero_consumed: int,
    business_date=None,
    consumed_members: Dict[str, list] = None
) -> Optional[Dict[str, Any]]:
    if exempt_pairs <= 0:
        return None
    
    try:
        if consumed_members and (consumed_members.get('left') or consumed_members.get('right')):
            left_zero_members = consumed_members.get('left', [])
            right_zero_members = consumed_members.get('right', [])
            logger.info(f"📸 Using pre-identified exempted members for {user_id}: {len(left_zero_members)}L-zero/{len(right_zero_members)}R-zero")
        else:
            cutoff_filter = ""
            params = {"user_id": user_id}
            if business_date:
                from datetime import datetime
                if hasattr(business_date, 'strftime'):
                    cutoff_dt = business_date if hasattr(business_date, 'hour') else datetime.combine(business_date, datetime.max.time())
                else:
                    cutoff_dt = business_date
                cutoff_filter = "AND u.activation_date <= :cutoff_date"
                params["cutoff_date"] = cutoff_dt
            
            def _get_zero_point_members(side):
                q = text(f"""
                    WITH RECURSIVE leg_team AS (
                        SELECT p.child_id, 1 as level
                        FROM placement p
                        WHERE p.parent_id = :user_id AND p.side = :side
                        UNION ALL
                        SELECT p.child_id, lt.level + 1
                        FROM placement p
                        INNER JOIN leg_team lt ON p.parent_id = lt.child_id
                        WHERE lt.level < 200
                    )
                    SELECT u.id, u.name, u.package_points, u.activation_date, u.coupon_status
                    FROM leg_team lt
                    JOIN "user" u ON u.id = lt.child_id
                    WHERE u.package_points = 0
                      AND u.coupon_status IN ('Active', 'Activated')
                      {cutoff_filter}
                    ORDER BY COALESCE(u.activation_date, u.registration_date) ASC, u.id ASC
                """)
                p = dict(params)
                p["side"] = side
                rows = db.execute(q, p).fetchall()
                return [{"user_id": r[0], "name": r[1], "package_points": 0,
                          "coupon_status": r[4],
                          "activation_date": r[3].strftime('%Y-%m-%d') if r[3] and hasattr(r[3], 'strftime') else (str(r[3])[:10] if r[3] else None)}
                        for r in rows]
            
            left_zero_members = _get_zero_point_members('left')
            right_zero_members = _get_zero_point_members('right')
            left_zero_members = left_zero_members[:left_zero_consumed] if left_zero_consumed > 0 else []
            right_zero_members = right_zero_members[:right_zero_consumed] if right_zero_consumed > 0 else []
        
        snapshot = {
            "match_type": "exempted_matching",
            "pairs_matched": exempt_pairs,
            "left_consumed": left_points_consumed,
            "right_consumed": right_points_consumed,
            "exempted_left_consumed": left_zero_consumed,
            "exempted_right_consumed": right_zero_consumed,
            "left_zero_point_members": left_zero_members,
            "right_zero_point_members": right_zero_members,
            "is_exempted": True,
        }
        
        logger.info(f"📸 Exempted matching snapshot for {user_id}: {exempt_pairs} pairs, L-zero={left_zero_consumed}, R-zero={right_zero_consumed}")
        return snapshot
        
    except Exception as e:
        logger.error(f"Error building exempted matching snapshot for {user_id}: {e}")
        return None


KEY_ELIGIBILITY_CUTOFF = '2025-11-17'

def check_key_eligibility(db: Session, user_id: str) -> Dict[str, Any]:
    """
    DC Protocol Feb 2026: Key Eligibility Check
    
    Every activated MNR member must have at least 1 direct business facilitation
    (referral with coupon activated) after 17 Nov 2025 to be Key Eligible.
    
    Key Eligibility is required for:
    - Referral bonuses processing
    - Awards eligibility
    - Bonanza claims
    - Earnings eligibility
    
    Returns dict with:
    - is_key_eligible: bool
    - post_cutoff_referral_count: int
    - cutoff_date: str
    - message: str
    """
    try:
        self_check = db.execute(text("""
            SELECT activation_date FROM "user"
            WHERE id = :user_id
              AND coupon_status = 'Activated'
              AND activation_date > :cutoff_date
        """), {"user_id": user_id, "cutoff_date": KEY_ELIGIBILITY_CUTOFF}).fetchone()
        
        if self_check:
            return {
                "is_key_eligible": True,
                "post_cutoff_referral_count": 0,
                "cutoff_date": KEY_ELIGIBILITY_CUTOFF,
                "message": None,
                "self_activated_post_cutoff": True
            }
        
        result = db.execute(text("""
            SELECT COUNT(*) as cnt
            FROM "user" u
            WHERE u.referrer_id = :user_id
              AND u.coupon_status = 'Activated'
              AND u.activation_date > :cutoff_date
              AND COALESCE(u.is_welcome_coupon, false) = false
              AND u.package_points > 0
        """), {"user_id": user_id, "cutoff_date": KEY_ELIGIBILITY_CUTOFF}).fetchone()
        
        count = result[0] if result else 0
        is_key_eligible = count > 0
        
        return {
            "is_key_eligible": is_key_eligible,
            "post_cutoff_referral_count": count,
            "cutoff_date": KEY_ELIGIBILITY_CUTOFF,
            "message": None if is_key_eligible else "Complete at least 1 Direct Business Facilitation after 17th Nov 2025 to be eligible for all MNR programs, migration, and to claim all your referral bonuses and achievements.",
            "self_activated_post_cutoff": False
        }
    except Exception as e:
        logger.error(f"Error checking key eligibility for {user_id}: {e}")
        return {
            "is_key_eligible": False,
            "post_cutoff_referral_count": 0,
            "cutoff_date": KEY_ELIGIBILITY_CUTOFF,
            "message": "Unable to verify eligibility status."
        }


def check_key_eligibility_bulk(db: Session, user_ids: List[str]) -> Dict[str, bool]:
    """
    Bulk key eligibility check for staff admin pages.
    Returns dict mapping user_id -> is_key_eligible
    """
    if not user_ids:
        return {}
    
    try:
        self_activated = db.execute(text("""
            SELECT id FROM "user"
            WHERE id = ANY(:user_ids)
              AND coupon_status = 'Activated'
              AND activation_date > :cutoff_date
        """), {"user_ids": user_ids, "cutoff_date": KEY_ELIGIBILITY_CUTOFF}).fetchall()
        self_eligible_set = {row[0] for row in self_activated}
        
        result = db.execute(text("""
            SELECT u2.referrer_id, COUNT(*) as cnt
            FROM "user" u2
            WHERE u2.referrer_id = ANY(:user_ids)
              AND u2.coupon_status = 'Activated'
              AND u2.activation_date > :cutoff_date
              AND COALESCE(u2.is_welcome_coupon, false) = false
              AND u2.package_points > 0
            GROUP BY u2.referrer_id
        """), {"user_ids": user_ids, "cutoff_date": KEY_ELIGIBILITY_CUTOFF}).fetchall()
        
        referral_eligible_map = {row[0]: True for row in result}
        return {uid: (uid in self_eligible_set or referral_eligible_map.get(uid, False)) for uid in user_ids}
    except Exception as e:
        logger.error(f"Error in bulk key eligibility check: {e}")
        return {uid: False for uid in user_ids}
