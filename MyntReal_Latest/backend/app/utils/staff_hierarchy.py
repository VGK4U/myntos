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
from datetime import date, datetime
from typing import List, Set, Optional
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import select, union_all, literal, and_, or_, func, text
from sqlalchemy.orm import aliased


def get_indian_date() -> date:
    """Return current date in Indian Standard Time (IST)."""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def get_effective_exit_date_expr(StaffEmployee):
    """
    Authoritative SQLAlchemy expression for an employee's effective exit date.
    Priority:
    1. last_working_date (explicit final working day before pause/resignation/termination)
    2. status_changed_at date (when transition away from active occurred)
    3. deleted_at date (when soft deletion occurred)
    4. date_of_joining (fallback: never active past joining date)
    """
    return func.coalesce(
        StaffEmployee.last_working_date,
        func.date(StaffEmployee.status_changed_at),
        func.date(StaffEmployee.deleted_at),
        StaffEmployee.date_of_joining
    )


def get_employee_eligibility_filter(
    StaffEmployee,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Authoritative employee eligibility filter expression across all modules.

    DC Protocol Core Rule — Effective Date Eligibility:
    - Soft-deleted records (is_deleted == True) are excluded from active operational views.
    - Date Range mode (start_date and end_date provided):
        * Employee must have joined on or before end_date: date_of_joining <= end_date
        * Employee must not have exited before start_date:
            - If status == 'active': last_working_date is None or last_working_date >= start_date
            - If status != 'active': effective_exit_date >= start_date
    - As-Of Date mode (as_of_date provided):
        * Employee must have joined on or before as_of_date: date_of_joining <= as_of_date
        * Employee must not have exited before as_of_date:
            - If status == 'active': last_working_date is None or last_working_date >= as_of_date
            - If status != 'active': effective_exit_date >= as_of_date
    - Current Operational mode (no dates provided, default):
        * Evaluated as of today (IST).
        * status == 'active' AND is_deleted == False AND date_of_joining <= today
          AND (last_working_date is None or last_working_date >= today)
    """
    base_cond = (StaffEmployee.is_deleted == False)

    # Mode 1: Date Range
    if start_date is not None and end_date is not None:
        eff_exit = get_effective_exit_date_expr(StaffEmployee)
        return and_(
            base_cond,
            StaffEmployee.date_of_joining <= end_date,
            or_(
                and_(
                    StaffEmployee.status == 'active',
                    or_(
                        StaffEmployee.last_working_date.is_(None),
                        StaffEmployee.last_working_date >= start_date
                    )
                ),
                and_(
                    StaffEmployee.status != 'active',
                    eff_exit >= start_date
                )
            )
        )

    # Mode 2: Historical As-Of Date
    if as_of_date is not None:
        eff_exit = get_effective_exit_date_expr(StaffEmployee)
        return and_(
            base_cond,
            StaffEmployee.date_of_joining <= as_of_date,
            or_(
                and_(
                    StaffEmployee.status == 'active',
                    or_(
                        StaffEmployee.last_working_date.is_(None),
                        StaffEmployee.last_working_date >= as_of_date
                    )
                ),
                and_(
                    StaffEmployee.status != 'active',
                    eff_exit >= as_of_date
                )
            )
        )

    # Mode 3: Current Operational Mode (default, today)
    today = get_indian_date()
    return and_(
        base_cond,
        StaffEmployee.status == 'active',
        StaffEmployee.date_of_joining <= today,
        or_(
            StaffEmployee.last_working_date.is_(None),
            StaffEmployee.last_working_date >= today
        )
    )


def is_employee_eligible_as_of(
    employee,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> bool:
    """
    Python-level helper to check if a StaffEmployee instance was eligible
    as of a date or during a date range.
    """
    if getattr(employee, 'is_deleted', False):
        return False

    doj = getattr(employee, 'date_of_joining', None)
    status = getattr(employee, 'status', 'active')
    lwd = getattr(employee, 'last_working_date', None)
    sc_at = getattr(employee, 'status_changed_at', None)
    sc_date = sc_at.date() if sc_at else None
    eff_exit = lwd or sc_date or doj

    if start_date is not None and end_date is not None:
        if doj and doj > end_date:
            return False
        if status == 'active':
            return lwd is None or lwd >= start_date
        return eff_exit is not None and eff_exit >= start_date

    target = as_of_date or get_indian_date()
    if doj and doj > target:
        return False

    if as_of_date is not None:
        if status == 'active':
            return lwd is None or lwd >= target
        return eff_exit is not None and eff_exit >= target

    # Current operational: strictly active today
    if status != 'active':
        return False
    return lwd is None or lwd >= target


def get_recursive_downline(
    manager_id: int, 
    db: Session, 
    StaffEmployee,
    max_depth: int = 10, 
    current_depth: int = 0,
    include_manager: bool = True,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[int]:
    """
    DC Protocol (Jan 07, 2026 / Sep 2026): Get all employee IDs in a manager's downline
    using SQLAlchemy CTE with effective-date eligibility.
    Based ONLY on reporting_manager_id chain - the org chart defines visibility.
    
    Args:
        manager_id: The manager's employee ID
        db: Database session
        StaffEmployee: The StaffEmployee model class
        max_depth: Maximum recursion depth (default 10 levels)
        current_depth: Current recursion depth (unused in CTE version, kept for API compat)
        include_manager: Whether to include manager's own ID in results
        as_of_date: Optional single date for as-of eligibility
        start_date: Optional start date for date range eligibility
        end_date: Optional end date for date range eligibility
    
    Returns:
        List of employee IDs in the manager's downline eligible for the specified date/range
    """
    base_eligibility = get_employee_eligibility_filter(
        StaffEmployee, as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )

    base_query = select(
        StaffEmployee.id.label('id'),
        StaffEmployee.reporting_manager_id.label('reporting_manager_id'),
        literal(1).label('depth')
    ).where(
        and_(
            StaffEmployee.reporting_manager_id == manager_id,
            base_eligibility
        )
    )
    
    subordinates = base_query.cte('subordinates', recursive=True)
    
    emp_alias = aliased(StaffEmployee, name='emp_alias')
    alias_eligibility = get_employee_eligibility_filter(
        emp_alias, as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    
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
            alias_eligibility,
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


def _get_saas_company_filter(current_user, db: Session, StaffEmployee):
    """Returns a filter predicate restricting queries to the SaaS tenant's company, or None."""
    if not current_user:
        return None
    try:
        from app.services.saas_tenant_resolver import resolve_tenant_context
        _saas_ctx = resolve_tenant_context(db, current_user)
        if _saas_ctx.is_saas_tenant and _saas_ctx.company:
            from app.models.staff import StaffCompanyMembership
            cid = _saas_ctx.company.id
            return or_(
                StaffEmployee.base_company_id == cid,
                StaffEmployee.id.in_(
                    db.query(StaffCompanyMembership.staff_id).filter(
                        StaffCompanyMembership.company_id == cid,
                        StaffCompanyMembership.is_active == True
                    )
                )
            )
    except Exception:
        pass
    return None


def get_accessible_employee_ids(
    current_user,
    db: Session,
    StaffEmployee,
    department_id: int = None,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[int]:
    """
    DC Protocol (Dec 04, 2025 / Sep 2026): Get list of employee IDs accessible to current user
    with effective-date eligibility.
    
    ACCESS RULES:
    - VGK4U Supreme, EA, HR, Accounts: See ALL eligible employees (full org visibility)
    - Key Leadership, Leadership Role: See all eligible employees EXCEPT EA/VGK Supreme
    - Other roles: See their complete downline via reporting_manager_id chain
    - SaaS tenants: Scoped strictly to employees within their authorized company
    
    Args:
        current_user: Current logged-in staff employee
        db: Database session
        StaffEmployee: The StaffEmployee model class
        department_id: Optional department filter
        as_of_date: Optional single date for as-of eligibility
        start_date: Optional start date for date range eligibility
        end_date: Optional end date for date range eligibility
    
    Returns:
        List of accessible employee IDs
    """
    role_code = _get_effective_role_code(current_user)
    eligibility_cond = get_employee_eligibility_filter(
        StaffEmployee, as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    saas_cond = _get_saas_company_filter(current_user, db, StaffEmployee)
    if saas_cond is not None:
        eligibility_cond = and_(eligibility_cond, saas_cond)
    
    if role_code in FULL_ACCESS_ROLES:
        base_query = db.query(StaffEmployee.id).filter(eligibility_cond)
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        return [e.id for e in base_query.all()]

    if role_code in LEADERSHIP_ROLES:
        excluded_ids = _get_ea_vgk_employee_ids(db)
        base_query = db.query(StaffEmployee.id).filter(eligibility_cond)
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        all_ids = [e.id for e in base_query.all()]
        return [eid for eid in all_ids if eid not in excluded_ids]
    
    downline_ids = get_recursive_downline(
        current_user.id, db, StaffEmployee, include_manager=True,
        as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    
    if department_id:
        filtered_ids = db.query(StaffEmployee.id).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.department_id == department_id,
            eligibility_cond
        ).all()
        return [e.id for e in filtered_ids]
    
    return downline_ids


def is_in_reporting_chain(
    employee_id: int,
    manager_id: int,
    db: Session,
    StaffEmployee,
    max_depth: int = 10,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> bool:
    """
    DC Protocol: Check if an employee is in a manager's reporting chain
    
    Args:
        employee_id: The employee to check
        manager_id: The manager's ID
        db: Database session
        StaffEmployee: The StaffEmployee model class
        max_depth: Maximum depth to search
        as_of_date: Optional as-of date
        start_date: Optional start date
        end_date: Optional end date
    
    Returns:
        True if employee reports to manager (directly or indirectly)
    """
    downline_ids = get_recursive_downline(
        manager_id, db, StaffEmployee, max_depth, include_manager=False,
        as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    return employee_id in downline_ids


def has_direct_reports(
    employee_id: int,
    db: Session,
    StaffEmployee,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> bool:
    """
    DC Protocol: Check if an employee has any direct reports with effective-date eligibility.
    
    Args:
        employee_id: The employee to check
        db: Database session
        StaffEmployee: The StaffEmployee model class
        as_of_date: Optional as-of date
        start_date: Optional start date
        end_date: Optional end date
    
    Returns:
        True if employee has at least one eligible direct report
    """
    eligibility_cond = get_employee_eligibility_filter(
        StaffEmployee, as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    count = db.query(StaffEmployee).filter(
        StaffEmployee.reporting_manager_id == employee_id,
        eligibility_cond
    ).count()
    return count > 0


def get_team_member_ids(
    current_user,
    db: Session,
    StaffEmployee,
    department_id: int = None,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[int]:
    """
    DC Protocol (Feb 25, 2026 / Sep 2026): Get team member IDs for team views/dashboards
    with effective-date employee eligibility.
    DC Protocol (Feb 27, 2026): key_leadership and leadership_role see full org minus EA/VGK Supreme.

    Always excludes: (1) current user's own ID, (2) HIDDEN_FROM_TEAM_CODES accounts.
    For key_leadership/leadership_role: additionally excludes employees with ea/vgk4u roles.

    ACCESS RULES:
    - VGK4U Supreme, EA, HR, Accounts: all eligible employees (minus self, minus HIDDEN_FROM_TEAM_CODES)
    - Key Leadership, Leadership Role: all eligible employees minus EA/VGK (minus self, minus HIDDEN_FROM_TEAM_CODES)
    - All others: recursive downline only (minus self, minus HIDDEN_FROM_TEAM_CODES)

    Use this for ALL team display endpoints (progress, KRA, timesheet, attendance,
    tasks, CRM, journeys, field work, etc.) to ensure consistent team filtering
    across web and mobile.

    For personal/self views, query current_user.id directly — not through this function.
    """
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    role_code = _get_effective_role_code(current_user)
    eligibility_cond = get_employee_eligibility_filter(
        StaffEmployee, as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    saas_cond = _get_saas_company_filter(current_user, db, StaffEmployee)
    if saas_cond is not None:
        eligibility_cond = and_(eligibility_cond, saas_cond)
    
    if role_code in FULL_ACCESS_ROLES:
        base_query = db.query(StaffEmployee.id).filter(eligibility_cond)
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        all_ids = [e.id for e in base_query.all()]
        exclude = hidden_ids | {current_user.id}
        return [eid for eid in all_ids if eid not in exclude]

    if role_code in LEADERSHIP_ROLES:
        ea_vgk_ids = _get_ea_vgk_employee_ids(db)
        base_query = db.query(StaffEmployee.id).filter(eligibility_cond)
        if department_id:
            base_query = base_query.filter(StaffEmployee.department_id == department_id)
        all_ids = [e.id for e in base_query.all()]
        exclude = hidden_ids | {current_user.id} | ea_vgk_ids
        return [eid for eid in all_ids if eid not in exclude]
    
    downline_ids = get_recursive_downline(
        current_user.id, db, StaffEmployee, include_manager=False,
        as_of_date=as_of_date, start_date=start_date, end_date=end_date
    )
    
    if department_id:
        filtered = db.query(StaffEmployee.id).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.department_id == department_id,
            eligibility_cond
        ).all()
        downline_ids = [e.id for e in filtered]
    
    return [eid for eid in downline_ids if eid not in hidden_ids]


def get_downline_employee_ids(
    db: Session,
    manager_id: int,
    recursive: bool = True,
    max_depth: int = 10,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Set[int]:
    """
    DC Protocol: Get the set of employee IDs that report under the given manager
    with effective-date employee eligibility.
    Args:
        db: SQLAlchemy session
        manager_id: The manager's employee ID
        recursive: Whether to traverse the full hierarchy (default True)
        max_depth: Max hierarchy depth (default 10)
        as_of_date: Optional single date for as-of eligibility
        start_date: Optional start date for date range eligibility
        end_date: Optional end date for date range eligibility
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
        as_of_date=as_of_date,
        start_date=start_date,
        end_date=end_date
    )
    return set(ids)
