# Staff System - Complete Structure & Phase-Wise Reimplementation Strategy
**Date:** November 26, 2025  
**Protocol Compliance:** WVV (Write-Verify-Validate) + DC (Data Consistency)  
**Integration Target:** MNR Reference Program Platform

---

## EXECUTIVE SUMMARY

The Staff System (Employee Tracker) is a comprehensive HR/employee management system that was previously developed as a separate Flask application on port 8080. This document outlines the complete structure and a phase-wise strategy to reimplement and integrate it with the existing MNR FastAPI backend.

---

## PART 1: COMPLETE SYSTEM STRUCTURE

### 1.1 Database Schema (23 Tables)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     STAFF SYSTEM DATABASE SCHEMA                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │   DEPARTMENTS   │────▶│    EMPLOYEES    │────▶│   TIMESHEETS  │ │
│  │   (id, name,    │     │ (id, emp_code,  │     │ (id, date,    │ │
│  │    head_id)     │     │  email, role,   │     │  geo_trace,   │ │
│  └─────────────────┘     │  password_hash) │     │  photo_url)   │ │
│                          └────────┬────────┘     └───────┬───────┘ │
│                                   │                      │         │
│  ┌─────────────────┐              │              ┌───────▼───────┐ │
│  │   ACTIVITIES    │◀─────────────┤              │  ATTENDANCE   │ │
│  │ (id, title,     │              │              │ (id, date,    │ │
│  │  assigned_to,   │              │              │  status,      │ │
│  │  target_date)   │              │              │  work_minutes)│ │
│  └────────┬────────┘              │              └───────────────┘ │
│           │                       │                                │
│  ┌────────▼────────┐     ┌────────▼────────┐     ┌───────────────┐ │
│  │   ACTIVITY      │     │      KRA        │     │  PAYROLL      │ │
│  │   ASSIGNMENTS   │     │ (id, title,     │     │  BATCHES      │ │
│  │ (id, level,     │     │  description,   │     │ (month, year, │ │
│  │  L1/L2/L3)      │     │  for_designation│     │  status)      │ │
│  └─────────────────┘     └─────────────────┘     └───────────────┘ │
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │   KRA_TRACKER   │     │   ESCALATIONS   │     │  APPROVALS    │ │
│  │ (employee_id,   │     │ (activity_id,   │     │ (record_type, │ │
│  │  kra_id, score) │     │  raised_by,     │     │  approver_id) │ │
│  └─────────────────┘     │  status)        │     └───────────────┘ │
│                          └─────────────────┘                        │
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  GEO_TRACKING   │     │ SALARY_TEMPLATES│     │   SETTINGS    │ │
│  │ (timesheet_id,  │     │ (department_id, │     │ (key, value,  │ │
│  │  lat, lon,      │     │  base_salary,   │     │  editable_by) │ │
│  │  timestamp)     │     │  HRA, allowance)│     └───────────────┘ │
│  └─────────────────┘     └─────────────────┘                        │
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  ACTIVITY       │     │  SYSTEM_ROLES   │     │ EMPLOYEE      │ │
│  │  EXTENSIONS     │     │ (role_name,     │     │ _ROLES        │ │
│  │ (old_date,      │     │  description)   │     │ (employee_id, │ │
│  │  new_date)      │     └─────────────────┘     │  role_id)     │ │
│  └─────────────────┘                             └───────────────┘ │
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │   AUDIT_LOGS    │     │ REVENUE_        │     │ REVENUE_      │ │
│  │ (timestamp,     │     │ TRANSACTIONS    │     │ SEGMENTS      │ │
│  │  action,        │     │ (trans_date,    │     │ (EV, BeV,     │ │
│  │  resource_type) │     │  amount_in/out) │     │  Fleet, etc.) │ │
│  └─────────────────┘     └─────────────────┘     └───────────────┘ │
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │ REVENUE_        │     │ REVENUE_        │     │ TRANSACTION   │ │
│  │ CATEGORIES      │     │ SOURCES         │     │ _IMAGES       │ │
│  │ (hierarchical)  │     │ (name)          │     │ (image_url)   │ │
│  └─────────────────┘     └─────────────────┘     └───────────────┘ │
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │ THIRD_PARTIES   │     │ REVENUE_        │     │ REVENUE_      │ │
│  │ (name,          │     │ AUDIT_LOG       │     │ CONFIG        │ │
│  │  contact_info)  │     │ (old_data,      │     │ (key, value)  │ │
│  └─────────────────┘     │  new_data)      │     └───────────────┘ │
│                          └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 1.2 Role Hierarchy & Permissions

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ROLE HIERARCHY (5 LEVELS)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Level 4: VGK4U (Supreme Admin)                                     │
│   ├── Full system access                                             │
│   ├── Settings management                                            │
│   ├── Payroll approval/release                                       │
│   ├── Employee deletion                                              │
│   ├── Audit logs access                                              │
│   └── Cannot be delegated                                            │
│                                                                      │
│   Level 3: HR (Human Resources)                                      │
│   ├── Employee CRUD (except VGK4U)                                   │
│   ├── Timesheet approval                                             │
│   ├── Attendance generation                                          │
│   ├── KRA management                                                 │
│   └── Report generation                                              │
│                                                                      │
│   Level 2: SUPERVISOR                                                │
│   ├── Team timesheet approval (department only)                      │
│   ├── Activity assignment                                            │
│   ├── View team records                                              │
│   └── Department-scoped access                                       │
│                                                                      │
│   Level 2: ACCOUNTS                                                  │
│   ├── Payroll creation                                               │
│   ├── Financial reports                                              │
│   └── Revenue management                                             │
│                                                                      │
│   Level 1: EMPLOYEE                                                  │
│   ├── Submit own timesheets                                          │
│   ├── View own records                                               │
│   └── Basic operations only                                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 1.3 Core Modules

| Module | Description | Tables Involved |
|--------|-------------|-----------------|
| **Employee Management** | CRUD operations for staff members | employees, departments, employee_roles |
| **Timesheet System** | GPS-tracked work logging | timesheets, geo_tracking, attendance |
| **Activity Management** | Task assignment with L1/L2/L3 levels | activities, activity_assignments, activity_extensions |
| **KRA System** | Key Result Areas tracking | kra, kra_tracker |
| **Attendance** | Auto-generated from timesheets | attendance (daily summaries) |
| **Payroll** | Monthly batch processing | payroll_batches, salary_templates |
| **Revenue Module** | Income/expense tracking | revenue_transactions, revenue_segments, revenue_categories |
| **Approvals** | Multi-level approval workflow | approvals (generic for all entities) |
| **Audit System** | Immutable activity logging | audit_logs (with triggers) |
| **Security** | Auth, 2FA, encryption | employees (security fields) |

---

### 1.4 API Endpoints (from original system)

```
AUTHENTICATION
├── POST /api/auth/login        → JWT token generation
├── GET  /api/auth/me           → Current user profile
└── POST /api/auth/2fa/verify   → TOTP verification

EMPLOYEE MANAGEMENT (HR/VGK4U)
├── GET    /api/employees       → List all employees
├── POST   /api/employees       → Create employee
├── PUT    /api/employees/<id>  → Update employee
└── DELETE /api/employees/<id>  → Delete employee (VGK4U only)

DEPARTMENTS
├── GET  /api/departments       → List departments
└── POST /api/departments       → Create department

TIMESHEETS
├── GET  /api/timesheets        → List timesheets (role-filtered)
├── POST /api/timesheet         → Submit timesheet with GPS
├── POST /api/timesheet/<id>/approve → Approve timesheet
└── GET  /api/timesheet/<id>/geo     → GPS trace details

ATTENDANCE
├── POST /api/attendance/generate    → Generate from timesheets
├── GET  /api/attendance             → List attendance records
└── PUT  /api/attendance/<id>        → Modify attendance

ACTIVITIES & KRA
├── GET  /api/activities        → List activities
├── POST /api/activities        → Create activity
├── GET  /api/kra               → List KRAs
├── POST /api/kra               → Create KRA
└── POST /api/kra/<id>/approve  → Approve KRA (VGK4U)

PAYROLL (VGK4U/ACCOUNTS)
├── POST /api/payroll/batch          → Create batch
├── POST /api/payroll/batch/<id>/approve  → Approve (VGK4U)
└── POST /api/payroll/batch/<id>/release  → Release (VGK4U)

SETTINGS (VGK4U ONLY)
├── GET  /api/settings          → View settings
└── PUT  /api/settings/<key>    → Update setting

REPORTS
├── GET /api/reports/attendance → Attendance summary
├── GET /api/reports/timesheet  → Timesheet summary
└── GET /api/reports/payroll    → Payroll reports
```

---

### 1.5 Security Features (Already Implemented)

| Feature | Implementation | Status |
|---------|----------------|--------|
| JWT Authentication | python-jose | ✅ Complete |
| Password Policy | 12+ chars, complexity | ✅ Complete |
| 2FA (TOTP) | PyOTP + QR code | ✅ Complete |
| Account Lockout | 5 attempts = 15min lock | ✅ Complete |
| Rate Limiting | Flask-Limiter (5/min login) | ✅ Complete |
| Field Encryption | Fernet + PBKDF2HMAC | ✅ Complete |
| Audit Logs | Immutable with triggers | ✅ Complete |
| RBAC Decorators | @requires_permission, @requires_role | ✅ Complete |
| Security Headers | CSP, X-Frame-Options, etc. | ✅ Complete |
| Input Sanitization | bleach, email-validator | ✅ Complete |

---

### 1.6 Known DC Protocol Violations (To Fix)

| Issue | Severity | Solution |
|-------|----------|----------|
| Dual Role System | 🔴 CRITICAL | Keep `employees.role`, deprecate `employee_roles` table |
| Duplicate Date Fields | 🟡 WARNING | Use `date_of_joining`, deprecate `doj` |
| Duplicate Status Fields | 🟡 WARNING | Use `status` VARCHAR, deprecate `active` BOOLEAN |

---

## PART 2: PHASE-WISE REIMPLEMENTATION STRATEGY

### Phase Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REIMPLEMENTATION PHASES                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 1: Database Foundation (Week 1)                              │
│  ├── Create staff tables in MNR PostgreSQL                          │
│  ├── Fix DC Protocol violations                                     │
│  └── Migrate audit infrastructure                                   │
│                                                                      │
│  PHASE 2: Core Models & Auth (Week 1-2)                             │
│  ├── Create SQLAlchemy models (FastAPI compatible)                  │
│  ├── Integrate with existing MNR auth                               │
│  └── Add staff-specific roles                                       │
│                                                                      │
│  PHASE 3: Employee & Department APIs (Week 2)                       │
│  ├── Implement CRUD endpoints                                       │
│  ├── Apply RBAC decorators                                          │
│  └── Add to MNR router                                              │
│                                                                      │
│  PHASE 4: Timesheet & Attendance (Week 2-3)                         │
│  ├── GPS tracking integration                                       │
│  ├── Photo upload handling                                          │
│  └── Auto-attendance generation                                     │
│                                                                      │
│  PHASE 5: Activity & KRA Management (Week 3)                        │
│  ├── Multi-level assignment (L1/L2/L3)                              │
│  ├── Extension requests                                             │
│  └── Escalation workflow                                            │
│                                                                      │
│  PHASE 6: Payroll & Reports (Week 3-4)                              │
│  ├── Batch processing                                               │
│  ├── Salary calculations                                            │
│  └── Report generation                                              │
│                                                                      │
│  PHASE 7: Frontend Integration (Week 4)                             │
│  ├── Staff login page                                               │
│  ├── Dashboard with role-based views                                │
│  └── All CRUD interfaces                                            │
│                                                                      │
│  PHASE 8: Testing & Security Audit (Week 4)                         │
│  ├── End-to-end testing                                             │
│  ├── Security penetration testing                                   │
│  └── Performance optimization                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### PHASE 1: Database Foundation
**Duration:** 2-3 days  
**Protocol:** DC (Data Consistency)

#### 1.1 Create Staff Tables (DC Compliant)

```sql
-- Staff System Tables for MNR PostgreSQL
-- Prefix: staff_ for namespace isolation

-- 1. Staff Departments
CREATE TABLE staff_departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    head_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Staff Employees (DC: Single role column, no duplicate fields)
CREATE TABLE staff_employees (
    id SERIAL PRIMARY KEY,
    emp_code VARCHAR(32) UNIQUE NOT NULL,
    full_name VARCHAR(256) NOT NULL,
    email VARCHAR(256) UNIQUE NOT NULL,
    phone VARCHAR(32),
    department_id INTEGER REFERENCES staff_departments(id),
    designation VARCHAR(128),
    role VARCHAR(64) DEFAULT 'employee',  -- SINGLE source of truth
    status VARCHAR(32) DEFAULT 'active',  -- SINGLE source of truth
    date_of_joining DATE,                 -- SINGLE source of truth
    password_hash VARCHAR(256),
    -- Security fields
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    totp_secret TEXT,
    last_password_change TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- (Additional tables follow same pattern...)
```

#### 1.2 DC Verification Checklist

- [ ] No duplicate fields (role/active/doj)
- [ ] Single source of truth for each data point
- [ ] Proper foreign key constraints
- [ ] Indexes for performance
- [ ] Audit trail setup

---

### PHASE 2: Core Models & Auth Integration
**Duration:** 2-3 days  
**Protocol:** WVV (Write-Verify-Validate)

#### 2.1 SQLAlchemy Models (FastAPI Compatible)

```python
# backend/app/models/staff.py

from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class StaffDepartment(Base):
    __tablename__ = 'staff_departments'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    head_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    employees = relationship("StaffEmployee", back_populates="department", foreign_keys="[StaffEmployee.department_id]")

class StaffEmployee(Base):
    __tablename__ = 'staff_employees'
    
    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String(32), unique=True, nullable=False, index=True)
    full_name = Column(String(256), nullable=False)
    email = Column(String(256), unique=True, nullable=False, index=True)
    phone = Column(String(32))
    department_id = Column(Integer, ForeignKey('staff_departments.id'))
    designation = Column(String(128))
    role = Column(String(64), default='employee', index=True)
    status = Column(String(32), default='active', index=True)
    date_of_joining = Column(Date)
    password_hash = Column(String(256))
    
    # Security fields
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    totp_secret = Column(Text, nullable=True)
    last_password_change = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    department = relationship("StaffDepartment", back_populates="employees", foreign_keys=[department_id])
```

#### 2.2 Auth Integration with MNR

```python
# backend/app/api/v1/endpoints/staff_auth.py

from fastapi import APIRouter, Depends, HTTPException
from app.core.security import create_access_token, verify_password
from app.models.staff import StaffEmployee

router = APIRouter()

@router.post("/staff/login")
async def staff_login(credentials: StaffLoginRequest, db: Session = Depends(get_db)):
    """
    Staff-specific login endpoint
    - Separate from MNR user login
    - Includes 2FA support
    - Account lockout protection
    """
    employee = db.query(StaffEmployee).filter_by(email=credentials.email).first()
    
    if not employee:
        raise HTTPException(401, "Invalid credentials")
    
    # Check lockout
    if employee.locked_until and employee.locked_until > datetime.utcnow():
        raise HTTPException(403, "Account locked. Try again later.")
    
    # Verify password
    if not verify_password(credentials.password, employee.password_hash):
        employee.failed_login_attempts += 1
        if employee.failed_login_attempts >= 5:
            employee.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        raise HTTPException(401, "Invalid credentials")
    
    # Check 2FA if enabled
    if employee.totp_secret and not credentials.totp_code:
        return {"requires_2fa": True}
    
    if employee.totp_secret:
        if not verify_totp(employee.totp_secret, credentials.totp_code):
            raise HTTPException(401, "Invalid 2FA code")
    
    # Reset failed attempts
    employee.failed_login_attempts = 0
    employee.locked_until = None
    db.commit()
    
    # Generate token
    token = create_access_token(
        subject=employee.id,
        user_type="staff",
        role=employee.role
    )
    
    return {
        "access_token": token,
        "employee": employee.to_dict()
    }
```

---

### PHASE 3: Employee & Department APIs
**Duration:** 2 days  
**Protocol:** WVV

#### 3.1 CRUD Endpoints with RBAC

```python
# backend/app/api/v1/endpoints/staff_employees.py

from fastapi import APIRouter, Depends, HTTPException
from app.core.rbac import requires_permission, requires_role

router = APIRouter()

@router.get("/staff/employees")
@requires_permission("view_all_employees")
async def list_employees(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """List employees (filtered by role)"""
    if current_user.role in ['vgk4u', 'hr']:
        return db.query(StaffEmployee).all()
    elif current_user.role == 'supervisor':
        # Only department members
        return db.query(StaffEmployee).filter_by(
            department_id=current_user.department_id
        ).all()
    else:
        return [current_user]

@router.post("/staff/employees")
@requires_permission("create_employee")
async def create_employee(
    data: EmployeeCreateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Create new employee (HR/VGK4U only)"""
    # Validate unique fields
    if db.query(StaffEmployee).filter_by(email=data.email).first():
        raise HTTPException(400, "Email already exists")
    
    if db.query(StaffEmployee).filter_by(emp_code=data.emp_code).first():
        raise HTTPException(400, "Employee code already exists")
    
    employee = StaffEmployee(**data.dict())
    employee.password_hash = hash_password(data.password)
    
    db.add(employee)
    db.commit()
    
    # Audit log
    log_audit("CREATE_EMPLOYEE", current_user, employee)
    
    return {"ok": True, "employee_id": employee.id}

@router.delete("/staff/employees/{emp_id}")
@requires_role("vgk4u", vgk_only=True)
async def delete_employee(
    emp_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Delete employee (VGK4U ONLY - cannot be delegated)"""
    employee = db.query(StaffEmployee).get(emp_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    
    # Cannot delete self
    if employee.id == current_user.id:
        raise HTTPException(400, "Cannot delete yourself")
    
    # Audit before delete
    log_audit("DELETE_EMPLOYEE", current_user, employee)
    
    db.delete(employee)
    db.commit()
    
    return {"ok": True}
```

---

### PHASE 4: Timesheet & Attendance
**Duration:** 3 days  
**Protocol:** WVV + DC

#### 4.1 Timesheet with GPS Tracking

```python
# backend/app/api/v1/endpoints/staff_timesheets.py

@router.post("/staff/timesheet")
async def submit_timesheet(
    data: TimesheetSubmitRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Submit timesheet with GPS trace and photo"""
    
    # Validate GPS trace format
    geo_trace = validate_geo_trace(data.geo_trace)
    
    # Validate photo (max 50KB)
    if data.photo_url:
        validate_photo_url(data.photo_url)
    
    timesheet = StaffTimesheet(
        employee_id=current_user.id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_minutes=data.duration_minutes,
        activity_id=data.activity_id,
        kra_id=data.kra_id,
        geo_trace=geo_trace,
        photo_url=data.photo_url,
        status='submitted'
    )
    
    db.add(timesheet)
    
    # Store individual GPS points
    for point in geo_trace:
        geo = StaffGeoTracking(
            timesheet_id=timesheet.id,
            employee_id=current_user.id,
            latitude=point['lat'],
            longitude=point['lon'],
            timestamp=point['t']
        )
        db.add(geo)
    
    db.commit()
    
    return {"ok": True, "timesheet_id": timesheet.id}
```

#### 4.2 Auto-Attendance Generation

```python
@router.post("/staff/attendance/generate")
@requires_permission("generate_attendance")
async def generate_attendance(
    data: AttendanceGenerateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Generate attendance from approved timesheets"""
    
    # Get settings
    present_minutes = int(get_setting('attendance_present_minutes', 480))
    half_day_minutes = int(get_setting('attendance_half_day_minutes', 240))
    
    # Find approved timesheets for date
    timesheets = db.query(StaffTimesheet).filter(
        StaffTimesheet.date == data.date,
        StaffTimesheet.supervisor_approval == True,
        StaffTimesheet.hr_approval == True
    ).all()
    
    records_created = 0
    
    for ts in timesheets:
        # Check if attendance already exists
        existing = db.query(StaffAttendance).filter_by(
            employee_id=ts.employee_id,
            attendance_date=data.date
        ).first()
        
        if existing:
            continue
        
        # Determine status based on minutes
        if ts.duration_minutes >= present_minutes:
            status = 'present'
        elif ts.duration_minutes >= half_day_minutes:
            status = 'half_day'
        else:
            status = 'absent'
        
        attendance = StaffAttendance(
            employee_id=ts.employee_id,
            attendance_date=data.date,
            total_hours=ts.duration_minutes / 60,
            status=status,
            source_timesheet_id=ts.id,
            approved_by=current_user.id
        )
        
        db.add(attendance)
        records_created += 1
    
    db.commit()
    
    return {"ok": True, "records_created": records_created}
```

---

### PHASE 5: Activity & KRA Management
**Duration:** 2 days  
**Protocol:** WVV

#### 5.1 Multi-Level Activity Assignment

```python
@router.post("/staff/activities")
@requires_permission("create_activity")
async def create_activity(
    data: ActivityCreateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Create activity with multi-level assignments"""
    
    activity = StaffActivity(
        title=data.title,
        description=data.description,
        created_by=current_user.id,
        department_id=data.department_id,
        target_date=data.target_date,
        status='Active'
    )
    
    db.add(activity)
    db.flush()  # Get activity.id
    
    # Create assignments for each level
    for assignment in data.assignments:
        assign = StaffActivityAssignment(
            activity_id=activity.id,
            employee_id=assignment.employee_id,
            level=assignment.level,  # L1, L2, L3
            status='Pending',
            review_deadline=datetime.utcnow() + timedelta(hours=48)
        )
        db.add(assign)
    
    db.commit()
    
    return {"ok": True, "activity_id": activity.id}
```

---

### PHASE 6: Payroll & Reports
**Duration:** 2-3 days  
**Protocol:** DC (Financial Data)

#### 6.1 Payroll Batch Processing

```python
@router.post("/staff/payroll/batch")
@requires_permission("create_payroll")
async def create_payroll_batch(
    data: PayrollBatchRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Create monthly payroll batch"""
    
    # Check if batch already exists
    existing = db.query(StaffPayrollBatch).filter_by(
        month=data.month,
        year=data.year
    ).first()
    
    if existing:
        raise HTTPException(400, "Batch already exists for this month")
    
    batch = StaffPayrollBatch(
        month=data.month,
        year=data.year,
        status='draft'
    )
    
    db.add(batch)
    db.commit()
    
    return {"ok": True, "batch_id": batch.id}

@router.post("/staff/payroll/batch/{batch_id}/approve")
@requires_role("vgk4u", vgk_only=True)
async def approve_payroll_batch(
    batch_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Approve payroll batch (VGK4U ONLY)"""
    
    batch = db.query(StaffPayrollBatch).get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    if batch.status != 'draft':
        raise HTTPException(400, "Batch must be in draft status")
    
    batch.status = 'locked'
    batch.approved_by = current_user.id
    
    db.commit()
    log_audit("APPROVE_PAYROLL", current_user, batch)
    
    return {"ok": True}
```

---

### PHASE 7: Frontend Integration
**Duration:** 3-4 days  
**Protocol:** FT (Frontend Testing)

#### 7.1 Staff Login Page

```html
<!-- frontend/staff_login.html -->
<!DOCTYPE html>
<html>
<head>
    <title>MNR Staff Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-md-6">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white text-center">
                        <h4><i class="fas fa-users"></i> MNR Staff Portal</h4>
                    </div>
                    <div class="card-body">
                        <form id="loginForm">
                            <div class="mb-3">
                                <label class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" class="form-control" id="password" required>
                            </div>
                            <div class="mb-3" id="totpSection" style="display:none;">
                                <label class="form-label">2FA Code</label>
                                <input type="text" class="form-control" id="totp" maxlength="6">
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Login</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/js/staff-login.js"></script>
</body>
</html>
```

#### 7.2 Role-Based Dashboard

```javascript
// frontend/static/js/staff-dashboard.js

async function loadDashboard() {
    const user = await getStaffProfile();
    
    // Show role-specific sections
    switch(user.role) {
        case 'vgk4u':
            showAllSections();
            showSettingsSection();
            showAuditLogsSection();
            break;
        case 'hr':
            showEmployeeSection();
            showTimesheetSection();
            showAttendanceSection();
            showPayrollSection();
            break;
        case 'supervisor':
            showTeamSection();
            showActivitySection();
            break;
        case 'accounts':
            showPayrollSection();
            showRevenueSection();
            break;
        default: // employee
            showMyTimesheetSection();
            showMyAttendanceSection();
    }
}
```

---

### PHASE 8: Testing & Security Audit
**Duration:** 2-3 days  
**Protocol:** WVV + STF (Test → Fix → Retest)

#### 8.1 Test Checklist

| Test Category | Test Cases | Status |
|---------------|------------|--------|
| **Authentication** | Login, logout, 2FA, lockout | ⬜ |
| **Authorization** | Role-based access for all endpoints | ⬜ |
| **Employee CRUD** | Create, read, update, delete | ⬜ |
| **Timesheet** | Submit, GPS validation, approval | ⬜ |
| **Attendance** | Auto-generation, status calculation | ⬜ |
| **Payroll** | Batch create, approve, release | ⬜ |
| **Audit Logs** | Immutability, completeness | ⬜ |
| **Security** | Rate limiting, injection, XSS | ⬜ |

---

## PART 3: INTEGRATION POINTS WITH MNR

### 3.1 Shared Infrastructure

| Component | MNR System | Staff System | Integration |
|-----------|------------|--------------|-------------|
| Database | PostgreSQL (Neon) | Same instance | Different tables (staff_ prefix) |
| Auth | JWT (python-jose) | Same library | Separate token type |
| Frontend | Node.js (port 5000) | Same server | New routes (/staff/*) |
| Backend | FastAPI (port 8000) | Same server | New router (/api/v1/staff/*) |

### 3.2 New Routes to Add

```python
# backend/app/api/v1/router.py

from app.api.v1.endpoints import staff_auth, staff_employees, staff_timesheets, staff_attendance, staff_payroll

# Add staff system routes
api_router.include_router(staff_auth.router, prefix="/staff", tags=["Staff Auth"])
api_router.include_router(staff_employees.router, prefix="/staff", tags=["Staff Employees"])
api_router.include_router(staff_timesheets.router, prefix="/staff", tags=["Staff Timesheets"])
api_router.include_router(staff_attendance.router, prefix="/staff", tags=["Staff Attendance"])
api_router.include_router(staff_payroll.router, prefix="/staff", tags=["Staff Payroll"])
```

### 3.3 Frontend Routes to Add

```javascript
// frontend/server.js - Add staff routes

// Staff System Routes
app.get('/staff/login', (req, res) => serveStaffLogin(req, res));
app.get('/staff/dashboard', (req, res) => serveStaffDashboard(req, res));
app.get('/staff/employees', (req, res) => serveStaffEmployees(req, res));
app.get('/staff/timesheets', (req, res) => serveStaffTimesheets(req, res));
app.get('/staff/attendance', (req, res) => serveStaffAttendance(req, res));
app.get('/staff/payroll', (req, res) => serveStaffPayroll(req, res));
app.get('/staff/activities', (req, res) => serveStaffActivities(req, res));
app.get('/staff/settings', (req, res) => serveStaffSettings(req, res));
```

---

## PART 4: DELIVERABLES CHECKLIST

### Phase 1 Deliverables
- [ ] staff_departments table created
- [ ] staff_employees table created (DC compliant)
- [ ] All 23 staff tables created
- [ ] Audit triggers installed
- [ ] DC verification complete

### Phase 2 Deliverables
- [ ] SQLAlchemy models for all tables
- [ ] Staff auth endpoint working
- [ ] JWT with staff user_type
- [ ] 2FA integration complete

### Phase 3 Deliverables
- [ ] Employee CRUD endpoints
- [ ] Department CRUD endpoints
- [ ] RBAC decorators applied
- [ ] Audit logging working

### Phase 4 Deliverables
- [ ] Timesheet submit with GPS
- [ ] Photo upload handling
- [ ] Timesheet approval workflow
- [ ] Auto-attendance generation

### Phase 5 Deliverables
- [ ] Activity CRUD with L1/L2/L3
- [ ] KRA management
- [ ] Extension requests
- [ ] Escalation workflow

### Phase 6 Deliverables
- [ ] Payroll batch processing
- [ ] VGK4U-only approval
- [ ] Salary calculations
- [ ] Report generation

### Phase 7 Deliverables
- [ ] Staff login page
- [ ] Role-based dashboard
- [ ] All CRUD interfaces
- [ ] Mobile-responsive design

### Phase 8 Deliverables
- [ ] All tests passing
- [ ] Security audit complete
- [ ] Performance optimized
- [ ] Documentation updated

---

## APPENDIX: FILES TO RESTORE FROM GIT

```bash
# Commands to extract original files
git show f678daf:employee-tracker-backend/app.py
git show f678daf:employee-tracker-backend/models.py
git show f678daf:employee-tracker-backend/routes.py
git show f678daf:employee-tracker-backend/security.py
git show f678daf:employee-tracker-backend/rbac.py
git show f678daf:employee-tracker-backend/audit.py
git show f678daf:employee-tracker-backend/SCHEMA.sql
git show f678daf:employee-tracker-backend/templates/login.html
git show f678daf:employee-tracker-backend/templates/dashboard.html
```

---

**Document Status:** Ready for Review  
**Next Step:** Approve Phase 1 to begin implementation  
**Estimated Total Duration:** 4 weeks
