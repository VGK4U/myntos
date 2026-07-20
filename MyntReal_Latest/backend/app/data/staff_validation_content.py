"""
DC Protocol: Staff System Validation Content
System enforcement validation data for all staff pages.
Maps menu_code -> validation rules, risk levels, field enforcement, workflow checks.
"""

VALIDATION_SECTION_DESCRIPTIONS = {
    "progress": {
        "description": "Validate real-time progress aggregation accuracy, data source sync, and cross-module time calculations.",
        "icon": "fas fa-chart-line",
        "risk_level": "medium"
    },
    "PROGRESS": {
        "description": "Validate real-time progress aggregation accuracy, data source sync, and cross-module time calculations.",
        "icon": "fas fa-chart-line",
        "risk_level": "medium"
    },
    "staff-dashboard": {
        "description": "Validate profile data integrity, KYC document handling, photo upload security, and role-based field visibility.",
        "icon": "fas fa-tachometer-alt",
        "risk_level": "high"
    },
    "STAFF_DASHBOARD": {
        "description": "Validate profile data integrity, KYC document handling, photo upload security, and role-based field visibility.",
        "icon": "fas fa-tachometer-alt",
        "risk_level": "high"
    },
    "attendance": {
        "description": "Validate clock in/out logic, leave approval chain, attendance exception handling, and HR override permissions.",
        "icon": "fas fa-clock",
        "risk_level": "high"
    },
    "crm": {
        "description": "Validate lead assignment logic, pipeline stage transitions, handler RBAC, and cross-selling data isolation.",
        "icon": "fas fa-handshake",
        "risk_level": "medium"
    },
    "task-management": {
        "description": "Validate task assignment rules, status transitions, time tracking accuracy, and day plan carry-forward logic.",
        "icon": "fas fa-tasks",
        "risk_level": "medium"
    },
    "kra-management": {
        "description": "Validate KRA template enforcement, completion calculation, approval chain, and time sync with timesheet.",
        "icon": "fas fa-bullseye",
        "risk_level": "medium"
    },
    "timesheet": {
        "description": "Validate auto-sync from 6 source systems, approved_minutes calculation, manager approval workflow, and duplicate entry prevention.",
        "icon": "fas fa-calendar-alt",
        "risk_level": "high"
    },
    "journey-tracking": {
        "description": "Validate GPS accuracy, route recording integrity, distance calculation, transport mode validation, and WVV Protocol compliance.",
        "icon": "fas fa-route",
        "risk_level": "high"
    },
    "location-tracking": {
        "description": "Validate real-time location accuracy, history recording, privacy controls, and data retention policy.",
        "icon": "fas fa-map-marker-alt",
        "risk_level": "high"
    },
    "reimbursement": {
        "description": "Validate expense claim validation, receipt upload security, approval chain, amount limits, and SFMS sync.",
        "icon": "fas fa-receipt",
        "risk_level": "high"
    },
    "service-tickets": {
        "description": "Validate ticket lifecycle, assignment rules, SLA tracking, escalation triggers, and resolution workflows.",
        "icon": "fas fa-headset",
        "risk_level": "medium"
    },
    "sfms": {
        "description": "Validate multi-company data segregation, ledger accuracy, journal entry integrity, and balance sheet calculations.",
        "icon": "fas fa-calculator",
        "risk_level": "critical"
    },
    "inventory": {
        "description": "Validate stock level tracking, purchase/sales invoice processing, HSN/SAC mapping, and periodic audit enforcement.",
        "icon": "fas fa-boxes",
        "risk_level": "high"
    },
    "payroll": {
        "description": "Validate salary calculation, deduction rules, ONROLE/OFFROLE logic, SFMS integration, and statutory compliance.",
        "icon": "fas fa-money-bill-wave",
        "risk_level": "critical"
    },
    "official-partners": {
        "description": "Validate B2B order management, partner onboarding, fulfillment tracking, and payment reconciliation.",
        "icon": "fas fa-handshake",
        "risk_level": "medium"
    },
    "nda-management": {
        "description": "Validate NDA enforcement middleware, version control, acceptance tracking, and access restriction logic.",
        "icon": "fas fa-file-contract",
        "risk_level": "high"
    },
    "configuration": {
        "description": "Validate system settings persistence, menu access cascade logic, zero-default policy enforcement, and audit logging.",
        "icon": "fas fa-cogs",
        "risk_level": "critical"
    },
    "zynova": {
        "description": "Validate VGK4U dual-segment data segregation, real estate listing integrity, and insurance policy management.",
        "icon": "fas fa-layer-group",
        "risk_level": "medium"
    },
    "real-dreams": {
        "description": "Validate property listing data, CRM lead management, company-wise segregation, and partner access controls.",
        "icon": "fas fa-building",
        "risk_level": "medium"
    },
    "zy-member-earnings": {
        "description": "Validate member earning calculations, referral commission accuracy, and wallet credit integrity.",
        "icon": "fas fa-wallet",
        "risk_level": "high"
    },
}

VALIDATION_SECTION_ORDER = [
    "progress", "PROGRESS", "STAFF_DASHBOARD", "staff-dashboard", "attendance", "crm",
    "task-management", "kra-management", "timesheet",
    "journey-tracking", "location-tracking", "reimbursement",
    "service-tickets", "sfms", "inventory", "payroll",
    "official-partners", "nda-management", "configuration",
    "zynova", "real-dreams", "zy-member-earnings"
]

