"""
DC Protocol Phase 1.4: Shadow Mode Monitoring Endpoints
Provides reconciliation and monitoring tools for materialized view validation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.wallet_balance_service import get_earning_wallet, get_withdrawable_wallet

router = APIRouter()

@router.get("/shadow-mode/reconciliation")
def get_shadow_mode_reconciliation(
    show_mismatches_only: bool = Query(False, description="Show only users with mismatches"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    DC Protocol Shadow Mode: Reconciliation Report
    Compares stored wallet balances vs materialized view computed balances
    
    Returns:
    - Total users analyzed
    - Mismatch count (should be 0)
    - Per-user comparison data
    - Statistical summary
    """
    # Only RVZ Admin and Super Admin can access
    if current_user.role not in ['RVZ ID', 'Super Admin']:
        raise HTTPException(status_code=403, detail="Only RVZ Admin and Super Admin can access Shadow Mode monitoring")
    
    # Get reconciliation data
    query = text("""
        WITH reconciliation AS (
            SELECT 
                u.id,
                u.name,
                u.role,
                u.earning_wallet as stored_earning,
                COALESCE(e.earning_wallet, 0) as view_earning,
                ABS(u.earning_wallet - COALESCE(e.earning_wallet, 0)) as earning_diff,
                u.withdrawable_wallet as stored_withdrawable,
                COALESCE(w.withdrawable_wallet, 0) as view_withdrawable,
                ABS(u.withdrawable_wallet - COALESCE(w.withdrawable_wallet, 0)) as withdrawable_diff,
                CASE 
                    WHEN ABS(u.earning_wallet - COALESCE(e.earning_wallet, 0)) > 0.01 THEN true
                    WHEN ABS(u.withdrawable_wallet - COALESCE(w.withdrawable_wallet, 0)) > 0.01 THEN true
                    ELSE false
                END as has_mismatch
            FROM "user" u
            LEFT JOIN user_earning_wallet_balance e ON u.id = e.user_id
            LEFT JOIN user_withdrawable_wallet_balance w ON u.id = w.user_id
            WHERE u.id != 'MNR00000000'  -- Exclude system user
        )
        SELECT * FROM reconciliation
        WHERE (:show_mismatches_only = false OR has_mismatch = true)
        ORDER BY 
            has_mismatch DESC,
            (earning_diff + withdrawable_diff) DESC,
            id
        LIMIT :page_size OFFSET :offset
    """)
    
    offset = (page - 1) * page_size
    results = db.execute(query, {
        'show_mismatches_only': show_mismatches_only,
        'page_size': page_size,
        'offset': offset
    }).fetchall()
    
    # Get summary statistics
    summary_query = text("""
        WITH reconciliation AS (
            SELECT 
                u.id,
                u.earning_wallet as stored_earning,
                COALESCE(e.earning_wallet, 0) as view_earning,
                ABS(u.earning_wallet - COALESCE(e.earning_wallet, 0)) as earning_diff,
                u.withdrawable_wallet as stored_withdrawable,
                COALESCE(w.withdrawable_wallet, 0) as view_withdrawable,
                ABS(u.withdrawable_wallet - COALESCE(w.withdrawable_wallet, 0)) as withdrawable_diff
            FROM "user" u
            LEFT JOIN user_earning_wallet_balance e ON u.id = e.user_id
            LEFT JOIN user_withdrawable_wallet_balance w ON u.id = w.user_id
            WHERE u.id != 'MNR00000000'
        )
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN earning_diff > 0.01 THEN 1 END) as earning_mismatches,
            COUNT(CASE WHEN withdrawable_diff > 0.01 THEN 1 END) as withdrawable_mismatches,
            COUNT(CASE WHEN earning_diff > 0.01 OR withdrawable_diff > 0.01 THEN 1 END) as total_mismatches,
            SUM(stored_earning) as total_stored_earning,
            SUM(view_earning) as total_view_earning,
            SUM(stored_withdrawable) as total_stored_withdrawable,
            SUM(view_withdrawable) as total_view_withdrawable,
            SUM(earning_diff) as total_earning_diff,
            SUM(withdrawable_diff) as total_withdrawable_diff
        FROM reconciliation
    """)
    
    summary = db.execute(summary_query).fetchone()
    
    # Format results
    users_data = []
    for row in results:
        users_data.append({
            'user_id': row.id,
            'name': row.name,
            'role': row.role,
            'earning_wallet': {
                'stored': float(row.stored_earning),
                'computed': float(row.view_earning),
                'difference': float(row.earning_diff),
                'matches': row.earning_diff <= 0.01
            },
            'withdrawable_wallet': {
                'stored': float(row.stored_withdrawable),
                'computed': float(row.view_withdrawable),
                'difference': float(row.withdrawable_diff),
                'matches': row.withdrawable_diff <= 0.01
            },
            'has_mismatch': row.has_mismatch
        })
    
    return {
        'status': 'success',
        'shadow_mode': True,
        'summary': {
            'total_users': summary.total_users,
            'users_with_mismatches': summary.total_mismatches,
            'earning_wallet_mismatches': summary.earning_mismatches,
            'withdrawable_wallet_mismatches': summary.withdrawable_mismatches,
            'reconciliation_rate': round((1 - (summary.total_mismatches / summary.total_users)) * 100, 2) if summary.total_users > 0 else 100.0,
            'totals': {
                'earning': {
                    'stored': float(summary.total_stored_earning or 0),
                    'computed': float(summary.total_view_earning or 0),
                    'difference': float(summary.total_earning_diff or 0)
                },
                'withdrawable': {
                    'stored': float(summary.total_stored_withdrawable or 0),
                    'computed': float(summary.total_view_withdrawable or 0),
                    'difference': float(summary.total_withdrawable_diff or 0)
                }
            }
        },
        'users': users_data,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_users': summary.total_users,
            'showing': len(users_data)
        }
    }


