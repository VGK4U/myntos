"""
CRM Settings & Handler-based Lead Routing API Endpoints
Provides full REST lifecycle for Categories and Handlers configuration.
Strictly authorized to: MR1001, VGK4U Supreme, and Yashwanth.
Created: Sep 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import logging

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee, StaffDepartment, StaffRole
from app.models.staff_accounts import AssociatedCompany
from app.models.signup_category import SignupCategory
from app.models.crm_handler import CRMLeadHandler, CRMLeadHandlerMember, CRMLeadHandlerAudit

logger = logging.getLogger(__name__)
router = APIRouter()


def is_crm_settings_authorized(employee: StaffEmployee) -> bool:
    """
    Canonical server-authoritative authorization check for CRM Settings.
    Strictly restricted to:
    1. MR1001 / MR10001 (Employee ID 1)
    2. VGK4U Supreme / Supreme account (is_supreme=True, role='vgk4u'/'super_admin', staff_type='VGK4U'/'VGK4U Supreme')
    3. Yashwanth (MR10016 / Employee ID 16 / 'Yaswanth')
    """
    if not employee:
        return False
    
    emp_code = (getattr(employee, 'emp_code', '') or '').strip().upper()
    full_name_lower = (
        getattr(employee, 'full_name', '') or 
        f"{getattr(employee, 'first_name', '') or ''} {getattr(employee, 'last_name', '') or ''}"
    ).strip().lower()
    is_supreme = getattr(employee, 'is_supreme', False)
    staff_type = (getattr(employee, 'staff_type', '') or '').strip().upper()
    
    role_code = ''
    if hasattr(employee, 'role') and employee.role:
        role_code = (getattr(employee.role, 'role_code', '') or '').strip().lower()

    if (
        emp_code in ('MR10001', 'MR1001', 'MR10016') or
        employee.id in (1, 16) or
        is_supreme is True or
        'yaswanth' in full_name_lower or
        'yashwanth' in full_name_lower or
        role_code in ('vgk4u', 'super_admin') or
        staff_type in ('VGK4U', 'VGK4U SUPREME', 'RVZ_SUPREME')
    ):
        return True
    
    return False


def enforce_crm_settings_access(current_employee: StaffEmployee = Depends(get_current_staff_user)) -> StaffEmployee:
    """Dependency that raises 403 Forbidden if staff member is not authorized for CRM Settings."""
    if not is_crm_settings_authorized(current_employee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: CRM Settings is strictly restricted to MR1001, VGK4U Supreme, and Yashwanth."
        )
    return current_employee


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────────────────────────────────────

class HandlerCreateRequest(BaseModel):
    company_id: int = Field(..., description="Target Company ID")
    department_id: int = Field(..., description="Target Department ID")
    category_id: int = Field(..., description="Target Category/Segment ID")
    employee_ids: Optional[List[int]] = Field(default=None, description="Active Staff Employee IDs for the handler team")
    member_ids: Optional[List[int]] = Field(default=None, description="Alias for employee_ids")
    is_active: bool = Field(default=True, description="Active status")


class HandlerUpdateRequest(BaseModel):
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    category_id: Optional[int] = None
    employee_ids: Optional[List[int]] = None
    member_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/access-check")
def check_access(
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Check if authenticated staff member has permission to access CRM Settings."""
    authorized = is_crm_settings_authorized(current_employee)
    return {
        "success": True,
        "authorized": authorized,
        "access_granted": authorized,
        "staff": {
            "id": current_employee.id,
            "emp_code": current_employee.emp_code,
            "name": current_employee.full_name or f"{current_employee.first_name or ''} {current_employee.last_name or ''}".strip(),
            "staff_type": current_employee.staff_type,
            "is_supreme": getattr(current_employee, 'is_supreme', False)
        }
    }