RISK_DEFINITIONS = {
    "critical": {"label": "CRITICAL", "color": "#dc2626", "description": "System failure, data corruption, or financial loss risk"},
    "high": {"label": "HIGH", "color": "#f59e0b", "description": "Significant workflow disruption or data integrity issue"},
    "medium": {"label": "MEDIUM", "color": "#3b82f6", "description": "Moderate impact on operations or user experience"},
    "low": {"label": "LOW", "color": "#059669", "description": "Minor cosmetic or non-blocking issue"}
}

GLOBAL_ENFORCEMENT_RULES = {
    "backend_revalidation": {
        "title": "Backend Must Re-Validate All Frontend Rules",
        "status": "MANDATORY",
        "checks": [
            "All Pydantic models use explicit Body(...) for POST/PUT endpoints",
            "Field type validation enforced at SQLAlchemy column level",
            "Required fields validated in Pydantic schema, not just frontend",
            "Enum values validated server-side against allowed lists",
            "Date format validation (ISO 8601) enforced in deserializer",
            "Numeric range limits enforced in Pydantic validators",
            "String length limits enforced via Column(String(N)) constraints"
        ]
    },
    "api_role_enforcement": {
        "title": "API-Level Role Enforcement",
        "status": "MANDATORY",
        "checks": [
            "JWT token validated on every protected endpoint",
            "Company ID extracted from token and enforced in queries (DC Protocol)",
            "Staff role checked against MENU_MASTER before allowing access",
            "Data ownership verified - staff can only access their company's data",
            "Supreme Admin actions require secondary verification",
            "Partner endpoints isolated from staff endpoints"
        ]
    },
    "team_view_data_visibility": {
        "title": "Team View Data Visibility Enforcement",
        "status": "MANDATORY",
        "checks": [
            "Team display views show only direct and indirect subordinates — manager's own record is excluded from the team section",
            "Manager's own data always appears in their personal/My section at the top, never duplicated in the team grid below",
            "Department filter correctly applied across all team display views",
            "Enforcement applied consistently across: Day Plans, Timesheet, KRA, Time Tracker, Attendance Sheet, Tasks, Progress, CRM, Journeys, Field Work"
        ]
    },
    "data_tampering_prevention": {
        "title": "Data Tampering Risk Mitigation",
        "status": "MANDATORY",
        "checks": [
            "SQL injection prevention via SQLAlchemy ORM parameterized queries",
            "Path traversal protection on all file upload endpoints",
            "ID manipulation blocked - user cannot change other users' data by modifying IDs",
            "Bulk operations require explicit authorization check per record",
            "File upload type/size validation enforced server-side",
            "TrustedHostMiddleware enabled for request origin validation"
        ]
    },
    "transaction_integrity": {
        "title": "Transaction & Race Condition Handling",
        "status": "MANDATORY",
        "checks": [
            "Database transactions used for multi-table operations",
            "Rollback on any failure within transaction scope",
            "Optimistic locking for concurrent update scenarios",
            "Double-submit prevention via idempotency checks",
            "Wallet operations use row-level locking to prevent race conditions",
            "Scheduler jobs use advisory locks to prevent duplicate execution"
        ]
    },
    "data_integrity": {
        "title": "Cross-Module Data Integrity",
        "status": "MANDATORY",
        "checks": [
            "Foreign key constraints enforced at database level",
            "Soft delete policy: is_active flag used, data retained for audit",
            "Cascade delete rules defined for dependent records",
            "Orphan record detection via periodic cleanup jobs",
            "Status desync prevention: single source of truth per status field",
            "Dual database consistency validated via audit framework"
        ]
    },
    "mobile_web_parity": {
        "title": "Mobile vs Web Parity Enforcement",
        "status": "MANDATORY",
        "checks": [
            "Same API endpoints used by both web and mobile (Capacitor)",
            "All form validations present in both platforms",
            "All buttons and actions available in both platforms",
            "Status flows identical across platforms",
            "Role-based access identical across platforms",
            "Any platform-specific difference = DEFECT to be filed"
        ]
    }
}