@router.get("/shadow-mode/user-balance/{user_id}")
def get_user_shadow_balance(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed balance comparison for a specific user
    Shows stored vs computed values with breakdown
    """
    # Allow users to check their own balance, admins can check anyone
    if current_user.id != user_id and current_user.role not in ['RVZ ID', 'Super Admin', 'Admin']:
        raise HTTPException(status_code=403, detail="You can only check your own balance")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get computed balances from materialized views
    computed_earning = get_earning_wallet(db, user_id)
    computed_withdrawable = get_withdrawable_wallet(db, user_id)
    
    # Get stored balances
    stored_earning = float(user.earning_wallet or 0)
    stored_withdrawable = float(user.withdrawable_wallet or 0)
    
    # Calculate differences
    earning_diff = abs(stored_earning - computed_earning)
    withdrawable_diff = abs(stored_withdrawable - computed_withdrawable)
    
    return {
        'status': 'success',
        'user_id': user_id,
        'name': user.name,
        'shadow_mode': True,
        'balances': {
            'earning_wallet': {
                'stored': stored_earning,
                'computed': computed_earning,
                'difference': earning_diff,
                'matches': earning_diff <= 0.01,
                'source': 'stored' if earning_diff <= 0.01 else 'MISMATCH'
            },
            'withdrawable_wallet': {
                'stored': stored_withdrawable,
                'computed': computed_withdrawable,
                'difference': withdrawable_diff,
                'matches': withdrawable_diff <= 0.01,
                'source': 'stored' if withdrawable_diff <= 0.01 else 'MISMATCH'
            }
        },
        'recommendation': 'OK' if (earning_diff <= 0.01 and withdrawable_diff <= 0.01) else 'INVESTIGATE',
        'note': 'During Shadow Mode, stored values are used for transactions. Computed values are for monitoring only.'
    }


@router.post("/shadow-mode/force-refresh")
def force_refresh_materialized_views(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger materialized view refresh
    Only for RVZ Admin and Super Admin
    """
    if current_user.role not in ['RVZ ID', 'Super Admin']:
        raise HTTPException(status_code=403, detail="Only RVZ Admin and Super Admin can force refresh")
    
    try:
        # Trigger refresh
        db.execute(text("SELECT refresh_wallet_materialized_views()"))
        db.commit()
        
        # Get stats
        stats = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM user_earning_wallet_balance) as earning_count,
                (SELECT COUNT(*) FROM user_withdrawable_wallet_balance) as withdrawable_count,
                (SELECT MAX(last_refreshed) FROM user_earning_wallet_balance) as last_refresh
        """)).fetchone()
        
        return {
            'status': 'success',
            'message': 'Materialized views refreshed successfully',
            'stats': {
                'earning_wallet_users': stats.earning_count,
                'withdrawable_wallet_users': stats.withdrawable_count,
                'last_refreshed': stats.last_refresh.isoformat() if stats.last_refresh else None
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")
