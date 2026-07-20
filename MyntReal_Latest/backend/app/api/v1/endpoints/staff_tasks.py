"""
Staff Task Management API Endpoints (DC Protocol Compliant)
Complete task management with assignment, comments, time tracking

Key Features:
- Anyone can assign tasks to anyone (no hierarchy restriction)
- Primary (1 mandatory) + Secondary (up to 2) assignees
- Running tasks: Anyone can invite others or reassign
- Full activity logging for audit trail

Endpoints:
- Task CRUD: Create, List, Detail, Update, Delete
- Assignment: Add/Remove secondary assignees, Reassign primary
- Comments: Add comments (immutable)
- Time Entries: Log time spent on tasks
- Views: Assigned By Me, Assigned To Me, Complete Tracker
- Analytics: Summary, By Status, By Employee, Overdue

Created: Nov 26, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, status, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import and_, or_, func, case, exists
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz
import os
import uuid
import logging
from pathlib import Path
from urllib.parse import quote

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.staff_tasks import (
    StaffTask, StaffTaskAssignee, StaffTaskComment,
    StaffTaskActivityLog, StaffTaskTimeEntry, StaffTaskAttachment,
    StaffTaskPhase, generate_task_code, log_task_activity
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.image_compression_service import ImageCompressionService, ImageCompressionError
from app.api.v1.endpoints.staff_task_schemas import (
    CreateTaskRequest, UpdateTaskRequest, UpdateTaskProgressRequest,
    UpdateTaskStatusRequest, AddSecondaryAssigneeRequest, ReassignPrimaryRequest,
    AddCommentRequest, LogTimeRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


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


def sanitize_filename_for_header(filename: str) -> str:
    """
    Sanitize filename for Content-Disposition header
    DC: Use RFC 2231 UTF-8 encoding to support Unicode characters
    """
    # Use RFC 2231 encoding: filename*=UTF-8''encoded_filename
    encoded_filename = quote(filename, safe='')
    return f"filename*=UTF-8''{encoded_filename}"


@router.get("/categories", summary="Get task categories")
async def get_task_categories(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    categories = [
        {"id": "general", "name": "General", "color": "#6c757d"},
        {"id": "development", "name": "Development", "color": "#0d6efd"},
        {"id": "design", "name": "Design", "color": "#6f42c1"},
        {"id": "marketing", "name": "Marketing", "color": "#d63384"},
        {"id": "sales", "name": "Sales", "color": "#fd7e14"},
        {"id": "support", "name": "Support", "color": "#20c997"},
        {"id": "hr", "name": "HR", "color": "#0dcaf0"},
        {"id": "finance", "name": "Finance", "color": "#198754"},
        {"id": "operations", "name": "Operations", "color": "#ffc107"},
        {"id": "admin", "name": "Admin", "color": "#dc3545"},
        {"id": "review", "name": "Review", "color": "#6610f2"},
        {"id": "meeting", "name": "Meeting", "color": "#087990"},
        {"id": "training", "name": "Training", "color": "#e35d6a"},
        {"id": "other", "name": "Other", "color": "#adb5bd"}
    ]

    try:
        distinct_cats = db.query(func.distinct(StaffTask.category)).filter(
            StaffTask.category.isnot(None),
            StaffTask.category != ''
        ).all()
        db_cats = [c[0] for c in distinct_cats if c[0]]
        existing_ids = {cat["id"] for cat in categories}
        for cat_name in db_cats:
            if cat_name.lower() not in existing_ids:
                categories.append({"id": cat_name.lower(), "name": cat_name.title(), "color": "#6c757d"})
    except Exception:
        pass

    return {"success": True, "categories": categories}


@router.get("/assignable-employees", summary="Get ALL active employees for task assignment")
async def get_assignable_employees(
    search: Optional[str] = Query(None, description="Search by name or employee code"),
    limit: int = Query(500, ge=1, le=1000, description="Max results (default 500, max 1000)"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 04, 2025): Get all active employees for task assignment
    
    IMPORTANT: Anyone can assign tasks to anyone - NO hierarchy restrictions
    This endpoint returns ALL active employees regardless of the caller's role.
    
    Used by: Task creation modal, Task editing modal, Team activities, Task tracker
    Returns: List of employees with id, employee_code, full_name, role_name, department
    
    Note: Default limit is 500 employees. For orgs with >500 staff, use the search
    parameter to filter results. Frontend autocomplete requires min 2 chars to search.
    """
    query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(StaffEmployee.full_name).like(search_term),
                func.lower(StaffEmployee.emp_code).like(search_term)
            )
        )
    
    # Get total count before limiting
    total_count = query.count()
    
    # Apply limit (default 500, max 1000 to handle larger orgs)
    employees = query.order_by(StaffEmployee.full_name).limit(limit).all()
    
    return {
        "success": True,
        "employees": [
            {
                "id": emp.id,
                "employee_code": emp.emp_code,
                "full_name": emp.full_name,
                "role_name": emp.role.role_name if emp.role else None,
                "designation": emp.designation,
                "department": emp.department.name if emp.department else None
            }
            for emp in employees
        ],
        "total": len(employees),
        "total_available": total_count,
        "has_more": total_count > len(employees)
    }


def apply_department_scope_to_query(query, current_user, db):
    """
    Apply reporting chain scope filtering to ANY task query
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users see tasks where primary assignee is in their reporting chain
    - The org chart (reporting_manager_id) defines visibility EXCLUSIVELY
    
    CRITICAL: Uses reporting chain to determine accessible employees
    Returns: Modified query with IN filter for reporting chain scope
    """
    from app.utils.staff_hierarchy import get_accessible_employee_ids
    
    # DC Protocol: Get accessible employees based on reporting chain (includes self)
    accessible_employee_ids = get_accessible_employee_ids(
        current_user, db, StaffEmployee, department_id=None
    )
    
    # Filter tasks to those assigned to employees in reporting chain
    query = query.filter(
        StaffTask.primary_assignee_id.in_(accessible_employee_ids)
    )
    
    return query


def verify_manager_task_scope(task: StaffTask, current_user: StaffEmployee, db: Session) -> bool:
    """
    DC Protocol (Dec 04, 2025): Verify user can access task based on reporting chain
    
    PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users can access tasks if primary assignee is in their reporting chain
    - The org chart (reporting_manager_id) defines visibility EXCLUSIVELY
    - Users can always access their own tasks (created by or assigned to them)
    
    Returns True if access is allowed, raises HTTPException otherwise
    """
    from app.utils.staff_hierarchy import get_accessible_employee_ids
    
    # Users can always access tasks created by them
    if task.created_by == current_user.id:
        return True
    
    # Users can always access tasks assigned to them (primary or secondary)
    if task.primary_assignee_id == current_user.id:
        return True
    
    # Check if user is secondary assignee
    is_secondary = db.query(StaffTaskAssignee).filter(
        StaffTaskAssignee.task_id == task.id,
        StaffTaskAssignee.employee_id == current_user.id
    ).first()
    if is_secondary:
        return True
    
    # DC Protocol: Check if task's primary assignee is in user's reporting chain
    accessible_employee_ids = get_accessible_employee_ids(
        current_user, db, StaffEmployee, department_id=None
    )
    
    if task.primary_assignee_id in accessible_employee_ids:
        return True
    
    # Deny access if assignee is not in reporting chain
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only access tasks within your reporting chain"
    )


# ==================== TASK CRUD ====================

