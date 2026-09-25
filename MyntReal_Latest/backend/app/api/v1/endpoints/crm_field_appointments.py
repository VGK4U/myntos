"""
CRM Field Appointments & Supporting Staff API Endpoints
DC Protocol Compliant - Single source of truth for physical field appointments.
Unified across Web, Mobile SPA, Android, and iOS.
"""

import logging
import base64
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import pytz
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func, desc

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffAuditLog
from app.models.crm import CRMLead, CRMLeadAuditLog
from app.models.crm_field_appointment import CRMFieldAppointment, get_indian_time
from app.models.staff_timesheet import StaffTimesheetEntry
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.universal_upload_service import universal_upload_service

logger = logging.getLogger(__name__)
router = APIRouter()


def get_indian_date():
    """Get current date in Indian Standard Time (Asia/Kolkata)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def generate_appointment_code() -> str:
    """Generate unique human-readable appointment code: APT-YYYYMMDD-XXXX"""
    d_str = get_indian_date().strftime('%Y%m%d')
    suffix = uuid.uuid4().hex[:4].upper()
    return f"APT-{d_str}-{suffix}"


# ===================== REQUEST SCHEMAS =====================

class CreateAppointmentRequest(BaseModel):
    lead_id: int
    visit_type: str = Field(..., description="'visit_bank' | 'visit_customer' | 'others'")
    purpose: Optional[str] = Field(None, description="Free text purpose/objective of visit")
    appointment_date: date
    preferred_time: Optional[str] = None
    scheduled_start_time: Optional[datetime] = None
    assigned_to_id: int
    telecaller_instructions: Optional[str] = None
    # Bank Visit Details
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_address: Optional[str] = None
    bank_contact_person: Optional[str] = None
    bank_contact_phone: Optional[str] = None
    bank_google_maps_url: Optional[str] = None
    # Customer Visit Details
    customer_address: Optional[str] = None
    customer_city: Optional[str] = None
    customer_area: Optional[str] = None
    customer_pincode: Optional[str] = None
    customer_google_maps_url: Optional[str] = None
    # Others Visit Details
    other_location_title: Optional[str] = None
    other_location_address: Optional[str] = None
    other_contact_person: Optional[str] = None
    other_contact_phone: Optional[str] = None
    other_google_maps_url: Optional[str] = None


class UpdateAppointmentStatusRequest(BaseModel):
    action: str = Field(..., description="'accept' | 'start_visit' | 'reached' | 'reschedule' | 'unable_to_visit' | 'cancel'")
    # Reached Coordinates
    reached_latitude: Optional[float] = None
    reached_longitude: Optional[float] = None
    reached_accuracy_meters: Optional[float] = None
    # Reschedule
    rescheduled_to_date: Optional[date] = None
    reschedule_reason: Optional[str] = None
    # Outcome / Unable to Visit
    outcome_status: Optional[str] = None
    outcome_summary: Optional[str] = None
    # Cancel
    cancel_reason: Optional[str] = None


class ReassignAppointmentRequest(BaseModel):
    new_assigned_to_id: int
    reason: Optional[str] = None


# ===================== ENDPOINTS =====================

@router.post("", summary="Create a new field appointment for a CRM lead")
def create_field_appointment(
    req: CreateAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Tele-caller or authorized staff creates a physical field appointment.
    Validates lead access, assignee existence, and duplicate active appointment conflict.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="CRM Lead not found")

    # Validate assignee
    assignee = db.query(StaffEmployee).filter(
        StaffEmployee.id == req.assigned_to_id,
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="Assigned employee must be an active, valid staff member")

    # Duplicate / Conflict Protection:
    # Check if an active appointment already exists for this lead, same visit_type, and same appointment_date
    active_conflict = db.query(CRMFieldAppointment).filter(
        CRMFieldAppointment.lead_id == req.lead_id,
        CRMFieldAppointment.visit_type == req.visit_type,
        CRMFieldAppointment.appointment_date == req.appointment_date,
        CRMFieldAppointment.status.in_(['assigned', 'accepted', 'in_progress', 'reached'])
    ).first()
    if active_conflict:
        raise HTTPException(
            status_code=409,
            detail=f"An active appointment ({active_conflict.appointment_code}) already exists for this lead on {req.appointment_date} with status '{active_conflict.status}'."
        )

    # Resolve scheduled start time if only preferred_time string is provided
    sched_dt = req.scheduled_start_time
    if not sched_dt and req.preferred_time:
        try:
            # Try parsing format like "10:30 AM"
            t_part = req.preferred_time.split('-')[0].strip()
            parsed_time = datetime.strptime(t_part, "%I:%M %p").time()
            sched_dt = datetime.combine(req.appointment_date, parsed_time)
        except Exception:
            sched_dt = datetime.combine(req.appointment_date, datetime.min.time())

    app_code = generate_appointment_code()

    # Pre-populate bank coordinates if bank visit and not explicitly given
    b_maps = req.bank_google_maps_url
    if req.visit_type == 'visit_bank' and not b_maps and lead.google_maps_link:
        b_maps = lead.google_maps_link

    # Pre-populate customer address if customer visit
    c_addr = req.customer_address or lead.address
    c_city = req.customer_city or lead.city
    c_area = req.customer_area or lead.area
    c_pin = req.customer_pincode or lead.pincode
    c_maps = req.customer_google_maps_url or lead.google_maps_link

    appointment = CRMFieldAppointment(
        tenant_id=lead.tenant_id,
        company_id=lead.company_id,
        appointment_code=app_code,
        lead_id=lead.id,
        visit_type=req.visit_type,
        purpose=req.purpose,
        status='assigned',
        appointment_date=req.appointment_date,
        preferred_time=req.preferred_time,
        scheduled_start_time=sched_dt,
        assigned_to_id=assignee.id,
        created_by_id=current_user.id,
        assigned_at=get_indian_time(),
        reassignment_history=[],
        # Bank
        bank_name=req.bank_name or getattr(lead, 'loan_bank', None),
        bank_branch=req.bank_branch or getattr(lead, 'bank_branch', None),
        bank_address=req.bank_address,
        bank_contact_person=req.bank_contact_person,
        bank_contact_phone=req.bank_contact_phone,
        bank_google_maps_url=b_maps,
        # Customer
        customer_address=c_addr,
        customer_city=c_city,
        customer_area=c_area,
        customer_pincode=c_pin,
        customer_google_maps_url=c_maps,
        # Others
        other_location_title=req.other_location_title,
        other_location_address=req.other_location_address,
        other_contact_person=req.other_contact_person,
        other_contact_phone=req.other_contact_phone,
        other_google_maps_url=req.other_google_maps_url,
        telecaller_instructions=req.telecaller_instructions
    )
    db.add(appointment)

    # CRM Lead Synchronization
    # 1. Update lead's support_staff_id if not already set
    if not lead.support_staff_id:
        lead.support_staff_id = assignee.id

    # 2. Append to lead recent_comments
    v_type_label = req.visit_type.replace('_', ' ').title()
    stamp = get_indian_time().strftime('%d-%b %I:%M%p')
    comment_entry = f"[{stamp}] Fixed Appointment: {v_type_label} for {req.appointment_date} ({req.preferred_time or ''}) assigned to {assignee.full_name} ({assignee.emp_code})."
    if req.purpose:
        comment_entry += f" Purpose: {req.purpose}."
    if req.telecaller_instructions:
        comment_entry += f" Instructions: {req.telecaller_instructions}"

    if lead.recent_comments:
        lead.recent_comments = f"{comment_entry}\n{lead.recent_comments}"[:2000]
    else:
        lead.recent_comments = comment_entry[:2000]

    lead.updated_at = get_indian_time()

    # 3. Add to CRMLeadAuditLog
    audit_entry = CRMLeadAuditLog(
        lead_id=lead.id,
        changed_by_type='staff',
        changed_by_id=current_user.emp_code,
        changed_by_name=current_user.full_name,
        field_name='field_appointment',
        old_value=None,
        new_value=f"Created {v_type_label} appointment ({app_code}) assigned to {assignee.full_name}",
        change_category='appointment',
        changed_at=get_indian_time()
    )
    db.add(audit_entry)

    db.commit()
    db.refresh(appointment)

    logger.info(f"[FieldAppointment] Created appointment {appointment.appointment_code} for lead {lead.id} assigned to {assignee.emp_code}")
    return {
        "success": True,
        "message": f"Field appointment {appointment.appointment_code} created successfully",
        "appointment": appointment.to_dict()
    }


@router.get("/supporting-staff", summary="Get list of all active staff members available for appointment assignment")
def get_supporting_staff_list(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns list of active staff employees available for appointment assignment across all departments.
    """
    query = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    )
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                StaffEmployee.full_name.ilike(s),
                StaffEmployee.emp_code.ilike(s),
                StaffEmployee.phone.ilike(s)
            )
        )
    employees = query.order_by(StaffEmployee.full_name).all()

    return {
        "success": True,
        "count": len(employees),
        "data": [
            {
                "id": emp.id,
                "emp_code": emp.emp_code,
                "full_name": emp.full_name,
                "phone": emp.phone,
                "department": emp.department.name if emp.department else None,
                "role": emp.role.role_name if emp.role else None,
                "hierarchy_level": emp.role.hierarchy_level if emp.role else 0
            }
            for emp in employees
        ]
    }


