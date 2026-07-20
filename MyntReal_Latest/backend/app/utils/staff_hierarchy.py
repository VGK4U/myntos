"""
DC Protocol: Staff Hierarchy Utility Functions
Single source of truth for reporting manager hierarchy operations
Created: Dec 04, 2025
Updated: Dec 04, 2025 - PURE reporting_manager_id based hierarchy - NO hierarchy_level checks
Updated: Jan 07, 2026 - Optimized with SQLAlchemy CTE to eliminate N+1 performance issue
Updated: Feb 25, 2026 - Added get_team_member_ids() to exclude self + hidden accounts from team views
Updated: Feb 27, 2026 - Added LEADERSHIP_ROLES (key_leadership, leadership_role) with full org
                         visibility EXCEPT EA/VGK Supreme employees (DC Protocol: senior roles
                         excluded from subordinate team views)
"""
from typing import List, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, union_all, literal, and_, func, text
from sqlalchemy.orm import aliased


def get_recursive_downline(
    manager_id: int, 
    db: Session, 
    StaffEmployee,
    max_depth: int = 10, 
    current_depth: int = 0,
    include_manager: bool = True
) -> List[int]:
    """
    DC Protocol (Jan 07, 2026): Get all employee IDs in a manager's downline using SQLAlchemy CTE
    Based ONLY on reporting_manager_id chain - the org chart defines visibility
    
    OPTIMIZED: Uses recursive CTE via SQLAlchemy instead of Python recursion to eliminate N+1 queries
    This is critical for production with large org hierarchies (1000+ employees)
    Maintains ORM compatibility and respects model filters
    
    Args:
        manager_id: The manager's employee ID
        db: Database session
        StaffEmployee: The StaffEmployee model class
        max_depth: Maximum recursion depth (default 10 levels)
        current_depth: Current recursion depth (unused in CTE version, kept for API compat)
        include_manager: Whether to include manager's own ID in results
    
    Returns:
        List of employee IDs in the manager's entire downline
    """
    base_query = select(
        StaffEmployee.id.label('id'),
        StaffEmployee.reporting_manager_id.label('reporting_manager_id'),
        literal(1).label('depth')
    ).where(
        and_(
            StaffEmployee.reporting_manager_id == manager_id,
            StaffEmployee.status == 'active'
        )
    )
    
    subordinates = base_query.cte('subordinates', recursive=True)
    
    emp_alias = aliased(StaffEmployee, name='emp_alias')
    
    recursive_query = select(
        emp_alias.id.label('id'),
        emp_alias.reporting_manager_id.label('reporting_manager_id'),
        (subordinates.c.depth + 1).label('depth')
    ).select_from(
        emp_alias
    ).join(
        subordinates, emp_alias.reporting_manager_id == subordinates.c.id
    ).where(
        and_(
            emp_alias.status == 'active',
            subordinates.c.depth < max_depth
        )
    )
    
    subordinates = subordinates.union_all(recursive_query)
    
    final_query = select(subordinates.c.id).order_by(subordinates.c.id)
    
    result = db.execute(final_query)
    subordinate_ids = [row[0] for row in result.fetchall()]
    
    if include_manager:
        return [manager_id] + subordinate_ids
    
    return subordinate_ids


FULL_ACCESS_ROLES = ['vgk4u', 'ea', 'hr', 'accounts']

LEADERSHIP_ROLES = ['key_leadership', 'leadership_role']

EXCLUDED_FROM_LEADERSHIP_VIEW = ['ea', 'vgk4u']

HIDDEN_FROM_TEAM_CODES = ["MR10001"]


def _get_effective_role_code(current_user) -> str:
    """
    DC Protocol (Mar 09, 2026): Derive effective role code considering additional departments.
    Additional department assignments for HR or Accounts grant the same team visibility
    as the primary HR/Accounts roles — consistent with DC access design intent.
    Primary role always takes precedence; additional departments only elevate when needed.
    """
    primary_code = (
        current_user.role.role_code.lower()
        if current_user.role and current_user.role.role_code else None
    )
    if primary_code in FULL_ACCESS_ROLES:
        return primary_code
    for ad in getattr(current_user, 'additional_departments', []):
        ad_dept = getattr(ad, 'department', None)
        if ad_dept:
            dept_name = (getattr(ad_dept, 'name', '') or '').lower()
            if 'human resources' in dept_name or dept_name == 'hr':
                return 'hr'
            if 'accounts' in dept_name or 'finance' in dept_name:
                return 'accounts'
    return primary_code


def _get_hidden_employee_ids(db: Session, StaffEmployee) -> Set[int]:
    if not HIDDEN_FROM_TEAM_CODES:
        return set()
    rows = db.query(StaffEmployee.id).filter(
        StaffEmployee.emp_code.in_(HIDDEN_FROM_TEAM_CODES),
        StaffEmployee.status == 'active'
    ).all()
    return {r.id for r in rows}


def _get_ea_vgk_employee_ids(db: Session) -> Set[int]:
    """
    DC Protocol (Feb 27, 2026): Get IDs of employees with EA or VGK Supreme roles.
    Used to exclude senior roles from leadership team views.
    Uses raw SQL join to avoid circular model imports.
    """
    result = db.execute(text(
        "SELECT e.id FROM staff_employees e "
        "JOIN staff_roles r ON e.role_id = r.id "
        "WHERE e.status = 'active' AND e.is_deleted = false "
        "AND r.role_code IN ('ea', 'vgk4u')"
    ))
    return {row[0] for row in result.fetchall()}


