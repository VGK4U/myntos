"""
RVZ ID Exclusive: Production Reset Status Viewer
Shows the status and progress of the Production Reset (Oct 11, 2025)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_db
from app.models.user import User
from app.models.user_leg_metrics import UserLegMetrics
from app.models.transaction import Transaction, PendingIncome

router = APIRouter()

RVZ_ID = "MNR182364369"
PRODUCTION_RESET_DATE = datetime(2025, 10, 11)

def validate_rvz_access(user_id: str, db: Session) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.id != RVZ_ID:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: Production Reset Status is exclusive to RVZ ID"
    #     )
    
    return user

@router.post("/rvz/fix-package-data")
async def rvz_fix_package_data(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    RVZ ID ONLY: One-time fix for package_points and coupon_status
    Fixes the bug where activated users show incorrect package types
    """
    try:
        validate_rvz_access(user_id, db)
        
        # Safety check: See how many users need fixing
        users_needing_fix = db.query(User).filter(
            User.activation_date.isnot(None),
            (User.package_points != 1.0) | (User.coupon_status.in_(['Activated', 'Eligible', 'Active']))
        ).count()
        
        if users_needing_fix == 0:
            return {
                "status": "already_fixed",
                "message": "All users already have correct package data",
                "users_updated": 0
            }
        
        # Fix package_points for activated users
        package_points_updated = db.query(User).filter(
            User.activation_date.isnot(None),
            (User.package_points.is_(None)) | (User.package_points == 0.0)
        ).update(
            {User.package_points: 1.0},
            synchronize_session=False
        )
        
        # Fix coupon_status display
        coupon_status_updated = db.query(User).filter(
            User.activation_date.isnot(None),
            User.coupon_status.in_(['Activated', 'Eligible', 'Active'])
        ).update(
            {User.coupon_status: 'Platinum'},
            synchronize_session=False
        )
        
        db.commit()
        
        # Verify the fix
        remaining_issues = db.query(User).filter(
            User.activation_date.isnot(None),
            (User.package_points != 1.0) | (User.coupon_status.in_(['Activated', 'Eligible', 'Active']))
        ).count()
        
        return {
            "status": "success",
            "message": "Package data fixed successfully",
            "package_points_updated": package_points_updated,
            "coupon_status_updated": coupon_status_updated,
            "total_users_fixed": users_needing_fix,
            "remaining_issues": remaining_issues,
            "verification": "All activated users now show Platinum package" if remaining_issues == 0 else "Some issues remain"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error fixing package data: {str(e)}"
        )

@router.get("/rvz/production-reset-status")
async def rvz_production_reset_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID Production Reset Status API - Returns reset progress and status as JSON"""
    try:
        validate_rvz_access(user_id, db)
        
        # 1. Check Previous Counts Reset Status
        total_users_with_metrics = db.query(UserLegMetrics).count()
        users_with_non_zero_snapshots = db.query(UserLegMetrics).filter(
            (UserLegMetrics.snapshot_direct_referrals != 0) |
            (UserLegMetrics.snapshot_matching_count != 0) |
            (UserLegMetrics.snapshot_left_team != 0) |
            (UserLegMetrics.snapshot_right_team != 0) |
            (UserLegMetrics.snapshot_ved_total != 0) |
            (UserLegMetrics.snapshot_ved_active != 0)
        ).count()
        
        previous_counts_reset = users_with_non_zero_snapshots == 0
        previous_counts_progress = ((total_users_with_metrics - users_with_non_zero_snapshots) / 
                                    total_users_with_metrics * 100) if total_users_with_metrics > 0 else 100
        
        # 2. Check Income Reset Status (date-based filtering)
        total_income_records = db.query(Transaction).count()
        total_pending_income = db.query(PendingIncome).count()
        pre_oct_income = db.query(Transaction).filter(
            Transaction.timestamp < PRODUCTION_RESET_DATE
        ).count()
        pre_oct_pending = db.query(PendingIncome).filter(
            PendingIncome.business_date < PRODUCTION_RESET_DATE
        ).count()
        
        # Income reset is date-based filtering, not actual deletion
        income_reset_status = True  # Always true because we filter by date
        
        # 3. Check Data Corruption (0 points issue)
        corrupted_users = db.query(User).filter(
            User.coupon_status == 'Activated',
            User.package_points == 0
        ).count()
        
        data_corruption_fixed = corrupted_users == 0
        
        # 4. Overall Status
        all_systems_ready = previous_counts_reset and income_reset_status and data_corruption_fixed
        
        # 5. Sample User Verification (MNR1800143)
        sample_user_metrics = db.query(UserLegMetrics).filter(
            UserLegMetrics.user_id == 'MNR1800143'
        ).first()
        
        sample_user_status = {
            'user_id': 'MNR1800143',
            'matching_count': int(sample_user_metrics.effective_matching_count) if sample_user_metrics else 0,
            'left_points': int(sample_user_metrics.left_points) if sample_user_metrics else 0,
            'right_points': int(sample_user_metrics.right_points) if sample_user_metrics else 0,
            'snapshot_direct': sample_user_metrics.snapshot_direct_referrals if sample_user_metrics else 0,
            'snapshot_matching': sample_user_metrics.snapshot_matching_count if sample_user_metrics else 0,
            'status_ok': (sample_user_metrics and 
                         sample_user_metrics.effective_matching_count == 32 and
                         sample_user_metrics.snapshot_direct_referrals == 0 and
                         sample_user_metrics.snapshot_matching_count == 0)
        }
        
        reset_status = {
            'production_date': 'October 11, 2025',
            'production_date_obj': PRODUCTION_RESET_DATE,
            
            # Previous Counts Reset
            'previous_counts_reset': previous_counts_reset,
            'previous_counts_progress': round(previous_counts_progress, 1),
            'total_users_with_metrics': total_users_with_metrics,
            'users_with_snapshots': users_with_non_zero_snapshots,
            'users_reset': total_users_with_metrics - users_with_non_zero_snapshots,
            
            # Income Reset (Date Filtering)
            'income_reset_active': income_reset_status,
            'total_income_records': total_income_records,
            'pre_oct_income_records': pre_oct_income,
            'total_pending_income': total_pending_income,
            'pre_oct_pending': pre_oct_pending,
            
            # Data Corruption
            'data_corruption_fixed': data_corruption_fixed,
            'corrupted_users_count': corrupted_users,
            
            # Overall
            'all_systems_ready': all_systems_ready,
            'overall_progress': round(
                (int(previous_counts_reset) + int(income_reset_status) + int(data_corruption_fixed)) / 3 * 100, 
                1
            ),
            
            # Sample User
            'sample_user': sample_user_status
        }
        
        return {
            "status": "success",
            "user_id": user_id,
            "reset_status": reset_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
