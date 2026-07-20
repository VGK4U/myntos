"""
DC Protocol: Staff System Guide Content
Dynamic training documentation for all staff pages.
Maps menu_code -> detailed guide content.
When new pages are added to StaffMenuRegistry, they auto-appear in the guide.
Pages with entries here get rich training content; others show basic info from registry.
"""

SECTION_DESCRIPTIONS = {
    "progress": {
        "description": "Real-time overview of your daily activities across all systems - attendance, tasks, KRA, timesheet, and journeys.",
        "icon": "fas fa-chart-line"
    },
    "PROGRESS": {
        "description": "Real-time overview of your daily activities across all systems - attendance, tasks, KRA, timesheet, and journeys.",
        "icon": "fas fa-chart-line"
    },
    "staff-dashboard": {
        "description": "Central hub for employee information, personal profile, KYC documents, and team overview.",
        "icon": "fas fa-tachometer-alt"
    },
    "STAFF_DASHBOARD": {
        "description": "Central hub for employee information, personal profile, KYC documents, and team overview.",
        "icon": "fas fa-tachometer-alt"
    },
    "attendance": {
        "description": "Complete attendance lifecycle - clock in/out, leave management, attendance records, and exception handling.",
        "icon": "fas fa-clock"
    },
    "crm": {
        "description": "Customer Relationship Management for tracking leads, managing sales pipeline, and team performance.",
        "icon": "fas fa-handshake"
    },
    "task-management": {
        "description": "Plan, assign, track, and review tasks. Includes day planner, task assignment, and team activity monitoring.",
        "icon": "fas fa-tasks"
    },
    "kra-management": {
        "description": "Key Result Areas tracking - set targets, monitor completion, and review performance metrics.",
        "icon": "fas fa-bullseye"
    },
    "timesheet": {
        "description": "Unified timesheet management with auto-synced time from KRA, Tasks, Day Plan, Journeys, Leads, and Tickets.",
        "icon": "fas fa-calendar-alt"
    },
    "journey-tracking": {
        "description": "GPS-based field visit tracking with route recording, distance calculation, and transport mode selection.",
        "icon": "fas fa-route"
    },
    "location-tracking": {
        "description": "Real-time and historical location tracking for field staff with live maps and movement history.",
        "icon": "fas fa-map-marker-alt"
    },
    "reimbursement": {
        "description": "Submit and approve expense reimbursement claims with receipt uploads and SFMS integration.",
        "icon": "fas fa-receipt"
    },
    "service-tickets": {
        "description": "Complete EV service ticket lifecycle - raise tickets, track repairs, manage spare parts, and monitor performance.",
        "icon": "fas fa-ticket-alt"
    },
    "sfms": {
        "description": "Staff Financial Management System - income, expenses, invoices, fund allocations, and financial reporting.",
        "icon": "fas fa-calculator"
    },
    "inventory": {
        "description": "Stock management including Bill of Materials, manufacturing, procurement, intake validation, and vendor returns.",
        "icon": "fas fa-boxes"
    },
    "payroll": {
        "description": "Complete payroll management with ONROLE/OFFROLE profiles, salary cycles, approvals, and consultant invoicing.",
        "icon": "fas fa-money-bill-wave"
    },
    "accounts": {
        "description": "Financial management system for accounts, invoices, and reporting.",
        "icon": "fas fa-calculator"
    },
    "official-partners": {
        "description": "B2B order management for Dealers, Distributors, Vendors, and Service Centers - from ordering to fulfillment.",
        "icon": "fas fa-handshake"
    },
    "nda-management": {
        "description": "Non-Disclosure Agreement management - create, version, track acceptance, and audit compliance.",
        "icon": "fas fa-file-signature"
    },
    "configuration": {
        "description": "System configuration and master data management - departments, companies, categories, menu access, and audit trails.",
        "icon": "fas fa-cog"
    },
    "zynova": {
        "description": "VGK4U Real Estate and Insurance program management with property listings and member earnings.",
        "icon": "fas fa-building"
    },
    "real-dreams": {
        "description": "Real Dreams property marketplace - browse, manage, and track real estate listings.",
        "icon": "fas fa-home"
    },
    "zy-member-earnings": {
        "description": "VGK4U member earnings, MNR Points tracking, incentive approvals, and program-wise member data.",
        "icon": "fas fa-coins"
    },
}

