"""
Staff KRA Performance Management API Endpoints (DC Protocol Compliant)
Complete KRA tracking with templates, assignments, daily instances, and performance analytics

Key Features:
- KRA Template CRUD with approval workflow (Key Leadership creates, VGK4U approves)
- KRA Assignment with SPOC and Manager tracking
- Daily KRA instance management with completion status and time tracking
- Performance analytics with dynamic date filters (daily/weekly/monthly)

Role Hierarchy:
- VGK4U Supreme (150): Full access, approve/reject templates, view all KRAs
- Key Leadership (100): Create templates (needs approval), view team KRAs
- HR (85): View all employees' KRAs
- Leadership/Manager (90/60): View own + direct reports' KRAs
- All Staff: View and update own KRAs

Created: Nov 27, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, case, desc
from typing import Optional, List
from datetime import datetime, date, timedelta
import re
import pytz

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffRole
from app.models.staff_kra import (
    StaffKRATemplate, StaffKRAAssignment, StaffKRADailyInstance,
    StaffKRAPerformanceSummary, StaffKRAAuditLog, StaffConfigurableStatus
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.schemas.staff_kra import (
    KRATemplateCreate, KRATemplateUpdate, KRATemplateApprove, KRATemplateReject,
    KRATemplateResponse, KRATemplateListResponse, KRAAssignmentCreate, KRAAssignmentResponse,
    ApprovalStatus, RecordStatus, FrequencyType,
    ManagerApproveKRARequest, ManagerEditKRARequest, ManagerRejectKRARequest,
    ManagerBulkApproveRequest, ManagerReviewSummaryResponse, ManagerReviewStatus,
    DailyKRAInstanceResponse, DailyKRAInstanceUpdate
)
from app.utils.staff_hierarchy import get_accessible_employee_ids, get_team_member_ids, get_recursive_downline, HIDDEN_FROM_TEAM_CODES, _get_hidden_employee_ids

router = APIRouter()


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)


def get_indian_date():
    """Get current date in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def get_client_ip(request: Request = None) -> str:
    """Extract client IP from request headers (handles None request)"""
    if request is None:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")


def log_kra_audit(
    db: Session,
    record_type: str,
    record_id: int,
    action: str,
    old_data: dict,
    new_data: dict,
    changed_by: str,
    ip_address: str,
    user_agent: str
):
    """Log KRA audit entry (immutable)"""
    audit_entry = StaffKRAAuditLog(
        record_type=record_type,
        record_id=record_id,
        action=action,
        old_data=old_data,
        new_data=new_data,
        changed_by_employee_id=changed_by,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_entry)


def check_vgk4u_supreme(current_user: StaffEmployee) -> bool:
    """Check if user has VGK4U Supreme role (level 150)"""
    if current_user.role and current_user.role.hierarchy_level >= 150:
        return True
    return False


def check_key_leadership_or_above(current_user: StaffEmployee) -> bool:
    """
    Check if user can create/manage KRA templates.
    Allows: hierarchy_level >= 100 (Key Leadership+) OR HR/EA role codes.
    DC-KRA-ACCESS-001: matches mobile canAddKRA logic.
    """
    if current_user.role:
        if current_user.role.hierarchy_level >= 100:
            return True
        if current_user.role.role_code in ('hr', 'ea', 'HR', 'EA'):
            return True
        if current_user.role.role_name in ('HR', 'Executive Assistant', 'Finance Admin'):
            return True
    return False


def _check_kra_delayed(instance, template):
    """
    DC Protocol: Check if a KRA instance is delayed.
    Delayed = completed after target time on same day OR completed on a later date.
    Returns: True if delayed, False if on-time or not completed yet, None if no target_time set.
    """
    if not instance.completed_at:
        return None
    
    completed_dt = instance.completed_at
    instance_date = instance.instance_date
    
    if completed_dt.tzinfo:
        completed_date = completed_dt.astimezone(pytz.timezone('Asia/Kolkata')).date()
        completed_time = completed_dt.astimezone(pytz.timezone('Asia/Kolkata')).time()
    else:
        completed_date = completed_dt.date()
        completed_time = completed_dt.time()
    
    if completed_date > instance_date:
        return True
    
    if template and template.target_time and completed_date == instance_date:
        if completed_time > template.target_time:
            return True
    
    return False


def check_hr(current_user: StaffEmployee) -> bool:
    """Check if user has HR or EA role (level 85)"""
    if current_user.role and current_user.role.role_name in ['HR', 'Executive Assistant']:
        return True
    if current_user.role and current_user.role.role_code in ['hr', 'ea']:
        return True
    return False


def check_manager_hierarchy_kra(db: Session, current_user: StaffEmployee, kra_instance: StaffKRADailyInstance) -> bool:
    """
    Check if current manager has authority to review this KRA instance
    DC: KRAs - Manager ONLY (reporting_manager OR primary_spoc)
    ONLY VGK4U Supreme (150) and HR can review all
    Leadership/Key Leadership must follow hierarchy
    """
    # DC: Guard against null role - should never happen but handle gracefully
    if not current_user.role:
        return False
    
    # ONLY VGK4U Supreme (150) OR HR/EA can review all
    if current_user.role.hierarchy_level >= 150:
        return True  # VGK4U Supreme
    if current_user.role.role_name in ['HR', 'Executive Assistant'] or current_user.role.role_code in ['hr', 'ea']:
        return True  # HR or EA
    
    # Get the KRA assignment to check hierarchy
    assignment = db.query(StaffKRAAssignment).filter(
        StaffKRAAssignment.id == kra_instance.kra_assignment_id
    ).first()
    
    if not assignment:
        return False
    
    # Check if current user is reporting_manager, SPOC, or in upline chain of the employee
    if (assignment.reporting_manager_id == current_user.id or
        assignment.primary_spoc_employee_id == current_user.id):
        return True
    
    # DC Protocol (Feb 2026): Full downline - check if employee is in current user's downline
    from app.utils.staff_hierarchy import get_recursive_downline
    downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=False)
    return assignment.employee_id in downline_ids


def check_task_approval_authority(db: Session, current_user: StaffEmployee, task) -> bool:
    """
    Check if current user has authority to review/approve this Task
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Task assigner (created_by) can approve
    - Reporting manager of assignee can approve (checked via reporting_manager_id, not hierarchy_level)
    - ONLY VGK4U Supreme (150) and HR can approve all
    """
    # DC: Guard against null role
    if not current_user.role:
        return False
    
    # ONLY VGK4U Supreme (150) OR HR/EA can approve all
    if current_user.role.hierarchy_level >= 150:
        return True  # VGK4U Supreme
    if current_user.role.role_name in ['HR', 'Executive Assistant'] or current_user.role.role_code in ['hr', 'ea']:
        return True  # HR or EA
    
    # Check if current user is the task assigner (created_by)
    if task.creator and task.creator.id == current_user.id:
        return True
    
    # DC Protocol (Feb 2026): Check if assignee is in current user's full downline
    from app.utils.staff_hierarchy import get_recursive_downline
    from app.models.staff import StaffEmployee as SE
    downline_ids = get_recursive_downline(current_user.id, db, SE, include_manager=False)
    if task.primary_assignee_id in downline_ids:
        return True
    
    return False


# ==================== KRA TEMPLATE ENDPOINTS ====================