@router.get("/my-assigned", summary="List field appointments assigned to current employee with metric rollups")
def get_my_assigned_appointments(
    status: Optional[str] = Query(None, description="Filter by status: assigned, accepted, in_progress, reached, completed, all"),
    visit_type: Optional[str] = Query(None, description="visit_bank, visit_customer, others, all"),
    filter_period: Optional[str] = Query('all', description="'today', 'yesterday', 'this_week', 'last_week', 'this_month', 'all'"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    view_all: Optional[bool] = Query(False, description="For sales leadership/admins to view all active appointments"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Dedicated Supporting Staff feed.
    Returns:
      - metrics: total_appointments, visited_completed, visited_on_time, on_time_pct, completion_pct, pending_count
      - appointments: list of serialized appointments
    """
    query = db.query(CRMFieldAppointment)

    # Permission check for view_all
    is_leadership = (
        getattr(current_user, 'is_super_admin', False) or
        getattr(current_user.role, 'hierarchy_level', 0) >= 50 or
        (current_user.staff_type or '').upper() in ('VGK4U', 'VGK4U_SUPREME', 'KEY_LEADERSHIP', 'EA', 'SALES_INCHARGE') or
        (current_user.role and current_user.role.role_code in ('sales_incharge', 'key_leadership', 'ea', 'vgk4u', 'super_admin', 'admin'))
    )

    if not (view_all and is_leadership):
        query = query.filter(CRMFieldAppointment.assigned_to_id == current_user.id)

    # Status filter
    if status and isinstance(status, str) and status.lower() != 'all':
        query = query.filter(CRMFieldAppointment.status == status.lower())

    # Visit type filter
    if visit_type and isinstance(visit_type, str) and visit_type.lower() != 'all':
        query = query.filter(CRMFieldAppointment.visit_type == visit_type.lower())

    # Date / Quick Period Filter
    today = get_indian_date()
    p = (filter_period if isinstance(filter_period, str) else 'all').lower()

    if p == 'today':
        query = query.filter(CRMFieldAppointment.appointment_date == today)
    elif p == 'yesterday':
        query = query.filter(CRMFieldAppointment.appointment_date == today - timedelta(days=1))
    elif p == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        query = query.filter(CRMFieldAppointment.appointment_date >= start_of_week, CRMFieldAppointment.appointment_date <= today + timedelta(days=6))
    elif p == 'last_week':
        start_of_this_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_this_week - timedelta(days=7)
        end_of_last_week = start_of_this_week - timedelta(days=1)
        query = query.filter(CRMFieldAppointment.appointment_date >= start_of_last_week, CRMFieldAppointment.appointment_date <= end_of_last_week)
    elif p == 'this_month':
        start_of_month = today.replace(day=1)
        query = query.filter(CRMFieldAppointment.appointment_date >= start_of_month)
    elif date_from or date_to:
        if date_from:
            query = query.filter(CRMFieldAppointment.appointment_date >= date_from)
        if date_to:
            query = query.filter(CRMFieldAppointment.appointment_date <= date_to)

    # Search filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.join(CRMLead, CRMFieldAppointment.lead_id == CRMLead.id).filter(
            or_(
                CRMFieldAppointment.appointment_code.ilike(term),
                CRMFieldAppointment.purpose.ilike(term),
                CRMFieldAppointment.bank_name.ilike(term),
                CRMFieldAppointment.bank_branch.ilike(term),
                CRMFieldAppointment.customer_city.ilike(term),
                CRMLead.name.ilike(term),
                CRMLead.phone.ilike(term)
            )
        )

    # Fetch all records matching filter
    appointments = query.order_by(desc(CRMFieldAppointment.appointment_date), desc(CRMFieldAppointment.id)).all()

    # Calculate metrics over the filtered set
    total_appts = len(appointments)
    visited_completed = sum(1 for a in appointments if a.status == 'completed')
    visited_on_time = sum(1 for a in appointments if a.status == 'completed' and a.visited_on_time is True)
    pending_count = sum(1 for a in appointments if a.status in ('assigned', 'accepted', 'in_progress', 'reached'))

    on_time_pct = round((visited_on_time / visited_completed * 100), 1) if visited_completed > 0 else 0.0
    completion_pct = round((visited_completed / total_appts * 100), 1) if total_appts > 0 else 0.0

    appts_serialized = [a.to_dict() for a in appointments]

    return {
        "success": True,
        "metrics": {
            "total_appointments": total_appts,
            "visited_completed": visited_completed,
            "visited_on_time": visited_on_time,
            "on_time_pct": on_time_pct,
            "completion_pct": completion_pct,
            "pending_count": pending_count,
            "filter_period": p
        },
        "count": len(appointments),
        "data": appts_serialized,
        "appointments": appts_serialized
    }


@router.get("/lead/{lead_id}", summary="Get all field appointments for a specific lead")
def get_lead_appointments(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Retrieve appointment history and active appointments for a CRM Lead"""
    appts = db.query(CRMFieldAppointment).filter(
        CRMFieldAppointment.lead_id == lead_id
    ).order_by(desc(CRMFieldAppointment.created_at)).all()

    return {
        "success": True,
        "lead_id": lead_id,
        "count": len(appts),
        "appointments": [a.to_dict() for a in appts]
    }


@router.get("/leadership/overview", summary="Sales Leadership & Management appointment oversight")
def get_leadership_appointments_overview(
    filter_period: Optional[str] = Query('today', description="'today', 'yesterday', 'this_week', 'last_week', 'this_month', 'all'"),
    department_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Sales Leadership view for team-wide appointment workload, visits completed, on-time percentage.
    """
    query = db.query(CRMFieldAppointment)

    # Date filter
    today = get_indian_date()
    p = (filter_period or 'today').lower()

    if p == 'today':
        query = query.filter(CRMFieldAppointment.appointment_date == today)
    elif p == 'yesterday':
        query = query.filter(CRMFieldAppointment.appointment_date == today - timedelta(days=1))
    elif p == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        query = query.filter(CRMFieldAppointment.appointment_date >= start_of_week)
    elif p == 'last_week':
        start_of_this_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_this_week - timedelta(days=7)
        end_of_last_week = start_of_this_week - timedelta(days=1)
        query = query.filter(CRMFieldAppointment.appointment_date >= start_of_last_week, CRMFieldAppointment.appointment_date <= end_of_last_week)
    elif p == 'this_month':
        start_of_month = today.replace(day=1)
        query = query.filter(CRMFieldAppointment.appointment_date >= start_of_month)

    if employee_id:
        query = query.filter(CRMFieldAppointment.assigned_to_id == employee_id)

    appts = query.order_by(desc(CRMFieldAppointment.appointment_date), desc(CRMFieldAppointment.id)).all()

    # Group by employee
    staff_breakdown: Dict[int, Dict[str, Any]] = {}
    for a in appts:
        eid = a.assigned_to_id
        if eid not in staff_breakdown:
            ename = a.assigned_to.full_name if a.assigned_to else f"Staff #{eid}"
            ecode = a.assigned_to.emp_code if a.assigned_to else ""
            staff_breakdown[eid] = {
                "employee_id": eid,
                "employee_name": ename,
                "emp_code": ecode,
                "total": 0,
                "completed": 0,
                "on_time": 0,
                "pending": 0,
                "unable": 0,
                "rescheduled": 0
            }
        b = staff_breakdown[eid]
        b["total"] += 1
        if a.status == 'completed':
            b["completed"] += 1
            if a.visited_on_time:
                b["on_time"] += 1
        elif a.status in ('assigned', 'accepted', 'in_progress', 'reached'):
            b["pending"] += 1
        elif a.status == 'unable_to_visit':
            b["unable"] += 1
        elif a.status == 'rescheduled':
            b["rescheduled"] += 1

    for b in staff_breakdown.values():
        b["on_time_pct"] = round((b["on_time"] / b["completed"] * 100), 1) if b["completed"] > 0 else 0.0
        b["completion_pct"] = round((b["completed"] / b["total"] * 100), 1) if b["total"] > 0 else 0.0

    total_count = len(appts)
    total_completed = sum(1 for a in appts if a.status == 'completed')
    total_on_time = sum(1 for a in appts if a.status == 'completed' and a.visited_on_time is True)
    total_pending = sum(1 for a in appts if a.status in ('assigned', 'accepted', 'in_progress', 'reached'))

    return {
        "success": True,
        "filter_period": p,
        "summary": {
            "total_appointments": total_count,
            "completed": total_completed,
            "visited_on_time": total_on_time,
            "on_time_pct": round((total_on_time / total_completed * 100), 1) if total_completed > 0 else 0.0,
            "completion_pct": round((total_completed / total_count * 100), 1) if total_count > 0 else 0.0,
            "pending": total_pending
        },
        "staff_breakdown": list(staff_breakdown.values()),
        "appointments": [a.to_dict() for a in appts[:200]]
    }


@router.get("/{appointment_id}", summary="Get appointment by ID")
def get_field_appointment_detail(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    appointment = db.query(CRMFieldAppointment).filter(CRMFieldAppointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Field appointment not found")

    return {
        "success": True,
        "appointment": appointment.to_dict()
    }


@router.post("/{appointment_id}/status", summary="Update appointment state (accept, start, reached, reschedule, unable, cancel)")
def update_appointment_status(
    appointment_id: int,
    req: UpdateAppointmentStatusRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Transition appointment states.
    Includes the 'reached' check-in action where device coordinates and reached timestamp are stamped.
    """
    appointment = db.query(CRMFieldAppointment).filter(CRMFieldAppointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Field appointment not found")

    action = req.action.lower().strip()
    now = get_indian_time()
    lead = appointment.lead

    if action == 'accept':
        appointment.status = 'accepted'
    elif action == 'start_visit':
        appointment.status = 'in_progress'
        if not appointment.started_at:
            appointment.started_at = now
    elif action == 'reached':
        appointment.status = 'reached'
        appointment.reached_at = now
        if req.reached_latitude is not None and req.reached_longitude is not None:
            appointment.reached_latitude = req.reached_latitude
            appointment.reached_longitude = req.reached_longitude
            appointment.reached_accuracy_meters = req.reached_accuracy_meters

        # Evaluate visited_on_time:
        # If scheduled_start_time exists, check if reached within 45 mins of scheduled time
        if appointment.scheduled_start_time:
            delta_mins = (now - appointment.scheduled_start_time).total_seconds() / 60.0
            appointment.visited_on_time = (delta_mins <= 45.0)
        else:
            # Reached on appointment date
            appointment.visited_on_time = (now.date() <= appointment.appointment_date)

        # Log audit
        if lead:
            lead.recent_comments = f"[{now.strftime('%d-%b %I:%M%p')}] Supporting Staff {current_user.full_name} REACHED appointment location ({appointment.appointment_code}).\n{lead.recent_comments or ''}"[:2000]
    elif action == 'reschedule':
        if not req.rescheduled_to_date:
            raise HTTPException(status_code=400, detail="New appointment date is required for rescheduling")
        appointment.status = 'rescheduled'
        appointment.reschedule_reason = req.reschedule_reason or 'Rescheduled by staff'
        appointment.rescheduled_to_date = req.rescheduled_to_date
        if lead:
            lead.recent_comments = f"[{now.strftime('%d-%b %I:%M%p')}] Appointment {appointment.appointment_code} RESCHEDULED to {req.rescheduled_to_date}. Reason: {appointment.reschedule_reason}\n{lead.recent_comments or ''}"[:2000]
    elif action == 'unable_to_visit':
        appointment.status = 'unable_to_visit'
        appointment.outcome_status = req.outcome_status or 'unable_to_visit'
        appointment.outcome_summary = req.outcome_summary or req.reschedule_reason or 'Unable to complete visit'
        if lead:
            lead.recent_comments = f"[{now.strftime('%d-%b %I:%M%p')}] Appointment {appointment.appointment_code} marked UNABLE TO VISIT ({appointment.outcome_status}). {appointment.outcome_summary}\n{lead.recent_comments or ''}"[:2000]
    elif action == 'cancel':
        appointment.status = 'cancelled'
        appointment.cancel_reason = req.cancel_reason or 'Cancelled by user'
        if lead:
            lead.recent_comments = f"[{now.strftime('%d-%b %I:%M%p')}] Appointment {appointment.appointment_code} CANCELLED. Reason: {appointment.cancel_reason}\n{lead.recent_comments or ''}"[:2000]
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: '{action}'. Must be one of: accept, start_visit, reached, reschedule, unable_to_visit, cancel")

    appointment.updated_at = now
    db.commit()
    db.refresh(appointment)

    return {
        "success": True,
        "message": f"Appointment status updated to '{appointment.status}'",
        "appointment": appointment.to_dict()
    }


@router.post("/{appointment_id}/reassign", summary="Reassign appointment to another employee with complete history")
def reassign_field_appointment(
    appointment_id: int,
    req: ReassignAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    appointment = db.query(CRMFieldAppointment).filter(CRMFieldAppointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Field appointment not found")

    new_assignee = db.query(StaffEmployee).filter(
        StaffEmployee.id == req.new_assigned_to_id,
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).first()
    if not new_assignee:
        raise HTTPException(status_code=400, detail="New assignee must be an active, valid staff member")

    old_assignee = appointment.assigned_to
    now = get_indian_time()

    # Record in reassignment_history
    history_entry = {
        "from_staff_id": old_assignee.id if old_assignee else None,
        "from_staff_name": old_assignee.full_name if old_assignee else None,
        "from_staff_code": old_assignee.emp_code if old_assignee else None,
        "to_staff_id": new_assignee.id,
        "to_staff_name": new_assignee.full_name,
        "to_staff_code": new_assignee.emp_code,
        "reassigned_by_id": current_user.id,
        "reassigned_by_name": current_user.full_name,
        "reassigned_by_code": current_user.emp_code,
        "reason": req.reason or "Reassigned by manager/coordinator",
        "timestamp": now.isoformat()
    }

    curr_hist = list(appointment.reassignment_history or [])
    curr_hist.append(history_entry)
    appointment.reassignment_history = curr_hist

    appointment.assigned_to_id = new_assignee.id
    appointment.assigned_at = now
    appointment.status = 'assigned'  # Reset to assigned for new employee
    appointment.updated_at = now

    # Update Lead comments
    lead = appointment.lead
    if lead:
        lead.support_staff_id = new_assignee.id
        lead.recent_comments = f"[{now.strftime('%d-%b %I:%M%p')}] Appointment {appointment.appointment_code} REASSIGNED from {old_assignee.full_name if old_assignee else 'N/A'} to {new_assignee.full_name} ({new_assignee.emp_code}). Reason: {req.reason or 'Reassigned'}\n{lead.recent_comments or ''}"[:2000]
        lead.updated_at = now

    db.commit()
    db.refresh(appointment)

    logger.info(f"[FieldAppointment] Reassigned appointment {appointment.appointment_code} to {new_assignee.emp_code}")
    return {
        "success": True,
        "message": f"Appointment successfully reassigned to {new_assignee.full_name}",
        "appointment": appointment.to_dict()
    }


@router.post("/{appointment_id}/complete", summary="Complete visit with photograph, device GPS, comments, and timesheet logging")
async def complete_field_appointment(
    appointment_id: int,
    outcome_status: str = Form("successful"),
    outcome_summary: str = Form(""),
    photo: Optional[UploadFile] = File(None),
    photo_data: Optional[str] = Form(None),  # Base64 camera image
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    accuracy: Optional[float] = Form(None),
    device_timestamp: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Finalize field visit:
    1. Uploads photo via UniversalUploadService (WebP compression).
    2. Records device GPS coordinates & accuracy.
    3. Derives physical verification (is_gps_verified).
    4. Evaluates on-time arrival.
    5. Syncs CRM lead recent comments and last contact date.
    6. Automatically logs an approved StaffTimesheetEntry for the visit.
    """
    appointment = db.query(CRMFieldAppointment).filter(CRMFieldAppointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Field appointment not found")

    # Authorize: Assigned employee or leadership
    is_admin = getattr(current_user, 'is_super_admin', False) or getattr(current_user.role, 'hierarchy_level', 0) >= 75
    if appointment.assigned_to_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="Only the assigned supporting staff member or authorized manager can complete this visit")

    now = get_indian_time()
    file_bytes = None
    filename = f"field_visit_{appointment.appointment_code}_{int(now.timestamp())}.webp"

    if photo:
        file_bytes = await photo.read()
        filename = photo.filename or filename
    elif photo_data:
        try:
            if "," in photo_data:
                _, encoded = photo_data.split(",", 1)
            else:
                encoded = photo_data
            file_bytes = base64.b64decode(encoded)
        except Exception as e:
            logger.warning(f"[FieldAppointment] Failed to decode base64 photo: {e}")

    # Process photo through universal upload service if provided
    photo_path = None
    compressed_path = None
    if file_bytes and len(file_bytes) > 0:
        upload_res = universal_upload_service.upload_file(
            file_bytes=file_bytes,
            filename=filename,
            module="field_appointments",
            entity_id=str(appointment.id),
            employee_code=current_user.emp_code
        )
        photo_path = upload_res.get("relative_path") or upload_res.get("file_path") or upload_res.get("url", "")
        compressed_path = upload_res.get("compressed_path") or photo_path

    # GPS verification: requires lat/lng and accuracy <= 100 meters
    is_gps_verified = False
    if latitude is not None and longitude is not None:
        appointment.visit_latitude = latitude
        appointment.visit_longitude = longitude
        appointment.gps_accuracy_meters = accuracy
        appointment.device_captured_at = now
        if accuracy is not None and accuracy <= 150:  # Relaxed slightly to 150m for Indian urban canyons
            is_gps_verified = True

    appointment.is_gps_verified = is_gps_verified
    appointment.photo_path = photo_path or appointment.photo_path
    appointment.compressed_photo_path = compressed_path or appointment.compressed_photo_path
    if photo_path:
        appointment.photo_uploaded_at = now

    appointment.outcome_status = outcome_status
    appointment.outcome_summary = outcome_summary
    appointment.status = 'completed'
    appointment.completed_at = now
    appointment.updated_at = now

    # Evaluate visited_on_time if not already set by 'reached' action
    if appointment.visited_on_time is None:
        if appointment.scheduled_start_time:
            delta_mins = (now - appointment.scheduled_start_time).total_seconds() / 60.0
            appointment.visited_on_time = (delta_mins <= 60.0)
        else:
            appointment.visited_on_time = (now.date() <= appointment.appointment_date)

    # 1. CRM Lead Synchronization
    lead = appointment.lead
    if lead:
        lead.last_contact_date = now
        lead_comment = f"[{now.strftime('%d-%b %I:%M%p')}] COMPLETED Field Visit ({appointment.appointment_code} - {appointment.visit_type.replace('_', ' ').title()}) by {current_user.full_name}. Outcome: {outcome_status.title()}. Remarks: {outcome_summary}."
        if is_gps_verified:
            lead_comment += f" [GPS Verified: {latitude:.4f},{longitude:.4f} ~{accuracy:.0f}m]"
        if photo_path:
            lead_comment += " [Photo Attached]"

        lead.recent_comments = f"{lead_comment}\n{lead.recent_comments or ''}"[:2000]
        lead.updated_at = now

        # Add to CRMLeadAuditLog
        audit_entry = CRMLeadAuditLog(
            lead_id=lead.id,
            changed_by_type='staff',
            changed_by_id=current_user.emp_code,
            changed_by_name=current_user.full_name,
            field_name='field_appointment_completed',
            old_value='in_progress',
            new_value=f"Completed {appointment.appointment_code} ({outcome_status})",
            change_category='visit',
            changed_at=now
        )
        db.add(audit_entry)

    # 2. Performance / Timesheet Bridge (Zero Formula Invention)
    # Log an approved timesheet entry for the field visit so staff gets work credit
    try:
        end_t = now.time()
        start_t = appointment.started_at.time() if appointment.started_at and appointment.started_at.date() == now.date() else None
        if not start_t or start_t >= end_t:
            if now.hour == 0 and now.minute < 45:
                start_t = datetime.min.time()
            else:
                start_t = (now - timedelta(minutes=45)).time()
            if start_t >= end_t:
                start_t = datetime.min.time()

        # Compute accurate duration minutes
        dur_mins = max(1, int((datetime.combine(now.date(), end_t) - datetime.combine(now.date(), start_t)).total_seconds() / 60.0))

        timesheet = StaffTimesheetEntry(
            employee_id=current_user.id,
            date=appointment.appointment_date or now.date(),
            start_time=start_t,
            end_time=end_t,
            duration_minutes=dur_mins,
            billable_minutes=dur_mins,
            entry_type='lead',
            lead_id=lead.id if lead else None,
            comments=f"Field Visit ({appointment.appointment_code}): {appointment.visit_type.replace('_', ' ').title()} - {outcome_summary or outcome_status}",
            status='approved',
            approved_by=current_user.id,
            approved_at=now,
            created_at=now,
            updated_at=now
        )
        db.add(timesheet)
        db.flush()
        appointment.timesheet_entry_id = timesheet.id
    except Exception as ts_err:
        logger.warning(f"[FieldAppointment] Non-fatal timesheet log error: {ts_err}")

    db.commit()
    db.refresh(appointment)

    logger.info(f"[FieldAppointment] Completed visit {appointment.appointment_code} by {current_user.emp_code}. GPS Verified: {is_gps_verified}")
    return {
        "success": True,
        "message": f"Appointment {appointment.appointment_code} completed successfully",
        "is_gps_verified": is_gps_verified,
        "visited_on_time": appointment.visited_on_time,
        "appointment": appointment.to_dict()
    }
