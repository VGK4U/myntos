from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional, List
from datetime import datetime, date
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead
from app.models.staff_kra import StaffKRADailyInstance
from app.models.staff_attendance import StaffActivityTimeLog
from app.models.staff_bonus_config import StaffQuarterlyBonusConfig
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter()
logger = logging.getLogger(__name__)

def _is_admin_or_manager(emp: StaffEmployee) -> bool:
    rc = (emp.role.role_code or '').lower() if emp.role else ''
    rn = (emp.role.role_name or '').lower() if emp.role else ''
    st = (getattr(emp, 'staff_type', '') or '').lower()
    dept = (emp.department.name or '').lower() if emp.department else ''
    ec = (emp.emp_code or '')
    return (
        ec in ('MR10001', 'MR10025') or
        rc in ('vgk4u', 'vgk4u_supreme', 'accounts', 'finance', 'key_leadership', 'executive_admin', 'manager', 'admin') or
        any(x in rn for x in ('ea', 'executive assistant', 'vgk4u supreme', 'accounts', 'finance', 'key leadership', 'executive admin', 'manager', 'admin')) or
        any(x in st for x in ('ea', 'vgk4u', 'vgk4u_supreme', 'accounts', 'finance', 'executive_admin')) or
        'accounts' in dept or 'finance' in dept or 'procurement' in dept
    )

@router.get("/performance/quarterly-bonus", summary="Get Quarterly Bonus stats and calculations")
def get_quarterly_bonus_report(
    employee_id: Optional[int] = Query(None),
    period_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    # 1. Access Check: employees can view their own, admins/managers can view any
    target_emp_id = employee_id if employee_id else current_user.id
    if target_emp_id != current_user.id and not _is_admin_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Only managers/admins can view other employees.")

    # 2. Get Employee
    emp = db.query(StaffEmployee).filter(StaffEmployee.id == target_emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # 3. Get Active / Selected configuration period
    if period_id:
        cfg = db.query(StaffQuarterlyBonusConfig).filter(StaffQuarterlyBonusConfig.id == period_id).first()
    else:
        # Default to current period based on today's date if possible
        today = date.today()
        cfg = db.query(StaffQuarterlyBonusConfig).filter(
            StaffQuarterlyBonusConfig.is_active == True,
            StaffQuarterlyBonusConfig.start_date <= today,
            StaffQuarterlyBonusConfig.end_date >= today
        ).first()
        if not cfg:
            cfg = db.query(StaffQuarterlyBonusConfig).filter(StaffQuarterlyBonusConfig.is_active == True).order_by(StaffQuarterlyBonusConfig.start_date.desc()).first()

    if not cfg:
        return {
            "success": True,
            "eligible": False,
            "message": "No active quarterly bonus configuration found.",
            "periods": [],
            "stats": None
        }

    # Get list of all periods for filter select
    periods = db.query(StaffQuarterlyBonusConfig).order_by(StaffQuarterlyBonusConfig.start_date.desc()).all()
    periods_list = [{
        "id": p.id,
        "period_name": p.period_name,
        "start_date": p.start_date.isoformat(),
        "end_date": p.end_date.isoformat(),
        "is_active": p.is_active
    } for p in periods]

    # If employee is not eligible, we still return the configuration details but set payout to 0
    is_eligible = getattr(emp, "is_quarterly_bonus_eligible", False)

    # 4. Calculate Completed Solar Files (Field Staff assigned and completed in period)
    completed_leads = db.query(CRMLead).filter(
        CRMLead.field_staff_id == target_emp_id,
        CRMLead.solar_pipeline_status == 'completed',
        CRMLead.actual_close_date >= datetime.combine(cfg.start_date, datetime.min.time()),
        CRMLead.actual_close_date <= datetime.combine(cfg.end_date, datetime.max.time())
    ).all()
    completed_count = len(completed_leads)

    # 5. Calculate KRA performance score during period
    # approved = count where manager_review_status IN ('approved', 'edited_by_manager')
    # total = count where completion_status NOT IN ('na', 'skipped')
    kra_total = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.employee_id == target_emp_id,
        StaffKRADailyInstance.instance_date >= cfg.start_date,
        StaffKRADailyInstance.instance_date <= cfg.end_date,
        StaffKRADailyInstance.completion_status.notin_(('na', 'skipped'))
    ).count()

    kra_approved = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.employee_id == target_emp_id,
        StaffKRADailyInstance.instance_date >= cfg.start_date,
        StaffKRADailyInstance.instance_date <= cfg.end_date,
        StaffKRADailyInstance.manager_review_status.in_(('approved', 'edited_by_manager')),
        StaffKRADailyInstance.completion_status.notin_(('na', 'skipped'))
    ).count()

    kra_score = (kra_approved / kra_total * 100.0) if kra_total > 0 else 100.0

    # 6. Calculate Activity completion percentage
    act_sum = db.query(
        func.sum(StaffActivityTimeLog.completed_minutes).label("completed"),
        func.sum(StaffActivityTimeLog.required_minutes).label("required")
    ).filter(
        StaffActivityTimeLog.employee_id == target_emp_id,
        StaffActivityTimeLog.date >= cfg.start_date,
        StaffActivityTimeLog.date <= cfg.end_date
    ).first()

    act_completed = act_sum[0] if act_sum and act_sum[0] else 0
    act_required = act_sum[1] if act_sum and act_sum[1] else 0
    activity_score = (act_completed / act_required * 100.0) if act_required > 0 else 100.0

    # 7. Combined Performance Average
    combined_score = (kra_score + activity_score) / 2.0

    # 8. Check Target & Apply Multiplier
    target_met = (completed_count >= cfg.min_target_files)
    
    multiplier = 0.0
    payout = 0.0
    if is_eligible and target_met:
        threshold = float(cfg.kra_activity_threshold_pct)
        if combined_score >= threshold:
            multiplier = float(cfg.high_performance_multiplier)
        else:
            multiplier = float(cfg.low_performance_multiplier)
        payout = completed_count * float(cfg.base_bonus_per_file) * multiplier

    leads_breakdown = [{
        "id": lead.id,
        "name": lead.name,
        "phone": lead.phone,
        "deal_value": lead.deal_value_total or 0,
        "completed_at": lead.actual_close_date.isoformat() if lead.actual_close_date else None
    } for lead in completed_leads]

    return {
        "success": True,
        "eligible": is_eligible,
        "employee": {
            "id": emp.id,
            "full_name": emp.full_name,
            "emp_code": emp.emp_code
        },
        "period": {
            "id": cfg.id,
            "period_name": cfg.period_name,
            "start_date": cfg.start_date.isoformat(),
            "end_date": cfg.end_date.isoformat(),
            "min_target_files": cfg.min_target_files,
            "base_bonus_per_file": float(cfg.base_bonus_per_file),
            "high_multiplier": float(cfg.high_performance_multiplier),
            "low_multiplier": float(cfg.low_performance_multiplier),
            "kra_activity_threshold": float(cfg.kra_activity_threshold_pct)
        },
        "periods": periods_list,
        "stats": {
            "completed_files": completed_count,
            "target_files": cfg.min_target_files,
            "target_met": target_met,
            "kra_score": round(kra_score, 2),
            "activity_score": round(activity_score, 2),
            "combined_score": round(combined_score, 2),
            "multiplier": multiplier,
            "estimated_payout": round(payout, 2),
            "leads": leads_breakdown
        }
    }

