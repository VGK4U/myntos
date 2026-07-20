"""
DC Protocol Jan 12 2026: Sidebar Sync Service - 18 SECTIONS per PDF Specification
CORRECT ORDER from PDF "PERORMANCE_REPORT_-_Final_Side_bar":
1-PROGRESS, 2-STAFF DASHBOARD, 3-ATTENDANCE, 4-CRM & LEADS, 5-TASK MANAGEMENT,
6-KRA MANAGEMENT, 7-TIMESHEET, 8-JOURNEY TRACKING, 9-LOCATION TRACKING,
10-REIMBURSEMENT, 11-SERVICE TICKETS, 12-ACCOUNTS, 13-BUSINESS PARTNERS,
14-NDA MANAGEMENT, 15-CONFIGURATION, 16-ZYNOVA, 17-MNR, 18-MNR USER SIDEBAR
"""
import logging
from sqlalchemy import text

# Canonical sidebar structure - 18 MAIN SECTIONS (PDF Specification Jan 12 2026)
SIDEBAR_SECTIONS = [
    # Section 1: PROGRESS
    {"id": "progress", "title": "PROGRESS", "order": 1, "parent": None, "cascade_enabled": True},
    # Section 2: STAFF DASHBOARD
    {"id": "staff-dashboard", "title": "STAFF DASHBOARD", "order": 2, "parent": None, "cascade_enabled": True},
    # Section 3: ATTENDANCE
    {"id": "attendance", "title": "ATTENDANCE", "order": 3, "parent": None, "cascade_enabled": True},
    # Section 4: CRM & LEADS
    {"id": "crm", "title": "CRM & LEADS", "order": 4, "parent": None, "cascade_enabled": True},
    # Section 5: TASK MANAGEMENT
    {"id": "task-management", "title": "TASK MANAGEMENT", "order": 5, "parent": None, "cascade_enabled": True},
    # Section 6: KRA MANAGEMENT
    {"id": "kra-management", "title": "KRA MANAGEMENT", "order": 6, "parent": None, "cascade_enabled": True},
    # Section 7: TIMESHEET
    {"id": "timesheet", "title": "TIMESHEET", "order": 7, "parent": None, "cascade_enabled": True},
    # Section 8: JOURNEY TRACKING
    {"id": "journey-tracking", "title": "JOURNEY TRACKING", "order": 8, "parent": None, "cascade_enabled": True},
    # Section 9: LOCATION TRACKING
    {"id": "location-tracking", "title": "LOCATION TRACKING", "order": 9, "parent": None, "cascade_enabled": True},
    # Section 10: REIMBURSEMENT
    {"id": "reimbursement", "title": "REIMBURSEMENT", "order": 10, "parent": None, "cascade_enabled": True},
    # Section 11: SERVICE TICKETS
    {"id": "service-tickets", "title": "SERVICE TICKETS", "order": 11, "parent": None, "cascade_enabled": True},
    # Section 12: ACCOUNTS with SFMS, Inventory, Payroll subsections
    {"id": "accounts", "title": "ACCOUNTS", "order": 12, "parent": None, "cascade_enabled": True},
    {"id": "sfms", "title": "SFMS", "order": 12, "parent": "accounts", "cascade_enabled": True},
    # DC_DAR_004 (May 2026): Consolidated subsection houses DAR + cross-company rollups
    {"id": "consolidated", "title": "Consolidated", "order": 12, "parent": "accounts", "cascade_enabled": True},
    {"id": "inventory", "title": "Inventory", "order": 12, "parent": "accounts", "cascade_enabled": True},
    {"id": "payroll", "title": "Payroll", "order": 12, "parent": "accounts", "cascade_enabled": True},
    {"id": "marketplace", "title": "Marketplace", "order": 12, "parent": "accounts", "cascade_enabled": True},
    # Section 13: BUSINESS PARTNERS
    {"id": "official-partners", "title": "BUSINESS PARTNERS", "order": 13, "parent": None, "cascade_enabled": True},
    # Section 14: NDA MANAGEMENT
    {"id": "nda-management", "title": "NDA MANAGEMENT", "order": 14, "parent": None, "cascade_enabled": True},
    # Section 15: CONFIGURATION
    {"id": "configuration", "title": "CONFIGURATION", "order": 15, "parent": None, "cascade_enabled": True},
    # Section 16: ZYNOVA with Property Workings, Member Earnings subsections
    {"id": "vgk4u", "title": "VGK4U", "order": 16, "parent": None, "cascade_enabled": True},
    {"id": "real-dreams", "title": "VGK4U Property", "order": 16, "parent": "vgk4u", "cascade_enabled": True},
    {"id": "zy-member-earnings", "title": "VGK4U Earnings", "order": 16, "parent": "vgk4u", "cascade_enabled": True},
    # Section 17: MNR with 11 subsections (PDF Spec Jan 12 2026)
    {"id": "mnr", "title": "MNR", "order": 17, "parent": None, "cascade_enabled": True},
    {"id": "mnr-users", "title": "Users (17.1)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-approvals", "title": "Approvals (17.2)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-awards", "title": "Awards (17.3)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-income", "title": "Income (17.4)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-withdrawals", "title": "Withdrawals (17.5)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-finance", "title": "Finance & Compliance (17.6)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-communications", "title": "Announcements (17.7)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-pins", "title": "PINs & Approvals (17.8)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-security", "title": "Password & Security (17.9)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-config", "title": "System Configuration (17.10)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    {"id": "mnr-data", "title": "Data Management (17.11)", "order": 17, "parent": "mnr", "cascade_enabled": True},
    # Section 18: MNR USER SIDEBAR with 9 subsections
    {"id": "mnr-user-sidebar", "title": "MNR USER SIDEBAR", "order": 18, "parent": None, "cascade_enabled": True},
    {"id": "staff_mnr_user_system", "title": "Audit Log", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_dashboard", "title": "Dashboard", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_announcements", "title": "Announcements", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_coupons", "title": "Coupons", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_members", "title": "Members", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_mnr", "title": "Earnings", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_myntreal", "title": "MyntReal", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_vgk4u", "title": "VGK4U", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    {"id": "staff_mnr_user_awards", "title": "Awards", "order": 18, "parent": "mnr-user-sidebar", "cascade_enabled": True},
    # Section 21: VGK TEAM with 2 subsections (orders 19-20 reserved for future sections)
    {"id": "vgk_team", "title": "VGK TEAM", "order": 21, "parent": None, "cascade_enabled": True},
    {"id": "vgk_team_management", "title": "VGK Team Management", "order": 21, "parent": "vgk_team", "cascade_enabled": True},
    {"id": "vgk_bonanza", "title": "VGK Bonanza", "order": 21, "parent": "vgk_team", "cascade_enabled": True},
    # Section 22: VENDOR MANAGEMENT with 5 subsections
    {"id": "vendor_management", "title": "VENDOR MANAGEMENT", "order": 22, "parent": None, "cascade_enabled": True},
    {"id": "vm_vendor_master", "title": "Vendor Master", "order": 22, "parent": "vendor_management", "cascade_enabled": True},
    {"id": "vm_products", "title": "Marketplace Products", "order": 22, "parent": "vendor_management", "cascade_enabled": True},
    {"id": "vm_transactions", "title": "Transactions", "order": 22, "parent": "vendor_management", "cascade_enabled": True},
    {"id": "vm_cash_income", "title": "Cash Income", "order": 22, "parent": "vendor_management", "cascade_enabled": True},
    {"id": "vm_wallet", "title": "Wallet", "order": 22, "parent": "vendor_management", "cascade_enabled": True},
    # Section 23: MYNT REAL (flat)
    {"id": "mynt_real", "title": "MYNT REAL", "order": 23, "parent": None, "cascade_enabled": True},
    # Section 24: VGK4U MEMBER (Task #33 Phase 1 — Read-Only Modules)
    # Zero-Default Access: visible only to staff explicitly granted via Menu Access Control.
    {"id": "vgk4u_member", "title": "VGK4U MEMBER", "order": 24, "parent": None, "cascade_enabled": True},
]

# Route path to section mapping - EXACT PDF SPECIFICATION (Jan 12 2026)
SIDEBAR_ROUTE_MAPPING = {
    # PARENT SECTION ENTRIES
    "/staff/accounts": {"section": "accounts", "order": 12},
    "/section/zynova": {"section": "zynova", "order": 16},
    "/section/mnr": {"section": "mnr", "order": 17},
    "/section/mnr-user-sidebar": {"section": "mnr-user-sidebar", "order": 18},
    "#zynova": {"section": "zynova", "order": 16},
    
    # ============== SECTION 1: PROGRESS ==============
    "/staff/progress": {"section": "progress", "order": 1},
    
    # ============== SECTION 2: STAFF DASHBOARD ==============
    # PDF Pages: Dashboard, Employees, Employee Directory, My KYC, KYC Approvals,
    #            Review Dashboard, Training Videos (DC_TRAINING_VIDEOS_001)
    "/staff/dashboard": {"section": "staff-dashboard", "order": 2},
    "/staff/training-videos": {"section": "staff-dashboard", "order": 2},
    "/staff/employees": {"section": "staff-dashboard", "order": 2},
    "/staff/employee-directory": {"section": "staff-dashboard", "order": 2},
    "/staff/my-kyc": {"section": "staff-dashboard", "order": 2},
    "/staff/kyc-approvals": {"section": "staff-dashboard", "order": 2},
    "/staff/manager-review": {"section": "staff-dashboard", "order": 2},
    "/staff/2fa-settings": {"section": "staff-dashboard", "order": 2},
    "/staff/change-password": {"section": "staff-dashboard", "order": 2},
    "/staff/team-attendance-summary": {"section": "staff-dashboard", "order": 2},
    
    # ============== SECTION 3: ATTENDANCE ==============
    # PDF Pages: In/Out Time, My Leaves, Leave Approvals, In/Out Records, Attendance Records, 
    #            Attendance Dashboard, Exception Approvals, Attendance Computation
    "/staff/my-attendance": {"section": "attendance", "order": 3},
    "/staff/my-leaves": {"section": "attendance", "order": 3},
    "/staff/leave-approvals": {"section": "attendance", "order": 3},
    "/staff/team-attendance": {"section": "attendance", "order": 3},
    "/staff/attendance-sheet": {"section": "attendance", "order": 3},
    "/staff/attendance-reports": {"section": "attendance", "order": 3},
    "/staff/attendance-exceptions": {"section": "attendance", "order": 3},
    "/staff/attendance-computation": {"section": "attendance", "order": 3},
    
    # ============== SECTION 4: CRM & LEADS ==============
    # PDF Pages: My CRM Dashboard, Staff Leads, Team Leads, My Leads, Lead Sources, WA Inbox
    "/staff/crm/dashboard": {"section": "crm", "order": 4},
    "/staff/leads": {"section": "crm", "order": 4},
    "/staff/crm/team-leads": {"section": "crm", "order": 4},
    "/staff/my-leads": {"section": "crm", "order": 4},
    "/staff/crm/lead-sources": {"section": "crm", "order": 4},
    "/rvz/crm-leads": {"section": "crm", "order": 4},
    "/staff/crm/whatsapp-inbox": {"section": "crm", "order": 4},
    
    # ============== SECTION 5: TASK MANAGEMENT ==============
    # PDF Pages: Task Planner, Task Dashboard, Team Day Plans, Assigned By Me, Assigned To Me, Team Activities, Task Reviews
    "/staff/tasks/day-planner": {"section": "task-management", "order": 5},
    "/staff/tasks/assigned-by-me-v2": {"section": "task-management", "order": 5},
    "/staff/tasks/assigned-to-me": {"section": "task-management", "order": 5},
    "/staff/tasks/team-activities": {"section": "task-management", "order": 5},
    "/staff/team-activities": {"section": "task-management", "order": 5},
    "/staff/tasks/tracker": {"section": "task-management", "order": 5},
    "/staff/task-review": {"section": "task-management", "order": 5},
    
    # ============== SECTION 6: KRA MANAGEMENT ==============
    # PDF Pages: My KRAs, KRA Templates, KRA Tracking Sheet, KRA Review
    "/staff/my-kras": {"section": "kra-management", "order": 6},
    "/staff/kra-templates": {"section": "kra-management", "order": 6},
    "/staff/kra-tracking-sheet": {"section": "kra-management", "order": 6},
    "/staff/kra-review": {"section": "kra-management", "order": 6},
    
    # ============== SECTION 7: TIMESHEET ==============
    # PDF Pages: My Timesheet, Timesheet Approval
    "/staff/my-timesheet": {"section": "timesheet", "order": 7},
    "/staff/timesheet-approval": {"section": "timesheet", "order": 7},
    
    # ============== SECTION 8: JOURNEY TRACKING ==============
    # PDF Pages: My Journeys, Team Journeys, All Journeys, VGK4U Journeys
    "/staff/my-journeys": {"section": "journey-tracking", "order": 8},
    "/staff/team-journeys": {"section": "journey-tracking", "order": 8},
    "/staff/all-journeys": {"section": "journey-tracking", "order": 8},
    "/staff/vgk4u-journeys": {"section": "journey-tracking", "order": 8},
    
    # ============== SECTION 9: LOCATION TRACKING ==============
    # PDF Pages: My Location History, Team Location Tracker
    "/staff/my-location-history": {"section": "location-tracking", "order": 9},
    "/staff/team-location-tracker": {"section": "location-tracking", "order": 9},
    
    # ============== SECTION 10: REIMBURSEMENT ==============
    # PDF Pages: My Reimbursement Claims, Reimbursement Approvals
    "/staff/accounts/my-reimbursements": {"section": "reimbursement", "order": 10},
    "/staff/accounts/reimbursement-approvals": {"section": "reimbursement", "order": 10},
    
    # ============== SECTION 11: SERVICE TICKETS ==============
    # PDF Pages: Dashboard, Performance, Procurement, Procurement Queue, Raise Ticket, Reports, Service Queue, Service Center Revenue
    "/staff/service-tickets/dashboard": {"section": "service-tickets", "order": 11},
    "/staff/service-tickets/performance": {"section": "service-tickets", "order": 11},
    "/staff/service-tickets/procurement": {"section": "service-tickets", "order": 11},
    "/staff/service-tickets/procurement-queue": {"section": "service-tickets", "order": 11},
    "/staff/service-tickets/raise": {"section": "service-tickets", "order": 11},
    "/staff/service-tickets/reports": {"section": "service-tickets", "order": 11},
    "/staff/service-tickets/queue": {"section": "service-tickets", "order": 11},
    "/staff/service-center-revenue": {"section": "service-tickets", "order": 11},
    
    # ============== SECTION 12: ACCOUNTS ==============
    # SFMS (12.1): Balance Sheet, Fund Allocations, Expense Entries, Income Entries, Purchase Invoices, 
    #              Sales Invoices, Invoice Reports, Accounts Payable, Accounts Receivable, Sales Team Revenue, Party Ledger
    # DC_DAR_004: DAR (renamed from balance-sheet) lives in Consolidated subsection
    "/staff/accounts/DAR": {"section": "consolidated", "order": 12, "parent": "accounts"},
    "/staff/accounts/balance-sheet": {"section": "consolidated", "order": 12, "parent": "accounts"},
    "/staff/consolidated": {"section": "consolidated", "order": 12, "parent": "accounts"},
    "/staff/accounts/fund-allocations": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/expense-entries": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/income-entries": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/purchase-invoices": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/sales-invoices": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/reports": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/payables": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/receivables": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/duties-taxes": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/capital": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/cash-in-hand": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/rvz/sales-revenue": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/party-ledger": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/general-ledger": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/journal-voucher": {"section": "sfms", "order": 12, "parent": "accounts"},
    "/staff/accounts/parties": {"section": "sfms", "order": 12, "parent": "accounts"},
    # ledger-masters intentionally excluded — hidden from sidebar
    # Inventory (12.2): Bill of Materials, Manufacturing, Procurement, Purchase Intake, Stock Items,
    #                   Stock Ledger, Stock Transfers, Stock Validation, Service Center Tracking, Vendor Returns
    "/staff/inventory/bom": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/accounts/bom": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/manufacturing": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/accounts/manufacturing": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/procurement": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/accounts/procurement": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/intake": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/stock-items": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/accounts/stock-items": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/stock-ledger": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/stock-transfers": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/stock-validation": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/service-center-tracking": {"section": "service-tickets", "order": 11},
    "/staff/inventory/vendor-returns": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/inventory/accessories": {"section": "inventory", "order": 12, "parent": "accounts"},
    "/staff/accounts/vendors": {"section": "inventory", "order": 12, "parent": "accounts"},
    # Payroll (12.3): Payroll Profiles, Payroll Cycles, Payroll Runs, Approvals, Consultant Invoices, Allowance Catalog, Documents
    "/staff/payroll/profiles": {"section": "payroll", "order": 12, "parent": "accounts"},
    "/staff/payroll/cycles": {"section": "payroll", "order": 12, "parent": "accounts"},
    "/staff/payroll/runs": {"section": "payroll", "order": 12, "parent": "accounts"},
    "/staff/payroll/approvals": {"section": "payroll", "order": 12, "parent": "accounts"},
    "/staff/payroll/consultant-invoices": {"section": "payroll", "order": 12, "parent": "accounts"},
    "/staff/payroll/allowance-catalog": {"section": "payroll", "order": 12, "parent": "accounts"},
    "/staff/payroll/documents": {"section": "payroll", "order": 12, "parent": "accounts"},
    
    # ============== SECTION 13: BUSINESS PARTNERS ==============
    # PDF Pages: Partner Orders, Partner Pricing, Order Approval, Order Routing, Order Fulfillment, 
    #            Dispatch Management, Partner Invoices, Payment Verification
    "/staff/partners/orders": {"section": "official-partners", "order": 13},
    "/staff/partners/pricing": {"section": "official-partners", "order": 13},
    "/staff/partners/approval": {"section": "official-partners", "order": 13},
    "/staff/partners/routing": {"section": "official-partners", "order": 13},
    "/staff/partners/fulfillment": {"section": "official-partners", "order": 13},
    "/order-fulfillment-dashboard": {"section": "official-partners", "order": 13},
    "/staff/partners/dispatch": {"section": "official-partners", "order": 13},
    "/staff/partners/invoices": {"section": "official-partners", "order": 13},
    "/staff/partners/payments": {"section": "official-partners", "order": 13},
    
    # ============== SECTION 14: NDA MANAGEMENT ==============
    # PDF Pages: NDA Versions, Acceptance Audit, Pending Acceptances
    "/staff/nda-versions": {"section": "nda-management", "order": 14},
    "/staff/nda-acceptance-audit": {"section": "nda-management", "order": 14},
    "/staff/nda-pending": {"section": "nda-management", "order": 14},
    "/staff/nda-editor": {"section": "nda-management", "order": 14},
    
    # ============== SECTION 15: CONFIGURATION ==============
    # PDF Pages: Departments, Companies, Business Partners Config, Segments, Expense Categories, 
    #            Pricing Config, HSN Master, Signup Categories, Menu Access Control, Sidebar Sync, Settings, Audit Logs
    "/staff/departments": {"section": "configuration", "order": 15},
    "/staff/partners/master": {"section": "configuration", "order": 15},
    "/staff/accounts/segments": {"section": "configuration", "order": 15},
    "/staff/accounts/expense-categories": {"section": "configuration", "order": 15},
    "/staff/accounts/pricing": {"section": "configuration", "order": 15},
    "/staff/accounts/hsn": {"section": "configuration", "order": 15},
    "/staff/marketplace/codes-segments": {"section": "marketplace", "order": 12, "parent": "accounts"},
    "/staff/settings": {"section": "configuration", "order": 15},
    # DC_SAAS_CONSOLE_001: SaaS-level routes moved into the VGK SaaS section (supreme-only).
    "/staff/accounts/companies": {"section": "vgk-saas", "order": 13},
    "/staff/my-tenant": {"section": "vgk-saas", "order": 13},
    "/staff/b2b-clients": {"section": "vgk-saas", "order": 13},
    "/staff/signup-categories": {"section": "vgk-saas", "order": 13},
    "/staff/lead-sync": {"section": "vgk-saas", "order": 13},
    "/rvz/menu-access-config": {"section": "vgk-saas", "order": 13},
    "/staff/page-registry": {"section": "vgk-saas", "order": 13},
    "/staff/sidebar-sync": {"section": "vgk-saas", "order": 13},
    "/staff/audit-logs": {"section": "vgk-saas", "order": 13},
    "/staff/platform-setup-guide": {"section": "vgk-saas", "order": 13},
    "/staff/day-planner-guide#sec-platform-setup": {"section": "vgk-saas", "order": 13},
    
    # ============== SECTION 16: ZYNOVA ==============
    # ZY Property Workings (16.1): Property Marketplace, Property Amenities, Partner Profiles, Property Handler
    "/rvz/real-dreams/marketplace": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/rvz/real-dreams": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/rvz/real-dreams/partners": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/rvz/real-dreams-partners": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/rvz/real-dreams/properties": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/rvz/real-dreams-properties": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/rvz/real-dreams-dashboard": {"section": "real-dreams", "order": 16, "parent": "vgk4u"},
    "/real-dreams/marketplace": {"section": "zynova", "order": 16},
    "/real-dreams/compare": {"section": "zynova", "order": 16},
    "/real-dreams/property": {"section": "zynova", "order": 16},
    # ZY Member Earnings (16.2): MNR Points, Incentive Approvals, All Zynova Members, VGK Real Dreams (ZR), VGK Care (ZC)
    "/staff/incentives/points": {"section": "zy-member-earnings", "order": 16, "parent": "vgk4u"},
    "/staff/incentives/approvals": {"section": "zy-member-earnings", "order": 16, "parent": "vgk4u"},
    "/staff/incentives/vgk4u": {"section": "zy-member-earnings", "order": 16, "parent": "vgk4u"},
    "/staff/vgk4u/real-estate": {"section": "zy-member-earnings", "order": 16, "parent": "vgk4u"},
    "/staff/vgk4u/insurance": {"section": "zy-member-earnings", "order": 16, "parent": "vgk4u"},
    # Zynova Mobility EV (16.3): ETC Student Master (Marketplace moved to Accounts > 12.4)
    "/staff/vgk4u/purchase-orders": {"section": "marketplace", "order": 12, "parent": "accounts"},
    "/staff/marketplace-config": {"section": "marketplace", "order": 12, "parent": "accounts"},
    "/staff/vgk4u/etc-students": {"section": "zy-member-earnings", "order": 16, "parent": "vgk4u"},
    
    # ============== SECTION 17: MNR (56 pages per PDF Jan 12 2026) ==============
    # 17.1 Users (9 pages)
    "/staff/mnr/dashboard": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/users": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/user-data-search": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/user-activation-control": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/bulk-user-edit": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/user-update-controls": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/reactivate-reassign": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/user-update-approvals": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    "/staff/mnr/birthdays": {"section": "mnr-users", "order": 17, "parent": "mnr"},
    # 17.2 Approvals (3 pages)
    "/staff/mnr/kyc-management": {"section": "mnr-approvals", "order": 17, "parent": "mnr"},
    "/staff/mnr/bank-pending": {"section": "mnr-approvals", "order": 17, "parent": "mnr"},
    "/staff/mnr/bank-all": {"section": "mnr-approvals", "order": 17, "parent": "mnr"},
    # 17.3 Awards (7 pages)
    "/staff/mnr/awards-all": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    "/staff/mnr/awards-approval-queue": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    "/staff/mnr/procurement-queue": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    "/staff/mnr/gift-wise-status": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    "/staff/mnr/award-management": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    "/staff/mnr/bonanza-management": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    "/staff/mnr/bonanza-claims": {"section": "mnr-awards", "order": 17, "parent": "mnr"},
    # 17.4 Income (3 pages)
    "/staff/mnr/income-records": {"section": "mnr-income", "order": 17, "parent": "mnr"},
    "/staff/mnr/income-supreme": {"section": "mnr-income", "order": 17, "parent": "mnr"},
    "/staff/mnr/income-finance-complete": {"section": "mnr-income", "order": 17, "parent": "mnr"},
    # 17.5 Withdrawals (3 pages)
    "/staff/mnr/withdrawal-supreme": {"section": "mnr-withdrawals", "order": 17, "parent": "mnr"},
    "/staff/mnr/withdrawal/approvals": {"section": "mnr-withdrawals", "order": 17, "parent": "mnr"},
    "/staff/mnr/withdrawal/history": {"section": "mnr-withdrawals", "order": 17, "parent": "mnr"},
    # 17.6 Finance & Compliance (8 pages)
    "/staff/mnr/finance-supreme": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/compliance": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/company-earnings": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/revenue-details": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/payout-details": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/expense-details": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/expenses-management": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    "/staff/mnr/expense-overview": {"section": "mnr-finance", "order": 17, "parent": "mnr"},
    # 17.7 Announcements (5 pages)
    "/staff/mnr/feedback/pending": {"section": "mnr-communications", "order": 17, "parent": "mnr"},
    "/staff/mnr/announcements/view": {"section": "mnr-communications", "order": 17, "parent": "mnr"},
    "/staff/mnr/banners-management": {"section": "mnr-communications", "order": 17, "parent": "mnr"},
    "/staff/mnr/banner-analytics": {"section": "mnr-communications", "order": 17, "parent": "mnr"},
    # 17.8 PINs & Approvals (3 pages)
    "/staff/mnr/pin-approvals": {"section": "mnr-pins", "order": 17, "parent": "mnr"},
    "/staff/mnr/coupon-status": {"section": "mnr-pins", "order": 17, "parent": "mnr"},
    "/staff/mnr/pins": {"section": "mnr-pins", "order": 17, "parent": "mnr"},
    # 17.9 Password & Security (3 pages)
    "/staff/mnr/change-user-password": {"section": "mnr-security", "order": 17, "parent": "mnr"},
    "/staff/mnr/password-change": {"section": "mnr-security", "order": 17, "parent": "mnr"},
    "/staff/mnr/secondary-password-setup": {"section": "mnr-security", "order": 17, "parent": "mnr"},
    # 17.10 System Configuration (9 pages)
    "/staff/mnr/system-controls": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/rate-configuration": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/daily-ceiling": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/emergency-wallet": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/role-management": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/add-packages": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/menu-configuration": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/menu-access-config": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    "/staff/mnr/scheduler-dashboard": {"section": "mnr-config", "order": 17, "parent": "mnr"},
    # 17.11 Data Management (3 pages)
    "/staff/mnr/delete-management": {"section": "mnr-data", "order": 17, "parent": "mnr"},
    "/staff/mnr/data-recovery": {"section": "mnr-data", "order": 17, "parent": "mnr"},
    "/staff/mnr/production-reset-status": {"section": "mnr-data", "order": 17, "parent": "mnr"},
    
    # ============== SECTION 18: MNR USER SIDEBAR ==============
    # Audit Log (18.0)
    "/staff/mnr-user/audit-log": {"section": "staff_mnr_user_system", "order": 18, "parent": "mnr-user-sidebar"},
    # Dashboard (18.1)
    "/staff/mnr-user/dashboard": {"section": "staff_mnr_user_dashboard", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/profile": {"section": "staff_mnr_user_dashboard", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/create-member": {"section": "staff_mnr_user_dashboard", "order": 18, "parent": "mnr-user-sidebar"},
    # Announcements (18.2)
    "/staff/mnr-user/announcements": {"section": "staff_mnr_user_announcements", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/announcements/create": {"section": "staff_mnr_user_announcements", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/announcements/pending": {"section": "staff_mnr_user_announcements", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/announcements/history": {"section": "staff_mnr_user_announcements", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/popups": {"section": "staff_mnr_user_announcements", "order": 18, "parent": "mnr-user-sidebar"},
    # Coupons (18.3)
    "/staff/mnr-user/coupons/available": {"section": "staff_mnr_user_coupons", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/coupons/red": {"section": "staff_mnr_user_coupons", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/coupons/green": {"section": "staff_mnr_user_coupons", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/coupons/ev": {"section": "staff_mnr_user_coupons", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/coupons/transfer": {"section": "staff_mnr_user_coupons", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/coupons/history": {"section": "staff_mnr_user_coupons", "order": 18, "parent": "mnr-user-sidebar"},
    # Members (18.4)
    "/staff/mnr-user/members": {"section": "staff_mnr_user_members", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/members/all": {"section": "staff_mnr_user_members", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/members/direct": {"section": "staff_mnr_user_members", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/members/downline": {"section": "staff_mnr_user_members", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/members/ved": {"section": "staff_mnr_user_members", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/members/picture": {"section": "staff_mnr_user_members", "order": 18, "parent": "mnr-user-sidebar"},
    # Earnings (18.5)
    "/staff/mnr-user/mnr/earnings": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/earnings-summary": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/direct": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/matching": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/ved": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/guru": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/wallet": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/withdrawals": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/points": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/mnr/benefits": {"section": "staff_mnr_user_mnr", "order": 18, "parent": "mnr-user-sidebar"},
    # MyntReal (18.6)
    "/staff/mnr-user/myntreal/properties": {"section": "staff_mnr_user_myntreal", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/myntreal/leads": {"section": "staff_mnr_user_myntreal", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/myntreal/franchise": {"section": "staff_mnr_user_myntreal", "order": 18, "parent": "mnr-user-sidebar"},
    # Zynova (18.7)
    "/staff/mnr-user/vgk4u/dashboard": {"section": "staff_mnr_user_vgk4u", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/vgk4u/real-estate": {"section": "staff_mnr_user_vgk4u", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/vgk4u/insurance": {"section": "staff_mnr_user_vgk4u", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/vgk4u/training": {"section": "staff_mnr_user_vgk4u", "order": 18, "parent": "mnr-user-sidebar"},
    # Awards (18.8)
    "/staff/mnr-user/awards/all": {"section": "staff_mnr_user_awards", "order": 18, "parent": "mnr-user-sidebar"},
    "/staff/mnr-user/awards/bonanza": {"section": "staff_mnr_user_awards", "order": 18, "parent": "mnr-user-sidebar"},

    # ============== SECTION 21: VGK TEAM ==============
    # Subsection 21.1: VGK Team Management
    "/staff/vgk/members": {"section": "vgk_team_management", "order": 21, "parent": "vgk_team"},
    "/staff/vgk/config": {"section": "vgk_team_management", "order": 21, "parent": "vgk_team"},
    "/staff/vgk/income": {"section": "vgk_team_management", "order": 21, "parent": "vgk_team"},
    "/staff/vgk/coupons/available": {"section": "vgk_team_management", "order": 21, "parent": "vgk_team"},
    "/staff/vgk/promo-codes": {"section": "vgk_team_management", "order": 21, "parent": "vgk_team"},
    # Subsection 21.2: VGK Bonanza
    "/staff/vgk/bonanza-management": {"section": "vgk_bonanza", "order": 21, "parent": "vgk_team"},
    "/staff/vgk/bonanza-claims": {"section": "vgk_bonanza", "order": 21, "parent": "vgk_team"},

    # ============== SECTION 22: VENDOR MANAGEMENT ==============
    # Subsection 22.1: Vendor Master
    "/staff/vgk/vendors": {"section": "vm_vendor_master", "order": 22, "parent": "vendor_management"},
    "/staff/vgk/vendor-categories": {"section": "vm_vendor_master", "order": 22, "parent": "vendor_management"},
    # Subsection 22.2: Marketplace Products
    "/staff/vgk/vendor-products": {"section": "vm_products", "order": 22, "parent": "vendor_management"},
    # Subsection 22.3: Transactions
    "/staff/vgk/vendor-transactions": {"section": "vm_transactions", "order": 22, "parent": "vendor_management"},
    # Subsection 22.4: Cash Income
    "/staff/vgk/cash-income/sales": {"section": "vm_cash_income", "order": 22, "parent": "vendor_management"},
    "/staff/vgk/cash-income/accounts": {"section": "vm_cash_income", "order": 22, "parent": "vendor_management"},
    # Subsection 22.5: Wallet
    "/staff/vgk/wallet": {"section": "vm_wallet", "order": 22, "parent": "vendor_management"},

    # ============== SECTION 23: MYNT REAL ==============
    "/staff/executive-dashboard": {"section": "mynt_real", "order": 23},
    "/staff/mnr-leads": {"section": "mynt_real", "order": 23},
    "/staff/solar-leads": {"section": "mynt_real", "order": 23},
    "/staff/ev-b2b-leads": {"section": "mynt_real", "order": 23},
    "/staff/ev-b2c-leads": {"section": "mynt_real", "order": 23},
    "/staff/ev-spares-leads": {"section": "mynt_real", "order": 23},
    "/staff/real-dreams-leads": {"section": "mynt_real", "order": 23},
    "/staff/insurance-leads": {"section": "mynt_real", "order": 23},
    "/staff/etc-leads": {"section": "mynt_real", "order": 23},
}

logger = logging.getLogger(__name__)

def get_section_for_route(route_path: str) -> dict:
    """Get section info for a given route path."""
    if route_path in SIDEBAR_ROUTE_MAPPING:
        return SIDEBAR_ROUTE_MAPPING[route_path]
    for pattern, section_info in SIDEBAR_ROUTE_MAPPING.items():
        if route_path.startswith(pattern.rstrip('/')):
            return section_info
    return {"section": "staff-dashboard", "order": 2}

REQUIRED_CANONICAL_ROUTES = [
    {
        "route_path": "/staff/tasks/day-planner",
        "section_id": "task-management",
        "section_title": "TASK MANAGEMENT",
        "section_order": 5,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Task Planner",
        "menu_icon": "fas fa-calendar-day"
    },
    {
        "route_path": "/staff/mnr/awards-management",
        "section_id": "mnr-awards",
        "section_title": "Awards",
        "section_order": 17,
        "subsection_title": "Awards",
        "is_submenu": True,
        "parent_section": "mnr",
        "menu_name": "Awards Management",
        "menu_icon": "fas fa-trophy"
    },
    {
        "route_path": "/staff/mnr/field-allowances",
        "section_id": "mnr-users",
        "section_title": "Users",
        "section_order": 17,
        "subsection_title": "Users",
        "is_submenu": True,
        "parent_section": "mnr",
        "menu_name": "Allowances",
        "menu_icon": "fas fa-car"
    },
    {
        "route_path": "/staff/mnr/income-unified",
        "section_id": "mnr-income",
        "section_title": "Income",
        "section_order": 17,
        "subsection_title": "Income",
        "is_submenu": True,
        "parent_section": "mnr",
        "menu_name": "Income Management",
        "menu_icon": "fas fa-chart-line"
    },
    {
        "route_path": "/staff/mnr/terms-versions",
        "section_id": "mnr-config",
        "section_title": "System Configuration",
        "section_order": 17,
        "subsection_title": "System Configuration",
        "is_submenu": True,
        "parent_section": "mnr",
        "menu_name": "T&C Versions",
        "menu_icon": "fas fa-file-contract"
    },
    {
        "route_path": "/staff/mnr/terms-editor",
        "section_id": "mnr-config",
        "section_title": "System Configuration",
        "section_order": 17,
        "subsection_title": "System Configuration",
        "is_submenu": True,
        "parent_section": "mnr",
        "menu_name": "T&C Editor",
        "menu_icon": "fas fa-edit"
    },
    {
        "route_path": "/staff/mnr/terms-audit",
        "section_id": "mnr-config",
        "section_title": "System Configuration",
        "section_order": 17,
        "subsection_title": "System Configuration",
        "is_submenu": True,
        "parent_section": "mnr",
        "menu_name": "T&C Audit",
        "menu_icon": "fas fa-history"
    },
    {
        "route_path": "/staff/vgk4u/purchase-orders",
        "section_id": "marketplace",
        "section_title": "Marketplace",
        "section_order": 12,
        "subsection_title": "Marketplace",
        "is_submenu": True,
        "parent_section": "accounts",
        "menu_name": "EV Spares PO Management",
        "menu_icon": "fas fa-shopping-cart"
    },
    {
        "route_path": "/staff/marketplace-config",
        "section_id": "marketplace",
        "section_title": "Marketplace",
        "section_order": 12,
        "subsection_title": "Marketplace",
        "is_submenu": True,
        "parent_section": "accounts",
        "menu_name": "Marketplace Config",
        "menu_icon": "fas fa-cog"
    },
    {
        "route_path": "/staff/vgk4u/etc-students",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U Marketplace",
        "section_order": 16,
        "subsection_title": "VGK4U Marketplace",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "ETC Student Master",
        "menu_icon": "fas fa-user-graduate"
    },
    {
        "route_path": "/staff/dialer",
        "section_id": "crm",
        "section_title": "CRM & LEADS",
        "section_order": 3,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Auto Dialer",
        "menu_icon": "fas fa-phone-volume"
    },
    # ── CRM & LEADS pages ────────────────────────────────────────────────────
    {
        "route_path": "/staff/call-management",
        "section_id": "crm",
        "section_title": "CRM & LEADS",
        "section_order": 3,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Call Management",
        "menu_icon": "fas fa-phone-alt"
    },
    {
        "route_path": "/staff/operator-calls",
        "section_id": "crm",
        "section_title": "CRM & LEADS",
        "section_order": 3,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Operator Calls",
        "menu_icon": "fas fa-headphones"
    },
    {
        # DC_SAAS_CONSOLE_001: moved to VGK SaaS section (supreme-only).
        "route_path": "/staff/lead-sync",
        "section_id": "vgk-saas",
        "section_title": "VGK SAAS",
        "section_order": 13,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Lead Sync",
        "menu_icon": "fas fa-arrows-rotate"
    },
    {
        "route_path": "/staff/lead-category",
        "section_id": "crm",
        "section_title": "CRM & LEADS",
        "section_order": 4,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Lead Categories",
        "menu_icon": "fas fa-tags"
    },
    # ── Staff Dashboard pages ─────────────────────────────────────────────────
    {
        "route_path": "/staff/overview",
        "section_id": "staff-dashboard",
        "section_title": "STAFF DASHBOARD",
        "section_order": 2,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "My Overview",
        "menu_icon": "fas fa-chart-bar"
    },
    # ── KRA Management ────────────────────────────────────────────────────────
    {
        "route_path": "/staff/kra-status",
        "section_id": "kra-management",
        "section_title": "KRA MANAGEMENT",
        "section_order": 6,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "KRA Status",
        "menu_icon": "fas fa-bullseye"
    },
    # ── Configuration pages ───────────────────────────────────────────────────
    {
        "route_path": "/staff/income-trigger",
        "section_id": "configuration",
        "section_title": "CONFIGURATION",
        "section_order": 14,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Income Trigger",
        "menu_icon": "fas fa-bolt"
    },
    {
        # DC_SAAS_CONSOLE_001: moved to VGK SaaS section (supreme-only).
        "route_path": "/staff/page-registry",
        "section_id": "vgk-saas",
        "section_title": "VGK SAAS",
        "section_order": 13,
        "subsection_title": None,
        "is_submenu": False,
        "parent_section": None,
        "menu_name": "Page Registry",
        "menu_icon": "fas fa-list-alt"
    },
    # ── VGK4U pages ───────────────────────────────────────────────────────────
    {
        "route_path": "/staff/vgk/members",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Members",
        "menu_icon": "fas fa-users"
    },
    {
        "route_path": "/staff/vgk/config",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Config",
        "menu_icon": "fas fa-cog"
    },
    {
        "route_path": "/staff/vgk/coupons/available",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK PIN Activation",
        "menu_icon": "fas fa-ticket-alt"
    },
    {
        "route_path": "/staff/vgk/promo-codes",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK Promo Codes",
        "menu_icon": "fas fa-tags"
    },
    {
        "route_path": "/staff/vgk/income",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Income",
        "menu_icon": "fas fa-hand-holding-usd"
    },
    {
        "route_path": "/staff/vgk/wallet",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Wallet",
        "menu_icon": "fas fa-wallet"
    },
    {
        "route_path": "/staff/vgk/bonanza-claims",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Bonanza Claims",
        "menu_icon": "fas fa-gift"
    },
    {
        "route_path": "/staff/vgk/bonanza-management",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Bonanza Management",
        "menu_icon": "fas fa-star"
    },
    # ── VGK4U Vendor pages ────────────────────────────────────────────────────
    {
        "route_path": "/staff/vgk/vendors",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U Vendors",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Vendors",
        "menu_icon": "fas fa-store"
    },
    {
        "route_path": "/staff/vgk/vendor-categories",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U Vendors",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Vendor Categories",
        "menu_icon": "fas fa-sitemap"
    },
    {
        "route_path": "/staff/vgk/vendor-products",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U Vendors",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Vendor Products",
        "menu_icon": "fas fa-box"
    },
    {
        "route_path": "/staff/vgk/vendor-transactions",
        "section_id": "zy-member-earnings",
        "section_title": "VGK4U",
        "section_order": 16,
        "subsection_title": "VGK4U Vendors",
        "is_submenu": True,
        "parent_section": "zynova",
        "menu_name": "VGK4U Vendor Transactions",
        "menu_icon": "fas fa-exchange-alt"
    },
    # ── Marketplace pages (moved to Accounts > 12.4) ──────────────────────────
    {
        "route_path": "/staff/marketplace/codes-segments",
        "section_id": "marketplace",
        "section_title": "Marketplace",
        "section_order": 12,
        "subsection_title": "Marketplace",
        "is_submenu": True,
        "parent_section": "accounts",
        "menu_name": "Marketplace Codes & Segments",
        "menu_icon": "fas fa-barcode"
    },
]

def ensure_pdf_canonical_routes_table_and_seed(db_session):
    """
    DC Protocol Mar 2026: Create pdf_canonical_routes table if missing, then seed ALL
    routes from SIDEBAR_ROUTE_MAPPING + SIDEBAR_SECTIONS + REQUIRED_CANONICAL_ROUTES.
    Uses ON CONFLICT DO UPDATE so structure is always correct.
    Also enriches menu_name/icon from existing staff_menu_registry where available.
    Must run BEFORE ensure_canonical_routes and sync_menu_registry_sections.

    DC Protocol Apr 2026: Session-level advisory lock (key 88776656) prevents both
    uvicorn workers from seeding simultaneously and causing INSERT deadlocks at startup.
    """
    _lock_acquired = False
    try:
        # STEP 0: Acquire session-level advisory lock — only one worker seeds at a time.
        # pg_try_advisory_lock is session-scoped (survives commits), released in finally.
        _lock_result = db_session.execute(
            text("SELECT pg_try_advisory_lock(88776656)")
        ).scalar()
        if not _lock_result:
            print("[DC-PDF-CANONICAL-DDL] Advisory lock held by peer worker — skipping seed (idempotent)", flush=True)
            return True
        _lock_acquired = True

        # Step 1: Create table DDL (idempotent)
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS pdf_canonical_routes (
                id SERIAL PRIMARY KEY,
                route_path TEXT NOT NULL UNIQUE,
                section_id TEXT NOT NULL,
                section_title TEXT,
                section_order INTEGER DEFAULT 1,
                subsection_title TEXT,
                is_submenu BOOLEAN DEFAULT FALSE,
                parent_section TEXT,
                menu_name TEXT,
                menu_icon TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        db_session.commit()
        logger.info("[DC-PDF-CANONICAL-DDL] Table ensured")

        # Step 2: Build section title/order lookup from SIDEBAR_SECTIONS
        section_info = {}
        for sec in SIDEBAR_SECTIONS:
            sid = sec["id"]
            if sid not in section_info:
                section_info[sid] = {
                    "title": sec["title"],
                    "order": sec["order"],
                    "parent": sec.get("parent"),
                }

        # Step 3: Seed from SIDEBAR_ROUTE_MAPPING (all 18 sections, every route)
        seeded = 0
        for route_path, route_info in SIDEBAR_ROUTE_MAPPING.items():
            section_id = route_info.get("section", "")
            section_order = route_info.get("order", 99)
            parent_section = route_info.get("parent")
            is_submenu = parent_section is not None

            sec_data = section_info.get(section_id, {})
            section_title = sec_data.get("title", section_id.upper().replace("-", " "))

            # Subsection title = title of this section when it is a subsection
            subsection_title = section_title if is_submenu else None

            # Derive menu_name from route_path last segment (will be overridden in Step 5)
            menu_name = route_path.rsplit("/", 1)[-1].replace("-", " ").title()
            menu_icon = "fas fa-file"

            db_session.execute(text("""
                INSERT INTO pdf_canonical_routes
                (route_path, section_id, section_title, section_order,
                 subsection_title, is_submenu, parent_section, menu_name, menu_icon)
                VALUES (:route_path, :section_id, :section_title, :section_order,
                        :subsection_title, :is_submenu, :parent_section, :menu_name, :menu_icon)
                ON CONFLICT (route_path) DO UPDATE SET
                    section_id      = EXCLUDED.section_id,
                    section_title   = EXCLUDED.section_title,
                    section_order   = EXCLUDED.section_order,
                    subsection_title = EXCLUDED.subsection_title,
                    is_submenu      = EXCLUDED.is_submenu,
                    parent_section  = EXCLUDED.parent_section
            """), {
                "route_path": route_path,
                "section_id": section_id,
                "section_title": section_title,
                "section_order": section_order,
                "subsection_title": subsection_title,
                "is_submenu": is_submenu,
                "parent_section": parent_section,
                "menu_name": menu_name,
                "menu_icon": menu_icon,
            })
            seeded += 1

        db_session.commit()
        logger.info(f"[DC-PDF-CANONICAL-SEED] SIDEBAR_ROUTE_MAPPING: {seeded} routes processed (structure corrected)")

        # Step 4: Seed REQUIRED_CANONICAL_ROUTES - only update menu_name/icon, NOT section structure
        # IMPORTANT: SIDEBAR_ROUTE_MAPPING is the canonical structure source (correct section IDs
        # and orders). REQUIRED_CANONICAL_ROUTES may have old/legacy section IDs so we only
        # use it to enrich menu_name and menu_icon, never to override section structure.
        for route in REQUIRED_CANONICAL_ROUTES:
            db_session.execute(text("""
                INSERT INTO pdf_canonical_routes
                (route_path, section_id, section_title, section_order,
                 subsection_title, is_submenu, parent_section, menu_name, menu_icon)
                VALUES (:route_path, :section_id, :section_title, :section_order,
                        :subsection_title, :is_submenu, :parent_section, :menu_name, :menu_icon)
                ON CONFLICT (route_path) DO UPDATE SET
                    menu_name = EXCLUDED.menu_name,
                    menu_icon = EXCLUDED.menu_icon
            """), route)
        db_session.commit()
        logger.info(f"[DC-PDF-CANONICAL-SEED] REQUIRED_CANONICAL_ROUTES: {len(REQUIRED_CANONICAL_ROUTES)} routes processed")

        # Step 5: Enrich menu_name / menu_icon from existing staff_menu_registry
        try:
            db_session.execute(text("""
                UPDATE pdf_canonical_routes c
                SET
                    menu_name = COALESCE(NULLIF(r.menu_name, ''), c.menu_name),
                    menu_icon = COALESCE(NULLIF(r.menu_icon, ''), c.menu_icon)
                FROM staff_menu_registry r
                WHERE r.route_path = c.route_path
                AND (r.menu_name IS NOT NULL AND r.menu_name <> '')
            """))
            db_session.commit()
            logger.info("[DC-PDF-CANONICAL-SEED] Enriched menu_name/icon from registry")
        except Exception as _enrich_err:
            logger.warning(f"[DC-PDF-CANONICAL-SEED] Enrich step skipped (non-fatal): {_enrich_err}")
            db_session.rollback()

        return True
    except Exception as e:
        logger.error(f"[DC-PDF-CANONICAL-DDL] Fatal error: {e}")
        db_session.rollback()
        return False
    finally:
        if _lock_acquired:
            try:
                db_session.execute(text("SELECT pg_advisory_unlock(88776656)"))
                db_session.commit()
                print("[DC-PDF-CANONICAL-DDL] Advisory lock released", flush=True)
            except Exception:
                pass


def ensure_canonical_routes(db_session):
    """
    DC Protocol Feb 2026: Ensure all required canonical routes exist in pdf_canonical_routes.
    This runs BEFORE sync_menu_registry_sections to guarantee production has all routes.
    Only inserts missing entries - never modifies existing ones.
    """
    try:
        added = 0
        for route in REQUIRED_CANONICAL_ROUTES:
            existing = db_session.execute(
                text("SELECT 1 FROM pdf_canonical_routes WHERE route_path = :rp"),
                {"rp": route["route_path"]}
            ).fetchone()
            if not existing:
                db_session.execute(text("""
                    INSERT INTO pdf_canonical_routes 
                    (route_path, section_id, section_title, section_order, subsection_title, is_submenu, parent_section, menu_name, menu_icon)
                    VALUES (:route_path, :section_id, :section_title, :section_order, :subsection_title, :is_submenu, :parent_section, :menu_name, :menu_icon)
                """), route)
                added += 1
                logger.info(f"[DC-CANONICAL-SEED] Added missing canonical route: {route['route_path']}")
        if added > 0:
            db_session.commit()
            logger.info(f"[DC-CANONICAL-SEED] Seeded {added} missing canonical routes")
        else:
            logger.info("[DC-CANONICAL-SEED] All canonical routes already exist")
        return added
    except Exception as e:
        logger.error(f"[DC-CANONICAL-SEED] Error seeding canonical routes: {e}")
        db_session.rollback()
        return 0

def sync_menu_registry_sections(db_session):
    """
    DC Protocol Jan 13 2026: Sync menu registry from pdf_canonical_routes table.
    This is the SINGLE SOURCE OF TRUTH - deactivates all non-canonical routes.
    DC Protocol Mar 17 2026: Advisory lock prevents deadlock when 2 uvicorn workers
    both run this at startup simultaneously.
    DC Protocol Apr 2026: Added retry-on-deadlock so races with other startup tasks
    (DC_VENDOR_MENU_001 etc) that also write staff_menu_master can recover gracefully.
    """
    import time as _time
    _max_retries = 3
    for _attempt in range(_max_retries):
        try:
            return _sync_menu_registry_sections_inner(db_session)
        except Exception as _e:
            _is_deadlock = 'deadlock' in str(_e).lower()
            if _is_deadlock and _attempt < _max_retries - 1:
                logger.warning(f"[DC-SIDEBAR-SYNC] Deadlock on attempt {_attempt + 1} — retrying in {(_attempt + 1) * 2}s")
                db_session.rollback()
                _time.sleep((_attempt + 1) * 2)
            else:
                logger.error(f"[DC-SIDEBAR-SYNC] Error: {_e}")
                db_session.rollback()
                return False
    return False


def _sync_menu_registry_sections_inner(db_session):
    """Inner implementation — called by sync_menu_registry_sections with retry wrapper."""
    try:
        # Acquire a TRANSACTION-level advisory lock (key: 88776655).
        # Transaction-level locks release automatically on commit/rollback,
        # preventing permanent lock hold-over via connection pool idle connections.
        lock_acquired = db_session.execute(
            text("SELECT pg_try_advisory_xact_lock(88776655)")
        ).scalar()
        if not lock_acquired:
            logger.info("[DC-SIDEBAR-SYNC] Advisory lock busy — another worker is syncing, skipping")
            return "skipped (concurrent worker)"

        # Step 1: Deactivate ALL staff-scope routes in both tables
        # DC_PARTNER_MENUS_001 (Apr 2026): partner/shared scope menus are managed separately
        # and must NOT be deactivated by this sync (they are not in pdf_canonical_routes)
        # DC_VGK4U_MEMBER_001 (May 2026 Task #33): vgk_member-scope is also managed separately
        db_session.execute(text("UPDATE staff_menu_registry SET is_active = false WHERE audience_scope NOT IN ('partner', 'shared', 'vgk_member')"))
        db_session.execute(text("UPDATE staff_menu_master SET is_active = false WHERE audience_scope NOT IN ('partner', 'shared', 'vgk_member')"))
        
        # Step 2a: Insert any canonical routes missing from registry
        db_session.execute(text("""
            INSERT INTO staff_menu_registry (menu_code, menu_name, route_path, menu_category, menu_icon, display_order, audience_scope, source, is_default_visible, is_default_accessible, is_active, is_system_default, sidebar_section, sidebar_section_title, sidebar_section_order, is_submenu, parent_section, menu_type)
            SELECT 
                REPLACE(REPLACE(TRIM(LEADING '/' FROM c.route_path), '/', '_'), '-', '_'),
                c.menu_name,
                c.route_path,
                c.section_id,
                c.menu_icon,
                1,
                'staff',
                'canonical_seed',
                true, true, true, true,
                c.section_id,
                COALESCE(c.subsection_title, c.section_title),
                c.section_order,
                c.is_submenu,
                c.parent_section,
                'page'
            FROM pdf_canonical_routes c
            WHERE NOT EXISTS (
                SELECT 1 FROM staff_menu_registry r WHERE r.route_path = c.route_path
            )
        """))

        # Step 2b: Activate ONLY canonical routes in Registry with all correct fields
        db_session.execute(text("""
            UPDATE staff_menu_registry r
            SET 
                is_active = true,
                sidebar_section = c.section_id,
                sidebar_section_title = COALESCE(c.subsection_title, c.section_title),
                sidebar_section_order = c.section_order,
                is_submenu = c.is_submenu,
                parent_section = c.parent_section,
                menu_name = c.menu_name,
                menu_icon = c.menu_icon
            FROM pdf_canonical_routes c
            WHERE r.route_path = c.route_path
        """))
        
        # Step 3a: Insert any canonical routes missing from master (for all active companies)
        db_session.execute(text("""
            INSERT INTO staff_menu_master (company_id, menu_code, menu_name, route_path, menu_category, menu_icon, display_order, audience_scope, is_active, is_default_visible, is_default_accessible)
            SELECT 
                ac.id,
                REPLACE(REPLACE(TRIM(LEADING '/' FROM c.route_path), '/', '_'), '-', '_'),
                c.menu_name,
                c.route_path,
                c.section_id,
                c.menu_icon,
                1,
                'staff',
                true,
                false,
                false
            FROM pdf_canonical_routes c
            CROSS JOIN associated_companies ac
            WHERE ac.is_active = true
            AND NOT EXISTS (
                SELECT 1 FROM staff_menu_master m 
                WHERE m.route_path = c.route_path AND m.company_id = ac.id
            )
        """))

        # Step 3b: Set is_default_visible=true ONLY for newly-seeded canonical master entries
        # (those that were just inserted and have source='canonical_seed' in registry)
        # This avoids widening access for existing menus that were intentionally restricted
        db_session.execute(text("""
            UPDATE staff_menu_master m
            SET is_default_visible = true, is_default_accessible = true
            FROM staff_menu_registry r
            WHERE r.route_path = m.route_path
            AND r.source = 'canonical_seed'
            AND m.is_active = true
        """))

        # Step 3c: Activate ONLY canonical routes in Master + propagate sidebar_section
        db_session.execute(text("""
            UPDATE staff_menu_master m
            SET 
                is_active = true,
                menu_name = c.menu_name,
                menu_icon = c.menu_icon,
                sidebar_section = c.section_id,
                sidebar_section_title = COALESCE(c.subsection_title, c.section_title),
                sidebar_section_order = c.section_order
            FROM pdf_canonical_routes c
            WHERE m.route_path = c.route_path
        """))
        
        # Get counts for logging
        registry_count = db_session.execute(text(
            "SELECT COUNT(*) FROM staff_menu_registry WHERE is_active = true"
        )).scalar()
        master_count = db_session.execute(text(
            "SELECT COUNT(*) FROM staff_menu_master WHERE is_active = true"
        )).scalar()
        
        db_session.commit()
        logger.info(f"[DC-SIDEBAR-SYNC] Synced from pdf_canonical_routes: Registry={registry_count}, Master={master_count}")
        return {"registry": registry_count, "master": master_count}
    except Exception as e:
        logger.error(f"[DC-SIDEBAR-SYNC] Error: {e}")
        db_session.rollback()
        return False

def get_all_sections():
    """Return all sidebar sections."""
    return SIDEBAR_SECTIONS

def get_parent_sections():
    """Return only parent sections (order 1-18)."""
    return [s for s in SIDEBAR_SECTIONS if s.get("parent") is None]