@router.post("/", summary="Create new task")
async def create_task(
    task_data: CreateTaskRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a new task
    DC: Anyone can assign tasks to anyone
    WVV: Validate all inputs before creation
    NEW: Support custom assigner for self-assigned tasks
    """
    primary_assignee = db.query(StaffEmployee).filter(
        StaffEmployee.id == task_data.primary_assignee_id,
        StaffEmployee.status == 'active'
    ).first()
    
    if not primary_assignee:
        raise HTTPException(status_code=400, detail="Primary assignee not found or inactive")
    
    for sec_id in task_data.secondary_assignee_ids:
        sec_assignee = db.query(StaffEmployee).filter(
            StaffEmployee.id == sec_id,
            StaffEmployee.status == 'active'
        ).first()
        if not sec_assignee:
            raise HTTPException(status_code=400, detail=f"Secondary assignee {sec_id} not found or inactive")
    
    # WVV: Determine assigner (current user by default)
    assigner_id = current_user.id
    
    # WVV: Log incoming request data for debugging
    print(f"📥 WVV: Task creation request from {current_user.full_name} ({current_user.emp_code})")
    print(f"   Primary Assignee ID: {task_data.primary_assignee_id}")
    print(f"   Custom Assigner ID: {task_data.custom_assigner_id}")
    print(f"   Is Self-Assigned: {task_data.primary_assignee_id == current_user.id}")
    
    # NEW: Handle custom assigner for self-assigned tasks
    if task_data.custom_assigner_id:
        # DC: Custom assigner only allowed for self-assigned tasks
        if task_data.primary_assignee_id != current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Custom assigner only allowed when assigning task to yourself"
            )
        
        # WVV: Validate custom assigner exists and is active
        custom_assigner = db.query(StaffEmployee).filter(
            StaffEmployee.id == task_data.custom_assigner_id,
            StaffEmployee.status == 'active'
        ).first()
        
        if not custom_assigner:
            raise HTTPException(
                status_code=400,
                detail="Custom assigner not found or inactive"
            )
        
        print(f"✅ WVV: Custom assigner validated: {custom_assigner.full_name} ({custom_assigner.emp_code})")
        assigner_id = task_data.custom_assigner_id
    else:
        print(f"✅ WVV: Using current user as assigner: {current_user.full_name} ({current_user.emp_code})")
    
    task_code = generate_task_code(db)
    
    # DC PROTOCOL: original_assigner_id MUST ALWAYS be current_user (immutable audit trail)
    # created_by can be custom assigner (for display), but original_assigner_id preserves truth
    task = StaffTask(
        task_code=task_code,
        title=task_data.title.strip(),
        description=task_data.description.strip() if task_data.description else None,
        category=task_data.category,
        priority=task_data.priority,
        status='pending',
        created_by=assigner_id,  # Display assigner (can be custom)
        original_assigner_id=current_user.id,  # DC: ALWAYS actual creator (immutable)
        primary_assignee_id=task_data.primary_assignee_id,
        due_date=task_data.due_date,
        start_date=task_data.start_date,
        estimated_hours=Decimal(str(task_data.estimated_hours)) if task_data.estimated_hours else None,
        tags=task_data.tags or [],
        contact_phone=task_data.contact_phone.strip() if task_data.contact_phone else None,
        contact_person_name=task_data.contact_person_name.strip() if task_data.contact_person_name else None
    )
    
    db.add(task)
    db.flush()
    
    for sec_id in task_data.secondary_assignee_ids:
        assignee = StaffTaskAssignee(
            task_id=task.id,
            employee_id=sec_id,
            assigned_by=current_user.id,
            role='secondary'
        )
        db.add(assignee)
    
    # DC Protocol (Dec 21, 2025): Multi-Stage Task System - Create phases with auto-generated child tasks
    phases_created = []
    if task_data.phases:
        print(f"📋 WVV: Creating {len(task_data.phases)} phases for task {task_code}")
        for phase_input in task_data.phases:
            # Validate phase assignee exists and is active
            phase_assignee = db.query(StaffEmployee).filter(
                StaffEmployee.id == phase_input.phase_assignee_id,
                StaffEmployee.status == 'active'
            ).first()
            
            if not phase_assignee:
                raise HTTPException(
                    status_code=400,
                    detail=f"Phase assignee {phase_input.phase_assignee_id} not found or inactive"
                )
            
            # Create child task for this phase (appears in assignee's "Assigned To Me")
            child_task_code = generate_task_code(db)
            child_task = StaffTask(
                task_code=child_task_code,
                title=f"[Phase {phase_input.phase_number}] {phase_input.phase_title}",
                description=phase_input.phase_description or f"Sub-task of: {task_data.title.strip()}",
                category=task_data.category,
                priority=task_data.priority,
                status='pending',
                created_by=assigner_id,
                original_assigner_id=current_user.id,
                primary_assignee_id=phase_input.phase_assignee_id,
                due_date=phase_input.target_date,
                start_date=task_data.start_date,
                tags=['phase-task', f'parent-{task_code}']
            )
            db.add(child_task)
            db.flush()
            
            # Create phase record linking parent and child
            phase = StaffTaskPhase(
                parent_task_id=task.id,
                child_task_id=child_task.id,
                phase_number=phase_input.phase_number,
                phase_title=phase_input.phase_title,
                phase_description=phase_input.phase_description,
                phase_assignee_id=phase_input.phase_assignee_id,
                target_date=phase_input.target_date,
                phase_status='pending',
                ordering_token=phase_input.phase_number * 100,
                contact_phone=phase_input.contact_phone.strip() if phase_input.contact_phone else None,
                contact_person_name=phase_input.contact_person_name.strip() if phase_input.contact_person_name else None,
                created_by=current_user.id
            )
            db.add(phase)
            db.flush()
            
            # DC Protocol (Feb 2026): Add secondary assignees to phase child task (max 2)
            phase_sec_names = []
            for sec_id in (phase_input.secondary_phase_assignee_ids or []):
                sec_emp = db.query(StaffEmployee).filter(
                    StaffEmployee.id == sec_id,
                    StaffEmployee.status == 'active'
                ).first()
                if not sec_emp:
                    raise HTTPException(status_code=400, detail=f"Phase secondary assignee {sec_id} not found or inactive")
                phase_sec_assignee = StaffTaskAssignee(
                    task_id=child_task.id,
                    employee_id=sec_id,
                    assigned_by=current_user.id,
                    role='secondary'
                )
                db.add(phase_sec_assignee)
                phase_sec_names.append(sec_emp.full_name)
            
            # Log child task creation
            log_task_activity(
                db=db,
                task_id=child_task.id,
                employee_id=current_user.id,
                action='created',
                details={
                    "title": child_task.title,
                    "phase_number": phase_input.phase_number,
                    "parent_task_id": task.id,
                    "parent_task_code": task_code,
                    "is_phase_task": True,
                    "secondary_assignees": phase_sec_names if phase_sec_names else None
                },
                ip_address=get_client_ip(request)
            )
            
            phases_created.append({
                "phase_number": phase_input.phase_number,
                "phase_title": phase_input.phase_title,
                "assignee_id": phase_input.phase_assignee_id,
                "assignee_name": phase_assignee.full_name,
                "secondary_assignee_ids": phase_input.secondary_phase_assignee_ids or [],
                "secondary_assignee_names": phase_sec_names,
                "child_task_code": child_task_code
            })
            
            sec_info = f" + {', '.join(phase_sec_names)}" if phase_sec_names else ""
            print(f"   ✅ Phase {phase_input.phase_number}: '{phase_input.phase_title}' → {phase_assignee.full_name}{sec_info} (Task: {child_task_code})")
    
    log_task_activity(
        db=db,
        task_id=task.id,
        employee_id=current_user.id,
        action='created',
        details={
            "title": task_data.title,
            "primary_assignee_id": task_data.primary_assignee_id,
            "secondary_assignee_ids": task_data.secondary_assignee_ids,
            "assigner_id": assigner_id,
            "custom_assigner_used": task_data.custom_assigner_id is not None,
            "phases_count": len(phases_created),
            "phases": phases_created if phases_created else None
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(task)
    
    # WVV: Eagerly load relationships for response
    db_task = db.query(StaffTask).options(
        joinedload(StaffTask.creator),
        joinedload(StaffTask.original_assigner),
        joinedload(StaffTask.primary_assignee)
    ).filter(StaffTask.id == task.id).first()
    
    task_dict = db_task.to_dict()
    
    # WVV: Log response data for debugging (DC: Show BOTH display and actual creator)
    print(f"📤 WVV: Task creation response:")
    print(f"   Task Code: {task_dict.get('task_code')}")
    print(f"   Created By (Display): {task_dict.get('creator_name')} (ID: {task_dict.get('created_by')})")
    print(f"   Original Creator (DC Audit): {current_user.full_name} (ID: {task_dict.get('original_assigner_id')})")
    print(f"   Primary Assignee: {primary_assignee.full_name} (ID: {task_data.primary_assignee_id})")
    if task_data.custom_assigner_id:
        print(f"   ⚠️  DC NOTE: Task delegated to {task_dict.get('creator_name')}, actual creator is {current_user.full_name}")
    
    return {
        "success": True,
        "message": "Task created successfully",
        "task": task_dict
    }


@router.get("/", summary="List all tasks")
async def list_tasks(
    status: str = None,
    priority: str = None,
    category: str = None,
    created_by: int = None,
    assignee_id: int = None,
    due_date_from: date = None,
    due_date_to: date = None,
    search: str = None,
    include_deleted: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all tasks with filters
    DC: Department managers see only tasks in their department scope
    """
    # DC FIX: Eagerly load ALL relationships touched by to_dict() to prevent N+1 OOM crashes
    query = db.query(StaffTask).options(
        joinedload(StaffTask.creator),
        joinedload(StaffTask.original_assigner),
        joinedload(StaffTask.primary_assignee),
        subqueryload(StaffTask.secondary_assignees).joinedload(StaffTaskAssignee.employee),
        subqueryload(StaffTask.attachment_files),
        subqueryload(StaffTask.phases).joinedload(StaffTaskPhase.assignee),
        subqueryload(StaffTask.phases).joinedload(StaffTaskPhase.creator)
    )
    
    # DC: Apply department scope filtering FIRST
    query = apply_department_scope_to_query(query, current_user, db)
    
    if not include_deleted:
        query = query.filter(StaffTask.is_deleted == False)
    
    if status:
        query = query.filter(StaffTask.status == status)
    
    if priority:
        query = query.filter(StaffTask.priority == priority)
    
    if category:
        query = query.filter(StaffTask.category == category)
    
    if created_by:
        query = query.filter(StaffTask.created_by == created_by)
    
    if assignee_id:
        secondary_task_ids = db.query(StaffTaskAssignee.task_id).filter(
            StaffTaskAssignee.employee_id == assignee_id
        ).scalar_subquery()
        
        query = query.filter(
            or_(
                StaffTask.primary_assignee_id == assignee_id,
                StaffTask.id.in_(secondary_task_ids)
            )
        )
    
    if due_date_from:
        query = query.filter(StaffTask.due_date >= due_date_from)
    
    if due_date_to:
        query = query.filter(StaffTask.due_date <= due_date_to)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                StaffTask.task_code.ilike(search_term),
                StaffTask.title.ilike(search_term),
                StaffTask.description.ilike(search_term)
            )
        )
    
    total = query.count()
    
    tasks = query.order_by(StaffTask.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "tasks": [t.to_dict() for t in tasks],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@router.get("/assigned-by-me", summary="Tasks assigned by me")
async def tasks_assigned_by_me(
    status: str = None,
    priority: str = None,
    date_filter: str = None,
    category: str = None,
    search: str = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get tasks created/assigned by current user
    DC Protocol (Dec 30, 2025): Tasks where created_by = current user
    NO department scope filtering - users should always see ALL tasks they created
    Supports dynamic date filters: today_pending, tomorrow_pending, next_week_pending, overdue_pending
    """
    # DC FIX: Eagerly load ALL relationships touched by to_dict() to prevent N+1 OOM crashes
    query = db.query(StaffTask).options(
        joinedload(StaffTask.creator),
        joinedload(StaffTask.original_assigner),
        joinedload(StaffTask.primary_assignee),
        subqueryload(StaffTask.secondary_assignees).joinedload(StaffTaskAssignee.employee),
        subqueryload(StaffTask.attachment_files),
        subqueryload(StaffTask.phases).joinedload(StaffTaskPhase.assignee),
        subqueryload(StaffTask.phases).joinedload(StaffTaskPhase.creator)
    ).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.is_deleted == False
    )
    
    # DC Protocol (Dec 30, 2025): NO department scope filtering for "Assigned by Me"
    # Users must see ALL tasks they created, regardless of assignee's department
    
    # Apply date-based filters
    today = get_indian_date()
    if date_filter == 'today_pending':
        query = query.filter(
            StaffTask.due_date == today,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    elif date_filter == 'tomorrow_pending':
        tomorrow = today + timedelta(days=1)
        query = query.filter(
            StaffTask.due_date == tomorrow,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    elif date_filter == 'next_week_pending':
        next_week_end = today + timedelta(days=7)
        query = query.filter(
            StaffTask.due_date > today,
            StaffTask.due_date <= next_week_end,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    elif date_filter == 'overdue_pending':
        query = query.filter(
            StaffTask.due_date < today,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    
    if status:
        query = query.filter(StaffTask.status == status)
    
    if priority:
        query = query.filter(StaffTask.priority == priority)
    
    if category:
        query = query.filter(StaffTask.category == category)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                StaffTask.task_code.ilike(search_term),
                StaffTask.title.ilike(search_term),
                StaffTask.description.ilike(search_term)
            )
        )
    
    total = query.count()
    
    # DC Protocol (Dec 30, 2025): NO department scope for summary counters
    # Users must see accurate counts of ALL tasks they created
    pending_count = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.is_deleted == False,
        StaffTask.status == 'pending'
    ).count()
    
    in_progress_count = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.is_deleted == False,
        StaffTask.status == 'in_progress'
    ).count()
    
    completed_count = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.is_deleted == False,
        StaffTask.status == 'completed'
    ).count()
    
    overdue_count = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.is_deleted == False,
        StaffTask.due_date < get_indian_date(),
        StaffTask.status.notin_(['completed', 'cancelled'])
    ).count()
    
    tasks = query.order_by(StaffTask.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "tasks": [t.to_dict() for t in tasks],
        "total": total,
        "page": page,
        "limit": limit,
        "summary": {
            "total": total,
            "pending": pending_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "overdue": overdue_count
        }
    }


@router.get("/created-by-me", summary="Tasks created by me (alias for assigned-by-me)")
async def tasks_created_by_me(
    status: str = None,
    priority: str = None,
    date_filter: str = None,
    category: str = None,
    search: str = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Dec 06, 2025): Alias route for /assigned-by-me
    Returns tasks where created_by = current user
    Added to fix frontend route mismatch without breaking existing functionality
    """
    return await tasks_assigned_by_me(
        status=status,
        priority=priority,
        date_filter=date_filter,
        category=category,
        search=search,
        page=page,
        limit=limit,
        db=db,
        current_user=current_user
    )


@router.get("/assigned-to-me", summary="Tasks assigned to me")
async def tasks_assigned_to_me(
    status: str = None,
    priority: str = None,
    role: str = None,
    date_filter: str = None,
    category: str = None,
    search: str = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get tasks assigned to current user (primary or secondary)
    DC: Tasks where I am primary_assignee OR in secondary_assignees AND within department scope for managers
    Supports dynamic date filters: today_pending, tomorrow_pending, next_week_pending, overdue_pending
    """
    secondary_task_ids = db.query(StaffTaskAssignee.task_id).filter(
        StaffTaskAssignee.employee_id == current_user.id
    ).scalar_subquery()
    
    # DC FIX: Eagerly load ALL relationships touched by to_dict() to prevent N+1 OOM crashes
    _eager_opts = [
        joinedload(StaffTask.creator),
        joinedload(StaffTask.original_assigner),
        joinedload(StaffTask.primary_assignee),
        subqueryload(StaffTask.secondary_assignees).joinedload(StaffTaskAssignee.employee),
        subqueryload(StaffTask.attachment_files),
        subqueryload(StaffTask.phases).joinedload(StaffTaskPhase.assignee),
        subqueryload(StaffTask.phases).joinedload(StaffTaskPhase.creator)
    ]
    if role == 'primary':
        query = db.query(StaffTask).options(*_eager_opts).filter(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.is_deleted == False
        )
    elif role == 'secondary':
        query = db.query(StaffTask).options(*_eager_opts).filter(
            StaffTask.id.in_(secondary_task_ids),
            StaffTask.is_deleted == False
        )
    else:
        query = db.query(StaffTask).options(*_eager_opts).filter(
            or_(
                StaffTask.primary_assignee_id == current_user.id,
                StaffTask.id.in_(secondary_task_ids)
            ),
            StaffTask.is_deleted == False
        )
    
    # DC: Apply department scope filtering
    query = apply_department_scope_to_query(query, current_user, db)
    
    # Apply date-based filters
    today = get_indian_date()
    if date_filter == 'today_pending':
        query = query.filter(
            StaffTask.due_date == today,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    elif date_filter == 'tomorrow_pending':
        tomorrow = today + timedelta(days=1)
        query = query.filter(
            StaffTask.due_date == tomorrow,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    elif date_filter == 'next_week_pending':
        next_week_end = today + timedelta(days=7)
        query = query.filter(
            StaffTask.due_date > today,
            StaffTask.due_date <= next_week_end,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    elif date_filter == 'overdue_pending':
        query = query.filter(
            StaffTask.due_date < today,
            StaffTask.status.notin_(['completed', 'cancelled'])
        )
    
    if status:
        query = query.filter(StaffTask.status == status)
    
    if priority:
        query = query.filter(StaffTask.priority == priority)
    
    if category:
        query = query.filter(StaffTask.category == category)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                StaffTask.task_code.ilike(search_term),
                StaffTask.title.ilike(search_term),
                StaffTask.description.ilike(search_term)
            )
        )
    
    total = query.count()
    
    # DC: Apply department scope to all summary counters
    pending_query = db.query(StaffTask).filter(
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        ),
        StaffTask.is_deleted == False,
        StaffTask.status == 'pending'
    )
    pending_query = apply_department_scope_to_query(pending_query, current_user, db)
    pending_count = pending_query.count()
    
    in_progress_query = db.query(StaffTask).filter(
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        ),
        StaffTask.is_deleted == False,
        StaffTask.status == 'in_progress'
    )
    in_progress_query = apply_department_scope_to_query(in_progress_query, current_user, db)
    in_progress_count = in_progress_query.count()
    
    completed_query = db.query(StaffTask).filter(
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        ),
        StaffTask.is_deleted == False,
        StaffTask.status == 'completed'
    )
    completed_query = apply_department_scope_to_query(completed_query, current_user, db)
    completed_count = completed_query.count()
    
    overdue_query = db.query(StaffTask).filter(
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        ),
        StaffTask.is_deleted == False,
        StaffTask.due_date < get_indian_date(),
        StaffTask.status.notin_(['completed', 'cancelled'])
    )
    overdue_query = apply_department_scope_to_query(overdue_query, current_user, db)
    overdue_count = overdue_query.count()
    
    tasks = query.order_by(StaffTask.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    tasks_with_role = []
    for task in tasks:
        task_dict = task.to_dict()
        if task.primary_assignee_id == current_user.id:
            task_dict['my_role'] = 'primary'
        else:
            task_dict['my_role'] = 'secondary'
        tasks_with_role.append(task_dict)
    
    return {
        "success": True,
        "tasks": tasks_with_role,
        "total": total,
        "page": page,
        "limit": limit,
        "summary": {
            "total": total,
            "pending": pending_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "overdue": overdue_count
        }
    }


@router.get("/team-activity", summary="Get team activities for managers")
async def get_team_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    employee_id: Optional[int] = Query(None, description="Filter by employee (assignee)"),
    created_by: Optional[int] = Query(None, description="Filter by task creator"),
    sort_by: Optional[str] = Query("priority", description="Column to sort by"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get team activities - Shows all tasks within user's reporting chain
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED HIERARCHY - NO HIERARCHY_LEVEL CHECKS
    - ALL roles use recursive downline via reporting_manager_id chain
    - VGK sees EA's tasks because EA's reporting_manager_id = VGK's ID
    - VGK sees HR's tasks because HR reports to EA who reports to VGK
    - Senior Executive with direct reports sees their team's tasks
    - The org chart (reporting_manager_id) defines visibility EXCLUSIVELY
    - Users with no direct reports see only their own tasks
    """
    from app.models.staff import StaffDepartment
    from app.utils.staff_hierarchy import get_team_member_ids, has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    
    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    accessible_employee_ids = get_team_member_ids(
        current_user, db, StaffEmployee, department_id
    )
    
    # Base query - filter tasks where assignee is in user's reporting chain
    query = db.query(StaffTask).options(
        joinedload(StaffTask.primary_assignee),
        joinedload(StaffTask.creator),
        joinedload(StaffTask.primary_assignee).joinedload(StaffEmployee.department)
    ).filter(
        StaffTask.is_deleted == False
    )
    
    # DC Protocol: Show tasks where primary assignee is in user's downline OR unassigned
    query = query.filter(
        or_(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.primary_assignee_id.is_(None)  # Include unassigned tasks
        )
    )
    
    # Apply filters
    if date_filter_start:
        query = query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        query = query.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        query = query.filter(StaffTask.status == status)
    if priority and priority != 'all':
        query = query.filter(StaffTask.priority == priority)
    if category and category != 'all':
        query = query.filter(StaffTask.category == category)
    
    # Filter by specific employee if provided (must be in accessible list)
    if employee_id:
        if employee_id in accessible_employee_ids:
            query = query.filter(StaffTask.primary_assignee_id == employee_id)
    
    # Filter by task creator if provided (must be in accessible list)
    if created_by:
        if created_by in accessible_employee_ids:
            query = query.filter(StaffTask.created_by == created_by)
    
    # Sorting logic
    today = get_indian_date()
    
    # Whitelist allowed sort columns
    allowed_sort_columns = {
        'task_code': StaffTask.task_code,
        'title': StaffTask.title,
        'status': StaffTask.status,
        'priority': StaffTask.priority,
        'due_date': StaffTask.due_date,
        'created_at': StaffTask.created_at
    }
    
    if sort_by == 'priority':
        # Default: Status-priority sorting (Overdue → Pending → In Progress → Completed)
        query = query.order_by(
            case(
                (and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1),  # Overdue
                (StaffTask.status == 'pending', 2),
                (StaffTask.status == 'in_progress', 3),
                (StaffTask.status == 'completed', 4),
                else_=5
            ),
            StaffTask.created_at.desc()
        )
    elif sort_by in allowed_sort_columns:
        # Column-based sorting
        sort_column = allowed_sort_columns[sort_by]
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
    else:
        # Fallback to default
        query = query.order_by(StaffTask.created_at.desc())
    
    # Use normal pagination with accessible employee filter
    total = query.count()
    tasks = query.offset((page - 1) * limit).limit(limit).all()
    
    # DC Protocol (Jan 07, 2026): OPTIMIZED - Single query to get departments from downline
    # Replaces N+1 loop that was causing production timeouts
    from sqlalchemy import distinct
    available_departments = db.query(StaffDepartment.id, StaffDepartment.name).join(
        StaffEmployee, StaffEmployee.department_id == StaffDepartment.id
    ).filter(
        StaffEmployee.id.in_(accessible_employee_ids),
        StaffDepartment.is_active == True
    ).distinct().all()
    available_departments = [{"id": d.id, "name": d.name} for d in available_departments]
    
    # DC Protocol: Departments derived from user's reporting chain, not their own department only
    
    # DC Protocol (Jan 07, 2026): OPTIMIZED - Batch fetch secondary assignees and attachments
    # Replaces N+1 queries per task that were causing production timeouts
    task_ids = [t.id for t in tasks]
    
    # Batch fetch all secondary assignees for visible tasks
    all_secondary_assignees = {}
    if task_ids:
        secondary_results = db.query(StaffTaskAssignee).options(
            joinedload(StaffTaskAssignee.employee)
        ).filter(
            StaffTaskAssignee.task_id.in_(task_ids)
        ).all()
        for sa in secondary_results:
            if sa.task_id not in all_secondary_assignees:
                all_secondary_assignees[sa.task_id] = []
            all_secondary_assignees[sa.task_id].append(sa)
    
    # Batch fetch all attachments for visible tasks
    all_attachments = {}
    if task_ids:
        attachment_results = db.query(StaffTaskAttachment).filter(
            StaffTaskAttachment.task_id.in_(task_ids)
        ).all()
        for att in attachment_results:
            if att.task_id not in all_attachments:
                all_attachments[att.task_id] = []
            all_attachments[att.task_id].append(att)
    
    # Serialize tasks with enhanced details (WVV: Match "Assigned to Me" pattern)
    task_list = []
    for task in tasks:
        # Check if overdue
        is_overdue = (task.due_date < today and task.status not in ['completed', 'cancelled']) if task.due_date else False
        
        # Get secondary assignees from batch-loaded data
        secondary_assignees = all_secondary_assignees.get(task.id, [])
        
        # Determine viewer's role in this task (PRIMARY/SECONDARY/CREATOR/VIEWER)
        viewer_role = None
        if task.primary_assignee_id == current_user.id:
            viewer_role = "primary"
        elif any(sa.employee_id == current_user.id for sa in secondary_assignees):
            viewer_role = "secondary"
        elif task.created_by == current_user.id:
            viewer_role = "creator"
        else:
            viewer_role = "viewer"
        
        # Determine if user can edit this task
        # DC Protocol: Managers (>=60) can edit tasks in their scope, or if they are assigned/creator
        can_edit = (
            is_manager and (viewer_role in ["primary", "secondary", "creator"]) or
            viewer_role in ["primary", "secondary"]
        )
        
        # Get attachments from batch-loaded data
        attachments = all_attachments.get(task.id, [])
        attachment_data = {
            "count": len(attachments),
            "files": [
                {
                    "id": att.id,
                    "filename": att.file_name,
                    "file_type": att.file_type,
                    "file_size": att.file_size
                } for att in attachments
            ] if attachments else []
        }
        
        # Use to_dict() for consistent serialization, then add team-specific fields
        task_dict = task.to_dict(include_assignees=True, include_comments=False, include_attachments=False)
        
        # Add team-specific enhancements
        task_dict.update({
            "is_overdue": is_overdue,
            "viewer_role": viewer_role,
            "can_edit": can_edit,
            "attachments": attachment_data,
            "secondary_assignees_count": len(secondary_assignees),
            "secondary_assignees": [
                {
                    "id": sa.employee.id,
                    "emp_code": sa.employee.emp_code,
                    "full_name": sa.employee.full_name
                } for sa in secondary_assignees if sa.employee
            ] if secondary_assignees else [],
            "assigned_date": task.created_at.isoformat() if task.created_at else None,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours else 0
        })
        
        task_list.append(task_dict)
    
    # Calculate summary statistics
    summary_stats = {
        "total": total,
        "pending": sum(1 for t in task_list if t.get("status") == "pending"),
        "in_progress": sum(1 for t in task_list if t.get("status") == "in_progress"),
        "completed": sum(1 for t in task_list if t.get("status") == "completed"),
        "overdue": sum(1 for t in task_list if t.get("is_overdue") == True)
    }
    
    # DC Protocol: Get hierarchy_level for access_level label ONLY (not for filtering)
    # Data visibility is controlled by get_accessible_employee_ids() via reporting_manager chain
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    # Determine access level label based on hierarchy
    if hierarchy_level >= 85:
        access_level = "supreme"
    elif hierarchy_level >= 75:
        access_level = "ea"
    else:
        access_level = "manager"
    
    return {
        "success": True,
        "is_manager": is_manager,
        "access_level": access_level,
        "hierarchy_level": hierarchy_level,
        "available_departments": available_departments,
        "tasks": task_list,
        "summary": summary_stats,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "priority": priority,
            "category": category,
            "department_id": department_id,
            "employee_id": employee_id,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
    }


# ==================== FILE ATTACHMENTS ====================

# DC: Use absolute path from project root
# File location: /home/runner/workspace/backend/app/api/v1/endpoints/staff_tasks.py
# Project root: /home/runner/workspace (6 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "frontend" / "storage" / "task_attachments"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# DC: Separate directory for comment attachments
COMMENT_UPLOAD_DIR = PROJECT_ROOT / "frontend" / "storage" / "comment_attachments"
COMMENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff',
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain'
}

# NEW: Differentiated size limits (WVV: Architect-mandated validation)
# UPDATED Nov 29, 2025: Align with Universal Upload System (5MB for all files)
IMAGE_MIME_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB for images (will be auto-compressed)
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB for documents (aligned with frontend)

MAX_FILES_PER_TASK_CREATE = 2  # Limit during task creation
MAX_FILES_PER_TASK_EDIT = 20  # DC: Reasonable upper limit during edit mode to prevent storage exhaustion


@router.get("/{task_id}", summary="Get task details")
async def get_task(
    task_id: int,
    include_comments: bool = True,
    include_activity: bool = True,
    include_time_entries: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get complete task details including comments and activity log
    DC: Everyone can view task details
    """
    # WVV FIX: Eagerly load all relationships to prevent None values in to_dict()
    task = db.query(StaffTask).options(
        joinedload(StaffTask.creator),
        joinedload(StaffTask.original_assigner),
        joinedload(StaffTask.primary_assignee)
    ).filter(StaffTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    result = task.to_dict(include_comments=include_comments)
    
    if include_activity:
        activities = db.query(StaffTaskActivityLog).filter(
            StaffTaskActivityLog.task_id == task_id
        ).order_by(StaffTaskActivityLog.created_at.desc()).limit(50).all()
        result['activity_log'] = [a.to_dict() for a in activities]
    
    if include_time_entries:
        time_entries = db.query(StaffTaskTimeEntry).filter(
            StaffTaskTimeEntry.task_id == task_id
        ).order_by(StaffTaskTimeEntry.date.desc()).all()
        result['time_entries'] = [t.to_dict() for t in time_entries]
        result['total_logged_hours'] = sum(float(t.hours) for t in time_entries)
    
    return {
        "success": True,
        "task": result
    }


@router.put("/{task_id}", summary="Update task")
async def update_task(
    task_id: int,
    update_data: UpdateTaskRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update task details
    DC: Creator OR assignees can update
    WVV: Validate changes before applying
    """
    # WVV FIX: Eagerly load all relationships to prevent None values in to_dict()
    task = db.query(StaffTask).options(
        joinedload(StaffTask.creator),
        joinedload(StaffTask.original_assigner),
        joinedload(StaffTask.primary_assignee)
    ).filter(StaffTask.id == task_id, StaffTask.is_deleted == False).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    is_assignee = task.created_by == current_user.id or task.primary_assignee_id == current_user.id
    if not is_assignee:
        secondary = db.query(StaffTaskAssignee).filter(
            StaffTaskAssignee.task_id == task_id,
            StaffTaskAssignee.employee_id == current_user.id
        ).first()
        is_assignee = secondary is not None
    
    if not is_assignee:
        raise HTTPException(status_code=403, detail="Only creator or assignees can update task")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    if task.status == 'completed':
        raise HTTPException(status_code=400, detail="Cannot update completed task. Reopen it first.")

    # Store system tasks are read-only (non-editable per DC Protocol)
    if 'store-system' in (task.tags or []):
        raise HTTPException(
            status_code=403,
            detail="This is a system-managed store task and cannot be edited manually."
        )

    changes = {}
    
    if update_data.title is not None and update_data.title != task.title:
        changes['title'] = {'old': task.title, 'new': update_data.title.strip()}
        task.title = update_data.title.strip()
    
    if update_data.description is not None and update_data.description != task.description:
        changes['description'] = {'old': task.description, 'new': update_data.description}
        task.description = update_data.description
    
    if update_data.category is not None and update_data.category != task.category:
        changes['category'] = {'old': task.category, 'new': update_data.category}
        task.category = update_data.category
    
    if update_data.priority is not None and update_data.priority != task.priority:
        changes['priority'] = {'old': task.priority, 'new': update_data.priority}
        task.priority = update_data.priority
    
    if update_data.status is not None and update_data.status != task.status:
        changes['status'] = {'old': task.status, 'new': update_data.status}
        old_status = task.status
        task.status = update_data.status
        # DC Protocol (Dec 21, 2025): Sync phase status if this is a child task
        sync_phase_from_child_task(db, task.id, update_data.status, current_user.id)
    
    if update_data.progress is not None and update_data.progress != task.progress:
        changes['progress'] = {'old': task.progress, 'new': update_data.progress}
        task.progress = update_data.progress
    
    if update_data.due_date is not None:
        old_due = task.due_date.isoformat() if task.due_date else None
        changes['due_date'] = {'old': old_due, 'new': str(update_data.due_date)}
        task.due_date = update_data.due_date
    
    if update_data.start_date is not None:
        old_start = task.start_date.isoformat() if task.start_date else None
        changes['start_date'] = {'old': old_start, 'new': str(update_data.start_date)}
        task.start_date = update_data.start_date
    
    if update_data.estimated_hours is not None:
        old_est = float(task.estimated_hours) if task.estimated_hours else None
        changes['estimated_hours'] = {'old': old_est, 'new': update_data.estimated_hours}
        task.estimated_hours = Decimal(str(update_data.estimated_hours))
    
    if update_data.tags is not None:
        changes['tags'] = {'old': task.tags, 'new': update_data.tags}
        task.tags = update_data.tags
    
    if update_data.contact_phone is not None:
        old_phone = task.contact_phone
        new_phone = update_data.contact_phone.strip() if update_data.contact_phone else None
        if old_phone != new_phone:
            changes['contact_phone'] = {'old': old_phone, 'new': new_phone}
            task.contact_phone = new_phone
    
    if update_data.contact_person_name is not None:
        old_name = task.contact_person_name
        new_name = update_data.contact_person_name.strip() if update_data.contact_person_name else None
        if old_name != new_name:
            changes['contact_person_name'] = {'old': old_name, 'new': new_name}
            task.contact_person_name = new_name
    
    # DC Protocol (Feb 2026): Handle secondary assignee updates during task edit
    if update_data.secondary_assignee_ids is not None:
        new_sec_ids = set(update_data.secondary_assignee_ids)
        
        # WVV: Ensure primary assignee is not in secondary list
        if task.primary_assignee_id in new_sec_ids:
            raise HTTPException(status_code=400, detail="Primary assignee cannot be a secondary assignee")
        
        # Get current secondary assignees
        current_secondaries = db.query(StaffTaskAssignee).filter(
            StaffTaskAssignee.task_id == task_id
        ).all()
        current_sec_ids = {sa.employee_id for sa in current_secondaries}
        
        # Determine additions and removals
        to_add = new_sec_ids - current_sec_ids
        to_remove = current_sec_ids - new_sec_ids
        
        # Validate all new assignees exist and are active
        for sec_id in to_add:
            emp = db.query(StaffEmployee).filter(
                StaffEmployee.id == sec_id,
                StaffEmployee.status == 'active'
            ).first()
            if not emp:
                raise HTTPException(status_code=400, detail=f"Secondary assignee {sec_id} not found or inactive")
        
        # Remove old assignees
        for sec_id in to_remove:
            existing = db.query(StaffTaskAssignee).filter(
                StaffTaskAssignee.task_id == task_id,
                StaffTaskAssignee.employee_id == sec_id
            ).first()
            if existing:
                removed_emp = db.query(StaffEmployee).filter(StaffEmployee.id == sec_id).first()
                db.delete(existing)
                log_task_activity(
                    db=db, task_id=task.id, employee_id=current_user.id,
                    action='removed_assignee',
                    details={"removed_employee_id": sec_id, "removed_employee_name": removed_emp.full_name if removed_emp else str(sec_id)},
                    ip_address=get_client_ip(request)
                )
        
        # Add new assignees
        for sec_id in to_add:
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == sec_id).first()
            new_assignee_rec = StaffTaskAssignee(
                task_id=task_id,
                employee_id=sec_id,
                assigned_by=current_user.id,
                role='secondary'
            )
            db.add(new_assignee_rec)
            log_task_activity(
                db=db, task_id=task.id, employee_id=current_user.id,
                action='assigned',
                details={"added_employee_id": sec_id, "added_employee_name": emp.full_name if emp else str(sec_id)},
                ip_address=get_client_ip(request)
            )
        
        if to_add or to_remove:
            changes['secondary_assignees'] = {
                'added': list(to_add),
                'removed': list(to_remove)
            }
    
    # NEW: Handle assigner update for self-assigned tasks
    if update_data.new_assigner_id is not None:
        # DC: Can only change assigner for self-assigned tasks
        if task.primary_assignee_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Can only update assigner for tasks assigned to you"
            )
        
        # WVV: Validate new assigner exists and is active
        new_assigner = db.query(StaffEmployee).filter(
            StaffEmployee.id == update_data.new_assigner_id,
            StaffEmployee.status == 'active'
        ).first()
        
        if not new_assigner:
            raise HTTPException(
                status_code=400,
                detail="New assigner not found or inactive"
            )
        
        # DC: Capture old value BEFORE mutation (critical for audit trail)
        old_created_by = task.created_by
        # CRITICAL: Must access relationship BEFORE mutation to avoid lazy-load issue
        old_creator = task.creator
        old_assigner_name = old_creator.full_name if old_creator else None
        
        # Update assigner (original_assigner_id remains immutable)
        task.created_by = update_data.new_assigner_id
        
        # DC: Log the assigner change separately with detailed audit trail
        log_task_activity(
            db=db,
            task_id=task.id,
            employee_id=current_user.id,
            action='assigner_updated',
            field_changed='created_by',
            old_value=str(old_created_by),
            new_value=str(update_data.new_assigner_id),
            details={
                "changed_by_emp_code": current_user.emp_code,
                "old_assigner_name": old_assigner_name,
                "new_assigner_name": new_assigner.full_name,
                "reason": "assigner_update_for_self_assigned_task"
            },
            ip_address=get_client_ip(request)
        )
        
        # Track change for generic update log
        changes['created_by'] = {
            'old': old_created_by,
            'new': update_data.new_assigner_id
        }
    
    if changes:
        log_task_activity(
            db=db,
            task_id=task.id,
            employee_id=current_user.id,
            action='updated',
            details=changes,
            ip_address=get_client_ip(request)
        )
        
        if update_data.time_taken_minutes and update_data.time_taken_minutes > 0:
            from app.services.activity_time_service import log_activity_time
            try:
                log_activity_time(
                    db=db,
                    employee_id=current_user.id,
                    source_type='task',
                    completed_minutes=update_data.time_taken_minutes,
                    source_id=task.id,
                    source_title=task.title,
                    description=f"Task update: {', '.join(changes.keys())}",
                    ip_address=get_client_ip(request),
                    user_agent=request.headers.get("User-Agent", "")[:500] if request else "",
                    created_by=current_user.id
                )
            except Exception as e:
                print(f"[DC-WARN] Activity time log failed for task update {task.id}: {e}")
        
        db.commit()
        db.refresh(task)
    
    return {
        "success": True,
        "message": "Task updated successfully",
        "task": task.to_dict()
    }


@router.put("/{task_id}/status", summary="Update task status")
async def update_task_status(
    task_id: int,
    status_data: UpdateTaskStatusRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update task status
    DC: Assignees can update status
    WVV: Validate status transitions
    """
    task = db.query(StaffTask).filter(StaffTask.id == task_id, StaffTask.is_deleted == False).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = status_data.status
    completion_notes = status_data.notes
    
    is_assignee = task.primary_assignee_id == current_user.id
    if not is_assignee:
        secondary = db.query(StaffTaskAssignee).filter(
            StaffTaskAssignee.task_id == task_id,
            StaffTaskAssignee.employee_id == current_user.id
        ).first()
        is_assignee = secondary is not None
    
    is_creator = task.created_by == current_user.id
    
    if not is_assignee and not is_creator:
        raise HTTPException(status_code=403, detail="Only creator or assignees can update status")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    old_status = task.status
    task.status = status
    
    if status == 'completed':
        task.completed_at = get_indian_time()
        if completion_notes:
            task.completion_notes = completion_notes
        action = 'completed'
    elif old_status == 'completed' and status != 'completed':
        task.completed_at = None
        action = 'reopened'
    elif status == 'cancelled':
        action = 'cancelled'
    else:
        action = 'status_changed'
    
    log_task_activity(
        db=db,
        task_id=task.id,
        employee_id=current_user.id,
        action=action,
        field_changed='status',
        old_value=old_status,
        new_value=status,
        ip_address=get_client_ip(request)
    )
    
    # DC Protocol (Dec 21, 2025): Sync phase status if this is a child task
    sync_phase_from_child_task(db, task.id, status, current_user.id)
    
    if status_data.time_taken_minutes and status_data.time_taken_minutes > 0:
        from app.services.activity_time_service import log_activity_time
        try:
            log_activity_time(
                db=db,
                employee_id=current_user.id,
                source_type='task',
                completed_minutes=status_data.time_taken_minutes,
                source_id=task.id,
                source_title=task.title,
                description=f"Task status: {old_status} → {status}",
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:500] if request else "",
                created_by=current_user.id
            )
        except Exception as e:
            print(f"[DC-WARN] Activity time log failed for task {task.id}: {e}")
    
    db.commit()
    db.refresh(task)
    
    return {
        "success": True,
        "message": f"Task status updated to {status}",
        "task": task.to_dict()
    }


# ==================== ASSIGNMENT MANAGEMENT ====================

@router.post("/{task_id}/invite", summary="Invite/Add secondary assignee")
async def invite_assignee(
    task_id: int,
    invite_data: AddSecondaryAssigneeRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Invite/Add a secondary assignee to a running task
    DC: Anyone can invite others to a task
    WVV: Max 2 secondary assignees
    """
    employee_id = invite_data.employee_id
    
    task = db.query(StaffTask).filter(StaffTask.id == task_id, StaffTask.is_deleted == False).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    if task.status in ['completed', 'cancelled']:
        raise HTTPException(status_code=400, detail="Cannot add assignees to completed or cancelled tasks")
    
    if employee_id == task.primary_assignee_id:
        raise HTTPException(status_code=400, detail="This person is already the primary assignee")
    
    existing = db.query(StaffTaskAssignee).filter(
        StaffTaskAssignee.task_id == task_id,
        StaffTaskAssignee.employee_id == employee_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="This person is already assigned to this task")
    
    current_count = db.query(StaffTaskAssignee).filter(
        StaffTaskAssignee.task_id == task_id
    ).count()
    
    if current_count >= 2:
        raise HTTPException(status_code=400, detail="Maximum 2 secondary assignees allowed")
    
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id,
        StaffEmployee.status == 'active'
    ).first()
    
    if not employee:
        raise HTTPException(status_code=400, detail="Employee not found or inactive")
    
    # DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    # Users can only invite employees in their reporting chain
    from app.utils.staff_hierarchy import get_accessible_employee_ids
    accessible_employee_ids = get_accessible_employee_ids(
        current_user, db, StaffEmployee, department_id=None
    )
    
    if employee.id not in accessible_employee_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only invite employees within your reporting chain"
        )
    
    assignee = StaffTaskAssignee(
        task_id=task_id,
        employee_id=employee_id,
        assigned_by=current_user.id,
        role='invited'
    )
    db.add(assignee)
    
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='invited',
        details={
            "invited_employee_id": employee_id,
            "invited_employee_name": employee.full_name
        },
        ip_address=get_client_ip(request)
    )
    
    comment = StaffTaskComment(
        task_id=task_id,
        employee_id=current_user.id,
        comment=f"Invited {employee.full_name} to this task",
        is_system_comment=True
    )
    db.add(comment)
    
    db.commit()
    db.refresh(task)
    
    return {
        "success": True,
        "message": f"{employee.full_name} has been invited to this task",
        "task": task.to_dict()
    }


