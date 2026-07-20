"""
RVZ Admin - Scheduler Management & Manual Triggers
Allows RVZ ID to monitor and manually trigger automated tasks
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid
from app.models.user import User
from fastapi import Request
from app.core.scheduler import (
    get_scheduler,
    calculate_previous_day_incomes,
    run_daily_wallet_sync,
    generate_automatic_withdrawals,
    refresh_leg_metrics_cache
)
from datetime import datetime, timedelta, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def require_rvz_id(request: Request, db: Session = Depends(get_db)):
    """Require authenticated staff/user - DC Protocol: Menu-based access control"""
    current_user = await get_current_user_hybrid(request, db)
    return current_user

@router.get("/rvz/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Get current status of all scheduled tasks
    Shows: Job name, next run time, last run (if available), enabled status
    """
    try:
        scheduler = get_scheduler()
        
        if not scheduler:
            return {
                "scheduler_active": False,
                "message": "APScheduler is not initialized",
                "jobs": []
            }
        
        jobs_info = []
        job_ids = [
            'leg_metrics_cache_refresh',
            'midnight_income_calculation', 
            'monthly_field_allowance_calculation',
            'daily_wallet_sync_kyc_enforcement',
            'automatic_withdrawal_generation'
        ]
        
        for job_id in job_ids:
            job = scheduler.get_job(job_id)
            if job:
                jobs_info.append({
                    "job_id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "enabled": True
                })
        
        # Get last execution logs from database
        from app.models.system_log import SchedulerLog
        last_runs = db.query(SchedulerLog).order_by(SchedulerLog.triggered_at.desc()).limit(10).all()
        
        last_runs_info = [
            {
                "id": log.id,
                "job_name": log.job_name,
                "scheduled_date": log.scheduled_date.isoformat() if log.scheduled_date else None,
                "triggered_at": log.triggered_at.isoformat() if log.triggered_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "overall_status": log.overall_status,
                "total_users_affected": log.total_users_affected,
                "total_incomes_created": log.total_incomes_created,
                "error_message": log.error_message
            }
            for log in last_runs
        ]
        
        return {
            "scheduler_active": True,
            "timezone": "Asia/Kolkata (IST)",
            "current_time": datetime.now().isoformat(),
            "jobs": jobs_info,
            "last_runs": last_runs_info
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/scheduler/trigger/income-calculation")
async def trigger_income_calculation(
    business_date: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Manually trigger daily income calculation
    Optional: Specify business_date (YYYY-MM-DD) to recalculate specific date
    Default: Yesterday's date
    """
    try:
        if business_date:
            target_date = datetime.strptime(business_date, "%Y-%m-%d").date()
        else:
            target_date = (datetime.now() - timedelta(days=1)).date()
        
        # Run in background to avoid timeout
        background_tasks.add_task(calculate_previous_day_incomes, target_date)
        
        return {
            "status": "success",
            "message": f"Income calculation triggered for {target_date}",
            "business_date": target_date.isoformat(),
            "triggered_by": current_user.id,
            "execution": "background_task"
        }
        
    except Exception as e:
        logger.error(f"Error triggering income calculation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rvz/scheduler/trigger/wallet-sync")
async def trigger_wallet_sync(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Manually trigger KYC-based wallet sync
    Transfers earning_wallet → withdrawable_wallet for KYC-approved users
    """
    try:
        # Run in background
        background_tasks.add_task(run_daily_wallet_sync)
        
        return {
            "status": "success",
            "message": "Wallet sync (KYC enforcement) triggered",
            "triggered_by": current_user.id,
            "execution": "background_task"
        }
        
    except Exception as e:
        logger.error(f"Error triggering wallet sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/scheduler/trigger/auto-withdrawals")
async def trigger_auto_withdrawals(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Manually trigger automatic withdrawal generation
    Creates withdrawal requests for eligible users
    """
    try:
        # Run in background
        background_tasks.add_task(generate_automatic_withdrawals)
        
        return {
            "status": "success",
            "message": "Automatic withdrawal generation triggered",
            "triggered_by": current_user.id,
            "execution": "background_task"
        }
        
    except Exception as e:
        logger.error(f"Error triggering auto withdrawals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rvz/scheduler/trigger/cache-refresh")
async def trigger_cache_refresh(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Manually trigger leg metrics cache refresh
    Pre-calculates leg points for performance optimization
    """
    try:
        # Run in background
        background_tasks.add_task(refresh_leg_metrics_cache)
        
        return {
            "status": "success",
            "message": "Leg metrics cache refresh triggered",
            "triggered_by": current_user.id,
            "execution": "background_task"
        }
        
    except Exception as e:
        logger.error(f"Error triggering cache refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rvz/scheduler/logs")
async def get_scheduler_logs(
    limit: int = 50,
    job_type: Optional[str] = None,
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Get detailed scheduler execution logs
    Filter by job_type if specified
    """
    try:
        from app.models.system_log import SchedulerLog
        
        query = db.query(SchedulerLog).order_by(SchedulerLog.triggered_at.desc())
        
        if job_type:
            query = query.filter(SchedulerLog.job_name == job_type)
        
        logs = query.limit(limit).all()
        
        return {
            "total_logs": len(logs),
            "logs": [
                {
                    "id": log.id,
                    "job_id": log.job_id,
                    "job_name": log.job_name,
                    "scheduled_date": log.scheduled_date.isoformat() if log.scheduled_date else None,
                    "triggered_at": log.triggered_at.isoformat() if log.triggered_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "duration_seconds": (log.completed_at - log.triggered_at).total_seconds() if log.completed_at and log.triggered_at else None,
                    "overall_status": log.overall_status,
                    "direct_referral_status": log.direct_referral_status,
                    "matching_status": log.matching_status,
                    "ved_income_status": log.ved_income_status,
                    "guru_dakshina_status": log.guru_dakshina_status,
                    "field_allowance_status": log.field_allowance_status,
                    "withdrawal_status": log.withdrawal_status,
                    "total_users_affected": log.total_users_affected,
                    "total_incomes_created": log.total_incomes_created,
                    "error_message": log.error_message
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rvz/scheduler/trigger/income-preview")
async def preview_income_trigger(
    start_date: str,
    end_date: str,
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Preview income trigger: Shows impacted dates, users, and estimated income records
    that would be created for a given date range. Dry-run only - no changes made.
    """
    from app.models.system_log import SchedulerLog
    from app.models.transaction import PendingIncome
    from sqlalchemy import func
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if end_dt > date.today():
        raise HTTPException(status_code=400, detail="Cannot process future dates")
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")
    if (end_dt - start_dt).days > 60:
        raise HTTPException(status_code=400, detail="Maximum date range is 60 days")
    
    activated_users = db.query(User).filter(
        User.coupon_status.in_(['Activated', 'Active']),
        User.package_points > 0
    ).all()
    
    from sqlalchemy import cast, Date
    existing_incomes = db.query(
        cast(PendingIncome.business_date, Date).label('bdate'),
        PendingIncome.income_type,
        func.count(PendingIncome.id).label('count')
    ).filter(
        PendingIncome.business_date >= datetime.combine(start_dt, datetime.min.time()),
        PendingIncome.business_date <= datetime.combine(end_dt, datetime.max.time())
    ).group_by(cast(PendingIncome.business_date, Date), PendingIncome.income_type).all()

    existing_by_date = {}
    for row in existing_incomes:
        d = row.bdate.strftime('%Y-%m-%d') if hasattr(row.bdate, 'strftime') else str(row.bdate)[:10]
        if d not in existing_by_date:
            existing_by_date[d] = {}
        existing_by_date[d][row.income_type] = row.count

    from sqlalchemy import or_
    scheduler_logs = db.query(SchedulerLog).filter(
        or_(
            SchedulerLog.job_name == 'Income Calculation',
            SchedulerLog.job_name.like('Manual Income Calculation%')
        ),
        SchedulerLog.scheduled_date >= datetime.combine(start_dt, datetime.min.time()),
        SchedulerLog.scheduled_date <= datetime.combine(end_dt, datetime.max.time())
    ).all()
    
    log_by_date = {}
    for log in scheduler_logs:
        d = log.scheduled_date.strftime('%Y-%m-%d') if log.scheduled_date else None
        if d:
            log_by_date[d] = {
                "total_incomes_created": log.total_incomes_created,
                "overall_status": log.overall_status,
                "matching_status": log.matching_status
            }

    dates_detail = []
    total_impacted_dates = 0
    current_dt = start_dt
    while current_dt <= end_dt:
        d_str = current_dt.strftime('%Y-%m-%d')
        existing = existing_by_date.get(d_str, {})
        log_info = log_by_date.get(d_str, {})
        has_matching = existing.get('Matching Referral', 0) > 0
        has_direct = existing.get('Direct Referral', 0) > 0
        has_ved = existing.get('Ved Income', 0) > 0
        has_guru = existing.get('Guru Dakshina', 0) > 0
        total_existing = sum(existing.values())
        scheduler_ran = bool(log_info and log_info.get('overall_status') in ('Completed', 'Completed with Errors'))
        scheduler_had_errors = bool(log_info and log_info.get('overall_status') == 'Completed with Errors')
        needs_processing = (total_existing == 0 and not scheduler_ran) or scheduler_had_errors
        if needs_processing:
            total_impacted_dates += 1
        dates_detail.append({
            "date": d_str,
            "existing_records": existing,
            "total_existing": total_existing,
            "has_matching": has_matching,
            "has_direct": has_direct,
            "has_ved": has_ved,
            "has_guru": has_guru,
            "scheduler_log": log_info,
            "scheduler_ran": scheduler_ran,
            "scheduler_had_errors": scheduler_had_errors,
            "needs_processing": needs_processing
        })
        current_dt += timedelta(days=1)
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates_detail),
        "impacted_dates": total_impacted_dates,
        "total_activated_users": len(activated_users),
        "dates": dates_detail,
        "duplicate_protection": "Built-in via check_duplicate_income() - existing records will be skipped automatically",
        "income_types": ["Matching Referral", "Direct Referral", "Ved Income", "Guru Dakshina", "Exempted Matching"]
    }


@router.post("/rvz/scheduler/trigger/income-execute")
async def execute_income_trigger(
    start_date: str,
    end_date: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Execute income trigger: Runs income calculation for each date in the range.
    Uses existing calculate_incomes_for_date_manual() which has built-in duplicate protection.
    Runs in background to avoid timeout.
    """
    from app.core.scheduler import calculate_incomes_for_date_manual
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if end_dt > date.today():
        raise HTTPException(status_code=400, detail="Cannot process future dates")
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")
    if (end_dt - start_dt).days > 60:
        raise HTTPException(status_code=400, detail="Maximum date range is 60 days")
    
    dates_to_process = []
    current_dt = start_dt
    while current_dt <= end_dt:
        dates_to_process.append(current_dt)
        current_dt += timedelta(days=1)
    
    triggered_by_id = str(current_user.id)
    
    def run_batch_income(dates_list, triggered_by):
        import logging
        batch_logger = logging.getLogger(__name__)
        batch_logger.warning(f"INCOME TRIGGER: Processing {len(dates_list)} dates ({dates_list[0]} to {dates_list[-1]}) by {triggered_by}")
        total_created = 0
        for d in dates_list:
            try:
                result = calculate_incomes_for_date_manual(d, triggered_by=triggered_by)
                created = result.get('total_incomes_created', 0)
                total_created += created
                if created > 0:
                    batch_logger.warning(f"INCOME TRIGGER: {d} -> {created} incomes created")
                else:
                    batch_logger.info(f"INCOME TRIGGER: {d} -> 0 new incomes (already processed or no eligible users)")
            except Exception as e:
                batch_logger.error(f"INCOME TRIGGER ERROR: {d} -> {e}", exc_info=True)
        batch_logger.warning(f"INCOME TRIGGER COMPLETE: {len(dates_list)} dates, {total_created} total incomes created")
    
    background_tasks.add_task(run_batch_income, dates_to_process, triggered_by_id)
    
    return {
        "status": "success",
        "message": f"Income calculation triggered for {len(dates_to_process)} dates ({start_date} to {end_date})",
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates_to_process),
        "triggered_by": triggered_by_id,
        "execution": "background",
        "duplicate_protection": "Active - existing records will be skipped"
    }


@router.get("/rvz/scheduler/trigger/income-status")
async def get_income_trigger_status(
    current_user: User = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Get recent income processing status - shows scheduler logs and income records by date.
    Used to monitor batch trigger progress.
    """
    from app.models.system_log import SchedulerLog
    from app.models.transaction import PendingIncome
    from sqlalchemy import func
    
    try:
        from sqlalchemy import or_
        all_log_list = db.query(SchedulerLog).filter(
            or_(
                SchedulerLog.job_name == 'Income Calculation',
                SchedulerLog.job_name.like('Manual Income Calculation%')
            )
        ).order_by(SchedulerLog.triggered_at.desc()).limit(30).all()
        
        all_logs = {log.id: log for log in all_log_list}
        
        daily_status = []
        for log in sorted(all_logs.values(), key=lambda x: x.triggered_at or datetime.min, reverse=True):
            daily_status.append({
                "id": log.id,
                "scheduled_date": log.scheduled_date.isoformat() if log.scheduled_date else None,
                "triggered_at": log.triggered_at.isoformat() if log.triggered_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "job_name": log.job_name,
                "overall_status": log.overall_status,
                "matching_status": log.matching_status,
                "direct_referral_status": log.direct_referral_status,
                "ved_income_status": getattr(log, 'ved_income_status', None),
                "guru_dakshina_status": getattr(log, 'guru_dakshina_status', None),
                "total_incomes_created": log.total_incomes_created,
                "total_users_affected": log.total_users_affected,
                "error_message": log.error_message
            })
        
        from sqlalchemy import cast, Date
        income_summary = db.query(
            cast(PendingIncome.business_date, Date).label('bdate'),
            PendingIncome.income_type,
            func.count(PendingIncome.id).label('count'),
            func.sum(PendingIncome.gross_amount).label('total_gross')
        ).group_by(
            cast(PendingIncome.business_date, Date),
            PendingIncome.income_type
        ).order_by(cast(PendingIncome.business_date, Date).desc()).limit(120).all()
        
        income_by_date = {}
        for row in income_summary:
            d = row.bdate.strftime('%Y-%m-%d') if row.bdate else None
            if d not in income_by_date:
                income_by_date[d] = {"date": d, "types": {}, "total_records": 0, "total_gross": 0}
            income_by_date[d]["types"][row.income_type] = {
                "count": row.count,
                "gross": float(row.total_gross or 0)
            }
            income_by_date[d]["total_records"] += row.count
            income_by_date[d]["total_gross"] += float(row.total_gross or 0)
        
        return {
            "scheduler_logs": daily_status[:30],
            "income_by_date": sorted(income_by_date.values(), key=lambda x: x['date'] or '', reverse=True)[:30]
        }
    except Exception as e:
        logger.error(f"Error getting income trigger status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rvz/scheduler/trigger/income-trigger/diagnose-matching")
async def diagnose_matching_calculation(
    user_id: str = None,
    business_date: str = None,
    current_user = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """Diagnose why matching referral income is not being created for a specific user or all users with available pairs"""
    try:
        from app.services.sql_utils import get_leg_points_sql, get_consumed_points_sql, get_consumed_zero_point_sql
        from app.services.sql_utils import get_leg_points_with_welcome_coupon_breakdown
        from app.core.scheduler import check_duplicate_income, check_direct_referrals_both_sides, check_first_matching_achieved
        from app.models.transaction import PendingIncome
        from sqlalchemy import func
        
        target_date = datetime.strptime(business_date, '%Y-%m-%d').date() if business_date else (datetime.utcnow() - timedelta(days=1)).date()
        
        if user_id:
            users = db.query(User).filter(User.id == user_id).all()
        else:
            users = db.query(User).filter(
                User.coupon_status.in_(['Activated', 'Active']),
                User.package_points > 0
            ).all()
        
        results = []
        users_with_available = 0
        
        for user in users:
            try:
                leg_points = get_leg_points_sql(db, user.id)
                consumed = get_consumed_points_sql(db, user.id, 'Matching Referral')
                consumed_zero = get_consumed_zero_point_sql(db, user.id)
                
                avail_left = leg_points['left'] - consumed['left']
                avail_right = leg_points['right'] - consumed['right']
                min_pairs = min(avail_left, avail_right) if avail_left > 0 and avail_right > 0 else 0
                
                previous_matching_count = db.query(func.count(PendingIncome.id)).filter(
                    PendingIncome.user_id == user.id,
                    PendingIncome.income_type == 'Matching Referral'
                ).scalar() or 0
                
                is_first = previous_matching_count == 0
                
                has_dup = check_duplicate_income(db, user.id, 'Matching Referral', target_date)
                
                if min_pairs > 0 or (user_id is not None):
                    has_direct_both = check_direct_referrals_both_sides(db, user.id)
                    has_first_matching = check_first_matching_achieved(db, user.id)
                    
                    entry = {
                        "user_id": user.id,
                        "package_points": float(user.package_points),
                        "total_left": leg_points['left'],
                        "total_right": leg_points['right'],
                        "consumed_left": consumed['left'],
                        "consumed_right": consumed['right'],
                        "available_left": avail_left,
                        "available_right": avail_right,
                        "available_pairs": int(min_pairs),
                        "is_first_matching": is_first,
                        "previous_matching_count": previous_matching_count,
                        "has_duplicate_for_date": has_dup,
                        "has_direct_both_sides": has_direct_both,
                        "has_first_matching_achieved": has_first_matching,
                        "left_zero_count": leg_points.get('left_zero_point_count', 0),
                        "right_zero_count": leg_points.get('right_zero_point_count', 0),
                    }
                    
                    if min_pairs > 0:
                        users_with_available += 1
                        try:
                            breakdown = get_leg_points_with_welcome_coupon_breakdown(db, user.id)
                            entry["welcome_breakdown"] = breakdown
                        except Exception as be:
                            entry["welcome_breakdown_error"] = str(be)
                    
                    results.append(entry)
            except Exception as ue:
                results.append({"user_id": user.id, "error": str(ue)})
        
        return {
            "target_date": str(target_date),
            "total_users_checked": len(users),
            "users_with_available_pairs": users_with_available,
            "results": results[:50]
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/rvz/scheduler/trigger/income-exclusions")
async def get_income_exclusions(
    current_user = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """Get list of users excluded from income calculations with reasons.
    Excluded categories: Welcome Coupon, Star (₹1000, 0 pts), Loyal (₹500, 0 pts)"""
    try:
        from sqlalchemy import text as sa_text
        
        query = sa_text("""
            SELECT 
                u.id,
                u.name,
                COALESCE(c.coupon_type, '') as coupon_type,
                u.package_points,
                COALESCE(u.is_welcome_coupon, false) as is_welcome_coupon,
                u.coupon_status,
                u.activation_date,
                u.referrer_id,
                CASE 
                    WHEN COALESCE(u.is_welcome_coupon, false) = true THEN 'Welcome Coupon'
                    WHEN COALESCE(u.package_points, 0) = 0 AND COALESCE(c.coupon_type, '') = '1000' THEN 'Star (₹1,000 - 0 Points)'
                    WHEN COALESCE(u.package_points, 0) = 0 AND COALESCE(c.coupon_type, '') = '500' THEN 'Loyal (₹500 - 0 Points)'
                    WHEN COALESCE(u.package_points, 0) = 0 THEN 'Zero Points Package'
                    ELSE 'Unknown'
                END as exclusion_reason,
                CASE
                    WHEN COALESCE(u.is_welcome_coupon, false) = true THEN 'welcome_coupon'
                    WHEN COALESCE(u.package_points, 0) = 0 THEN 'zero_points'
                    ELSE 'other'
                END as exclusion_type
            FROM "user" u
            LEFT JOIN coupon c ON c.owner_id = u.id
            WHERE u.coupon_status IN ('Active', 'Activated')
              AND (COALESCE(u.is_welcome_coupon, false) = true OR COALESCE(u.package_points, 0) = 0)
            ORDER BY 
                CASE WHEN COALESCE(u.is_welcome_coupon, false) = true THEN 0 ELSE 1 END,
                COALESCE(c.coupon_type, ''),
                u.name
        """)
        
        rows = db.execute(query).fetchall()
        
        excluded_users = []
        welcome_count = 0
        star_count = 0
        loyal_count = 0
        zero_other_count = 0
        
        for row in rows:
            coupon_type_val = row[2] or ''
            user_data = {
                "user_id": row[0],
                "name": row[1],
                "coupon_type": coupon_type_val,
                "package_points": float(row[3] or 0),
                "is_welcome_coupon": row[4],
                "coupon_status": row[5],
                "activation_date": str(row[6]) if row[6] else None,
                "sponsor_id": row[7],
                "exclusion_reason": row[8],
                "exclusion_type": row[9]
            }
            excluded_users.append(user_data)
            
            if row[4]:
                welcome_count += 1
            elif coupon_type_val == '1000':
                star_count += 1
            elif coupon_type_val == '500':
                loyal_count += 1
            else:
                zero_other_count += 1
        
        total_active = db.execute(sa_text("""
            SELECT COUNT(*) FROM "user" WHERE coupon_status IN ('Active', 'Activated')
        """)).scalar() or 0
        
        return {
            "total_excluded": len(excluded_users),
            "total_active_users": total_active,
            "total_eligible": total_active - len(excluded_users),
            "breakdown": {
                "welcome_coupon": welcome_count,
                "star_zero_points": star_count,
                "loyal_zero_points": loyal_count,
                "other_zero_points": zero_other_count
            },
            "exclusion_rules": [
                {"type": "Welcome Coupon", "description": "Users with is_welcome_coupon=true. Excluded from ALL income types and pair calculations.", "count": welcome_count},
                {"type": "Star (₹1,000)", "description": "Package points = 0. Excluded from pair calculations. Cannot generate Direct Referral, Ved Income, or Guru Dakshina.", "count": star_count},
                {"type": "Loyal (₹500)", "description": "Package points = 0. Excluded from pair calculations. Cannot generate Direct Referral, Ved Income, or Guru Dakshina.", "count": loyal_count}
            ],
            "excluded_users": excluded_users
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/rvz/scheduler/trigger/scheduler-run-logs")
async def get_scheduler_run_logs(
    limit: int = 30,
    current_user = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """Get detailed scheduler run logs with status tracking for each income type"""
    try:
        from sqlalchemy import text as sa_text
        
        query = sa_text("""
            SELECT 
                id,
                scheduled_date,
                triggered_at,
                completed_at,
                overall_status,
                COALESCE(matching_status, 'Pending') as matching_status,
                COALESCE(direct_referral_status, 'Pending') as direct_referral_status,
                COALESCE(ved_income_status, 'Pending') as ved_income_status,
                COALESCE(guru_dakshina_status, 'Pending') as guru_dakshina_status,
                COALESCE(awards_status, 'Pending') as awards_status,
                total_incomes_created,
                total_users_affected,
                error_message,
                job_name,
                income_triggered,
                EXTRACT(EPOCH FROM (completed_at - triggered_at)) as duration_seconds,
                COALESCE(field_allowance_status, 'Pending') as field_allowance_status,
                COALESCE(wallet_sync_status, 'Pending') as wallet_sync_status,
                COALESCE(withdrawal_status, 'Pending') as withdrawal_status
            FROM scheduler_log
            ORDER BY scheduled_date DESC, triggered_at DESC
            LIMIT :limit
        """)
        
        rows = db.execute(query, {"limit": limit}).fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "run_date": str(row[1]) if row[1] else None,
                "started_at": str(row[2]) if row[2] else None,
                "completed_at": str(row[3]) if row[3] else None,
                "status": row[4],
                "matching_status": row[5],
                "direct_referral_status": row[6],
                "ved_income_status": row[7],
                "guru_dakshina_status": row[8],
                "awards_status": row[9],
                "total_incomes_created": row[10] or 0,
                "total_users_affected": row[11] or 0,
                "error_message": row[12],
                "job_name": row[13],
                "income_triggered": row[14],
                "duration_seconds": round(float(row[15] or 0), 1),
                "field_allowance_status": row[16],
                "wallet_sync_status": row[17],
                "withdrawal_status": row[18]
            })
        
        return {
            "total_logs": len(logs),
            "logs": logs
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/rvz/scheduler/ved-tracker/{user_id}")
async def get_ved_tracker(
    user_id: str,
    current_user = Depends(require_rvz_id),
    db: Session = Depends(get_db)
):
    """
    Ved Tracker: Shows complete Ved connections for any MNR ID.
    
    Returns:
    - User's own Ved status (is_ved, ved_owner, ved_head info)
    - Ved Heads owned by this user (3rd+ direct referrals)
    - Ved Team members under each Ved Head with levels
    - Ved Income eligibility status
    - Ved Income history
    """
    try:
        from sqlalchemy import text as sa_text
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        result = {
            "user_id": user.id,
            "user_name": user.name,
            "package_points": float(user.package_points or 0),
            "activation_date": str(user.activation_date) if user.activation_date else None,
            "coupon_status": user.coupon_status,
            "is_ved_head": user.is_ved,
            "ved_owner_id": user.ved_owner_id,
            "ved_paused": getattr(user, 'ved_paused', False),
        }
        
        if user.ved_owner_id:
            owner = db.query(User).filter(User.id == user.ved_owner_id).first()
            result["ved_owner_name"] = owner.name if owner else "Unknown"
        else:
            result["ved_owner_name"] = None
        
        direct_refs_query = sa_text("""
            SELECT u.id, u.name, u.activation_date, u.package_points, u.coupon_status,
                   u.is_ved, u.ved_owner_id,
                   ROW_NUMBER() OVER (ORDER BY u.registration_date, u.id) as referral_number
            FROM "user" u
            WHERE u.referrer_id = :user_id
            ORDER BY u.registration_date, u.id
        """)
        direct_refs = db.execute(direct_refs_query, {"user_id": user_id}).fetchall()
        
        result["direct_referrals"] = []
        ved_heads = []
        for ref in direct_refs:
            ref_data = {
                "id": ref[0],
                "name": ref[1],
                "activation_date": str(ref[2]) if ref[2] else None,
                "package_points": float(ref[3] or 0),
                "coupon_status": ref[4],
                "is_ved_head": ref[5],
                "ved_owner_id": ref[6],
                "referral_number": ref[7],
                "is_3rd_or_later": ref[7] >= 3
            }
            result["direct_referrals"].append(ref_data)
            if ref[7] >= 3:
                ved_heads.append(ref_data)
        
        result["ved_heads_owned"] = []
        for vh in ved_heads:
            vh_id = vh["id"]
            
            team_query = sa_text("""
                WITH RECURSIVE ved_downlines AS (
                    SELECT 
                        p.child_id,
                        p.side,
                        1 as level
                    FROM placement p
                    WHERE p.parent_id = :ved_head_id
                    
                    UNION ALL
                    
                    SELECT 
                        p.child_id,
                        p.side,
                        vd.level + 1
                    FROM ved_downlines vd
                    INNER JOIN placement p ON p.parent_id = vd.child_id
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE vd.level < 15
                      AND u.is_ved = false
                )
                SELECT 
                    vd.child_id,
                    u.name,
                    u.activation_date,
                    u.package_points,
                    u.coupon_status,
                    u.is_ved,
                    vd.level,
                    vd.side
                FROM ved_downlines vd
                INNER JOIN "user" u ON u.id = vd.child_id
                ORDER BY vd.level, u.name
            """)
            team_rows = db.execute(team_query, {"ved_head_id": vh_id}).fetchall()
            
            team_members = []
            total_active = 0
            total_inactive = 0
            for tr in team_rows:
                is_activated = tr[2] is not None and float(tr[3] or 0) > 0
                if is_activated:
                    total_active += 1
                else:
                    total_inactive += 1
                team_members.append({
                    "id": tr[0],
                    "name": tr[1],
                    "activation_date": str(tr[2]) if tr[2] else None,
                    "package_points": float(tr[3] or 0),
                    "coupon_status": tr[4],
                    "is_ved_head_nested": tr[5],
                    "level": tr[6],
                    "side": tr[7],
                    "is_activated": is_activated
                })
            
            result["ved_heads_owned"].append({
                "ved_head_id": vh_id,
                "ved_head_name": vh["name"],
                "ved_head_activated": vh["activation_date"] is not None and vh["package_points"] >= 0.5,
                "ved_head_activation_date": vh["activation_date"],
                "ved_head_package_points": vh["package_points"],
                "referral_number": vh["referral_number"],
                "team_total": len(team_members),
                "team_active": total_active,
                "team_inactive": total_inactive,
                "team_members": team_members
            })
        
        from app.core.scheduler import check_direct_referrals_both_sides, check_first_matching_achieved
        result["eligibility"] = {
            "has_direct_both_sides": check_direct_referrals_both_sides(db, user_id),
            "has_first_matching": check_first_matching_achieved(db, user_id),
            "is_activated": user.activation_date is not None and float(user.package_points or 0) >= 0.5,
            "has_ved_head": len(ved_heads) > 0,
            "any_ved_head_activated": any(vh.get("ved_head_activated") for vh in result["ved_heads_owned"])
        }
        result["eligibility"]["fully_eligible"] = all([
            result["eligibility"]["is_activated"],
            result["eligibility"]["has_direct_both_sides"],
            result["eligibility"]["has_first_matching"],
            result["eligibility"]["has_ved_head"],
            result["eligibility"]["any_ved_head_activated"]
        ])
        
        income_query = sa_text("""
            SELECT pi.id, pi.business_date, pi.gross_amount, pi.net_amount, 
                   pi.related_user_id, u.name as related_user_name,
                   pi.verification_status, pi.notes
            FROM pending_income pi
            LEFT JOIN "user" u ON u.id = pi.related_user_id
            WHERE pi.user_id = :user_id AND pi.income_type = 'Ved Income'
            ORDER BY pi.business_date DESC
            LIMIT 20
        """)
        income_rows = db.execute(income_query, {"user_id": user_id}).fetchall()
        
        result["ved_income_history"] = []
        for ir in income_rows:
            result["ved_income_history"].append({
                "id": ir[0],
                "business_date": str(ir[1]) if ir[1] else None,
                "gross_amount": float(ir[2] or 0),
                "net_amount": float(ir[3] or 0),
                "related_user_id": ir[4],
                "related_user_name": ir[5],
                "status": ir[6],
                "notes": ir[7]
            })
        
        member_of_query = sa_text("""
            SELECT vtm.ved_owner_id, o.name as owner_name,
                   vtm.ved_head_id, h.name as head_name,
                   vtm.level, vtm.position, vtm.is_active,
                   o.activation_date as owner_activation_date,
                   h.activation_date as head_activation_date,
                   o.package_points as owner_points, o.coupon_status as owner_coupon,
                   h.package_points as head_points, h.coupon_status as head_coupon
            FROM ved_team_member vtm
            LEFT JOIN "user" o ON o.id = vtm.ved_owner_id
            LEFT JOIN "user" h ON h.id = vtm.ved_head_id
            WHERE vtm.member_id = :user_id
            ORDER BY vtm.is_active DESC
        """)
        member_rows = db.execute(member_of_query, {"user_id": user_id}).fetchall()
        
        result["member_of_ved_teams"] = []
        for mr in member_rows:
            owner_income_query = sa_text("""
                SELECT COUNT(*) FROM pending_income
                WHERE user_id = :owner_id AND income_type = 'Ved Income'
            """)
            owner_ved_income_count = db.execute(owner_income_query, {"owner_id": mr[0]}).scalar() or 0
            
            team_entry = {
                "ved_owner_id": mr[0],
                "ved_owner_name": mr[1],
                "ved_head_id": mr[2],
                "ved_head_name": mr[3],
                "level": mr[4],
                "position": mr[5],
                "is_active": mr[6],
                "owner_activated": mr[7] is not None,
                "owner_activation_date": str(mr[7]) if mr[7] else None,
                "head_activated": mr[8] is not None,
                "head_activation_date": str(mr[8]) if mr[8] else None,
                "owner_points": float(mr[9] or 0),
                "owner_coupon": mr[10],
                "head_points": float(mr[11] or 0),
                "head_coupon": mr[12],
                "owner_ved_income_created": owner_ved_income_count > 0,
                "owner_ved_income_count": owner_ved_income_count,
                "full_team": []
            }
            owner_id = mr[0]
            owner_refs_query = sa_text("""
                SELECT u.id, u.name, u.package_points, u.coupon_status, u.is_ved, u.ved_owner_id,
                       u.activation_date, u.position,
                       ROW_NUMBER() OVER (ORDER BY u.registration_date, u.id) as ref_number
                FROM "user" u WHERE u.referrer_id = :owner_id
                ORDER BY u.registration_date, u.id
            """)
            owner_refs = db.execute(owner_refs_query, {"owner_id": owner_id}).fetchall()
            
            for oref in owner_refs:
                ref_id = oref[0]
                ref_num = oref[8]
                is_ved_head = oref[4] and oref[5] == owner_id
                team_entry["full_team"].append({
                    "member_id": ref_id,
                    "name": oref[1],
                    "parent_id": owner_id,
                    "level": 0,
                    "position": oref[7] or "-",
                    "is_active": oref[6] is not None,
                    "package_points": float(oref[2] or 0),
                    "coupon_status": oref[3],
                    "is_ved": oref[4],
                    "ved_owner_id": oref[5],
                    "is_current_user": ref_id == user_id,
                    "is_ved_head_row": is_ved_head,
                    "ref_number": int(ref_num),
                    "row_type": "ved_head" if is_ved_head else "direct_ref"
                })
                
                if is_ved_head:
                    members_query = sa_text("""
                        SELECT vtm.member_id, u.name, vtm.parent_id, vtm.level, vtm.position,
                               vtm.is_active, u.package_points, u.coupon_status, u.is_ved, u.ved_owner_id
                        FROM ved_team_member vtm
                        LEFT JOIN "user" u ON u.id = vtm.member_id
                        WHERE vtm.ved_owner_id = :owner_id AND vtm.ved_head_id = :head_id
                        ORDER BY vtm.level, vtm.position, u.name
                    """)
                    members = db.execute(members_query, {"owner_id": owner_id, "head_id": ref_id}).fetchall()
                    for mem in members:
                        team_entry["full_team"].append({
                            "member_id": mem[0],
                            "name": mem[1],
                            "parent_id": mem[2],
                            "level": mem[3],
                            "position": mem[4],
                            "is_active": mem[5],
                            "package_points": float(mem[6] or 0),
                            "coupon_status": mem[7],
                            "is_ved": mem[8],
                            "ved_owner_id": mem[9],
                            "is_current_user": mem[0] == user_id,
                            "is_ved_head_row": False,
                            "ref_number": None,
                            "row_type": "member"
                        })
            
            result["member_of_ved_teams"].append(team_entry)
        
        referral_chain_query = sa_text("""
            WITH RECURSIVE ref_chain AS (
                SELECT u.id, u.name, u.referrer_id, u.is_ved, u.ved_owner_id, u.position, 
                       u.package_points, u.coupon_status, 1 as depth
                FROM "user" u WHERE u.id = :user_id
                UNION ALL
                SELECT u.id, u.name, u.referrer_id, u.is_ved, u.ved_owner_id, u.position,
                       u.package_points, u.coupon_status, rc.depth + 1
                FROM "user" u
                JOIN ref_chain rc ON u.id = rc.referrer_id
                WHERE rc.depth < 20 AND rc.referrer_id IS NOT NULL
            )
            SELECT id, name, referrer_id, is_ved, ved_owner_id, position, package_points, coupon_status, depth
            FROM ref_chain
            WHERE depth > 1
            ORDER BY depth
        """)
        chain_rows = db.execute(referral_chain_query, {"user_id": user_id}).fetchall()
        
        result["placement_chain_upward"] = []
        for cr in chain_rows:
            result["placement_chain_upward"].append({
                "id": cr[0],
                "name": cr[1],
                "referrer_id": cr[2],
                "is_ved_head": cr[3],
                "ved_owner_id": cr[4],
                "side": cr[5],
                "package_points": float(cr[6] or 0),
                "coupon_status": cr[7],
                "depth": cr[8]
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Ved Tracker error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