@router.get("/options")
def get_handler_options(
    company_id: Optional[int] = Query(None, description="Optional Company ID to filter categories"),
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """
    Returns active master data for Handler configuration:
    - Active Companies (from associated_companies)
    - Active Departments (from staff_departments)
    - Active Categories / Segments (from signup_categories)
    - Active Staff Employees (from staff_employees)
    """
    # 1. Active Companies
    companies = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_active == True
    ).order_by(AssociatedCompany.id).all()
    company_list = [
        {"id": c.id, "company_name": c.company_name, "company_code": getattr(c, 'company_code', '')}
        for c in companies
    ]

    # 2. Active Departments
    departments = db.query(StaffDepartment).filter(
        StaffDepartment.is_active == True
    ).order_by(StaffDepartment.name).all()
    dept_list = [
        {"id": d.id, "name": d.name, "description": d.description}
        for d in departments
    ]

    # 3. Active Categories
    cat_query = db.query(SignupCategory).filter(SignupCategory.is_active == True)
    if company_id:
        cat_query = cat_query.filter(SignupCategory.company_id == company_id)
    categories = cat_query.order_by(SignupCategory.name, SignupCategory.id).all()
    
    # If filtered by company_id and no categories found for that company, fallback to distinct active categories
    if not categories:
        categories = db.query(SignupCategory).filter(SignupCategory.is_active == True).order_by(SignupCategory.name).all()
    
    seen_cats = set()
    cat_list = []
    for c in categories:
        # Include company info
        cat_list.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "company_id": c.company_id,
            "icon": c.icon or "fas fa-tag"
        })

    # 4. Active Employees (excluding deleted/resigned)
    employees = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        or_(StaffEmployee.is_deleted.is_(False), StaffEmployee.is_deleted.is_(None))
    ).order_by(StaffEmployee.emp_code).all()

    # Map department IDs and roles
    dept_map = {d.id: d.name for d in departments}
    role_ids = {e.role_id for e in employees if e.role_id}
    roles = db.query(StaffRole).filter(StaffRole.id.in_(role_ids)).all() if role_ids else []
    role_map = {r.id: r.role_name for r in roles}

    emp_list = []
    for e in employees:
        emp_list.append({
            "id": e.id,
            "emp_code": e.emp_code,
            "full_name": e.full_name or f"{e.first_name or ''} {e.last_name or ''}".strip() or e.emp_code,
            "department_id": e.department_id,
            "department_name": dept_map.get(e.department_id, "—"),
            "role_id": e.role_id,
            "role_name": role_map.get(e.role_id, getattr(e, 'designation', '—') or 'Staff'),
            "designation": getattr(e, 'designation', '') or '—',
            "email": e.email or ''
        })

    options_payload = {
        "companies": company_list,
        "departments": dept_list,
        "categories": cat_list,
        "active_staff": emp_list,
        "employees": emp_list
    }

    return {
        "success": True,
        "data": options_payload,
        "companies": company_list,
        "departments": dept_list,
        "categories": cat_list,
        "active_staff": emp_list,
        "employees": emp_list
    }