@router.post("/{task_id}/reassign", summary="Reassign primary assignee")
async def reassign_task(
    task_id: int,
    reassign_data: ReassignPrimaryRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reassign primary assignee
    DC: Anyone can reassign tasks
    WVV: New assignee must be active employee
    """
    new_primary_id = reassign_data.new_primary_id
    
    task = db.query(StaffTask).filter(StaffTask.id == task_id, StaffTask.is_deleted == False).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in ['completed', 'cancelled']:
        raise HTTPException(status_code=400, detail="Cannot reassign completed or cancelled tasks")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    if new_primary_id == task.primary_assignee_id:
        raise HTTPException(status_code=400, detail="This person is already the primary assignee")
    
    new_assignee = db.query(StaffEmployee).filter(
        StaffEmployee.id == new_primary_id,
        StaffEmployee.status == 'active'
    ).first()
    
    if not new_assignee:
        raise HTTPException(status_code=400, detail="New assignee not found or inactive")
    
    # DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    # Users can only reassign to employees in their reporting chain
    from app.utils.staff_hierarchy import get_accessible_employee_ids
    accessible_employee_ids = get_accessible_employee_ids(
        current_user, db, StaffEmployee, department_id=None
    )
    
    if new_assignee.id not in accessible_employee_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reassign tasks to employees within your reporting chain"
        )
    
    old_assignee_id = task.primary_assignee_id
    old_assignee = task.primary_assignee
    
    existing_secondary = db.query(StaffTaskAssignee).filter(
        StaffTaskAssignee.task_id == task_id,
        StaffTaskAssignee.employee_id == new_primary_id
    ).first()
    
    if existing_secondary:
        db.delete(existing_secondary)
    
    task.primary_assignee_id = new_primary_id
    
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='reassigned',
        field_changed='primary_assignee',
        old_value=old_assignee.full_name if old_assignee else str(old_assignee_id),
        new_value=new_assignee.full_name,
        ip_address=get_client_ip(request)
    )
    
    comment = StaffTaskComment(
        task_id=task_id,
        employee_id=current_user.id,
        comment=f"Reassigned task from {old_assignee.full_name if old_assignee else 'Unknown'} to {new_assignee.full_name}",
        is_system_comment=True
    )
    db.add(comment)
    
    db.commit()
    db.refresh(task)
    
    return {
        "success": True,
        "message": f"Task reassigned to {new_assignee.full_name}",
        "task": task.to_dict()
    }


@router.delete("/{task_id}/assignee/{employee_id}", summary="Remove secondary assignee")
async def remove_assignee(
    request: Request,
    task_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Remove a secondary assignee from task
    DC: Creator or assignee being removed can do this
    """
    task = db.query(StaffTask).filter(StaffTask.id == task_id, StaffTask.is_deleted == False).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    assignee = db.query(StaffTaskAssignee).filter(
        StaffTaskAssignee.task_id == task_id,
        StaffTaskAssignee.employee_id == employee_id
    ).first()
    
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found on this task")
    
    removed_name = assignee.employee.full_name if assignee.employee else "Unknown"
    
    db.delete(assignee)
    
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='removed_assignee',
        details={"removed_employee_id": employee_id, "removed_name": removed_name},
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"{removed_name} removed from task"
    }


# ==================== COMMENTS ====================