GUIDE_CONTENT = {
    "staff_progress_dashboard": {
        "purpose": "Single-screen dashboard showing your complete daily activity status across all systems - attendance, day planner, KRA, day closure, timesheet, and HR attendance.",
        "who_can_access": "All Staff Members. Supervisors/Managers also see their team members' progress.",
        "main_sections": [
            {"name": "My Progress", "description": "Your personal row showing 8 activity columns for the selected date"},
            {"name": "Team Progress", "description": "Same 8-column view for each team member (supervisors only)"},
            {"name": "On Leave Section", "description": "Team members detected as on leave, shown separately with leave type badges"}
        ],
        "usage_flow": [
            "Open the Progress page - it loads today's date by default",
            "Review your personal row across all 8 columns: Name, Clock In, Task Planner, KRA Status, Day Closure, Time Sheet, Clock Out, HR Attendance",
            "Check the number breakdowns: Grey = Total, Green = Done, Red = Delayed, Yellow = Pending, Blue = Updated time",
            "If you're a supervisor, scroll down to see your team's progress rows",
            "Use the date picker to check progress for any previous date",
            "Use the Filter Employees dropdown to focus on specific team members"
        ],
        "fields": [
            {"name": "Clock In", "description": "Shows whether you clocked in and at what time. Green = Done, Red = Pending."},
            {"name": "Task Planner", "description": "Plan status with breakdown: Overall / Pending / Planned tasks count."},
            {"name": "KRA Status", "description": "KRA completion: Total / Done / Delayed / Pending or Skipped."},
            {"name": "Day Closure", "description": "End-of-day summary: Planned / Closed / Left / Worked."},
            {"name": "Time Sheet", "description": "Timesheet with time breakdown: Updated time (blue) / Approved time (green)."},
            {"name": "Clock Out", "description": "Shows whether you clocked out and at what time."},
            {"name": "HR Attendance", "description": "HR-marked attendance status with approval state."}
        ],
        "statuses": [
            {"status": "Present", "meaning": "Marked present by HR", "color": "#dcfce7"},
            {"status": "Half Day", "meaning": "Marked as half day attendance", "color": "#ffc107"},
            {"status": "Absent", "meaning": "Marked absent by HR", "color": "#dc3545"},
            {"status": "Sick Leave", "meaning": "On approved sick leave", "color": "#0dcaf0"},
            {"status": "Casual Leave", "meaning": "On approved casual leave", "color": "#0dcaf0"},
            {"status": "Approved Leave", "meaning": "On approved leave (general)", "color": "#0dcaf0"},
            {"status": "Holiday", "meaning": "Company holiday", "color": "#0d6efd"},
            {"status": "Weekend", "meaning": "Weekend off", "color": "#0d6efd"}
        ],
        "tips": [
            "Check your progress dashboard first thing in the morning to confirm your clock-in registered",
            "Review team progress at end of day before finalizing your own day closure",
            "On-leave team members appear in a separate section - no need to worry about missing rows",
            "Team section shows only your subordinates - your own data always appears in the My Progress section at the top, never duplicated in the team grid"
        ],
        "common_mistakes": [
            "Forgetting to clock in - this shows as 'Pending' all day",
            "Not finalizing day planner - numbers stay as 'pending'",
            "Checking yesterday's date instead of today's when reviewing current status"
        ]
    },

    "staff_dashboard_main": {
        "purpose": "Your personal home page in the Staff Portal. Shows quick access to all key areas, recent notifications, and a summary of your daily status.",
        "who_can_access": "All Staff Members",
        "main_sections": [
            {"name": "Quick Stats", "description": "Summary cards showing attendance status, pending tasks, and notifications"},
            {"name": "Navigation Cards", "description": "Quick-access cards to commonly used pages"},
            {"name": "Recent Activity", "description": "Latest updates and notifications relevant to you"}
        ],
        "usage_flow": [
            "Dashboard loads automatically after login",
            "Review any pending notifications or alerts at the top",
            "Click on quick-access cards to navigate to specific modules",
            "Check your daily stats summary"
        ],
        "fields": [],
        "statuses": [],
        "tips": [
            "Bookmark your dashboard for quick access",
            "Check notifications regularly - they include pending approvals and important updates"
        ],
        "common_mistakes": []
    },

    "staff_employees": {
        "purpose": "View and manage employee records including personal details, employment status, department assignment, and reporting structure.",
        "who_can_access": "HR Managers, Department Heads, and authorized supervisors",
        "main_sections": [
            {"name": "Employee List", "description": "Searchable table of all employees with key details"},
            {"name": "Employee Profile", "description": "Detailed view of individual employee information"},
            {"name": "Filters", "description": "Filter by department, status, role, or employment type"}
        ],
        "usage_flow": [
            "Open the Employees page to see the full list",
            "Use search bar to find specific employees by name or code",
            "Apply filters to narrow down by department, status, or role",
            "Click on an employee to view their full profile",
            "Edit employee details if you have the required permissions"
        ],
        "fields": [
            {"name": "Employee Code", "description": "Unique identifier assigned to each employee"},
            {"name": "Department", "description": "The department the employee belongs to"},
            {"name": "Designation", "description": "Employee's job title/role"},
            {"name": "Reporting To", "description": "The supervisor/manager this employee reports to"},
            {"name": "Status", "description": "Active, Inactive, or On Notice period"},
            {"name": "Employment Type", "description": "ONROLE (full-time) or OFFROLE (consultant/contract)"}
        ],
        "statuses": [
            {"status": "Active", "meaning": "Currently employed and working", "color": "#dcfce7"},
            {"status": "Inactive", "meaning": "No longer employed or suspended", "color": "#fee2e2"},
            {"status": "On Notice", "meaning": "In the notice/separation period", "color": "#fef3c7"}
        ],
        "tips": [
            "Always verify the reporting structure is correct - it affects approvals across the system",
            "Keep contact details updated for emergency communications"
        ],
        "common_mistakes": [
            "Assigning wrong reporting manager - this breaks all approval chains",
            "Not updating employment status promptly when someone leaves"
        ]
    },

    "staff_employee_directory": {
        "purpose": "Quick-reference directory of all employees with contact information, department, and designation. Designed for looking up colleagues.",
        "who_can_access": "All Staff Members (read-only for most users)",
        "main_sections": [
            {"name": "Directory Grid", "description": "Card or list view of employees with photo, name, department, and contact info"},
            {"name": "Search & Filter", "description": "Search by name, department, or designation"}
        ],
        "usage_flow": [
            "Open Employee Directory to browse all colleagues",
            "Use search to find someone by name",
            "Filter by department to see team members",
            "Click on a card to see contact details"
        ],
        "fields": [
            {"name": "Name & Photo", "description": "Employee name with profile picture if available"},
            {"name": "Department", "description": "Department the employee belongs to"},
            {"name": "Designation", "description": "Job title"},
            {"name": "Contact", "description": "Phone number and email for reaching out"}
        ],
        "statuses": [],
        "tips": ["Use this page to quickly find a colleague's contact number or department"],
        "common_mistakes": []
    },

    "staff_my_kyc": {
        "purpose": "Upload and manage your KYC (Know Your Customer) documents such as Aadhaar, PAN, bank details, and address proof.",
        "who_can_access": "All Staff Members (own profile only)",
        "main_sections": [
            {"name": "Document Upload", "description": "Upload areas for each required document type"},
            {"name": "Verification Status", "description": "Shows approval status of each uploaded document"},
            {"name": "Bank Details", "description": "Bank account information for salary processing"}
        ],
        "usage_flow": [
            "Open My KYC page",
            "Upload each required document (Aadhaar, PAN, etc.)",
            "Fill in bank account details",
            "Submit for verification",
            "Wait for HR/Admin approval - status will update automatically"
        ],
        "fields": [
            {"name": "Aadhaar Card", "description": "Upload front and back of Aadhaar card"},
            {"name": "PAN Card", "description": "Upload PAN card image"},
            {"name": "Bank Account", "description": "Account number, IFSC code, bank name, branch"},
            {"name": "Address Proof", "description": "Any government-issued address proof"}
        ],
        "statuses": [
            {"status": "Pending", "meaning": "Document uploaded but not yet reviewed", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Document verified and accepted", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Document rejected - re-upload required", "color": "#fee2e2"}
        ],
        "tips": [
            "Upload clear, readable scans - blurry images get rejected",
            "Double-check bank details before submitting - wrong IFSC delays salary processing"
        ],
        "common_mistakes": [
            "Uploading blurry or cropped document images",
            "Entering wrong bank account number or IFSC code",
            "Not completing all mandatory documents"
        ]
    },

    "staff_kyc_approvals": {
        "purpose": "Review and approve/reject KYC documents submitted by employees. Each field (Aadhaar, PAN, Bank) is tracked independently.",
        "who_can_access": "HR Managers and authorized approvers",
        "main_sections": [
            {"name": "Pending Approvals", "description": "List of employees with documents waiting for review"},
            {"name": "Document Preview", "description": "View uploaded documents side by side"},
            {"name": "Approval Actions", "description": "Approve or reject each document with comments"}
        ],
        "usage_flow": [
            "Open KYC Approvals page",
            "See list of employees with pending document submissions",
            "Click on an employee to view their uploaded documents",
            "Review each document carefully",
            "Approve or Reject with comments explaining any issues",
            "Employee gets notified of the decision"
        ],
        "fields": [],
        "statuses": [
            {"status": "Pending Review", "meaning": "Waiting for your review", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Document accepted", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Document needs re-submission", "color": "#fee2e2"}
        ],
        "tips": [
            "Always add a clear reason when rejecting so employees know what to fix",
            "Process KYC approvals promptly - delays hold up salary processing"
        ],
        "common_mistakes": [
            "Approving blurry or unreadable documents",
            "Not verifying bank details match the employee's name"
        ]
    },

    "staff_my_attendance": {
        "purpose": "View your daily clock-in and clock-out records. Shows your attendance history with timestamps.",
        "who_can_access": "All Staff Members (own records only)",
        "main_sections": [
            {"name": "Today's Status", "description": "Current day clock-in/out status"},
            {"name": "Monthly View", "description": "Calendar or list view of attendance records for the month"},
            {"name": "Summary", "description": "Total present days, leaves, and late arrivals"}
        ],
        "usage_flow": [
            "Open My Attendance (In/Out Time) page",
            "View today's clock-in time at the top",
            "Browse monthly attendance using the date navigator",
            "Check summary statistics at the bottom"
        ],
        "fields": [
            {"name": "Date", "description": "The working date"},
            {"name": "Clock In", "description": "Time you marked attendance in the morning"},
            {"name": "Clock Out", "description": "Time you marked end-of-day"},
            {"name": "Total Hours", "description": "Duration between clock-in and clock-out"},
            {"name": "Status", "description": "Present, Absent, Leave, Half Day, etc."}
        ],
        "statuses": [],
        "tips": [
            "Always clock in as soon as you start your workday",
            "If you forget to clock out, it may show as incomplete"
        ],
        "common_mistakes": [
            "Forgetting to clock in/out results in attendance discrepancies",
            "Not applying for regularization when you miss a punch"
        ]
    },

    "staff_my_leaves": {
        "purpose": "Apply for leave, view leave balance, and track the status of your leave requests.",
        "who_can_access": "All Staff Members",
        "main_sections": [
            {"name": "Leave Balance", "description": "Available balance for each leave type (Casual, Sick, etc.)"},
            {"name": "Apply Leave", "description": "Form to submit a new leave request"},
            {"name": "Leave History", "description": "Past leave applications with approval status"}
        ],
        "usage_flow": [
            "Open My Leaves page",
            "Check your available leave balance at the top",
            "Click 'Apply Leave' to submit a new request",
            "Select leave type, start date, end date, and reason",
            "Submit the request - it goes to your reporting manager",
            "Track the approval status in Leave History"
        ],
        "fields": [
            {"name": "Leave Type", "description": "Casual Leave, Sick Leave, Unpaid Leave, etc."},
            {"name": "Start Date", "description": "First day of leave"},
            {"name": "End Date", "description": "Last day of leave"},
            {"name": "Reason", "description": "Why you need the leave"},
            {"name": "Status", "description": "Pending, Approved, Rejected"}
        ],
        "statuses": [
            {"status": "Pending Manager", "meaning": "Waiting for your manager's approval", "color": "#fef3c7"},
            {"status": "Pending HR", "meaning": "Manager approved, waiting for HR confirmation", "color": "#dbeafe"},
            {"status": "Approved", "meaning": "Leave granted", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Leave request denied", "color": "#fee2e2"}
        ],
        "tips": [
            "Apply for planned leave at least 2-3 days in advance",
            "For sick leave, apply as soon as possible and attach medical documents if needed",
            "Check your balance before applying to avoid rejections"
        ],
        "common_mistakes": [
            "Applying for leave after the fact without prior intimation",
            "Not checking leave balance before applying",
            "Missing the reason field - managers may reject without context"
        ]
    },

    "staff_leave_approvals": {
        "purpose": "Review and approve/reject leave requests from your team members.",
        "who_can_access": "Managers and Supervisors (for their direct reports)",
        "main_sections": [
            {"name": "Pending Requests", "description": "Leave applications waiting for your decision"},
            {"name": "Approved/Rejected", "description": "History of your past decisions"},
            {"name": "Team Calendar", "description": "View of who is on leave on which dates"}
        ],
        "usage_flow": [
            "Open Leave Approvals page",
            "Review pending leave requests from your team",
            "Check the team calendar to see if there are conflicts",
            "Approve or reject each request with optional comments",
            "Employee gets notified of your decision"
        ],
        "fields": [],
        "statuses": [
            {"status": "Pending", "meaning": "Waiting for your action", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "You approved this request", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "You rejected this request", "color": "#fee2e2"}
        ],
        "tips": [
            "Check the team calendar before approving to avoid too many people being absent",
            "Process pending requests within 24 hours"
        ],
        "common_mistakes": [
            "Approving overlapping leaves that leave the team understaffed"
        ]
    },

    "staff_attendance_sheet": {
        "purpose": "HR master attendance record. Mark attendance status for each employee on a daily basis - present, absent, half day, or leave type.",
        "who_can_access": "HR team and authorized attendance managers",
        "main_sections": [
            {"name": "Daily Sheet", "description": "Grid showing all employees with attendance marking options"},
            {"name": "Bulk Actions", "description": "Mark multiple employees at once for holidays/weekends"},
            {"name": "Status Filters", "description": "Filter to see only unmarked or specific status entries"}
        ],
        "usage_flow": [
            "Open Attendance Records for the target date",
            "Review each employee's clock-in/out data",
            "Mark the appropriate attendance status for each employee",
            "Use bulk actions for company-wide holidays or weekends",
            "Save/submit the sheet for the day"
        ],
        "fields": [
            {"name": "Employee", "description": "Employee name and code"},
            {"name": "Clock In/Out", "description": "System-recorded timestamps from biometric/app"},
            {"name": "Status", "description": "Present, Absent, Half Day, Sick Leave, Casual Leave, Approved Leave, Unpaid Leave, Holiday, Weekend"},
            {"name": "Remarks", "description": "Optional notes for special cases"}
        ],
        "statuses": [
            {"status": "Present", "meaning": "Employee worked full day", "color": "#dcfce7"},
            {"status": "Half Day", "meaning": "Employee worked partial day", "color": "#ffc107"},
            {"status": "Absent", "meaning": "No attendance without approved leave", "color": "#dc3545"},
            {"status": "Sick Leave", "meaning": "On sick leave", "color": "#0dcaf0"},
            {"status": "Casual Leave", "meaning": "On casual leave", "color": "#0dcaf0"},
            {"status": "Approved Leave", "meaning": "On pre-approved leave", "color": "#0dcaf0"},
            {"status": "Unpaid Leave", "meaning": "Leave without pay", "color": "#6c757d"},
            {"status": "Holiday", "meaning": "Company holiday", "color": "#0d6efd"},
            {"status": "Weekend", "meaning": "Weekly off", "color": "#0d6efd"}
        ],
        "tips": [
            "Complete attendance marking before end of day",
            "Cross-reference with leave approvals before marking absent"
        ],
        "common_mistakes": [
            "Marking someone absent when they have an approved leave request",
            "Forgetting to mark weekends/holidays for the whole organization"
        ]
    },

    "staff_attendance_reports": {
        "purpose": "Comprehensive attendance analytics dashboard with reports on attendance patterns, late arrivals, leave utilization, and monthly summaries.",
        "who_can_access": "HR team, Managers (for their team), and authorized staff",
        "main_sections": [
            {"name": "Summary Dashboard", "description": "Visual charts showing attendance trends"},
            {"name": "Detailed Reports", "description": "Downloadable reports with attendance data"},
            {"name": "Filters", "description": "Filter by date range, department, and employee"}
        ],
        "usage_flow": [
            "Open Attendance Dashboard",
            "Select the date range for the report",
            "Choose department or employee filters as needed",
            "Review visual charts and summary statistics",
            "Download detailed reports for payroll processing"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Use this at month-end to prepare payroll attendance data"],
        "common_mistakes": []
    },

    "staff_attendance_exceptions": {
        "purpose": "Handle attendance exceptions like missed punches, incorrect entries, or regularization requests from employees.",
        "who_can_access": "HR Managers and authorized supervisors",
        "main_sections": [
            {"name": "Exception List", "description": "All attendance irregularities pending resolution"},
            {"name": "Regularization Requests", "description": "Employee-submitted requests to correct attendance"},
            {"name": "Approval Actions", "description": "Approve or reject exception requests"}
        ],
        "usage_flow": [
            "Open Exception Approvals page",
            "Review list of attendance exceptions",
            "Check supporting evidence (reason, time, etc.)",
            "Approve or reject each exception",
            "Approved exceptions auto-update the attendance sheet"
        ],
        "fields": [],
        "statuses": [
            {"status": "Pending", "meaning": "Waiting for review", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Exception accepted, attendance corrected", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Exception denied", "color": "#fee2e2"}
        ],
        "tips": ["Process exceptions within the same pay period to avoid payroll delays"],
        "common_mistakes": []
    },

    "staff_team_attendance": {
        "purpose": "View clock-in and clock-out records for all team members. Admin view of daily attendance timestamps.",
        "who_can_access": "Managers, HR, and authorized supervisors",
        "main_sections": [
            {"name": "Daily Records", "description": "Table showing all employees' in/out times for the selected date"},
            {"name": "Date Navigation", "description": "Browse attendance by date"},
            {"name": "Summary", "description": "Quick counts of present, absent, late, etc."}
        ],
        "usage_flow": [
            "Open Team Attendance (In/Out Records) page",
            "Select the date to review",
            "Browse team members' clock-in and clock-out times",
            "Identify late arrivals or missing entries"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Use this with the Attendance Sheet for comprehensive attendance tracking"],
        "common_mistakes": []
    },

    "staff_team_attendance_summary": {
        "purpose": "Monthly summary view of team attendance statistics including present days, leaves taken, and late arrivals.",
        "who_can_access": "Managers and HR staff",
        "main_sections": [
            {"name": "Monthly Grid", "description": "Calendar-style grid showing attendance for each employee per day"},
            {"name": "Statistics", "description": "Counts of present, absent, leave, late for each employee"},
            {"name": "Export", "description": "Download attendance summary for payroll"}
        ],
        "usage_flow": [
            "Open Team Attendance Summary",
            "Select the month to review",
            "Review the monthly grid for each employee",
            "Check statistics for attendance compliance",
            "Export data for payroll if needed"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Review at month-end before payroll processing"],
        "common_mistakes": []
    },

    "staff_crm_dashboard": {
        "purpose": "Personal CRM dashboard showing your lead pipeline, conversion rates, follow-up tasks, and revenue tracking.",
        "who_can_access": "All Staff with CRM access",
        "main_sections": [
            {"name": "Pipeline Overview", "description": "Visual funnel showing leads at each stage"},
            {"name": "Today's Follow-ups", "description": "Leads that need action today"},
            {"name": "Performance Metrics", "description": "Your conversion rates and targets"},
            {"name": "Recent Activity", "description": "Latest lead interactions and updates"}
        ],
        "usage_flow": [
            "Open My CRM Dashboard",
            "Check today's follow-ups first - these are priority",
            "Review your pipeline for any stalled leads",
            "Update lead statuses after interactions",
            "Track your performance against targets"
        ],
        "fields": [],
        "statuses": [],
        "tips": [
            "Start each day by checking today's follow-ups",
            "Update lead status immediately after every interaction"
        ],
        "common_mistakes": [
            "Not updating lead status after calls/meetings",
            "Ignoring stalled leads in the pipeline"
        ]
    },

    "staff_my_leads": {
        "purpose": "View and manage all leads assigned to you. Track lead status, add follow-up notes, schedule calls, and update deal values.",
        "who_can_access": "All Staff Members with CRM access (own leads only)",
        "main_sections": [
            {"name": "Lead List", "description": "All leads assigned to you with filters and search"},
            {"name": "Lead Detail", "description": "Complete lead information with interaction history"},
            {"name": "Follow-up Actions", "description": "Schedule calls, meetings, and set reminders"}
        ],
        "usage_flow": [
            "Open My Leads page",
            "Filter leads by status, priority, or date",
            "Click on a lead to view full details",
            "Add notes after each interaction",
            "Update lead status as it progresses through stages",
            "Schedule follow-up actions with reminders"
        ],
        "fields": [
            {"name": "Lead Name", "description": "Name of the potential customer/contact"},
            {"name": "Category", "description": "Business category (EV, Real Estate, Insurance, etc.)"},
            {"name": "Status", "description": "New, Contacted, Qualified, Proposal, Won, Lost"},
            {"name": "Deal Value", "description": "Expected revenue from this lead"},
            {"name": "Next Follow-up", "description": "Scheduled date for next action"},
            {"name": "Source", "description": "Where this lead came from (referral, website, event, etc.)"}
        ],
        "statuses": [
            {"status": "New", "meaning": "Freshly assigned, not yet contacted", "color": "#dbeafe"},
            {"status": "Contacted", "meaning": "Initial contact made", "color": "#fef3c7"},
            {"status": "Qualified", "meaning": "Lead shows genuine interest", "color": "#dcfce7"},
            {"status": "Proposal", "meaning": "Proposal/quote sent", "color": "#e9d5ff"},
            {"status": "Won", "meaning": "Deal closed successfully", "color": "#dcfce7"},
            {"status": "Lost", "meaning": "Lead did not convert", "color": "#fee2e2"}
        ],
        "tips": [
            "Update lead status after every interaction",
            "Add detailed notes - they help when following up weeks later",
            "Set follow-up reminders to never miss a callback"
        ],
        "common_mistakes": [
            "Leaving leads in 'New' status for too long",
            "Not adding follow-up notes after calls",
            "Forgetting to update deal values when they change"
        ]
    },

    "staff_leads": {
        "purpose": "Central lead management page for viewing and managing all leads across the organization with advanced filters.",
        "who_can_access": "Staff with lead management permissions",
        "main_sections": [
            {"name": "Lead Grid", "description": "Complete list of all leads with search, sort, and filter"},
            {"name": "Bulk Actions", "description": "Assign, re-assign, or update multiple leads at once"},
            {"name": "Analytics", "description": "Lead conversion metrics and source analysis"}
        ],
        "usage_flow": [
            "Open Staff Leads page",
            "Use filters to narrow down leads by status, category, handler, or date",
            "Click on a lead to view/edit full details",
            "Use bulk actions to reassign leads between team members"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Use filters effectively to focus on high-priority leads"],
        "common_mistakes": []
    },

    "staff_team_leads": {
        "purpose": "View all leads managed by your team members. Monitor team lead activity and conversion performance.",
        "who_can_access": "Team Leaders, Managers, and Supervisors",
        "main_sections": [
            {"name": "Team Lead Overview", "description": "All leads handled by your team with member-wise breakdown"},
            {"name": "Performance Comparison", "description": "Compare conversion rates across team members"},
            {"name": "Reassignment", "description": "Move leads between team members as needed"}
        ],
        "usage_flow": [
            "Open Team Leads page",
            "Review each team member's lead pipeline",
            "Identify any stalled or overdue follow-ups",
            "Reassign leads if a team member is overloaded or unavailable"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Regularly review team lead distribution to ensure balanced workload"],
        "common_mistakes": []
    },

    "staff_lead_sources": {
        "purpose": "Manage and configure lead sources - where leads come from (referrals, website, events, campaigns, etc.).",
        "who_can_access": "CRM Administrators and authorized managers",
        "main_sections": [
            {"name": "Source List", "description": "All configured lead sources"},
            {"name": "Source Performance", "description": "Which sources generate the most leads and conversions"},
            {"name": "Add/Edit Source", "description": "Create new lead sources or modify existing ones"}
        ],
        "usage_flow": [
            "Open Lead Sources page",
            "Review existing lead sources and their performance",
            "Add new sources as your marketing channels expand",
            "Deactivate sources that are no longer relevant"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Keep lead sources up to date for accurate analytics"],
        "common_mistakes": []
    },

    "staff_tasks_day_planner": {
        "purpose": "Plan your daily work by selecting tasks, organizing priorities, tracking time spent, and finalizing your day with end-of-day updates.",
        "who_can_access": "All Staff Members",
        "main_sections": [
            {"name": "Summary Cards", "description": "5 status cards: Total Planned, Completed, In Progress, Pending, Carried Forward"},
            {"name": "Today's Plan (Left Panel)", "description": "Your organized task list with priority, status, progress, and EOD updates"},
            {"name": "Available Tasks (Right Panel)", "description": "All open tasks not yet in today's plan - pick and add"},
            {"name": "Finalize Day", "description": "Lock your day's plan as a daily report submission"}
        ],
        "usage_flow": [
            "Open Task Planner at the start of your workday",
            "Check yesterday's carried-forward tasks (shown with orange highlight)",
            "Browse Available Tasks on the right and select items for today",
            "Click 'Add Selected to Plan' to move them to your daily plan",
            "Throughout the day, update task status as you work",
            "Add time spent on each task using the time tracker",
            "At end of day, add EOD status updates for each task",
            "Click 'Finalize Day' to submit your daily report"
        ],
        "fields": [
            {"name": "#", "description": "Priority order number (you set the sequence)"},
            {"name": "Task / Phase", "description": "Task name - click to view full details"},
            {"name": "Days Pending", "description": "How long the task has been waiting. Green = fresh, Yellow = 2+ weeks, Red = 30+ days"},
            {"name": "Times Planned", "description": "How many previous days this task was added to a plan"},
            {"name": "Type", "description": "Whether it's a Task or a Phase"},
            {"name": "Priority", "description": "Low / Medium / High / Urgent / Critical"},
            {"name": "Status", "description": "Pending, In Progress, Completed, On Hold, etc."},
            {"name": "Progress", "description": "Visual progress bar with percentage"},
            {"name": "Due Date", "description": "Red if overdue, Yellow if today, Green if upcoming"},
            {"name": "Time Sheet", "description": "Updated / Approved time breakdown (blue/green)"},
            {"name": "EOD Status", "description": "Your end-of-day update on this task"}
        ],
        "statuses": [],
        "tips": [
            "Plan your day first thing in the morning",
            "Prioritize critical and urgent tasks at the top",
            "Update task progress throughout the day, not just at EOD",
            "Finalize your day before logging off - carried-forward tasks auto-appear tomorrow"
        ],
        "common_mistakes": [
            "Not planning the day - all tasks stay as 'available' with no tracking",
            "Forgetting to finalize - your daily report doesn't get submitted",
            "Adding too many tasks - be realistic about what you can complete"
        ]
    },

    "staff_tasks_assigned_to_me": {
        "purpose": "View all tasks assigned to you by managers or colleagues. Track deadlines, update progress, and manage your workload.",
        "who_can_access": "All Staff Members (own tasks only)",
        "main_sections": [
            {"name": "Task List", "description": "All tasks assigned to you with status, priority, and deadline"},
            {"name": "Task Detail", "description": "Full task description, attachments, comments, and history"},
            {"name": "Filters", "description": "Filter by status, priority, due date, or assigner"}
        ],
        "usage_flow": [
            "Open Tasks Assigned to Me page",
            "Review pending tasks sorted by priority/deadline",
            "Click on a task to see full details and instructions",
            "Update status as you start working (In Progress)",
            "Add comments or attachments as needed",
            "Mark as completed when done"
        ],
        "fields": [
            {"name": "Task Name", "description": "Title of the task"},
            {"name": "Assigned By", "description": "Who created/assigned this task"},
            {"name": "Priority", "description": "Low, Medium, High, Urgent, Critical"},
            {"name": "Due Date", "description": "Deadline for completion"},
            {"name": "Status", "description": "Pending, In Progress, Completed, On Hold, Cancelled"},
            {"name": "Progress", "description": "Percentage of completion"}
        ],
        "statuses": [
            {"status": "Pending", "meaning": "Not yet started", "color": "#fef3c7"},
            {"status": "In Progress", "meaning": "Currently being worked on", "color": "#dbeafe"},
            {"status": "Completed", "meaning": "Task finished", "color": "#dcfce7"},
            {"status": "On Hold", "meaning": "Paused due to dependency or blocker", "color": "#e5e7eb"},
            {"status": "Cancelled", "meaning": "Task no longer needed", "color": "#fee2e2"}
        ],
        "tips": [
            "Update task status regularly so your manager has visibility",
            "If you're blocked, mark as 'On Hold' and add a comment explaining why"
        ],
        "common_mistakes": [
            "Leaving tasks in 'Pending' when you've already started working",
            "Not checking due dates and missing deadlines"
        ]
    },

    "staff_tasks_assigned_by_me_v2": {
        "purpose": "Track all tasks you've created and assigned to team members. Monitor their progress and provide feedback.",
        "who_can_access": "All Staff Members who can assign tasks",
        "main_sections": [
            {"name": "Task List", "description": "All tasks you've assigned with assignee, status, and progress"},
            {"name": "Create Task", "description": "Form to create and assign new tasks"},
            {"name": "Progress Tracking", "description": "Monitor completion rates and overdue items"}
        ],
        "usage_flow": [
            "Open Assigned By Me page",
            "Click 'Create Task' to assign a new task",
            "Fill in task details: name, description, assignee, priority, due date",
            "Submit the task - assignee gets notified",
            "Monitor progress and add comments as needed",
            "Review completed tasks and provide feedback"
        ],
        "fields": [],
        "statuses": [],
        "tips": [
            "Set clear due dates and priorities when assigning tasks",
            "Add detailed descriptions so assignees know exactly what's expected"
        ],
        "common_mistakes": [
            "Assigning tasks without clear descriptions or deadlines",
            "Not following up on overdue tasks"
        ]
    },

    "staff_task_review": {
        "purpose": "Review completed tasks submitted by team members. Provide feedback, request revisions, or approve the work.",
        "who_can_access": "Managers and Task Reviewers",
        "main_sections": [
            {"name": "Pending Reviews", "description": "Tasks completed and waiting for your review"},
            {"name": "Review Form", "description": "Approve, request changes, or reject with feedback"},
            {"name": "Review History", "description": "Past reviews you've completed"}
        ],
        "usage_flow": [
            "Open Task Review page",
            "See list of tasks awaiting your review",
            "Click on a task to review the work done",
            "Approve if satisfactory, or request revisions with comments",
            "The assignee gets notified of your decision"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Provide constructive feedback when requesting revisions"],
        "common_mistakes": []
    },

    "staff_tasks_tracker": {
        "purpose": "High-level task dashboard showing task distribution, completion trends, and team workload across all projects.",
        "who_can_access": "Managers, Team Leaders, and Project Managers",
        "main_sections": [
            {"name": "Task Overview Charts", "description": "Visual breakdown of tasks by status, priority, and assignee"},
            {"name": "Workload Distribution", "description": "Who has how many tasks and their completion rates"},
            {"name": "Overdue Tracker", "description": "Tasks past their deadline that need attention"}
        ],
        "usage_flow": [
            "Open Task Tracker/Dashboard",
            "Review the overview charts for task health",
            "Check workload distribution to identify overloaded team members",
            "Address any overdue tasks immediately"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Check the overdue tracker daily to prevent tasks from falling through"],
        "common_mistakes": []
    },

    "staff_team_activities": {
        "purpose": "Monitor all activities and task updates from your team members in a unified timeline view.",
        "who_can_access": "Managers and Supervisors",
        "main_sections": [
            {"name": "Activity Feed", "description": "Chronological list of all team task activities"},
            {"name": "Member Filter", "description": "Focus on a specific team member's activities"},
            {"name": "Date Range", "description": "Filter activities by time period"}
        ],
        "usage_flow": [
            "Open Team Activities page",
            "Browse the activity feed to see recent team updates",
            "Filter by specific team member if needed",
            "Use date range to review historical activities"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Quick way to see who did what without opening individual task pages"],
        "common_mistakes": []
    },

    "staff_my_kras": {
        "purpose": "View and track your Key Result Areas (KRAs) - the measurable targets set for your role. Update completion status and log time spent.",
        "who_can_access": "All Staff Members (own KRAs only)",
        "main_sections": [
            {"name": "KRA List", "description": "All your assigned KRAs with targets, deadlines, and current status"},
            {"name": "KRA Detail", "description": "Individual KRA with progress updates and evidence"},
            {"name": "Time Tracking", "description": "Log time spent on each KRA activity"}
        ],
        "usage_flow": [
            "Open My KRAs page",
            "Review your assigned KRAs and their deadlines",
            "Update progress as you complete milestones",
            "Log time spent on KRA activities (auto-syncs to timesheet)",
            "Add evidence or notes for each update",
            "Submit for review when a KRA is fully completed"
        ],
        "fields": [
            {"name": "KRA Title", "description": "Name/description of the key result area"},
            {"name": "Target", "description": "The measurable goal to achieve"},
            {"name": "Deadline", "description": "When this KRA should be completed"},
            {"name": "Progress", "description": "Percentage of completion"},
            {"name": "Status", "description": "Pending, In Progress, Completed, Delayed"},
            {"name": "Time Logged", "description": "Total time spent on this KRA"}
        ],
        "statuses": [
            {"status": "Pending", "meaning": "Not started yet", "color": "#fef3c7"},
            {"status": "In Progress", "meaning": "Actively working on it", "color": "#dbeafe"},
            {"status": "Completed", "meaning": "Target achieved", "color": "#dcfce7"},
            {"status": "Delayed", "meaning": "Past deadline, not completed", "color": "#fee2e2"},
            {"status": "Skipped", "meaning": "Not applicable for this period", "color": "#e5e7eb"}
        ],
        "tips": [
            "Update KRA progress daily for accurate tracking",
            "Time logged here auto-appears in your timesheet"
        ],
        "common_mistakes": [
            "Not updating KRAs regularly - they show as 'Delayed' when deadline passes",
            "Forgetting to log time - it won't reflect in your timesheet"
        ]
    },

    "staff_kra_templates": {
        "purpose": "Create and manage KRA templates that can be assigned to employees based on their role and department.",
        "who_can_access": "HR Managers and KRA Administrators",
        "main_sections": [
            {"name": "Template List", "description": "All available KRA templates"},
            {"name": "Template Builder", "description": "Create new templates with targets and weightage"},
            {"name": "Assignment", "description": "Assign templates to roles/departments"}
        ],
        "usage_flow": [
            "Open KRA Templates page",
            "Create a new template or edit an existing one",
            "Define KRA items with titles, targets, weightage, and deadlines",
            "Save the template",
            "Assign the template to specific roles or departments"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Keep templates role-specific for accurate performance measurement"],
        "common_mistakes": []
    },

    "staff_kra_tracking_sheet": {
        "purpose": "Consolidated tracking sheet showing KRA progress for all team members in a spreadsheet-like view.",
        "who_can_access": "Managers, HR, and KRA Reviewers",
        "main_sections": [
            {"name": "Tracking Grid", "description": "Matrix of employees vs KRAs with status indicators"},
            {"name": "Progress Summary", "description": "Aggregate completion percentages"},
            {"name": "Filters", "description": "Filter by department, employee, or KRA status"}
        ],
        "usage_flow": [
            "Open KRA Tracking Sheet",
            "Select the review period",
            "Browse the tracking grid to see team KRA progress",
            "Click on individual cells for detailed status",
            "Export the sheet for review meetings"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Use this in weekly/monthly review meetings for quick team overview"],
        "common_mistakes": []
    },

    "staff_kra_review": {
        "purpose": "Review and evaluate KRA submissions from team members. Score, provide feedback, and finalize KRA performance.",
        "who_can_access": "Managers and designated KRA Reviewers",
        "main_sections": [
            {"name": "Pending Reviews", "description": "KRA submissions waiting for your evaluation"},
            {"name": "Review Form", "description": "Scoring interface with feedback fields"},
            {"name": "Completed Reviews", "description": "Past evaluations you've done"}
        ],
        "usage_flow": [
            "Open KRA Review page",
            "Select a pending KRA submission to review",
            "Review the employee's progress, evidence, and self-assessment",
            "Provide your score and written feedback",
            "Submit the review - employee gets notified"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Provide specific, actionable feedback for each KRA"],
        "common_mistakes": ["Giving scores without written feedback - employees need context"]
    },

    "staff_my_timesheet": {
        "purpose": "View your unified timesheet with auto-synced time entries from KRA, Tasks, Day Plan, Journeys, Leads, and Tickets. Submit for approval.",
        "who_can_access": "All Staff Members (own timesheet only)",
        "main_sections": [
            {"name": "Today's Entries", "description": "Single-day view of all activity time entries with source breakdown"},
            {"name": "My Timesheet", "description": "Own records in accordion layout showing auto-synced time from each source system"},
            {"name": "Submission", "description": "Submit timesheet for manager approval"}
        ],
        "usage_flow": [
            "Open My Timesheet page",
            "Switch between Today's Entries and My Timesheet views",
            "Today's Entries shows all time logged today from different sources",
            "My Timesheet shows the accordion layout with time grouped by source: KRA, Tasks, Day Plan, Journeys, Leads, Tickets",
            "Review auto-synced entries for accuracy",
            "Submit timesheet for the period when ready"
        ],
        "fields": [
            {"name": "Source", "description": "Which system the time came from (KRA, Tasks, Day Plan, Journeys, Leads, Tickets)"},
            {"name": "Activity", "description": "Specific activity or task name"},
            {"name": "Time Logged", "description": "Duration spent on the activity"},
            {"name": "Approved Minutes", "description": "Time approved by your manager"},
            {"name": "Status", "description": "Auto-synced, Submitted, Approved, Rejected"}
        ],
        "statuses": [
            {"status": "Auto-Synced", "meaning": "Time automatically pulled from source systems", "color": "#dbeafe"},
            {"status": "Submitted", "meaning": "You've submitted for approval", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Manager has approved this entry", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Manager rejected - check comments", "color": "#fee2e2"}
        ],
        "tips": [
            "Review auto-synced entries daily - they come from your KRA, task, and journey updates",
            "Time logged in Task Planner, KRA, and Tasks auto-appears here",
            "Submit your timesheet on time for the approval cycle"
        ],
        "common_mistakes": [
            "Not logging time in source systems - nothing appears here to submit",
            "Submitting without reviewing auto-synced entries for accuracy"
        ]
    },

    "staff_timesheet_approval": {
        "purpose": "Review and approve timesheets submitted by your team members. Approve, reject, or adjust individual time entries.",
        "who_can_access": "Managers and authorized Timesheet Approvers",
        "main_sections": [
            {"name": "Pending Approvals", "description": "Timesheets waiting for your review"},
            {"name": "Team Timesheet View", "description": "Overview of all team members' timesheet status"},
            {"name": "Entry-Level Approval", "description": "Approve/reject individual time entries within a timesheet"}
        ],
        "usage_flow": [
            "Open Timesheet Approval page",
            "See list of team members with pending timesheets",
            "Click on a member to review their detailed entries",
            "Review each time entry - source, activity, duration",
            "Approve valid entries, reject questionable ones with comments",
            "Approved time reflects in the employee's progress dashboard"
        ],
        "fields": [],
        "statuses": [
            {"status": "Pending", "meaning": "Waiting for your review", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Time entry accepted", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Time entry rejected with comments", "color": "#fee2e2"}
        ],
        "tips": [
            "Cross-reference timesheet entries with journey logs and task updates for verification",
            "Approve timesheets within the designated cycle to avoid payroll delays"
        ],
        "common_mistakes": [
            "Bulk approving without reviewing individual entries",
            "Not adding rejection reasons - employees can't correct without feedback"
        ]
    },

    "staff_my_journeys": {
        "purpose": "Track and log your field visits/travel with GPS recording, distance calculation, and transport mode. Each journey auto-syncs time to your timesheet.",
        "who_can_access": "All Staff Members with Journey access",
        "main_sections": [
            {"name": "Active Journey", "description": "Currently running journey with live GPS tracking"},
            {"name": "Journey List", "description": "All your past journeys with distance, time, and route"},
            {"name": "Start Journey", "description": "Begin a new field visit with GPS recording"}
        ],
        "usage_flow": [
            "Open My Journeys page",
            "Click 'Start Journey' before leaving for a field visit",
            "Select transport mode (bike, car, public transport, etc.)",
            "Select the company context for billing",
            "GPS records your route automatically while journey is active",
            "Click 'End Journey' when you arrive back",
            "Journey time auto-syncs to your timesheet",
            "Add visit notes and expense details if applicable"
        ],
        "fields": [
            {"name": "Start Location", "description": "GPS-detected starting point"},
            {"name": "End Location", "description": "GPS-detected destination"},
            {"name": "Distance", "description": "Total kilometers traveled"},
            {"name": "Duration", "description": "Total travel time"},
            {"name": "Transport Mode", "description": "Bike, Car, Public Transport, Walking, etc."},
            {"name": "Company", "description": "Which company this journey is billed to"}
        ],
        "statuses": [
            {"status": "Active", "meaning": "Journey is currently in progress", "color": "#dbeafe"},
            {"status": "Completed", "meaning": "Journey finished successfully", "color": "#dcfce7"},
            {"status": "Cancelled", "meaning": "Journey was cancelled", "color": "#fee2e2"}
        ],
        "tips": [
            "Always start the journey BEFORE you leave - late starts lose GPS data",
            "Keep GPS/location services enabled on your phone during the journey",
            "End the journey when you arrive - don't leave it running"
        ],
        "common_mistakes": [
            "Starting journey after already traveling - GPS misses the route",
            "Forgetting to end the journey - it keeps recording",
            "Not selecting the correct company for billing"
        ]
    },

    "staff_team_journeys": {
        "purpose": "Monitor all journeys taken by your team members. View routes, distances, and durations for oversight.",
        "who_can_access": "Managers and Supervisors (for their team)",
        "main_sections": [
            {"name": "Team Journey List", "description": "All journeys by team members with filters"},
            {"name": "Map View", "description": "Visual representation of journey routes"},
            {"name": "Summary", "description": "Total distance and time by team member"}
        ],
        "usage_flow": [
            "Open Team Journeys page",
            "Filter by date range and team member",
            "Review journey details - route, distance, duration",
            "Check for any anomalies in distance or timing"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Review team journeys weekly to ensure route efficiency"],
        "common_mistakes": []
    },

    "staff_all_journeys": {
        "purpose": "Organization-wide journey records accessible to authorized managers for comprehensive travel oversight.",
        "who_can_access": "Senior Managers and HR with full journey access",
        "main_sections": [
            {"name": "All Journeys Grid", "description": "Every journey across the organization"},
            {"name": "Advanced Filters", "description": "Filter by employee, department, date, distance, and transport mode"},
            {"name": "Export", "description": "Download journey data for analysis"}
        ],
        "usage_flow": [
            "Open All Journeys page",
            "Apply filters to find specific journeys",
            "Review journey details and routes",
            "Export data for reporting or reimbursement processing"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Use this for monthly travel expense reconciliation"],
        "common_mistakes": []
    },

    "staff_vgk4u_journeys": {
        "purpose": "Specialized journey dashboard for VGK4U-related field visits with company-specific tracking and billing.",
        "who_can_access": "Staff with VGK4U journey access",
        "main_sections": [
            {"name": "VGK4U Journey List", "description": "Journeys specifically for VGK4U operations"},
            {"name": "Distance & Billing", "description": "Transport-wise distance with rate calculation"}
        ],
        "usage_flow": [
            "Open VGK4U Journeys dashboard",
            "View journeys tagged to VGK4U operations",
            "Review distance calculations and billing rates"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Ensure you select the correct company when starting VGK4U journeys"],
        "common_mistakes": []
    },

    "staff_my_location_history": {
        "purpose": "View your own GPS location history on a map. Shows recorded locations during work hours for self-verification.",
        "who_can_access": "All Staff Members (own history only)",
        "main_sections": [
            {"name": "Map View", "description": "Your location points plotted on a map for selected date"},
            {"name": "Timeline", "description": "Chronological list of location captures with timestamps"}
        ],
        "usage_flow": [
            "Open My Location History page",
            "Select a date to view",
            "See your location points on the map",
            "Click on points to see exact timestamps"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Use this to verify your journey routes and field visit records"],
        "common_mistakes": []
    },

    "staff_team_location_tracker": {
        "purpose": "Monitor the current and historical locations of your team members on a map for field staff oversight.",
        "who_can_access": "Managers and Supervisors (for their direct reports)",
        "main_sections": [
            {"name": "Live Map", "description": "Current locations of team members on a map"},
            {"name": "History View", "description": "Historical location trails for selected date"},
            {"name": "Employee Selector", "description": "Choose specific team members to track"}
        ],
        "usage_flow": [
            "Open Team Location Tracker",
            "View current positions of all team members on the map",
            "Click on a member to see their movement trail",
            "Use date picker for historical location data"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Check live locations when coordinating field team deployments"],
        "common_mistakes": []
    },

    "staff_accounts_my_reimbursements": {
        "purpose": "Submit expense reimbursement claims with receipt uploads. Track claim status through the approval pipeline.",
        "who_can_access": "All Staff Members",
        "main_sections": [
            {"name": "Submit Claim", "description": "Form to create a new reimbursement request"},
            {"name": "My Claims", "description": "List of all your submitted claims with status"},
            {"name": "Upload Receipts", "description": "Attach receipt images/documents to claims"}
        ],
        "usage_flow": [
            "Open My Reimbursement Claims page",
            "Click 'New Claim' to submit a new expense",
            "Fill in expense details: date, amount, category, description",
            "Upload receipt/bill image",
            "Submit the claim for approval",
            "Track status in your claims list"
        ],
        "fields": [
            {"name": "Expense Date", "description": "When the expense was incurred"},
            {"name": "Amount", "description": "Total expense amount"},
            {"name": "Category", "description": "Type of expense (travel, food, stationery, etc.)"},
            {"name": "Receipt", "description": "Upload photo/scan of the bill"},
            {"name": "Description", "description": "Brief explanation of the expense"}
        ],
        "statuses": [
            {"status": "Submitted", "meaning": "Claim submitted, waiting for review", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Claim approved for payment", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Claim rejected - check comments", "color": "#fee2e2"},
            {"status": "Paid", "meaning": "Reimbursement processed to your account", "color": "#dbeafe"}
        ],
        "tips": [
            "Submit claims promptly - delayed claims may be rejected",
            "Always attach clear receipt images",
            "Add descriptive notes for unusual expenses"
        ],
        "common_mistakes": [
            "Submitting without receipt attachments",
            "Not categorizing expenses correctly",
            "Delayed submissions beyond the claim window"
        ]
    },

    "staff_accounts_reimbursement_approvals": {
        "purpose": "Review and approve/reject expense reimbursement claims submitted by team members.",
        "who_can_access": "Managers, Finance team, and authorized approvers",
        "main_sections": [
            {"name": "Pending Claims", "description": "Claims waiting for your approval"},
            {"name": "Claim Review", "description": "Detailed view with receipts and expense details"},
            {"name": "Approval History", "description": "Past claims you've processed"}
        ],
        "usage_flow": [
            "Open Reimbursement Approvals page",
            "Review pending claims from your team",
            "Verify receipt images and expense details",
            "Approve valid claims or reject with explanation",
            "Approved claims go to finance for payment processing"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Verify receipts match the claimed amounts before approving"],
        "common_mistakes": []
    },

    "staff_service_tickets_dashboard": {
        "purpose": "Central dashboard for EV service ticket management. Shows ticket pipeline, performance metrics, and quick actions.",
        "who_can_access": "Service team staff and managers",
        "main_sections": [
            {"name": "Ticket Summary", "description": "Cards showing open, in-progress, completed, and overdue tickets"},
            {"name": "Recent Tickets", "description": "Latest tickets with quick status updates"},
            {"name": "Performance Charts", "description": "Resolution time, SLA compliance, and workload distribution"}
        ],
        "usage_flow": [
            "Open Service Dashboard",
            "Review summary cards for quick status overview",
            "Check overdue tickets that need immediate attention",
            "Review performance metrics and SLA compliance"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Check the dashboard at start and end of each day"],
        "common_mistakes": []
    },

    "staff_service_tickets_raise": {
        "purpose": "Create a new EV service ticket. Enter vehicle details, complaint description, and assign to the appropriate service center.",
        "who_can_access": "Staff authorized to raise service tickets",
        "main_sections": [
            {"name": "Ticket Form", "description": "Form with vehicle details, complaint, priority, and assignment"},
            {"name": "Customer Info", "description": "Customer/MNR member details linked to the ticket"},
            {"name": "Spare Parts", "description": "Request spare parts needed for the service"}
        ],
        "usage_flow": [
            "Click 'Raise Ticket' from the Service section",
            "Enter customer/vehicle details",
            "Describe the complaint or service needed",
            "Set priority level",
            "Assign to appropriate service center/technician",
            "Add spare part requests if needed",
            "Submit the ticket"
        ],
        "fields": [
            {"name": "Customer Name", "description": "Name of the vehicle owner"},
            {"name": "Vehicle Details", "description": "Model, registration number, etc."},
            {"name": "Complaint", "description": "Description of the issue or service needed"},
            {"name": "Priority", "description": "Low, Medium, High, Critical"},
            {"name": "Service Center", "description": "Which center will handle this ticket"},
            {"name": "Assigned To", "description": "Technician or team responsible"}
        ],
        "statuses": [
            {"status": "Open", "meaning": "Ticket created, waiting for work to begin", "color": "#dbeafe"},
            {"status": "In Progress", "meaning": "Service work has started", "color": "#fef3c7"},
            {"status": "Waiting Parts", "meaning": "On hold waiting for spare parts", "color": "#e5e7eb"},
            {"status": "Completed", "meaning": "Service work finished", "color": "#dcfce7"},
            {"status": "Closed", "meaning": "Customer confirmed, ticket closed", "color": "#d1d5db"}
        ],
        "tips": [
            "Include as much detail as possible in the complaint description",
            "Set correct priority - Critical for safety issues, Low for cosmetic"
        ],
        "common_mistakes": [
            "Not including vehicle registration/model details",
            "Setting wrong priority level"
        ]
    },

    "staff_service_tickets_queue": {
        "purpose": "View and manage the service ticket queue. Process tickets in order of priority and assignment.",
        "who_can_access": "Service team members and technicians",
        "main_sections": [
            {"name": "Ticket Queue", "description": "Ordered list of tickets assigned to you or your team"},
            {"name": "Filters", "description": "Filter by status, priority, service center, or date"},
            {"name": "Quick Actions", "description": "Update status, add notes, request parts directly from queue"}
        ],
        "usage_flow": [
            "Open Service Queue page",
            "Review tickets assigned to you in priority order",
            "Click on a ticket to update its status",
            "Add service notes as you work",
            "Mark ticket as completed when done"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Process Critical and High priority tickets first"],
        "common_mistakes": []
    },

    "staff_nda_versions": {
        "purpose": "Manage NDA document versions. Create new versions, edit content, and track which version is currently active.",
        "who_can_access": "HR/Legal Administrators",
        "main_sections": [
            {"name": "Version List", "description": "All NDA versions with creation dates and status"},
            {"name": "Active Version", "description": "Currently active NDA that employees must accept"},
            {"name": "Version History", "description": "Track changes between versions"}
        ],
        "usage_flow": [
            "Open NDA Versions page",
            "View all existing NDA versions",
            "Create a new version when NDA terms change",
            "Set the new version as active",
            "Employees will be prompted to accept the new version"
        ],
        "fields": [],
        "statuses": [
            {"status": "Active", "meaning": "Currently enforced NDA version", "color": "#dcfce7"},
            {"status": "Draft", "meaning": "Being prepared, not yet active", "color": "#fef3c7"},
            {"status": "Archived", "meaning": "Previous version, no longer active", "color": "#e5e7eb"}
        ],
        "tips": ["Always create a new version instead of editing the active one"],
        "common_mistakes": []
    },

    "staff_nda_pending": {
        "purpose": "View list of employees who haven't yet accepted the current active NDA. Send reminders and track compliance.",
        "who_can_access": "HR Managers and NDA Administrators",
        "main_sections": [
            {"name": "Pending List", "description": "Employees who haven't accepted the current NDA"},
            {"name": "Send Reminder", "description": "Send notification to pending employees"},
            {"name": "Compliance Stats", "description": "Percentage of employees who have accepted"}
        ],
        "usage_flow": [
            "Open NDA Pending page",
            "Review list of employees who haven't accepted",
            "Send reminders to individuals or in bulk",
            "Monitor compliance percentage"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Follow up promptly - NDA acceptance is a compliance requirement"],
        "common_mistakes": []
    },

    "staff_nda_acceptance_audit": {
        "purpose": "Audit trail of all NDA acceptances with timestamps, IP addresses, and version details for legal compliance.",
        "who_can_access": "HR/Legal Administrators and Auditors",
        "main_sections": [
            {"name": "Acceptance Log", "description": "Complete log of who accepted which NDA version and when"},
            {"name": "Search & Filter", "description": "Find specific acceptance records"},
            {"name": "Export", "description": "Download audit data for compliance reporting"}
        ],
        "usage_flow": [
            "Open NDA Acceptance Audit page",
            "Search for specific employees or date ranges",
            "Review acceptance details including timestamps",
            "Export data for compliance audits"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Export acceptance data quarterly for compliance records"],
        "common_mistakes": []
    },

    "staff_nda_editor": {
        "purpose": "Rich text editor for creating and editing NDA document content with formatting, clauses, and legal terms.",
        "who_can_access": "HR/Legal Administrators authorized to draft NDAs",
        "main_sections": [
            {"name": "Editor", "description": "WYSIWYG editor for NDA content"},
            {"name": "Preview", "description": "Preview how the NDA will appear to employees"},
            {"name": "Save/Publish", "description": "Save draft or publish as new version"}
        ],
        "usage_flow": [
            "Open NDA Editor",
            "Draft or edit NDA content using the rich text editor",
            "Preview the document to check formatting",
            "Save as draft for review",
            "Publish as a new version when approved by legal"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Always have legal review before publishing a new NDA version"],
        "common_mistakes": []
    },

    "staff_departments": {
        "purpose": "Create and manage organizational departments with hierarchy, head assignments, and employee mapping.",
        "who_can_access": "HR Administrators and authorized managers",
        "main_sections": [
            {"name": "Department List", "description": "All departments with head and employee count"},
            {"name": "Create/Edit", "description": "Add new departments or modify existing ones"},
            {"name": "Hierarchy", "description": "Parent-child relationships between departments"}
        ],
        "usage_flow": [
            "Open Department Management page",
            "View all departments and their structure",
            "Add new department with name, code, and department head",
            "Set parent department for hierarchical structure",
            "Assign employees to departments"
        ],
        "fields": [
            {"name": "Department Name", "description": "Name of the department"},
            {"name": "Department Code", "description": "Unique code identifier"},
            {"name": "Department Head", "description": "Employee who leads this department"},
            {"name": "Parent Department", "description": "Which department this falls under (for hierarchy)"}
        ],
        "statuses": [],
        "tips": ["Keep department hierarchy clean - it affects reporting chains across the system"],
        "common_mistakes": []
    },

    "staff_signup_categories": {
        "purpose": "Configure business categories with document requirements and validation rules. Single source of truth for all registration categories.",
        "who_can_access": "System Administrators",
        "main_sections": [
            {"name": "Category List", "description": "All configured signup/business categories"},
            {"name": "Document Requirements", "description": "Required documents per category"},
            {"name": "Validation Rules", "description": "Mobile number and field validation settings"}
        ],
        "usage_flow": [
            "Open Signup Categories page",
            "View all configured categories",
            "Add or edit category details including required documents",
            "Set mobile number validation rules",
            "Categories appear across CRM, leads, and registration flows"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Changes here affect all systems that use business categories"],
        "common_mistakes": []
    },

    "staff_settings": {
        "purpose": "System-wide settings and configuration options for the Staff Portal.",
        "who_can_access": "System Administrators",
        "main_sections": [
            {"name": "General Settings", "description": "Basic system configuration"},
            {"name": "Notification Settings", "description": "Configure alerts and notification channels"},
            {"name": "Feature Toggles", "description": "Enable or disable specific features"}
        ],
        "usage_flow": [
            "Open Settings page",
            "Navigate to the relevant settings section",
            "Make configuration changes",
            "Save changes"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Be careful with settings changes - they affect all users"],
        "common_mistakes": []
    },

    "staff_audit_logs": {
        "purpose": "View system audit trail showing all significant actions performed by staff - logins, data changes, approvals, and deletions.",
        "who_can_access": "System Administrators and Compliance Officers",
        "main_sections": [
            {"name": "Log Feed", "description": "Chronological list of all system actions"},
            {"name": "Search & Filter", "description": "Filter by user, action type, date range, or page"},
            {"name": "Export", "description": "Download audit data for compliance"}
        ],
        "usage_flow": [
            "Open Audit Logs page",
            "Use filters to find specific actions or time periods",
            "Review log entries for suspicious or unauthorized activities",
            "Export logs for compliance audits"
        ],
        "fields": [
            {"name": "Timestamp", "description": "When the action occurred"},
            {"name": "User", "description": "Who performed the action"},
            {"name": "Action", "description": "What was done (login, edit, delete, approve, etc.)"},
            {"name": "Page", "description": "Which page/module the action was on"},
            {"name": "Details", "description": "Additional context about the action"}
        ],
        "statuses": [],
        "tips": ["Review audit logs periodically for security compliance"],
        "common_mistakes": []
    },

    "staff_accounts_balance_sheet": {
        "purpose": "View the consolidated Balance Sheet Dashboard showing assets, liabilities, and equity for each company in the SFMS.",
        "who_can_access": "Finance team and authorized managers",
        "main_sections": [
            {"name": "Balance Sheet View", "description": "Assets, Liabilities, and Equity breakdown"},
            {"name": "Company Selector", "description": "Switch between companies"},
            {"name": "Period Selection", "description": "View for specific financial periods"}
        ],
        "usage_flow": [
            "Open Balance Sheet Dashboard",
            "Select the company and financial period",
            "Review the balance sheet with all account heads",
            "Drill down into specific account categories"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Always verify totals match: Assets = Liabilities + Equity"],
        "common_mistakes": []
    },

    "staff_accounts_income_entries": {
        "purpose": "Record and manage income entries in the financial system. Link to leads, CRM transactions, and revenue categories.",
        "who_can_access": "Finance team and authorized staff",
        "main_sections": [
            {"name": "Income List", "description": "All recorded income entries with filters"},
            {"name": "Add Income", "description": "Form to create a new income entry"},
            {"name": "Verification", "description": "Confirm and verify income records"}
        ],
        "usage_flow": [
            "Open Income Entries page",
            "Click 'Add' to create a new income entry",
            "Fill in amount, category, source, and date",
            "Link to a lead or CRM transaction if applicable",
            "Submit for verification"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Always link income to the correct revenue category and lead"],
        "common_mistakes": []
    },

    "staff_accounts_expense_entries": {
        "purpose": "Record and manage business expense entries. Categorize, attach receipts, and submit for approval.",
        "who_can_access": "Finance team and authorized staff",
        "main_sections": [
            {"name": "Expense List", "description": "All recorded expense entries"},
            {"name": "Add Expense", "description": "Form to create a new expense entry"},
            {"name": "Receipt Upload", "description": "Attach supporting documents"}
        ],
        "usage_flow": [
            "Open Expense Entries page",
            "Click 'Add' to create a new expense",
            "Select expense category, amount, and date",
            "Upload receipt/invoice image",
            "Submit the entry"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Categorize expenses correctly for accurate financial reporting"],
        "common_mistakes": []
    },

    "staff_accounts_purchase_invoices": {
        "purpose": "Manage purchase invoices from vendors. Record, validate, and track payment status for all purchase transactions.",
        "who_can_access": "Finance team, Procurement staff",
        "main_sections": [
            {"name": "Invoice List", "description": "All purchase invoices with payment status"},
            {"name": "Create Invoice", "description": "Record a new purchase invoice"},
            {"name": "Payment Tracking", "description": "Track which invoices are paid, pending, or overdue"}
        ],
        "usage_flow": [
            "Open Purchase Invoices page",
            "Create a new invoice with vendor, items, and amounts",
            "Validate GST/HSN details",
            "Submit for approval",
            "Track payment status"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Verify HSN codes and GST rates before submitting"],
        "common_mistakes": []
    },

    "staff_accounts_sales_invoices": {
        "purpose": "Create and manage sales invoices for customers. Generate GST-compliant invoices with automatic numbering.",
        "who_can_access": "Finance team and Sales staff",
        "main_sections": [
            {"name": "Invoice List", "description": "All sales invoices with collection status"},
            {"name": "Create Invoice", "description": "Generate a new sales invoice"},
            {"name": "Collection Tracking", "description": "Track which invoices are collected"}
        ],
        "usage_flow": [
            "Open Sales Invoices page",
            "Create a new invoice with customer and item details",
            "System auto-generates invoice number",
            "Verify GST calculations",
            "Submit and send to customer"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Always verify GST amounts before sending invoices to customers"],
        "common_mistakes": []
    },

    "staff_accounts_fund_allocations": {
        "purpose": "Manage fund allocations between accounts and companies. Track budget utilization and transfers.",
        "who_can_access": "Finance Managers",
        "main_sections": [
            {"name": "Allocation List", "description": "All fund allocation records"},
            {"name": "Create Allocation", "description": "Set up a new fund allocation"},
            {"name": "Utilization Report", "description": "Track how allocated funds are being used"}
        ],
        "usage_flow": [
            "Open Fund Allocations page",
            "Create new allocation specifying source, destination, and amount",
            "Submit for approval",
            "Track utilization against allocation"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Ensure allocations are backed by approved budgets"],
        "common_mistakes": []
    },

    "staff_accounts_payables": {
        "purpose": "Track and manage all outstanding payments to vendors and suppliers. Monitor aging and payment schedules.",
        "who_can_access": "Finance team",
        "main_sections": [
            {"name": "Payable List", "description": "All pending payable amounts vendor-wise"},
            {"name": "Aging Report", "description": "How long payments have been pending"},
            {"name": "Payment Schedule", "description": "Upcoming payment dates"}
        ],
        "usage_flow": [
            "Open Accounts Payable page",
            "Review outstanding payables by vendor",
            "Check aging report for overdue payments",
            "Process payments as per schedule"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Monitor the aging report to avoid payment delays"],
        "common_mistakes": []
    },

    "staff_accounts_receivables": {
        "purpose": "Track all outstanding receivables from customers. Monitor collection progress and aging.",
        "who_can_access": "Finance team",
        "main_sections": [
            {"name": "Receivable List", "description": "All outstanding amounts customer-wise"},
            {"name": "Aging Report", "description": "How long receivables have been pending"},
            {"name": "Collection Status", "description": "Payment collection tracking"}
        ],
        "usage_flow": [
            "Open Accounts Receivable page",
            "Review outstanding receivables by customer",
            "Check aging report for overdue collections",
            "Follow up on overdue amounts"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Follow up on receivables older than 30 days"],
        "common_mistakes": []
    },

    "staff_accounts_party_ledger": {
        "purpose": "View detailed transaction ledger for any party (customer/vendor) showing all debits, credits, and running balance.",
        "who_can_access": "Finance team and authorized managers",
        "main_sections": [
            {"name": "Party Selector", "description": "Choose the party to view"},
            {"name": "Transaction Ledger", "description": "Chronological list of all transactions"},
            {"name": "Balance Summary", "description": "Current outstanding balance"}
        ],
        "usage_flow": [
            "Open Party Ledger page",
            "Select the party (customer or vendor)",
            "Review all transactions chronologically",
            "Check the running balance and outstanding amount"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Reconcile party ledger monthly for accurate bookkeeping"],
        "common_mistakes": []
    },

    "staff_accounts_reports": {
        "purpose": "Generate and view financial reports including profit & loss, trial balance, and other SFMS reports.",
        "who_can_access": "Finance team and management",
        "main_sections": [
            {"name": "Report Types", "description": "Select from available report templates"},
            {"name": "Parameters", "description": "Set date range, company, and other filters"},
            {"name": "Report View", "description": "View and export generated reports"}
        ],
        "usage_flow": [
            "Open SFMS Reports page",
            "Select the report type needed",
            "Set parameters (date range, company)",
            "Generate the report",
            "Export as needed (PDF/Excel)"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Generate reports at month-end for financial review"],
        "common_mistakes": []
    },

    "staff_partners_orders": {
        "purpose": "Manage orders from official business partners (Dealers/Distributors). View, process, and track partner purchase orders.",
        "who_can_access": "Partner Management team and authorized staff",
        "main_sections": [
            {"name": "Order List", "description": "All partner orders with status and amounts"},
            {"name": "Order Detail", "description": "Full order with items, quantities, and pricing"},
            {"name": "Order Lifecycle", "description": "Track order from creation to delivery"}
        ],
        "usage_flow": [
            "Open Partner Orders page",
            "View incoming orders from partners",
            "Review order details - items, quantities, pricing",
            "Process the order through the approval pipeline",
            "Track fulfillment and delivery"
        ],
        "fields": [],
        "statuses": [
            {"status": "New", "meaning": "Order just received", "color": "#dbeafe"},
            {"status": "Approved", "meaning": "Order approved for processing", "color": "#dcfce7"},
            {"status": "In Fulfillment", "meaning": "Being prepared for dispatch", "color": "#fef3c7"},
            {"status": "Dispatched", "meaning": "Shipped to the partner", "color": "#e9d5ff"},
            {"status": "Delivered", "meaning": "Successfully delivered", "color": "#dcfce7"},
            {"status": "Cancelled", "meaning": "Order cancelled", "color": "#fee2e2"}
        ],
        "tips": ["Process new orders within 24 hours"],
        "common_mistakes": []
    },

    "staff_inventory_bom": {
        "purpose": "Manage Bill of Materials - define components and sub-assemblies needed to build/assemble products.",
        "who_can_access": "Inventory Managers and Production staff",
        "main_sections": [
            {"name": "BOM List", "description": "All defined bills of materials"},
            {"name": "BOM Detail", "description": "Components, quantities, and costs for each product"},
            {"name": "Create/Edit", "description": "Define new BOMs or modify existing ones"}
        ],
        "usage_flow": [
            "Open Bill of Materials page",
            "View existing BOMs for products",
            "Create new BOM with component list and quantities",
            "Set cost and procurement details for each component",
            "Save and use in manufacturing orders"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Keep BOMs updated when component specifications change"],
        "common_mistakes": []
    },

    "staff_inventory_stock_items": {
        "purpose": "Master catalog of all stock items with specifications, pricing, and inventory levels across locations.",
        "who_can_access": "Inventory team and authorized staff",
        "main_sections": [
            {"name": "Item Catalog", "description": "Searchable list of all stock items"},
            {"name": "Item Detail", "description": "Full specifications, pricing, and stock levels"},
            {"name": "Add/Edit Item", "description": "Create or modify stock items"}
        ],
        "usage_flow": [
            "Open Stock Items page",
            "Search for items by name, code, or category",
            "View item details including current stock levels",
            "Add new items with specifications and pricing"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Keep item specifications and pricing updated"],
        "common_mistakes": []
    },

    "staff_inventory_stock_ledger": {
        "purpose": "View detailed stock movement ledger showing all inflows (purchases, returns) and outflows (sales, consumption) for each item.",
        "who_can_access": "Inventory Managers",
        "main_sections": [
            {"name": "Item Selector", "description": "Choose the stock item to view"},
            {"name": "Movement Ledger", "description": "Chronological list of all stock movements"},
            {"name": "Running Balance", "description": "Current stock quantity"}
        ],
        "usage_flow": [
            "Open Stock Ledger page",
            "Select the stock item",
            "View all movements with dates and quantities",
            "Check the running balance"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Reconcile stock ledger with physical inventory periodically"],
        "common_mistakes": []
    },

    "staff_inventory_stock_validation": {
        "purpose": "Conduct periodic physical stock counts and validate against system records. Record discrepancies and adjustments.",
        "who_can_access": "Inventory Managers and Auditors",
        "main_sections": [
            {"name": "Validation Sessions", "description": "Create and manage stock count sessions"},
            {"name": "Count Entry", "description": "Enter physical count quantities"},
            {"name": "Discrepancy Report", "description": "System vs physical count comparison"}
        ],
        "usage_flow": [
            "Open Stock Validation page",
            "Create a new validation session",
            "Enter physical count for each item",
            "System compares with book stock",
            "Review and reconcile discrepancies",
            "Approve adjustments"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Conduct stock validation at least quarterly"],
        "common_mistakes": []
    },

    "staff_payroll_profiles": {
        "purpose": "Manage payroll profiles for employees - salary structure, components, deductions, and employment type (ONROLE/OFFROLE).",
        "who_can_access": "HR/Payroll Administrators",
        "main_sections": [
            {"name": "Profile List", "description": "All employee payroll profiles"},
            {"name": "Salary Structure", "description": "Component-wise salary breakdown"},
            {"name": "Create/Edit Profile", "description": "Set up or modify payroll profile"}
        ],
        "usage_flow": [
            "Open Payroll Profiles page",
            "Search for an employee's payroll profile",
            "View or edit salary structure with components (Basic, HRA, DA, etc.)",
            "Set deductions (PF, ESI, TDS, etc.)",
            "Mark employment type: ONROLE or OFFROLE"
        ],
        "fields": [
            {"name": "Employment Type", "description": "ONROLE (full-time with benefits) or OFFROLE (consultant/contract)"},
            {"name": "CTC", "description": "Cost to Company - total annual package"},
            {"name": "Salary Components", "description": "Basic, HRA, DA, Special Allowance, etc."},
            {"name": "Deductions", "description": "PF, ESI, Professional Tax, TDS, etc."}
        ],
        "statuses": [],
        "tips": ["Verify salary structures comply with statutory requirements"],
        "common_mistakes": []
    },

    "staff_payroll_runs": {
        "purpose": "Execute payroll processing for a specific period. Calculate salaries, apply deductions, and generate payslips.",
        "who_can_access": "Payroll Administrators",
        "main_sections": [
            {"name": "Payroll Run List", "description": "All payroll runs with status"},
            {"name": "Run Details", "description": "Employee-wise salary calculations"},
            {"name": "Generate Payslips", "description": "Create payslip documents"}
        ],
        "usage_flow": [
            "Open Payroll Runs page",
            "Create a new payroll run for the period",
            "System auto-calculates based on attendance, leaves, and salary profiles",
            "Review calculations for each employee",
            "Submit for approval",
            "Generate payslips after approval"
        ],
        "fields": [],
        "statuses": [
            {"status": "Draft", "meaning": "Being prepared, not finalized", "color": "#fef3c7"},
            {"status": "Submitted", "meaning": "Sent for approval", "color": "#dbeafe"},
            {"status": "Approved", "meaning": "Approved for processing", "color": "#dcfce7"},
            {"status": "Processed", "meaning": "Salaries disbursed", "color": "#d1d5db"}
        ],
        "tips": ["Always reconcile attendance data before running payroll"],
        "common_mistakes": []
    },

    "staff_incentives_points": {
        "purpose": "Track MNR Points earned by members through deliverables. Generate unique receipt numbers and manage point allocations.",
        "who_can_access": "Staff with VGK4U member earnings access",
        "main_sections": [
            {"name": "Points Overview", "description": "Summary of points distributed"},
            {"name": "User Deliverables", "description": "Deliverables linked to point earnings"},
            {"name": "Receipt Generation", "description": "Generate unique receipt numbers for point transactions"}
        ],
        "usage_flow": [
            "Open MNR Points / User Deliverables page",
            "View point allocation summary",
            "Review deliverable submissions",
            "Generate receipt numbers for approved transactions"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Verify deliverables before approving point allocations"],
        "common_mistakes": []
    },

    "staff_incentives_approvals": {
        "purpose": "Review and approve incentive claims and point allocations submitted by members or auto-generated by the system.",
        "who_can_access": "Authorized Incentive Approvers",
        "main_sections": [
            {"name": "Pending Approvals", "description": "Incentive claims waiting for review"},
            {"name": "Approval History", "description": "Past approved/rejected claims"},
            {"name": "Bulk Actions", "description": "Approve or reject multiple items at once"}
        ],
        "usage_flow": [
            "Open Incentive Approvals page",
            "Review pending incentive claims",
            "Verify eligibility and amounts",
            "Approve or reject with comments",
            "Approved incentives get processed for payment"
        ],
        "fields": [],
        "statuses": [
            {"status": "Pending", "meaning": "Waiting for review", "color": "#fef3c7"},
            {"status": "Approved", "meaning": "Incentive approved for payment", "color": "#dcfce7"},
            {"status": "Rejected", "meaning": "Incentive claim denied", "color": "#fee2e2"}
        ],
        "tips": ["Verify eligibility criteria before approving"],
        "common_mistakes": []
    },

    "staff_zynova_real_estate": {
        "purpose": "Manage VGK4U Real Estate (VGK Real Dreams - ZR) program members, their earnings, and property-linked benefits.",
        "who_can_access": "Staff with VGK4U Real Estate access",
        "main_sections": [
            {"name": "ZR Member List", "description": "All members enrolled in the Real Estate program"},
            {"name": "Earnings", "description": "Property-linked earnings and commissions"},
            {"name": "Status Tracking", "description": "Program membership and activity status"}
        ],
        "usage_flow": [
            "Open VGK Real Dreams (ZR) page",
            "View Real Estate program members",
            "Review member earnings and property linkages",
            "Track program activity status"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Cross-reference with property marketplace for active listings"],
        "common_mistakes": []
    },

    "staff_zynova_insurance": {
        "purpose": "Manage VGK4U Insurance (VGK Care - ZC) program members, policy details, and insurance-linked benefits.",
        "who_can_access": "Staff with VGK4U Insurance access",
        "main_sections": [
            {"name": "ZC Member List", "description": "All members enrolled in the Insurance program"},
            {"name": "Policy Details", "description": "Insurance policy information and coverage"},
            {"name": "Benefits Tracking", "description": "Insurance-linked member benefits"}
        ],
        "usage_flow": [
            "Open VGK Care (ZC) page",
            "View Insurance program members",
            "Review policy details and coverage",
            "Track member benefits and claims"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Ensure policy details are always up to date"],
        "common_mistakes": []
    },

    "staff_call_management": {
        "purpose": "Track and manage staff phone calls including call logs, recordings, and call performance analytics.",
        "who_can_access": "Staff with call tracking enabled and their managers",
        "main_sections": [
            {"name": "Call Log", "description": "List of all calls made/received with duration and outcomes"},
            {"name": "Recordings", "description": "Access call recordings for training and quality"},
            {"name": "Analytics", "description": "Call volume, duration, and performance metrics"}
        ],
        "usage_flow": [
            "Open Call Tracking Dashboard",
            "View your recent call log",
            "Review call recordings for quality assurance",
            "Check analytics for call performance"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Log call outcomes for better lead tracking"],
        "common_mistakes": []
    },

    "staff_coupon_status": {
        "purpose": "View and track EV coupon status including allocation, redemption, and benefit utilization for MNR members.",
        "who_can_access": "Staff with coupon management access",
        "main_sections": [
            {"name": "Coupon Overview", "description": "Summary of coupon allocations and redemptions"},
            {"name": "Status Tracking", "description": "Individual coupon lifecycle tracking"},
            {"name": "Benefit Details", "description": "6 benefits linked to each coupon"}
        ],
        "usage_flow": [
            "Open Coupon Status page",
            "View coupon allocation summary",
            "Search for specific coupons by member or code",
            "Track benefit redemption progress"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Monitor redemption rates to identify unused benefits"],
        "common_mistakes": []
    },

    "staff_offboarding": {
        "purpose": "Manage the employee separation/offboarding process including exit checklists, knowledge transfer, and final settlements.",
        "who_can_access": "HR Managers and authorized administrators",
        "main_sections": [
            {"name": "Offboarding Queue", "description": "Employees in the separation process"},
            {"name": "Exit Checklist", "description": "Items to complete before final separation"},
            {"name": "Final Settlement", "description": "Calculate and process final dues"}
        ],
        "usage_flow": [
            "Open Employee Offboarding page",
            "Initiate offboarding for a departing employee",
            "Complete exit checklist items (asset return, knowledge transfer, etc.)",
            "Process final settlement calculations",
            "Close the offboarding process"
        ],
        "fields": [],
        "statuses": [
            {"status": "Initiated", "meaning": "Offboarding process started", "color": "#fef3c7"},
            {"status": "In Progress", "meaning": "Checklist items being completed", "color": "#dbeafe"},
            {"status": "Completed", "meaning": "All steps done, employee separated", "color": "#dcfce7"}
        ],
        "tips": ["Start offboarding process on the first day of notice period"],
        "common_mistakes": []
    },

    "staff_manager_review": {
        "purpose": "Manager dashboard for reviewing team member performance, approvals, and overall team health.",
        "who_can_access": "Managers and Team Leaders",
        "main_sections": [
            {"name": "Team Overview", "description": "Summary of all direct reports and their status"},
            {"name": "Pending Actions", "description": "Items waiting for your approval across all modules"},
            {"name": "Performance Summary", "description": "Team performance metrics"}
        ],
        "usage_flow": [
            "Open Manager Review dashboard",
            "Check pending approvals across all modules",
            "Review team member performance",
            "Process any pending actions"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Check this dashboard daily to stay on top of pending approvals"],
        "common_mistakes": []
    },

    "staff_mnr_announcements_view": {
        "purpose": "View community announcements and updates published for staff members. Includes media attachments and engagement features.",
        "who_can_access": "All Staff Members",
        "main_sections": [
            {"name": "Announcement Feed", "description": "Latest announcements with media content"},
            {"name": "Engagement", "description": "Like, comment, and share announcements"},
            {"name": "Filters", "description": "Filter by date, category, or type"}
        ],
        "usage_flow": [
            "Open View Announcements page",
            "Browse latest announcements",
            "Click on an announcement to see full content and media",
            "Engage with announcements through likes and comments"
        ],
        "fields": [],
        "statuses": [],
        "tips": ["Check announcements regularly for important company updates"],
        "common_mistakes": []
    },

    "staff_timesheet": {
        "purpose": "Quick-access timesheet view in the Progress section showing today's time breakdown across all activity sources.",
        "who_can_access": "All staff members",
        "main_sections": ["Time Breakdown Chart", "Source System Tags", "Daily Total"],
        "usage_flow": ["View auto-calculated time entries", "Check breakdown by KRA/Task/DayPlan/Journey/Lead/Ticket", "Review daily total against expected hours"],
        "fields": [{"name": "Total Minutes", "description": "Sum of all activity time for today"}, {"name": "Source", "description": "Which system generated the time entry"}],
        "statuses": [],
        "tips": ["Use this for a quick daily overview — go to My Timesheet for detailed editing"],
        "common_mistakes": ["Confusing this summary view with the full timesheet management page"]
    },

    "staff_kra_status": {
        "purpose": "Quick-access KRA completion status in the Progress section showing current period KRA progress.",
        "who_can_access": "All staff members",
        "main_sections": ["KRA Progress Bar", "Completion Percentage", "Pending Items"],
        "usage_flow": ["View current KRA completion percentage", "Identify pending KRA items", "Click through to full KRA management"],
        "fields": [{"name": "Completion %", "description": "Percentage of KRA targets achieved"}, {"name": "Period", "description": "Current KRA review period"}],
        "statuses": [],
        "tips": ["Check this daily to stay on track with your KRA targets"],
        "common_mistakes": ["Not clicking through to update KRA progress regularly"]
    },

    "staff_change_password": {
        "purpose": "Change your staff portal login password. Enforces password complexity requirements.",
        "who_can_access": "All staff members (own password only)",
        "main_sections": ["Current Password Field", "New Password Field", "Confirm Password", "Strength Indicator"],
        "usage_flow": ["Enter current password", "Enter new password meeting complexity rules", "Confirm new password", "Click Change Password"],
        "fields": [{"name": "Current Password", "description": "Your existing password for verification"}, {"name": "New Password", "description": "Must meet minimum length, uppercase, lowercase, number, special character requirements"}],
        "statuses": [],
        "tips": ["Change password every 90 days for security", "Use a password manager to generate strong passwords"],
        "common_mistakes": ["Using a password that doesn't meet complexity requirements", "Forgetting to update saved passwords in browsers"]
    },

    "staff_2fa_settings": {
        "purpose": "Configure two-factor authentication for enhanced account security.",
        "who_can_access": "All staff members (own account)",
        "main_sections": ["2FA Status", "Setup QR Code", "Backup Codes", "Enable/Disable Toggle"],
        "usage_flow": ["Click Enable 2FA", "Scan QR code with authenticator app", "Enter verification code to confirm", "Save backup codes securely"],
        "fields": [{"name": "Verification Code", "description": "6-digit code from authenticator app"}, {"name": "Backup Codes", "description": "One-time use codes for account recovery"}],
        "statuses": [{"name": "Enabled", "description": "2FA is active on your account"}, {"name": "Disabled", "description": "2FA is not active — less secure"}],
        "tips": ["Always save backup codes in a secure location", "Use apps like Google Authenticator or Authy"],
        "common_mistakes": ["Not saving backup codes before enabling 2FA", "Losing access to authenticator app without backup codes"]
    },

    "staff_attendance_computation": {
        "purpose": "Automated attendance computation engine that calculates working hours, overtime, and attendance summaries for payroll processing.",
        "who_can_access": "HR Admin, Payroll Admin",
        "main_sections": ["Computation Period Selector", "Employee List", "Computation Results", "Override Panel", "Export"],
        "usage_flow": ["Select computation period (month)", "Run computation for all employees", "Review calculated hours and exceptions", "Override specific entries if needed", "Lock computation for payroll"],
        "fields": [{"name": "Working Days", "description": "Total working days in the period"}, {"name": "Present Days", "description": "Days marked as present"}, {"name": "Overtime Hours", "description": "Hours beyond standard working hours"}, {"name": "Loss of Pay Days", "description": "Absent days without approved leave"}],
        "statuses": [{"name": "Pending", "description": "Computation not yet run"}, {"name": "Computed", "description": "Calculation complete, ready for review"}, {"name": "Locked", "description": "Locked for payroll processing"}],
        "tips": ["Always review exception cases before locking", "Run computation after all attendance corrections are made"],
        "common_mistakes": ["Locking computation before all leave approvals are processed", "Not accounting for mid-month joiners"]
    },

    "rvz_crm_leads": {
        "purpose": "Supreme Admin CRM lead management view with full access to all leads across all companies and categories.",
        "who_can_access": "Supreme Admin, RVZ Admin",
        "main_sections": ["All Leads Table", "Company Filter", "Category Filter", "Pipeline View", "Bulk Actions", "Analytics"],
        "usage_flow": ["View all leads across companies", "Filter by company, category, or handler", "Reassign leads between handlers", "Monitor pipeline conversion rates", "Export lead data"],
        "fields": [{"name": "Lead Name", "description": "Contact name"}, {"name": "Company", "description": "DC Protocol company assignment"}, {"name": "Category", "description": "Business category from signup categories"}, {"name": "Handler", "description": "Assigned staff/partner/member"}],
        "statuses": [{"name": "New", "description": "Freshly created lead"}, {"name": "Contacted", "description": "Initial contact made"}, {"name": "Qualified", "description": "Lead meets criteria"}, {"name": "Converted", "description": "Successfully converted"}],
        "tips": ["Use company filter to focus on specific business units", "Monitor conversion rates to identify top performers"],
        "common_mistakes": ["Reassigning leads without notifying the current handler"]
    },

    "staff_tasks_team_activities": {
        "purpose": "View and manage team activities and task assignments across your team members.",
        "who_can_access": "Managers, Team Leads",
        "main_sections": ["Team Activity Feed", "Task Distribution Chart", "Member Workload", "Overdue Tasks"],
        "usage_flow": ["View all team member activities", "Check task distribution and workload balance", "Identify overdue tasks", "Reassign tasks if needed"],
        "fields": [{"name": "Team Member", "description": "Employee name and role"}, {"name": "Active Tasks", "description": "Number of tasks in progress"}, {"name": "Completed Today", "description": "Tasks completed in current day"}],
        "statuses": [],
        "tips": ["Review daily to ensure balanced workload across team", "Address overdue tasks promptly"],
        "common_mistakes": ["Not monitoring overdue tasks leading to missed deadlines"]
    },

    "staff_all_location_tracker": {
        "purpose": "Admin view of all employee locations with real-time and historical tracking across the organization.",
        "who_can_access": "HR Admin, Supreme Admin",
        "main_sections": ["Live Map View", "Employee List", "Location History", "Time Filters", "Export"],
        "usage_flow": ["View live locations of all field employees on map", "Click employee pin for details", "Filter by department or date range", "View location history trail"],
        "fields": [{"name": "Employee", "description": "Name and department"}, {"name": "Last Location", "description": "Most recent GPS coordinates"}, {"name": "Last Updated", "description": "Timestamp of last location update"}, {"name": "Status", "description": "Online/Offline/On Journey"}],
        "statuses": [{"name": "Online", "description": "Currently sharing location"}, {"name": "Offline", "description": "Location sharing inactive"}, {"name": "On Journey", "description": "Active journey in progress"}],
        "tips": ["Use this for field team coordination and safety monitoring", "Respect privacy — location data is for operational purposes only"],
        "common_mistakes": ["Using location data for micromanagement rather than operational needs"]
    },

    "staff_team_live_tracker": {
        "purpose": "Real-time live tracking view specifically for your direct team members currently in the field.",
        "who_can_access": "Managers, Team Leads",
        "main_sections": ["Live Map", "Team Member Cards", "Journey Status", "Last Check-in Time"],
        "usage_flow": ["View your team members on live map", "Check who is currently on journeys", "Monitor field visit progress", "Contact team members if needed"],
        "fields": [{"name": "Team Member", "description": "Direct report name"}, {"name": "Current Location", "description": "Live GPS position"}, {"name": "Journey Status", "description": "Active/Completed/Not Started"}, {"name": "ETA", "description": "Estimated time to next checkpoint"}],
        "statuses": [],
        "tips": ["Use for real-time coordination with field teams", "Check before assigning urgent field tasks"],
        "common_mistakes": ["Expecting location updates when employees have GPS disabled"]
    },

    "staff_service_tickets_performance": {
        "purpose": "Performance analytics for service ticket operations — resolution times, SLA compliance, technician efficiency.",
        "who_can_access": "Service Manager, Admin",
        "main_sections": ["KPI Dashboard", "SLA Compliance Chart", "Technician Scorecard", "Resolution Time Trends", "Category Analysis"],
        "usage_flow": ["View overall SLA compliance percentage", "Drill into technician-level performance", "Analyze resolution time by ticket category", "Identify bottlenecks and improvement areas", "Export performance reports"],
        "fields": [{"name": "SLA Compliance %", "description": "Percentage of tickets resolved within SLA"}, {"name": "Avg Resolution Time", "description": "Average hours to resolve tickets"}, {"name": "Tickets per Technician", "description": "Workload distribution metric"}],
        "statuses": [],
        "tips": ["Review weekly to identify trends", "Use technician scorecards for performance reviews"],
        "common_mistakes": ["Focusing only on speed without considering quality of resolution"]
    },

    "staff_service_tickets_procurement": {
        "purpose": "Manage procurement requests generated from service tickets — parts ordering, vendor coordination, and inventory requests.",
        "who_can_access": "Service Manager, Procurement Team, Admin",
        "main_sections": ["Procurement Queue", "Parts Request Form", "Vendor Selection", "Order Tracking", "Cost Summary"],
        "usage_flow": ["Review parts needed from service tickets", "Create procurement request", "Select vendor and get pricing", "Track order delivery", "Update ticket when parts arrive"],
        "fields": [{"name": "Part/Item", "description": "Required component or material"}, {"name": "Quantity", "description": "Number of units needed"}, {"name": "Vendor", "description": "Selected supplier"}, {"name": "Expected Delivery", "description": "Estimated arrival date"}, {"name": "Cost", "description": "Total procurement cost"}],
        "statuses": [{"name": "Requested", "description": "Procurement request submitted"}, {"name": "Approved", "description": "Request approved for ordering"}, {"name": "Ordered", "description": "Order placed with vendor"}, {"name": "Delivered", "description": "Parts received"}, {"name": "Installed", "description": "Parts installed in service"}],
        "tips": ["Link procurement to specific service ticket for traceability", "Compare multiple vendor quotes for cost optimization"],
        "common_mistakes": ["Not checking existing inventory before raising procurement request"]
    },

    "staff_service_tickets_procurement_queue": {
        "purpose": "Queue view for pending procurement requests awaiting approval or processing.",
        "who_can_access": "Procurement Manager, Admin",
        "main_sections": ["Pending Queue", "Priority Sorting", "Approval Actions", "Bulk Processing"],
        "usage_flow": ["Review pending procurement requests", "Prioritize by urgency and ticket SLA", "Approve or reject requests", "Process approved requests in bulk"],
        "fields": [{"name": "Request ID", "description": "Unique procurement request identifier"}, {"name": "Ticket Reference", "description": "Linked service ticket"}, {"name": "Priority", "description": "Urgency level based on ticket SLA"}, {"name": "Amount", "description": "Estimated cost"}],
        "statuses": [{"name": "Pending Approval", "description": "Awaiting manager approval"}, {"name": "Approved", "description": "Ready for ordering"}, {"name": "Rejected", "description": "Request denied with reason"}],
        "tips": ["Process urgent requests first based on ticket SLA deadlines"],
        "common_mistakes": ["Batch approving without reviewing individual request details"]
    },

    "staff_service_tickets_reports": {
        "purpose": "Comprehensive reporting for service ticket operations — volume trends, category distribution, financial impact.",
        "who_can_access": "Service Manager, Admin, Finance",
        "main_sections": ["Volume Reports", "Category Distribution", "Financial Summary", "Customer Satisfaction", "Export Options"],
        "usage_flow": ["Select report type and date range", "View charts and data tables", "Filter by category, technician, or status", "Export reports for presentations"],
        "fields": [{"name": "Report Period", "description": "Date range for report generation"}, {"name": "Ticket Volume", "description": "Total tickets in period"}, {"name": "Revenue", "description": "Service revenue generated"}, {"name": "Cost", "description": "Parts and labor costs"}],
        "statuses": [],
        "tips": ["Generate monthly reports for management review", "Compare periods to identify seasonal trends"],
        "common_mistakes": ["Not filtering by correct date range leading to misleading data"]
    },

    "staff_service_center_revenue": {
        "purpose": "Track and analyze revenue generated by each service center location.",
        "who_can_access": "Service Manager, Finance, Admin",
        "main_sections": ["Revenue Dashboard", "Center-wise Breakdown", "Service Type Revenue", "Monthly Trends", "Target vs Actual"],
        "usage_flow": ["View total revenue across all centers", "Drill into individual center performance", "Compare revenue by service type", "Track against monthly targets"],
        "fields": [{"name": "Service Center", "description": "Location/branch name"}, {"name": "Total Revenue", "description": "Sum of all service charges"}, {"name": "Parts Revenue", "description": "Revenue from parts sales"}, {"name": "Labor Revenue", "description": "Revenue from service labor"}],
        "statuses": [],
        "tips": ["Review weekly to identify underperforming centers early", "Cross-reference with ticket volume for efficiency analysis"],
        "common_mistakes": ["Not accounting for pending invoices in revenue calculations"]
    },

    "rvz_sales_revenue": {
        "purpose": "Sales team revenue tracking dashboard showing team-wise and individual sales performance across all companies.",
        "who_can_access": "Sales Manager, Supreme Admin, RVZ Admin",
        "main_sections": ["Revenue Overview", "Team Performance", "Individual Scorecard", "Pipeline Value", "Monthly Targets"],
        "usage_flow": ["View overall sales revenue", "Drill into team-level performance", "Check individual salesperson metrics", "Monitor pipeline value for forecasting"],
        "fields": [{"name": "Team", "description": "Sales team/department"}, {"name": "Revenue", "description": "Total closed revenue"}, {"name": "Pipeline", "description": "Value of open opportunities"}, {"name": "Conversion Rate", "description": "Lead to customer conversion percentage"}],
        "statuses": [],
        "tips": ["Use pipeline value for revenue forecasting", "Compare conversion rates across teams for training opportunities"],
        "common_mistakes": ["Counting pipeline value as confirmed revenue"]
    },

    "staff_inventory_manufacturing": {
        "purpose": "Track manufacturing processes, work orders, and production scheduling linked to Bill of Materials.",
        "who_can_access": "Inventory Manager, Production Team, Admin",
        "main_sections": ["Work Orders", "Production Schedule", "BOM Requirements", "Output Tracking", "Quality Check"],
        "usage_flow": ["Create work order from BOM", "Schedule production run", "Track material consumption", "Record output quantities", "Perform quality checks"],
        "fields": [{"name": "Work Order", "description": "Production order reference"}, {"name": "BOM Reference", "description": "Linked Bill of Materials"}, {"name": "Input Materials", "description": "Raw materials consumed"}, {"name": "Output Quantity", "description": "Units produced"}, {"name": "Quality Status", "description": "Pass/Fail/Pending"}],
        "statuses": [{"name": "Planned", "description": "Work order created"}, {"name": "In Production", "description": "Manufacturing in progress"}, {"name": "Quality Check", "description": "Awaiting quality verification"}, {"name": "Completed", "description": "Production finished and accepted"}],
        "tips": ["Always verify BOM material availability before starting production", "Record output quantities in real-time"],
        "common_mistakes": ["Starting production without checking raw material stock levels"]
    },

    "staff_inventory_procurement": {
        "purpose": "Manage inventory procurement — purchase requests, vendor selection, and order tracking for stock replenishment.",
        "who_can_access": "Inventory Manager, Procurement Team, Admin",
        "main_sections": ["Purchase Requests", "Vendor Comparison", "Order Pipeline", "Delivery Tracking", "Cost Analysis"],
        "usage_flow": ["Identify items below reorder level", "Create purchase request", "Compare vendor quotes", "Place order with selected vendor", "Track delivery and update stock"],
        "fields": [{"name": "Item", "description": "Stock item requiring procurement"}, {"name": "Current Stock", "description": "Available quantity"}, {"name": "Reorder Level", "description": "Minimum stock threshold"}, {"name": "Order Quantity", "description": "Quantity to order"}, {"name": "Vendor", "description": "Selected supplier"}],
        "statuses": [{"name": "Request Created", "description": "Purchase request submitted"}, {"name": "Approved", "description": "Request approved"}, {"name": "Ordered", "description": "PO sent to vendor"}, {"name": "Received", "description": "Goods received and verified"}],
        "tips": ["Set up automatic reorder alerts for critical items", "Maintain at least 2 vendor options per item category"],
        "common_mistakes": ["Not verifying delivery against purchase order quantities"]
    },

    "staff_inventory_intake": {
        "purpose": "Record incoming inventory from purchases, returns, and transfers. Verify quantities and quality before acceptance.",
        "who_can_access": "Inventory Team, Warehouse Staff, Admin",
        "main_sections": ["Pending Receipts", "Intake Form", "Quality Check", "Quantity Verification", "GRN Generation"],
        "usage_flow": ["Select pending purchase order", "Verify delivered quantities against PO", "Perform quality inspection", "Accept or reject items", "Generate Goods Receipt Note (GRN)"],
        "fields": [{"name": "PO Reference", "description": "Purchase order being received"}, {"name": "Expected Qty", "description": "Quantity as per PO"}, {"name": "Received Qty", "description": "Actual quantity delivered"}, {"name": "Accepted Qty", "description": "Quantity passing quality check"}, {"name": "GRN Number", "description": "Goods Receipt Note reference"}],
        "statuses": [{"name": "Pending Receipt", "description": "Awaiting delivery"}, {"name": "Partially Received", "description": "Some items received"}, {"name": "Fully Received", "description": "All items delivered"}, {"name": "Quality Hold", "description": "Items under inspection"}],
        "tips": ["Always count items before signing delivery receipt", "Document any damaged items with photos"],
        "common_mistakes": ["Accepting delivery without verifying quantities against PO"]
    },

    "staff_inventory_service_center_tracking": {
        "purpose": "Track inventory allocated to and consumed by each service center for repair and maintenance operations.",
        "who_can_access": "Service Manager, Inventory Manager, Admin",
        "main_sections": ["Center-wise Stock", "Consumption Report", "Transfer Requests", "Low Stock Alerts", "Usage Analytics"],
        "usage_flow": ["View stock levels per service center", "Monitor consumption patterns", "Process inter-center transfer requests", "Set up low stock alerts", "Analyze usage trends"],
        "fields": [{"name": "Service Center", "description": "Location/branch"}, {"name": "Item", "description": "Stock item name"}, {"name": "Available Qty", "description": "Current stock at center"}, {"name": "Consumed This Month", "description": "Units used in current month"}, {"name": "Reorder Point", "description": "When to request replenishment"}],
        "statuses": [],
        "tips": ["Review consumption reports monthly to optimize stock levels per center", "Set up automated low stock alerts"],
        "common_mistakes": ["Not recording consumption in real-time leading to stock discrepancies"]
    },

    "staff_inventory_vendor_returns": {
        "purpose": "Manage return of defective or incorrect items to vendors with proper documentation and credit tracking.",
        "who_can_access": "Inventory Manager, Procurement Team, Admin",
        "main_sections": ["Return Requests", "Return Form", "Vendor Communication", "Credit Note Tracking", "Return History"],
        "usage_flow": ["Identify items for return", "Create return request with reason", "Get return authorization from vendor", "Ship items back", "Track credit note receipt"],
        "fields": [{"name": "Return Reason", "description": "Defective/Wrong item/Excess quantity"}, {"name": "Original PO", "description": "Reference purchase order"}, {"name": "Return Qty", "description": "Number of items being returned"}, {"name": "Credit Amount", "description": "Expected credit from vendor"}, {"name": "Return Status", "description": "Current state of return process"}],
        "statuses": [{"name": "Requested", "description": "Return request created"}, {"name": "Authorized", "description": "Vendor approved return"}, {"name": "Shipped", "description": "Items sent back to vendor"}, {"name": "Credit Received", "description": "Credit note applied"}],
        "tips": ["Document defects with photos before returning", "Follow up on credit notes within 30 days"],
        "common_mistakes": ["Returning items without vendor authorization leading to rejection"]
    },

    "staff_inventory_stock_transfers": {
        "purpose": "Manage stock transfers between warehouses, service centers, and locations within the organization.",
        "who_can_access": "Inventory Manager, Warehouse Staff, Admin",
        "main_sections": ["Transfer Requests", "Transfer Form", "In-Transit Tracker", "Receiving Confirmation", "Transfer History"],
        "usage_flow": ["Create transfer request from source location", "Specify items and quantities", "Get approval from both source and destination managers", "Ship and track in transit", "Confirm receipt at destination"],
        "fields": [{"name": "Source Location", "description": "Where items are shipping from"}, {"name": "Destination", "description": "Where items are shipping to"}, {"name": "Items", "description": "Stock items and quantities"}, {"name": "Transfer Reason", "description": "Why transfer is needed"}, {"name": "Tracking", "description": "Shipment tracking details"}],
        "statuses": [{"name": "Requested", "description": "Transfer request submitted"}, {"name": "Approved", "description": "Both locations approved"}, {"name": "In Transit", "description": "Items shipped"}, {"name": "Received", "description": "Destination confirmed receipt"}],
        "tips": ["Always get destination confirmation before marking transfer complete", "Use for balancing stock across locations"],
        "common_mistakes": ["Transferring items without updating source location stock first"]
    },

    "staff_payroll_cycles": {
        "purpose": "Define and manage payroll processing cycles — monthly, bi-weekly, or custom periods with deadline tracking.",
        "who_can_access": "HR Admin, Payroll Admin",
        "main_sections": ["Cycle Calendar", "Active Cycle", "Deadline Tracker", "Cycle Configuration", "History"],
        "usage_flow": ["View current payroll cycle", "Check upcoming deadlines (attendance lock, computation, approval)", "Configure cycle parameters", "Close current cycle and open next"],
        "fields": [{"name": "Cycle Period", "description": "Start and end dates"}, {"name": "Attendance Deadline", "description": "Last date for attendance corrections"}, {"name": "Processing Date", "description": "When payroll computation runs"}, {"name": "Payment Date", "description": "When salaries are paid"}],
        "statuses": [{"name": "Open", "description": "Current active cycle"}, {"name": "Attendance Locked", "description": "No more attendance changes"}, {"name": "Processing", "description": "Payroll being calculated"}, {"name": "Completed", "description": "Salaries processed and paid"}],
        "tips": ["Set calendar reminders for each deadline", "Ensure all leaves are approved before attendance lock"],
        "common_mistakes": ["Missing attendance lock deadline causing payroll delays"]
    },

    "staff_payroll_approvals": {
        "purpose": "Review and approve computed payroll before final payment processing. Multi-level approval chain.",
        "who_can_access": "HR Admin, Finance Manager, Director",
        "main_sections": ["Pending Approvals Queue", "Payroll Summary", "Employee Breakdown", "Variance Report", "Approval Actions"],
        "usage_flow": ["Review computed payroll summary", "Check variance from previous month", "Drill into individual employee details", "Approve or reject with comments", "Forward to next approval level"],
        "fields": [{"name": "Total Gross", "description": "Sum of all employee gross salaries"}, {"name": "Total Deductions", "description": "Sum of all deductions"}, {"name": "Total Net", "description": "Sum of all net payments"}, {"name": "Variance", "description": "Change from previous month"}, {"name": "Head Count", "description": "Number of employees in payroll"}],
        "statuses": [{"name": "Pending Review", "description": "Awaiting first approval"}, {"name": "HR Approved", "description": "HR has reviewed and approved"}, {"name": "Finance Approved", "description": "Finance has verified budgets"}, {"name": "Director Approved", "description": "Final approval for payment"}],
        "tips": ["Always check variance report for unexpected changes", "Verify head count matches active employees"],
        "common_mistakes": ["Approving without checking individual employee calculations"]
    },

    "staff_payroll_consultant_invoices": {
        "purpose": "Manage invoices from OFFROLE consultants and contractors for payment processing through payroll.",
        "who_can_access": "HR Admin, Finance",
        "main_sections": ["Invoice Queue", "Invoice Details", "Verification", "Payment Schedule", "History"],
        "usage_flow": ["Consultant submits invoice", "HR verifies against contract terms", "Finance approves for payment", "Process payment in batch", "Record in SFMS"],
        "fields": [{"name": "Consultant", "description": "Name and contract reference"}, {"name": "Invoice Amount", "description": "Billed amount"}, {"name": "Service Period", "description": "Period covered by invoice"}, {"name": "GST", "description": "GST amount if applicable"}, {"name": "TDS", "description": "Tax deducted at source"}],
        "statuses": [{"name": "Submitted", "description": "Invoice received from consultant"}, {"name": "Verified", "description": "Matched against contract"}, {"name": "Approved", "description": "Ready for payment"}, {"name": "Paid", "description": "Payment processed"}],
        "tips": ["Cross-verify invoice amounts against contract rates", "Ensure correct TDS deduction based on consultant category"],
        "common_mistakes": ["Processing duplicate invoices for same service period"]
    },

    "staff_payroll_allowance_catalog": {
        "purpose": "Define and manage the catalog of allowances available for payroll — HRA, DA, special allowances, etc.",
        "who_can_access": "HR Admin, Payroll Admin",
        "main_sections": ["Allowance List", "Add/Edit Allowance", "Applicability Rules", "Tax Treatment", "History"],
        "usage_flow": ["View all configured allowances", "Add new allowance type with tax rules", "Set applicability (by grade/department/location)", "Configure calculation method (fixed/percentage)", "Activate/deactivate allowances"],
        "fields": [{"name": "Allowance Name", "description": "Name of the allowance component"}, {"name": "Type", "description": "Fixed amount or percentage of basic"}, {"name": "Tax Treatment", "description": "Taxable/Exempt/Partially exempt"}, {"name": "Applicability", "description": "Which employee grades/departments receive this"}],
        "statuses": [{"name": "Active", "description": "Currently in use for payroll"}, {"name": "Inactive", "description": "Deactivated, not applied to new payrolls"}],
        "tips": ["Review allowance catalog annually for compliance with tax law changes", "Document the purpose and eligibility for each allowance"],
        "common_mistakes": ["Not updating tax treatment when tax rules change"]
    },

    "staff_payroll_documents": {
        "purpose": "Manage payroll-related documents — payslips, Form 16, salary certificates, and compliance documents.",
        "who_can_access": "HR Admin, Employees (own documents)",
        "main_sections": ["Document Library", "Payslip Archive", "Form 16 Generator", "Certificate Templates", "Bulk Generation"],
        "usage_flow": ["Select document type", "Choose employee(s) and period", "Generate document", "Review and publish", "Employee downloads from portal"],
        "fields": [{"name": "Document Type", "description": "Payslip/Form 16/Salary Certificate/etc."}, {"name": "Employee", "description": "Target employee"}, {"name": "Period", "description": "Relevant pay period"}, {"name": "Status", "description": "Draft/Published/Downloaded"}],
        "statuses": [{"name": "Generated", "description": "Document created"}, {"name": "Published", "description": "Available for employee download"}, {"name": "Downloaded", "description": "Employee has accessed the document"}],
        "tips": ["Generate Form 16 before the annual deadline", "Bulk generate payslips right after payroll processing"],
        "common_mistakes": ["Publishing payslips before final payroll approval"]
    },

    "staff_partners_pricing": {
        "purpose": "Manage pricing tiers and discount structures for Official Business Partners (Dealers/Distributors/Vendors).",
        "who_can_access": "Partner Manager, Admin, Finance",
        "main_sections": ["Price Lists", "Partner-wise Pricing", "Discount Rules", "Margin Configuration", "Price History"],
        "usage_flow": ["Create or edit price list", "Assign pricing tier to partner", "Configure volume-based discounts", "Set margin requirements", "Publish price list"],
        "fields": [{"name": "Price List Name", "description": "Identifier for the pricing tier"}, {"name": "Base Price", "description": "Standard price per item"}, {"name": "Partner Discount %", "description": "Discount applied for this partner tier"}, {"name": "Volume Discount", "description": "Additional discount for bulk orders"}, {"name": "Effective Date", "description": "When pricing takes effect"}],
        "statuses": [{"name": "Draft", "description": "Under preparation"}, {"name": "Active", "description": "Currently in effect"}, {"name": "Expired", "description": "No longer valid"}],
        "tips": ["Always set an effective date to avoid retroactive pricing issues", "Review pricing quarterly for market competitiveness"],
        "common_mistakes": ["Activating new pricing without deactivating old price list"]
    },

    "staff_partners_approval": {
        "purpose": "Review and approve partner orders before fulfillment. Multi-level approval based on order value.",
        "who_can_access": "Partner Manager, Sales Manager, Admin",
        "main_sections": ["Approval Queue", "Order Summary", "Credit Check", "Approval Chain", "Rejection Form"],
        "usage_flow": ["Review pending partner orders", "Verify credit limit and payment history", "Check inventory availability", "Approve or reject with notes", "Forward large orders to higher approval"],
        "fields": [{"name": "Order ID", "description": "Unique order reference"}, {"name": "Partner", "description": "Ordering business partner"}, {"name": "Order Value", "description": "Total order amount"}, {"name": "Credit Available", "description": "Remaining credit limit"}, {"name": "Approval Level", "description": "Required approval tier based on value"}],
        "statuses": [{"name": "Pending", "description": "Awaiting review"}, {"name": "Approved", "description": "Order approved for processing"}, {"name": "Rejected", "description": "Order declined with reason"}, {"name": "Escalated", "description": "Sent to higher authority"}],
        "tips": ["Always check credit availability before approving", "Escalate orders exceeding your approval limit"],
        "common_mistakes": ["Approving orders beyond partner's credit limit"]
    },

    "staff_partners_routing": {
        "purpose": "Configure order routing rules — which warehouse/location fulfills orders based on partner location and item availability.",
        "who_can_access": "Operations Manager, Admin",
        "main_sections": ["Routing Rules", "Warehouse Assignment", "Priority Configuration", "Fallback Rules", "Routing History"],
        "usage_flow": ["Define routing rules based on partner geography", "Assign primary and fallback warehouses", "Set priority for multi-warehouse items", "Test routing with sample orders"],
        "fields": [{"name": "Partner Region", "description": "Geographic zone of the partner"}, {"name": "Primary Warehouse", "description": "Default fulfillment location"}, {"name": "Fallback Warehouse", "description": "Alternative if primary is out of stock"}, {"name": "Priority", "description": "Order of preference for multiple options"}],
        "statuses": [{"name": "Active", "description": "Rule currently in effect"}, {"name": "Inactive", "description": "Rule disabled"}],
        "tips": ["Test routing rules with sample orders before activating", "Set fallback warehouses for business continuity"],
        "common_mistakes": ["Not setting fallback routes causing order fulfillment failures"]
    },

    "staff_partners_fulfillment": {
        "purpose": "Track and manage the fulfillment process for approved partner orders — picking, packing, quality check, and readiness.",
        "who_can_access": "Warehouse Team, Operations Manager, Admin",
        "main_sections": ["Fulfillment Queue", "Pick List", "Pack Station", "Quality Check", "Ready for Dispatch"],
        "usage_flow": ["View approved orders ready for fulfillment", "Generate pick list from warehouse", "Pack items and verify quantities", "Perform quality check", "Mark ready for dispatch"],
        "fields": [{"name": "Order", "description": "Partner order reference"}, {"name": "Items", "description": "Products and quantities to fulfill"}, {"name": "Pick Status", "description": "Items collected from shelves"}, {"name": "Pack Status", "description": "Items packaged for shipping"}, {"name": "QC Status", "description": "Quality check passed/failed"}],
        "statuses": [{"name": "Pending Pick", "description": "Items not yet collected"}, {"name": "Picked", "description": "Items collected from warehouse"}, {"name": "Packed", "description": "Items packaged"}, {"name": "QC Passed", "description": "Quality check successful"}, {"name": "Ready", "description": "Ready for dispatch"}],
        "tips": ["Process FIFO — oldest orders first", "Double-check quantities at pack station"],
        "common_mistakes": ["Skipping quality check leading to defective shipments"]
    },

    "staff_partners_dispatch": {
        "purpose": "Manage dispatch and shipping of fulfilled partner orders — carrier selection, tracking, and delivery confirmation.",
        "who_can_access": "Dispatch Team, Operations Manager, Admin",
        "main_sections": ["Dispatch Queue", "Carrier Selection", "Shipping Label", "Tracking", "Delivery Confirmation"],
        "usage_flow": ["View orders ready for dispatch", "Select shipping carrier", "Generate shipping label and documents", "Hand over to carrier", "Track shipment", "Confirm delivery"],
        "fields": [{"name": "Order", "description": "Partner order reference"}, {"name": "Carrier", "description": "Shipping company"}, {"name": "Tracking Number", "description": "Shipment tracking ID"}, {"name": "Dispatch Date", "description": "Date shipped"}, {"name": "Delivery Date", "description": "Actual delivery date"}],
        "statuses": [{"name": "Ready for Dispatch", "description": "Packed and waiting"}, {"name": "Dispatched", "description": "Handed to carrier"}, {"name": "In Transit", "description": "En route to partner"}, {"name": "Delivered", "description": "Partner confirmed receipt"}],
        "tips": ["Choose carrier based on partner location and urgency", "Send tracking details to partner immediately"],
        "common_mistakes": ["Not recording tracking number making delivery follow-up impossible"]
    },

    "staff_partners_invoices": {
        "purpose": "Generate and manage invoices for partner orders — billing, GST calculation, and payment terms.",
        "who_can_access": "Finance, Partner Manager, Admin",
        "main_sections": ["Invoice Queue", "Invoice Generator", "GST Summary", "Outstanding Tracker", "Credit Notes"],
        "usage_flow": ["Select dispatched order for invoicing", "Verify quantities and pricing", "Generate invoice with GST", "Send to partner", "Track payment against invoice"],
        "fields": [{"name": "Invoice Number", "description": "Unique invoice reference"}, {"name": "Partner", "description": "Billing party"}, {"name": "Order Reference", "description": "Linked order"}, {"name": "Subtotal", "description": "Amount before tax"}, {"name": "GST", "description": "Applicable GST amount"}, {"name": "Total", "description": "Final billing amount"}, {"name": "Due Date", "description": "Payment deadline"}],
        "statuses": [{"name": "Draft", "description": "Invoice prepared"}, {"name": "Sent", "description": "Delivered to partner"}, {"name": "Partially Paid", "description": "Partial payment received"}, {"name": "Paid", "description": "Full payment received"}, {"name": "Overdue", "description": "Past due date"}],
        "tips": ["Generate invoices on same day as dispatch", "Follow up on overdue invoices weekly"],
        "common_mistakes": ["Incorrect GST rate application based on item HSN code"]
    },

    "staff_partners_payments": {
        "purpose": "Verify and reconcile payments received from business partners against outstanding invoices.",
        "who_can_access": "Finance, Admin",
        "main_sections": ["Payment Queue", "Payment Verification", "Bank Reconciliation", "Outstanding Summary", "Payment History"],
        "usage_flow": ["Partner makes payment", "Record payment receipt", "Match against open invoices", "Verify bank credit", "Update partner account balance"],
        "fields": [{"name": "Payment Reference", "description": "Transaction ID or cheque number"}, {"name": "Amount", "description": "Payment amount received"}, {"name": "Payment Mode", "description": "Bank transfer/Cheque/Cash/UPI"}, {"name": "Against Invoice", "description": "Invoice being paid"}, {"name": "Balance", "description": "Remaining outstanding amount"}],
        "statuses": [{"name": "Received", "description": "Payment recorded"}, {"name": "Verified", "description": "Bank credit confirmed"}, {"name": "Matched", "description": "Linked to invoice"}, {"name": "Disputed", "description": "Amount mismatch under investigation"}],
        "tips": ["Reconcile payments daily to maintain accurate partner balances", "Investigate mismatches within 48 hours"],
        "common_mistakes": ["Not matching payment to correct invoice leading to incorrect outstanding balance"]
    },

    "staff_partners_master": {
        "purpose": "Configure and manage the master list of business partners — onboarding, categorization, and status management.",
        "who_can_access": "Partner Manager, Admin",
        "main_sections": ["Partner List", "Add Partner Form", "Category Assignment", "Credit Limit Configuration", "Partner Profile"],
        "usage_flow": ["Add new business partner", "Set partner category (Dealer/Distributor/Vendor/Service Center)", "Configure credit limit", "Assign pricing tier", "Activate partner account"],
        "fields": [{"name": "Partner Name", "description": "Business name"}, {"name": "Category", "description": "Dealer/Distributor/Vendor/Service Center"}, {"name": "Credit Limit", "description": "Maximum outstanding amount allowed"}, {"name": "Pricing Tier", "description": "Assigned price list"}, {"name": "GST Number", "description": "Partner's GST registration"}],
        "statuses": [{"name": "Active", "description": "Fully operational partner"}, {"name": "Inactive", "description": "Temporarily suspended"}, {"name": "Blacklisted", "description": "Permanently blocked"}],
        "tips": ["Verify GST number authenticity before activation", "Review credit limits quarterly based on payment history"],
        "common_mistakes": ["Setting credit limits without checking partner payment track record"]
    },

    "staff_accounts_expense_categories": {
        "purpose": "Define and manage expense categories used across the SFMS accounting system for standardized expense tracking.",
        "who_can_access": "Finance Admin, Accountant",
        "main_sections": ["Category Tree", "Add/Edit Category", "Sub-categories", "GL Account Mapping", "Activation Status"],
        "usage_flow": ["View category hierarchy", "Add new category with GL mapping", "Set parent-child relationships", "Activate or deactivate categories"],
        "fields": [{"name": "Category Name", "description": "Expense category label"}, {"name": "Parent Category", "description": "Hierarchical parent if sub-category"}, {"name": "GL Account", "description": "Mapped general ledger account"}, {"name": "Budget Code", "description": "Budget tracking reference"}],
        "statuses": [{"name": "Active", "description": "Available for use in expense entries"}, {"name": "Inactive", "description": "Hidden from new entries, historical data retained"}],
        "tips": ["Align categories with Indian accounting standards", "Keep category tree depth to 3 levels maximum for usability"],
        "common_mistakes": ["Creating duplicate categories instead of using existing ones"]
    },

    "staff_sidebar_sync": {
        "purpose": "Synchronize sidebar menu configuration between database and frontend. Ensures menu items match StaffMenuRegistry.",
        "who_can_access": "Supreme Admin, System Admin",
        "main_sections": ["Sync Status", "Registry View", "Mismatch Detection", "Force Sync", "Sync History"],
        "usage_flow": ["View current sync status", "Detect mismatches between DB and frontend", "Review proposed changes", "Execute sync", "Verify result"],
        "fields": [{"name": "Registry Count", "description": "Total menu items in database"}, {"name": "Frontend Count", "description": "Menu items in sidebar JS"}, {"name": "Mismatches", "description": "Items present in one but not other"}, {"name": "Last Sync", "description": "Timestamp of last synchronization"}],
        "statuses": [{"name": "In Sync", "description": "Database and frontend match"}, {"name": "Out of Sync", "description": "Differences detected"}, {"name": "Syncing", "description": "Synchronization in progress"}],
        "tips": ["Run sync after adding new menu items to the registry", "Review mismatches before force-syncing to avoid accidental deletions"],
        "common_mistakes": ["Force-syncing without reviewing what will change"]
    },

    "staff_accounts_companies": {
        "purpose": "Manage company entities for multi-company SFMS accounting. Each company has independent financial records per DC Protocol.",
        "who_can_access": "Supreme Admin, Finance Admin",
        "main_sections": ["Company List", "Add Company", "Company Profile", "Financial Year Config", "Currency Settings"],
        "usage_flow": ["View all registered companies", "Add new company with registration details", "Configure financial year and tax settings", "Set default currency and bank accounts"],
        "fields": [{"name": "Company Name", "description": "Legal entity name"}, {"name": "Registration Number", "description": "Company registration/CIN"}, {"name": "GST Number", "description": "GST registration"}, {"name": "Financial Year", "description": "April-March or custom"}, {"name": "Base Currency", "description": "INR default"}],
        "statuses": [{"name": "Active", "description": "Operational company"}, {"name": "Inactive", "description": "Dormant or closed"}],
        "tips": ["Ensure DC Protocol company_id is set correctly for data segregation", "Configure tax settings before processing first transaction"],
        "common_mistakes": ["Creating transactions before completing company setup"]
    },

    "staff_accounts_hsn": {
        "purpose": "Manage HSN/SAC code master data for GST-compliant invoicing across all product and service categories.",
        "who_can_access": "Finance Admin, Accountant",
        "main_sections": ["HSN/SAC Code List", "Add Code", "GST Rate Mapping", "Search", "Import/Export"],
        "usage_flow": ["Search for HSN/SAC code", "Add new code with GST rate", "Map to stock items and service categories", "Verify rate against latest GST schedule"],
        "fields": [{"name": "HSN/SAC Code", "description": "Government-assigned code"}, {"name": "Description", "description": "Product/service category description"}, {"name": "GST Rate", "description": "Applicable GST percentage"}, {"name": "CGST/SGST/IGST", "description": "Rate split for central/state/integrated GST"}],
        "statuses": [{"name": "Active", "description": "Code in use"}, {"name": "Deprecated", "description": "Code replaced by new classification"}],
        "tips": ["Update GST rates whenever government notifications are issued", "Verify HSN codes against official GST portal"],
        "common_mistakes": ["Using wrong HSN code leading to incorrect GST calculation on invoices"]
    },

    "rvz_menu_access_config": {
        "purpose": "Supreme Admin panel for configuring menu access across all staff members. Implements Zero-Default Access Policy.",
        "who_can_access": "Supreme Admin only",
        "main_sections": ["Employee Selector", "Menu Tree", "Bulk Assignment", "Role Templates", "Audit Log"],
        "usage_flow": ["Select staff member", "View full menu tree with checkboxes", "Grant/revoke individual or section-level access", "Use role templates for common patterns", "Save and verify immediate effect"],
        "fields": [{"name": "Staff Member", "description": "Target employee"}, {"name": "Menu Section", "description": "Top-level menu group"}, {"name": "Menu Item", "description": "Individual page"}, {"name": "Access", "description": "Granted or revoked"}],
        "statuses": [],
        "tips": ["Use role templates for new employees to save time", "Audit access quarterly — remove unused permissions", "Remember: Zero-Default means new staff have NO access until explicitly granted"],
        "common_mistakes": ["Granting section-level access without reviewing which pages are included", "Not removing access when employee changes department"]
    },

    "staff_accounts_segments": {
        "purpose": "Configure business segments for segmented financial reporting within SFMS multi-company accounting.",
        "who_can_access": "Finance Admin, Accountant",
        "main_sections": ["Segment List", "Add Segment", "Segment Mapping", "Report Configuration"],
        "usage_flow": ["Define business segments", "Map accounts and transactions to segments", "Configure segment-wise reporting", "Generate segmented P&L and Balance Sheet"],
        "fields": [{"name": "Segment Name", "description": "Business segment identifier"}, {"name": "Segment Code", "description": "Short code for references"}, {"name": "Parent Segment", "description": "Hierarchical parent if sub-segment"}, {"name": "Description", "description": "Segment purpose and scope"}],
        "statuses": [{"name": "Active", "description": "Segment in use"}, {"name": "Inactive", "description": "Segment deactivated"}],
        "tips": ["Align segments with your company's management reporting structure", "Keep segment hierarchy simple for easy reporting"],
        "common_mistakes": ["Creating too many segments making reporting overly complex"]
    },

    "staff_accounts_pricing": {
        "purpose": "Configure pricing rules, discount structures, and margin settings for sales and partner operations.",
        "who_can_access": "Finance Admin, Sales Manager",
        "main_sections": ["Price Rules", "Discount Configuration", "Margin Settings", "Price List Management", "Effective Dates"],
        "usage_flow": ["Create pricing rule", "Set base prices and discount tiers", "Configure minimum margin requirements", "Assign to customer/partner groups", "Set effective dates"],
        "fields": [{"name": "Rule Name", "description": "Pricing rule identifier"}, {"name": "Base Price", "description": "Standard selling price"}, {"name": "Discount %", "description": "Applicable discount"}, {"name": "Min Margin %", "description": "Minimum allowed margin"}, {"name": "Effective From", "description": "Date rule takes effect"}],
        "statuses": [{"name": "Active", "description": "Rule currently applied"}, {"name": "Scheduled", "description": "Will activate on effective date"}, {"name": "Expired", "description": "Past validity period"}],
        "tips": ["Test pricing rules with sample orders before activating", "Set minimum margin to prevent below-cost sales"],
        "common_mistakes": ["Overlapping pricing rules causing unpredictable price selection"]
    },

    "rvz_real_dreams_partners": {
        "purpose": "Manage Real Dreams real estate partners — agents, brokers, and property developers in the VGK4U ecosystem.",
        "who_can_access": "RVZ Admin, Real Dreams Manager",
        "main_sections": ["Partner Directory", "Add Partner", "Commission Config", "Performance Dashboard", "Partner Profile"],
        "usage_flow": ["View all real estate partners", "Onboard new partner with verification", "Configure commission rates", "Track partner performance", "Manage partner status"],
        "fields": [{"name": "Partner Name", "description": "Agent/broker/developer name"}, {"name": "RERA Number", "description": "Real estate regulatory registration"}, {"name": "Commission %", "description": "Commission rate on transactions"}, {"name": "Active Listings", "description": "Number of active property listings"}, {"name": "Territory", "description": "Geographic coverage area"}],
        "statuses": [{"name": "Active", "description": "Authorized partner"}, {"name": "Suspended", "description": "Temporarily inactive"}, {"name": "Terminated", "description": "Partnership ended"}],
        "tips": ["Verify RERA registration before onboarding", "Review partner performance quarterly"],
        "common_mistakes": ["Not updating commission rates when agreements change"]
    },

    "rvz_real_dreams_properties": {
        "purpose": "Manage property listings in the Real Dreams marketplace — add, edit, verify, and publish properties.",
        "who_can_access": "RVZ Admin, Real Dreams Manager, Partners",
        "main_sections": ["Property List", "Add Property", "Verification Queue", "Media Manager", "Pricing"],
        "usage_flow": ["Add property with details and photos", "Submit for verification", "Admin verifies property details", "Set pricing and availability", "Publish to marketplace"],
        "fields": [{"name": "Property Title", "description": "Marketing title"}, {"name": "Property Type", "description": "Apartment/Villa/Plot/Commercial"}, {"name": "Location", "description": "City, area, and pin code"}, {"name": "Price", "description": "Asking price or price range"}, {"name": "Area", "description": "Square feet/meters"}, {"name": "RERA ID", "description": "RERA project registration"}],
        "statuses": [{"name": "Draft", "description": "Incomplete listing"}, {"name": "Submitted", "description": "Awaiting verification"}, {"name": "Verified", "description": "Details confirmed"}, {"name": "Published", "description": "Live on marketplace"}, {"name": "Sold", "description": "Property sold"}],
        "tips": ["Include high-quality photos — listings with 10+ photos get 3x more views", "Verify RERA ID before publishing"],
        "common_mistakes": ["Publishing without complete property documentation"]
    },

    "real_dreams_marketplace": {
        "purpose": "Public-facing property marketplace where users browse, search, and shortlist properties.",
        "who_can_access": "All users (public page)",
        "main_sections": ["Property Grid/List", "Search & Filters", "Map View", "Shortlist", "Contact Form"],
        "usage_flow": ["Browse or search properties", "Apply filters (location, type, budget)", "View property details", "Save to shortlist", "Contact agent/partner"],
        "fields": [{"name": "Search", "description": "Keyword search"}, {"name": "Location Filter", "description": "City or area"}, {"name": "Budget Range", "description": "Min-Max price"}, {"name": "Property Type", "description": "Category filter"}],
        "statuses": [],
        "tips": ["Use map view to find properties near preferred locations", "Save favorites to compare later"],
        "common_mistakes": ["Setting filters too narrow and missing good options"]
    },

    "real_dreams_property_detail": {
        "purpose": "Detailed property page showing all information, media gallery, amenities, and contact options.",
        "who_can_access": "All users (public page)",
        "main_sections": ["Photo Gallery", "Property Details", "Amenities", "Floor Plans", "Location Map", "Similar Properties", "Contact Agent"],
        "usage_flow": ["View property photos and videos", "Read detailed description", "Check amenities and specifications", "View on map", "Contact agent for visit"],
        "fields": [{"name": "Price", "description": "Listed price or price on request"}, {"name": "Configuration", "description": "BHK/rooms layout"}, {"name": "Area", "description": "Built-up and carpet area"}, {"name": "Possession", "description": "Ready/Under construction with date"}],
        "statuses": [],
        "tips": ["Check possession date and RERA compliance before expressing interest"],
        "common_mistakes": ["Not verifying builder credentials before site visit"]
    },

    "real_dreams_compare": {
        "purpose": "Side-by-side property comparison tool to help users evaluate multiple properties.",
        "who_can_access": "All users (public page)",
        "main_sections": ["Comparison Table", "Feature Highlights", "Price Comparison", "Location Comparison"],
        "usage_flow": ["Add 2-4 properties from shortlist", "View side-by-side comparison", "Compare features, pricing, and location", "Make informed decision"],
        "fields": [{"name": "Properties", "description": "Selected properties for comparison"}, {"name": "Features", "description": "Amenities and specifications compared"}],
        "statuses": [],
        "tips": ["Compare properties of same type and area for meaningful comparison"],
        "common_mistakes": ["Comparing properties in vastly different price ranges"]
    },

    "rvz_real_dreams_marketplace": {
        "purpose": "Admin view of the Real Dreams property marketplace with management controls for listing visibility and featured properties.",
        "who_can_access": "RVZ Admin, Real Dreams Manager",
        "main_sections": ["All Listings", "Featured Properties", "Visibility Controls", "Analytics", "User Inquiries"],
        "usage_flow": ["View all marketplace listings", "Set featured properties", "Control visibility and ordering", "Review marketplace analytics", "Manage user inquiries"],
        "fields": [{"name": "Listing", "description": "Property reference"}, {"name": "Views", "description": "Number of page views"}, {"name": "Inquiries", "description": "Contact requests received"}, {"name": "Featured", "description": "Highlighted on homepage"}],
        "statuses": [],
        "tips": ["Feature properties with good photos and competitive pricing for best engagement"],
        "common_mistakes": ["Featuring too many properties dilutes the impact"]
    },

    "rvz_real_dreams": {
        "purpose": "Configure property amenities, features, and specifications available for property listings.",
        "who_can_access": "RVZ Admin, Real Dreams Manager",
        "main_sections": ["Amenity Categories", "Add Amenity", "Feature Tags", "Specification Types", "Icon Library"],
        "usage_flow": ["View available amenities", "Add new amenity with icon", "Categorize (Safety/Lifestyle/Convenience)", "Assign to property types", "Activate/deactivate"],
        "fields": [{"name": "Amenity Name", "description": "Feature label (e.g. Swimming Pool)"}, {"name": "Category", "description": "Safety/Lifestyle/Convenience"}, {"name": "Icon", "description": "Display icon for UI"}, {"name": "Applicable To", "description": "Property types this applies to"}],
        "statuses": [{"name": "Active", "description": "Available for listings"}, {"name": "Inactive", "description": "Not available for new listings"}],
        "tips": ["Add amenities commonly searched by buyers for better SEO", "Keep amenity list curated — quality over quantity"],
        "common_mistakes": ["Creating duplicate amenities with different names"]
    },

    "rvz_real_dreams_dashboard": {
        "purpose": "Real Dreams management dashboard with key metrics — listings, inquiries, conversions, and partner performance.",
        "who_can_access": "RVZ Admin, Real Dreams Manager",
        "main_sections": ["KPI Cards", "Listing Trends", "Inquiry Funnel", "Partner Leaderboard", "Revenue Chart"],
        "usage_flow": ["View key metrics at a glance", "Drill into trends by time period", "Monitor inquiry-to-visit conversion", "Track partner performance", "Review revenue by property type"],
        "fields": [{"name": "Active Listings", "description": "Total live properties"}, {"name": "Monthly Inquiries", "description": "New contact requests this month"}, {"name": "Conversion Rate", "description": "Inquiry to visit/sale percentage"}, {"name": "Revenue", "description": "Total transaction value"}],
        "statuses": [],
        "tips": ["Review dashboard weekly for trend identification", "Focus on conversion rate improvements"],
        "common_mistakes": ["Looking at vanity metrics (views) instead of conversion metrics"]
    },

    "_rvz_real-dreams_partners": {
        "purpose": "Alternate access point for Real Dreams partner management with property handler assignment view.",
        "who_can_access": "RVZ Admin",
        "main_sections": ["Partner List", "Handler Assignment", "Territory View", "Commission Tracker"],
        "usage_flow": ["View partners and their assigned territories", "Assign or reassign property handlers", "Track commission earnings", "Monitor partner activity"],
        "fields": [{"name": "Partner", "description": "Partner name and ID"}, {"name": "Territory", "description": "Assigned geographic area"}, {"name": "Properties Handled", "description": "Active listings count"}, {"name": "Commission YTD", "description": "Year-to-date commission earned"}],
        "statuses": [],
        "tips": ["Balance property assignments across partners for fair distribution"],
        "common_mistakes": ["Assigning too many properties to one partner causing poor service"]
    },

    "_rvz_real-dreams_properties": {
        "purpose": "Alternate access point for property management with handler-centric view and bulk operations.",
        "who_can_access": "RVZ Admin",
        "main_sections": ["Property Grid", "Handler Filter", "Bulk Status Update", "Verification Queue", "Archive"],
        "usage_flow": ["Filter properties by handler", "Bulk update property statuses", "Process verification queue", "Archive sold or expired listings"],
        "fields": [{"name": "Property", "description": "Property title and ID"}, {"name": "Handler", "description": "Assigned partner/agent"}, {"name": "Status", "description": "Current listing status"}, {"name": "Last Updated", "description": "Most recent modification date"}],
        "statuses": [],
        "tips": ["Archive sold properties promptly to keep marketplace current"],
        "common_mistakes": ["Not archiving expired listings leading to stale marketplace"]
    },

    "staff_incentives_zynova": {
        "purpose": "View and manage all VGK4U member records — both Real Estate (ZR) and Insurance (ZC) segments.",
        "who_can_access": "Admin, VGK4U Manager",
        "main_sections": ["Member List", "Segment Filter (ZR/ZC)", "Earning Summary", "Referral Tree", "Status Management"],
        "usage_flow": ["View all VGK4U members", "Filter by Real Estate or Insurance segment", "Check earning summaries", "View referral relationships", "Manage member status"],
        "fields": [{"name": "Member Name", "description": "VGK4U member"}, {"name": "Segment", "description": "ZR (Real Estate) or ZC (Insurance)"}, {"name": "Referral Count", "description": "Direct referrals in segment"}, {"name": "Total Earnings", "description": "Lifetime earnings in this segment"}, {"name": "Status", "description": "Active/Inactive"}],
        "statuses": [{"name": "Active", "description": "Currently earning member"}, {"name": "Inactive", "description": "Membership suspended/expired"}],
        "tips": ["Review earnings across both segments for cross-selling opportunities"],
        "common_mistakes": ["Confusing VGK4U segment earnings with MNR core income"]
    },
}

SECTION_ORDER = [
    "progress", "PROGRESS", "STAFF_DASHBOARD", "staff-dashboard", "attendance", "crm",
    "task-management", "kra-management", "timesheet",
    "journey-tracking", "location-tracking", "reimbursement",
    "service-tickets", "sfms", "inventory", "payroll",
    "official-partners", "nda-management", "configuration",
    "zynova", "real-dreams", "zy-member-earnings"
]

MNR_EXCLUDED_SECTIONS = {
    "mnr-users", "mnr-approvals", "mnr-awards", "mnr-communications",
    "mnr-config", "mnr-data", "mnr-finance", "mnr-income",
    "mnr-pins", "mnr-security", "mnr-withdrawals",
    "staff_mnr_user_announcements", "staff_mnr_user_awards",
    "staff_mnr_user_coupons", "staff_mnr_user_dashboard",
    "staff_mnr_user_members", "staff_mnr_user_mnr",
    "staff_mnr_user_myntreal", "staff_mnr_user_system",
    "staff_mnr_user_zynova",
    "mnr-admin", "mnr-user"
}