@router.get("/handlers")
def list_handlers(
    company_id: Optional[int] = Query(None, description="Optional Company ID filter"),
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """List all CRM Handler configurations with associated active team members."""
    query = db.query(CRMLeadHandler)
    if company_id:
        query = query.filter(CRMLeadHandler.company_id == company_id)
    
    handlers = query.order_by(CRMLeadHandler.company_id, CRMLeadHandler.department_id, CRMLeadHandler.category_id).all()

    # Fetch lookup maps
    co_map = {c.id: c.company_name for c in db.query(AssociatedCompany).all()}
    dept_map = {d.id: d.name for d in db.query(StaffDepartment).all()}
    cat_map = {c.id: c.name for c in db.query(SignupCategory).all()}
    
    # Collect all member employee IDs
    all_emp_ids = set()
    for h in handlers:
        for m in h.members:
            all_emp_ids.add(m.employee_id)

    emp_dict = {}
    if all_emp_ids:
        emps = db.query(StaffEmployee).filter(StaffEmployee.id.in_(all_emp_ids)).all()
        r_ids = {e.role_id for e in emps if e.role_id}
        r_map = {r.id: r.role_name for r in db.query(StaffRole).filter(StaffRole.id.in_(r_ids)).all()} if r_ids else {}
        for e in emps:
            emp_dict[e.id] = {
                "id": e.id,
                "emp_code": e.emp_code,
                "full_name": e.full_name or f"{e.first_name or ''} {e.last_name or ''}".strip() or e.emp_code,
                "department_name": dept_map.get(e.department_id, "—"),
                "designation": getattr(e, 'designation', '') or '—',
                "role_name": r_map.get(e.role_id, 'Staff'),
                "status": e.status
            }

    results = []
    for h in handlers:
        member_list = []
        for m in h.members:
            emp_info = emp_dict.get(m.employee_id, {
                "id": m.employee_id,
                "emp_code": f"EMP#{m.employee_id}",
                "full_name": f"Employee #{m.employee_id}",
                "department_name": "—",
                "designation": "—",
                "role_name": "—",
                "status": "unknown"
            })
            member_list.append({
                "id": m.id,
                "employee_id": m.employee_id,
                "is_active": m.is_active,
                "emp_code": emp_info["emp_code"],
                "full_name": emp_info["full_name"],
                "department_name": emp_info["department_name"],
                "designation": emp_info["designation"],
                "role_name": emp_info["role_name"],
                "employee_status": emp_info["status"]
            })

        results.append({
            "id": h.id,
            "company_id": h.company_id,
            "company_name": co_map.get(h.company_id, f"Company #{h.company_id}"),
            "department_id": h.department_id,
            "department_name": dept_map.get(h.department_id, f"Department #{h.department_id}"),
            "category_id": h.category_id,
            "category_name": cat_map.get(h.category_id, f"Category #{h.category_id}"),
            "is_active": h.is_active,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "updated_at": h.updated_at.isoformat() if h.updated_at else None,
            "members": member_list
        })

    return {
        "success": True,
        "total": len(results),
        "data": results
    }


@router.post("/handlers")
def create_handler(
    payload: HandlerCreateRequest,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """
    Create a new CRM Handler mapping for Company + Department + Segment/Category -> Associated Team.
    Prevents duplicate mappings.
    """
    # 1. Validate Company
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.id == payload.company_id,
        AssociatedCompany.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=400, detail="Selected company is invalid or inactive.")

    # 2. Validate Department
    department = db.query(StaffDepartment).filter(
        StaffDepartment.id == payload.department_id,
        StaffDepartment.is_active == True
    ).first()
    if not department:
        raise HTTPException(status_code=400, detail="Selected department is invalid or inactive.")

    # 3. Validate Category
    category = db.query(SignupCategory).filter(
        SignupCategory.id == payload.category_id,
        SignupCategory.is_active == True
    ).first()
    if not category:
        raise HTTPException(status_code=400, detail="Selected category/segment is invalid or inactive.")

    # 4. Check for duplicate mapping
    existing = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id == payload.company_id,
        CRMLeadHandler.department_id == payload.department_id,
        CRMLeadHandler.category_id == payload.category_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Handler configuration for {company.company_name} > {department.name} > {category.name} already exists."
        )

    # 5. Create Handler Entity
    handler = CRMLeadHandler(
        company_id=payload.company_id,
        department_id=payload.department_id,
        category_id=payload.category_id,
        is_active=payload.is_active,
        created_by_id=admin_user.id
    )
    db.add(handler)
    db.flush()

    # 6. Attach Members
    added_members = []
    input_emp_ids = payload.employee_ids if payload.employee_ids is not None else payload.member_ids
    if input_emp_ids:
        # Validate active employees
        valid_emps = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(input_emp_ids),
            StaffEmployee.status == 'active',
            or_(StaffEmployee.is_deleted.is_(False), StaffEmployee.is_deleted.is_(None))
        ).all()
        valid_emp_ids = {e.id for e in valid_emps}

        for emp_id in input_emp_ids:
            if emp_id in valid_emp_ids:
                member = CRMLeadHandlerMember(
                    handler_id=handler.id,
                    employee_id=emp_id,
                    is_active=True,
                    created_by_id=admin_user.id
                )
                db.add(member)
                added_members.append(emp_id)

    # 7. Audit Log
    audit = CRMLeadHandlerAudit(
        handler_id=handler.id,
        action="CREATE",
        details=json.dumps({
            "company_id": payload.company_id,
            "company_name": company.company_name,
            "department_id": payload.department_id,
            "department_name": department.name,
            "category_id": payload.category_id,
            "category_name": category.name,
            "member_ids": added_members,
            "is_active": payload.is_active
        }),
        performed_by_id=admin_user.id
    )
    db.add(audit)

    db.commit()
    db.refresh(handler)

    return {
        "success": True,
        "message": f"Handler configured successfully for {company.company_name} > {department.name} > {category.name}",
        "data": handler.to_dict()
    }