@router.post("/{task_id}/comments", summary="Add comment with optional file attachment")
async def add_comment(
    request: Request,
    task_id: int,
    content: str = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Add a comment to a task with optional file attachment
    DC: Anyone can comment on any task
    WVV: Comments are immutable (cannot be deleted)
    STF: Optional file upload (1 file per comment, max 500KB, 15 formats supported)
    Formats: PNG, JPEG, GIF, WebP, BMP, TIFF, PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, ZIP
    """
    # VERIFY: Task exists
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    # VERIFY: Content or file must be provided
    if not content and not file:
        raise HTTPException(status_code=400, detail="Comment text or file attachment is required")
    
    attachments = []
    
    # WVV: Validate and save file if provided
    if file and file.filename:
        # VERIFY: Check file type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file.content_type}' not allowed. Allowed: PNG, JPEG, GIF, WebP, BMP, TIFF, PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, ZIP"
            )
        
        # VERIFY: Check file size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size (500KB)"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # DC Protocol: Upload file to Object Storage
        from app.services.object_storage import storage_service
        
        file_extension = Path(file.filename).suffix
        unique_filename = f"comment_{task_id}_{uuid.uuid4().hex}{file_extension}"
        storage_path = f"comment_attachments/{unique_filename}"
        
        success = storage_service.upload_file(storage_path, file_content)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload attachment to storage")
        
        # DC: Store attachment metadata in JSONB with Object Storage path
        attachments.append({
            "filename": file.filename,
            "stored_filename": unique_filename,
            "file_path": f"/storage/{storage_path}",
            "storage_path": storage_path,
            "file_type": file.content_type,
            "file_size": file_size,
            "uploaded_at": get_indian_time().isoformat()
        })
    
    # WRITE: Create comment
    new_comment = StaffTaskComment(
        task_id=task_id,
        employee_id=current_user.id,
        comment=(content or "").strip() if content else "",
        attachments=attachments,
        is_system_comment=False
    )
    db.add(new_comment)
    
    # WRITE: Log activity
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='commented',
        details={"has_attachment": len(attachments) > 0},
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(new_comment)
    
    return {
        "success": True,
        "message": "Comment added" + (" with attachment" if attachments else ""),
        "comment": new_comment.to_dict()
    }


@router.get("/{task_id}/comments", summary="Get task comments")
async def get_comments(
    task_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get all comments for a task"""
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    query = db.query(StaffTaskComment).filter(StaffTaskComment.task_id == task_id)
    total = query.count()
    
    comments = query.order_by(StaffTaskComment.created_at.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "comments": [c.to_dict() for c in comments],
        "total": total,
        "page": page
    }


@router.get("/comments/{comment_id}/attachment/{filename}", summary="Download comment attachment")
async def download_comment_attachment(
    comment_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Download a comment attachment
    DC: Department scope enforced - verify access to parent task
    """
    # VERIFY: Comment exists
    comment = db.query(StaffTaskComment).filter(StaffTaskComment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # DC: Verify manager department scope via parent task
    task = db.query(StaffTask).filter(StaffTask.id == comment.task_id).first()
    if task:
        verify_manager_task_scope(task, current_user, db)
    
    # VERIFY: File exists in comment attachments
    if not comment.attachments or len(comment.attachments) == 0:
        raise HTTPException(status_code=404, detail="No attachments found for this comment")
    
    # VERIFY: Find the specific attachment
    attachment = None
    for att in comment.attachments:
        if att.get("stored_filename") == filename:
            attachment = att
            break
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # DC Protocol: Try Object Storage first (new uploads)
    from app.services.object_storage import storage_service
    from fastapi.responses import StreamingResponse
    import io
    
    storage_path = attachment.get("storage_path") or f"comment_attachments/{filename}"
    file_data = storage_service.download_file(storage_path)
    
    if file_data:
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=attachment.get("file_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{attachment.get("filename", filename)}"'
            }
        )
    
    # Fallback: Try local storage (legacy files)
    file_path = COMMENT_UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            filename=attachment.get("filename", filename),
            media_type=attachment.get("file_type", "application/octet-stream")
        )
    
    raise HTTPException(status_code=404, detail="File not found")


# ==================== TIME ENTRIES ====================

@router.post("/{task_id}/time-entry", summary="Log time spent")
async def log_time_entry(
    task_id: int,
    time_data: LogTimeRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Log time spent on a task
    DC: Only assignees can log time
    WVV: Validate hours > 0 and <= 24
    """
    task = db.query(StaffTask).filter(StaffTask.id == task_id, StaffTask.is_deleted == False).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    is_assignee = task.primary_assignee_id == current_user.id
    if not is_assignee:
        secondary = db.query(StaffTaskAssignee).filter(
            StaffTaskAssignee.task_id == task_id,
            StaffTaskAssignee.employee_id == current_user.id
        ).first()
        is_assignee = secondary is not None
    
    if not is_assignee:
        raise HTTPException(status_code=403, detail="Only assignees can log time")
    
    hours = time_data.hours
    work_date = time_data.work_date
    description = time_data.notes
    
    time_entry = StaffTaskTimeEntry(
        task_id=task_id,
        employee_id=current_user.id,
        date=work_date,
        hours=Decimal(str(hours)),
        description=description
    )
    db.add(time_entry)
    
    total_hours = db.query(func.sum(StaffTaskTimeEntry.hours)).filter(
        StaffTaskTimeEntry.task_id == task_id
    ).scalar() or 0
    
    task.actual_hours = Decimal(str(float(total_hours) + hours))
    
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='time_logged',
        details={"hours": hours, "date": work_date.isoformat()},
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(time_entry)
    
    return {
        "success": True,
        "message": f"Logged {hours} hours",
        "time_entry": time_entry.to_dict(),
        "task_total_hours": float(task.actual_hours or 0)
    }


# ==================== ANALYTICS ====================

@router.get("/analytics/summary", summary="Get task analytics summary")
async def get_analytics_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get overall task analytics summary
    DC: Available to all employees
    """
    start_date = get_indian_date() - timedelta(days=days)
    
    total_tasks = db.query(StaffTask).filter(StaffTask.is_deleted == False).count()
    
    status_counts = db.query(
        StaffTask.status,
        func.count(StaffTask.id)
    ).filter(
        StaffTask.is_deleted == False
    ).group_by(StaffTask.status).all()
    
    status_summary = {s[0]: s[1] for s in status_counts}
    
    priority_counts = db.query(
        StaffTask.priority,
        func.count(StaffTask.id)
    ).filter(
        StaffTask.is_deleted == False
    ).group_by(StaffTask.priority).all()
    
    priority_summary = {p[0]: p[1] for p in priority_counts}
    
    category_counts = db.query(
        StaffTask.category,
        func.count(StaffTask.id)
    ).filter(
        StaffTask.is_deleted == False
    ).group_by(StaffTask.category).all()
    
    category_summary = {c[0]: c[1] for c in category_counts}
    
    overdue_count = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        StaffTask.due_date < get_indian_date(),
        StaffTask.status.notin_(['completed', 'cancelled'])
    ).count()
    
    completed_in_period = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        StaffTask.status == 'completed',
        StaffTask.completed_at >= start_date
    ).count()
    
    created_in_period = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        StaffTask.created_at >= start_date
    ).count()
    
    total_time_logged = db.query(func.sum(StaffTaskTimeEntry.hours)).scalar() or 0
    
    return {
        "success": True,
        "period_days": days,
        "summary": {
            "total_tasks": total_tasks,
            "by_status": status_summary,
            "by_priority": priority_summary,
            "by_category": category_summary,
            "overdue": overdue_count,
            "completed_in_period": completed_in_period,
            "created_in_period": created_in_period,
            "total_hours_logged": float(total_time_logged)
        }
    }


@router.get("/analytics/by-employee", summary="Get tasks by employee")
async def get_analytics_by_employee(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get task distribution by employee
    DC: Shows workload per employee, excludes self and hidden accounts from team views
    """
    from app.utils.staff_hierarchy import get_team_member_ids
    team_ids = get_team_member_ids(current_user, db, StaffEmployee)
    employees = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.id.in_(team_ids)
    ).all()
    
    employee_stats = []
    
    for emp in employees:
        secondary_task_ids = db.query(StaffTaskAssignee.task_id).filter(
            StaffTaskAssignee.employee_id == emp.id
        ).scalar_subquery()
        
        as_primary = db.query(StaffTask).filter(
            StaffTask.primary_assignee_id == emp.id,
            StaffTask.is_deleted == False
        ).count()
        
        as_secondary = db.query(StaffTask).filter(
            StaffTask.id.in_(secondary_task_ids),
            StaffTask.is_deleted == False
        ).count()
        
        completed = db.query(StaffTask).filter(
            or_(
                StaffTask.primary_assignee_id == emp.id,
                StaffTask.id.in_(secondary_task_ids)
            ),
            StaffTask.is_deleted == False,
            StaffTask.status == 'completed'
        ).count()
        
        pending = db.query(StaffTask).filter(
            or_(
                StaffTask.primary_assignee_id == emp.id,
                StaffTask.id.in_(secondary_task_ids)
            ),
            StaffTask.is_deleted == False,
            StaffTask.status.in_(['pending', 'in_progress'])
        ).count()
        
        hours_logged = db.query(func.sum(StaffTaskTimeEntry.hours)).filter(
            StaffTaskTimeEntry.employee_id == emp.id
        ).scalar() or 0
        
        employee_stats.append({
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "employee_code": emp.emp_code,
            "department": emp.department.name if emp.department else None,
            "as_primary": as_primary,
            "as_secondary": as_secondary,
            "total_assigned": as_primary + as_secondary,
            "completed": completed,
            "pending": pending,
            "hours_logged": float(hours_logged),
            "workload_score": as_primary + (as_secondary * 0.5)
        })
    
    employee_stats.sort(key=lambda x: x['workload_score'], reverse=True)
    
    return {
        "success": True,
        "employees": employee_stats
    }


@router.get("/analytics/overdue", summary="Get overdue tasks")
async def get_overdue_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all overdue tasks
    DC: Tasks past due date that are not completed/cancelled
    """
    query = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        StaffTask.due_date < get_indian_date(),
        StaffTask.status.notin_(['completed', 'cancelled'])
    )
    
    total = query.count()
    
    tasks = query.order_by(StaffTask.due_date.asc()).offset((page - 1) * limit).limit(limit).all()
    
    overdue_tasks = []
    today = get_indian_date()
    for task in tasks:
        task_dict = task.to_dict()
        task_dict['days_overdue'] = (today - task.due_date).days
        overdue_tasks.append(task_dict)
    
    return {
        "success": True,
        "tasks": overdue_tasks,
        "total": total,
        "page": page
    }


@router.get("/analytics/department-summary", summary="Get department-wise task summary")
async def get_department_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get department-wise task summary for tasks assigned by current user
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - This endpoint shows tasks CREATED BY the user, grouped by department
    - No hierarchy check needed - every user sees their own created tasks
    """
    from app.models.staff import StaffDepartment
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: is_manager based on having direct reports, not role level
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    
    # Parse date filters
    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # DC Protocol Fix (Dec 04, 2025): "ASSIGNED BY ME" must ALWAYS filter by created_by
    # Manager privilege only expands which departments they can SEE, not remove assignment attribution
    # Previous bug: Managers lost created_by filter, showing empty data for their assigned tasks
    base_query = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.is_deleted == False
    )
    
    # Apply filters (including date filters)
    if date_filter_start:
        base_query = base_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        base_query = base_query.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        base_query = base_query.filter(StaffTask.status == status)
    if priority and priority != 'all':
        base_query = base_query.filter(StaffTask.priority == priority)
    if category and category != 'all':
        base_query = base_query.filter(StaffTask.category == category)
    
    # Get all departments (or filtered if department_id provided)
    if department_id:
        departments = db.query(StaffDepartment).filter(StaffDepartment.id == department_id).all()
    else:
        departments = db.query(StaffDepartment).all()
    
    today = get_indian_date()
    department_summaries = []
    
    for dept in departments:
        # Get tasks where primary assignee belongs to this department (with ALL filters)
        dept_tasks_query = base_query.join(
            StaffEmployee,
            StaffTask.primary_assignee_id == StaffEmployee.id
        ).filter(StaffEmployee.department_id == dept.id)
        
        total = dept_tasks_query.count()
        
        # Skip departments with no tasks (unless user explicitly filters by department)
        if total == 0 and not department_id:
            continue
        
        completed = dept_tasks_query.filter(StaffTask.status == 'completed').count()
        in_progress = dept_tasks_query.filter(StaffTask.status == 'in_progress').count()
        pending = dept_tasks_query.filter(StaffTask.status == 'pending').count()
        overdue = dept_tasks_query.filter(
            StaffTask.due_date < today,
            StaffTask.status.notin_(['completed', 'cancelled'])
        ).count()
        
        # New Tasks Assigned: Count tasks created in date range (ignore status/priority/category filters)
        # Build separate query with ONLY date filters for this metric
        # DC Protocol Fix (Dec 04, 2025): ALWAYS filter by created_by for "ASSIGNED BY ME" semantics
        new_tasks_query = db.query(StaffTask).filter(
            StaffTask.created_by == current_user.id,
            StaffTask.is_deleted == False
        )
        
        # Apply ONLY date filters (no status/priority/category)
        if date_filter_start:
            new_tasks_query = new_tasks_query.filter(StaffTask.created_at >= date_filter_start)
        if date_filter_end:
            new_tasks_query = new_tasks_query.filter(StaffTask.created_at <= date_filter_end)
        
        # Filter by department
        dept_new_tasks_query = new_tasks_query.join(
            StaffEmployee,
            StaffTask.primary_assignee_id == StaffEmployee.id
        ).filter(StaffEmployee.department_id == dept.id)
        
        new_tasks_assigned = dept_new_tasks_query.count()
        
        department_summaries.append({
            "department_id": dept.id,
            "department_name": dept.name,
            "total": total,
            "new_tasks_assigned": new_tasks_assigned,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)
        })
    
    # Determine access level for manager filters
    is_supreme = current_user.role.hierarchy_level >= 85 if current_user.role else False
    
    # Get available departments for dropdown (if manager)
    available_departments = []
    if is_manager:
        if is_supreme:
            # Supreme users see all departments
            all_depts = db.query(StaffDepartment).filter(StaffDepartment.is_active == True).all()
            available_departments = [{"id": d.id, "name": d.name} for d in all_depts]
        else:
            # Department managers see only their department
            if current_user.department:
                available_departments = [{"id": current_user.department.id, "name": current_user.department.name}]
    
    return {
        "success": True,
        "is_manager": is_manager,
        "is_supreme": is_supreme,
        "available_departments": available_departments,
        "departments": department_summaries,
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "priority": priority,
            "category": category,
            "department_id": department_id
        }
    }


@router.get("/analytics/team-performance", summary="Get overall team performance data")
async def get_team_performance(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    employee_id: Optional[int] = Query(None, description="Filter by specific employee"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Dec 06, 2025): Overall Team Performance endpoint - OPTIMIZED
    
    PERFORMANCE FIX: Replaced N+1 query loops with bulk SQL aggregations
    - Before: 500+ queries per request causing 502 timeouts
    - After: 5-8 queries per request (~100ms response)
    
    PURE REPORTING_MANAGER BASED HIERARCHY - NO HIERARCHY_LEVEL CHECKS:
    - ALL roles use recursive downline via reporting_manager_id chain
    - VGK sees EA's data because EA's reporting_manager_id = VGK's ID
    - VGK sees HR's data because HR reports to EA who reports to VGK
    - Senior Executive with direct reports sees their team's data
    - The org chart (reporting_manager_id) defines visibility EXCLUSIVELY
    - Access granted to anyone with direct reports OR shows own data if no reports
    
    Returns department-wise and employee-wise task data with same format as Summary Tables
    """
    from sqlalchemy import func, case
    from app.models.staff import StaffDepartment, StaffRole
    from app.utils.staff_hierarchy import get_team_member_ids, has_direct_reports
    
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    accessible_employee_ids = get_team_member_ids(
        current_user, db, StaffEmployee, department_id
    )
    
    # Filter by specific employee if provided
    if employee_id:
        if employee_id in accessible_employee_ids:
            accessible_employee_ids = [employee_id]
        else:
            accessible_employee_ids = []
    
    # OPTIMIZATION: Single bulk query to get employee details with department join
    accessible_employees = db.query(StaffEmployee).options(
        joinedload(StaffEmployee.department)
    ).filter(
        StaffEmployee.id.in_(accessible_employee_ids),
        StaffEmployee.status == 'active'
    ).all()
    
    # Build employee lookup and department set from single query
    emp_lookup = {emp.id: emp for emp in accessible_employees}
    accessible_dept_ids = set()
    for emp in accessible_employees:
        if emp.department_id:
            accessible_dept_ids.add(emp.department_id)
    
    # OPTIMIZATION: Single query for accessible departments
    accessible_departments = []
    if accessible_dept_ids:
        depts = db.query(StaffDepartment).filter(
            StaffDepartment.id.in_(accessible_dept_ids),
            StaffDepartment.is_active == True
        ).all()
        accessible_departments = [{"id": d.id, "name": d.name} for d in depts]
    
    today = get_indian_date()
    
    # OPTIMIZATION: Build reusable filter conditions
    def apply_task_filters(query):
        if date_filter_start:
            query = query.filter(StaffTask.created_at >= date_filter_start)
        if date_filter_end:
            query = query.filter(StaffTask.created_at <= date_filter_end)
        if status and status != 'all':
            query = query.filter(StaffTask.status == status)
        if priority and priority != 'all':
            query = query.filter(StaffTask.priority == priority)
        if category and category != 'all':
            query = query.filter(StaffTask.category == category)
        return query
    
    # OPTIMIZATION: Single aggregated query for overall totals
    base_totals = db.query(
        func.count(StaffTask.id).label('total'),
        func.sum(case((StaffTask.status == 'completed', 1), else_=0)).label('completed'),
        func.sum(case((StaffTask.status == 'in_progress', 1), else_=0)).label('in_progress'),
        func.sum(case((StaffTask.status == 'pending', 1), else_=0)).label('pending'),
        func.sum(case(
            (and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1),
            else_=0
        )).label('overdue')
    ).filter(
        or_(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.primary_assignee_id.is_(None)
        ),
        StaffTask.is_deleted == False
    )
    base_totals = apply_task_filters(base_totals)
    totals_result = base_totals.first()
    
    total_tasks = totals_result.total or 0
    total_completed = totals_result.completed or 0
    total_in_progress = totals_result.in_progress or 0
    total_pending = totals_result.pending or 0
    total_overdue = totals_result.overdue or 0
    
    # New tasks assigned count (date range only, no status filter)
    new_tasks_query = db.query(func.count(StaffTask.id)).filter(
        or_(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.primary_assignee_id.is_(None)
        ),
        StaffTask.is_deleted == False
    )
    if date_filter_start:
        new_tasks_query = new_tasks_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        new_tasks_query = new_tasks_query.filter(StaffTask.created_at <= date_filter_end)
    total_new_assigned = new_tasks_query.scalar() or 0
    
    # OPTIMIZATION: Department-wise breakdown using GROUP BY aggregation
    department_data = []
    if not department_id and accessible_employee_ids:
        # Build employee-to-department mapping
        emp_dept_map = {emp.id: emp.department_id for emp in accessible_employees if emp.department_id}
        dept_name_map = {d["id"]: d["name"] for d in accessible_departments}
        
        # Single aggregated query for department stats
        dept_stats_query = db.query(
            StaffEmployee.department_id,
            func.count(StaffTask.id).label('total'),
            func.sum(case((StaffTask.status == 'completed', 1), else_=0)).label('completed'),
            func.sum(case((StaffTask.status == 'in_progress', 1), else_=0)).label('in_progress'),
            func.sum(case((StaffTask.status == 'pending', 1), else_=0)).label('pending'),
            func.sum(case(
                (and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1),
                else_=0
            )).label('overdue')
        ).join(
            StaffEmployee, StaffTask.primary_assignee_id == StaffEmployee.id
        ).filter(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.is_deleted == False,
            StaffEmployee.department_id.isnot(None)
        ).group_by(StaffEmployee.department_id)
        
        dept_stats_query = apply_task_filters(dept_stats_query)
        dept_stats = dept_stats_query.all()
        
        # Query for new tasks by department (date range only)
        dept_new_query = db.query(
            StaffEmployee.department_id,
            func.count(StaffTask.id).label('new_assigned')
        ).join(
            StaffEmployee, StaffTask.primary_assignee_id == StaffEmployee.id
        ).filter(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.is_deleted == False,
            StaffEmployee.department_id.isnot(None)
        ).group_by(StaffEmployee.department_id)
        if date_filter_start:
            dept_new_query = dept_new_query.filter(StaffTask.created_at >= date_filter_start)
        if date_filter_end:
            dept_new_query = dept_new_query.filter(StaffTask.created_at <= date_filter_end)
        dept_new_stats = {row.department_id: row.new_assigned for row in dept_new_query.all()}
        
        for row in dept_stats:
            if row.department_id and row.total > 0:
                dept_name = dept_name_map.get(row.department_id, "Unknown")
                department_data.append({
                    "department_id": row.department_id,
                    "department_name": dept_name,
                    "total": row.total or 0,
                    "completed": row.completed or 0,
                    "dues": (row.total or 0) - (row.completed or 0),
                    "new_tasks_assigned": dept_new_stats.get(row.department_id, 0),
                    "in_progress": row.in_progress or 0,
                    "pending": row.pending or 0,
                    "overdue": row.overdue or 0
                })
    
    # Unassigned tasks bucket
    unassigned_stats = db.query(
        func.count(StaffTask.id).label('total'),
        func.sum(case((StaffTask.status == 'completed', 1), else_=0)).label('completed'),
        func.sum(case((StaffTask.status == 'in_progress', 1), else_=0)).label('in_progress'),
        func.sum(case((StaffTask.status == 'pending', 1), else_=0)).label('pending'),
        func.sum(case(
            (and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1),
            else_=0
        )).label('overdue')
    ).filter(
        StaffTask.primary_assignee_id.is_(None),
        StaffTask.is_deleted == False
    )
    unassigned_stats = apply_task_filters(unassigned_stats)
    unassigned_result = unassigned_stats.first()
    
    if unassigned_result and unassigned_result.total and unassigned_result.total > 0:
        department_data.append({
            "department_id": None,
            "department_name": "Unassigned Tasks",
            "total": unassigned_result.total or 0,
            "completed": unassigned_result.completed or 0,
            "dues": (unassigned_result.total or 0) - (unassigned_result.completed or 0),
            "new_tasks_assigned": unassigned_result.total or 0,
            "in_progress": unassigned_result.in_progress or 0,
            "pending": unassigned_result.pending or 0,
            "overdue": unassigned_result.overdue or 0
        })
    
    # OPTIMIZATION: Employee-wise breakdown using GROUP BY aggregation
    employee_data = []
    if accessible_employee_ids:
        # Single aggregated query for employee stats
        emp_stats_query = db.query(
            StaffTask.primary_assignee_id,
            func.count(StaffTask.id).label('total'),
            func.sum(case((StaffTask.status == 'completed', 1), else_=0)).label('completed'),
            func.sum(case((StaffTask.status == 'in_progress', 1), else_=0)).label('in_progress'),
            func.sum(case((StaffTask.status == 'pending', 1), else_=0)).label('pending'),
            func.sum(case(
                (and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1),
                else_=0
            )).label('overdue')
        ).filter(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.is_deleted == False
        ).group_by(StaffTask.primary_assignee_id)
        
        emp_stats_query = apply_task_filters(emp_stats_query)
        emp_stats = {row.primary_assignee_id: row for row in emp_stats_query.all()}
        
        # Query for new tasks by employee (date range only)
        emp_new_query = db.query(
            StaffTask.primary_assignee_id,
            func.count(StaffTask.id).label('new_assigned')
        ).filter(
            StaffTask.primary_assignee_id.in_(accessible_employee_ids),
            StaffTask.is_deleted == False
        ).group_by(StaffTask.primary_assignee_id)
        if date_filter_start:
            emp_new_query = emp_new_query.filter(StaffTask.created_at >= date_filter_start)
        if date_filter_end:
            emp_new_query = emp_new_query.filter(StaffTask.created_at <= date_filter_end)
        emp_new_stats = {row.primary_assignee_id: row.new_assigned for row in emp_new_query.all()}
        
        # Build employee data from lookup (no additional queries)
        for emp_id in accessible_employee_ids:
            emp = emp_lookup.get(emp_id)
            if not emp:
                continue
            
            stats = emp_stats.get(emp_id)
            total = stats.total if stats else 0
            
            # Skip employees with no tasks unless filtering by specific employee
            if total == 0 and not employee_id:
                continue
            
            employee_data.append({
                "employee_id": emp.id,
                "emp_code": emp.emp_code,
                "employee_name": emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip(),
                "department_name": emp.department.name if emp.department else "N/A",
                "total": total,
                "completed": stats.completed if stats else 0,
                "dues": total - (stats.completed if stats else 0),
                "new_tasks_assigned": emp_new_stats.get(emp_id, 0),
                "in_progress": stats.in_progress if stats else 0,
                "pending": stats.pending if stats else 0,
                "overdue": stats.overdue if stats else 0
            })
    
    # Determine access level label based on hierarchy
    if hierarchy_level >= 85:
        access_level = "supreme"
    elif hierarchy_level >= 75:
        access_level = "ea"
    else:
        access_level = "manager"
    
    return {
        "success": True,
        "access_level": access_level,
        "hierarchy_level": hierarchy_level,
        "available_departments": accessible_departments,
        "totals": {
            "total": total_tasks,
            "completed": total_completed,
            "dues": total_tasks - total_completed,
            "new_tasks_assigned": total_new_assigned,
            "in_progress": total_in_progress,
            "pending": total_pending,
            "overdue": total_overdue
        },
        "departments": department_data,
        "employees": employee_data,
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "priority": priority,
            "category": category,
            "department_id": department_id,
            "employee_id": employee_id
        }
    }


@router.get("/analytics/employee-summary", summary="Get employee-wise task breakdown")
async def get_employee_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    employee_id: Optional[int] = Query(None, description="Filter by specific employee"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get employee-wise task breakdown based on reporting chain
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Shows breakdown for employees in user's reporting chain
    - Users with no direct reports see only their own data
    """
    from app.utils.staff_hierarchy import get_team_member_ids, has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    
    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    accessible_employee_ids = get_team_member_ids(
        current_user, db, StaffEmployee, department_id
    )
    
    base_query = db.query(StaffTask).filter(StaffTask.is_deleted == False)
    
    if date_filter_start:
        base_query = base_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        base_query = base_query.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        base_query = base_query.filter(StaffTask.status == status)
    if priority and priority != 'all':
        base_query = base_query.filter(StaffTask.priority == priority)
    if category and category != 'all':
        base_query = base_query.filter(StaffTask.category == category)
    
    emp_query = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.id.in_(accessible_employee_ids)
    )
    if employee_id:
        # Only allow filtering by employee if they're in accessible list
        if employee_id in accessible_employee_ids:
            emp_query = emp_query.filter(StaffEmployee.id == employee_id)
        else:
            emp_query = emp_query.filter(StaffEmployee.id == -1)  # Return empty
    
    employees = emp_query.all()
    
    today = get_indian_date()
    employee_summaries = []
    
    for emp in employees:
        emp_tasks_query = base_query.filter(StaffTask.primary_assignee_id == emp.id)
        
        total = emp_tasks_query.count()
        
        # Skip employees with no tasks (unless explicitly filtered)
        if total == 0 and not employee_id:
            continue
        
        completed = emp_tasks_query.filter(StaffTask.status == 'completed').count()
        in_progress = emp_tasks_query.filter(StaffTask.status == 'in_progress').count()
        pending = emp_tasks_query.filter(StaffTask.status == 'pending').count()
        overdue = emp_tasks_query.filter(
            StaffTask.due_date < today,
            StaffTask.status.notin_(['completed', 'cancelled'])
        ).count()
        
        employee_summaries.append({
            "employee_id": emp.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "department_id": emp.department_id,
            "department_name": emp.department.name if emp.department else None,
            "designation": emp.designation,
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)
        })
    
    return {
        "success": True,
        "employees": employee_summaries,
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "priority": priority,
            "category": category,
            "department_id": department_id,
            "employee_id": employee_id
        }
    }


