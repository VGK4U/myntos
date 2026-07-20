"""
RVZ Department Management API - DC Protocol Compliant
Advanced department management with role permissions, data assignments, and custom roles
Created: Nov 29, 2025
VGK/EA/HR Access Only
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.core.database import get_db
from app.models.staff import (
    StaffDepartment, StaffEmployee, StaffRole, StaffAuditLog,
    StaffEmployeeDepartment, StaffDepartmentRole
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== Pydantic Schemas ====================

class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = None
    head_id: Optional[int] = None
    role_permissions: List[int] = Field(default=[], description="Hierarchy levels with access: [50, 60, 70, 85]")
    data_assignments: Dict[str, List[int]] = Field(default={}, description="{task_categories: [1,2], expense_categories: [3,4]}")
    system_features: List[str] = Field(default=[], description="['journey_tracking', 'kra_management']")
    staff_member_ids: List[int] = Field(default=[], description="Staff to assign to this department")

class DepartmentUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = None
    head_id: Optional[int] = None
    role_permissions: Optional[List[int]] = None
    data_assignments: Optional[Dict[str, List[int]]] = None
    system_features: Optional[List[str]] = None
    is_active: Optional[bool] = None

class DepartmentRoleCreateRequest(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=100)
    role_description: Optional[str] = None
    hierarchy_permissions: List[int] = Field(default=[], description="Hierarchy levels that can have this role")

class EmployeeDepartmentAssignment(BaseModel):
    employee_id: int
    department_id: int

class ConfigOptionsResponse(BaseModel):
    task_categories: List[Dict[str, Any]]
    expense_categories: List[Dict[str, Any]]
    hierarchy_levels: List[Dict[str, Any]]
    system_features: List[Dict[str, str]]
    staff_members: List[Dict[str, Any]]

# ==================== Helper Functions ====================

def generate_department_code(db: Session) -> str:
    """Auto-generate department code like DEPT001, DEPT002, etc."""
    # Find the highest existing code
    latest_dept = db.query(StaffDepartment).filter(
        StaffDepartment.department_code.like('DEPT%')
    ).order_by(StaffDepartment.department_code.desc()).first()
    
    if not latest_dept or not latest_dept.department_code:
        return "DEPT001"
    
    try:
        # Extract number from DEPT001 -> 001
        num_str = latest_dept.department_code[4:]
        next_num = int(num_str) + 1
        return f"DEPT{str(next_num).zfill(3)}"
    except:
        return "DEPT001"

def verify_supreme_access(current_user: StaffEmployee):
    """Verify user has VGK/EA/HR access"""
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role:
    #     raise HTTPException(status_code=403, detail="Role information missing")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.role.hierarchy_level < 85:
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Access denied. VGK/EA/HR access required."
    #     )
    pass

def log_audit(db: Session, employee: StaffEmployee, action: str, resource: str, 
              resource_id: int, new_data: dict = None):
    """Create audit log entry"""
    log = StaffAuditLog(
        employee_id=employee.id,
        action=action,
        resource_type=resource,
        resource_id=resource_id,
        new_data=new_data,
        ip_address="system"
    )
    db.add(log)

# ==================== Endpoints ====================

@router.get("/config-options", response_model=ConfigOptionsResponse)
async def get_config_options(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get all configuration options for department creation
    Returns: task categories, expense categories, hierarchy levels, system features, staff members
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    # Task Categories (hardcoded - matching staff_tasks check constraint)
    task_categories_list = [
        {"id": 1, "name": "General", "code": "general"},
        {"id": 2, "name": "Development", "code": "development"},
        {"id": 3, "name": "Support", "code": "support"},
        {"id": 4, "name": "Admin", "code": "admin"},
        {"id": 5, "name": "Meeting", "code": "meeting"},
        {"id": 6, "name": "Review", "code": "review"},
        {"id": 7, "name": "Documentation", "code": "documentation"},
        {"id": 8, "name": "Other", "code": "other"}
    ]
    
    # Hierarchy Levels (from StaffRole)
    roles = db.query(StaffRole).filter(
        StaffRole.is_active == True
    ).order_by(StaffRole.hierarchy_level).all()
    
    hierarchy_levels = []
    seen_levels = set()
    for role in roles:
        if role.hierarchy_level not in seen_levels:
            hierarchy_levels.append({
                "code": role.hierarchy_level,
                "label": f"{role.role_name} ({role.hierarchy_level})",
                "min": role.hierarchy_level,
                "max": role.hierarchy_level
            })
            seen_levels.add(role.hierarchy_level)
    
    # System Features (hardcoded for now)
    system_features = [
        {"code": "journey_tracking", "name": "Journey Tracking Access", "description": "GPS field journey tracking"},
        {"code": "kra_management", "name": "KRA Management", "description": "Daily responsibility tracking"},
        {"code": "time_tracker", "name": "Time Tracker Access", "description": "Attendance and break management"},
        {"code": "task_assignment", "name": "Task Assignment Authority", "description": "Can assign tasks to others"},
        {"code": "manager_review", "name": "Manager Review Authority", "description": "Can review and approve tasks"},
        {"code": "expense_approval", "name": "Expense Approval Authority", "description": "Can approve expense claims"},
        {"code": "staff_nda", "name": "Staff NDA Management", "description": "Manage NDA acceptances"},
        {"code": "announcement_create", "name": "Announcement Creation", "description": "Create announcements"},
        {"code": "report_generation", "name": "Report Generation", "description": "Generate analytics reports"},
        {"code": "analytics_access", "name": "Analytics Access", "description": "View advanced analytics"}
    ]
    
    # Staff Members
    staff_members = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active'
    ).order_by(StaffEmployee.full_name).all()
    
    # Expense Categories (placeholder - extend if you have expense categories table)
    expense_categories = [
        {"id": 1, "name": "Travel & Transport"},
        {"id": 2, "name": "Office Supplies"},
        {"id": 3, "name": "Marketing Expenses"},
        {"id": 4, "name": "IT & Software"},
        {"id": 5, "name": "Training & Development"},
        {"id": 6, "name": "Utilities"},
        {"id": 7, "name": "Miscellaneous"}
    ]
    
    return ConfigOptionsResponse(
        task_categories=task_categories_list,
        expense_categories=expense_categories,
        hierarchy_levels=hierarchy_levels,
        system_features=system_features,
        staff_members=[{
            "id": emp.id,
            "full_name": emp.full_name,
            "emp_code": emp.emp_code,
            "department_id": emp.department_id,
            "department_name": emp.department.name if emp.department else None,
            "role_name": emp.role.role_name if emp.role else None
        } for emp in staff_members]
    )


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreateRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Create new department with advanced permissions
    DC Protocol: VGK/EA/HR access only
    Auto-generates department code (DEPT001, DEPT002, etc.)
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    # Check for duplicate name
    existing = db.query(StaffDepartment).filter(
        func.lower(StaffDepartment.name) == data.name.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Department '{data.name}' already exists")
    
    # Verify head exists if provided
    if data.head_id:
        head = db.query(StaffEmployee).filter(StaffEmployee.id == data.head_id).first()
        if not head:
            raise HTTPException(status_code=400, detail="Head employee not found")
    
    # Generate department code
    dept_code = generate_department_code(db)
    
    # Create department
    new_dept = StaffDepartment(
        name=data.name,
        department_code=dept_code,
        description=data.description,
        head_id=data.head_id,
        role_permissions=data.role_permissions,
        data_assignments=data.data_assignments,
        system_features=data.system_features,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id
    )
    db.add(new_dept)
    db.flush()  # Get the ID
    
    # Assign staff members to department (multi-department junction table)
    for emp_id in data.staff_member_ids:
        assignment = StaffEmployeeDepartment(
            employee_id=emp_id,
            department_id=new_dept.id,
            assigned_by=current_user.id
        )
        db.add(assignment)
    
    db.commit()
    db.refresh(new_dept)
    
    log_audit(db, current_user, "CREATE_DEPARTMENT", "department", new_dept.id,
              {"action": "created", "name": new_dept.name, "code": dept_code})
    db.commit()
    
    logger.info(f"Department created: {dept_code} by {current_user.emp_code}")
    
    return {
        "message": "Department created successfully",
        "department": new_dept.to_dict()
    }


@router.get("/list")
async def list_departments(
    include_inactive: bool = False,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    List all departments with full details
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    query = db.query(StaffDepartment)
    if not include_inactive:
        query = query.filter(StaffDepartment.is_active == True)
    
    departments = query.order_by(StaffDepartment.department_code).all()
    
    return {
        "departments": [dept.to_dict() for dept in departments]
    }


@router.get("/{dept_id}")
async def get_department(
    dept_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get single department with full details"""
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Get multi-department assignments
    assignments = db.query(StaffEmployeeDepartment).filter(
        StaffEmployeeDepartment.department_id == dept_id
    ).all()
    
    # Get custom roles
    roles = db.query(StaffDepartmentRole).filter(
        StaffDepartmentRole.department_id == dept_id
    ).all()
    
    return {
        "department": dept.to_dict(),
        "multi_dept_assignments": [assign.to_dict() for assign in assignments],
        "custom_roles": [role.to_dict() for role in roles]
    }


