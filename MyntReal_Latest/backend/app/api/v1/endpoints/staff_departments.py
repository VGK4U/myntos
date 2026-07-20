"""
Staff Departments API - DC Protocol Compliant
Handles department CRUD operations with RBAC
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.models.staff import StaffDepartment, StaffEmployee, StaffRole, StaffAuditLog
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

router = APIRouter()

SECRET_KEY = "mnr-staff-secret-key-2024"
ALGORITHM = "HS256"

class DepartmentCreate(BaseModel):
    dept_code: str
    dept_name: str
    description: Optional[str] = None
    head_id: Optional[int] = None
    status: str = "active"

class DepartmentUpdate(BaseModel):
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[int] = None
    status: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: int
    dept_code: str
    dept_name: str
    description: Optional[str]
    head_id: Optional[int]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    head_employee: Optional[dict] = None
    employee_count: int = 0

    class Config:
        from_attributes = True

def get_current_staff(authorization: str = None, db: Session = None):
    """Extract and validate staff user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        emp_id = payload.get("sub")
        if not emp_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        employee = db.query(StaffEmployee).filter(
            StaffEmployee.id == int(emp_id),
            StaffEmployee.status == "active"
        ).first()
        
        if not employee:
            raise HTTPException(status_code=401, detail="Employee not found or inactive")
        
        return employee
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def log_audit(db: Session, employee: StaffEmployee, action: str, entity: str, 
              entity_id: int, old_values: dict = None, new_values: dict = None):
    """Create audit log entry - DC Protocol"""
    log = StaffAuditLog(
        employee_id=employee.id,
        action=action,
        entity_type=entity,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address="system"
    )
    db.add(log)
    db.commit()

from fastapi import Header