WORKFLOW_VALIDATIONS = {
    "attendance_workflow": {
        "title": "Attendance & Leave Workflow",
        "module": "attendance",
        "states": ["Absent", "Present", "Half Day", "On Leave", "Week Off", "Holiday", "Comp Off"],
        "transitions": [
            {"from": "Absent", "to": "Present", "who": "Employee (clock-in)", "condition": "Within allowed time window"},
            {"from": "Absent", "to": "On Leave", "who": "Employee (leave request)", "condition": "Leave balance available"},
            {"from": "Absent", "to": "Half Day", "who": "HR/Manager", "condition": "Manual override with reason"},
            {"from": "Present", "to": "Half Day", "who": "System/HR", "condition": "Clock hours < threshold"},
        ],
        "invalid_transitions": [
            {"from": "On Leave", "to": "Present", "reason": "Cannot clock in while on approved leave"},
            {"from": "Holiday", "to": "Absent", "reason": "System holiday cannot be marked absent"},
        ],
        "lock_conditions": ["Past dates locked after 48 hours", "Payroll-processed months fully locked"],
        "escalation": "Unmarked attendance auto-escalates to manager after 24 hours",
        "audit_required": True,
        "risk_level": "high"
    },
    "leave_approval_workflow": {
        "title": "Leave Approval Chain",
        "module": "attendance",
        "states": ["Draft", "Pending", "Manager Approved", "HR Approved", "Rejected", "Cancelled"],
        "transitions": [
            {"from": "Draft", "to": "Pending", "who": "Employee", "condition": "All required fields filled"},
            {"from": "Pending", "to": "Manager Approved", "who": "Reporting Manager", "condition": "Manager has approval rights"},
            {"from": "Manager Approved", "to": "HR Approved", "who": "HR Admin", "condition": "Leave balance verified"},
            {"from": "Pending", "to": "Rejected", "who": "Manager/HR", "condition": "Rejection reason mandatory"},
            {"from": "Pending", "to": "Cancelled", "who": "Employee", "condition": "Only before approval"},
        ],
        "invalid_transitions": [
            {"from": "HR Approved", "to": "Cancelled", "reason": "Cannot cancel after HR approval without HR action"},
            {"from": "Rejected", "to": "Manager Approved", "reason": "Must re-submit new request"},
        ],
        "lock_conditions": ["Cannot apply for past dates", "Cannot apply during payroll processing"],
        "escalation": "Pending requests auto-escalate after 48 hours",
        "audit_required": True,
        "risk_level": "high"
    },
    "task_workflow": {
        "title": "Task Lifecycle",
        "module": "task-management",
        "states": ["Created", "Assigned", "In Progress", "Completed", "Verified", "Reopened"],
        "transitions": [
            {"from": "Created", "to": "Assigned", "who": "Manager/Creator", "condition": "Assignee selected"},
            {"from": "Assigned", "to": "In Progress", "who": "Assignee", "condition": "Task accepted"},
            {"from": "In Progress", "to": "Completed", "who": "Assignee", "condition": "Completion notes added"},
            {"from": "Completed", "to": "Verified", "who": "Manager", "condition": "Work output reviewed"},
            {"from": "Verified", "to": "Reopened", "who": "Manager", "condition": "Quality issues found"},
            {"from": "Reopened", "to": "In Progress", "who": "Assignee", "condition": "Acknowledged reopen"},
        ],
        "invalid_transitions": [
            {"from": "Created", "to": "Completed", "reason": "Cannot skip assignment and progress stages"},
            {"from": "Verified", "to": "Created", "reason": "Cannot revert to initial state"},
        ],
        "lock_conditions": ["Verified tasks locked after 7 days"],
        "escalation": "Overdue tasks flagged to manager daily",
        "audit_required": True,
        "risk_level": "medium"
    },
    "kra_workflow": {
        "title": "KRA Review Lifecycle",
        "module": "kra-management",
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Revision Required"],
        "transitions": [
            {"from": "Draft", "to": "Submitted", "who": "Employee", "condition": "All KRA items filled"},
            {"from": "Submitted", "to": "Under Review", "who": "System", "condition": "Auto-transition on submit"},
            {"from": "Under Review", "to": "Approved", "who": "Manager", "condition": "Review completed"},
            {"from": "Under Review", "to": "Rejected", "who": "Manager", "condition": "Rejection reason required"},
            {"from": "Under Review", "to": "Revision Required", "who": "Manager", "condition": "Specific items flagged"},
            {"from": "Revision Required", "to": "Submitted", "who": "Employee", "condition": "Flagged items updated"},
        ],
        "invalid_transitions": [
            {"from": "Approved", "to": "Draft", "reason": "Cannot revert approved KRA to draft"},
        ],
        "lock_conditions": ["KRA period locks after review deadline"],
        "escalation": "Unreviewed KRAs escalate to skip-level after 5 days",
        "audit_required": True,
        "risk_level": "medium"
    },
    "timesheet_workflow": {
        "title": "Timesheet Approval",
        "module": "timesheet",
        "states": ["Auto-Synced", "Submitted", "Manager Approved", "Rejected", "Locked"],
        "transitions": [
            {"from": "Auto-Synced", "to": "Submitted", "who": "Employee", "condition": "Review and confirm entries"},
            {"from": "Submitted", "to": "Manager Approved", "who": "Manager", "condition": "Time entries verified"},
            {"from": "Submitted", "to": "Rejected", "who": "Manager", "condition": "Discrepancy found, reason required"},
            {"from": "Manager Approved", "to": "Locked", "who": "System", "condition": "Payroll processing begins"},
        ],
        "invalid_transitions": [
            {"from": "Locked", "to": "Submitted", "reason": "Cannot modify after payroll lock"},
            {"from": "Manager Approved", "to": "Auto-Synced", "reason": "Cannot revert approved timesheet"},
        ],
        "lock_conditions": ["Locked when payroll processes", "Past month entries lock on 5th of next month"],
        "escalation": "Unapproved timesheets flagged to HR weekly",
        "audit_required": True,
        "risk_level": "high"
    },
    "journey_workflow": {
        "title": "Journey Tracking Lifecycle",
        "module": "journey-tracking",
        "states": ["Started", "In Transit", "Checkpoint", "Completed", "Submitted", "Approved", "Rejected"],
        "transitions": [
            {"from": "Started", "to": "In Transit", "who": "Employee", "condition": "GPS enabled, transport selected"},
            {"from": "In Transit", "to": "Checkpoint", "who": "Employee", "condition": "Reached destination, proof uploaded"},
            {"from": "Checkpoint", "to": "In Transit", "who": "Employee", "condition": "Continuing to next stop"},
            {"from": "In Transit", "to": "Completed", "who": "Employee", "condition": "Journey ended, returned to base"},
            {"from": "Completed", "to": "Submitted", "who": "Employee", "condition": "Journey summary reviewed"},
            {"from": "Submitted", "to": "Approved", "who": "Manager", "condition": "Route and distance verified"},
            {"from": "Submitted", "to": "Rejected", "who": "Manager", "condition": "Discrepancy found"},
        ],
        "invalid_transitions": [
            {"from": "Approved", "to": "Started", "reason": "Cannot restart approved journey"},
            {"from": "Started", "to": "Approved", "reason": "Cannot skip transit and completion"},
        ],
        "lock_conditions": ["GPS must be active during entire journey", "WVV Protocol compliance required"],
        "escalation": "Incomplete journeys flagged after 12 hours",
        "audit_required": True,
        "risk_level": "high"
    },
    "service_ticket_workflow": {
        "title": "Service Ticket Lifecycle",
        "module": "service-tickets",
        "states": ["Open", "Assigned", "In Progress", "Waiting on Customer", "Resolved", "Closed", "Reopened"],
        "transitions": [
            {"from": "Open", "to": "Assigned", "who": "Manager/System", "condition": "Technician assigned"},
            {"from": "Assigned", "to": "In Progress", "who": "Technician", "condition": "Work started"},
            {"from": "In Progress", "to": "Waiting on Customer", "who": "Technician", "condition": "Customer input needed"},
            {"from": "Waiting on Customer", "to": "In Progress", "who": "Technician", "condition": "Customer responded"},
            {"from": "In Progress", "to": "Resolved", "who": "Technician", "condition": "Resolution notes added"},
            {"from": "Resolved", "to": "Closed", "who": "Customer/System", "condition": "Customer confirms or 48h auto-close"},
            {"from": "Closed", "to": "Reopened", "who": "Customer", "condition": "Within 7 days of closure"},
        ],
        "invalid_transitions": [
            {"from": "Open", "to": "Closed", "reason": "Cannot close without resolution"},
            {"from": "Closed", "to": "Open", "reason": "Must reopen, not reset to open"},
        ],
        "lock_conditions": ["Closed tickets lock after 30 days"],
        "escalation": "Unresolved tickets escalate by priority tier",
        "audit_required": True,
        "risk_level": "medium"
    },
    "reimbursement_workflow": {
        "title": "Reimbursement Claim Processing",
        "module": "reimbursement",
        "states": ["Draft", "Submitted", "Manager Approved", "Finance Approved", "Paid", "Rejected"],
        "transitions": [
            {"from": "Draft", "to": "Submitted", "who": "Employee", "condition": "Receipt uploaded, amount entered"},
            {"from": "Submitted", "to": "Manager Approved", "who": "Manager", "condition": "Expense justified"},
            {"from": "Manager Approved", "to": "Finance Approved", "who": "Finance", "condition": "Budget available, policy compliant"},
            {"from": "Finance Approved", "to": "Paid", "who": "System", "condition": "Payment processed via SFMS"},
            {"from": "Submitted", "to": "Rejected", "who": "Manager/Finance", "condition": "Rejection reason mandatory"},
        ],
        "invalid_transitions": [
            {"from": "Paid", "to": "Draft", "reason": "Cannot revert paid reimbursement"},
            {"from": "Submitted", "to": "Paid", "reason": "Cannot skip approval chain"},
        ],
        "lock_conditions": ["Paid claims locked permanently", "Claims older than 90 days auto-expire"],
        "escalation": "Pending claims escalate after 5 business days",
        "audit_required": True,
        "risk_level": "high"
    },
    "nda_workflow": {
        "title": "NDA Acceptance & Enforcement",
        "module": "nda-management",
        "states": ["Not Presented", "Presented", "Accepted", "Expired", "Revoked"],
        "transitions": [
            {"from": "Not Presented", "to": "Presented", "who": "System", "condition": "Employee login triggers NDA check"},
            {"from": "Presented", "to": "Accepted", "who": "Employee", "condition": "Digital signature provided"},
            {"from": "Accepted", "to": "Expired", "who": "System", "condition": "NDA validity period ends"},
            {"from": "Expired", "to": "Presented", "who": "System", "condition": "New version auto-presented on login"},
            {"from": "Accepted", "to": "Revoked", "who": "HR Admin", "condition": "Employee offboarding"},
        ],
        "invalid_transitions": [
            {"from": "Presented", "to": "Not Presented", "reason": "Cannot dismiss NDA without acceptance"},
        ],
        "lock_conditions": ["NDA middleware blocks all pages until accepted", "Cannot access system with expired NDA"],
        "escalation": "Unaccepted NDAs block system access entirely",
        "audit_required": True,
        "risk_level": "critical"
    },
    "payroll_workflow": {
        "title": "Payroll Processing Pipeline",
        "module": "payroll",
        "states": ["Draft", "Attendance Locked", "Calculated", "Manager Reviewed", "Finance Approved", "Processed", "Paid"],
        "transitions": [
            {"from": "Draft", "to": "Attendance Locked", "who": "HR", "condition": "All attendance finalized for month"},
            {"from": "Attendance Locked", "to": "Calculated", "who": "System", "condition": "Salary engine runs calculations"},
            {"from": "Calculated", "to": "Manager Reviewed", "who": "Manager", "condition": "Team payroll reviewed"},
            {"from": "Manager Reviewed", "to": "Finance Approved", "who": "Finance", "condition": "Budget verified"},
            {"from": "Finance Approved", "to": "Processed", "who": "System", "condition": "Payment file generated"},
            {"from": "Processed", "to": "Paid", "who": "Finance", "condition": "Bank confirms payment"},
        ],
        "invalid_transitions": [
            {"from": "Paid", "to": "Draft", "reason": "Cannot reverse paid payroll"},
            {"from": "Calculated", "to": "Draft", "reason": "Must re-run calculation, not revert"},
        ],
        "lock_conditions": ["Paid payroll permanently locked", "Attendance locked after payroll initiation"],
        "escalation": "Unpaid payroll after 5th escalates to CEO",
        "audit_required": True,
        "risk_level": "critical"
    },
}

