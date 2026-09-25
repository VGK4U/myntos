# MYNTOS — SAAS MODULE EXPANSION ARCHITECTURE DISCOVERY REPORT
## SERVICE + HRMS (EMPLOYEES, ATTENDANCE, JOURNEYS, TASKS, KRA, TIMESHEET)
### Web, /mobile, Android (Capacitor), and iOS (Capacitor)

---

## 1. Executive Summary & Current State

MyntOS has successfully established an authoritative, multi-tenant SaaS foundation with `CORE WORKSPACE` (Company Profile, Staff & Users, CRM/Workflow Setup), `CRM & LEADS`, and `WORKFLOWS`.

A comprehensive, read-only discovery of the codebase reveals that **MyntOS already contains complete, highly sophisticated backend engines, databases, web interfaces, and mobile screens for Service Desk and the entire HRMS suite**.
Nothing needs to be built from scratch. Rather, the existing engines were historically built for internal multi-entity operations (MR, RVZ, Zynova) using role-based visibility (`key_leadership`, `manager`, `vgk4u`). 

The SaaS expansion task is an **entitlement, tenant-scoping, and navigation integration pass**:
1. Map `SERVICE_TICKETS` and `STAFF_HRMS` in the SaaS Entitlement Resolver (`saas_tenant_resolver.py`).
2. Bind existing query services to `RequestContext.tenant_company_id` so that SaaS tenants only see their own tickets, employees, attendance, journeys, tasks, KRAs, and timesheets.
3. Expose canonical, clean SaaS sidebar menus on Web and `/mobile` (and via Capacitor on Android and iOS).
4. Strictly protect internal platform engines (Zynova MLM, VGK team marketplace, internal group accounting, platform administration) from tenant leakage.
5. Strictly adhere to **Rule #6 Telephony Freeze** and **Rule #5 Single Platform Parity**.

---

## 2. Current SaaS Module Registry & Entitlement Architecture

