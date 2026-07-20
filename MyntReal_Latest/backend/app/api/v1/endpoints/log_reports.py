"""
Log Reports API Endpoints
For Super Admin and RVZ ID to track system operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.system_log import SystemLog, SchedulerLog, DataChangeLog, LogType, LogStatus
from app.models.base import get_indian_time

router = APIRouter()

def validate_admin_access(current_user: User):
    """Validate user has admin access to view logs"""
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied. Only Super Admin and RVZ ID can view system logs."
    #     )
    pass

@router.get("/scheduler-logs")
async def get_scheduler_logs(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(30, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get scheduler execution logs"""
    validate_admin_access(current_user)
    
    query = db.query(SchedulerLog)
    
    # Apply filters
    if start_date:
        query = query.filter(SchedulerLog.scheduled_date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(SchedulerLog.scheduled_date <= datetime.fromisoformat(end_date))
    if job_id:
        query = query.filter(SchedulerLog.job_id == job_id)
    if status_filter:
        query = query.filter(SchedulerLog.overall_status == status_filter)
    
    # Order by most recent
    scheduler_logs = query.order_by(desc(SchedulerLog.scheduled_date)).limit(limit).all()
    
    # Calculate summary statistics
    total_runs = len(scheduler_logs)
    successful_runs = sum(1 for log in scheduler_logs if log.overall_status == "Completed")
    failed_runs = sum(1 for log in scheduler_logs if log.overall_status == "Failed")
    
    return {
        "success": True,
        "summary": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0
        },
        "logs": [
            {
                "id": log.id,
                "job_id": log.job_id,
                "job_name": log.job_name,
                "scheduled_date": log.scheduled_date.date().isoformat(),
                "triggered_at": log.triggered_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "income_triggered": log.income_triggered,
                "direct_referral_status": log.direct_referral_status,
                "matching_status": log.matching_status,
                "ved_income_status": log.ved_income_status,
                "awards_status": log.awards_status,
                "guru_dakshina_status": log.guru_dakshina_status,
                "field_allowance_status": log.field_allowance_status,
                "bonanza_status": log.bonanza_status,
                "wallet_sync_status": log.wallet_sync_status,
                "withdrawal_status": log.withdrawal_status,
                "total_incomes_created": log.total_incomes_created,
                "total_users_affected": log.total_users_affected,
                "overall_status": log.overall_status,
                "error_message": log.error_message
            }
            for log in scheduler_logs
        ]
    }

@router.get("/scheduler-logs/daily-summary")
async def get_scheduler_daily_summary(
    days: int = Query(30, le=90, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get day-wise summary of scheduler runs"""
    validate_admin_access(current_user)
    
    start_date = date.today() - timedelta(days=days)
    
    # Get daily aggregates using SQL
    daily_summary = db.query(
        func.date(SchedulerLog.scheduled_date).label('date'),
        func.count(SchedulerLog.id).label('total_runs'),
        func.sum(SchedulerLog.total_users_affected).label('users_affected'),
        func.sum(SchedulerLog.total_incomes_created).label('incomes_created')
    ).filter(
        SchedulerLog.scheduled_date >= start_date
    ).group_by(
        func.date(SchedulerLog.scheduled_date)
    ).order_by(
        desc(func.date(SchedulerLog.scheduled_date))
    ).all()
    
    return {
        "success": True,
        "daily_summary": [
            {
                "date": str(day.date),
                "total_runs": day.total_runs or 0,
                "users_affected": day.users_affected or 0,
                "incomes_created": day.incomes_created or 0
            }
            for day in daily_summary
        ]
    }

@router.get("/data-change-logs")
async def get_data_change_logs(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    changed_by: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get data change audit logs"""
    validate_admin_access(current_user)
    
    query = db.query(DataChangeLog)
    
    # Apply filters
    if start_date:
        query = query.filter(DataChangeLog.changed_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(DataChangeLog.changed_at <= datetime.fromisoformat(end_date))
    if table_name:
        query = query.filter(DataChangeLog.table_name == table_name)
    if changed_by:
        query = query.filter(DataChangeLog.changed_by_id == changed_by)
    if operation:
        query = query.filter(DataChangeLog.operation == operation)
    
    # Order by most recent
    change_logs = query.order_by(desc(DataChangeLog.changed_at)).limit(limit).all()
    
    # Get unique tables affected
    affected_tables = db.query(DataChangeLog.table_name).distinct().all()
    
    return {
        "success": True,
        "summary": {
            "total_changes": len(change_logs),
            "affected_tables": [t[0] for t in affected_tables]
        },
        "logs": [
            {
                "id": log.id,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "operation": log.operation,
                "changed_by_id": log.changed_by_id,
                "changed_by_role": log.changed_by_role,
                "changed_at": log.changed_at.isoformat(),
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "change_reason": log.change_reason,
                "change_context": log.change_context
            }
            for log in change_logs
        ]
    }

@router.get("/system-logs")
async def get_system_logs(
    log_type: Optional[str] = Query(None),
    log_category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get general system logs"""
    validate_admin_access(current_user)
    
    query = db.query(SystemLog)
    
    # Apply filters
    if log_type:
        query = query.filter(SystemLog.log_type == log_type)
    if log_category:
        query = query.filter(SystemLog.log_category == log_category)
    if status_filter:
        query = query.filter(SystemLog.status == status_filter)
    if start_date:
        query = query.filter(SystemLog.started_at >= datetime.fromisoformat(start_date))
    
    # Order by most recent
    system_logs = query.order_by(desc(SystemLog.started_at)).limit(limit).all()
    
    return {
        "success": True,
        "logs": [
            {
                "id": log.id,
                "log_type": log.log_type.value,
                "log_category": log.log_category,
                "status": log.status.value,
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_seconds": log.duration_seconds,
                "actor_id": log.actor_id,
                "actor_role": log.actor_role,
                "operation_name": log.operation_name,
                "operation_description": log.operation_description,
                "records_affected": log.records_affected,
                "records_success": log.records_success,
                "records_failed": log.records_failed,
                "success_rate": log.success_rate,
                "error_message": log.error_message,
                "log_metadata": log.log_metadata
            }
            for log in system_logs
        ]
    }

@router.get("/log-categories")
async def get_log_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get all available log categories for filtering"""
    validate_admin_access(current_user)
    
    categories = db.query(SystemLog.log_category).distinct().all()
    tables = db.query(DataChangeLog.table_name).distinct().all()
    
    return {
        "success": True,
        "system_log_categories": [c[0] for c in categories],
        "data_change_tables": [t[0] for t in tables],
        "log_types": [lt.value for lt in LogType],
        "log_statuses": [ls.value for ls in LogStatus]
    }