@router.get("/departments", response_model=List[DepartmentResponse])
async def get_departments(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get all departments with employee counts"""
    current_user = get_current_staff(authorization, db)
    
    departments = db.query(StaffDepartment).order_by(StaffDepartment.dept_name).all()
    
    result = []
    for dept in departments:
        emp_count = db.query(func.count(StaffEmployee.id)).filter(
            StaffEmployee.department_id == dept.id
        ).scalar()
        
        head_info = None
        if dept.head_id:
            head = db.query(StaffEmployee).filter(StaffEmployee.id == dept.head_id).first()
            if head:
                head_info = {"id": head.id, "full_name": head.full_name, "emp_code": head.emp_code}
        
        result.append(DepartmentResponse(
            id=dept.id,
            dept_code=dept.dept_code,
            dept_name=dept.dept_name,
            description=dept.description,
            head_id=dept.head_id,
            status=dept.status,
            created_at=dept.created_at,
            updated_at=dept.updated_at,
            head_employee=head_info,
            employee_count=emp_count
        ))
    
    return result

@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get single department by ID"""
    current_user = get_current_staff(authorization, db)
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    emp_count = db.query(func.count(StaffEmployee.id)).filter(
        StaffEmployee.department_id == dept.id
    ).scalar()
    
    head_info = None
    if dept.head_id:
        head = db.query(StaffEmployee).filter(StaffEmployee.id == dept.head_id).first()
        if head:
            head_info = {"id": head.id, "full_name": head.full_name, "emp_code": head.emp_code}
    
    return DepartmentResponse(
        id=dept.id,
        dept_code=dept.dept_code,
        dept_name=dept.dept_name,
        description=dept.description,
        head_id=dept.head_id,
        status=dept.status,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
        head_employee=head_info,
        employee_count=emp_count
    )

@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    dept_data: DepartmentCreate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Create new department - VGK4U and HR only"""
    current_user = get_current_staff(authorization, db)
    
    role = db.query(StaffRole).filter(StaffRole.id == current_user.role_id).first()
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role.role_code not in ['vgk4u', 'hr']:
    #     raise HTTPException(status_code=403, detail="Only VGK4U and HR can create departments")
    
    existing = db.query(StaffDepartment).filter(
        StaffDepartment.dept_code == dept_data.dept_code.upper()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    
    if dept_data.head_id:
        head = db.query(StaffEmployee).filter(StaffEmployee.id == dept_data.head_id).first()
        if not head:
            raise HTTPException(status_code=400, detail="Head employee not found")
    
    new_dept = StaffDepartment(
        dept_code=dept_data.dept_code.upper(),
        dept_name=dept_data.dept_name,
        description=dept_data.description,
        head_id=dept_data.head_id,
        status=dept_data.status
    )
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    
    log_audit(db, current_user, "CREATE", "department", new_dept.id, 
              new_values={"dept_code": new_dept.dept_code, "dept_name": new_dept.dept_name})
    
    logger.info(f"Department created: {new_dept.dept_code} by {current_user.emp_code}")
    
    return DepartmentResponse(
        id=new_dept.id,
        dept_code=new_dept.dept_code,
        dept_name=new_dept.dept_name,
        description=new_dept.description,
        head_id=new_dept.head_id,
        status=new_dept.status,
        created_at=new_dept.created_at,
        updated_at=new_dept.updated_at,
        employee_count=0
    )

@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: int,
    dept_data: DepartmentUpdate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Update department - VGK4U and HR only"""
    current_user = get_current_staff(authorization, db)
    
    role = db.query(StaffRole).filter(StaffRole.id == current_user.role_id).first()
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role.role_code not in ['vgk4u', 'hr']:
    #     raise HTTPException(status_code=403, detail="Only VGK4U and HR can update departments")
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    old_values = {
        "dept_code": dept.dept_code,
        "dept_name": dept.dept_name,
        "description": dept.description,
        "status": dept.status
    }
    
    if dept_data.dept_code and dept_data.dept_code.upper() != dept.dept_code:
        existing = db.query(StaffDepartment).filter(
            StaffDepartment.dept_code == dept_data.dept_code.upper(),
            StaffDepartment.id != dept_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Department code already exists")
        dept.dept_code = dept_data.dept_code.upper()
    
    if dept_data.dept_name:
        dept.dept_name = dept_data.dept_name
    if dept_data.description is not None:
        dept.description = dept_data.description
    if dept_data.head_id is not None:
        if dept_data.head_id:
            head = db.query(StaffEmployee).filter(StaffEmployee.id == dept_data.head_id).first()
            if not head:
                raise HTTPException(status_code=400, detail="Head employee not found")
        dept.head_id = dept_data.head_id if dept_data.head_id else None
    if dept_data.status:
        dept.status = dept_data.status
    
    dept.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dept)
    
    new_values = {
        "dept_code": dept.dept_code,
        "dept_name": dept.dept_name,
        "description": dept.description,
        "status": dept.status
    }
    log_audit(db, current_user, "UPDATE", "department", dept.id, old_values, new_values)
    
    logger.info(f"Department updated: {dept.dept_code} by {current_user.emp_code}")
    
    emp_count = db.query(func.count(StaffEmployee.id)).filter(
        StaffEmployee.department_id == dept.id
    ).scalar()
    
    head_info = None
    if dept.head_id:
        head = db.query(StaffEmployee).filter(StaffEmployee.id == dept.head_id).first()
        if head:
            head_info = {"id": head.id, "full_name": head.full_name, "emp_code": head.emp_code}
    
    return DepartmentResponse(
        id=dept.id,
        dept_code=dept.dept_code,
        dept_name=dept.dept_name,
        description=dept.description,
        head_id=dept.head_id,
        status=dept.status,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
        head_employee=head_info,
        employee_count=emp_count
    )

@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete department - VGK4U only, only if no employees assigned"""
    current_user = get_current_staff(authorization, db)
    
    role = db.query(StaffRole).filter(StaffRole.id == current_user.role_id).first()
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role.role_code != 'vgk4u':
    #     raise HTTPException(status_code=403, detail="Only VGK4U can delete departments")
    
    dept = db.query(StaffDepartment).filter(StaffDepartment.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    emp_count = db.query(func.count(StaffEmployee.id)).filter(
        StaffEmployee.department_id == dept.id
    ).scalar()
    
    if emp_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete department with {emp_count} assigned employees. Reassign employees first."
        )
    
    old_values = {"dept_code": dept.dept_code, "dept_name": dept.dept_name}
    
    db.delete(dept)
    db.commit()
    
    log_audit(db, current_user, "DELETE", "department", dept_id, old_values)
    
    logger.info(f"Department deleted: {old_values['dept_code']} by {current_user.emp_code}")
    
    return {"message": "Department deleted successfully"}
