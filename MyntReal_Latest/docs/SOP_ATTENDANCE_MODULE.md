# Attendance Module - Standard Operating Procedure (SOP)

**Document Version:** 1.0  
**Created:** January 04, 2026  
**System:** MyntReal LLP Staff Management System  
**Module:** Attendance Management

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Role Definitions & Access Levels](#2-role-definitions--access-levels)
3. [Frontend Pages & Functions](#3-frontend-pages--functions)
4. [Permissions Matrix](#4-permissions-matrix)
5. [Step-by-Step Workflows by Role](#5-step-by-step-workflows-by-role)
6. [Screen-by-Screen Instructions](#6-screen-by-screen-instructions)
7. [Status Definitions](#7-status-definitions)
8. [Reconciliation Rules](#8-reconciliation-rules)
9. [Exception Handling](#9-exception-handling)

---

## 1. Module Overview

The Attendance Module provides comprehensive attendance management for staff including:

- **Clock In/Out System**: Daily punch records with timestamp capture
- **Location Tracking**: Office, WFH (Work From Home), Field, or Hybrid modes
- **Break Management**: Paid/unpaid break tracking with type categorization
- **Photo Evidence**: Clock-in/out photo capture with GPS location
- **Attendance Sheet**: HR bulk marking with EA/VGK approval workflow
- **Reporting & Analytics**: Monthly reports, reconciliation, exception tracking

### Key Features

| Feature | Description |
|---------|-------------|
| Daily Punch Records | Clock-in/out with timestamp capture |
| Location Modes | Office, WFH, Field, Hybrid |
| Break Management | Paid/unpaid breaks with type reference |
| Photo Evidence | Camera capture with GPS coordinates |
| Face Detection | AI-powered human face verification |
| Auto-Calculation | Worked hours computed automatically |
| Audit Trail | Immutable log of all attendance actions |

---

## 2. Role Definitions & Access Levels

### 2.1 Role Hierarchy

| Role Code | Role Name | Hierarchy Level | Description |
|-----------|-----------|-----------------|-------------|
| `vgk4u` | VGK4U Supreme | 100 | Full system access, highest authority |
| `ea` | Executive Assistant | 90 | Approval authority, exception bypass |
| `hr` | Human Resources | 80 | Attendance marking, employee management |
| `manager` | Manager | 70 | Team oversight, reporting access |
| `team_leader` | Team Leader | 60 | Team attendance view |
| `senior_executive` | Senior Executive | 50 | Limited team access |
| `employee` | Staff | 30 | Personal attendance only |

### 2.2 Role Capabilities Summary

| Role | Mark Attendance | Approve Hours | View Team | Edit Status | Exception Bypass | Reports |
|------|-----------------|---------------|-----------|-------------|------------------|---------|
| Staff | Own only | No | No | No | No | Own only |
| Manager | No | No | Own team | No | No | Team |
| HR | Yes (All) | No | All | No | No | All |
| EA | Yes | Yes | All | Yes | Yes | All |
| VGK4U Supreme | Yes | Yes | All | Yes | Yes | All |

---

## 3. Frontend Pages & Functions

### 3.1 Page Directory

| Page | File | Primary Users | Purpose |
|------|------|---------------|---------|
| My Attendance (In/Out Time) | `staff_my_attendance.html` | All Staff | Personal clock-in/out, breaks |
| Team Attendance | `staff_team_attendance.html` | Manager, HR, EA, VGK4U | View team records |
| Attendance Sheet | `staff_attendance_sheet.html` | HR, EA, VGK4U | Bulk marking & approval |
| Attendance Reports | `staff_attendance_reports.html` | Manager, HR, EA, VGK4U | Analytics dashboard |
| Attendance Exceptions | `staff_attendance_exceptions.html` | EA, VGK4U | Exception approvals |
| Team Attendance Summary | `staff_team_attendance_summary.html` | Manager, HR, EA, VGK4U | Monthly summary view |

### 3.2 Page Functions Detail

#### My Attendance (`staff_my_attendance.html`)
- **Clock In**: Start work day with photo + GPS capture
- **Clock Out**: End work day with photo + GPS capture
- **Start Break**: Begin break with type selection
- **End Break**: Complete break session
- **Work Mode Selection**: Office/WFH/Field/Hybrid
- **Today's Timeline**: Visual activity log
- **Monthly History**: Past attendance records
- **Statistics**: Worked hours, breaks, overtime

#### Team Attendance (`staff_team_attendance.html`)
- **Live Status Dashboard**: Real-time team presence
- **Date Filter**: View specific date records
- **Department Filter**: Filter by department
- **Status Indicators**: Present/Absent/On Break
- **Admin Clock Out**: Force clock-out for employees
- **Photo Viewing**: View clock-in/out photos
- **Location Display**: GPS coordinates and area names

#### Attendance Sheet (`staff_attendance_sheet.html`)
- **Monthly Grid View**: Calendar-style attendance display
- **Bulk Marking**: HR marks multiple employees
- **Status Assignment**: Present/Half Day/Leave types
- **Approval Workflow**: EA/VGK approval process
- **Reconciliation Alerts**: Timesheet mismatch warnings
- **Exception Handling**: Bypass approvals for exceptions
- **Export Functions**: CSV/Excel export

#### Attendance Reports (`staff_attendance_reports.html`)
- **Attendance Analytics**: Charts and graphs
- **Department Comparison**: Cross-department metrics
- **Trend Analysis**: Weekly/Monthly patterns
- **Late Arrival Tracking**: Punctuality metrics
- **Export Capabilities**: Report downloads

---

## 4. Permissions Matrix

### 4.1 Feature-Level Permissions

| Feature/Action | Staff | Manager | HR | EA | VGK4U Supreme |
|----------------|-------|---------|----|----|---------------|
| **Clock In/Out** |
| Clock in (own) | Yes | Yes | Yes | Yes | Yes |
| Clock out (own) | Yes | Yes | Yes | Yes | Yes |
| View own history | Yes | Yes | Yes | Yes | Yes |
| **Breaks** |
| Start/end breaks | Yes | Yes | Yes | Yes | Yes |
| View break types | Yes | Yes | Yes | Yes | Yes |
| **Team Access** |
| View team attendance | No | Own Team | All | All | All |
| Force clock-out others | No | No | No | Yes | Yes |
| View photos (team) | No | Yes | Yes | Yes | Yes |
| **Attendance Sheet** |
| View attendance sheet | No | View Only | Yes | Yes | Yes |
| Mark attendance | No | No | Yes | Yes | Yes |
| Edit attendance status | No | No | No | Yes | Yes |
| Approve hours | No | No | No | Yes | Yes |
| Bulk approve | No | No | No | Yes | Yes |
| **Exceptions** |
| View exceptions | No | No | View | Yes | Yes |
| Grant exception bypass | No | No | No | Yes | Yes |
| **Reports** |
| View own reports | Yes | Yes | Yes | Yes | Yes |
| View team reports | No | Own Team | All | All | All |
| View all reports | No | No | Yes | Yes | Yes |
| Export reports | No | No | Yes | Yes | Yes |
| **System** |
| Configure break types | No | No | No | No | Yes |
| Configure attendance rules | No | No | No | No | Yes |

### 4.2 Data Access Scope

| Role | Employee Scope | Department Scope | Company Scope |
|------|----------------|------------------|---------------|
| Staff | Self only | N/A | N/A |
| Manager | Direct reports | Own department | N/A |
| HR | All active | All | Base company |
| EA | All | All | All assigned |
| VGK4U Supreme | All | All | All |

---

## 5. Step-by-Step Workflows by Role

### 5.1 Staff Workflow

#### Daily Attendance Workflow

```
START DAY
    │
    ├── 1. Navigate to "My Attendance" (In/Out Time)
    │
    ├── 2. Select Work Mode
    │       ├── Office (default)
    │       ├── WFH (Work From Home)
    │       ├── Field
    │       └── Hybrid
    │
    ├── 3. Click "Clock In" Button
    │       ├── Camera opens automatically
    │       ├── Take selfie photo
    │       ├── Face detection validates
    │       ├── GPS location captured
    │       └── Timestamp recorded
    │
    ├── 4. DURING WORK DAY
    │       │
    │       ├── Take Break
    │       │   ├── Click "Start Break"
    │       │   ├── Select break type (Lunch/Tea/Personal/etc.)
    │       │   ├── Break timer starts
    │       │   └── Click "End Break" when returning
    │       │
    │       └── View Status
    │           ├── Current worked hours
    │           ├── Break time consumed
    │           └── Today's timeline
    │
    ├── 5. Click "Clock Out" Button
    │       ├── Camera opens
    │       ├── Take exit photo
    │       ├── GPS location captured
    │       └── Day marked complete
    │
    └── 6. Review Daily Summary
            ├── Total worked hours
            ├── Total break time
            └── Status (Present/Half Day)
```

#### Viewing History Workflow

```
VIEW HISTORY
    │
    ├── 1. Go to "My Attendance"
    │
    ├── 2. Scroll to "Attendance History" section
    │
    ├── 3. Filter by month/date range
    │
    └── 4. View details
            ├── Clock in/out times
            ├── Break records
            ├── Worked hours
            └── Status (Present/Absent/Half Day)
```

---

### 5.2 Manager Workflow

#### Team Monitoring Workflow

```
DAILY MONITORING
    │
    ├── 1. Navigate to "In/Out Records - Admin"
    │
    ├── 2. View Dashboard Stats
    │       ├── Total team members
    │       ├── Present count
    │       ├── Absent count
    │       └── On break count
    │
    ├── 3. Apply Filters (optional)
    │       ├── Date selection
    │       ├── Department filter
    │       └── Status filter
    │
    ├── 4. Review Individual Records
    │       ├── Employee name/code
    │       ├── Clock in/out times
    │       ├── Location mode
    │       ├── Battery status
    │       └── Break status
    │
    └── 5. View Photo Evidence (if needed)
            ├── Click "View Photos" button
            ├── See clock-in photo
            ├── See clock-out photo
            └── Verify GPS location
```

#### Team Reports Workflow

```
GENERATE REPORTS
    │
    ├── 1. Go to "Attendance Dashboard"
    │
    ├── 2. Select Report Period
    │       ├── This Week
    │       ├── This Month
    │       ├── This Quarter
    │       └── This Year
    │
    ├── 3. Apply Department Filter (own team auto-selected)
    │
    ├── 4. Review Analytics
    │       ├── Average attendance %
    │       ├── Total working hours
    │       ├── Late arrival count
    │       └── Trend charts
    │
    └── 5. Export Report (CSV)
```

---

### 5.3 HR Workflow

#### Bulk Attendance Marking Workflow

```
MARK ATTENDANCE
    │
    ├── 1. Navigate to "Attendance Records"
    │
    ├── 2. Select Month/Year
    │       └── Use date picker
    │
    ├── 3. Apply Filters
    │       ├── Department
    │       ├── Manager
    │       ├── Staff Type (MN Staff/Employee/Freelancer)
    │       └── Shift type
    │
    ├── 4. View Monthly Grid
    │       ├── Employees listed vertically
    │       ├── Dates as columns
    │       └── Status cells (color-coded)
    │
    ├── 5. Mark Individual Cells
    │       │
    │       ├── Click on empty cell
    │       │
    │       ├── Select Status:
    │       │   ├── Present (8 hours)
    │       │   ├── Half Day (4 hours)
    │       │   ├── Absent (0 hours)
    │       │   ├── Sick Leave
    │       │   ├── Approved Leave
    │       │   ├── Casual Leave
    │       │   ├── Unpaid Leave
    │       │   ├── Holiday
    │       │   └── Weekend
    │       │
    │       └── Add Notes (optional)
    │
    ├── 6. Check Reconciliation Status
    │       ├── ✓ Matched: Timesheet matches marked hours
    │       ├── ⚠ Mismatch Warning: >30 min difference
    │       ├── ✗ No Entry: No timesheet for date
    │       └── 🔧 Manual Override: Status manually set
    │
    └── 7. Records sent to EA/VGK for approval
```

---

### 5.4 EA (Executive Assistant) Workflow

#### Approval Workflow

```
APPROVE ATTENDANCE
    │
    ├── 1. Navigate to "Attendance Records"
    │
    ├── 2. Filter for Pending Approvals
    │       └── Approval Status = "Pending"
    │
    ├── 3. Review Marked Records
    │       │
    │       ├── Check Reconciliation Status:
    │       │   │
    │       │   ├── IF Matched:
    │       │   │   ├── Review marked hours
    │       │   │   └── Proceed to approve
    │       │   │
    │       │   ├── IF Mismatch Warning:
    │       │   │   ├── Compare marked vs timesheet hours
    │       │   │   ├── Investigate discrepancy
    │       │   │   ├── Provide approval reason
    │       │   │   └── Approve with explanation
    │       │   │
    │       │   └── IF No Entry:
    │       │       ├── BLOCKED by default
    │       │       ├── Employee must submit timesheet
    │       │       │
    │       │       └── OR Grant Exception Bypass:
    │       │           ├── Check "Bypass Exception" option
    │       │           ├── Enter reason (min 10 characters)
    │       │           └── Exception logged in audit
    │
    ├── 4. Approve Individual Record
    │       ├── Set approved hours (can differ from marked)
    │       ├── Change status if needed
    │       ├── Add approval reason
    │       └── Click "Approve"
    │
    └── 5. OR Bulk Approve
            ├── Select month
            ├── Apply department filter
            ├── Click "Bulk Approve"
            ├── System skips NO_ENTRY records
            └── Review approval summary
```

#### Edit Attendance Status Workflow

```
EDIT STATUS
    │
    ├── 1. Find the attendance record
    │
    ├── 2. Click "Edit" button
    │
    ├── 3. Select new status
    │       └── (Present, Half Day, Leave types, etc.)
    │
    ├── 4. Enter edit reason (required)
    │
    ├── 5. Submit change
    │       ├── Marked hours recalculated
    │       ├── Approval status reset to PENDING
    │       └── Audit log created
    │
    └── 6. Re-approve if needed
```

#### Exception Management Workflow

```
HANDLE EXCEPTIONS
    │
    ├── 1. Go to "Attendance Exceptions"
    │
    ├── 2. View Exception Requests
    │       ├── Filter by company
    │       ├── Filter by date range
    │       └── Filter by status
    │
    ├── 3. Review Exception Details
    │       ├── Employee info
    │       ├── Exception type (No Timesheet/Mismatch Override)
    │       ├── Reconciliation snapshot
    │       └── Requester reason
    │
    └── 4. Grant or Deny
            ├── IF Grant:
            │   ├── Enter approval reason
            │   ├── Set approved hours
            │   └── Exception recorded in audit
            │
            └── IF Deny:
                └── Reject with reason
```

---

### 5.5 VGK4U Supreme Workflow

VGK4U Supreme has all EA capabilities plus:

#### System Configuration Workflow

```
CONFIGURE SYSTEM
    │
    ├── Break Types Management
    │   ├── Add new break types
    │   ├── Set duration limits
    │   ├── Mark paid/unpaid
    │   └── Set evidence requirements
    │
    ├── Attendance Rules
    │   ├── Standard work hours (default: 8)
    │   ├── Half day threshold (default: 4 hours)
    │   ├── Late tolerance
    │   └── Auto-close settings
    │
    └── Report Access
        ├── Company-wide reports
        ├── Cross-department analytics
        └── Exception audit reports
```

#### Complete Audit Trail Access

```
AUDIT REVIEW
    │
    ├── 1. Access any attendance record
    │
    ├── 2. View full change history
    │       ├── Who made changes
    │       ├── What was changed
    │       ├── When changed
    │       └── Why (reason)
    │
    └── 3. Review exception grants
            ├── All bypass approvals
            ├── Approver details
            └── Original reconciliation state
```

---

## 6. Screen-by-Screen Instructions

### 6.1 My Attendance Screen (Staff)

#### Screen Layout
```
┌─────────────────────────────────────────────────────────┐
│ HEADER: MyntReal LLP - In/Out Time    [User Info] [X]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              PUNCH CARD (Purple)                 │   │
│  │                                                  │   │
│  │           Current Time: 10:30 AM                 │   │
│  │           Monday, January 04, 2026               │   │
│  │                                                  │   │
│  │        Status: ✓ Clocked In (2h 30m)            │   │
│  │                                                  │   │
│  │    [Office] [WFH] [Field] [Hybrid]              │   │
│  │                                                  │   │
│  │  [🟢 CLOCK OUT]    [☕ START BREAK]             │   │
│  │                                                  │   │
│  │         📍 Location captured                     │   │
│  │         🔋 Battery: 85%                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  TODAY'S STATS                                   │   │
│  │  [Worked: 2h 30m] [Breaks: 15m] [OT: 0m]        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  TODAY'S TIMELINE                                │   │
│  │  ● 08:00 - Clock In (Office)                    │   │
│  │  ○ 10:00 - Break Start (Tea)                    │   │
│  │  ● 10:15 - Break End                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  MONTHLY HISTORY                                 │   │
│  │  [Month: January 2026 ▼]                        │   │
│  │  ┌──────────────────────────────────────────┐   │   │
│  │  │ Date    In     Out    Hours  Status     │   │   │
│  │  │ Jan 03  08:00  17:30  8.5h   Present    │   │   │
│  │  │ Jan 02  08:15  17:00  8.0h   Present    │   │   │
│  │  └──────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Button States & Actions

| Button | State | Action |
|--------|-------|--------|
| CLOCK IN | Visible before clock-in | Opens camera modal, captures photo + GPS |
| CLOCK OUT | Visible after clock-in | Opens camera modal, ends work day |
| START BREAK | Visible when clocked in | Opens break type selector |
| END BREAK | Visible during break | Ends current break |

#### Camera Modal Instructions

1. **Grant Permissions**: Allow camera and location access
2. **Position Face**: Align face in the frame
3. **Face Detection**: Wait for green indicator
4. **Capture**: Click capture button
5. **Confirm**: Review photo and confirm

---

### 6.2 Team Attendance Screen (Manager/HR/EA/VGK4U)

#### Screen Layout
```
┌─────────────────────────────────────────────────────────┐
│ HEADER: In/Out Records - Admin        [User] [Logout]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ TOTAL   │ │ PRESENT │ │ ABSENT  │ │ LATE    │       │
│  │   45    │ │   38    │ │    5    │ │    3    │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ FILTERS                                          │   │
│  │ [Date: 2026-01-04] [Dept: All ▼] [Status: All ▼]│   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ATTENDANCE TABLE                                 │   │
│  │ ┌─────────────────────────────────────────────┐ │   │
│  │ │ Employee     In      Out    Mode   Status   │ │   │
│  │ │ ──────────────────────────────────────────── │ │   │
│  │ │ 👤 John Doe  08:00   -      Office  🟢 In   │ │   │
│  │ │ 👤 Jane S.   08:15   -      WFH     🟢 In   │ │   │
│  │ │ 👤 Mike R.   09:00   17:00  Field   ✓ Done  │ │   │
│  │ │ 👤 Sarah K.  -       -      -       ⚪ Absent│ │   │
│  │ └─────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Filter Options

| Filter | Options | Purpose |
|--------|---------|---------|
| Date | Calendar picker | View specific date |
| Department | Dropdown list | Filter by department |
| Status | Present/Absent/On Break/All | Filter by current status |
| Location Mode | Office/WFH/Field/All | Filter by work mode |

#### Table Column Descriptions

| Column | Description |
|--------|-------------|
| Employee | Name, code, avatar |
| Clock In | Time with late indicator |
| Clock Out | Time or "-" if still working |
| Mode | Office/WFH/Field badge |
| Status | Present/Absent/On Break |
| Battery | Battery percentage at last update |
| Photos | View photos button |
| Actions | Admin clock-out button |

---

### 6.3 Attendance Sheet Screen (HR/EA/VGK4U)

#### Screen Layout
```
┌─────────────────────────────────────────────────────────┐
│ HEADER: Attendance Records            [User] [Logout]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ FILTERS                                          │   │
│  │ [Month: Jan 2026 ▼] [Dept: All ▼] [Manager: ▼] │   │
│  │ [Status: All ▼] [Reconciliation: All ▼]         │   │
│  │ [Apply] [Clear] [Export CSV]                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ MONTHLY GRID                                     │   │
│  │ ┌─────────────────────────────────────────────┐ │   │
│  │ │ Employee   │ 1  │ 2  │ 3  │ 4  │ ... │ Net │ │   │
│  │ │ ────────────────────────────────────────────│ │   │
│  │ │ John Doe   │ P  │ P  │ H  │ P  │     │ 3.0 │ │   │
│  │ │ Jane Smith │ P  │ A  │ H  │ ⚠P │     │ 2.0 │ │   │
│  │ │ Mike Ross  │ ✗  │ L  │ H  │ P  │     │ 1.5 │ │   │
│  │ └─────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  LEGEND:                                                │
│  P = Present  H = Half Day  A = Absent  L = Leave      │
│  ✗ = No Entry  ⚠ = Mismatch Warning                    │
│                                                         │
│  [Bulk Approve Pending] (EA/VGK4U only)                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Cell Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| Present | Green | Full day attendance |
| Half Day | Yellow | Partial attendance |
| Absent | Red | Not present |
| Leave | Blue | Approved leave |
| Holiday | Gray | Public holiday |
| Weekend | Light Gray | Non-working day |

#### Reconciliation Indicators

| Symbol | Status | Description |
|--------|--------|-------------|
| ✓ | Matched | Timesheet matches marked hours (±30 min) |
| ⚠ | Mismatch Warning | >30 min difference from timesheet |
| ✗ | No Entry | No timesheet submitted |
| 🔧 | Manual Override | Status manually set by EA/VGK4U |

---

### 6.4 Approval Modal (EA/VGK4U)

#### Modal Layout
```
┌───────────────────────────────────────────────────┐
│ APPROVE ATTENDANCE                          [X]   │
├───────────────────────────────────────────────────┤
│                                                   │
│ Employee: John Doe (MN10025)                      │
│ Date: January 04, 2026                            │
│                                                   │
│ ┌───────────────────────────────────────────────┐ │
│ │ HR Marked Status: Present (8 hours)           │ │
│ │ Timesheet Hours:  7.5 hours                   │ │
│ │ Reconciliation:   ⚠ Mismatch (-30 min)       │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ Approved Hours: [____8____] hours                │
│                                                   │
│ Change Status: [Present ▼]                        │
│   ○ Present   ○ Half Day   ○ Absent              │
│   ○ Sick Leave  ○ Casual Leave  ○ Other          │
│                                                   │
│ Approval Reason: (Required for mismatch)         │
│ ┌───────────────────────────────────────────────┐ │
│ │ Verified with employee - 30 min client call   │ │
│ │ not logged in timesheet.                      │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ ☐ Bypass Exception (if no timesheet)             │
│   Exception Reason: [________________]            │
│                                                   │
│         [Cancel]        [✓ Approve]               │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## 7. Status Definitions

### 7.1 Attendance Status

| Status | Code | Hours | Description |
|--------|------|-------|-------------|
| Present | `present` | 8 | Full working day |
| Half Day | `half_day` | 4 | Partial attendance (4-8 hours worked) |
| Absent | `absent` | 0 | No attendance, no leave |
| Sick Leave | `sick_leave` | 0 | Medical leave |
| Approved Leave | `approved_leave` | 0 | Pre-approved leave |
| Casual Leave | `casual_leave` | 0 | Casual/personal leave |
| Unpaid Leave | `unpaid_leave` | 0 | Leave without pay |
| Holiday | `holiday` | 8 | Company holiday |
| Weekend | `weekend` | 0 | Non-working day |

### 7.2 Approval Status

| Status | Code | Description |
|--------|------|-------------|
| Pending | `pending` | Awaiting EA/VGK4U approval |
| Approved | `approved` | Hours approved |
| Rejected | `rejected` | Approval denied |
| On Hold | `on_hold` | Pending investigation |

### 7.3 Reconciliation Status

| Status | Code | Description |
|--------|------|-------------|
| Matched | `matched` | Marked hours ≈ timesheet (±30 min) |
| Mismatch Warning | `mismatch_warning` | Significant hour difference |
| Manual Override | `manual_override` | EA/VGK4U bypassed rules |
| No Entry | `no_entry` | No timesheet for date |

---

## 8. Reconciliation Rules

### 8.1 Tolerance Calculation

```
Tolerance = ±30 minutes (0.5 hours)

IF |Marked Hours - Timesheet Hours| ≤ 0.5:
    Status = MATCHED
ELSE:
    Status = MISMATCH_WARNING
```

### 8.2 Approval Rules

| Scenario | HR Action | EA/VGK4U Action |
|----------|-----------|-----------------|
| Matched | Mark attendance | Approve (no reason needed) |
| Mismatch Warning | Mark attendance | Approve with reason |
| No Entry (default) | Mark attendance | BLOCKED - Cannot approve |
| No Entry + Bypass | Mark attendance | Approve with exception |

### 8.3 Exception Bypass Requirements

- **Minimum Reason Length**: 10 characters
- **Exception Record Created**: Yes (immutable audit)
- **Snapshot Stored**: Original reconciliation state
- **Approver Logged**: Employee ID and role

---

## 9. Exception Handling

### 9.1 Exception Types

| Type | Code | Description |
|------|------|-------------|
| No Timesheet | `no_timesheet` | Approved without timesheet entry |
| Mismatch Override | `mismatch_override` | Approved despite hour mismatch |
| Manual Adjustment | `manual_adjustment` | Manual hour adjustment |

### 9.2 Exception Approval Flow

```
EXCEPTION REQUEST
    │
    ├── 1. EA/VGK4U identifies blocked record
    │
    ├── 2. Check "Bypass Exception" option
    │
    ├── 3. Enter detailed reason (min 10 chars)
    │       Examples:
    │       - "Field work without system access"
    │       - "Employee on client site - verbal confirmation"
    │       - "System outage prevented timesheet entry"
    │
    ├── 4. Submit for approval
    │
    ├── 5. System creates:
    │       ├── StaffAttendanceException record
    │       ├── Reconciliation snapshot
    │       └── Audit trail entry
    │
    └── 6. Record marked as MANUAL_OVERRIDE
```

### 9.3 Exception Audit Report

Available to EA/VGK4U:

| Field | Description |
|-------|-------------|
| Exception ID | Unique identifier |
| Company | Associated company |
| Employee | Employee name/code |
| Date | Attendance date |
| Bypass Type | Exception category |
| Exception Reason | Justification text |
| Approver | Who approved |
| Approver Role | EA or VGK4U |
| Original State | Reconciliation snapshot |
| Approved Hours | Final approved hours |
| Created At | Timestamp |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-04 | System | Initial SOP creation |

---

**End of Document**