@router.get("/analytics/my-summary", summary="Get personal task summary (assigned to me)")
async def get_my_task_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get summary of tasks assigned TO current user
    DC/WVV: Shows personal workload breakdown
    """
    # Parse date filters
    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get secondary task IDs
    secondary_task_ids = db.query(StaffTaskAssignee.task_id).filter(
        StaffTaskAssignee.employee_id == current_user.id
    ).scalar_subquery()
    
    # Base query: Tasks where user is primary or secondary assignee
    base_query = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        )
    )
    
    # Apply filters (including date filters)
    if date_filter_start:
        base_query = base_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        base_query = base_query.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        base_query = base_query.filter(StaffTask.status == status)
    if priority and priority != 'all':
        base_query = base_query.filter(StaffTask.priority == priority)
    if category and category != 'all':
        base_query = base_query.filter(StaffTask.category == category)
    
    # DC Protocol (Jan 22, 2026): Optimized query - consolidate 26 queries into 3 using aggregation
    from sqlalchemy import func, case, literal
    
    today = get_indian_date()
    
    # Query 1: Get all counts in single aggregated query
    aggregated = db.query(
        func.count().label('total'),
        # Status counts
        func.count(case((StaffTask.status == 'pending', 1))).label('pending'),
        func.count(case((StaffTask.status == 'in_progress', 1))).label('in_progress'),
        func.count(case((StaffTask.status == 'completed', 1))).label('completed'),
        func.count(case((StaffTask.status == 'cancelled', 1))).label('cancelled'),
        # Overdue count
        func.count(case((and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1))).label('overdue'),
        # Category counts
        func.count(case((StaffTask.category == 'development', 1))).label('cat_development'),
        func.count(case((StaffTask.category == 'design', 1))).label('cat_design'),
        func.count(case((StaffTask.category == 'testing', 1))).label('cat_testing'),
        func.count(case((StaffTask.category == 'documentation', 1))).label('cat_documentation'),
        func.count(case((StaffTask.category == 'support', 1))).label('cat_support'),
        func.count(case((StaffTask.category == 'other', 1))).label('cat_other'),
    ).filter(
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        )
    )
    
    # Apply filters to aggregated query
    if date_filter_start:
        aggregated = aggregated.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        aggregated = aggregated.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        aggregated = aggregated.filter(StaffTask.status == status)
    if priority and priority != 'all':
        aggregated = aggregated.filter(StaffTask.priority == priority)
    if category and category != 'all':
        aggregated = aggregated.filter(StaffTask.category == category)
    
    agg_result = aggregated.first()
    total = agg_result.total or 0
    overdue = agg_result.overdue or 0
    
    # Query 2: Priority breakdown per status (single query with GROUP BY)
    priority_stats = db.query(
        StaffTask.status,
        StaffTask.priority,
        func.count().label('count')
    ).filter(
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        )
    )
    if date_filter_start:
        priority_stats = priority_stats.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        priority_stats = priority_stats.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        priority_stats = priority_stats.filter(StaffTask.status == status)
    if priority and priority != 'all':
        priority_stats = priority_stats.filter(StaffTask.priority == priority)
    if category and category != 'all':
        priority_stats = priority_stats.filter(StaffTask.category == category)
    
    priority_stats = priority_stats.group_by(StaffTask.status, StaffTask.priority).all()
    
    # Build priority breakdown map
    priority_map = {}
    for row in priority_stats:
        if row.status not in priority_map:
            priority_map[row.status] = {}
        if row.priority and row.count > 0:
            priority_map[row.status][row.priority] = row.count
    
    # Build status breakdown
    status_breakdown = []
    status_counts = {
        'pending': agg_result.pending or 0,
        'in_progress': agg_result.in_progress or 0,
        'completed': agg_result.completed or 0,
        'cancelled': agg_result.cancelled or 0
    }
    for status_value in ['pending', 'in_progress', 'completed', 'cancelled']:
        status_breakdown.append({
            "status": status_value,
            "count": status_counts[status_value],
            "priority_breakdown": priority_map.get(status_value, {})
        })
    
    # Category breakdown from aggregated result
    category_breakdown = {}
    cat_map = {
        'development': agg_result.cat_development or 0,
        'design': agg_result.cat_design or 0,
        'testing': agg_result.cat_testing or 0,
        'documentation': agg_result.cat_documentation or 0,
        'support': agg_result.cat_support or 0,
        'other': agg_result.cat_other or 0
    }
    for cat, count in cat_map.items():
        if count > 0:
            category_breakdown[cat] = count
    
    # New Tasks Assigned: Count tasks created in date range (ignore status/priority/category filters)
    # Build separate query with ONLY date filters for this metric
    new_tasks_query = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == current_user.id,
            StaffTask.id.in_(secondary_task_ids)
        )
    )
    
    # Apply ONLY date filters (no status/priority/category)
    if date_filter_start:
        new_tasks_query = new_tasks_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        new_tasks_query = new_tasks_query.filter(StaffTask.created_at <= date_filter_end)
    
    new_tasks_assigned = new_tasks_query.count()
    
    # DC Protocol: Manager metadata based on reporting chain, not hierarchy_level
    from app.utils.staff_hierarchy import has_direct_reports
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    
    # DC Protocol Feb 2026: Subtask (phase) counts for self
    # Subtasks assigned TO me (I'm the phase assignee)
    subtask_base = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.is_deleted == False,
        StaffTaskPhase.phase_assignee_id == current_user.id
    )
    subtask_total = subtask_base.count()
    subtask_completed = subtask_base.filter(StaffTaskPhase.phase_status == 'completed').count()
    subtask_in_progress = subtask_base.filter(StaffTaskPhase.phase_status == 'in_progress').count()
    subtask_pending = subtask_base.filter(StaffTaskPhase.phase_status == 'pending').count()
    subtask_cancelled = subtask_base.filter(StaffTaskPhase.phase_status == 'cancelled').count()
    subtask_overdue = subtask_base.filter(
        StaffTaskPhase.target_date < today,
        StaffTaskPhase.phase_status.notin_(['completed', 'cancelled'])
    ).count()
    
    return {
        "success": True,
        "is_manager": is_manager,
        "summary": {
            "total": total,
            "new_tasks_assigned": new_tasks_assigned,
            "status_breakdown": status_breakdown,
            "overdue": overdue,
            "category_breakdown": category_breakdown,
            "completion_rate": round((base_query.filter(StaffTask.status == 'completed').count() / total * 100) if total > 0 else 0, 1)
        },
        "subtask_summary": {
            "total": subtask_total,
            "completed": subtask_completed,
            "in_progress": subtask_in_progress,
            "pending": subtask_pending,
            "cancelled": subtask_cancelled,
            "overdue": subtask_overdue,
            "completion_rate": round((subtask_completed / subtask_total * 100) if subtask_total > 0 else 0, 1)
        },
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "priority": priority,
            "category": category
        }
    }


@router.get("/analytics/my-assigned-summary", summary="Get summary of tasks I assigned to others with subtask counts")
async def get_my_assigned_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol Feb 2026: Summary of tasks created/assigned BY current user
    Includes subtask (phase) counts for tasks I created
    Supports full filter set: dates, status, priority, category
    """
    return _build_employee_assigned_summary(current_user.id, start_date, end_date, status, priority, category, db)


def _build_employee_assigned_summary(employee_id, start_date, end_date, status, priority, category, db):
    """Reusable helper: build assigned-BY summary for any employee"""
    from sqlalchemy import func, case

    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass

    today = get_indian_date()

    def apply_filters(q):
        if date_filter_start:
            q = q.filter(StaffTask.created_at >= date_filter_start)
        if date_filter_end:
            q = q.filter(StaffTask.created_at <= date_filter_end)
        if status and status != 'all':
            q = q.filter(StaffTask.status == status)
        if priority and priority != 'all':
            q = q.filter(StaffTask.priority == priority)
        if category and category != 'all':
            q = q.filter(StaffTask.category == category)
        return q

    base_filters = [StaffTask.is_deleted == False, StaffTask.created_by == employee_id]

    agg = apply_filters(db.query(
        func.count().label('total'),
        func.count(case((StaffTask.status == 'pending', 1))).label('pending'),
        func.count(case((StaffTask.status == 'in_progress', 1))).label('in_progress'),
        func.count(case((StaffTask.status == 'completed', 1))).label('completed'),
        func.count(case((StaffTask.status == 'cancelled', 1))).label('cancelled'),
        func.count(case((and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1))).label('overdue'),
    ).filter(*base_filters))

    r = agg.first()
    total = r.total or 0

    new_query = db.query(StaffTask).filter(*base_filters)
    if date_filter_start:
        new_query = new_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        new_query = new_query.filter(StaffTask.created_at <= date_filter_end)
    new_tasks = new_query.count()

    my_task_ids = db.query(StaffTask.id).filter(*base_filters)
    if date_filter_start:
        my_task_ids = my_task_ids.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        my_task_ids = my_task_ids.filter(StaffTask.created_at <= date_filter_end)

    subtask_base = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.is_deleted == False,
        StaffTaskPhase.parent_task_id.in_(my_task_ids.scalar_subquery())
    )
    if date_filter_start:
        subtask_base = subtask_base.filter(StaffTaskPhase.created_at >= date_filter_start)
    if date_filter_end:
        subtask_base = subtask_base.filter(StaffTaskPhase.created_at <= date_filter_end)
    if status and status != 'all':
        subtask_base = subtask_base.filter(StaffTaskPhase.phase_status == status)

    st_total = subtask_base.count()
    st_completed = subtask_base.filter(StaffTaskPhase.phase_status == 'completed').count()
    st_in_progress = subtask_base.filter(StaffTaskPhase.phase_status == 'in_progress').count()
    st_pending = subtask_base.filter(StaffTaskPhase.phase_status == 'pending').count()
    st_cancelled = subtask_base.filter(StaffTaskPhase.phase_status == 'cancelled').count()
    st_overdue = subtask_base.filter(
        StaffTaskPhase.target_date < today,
        StaffTaskPhase.phase_status.notin_(['completed', 'cancelled'])
    ).count()

    return {
        "success": True,
        "summary": {
            "total": total,
            "new_tasks_assigned": new_tasks,
            "completed": r.completed or 0,
            "in_progress": r.in_progress or 0,
            "pending": r.pending or 0,
            "cancelled": r.cancelled or 0,
            "overdue": r.overdue or 0,
            "completion_rate": round(((r.completed or 0) / total * 100) if total > 0 else 0, 1)
        },
        "subtask_summary": {
            "total": st_total,
            "completed": st_completed,
            "in_progress": st_in_progress,
            "pending": st_pending,
            "cancelled": st_cancelled,
            "overdue": st_overdue,
            "completion_rate": round((st_completed / st_total * 100) if st_total > 0 else 0, 1)
        }
    }


def _build_employee_received_summary(employee_id, start_date, end_date, status, priority, category, db):
    """Reusable helper: build assigned-TO summary for any employee"""
    from sqlalchemy import func, case

    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass

    today = get_indian_date()

    secondary_task_ids = db.query(StaffTaskAssignee.task_id).filter(
        StaffTaskAssignee.employee_id == employee_id
    ).scalar_subquery()

    base_filters = [
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == employee_id,
            StaffTask.id.in_(secondary_task_ids)
        )
    ]

    def apply_filters(q):
        if date_filter_start:
            q = q.filter(StaffTask.created_at >= date_filter_start)
        if date_filter_end:
            q = q.filter(StaffTask.created_at <= date_filter_end)
        if status and status != 'all':
            q = q.filter(StaffTask.status == status)
        if priority and priority != 'all':
            q = q.filter(StaffTask.priority == priority)
        if category and category != 'all':
            q = q.filter(StaffTask.category == category)
        return q

    agg = apply_filters(db.query(
        func.count().label('total'),
        func.count(case((StaffTask.status == 'pending', 1))).label('pending'),
        func.count(case((StaffTask.status == 'in_progress', 1))).label('in_progress'),
        func.count(case((StaffTask.status == 'completed', 1))).label('completed'),
        func.count(case((StaffTask.status == 'cancelled', 1))).label('cancelled'),
        func.count(case((and_(StaffTask.due_date < today, StaffTask.status.notin_(['completed', 'cancelled'])), 1))).label('overdue'),
    ).filter(*base_filters))

    r = agg.first()
    total = r.total or 0

    new_query = db.query(StaffTask).filter(*base_filters)
    if date_filter_start:
        new_query = new_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        new_query = new_query.filter(StaffTask.created_at <= date_filter_end)
    new_tasks = new_query.count()

    completed_for_rate = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == employee_id,
            StaffTask.id.in_(secondary_task_ids)
        ),
        StaffTask.status == 'completed'
    )
    if date_filter_start:
        completed_for_rate = completed_for_rate.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        completed_for_rate = completed_for_rate.filter(StaffTask.created_at <= date_filter_end)

    total_for_rate = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        or_(
            StaffTask.primary_assignee_id == employee_id,
            StaffTask.id.in_(secondary_task_ids)
        )
    )
    if date_filter_start:
        total_for_rate = total_for_rate.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        total_for_rate = total_for_rate.filter(StaffTask.created_at <= date_filter_end)
    total_unfiltered = total_for_rate.count()
    completion_rate = round((completed_for_rate.count() / total_unfiltered * 100) if total_unfiltered > 0 else 0, 1)

    subtask_base = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.is_deleted == False,
        StaffTaskPhase.phase_assignee_id == employee_id
    )
    if date_filter_start:
        subtask_base = subtask_base.filter(StaffTaskPhase.created_at >= date_filter_start)
    if date_filter_end:
        subtask_base = subtask_base.filter(StaffTaskPhase.created_at <= date_filter_end)
    if status and status != 'all':
        subtask_base = subtask_base.filter(StaffTaskPhase.phase_status == status)

    st_total = subtask_base.count()
    st_completed = subtask_base.filter(StaffTaskPhase.phase_status == 'completed').count()
    st_in_progress = subtask_base.filter(StaffTaskPhase.phase_status == 'in_progress').count()
    st_pending = subtask_base.filter(StaffTaskPhase.phase_status == 'pending').count()
    st_cancelled = subtask_base.filter(StaffTaskPhase.phase_status == 'cancelled').count()
    st_overdue = subtask_base.filter(
        StaffTaskPhase.target_date < today,
        StaffTaskPhase.phase_status.notin_(['completed', 'cancelled'])
    ).count()

    status_breakdown = [
        {"status": "pending", "count": r.pending or 0},
        {"status": "in_progress", "count": r.in_progress or 0},
        {"status": "completed", "count": r.completed or 0},
        {"status": "cancelled", "count": r.cancelled or 0}
    ]

    return {
        "success": True,
        "summary": {
            "total": total,
            "new_tasks_assigned": new_tasks,
            "status_breakdown": status_breakdown,
            "overdue": r.overdue or 0,
            "completion_rate": completion_rate
        },
        "subtask_summary": {
            "total": st_total,
            "completed": st_completed,
            "in_progress": st_in_progress,
            "pending": st_pending,
            "cancelled": st_cancelled,
            "overdue": st_overdue,
            "completion_rate": round((st_completed / st_total * 100) if st_total > 0 else 0, 1)
        }
    }