@router.get("/performance/quarterly-bonus/config", summary="Get Quarterly Bonus Configurations")
def get_quarterly_bonus_configs(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    if not _is_admin_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Admins/Managers only.")
    
    configs = db.query(StaffQuarterlyBonusConfig).order_by(StaffQuarterlyBonusConfig.start_date.desc()).all()
    return {
        "success": True,
        "configs": [{
            "id": c.id,
            "period_name": c.period_name,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
            "min_target_files": c.min_target_files,
            "base_bonus_per_file": float(c.base_bonus_per_file),
            "high_performance_multiplier": float(c.high_performance_multiplier),
            "low_performance_multiplier": float(c.low_performance_multiplier),
            "kra_activity_threshold_pct": float(c.kra_activity_threshold_pct),
            "is_active": c.is_active
        } for c in configs]
    }

@router.post("/performance/quarterly-bonus/config", summary="Add or Update Quarterly Bonus Configuration")
def save_quarterly_bonus_config(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    if not _is_admin_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Admins/Managers only.")

    period_id = payload.get("id")
    period_name = payload.get("period_name")
    start_date_str = payload.get("start_date")
    end_date_str = payload.get("end_date")
    min_target_files = payload.get("min_target_files", 50)
    base_bonus_per_file = payload.get("base_bonus_per_file", 150.00)
    high_mult = payload.get("high_performance_multiplier", 1.20)
    low_mult = payload.get("low_performance_multiplier", 0.50)
    threshold = payload.get("kra_activity_threshold_pct", 80.00)
    is_active = payload.get("is_active", True)

    if not period_name or not start_date_str or not end_date_str:
        raise HTTPException(status_code=400, detail="period_name, start_date, and end_date are required.")

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if is_active:
        # Deactivate all other active configs
        db.query(StaffQuarterlyBonusConfig).filter(StaffQuarterlyBonusConfig.is_active == True).update({"is_active": False})

    if period_id:
        cfg = db.query(StaffQuarterlyBonusConfig).filter(StaffQuarterlyBonusConfig.id == period_id).first()
        if not cfg:
            raise HTTPException(status_code=404, detail="Configuration period not found.")
        cfg.period_name = period_name
        cfg.start_date = start_date
        cfg.end_date = end_date
        cfg.min_target_files = min_target_files
        cfg.base_bonus_per_file = base_bonus_per_file
        cfg.high_performance_multiplier = high_mult
        cfg.low_performance_multiplier = low_mult
        cfg.kra_activity_threshold_pct = threshold
        cfg.is_active = is_active
    else:
        # Check uniqueness of period_name
        existing = db.query(StaffQuarterlyBonusConfig).filter(StaffQuarterlyBonusConfig.period_name == period_name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Period '{period_name}' already exists.")
        
        cfg = StaffQuarterlyBonusConfig(
            period_name=period_name,
            start_date=start_date,
            end_date=end_date,
            min_target_files=min_target_files,
            base_bonus_per_file=base_bonus_per_file,
            high_performance_multiplier=high_mult,
            low_performance_multiplier=low_mult,
            kra_activity_threshold_pct=threshold,
            is_active=is_active
        )
        db.add(cfg)

    db.commit()
    db.refresh(cfg)
    return {
        "success": True,
        "message": "Quarterly bonus configuration saved successfully",
        "config": {
            "id": cfg.id,
            "period_name": cfg.period_name,
            "start_date": cfg.start_date.isoformat(),
            "end_date": cfg.end_date.isoformat(),
            "is_active": cfg.is_active
        }
    }