STAFF_VALIDATION_CONTENT = {
    "staff_dashboard": {
        "risk_level": "high",
        "ui_components": ["Profile Card", "KYC Status Panel", "Team Overview", "Quick Actions", "Notifications"],
        "field_rules": [
            {"field": "Employee Name", "type": "string", "required": True, "max_length": 128, "editable_by": "HR only", "validation": "No special characters except space and period"},
            {"field": "Phone Number", "type": "string", "required": True, "format": "10-digit Indian mobile", "editable_by": "HR only", "validation": "Regex: ^[6-9]\\d{9}$"},
            {"field": "Email", "type": "string", "required": True, "format": "Valid email", "editable_by": "HR only", "validation": "RFC 5322 compliant"},
            {"field": "Date of Birth", "type": "date", "required": True, "format": "YYYY-MM-DD", "editable_by": "HR only", "validation": "Must be 18+ years, not future date"},
            {"field": "Profile Photo", "type": "file", "required": False, "format": "JPEG/PNG, max 5MB", "editable_by": "Self + HR", "validation": "Server-side type check, path traversal blocked"},
        ],
        "button_validations": [
            {"button": "Update Profile", "api": "PUT /api/v1/staff/profile", "requires": "Valid form data", "role": "Self (limited fields) + HR (all fields)", "double_click": "Disabled after first click"},
            {"button": "Upload Document", "api": "POST /api/v1/staff/documents/upload", "requires": "File selected, type valid", "role": "Self + HR", "double_click": "Upload progress indicator"},
        ],
        "backend_checks": [
            "Profile updates validate field-level edit permissions per role",
            "Photo uploads checked for file type, size, and path traversal",
            "Company ID from JWT enforced on all queries",
            "Cannot view other company's employee data"
        ],
        "mobile_parity": [
            {"check": "Profile photo upload", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "KYC document upload", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Edit personal info", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "high", "description": "Photo upload without server-side type validation could allow malicious files"},
            {"level": "medium", "description": "Profile field edit permissions must be backend-enforced, not frontend-only"},
            {"level": "medium", "description": "KYC document URLs must not be guessable or enumerable"},
        ]
    },

    "staff_attendance_marking": {
        "risk_level": "high",
        "ui_components": ["Clock In/Out Button", "Selfie Capture", "Location Stamp", "Attendance Calendar", "Status Legend"],
        "field_rules": [
            {"field": "Clock In Time", "type": "datetime", "required": True, "format": "ISO 8601", "editable_by": "System only", "validation": "Server timestamp, not client"},
            {"field": "Selfie", "type": "file", "required": True, "format": "JPEG, max 2MB", "editable_by": "Employee", "validation": "Captured in real-time, no gallery upload"},
            {"field": "Location", "type": "coordinates", "required": True, "format": "lat,lng", "editable_by": "System only", "validation": "GPS accuracy check, mock location detection"},
        ],
        "button_validations": [
            {"button": "Clock In", "api": "POST /api/v1/staff/attendance/clock-in", "requires": "Selfie captured, GPS active", "role": "Employee", "double_click": "Disabled for 60 seconds after click"},
            {"button": "Clock Out", "api": "POST /api/v1/staff/attendance/clock-out", "requires": "Currently clocked in", "role": "Employee", "double_click": "Disabled for 60 seconds after click"},
        ],
        "backend_checks": [
            "Server-side timestamp used, client time ignored",
            "Cannot clock in twice without clocking out",
            "GPS coordinates validated for reasonableness",
            "Selfie file validated for recency metadata",
            "Attendance modification requires HR override with audit log"
        ],
        "mobile_parity": [
            {"check": "Clock In with selfie", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "GPS capture", "web": "Limited", "mobile": "Full GPS", "status": "VERIFY"},
            {"check": "Mock location detection", "web": "N/A", "mobile": "Required", "status": "VERIFY"},
        ],
        "risks": [
            {"level": "critical", "description": "Client-side timestamp manipulation could allow false attendance entries"},
            {"level": "high", "description": "GPS spoofing on mobile could fake location-based attendance"},
            {"level": "high", "description": "Gallery photo upload instead of live selfie defeats identity verification"},
            {"level": "medium", "description": "Multiple devices could allow simultaneous clock-in attempts"},
        ]
    },

    "staff_leave_request": {
        "risk_level": "high",
        "ui_components": ["Leave Form", "Balance Display", "Calendar View", "Approval Status", "History Table"],
        "field_rules": [
            {"field": "Leave Type", "type": "enum", "required": True, "format": "CL/SL/EL/LWP/Comp Off", "editable_by": "Employee", "validation": "Must match allowed leave types for employee category"},
            {"field": "From Date", "type": "date", "required": True, "format": "YYYY-MM-DD", "editable_by": "Employee", "validation": "Cannot be past date, cannot exceed 30 days"},
            {"field": "To Date", "type": "date", "required": True, "format": "YYYY-MM-DD", "editable_by": "Employee", "validation": "Must be >= From Date"},
            {"field": "Reason", "type": "text", "required": True, "format": "Min 10 chars", "editable_by": "Employee", "validation": "Non-empty, meaningful text"},
            {"field": "Half Day", "type": "boolean", "required": False, "format": "First Half/Second Half", "editable_by": "Employee", "validation": "Only for single-day leaves"},
        ],
        "button_validations": [
            {"button": "Submit Leave", "api": "POST /api/v1/staff/leaves", "requires": "All fields valid, balance available", "role": "Employee", "double_click": "Disabled after submit"},
            {"button": "Approve", "api": "PUT /api/v1/staff/leaves/{id}/approve", "requires": "Pending status, manager role", "role": "Manager/HR", "double_click": "Confirmation modal"},
            {"button": "Reject", "api": "PUT /api/v1/staff/leaves/{id}/reject", "requires": "Rejection reason filled", "role": "Manager/HR", "double_click": "Confirmation modal"},
        ],
        "backend_checks": [
            "Leave balance validated server-side before approval",
            "Three-tier chain: Employee -> Manager -> HR enforced",
            "Cannot approve own leave request",
            "Overlapping leave detection before submission",
            "Attendance integration: approved leave auto-marks attendance"
        ],
        "mobile_parity": [
            {"check": "Submit leave", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "View balance", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Approve/Reject", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "high", "description": "Approving leave without balance check could create negative balances"},
            {"level": "high", "description": "Self-approval bypass via direct API call must be blocked"},
            {"level": "medium", "description": "Overlapping leave requests across different leave types"},
        ]
    },

    "staff_my_timesheet": {
        "risk_level": "high",
        "ui_components": ["Today Tab", "My Timesheet Tab", "Team Approval Tab", "Time Entry Cards", "Source System Tags"],
        "field_rules": [
            {"field": "Activity Source", "type": "enum", "required": True, "format": "KRA/Task/DayPlan/Journey/Lead/Ticket", "editable_by": "System (auto-sync)", "validation": "Must match valid source system"},
            {"field": "Minutes", "type": "integer", "required": True, "format": "0-1440", "editable_by": "System/Employee", "validation": "Cannot exceed 24 hours per day total"},
            {"field": "Approved Minutes", "type": "integer", "required": False, "format": "0-1440", "editable_by": "Manager", "validation": "Cannot exceed submitted minutes"},
            {"field": "Date", "type": "date", "required": True, "format": "YYYY-MM-DD", "editable_by": "System", "validation": "Auto-set from source activity date"},
        ],
        "button_validations": [
            {"button": "Submit Timesheet", "api": "POST /api/v1/staff/timesheet/submit", "requires": "All entries reviewed", "role": "Employee", "double_click": "Disabled after submit"},
            {"button": "Approve", "api": "PUT /api/v1/staff/timesheet/{id}/approve", "requires": "Submitted status", "role": "Manager", "double_click": "Confirmation required"},
        ],
        "backend_checks": [
            "Auto-sync pulls from 6 source systems - no manual entry of auto-synced data",
            "Total daily minutes capped at 1440 (24 hours)",
            "Approved minutes cannot exceed submitted minutes",
            "Manager can only approve their team members' timesheets",
            "Locked after payroll processing"
        ],
        "mobile_parity": [
            {"check": "View today entries", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Submit timesheet", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Team approval", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "high", "description": "Manual time entry injection bypassing auto-sync source validation"},
            {"level": "high", "description": "Approved minutes exceeding submitted minutes creates data inconsistency"},
            {"level": "medium", "description": "Cross-team approval bypass - manager approving non-team member"},
        ]
    },

    "staff_day_planner": {
        "risk_level": "medium",
        "ui_components": ["Day Progress Tab", "Task Planner Tab", "KRA Status Tab", "Time Sheet Tab", "Summary Cards", "Team View"],
        "field_rules": [
            {"field": "Plan Item", "type": "string", "required": True, "max_length": 256, "editable_by": "Employee", "validation": "Non-empty text"},
            {"field": "Planned Time", "type": "integer", "required": True, "format": "Minutes (15-480)", "editable_by": "Employee", "validation": "Min 15 min, max 8 hours per item"},
            {"field": "Actual Time", "type": "integer", "required": False, "format": "Minutes", "editable_by": "Employee", "validation": "Must be logged during/after execution"},
            {"field": "Status", "type": "enum", "required": True, "format": "Pending/In Progress/Completed/Carried Forward", "editable_by": "Employee/System", "validation": "System auto-carries forward unfinished items"},
        ],
        "button_validations": [
            {"button": "Add Plan Item", "api": "POST /api/v1/staff/day-plans/items", "requires": "Text and time entered", "role": "Employee", "double_click": "Disabled while saving"},
            {"button": "Start Timer", "api": "PUT /api/v1/staff/day-plans/items/{id}/start", "requires": "Item in Pending status", "role": "Employee", "double_click": "Toggle behavior"},
        ],
        "backend_checks": [
            "Plan items validated for date ownership (cannot modify other dates without carry-forward)",
            "Carried forward items auto-created by system, not manual",
            "Time sheet data syncs with timesheet module",
            "On-leave detection prevents plan creation for leave days"
        ],
        "mobile_parity": [
            {"check": "Create plan items", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Day Progress view", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Team view", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "medium", "description": "Carry-forward logic must be system-driven to prevent manual backdating"},
            {"level": "medium", "description": "Time sheet sync must be atomic to prevent partial updates"},
            {"level": "low", "description": "On-leave employees should not see plan creation options"},
        ]
    },

    "staff_journey_tracking": {
        "risk_level": "high",
        "ui_components": ["Journey Start Form", "Live Map", "Checkpoint Logger", "Distance Calculator", "Journey History"],
        "field_rules": [
            {"field": "Transport Mode", "type": "enum", "required": True, "format": "Bike/Car/Bus/Train/Auto/Walk", "editable_by": "Employee", "validation": "Must select before journey start"},
            {"field": "Company", "type": "enum", "required": True, "format": "Company list from DC Protocol", "editable_by": "Employee", "validation": "Must match assigned companies"},
            {"field": "Start Location", "type": "coordinates", "required": True, "format": "lat,lng", "editable_by": "System (GPS)", "validation": "Auto-captured, not manual entry"},
            {"field": "End Location", "type": "coordinates", "required": True, "format": "lat,lng", "editable_by": "System (GPS)", "validation": "Auto-captured at journey end"},
            {"field": "Distance (km)", "type": "float", "required": True, "format": "0.1-500", "editable_by": "System (calculated)", "validation": "Calculated from GPS route, not manual"},
        ],
        "button_validations": [
            {"button": "Start Journey", "api": "POST /api/v1/staff/journeys/start", "requires": "Company selected, transport selected, GPS active", "role": "Employee", "double_click": "Cannot start two journeys simultaneously"},
            {"button": "Add Checkpoint", "api": "POST /api/v1/staff/journeys/{id}/checkpoint", "requires": "Journey in progress", "role": "Employee", "double_click": "Min 2-minute gap between checkpoints"},
            {"button": "End Journey", "api": "PUT /api/v1/staff/journeys/{id}/end", "requires": "Journey in progress", "role": "Employee", "double_click": "Confirmation required"},
        ],
        "backend_checks": [
            "GPS coordinates validated for reasonableness (speed between points)",
            "Distance calculated server-side from GPS track, not client",
            "Transport rate applied from dynamic rate configuration",
            "WVV Protocol compliance verified",
            "Cannot have overlapping journeys",
            "Journey auto-ends after 12 hours if not manually ended"
        ],
        "mobile_parity": [
            {"check": "GPS tracking", "web": "Limited", "mobile": "Full background GPS", "status": "MOBILE-ONLY"},
            {"check": "Background tracking", "web": "No", "mobile": "Yes (Capacitor)", "status": "MOBILE-ONLY"},
            {"check": "Journey history", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "critical", "description": "GPS spoofing could fabricate entire journeys for false reimbursement"},
            {"level": "high", "description": "Client-side distance calculation could be manipulated"},
            {"level": "high", "description": "Transport mode misselection to claim higher rates"},
            {"level": "medium", "description": "Overlapping journey detection failure could create duplicate claims"},
        ]
    },

    "staff_crm_leads": {
        "risk_level": "medium",
        "ui_components": ["Lead List", "Pipeline Board", "Lead Detail Form", "Activity Timeline", "Assignment Panel"],
        "field_rules": [
            {"field": "Lead Name", "type": "string", "required": True, "max_length": 128, "editable_by": "Creator/Handler", "validation": "Non-empty"},
            {"field": "Phone", "type": "string", "required": True, "format": "10-digit", "editable_by": "Creator/Handler", "validation": "Valid Indian mobile number"},
            {"field": "Category", "type": "enum", "required": True, "format": "From signup_categories", "editable_by": "Creator", "validation": "Must match active categories"},
            {"field": "Handler", "type": "reference", "required": True, "format": "Staff/Partner/Member ID", "editable_by": "Manager", "validation": "Must be active employee/partner"},
            {"field": "Stage", "type": "enum", "required": True, "format": "Pipeline stages", "editable_by": "Handler/Manager", "validation": "Must follow valid stage transitions"},
        ],
        "button_validations": [
            {"button": "Create Lead", "api": "POST /api/v1/crm/leads", "requires": "Name, phone, category filled", "role": "Any staff", "double_click": "Duplicate phone check"},
            {"button": "Assign Handler", "api": "PUT /api/v1/crm/leads/{id}/assign", "requires": "Valid handler selected", "role": "Manager", "double_click": "Confirmation modal"},
            {"button": "Convert", "api": "PUT /api/v1/crm/leads/{id}/convert", "requires": "All required fields completed", "role": "Handler", "double_click": "Disabled after click"},
        ],
        "backend_checks": [
            "Tri-user RBAC: Staff, Partner, Member handler types validated",
            "Company ID isolation on all lead queries",
            "Cross-selling leads maintain source category reference",
            "Lead assignment validates handler belongs to same company",
            "Auto-sync with SFMS on conversion"
        ],
        "mobile_parity": [
            {"check": "Create lead", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Pipeline view", "web": "Board view", "mobile": "List view", "status": "VERIFY"},
            {"check": "Activity logging", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "medium", "description": "Handler assignment across companies could leak data"},
            {"level": "medium", "description": "Duplicate lead creation for same phone number across categories"},
            {"level": "low", "description": "Pipeline view differences between web and mobile"},
        ]
    },

    "staff_menu_access": {
        "risk_level": "critical",
        "ui_components": ["Staff List", "Menu Tree", "Permission Checkboxes", "Cascade Toggle", "Bulk Assignment"],
        "field_rules": [
            {"field": "Staff Member", "type": "reference", "required": True, "format": "Employee ID", "editable_by": "Admin/HR", "validation": "Must be active employee"},
            {"field": "Menu Item", "type": "reference", "required": True, "format": "Menu code", "editable_by": "Admin", "validation": "Must exist in StaffMenuRegistry"},
            {"field": "Access", "type": "boolean", "required": True, "format": "Grant/Revoke", "editable_by": "Admin", "validation": "Cascade logic for parent sections"},
        ],
        "button_validations": [
            {"button": "Save Permissions", "api": "PUT /api/v1/staff/menu-settings/update", "requires": "At least one change made", "role": "Admin/HR", "double_click": "Disabled during save"},
            {"button": "Bulk Assign", "api": "POST /api/v1/staff/menu-settings/bulk", "requires": "Staff and menus selected", "role": "Admin", "double_click": "Confirmation required"},
        ],
        "backend_checks": [
            "Zero-Default Policy: new staff have NO access until explicitly granted",
            "Parent section cascade properly includes/excludes children",
            "Cannot grant access beyond own access level (privilege escalation blocked)",
            "All permission changes audit-logged with who/when/what",
            "Immediate effect on next page load for the target staff member"
        ],
        "mobile_parity": [
            {"check": "View permissions", "web": "Yes", "mobile": "Limited", "status": "VERIFY"},
            {"check": "Modify permissions", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "critical", "description": "Privilege escalation: staff granting themselves admin access via direct API"},
            {"level": "critical", "description": "Cascade logic error could grant unintended access to sensitive pages"},
            {"level": "high", "description": "Permission changes not taking immediate effect (caching issue)"},
            {"level": "high", "description": "No audit trail would make unauthorized access undetectable"},
        ]
    },

    "staff_payroll_management": {
        "risk_level": "critical",
        "ui_components": ["Payroll Dashboard", "Salary Calculator", "Deduction Manager", "Payment Status", "Payslip Generator"],
        "field_rules": [
            {"field": "Basic Salary", "type": "decimal", "required": True, "format": "Positive number", "editable_by": "HR/Finance", "validation": "Min wage compliance check"},
            {"field": "Deductions", "type": "decimal", "required": False, "format": "Positive number", "editable_by": "System/HR", "validation": "Cannot exceed gross salary"},
            {"field": "Net Pay", "type": "decimal", "required": True, "format": "Calculated", "editable_by": "System only", "validation": "Gross - Deductions, must be >= 0"},
            {"field": "Pay Period", "type": "date_range", "required": True, "format": "Month-Year", "editable_by": "System", "validation": "Cannot process same period twice"},
        ],
        "button_validations": [
            {"button": "Run Payroll", "api": "POST /api/v1/staff/payroll/calculate", "requires": "Attendance locked, previous payroll completed", "role": "HR/Finance", "double_click": "Single execution lock with advisory lock"},
            {"button": "Approve Payroll", "api": "PUT /api/v1/staff/payroll/{id}/approve", "requires": "Calculated status, review completed", "role": "Finance Admin", "double_click": "Confirmation with amount summary"},
        ],
        "backend_checks": [
            "Payroll calculation uses advisory lock to prevent duplicate execution",
            "Attendance must be locked before payroll can start",
            "Net pay validation: cannot be negative",
            "Statutory deductions (PF, ESI, TDS) auto-calculated per rules",
            "SFMS integration creates corresponding journal entries",
            "Payslip generation only after final approval"
        ],
        "mobile_parity": [
            {"check": "View payslip", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Run payroll", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
            {"check": "Approve payroll", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "critical", "description": "Duplicate payroll execution could double-pay all employees"},
            {"level": "critical", "description": "Salary manipulation via direct API without proper authorization"},
            {"level": "high", "description": "Deduction calculation errors affecting statutory compliance"},
            {"level": "high", "description": "SFMS sync failure creating accounting discrepancies"},
        ]
    },
}