def get_accessible_employee_ids(
    current_user,
    db: Session,
    StaffEmployee,
    department_id: int = None
) -> List[int]:
    """
    DC Protocol (Dec 04, 2025): Get list of employee IDs accessible to current user.
    
    ACCESS RULES:
    - VGK4U Supreme, EA, HR, Accounts: See ALL active employees (full org visibility)
    - Key Leadership, Leadership Role: See all active employees EXCEPT EA/VGK Supreme
    - Other roles: See their complete downline via reporting_manager_id chain
    
    Args:
        current_user: Current logged-in staff employee
        db: Database session
        StaffEmployee: The StaffEmployee model class
        department_id: Optional department filter
    
    Returns:
        List of accessible employee IDs
    """
    role_code = _get_effective_role_code(current_user)
    
    if role_code in FULL_ACCESS_ROLES:
        base_query = db.query(StaffEmployee.id).filter(
            StaffEmployee.status == 'active'
        )
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        return [e.id for e in base_query.all()]

    if role_code in LEADERSHIP_ROLES:
        excluded_ids = _get_ea_vgk_employee_ids(db)
        base_query = db.query(StaffEmployee.id).filter(
            StaffEmployee.status == 'active'
        )
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        all_ids = [e.id for e in base_query.all()]
        return [eid for eid in all_ids if eid not in excluded_ids]
    
    downline_ids = get_recursive_downline(
        current_user.id, db, StaffEmployee, include_manager=True
    )
    
    if department_id:
        filtered_ids = db.query(StaffEmployee.id).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.department_id == department_id,
            StaffEmployee.status == 'active'
        ).all()
        return [e.id for e in filtered_ids]
    
    return downline_ids


def is_in_reporting_chain(
    employee_id: int,
    manager_id: int,
    db: Session,
    StaffEmployee,
    max_depth: int = 10
) -> bool:
    """
    DC Protocol: Check if an employee is in a manager's reporting chain
    
    Args:
        employee_id: The employee to check
        manager_id: The manager's ID
        db: Database session
        StaffEmployee: The StaffEmployee model class
        max_depth: Maximum depth to search
    
    Returns:
        True if employee reports to manager (directly or indirectly)
    """
    downline_ids = get_recursive_downline(
        manager_id, db, StaffEmployee, max_depth, include_manager=False
    )
    return employee_id in downline_ids


def has_direct_reports(
    employee_id: int,
    db: Session,
    StaffEmployee
) -> bool:
    """
    DC Protocol: Check if an employee has any direct reports
    
    Args:
        employee_id: The employee to check
        db: Database session
        StaffEmployee: The StaffEmployee model class
    
    Returns:
        True if employee has at least one direct report
    """
    count = db.query(StaffEmployee).filter(
        StaffEmployee.reporting_manager_id == employee_id,
        StaffEmployee.status == 'active'
    ).count()
    return count > 0


def get_team_member_ids(
    current_user,
    db: Session,
    StaffEmployee,
    department_id: int = None
) -> List[int]:
    """
    DC Protocol (Feb 25, 2026): Get team member IDs for team views/dashboards.
    DC Protocol (Feb 27, 2026): key_leadership and leadership_role see full org minus EA/VGK Supreme.

    Always excludes: (1) current user's own ID, (2) HIDDEN_FROM_TEAM_CODES accounts.
    For key_leadership/leadership_role: additionally excludes employees with ea/vgk4u roles.

    ACCESS RULES:
    - VGK4U Supreme, EA, HR, Accounts: all active employees (minus self, minus HIDDEN_FROM_TEAM_CODES)
    - Key Leadership, Leadership Role: all active employees minus EA/VGK (minus self, minus HIDDEN_FROM_TEAM_CODES)
    - All others: recursive downline only (minus self, minus HIDDEN_FROM_TEAM_CODES)

    Use this for ALL team display endpoints (progress, KRA, timesheet, attendance,
    tasks, CRM, journeys, field work, etc.) to ensure consistent team filtering
    across web and mobile.

    For personal/self views, query current_user.id directly — not through this function.
    """
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    
    role_code = _get_effective_role_code(current_user)
    
    if role_code in FULL_ACCESS_ROLES:
        base_query = db.query(StaffEmployee.id).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False
        )
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        all_ids = [e.id for e in base_query.all()]
        exclude = hidden_ids | {current_user.id}
        return [eid for eid in all_ids if eid not in exclude]

    if role_code in LEADERSHIP_ROLES:
        ea_vgk_ids = _get_ea_vgk_employee_ids(db)
        base_query = db.query(StaffEmployee.id).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False
        )
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        all_ids = [e.id for e in base_query.all()]
        exclude = hidden_ids | {current_user.id} | ea_vgk_ids
        return [eid for eid in all_ids if eid not in exclude]
    
    downline_ids = get_recursive_downline(
        current_user.id, db, StaffEmployee, include_manager=False
    )
    
    if department_id:
        filtered = db.query(StaffEmployee.id).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.department_id == department_id,
            StaffEmployee.status == 'active'
        ).all()
        downline_ids = [e.id for e in filtered]
    
    return [eid for eid in downline_ids if eid not in hidden_ids]


def get_downline_employee_ids(
    db: Session,
    manager_id: int,
    recursive: bool = True,
    max_depth: int = 10
) -> Set[int]:
    """
    DC Protocol: Get the set of employee IDs that report under the given manager.
    Thin wrapper around get_recursive_downline for consistent call signature.
    Args:
        db: SQLAlchemy session
        manager_id: The manager's employee ID
        recursive: Whether to traverse the full hierarchy (default True)
        max_depth: Max hierarchy depth (default 10)
    Returns:
        set of employee IDs in the downline (excluding manager)
    """
    from app.models.staff import StaffEmployee as _SE
    ids = get_recursive_downline(
        manager_id=manager_id,
        db=db,
        StaffEmployee=_SE,
        max_depth=max_depth if recursive else 1,
        include_manager=False,
    )
    return set(ids)