@router.get("/analytics/team-member-summary", summary="Get task summary for a specific team member")
async def get_team_member_summary(
    employee_id: int = Query(..., description="Employee ID to view"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol Feb 2026: Get assigned-by and assigned-to summary with subtask counts
    for a specific team member. Returns both sections in a single response.
    """
    target_employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id,
        StaffEmployee.status == 'active'
    ).first()
    if not target_employee:
        return {"success": False, "detail": "Employee not found"}

    assigned_by = _build_employee_assigned_summary(employee_id, start_date, end_date, status, priority, category, db)
    assigned_to = _build_employee_received_summary(employee_id, start_date, end_date, status, priority, category, db)

    return {
        "success": True,
        "employee": {
            "id": target_employee.id,
            "emp_code": target_employee.emp_code,
            "full_name": target_employee.full_name
        },
        "assigned_by": assigned_by,
        "assigned_to": assigned_to
    }


@router.get("/analytics/chart-data", summary="Get chart data for Analytics Charts tab")
async def get_chart_data(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get chart data for graphical representations
    Returns data for:
    1. Status Distribution (pie chart)
    2. Priority Breakdown (bar chart)
    3. Tasks Timeline (line chart)
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users see chart data for tasks in their reporting chain
    - Users with direct reports can filter by department/employee within their chain
    """
    from app.utils.staff_hierarchy import get_team_member_ids, has_direct_reports
    
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    
    date_filter_start = None
    date_filter_end = None
    if start_date:
        try:
            date_filter_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date:
        try:
            date_filter_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    accessible_employee_ids = get_team_member_ids(
        current_user, db, StaffEmployee, department_id
    )
    
    if employee_id and employee_id != 0:
        if employee_id in accessible_employee_ids:
            accessible_employee_ids = [employee_id]
        else:
            accessible_employee_ids = []
    
    base_query = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        StaffTask.primary_assignee_id.in_(accessible_employee_ids)
    )
    
    # Apply common filters
    if date_filter_start:
        base_query = base_query.filter(StaffTask.created_at >= date_filter_start)
    if date_filter_end:
        base_query = base_query.filter(StaffTask.created_at <= date_filter_end)
    if status and status != 'all':
        base_query = base_query.filter(StaffTask.status == status)
    if priority and priority != 'all':
        base_query = base_query.filter(StaffTask.priority == priority)
    if category and category != 'all':
        base_query = base_query.filter(StaffTask.category == category)
    
    # 1. Status Distribution (for pie chart)
    status_distribution = []
    for status_value in ['pending', 'in_progress', 'completed', 'cancelled']:
        count = base_query.filter(StaffTask.status == status_value).count()
        status_distribution.append({
            "status": status_value,
            "count": count
        })
    
    # 2. Priority Breakdown (for bar chart)
    priority_breakdown = []
    for priority_value in ['high', 'medium', 'low']:
        count = base_query.filter(StaffTask.priority == priority_value).count()
        priority_breakdown.append({
            "priority": priority_value,
            "count": count
        })
    
    # 3. Tasks Timeline (for line chart) - Category-wise task counts over time
    timeline_data = {}
    
    # Get all tasks with their created dates and categories
    timeline_tasks = base_query.all()
    
    # Group by category
    for cat in ['development', 'design', 'testing', 'documentation', 'support', 'other']:
        cat_tasks = [t for t in timeline_tasks if t.category == cat]
        
        # Group by date
        date_counts = {}
        for task in cat_tasks:
            task_date = task.created_at.date() if isinstance(task.created_at, datetime) else task.created_at
            date_str = task_date.strftime('%Y-%m-%d')
            date_counts[date_str] = date_counts.get(date_str, 0) + 1
        
        # Convert to sorted array
        timeline_data[cat] = sorted([
            {"date": date, "count": count}
            for date, count in date_counts.items()
        ], key=lambda x: x['date'])
    
    return {
        "success": True,
        "charts": {
            "status_distribution": status_distribution,
            "priority_breakdown": priority_breakdown,
            "timeline": timeline_data
        },
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "priority": priority,
            "category": category
        }
    }


@router.get("/analytics/filter-options", summary="Get universal filter options for staff pages")
async def get_filter_options(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_UNIVERSAL_FILTER_001: Get all filter options for universal filter component
    
    Returns:
    - Companies: List of active associated companies
    - Staff Types: List of valid staff types with labels
    - Departments: List of active departments (for reference)
    
    DC Protocol (Dec 07, 2025):
    - Single endpoint for all filter dropdowns
    - Optimized to reduce multiple API calls
    - Role-agnostic: All authenticated staff can access filter options
    """
    from app.models.staff_accounts import AssociatedCompany
    from app.models.staff import StaffDepartment
    
    # Get active companies
    companies = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_active == True
    ).order_by(AssociatedCompany.company_name).all()
    
    # Get active departments
    departments = db.query(StaffDepartment).filter(
        StaffDepartment.is_active == True
    ).order_by(StaffDepartment.name).all()
    
    # Staff types with display labels
    staff_types = [
        {"value": "MN_STAFF", "label": "MN Staff"},
        {"value": "MN_EMPLOYEE", "label": "MN Employee"},
        {"value": "FREELANCER", "label": "Freelancer"},
        {"value": "MYNT_REAL", "label": "Mynt Real"}
    ]
    
    return {
        "success": True,
        "companies": [
            {
                "id": c.id,
                "company_code": c.company_code,
                "company_name": c.company_name
            }
            for c in companies
        ],
        "staff_types": staff_types,
        "departments": [
            {
                "id": d.id,
                "name": d.name
            }
            for d in departments
        ]
    }


@router.get("/analytics/employees-for-filter", summary="Get employees list for filter with autocomplete support")
async def get_employees_for_filter(
    department_id: Optional[int] = Query(None, description="Filter by department"),
    staff_type: Optional[str] = Query(None, description="Filter by staff type: MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL"),
    search: Optional[str] = Query(None, description="Search by employee name or code"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get employees for filter with autocomplete search support
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Users see only employees in their reporting chain
    - Supports search by name or employee code for autocomplete
    
    DC Protocol (Dec 07, 2025): DC_UNIVERSAL_FILTER_001
    - Added staff_type filter for staff type-wise filtering
    - Maintains backward compatibility with existing callers
    - Note: Company filter not applicable to employees (no company_id in model)
    """
    from app.utils.staff_hierarchy import get_team_member_ids
    
    accessible_employee_ids = get_team_member_ids(
        current_user, db, StaffEmployee, department_id
    )
    
    query = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.id.in_(accessible_employee_ids)
    )
    
    if staff_type and staff_type in ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']:
        query = query.filter(StaffEmployee.staff_type == staff_type)
    
    # Apply search filter (case-insensitive)
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                StaffEmployee.full_name.ilike(search_term),
                StaffEmployee.emp_code.ilike(search_term)
            )
        )
    
    # Get employees with limit
    employees = query.order_by(StaffEmployee.full_name).limit(limit).all()
    
    return {
        "success": True,
        "employees": [
            {
                "id": emp.id,
                "employee_code": emp.emp_code,
                "name": emp.full_name,
                "emp_code": emp.emp_code,
                "full_name": emp.full_name,
                "staff_type": emp.staff_type,
                "department_name": emp.department.name if emp.department else "N/A"
            }
            for emp in employees
        ],
        "total": len(employees),
        "has_more": len(employees) >= limit
    }


