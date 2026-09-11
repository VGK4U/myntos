"""
CRM Settings & Handler-based Lead Routing API Endpoints
Provides full REST lifecycle for Categories and Handlers configuration.
Strictly authorized to: MR1001, VGK4U Supreme, and Yashwanth.
Created: Sep 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
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
from app.models.crm import CRMLead

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


class EmployeeCategoryAssignRequest(BaseModel):
    employee_id: int = Field(..., description="Target Staff Employee ID")
    company_id: Optional[int] = Field(default=None, description="Company ID (when syncing per-company)")
    category_ids: Optional[List[int]] = Field(default=None, description="List of Category IDs for the given company_id")
    department_id: Optional[int] = Field(default=None, description="Department ID (defaults to employee's department)")
    assignments: Optional[List[Dict[str, Any]]] = Field(default=None, description="Detailed list of {company_id, category_id, department_id} tuples")



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
    # 1. Active Companies strictly for CRM Routing (MyntReal LLP & Zynova Mobility)
    companies = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_active == True,
        AssociatedCompany.id.in_([4, 2])
    ).order_by(AssociatedCompany.id.desc()).all()
    company_list = [
        {"id": c.id, "company_name": c.company_name, "name": c.company_name, "company_code": getattr(c, 'company_code', '')}
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

    # 3. Active Categories strictly for CRM companies (MyntReal & Zynova)
    cat_query = db.query(SignupCategory).filter(
        SignupCategory.is_active == True,
        SignupCategory.company_id.in_([4, 2])
    )
    if company_id:
        cat_query = cat_query.filter(SignupCategory.company_id == company_id)
    categories = cat_query.order_by(SignupCategory.name, SignupCategory.id).all()
    
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

    return {
        "success": True,
        "message": "Handler configuration deleted successfully."
    }


# ──────────────────────────────────────────────────────────────────────────────
# EMPLOYEE-CENTRIC HANDLERS & ROUTING ENDPOINTS
# Flow: Employee --- Assigned Categories
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/employee-handlers")
def list_employee_handlers(
    department_filter: Optional[str] = Query("sales", description="'sales', 'all', or specific department_id"),
    company_id: Optional[int] = Query(None, description="Optional Company ID filter"),
    search: Optional[str] = Query(None, description="Search employee name or code"),
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """
    List active staff members (defaulting to Sales & Tele Sales personnel, with filter for all departments)
    showing their assigned categories, company routing, and real-time Fresh and Claimed lead counts.
    """
    # 1. Fetch metadata lookup maps
    companies = db.query(AssociatedCompany).all()
    departments = db.query(StaffDepartment).all()
    categories = db.query(SignupCategory).all()

    co_map = {c.id: c.company_name for c in companies}
    dept_map = {d.id: d.name for d in departments}
    cat_map = {c.id: c for c in categories}

    # 2. Build Employees query
    emp_query = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        or_(StaffEmployee.is_deleted.is_(False), StaffEmployee.is_deleted.is_(None))
    )

    # Determine Sales department IDs
    sales_dept_ids = [d.id for d in departments if 'sales' in (d.name or '').lower()]

    if department_filter == "sales":
        if sales_dept_ids:
            emp_query = emp_query.filter(StaffEmployee.department_id.in_(sales_dept_ids))
    elif department_filter and department_filter != "all":
        try:
            dept_id = int(department_filter)
            emp_query = emp_query.filter(StaffEmployee.department_id == dept_id)
        except ValueError:
            pass

    if search:
        s = f"%{search.strip()}%"
        emp_query = emp_query.filter(
            or_(
                StaffEmployee.emp_code.ilike(s),
                StaffEmployee.full_name.ilike(s),
                StaffEmployee.first_name.ilike(s),
                StaffEmployee.last_name.ilike(s),
                StaffEmployee.email.ilike(s)
            )
        )

    employees = emp_query.order_by(StaffEmployee.department_id, StaffEmployee.emp_code).all()

    # 3. Load roles
    role_ids = {e.role_id for e in employees if e.role_id}
    roles = db.query(StaffRole).filter(StaffRole.id.in_(role_ids)).all() if role_ids else []
    role_map = {r.id: r.role_name for r in roles}

    # 4. Fetch all active handlers and their active memberships
    all_handlers = db.query(CRMLeadHandler).filter(CRMLeadHandler.is_active == True).all()
    handler_dict = {h.id: h for h in all_handlers}

    all_members = db.query(CRMLeadHandlerMember).filter(CRMLeadHandlerMember.is_active == True).all()
    emp_members_map: Dict[int, List[Dict[str, Any]]] = {}

    for m in all_members:
        h = handler_dict.get(m.handler_id)
        if not h:
            continue
        if company_id and h.company_id != company_id:
            continue
        
        cat = cat_map.get(h.category_id)
        cat_name = cat.name if cat else f"Category #{h.category_id}"
        co_name = co_map.get(h.company_id, f"Company #{h.company_id}")
        d_name = dept_map.get(h.department_id, f"Dept #{h.department_id}")

        assigned_item = {
            "handler_id": h.id,
            "member_id": m.id,
            "company_id": h.company_id,
            "company_name": co_name,
            "department_id": h.department_id,
            "department_name": d_name,
            "category_id": h.category_id,
            "category_name": cat_name,
            "is_active": m.is_active and h.is_active
        }

        emp_members_map.setdefault(m.employee_id, []).append(assigned_item)

    # 5. High-performance lead counts aggregation
    # 5a. Fresh leads by (company_id, category_id)
    u_conds = [
        ~CRMLead.status.in_(['won', 'lost']),
        CRMLead.handler_type == 'unassigned',
        CRMLead.telecaller_id.is_(None),
        CRMLead.field_staff_id.is_(None),
        CRMLead.primary_owner_id.is_(None)
    ]
    fresh_counts_raw = db.query(
        CRMLead.company_id, CRMLead.category_id, func.count(CRMLead.id)
    ).filter(*u_conds).group_by(CRMLead.company_id, CRMLead.category_id).all()
    fresh_by_co_cat = {(r[0], r[1]): r[2] for r in fresh_counts_raw}

    # 5b. Claimed / Owned leads by employee
    claimed_counts = {}
    try:
        claimed_sql = text("""
            SELECT employee_id, count(lead_id) as claimed_count FROM (
                SELECT primary_owner_id as employee_id, id as lead_id FROM crm_leads WHERE primary_owner_type = 'staff' AND primary_owner_id IS NOT NULL
                UNION
                SELECT telecaller_id as employee_id, id as lead_id FROM crm_leads WHERE telecaller_id IS NOT NULL
                UNION
                SELECT field_staff_id as employee_id, id as lead_id FROM crm_leads WHERE field_staff_id IS NOT NULL
                UNION
                SELECT se.id as employee_id, cl.id as lead_id
                FROM crm_leads cl
                JOIN staff_employees se ON cl.mnr_handler_id = se.emp_code
                WHERE cl.mnr_handler_id IS NOT NULL AND se.emp_code IS NOT NULL
            ) sub GROUP BY employee_id
        """)
        claimed_counts = dict(db.execute(claimed_sql).fetchall())
    except Exception as e:
        logger.warning(f"Failed to fetch claimed counts: {e}")

    # 6. Format employee items
    results = []
    for emp in employees:
        assigned = emp_members_map.get(emp.id, [])

        # Calculate distinct fresh leads matching this employee's active eligibility
        emp_co_cats = {(item["company_id"], item["category_id"]) for item in assigned if item["is_active"]}
        fresh_count = sum(fresh_by_co_cat.get(co_cat, 0) for co_cat in emp_co_cats)
        claimed_count = claimed_counts.get(emp.id, 0)

        results.append({
            "id": emp.id,
            "employee_id": emp.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code,
            "department_id": emp.department_id,
            "department_name": dept_map.get(emp.department_id, "—"),
            "designation": getattr(emp, 'designation', '') or '—',
            "role_name": role_map.get(emp.role_id, getattr(emp, 'designation', '—') or 'Staff'),
            "email": emp.email or '',
            "phone": emp.phone or '',
            "status": emp.status,
            "assigned_categories": assigned,
            "categories_count": len(assigned),
            "fresh_leads_count": fresh_count,
            "claimed_leads_count": claimed_count,
            "total_leads_count": fresh_count + claimed_count
        })

    return {
        "success": True,
        "total": len(results),
        "department_filter": department_filter,
        "data": results,
        "departments": [{"id": d.id, "name": d.name} for d in departments],
        "companies": [{"id": c.id, "company_name": c.company_name} for c in companies]
    }


@router.post("/employee-handlers/assign")
def assign_employee_categories(
    payload: EmployeeCategoryAssignRequest,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """
    Assign or synchronize lead categories for a specific employee.
    Ensures CRMLeadHandler exists and atomically configures CRMLeadHandlerMember.
    Changes immediately update fresh leads visibility in real-time.
    """
    # 1. Validate employee
    emp = db.query(StaffEmployee).filter(StaffEmployee.id == payload.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee ID {payload.employee_id} not found.")

    target_dept_id = payload.department_id or emp.department_id
    if not target_dept_id:
        # Fallback to Sales department or first department
        first_dept = db.query(StaffDepartment).filter(StaffDepartment.name.ilike('%sales%')).first() or db.query(StaffDepartment).first()
        target_dept_id = first_dept.id if first_dept else 1

    updated_handlers = []

    # Case A: Detailed list of assignments provided
    if payload.assignments is not None:
        for item in payload.assignments:
            co_id = item.get("company_id")
            cat_id = item.get("category_id")
            dept_id = item.get("department_id") or target_dept_id
            if not co_id or not cat_id:
                continue

            handler = db.query(CRMLeadHandler).filter(
                CRMLeadHandler.company_id == co_id,
                CRMLeadHandler.department_id == dept_id,
                CRMLeadHandler.category_id == cat_id
            ).first()

            if not handler:
                handler = CRMLeadHandler(
                    company_id=co_id,
                    department_id=dept_id,
                    category_id=cat_id,
                    is_active=True,
                    created_by_id=admin_user.id
                )
                db.add(handler)
                db.flush()
            elif not handler.is_active:
                handler.is_active = True

            member = db.query(CRMLeadHandlerMember).filter(
                CRMLeadHandlerMember.handler_id == handler.id,
                CRMLeadHandlerMember.employee_id == emp.id
            ).first()

            if not member:
                member = CRMLeadHandlerMember(
                    handler_id=handler.id,
                    employee_id=emp.id,
                    is_active=True,
                    created_by_id=admin_user.id
                )
                db.add(member)
            else:
                member.is_active = True

            updated_handlers.append(handler.id)

    # Case B: company_id and category_ids list provided (per-company sync)
    elif payload.company_id is not None:
        selected_cat_ids = set(payload.category_ids or [])
        
        # Fetch all categories that exist for this company
        company_cats = db.query(SignupCategory).filter(SignupCategory.company_id == payload.company_id).all()
        company_cat_ids = {c.id for c in company_cats}

        for cat_id in company_cat_ids:
            # Find handler
            handler = db.query(CRMLeadHandler).filter(
                CRMLeadHandler.company_id == payload.company_id,
                CRMLeadHandler.category_id == cat_id
            ).first()

            if cat_id in selected_cat_ids:
                # Should be active
                if not handler:
                    handler = CRMLeadHandler(
                        company_id=payload.company_id,
                        department_id=target_dept_id,
                        category_id=cat_id,
                        is_active=True,
                        created_by_id=admin_user.id
                    )
                    db.add(handler)
                    db.flush()
                elif not handler.is_active:
                    handler.is_active = True

                member = db.query(CRMLeadHandlerMember).filter(
                    CRMLeadHandlerMember.handler_id == handler.id,
                    CRMLeadHandlerMember.employee_id == emp.id
                ).first()

                if not member:
                    member = CRMLeadHandlerMember(
                        handler_id=handler.id,
                        employee_id=emp.id,
                        is_active=True,
                        created_by_id=admin_user.id
                    )
                    db.add(member)
                else:
                    member.is_active = True
                
                updated_handlers.append(handler.id)
            else:
                # Unselected for this company -> deactivate if present
                if handler:
                    member = db.query(CRMLeadHandlerMember).filter(
                        CRMLeadHandlerMember.handler_id == handler.id,
                        CRMLeadHandlerMember.employee_id == emp.id
                    ).first()
                    if member and member.is_active:
                        member.is_active = False

    # Audit log
    audit = CRMLeadHandlerAudit(
        handler_id=None,
        action="EMPLOYEE_CATEGORIES_SYNC",
        details=json.dumps({
            "employee_id": emp.id,
            "emp_code": emp.emp_code,
            "company_id": payload.company_id,
            "assigned_category_ids": payload.category_ids or []
        }),
        performed_by_id=admin_user.id
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Categories successfully updated for {emp.full_name or emp.emp_code}.",
        "employee_id": emp.id,
        "updated_handlers": updated_handlers
    }


@router.delete("/employee-handlers/{employee_id}/categories/{handler_id}")
def remove_employee_category_assignment(
    employee_id: int,
    handler_id: int,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """Remove a specific category assignment from an employee."""
    member = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.handler_id == handler_id,
        CRMLeadHandlerMember.employee_id == employee_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Category assignment not found for this employee.")

    member.is_active = False

    audit = CRMLeadHandlerAudit(
        handler_id=handler_id,
        action="MEMBER_REMOVE",
        details=json.dumps({"employee_id": employee_id, "handler_id": handler_id}),
        performed_by_id=admin_user.id
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": "Category assignment removed successfully."
    }


@router.delete("/employee-handlers/{employee_id}/categories")
def clear_all_employee_categories(
    employee_id: int,
    db: Session = Depends(get_db),
    admin_user: StaffEmployee = Depends(enforce_crm_settings_access)
):
    """Clear all category assignments for an employee."""
    members = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.employee_id == employee_id,
        CRMLeadHandlerMember.is_active == True
    ).all()

    count = len(members)
    for m in members:
        m.is_active = False

    audit = CRMLeadHandlerAudit(
        handler_id=None,
        action="EMPLOYEE_CATEGORIES_CLEAR",
        details=json.dumps({"employee_id": employee_id, "cleared_count": count}),
        performed_by_id=admin_user.id
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"All {count} category assignment(s) cleared successfully."
    }

