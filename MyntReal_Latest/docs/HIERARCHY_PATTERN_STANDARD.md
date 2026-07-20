# Pure Reporting Manager Hierarchy Pattern Standard

**Effective Date:** December 04, 2025  
**Status:** MANDATORY for all Staff System modules

---

## Overview

This document defines the **MANDATORY** pattern for implementing data visibility checks across ALL staff system modules. The core principle is:

> **Data visibility MUST use pure `reporting_manager_id` chain, NOT `hierarchy_level` checks.**

---

## Core Principle

### OLD (Deprecated - DO NOT USE)
```python
# WRONG - Do not use hierarchy_level for data visibility
if current_user.role.hierarchy_level < 60:
    raise HTTPException(status_code=403, detail="Manager access required")
```

### NEW (Mandatory Standard)
```python
# CORRECT - Use has_direct_reports() for data visibility
from app.utils.staff_hierarchy import has_direct_reports

is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
is_vgk4u_or_hr = current_user.role and (
    current_user.role.hierarchy_level >= 150 or 
    current_user.role.role_name in ['HR', 'Executive Assistant'] or
    current_user.role.role_code in ['hr', 'ea']
)

if not is_manager and not is_vgk4u_or_hr:
    raise HTTPException(
        status_code=403, 
        detail="Only those with direct reports or HR/VGK4U can access this resource"
    )
```

---

## Key Helper Functions

Located in: `backend/app/utils/staff_hierarchy.py`

### 1. `has_direct_reports(employee_id, db, StaffEmployee)`
Checks if any employee has this person as their `reporting_manager_id`.

**Use Case:** Early access gate - determines if user should have manager-level access.

```python
from app.utils.staff_hierarchy import has_direct_reports

is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
```

### 2. `get_accessible_employee_ids(current_user, db, StaffEmployee, department_id=None)`
Returns list of employee IDs in the user's recursive downline.

**Use Case:** Data scoping - filter queries to only include accessible employees.

```python
from app.utils.staff_hierarchy import get_accessible_employee_ids

accessible_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
query = db.query(SomeModel).filter(SomeModel.employee_id.in_(accessible_ids))
```

---

## When to Use Each Pattern

### For DATA VISIBILITY Endpoints (Team view, All view, etc.)
Use `has_direct_reports()` + VGK/HR override:

```python
is_manager = has_direct_reports(current_user.id, db, StaffEmployee)
is_vgk4u_or_hr = current_user.role and (
    current_user.role.hierarchy_level >= 150 or 
    current_user.role.role_name in ['HR', 'Executive Assistant'] or
    current_user.role.role_code in ['hr', 'ea']
)

if not is_manager and not is_vgk4u_or_hr:
    raise HTTPException(status_code=403, detail="Only those with direct reports or HR/VGK4U can...")
```

### For ADMIN ACTIONS (Clockout, Config changes, etc.)
Still use `hierarchy_level >= 85` for special admin operations:

```python
# Admin actions like forced clockout still use hierarchy_level
if current_user.role.hierarchy_level < 85:
    raise HTTPException(status_code=403, detail="HR level (85+) access required")
```

---

## VGK/HR Override Definition

The VGK/HR admin override allows special roles to see all data regardless of reporting chain:

```python
is_vgk4u_or_hr = current_user.role and (
    current_user.role.hierarchy_level >= 150 or                     # VGK4U Supreme
    current_user.role.role_name in ['HR', 'Executive Assistant'] or # By role name
    current_user.role.role_code in ['hr', 'ea']                     # By role code
)
```

---

## Standard Error Message

Use consistent error messaging across all endpoints:

```
"Only those with direct reports or HR/VGK4U can [action description]"
```

Examples:
- "Only those with direct reports or HR/VGK4U can view team journeys"
- "Only those with direct reports or HR/VGK4U can approve tasks"
- "Only those with direct reports or HR/VGK4U can access location history"

---

## Modules Already Using This Pattern

As of December 04, 2025, the following modules have been refactored:

| Module | File | Status |
|--------|------|--------|
| Task Management | `staff_tasks.py` | ✅ Complete (17 fixes) |
| KRA Management | `staff_kra.py` | ✅ Complete (6 fixes) |
| Time Tracker | `staff_time_tracker.py` | ✅ Complete (4 fixes) |
| Journey Management | `staff_journeys.py` | ✅ Complete (6 fixes) |

---

## Checklist for New Endpoints

When creating new staff endpoints that require manager access:

1. [ ] Import `has_direct_reports` from `app.utils.staff_hierarchy`
2. [ ] Use `has_direct_reports()` check instead of `hierarchy_level >= 60`
3. [ ] Include VGK/HR override for admin users
4. [ ] Use `get_accessible_employee_ids()` for data scoping
5. [ ] Use standard error message format
6. [ ] Document with "DC Protocol (Dec 04, 2025): PURE REPORTING_MANAGER BASED"

---

## Why This Pattern?

### Problem with hierarchy_level checks:
- A Team Lead with `hierarchy_level = 60` could see ALL employees in the system
- No connection between org chart structure and data access
- Promotions/role changes unexpectedly grant broad access

### Solution with reporting_manager_id chain:
- VGK sees EA's data because EA's `reporting_manager_id` = VGK's ID
- VGK sees HR's data through recursive chain (HR → EA → VGK)
- The org chart defines visibility, not arbitrary hierarchy levels
- Access is automatically scoped to actual team structure

---

## Contact

For questions about this pattern, refer to the architect review or the project documentation in `replit.md`.
