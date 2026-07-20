"""
Staff Employee Offboarding / Data Transfer API
DC Protocol: Segment-wise data transfer when employees are deactivated/resigned
Provides summary of all linked data and transfer capabilities with full audit trail
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime
from typing import Optional, List
import pytz

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffAuditLog, log_staff_audit
from app.models.staff_tasks import StaffTask, StaffTaskAssignee, StaffTaskPhase, StaffDayPlanItem, StaffDayPlan
from app.models.staff_kra import StaffKRAAssignment, StaffKRADailyInstance
from app.models.crm import CRMLead
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter(prefix="/staff/offboarding", tags=["Staff Offboarding"])

IST = pytz.timezone("Asia/Kolkata")

def get_indian_time():
    return datetime.now(IST)

OFFBOARDING_ACCESS_ROLES = ['hr', 'ea', 'vgk4u', 'ceo', 'md']


def _check_offboarding_access(current_user: StaffEmployee):
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    hierarchy = current_user.role.hierarchy_level if current_user.role else 0
    if role_code not in OFFBOARDING_ACCESS_ROLES and hierarchy < 150:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR/EA/VGK4U can access offboarding"
        )


def _get_employee_or_404(db: Session, employee_id: int) -> StaffEmployee:
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _resolve_actor_id(current_user: StaffEmployee) -> str:
    return current_user.emp_code if current_user.emp_code else str(current_user.id)


@router.get("/employees", summary="List employees eligible for offboarding")
async def list_offboarding_employees(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    _check_offboarding_access(current_user)

    employees = db.query(StaffEmployee).filter(
        StaffEmployee.status.in_(['deactivated', 'resigned'])
    ).order_by(StaffEmployee.updated_at.desc()).all()

    result = []
    for emp in employees:
        task_count = db.query(func.count(StaffTask.id)).filter(
            StaffTask.primary_assignee_id == emp.id,
            StaffTask.status.notin_(['completed', 'cancelled', 'deleted'])
        ).scalar() or 0

        kra_count = db.query(func.count(StaffKRAAssignment.id)).filter(
            StaffKRAAssignment.employee_id == emp.id,
            StaffKRAAssignment.status == 'active'
        ).scalar() or 0

        lead_count = db.query(func.count(CRMLead.id)).filter(
            or_(
                CRMLead.field_staff_id == emp.id,
                CRMLead.telecaller_id == emp.id,
                CRMLead.depends_on_staff_id == emp.id
            ),
            CRMLead.status.notin_(['closed', 'lost', 'converted'])
        ).scalar() or 0

        total = task_count + kra_count + lead_count

        result.append({
            "id": emp.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "status": emp.status,
            "department": emp.department.name if emp.department else None,
            "role": emp.role.role_name if emp.role else None,
            "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
            "pending_items": total,
            "segments": {
                "tasks": task_count,
                "kra": kra_count,
                "leads": lead_count
            }
        })

    return {
        "success": True,
        "employees": result,
        "total": len(result)
    }


@router.get("/{employee_id}/summary", summary="Get offboarding data summary for employee")
async def get_offboarding_summary(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    import logging
    logger = logging.getLogger(__name__)

    _check_offboarding_access(current_user)
    employee = _get_employee_or_404(db, employee_id)
    logger.info(f"[DC-OFFBOARD] Loading summary for employee {employee_id} ({employee.emp_code})")

    tasks = db.query(StaffTask).filter(
        StaffTask.primary_assignee_id == employee_id,
        StaffTask.status.notin_(['completed', 'cancelled', 'deleted'])
    ).all()

    secondary_tasks = db.query(StaffTaskAssignee).filter(
        StaffTaskAssignee.employee_id == employee_id
    ).all()
    secondary_task_ids = [sa.task_id for sa in secondary_tasks]
    secondary_task_records = []
    if secondary_task_ids:
        secondary_task_records = db.query(StaffTask).filter(
            StaffTask.id.in_(secondary_task_ids),
            StaffTask.status.notin_(['completed', 'cancelled', 'deleted'])
        ).all()

    phase_assignments = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.phase_assignee_id == employee_id,
        StaffTaskPhase.phase_status.notin_(['completed', 'cancelled']),
        StaffTaskPhase.is_deleted == False
    ).all()

    kra_assignments = db.query(StaffKRAAssignment).filter(
        StaffKRAAssignment.employee_id == employee_id,
        StaffKRAAssignment.status == 'active'
    ).all()

    future_instances_count = 0
    if kra_assignments:
        assignment_ids = [a.id for a in kra_assignments]
        future_instances_count = db.query(func.count(StaffKRADailyInstance.id)).filter(
            StaffKRADailyInstance.kra_assignment_id.in_(assignment_ids),
            StaffKRADailyInstance.instance_date > datetime.now(IST).date(),
            StaffKRADailyInstance.completion_status == 'pending'
        ).scalar() or 0

    leads_as_field = db.query(CRMLead).filter(
        CRMLead.field_staff_id == employee_id,
        CRMLead.status.notin_(['closed', 'lost', 'converted'])
    ).all()

    leads_as_telecaller = db.query(CRMLead).filter(
        CRMLead.telecaller_id == employee_id,
        CRMLead.status.notin_(['closed', 'lost', 'converted'])
    ).all()

    leads_as_depends = db.query(CRMLead).filter(
        CRMLead.depends_on_staff_id == employee_id,
        CRMLead.status.notin_(['closed', 'lost', 'converted'])
    ).all()

    all_task_ids = list(set(
        [t.id for t in tasks] +
        [t.id for t in secondary_task_records] +
        [p.parent_task_id for p in phase_assignments]
    ))
    all_phase_ids = [p.id for p in phase_assignments]

    task_plan_counts = {}
    phase_plan_counts = {}
    if all_task_ids:
        task_counts_q = db.query(
            StaffDayPlanItem.task_id,
            func.count(func.distinct(StaffDayPlan.plan_date))
        ).join(
            StaffDayPlan, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
        ).filter(
            StaffDayPlanItem.task_id.in_(all_task_ids),
            StaffDayPlanItem.item_type == 'task',
            StaffDayPlanItem.phase_id.is_(None)
        ).group_by(StaffDayPlanItem.task_id).all()
        task_plan_counts = {tid: cnt for tid, cnt in task_counts_q}

    if all_phase_ids:
        phase_counts_q = db.query(
            StaffDayPlanItem.phase_id,
            func.count(func.distinct(StaffDayPlan.plan_date))
        ).join(
            StaffDayPlan, StaffDayPlanItem.day_plan_id == StaffDayPlan.id
        ).filter(
            StaffDayPlanItem.phase_id.in_(all_phase_ids),
            StaffDayPlanItem.item_type == 'phase'
        ).group_by(StaffDayPlanItem.phase_id).all()
        phase_plan_counts = {pid: cnt for pid, cnt in phase_counts_q}

    today = datetime.now(IST).date()

    def task_to_dict(t):
        created = t.created_at
        days_pending = (today - created.date()).days if created else None
        return {
            "id": t.id,
            "task_code": t.task_code,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "category": t.category,
            "created_at": created.isoformat() if created else None,
            "days_pending": days_pending,
            "times_planned": task_plan_counts.get(t.id, 0)
        }

    def lead_to_dict(l):
        return {
            "id": l.id,
            "name": l.name,
            "phone": l.phone,
            "status": l.status,
            "priority": l.priority,
            "city": l.city,
            "company_id": l.company_id,
            "deal_value_total": float(l.deal_value_total) if l.deal_value_total else 0
        }

    def kra_to_dict(a):
        try:
            template = a.template
            template_name = template.name if template else f"Template #{a.kra_template_id}"
        except Exception:
            template_name = f"Template #{a.kra_template_id}"
        return {
            "id": a.id,
            "template_id": a.kra_template_id,
            "template_name": template_name,
            "effective_from": a.effective_from.isoformat() if a.effective_from else None,
            "effective_until": a.effective_until.isoformat() if a.effective_until else None,
            "status": a.status
        }

    summary = {
        "employee": {
            "id": employee.id,
            "emp_code": employee.emp_code,
            "full_name": employee.full_name,
            "status": employee.status,
            "department": employee.department.name if employee.department else None,
            "role": employee.role.role_name if employee.role else None
        },
        "segments": {
            "tasks_primary": {
                "label": "Tasks (Primary Assignee)",
                "count": len(tasks),
                "items": [task_to_dict(t) for t in tasks],
                "transferable": True
            },
            "tasks_secondary": {
                "label": "Tasks (Secondary Assignee)",
                "count": len(secondary_task_records),
                "items": [task_to_dict(t) for t in secondary_task_records],
                "transferable": True
            },
            "task_phases": {
                "label": "Task Phase Assignments",
                "count": len(phase_assignments),
                "items": [{
                    "id": p.id,
                    "task_id": p.parent_task_id,
                    "phase_name": p.phase_title,
                    "status": p.phase_status,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "days_pending": (today - p.created_at.date()).days if p.created_at else None,
                    "times_planned": phase_plan_counts.get(p.id, 0)
                } for p in phase_assignments],
                "transferable": True
            },
            "kra_assignments": {
                "label": "KRA Assignments",
                "count": len(kra_assignments),
                "future_instances": future_instances_count,
                "items": [kra_to_dict(a) for a in kra_assignments],
                "transferable": True
            },
            "leads_field_staff": {
                "label": "CRM Leads (Field Staff)",
                "count": len(leads_as_field),
                "items": [lead_to_dict(l) for l in leads_as_field],
                "transferable": True
            },
            "leads_telecaller": {
                "label": "CRM Leads (Telecaller)",
                "count": len(leads_as_telecaller),
                "items": [lead_to_dict(l) for l in leads_as_telecaller],
                "transferable": True
            },
            "leads_depends": {
                "label": "CRM Leads (Depends On)",
                "count": len(leads_as_depends),
                "items": [lead_to_dict(l) for l in leads_as_depends],
                "transferable": True
            }
        },
        "total_pending": (
            len(tasks) + len(secondary_task_records) + len(phase_assignments) +
            len(kra_assignments) + len(leads_as_field) + len(leads_as_telecaller) + len(leads_as_depends)
        )
    }

    return {"success": True, "summary": summary}


@router.post("/{employee_id}/transfer", summary="Transfer segment data to another employee")
async def transfer_offboarding_data(
    employee_id: int,
    request: Request,
    transfer_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    _check_offboarding_access(current_user)
    source_employee = _get_employee_or_404(db, employee_id)

    target_emp_code = transfer_data.get("target_employee_code")
    segments = transfer_data.get("segments", [])
    reason = transfer_data.get("reason", "Employee offboarding transfer")

    if not target_emp_code:
        raise HTTPException(status_code=400, detail="target_employee_code is required")
    if not segments:
        raise HTTPException(status_code=400, detail="At least one segment must be selected")

    target_employee = db.query(StaffEmployee).filter(
        StaffEmployee.emp_code == target_emp_code,
        StaffEmployee.status == 'active'
    ).first()

    if not target_employee:
        raise HTTPException(status_code=404, detail=f"Target employee {target_emp_code} not found or not active")

    if target_employee.id == employee_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same employee")

    results = {}
    total_transferred = 0
    actor_id = _resolve_actor_id(current_user)

    try:
        for segment in segments:
            count = 0

            if segment == "tasks_primary":
                tasks = db.query(StaffTask).filter(
                    StaffTask.primary_assignee_id == employee_id,
                    StaffTask.status.notin_(['completed', 'cancelled', 'deleted'])
                ).all()
                for task in tasks:
                    task.primary_assignee_id = target_employee.id
                    count += 1
                results["tasks_primary"] = {"transferred": count, "target": target_employee.full_name}

            elif segment == "tasks_secondary":
                assignees = db.query(StaffTaskAssignee).filter(
                    StaffTaskAssignee.employee_id == employee_id
                ).all()
                for assignee in assignees:
                    task_active = db.query(StaffTask).filter(
                        StaffTask.id == assignee.task_id,
                        StaffTask.status.notin_(['completed', 'cancelled', 'deleted'])
                    ).first()
                    if task_active:
                        existing = db.query(StaffTaskAssignee).filter(
                            StaffTaskAssignee.task_id == assignee.task_id,
                            StaffTaskAssignee.employee_id == target_employee.id
                        ).first()
                        if not existing:
                            assignee.employee_id = target_employee.id
                            count += 1
                        else:
                            db.delete(assignee)
                results["tasks_secondary"] = {"transferred": count, "target": target_employee.full_name}

            elif segment == "task_phases":
                phases = db.query(StaffTaskPhase).filter(
                    StaffTaskPhase.phase_assignee_id == employee_id,
                    StaffTaskPhase.phase_status.notin_(['completed', 'cancelled']),
                    StaffTaskPhase.is_deleted == False
                ).all()
                for phase in phases:
                    phase.phase_assignee_id = target_employee.id
                    count += 1
                results["task_phases"] = {"transferred": count, "target": target_employee.full_name}

            elif segment == "kra_assignments":
                assignments = db.query(StaffKRAAssignment).filter(
                    StaffKRAAssignment.employee_id == employee_id,
                    StaffKRAAssignment.status == 'active'
                ).all()
                for assignment in assignments:
                    assignment.status = 'inactive'
                    db.query(StaffKRADailyInstance).filter(
                        StaffKRADailyInstance.kra_assignment_id == assignment.id,
                        StaffKRADailyInstance.instance_date > datetime.now(IST).date(),
                        StaffKRADailyInstance.completion_status == 'pending'
                    ).delete(synchronize_session=False)
                    count += 1
                results["kra_assignments"] = {"deactivated": count, "note": "KRA assignments deactivated and future instances removed"}

            elif segment == "leads_field_staff":
                leads = db.query(CRMLead).filter(
                    CRMLead.field_staff_id == employee_id,
                    CRMLead.status.notin_(['closed', 'lost', 'converted'])
                ).all()
                for lead in leads:
                    lead.field_staff_id = target_employee.id
                    count += 1
                results["leads_field_staff"] = {"transferred": count, "target": target_employee.full_name}

            elif segment == "leads_telecaller":
                leads = db.query(CRMLead).filter(
                    CRMLead.telecaller_id == employee_id,
                    CRMLead.status.notin_(['closed', 'lost', 'converted'])
                ).all()
                for lead in leads:
                    lead.telecaller_id = target_employee.id
                    count += 1
                results["leads_telecaller"] = {"transferred": count, "target": target_employee.full_name}

            elif segment == "leads_depends":
                leads = db.query(CRMLead).filter(
                    CRMLead.depends_on_staff_id == employee_id,
                    CRMLead.status.notin_(['closed', 'lost', 'converted'])
                ).all()
                for lead in leads:
                    lead.depends_on_staff_id = target_employee.id
                    count += 1
                results["leads_depends"] = {"transferred": count, "target": target_employee.full_name}

            total_transferred += count

        log_staff_audit(
            db=db,
            employee_id=current_user.id,
            action='offboarding_transfer',
            resource_type='staff_employees',
            resource_id=employee_id,
            new_data={
                "source_employee": source_employee.emp_code,
                "source_name": source_employee.full_name,
                "target_employee": target_employee.emp_code,
                "target_name": target_employee.full_name,
                "segments": segments,
                "results": results,
                "reason": reason,
                "transferred_by": actor_id
            },
            ip_address=request.client.host if request.client else "unknown"
        )

        db.commit()

        return {
            "success": True,
            "message": f"Successfully processed {total_transferred} items across {len(segments)} segments",
            "results": results,
            "source": {"emp_code": source_employee.emp_code, "name": source_employee.full_name},
            "target": {"emp_code": target_employee.emp_code, "name": target_employee.full_name}
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")


@router.post("/{employee_id}/transfer-bulk", summary="Bulk transfer all segments to one employee")
async def bulk_transfer_offboarding_data(
    employee_id: int,
    request: Request,
    transfer_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    _check_offboarding_access(current_user)

    all_segments = [
        "tasks_primary", "tasks_secondary", "task_phases",
        "kra_assignments",
        "leads_field_staff", "leads_telecaller", "leads_depends"
    ]
    transfer_data["segments"] = all_segments

    return await transfer_offboarding_data(employee_id, request, transfer_data, db, current_user)


@router.get("/transfer-history", summary="Get transfer audit history")
async def get_transfer_history(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    _check_offboarding_access(current_user)

    query = db.query(StaffAuditLog).filter(
        StaffAuditLog.action == 'offboarding_transfer'
    )

    if employee_id:
        query = query.filter(StaffAuditLog.resource_id == employee_id)

    history = query.order_by(StaffAuditLog.timestamp.desc()).limit(100).all()

    return {
        "success": True,
        "history": [
            {
                "id": h.id,
                "action": h.action,
                "details": h.new_data,
                "performed_by": h.employee_id,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                "ip_address": h.ip_address
            }
            for h in history
        ],
        "total": len(history)
    }