### A. SaaS Module Definitions & Aliases
In `backend/app/services/saas_tenant_resolver.py`, the `MODULE_ALIASES` dictionary establishes the canonical module codes:
- **`CORE_WORKSPACE`**: Non-negotiable foundation for every SaaS tenant.
- **`CRM_LEADS`**: `{'CRM_LEADS', 'CRM', 'CRM & LEADS'}`
- **`SOLAR_EV`**: `{'SOLAR_EV', 'SOLAR', 'SOLAR & EV', 'WORKFLOWS'}`
- **`SERVICE_TICKETS`**: `{'SERVICE_TICKETS', 'SERVICE', 'SERVICE DESK'}`
- **`STAFF_HRMS`**: `{'STAFF_HRMS', 'HRMS', 'HR'}`
- **`ACCOUNTS_GST`**: `{'ACCOUNTS_GST', 'ACCOUNTS', 'ACCOUNTS_FINANCE'}`
- **`TELEPHONY_SOFTPHONE`**: `{'TELEPHONY_SOFTPHONE', 'TELEPHONY', 'SOFTPHONE'}` (Frozen per Rule #6)

### B. SaaS Entitlement Flow Hierarchy
The system uses a 4-tier entitlement cascade:
1. **Tenant Subscription (`PlatformSubscriptionModule`)**: Defines what modules the paying tenant purchased.
2. **Company License (`AssociatedCompany.licensed_modules`)**: JSONB list defining enabled modules for the company.
3. **Staff User Assignment (`StaffEmployee.assigned_modules`)**: JSONB array defining which entitled modules are granted to the specific user. For tenant admins, all licensed modules are automatically available.
4. **Resolved Context (`TenantContext`)**: Computes `effective_modules` = `(Tenant Modules ∩ Company Modules ∩ User Modules)`.
5. **Enforcement**:
   - Web Navigation: `GET /api/v1/saas/tenant-context` -> dynamic sidebar rendering via `staff_sidebar.js`.
   - Mobile Navigation: `SideDrawer.ts` dynamically filters sections using `effective_modules`.
   - API Route Guards: `ctx.require_module('SERVICE_TICKETS')` / `ctx.require_module('STAFF_HRMS')`.

---

## 3. Comprehensive Inventory & SaaS Reusability Matrix

| Function / Domain | Existing Web Page | Existing Mobile Route | Backend Endpoint / Router | DB Models & Tables | Tenant Scoping Field | Reusable for SaaS? | Required Changes for SaaS | Internal Only? |
|---|---|---|---|---|---|---|---|---|
| **Service Tickets Dashboard** | `staff_service_dashboard.html` (`/staff/service-dashboard`) | `ServiceDashboardPage.ts` (`service-dashboard`) | `/api/v1/service/dashboard-stats` | `ServiceTicket` (`service_tickets`) | `company_id` exists | **Yes (100%)** | Bind query to `company_id` | No |
| **Service Queue / List** | `staff_service_queue.html` (`/staff/service-queue`) | `StaffServiceQueuePage.ts` (`staff-service-queue`) | `/api/v1/service/queue` | `ServiceTicket`, `TicketAssignment` | `company_id` exists | **Yes (100%)** | Pass `ctx.company_id` into `TicketService.get_service_queue` | No |
| **Raise Ticket** | `staff_service_raise_ticket.html` (`/staff/service-tickets`) | `RaiseTicketPage.ts` (`raise-ticket`) | `/api/v1/service/create` | `ServiceTicket`, `TicketAttachment` | `company_id` exists | **Yes (100%)** | Auto-populate `company_id` from `RequestContext` | No |
| **Service Reports** | `staff_service_reports.html` (`/staff/service-reports`) | `ServiceReportsPage.ts` (`service-reports`) | `/api/v1/service/reports` | `ServiceTicket` | `company_id` exists | **Yes (100%)** | Scope analytics by `company_id` | No |
| **Service Procurement** | `staff_service_procurement.html` (`/staff/service-procurement`) | `StaffServiceProcurementPage.ts` (`service-procurement`) | `/api/v1/service/procurement` | `ServiceTicketSpareRequest` | `ticket.company_id` | **Yes (Advanced)** | Scope spares to tenant | No |
| **Staff & Users** | `staff_tenant_users.html` (`/staff/tenant-users`) | `StaffTenantUsersPage.ts` (`staff-tenant-users`) | `/api/v1/tenant-users` | `StaffEmployee` (`staff_employees`) | `base_company_id` | **Yes (Canonical)** | Already operational | No |
| **Employee Directory** | `staff_directory.html` (`/staff/directory`) | `ProfilePage.ts` (`profile`) | `/api/v1/staff-directory` | `StaffEmployee` | `base_company_id` | **Yes** | Filter by `base_company_id` | No |
| **My Attendance** | `staff_my_attendance.html` (`/staff/my-attendance`) | `AttendancePage.ts` (`attendance`) | `/api/v1/staff-attendance/*` | `StaffAttendance` (`staff_attendance`) | `employee.base_company_id` | **Yes (100%)** | Scoped via authenticated `staff.id` | No |
| **Team Attendance** | `staff_team_attendance.html` (`/staff/attendance-records`) | `TeamAttendancePage.ts` (`team-attendance`) | `/api/v1/staff-attendance/team` | `StaffAttendance`, `StaffEmployee` | `base_company_id` | **Yes (100%)** | Filter team members by `base_company_id` | No |
| **Attendance Sheet / Register** | `staff_attendance_sheet.html` (`/staff/attendance-sheet`) | `StaffAttendanceSheetPage.ts` (`staff-attendance-sheet`) | `/api/v1/staff/attendance-sheet` | `StaffAttendanceSheet` | `company_id` exists | **Yes (100%)** | Filter by `company_id` | No |
| **Leave Management** | `staff_my_leaves.html` (`/staff/my-leaves`) | `LeavesPage.ts` (`leaves`) | `/api/v1/staff/leaves` | `StaffLeaveRequest` | `employee.base_company_id` | **Yes (100%)** | Employee self-service | No |
| **Leave Approvals** | `staff_leave_approvals.html` (`/staff/leave-approvals`) | `StaffLeaveApprovalsPage.ts` (`staff-leave-approvals`) | `/api/v1/staff/leave-approvals` | `StaffLeaveRequest` | `employee.base_company_id` | **Yes (100%)** | Restrict approver scope to tenant staff | No |
| **My Journeys (Mobility/GPS)** | `staff_my_journeys.html` (`/staff/my-journeys`) | `JourneysPage.ts` (`journeys`) | `/api/v1/staff/journeys/my` | `StaffJourney` (`staff_journeys`) | `company_id` exists | **Yes (100%)** | Self-service field travel tracking | No |
| **Team Journeys / Approvals** | `staff_team_journeys.html` (`/staff/team-journeys`) | `TeamJourneysPage.ts` (`team-journeys`) | `/api/v1/staff/journeys/team` | `StaffJourney` | `company_id` exists | **Yes (100%)** | Filter claims by `company_id` | No |
| **Live Location Tracker** | `staff_team_live_tracker.html` (`/staff/team-live-tracker`) | `StaffTeamLiveTrackerPage.ts` (`staff-team-live-tracker`) | `/api/v1/staff/journeys/live` | `StaffJourneyTrackPoint` | `journey.company_id` | **Yes (100%)** | Filter by tenant staff only | No |
| **Tasks Assigned to Me** | `staff_tasks_assigned_to_me.html` (`/staff/tasks/assigned-to-me`) | `TasksReceivedPage.ts` (`tasks-received`) | `/api/v1/staff/tasks/assigned-to-me` | `StaffTask` (`staff_tasks`) | `primary_assignee_id` | **Yes (100%)** | Scoped via staff user ID | No |
| **Tasks Assigned by Me** | `staff_tasks_assigned_by_me.html` (`/staff/tasks/assigned-by-me`) | `TasksAssignedPage.ts` (`tasks-assigned`) | `/api/v1/staff/tasks/assigned-by-me` | `StaffTask` | `created_by` | **Yes (100%)** | Scoped via staff user ID | No |
| **Day Planner** | `staff_day_planner.html` (`/staff/tasks/day-planner`) | `TasksPage.ts` (`tasks`) | `/api/v1/staff/day-plans` | `StaffDayPlan`, `StaffDayPlanItem` | `employee.base_company_id` | **Yes (100%)** | Filter plans by `base_company_id` | No |
| **Task Tracker** | `staff_task_tracker.html` (`/staff/tasks/task-tracker`) | `StaffTaskTrackerPage.ts` (`staff-task-tracker`) | `/api/v1/staff/tasks/tracker` | `StaffTask` | `employee.base_company_id` | **Yes (100%)** | Filter all tasks by `base_company_id` | No |
| **My KRAs** | `staff_my_kras.html` (`/staff/my-kras`) | `KrasPage.ts` (`kras`) | `/api/v1/staff/kra/my-kras` | `StaffKRAAssignment`, `StaffKRADailyInstance` | `employee.base_company_id` | **Yes (100%)** | Scoped via staff user ID | No |
| **KRA Templates** | `staff_kra_templates.html` (`/staff/kra-templates`) | `StaffKraTemplatesPage.ts` (`staff-kra-templates`) | `/api/v1/staff/kra/templates` | `StaffKRATemplate` | `company_id` (Add nullable FK) | **Yes (100%)** | Scope custom templates by company | No |
| **KRA Tracking Sheet** | `staff_kra_tracking_sheet.html` (`/staff/kra-tracking-sheet`) | `StaffKraTrackingPage.ts` (`staff-kra-tracking`) | `/api/v1/staff/kra/tracking-sheet` | `StaffKRADailyInstance` | `employee.base_company_id` | **Yes (100%)** | Scope reporting by `base_company_id` | No |
| **Timesheet (My & Team)** | `staff_my_timesheet.html` (`/staff/timesheet`) | `TimesheetPage.ts` (`timesheet`) | `/api/v1/staff/timesheet/*` | `StaffTimesheetEntry` | `employee.base_company_id` | **Yes (100%)** | Filter team approvals by `base_company_id` | No |
| **Corporate Master HRMS** | `staff_users.html`, `staff_hr_payroll.html` | None | `/api/v1/platform/internal-hr` | Platform tables | Internal Multi-Company | **No** | Keep internal to platform admins | **YES** |
| **MNR / VGK Ecosystem** | `staff_vgk_members.html`, `mnr_leads.html` | `staff-vgk-members` | `/api/v1/vgk/*`, `/api/v1/mnr/*` | MLM, binary trees | Internal | **No** | Hide completely from SaaS tenants | **YES** |

---

## 4. Deep-Dive Domain Architecture

### A. SERVICE MODULE (`SERVICE_TICKETS`)
1. **Existing Foundation**:
   - Primary model: `ServiceTicket` (`models/ticket.py`).
   - Notice: `service_tickets` table **already contains a `company_id` column** with existing records (Company 4: 226 rows, Company 2: 12 rows, Company 3: 1 row).
   - Lifecycle: `OPEN` -> `ASSIGNED` -> `DIAGNOSED` -> `SPARES_REQUESTED` -> `IN_PROGRESS` -> `RESOLVED` -> `CLOSED`.
2. **SaaS User Experience**:
   - **Ticket Queue**: Filtered strictly by `company_id = ctx.company.id`.
   - **Raise Ticket**: Allows tenant staff to create customer service/complaint tickets with asset details, priority, and assign to internal tenant technicians.
   - **Service Dashboard**: Real-time SLA counters, resolution times, pending diagnostics.
   - **Service Reports**: Downloadable reports and performance tracking.
3. **Tenant Scoping Gap**:
   - In `backend/app/services/ticket_service.py` (`get_service_queue`), the query filters by `staff_id` and status, but neglects `company_id`. For SaaS tenants, it must filter by `ServiceTicket.company_id == ctx.company.id`.

### B. HRMS MODULE (`STAFF_HRMS`)
The HRMS module encapsulates 6 operational domains:

#### 1. Employee Management & Staff Identity
- **Single Identity Standard**: A tenant staff user and an HRMS employee are **the exact same entity** (`StaffEmployee`).
- The canonical SaaS Staff & Users interface (`/staff/tenant-users` and mobile `StaffTenantUsersPage.ts`) handles employee creation, role assignment, reporting manager linkage, and module entitlements.
- Reusable Employee Directory (`/staff/directory`) provides an address book for the tenant's workforce.

#### 2. Attendance & Leaves
- **Check-in / Check-out**: Geo-tagged and selfie-enabled check-in via mobile (`AttendancePage.ts`) and web (`/staff/my-attendance`).
- **Team Attendance**: Managers review check-in/out stamps, working hours, and field statuses.
- **Attendance Sheet**: Monthly master register calculating total working days, present days, and payable days (`/staff/attendance-sheet`).
- **Leaves**: Leave applications (`/staff/my-leaves`) and multi-level manager approvals (`/staff/leave-approvals`).

#### 3. Journeys (Field Mobility, Tracking & Travel Reimbursement)
- **True Business Definition**: **Field Mobility & Travel Allowance**.
- When sales reps or service technicians travel for customer visits or field tasks, they start a Journey.
- Captures starting odometer reading + photo, GPS track points throughout the day, customer check-ins, ending odometer reading + photo, and calculates distance (km).
- Computes travel allowance based on tenant rate-per-km.
- Manager dashboard (`/staff/team-journeys`) allows reviewing GPS breadcrumbs, photos, and approving/rejecting expense claims.
- Already has native Capacitor Geolocation integration via `gps.service.ts`!

#### 4. Task Management & Day Planner
- **Day Planner (`/staff/tasks/day-planner`)**: Daily morning routine where staff plan their key priorities and customer calls.
- **Task Delegation (`/staff/tasks/assigned-to-me` & `/staff/tasks/assigned-by-me`)**: Create tasks, set priorities, assign to peers, and track progress.
- **Task Tracker (`/staff/tasks/task-tracker`)**: Kanban and list view for managers.

#### 5. KRA (Key Result Areas)
- **KRA Templates (`/staff/kra-templates`)**: Define weighted performance metrics per designation.
- **Daily KRA Instance (`/staff/my-kras`)**: Employees record daily scores against targets.
- **Tracking Sheet (`/staff/kra-tracking-sheet`)**: Manager scorecards.

#### 6. Timesheet
- **Daily Timesheet (`/staff/timesheet`)**: Log hours worked against Leads, Tasks, KRAs, or Journeys.
- **Manager Approval**: Tabular approval interface for submitted hours.

---

## 5. Unified Platform Parity: Web, /mobile, Android, iOS

Per **VGK4U Rule #5**, all business capabilities must achieve parity across all delivery forms:
1. **Web**: Modular sidebars rendered via `staff_sidebar.js` and `saas_tenant_resolver.py`.
2. **Mobile Web (`/mobile`)**: Single-page application built with TypeScript and Vanilla JS.
3. **Android**: Capacitor container wrapping `/mobile` assets with native Geolocation & Foreground Service.
4. **iOS**: Capacitor container wrapping `/mobile` assets with CoreLocation background permissions.

### Mobile Navigation Alignment
In `mobile/src/components/SideDrawer.ts`, sections `HR`, `TASK_MANAGEMENT`, `KRA_MANAGEMENT`, `FIELD_LOCATION`, and `SERVICE_SIDEBAR` were previously in `saasRestricted`. 
When `ctx.has_module('SERVICE_TICKETS')` and `ctx.has_module('STAFF_HRMS')` are active, these sections will be dynamically included under clean SaaS titles:
- `SERVICE DESK`: Service Queue, Raise Ticket, Service Dashboard, Service Reports.
- `HRMS`: Attendance, Leaves, Field Journeys, Tasks, KRAs, Timesheet.

---

## 6. Tenant Scoping & Data Isolation Plan

To guarantee zero cross-tenant data leakage:
1. **Service**:
   - `ServiceTicket.company_id` is mandatory.
   - All queue, stats, and reports queries will enforce `.filter(ServiceTicket.company_id == tenant_company_id)`.
2. **Staff / HRMS**:
   - `StaffEmployee.base_company_id` isolates employees.
   - `StaffAttendance`: Filter by `StaffEmployee.base_company_id == tenant_company_id`.
   - `StaffJourney`: Has explicit `company_id`. Enforce `.filter(StaffJourney.company_id == tenant_company_id)`.
   - `StaffTask`: Filter by `primary_assignee.base_company_id == tenant_company_id`.
   - `StaffTimesheetEntry`: Filter by `StaffEmployee.base_company_id == tenant_company_id`.
3. **KRA Templates**:
   - Add nullable `company_id` to `staff_kra_templates` so tenants can create custom role templates without overwriting global defaults.

---

## 7. Recommended Implementation Phases

```
Phase 1: SaaS Resolver & Module Registry Update (SERVICE_TICKETS & STAFF_HRMS)
Phase 2: Service Desk Backend Tenant Scoping (TicketService & endpoints)
Phase 3: Service Desk Web & Mobile Navigation Activation
Phase 4: Attendance & Leaves Tenant Scoping & Activation
Phase 5: Journeys (Field Mobility & GPS) Tenant Scoping & Activation
Phase 6: Tasks & Day Planner Tenant Scoping & Activation
Phase 7: KRA Management Tenant Scoping & Activation
Phase 8: Timesheet Management Tenant Scoping & Activation
Phase 9: Mobile SideDrawer & Route Guard Synchronization
Phase 10: Platform Parity Sync (npm build -> capacitor sync android/ios) & Final Validation
```

---
*End of Architectural Discovery Report.*