@router.get("/next-code", summary="Get next auto-generated KRA code")
async def get_next_kra_code(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Generate next sequential KRA code
    DC Protocol: Deterministic code generation based on last code in database
    WVV: Validate uniqueness before returning
    Pattern: KRA-001, KRA-002, KRA-003, etc.
    """
    try:
        # DC: Only Key Leadership+ can request codes
        if not check_key_leadership_or_above(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only Key Leadership and above can create KRA templates"
            )
        
        # Query last template by ID (most recent)
        last_template = db.query(StaffKRATemplate).order_by(
            desc(StaffKRATemplate.id)
        ).first()
        
        # Extract counter from last code
        next_counter = 1
        if last_template and last_template.kra_code:
            try:
                # Parse: "KRA-001" → extract "001"
                parts = last_template.kra_code.split('-')
                if len(parts) == 2:
                    counter = int(parts[1])
                    next_counter = counter + 1
            except (ValueError, IndexError):
                next_counter = 1
        
        # Generate new code
        next_code = f"KRA-{next_counter:03d}"
        
        # WVV: Verify code doesn't already exist (DC deterministic)
        existing = db.query(StaffKRATemplate).filter(
            StaffKRATemplate.kra_code == next_code
        ).first()
        
        if existing:
            # If collision, find next available
            counter = next_counter + 1
            while db.query(StaffKRATemplate).filter(
                StaffKRATemplate.kra_code == f"KRA-{counter:03d}"
            ).first():
                counter += 1
            next_code = f"KRA-{counter:03d}"
        
        return {
            "kra_code": next_code,
            "message": "Auto-generated KRA code (read-only)"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"DC ERROR in get_next_kra_code: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate KRA code: {str(e)}"
        )


@router.post("/templates", summary="Create KRA template", response_model=KRATemplateResponse)
async def create_kra_template(
    template_data: KRATemplateCreate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a new KRA template
    DC: Key Leadership+ can create templates
    WVV: Template requires VGK4U approval unless created by VGK4U
    """
    if not check_key_leadership_or_above(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only Key Leadership, HR, EA, or Finance Admin can create KRA templates"
        )

    # DC-KRA-CODE-001: Server-side auto-generation of kra_code.
    # Client may send a code (e.g. from /next-code) or omit / send an invalid value.
    # Always generate server-side to guarantee correctness.
    _KRA_PATTERN = re.compile(r'^[A-Z]{2,4}-\d{3}$')
    provided = (template_data.kra_code or '').strip()
    if provided and _KRA_PATTERN.match(provided):
        # Client sent a valid code — honour it unless it collides
        kra_code_to_use = provided
        if db.query(StaffKRATemplate).filter(
            StaffKRATemplate.kra_code == kra_code_to_use
        ).first():
            kra_code_to_use = None  # fall through to auto-generate
    else:
        kra_code_to_use = None

    if kra_code_to_use is None:
        # Auto-generate next available code
        last = db.query(StaffKRATemplate).order_by(desc(StaffKRATemplate.id)).first()
        _counter = 1
        if last and last.kra_code:
            try:
                _parts = last.kra_code.split('-')
                if len(_parts) == 2:
                    _counter = int(_parts[1]) + 1
            except (ValueError, IndexError):
                _counter = 1
        kra_code_to_use = f"KRA-{_counter:03d}"
        while db.query(StaffKRATemplate).filter(
            StaffKRATemplate.kra_code == kra_code_to_use
        ).first():
            _counter += 1
            kra_code_to_use = f"KRA-{_counter:03d}"

    is_vgk4u = check_vgk4u_supreme(current_user)

    parsed_target_time = None
    if template_data.target_time:
        from datetime import time as dt_time
        h, m = map(int, template_data.target_time.split(':'))
        parsed_target_time = dt_time(h, m)

    template = StaffKRATemplate(
        kra_code=kra_code_to_use,
        title=template_data.title.strip(),
        description=template_data.description.strip() if template_data.description else None,
        applicable_to_role=template_data.applicable_to_role,
        applicable_to_designation=template_data.applicable_to_designation,
        frequency=template_data.frequency,
        frequency_config=template_data.frequency_config,
        estimated_time_minutes=template_data.estimated_time_minutes,
        target_time=parsed_target_time,
        is_mandatory=template_data.is_mandatory,
        approval_status='approved' if is_vgk4u else 'pending_approval',
        created_by_employee_id=current_user.id,
        approved_by_employee_id=current_user.id if is_vgk4u else None,
        approval_date=get_indian_time() if is_vgk4u else None,
        status='active'
    )
    
    db.add(template)
    db.flush()
    
    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='create',
        old_data={},
        new_data={
            'kra_code': template.kra_code,
            'title': template.title,
            'frequency': template.frequency,
            'approval_status': template.approval_status,
            'created_by': current_user.id
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "kra_code": template.kra_code,
        "title": template.title,
        "description": template.description,
        "applicable_to_role": template.applicable_to_role,
        "applicable_to_designation": template.applicable_to_designation,
        "frequency": template.frequency,
        "frequency_config": template.frequency_config,
        "estimated_time_minutes": template.estimated_time_minutes,
        "target_time": template.target_time.strftime('%H:%M') if template.target_time else None,
        "is_mandatory": template.is_mandatory,
        "approval_status": template.approval_status,
        "created_by_employee_id": template.created_by_employee_id,
        "approved_by_employee_id": template.approved_by_employee_id,
        "approval_date": template.approval_date.isoformat() if template.approval_date else None,
        "rejection_reason": template.rejection_reason,
        "status": template.status,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }


@router.get("/templates", summary="List KRA templates", response_model=KRATemplateListResponse)
async def list_kra_templates(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: active, inactive"),
    approval_status: Optional[str] = Query(None, description="Filter by approval: draft, pending_approval, approved, rejected"),
    frequency: Optional[str] = Query(None, description="Filter by frequency type"),
    search: Optional[str] = Query(None, description="Search by code or title"),
    employee_search: Optional[str] = Query(None, description="Search by assigned employee name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List KRA templates with filters
    DC: VGK4U/HR see all; others see only approved templates
    WVV: Validate user and role before returning data
    """
    try:
        # WVV: Validate current user exists and has role
        if not current_user or not current_user.role:
            raise HTTPException(status_code=401, detail="User authentication failed")
        
        query = db.query(StaffKRATemplate).filter(StaffKRATemplate.status != 'deleted')
        
        # DC: Role-based access control
        is_vgk4u = check_vgk4u_supreme(current_user)
        is_hr = check_hr(current_user)
        is_key_leadership = check_key_leadership_or_above(current_user)
        
        if not (is_vgk4u or is_hr):
            if is_key_leadership:
                query = query.filter(
                    or_(
                        StaffKRATemplate.approval_status == 'approved',
                        StaffKRATemplate.created_by_employee_id == current_user.id
                    )
                )
            else:
                query = query.filter(StaffKRATemplate.approval_status == 'approved')
        
        # Apply filters
        if status:
            query = query.filter(StaffKRATemplate.status == status)
        
        if approval_status:
            query = query.filter(StaffKRATemplate.approval_status == approval_status)
        
        if frequency:
            query = query.filter(StaffKRATemplate.frequency == frequency)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    StaffKRATemplate.kra_code.ilike(search_term),
                    StaffKRATemplate.title.ilike(search_term)
                )
            )
        
        if employee_search:
            employee_search_term = f"%{employee_search}%"
            matching_template_ids = db.query(StaffKRAAssignment.kra_template_id).join(
                StaffEmployee, StaffKRAAssignment.employee_id == StaffEmployee.id
            ).filter(
                or_(
                    StaffEmployee.full_name.ilike(employee_search_term),
                    StaffEmployee.first_name.ilike(employee_search_term),
                    StaffEmployee.last_name.ilike(employee_search_term),
                    StaffEmployee.emp_code.ilike(employee_search_term)
                ),
                StaffKRAAssignment.status == 'active'
            ).distinct()
            query = query.filter(StaffKRATemplate.id.in_(matching_template_ids.subquery()))
        
        # Count total before pagination
        total = query.count()
        
        # Fetch templates with pagination
        templates = query.order_by(
            desc(StaffKRATemplate.created_at)
        ).offset((page - 1) * per_page).limit(per_page).all()
        
        # Get assigned employee counts and names for each template
        template_ids = [t.id for t in templates]
        assignment_data = {}
        if template_ids:
            assignments = db.query(
                StaffKRAAssignment.kra_template_id,
                func.count(StaffKRAAssignment.id).label('count'),
                func.array_agg(
                    func.coalesce(
                        func.nullif(StaffEmployee.full_name, ''),
                        func.concat(StaffEmployee.first_name, ' ', StaffEmployee.last_name)
                    )
                ).label('names')
            ).join(
                StaffEmployee, StaffKRAAssignment.employee_id == StaffEmployee.id
            ).filter(
                StaffKRAAssignment.kra_template_id.in_(template_ids),
                StaffKRAAssignment.status == 'active'
            ).group_by(StaffKRAAssignment.kra_template_id).all()
            
            for a in assignments:
                names = [n.strip() for n in (a.names or []) if n and n.strip()][:5]
                assignment_data[a.kra_template_id] = {
                    'count': a.count,
                    'names': names
                }
        
        # DC: Build response with all required fields
        return {
            "templates": [
                {
                    "id": t.id,
                    "kra_code": t.kra_code,
                    "title": t.title,
                    "description": t.description,
                    "applicable_to_role": t.applicable_to_role,
                    "applicable_to_designation": t.applicable_to_designation,
                    "frequency": t.frequency,
                    "frequency_config": t.frequency_config,
                    "estimated_time_minutes": t.estimated_time_minutes,
                    "target_time": t.target_time.strftime('%H:%M') if t.target_time else None,
                    "is_mandatory": t.is_mandatory,
                    "approval_status": t.approval_status,
                    "created_by_employee_id": t.created_by_employee_id,
                    "approved_by_employee_id": t.approved_by_employee_id,
                    "approval_date": t.approval_date.isoformat() if t.approval_date else None,
                    "rejection_reason": t.rejection_reason,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                    "assigned_count": assignment_data.get(t.id, {}).get('count', 0),
                    "assigned_employee_names": assignment_data.get(t.id, {}).get('names', [])
                }
                for t in templates
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    
    except HTTPException:
        raise
    except Exception as e:
        # WVV: Log error for debugging
        import traceback
        print(f"DC ERROR in list_kra_templates: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load KRA templates: {str(e)}"
        )


@router.get("/templates/pending", summary="List pending approval templates")
async def list_pending_templates(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List templates pending VGK4U approval
    DC: Only VGK4U Supreme can view pending templates
    """
    if not check_vgk4u_supreme(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can view pending templates"
        )
    
    query = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.approval_status == 'pending_approval',
        StaffKRATemplate.status == 'active'
    )
    
    total = query.count()
    
    templates = query.order_by(
        StaffKRATemplate.created_at
    ).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "templates": [
            {
                "id": t.id,
                "kra_code": t.kra_code,
                "title": t.title,
                "description": t.description,
                "applicable_to_role": t.applicable_to_role,
                "applicable_to_designation": t.applicable_to_designation,
                "frequency": t.frequency,
                "frequency_config": t.frequency_config,
                "estimated_time_minutes": t.estimated_time_minutes,
                "target_time": t.target_time.strftime('%H:%M') if t.target_time else None,
                "is_mandatory": t.is_mandatory,
                "approval_status": t.approval_status,
                "created_by_employee_id": t.created_by_employee_id,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in templates
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/templates/{template_id}", summary="Get KRA template details")
async def get_kra_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get KRA template by ID
    DC: Same visibility rules as list
    """
    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    is_vgk4u = check_vgk4u_supreme(current_user)
    is_hr = check_hr(current_user)
    is_key_leadership = check_key_leadership_or_above(current_user)
    
    if not (is_vgk4u or is_hr):
        if is_key_leadership:
            if template.approval_status != 'approved' and template.created_by_employee_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            if template.approval_status != 'approved':
                raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": template.id,
        "kra_code": template.kra_code,
        "title": template.title,
        "description": template.description,
        "applicable_to_role": template.applicable_to_role,
        "applicable_to_designation": template.applicable_to_designation,
        "frequency": template.frequency,
        "frequency_config": template.frequency_config,
        "estimated_time_minutes": template.estimated_time_minutes,
        "target_time": template.target_time.strftime('%H:%M') if template.target_time else None,
        "is_mandatory": template.is_mandatory,
        "approval_status": template.approval_status,
        "created_by_employee_id": template.created_by_employee_id,
        "approved_by_employee_id": template.approved_by_employee_id,
        "approval_date": template.approval_date.isoformat() if template.approval_date else None,
        "rejection_reason": template.rejection_reason,
        "status": template.status,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }


@router.put("/templates/{template_id}", summary="Update KRA template")
async def update_kra_template(
    template_id: int,
    template_data: KRATemplateUpdate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update KRA template
    DC: Only creator or VGK4U can update; approved templates need re-approval
    """
    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    is_vgk4u = check_vgk4u_supreme(current_user)
    
    if not is_vgk4u and template.created_by_employee_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the creator or VGK4U can update this template"
        )
    
    old_data = {
        "title": template.title,
        "description": template.description,
        "frequency": template.frequency,
        "frequency_config": template.frequency_config,
        "estimated_time_minutes": template.estimated_time_minutes,
        "target_time": template.target_time.strftime('%H:%M') if template.target_time else None,
        "is_mandatory": template.is_mandatory,
        "status": template.status,
        "approval_status": template.approval_status
    }
    
    update_data = template_data.dict(exclude_unset=True)
    needs_reapproval = False
    
    for field, value in update_data.items():
        if field in ['frequency', 'frequency_config', 'estimated_time_minutes', 'is_mandatory']:
            needs_reapproval = True
        if field == 'target_time' and value:
            from datetime import time as dt_time
            h, m = map(int, value.split(':'))
            value = dt_time(h, m)
        setattr(template, field, value)
    
    if needs_reapproval and template.approval_status == 'approved' and not is_vgk4u:
        template.approval_status = 'pending_approval'
        template.approved_by_employee_id = None
        template.approval_date = None
    
    template.updated_at = get_indian_time()
    
    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='update',
        old_data=old_data,
        new_data=update_data,
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    db.refresh(template)
    
    return {
        "success": True,
        "message": "Template updated successfully",
        "needs_reapproval": needs_reapproval and not is_vgk4u,
        "template": {
            "id": template.id,
            "kra_code": template.kra_code,
            "title": template.title,
            "approval_status": template.approval_status
        }
    }


@router.post("/templates/{template_id}/approve", summary="Approve KRA template")
async def approve_kra_template(
    template_id: int,
    approve_data: KRATemplateApprove = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve KRA template
    DC: Only VGK4U Supreme can approve templates
    """
    if not check_vgk4u_supreme(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can approve KRA templates"
        )
    
    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id,
        StaffKRATemplate.approval_status == 'pending_approval'
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found or not pending approval"
        )
    
    old_status = template.approval_status
    
    template.approval_status = 'approved'
    template.approved_by_employee_id = current_user.id
    template.approval_date = get_indian_time()
    template.updated_at = get_indian_time()
    
    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='approve',
        old_data={'approval_status': old_status},
        new_data={
            'approval_status': 'approved',
            'approved_by': current_user.id,
            'notes': approve_data.notes
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Template {template.kra_code} approved successfully",
        "template_id": template.id,
        "kra_code": template.kra_code
    }


@router.post("/templates/{template_id}/reject", summary="Reject KRA template")
async def reject_kra_template(
    template_id: int,
    reject_data: KRATemplateReject = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reject KRA template
    DC: Only VGK4U Supreme can reject templates
    """
    if not check_vgk4u_supreme(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can reject KRA templates"
        )
    
    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id,
        StaffKRATemplate.approval_status == 'pending_approval'
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found or not pending approval"
        )
    
    old_status = template.approval_status
    
    template.approval_status = 'rejected'
    template.rejection_reason = reject_data.reason
    template.updated_at = get_indian_time()
    
    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='reject',
        old_data={'approval_status': old_status},
        new_data={
            'approval_status': 'rejected',
            'rejection_reason': reject_data.reason,
            'rejected_by': current_user.emp_code
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Template {template.kra_code} rejected",
        "template_id": template.id,
        "kra_code": template.kra_code,
        "reason": reject_data.reason
    }


@router.delete("/templates/{template_id}", summary="Deactivate KRA template")
async def deactivate_kra_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Deactivate (soft delete) KRA template
    DC Protocol: Menu-based access control - page assignment = full access
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    
    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id,
        StaffKRATemplate.status == 'active'
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Active template not found")
    
    template.status = 'inactive'
    template.updated_at = get_indian_time()
    
    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='deactivate',
        old_data={'status': 'active'},
        new_data={'status': 'inactive', 'deactivated_by': current_user.emp_code},
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Template {template.kra_code} deactivated",
        "template_id": template.id
    }


@router.post("/templates/{template_id}/reactivate", summary="Reactivate KRA template")
async def reactivate_kra_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reactivate a previously deactivated KRA template
    DC Protocol: Menu-based access control - page assignment = full access
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    
    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id,
        StaffKRATemplate.status == 'inactive'
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Inactive template not found")
    
    template.status = 'active'
    template.updated_at = get_indian_time()
    
    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='reactivate',
        old_data={'status': 'inactive'},
        new_data={'status': 'active', 'reactivated_by': current_user.emp_code},
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Template {template.kra_code} reactivated",
        "template_id": template.id
    }


@router.delete("/templates/{template_id}/permanent", summary="Permanently delete KRA template")
async def permanent_delete_kra_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Permanently delete a KRA template (soft-delete with future cleanup).
    DC Protocol: Menu-based access control - page assignment = full access.
    Rules:
    - Only deactivated (inactive) OR unassigned templates can be deleted
    - Future assignments (effective_from > today) are removed
    - Future daily instances (instance_date > today) are removed
    - Past/historical assignments and instances are preserved
    - Template status set to 'deleted'
    """
    # DC Protocol: Menu-based access control - page assignment = full access

    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id,
        StaffKRATemplate.status.in_(['active', 'inactive'])
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or already deleted")

    today = get_indian_date()

    active_assignment_count = db.query(func.count(StaffKRAAssignment.id)).filter(
        StaffKRAAssignment.kra_template_id == template_id,
        StaffKRAAssignment.status == 'active',
        or_(
            StaffKRAAssignment.effective_until.is_(None),
            StaffKRAAssignment.effective_until >= today
        ),
        StaffKRAAssignment.effective_from <= today
    ).scalar() or 0

    if template.status == 'active' and active_assignment_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete active template with {active_assignment_count} current assignments. Deactivate it first."
        )

    future_assignments_deleted = db.query(StaffKRAAssignment).filter(
        StaffKRAAssignment.kra_template_id == template_id,
        StaffKRAAssignment.effective_from > today
    ).delete(synchronize_session='fetch')

    future_instances_deleted = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.kra_template_id == template_id,
        StaffKRADailyInstance.instance_date > today
    ).delete(synchronize_session='fetch')

    remaining_assignments = db.query(StaffKRAAssignment).filter(
        StaffKRAAssignment.kra_template_id == template_id,
        StaffKRAAssignment.status == 'active',
        StaffKRAAssignment.effective_from <= today
    ).all()
    for assignment in remaining_assignments:
        assignment.effective_until = today
        assignment.status = 'inactive'

    old_status = template.status
    template.status = 'deleted'
    template.updated_at = get_indian_time()

    log_kra_audit(
        db=db,
        record_type='staff_kra_templates',
        record_id=template.id,
        action='permanent_delete',
        old_data={'status': old_status, 'kra_code': template.kra_code},
        new_data={
            'status': 'deleted',
            'deleted_by': current_user.emp_code,
            'future_assignments_removed': future_assignments_deleted,
            'future_instances_removed': future_instances_deleted,
            'current_assignments_ended': len(remaining_assignments)
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )

    db.commit()

    return {
        "success": True,
        "message": f"Template {template.kra_code} permanently deleted",
        "template_id": template.id,
        "future_assignments_removed": future_assignments_deleted,
        "future_instances_removed": future_instances_deleted,
        "current_assignments_ended": len(remaining_assignments)
    }


@router.get("/templates/{template_id}/delete-preview", summary="Preview what will be deleted")
async def preview_template_delete(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Preview the impact of deleting a KRA template.
    Shows counts of future assignments/instances that will be removed.
    """
    # DC Protocol: Menu-based access control - page assignment = full access

    template = db.query(StaffKRATemplate).filter(
        StaffKRATemplate.id == template_id,
        StaffKRATemplate.status.in_(['active', 'inactive'])
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or already deleted")

    today = get_indian_date()

    active_current_assignments = db.query(func.count(StaffKRAAssignment.id)).filter(
        StaffKRAAssignment.kra_template_id == template_id,
        StaffKRAAssignment.status == 'active',
        StaffKRAAssignment.effective_from <= today,
        or_(
            StaffKRAAssignment.effective_until.is_(None),
            StaffKRAAssignment.effective_until >= today
        )
    ).scalar() or 0

    future_assignments = db.query(func.count(StaffKRAAssignment.id)).filter(
        StaffKRAAssignment.kra_template_id == template_id,
        StaffKRAAssignment.effective_from > today
    ).scalar() or 0

    future_instances = db.query(func.count(StaffKRADailyInstance.id)).filter(
        StaffKRADailyInstance.kra_template_id == template_id,
        StaffKRADailyInstance.instance_date > today
    ).scalar() or 0

    past_instances = db.query(func.count(StaffKRADailyInstance.id)).filter(
        StaffKRADailyInstance.kra_template_id == template_id,
        StaffKRADailyInstance.instance_date <= today
    ).scalar() or 0

    can_delete = template.status == 'inactive' or active_current_assignments == 0

    return {
        "template_id": template.id,
        "kra_code": template.kra_code,
        "title": template.title,
        "status": template.status,
        "can_delete": can_delete,
        "reason": None if can_delete else f"Template is active with {active_current_assignments} current assignments. Deactivate first.",
        "impact": {
            "future_assignments_to_remove": future_assignments,
            "future_instances_to_remove": future_instances,
            "current_assignments_to_end": active_current_assignments,
            "past_instances_preserved": past_instances
        }
    }


# ==================== KRA STATUS DASHBOARD ====================

@router.get("/status-dashboard", summary="KRA Status Dashboard with aggregated metrics")
async def get_kra_status_dashboard(
    request: Request,
    date_from: Optional[date] = Query(None, description="Start date for filtering"),
    date_to: Optional[date] = Query(None, description="End date for filtering"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    reporting_manager_id: Optional[int] = Query(None, description="Filter by reporting manager (shows their downline)"),
    staff_type: Optional[str] = Query(None, description="Filter by staff type (MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL)"),
    search: Optional[str] = Query(None, description="Search by employee name or code"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    KRA Status Dashboard - Aggregated KRA completion metrics.
    Shows per-KRA: assigned staff, completed staff, on-time, delayed, % completed.
    For reporting managers: shows only their downline team data.
    """
    today = get_indian_date()
    if not date_from:
        date_from = today
    if not date_to:
        date_to = today

    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be before date_to")

    employee_filter_ids = None

    if reporting_manager_id:
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        raw_ids = get_recursive_downline(reporting_manager_id, db, StaffEmployee, include_manager=True)
        accessible_ids = [eid for eid in raw_ids if eid not in hidden_ids]
        employee_filter_ids = accessible_ids if accessible_ids else [-1]

    if department_id:
        from app.models.staff import StaffEmployeeDepartment
        dept_employee_ids = [
            r[0] for r in db.query(StaffEmployee.id).outerjoin(
                StaffEmployeeDepartment, StaffEmployeeDepartment.employee_id == StaffEmployee.id
            ).filter(
                or_(
                    StaffEmployee.department_id == department_id,
                    StaffEmployeeDepartment.department_id == department_id
                ),
                StaffEmployee.status == 'active'
            ).distinct().all()
        ]
        if employee_filter_ids is not None:
            employee_filter_ids = list(set(employee_filter_ids) & set(dept_employee_ids))
        else:
            employee_filter_ids = dept_employee_ids if dept_employee_ids else [-1]

    if staff_type:
        st_emp_ids = [
            r[0] for r in db.query(StaffEmployee.id).filter(
                StaffEmployee.staff_type == staff_type,
                StaffEmployee.status == 'active'
            ).all()
        ]
        if employee_filter_ids is not None:
            employee_filter_ids = list(set(employee_filter_ids) & set(st_emp_ids))
        else:
            employee_filter_ids = st_emp_ids if st_emp_ids else [-1]

    if search:
        search_term = f"%{search}%"
        search_emp_ids = [
            r[0] for r in db.query(StaffEmployee.id).filter(
                or_(
                    StaffEmployee.first_name.ilike(search_term),
                    StaffEmployee.last_name.ilike(search_term),
                    StaffEmployee.emp_code.ilike(search_term)
                ),
                StaffEmployee.status == 'active'
            ).all()
        ]
        if employee_filter_ids is not None:
            employee_filter_ids = list(set(employee_filter_ids) & set(search_emp_ids))
        else:
            employee_filter_ids = search_emp_ids if search_emp_ids else [-1]

    def _is_applicable_day(tmpl, inst_date):
        if not tmpl:
            return True
        if tmpl.frequency == 'selected_days' and tmpl.frequency_config:
            day_names = tmpl.frequency_config.get('days', [])
            weekday_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
            allowed_days = {weekday_map[d.lower()] for d in day_names if d.lower() in weekday_map}
            d = inst_date.date() if hasattr(inst_date, 'date') and callable(inst_date.date) else inst_date
            return d.weekday() in allowed_days
        return True

    all_templates = db.query(StaffKRATemplate).filter(StaffKRATemplate.status == 'active').all()
    templates_map = {t.id: t for t in all_templates}

    # DC-JIT: Auto-generate missing instances for queried employees & date range (max 7 days)
    if (date_to - date_from).days <= 7:
        _sd_emp_ids = employee_filter_ids
        if _sd_emp_ids is None:
            _sd_emp_ids = [r[0] for r in db.query(StaffEmployee.id).filter(StaffEmployee.status == 'active').all()]
        if _sd_emp_ids:
            _sd_assigns = db.query(StaffKRAAssignment).options(
                joinedload(StaffKRAAssignment.kra_template)
            ).filter(
                StaffKRAAssignment.employee_id.in_(_sd_emp_ids),
                StaffKRAAssignment.status == 'active',
                StaffKRAAssignment.effective_from <= date_to,
                or_(StaffKRAAssignment.effective_until.is_(None), StaffKRAAssignment.effective_until >= date_from)
            ).all()
            if _sd_assigns:
                _sd_existing = set(
                    (r[0], r[1], r[2]) for r in db.query(
                        StaffKRADailyInstance.employee_id,
                        StaffKRADailyInstance.kra_template_id,
                        StaffKRADailyInstance.instance_date
                    ).filter(
                        StaffKRADailyInstance.employee_id.in_(_sd_emp_ids),
                        StaffKRADailyInstance.instance_date >= date_from,
                        StaffKRADailyInstance.instance_date <= date_to
                    ).all()
                )
                _sd_count = 0
                _sd_cur = date_from
                while _sd_cur <= date_to:
                    _sd_sun = (_sd_cur.weekday() == 6)
                    for _sd_a in _sd_assigns:
                        _sd_t = _sd_a.kra_template
                        if _sd_sun:
                            _sun_ok = (_sd_t and _sd_t.frequency == 'selected_days' and _sd_t.frequency_config
                                       and 'sunday' in [d.lower() for d in _sd_t.frequency_config.get('days', [])])
                            if not _sun_ok:
                                continue
                        _sd_key = (_sd_a.employee_id, _sd_a.kra_template_id, _sd_cur)
                        if _sd_key not in _sd_existing and _sd_cur >= _sd_a.effective_from:
                            db.add(StaffKRADailyInstance(
                                employee_id=_sd_a.employee_id,
                                kra_template_id=_sd_a.kra_template_id,
                                kra_assignment_id=_sd_a.id,
                                instance_date=_sd_cur,
                                completion_status='pending',
                                manager_review_status='pending_review',
                                created_at=get_indian_time()
                            ))
                            _sd_existing.add(_sd_key)
                            _sd_count += 1
                    _sd_cur += timedelta(days=1)
                if _sd_count > 0:
                    try:
                        db.commit()
                    except Exception as _je:
                        db.rollback()

    raw_instance_query = db.query(StaffKRADailyInstance).join(
        StaffEmployee, StaffEmployee.id == StaffKRADailyInstance.employee_id
    ).filter(
        StaffKRADailyInstance.instance_date >= date_from,
        StaffKRADailyInstance.instance_date <= date_to,
        StaffEmployee.status == 'active'
    )
    if employee_filter_ids is not None:
        raw_instance_query = raw_instance_query.filter(StaffKRADailyInstance.employee_id.in_(employee_filter_ids))
    raw_instances = raw_instance_query.all()

    valid_instances = [inst for inst in raw_instances if _is_applicable_day(templates_map.get(inst.kra_template_id), inst.instance_date)]

    # Exclude instances on employee leave days
    from app.utils.leave_utils import get_employee_leave_dates as _get_leave_dates
    _dash_emp_ids = list(set(inst.employee_id for inst in valid_instances))
    _dash_leave_map = _get_leave_dates(db, _dash_emp_ids, date_from, date_to)
    if _dash_leave_map:
        def _inst_on_leave(inst):
            d = inst.instance_date.date() if hasattr(inst.instance_date, 'date') and callable(inst.instance_date.date) else inst.instance_date
            return d in _dash_leave_map.get(inst.employee_id, set())
        valid_instances = [inst for inst in valid_instances if not _inst_on_leave(inst)]

    from collections import defaultdict
    tmpl_assigned = defaultdict(set)
    tmpl_completed = defaultdict(int)
    tmpl_pending = defaultdict(int)
    for inst in valid_instances:
        tid = inst.kra_template_id
        tmpl_assigned[tid].add(inst.employee_id)
        if inst.completion_status == 'completed':
            tmpl_completed[tid] += 1
        elif inst.completion_status in ('pending', 'in_progress'):
            tmpl_pending[tid] += 1

    template_ids = list(set(tmpl_assigned.keys()))

    on_time_map = {}
    delayed_map = {}
    for inst in valid_instances:
        if inst.completion_status != 'completed':
            continue
        tmpl = templates_map.get(inst.kra_template_id)
        is_delayed = _check_kra_delayed(inst, tmpl)
        if is_delayed:
            delayed_map[inst.kra_template_id] = delayed_map.get(inst.kra_template_id, 0) + 1
        else:
            on_time_map[inst.kra_template_id] = on_time_map.get(inst.kra_template_id, 0) + 1

    dashboard_data = []
    for template_id in template_ids:
        tmpl = templates_map.get(template_id)
        if not tmpl:
            continue

        assigned_staff = len(tmpl_assigned[template_id])
        completed_count = tmpl_completed[template_id]
        pending_count = tmpl_pending[template_id]
        total_instances = completed_count + pending_count
        pct_completed = round((completed_count / total_instances * 100), 1) if total_instances > 0 else 0.0

        dashboard_data.append({
            "template_id": template_id,
            "kra_code": tmpl.kra_code,
            "title": tmpl.title,
            "frequency": tmpl.frequency,
            "target_time": str(tmpl.target_time) if tmpl.target_time else None,
            "assigned_staff": assigned_staff,
            "completed_staff": completed_count,
            "completed_in_time": on_time_map.get(template_id, 0),
            "delayed": delayed_map.get(template_id, 0),
            "pct_completed": pct_completed,
            "total_instances": total_instances
        })

    return {
        "success": True,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "department_id": department_id,
        "reporting_manager_id": reporting_manager_id,
        "kras": dashboard_data,
        "total_kras": len(dashboard_data)
    }


@router.get("/status-dashboard/{template_id}/staff", summary="Get staff detail for a specific KRA")
async def get_kra_status_staff_detail(
    template_id: int,
    request: Request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    department_id: Optional[int] = Query(None),
    reporting_manager_id: Optional[int] = Query(None),
    staff_type: Optional[str] = Query(None, description="Filter by staff type (MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL)"),
    search: Optional[str] = Query(None, description="Search by employee name or code"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get detailed staff-level status for a specific KRA within date range.
    Shows each assigned staff member's completion status, timing, etc.
    """
    today = get_indian_date()
    if not date_from:
        date_from = today
    if not date_to:
        date_to = today

    template = db.query(StaffKRATemplate).filter(StaffKRATemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="KRA template not found")

    employee_filter_ids = None

    if reporting_manager_id:
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        raw_ids = get_recursive_downline(reporting_manager_id, db, StaffEmployee, include_manager=True)
        accessible_ids = [eid for eid in raw_ids if eid not in hidden_ids]
        employee_filter_ids = accessible_ids if accessible_ids else [-1]

    if department_id:
        from app.models.staff import StaffEmployeeDepartment
        dept_employee_ids = [
            r[0] for r in db.query(StaffEmployee.id).outerjoin(
                StaffEmployeeDepartment, StaffEmployeeDepartment.employee_id == StaffEmployee.id
            ).filter(
                or_(
                    StaffEmployee.department_id == department_id,
                    StaffEmployeeDepartment.department_id == department_id
                ),
                StaffEmployee.status == 'active'
            ).distinct().all()
        ]
        if employee_filter_ids is not None:
            employee_filter_ids = list(set(employee_filter_ids) & set(dept_employee_ids))
        else:
            employee_filter_ids = dept_employee_ids if dept_employee_ids else [-1]

    if staff_type:
        st_emp_ids = [
            r[0] for r in db.query(StaffEmployee.id).filter(
                StaffEmployee.staff_type == staff_type,
                StaffEmployee.status == 'active'
            ).all()
        ]
        if employee_filter_ids is not None:
            employee_filter_ids = list(set(employee_filter_ids) & set(st_emp_ids))
        else:
            employee_filter_ids = st_emp_ids if st_emp_ids else [-1]

    if search:
        search_term = f"%{search}%"
        search_emp_ids = [
            r[0] for r in db.query(StaffEmployee.id).filter(
                or_(
                    StaffEmployee.first_name.ilike(search_term),
                    StaffEmployee.last_name.ilike(search_term),
                    StaffEmployee.emp_code.ilike(search_term)
                ),
                StaffEmployee.status == 'active'
            ).all()
        ]
        if employee_filter_ids is not None:
            employee_filter_ids = list(set(employee_filter_ids) & set(search_emp_ids))
        else:
            employee_filter_ids = search_emp_ids if search_emp_ids else [-1]

    # DC-JIT: Auto-generate missing instances for this specific template (max 7 days)
    if (date_to - date_from).days <= 7:
        _st_emp_ids = employee_filter_ids
        if _st_emp_ids is None:
            _st_emp_ids = [r[0] for r in db.query(StaffEmployee.id).filter(StaffEmployee.status == 'active').all()]
        if _st_emp_ids:
            _st_assigns = db.query(StaffKRAAssignment).options(
                joinedload(StaffKRAAssignment.kra_template)
            ).filter(
                StaffKRAAssignment.employee_id.in_(_st_emp_ids),
                StaffKRAAssignment.kra_template_id == template_id,
                StaffKRAAssignment.status == 'active',
                StaffKRAAssignment.effective_from <= date_to,
                or_(StaffKRAAssignment.effective_until.is_(None), StaffKRAAssignment.effective_until >= date_from)
            ).all()
            if _st_assigns:
                _st_existing = set(
                    (r[0], r[1], r[2]) for r in db.query(
                        StaffKRADailyInstance.employee_id,
                        StaffKRADailyInstance.kra_template_id,
                        StaffKRADailyInstance.instance_date
                    ).filter(
                        StaffKRADailyInstance.employee_id.in_(_st_emp_ids),
                        StaffKRADailyInstance.kra_template_id == template_id,
                        StaffKRADailyInstance.instance_date >= date_from,
                        StaffKRADailyInstance.instance_date <= date_to
                    ).all()
                )
                _st_count = 0
                _st_cur = date_from
                while _st_cur <= date_to:
                    _st_sun = (_st_cur.weekday() == 6)
                    for _st_a in _st_assigns:
                        _st_t = _st_a.kra_template
                        if _st_sun:
                            _sun_ok = (_st_t and _st_t.frequency == 'selected_days' and _st_t.frequency_config
                                       and 'sunday' in [d.lower() for d in _st_t.frequency_config.get('days', [])])
                            if not _sun_ok:
                                continue
                        _st_key = (_st_a.employee_id, _st_a.kra_template_id, _st_cur)
                        if _st_key not in _st_existing and _st_cur >= _st_a.effective_from:
                            db.add(StaffKRADailyInstance(
                                employee_id=_st_a.employee_id,
                                kra_template_id=_st_a.kra_template_id,
                                kra_assignment_id=_st_a.id,
                                instance_date=_st_cur,
                                completion_status='pending',
                                manager_review_status='pending_review',
                                created_at=get_indian_time()
                            ))
                            _st_existing.add(_st_key)
                            _st_count += 1
                    _st_cur += timedelta(days=1)
                if _st_count > 0:
                    try:
                        db.commit()
                    except Exception as _je:
                        db.rollback()

    instance_query = db.query(StaffKRADailyInstance).join(
        StaffEmployee, StaffEmployee.id == StaffKRADailyInstance.employee_id
    ).filter(
        StaffKRADailyInstance.kra_template_id == template_id,
        StaffKRADailyInstance.instance_date >= date_from,
        StaffKRADailyInstance.instance_date <= date_to,
        StaffEmployee.status == 'active'
    )

    if employee_filter_ids is not None:
        instance_query = instance_query.filter(StaffKRADailyInstance.employee_id.in_(employee_filter_ids))

    all_instances_raw = instance_query.order_by(StaffKRADailyInstance.instance_date.desc()).all()

    def _is_applicable_day_detail(tmpl, inst_date):
        if not tmpl:
            return True
        if tmpl.frequency == 'selected_days' and tmpl.frequency_config:
            day_names = tmpl.frequency_config.get('days', [])
            weekday_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
            allowed_days = {weekday_map[d.lower()] for d in day_names if d.lower() in weekday_map}
            d = inst_date.date() if hasattr(inst_date, 'date') and callable(inst_date.date) else inst_date
            return d.weekday() in allowed_days
        return True

    instances = [inst for inst in all_instances_raw if _is_applicable_day_detail(template, inst.instance_date)]

    # DC: Exclude instances on leave/holiday/Sunday days — dynamic from live DB
    if instances:
        from app.utils.leave_utils import get_employee_leave_dates as _get_leaves_detail
        _detail_emp_ids = list(set(inst.employee_id for inst in instances))
        _detail_leave_map = _get_leaves_detail(db, _detail_emp_ids, date_from, date_to)
        def _detail_on_leave(inst):
            d = inst.instance_date.date() if hasattr(inst.instance_date, 'date') and callable(inst.instance_date.date) else inst.instance_date
            return d in _detail_leave_map.get(inst.employee_id, set())
        instances = [inst for inst in instances if not _detail_on_leave(inst)]

    employee_ids = list(set(inst.employee_id for inst in instances))
    employees_map = {}
    if employee_ids:
        emps = db.query(StaffEmployee).filter(StaffEmployee.id.in_(employee_ids), StaffEmployee.status == 'active').all()
        employees_map = {e.id: e for e in emps}

    staff_data = []
    for inst in instances:
        emp = employees_map.get(inst.employee_id)
        is_delayed = _check_kra_delayed(inst, template)

        staff_data.append({
            "instance_id": inst.id,
            "employee_id": inst.employee_id,
            "emp_code": emp.emp_code if emp else "Unknown",
            "employee_name": f"{emp.first_name or ''} {emp.last_name or ''}".strip() if emp else "Unknown",
            "instance_date": str(inst.instance_date),
            "completion_status": inst.completion_status,
            "completion_percentage": inst.completion_percentage,
            "completed_at": str(inst.completed_at) if inst.completed_at else None,
            "time_spent_minutes": inst.time_spent_minutes,
            "is_delayed": is_delayed,
            "timing": "Delayed" if is_delayed else ("On Time" if is_delayed is False else "Pending"),
            "manager_review_status": inst.manager_review_status,
            "staff_notes": inst.staff_notes
        })

    return {
        "success": True,
        "template_id": template_id,
        "kra_code": template.kra_code,
        "title": template.title,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "staff": staff_data,
        "total_staff": len(staff_data)
    }


# ==================== STATISTICS ENDPOINTS ====================

@router.get("/templates/stats/summary", summary="Get KRA template statistics")
async def get_template_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get KRA template summary statistics
    DC: Different stats based on role
    """
    is_vgk4u = check_vgk4u_supreme(current_user)
    
    base_query = db.query(StaffKRATemplate)
    
    if not is_vgk4u:
        base_query = base_query.filter(StaffKRATemplate.status == 'active')
    
    total = base_query.count()
    
    by_status = db.query(
        StaffKRATemplate.approval_status,
        func.count(StaffKRATemplate.id)
    ).filter(
        StaffKRATemplate.status == 'active'
    ).group_by(
        StaffKRATemplate.approval_status
    ).all()
    
    by_frequency = db.query(
        StaffKRATemplate.frequency,
        func.count(StaffKRATemplate.id)
    ).filter(
        StaffKRATemplate.status == 'active',
        StaffKRATemplate.approval_status == 'approved'
    ).group_by(
        StaffKRATemplate.frequency
    ).all()
    
    pending_count = db.query(func.count(StaffKRATemplate.id)).filter(
        StaffKRATemplate.approval_status == 'pending_approval',
        StaffKRATemplate.status == 'active'
    ).scalar()
    
    return {
        "total_templates": total,
        "pending_approval": pending_count if is_vgk4u else None,
        "by_approval_status": {status: count for status, count in by_status},
        "by_frequency": {freq: count for freq, count in by_frequency}
    }


# ==================== MY KRAs ENDPOINTS (Staff Personal) ====================

@router.get("/my-kras", summary="Get current user's KRAs")
async def get_my_kras(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: pending, submitted, approved, rejected"),
    frequency: Optional[str] = Query(None, description="Filter by frequency type"),
    date_from: Optional[date] = Query(None, description="Filter from date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter to date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all KRA assignments and instances for the current logged-in user
    DC: Staff can only see their own KRAs
    DC Protocol (Jan 27, 2026): Added date_from/date_to filtering for mobile parity
    """
    today = get_indian_date()

    # DC-JIT: Auto-generate missing KRA instances for the requested date range
    # Mirrors the /instances endpoint logic, scoped to the current user only
    if date_from and date_to:
        _jit_assigns = db.query(StaffKRAAssignment).options(
            joinedload(StaffKRAAssignment.kra_template)
        ).filter(
            StaffKRAAssignment.employee_id == current_user.id,
            StaffKRAAssignment.status == 'active',
            StaffKRAAssignment.effective_from <= date_to,
            or_(StaffKRAAssignment.effective_until.is_(None), StaffKRAAssignment.effective_until >= date_from)
        ).all()
        if _jit_assigns:
            _jit_existing = set(
                (r[0], r[1], r[2]) for r in db.query(
                    StaffKRADailyInstance.employee_id,
                    StaffKRADailyInstance.kra_template_id,
                    StaffKRADailyInstance.instance_date
                ).filter(
                    StaffKRADailyInstance.employee_id == current_user.id,
                    StaffKRADailyInstance.instance_date >= date_from,
                    StaffKRADailyInstance.instance_date <= date_to
                ).all()
            )
            _jit_count = 0
            _jit_cur = date_from
            while _jit_cur <= date_to:
                _jit_sun = (_jit_cur.weekday() == 6)
                for _jit_a in _jit_assigns:
                    _jit_t = _jit_a.kra_template
                    if _jit_sun:
                        _sun_ok = (_jit_t and _jit_t.frequency == 'selected_days' and _jit_t.frequency_config
                                   and 'sunday' in [d.lower() for d in _jit_t.frequency_config.get('days', [])])
                        if not _sun_ok:
                            continue
                    _jit_key = (current_user.id, _jit_a.kra_template_id, _jit_cur)
                    if _jit_key not in _jit_existing and _jit_cur >= _jit_a.effective_from:
                        db.add(StaffKRADailyInstance(
                            employee_id=current_user.id,
                            kra_template_id=_jit_a.kra_template_id,
                            kra_assignment_id=_jit_a.id,
                            instance_date=_jit_cur,
                            completion_status='pending',
                            manager_review_status='pending_review',
                            created_at=get_indian_time()
                        ))
                        _jit_existing.add(_jit_key)
                        _jit_count += 1
                _jit_cur += timedelta(days=1)
            if _jit_count > 0:
                try:
                    db.commit()
                except Exception as _je:
                    db.rollback()

    query = db.query(StaffKRADailyInstance).join(
        StaffKRAAssignment,
        StaffKRADailyInstance.kra_assignment_id == StaffKRAAssignment.id
    ).join(
        StaffKRATemplate,
        StaffKRAAssignment.kra_template_id == StaffKRATemplate.id
    ).filter(
        StaffKRAAssignment.employee_id == current_user.id,
        StaffKRAAssignment.status == 'active'
    )
    
    # DC Protocol: Apply date range filter (mobile parity)
    if date_from:
        query = query.filter(StaffKRADailyInstance.instance_date >= date_from)
    if date_to:
        query = query.filter(StaffKRADailyInstance.instance_date <= date_to)
    
    if status:
        if status == 'pending':
            query = query.filter(StaffKRADailyInstance.completion_status == 'pending')
        elif status == 'submitted':
            query = query.filter(
                StaffKRADailyInstance.completion_status == 'completed',
                StaffKRADailyInstance.manager_review_status == 'pending_review'
            )
        elif status == 'approved':
            query = query.filter(
                StaffKRADailyInstance.manager_review_status.in_(['approved', 'edited_by_manager'])
            )
        elif status == 'rejected':
            query = query.filter(StaffKRADailyInstance.manager_review_status == 'rejected')
    
    if frequency:
        query = query.filter(StaffKRATemplate.frequency == frequency)
    
    instances = query.options(
        joinedload(StaffKRADailyInstance.kra_template),
        joinedload(StaffKRADailyInstance.assignment)
    ).order_by(
        StaffKRADailyInstance.instance_date.asc(),
        StaffKRADailyInstance.due_date.asc()
    ).all()
    
    def _is_applicable_my_kra(inst):
        tmpl = inst.kra_template
        if tmpl and tmpl.frequency == 'selected_days' and tmpl.frequency_config:
            day_names = tmpl.frequency_config.get('days', [])
            weekday_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
            allowed = {weekday_map[d.lower()] for d in day_names if d.lower() in weekday_map}
            d = inst.instance_date.date() if hasattr(inst.instance_date, 'date') and callable(inst.instance_date.date) else inst.instance_date
            return d.weekday() in allowed
        return True

    instances = [i for i in instances if _is_applicable_my_kra(i)]

    # DC: Exclude instances on leave days (includes auto-Sundays, holidays, approved leaves)
    _eff_from = date_from if date_from else (instances[0].instance_date if instances else today)
    _eff_to = date_to if date_to else today
    if hasattr(_eff_from, 'date') and callable(_eff_from.date):
        _eff_from = _eff_from.date()
    if hasattr(_eff_to, 'date') and callable(_eff_to.date):
        _eff_to = _eff_to.date()
    from app.utils.leave_utils import get_employee_nonworking_data as _get_nonworking
    _my_leave_map, _my_half_map = _get_nonworking(db, [current_user.id], _eff_from, _eff_to)
    _my_leaves = _my_leave_map.get(current_user.id, set())
    _my_half_days = _my_half_map.get(current_user.id, set())

    def _inst_date(inst):
        d = inst.instance_date
        return d.date() if hasattr(d, 'date') and callable(d.date) else d

    # Split: full leave exemptions are excluded entirely; half-days carry a flag for the frontend
    instances = [i for i in instances if _inst_date(i) not in _my_leaves]

    stats = {
        "total": len(instances),
        "pending_submission": len([i for i in instances if i.completion_status == 'pending']),
        "awaiting_review": len([i for i in instances if i.completion_status == 'completed' and i.manager_review_status == 'pending_review']),
        "approved": len([i for i in instances if i.manager_review_status in ('approved', 'edited_by_manager')])
    }
    
    kras_data = []
    for inst in instances:
        template = inst.kra_template
        kras_data.append({
            "id": inst.id,
            "assignment_id": inst.kra_assignment_id,
            "template_id": template.id if template else None,
            "kra_code": template.kra_code if template else None,
            "title": template.title if template else "Unknown",
            "description": template.description if template else None,
            "frequency": template.frequency if template else None,
            "target_time": template.target_time.strftime('%H:%M') if template and template.target_time else None,
            "instance_date": inst.instance_date.isoformat() if inst.instance_date else None,
            "due_date": inst.due_date.isoformat() if inst.due_date else None,
            "completion_status": inst.completion_status,
            "completed_at": inst.completed_at.isoformat() if inst.completed_at else None,
            "manager_review_status": inst.manager_review_status,
            "self_rating": inst.self_rating,
            "self_remarks": inst.self_remarks,
            "time_spent_minutes": inst.time_spent_minutes,
            "submitted_at": inst.submitted_at.isoformat() if inst.submitted_at else None,
            "is_late": inst.due_date < today if inst.due_date and inst.completion_status == 'pending' else False,
            "is_delayed": _check_kra_delayed(inst, template)
        })
    
    return {
        "success": True,
        "stats": stats,
        "kras": kras_data
    }


@router.get("/my-kras/{instance_id}", summary="Get specific KRA instance details")
async def get_my_kra_detail(
    instance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get details of a specific KRA daily instance
    DC: Staff can only view their own KRA instances
    """
    instance = db.query(StaffKRADailyInstance).join(
        StaffKRAAssignment,
        StaffKRADailyInstance.kra_assignment_id == StaffKRAAssignment.id
    ).filter(
        StaffKRADailyInstance.id == instance_id,
        StaffKRAAssignment.employee_id == current_user.id
    ).options(
        joinedload(StaffKRADailyInstance.kra_template),
        joinedload(StaffKRADailyInstance.assignment)
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="KRA instance not found or access denied")
    
    template = instance.kra_template
    assignment = instance.assignment
    
    return {
        "success": True,
        "kra": {
            "id": instance.id,
            "assignment_id": instance.kra_assignment_id,
            "template_id": template.id if template else None,
            "kra_code": template.kra_code if template else None,
            "title": template.title if template else "Unknown",
            "description": template.description if template else None,
            "frequency": template.frequency if template else None,
            "estimated_time_minutes": template.estimated_time_minutes if template else None,
            "target_time": template.target_time.strftime('%H:%M') if template and template.target_time else None,
            "is_mandatory": template.is_mandatory if template else False,
            "instance_date": instance.instance_date.isoformat() if instance.instance_date else None,
            "due_date": instance.due_date.isoformat() if instance.due_date else None,
            "completion_status": instance.completion_status,
            "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
            "is_delayed": _check_kra_delayed(instance, template),
            "manager_review_status": instance.manager_review_status,
            "self_rating": instance.self_rating,
            "self_remarks": instance.self_remarks,
            "time_spent_minutes": instance.time_spent_minutes,
            "submitted_at": instance.submitted_at.isoformat() if instance.submitted_at else None,
            "manager_rating": instance.manager_rating,
            "manager_remarks": instance.manager_remarks,
            "reviewed_at": instance.reviewed_at.isoformat() if instance.reviewed_at else None
        }
    }


@router.post("/my-kras/{instance_id}/submit", summary="Submit a KRA for review")
async def submit_my_kra(
    instance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Submit a KRA daily instance for manager review
    DC: Staff can only submit their own pending KRAs
    """
    body = await request.json()
    self_rating = body.get("self_rating")
    self_remarks = body.get("self_remarks", "")
    time_spent = body.get("time_spent_minutes", 0)
    
    if not self_rating or self_rating < 1 or self_rating > 5:
        raise HTTPException(status_code=400, detail="Self rating must be between 1 and 5")
    
    instance = db.query(StaffKRADailyInstance).join(
        StaffKRAAssignment,
        StaffKRADailyInstance.kra_assignment_id == StaffKRAAssignment.id
    ).filter(
        StaffKRADailyInstance.id == instance_id,
        StaffKRAAssignment.employee_id == current_user.id
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="KRA instance not found or access denied")
    
    if instance.submitted_at:
        raise HTTPException(status_code=400, detail="KRA already submitted for review")
    
    now = get_indian_time()
    old_data = {
        "completion_status": instance.completion_status,
        "self_rating": instance.self_rating,
        "self_remarks": instance.self_remarks
    }
    
    instance.completion_status = 'completed'
    instance.self_rating = self_rating
    instance.self_remarks = self_remarks.strip() if self_remarks else None
    instance.time_spent_minutes = time_spent
    instance.submitted_at = now
    instance.manager_review_status = 'pending_review'
    
    log_kra_audit(
        db=db,
        record_type='kra_daily_instance',
        record_id=instance.id,
        action='submit',
        old_data=old_data,
        new_data={
            "completion_status": 'completed',
            "self_rating": self_rating,
            "self_remarks": self_remarks
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")[:500]
    )

    # DC Protocol (Mar 2026): Auto-capture KRA time into timesheet
    if time_spent and time_spent > 0:
        try:
            from app.services.timesheet_auto_service import auto_upsert_timesheet_entry
            kra_name = (instance.kra_template.title if instance.kra_template else None) or f"KRA #{instance.id}"
            auto_upsert_timesheet_entry(
                db=db,
                employee_id=current_user.id,
                entry_date=instance.instance_date,
                time_spent_minutes=int(time_spent),
                entry_type='kra',
                auto_source='kra',
                comments=f"[Auto from KRA] {kra_name}",
                kra_id=instance.kra_assignment_id,
                created_by=current_user.id,
            )
        except Exception as _e:
            print(f"[DC-WARN] Auto timesheet entry failed for KRA instance {instance.id}: {_e}")

    db.commit()

    return {
        "success": True,
        "message": "KRA submitted successfully for manager review",
        "kra_id": instance.id
    }


# ==================== MANAGER REVIEW ENDPOINTS ====================

@router.get("/manager-review/pending", summary="Get pending/approved KRAs with comprehensive filtering")
async def get_pending_kras_for_review(
    request: Request,
    employee_id: Optional[int] = Query(None, description="Filter by specific employee ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    completion_status: Optional[str] = Query(None, description="Comma-separated completion statuses (pending, completed, partial, skipped, in_progress, na)"),
    manager_review_status: Optional[str] = Query(None, description="Comma-separated review statuses (pending_review, approved, edited_by_manager, rejected)"),
    frequency: Optional[str] = Query(None, description="Comma-separated frequencies (daily, weekly, monthly, etc)"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    manager_rating_min: Optional[int] = Query(None, description="Minimum manager rating (1-5)", ge=1, le=5),
    manager_rating_max: Optional[int] = Query(None, description="Maximum manager rating (1-5)", ge=1, le=5),
    self_rating_min: Optional[int] = Query(None, description="Minimum self rating (1-5)", ge=1, le=5),
    self_rating_max: Optional[int] = Query(None, description="Maximum self rating (1-5)", ge=1, le=5),
    view_mode: Optional[str] = Query("pending", description="View mode: 'pending' (default) or 'performance_review' (approved only)"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get KRA daily instances with comprehensive filtering
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users with direct reports can access; see only direct reports
    - VGK4U/HR see all
    CRITICAL: Performance review shows ONLY approved by upline managers (manager_review_status IN ('approved', 'edited_by_manager'))
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    print(f"[DC-KRA-REVIEW] User {current_user.id} ({current_user.role.role_name if current_user.role else 'None'}) accessing KRA review, view_mode={view_mode}")
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        print(f"[DC-KRA-REVIEW] User {current_user.id} has no direct reports and is not VGK4U/HR - returning empty results")
        return {
            "success": True,
            "view_mode": view_mode,
            "pending_count": 0,
            "pending_kras": [],
            "approved_today": 0,
            "rejected_today": 0,
            "no_review_access": True
        }
    
    # Build base query with hierarchy filter
    query = db.query(StaffKRADailyInstance).join(
        StaffKRAAssignment,
        StaffKRADailyInstance.kra_assignment_id == StaffKRAAssignment.id
    ).join(
        StaffKRATemplate,
        StaffKRADailyInstance.kra_template_id == StaffKRATemplate.id
    ).join(
        StaffEmployee,
        StaffKRADailyInstance.employee_id == StaffEmployee.id
    )
    
    # DC: PHASE1-WRITE: Apply manager review status filter based on view_mode
    # CRITICAL CONSTRAINT: Performance review shows ONLY approved KRAs
    if view_mode == "performance_review":
        print(f"[DC-PERFORMANCE-REVIEW] Filtering for approved KRAs only (approved/edited_by_manager)")
        query = query.filter(
            StaffKRADailyInstance.manager_review_status.in_(['approved', 'edited_by_manager'])
        )
    else:
        if manager_review_status:
            statuses = [s.strip() for s in manager_review_status.split(',')]
            query = query.filter(StaffKRADailyInstance.manager_review_status.in_(statuses))
        else:
            query = query.filter(StaffKRADailyInstance.manager_review_status == 'pending_review')
        if completion_status:
            pass  # already filtered above via completion_status param
    
    # DC: PHASE1-WRITE: Enforce reporting hierarchy - FULL DOWNLINE (not just direct reports)
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    if not is_vgk4u_or_hr:
        from app.utils.staff_hierarchy import get_recursive_downline
        downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=False)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        print(f"[DC-HIERARCHY] Manager {current_user.id} - enforcing full downline hierarchy ({len(downline_ids)} members)")
        query = query.filter(
            or_(
                StaffKRAAssignment.reporting_manager_id == current_user.id,
                StaffKRAAssignment.primary_spoc_employee_id == current_user.id,
                StaffKRAAssignment.employee_id.in_(downline_ids) if downline_ids else False
            )
        )
    if hidden_ids:
        query = query.filter(~StaffKRADailyInstance.employee_id.in_(hidden_ids))
    
    # DC: PHASE1-WRITE: Apply date range filter
    if date_from:
        query = query.filter(StaffKRADailyInstance.instance_date >= date_from)
        print(f"[DC-DATE-FILTER] Applied date_from: {date_from}")
    if date_to:
        query = query.filter(StaffKRADailyInstance.instance_date <= date_to)
        print(f"[DC-DATE-FILTER] Applied date_to: {date_to}")
    
    # DC: PHASE1-WRITE: Apply employee filter
    if employee_id:
        query = query.filter(StaffKRADailyInstance.employee_id == employee_id)
        print(f"[DC-EMPLOYEE-FILTER] Applied employee_id: {employee_id}")
    
    # DC: PHASE1-WRITE: Apply completion status filter
    if completion_status:
        statuses = [s.strip() for s in completion_status.split(',')]
        query = query.filter(StaffKRADailyInstance.completion_status.in_(statuses))
        print(f"[DC-STATUS-FILTER] Applied completion_status: {statuses}")
    
    # DC: PHASE1-WRITE: Apply frequency filter
    if frequency:
        frequencies = [f.strip() for f in frequency.split(',')]
        query = query.filter(StaffKRATemplate.frequency.in_(frequencies))
        print(f"[DC-FREQ-FILTER] Applied frequencies: {frequencies}")
    
    # DC: PHASE1-WRITE: Apply department filter
    if department_id:
        query = query.filter(StaffEmployee.department_id == department_id)
        print(f"[DC-DEPT-FILTER] Applied department_id: {department_id}")
    
    # DC: PHASE1-WRITE: Apply rating filters
    if manager_rating_min is not None:
        query = query.filter(StaffKRADailyInstance.manager_rating >= manager_rating_min)
    if manager_rating_max is not None:
        query = query.filter(StaffKRADailyInstance.manager_rating <= manager_rating_max)
    if self_rating_min is not None:
        query = query.filter(StaffKRADailyInstance.self_rating >= self_rating_min)
    if self_rating_max is not None:
        query = query.filter(StaffKRADailyInstance.self_rating <= self_rating_max)
    
    # DC: PHASE2-VERIFY: Execute query with joinedload to prevent N+1 queries
    pending_instances = query.options(
        joinedload(StaffKRADailyInstance.kra_template),
        joinedload(StaffKRADailyInstance.assignment),
        joinedload(StaffKRADailyInstance.employee)
    ).order_by(
        StaffKRADailyInstance.instance_date.desc()
    ).all()
    
    print(f"[DC-QUERY-RESULT] Returned {len(pending_instances)} KRA instances after filtering")
    
    # DC: PHASE3-VALIDATE: Build rich response (N+1 query fix: use preloaded employee)
    pending_kras_data = []
    for inst in pending_instances:
        template = inst.kra_template
        employee = inst.employee  # Use preloaded relationship instead of N+1 query
        
        kra_dict = {
            "id": inst.id,
            "employee_id": inst.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "employee_department_id": employee.department_id if employee else None,
            "kra_assignment_id": inst.kra_assignment_id,
            "kra_template_id": inst.kra_template_id,
            "kra_code": template.kra_code if template else None,
            "title": template.title if template else "Unknown",
            "description": template.description if template else None,
            "frequency": template.frequency if template else None,
            "target_time": template.target_time.strftime('%H:%M') if template and template.target_time else None,
            "instance_date": inst.instance_date.isoformat() if inst.instance_date else None,
            "due_date": inst.due_date.isoformat() if inst.due_date else None,
            "completion_status": inst.completion_status,
            "completed_at": inst.completed_at.isoformat() if inst.completed_at else None,
            "is_delayed": _check_kra_delayed(inst, template),
            "completion_percentage": inst.completion_percentage,
            "self_rating": inst.self_rating,
            "self_remarks": inst.self_remarks,
            "time_spent_minutes": inst.time_spent_minutes,
            "submitted_at": inst.submitted_at.isoformat() if inst.submitted_at else None,
            "manager_review_status": inst.manager_review_status,
            "manager_rating": inst.manager_rating,
            "manager_remarks": inst.manager_remarks,
            "manager_review_date": inst.manager_review_date.isoformat() if inst.manager_review_date else None,
            "updated_at": inst.updated_at.isoformat() if inst.updated_at else None
        }
        pending_kras_data.append(kra_dict)
    
    # DC-PHASE3-VALIDATE: Log response verification
    print(f"[DC-RESPONSE-VERIFY] Building response with {len(pending_kras_data)} KRAs")
    if pending_kras_data:
        sample = pending_kras_data[0]
        print(f"[DC-SAMPLE-RESPONSE] ID={sample.get('id')}, completion_status={sample.get('completion_status')}, manager_review_status={sample.get('manager_review_status')}")
    
    return {
        "success": True,
        "view_mode": view_mode,
        "pending_count": len(pending_instances),
        "pending_kras": pending_kras_data,
        "approved_today": len([k for k in pending_kras_data if k.get('manager_review_status') in ('approved', 'edited_by_manager')]),
        "rejected_today": len([k for k in pending_kras_data if k.get('manager_review_status') == 'rejected'])
    }


@router.get("/team-summary", summary="Get team KRA summary with employee-level metrics")
async def get_team_kra_summary(
    request: Request,
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    scope: str = Query("self", description="Scope: self, team, or all (VGK/EA/Key Leadership only)"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    employee_id: Optional[int] = Query(None, description="Filter by specific employee"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get team KRA summary with employee-level performance metrics.
    
    DC Protocol (Jan 01, 2026): Team Summary for KRA Review Dashboard
    - scope='self': Only logged-in user's KRAs
    - scope='team': Downline employees (requires has_direct_reports)
    - scope='all': Cross-company, all employees (VGK/EA/Key Leadership only)
    """
    from app.utils.staff_hierarchy import has_direct_reports, get_recursive_downline
    
    print(f"[DC-TEAM-SUMMARY] User {current_user.id} ({current_user.role.role_name if current_user.role else 'No Role'}) requesting scope={scope}")
    
    # Check permissions for scope
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant', 'Key Leadership'] or
        current_user.role.role_code in ['hr', 'ea', 'kl']
    )
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    
    # Determine which employees to include
    employee_ids = []
    if scope == 'self':
        employee_ids = [current_user.id]
    elif scope == 'team':
        if not is_manager and not is_vgk4u_or_hr:
            raise HTTPException(status_code=403, detail="Team scope requires management access")
        employee_ids = get_team_member_ids(current_user, db, StaffEmployee, department_id=department_id)
        if not employee_ids:
            employee_ids = [current_user.id]
    elif scope == 'all':
        if not is_vgk4u_or_hr:
            raise HTTPException(status_code=403, detail="All scope requires VGK/EA/Key Leadership access")
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        all_active = db.query(StaffEmployee.id).filter(StaffEmployee.status == 'active').all()
        employee_ids = [e.id for e in all_active if e.id not in hidden_ids]
    else:
        raise HTTPException(status_code=400, detail="Invalid scope. Use: self, team, or all")
    
    # First, get all relevant employees based on scope
    emp_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
    
    if employee_ids is not None:
        emp_query = emp_query.filter(StaffEmployee.id.in_(employee_ids))
    
    if department_id:
        emp_query = emp_query.filter(StaffEmployee.department_id == department_id)
    
    if employee_id:
        emp_query = emp_query.filter(StaffEmployee.id == employee_id)
    
    all_employees = emp_query.all()
    print(f"[DC-TEAM-SUMMARY] Found {len(all_employees)} employees for scope={scope}")

    # DC Protocol: JIT generation for team view — generate missing instances for all team members
    # so the manager sees accurate current state even before employees open their own KRA page.
    # Limit to 14-day windows to keep generation cost bounded.
    if date_from and date_to and all_employees and (date_to - date_from).days <= 14:
        _gen_emp_ids = [e.id for e in all_employees]
        _gen_assignments = db.query(StaffKRAAssignment).options(
            joinedload(StaffKRAAssignment.kra_template)
        ).filter(
            StaffKRAAssignment.employee_id.in_(_gen_emp_ids),
            StaffKRAAssignment.status == 'active',
            StaffKRAAssignment.effective_from <= date_to,
            or_(StaffKRAAssignment.effective_until.is_(None), StaffKRAAssignment.effective_until >= date_from)
        ).all()

        if _gen_assignments:
            _existing_keys = set(
                (r[0], r[1], r[2])
                for r in db.query(
                    StaffKRADailyInstance.employee_id,
                    StaffKRADailyInstance.kra_template_id,
                    StaffKRADailyInstance.instance_date
                ).filter(
                    StaffKRADailyInstance.employee_id.in_(_gen_emp_ids),
                    StaffKRADailyInstance.instance_date >= date_from,
                    StaffKRADailyInstance.instance_date <= date_to
                ).all()
            )
            _gen_count = 0
            _cur = date_from
            while _cur <= date_to:
                _is_sunday = (_cur.weekday() == 6)
                for _asgn in _gen_assignments:
                    _tmpl = _asgn.kra_template
                    if _is_sunday:
                        _sun_sel = (
                            _tmpl and _tmpl.frequency == 'selected_days' and _tmpl.frequency_config
                            and 'sunday' in [d.lower() for d in _tmpl.frequency_config.get('days', [])]
                        )
                        if not _sun_sel:
                            continue
                    _key = (_asgn.employee_id, _asgn.kra_template_id, _cur)
                    if _key not in _existing_keys and _cur >= _asgn.effective_from:
                        db.add(StaffKRADailyInstance(
                            employee_id=_asgn.employee_id,
                            kra_template_id=_asgn.kra_template_id,
                            kra_assignment_id=_asgn.id,
                            instance_date=_cur,
                            completion_status='pending',
                            manager_review_status='pending_review',
                        ))
                        _existing_keys.add(_key)
                        _gen_count += 1
                _cur += timedelta(days=1)
            if _gen_count > 0:
                try:
                    db.flush()
                    print(f"[DC-TEAM-JIT] Generated {_gen_count} missing KRA instances for {len(_gen_emp_ids)} employees ({date_from} to {date_to})")
                except Exception as _je:
                    db.rollback()
                    print(f"[DC-TEAM-JIT] Flush failed (non-fatal): {_je}")

    # Initialize stats for all employees
    employee_stats = {}
    for emp in all_employees:
        dept = emp.department.name if emp.department else None
        emp_name = emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or "Unknown"
        employee_stats[emp.id] = {
            "employee_id": emp.id,
            "employee_name": emp_name,
            "emp_code": emp.emp_code,
            "department": dept,
            "staff_type": emp.staff_type,
            "designation": emp.designation,
            "assigned_kras": 0,
            "completed_kras": 0,
            "not_completed": 0,
            "approved": 0,
            "pending_review": 0,
            "rejected": 0
        }
    
    # Build query for KRA instances
    query = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.employee_id.in_([e.id for e in all_employees])
    )
    
    # Apply date range filter
    if date_from:
        query = query.filter(StaffKRADailyInstance.instance_date >= date_from)
    if date_to:
        query = query.filter(StaffKRADailyInstance.instance_date <= date_to)
    
    # Get all matching instances
    instances = query.all()
    print(f"[DC-TEAM-SUMMARY] Found {len(instances)} KRA instances in date range")

    # Build leave dates map — instances on leave days are excluded from all calculations
    from app.utils.leave_utils import get_employee_leave_dates
    _all_emp_ids = [e.id for e in all_employees]
    _eff_from = date_from if date_from else date.today()
    _eff_to = date_to if date_to else date.today()
    leave_dates_map = get_employee_leave_dates(db, _all_emp_ids, _eff_from, _eff_to)

    # Build employee-level summary from instances (leave days excluded)
    for inst in instances:
        emp_id = inst.employee_id
        if emp_id not in employee_stats:
            continue  # Skip if employee not in our list

        # Exclude KRA instances that fall on the employee's leave days
        inst_date = inst.instance_date.date() if hasattr(inst.instance_date, 'date') and callable(inst.instance_date.date) else inst.instance_date
        if inst_date in leave_dates_map.get(emp_id, set()):
            continue

        stats = employee_stats[emp_id]
        stats["assigned_kras"] += 1

        # NA/Exempted and Skipped do not count toward performance denominator
        is_na_or_skipped = inst.completion_status in ('na', 'skipped')
        if not is_na_or_skipped:
            stats["applicable_kras"] = stats.get("applicable_kras", 0) + 1

        # Completion status
        if inst.completion_status == 'completed':
            stats["completed_kras"] += 1
        elif not is_na_or_skipped:
            stats["not_completed"] += 1
        
        # Manager review status (NA/Exempted and Skipped excluded)
        if not is_na_or_skipped:
            if inst.manager_review_status in ('approved', 'edited_by_manager'):
                stats["approved"] += 1
            elif inst.manager_review_status == 'pending_review' and inst.completion_status == 'completed':
                stats["pending_review"] += 1
            elif inst.manager_review_status == 'rejected':
                stats["rejected"] += 1
    
    # Calculate performance percentage — NA/Exempted and Skipped excluded from denominator
    summary = []
    for emp_id, stats in employee_stats.items():
        stats.setdefault("applicable_kras", 0)
        total = stats["applicable_kras"]
        approved = stats["approved"]
        stats["performance_percentage"] = round((approved / total * 100), 1) if total > 0 else 0.0
        summary.append(stats)
    
    # Sort by performance descending
    summary.sort(key=lambda x: x["performance_percentage"], reverse=True)
    
    print(f"[DC-TEAM-SUMMARY] Returning {len(summary)} employees in summary")
    
    return {
        "success": True,
        "scope": scope,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "total_employees": len(summary),
        "summary": summary
    }


@router.post("/manager-review/approve", summary="Approve a KRA daily instance")
async def approve_kra_instance(
    request_data: ManagerApproveKRARequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve a KRA daily instance
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Status changes to 'approved', counts for performance
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can approve KRAs")
    
    # Get the KRA instance
    instance = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.id == request_data.instance_id
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="KRA instance not found")
    
    # DC: Verify manager has authority for THIS specific KRA instance
    if not check_manager_hierarchy_kra(db, current_user, instance):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to approve this KRA (not reporting manager or SPOC for this assignment)"
        )
    
    if instance.manager_review_status != 'pending_review':
        raise HTTPException(status_code=400, detail=f"Cannot approve KRA with status: {instance.manager_review_status}")
    
    # DC: Verify 'approved' status counts for performance
    approved_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'kra',
        StaffConfigurableStatus.status_code == 'approved',
        StaffConfigurableStatus.status == 'active',
        StaffConfigurableStatus.counts_for_performance == True
    ).first()
    
    if not approved_status:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured to count for performance")
    
    # Update status to approved
    instance.manager_review_status = 'approved'
    instance.manager_reviewed_by_employee_id = current_user.id
    instance.manager_review_date = get_indian_time()
    if request_data.notes:
        instance.manager_edit_notes = request_data.notes
    
    # Log audit
    log_kra_audit(
        db=db,
        record_type='kra_daily_instance',
        record_id=instance.id,
        action='manager_approved',
        old_data={'manager_review_status': 'pending_review'},
        new_data={'manager_review_status': 'approved', 'approved_by': current_user.id},
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    db.refresh(instance)
    
    return {
        "success": True,
        "message": "KRA approved successfully",
        "instance": DailyKRAInstanceResponse.model_validate(instance, from_attributes=True)
    }


@router.post("/manager-review/edit", summary="Edit and auto-approve a KRA daily instance")
async def edit_kra_instance(
    request_data: ManagerEditKRARequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Edit a KRA daily instance and auto-approve
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Stores original values, status changes to 'edited_by_manager', counts for performance
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can edit KRAs")
    
    # Get the KRA instance
    instance = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.id == request_data.instance_id
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="KRA instance not found")
    
    # DC: Verify manager has authority for THIS specific KRA instance
    if not check_manager_hierarchy_kra(db, current_user, instance):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to edit this KRA (not reporting manager or SPOC for this assignment)"
        )
    
    if instance.manager_review_status not in ['pending_review', 'rejected']:
        raise HTTPException(status_code=400, detail=f"Cannot edit KRA with status: {instance.manager_review_status}")
    
    # DC: Verify 'edited_by_manager' status counts for performance
    edited_by_manager_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'kra',
        StaffConfigurableStatus.status_code == 'edited_by_manager',
        StaffConfigurableStatus.status == 'active',
        StaffConfigurableStatus.counts_for_performance == True
    ).first()
    
    if not edited_by_manager_status:
        raise HTTPException(status_code=500, detail="System error: 'edited_by_manager' status not configured to count for performance")
    
    # Validate completion_status against configurable statuses
    if request_data.completion_status:
        status_valid = db.query(StaffConfigurableStatus).filter(
            StaffConfigurableStatus.category == 'kra',
            StaffConfigurableStatus.status_code == request_data.completion_status,
            StaffConfigurableStatus.status == 'active'
        ).first()
        
        if not status_valid:
            raise HTTPException(status_code=400, detail=f"Invalid completion status: {request_data.completion_status}")
    
    # Store original values
    original_values = {
        "completion_status": instance.completion_status,
        "completion_percentage": instance.completion_percentage,
        "time_spent_minutes": instance.time_spent_minutes,
        "staff_notes": instance.staff_notes
    }
    
    # Apply edits
    if request_data.completion_status is not None:
        instance.completion_status = request_data.completion_status
    if request_data.completion_percentage is not None:
        instance.completion_percentage = request_data.completion_percentage
    if request_data.time_spent_minutes is not None:
        instance.time_spent_minutes = request_data.time_spent_minutes
    if request_data.staff_notes is not None:
        instance.staff_notes = request_data.staff_notes
    
    # Update manager review fields
    instance.manager_review_status = 'edited_by_manager'
    instance.manager_reviewed_by_employee_id = current_user.id
    instance.manager_review_date = get_indian_time()
    instance.manager_edit_notes = request_data.manager_edit_notes
    instance.original_values = original_values
    
    # Log audit
    log_kra_audit(
        db=db,
        record_type='kra_daily_instance',
        record_id=instance.id,
        action='manager_edited',
        old_data=original_values,
        new_data={
            "completion_status": instance.completion_status,
            "completion_percentage": instance.completion_percentage,
            "time_spent_minutes": instance.time_spent_minutes,
            "staff_notes": instance.staff_notes,
            "edited_by": current_user.id
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    db.refresh(instance)
    
    return {
        "success": True,
        "message": "KRA edited and auto-approved successfully",
        "instance": DailyKRAInstanceResponse.model_validate(instance, from_attributes=True)
    }


@router.post("/manager-review/reject", summary="Reject a KRA daily instance")
async def reject_kra_instance(
    request_data: ManagerRejectKRARequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reject a KRA daily instance
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Status changes to 'rejected', does NOT count for performance
    - Staff must resubmit for re-approval
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can reject KRAs")
    
    # Get the KRA instance
    instance = db.query(StaffKRADailyInstance).filter(
        StaffKRADailyInstance.id == request_data.instance_id
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="KRA instance not found")
    
    # DC: Verify manager has authority for THIS specific KRA instance
    if not check_manager_hierarchy_kra(db, current_user, instance):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to reject this KRA (not reporting manager or SPOC for this assignment)"
        )
    
    if instance.manager_review_status != 'pending_review':
        raise HTTPException(status_code=400, detail=f"Cannot reject KRA with status: {instance.manager_review_status}")
    
    # DC: Verify 'rejected' status exists, is active, and does NOT count for performance
    rejected_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'kra',
        StaffConfigurableStatus.status_code == 'rejected',
        StaffConfigurableStatus.status == 'active'
    ).first()
    
    if not rejected_status:
        raise HTTPException(status_code=500, detail="System error: 'rejected' status not configured in catalog")
    
    # DC: Rejected status must NOT count for performance (semantic validation)
    if rejected_status.counts_for_performance:
        raise HTTPException(status_code=500, detail="System error: 'rejected' status incorrectly configured to count for performance")
    
    # Update status to rejected
    instance.manager_review_status = 'rejected'
    instance.manager_reviewed_by_employee_id = current_user.id
    instance.manager_review_date = get_indian_time()
    instance.rejection_reason = request_data.rejection_reason
    
    # Log audit
    log_kra_audit(
        db=db,
        record_type='kra_daily_instance',
        record_id=instance.id,
        action='manager_rejected',
        old_data={'manager_review_status': 'pending_review'},
        new_data={
            'manager_review_status': 'rejected',
            'rejected_by': current_user.id,
            'rejection_reason': request_data.rejection_reason
        },
        changed_by=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "unknown")
    )
    
    db.commit()
    db.refresh(instance)
    
    return {
        "success": True,
        "message": "KRA rejected successfully. Staff must resubmit for re-approval.",
        "instance": DailyKRAInstanceResponse.model_validate(instance, from_attributes=True)
    }


@router.post("/manager-review/bulk-approve", summary="Bulk approve multiple KRA instances")
async def bulk_approve_kras(
    request_data: ManagerBulkApproveRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Bulk approve multiple KRA daily instances
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - TRANSACTIONAL - All-or-nothing. Validates ALL instances BEFORE any mutation.
    - If ANY instance fails validation, entire batch is rejected.
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can bulk approve KRAs")
    
    # DC: PHASE 1 - Validate ALL instances BEFORE any mutation (fail-fast)
    validated_instances = []
    validation_errors = []
    
    for instance_id in request_data.instance_ids:
        # Get the KRA instance
        instance = db.query(StaffKRADailyInstance).filter(
            StaffKRADailyInstance.id == instance_id
        ).first()
        
        if not instance:
            validation_errors.append({"id": instance_id, "reason": "Not found"})
            continue
        
        # DC: Verify manager has authority for THIS specific KRA instance
        if not check_manager_hierarchy_kra(db, current_user, instance):
            validation_errors.append({"id": instance_id, "reason": "Not authorized (not your team member)"})
            continue
        
        if instance.manager_review_status != 'pending_review':
            validation_errors.append({"id": instance_id, "reason": f"Invalid status: {instance.manager_review_status}"})
            continue
        
        # Instance passed all validation
        validated_instances.append(instance)
    
    # DC: FAIL-FAST - If ANY validation errors, reject entire batch
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Bulk approval rejected: {len(validation_errors)} instances failed validation. No changes made.",
                "failed_count": len(validation_errors),
                "validated_count": len(validated_instances),
                "validation_errors": validation_errors
            }
        )
    
    # DC: Verify 'approved' status exists and is active before mutation
    approved_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'kra',
        StaffConfigurableStatus.status_code == 'approved',
        StaffConfigurableStatus.status == 'active'
    ).first()
    
    if not approved_status:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured in catalog")
    
    if not approved_status.counts_for_performance:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured to count for performance")
    
    # DC: PHASE 2 - All validated, now mutate (transactional)
    try:
        approval_time = get_indian_time()
        
        for instance in validated_instances:
            # Update status to approved
            instance.manager_review_status = 'approved'
            instance.manager_reviewed_by_employee_id = current_user.id
            instance.manager_review_date = approval_time
            if request_data.notes:
                instance.manager_edit_notes = request_data.notes
            
            # Log audit
            log_kra_audit(
                db=db,
                record_type='kra_daily_instance',
                record_id=instance.id,
                action='manager_bulk_approved',
                old_data={'manager_review_status': 'pending_review'},
                new_data={'manager_review_status': 'approved', 'approved_by': current_user.id},
                changed_by=current_user.id,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "unknown")
            )
        
        db.commit()
        
        return {
            "success": True,
            "approved_count": len(validated_instances),
            "failed_count": 0,
            "failed_instances": [],
            "message": f"Bulk approval successful: {len(validated_instances)} KRAs approved"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Transaction failed, all changes rolled back: {str(e)}"
        )


@router.get("/manager-review/summary", summary="Get manager review summary")
async def get_manager_review_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get summary of pending items for manager review (KRAs + Tasks)
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Unified day-end review interface
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can access review summary")
    
    # Build base query with hierarchy filter
    query = db.query(StaffKRADailyInstance).join(
        StaffKRAAssignment,
        StaffKRADailyInstance.kra_assignment_id == StaffKRAAssignment.id
    ).filter(
        StaffKRADailyInstance.manager_review_status == 'pending_review'
    )
    hidden_ids_review = _get_hidden_employee_ids(db, StaffEmployee)
    if not is_vgk4u_or_hr:
        from app.utils.staff_hierarchy import get_recursive_downline
        downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=False)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids_review]
        query = query.filter(
            or_(
                StaffKRAAssignment.reporting_manager_id == current_user.id,
                StaffKRAAssignment.primary_spoc_employee_id == current_user.id,
                StaffKRAAssignment.employee_id.in_(downline_ids) if downline_ids else False
            )
        )
    if hidden_ids_review:
        query = query.filter(~StaffKRADailyInstance.employee_id.in_(hidden_ids_review))
    
    # Get pending KRAs
    pending_kras = query.options(
        joinedload(StaffKRADailyInstance.kra_template)
    ).order_by(
        StaffKRADailyInstance.instance_date.desc()
    ).all()
    
    # Get pending Tasks (placeholder - will be implemented when task review is added)
    pending_tasks = []
    
    return {
        "pending_kra_count": len(pending_kras),
        "pending_task_count": len(pending_tasks),
        "pending_kras": [DailyKRAInstanceResponse.model_validate(inst, from_attributes=True) for inst in pending_kras],
        "pending_tasks": pending_tasks
    }


# ==================== KRA ASSIGNMENT & INSTANCE GENERATION ====================

@router.post("/templates/{template_id}/assign", summary="Assign KRA template to multiple employees")
async def assign_kra_to_employees(
    template_id: int,
    assignment_data: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Assign KRA template to multiple employees with auto-instance generation
    DC Protocol: Write → Verify → Validate
    - WRITE: Accept MNR IDs, convert to employee IDs
    - VERIFY: Check template exists, validate employee existence
    - VALIDATE: Create assignments and auto-generate instances
    WVV: Deterministic instance generation based on frequency
    """
    try:
        # DC-WRITE: Only VGK/EA/HR can assign KRAs
        if not (current_user.role and current_user.role.role_name in ['HR', 'Executive Assistant'] or 
                current_user.role.role_code in ['hr', 'ea'] or
                current_user.role.hierarchy_level >= 150):
            raise HTTPException(status_code=403, detail="Only HR/EA/VGK4U can assign KRAs")
        
        # DC-VERIFY: Get template
        template = db.query(StaffKRATemplate).filter(StaffKRATemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="KRA template not found")
        
        # DC-WRITE: Extract and convert data
        employee_mnr_ids = assignment_data.get("employee_ids", [])
        effective_from = assignment_data.get("effective_from")
        effective_until = assignment_data.get("effective_until")
        
        if not employee_mnr_ids or not effective_from:
            raise HTTPException(status_code=400, detail="employee_ids and effective_from are required")
        
        from datetime import datetime, timedelta
        
        effective_from_date = datetime.fromisoformat(effective_from).date()
        effective_until_date = datetime.fromisoformat(effective_until).date() if effective_until else None
        
        created_instances = 0
        errors = []
        
        employee_ids = []
        for emp_code in employee_mnr_ids:
            try:
                emp = db.query(StaffEmployee).filter(
                    StaffEmployee.emp_code == emp_code,
                    StaffEmployee.status == 'active'
                ).first()
                if not emp:
                    errors.append(f"Employee {emp_code} not found or inactive")
                else:
                    employee_ids.append(emp.id)
            except Exception as e:
                errors.append(f"Error looking up {emp_code}: {str(e)}")
        
        if not employee_ids and errors:
            raise HTTPException(status_code=400, detail=f"No valid employees found. Errors: {errors}")
        
        assigned_count = 0
        client_ip = get_client_ip(request)
        client_ua = request.headers.get("User-Agent", "unknown")

        for emp_id in employee_ids:
            try:
                existing = db.query(StaffKRAAssignment).filter(
                    StaffKRAAssignment.employee_id == emp_id,
                    StaffKRAAssignment.kra_template_id == template_id,
                    StaffKRAAssignment.effective_from == effective_from_date
                ).first()
                
                if existing:
                    errors.append(f"Employee {emp_id} already has this KRA assignment from {effective_from_date}")
                    continue
                
                assignment = StaffKRAAssignment(
                    employee_id=emp_id,
                    kra_template_id=template_id,
                    primary_spoc_employee_id=current_user.id,
                    assigned_by_employee_id=current_user.id,
                    assigned_date=get_indian_time().date(),
                    effective_from=effective_from_date,
                    effective_until=effective_until_date,
                    status='active'
                )
                db.add(assignment)
                db.flush()
                
                existing_dates = set(
                    row[0] for row in db.query(StaffKRADailyInstance.instance_date).filter(
                        StaffKRADailyInstance.employee_id == emp_id,
                        StaffKRADailyInstance.kra_template_id == template_id,
                        StaffKRADailyInstance.instance_date >= effective_from_date,
                        StaffKRADailyInstance.instance_date <= effective_from_date + timedelta(days=30)
                    ).all()
                )
                
                current_date = effective_from_date
                end_date = current_date + timedelta(days=30)
                emp_instances = 0
                
                while current_date <= end_date:
                    should_create = False

                    # DC: Never generate instances on Sundays for daily/weekly/monthly KRAs.
                    # selected_days can explicitly include Sunday if configured.
                    is_sunday = (current_date.weekday() == 6)

                    if template.frequency == 'daily':
                        should_create = not is_sunday
                    elif template.frequency == 'weekly':
                        should_create = (current_date.weekday() == 0)
                    elif template.frequency == 'selected_days' and template.frequency_config:
                        day_names = template.frequency_config.get('days', [])
                        weekday_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
                        allowed_days = {weekday_map[d.lower()] for d in day_names if d.lower() in weekday_map}
                        should_create = (current_date.weekday() in allowed_days)
                    elif template.frequency == 'custom' and template.frequency_config:
                        dates = template.frequency_config.get('dates', [])
                        should_create = ((current_date.weekday() + 1) in dates)
                    elif template.frequency == 'monthly':
                        should_create = (current_date.day == 1)
                    else:
                        should_create = not is_sunday
                    
                    if should_create and current_date not in existing_dates:
                        instance = StaffKRADailyInstance(
                            employee_id=emp_id,
                            kra_assignment_id=assignment.id,
                            kra_template_id=template_id,
                            instance_date=current_date,
                            completion_status='pending',
                            manager_review_status='pending_review'
                        )
                        db.add(instance)
                        emp_instances += 1
                    
                    current_date += timedelta(days=1)
                
                created_instances += emp_instances
                
                log_kra_audit(
                    db=db,
                    record_type='staff_kra_assignments',
                    record_id=assignment.id,
                    action='create',
                    old_data={},
                    new_data={'employee_id': emp_id, 'template_id': template_id, 'instances_created': emp_instances},
                    changed_by=current_user.id,
                    ip_address=client_ip,
                    user_agent=client_ua
                )
                
                db.commit()
                assigned_count += 1
            
            except Exception as e:
                db.rollback()
                errors.append(f"Error assigning to employee {emp_id}: {str(e)}")
        
        return {
            "success": True,
            "created_instances": created_instances,
            "errors": errors,
            "message": f"Assigned to {len(employee_ids) - len(errors)} employees with {created_instances} instances created"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to assign KRA: {str(e)}")


@router.get("/instances", summary="Get KRA instances with filtering")
async def get_kra_instances(
    request: Request,
    employee_id: int = Query(None),
    template_id: int = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get KRA instances with customizable filtering + On-Demand Generation
    DC: Instances auto-generated for filtered date range if missing
    WVV: Write instances → Verify against assignments → Validate date range
    """
    try:
        # Parse dates
        from_date = datetime.fromisoformat(date_from).date() if date_from else None
        to_date = datetime.fromisoformat(date_to).date() if date_to else None
        
        # WVV-PHASE1: WRITE - Auto-generate missing instances for filtered date range
        if from_date and to_date:
            print(f"[DC-AUTO-GEN] Starting instance generation for user {current_user.id} (role: {current_user.role.role_name if current_user.role else 'No Role'})")
            print(f"[DC-AUTO-GEN] Date range: {from_date} to {to_date}")

            # Get active assignments scoped to the target employee
            # DC Protocol: When employee_id is provided, always scope generation to that employee only.
            # This prevents org-wide N×M query explosion when a manager views a team member's KRAs.
            is_admin_or_hr = current_user.role and (
                current_user.role.hierarchy_level >= 150 or
                current_user.role.role_name in ['HR', 'Executive Assistant']
            )

            assignment_query = db.query(StaffKRAAssignment).join(
                StaffKRATemplate,
                StaffKRAAssignment.kra_template_id == StaffKRATemplate.id
            )

            if employee_id:
                # Scope tightly to the requested employee — avoids generating for entire org
                print(f"[DC-FILTER] Scoping auto-gen to employee_id={employee_id}")
                assignment_query = assignment_query.filter(StaffKRAAssignment.employee_id == employee_id)
            elif not is_admin_or_hr:
                print(f"[DC-FILTER] Non-admin: scoping to self employee_id={current_user.id}")
                assignment_query = assignment_query.filter(StaffKRAAssignment.employee_id == current_user.id)
            else:
                print(f"[DC-FILTER] Admin/Manager mode with no employee_id — scoping to self to prevent org-wide gen")
                assignment_query = assignment_query.filter(StaffKRAAssignment.employee_id == current_user.id)

            assignment_query = assignment_query.filter(
                StaffKRAAssignment.status == 'active',
                StaffKRAAssignment.effective_from <= to_date,
                or_(StaffKRAAssignment.effective_until.is_(None), StaffKRAAssignment.effective_until >= from_date)
            )

            assignments = assignment_query.all()
            print(f"[DC-AUTO-GEN] Found {len(assignments)} active assignments in date range")

            if assignments:
                # DC-BULK-CHECK: Fetch all existing instances for this employee + date range in ONE query
                # Replaces the previous N×M individual-SELECT loop (was 268 queries for 67 assignments × 4 days)
                target_employee_ids = list(set(a.employee_id for a in assignments))
                existing_keys = set(
                    (inst.employee_id, inst.kra_template_id, inst.instance_date)
                    for inst in db.query(
                        StaffKRADailyInstance.employee_id,
                        StaffKRADailyInstance.kra_template_id,
                        StaffKRADailyInstance.instance_date
                    ).filter(
                        StaffKRADailyInstance.employee_id.in_(target_employee_ids),
                        StaffKRADailyInstance.instance_date >= from_date,
                        StaffKRADailyInstance.instance_date <= to_date
                    ).all()
                )
                print(f"[DC-AUTO-GEN] Bulk-fetched {len(existing_keys)} existing instance keys")

                # Generate only truly missing instances — skip Sundays for non-selected_days KRAs
                generated_count = 0
                current_date = from_date
                while current_date <= to_date:
                    is_sunday = (current_date.weekday() == 6)
                    for assignment in assignments:
                        tmpl = db.query(StaffKRATemplate).get(assignment.kra_template_id)
                        # Skip Sundays unless the template explicitly includes Sunday via selected_days
                        if is_sunday:
                            is_sunday_selected = False
                            if tmpl and tmpl.frequency == 'selected_days' and tmpl.frequency_config:
                                day_names = tmpl.frequency_config.get('days', [])
                                is_sunday_selected = 'sunday' in [d.lower() for d in day_names]
                            if not is_sunday_selected:
                                continue
                        key = (assignment.employee_id, assignment.kra_template_id, current_date)
                        if key not in existing_keys and current_date >= assignment.effective_from:
                            db.add(StaffKRADailyInstance(
                                employee_id=assignment.employee_id,
                                kra_template_id=assignment.kra_template_id,
                                kra_assignment_id=assignment.id,
                                instance_date=current_date,
                                completion_status='pending',
                                manager_review_status='pending_review',
                                created_at=get_indian_time()
                            ))
                            existing_keys.add(key)
                            generated_count += 1
                    current_date += timedelta(days=1)

                # WVV-PHASE2: VERIFY - Commit auto-generated instances
                try:
                    db.commit()
                    print(f"[DC-AUTO-GEN] ✅ Generated {generated_count} new instances")
                except Exception as e:
                    db.rollback()
                    print(f"[DC-AUTO-GEN-ERROR] Failed to generate instances: {str(e)}")
                    pass
        
        # WVV-PHASE3: VERIFY - Query instances with filters
        query = db.query(StaffKRADailyInstance).join(
            StaffKRATemplate,
            StaffKRADailyInstance.kra_template_id == StaffKRATemplate.id
        )
        
        # DC-CONSISTENCY: Role-based filtering (same logic as assignment generation)
        is_admin_view = current_user.role and (
            current_user.role.hierarchy_level >= 150 or
            current_user.role.role_name in ['HR', 'Executive Assistant']
        )
        if not is_admin_view:
            print(f"[DC-QUERY-FILTER] Staff member {current_user.id} - showing own instances only")
            query = query.filter(StaffKRADailyInstance.employee_id == current_user.id)
        else:
            print(f"[DC-QUERY-FILTER] Manager/Admin {current_user.id} - showing all instances")
        
        # Apply filters
        if employee_id:
            print(f"[DC-QUERY-FILTER] Applied employee_id filter: {employee_id}")
            query = query.filter(StaffKRADailyInstance.employee_id == employee_id)
        
        if template_id:
            query = query.filter(StaffKRADailyInstance.kra_template_id == template_id)
        
        if from_date:
            query = query.filter(StaffKRADailyInstance.instance_date >= from_date)
        
        if to_date:
            query = query.filter(StaffKRADailyInstance.instance_date <= to_date)
        
        if status:
            query = query.filter(StaffKRADailyInstance.completion_status == status)
        
        instances = query.order_by(StaffKRADailyInstance.instance_date.desc()).all()
        
        # DC-VALIDATE: Compute statistics
        unique_dates = len(set(inst.instance_date for inst in instances))
        unique_kras = len(set(inst.kra_template_id for inst in instances))
        date_range = f"{min(inst.instance_date for inst in instances) if instances else 'N/A'} to {max(inst.instance_date for inst in instances) if instances else 'N/A'}"
        
        print(f"[DC-VALIDATE] ✅ Query returned {len(instances)} instances from {unique_dates} dates covering {unique_kras} KRAs")
        print(f"[DC-VALIDATE] Date range: {date_range}")
        
        # WVV-COMPLETE: Return instances with audit info
        template_cache = {}
        for inst in instances:
            if inst.kra_template_id not in template_cache and inst.kra_template:
                template_cache[inst.kra_template_id] = inst.kra_template

        return {
            "total": len(instances),
            "instances": [
                {
                    "id": inst.id,
                    "employee_id": inst.employee_id,
                    "kra_template_id": inst.kra_template_id,
                    "kra_title": inst.kra_template.title if inst.kra_template else "Unknown",
                    "kra_code": inst.kra_template.kra_code if inst.kra_template else None,
                    "frequency": inst.kra_template.frequency if inst.kra_template else None,
                    "instance_date": inst.instance_date.isoformat(),
                    "completion_status": inst.completion_status,
                    "staff_notes": inst.staff_notes,
                    "manager_remarks": inst.manager_remarks,
                    "manager_review_status": inst.manager_review_status,
                    "time_spent_minutes": inst.time_spent_minutes,
                    "submitted_at": inst.submitted_at.isoformat() if inst.submitted_at else None,
                    "self_rating": inst.self_rating
                }
                for inst in instances
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch instances: {str(e)}")


@router.put("/instances/{instance_id}", summary="Update KRA instance status")
async def update_kra_instance(
    instance_id: int,
    update_data: DailyKRAInstanceUpdate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update KRA instance (mark done/pending or manager review)
    DC: Immutable audit trail of all changes
    WVV: Write changes → Verify timestamp → Validate audit
    """
    try:
        instance = db.query(StaffKRADailyInstance).filter(
            StaffKRADailyInstance.id == instance_id
        ).first()
        
        if not instance:
            raise HTTPException(status_code=404, detail="KRA instance not found")
        
        # DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - Check permissions
        from app.utils.staff_hierarchy import has_direct_reports
        
        is_employee = instance.employee_id == current_user.id
        is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
        is_vgk4u_or_hr = current_user.role and (
            current_user.role.hierarchy_level >= 150 or 
            current_user.role.role_name in ['HR', 'Executive Assistant'] or
            current_user.role.role_code in ['hr', 'ea']
        )
        
        if not (is_employee or is_manager or is_vgk4u_or_hr):
            raise HTTPException(status_code=403, detail="Not authorized to update this instance")
        
        if is_employee and not is_manager and not is_vgk4u_or_hr and instance.submitted_at:
            raise HTTPException(status_code=400, detail="Cannot modify a submitted KRA. It is under manager review.")
        
        old_data = {
            "completion_status": instance.completion_status,
            "staff_notes": instance.staff_notes,
            "manager_review_status": instance.manager_review_status
        }
        
        # DC-PHASE1-WRITE: Employee can update: completion_status, staff_notes, time_spent_minutes
        # Allow both employees AND admins/managers to update completion status
        if is_employee or is_manager:
            instance.completion_status = update_data.completion_status
            instance.completion_percentage = update_data.completion_percentage
            instance.staff_notes = update_data.staff_notes
            if update_data.time_spent_minutes is not None:
                instance.time_spent_minutes = update_data.time_spent_minutes
                instance.time_source = update_data.time_source
            if instance.completion_status == 'completed':
                instance.completed_at = get_indian_time()
            print(f'[DC-WRITE] Update by user {current_user.id}: status={instance.completion_status}, percentage={instance.completion_percentage}')
            
            # If manager, also record review metadata
            if is_manager:
                instance.manager_reviewed_by_employee_id = current_user.id
                instance.manager_review_date = get_indian_time()
                if hasattr(update_data, 'manager_review_status') and update_data.manager_review_status:
                    review_status = update_data.manager_review_status
                    if review_status in ['pending_review', 'approved', 'rejected', 'edited_by_manager']:
                        instance.manager_review_status = review_status
                print(f'[DC-WRITE] Manager metadata recorded: review_status={instance.manager_review_status}')
        
        db.add(instance)
        db.flush()
        
        if is_employee and update_data.time_spent_minutes and update_data.time_spent_minutes > 0:
            from app.services.activity_time_service import log_activity_time
            try:
                kra_title = instance.kra_template.title if instance.kra_template else f"KRA #{instance.kra_template_id}"
                kra_code = instance.kra_template.kra_code if instance.kra_template else None
                estimated = instance.kra_template.estimated_time_minutes if instance.kra_template else 0
                log_activity_time(
                    db=db,
                    employee_id=instance.employee_id,
                    source_type='kra',
                    completed_minutes=update_data.time_spent_minutes,
                    target_date=instance.instance_date,
                    source_id=instance.id,
                    source_title=kra_title,
                    source_code=kra_code,
                    required_minutes=estimated or 0,
                    description=f"KRA update: {instance.completion_status}",
                    ip_address=get_client_ip(request),
                    user_agent=request.headers.get("User-Agent", "")[:500],
                    created_by=current_user.id
                )
            except Exception as e:
                print(f"[DC-WARN] Activity time log failed for KRA instance {instance.id}: {e}")
        
        new_data = {
            "completion_status": instance.completion_status,
            "staff_notes": instance.staff_notes,
            "manager_review_status": instance.manager_review_status
        }
        
        log_kra_audit(
            db=db,
            record_type='staff_kra_daily_instances',
            record_id=instance.id,
            action='update',
            old_data=old_data,
            new_data=new_data,
            changed_by=current_user.id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", "unknown")
        )
        
        db.commit()
        db.refresh(instance)
        
        return {
            "id": instance.id,
            "completion_status": instance.completion_status,
            "manager_review_status": instance.manager_review_status,
            "updated_at": instance.updated_at.isoformat(),
            "audit_created": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update instance: {str(e)}")


@router.get("/activity/manager-reviews", summary="Get recent manager review activity")
async def get_manager_review_activity(
    request: Request,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get recent manager review activity (approved/rejected KRAs and tasks)
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Activity feed for manager review dashboard
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager (has_direct_reports) OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or 
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can access review activity")
    
    ist = pytz.timezone('Asia/Kolkata')
    
    # Get recent KRA reviews (approved/rejected)
    kra_query = db.query(StaffKRADailyInstance).join(
        StaffKRAAssignment,
        StaffKRADailyInstance.kra_assignment_id == StaffKRAAssignment.id
    ).filter(
        StaffKRADailyInstance.manager_review_status.in_(['approved', 'rejected'])
    )
    
    hidden_ids_activity = _get_hidden_employee_ids(db, StaffEmployee)
    if not is_vgk4u_or_hr:
        from app.utils.staff_hierarchy import get_recursive_downline
        downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=False)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids_activity]
        kra_query = kra_query.filter(
            or_(
                StaffKRAAssignment.reporting_manager_id == current_user.id,
                StaffKRAAssignment.primary_spoc_employee_id == current_user.id,
                StaffKRAAssignment.employee_id.in_(downline_ids) if downline_ids else False
            )
        )
    if hidden_ids_activity:
        kra_query = kra_query.filter(~StaffKRADailyInstance.employee_id.in_(hidden_ids_activity))
    
    recent_kras = kra_query.options(
        joinedload(StaffKRADailyInstance.kra_template)
    ).order_by(
        StaffKRADailyInstance.manager_review_date.desc()
    ).limit(limit).all()
    
    # Build activity list
    activity = []
    for kra in recent_kras:
        # Get employee name
        employee = db.query(StaffEmployee).filter(
            StaffEmployee.id == kra.employee_id
        ).first()
        
        activity.append({
            "type": "kra",
            "id": kra.id,
            "title": kra.kra_template.title if kra.kra_template else "Unknown KRA",
            "employee_id": kra.employee_id,
            "employee_name": employee.full_name if employee else kra.employee_id,
            "action": kra.manager_review_status,
            "reviewed_by": kra.manager_reviewed_by_employee_id,
            "reviewed_at": kra.manager_review_date.astimezone(ist).isoformat() if kra.manager_review_date else None,
            "instance_date": kra.instance_date.isoformat()
        })
    
    # Sort by review timestamp descending
    activity.sort(key=lambda x: x.get('reviewed_at') or '', reverse=True)
    
    return {
        "activity": activity[:limit],
        "total_count": len(activity)
    }