@router.post("/{task_id}/attachments", summary="Upload file to task")
async def upload_task_attachment(
    task_id: int,
    request: Request,
    file: UploadFile = File(...),
    source: Optional[str] = Query(None, description="Upload source: 'edit' for edit modal, None for create modal"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Upload file attachment to task
    DC: Max 2 files during CREATE, max 20 files during EDIT (prevent storage exhaustion)
    WVV: Validate file type, size, and count before saving
    DC: Activity log tags edit-mode uploads with 'attachment_added_via_edit'
    """
    # VERIFY: Task exists
    task = db.query(StaffTask).filter(
        StaffTask.id == task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # VERIFY: User has access to this task
    if task.created_by != current_user.id and task.primary_assignee_id != current_user.id:
        secondary = db.query(StaffTaskAssignee).filter(
            StaffTaskAssignee.task_id == task_id,
            StaffTaskAssignee.employee_id == current_user.id
        ).first()
        if not secondary:
            raise HTTPException(status_code=403, detail="You don't have access to this task")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    # VERIFY: Check current attachment count
    current_count = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.task_id == task_id,
        StaffTaskAttachment.is_deleted == False
    ).count()
    
    # DC: Enforce different limits for CREATE vs EDIT mode
    if source is None:
        # CREATE mode: Max 2 files
        if current_count >= MAX_FILES_PER_TASK_CREATE:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_FILES_PER_TASK_CREATE} files allowed during task creation. You can add more files after creating the task."
            )
    else:
        # EDIT mode: Max 20 files total (DC: Prevent storage exhaustion)
        if current_count >= MAX_FILES_PER_TASK_EDIT:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_FILES_PER_TASK_EDIT} files allowed per task. Delete existing files to upload new ones."
            )
    
    # VERIFY: Check file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Allowed: JPEG, PNG, GIF, WebP, BMP, TIFF, PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT"
        )
    
    # DC Protocol: Enforce size limits BEFORE upload (prevent orphan records)
    # Read file content to validate size
    file_content = await file.read()
    file_size = len(file_content)
    file.file.seek(0)  # Reset file pointer for UniversalUploadService (synchronous seek for SpooledTemporaryFile)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Apply different size limits based on file type (DC Protocol requirement)
    # UPDATED Nov 29, 2025: 5MB for all file types (aligned with Universal Upload System)
    is_image = file.content_type in IMAGE_MIME_TYPES
    max_allowed_size = MAX_IMAGE_SIZE if is_image else MAX_DOCUMENT_SIZE
    file_type_label = "Image" if is_image else "Document"
    size_limit_label = "5MB"  # Unified limit for all files
    
    if file_size > max_allowed_size:
        raise HTTPException(
            status_code=400,
            detail=f"{file_type_label} size ({round(file_size/1024, 2)}KB) exceeds maximum allowed size ({size_limit_label}). "
                   f"{'Images will be automatically compressed after upload.' if is_image else 'Please compress the document before uploading.'}"
        )
    
    # Universal Upload System: 5MB for images/docs, auto-compression, dual storage
    from app.services.universal_upload_service import UniversalUploadService
    
    # DC Protocol: Atomic transaction - attachment + activity log commit together
    attachment = None
    upload_result = None
    try:
        # Create placeholder record to get ID (within transaction - NOT committed yet)
        # DC FIX: Use actual file_size to satisfy constraint (file_size > 0)
        attachment = StaffTaskAttachment(
            task_id=task_id,
            file_name=file.filename,
            file_path="pending",  # Temporary
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,  # DC: Use actual size (satisfies constraint: file_size > 0)
            uploaded_by=current_user.id,
            processing_status='pending',
            has_original=True,
            storage_tier='hot',
            checksum_algorithm='SHA-256'
        )
        db.add(attachment)
        db.flush()  # Get attachment ID for upload (still within transaction)
        
        # Upload file using attachment ID (if this fails, transaction rolls back)
        # DC Protocol: defer_scheduler=True ensures job only scheduled AFTER db.commit()
        upload_result = await UniversalUploadService.handle_upload(
            file=file,
            table_name='staff_task_attachments',
            record_id=attachment.id,
            uploaded_by_id=current_user.id,
            uploaded_by_type='staff',
            storage_dir='task_attachments',
            db=db,
            emp_code=current_user.emp_code,
            defer_scheduler=True  # DC: Transaction safety - schedule job AFTER commit
        )
        
        # DC Protocol: Update attachment with ALL metadata from upload result
        attachment.file_name = upload_result['file_name']
        attachment.file_path = upload_result['file_path']
        attachment.file_type = upload_result['file_type']
        attachment.file_size = upload_result['file_size']
        attachment.processing_status = 'pending' if upload_result['needs_compression'] else 'completed'
        
        # DC Protocol: Dual storage architecture metadata (ALL available fields from upload_result)
        # Note: Compressed metadata (compressed_path, compressed_size, etc.) updated LATER by background job
        attachment.original_checksum = upload_result.get('original_checksum')
        attachment.original_storage_type = upload_result.get('storage_type', 'local')
        attachment.original_storage_key = upload_result.get('storage_key')
        
        # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
        # Format: {SEGMENT}_{ENTITY_ID}_{ATTACHMENT_ID}_{TIMESTAMP}_{UPLOADER}_{ORIGINAL}
        # Example: TASK_T40_00024_20251129_063020_MR10009_screenshot.png
        try:
            ist_tz = pytz.timezone('Asia/Kolkata')
            uploaded_at_ist = datetime.now(ist_tz)
            
            download_name = UniversalUploadService.generate_download_filename(
                segment_key='task_attachment',  # Functional segment
                entity_type='task',  # Entity type for prefix
                entity_id=task_id,  # Task ID
                attachment_id=attachment.id,  # Attachment ID
                uploader_code=current_user.emp_code,  # Employee code (MR10009, etc.)
                original_filename=file.filename,  # User's uploaded filename
                uploaded_at=uploaded_at_ist  # IST timestamp
            )
            
            # WVV: Populate new columns
            attachment.download_filename = download_name
            attachment.uses_new_naming = True
            
        except HTTPException:
            # DC PROTOCOL: Re-raise validation errors (UNKNOWN segments must hard-fail)
            # WVV: Prevent silent audit corruption by aborting on misconfigured metadata
            raise
        except Exception as e:
            # DC: Log unexpected errors (e.g., timezone issues) but still fail the upload
            # WVV: Semantic naming is mandatory - fallback disabled per architect mandate
            logger.error(f"Unexpected error generating download filename for attachment {attachment.id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate semantic filename: {str(e)}"
            )
        
        # DC: Log activity in SAME transaction
        action = 'attachment_added_via_edit' if source == 'edit' else 'file_uploaded'
        log_task_activity(
            db=db,
            task_id=task_id,
            employee_id=current_user.id,
            action=action,
            details=f"Uploaded file: {file.filename} ({attachment.file_size} bytes)",
            ip_address=get_client_ip(request)
        )
        
        # DC Protocol: Single commit for attachment + activity log (atomic operation)
        # PostCommitScheduler will automatically enqueue deferred jobs AFTER this commit
        db.commit()
        db.refresh(attachment)
        
    except HTTPException as e:
        # DC PROTOCOL: Preserve validation errors (UNKNOWN segments, metadata issues)
        # WVV: Re-raise with original status code and message for audit compliance
        db.rollback()
        raise e
    except Exception as e:
        # DC Protocol: Transaction rollback removes BOTH attachment and activity log
        # WVV: Only generic errors (non-validation) reach here
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload {file.filename}: {str(e)}"
        )
    
    # Prepare response message based on compression status
    if upload_result['needs_compression']:
        message = "File uploaded successfully. Compression processing in background..."
    else:
        message = "File uploaded successfully"
    
    return {
        "success": True,
        "message": message,
        "attachment": attachment.to_dict(),
        "compression_queued": upload_result['needs_compression'],
        "compression_job_id": upload_result.get('compression_job_id')
    }


@router.get("/attachments/{attachment_id}/status", summary="Get attachment processing status")
async def get_attachment_status(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get processing status of an attachment (for background compression polling)
    WVV: Real-time status updates for frontend
    
    Returns:
        - attachment: Attachment details
        - background_job: Job status if compression in progress
    """
    # Get attachment
    attachment = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.id == attachment_id,
        StaffTaskAttachment.is_deleted == False
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Verify user has access to this attachment's task
    task = db.query(StaffTask).filter(
        StaffTask.id == attachment.task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check access
    if task.created_by != current_user.id and task.primary_assignee_id != current_user.id:
        secondary = db.query(StaffTaskAssignee).filter(
            StaffTaskAssignee.task_id == task.id,
            StaffTaskAssignee.employee_id == current_user.id
        ).first()
        if not secondary:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get background job status if exists
    from app.services.background_job_service import BackgroundJobService
    from app.models.background_jobs import BackgroundJob
    
    background_job = db.query(BackgroundJob).filter(
        BackgroundJob.job_key == f'compress_attachment_{attachment_id}',
        BackgroundJob.job_type == BackgroundJobService.JOB_TYPE_IMAGE_COMPRESSION
    ).order_by(BackgroundJob.created_at.desc()).first()
    
    response = {
        "success": True,
        "attachment": attachment.to_dict(),
        "background_job": background_job.to_dict() if background_job else None
    }
    
    return response


@router.get("/{task_id}/attachments", summary="Get task attachments")
async def get_task_attachments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all attachments for a task
    DC: Only non-deleted attachments, department scope enforced
    """
    task = db.query(StaffTask).filter(
        StaffTask.id == task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify manager department scope
    verify_manager_task_scope(task, current_user, db)
    
    attachments = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.task_id == task_id,
        StaffTaskAttachment.is_deleted == False
    ).order_by(StaffTaskAttachment.uploaded_at.desc()).all()
    
    return {
        "success": True,
        "attachments": [a.to_dict() for a in attachments]
    }


@router.get("/attachments/{attachment_id}/metadata", summary="Get attachment metadata for preview")
async def get_attachment_metadata(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get attachment metadata for preview modal
    WVV: Returns all display info without transferring file bytes
    DC: Includes uploader info, compression status, department scope enforced
    """
    attachment = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.id == attachment_id,
        StaffTaskAttachment.is_deleted == False
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # DC: Verify manager department scope via parent task
    task = db.query(StaffTask).filter(StaffTask.id == attachment.task_id).first()
    if task:
        verify_manager_task_scope(task, current_user, db)
    
    # Get uploader info
    uploader = db.query(StaffEmployee).filter(
        StaffEmployee.id == attachment.uploaded_by
    ).first()
    
    return {
        "success": True,
        "attachment": {
            "id": attachment.id,
            "task_id": attachment.task_id,
            "file_name": attachment.file_name,
            "file_type": attachment.file_type,
            "file_size": attachment.file_size,
            "compressed_size_bytes": attachment.compressed_size_bytes,
            "has_original": attachment.has_original,
            "has_compressed": attachment.has_compressed,
            "processing_status": attachment.processing_status,
            "uploaded_by": attachment.uploaded_by,
            "uploaded_by_name": uploader.full_name if uploader else "Unknown",
            "uploaded_by_emp_code": uploader.emp_code if uploader else None,
            "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None,
            "storage_tier": attachment.storage_tier
        }
    }


@router.get("/attachments/{attachment_id}/view", summary="View attachment in browser")
async def view_attachment(
    attachment_id: int,
    version: Optional[str] = Query(None, description="Version: 'compressed' or 'original' (default)"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    View task attachment in browser
    DC: Serves file inline (not as download), department scope enforced
    DC: Supports dual evidence - compressed (optimized) or original (full quality)
    WVV: Unicode-safe filename handling
    """
    attachment = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.id == attachment_id,
        StaffTaskAttachment.is_deleted == False
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # DC: Verify manager department scope via parent task
    task = db.query(StaffTask).filter(StaffTask.id == attachment.task_id).first()
    if task:
        verify_manager_task_scope(task, current_user, db)
    
    # DC PROTOCOL: Determine which version to serve (compressed vs original)
    if version == "compressed" and attachment.has_compressed and attachment.compressed_path:
        # Serve compressed version (faster, optimized)
        file_path = Path(attachment.compressed_path)
        if not file_path.exists():
            # Fallback to original if compressed not found
            logger.warning(f"Compressed file not found for attachment {attachment_id}, falling back to original")
            file_path = Path(attachment.file_path)
    else:
        # Serve original version (default, full quality)
        file_path = Path(attachment.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # DC: Use sanitized filename to prevent Unicode encoding errors
    content_disposition = f"inline; {sanitize_filename_for_header(attachment.file_name)}"
    
    return FileResponse(
        path=str(file_path),
        media_type=attachment.file_type,
        headers={"Content-Disposition": content_disposition}
    )


@router.get("/attachments/{attachment_id}/download", summary="Download attachment")
async def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Download task attachment
    DC: Serves file directly from storage as download, department scope enforced
    WVV: Unicode-safe filename handling
    """
    attachment = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.id == attachment_id,
        StaffTaskAttachment.is_deleted == False
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # DC: Verify manager department scope via parent task
    task = db.query(StaffTask).filter(StaffTask.id == attachment.task_id).first()
    if task:
        verify_manager_task_scope(task, current_user, db)
    
    # Check file exists
    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # DC PROTOCOL: Use semantic download filename if available (NEW - Nov 29, 2025)
    # WVV: Fallback to legacy behavior for existing records
    if attachment.uses_new_naming and attachment.download_filename:
        # NEW: Use pre-generated semantic filename (already filesystem-safe)
        # Format: TASK_T40_00024_20251129_063020_MR10009_screenshot.png
        # DC: No further encoding needed (filename already DC-compliant)
        content_disposition = f"attachment; filename=\"{attachment.download_filename}\""
    else:
        # LEGACY: Use sanitized original filename with RFC 2231 encoding (Unicode support)
        content_disposition = f"attachment; {sanitize_filename_for_header(attachment.file_name)}"
    
    return FileResponse(
        path=str(file_path),
        media_type=attachment.file_type,
        headers={"Content-Disposition": content_disposition}
    )


@router.post("/attachments/{attachment_id}/log-preview", summary="Log attachment preview action")
async def log_attachment_preview(
    attachment_id: int,
    request: Request,
    version: Optional[str] = Query("original", description="Version viewed: 'compressed' or 'original'"),
    preview_method: Optional[str] = Query("inline", description="Preview method: 'inline', 'download', 'pdf_tab'"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Log attachment preview action for audit trail
    DC PROTOCOL: Complete audit logging for all preview actions
    WVV: Tracks who viewed what file, when, and how
    """
    attachment = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.id == attachment_id,
        StaffTaskAttachment.is_deleted == False
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # DC: Prepare audit details
    file_size_kb = round(attachment.file_size / 1024, 2)
    compressed_size_kb = round(attachment.compressed_size_bytes / 1024, 2) if attachment.compressed_size_bytes else None
    
    preview_details = {
        "attachment_id": attachment_id,
        "filename": attachment.file_name,
        "file_type": attachment.file_type,
        "original_size_kb": file_size_kb,
        "compressed_size_kb": compressed_size_kb,
        "version_viewed": version,
        "preview_method": preview_method,
        "viewer_name": current_user.full_name,
        "viewer_emp_code": current_user.emp_code
    }
    
    # DC/WVV: Log activity for complete audit trail
    log_task_activity(
        db=db,
        task_id=attachment.task_id,
        employee_id=current_user.id,
        action='attachment_previewed',
        details=preview_details,
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Preview action logged",
        "logged_at": get_indian_time().isoformat()
    }


@router.delete("/attachments/{attachment_id}", summary="Delete attachment")
async def delete_attachment(
    attachment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Soft delete task attachment
    DC: Soft delete only (keeps audit trail), uploader-only permission
    WVV: Verify uploader before deletion, comprehensive activity logging
    """
    attachment = db.query(StaffTaskAttachment).filter(
        StaffTaskAttachment.id == attachment_id,
        StaffTaskAttachment.is_deleted == False
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # WVV: Only uploader can delete (strict permission check)
    if attachment.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Only the person who uploaded this file can delete it"
        )
    
    # DC: Prepare detailed activity log (filename + size for audit trail)
    file_size_kb = round(attachment.file_size / 1024, 2)
    compressed_size_kb = round(attachment.compressed_size_bytes / 1024, 2) if attachment.compressed_size_bytes else None
    
    deletion_details = {
        "filename": attachment.file_name,
        "original_size_kb": file_size_kb,
        "compressed_size_kb": compressed_size_kb,
        "file_type": attachment.file_type,
        "deleted_by_name": current_user.full_name,
        "deleted_by_emp_code": current_user.emp_code
    }
    
    # DC: Soft delete (immutable timestamps)
    attachment.is_deleted = True
    attachment.deleted_at = get_indian_time()
    attachment.deleted_by = current_user.id
    
    # DC/WVV: Log activity with complete details for audit trail
    log_task_activity(
        db=db,
        task_id=attachment.task_id,
        employee_id=current_user.id,
        action='attachment_deleted',
        details=deletion_details,
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    # WVV: Return detailed success response
    return {
        "success": True,
        "message": f"File '{attachment.file_name}' deleted successfully",
        "deleted_file": {
            "filename": attachment.file_name,
            "size_kb": file_size_kb
        }
    }


# ==================== TASK MANAGER REVIEW ENDPOINTS ====================
# DC: Dual Authority - Task assigner (created_by) OR manager can approve
# VGK4U Supreme (150) and HR have global access

from app.models.staff_kra import StaffConfigurableStatus
from app.api.v1.endpoints.staff_task_schemas import (
    TaskManagerApproveRequest, TaskManagerEditRequest,
    TaskManagerRejectRequest, TaskManagerBulkApproveRequest
)


def check_task_approval_authority(db: Session, current_user: StaffEmployee, task: StaffTask) -> bool:
    """
    Check if current user has authority to review/approve this Task
    DC: Tasks - DUAL AUTHORITY (assigner OR manager can approve)
    - Task assigner (created_by) can approve
    - Primary assignee's reporting manager can approve
    - ONLY VGK4U Supreme (150) and HR can approve all
    """
    if not current_user.role:
        return False
    
    # VGK4U Supreme (150) OR HR/EA can approve all
    if current_user.role.hierarchy_level >= 150:
        return True
    if current_user.role.role_name in ['HR', 'Executive Assistant'] or current_user.role.role_code in ['hr', 'ea']:
        return True
    
    # Task assigner (created_by) can approve
    if task.created_by == current_user.id:
        return True
    
    # Check if current user is reporting manager of primary assignee
    primary_assignee = db.query(StaffEmployee).filter(
        StaffEmployee.id == task.primary_assignee_id
    ).first()
    
    if primary_assignee and primary_assignee.reporting_manager_id == current_user.id:
        return True
    
    return False


@router.get("/manager-review/pending", summary="Get pending tasks for manager review")
async def get_pending_tasks_for_review(
    request: Request,
    employee_id: Optional[int] = Query(None, description="Filter by specific employee ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get tasks pending manager review
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED - NO HIERARCHY_LEVEL CHECKS
    - Shows tasks where user is assigner OR in user's reporting chain
    - VGK4U/HR see all pending tasks
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager OR VGK4U/HR OR task assigner
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    is_task_assigner = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.manager_review_status == 'pending_review'
    ).first() is not None
    
    if not is_manager and not is_vgk4u_or_hr and not is_task_assigner:
        raise HTTPException(status_code=403, detail="Only those with direct reports, HR/VGK4U, or task assigners can view pending reviews")
    
    # Build base query
    query = db.query(StaffTask).filter(
        StaffTask.manager_review_status == 'pending_review',
        StaffTask.is_deleted == False,
        StaffTask.status == 'completed'  # Only completed tasks need review
    )
    
    # VGK4U/HR/EA see all
    is_vgk4u_or_hr = (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    team_ids = []
    if not is_vgk4u_or_hr:
        from app.utils.staff_hierarchy import get_team_member_ids as _get_team_ids
        team_ids = _get_team_ids(current_user, db, StaffEmployee)
        
        query = query.filter(
            or_(
                StaffTask.created_by == current_user.id,
                StaffTask.primary_assignee_id.in_(team_ids) if team_ids else False
            )
        )
    
    query = apply_department_scope_to_query(query, current_user, db)
    
    if date_from:
        query = query.filter(StaffTask.completed_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(StaffTask.completed_at <= datetime.combine(date_to, datetime.max.time()))
    
    if employee_id:
        if not is_vgk4u_or_hr:
            # CRITICAL FIX: Reuse the main query (already fully scoped with department + date filters)
            # Extract allowed employee IDs from the SAME query that will be used for results
            allowed_employee_ids = {
                row[0] for row in query.with_entities(StaffTask.primary_assignee_id).distinct().all()
            }
            
            if employee_id not in allowed_employee_ids:
                raise HTTPException(
                    status_code=403,
                    detail=f"You are not authorized to filter by employee {employee_id} (not in your current pending review scope)"
                )
        query = query.filter(StaffTask.primary_assignee_id == employee_id)
    
    pending_tasks = query.order_by(StaffTask.completed_at.desc()).all()
    
    return {
        "pending_count": len(pending_tasks),
        "pending_tasks": [
            {
                "id": t.id,
                "task_code": t.task_code,
                "title": t.title,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "primary_assignee_id": t.primary_assignee_id,
                "primary_assignee_name": t.primary_assignee.full_name if t.primary_assignee else None,
                "created_by": t.created_by,
                "creator_name": t.creator.full_name if t.creator else None,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "progress": t.progress,
                "actual_hours": float(t.actual_hours) if t.actual_hours else 0,
                "completion_notes": t.completion_notes,
                "manager_review_status": t.manager_review_status
            }
            for t in pending_tasks
        ]
    }


@router.post("/manager-review/approve", summary="Approve a completed task")
async def approve_task(
    request_data: TaskManagerApproveRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve a completed task
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    - Dual authority: assigner OR reporting manager can approve
    - Status changes to 'approved', counts for performance
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager OR task assigner OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    # For efficiency, check if user is task assigner for any pending review task
    is_potential_assigner = db.query(StaffTask).filter(
        StaffTask.id == request_data.task_id,
        StaffTask.created_by == current_user.id
    ).first() is not None
    
    if not is_manager and not is_vgk4u_or_hr and not is_potential_assigner:
        raise HTTPException(status_code=403, detail="Only those with direct reports, HR/VGK4U, or task assigners can approve tasks")
    
    task = db.query(StaffTask).filter(
        StaffTask.id == request_data.task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify dual authority
    if not check_task_approval_authority(db, current_user, task):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to approve this task (not assigner or manager of assignee)"
        )
    
    if task.manager_review_status != 'pending_review':
        raise HTTPException(status_code=400, detail=f"Cannot approve task with status: {task.manager_review_status}")
    
    # DC: Verify 'approved' status exists and counts for performance
    approved_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'task',
        StaffConfigurableStatus.status_code == 'approved',
        StaffConfigurableStatus.status == 'active'
    ).first()
    
    if not approved_status:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured in catalog")
    
    if not approved_status.counts_for_performance:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured to count for performance")
    
    # Update status
    task.manager_review_status = 'approved'
    task.manager_reviewed_by_employee_id = current_user.id
    task.manager_review_date = get_indian_time()
    if request_data.notes:
        task.manager_edit_notes = request_data.notes
    
    # Log activity
    log_task_activity(
        db=db,
        task_id=task.id,
        employee_id=current_user.id,
        action='manager_approved',
        details=f"Task approved by {current_user.full_name}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Task approved successfully",
        "task_id": task.id,
        "task_code": task.task_code
    }


@router.post("/manager-review/edit", summary="Edit and auto-approve a task")
async def edit_task_by_manager(
    request_data: TaskManagerEditRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Edit task values and auto-approve
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    - Dual authority: assigner OR reporting manager can edit
    - Stores original values, status changes to 'edited_by_manager'
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager OR task assigner OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    is_potential_assigner = db.query(StaffTask).filter(
        StaffTask.id == request_data.task_id,
        StaffTask.created_by == current_user.id
    ).first() is not None
    
    if not is_manager and not is_vgk4u_or_hr and not is_potential_assigner:
        raise HTTPException(status_code=403, detail="Only those with direct reports, HR/VGK4U, or task assigners can edit tasks")
    
    task = db.query(StaffTask).filter(
        StaffTask.id == request_data.task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify dual authority
    if not check_task_approval_authority(db, current_user, task):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to edit this task (not assigner or manager of assignee)"
        )
    
    if task.manager_review_status not in ['pending_review', 'rejected']:
        raise HTTPException(status_code=400, detail=f"Cannot edit task with status: {task.manager_review_status}")
    
    # DC: Verify 'edited_by_manager' status exists and counts for performance
    edited_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'task',
        StaffConfigurableStatus.status_code == 'edited_by_manager',
        StaffConfigurableStatus.status == 'active'
    ).first()
    
    if not edited_status:
        raise HTTPException(status_code=500, detail="System error: 'edited_by_manager' status not configured in catalog")
    
    if not edited_status.counts_for_performance:
        raise HTTPException(status_code=500, detail="System error: 'edited_by_manager' status not configured to count for performance")
    
    # Store original values
    original_values = {
        "progress": task.progress,
        "actual_hours": float(task.actual_hours) if task.actual_hours else None,
        "completion_notes": task.completion_notes
    }
    task.original_values = original_values
    
    # Apply edits
    if request_data.progress is not None:
        task.progress = request_data.progress
    if request_data.actual_hours is not None:
        task.actual_hours = Decimal(str(request_data.actual_hours))
    if request_data.completion_notes is not None:
        task.completion_notes = request_data.completion_notes
    
    # Update review status
    task.manager_review_status = 'edited_by_manager'
    task.manager_reviewed_by_employee_id = current_user.id
    task.manager_review_date = get_indian_time()
    task.manager_edit_notes = request_data.manager_edit_notes
    
    # Log activity
    log_task_activity(
        db=db,
        task_id=task.id,
        employee_id=current_user.id,
        action='manager_edited',
        details=f"Task edited by {current_user.full_name}. Original: {original_values}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Task edited and approved successfully",
        "task_id": task.id,
        "task_code": task.task_code,
        "original_values": original_values
    }


@router.post("/manager-review/reject", summary="Reject a task")
async def reject_task(
    request_data: TaskManagerRejectRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reject a task
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    - Dual authority: assigner OR reporting manager can reject
    - Status changes to 'rejected', staff must resubmit
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager OR task assigner OR VGK4U/HR
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    is_potential_assigner = db.query(StaffTask).filter(
        StaffTask.id == request_data.task_id,
        StaffTask.created_by == current_user.id
    ).first() is not None
    
    if not is_manager and not is_vgk4u_or_hr and not is_potential_assigner:
        raise HTTPException(status_code=403, detail="Only those with direct reports, HR/VGK4U, or task assigners can reject tasks")
    
    task = db.query(StaffTask).filter(
        StaffTask.id == request_data.task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # DC: Verify dual authority
    if not check_task_approval_authority(db, current_user, task):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to reject this task (not assigner or manager of assignee)"
        )
    
    if task.manager_review_status != 'pending_review':
        raise HTTPException(status_code=400, detail=f"Cannot reject task with status: {task.manager_review_status}")
    
    # DC: Verify 'rejected' status exists and does NOT count for performance
    rejected_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'task',
        StaffConfigurableStatus.status_code == 'rejected',
        StaffConfigurableStatus.status == 'active'
    ).first()
    
    if not rejected_status:
        raise HTTPException(status_code=500, detail="System error: 'rejected' status not configured in catalog")
    
    if rejected_status.counts_for_performance:
        raise HTTPException(status_code=500, detail="System error: 'rejected' status incorrectly configured to count for performance")
    
    # Update status
    task.manager_review_status = 'rejected'
    task.manager_reviewed_by_employee_id = current_user.id
    task.manager_review_date = get_indian_time()
    task.rejection_reason = request_data.rejection_reason
    
    # Log activity
    log_task_activity(
        db=db,
        task_id=task.id,
        employee_id=current_user.id,
        action='manager_rejected',
        details=f"Task rejected by {current_user.full_name}. Reason: {request_data.rejection_reason}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Task rejected. Staff must resubmit for re-approval.",
        "task_id": task.id,
        "task_code": task.task_code
    }


@router.post("/manager-review/bulk-approve", summary="Bulk approve multiple tasks")
async def bulk_approve_tasks(
    request_data: TaskManagerBulkApproveRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Bulk approve multiple tasks
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    - TRANSACTIONAL - All-or-nothing. Validates ALL before mutation.
    - Authority check done per-task in check_task_approval_authority
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager OR VGK4U/HR (bulk approve typically for managers)
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    # For bulk approve, user must be manager or VGK4U/HR - per-task authority checked below
    if not is_manager and not is_vgk4u_or_hr:
        raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can bulk approve tasks")
    
    # Phase 1: Validate all tasks
    validated_tasks = []
    validation_errors = []
    
    for task_id in request_data.task_ids:
        task = db.query(StaffTask).filter(
            StaffTask.id == task_id,
            StaffTask.is_deleted == False
        ).first()
        
        if not task:
            validation_errors.append({"id": task_id, "reason": "Not found"})
            continue
        
        if not check_task_approval_authority(db, current_user, task):
            validation_errors.append({"id": task_id, "reason": "Not authorized (not assigner or manager)"})
            continue
        
        if task.manager_review_status != 'pending_review':
            validation_errors.append({"id": task_id, "reason": f"Invalid status: {task.manager_review_status}"})
            continue
        
        validated_tasks.append(task)
    
    # Fail-fast if any errors
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Bulk approval rejected: {len(validation_errors)} tasks failed validation",
                "failed_count": len(validation_errors),
                "validated_count": len(validated_tasks),
                "validation_errors": validation_errors
            }
        )
    
    # Verify status catalog
    approved_status = db.query(StaffConfigurableStatus).filter(
        StaffConfigurableStatus.category == 'task',
        StaffConfigurableStatus.status_code == 'approved',
        StaffConfigurableStatus.status == 'active'
    ).first()
    
    if not approved_status:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured")
    
    if not approved_status.counts_for_performance:
        raise HTTPException(status_code=500, detail="System error: 'approved' status not configured to count for performance")
    
    # Phase 2: Mutate all tasks
    try:
        approval_time = get_indian_time()
        
        for task in validated_tasks:
            task.manager_review_status = 'approved'
            task.manager_reviewed_by_employee_id = current_user.id
            task.manager_review_date = approval_time
            if request_data.notes:
                task.manager_edit_notes = request_data.notes
            
            log_task_activity(
                db=db,
                task_id=task.id,
                employee_id=current_user.id,
                action='manager_bulk_approved',
                details=f"Task bulk approved by {current_user.full_name}",
                ip_address=get_client_ip(request)
            )
        
        db.commit()
        
        return {
            "success": True,
            "approved_count": len(validated_tasks),
            "failed_count": 0,
            "message": f"Bulk approval successful: {len(validated_tasks)} tasks approved"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Transaction failed, all changes rolled back: {str(e)}"
        )


@router.get("/manager-review/summary", summary="Get manager review summary")
async def get_task_manager_review_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get summary of pending task reviews
    
    DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED
    - Users with direct reports, VGK4U/HR, or pending task approvals can view summary
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    # DC Protocol: Early gate - must be manager OR VGK4U/HR OR task assigner
    is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
    is_vgk4u_or_hr = current_user.role and (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    has_pending = db.query(StaffTask).filter(
        StaffTask.created_by == current_user.id,
        StaffTask.manager_review_status == 'pending_review'
    ).first() is not None
    
    if not is_manager and not is_vgk4u_or_hr and not has_pending:
        raise HTTPException(status_code=403, detail="Only those with direct reports, HR/VGK4U, or pending task reviews can access this")
    
    # Build base query
    query = db.query(StaffTask).filter(
        StaffTask.manager_review_status == 'pending_review',
        StaffTask.is_deleted == False,
        StaffTask.status == 'completed'
    )
    
    # VGK4U/HR/EA see all
    is_vgk4u_or_hr = (
        current_user.role.hierarchy_level >= 150 or
        current_user.role.role_name in ['HR', 'Executive Assistant'] or
        current_user.role.role_code in ['hr', 'ea']
    )
    
    if not is_vgk4u_or_hr:
        from app.utils.staff_hierarchy import get_team_member_ids as _get_team_ids2
        team_ids = _get_team_ids2(current_user, db, StaffEmployee)
        
        query = query.filter(
            or_(
                StaffTask.created_by == current_user.id,
                StaffTask.primary_assignee_id.in_(team_ids) if team_ids else False
            )
        )
    
    query = apply_department_scope_to_query(query, current_user, db)
    
    pending_count = query.count()
    
    return {
        "pending_task_count": pending_count,
        "message": f"You have {pending_count} task(s) pending review"
    }


# ==================== MULTI-STAGE TASK PHASE ENDPOINTS (DC Protocol Dec 21, 2025) ====================

@router.get("/{task_id}/phases", summary="Get phases for a task")
async def get_task_phases(
    task_id: int,
    include_child_tasks: bool = Query(False, description="Include child task details"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all phases for a task
    DC Protocol: Returns phases with optional child task details
    WVV Protocol: Requires staff authentication
    """
    task = db.query(StaffTask).filter(
        StaffTask.id == task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    verify_manager_task_scope(task, current_user, db)
    
    phases = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.parent_task_id == task_id,
        StaffTaskPhase.is_deleted == False
    ).order_by(StaffTaskPhase.phase_number).all()
    
    return {
        "success": True,
        "task_id": task_id,
        "task_code": task.task_code,
        "task_title": task.title,
        "phases": [p.to_dict(include_child_task=include_child_tasks) for p in phases],
        "total": len(phases),
        "completed": sum(1 for p in phases if p.phase_status == 'completed'),
        "progress": int((sum(1 for p in phases if p.phase_status == 'completed') / len(phases)) * 100) if phases else 0
    }


@router.post("/{task_id}/phases", summary="Add phase to existing task")
async def add_task_phase(
    task_id: int,
    phase_data: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Add a new phase to an existing task
    DC Protocol: Auto-creates child task for the phase assignee
    WVV Protocol: Validates assignee and creates audit trail
    """
    task = db.query(StaffTask).filter(
        StaffTask.id == task_id,
        StaffTask.is_deleted == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    verify_manager_task_scope(task, current_user, db)
    
    phase_title = phase_data.get('phase_title', '').strip()
    phase_description = phase_data.get('phase_description', '').strip() or None
    phase_assignee_id = phase_data.get('phase_assignee_id')
    secondary_phase_assignee_ids = phase_data.get('secondary_phase_assignee_ids', [])
    target_date_str = phase_data.get('target_date')
    contact_phone = (phase_data.get('contact_phone') or '').strip() or None
    contact_person_name = (phase_data.get('contact_person_name') or '').strip() or None
    
    if not phase_title or not phase_assignee_id:
        raise HTTPException(status_code=400, detail="phase_title and phase_assignee_id are required")
    
    if len(secondary_phase_assignee_ids) > 2:
        raise HTTPException(status_code=400, detail="Maximum 2 secondary assignees allowed per phase")
    if phase_assignee_id in secondary_phase_assignee_ids:
        raise HTTPException(status_code=400, detail="Primary phase assignee cannot be a secondary assignee")
    
    # DC Protocol (Dec 22, 2025): Calculate next phase number from ALL phases (including deleted)
    # to avoid unique constraint violations on (parent_task_id, phase_number)
    max_phase_result = db.query(func.max(StaffTaskPhase.phase_number)).filter(
        StaffTaskPhase.parent_task_id == task_id
    ).scalar()
    phase_number = (max_phase_result or 0) + 1
    
    phase_assignee = db.query(StaffEmployee).filter(
        StaffEmployee.id == phase_assignee_id,
        StaffEmployee.status == 'active'
    ).first()
    
    if not phase_assignee:
        raise HTTPException(status_code=400, detail="Phase assignee not found or inactive")
    
    target_date = None
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target_date format (use YYYY-MM-DD)")
    
    child_task_code = generate_task_code(db)
    child_task = StaffTask(
        task_code=child_task_code,
        title=f"[Phase {phase_number}] {phase_title}",
        description=phase_description or f"Sub-task of: {task.title}",
        category=task.category,
        priority=task.priority,
        status='pending',
        created_by=current_user.id,
        original_assigner_id=current_user.id,
        primary_assignee_id=phase_assignee_id,
        due_date=target_date,
        start_date=task.start_date,
        tags=['phase-task', f'parent-{task.task_code}']
    )
    db.add(child_task)
    db.flush()
    
    phase = StaffTaskPhase(
        parent_task_id=task_id,
        child_task_id=child_task.id,
        phase_number=phase_number,
        phase_title=phase_title,
        phase_description=phase_description,
        phase_assignee_id=phase_assignee_id,
        target_date=target_date,
        phase_status='pending',
        ordering_token=phase_number * 100,
        contact_phone=contact_phone,
        contact_person_name=contact_person_name,
        created_by=current_user.id
    )
    db.add(phase)
    db.flush()
    
    # DC Protocol (Feb 2026): Add secondary assignees to phase child task
    phase_sec_names = []
    for sec_id in secondary_phase_assignee_ids:
        sec_emp = db.query(StaffEmployee).filter(
            StaffEmployee.id == sec_id, StaffEmployee.status == 'active'
        ).first()
        if not sec_emp:
            raise HTTPException(status_code=400, detail=f"Phase secondary assignee {sec_id} not found or inactive")
        phase_sec_rec = StaffTaskAssignee(
            task_id=child_task.id, employee_id=sec_id,
            assigned_by=current_user.id, role='secondary'
        )
        db.add(phase_sec_rec)
        phase_sec_names.append(sec_emp.full_name)
    
    log_task_activity(
        db=db,
        task_id=child_task.id,
        employee_id=current_user.id,
        action='created',
        details={
            "title": child_task.title,
            "phase_number": phase_number,
            "parent_task_id": task_id,
            "parent_task_code": task.task_code,
            "is_phase_task": True,
            "secondary_assignees": phase_sec_names if phase_sec_names else None
        },
        ip_address=get_client_ip(request)
    )
    
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='updated',
        field_changed='phases',
        new_value=f"Added Phase {phase_number}: {phase_title}",
        details={
            "action_type": "phase_added",
            "phase_id": phase.id,
            "phase_number": phase_number,
            "phase_title": phase_title,
            "assignee_id": phase_assignee_id,
            "assignee_name": phase_assignee.full_name,
            "secondary_assignee_names": phase_sec_names if phase_sec_names else None,
            "child_task_code": child_task_code
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Phase {phase_number} added successfully",
        "phase": phase.to_dict(include_child_task=True)
    }


@router.patch("/{task_id}/phases/{phase_id}", summary="Update phase details")
async def update_task_phase(
    task_id: int,
    phase_id: int,
    update_data: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update a phase (title, description, status, assignee, target date)
    DC Protocol: Status/assignee changes sync bidirectionally with child task
    WVV Protocol: Full audit trail for all changes
    Enhanced: Dec 22, 2025 - Added title, description, assignee reassignment
    """
    phase = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.id == phase_id,
        StaffTaskPhase.parent_task_id == task_id,
        StaffTaskPhase.is_deleted == False
    ).first()
    
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    
    # DC Protocol: Get parent task and verify scope
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Parent task not found")
    
    verify_manager_task_scope(task, current_user, db)
    
    changes = []
    
    if 'phase_title' in update_data:
        new_title = update_data['phase_title'].strip() if update_data['phase_title'] else ''
        if not new_title:
            raise HTTPException(status_code=400, detail="Phase title cannot be empty")
        if len(new_title) > 256:
            raise HTTPException(status_code=400, detail="Phase title must be 256 characters or less")
        if phase.phase_title != new_title:
            old_title = phase.phase_title
            phase.phase_title = new_title
            if phase.child_task_id:
                child_task = db.query(StaffTask).filter(StaffTask.id == phase.child_task_id).first()
                if child_task:
                    child_task.title = f"[Phase {phase.phase_number}] {new_title}"
            changes.append(f"title: {old_title} → {new_title}")
    
    if 'phase_description' in update_data:
        new_desc = update_data['phase_description'].strip() if update_data['phase_description'] else None
        if phase.phase_description != new_desc:
            phase.phase_description = new_desc
            if phase.child_task_id:
                child_task = db.query(StaffTask).filter(StaffTask.id == phase.child_task_id).first()
                if child_task:
                    child_task.description = new_desc or f"Sub-task of: {task.title}"
            changes.append("description updated")
    
    if 'phase_assignee_id' in update_data:
        new_assignee_id = update_data['phase_assignee_id']
        if new_assignee_id and new_assignee_id != phase.phase_assignee_id:
            new_assignee = db.query(StaffEmployee).filter(
                StaffEmployee.id == new_assignee_id,
                StaffEmployee.status == 'active'
            ).first()
            if not new_assignee:
                raise HTTPException(status_code=400, detail="New assignee not found or inactive")
            
            old_assignee = phase.assignee
            old_assignee_name = old_assignee.full_name if old_assignee else "Unknown"
            old_assignee_id = phase.phase_assignee_id
            
            phase.phase_assignee_id = new_assignee_id
            
            if phase.child_task_id:
                child_task = db.query(StaffTask).filter(StaffTask.id == phase.child_task_id).first()
                if child_task:
                    child_task.primary_assignee_id = new_assignee_id
                    log_task_activity(
                        db=db,
                        task_id=child_task.id,
                        employee_id=current_user.id,
                        action='reassigned',
                        field_changed='primary_assignee_id',
                        old_value=old_assignee_name,
                        new_value=new_assignee.full_name,
                        details={
                            "synced_from_phase": True,
                            "phase_id": phase_id,
                            "old_assignee_id": old_assignee_id,
                            "new_assignee_id": new_assignee_id
                        },
                        ip_address=get_client_ip(request)
                    )
            
            # WVV: Also log on parent task for audit trail
            log_task_activity(
                db=db,
                task_id=task_id,
                employee_id=current_user.id,
                action='phase_reassigned',
                field_changed='phase_assignee',
                old_value=old_assignee_name,
                new_value=new_assignee.full_name,
                details={
                    "phase_id": phase_id,
                    "phase_number": phase.phase_number,
                    "old_assignee_id": old_assignee_id,
                    "new_assignee_id": new_assignee_id
                },
                ip_address=get_client_ip(request)
            )
            
            changes.append(f"assignee: {old_assignee_name} → {new_assignee.full_name}")
    
    # DC Protocol (Feb 2026): Handle secondary phase assignee updates on child task
    if 'secondary_phase_assignee_ids' in update_data and phase.child_task_id:
        new_sec_ids = set(update_data['secondary_phase_assignee_ids'] or [])
        if len(new_sec_ids) > 2:
            raise HTTPException(status_code=400, detail="Maximum 2 secondary assignees allowed per phase")
        current_primary = phase.phase_assignee_id
        if current_primary in new_sec_ids:
            raise HTTPException(status_code=400, detail="Primary phase assignee cannot be a secondary assignee")
        
        child_task_obj = db.query(StaffTask).filter(StaffTask.id == phase.child_task_id).first()
        if child_task_obj:
            current_secs = db.query(StaffTaskAssignee).filter(
                StaffTaskAssignee.task_id == phase.child_task_id
            ).all()
            current_sec_ids = {sa.employee_id for sa in current_secs}
            to_add_sec = new_sec_ids - current_sec_ids
            to_remove_sec = current_sec_ids - new_sec_ids
            
            for sec_id in to_remove_sec:
                existing_sa = db.query(StaffTaskAssignee).filter(
                    StaffTaskAssignee.task_id == phase.child_task_id,
                    StaffTaskAssignee.employee_id == sec_id
                ).first()
                if existing_sa:
                    removed_emp = db.query(StaffEmployee).filter(StaffEmployee.id == sec_id).first()
                    db.delete(existing_sa)
                    log_task_activity(
                        db=db, task_id=phase.child_task_id, employee_id=current_user.id,
                        action='removed_assignee',
                        details={"removed_employee_id": sec_id, "removed_employee_name": removed_emp.full_name if removed_emp else str(sec_id), "synced_from_phase": True},
                        ip_address=get_client_ip(request)
                    )
            
            for sec_id in to_add_sec:
                sec_emp = db.query(StaffEmployee).filter(StaffEmployee.id == sec_id, StaffEmployee.status == 'active').first()
                if not sec_emp:
                    raise HTTPException(status_code=400, detail=f"Phase secondary assignee {sec_id} not found or inactive")
                new_sa_rec = StaffTaskAssignee(
                    task_id=phase.child_task_id, employee_id=sec_id,
                    assigned_by=current_user.id, role='secondary'
                )
                db.add(new_sa_rec)
                log_task_activity(
                    db=db, task_id=phase.child_task_id, employee_id=current_user.id,
                    action='assigned',
                    details={"added_employee_id": sec_id, "added_employee_name": sec_emp.full_name, "synced_from_phase": True},
                    ip_address=get_client_ip(request)
                )
            
            if to_add_sec or to_remove_sec:
                changes.append(f"secondary assignees updated (+{len(to_add_sec)}, -{len(to_remove_sec)})")
    
    if 'phase_status' in update_data:
        new_status = update_data['phase_status']
        valid_statuses = ['pending', 'in_progress', 'on_hold', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        if phase.phase_status != new_status:
            old_status = phase.phase_status
            phase.phase_status = new_status
            
            if new_status == 'completed':
                phase.completed_at = get_indian_time()
            elif old_status == 'completed':
                phase.completed_at = None
            
            if phase.child_task_id:
                child_task = db.query(StaffTask).filter(StaffTask.id == phase.child_task_id).first()
                if child_task:
                    status_map = {
                        'pending': 'pending',
                        'in_progress': 'in_progress',
                        'on_hold': 'on_hold',
                        'completed': 'completed',
                        'cancelled': 'cancelled'
                    }
                    child_task.status = status_map.get(new_status, 'pending')
                    if new_status == 'completed':
                        child_task.completed_at = get_indian_time()
                    
                    log_task_activity(
                        db=db,
                        task_id=child_task.id,
                        employee_id=current_user.id,
                        action='status_changed',
                        field_changed='status',
                        old_value=old_status,
                        new_value=new_status,
                        details={"synced_from_phase": True, "phase_id": phase_id},
                        ip_address=get_client_ip(request)
                    )
            
            changes.append(f"status: {old_status} → {new_status}")
    
    if 'contact_phone' in update_data:
        new_phone = update_data['contact_phone'].strip() if update_data['contact_phone'] else None
        if phase.contact_phone != new_phone:
            changes.append(f"contact_phone: {phase.contact_phone or 'none'} → {new_phone or 'none'}")
            phase.contact_phone = new_phone
    
    if 'contact_person_name' in update_data:
        new_cpn = update_data['contact_person_name'].strip() if update_data['contact_person_name'] else None
        if phase.contact_person_name != new_cpn:
            changes.append(f"contact_person: {phase.contact_person_name or 'none'} → {new_cpn or 'none'}")
            phase.contact_person_name = new_cpn
    
    if 'completion_notes' in update_data:
        phase.completion_notes = update_data['completion_notes']
        changes.append("completion_notes updated")
    
    if 'target_date' in update_data:
        new_target = None
        if update_data['target_date']:
            try:
                new_target = date.fromisoformat(update_data['target_date'])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid target_date format")
        phase.target_date = new_target
        changes.append(f"target_date → {new_target}")
    
    if changes:
        log_task_activity(
            db=db,
            task_id=task_id,
            employee_id=current_user.id,
            action='updated',
            field_changed='phase',
            new_value='; '.join(changes),
            details={
                "action_type": "phase_updated",
                "phase_id": phase_id,
                "phase_number": phase.phase_number,
                "changes": changes
            },
            ip_address=get_client_ip(request)
        )
    
    db.commit()
    db.refresh(phase)
    
    return {
        "success": True,
        "message": "Phase updated successfully",
        "phase": phase.to_dict(include_child_task=True)
    }


@router.delete("/{task_id}/phases/{phase_id}", summary="Delete phase")
async def delete_task_phase(
    task_id: int,
    phase_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Soft-delete a phase and its child task
    DC Protocol: Both phase and child task are soft-deleted
    WVV Protocol: Full audit trail
    """
    phase = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.id == phase_id,
        StaffTaskPhase.parent_task_id == task_id,
        StaffTaskPhase.is_deleted == False
    ).first()
    
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if task:
        verify_manager_task_scope(task, current_user, db)
    
    phase.is_deleted = True
    phase.deleted_at = get_indian_time()
    phase.deleted_by = current_user.id
    
    if phase.child_task_id:
        child_task = db.query(StaffTask).filter(StaffTask.id == phase.child_task_id).first()
        if child_task:
            child_task.is_deleted = True
            child_task.deleted_at = get_indian_time()
            child_task.deleted_by = current_user.id
            
            log_task_activity(
                db=db,
                task_id=child_task.id,
                employee_id=current_user.id,
                action='deleted',
                details={"deleted_with_phase": True, "phase_id": phase_id},
                ip_address=get_client_ip(request)
            )
    
    log_task_activity(
        db=db,
        task_id=task_id,
        employee_id=current_user.id,
        action='updated',
        field_changed='phases',
        new_value=f"Deleted Phase {phase.phase_number}: {phase.phase_title}",
        details={
            "action_type": "phase_deleted",
            "phase_id": phase_id,
            "phase_number": phase.phase_number,
            "phase_title": phase.phase_title
        },
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Phase {phase.phase_number} deleted successfully"
    }


def sync_phase_from_child_task(db: Session, child_task_id: int, new_status: str, employee_id: int):
    """
    DC Protocol: Sync phase status when child task status changes
    Called from task update endpoints to maintain bidirectional sync
    """
    phase = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.child_task_id == child_task_id,
        StaffTaskPhase.is_deleted == False
    ).first()
    
    if not phase:
        return None
    
    status_map = {
        'pending': 'pending',
        'in_progress': 'in_progress',
        'on_hold': 'on_hold',
        'under_review': 'in_progress',
        'completed': 'completed',
        'cancelled': 'cancelled'
    }
    
    new_phase_status = status_map.get(new_status, 'pending')
    
    if phase.phase_status != new_phase_status:
        phase.phase_status = new_phase_status
        if new_phase_status == 'completed':
            phase.completed_at = get_indian_time()
        elif phase.phase_status == 'completed':
            phase.completed_at = None
        
        log_task_activity(
            db=db,
            task_id=phase.parent_task_id,
            employee_id=employee_id,
            action='updated',
            field_changed='phase_status',
            new_value=f"Phase {phase.phase_number} status synced: {new_phase_status}",
            details={
                "action_type": "phase_status_synced",
                "phase_id": phase.id,
                "phase_number": phase.phase_number,
                "synced_from_child_task": child_task_id,
                "new_status": new_phase_status
            }
        )
    
    return phase