@router.put("/handlers/{handler_id}")
def update_handler(
    handler_id: int,
    payload: HandlerUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """
    Update an existing CRM Handler configuration and its associated team members.
    """
    handler = db.query(CRMLeadHandler).filter(CRMLeadHandler.id == handler_id).first()
    if not handler:
        raise HTTPException(status_code=404, detail="Handler configuration not found.")

    changes = {}

    # Update active status
    if payload.is_active is not None and payload.is_active != handler.is_active:
        changes["is_active"] = {"old": handler.is_active, "new": payload.is_active}
        handler.is_active = payload.is_active

    # Update company/dept/category if provided
    new_co = payload.company_id if payload.company_id is not None else handler.company_id
    new_dept = payload.department_id if payload.department_id is not None else handler.department_id
    new_cat = payload.category_id if payload.category_id is not None else handler.category_id

    if (new_co != handler.company_id or new_dept != handler.department_id or new_cat != handler.category_id):
        # Check duplicate
        dup = db.query(CRMLeadHandler).filter(
            CRMLeadHandler.company_id == new_co,
            CRMLeadHandler.department_id == new_dept,
            CRMLeadHandler.category_id == new_cat,
            CRMLeadHandler.id != handler_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="Another handler with this Company, Department, and Category already exists.")
        
        changes["mapping"] = {
            "old": {"company_id": handler.company_id, "department_id": handler.department_id, "category_id": handler.category_id},
            "new": {"company_id": new_co, "department_id": new_dept, "category_id": new_cat}
        }
        handler.company_id = new_co
        handler.department_id = new_dept
        handler.category_id = new_cat

    # Update members if provided
    update_emp_ids = payload.employee_ids if payload.employee_ids is not None else payload.member_ids
    if update_emp_ids is not None:
        valid_emps = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(update_emp_ids),
            StaffEmployee.status == 'active',
            or_(StaffEmployee.is_deleted.is_(False), StaffEmployee.is_deleted.is_(None))
        ).all()
        target_emp_ids = {e.id for e in valid_emps}

        current_members = db.query(CRMLeadHandlerMember).filter(CRMLeadHandlerMember.handler_id == handler_id).all()
        current_emp_ids = {m.employee_id for m in current_members}

        # Remove members not in target
        to_remove = current_emp_ids - target_emp_ids
        if to_remove:
            db.query(CRMLeadHandlerMember).filter(
                CRMLeadHandlerMember.handler_id == handler_id,
                CRMLeadHandlerMember.employee_id.in_(to_remove)
            ).delete(synchronize_session=False)

        # Add new members
        to_add = target_emp_ids - current_emp_ids
        for emp_id in to_add:
            m = CRMLeadHandlerMember(
                handler_id=handler_id,
                employee_id=emp_id,
                is_active=True,
                created_by_id=admin_user.id
            )
            db.add(m)

        changes["members"] = {
            "added": list(to_add),
            "removed": list(to_remove),
            "final": list(target_emp_ids)
        }

    # Audit Log
    audit = CRMLeadHandlerAudit(
        handler_id=handler.id,
        action="UPDATE",
        details=json.dumps(changes),
        performed_by_id=admin_user.id
    )
    db.add(audit)

    db.commit()
    db.refresh(handler)

    return {
        "success": True,
        "message": "Handler configuration updated successfully.",
        "data": handler.to_dict()
    }


@router.post("/handlers/{handler_id}/toggle-status")
def toggle_handler_status(
    handler_id: int,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """Enable or disable a CRM Handler configuration."""
    handler = db.query(CRMLeadHandler).filter(CRMLeadHandler.id == handler_id).first()
    if not handler:
        raise HTTPException(status_code=404, detail="Handler configuration not found.")

    handler.is_active = not handler.is_active
    action = "ENABLE" if handler.is_active else "DISABLE"

    audit = CRMLeadHandlerAudit(
        handler_id=handler.id,
        action=action,
        details=json.dumps({"is_active": handler.is_active}),
        performed_by_id=admin_user.id
    )
    db.add(audit)

    db.commit()
    db.refresh(handler)

    return {
        "success": True,
        "message": f"Handler status changed to {'Active' if handler.is_active else 'Inactive'}.",
        "is_active": handler.is_active
    }


@router.delete("/handlers/{handler_id}")
def delete_handler(
    handler_id: int,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """Delete a CRM Handler configuration and its member associations."""
    handler = db.query(CRMLeadHandler).filter(CRMLeadHandler.id == handler_id).first()
    if not handler:
        raise HTTPException(status_code=404, detail="Handler configuration not found.")

    # Audit Log
    audit = CRMLeadHandlerAudit(
        handler_id=handler.id,
        action="DELETE",
        details=json.dumps({
            "company_id": handler.company_id,
            "department_id": handler.department_id,
            "category_id": handler.category_id
        }),
        performed_by_id=admin_user.id
    )
    db.add(audit)

    db.delete(handler)
    db.commit()

    return {
        "success": True,
        "message": "Handler configuration deleted successfully."
    }