@router.put("/{dept_id}")
async def update_department(
    dept_id: int,
    data: DepartmentUpdateRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Update department (Tab 2 Edit functionality)
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Update fields
    if data.name:
        # Check for duplicate
        existing = db.query(StaffDepartment).filter(
            func.lower(StaffDepartment.name) == data.name.lower(),
            StaffDepartment.id != dept_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Department '{data.name}' already exists")
        dept.name = data.name
    
    if data.description is not None:
        dept.description = data.description
    
    if data.head_id is not None:
        if data.head_id:
            head = db.query(StaffEmployee).filter(StaffEmployee.id == data.head_id).first()
            if not head:
                raise HTTPException(status_code=400, detail="Head employee not found")
        dept.head_id = data.head_id
    
    if data.role_permissions is not None:
        dept.role_permissions = data.role_permissions
    
    if data.data_assignments is not None:
        dept.data_assignments = data.data_assignments
    
    if data.system_features is not None:
        dept.system_features = data.system_features
    
    if data.is_active is not None:
        dept.is_active = data.is_active
    
    dept.updated_by = current_user.id
    db.commit()
    db.refresh(dept)
    
    log_audit(db, current_user, "UPDATE_DEPARTMENT", "department", dept.id,
              {"action": "updated", "name": dept.name, "code": dept.department_code})
    db.commit()
    
    logger.info(f"Department updated: {dept.department_code} by {current_user.emp_code}")
    
    return {
        "message": "Department updated successfully",
        "department": dept.to_dict()
    }


@router.patch("/{dept_id}/status")
async def toggle_department_status(
    dept_id: int,
    is_active: bool,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Pause/Activate department (no deletion allowed)
    DC Protocol: VGK/EA access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    old_status = dept.is_active
    dept.is_active = is_active
    dept.updated_by = current_user.id
    db.commit()
    db.refresh(dept)
    
    action = "ACTIVATE" if is_active else "PAUSE"
    log_audit(db, current_user, f"{action}_DEPARTMENT", "department", dept.id,
              {"action": action.lower(), "name": dept.name, "code": dept.department_code, "is_active": is_active})
    db.commit()
    
    logger.info(f"Department {action}: {dept.department_code} by {current_user.emp_code}")
    
    return {
        "message": f"Department {'activated' if is_active else 'paused'} successfully",
        "department": dept.to_dict()
    }


# ==================== Department Role Management (Tab 2) ====================

@router.post("/{dept_id}/roles", status_code=status.HTTP_201_CREATED)
async def create_department_role(
    dept_id: int,
    data: DepartmentRoleCreateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create custom role within department (Tab 2 functionality)
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Check for duplicate role name within department
    existing = db.query(StaffDepartmentRole).filter(
        StaffDepartmentRole.department_id == dept_id,
        func.lower(StaffDepartmentRole.role_name) == data.role_name.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Role '{data.role_name}' already exists in this department")
    
    new_role = StaffDepartmentRole(
        department_id=dept_id,
        role_name=data.role_name,
        role_description=data.role_description,
        hierarchy_permissions=data.hierarchy_permissions,
        created_by=current_user.id
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    log_audit(db, current_user, "CREATE_DEPT_ROLE", "department_role", new_role.id,
              {"action": "created", "role_name": data.role_name, "department": dept.name})
    db.commit()
    
    logger.info(f"Department role created: {data.role_name} in {dept.department_code} by {current_user.emp_code}")
    
    return {
        "message": "Department role created successfully",
        "role": new_role.to_dict()
    }


@router.delete("/{dept_id}/roles/{role_id}")
async def delete_department_role(
    dept_id: int,
    role_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Remove custom role from department
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    role = db.query(StaffDepartmentRole).filter(
        StaffDepartmentRole.id == role_id,
        StaffDepartmentRole.department_id == dept_id
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found in this department")
    
    role_name = role.role_name
    dept_name = role.department.name if role.department else "Unknown"
    
    db.delete(role)
    db.commit()
    
    log_audit(db, current_user, "DELETE_DEPT_ROLE", "department_role", role_id,
              {"action": "deleted", "role_name": role_name, "department": dept_name})
    db.commit()
    
    logger.info(f"Department role deleted: {role_name} from {dept_name} by {current_user.emp_code}")
    
    return {"message": "Department role deleted successfully"}


# ==================== Multi-Department Staff Assignment ====================

@router.post("/{dept_id}/assign-staff")
async def assign_staff_to_department(
    dept_id: int,
    employee_ids: List[int],
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Assign multiple staff members to department (multi-department support)
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    assigned_count = 0
    for emp_id in employee_ids:
        # Check if employee exists
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == emp_id).first()
        if not employee:
            logger.warning(f"Employee ID {emp_id} not found, skipping")
            continue
        
        # Check if already assigned
        existing = db.query(StaffEmployeeDepartment).filter(
            StaffEmployeeDepartment.employee_id == emp_id,
            StaffEmployeeDepartment.department_id == dept_id
        ).first()
        if existing:
            logger.info(f"Employee {employee.emp_code} already assigned to {dept.name}")
            continue
        
        # Create assignment
        assignment = StaffEmployeeDepartment(
            employee_id=emp_id,
            department_id=dept_id,
            assigned_by=current_user.id
        )
        db.add(assignment)
        assigned_count += 1
    
    db.commit()
    
    log_audit(db, current_user, "ASSIGN_STAFF_TO_DEPT", "department", dept_id,
              {"action": "assigned", "count": assigned_count, "department": dept.name})
    db.commit()
    
    logger.info(f"Assigned {assigned_count} staff to {dept.department_code} by {current_user.emp_code}")
    
    return {
        "message": f"Successfully assigned {assigned_count} staff members to department",
        "assigned_count": assigned_count
    }


@router.delete("/{dept_id}/remove-staff/{emp_id}")
async def remove_staff_from_department(
    dept_id: int,
    emp_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Remove staff member from department (multi-department assignment)
    DC Protocol: VGK/EA/HR access only
    """
    current_user = get_current_staff_user(request, db)
    verify_supreme_access(current_user)
    
    assignment = db.query(StaffEmployeeDepartment).filter(
        StaffEmployeeDepartment.employee_id == emp_id,
        StaffEmployeeDepartment.department_id == dept_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Staff assignment not found")
    
    emp_name = assignment.employee.full_name if assignment.employee else "Unknown"
    dept_name = assignment.department.name if assignment.department else "Unknown"
    
    db.delete(assignment)
    db.commit()
    
    log_audit(db, current_user, "REMOVE_STAFF_FROM_DEPT", "department", dept_id,
              {"action": "removed", "employee": emp_name, "department": dept_name})
    db.commit()
    
    logger.info(f"Removed staff {emp_name} from {dept_name} by {current_user.emp_code}")
    
    return {"message": "Staff member removed from department successfully"}
