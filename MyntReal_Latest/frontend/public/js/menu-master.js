/**
 * MENU MASTER - Single Source of Truth for Staff Sidebar
 * DC_LAYOUT_PHASE_1: CREATE_MENU_MASTER_FROM_PDF
 * Created: Jan 22, 2026
 * 
 * Source: Final Side bar-2.pdf (PERORMANCE_REPORT_-_Final_Side_bar-2_1769075926029.pdf)
 * 
 * RULES:
 * - This file is the ONLY source of truth for sidebar menus
 * - All menus, labels, and routes are exactly as defined in the PDF
 * - No inference or invention of pages
 * - No renaming of menu labels
 * - No removal of any menu from the PDF
 */

const MENU_MASTER = [
  {
    section_code: "PROGRESS",
    section_label: "PROGRESS",
    order: 1,
    items: [
      { menu_code: "PROGRESS_DASHBOARD", label: "Progress Dashboard", route: "/staff/progress", audience: ["STAFF"] },
      { menu_code: "DAY_PLANNER", label: "Task Planner", route: "/staff/tasks/day-planner", audience: ["STAFF"] },
      { menu_code: "KRA_STATUS", label: "KRA Status", route: "/staff/kra-status", audience: ["STAFF"] },
      { menu_code: "MY_TIMESHEET", label: "Time Sheet", route: "/staff/timesheet", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "STAFF_DASHBOARD",
    section_label: "STAFF DASHBOARD",
    order: 2,
    items: [
      { menu_code: "DASHBOARD", label: "Dashboard", route: "/staff/dashboard", audience: ["STAFF"] },
      { menu_code: "EMPLOYEES", label: "Employees", route: "/staff/employees", audience: ["STAFF"] },
      { menu_code: "EMPLOYEE_DIRECTORY", label: "Employee Directory", route: "/staff/employee-directory", audience: ["STAFF"] },
      { menu_code: "OFFBOARDING", label: "Offboarding & Transfer", route: "/staff/offboarding", audience: ["STAFF"] },
      { menu_code: "TRAINING_VIDEOS", label: "Training Videos", route: "/staff/training-videos", audience: ["STAFF"] },
      { menu_code: "MY_KYC", label: "My KYC", route: "/staff/my-kyc", audience: ["STAFF"] },
      { menu_code: "KYC_APPROVALS", label: "KYC Approvals", route: "/staff/kyc-approvals", audience: ["STAFF"] },
      { menu_code: "REVIEW_DASHBOARD", label: "Review Dashboard", route: "/staff/manager-review", audience: ["STAFF"] },
      { menu_code: "STAFF_MY_LEAD_INCENTIVES", label: "My Earnings", route: "/staff/my-lead-incentives", audience: ["STAFF"] },
      { menu_code: "MY_REIMBURSEMENT_CLAIMS", label: "My Reimbursement Claims", route: "/staff/accounts/my-reimbursements", audience: ["STAFF"] },
      { menu_code: "REIMBURSEMENT_APPROVALS", label: "Reimbursement Approvals", route: "/staff/accounts/reimbursement-approvals", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "ATTENDANCE",
    section_label: "ATTENDANCE",
    order: 3,
    items: [
      { menu_code: "IN_OUT_TIME", label: "In/Out Time", route: "/staff/my-attendance", audience: ["STAFF"] },
      { menu_code: "MY_LEAVES", label: "My Leaves", route: "/staff/my-leaves", audience: ["STAFF"] },
      { menu_code: "LEAVE_APPROVALS", label: "Leave Approvals", route: "/staff/leave-approvals", audience: ["STAFF"] },
      { menu_code: "IN_OUT_RECORDS_ADMIN", label: "In/Out Records - Admin", route: "/staff/team-attendance", audience: ["STAFF"] },
      { menu_code: "ATTENDANCE_RECORDS", label: "Attendance Records", route: "/staff/attendance-sheet", audience: ["STAFF"] },
      { menu_code: "ATTENDANCE_DASHBOARD", label: "Attendance Dashboard", route: "/staff/attendance-reports", audience: ["STAFF"] },
      { menu_code: "EXCEPTION_APPROVALS", label: "Exception Approvals", route: "/staff/attendance-exceptions", audience: ["STAFF"] },
      { menu_code: "ATTENDANCE_COMPUTATION", label: "Attendance Computation", route: "/staff/attendance-computation", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "CRM_LEADS",
    section_label: "CRM & LEADS",
    order: 4,
    items: [
      { menu_code: "MY_CRM_DASHBOARD", label: "CRM Dashboard", route: "/staff/crm/dashboard", audience: ["STAFF"] },
      { menu_code: "STAFF_LEADS", label: "Staff Leads", route: "/staff/leads", audience: ["STAFF"] },
      { menu_code: "TEAM_LEADS", label: "Team Leads", route: "/staff/crm/team-leads", audience: ["STAFF"] },
      { menu_code: "MY_LEADS", label: "My Leads", route: "/staff/my-leads", audience: ["STAFF"] },
      { menu_code: "LEAD_SOURCES", label: "Lead Sources", route: "/staff/crm/lead-sources", audience: ["STAFF"] },
      { menu_code: "CALL_TRACKING_DASHBOARD", label: "Call Management", route: "/staff/call-management", audience: ["STAFF"] },
      { menu_code: "AUTO_DIALER", label: "Auto Dialer", route: "/staff/dialer", audience: ["STAFF"] },
      { menu_code: "CALL_QUALITY_REVIEW", label: "Call Quality Review", route: "/staff/call-quality", audience: ["STAFF"] },
      { menu_code: "STAFF_OPERATOR_CALLS", label: "Operator Calls", route: "/staff/operator-calls", audience: ["STAFF"] },
      { menu_code: "CRM_SALES_REPORT", label: "Sales Team Report", route: "/staff/crm/sales-report", audience: ["STAFF"] },
      { menu_code: "CRM_WA_INBOX", label: "WA Inbox (CRM)", route: "/staff/crm/whatsapp-inbox", icon: "fab fa-whatsapp", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "TASK_MANAGEMENT",
    section_label: "TASK MANAGEMENT",
    order: 5,
    items: [
      { menu_code: "TASK_TRACKER", label: "Task Dashboard", route: "/staff/tasks/tracker", audience: ["STAFF"] },
      { menu_code: "ASSIGNED_BY_ME", label: "Assigned By Me", route: "/staff/tasks/assigned-by-me-v2", audience: ["STAFF"] },
      { menu_code: "ASSIGNED_TO_ME", label: "Assigned To Me", route: "/staff/tasks/assigned-to-me", audience: ["STAFF"] },
      { menu_code: "TEAM_ACTIVITIES", label: "Team Activities", route: "/staff/tasks/team-activities", audience: ["STAFF"] },
      { menu_code: "TASK_REVIEWS", label: "Task Reviews", route: "/staff/task-review", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "KRA_MANAGEMENT",
    section_label: "KRA MANAGEMENT",
    order: 6,
    items: [
      { menu_code: "MY_KRAS", label: "My KRAs", route: "/staff/my-kras", audience: ["STAFF"] },
      { menu_code: "KRA_TEMPLATES", label: "KRA Templates", route: "/staff/kra-templates", audience: ["STAFF"] },
      { menu_code: "KRA_TRACKING_SHEET", label: "KRA Tracking Sheet", route: "/staff/kra-tracking-sheet", audience: ["STAFF"] },
      { menu_code: "KRA_REVIEW", label: "KRA Review", route: "/staff/kra-status#reviews", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "JOURNEY_TRACKING",
    section_label: "JOURNEY TRACKING",
    order: 7,
    items: [
      { menu_code: "MY_JOURNEYS", label: "My Journeys", route: "/staff/my-journeys", audience: ["STAFF"] },
      { menu_code: "TEAM_JOURNEYS", label: "Team Journeys", route: "/staff/team-journeys", audience: ["STAFF"] },
      { menu_code: "ALL_JOURNEYS", label: "All Journeys", route: "/staff/all-journeys", audience: ["STAFF"] },
      { menu_code: "VGK4U_JOURNEYS", label: "VGK4U Journeys", route: "/staff/vgk4u-journeys", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "LOCATION_TRACKING",
    section_label: "LOCATION TRACKING",
    order: 8,
    items: [
      { menu_code: "MY_LOCATION_HISTORY", label: "My Location History", route: "/staff/my-location-history", audience: ["STAFF"] },
      { menu_code: "TEAM_LOCATION_TRACKER", label: "Team Location Tracker", route: "/staff/team-location-tracker", audience: ["STAFF"] },
      { menu_code: "ALL_LOCATION_TRACKER", label: "All Location Tracker", route: "/staff/all-location-tracker", audience: ["STAFF"] },
      { menu_code: "TEAM_LIVE_TRACKER", label: "Team Live Tracker", route: "/staff/team-live-tracker", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "SERVICE_TICKETS",
    section_label: "SERVICE TICKETS",
    order: 10,
    items: [
      { menu_code: "ST_SERVICE_QUEUE", label: "Service Queue", route: "/staff/service-tickets/queue", audience: ["STAFF"] },
      { menu_code: "ST_DASHBOARD", label: "Dashboard", route: "/staff/service-tickets/dashboard", audience: ["STAFF"] },
      { menu_code: "SERVICE_CENTER_TRACKING", label: "Service Center Tracking", route: "/staff/inventory/service-center-tracking", audience: ["STAFF"] },
      { menu_code: "ST_PROCUREMENT_QUEUE", label: "Procurement Queue", route: "/staff/service-tickets/procurement-queue", audience: ["STAFF"] },
      { menu_code: "ST_RAISE_TICKET", label: "Raise Ticket", route: "/staff/service-tickets/raise", audience: ["STAFF"] },
      { menu_code: "ST_SERVICE_CENTER_REVENUE", label: "Service Center Revenue", route: "/staff/service-center-revenue", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "ACCOUNTS",
    section_label: "ACCOUNTS",
    order: 11,
    subSections: [
      {
        sub_section_code: "SFMS",
        sub_section_label: "SFMS (12.1)",
        items: [
          { menu_code: "FUND_ALLOCATIONS", label: "Fund Allocations", route: "/staff/accounts/fund-allocations", audience: ["STAFF"] },
          { menu_code: "EXPENSE_ENTRIES", label: "Expense Entries", route: "/staff/accounts/expense-entries", audience: ["STAFF"] },
          { menu_code: "INCOME_ENTRIES", label: "Income Entries", route: "/staff/accounts/income-entries", audience: ["STAFF"] },
          { menu_code: "PENDING_TO_CLEAR", label: "Pending to Clear", route: "/staff/accounts/pending-to-clear", audience: ["STAFF"] },
          { menu_code: "PARTIES_MASTER", label: "Parties Master", route: "/staff/accounts/parties", icon: "fas fa-users", audience: ["STAFF"] },
          { menu_code: "sfms_capital_account", label: "Capital Account", route: "/staff/accounts/capital", icon: "fas fa-coins", audience: ["STAFF"] },
          { menu_code: "sfms_cash_in_hand", label: "Cash in Hand", route: "/staff/accounts/cash-in-hand", icon: "fas fa-hand-holding-usd", audience: ["STAFF"] },
          { menu_code: "sfms_duties_taxes", label: "Duties & Taxes", route: "/staff/accounts/duties-taxes", icon: "fas fa-percent", audience: ["STAFF"] },
          { menu_code: "VENDORS", label: "Vendors", route: "/staff/accounts/vendors", audience: ["STAFF"] },
          { menu_code: "PURCHASE_INVOICES", label: "Purchase Invoices", route: "/staff/accounts/purchase-invoices", audience: ["STAFF"] },
          { menu_code: "SALES_INVOICES", label: "Sales Invoices", route: "/staff/accounts/sales-invoices", audience: ["STAFF"] },
          { menu_code: "INVOICE_REPORTS", label: "Invoice Reports", route: "/staff/accounts/reports", audience: ["STAFF"] },
          { menu_code: "ACCOUNTS_PAYABLE", label: "Accounts Payable", route: "/staff/accounts/payables", audience: ["STAFF"] },
          { menu_code: "ACCOUNTS_RECEIVABLE", label: "Accounts Receivable", route: "/staff/accounts/receivables", audience: ["STAFF"] },
          { menu_code: "SALES_TEAM_REVENUE", label: "Sales Team Revenue", route: "/rvz/sales-revenue", audience: ["STAFF"] },
          { menu_code: "PARTY_LEDGER", label: "Party Ledger", route: "/staff/accounts/party-ledger", audience: ["STAFF"] },
          { menu_code: "GENERAL_LEDGER", label: "General Ledger", route: "/staff/accounts/general-ledger", audience: ["STAFF"] },
          { menu_code: "JOURNAL_VOUCHER", label: "Entries", route: "/staff/accounts/journal-voucher", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "CONSOLIDATED",
        sub_section_label: "Consolidated (12.2)",
        items: [
          { menu_code: "DAR", label: "DAR", route: "/staff/accounts/DAR", audience: ["STAFF"] },
          { menu_code: "CONSOLIDATED_REPORTS", label: "Consolidated Reports", route: "/staff/consolidated", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "INVENTORY",
        sub_section_label: "Inventory (12.3)",
        items: [
          { menu_code: "BILL_OF_MATERIALS", label: "Bill of Materials", route: "/staff/inventory/bom", audience: ["STAFF"] },
          { menu_code: "MANUFACTURING", label: "Manufacturing", route: "/staff/inventory/manufacturing", audience: ["STAFF"] },
          { menu_code: "INV_PROCUREMENT", label: "Procurement", route: "/staff/inventory/procurement", audience: ["STAFF"] },
          { menu_code: "PURCHASE_INTAKE", label: "Purchase Intake", route: "/staff/inventory/intake", audience: ["STAFF"] },
          { menu_code: "STOCK_ITEMS", label: "Stock Items", route: "/staff/inventory/stock-items", audience: ["STAFF"] },
          { menu_code: "STOCK_LEDGER", label: "Stock Ledger", route: "/staff/inventory/stock-ledger", audience: ["STAFF"] },
          { menu_code: "STOCK_TRANSFERS", label: "Stock Transfers", route: "/staff/inventory/stock-transfers", audience: ["STAFF"] },
          { menu_code: "STOCK_VALIDATION", label: "Stock Validation", route: "/staff/inventory/stock-validation", audience: ["STAFF"] },
          { menu_code: "VENDOR_RETURNS", label: "Vendor Returns", route: "/staff/inventory/vendor-returns", audience: ["STAFF"] },
          { menu_code: "ACC_INV_SHEET", label: "IN&OUT", route: "/staff/inventory/accessories", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "PAYROLL",
        sub_section_label: "Payroll (12.3)",
        items: [
          { menu_code: "PAYROLL_PROFILES", label: "Payroll Profiles", route: "/staff/payroll/profiles", audience: ["STAFF"] },
          { menu_code: "PAYROLL_CYCLES", label: "Payroll Cycles", route: "/staff/payroll/cycles", audience: ["STAFF"] },
          { menu_code: "PAYROLL_RUNS", label: "Payroll Runs", route: "/staff/payroll/runs", audience: ["STAFF"] },
          { menu_code: "PAYROLL_APPROVALS", label: "Approvals", route: "/staff/payroll/approvals", audience: ["STAFF"] },
          { menu_code: "CONSULTANT_INVOICES", label: "Consultant Invoices", route: "/staff/payroll/consultant-invoices", audience: ["STAFF"] },
          { menu_code: "ALLOWANCE_CATALOG", label: "Allowance Catalog", route: "/staff/payroll/allowance-catalog", audience: ["STAFF"] },
          { menu_code: "PAYROLL_DOCUMENTS", label: "Documents", route: "/staff/payroll/documents", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MARKETPLACE",
        sub_section_label: "Marketplace (12.4)",
        items: [
          { menu_code: "VGK4U_PO_MANAGEMENT", label: "EV Spares PO Management", route: "/staff/vgk4u/purchase-orders", audience: ["STAFF"] },
          { menu_code: "VGK4U_MARKETPLACE_CONFIG", label: "Marketplace Config", route: "/staff/marketplace-config", audience: ["STAFF"] },
          { menu_code: "MARKETPLACE_CODES_SEGMENTS", label: "Marketplace Codes & Segments", route: "/staff/marketplace/codes-segments", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "ACCOUNTS_OTHER",
        sub_section_label: "Other",
        items: [
          { menu_code: "PRICING_CONFIG", label: "Pricing Config", route: "/staff/accounts/pricing", audience: ["STAFF"] },
          { menu_code: "EXPENSE_CATEGORIES", label: "Expense Categories", route: "/staff/accounts/expense-categories", audience: ["STAFF"] },
          { menu_code: "INCOME_TRIGGER", label: "Income Trigger", route: "/staff/income-trigger", audience: ["STAFF"] }
        ]
      }
    ]
  },
  {
    section_code: "BUSINESS_PARTNERS",
    section_label: "BUSINESS PARTNERS",
    order: 12,
    items: [
      { menu_code: "PARTNER_ORDERS", label: "Partner Orders", route: "/staff/partners/orders", audience: ["STAFF"] },
      { menu_code: "PARTNER_PRICING", label: "Partner Pricing", route: "/staff/partners/pricing", audience: ["STAFF"] },
      { menu_code: "ORDER_APPROVAL", label: "Order Approval", route: "/staff/partners/approval", audience: ["STAFF"] },
      { menu_code: "ORDER_ROUTING", label: "Order Routing", route: "/staff/partners/routing", audience: ["STAFF"] },
      { menu_code: "ORDER_FULFILLMENT", label: "Order Fulfillment", route: "/staff/partners/fulfillment", audience: ["STAFF"] },
      { menu_code: "DISPATCH_MANAGEMENT", label: "Dispatch Management", route: "/staff/partners/dispatch", audience: ["STAFF"] },
      { menu_code: "PARTNER_INVOICES", label: "Partner Invoices", route: "/staff/partners/invoices", audience: ["STAFF"] },
      { menu_code: "PAYMENT_VERIFICATION", label: "Payment Verification", route: "/staff/partners/payments", audience: ["STAFF"] },
      { menu_code: "PARTNER_SALES_INVOICES", label: "Partner Sales", route: "/staff/partners/sales", audience: ["STAFF"] },
      { menu_code: "PARTNER_WALKINS", label: "Partner Walk-ins", route: "/staff/partners/walkins", audience: ["STAFF"] },
      { menu_code: "PARTNER_STOCK", label: "Partner Stock", route: "/staff/partners/stock", audience: ["STAFF"] }
    ]
  },
  // DC_SAAS_CONSOLE_001 (May 2026): VGK SaaS — supreme-only consolidated SaaS controls
  {
    section_code: "VGK_SAAS",
    section_label: "VGK4U SAAS",
    order: 13,
    items: [
      { menu_code: "VGK_SAAS_ALL_TENANTS", label: "All Tenants", route: "/staff/my-tenant", icon: "fas fa-layer-group", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_TENANT_ONBOARDING", label: "Tenant Onboarding", route: "/staff/accounts/companies", icon: "fas fa-building-circle-arrow-right", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_PLATFORM_CLIENTS", label: "Platform Clients (B2B)", route: "/staff/b2b-clients", icon: "fas fa-handshake", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_PUBLIC_SIGNUP_PREVIEW", label: "Public Signup Preview", route: "/b2b-signup", icon: "fas fa-eye", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_SIGNUP_CATEGORIES", label: "Signup Categories", route: "/staff/signup-categories", icon: "fas fa-tags", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_LEAD_SYNC", label: "Lead Sync", route: "/staff/lead-sync", icon: "fas fa-arrows-rotate", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_MENU_ACCESS", label: "Menu Access Control", route: "/rvz/menu-access-config", icon: "fas fa-shield-halved", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_PAGE_REGISTRY", label: "Page Registry Manager", route: "/staff/page-registry", icon: "fas fa-sitemap", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_SIDEBAR_SYNC", label: "Sidebar Sync", route: "/staff/sidebar-sync", icon: "fas fa-rotate", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_PLATFORM_SETUP_GUIDE", label: "Platform Setup Guide", route: "/staff/day-planner-guide#sec-platform-setup", icon: "fas fa-book-open", audience: ["VGK4U"] },
      { menu_code: "VGK_SAAS_AUDIT_LOGS", label: "Audit Logs (SaaS)", route: "/staff/audit-logs", icon: "fas fa-clipboard-list", audience: ["VGK4U"] }
    ]
  },
  {
    section_code: "CONFIGURATION",
    section_label: "CONFIGURATION",
    order: 14,
    items: [
      { menu_code: "DEPARTMENTS", label: "Departments", route: "/staff/departments", audience: ["STAFF"] },
      { menu_code: "BUSINESS_PARTNERS_CONFIG", label: "Business Partners Config", route: "/staff/partners/master", audience: ["STAFF"] },
      { menu_code: "SEGMENTS", label: "Segments", route: "/staff/accounts/segments", audience: ["STAFF"] },
      { menu_code: "HSN_MASTER", label: "HSN Master", route: "/staff/accounts/hsn", audience: ["STAFF"] },
      { menu_code: "SETTINGS", label: "Settings", route: "/staff/settings", audience: ["STAFF"] },
      { menu_code: "VGK_COMMISSION_CONFIG", label: "VGK Commission Config", route: "/staff/vgk/config", audience: ["STAFF"] },
      { menu_code: "AI_CALLING", label: "AI Calling", route: "/staff/crm/ai-calling", audience: ["STAFF"] },
      { menu_code: "WA_CONFIG", label: "WhatsApp Center", route: "/staff/whatsapp-config", icon: "fab fa-whatsapp", audience: ["STAFF"] },
      { menu_code: "SOLAR_VENDORS", label: "Solar Vendors", route: "/staff/solar-vendors", icon: "fas fa-solar-panel", audience: ["STAFF"] },
      { menu_code: "VGK_MEDIA_MANAGER", label: "Media Manager", route: "/staff/vgk/media", icon: "fas fa-globe", audience: ["STAFF"] },
      { menu_code: "MNR_VIEW_ANNOUNCEMENTS", label: "View Announcements", route: "/staff/mnr/announcements/view", icon: "fas fa-globe", audience: ["STAFF"] },
      { menu_code: "MNR_USER_CREATE_ANNOUNCEMENT", label: "Create Announcement", route: "/staff/mnr-user/announcements/create", icon: "fas fa-globe", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "MNR",
    section_label: "MNR Admin",
    order: 16,
    items: [
      { menu_code: "MNR_INCOME_UNIFIED", label: "Income Management", route: "/staff/mnr/income-unified", audience: ["STAFF"] },
      { menu_code: "MNR_AWARDS_MANAGEMENT", label: "Awards Management", route: "/staff/mnr/awards-management", audience: ["STAFF"] },
      { menu_code: "MNR_PROCUREMENT_QUEUE", label: "Procurement Queue", route: "/staff/mnr/procurement-queue", audience: ["STAFF"] },
      { menu_code: "MNR_KYC_MANAGEMENT", label: "KYC Management", route: "/staff/mnr/kyc-management", audience: ["STAFF"] },
      { menu_code: "MNR_USER_DELIVERABLES", label: "User Deliverables", route: "/staff/incentives/points", audience: ["STAFF"] },
      { menu_code: "MNR_ALL_USERS", label: "All Users", route: "/staff/mnr/users", audience: ["STAFF"] },
      { menu_code: "MNR_FINANCIAL_STATEMENT", label: "Financial Statement", route: "/staff/mnr/financial-statement", audience: ["VGK4U"] }
    ],
    subSections: [
      {
        sub_section_code: "MNR_USERS",
        sub_section_label: "Users (17.1)",
        items: [
          { menu_code: "MNR_ALL_USERS", label: "All Users", route: "/staff/mnr/users", audience: ["STAFF"] },
          { menu_code: "MNR_USER_ACTIVATION_CONTROL", label: "User Activation Control", route: "/staff/mnr/user-activation-control", audience: ["STAFF"] },
          { menu_code: "MNR_BIRTHDAY_DETAILS", label: "Birthday Details", route: "/staff/mnr/birthdays", audience: ["STAFF"] },
          { menu_code: "MNR_FIELD_ALLOWANCES", label: "Allowances", route: "/staff/mnr/field-allowances", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_AWARDS",
        sub_section_label: "Awards (17.2)",
        items: [
          { menu_code: "MNR_AWARDS_CONFIGURATION", label: "Awards Configuration", route: "/staff/mnr/award-management", audience: ["STAFF"] },
          { menu_code: "MNR_BONANZA_MANAGEMENT", label: "Bonanza Management", route: "/staff/mnr/bonanza-management", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_WITHDRAWALS",
        sub_section_label: "Withdrawals (17.3)",
        items: [
          { menu_code: "MNR_WITHDRAWAL_SUPREME", label: "Withdrawal Supreme", route: "/staff/mnr/withdrawal-supreme", audience: ["STAFF"] },
          { menu_code: "MNR_WITHDRAWAL_APPROVALS", label: "Withdrawal Approvals", route: "/staff/mnr/withdrawal/approvals", audience: ["STAFF"] },
          { menu_code: "MNR_WITHDRAWAL_HISTORY", label: "Withdrawal History", route: "/staff/mnr/withdrawal/history", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_FINANCE_COMPLIANCE",
        sub_section_label: "Finance & Compliance (17.4)",
        items: [
          { menu_code: "MNR_FINANCE_SUPREME", label: "Finance Supreme", route: "/staff/mnr/finance-supreme", audience: ["STAFF"] },
          { menu_code: "MNR_FINANCIAL_STATEMENT", label: "Financial Statement", route: "/staff/mnr/financial-statement", audience: ["STAFF"] },
          { menu_code: "MNR_COMPLIANCE_DASHBOARD", label: "Compliance Dashboard", route: "/staff/mnr/compliance", audience: ["STAFF"] },
          { menu_code: "MNR_COMPANY_EARNINGS", label: "Company Earnings", route: "/staff/mnr/company-earnings", audience: ["STAFF"] },
          { menu_code: "MNR_REVENUE_DETAILS", label: "Revenue Details", route: "/staff/mnr/revenue-details", audience: ["STAFF"] },
          { menu_code: "MNR_PAYOUT_DETAILS", label: "Payout Details", route: "/staff/mnr/payout-details", audience: ["STAFF"] },
          { menu_code: "MNR_EXPENSE_DETAILS", label: "Expense Details", route: "/staff/mnr/expense-details", audience: ["STAFF"] },
          { menu_code: "MNR_EXPENSE_MANAGEMENT", label: "Expense Management", route: "/staff/mnr/expenses-management", audience: ["STAFF"] },
          { menu_code: "MNR_EXPENSE_OVERVIEW", label: "Expense Overview", route: "/staff/mnr/expense-overview", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_ANNOUNCEMENTS",
        sub_section_label: "Announcements (17.5)",
        items: [
          { menu_code: "MNR_PENDING_ANNOUNCEMENTS", label: "Pending Announcements", route: "/staff/mnr/feedback/pending", audience: ["STAFF"] },
          { menu_code: "MNR_BANNERS_MANAGEMENT", label: "Banners Management", route: "/staff/mnr/banners-management", audience: ["STAFF"] },
          { menu_code: "MNR_BANNER_ANALYTICS", label: "Banner Analytics", route: "/staff/mnr/banner-analytics", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_PINS_APPROVALS",
        sub_section_label: "PINs & Approvals (17.6)",
        items: [
          { menu_code: "MNR_PIN_APPROVALS", label: "PIN Approvals", route: "/staff/mnr/pin-approvals", audience: ["STAFF"] },
          { menu_code: "MNR_COUPON_STATUS", label: "Coupon Status", route: "/staff/mnr/coupon-status", audience: ["STAFF"] },
          { menu_code: "MNR_ALL_PINS", label: "All PINs", route: "/staff/mnr/pins", audience: ["STAFF"] },
          { menu_code: "MNR_CHANGE_USER_PASSWORD", label: "Change User Password", route: "/staff/mnr/change-user-password", audience: ["STAFF"] },
          { menu_code: "MNR_RVZ_PASSWORD_CHANGE", label: "RVZ Password Change", route: "/staff/mnr/password-change", audience: ["STAFF"] },
          { menu_code: "MNR_SECONDARY_PASSWORD_SETUP", label: "Secondary Password Setup", route: "/staff/mnr/secondary-password-setup", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_SYSTEM_CONFIG",
        sub_section_label: "System Config (17.7)",
        items: [
          { menu_code: "MNR_SYSTEM_CONTROLS", label: "System Controls", route: "/staff/mnr/system-controls", audience: ["STAFF"] },
          { menu_code: "MNR_RATE_CONFIGURATION", label: "Rate Configuration", route: "/staff/mnr/rate-configuration", audience: ["STAFF"] },
          { menu_code: "MNR_DAILY_CEILING", label: "Daily Ceiling", route: "/staff/mnr/daily-ceiling", audience: ["STAFF"] },
          { menu_code: "MNR_EMERGENCY_WALLET", label: "Emergency Wallet", route: "/staff/mnr/emergency-wallet", audience: ["STAFF"] },
          { menu_code: "MNR_PRODUCTION_RESET_STATUS", label: "Production Reset Status", route: "/staff/mnr/production-reset-status", audience: ["STAFF"] }
        ]
      },
    ]
  },
  {
    section_code: "MNR_USER_SIDEBAR",
    section_label: "MNR",
    order: 17,
    subSections: [
      {
        sub_section_code: "MNR_USER_AUDIT",
        sub_section_label: "Audit Log (18.0)",
        items: [
          { menu_code: "MNR_USER_AUDIT_LOG", label: "Audit Log", route: "/staff/mnr-user/audit-log", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_DASHBOARD",
        sub_section_label: "Dashboard (18.1)",
        items: [
          { menu_code: "MNR_USER_DASHBOARD", label: "Dashboard", route: "/staff/mnr-user/dashboard", audience: ["STAFF"] },
          { menu_code: "MNR_USER_PROFILE", label: "Profile", route: "/staff/mnr-user/profile", audience: ["STAFF"] },
          { menu_code: "MNR_USER_CREATE_MEMBER", label: "Create Member", route: "/staff/mnr-user/create-member", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_ANNOUNCEMENTS",
        sub_section_label: "Announcements (18.2)",
        items: [
          { menu_code: "MNR_USER_ANNOUNCEMENTS", label: "Announcements", route: "/staff/mnr-user/announcements", audience: ["STAFF"] },
          { menu_code: "MNR_USER_PENDING_ANNOUNCEMENTS", label: "Pending", route: "/staff/mnr-user/announcements/pending", audience: ["STAFF"] },
          { menu_code: "MNR_USER_ANNOUNCEMENTS_HISTORY", label: "History", route: "/staff/mnr-user/announcements/history", audience: ["STAFF"] },
          { menu_code: "MNR_USER_POPUPS", label: "Popups", route: "/staff/mnr-user/popups", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_COUPONS",
        sub_section_label: "Coupons (18.3)",
        items: [
          { menu_code: "MNR_USER_AVAILABLE_COUPONS", label: "Available Coupons", route: "/staff/mnr-user/coupons/available", audience: ["STAFF"] },
          { menu_code: "MNR_USER_RED_COUPONS", label: "Red Coupons", route: "/staff/mnr-user/coupons/red", audience: ["STAFF"] },
          { menu_code: "MNR_USER_GREEN_COUPONS", label: "Green Coupons", route: "/staff/mnr-user/coupons/green", audience: ["STAFF"] },
          { menu_code: "MNR_USER_EV_COUPONS", label: "EV Coupons", route: "/staff/mnr-user/coupons/ev", audience: ["STAFF"] },
          { menu_code: "MNR_USER_COUPONS_TRANSFER", label: "Transfer", route: "/staff/mnr-user/coupons/transfer", audience: ["STAFF"] },
          { menu_code: "MNR_USER_COUPONS_HISTORY", label: "History", route: "/staff/mnr-user/coupons/history", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_MEMBERS",
        sub_section_label: "Members (18.4)",
        items: [
          { menu_code: "MNR_USER_MEMBERS", label: "Members", route: "/staff/mnr-user/members", audience: ["STAFF"] },
          { menu_code: "MNR_USER_ALL_MEMBERS", label: "All Members", route: "/staff/mnr-user/members/all", audience: ["STAFF"] },
          { menu_code: "MNR_USER_DIRECT_MEMBERS", label: "Direct Members", route: "/staff/mnr-user/members/direct", audience: ["STAFF"] },
          { menu_code: "MNR_USER_DOWNLINE", label: "Downline", route: "/staff/mnr-user/members/downline", audience: ["STAFF"] },
          { menu_code: "MNR_USER_VED_MEMBERS", label: "VED Members", route: "/staff/mnr-user/members/ved", audience: ["STAFF"] },
          { menu_code: "MNR_USER_PICTURE", label: "Picture", route: "/staff/mnr-user/members/picture", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_EARNINGS",
        sub_section_label: "Earnings (18.5)",
        items: [
          { menu_code: "MNR_USER_EARNINGS", label: "Earnings", route: "/staff/mnr-user/mnr/earnings", audience: ["STAFF"] },
          { menu_code: "MNR_USER_EARNINGS_SUMMARY", label: "Earnings Summary", route: "/staff/mnr-user/mnr/earnings-summary", audience: ["STAFF"] },
          { menu_code: "MNR_USER_DIRECT_REFERRAL", label: "Direct Facilitation", route: "/staff/mnr-user/mnr/direct", audience: ["STAFF"] },
          { menu_code: "MNR_USER_MATCHING", label: "Matching", route: "/staff/mnr-user/mnr/matching", audience: ["STAFF"] },
          { menu_code: "MNR_USER_VED_INCOME", label: "VED Income", route: "/staff/mnr-user/mnr/ved", audience: ["STAFF"] },
          { menu_code: "MNR_USER_GURU_DAKSHINA", label: "Mentorship Contribution Benefit", route: "/staff/mnr-user/mnr/guru", audience: ["STAFF"] },
          { menu_code: "MNR_USER_WALLET", label: "Wallet", route: "/staff/mnr-user/mnr/wallet", audience: ["STAFF"] },
          { menu_code: "MNR_USER_WITHDRAWALS", label: "Withdrawals", route: "/staff/mnr-user/mnr/withdrawals", audience: ["STAFF"] },
          { menu_code: "MNR_USER_POINTS", label: "Points", route: "/staff/mnr-user/mnr/points", audience: ["STAFF"] },
          { menu_code: "MNR_USER_BENEFITS", label: "Benefits", route: "/staff/mnr-user/mnr/benefits", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_MYNTREAL",
        sub_section_label: "MyntReal (18.6)",
        items: [
          { menu_code: "MNR_USER_PROPERTIES", label: "Properties", route: "/staff/mnr-user/myntreal/properties", audience: ["STAFF"] },
          { menu_code: "MNR_USER_LEADS", label: "Leads", route: "/staff/mnr-user/myntreal/leads", audience: ["STAFF"] },
          { menu_code: "MNR_USER_FRANCHISE", label: "Franchise", route: "/staff/mnr-user/myntreal/franchise", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_VGK4U",
        sub_section_label: "VGK4U (18.7)",
        items: [
          { menu_code: "MNR_USER_VGK4U_DASHBOARD", label: "Dashboard", route: "/staff/mnr-user/vgk4u/dashboard", audience: ["STAFF"] },
          { menu_code: "MNR_USER_REAL_ESTATE", label: "Real Estate", route: "/staff/mnr-user/vgk4u/real-estate", audience: ["STAFF"] },
          { menu_code: "MNR_USER_INSURANCE", label: "Insurance", route: "/staff/mnr-user/vgk4u/insurance", audience: ["STAFF"] },
          { menu_code: "MNR_USER_TRAINING", label: "Training", route: "/staff/mnr-user/vgk4u/training", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "MNR_USER_AWARDS",
        sub_section_label: "Awards (18.8)",
        items: [
          { menu_code: "MNR_USER_ALL_AWARDS", label: "All Awards", route: "/staff/mnr-user/awards/all", audience: ["STAFF"] },
          { menu_code: "MNR_USER_BONANZA", label: "Bonanza", route: "/staff/mnr-user/awards/bonanza", audience: ["STAFF"] }
        ]
      }
    ]
  },
  {
    section_code: "VGK_TEAM",
    section_label: "VGK4U",
    order: 18,
    subSections: [
      {
        sub_section_code: "VGK_TEAM_MANAGEMENT",
        sub_section_label: "VGK Team Management",
        items: [
          { menu_code: "VGK_TEAM_MEMBERS", label: "VGK Members", route: "/staff/vgk/members", audience: ["STAFF"] },
          { menu_code: "VGK_INCOME_MANAGEMENT", label: "Income Management", route: "/staff/vgk/income", audience: ["STAFF"] },
          { menu_code: "VGK_COUPONS", label: "VGK PIN Activation", route: "/staff/vgk/coupons/available", audience: ["STAFF"] },
          { menu_code: "VGK_PROMO_CODES", label: "VGK Promo Codes", route: "/staff/vgk/promo-codes", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "VGK_BONANZA",
        sub_section_label: "VGK Bonanza",
        items: [
          { menu_code: "VGK_BONANZA_MANAGEMENT", label: "Bonanza Campaigns", route: "/staff/vgk/bonanza-management", audience: ["STAFF"] },
          { menu_code: "VGK_BONANZA_CLAIMS", label: "Bonanza Claims", route: "/staff/vgk/bonanza-claims", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "VGK_ADMIN",
        sub_section_label: "VGK Admin",
        items: [
          { menu_code: "VGK_INCOME_UNIFIED",       label: "Income — Unified",       route: "/staff/vgk/income-unified",       audience: ["STAFF"], icon: "fas fa-coins" },
          { menu_code: "VGK_CASH_INCOME_SALES",    label: "Cash Income (Sales)",    route: "/staff/vgk/cash-income/sales",    audience: ["STAFF"] },
          { menu_code: "VGK_CASH_INCOME_ACCOUNTS", label: "Cash Income (Accounts)", route: "/staff/vgk/cash-income/accounts", audience: ["STAFF"] },
          { menu_code: "VGK_PARTNER_KYC_REVIEW",   label: "Partner KYC Review",     route: "/staff/vgk/partner-kyc-review",   audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "VM_VENDOR_MASTER",
        sub_section_label: "Vendor Master",
        items: [
          { menu_code: "VGK_VENDORS", label: "Vendor Master", route: "/staff/vgk/vendors", audience: ["STAFF"] },
          { menu_code: "VGK_VENDOR_CATEGORIES", label: "Vendor Categories", route: "/staff/vgk/vendor-categories", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "VM_PRODUCTS",
        sub_section_label: "Marketplace Products",
        items: [
          { menu_code: "VGK_VENDOR_PRODUCTS", label: "Vendor Products", route: "/staff/vgk/vendor-products", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "VM_TRANSACTIONS",
        sub_section_label: "Transactions",
        items: [
          { menu_code: "VGK_VENDOR_TRANSACTIONS", label: "Transaction Approvals", route: "/staff/vgk/vendor-transactions", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "VM_WALLET",
        sub_section_label: "Wallet",
        items: [
          { menu_code: "VGK_WALLET_WITHDRAWALS", label: "Wallet & Withdrawals", route: "/staff/vgk/wallet", audience: ["STAFF"] }
        ]
      }
    ]
  },
  {
    section_code: "MYNT_REAL",
    section_label: "MYNTREAL",
    order: 20,
    items: [
      { menu_code: "MNR_EXECUTIVE_DASHBOARD", label: "Executive Dashboard", route: "/staff/executive-dashboard", icon: "fas fa-chart-line", audience: ["STAFF"] },
      { menu_code: "MNR_CATEGORY_LEADS", label: "Category Lead Master", route: "/staff/mnr-leads", icon: "fas fa-layer-group", audience: ["STAFF"] },
      { menu_code: "MNR_SOLAR_LEADS", label: "Solar Leads", route: "/staff/solar-leads", icon: "fas fa-solar-panel", audience: ["STAFF"] },
      { menu_code: "MNR_EV_B2B_LEADS", label: "EV B2B Leads", route: "/staff/ev-b2b-leads", icon: "fas fa-truck", audience: ["STAFF"] },
      { menu_code: "MNR_EV_B2C_LEADS", label: "EV B2C Leads", route: "/staff/ev-b2c-leads", icon: "fas fa-car", audience: ["STAFF"] },
      { menu_code: "MNR_EV_SPARES_LEADS", label: "EV Spares Leads", route: "/staff/ev-spares-leads", icon: "fas fa-cogs", audience: ["STAFF"] },
      { menu_code: "MNR_REAL_DREAMS_LEADS", label: "Real Dreams Leads", route: "/staff/real-dreams-leads", icon: "fas fa-home", audience: ["STAFF"] },
      { menu_code: "MNR_INSURANCE_LEADS", label: "Insurance Leads", route: "/staff/insurance-leads", icon: "fas fa-shield-alt", audience: ["STAFF"] },
      { menu_code: "MNR_ETC_LEADS", label: "ETC Training Students", route: "/staff/etc-leads", icon: "fas fa-graduation-cap", audience: ["STAFF"] }
    ]
  },
  {
    section_code: "INTERNAL",
    section_label: "INTERNAL",
    order: 30,
    subSections: [
      {
        sub_section_code: "INTERNAL_SFMS_TOOLS",
        sub_section_label: "SFMS Tools",
        items: [
          { menu_code: "SFMS_ESTIMATIONS", label: "Estimations", route: "/staff/accounts/estimations", icon: "fas fa-calculator", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "INTERNAL_STAFF_NDA",
        sub_section_label: "Staff NDA",
        items: [
          { menu_code: "NDA_VERSIONS", label: "NDA Versions", route: "/staff/nda-versions", icon: "fas fa-file-alt", audience: ["STAFF"] },
          { menu_code: "ACCEPTANCE_AUDIT", label: "Acceptance Audit", route: "/staff/nda-acceptance-audit", icon: "fas fa-list-check", audience: ["STAFF"] },
          { menu_code: "PENDING_ACCEPTANCES", label: "Pending Acceptances", route: "/staff/nda-pending", icon: "fas fa-clock", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "INTERNAL_PROMOTERS",
        sub_section_label: "Promoters",
        items: [
          { menu_code: "PROMOTER_MANAGEMENT", label: "Promoter Management", route: "/staff/promoters", icon: "fas fa-users", audience: ["STAFF"] },
          { menu_code: "PROMO_NDA_EDITOR", label: "Promo NDA Editor", route: "/staff/promo-nda-editor", icon: "fas fa-file-contract", audience: ["STAFF"] },
          { menu_code: "PROMO_NDA_AUDIT", label: "Promo NDA Audit", route: "/staff/promo-nda-audit", icon: "fas fa-list-alt", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "INTERNAL_MNR_TC",
        sub_section_label: "MNR Terms & Conditions",
        items: [
          { menu_code: "staff_mnr_terms_versions", label: "T&C Versions", route: "/staff/mnr/terms-versions", icon: "fas fa-file-contract", audience: ["STAFF"] },
          { menu_code: "staff_mnr_terms_editor", label: "T&C Editor", route: "/staff/mnr/terms-editor", icon: "fas fa-edit", audience: ["STAFF"] },
          { menu_code: "staff_mnr_terms_audit", label: "T&C Audit", route: "/staff/mnr/terms-audit", icon: "fas fa-history", audience: ["STAFF"] }
        ]
      },
    ]
  },
  {
    section_code: "NOT_IN_USE",
    section_label: "NOT IN USE",
    order: 31,
    subSections: [
      {
        sub_section_code: "INTERNAL_RVZ_TC",
        sub_section_label: "RVZ Terms & Conditions",
        items: [
          { menu_code: "RVZ_TERMS_MGMT", label: "T&C Management", route: "/rvz/terms-conditions-management", icon: "fas fa-file-contract", audience: ["STAFF"] },
          { menu_code: "RVZ_TERMS_VERSIONS", label: "T&C Versions", route: "/rvz/terms-versions", icon: "fas fa-file-alt", audience: ["STAFF"] },
          { menu_code: "RVZ_TERMS_EDITOR", label: "T&C Editor", route: "/rvz/terms-editor", icon: "fas fa-edit", audience: ["STAFF"] },
          { menu_code: "RVZ_TERMS_AUDIT", label: "T&C Audit", route: "/rvz/terms-audit", icon: "fas fa-history", audience: ["STAFF"] },
          { menu_code: "RVZ_TERMS_CONDITIONS_AUDIT", label: "Conditions Audit", route: "/rvz/terms-conditions-audit", icon: "fas fa-list-check", audience: ["STAFF"] },
          { menu_code: "RVZ_TERMS_ACCEPTANCE", label: "T&C Acceptance", route: "/rvz/terms-acceptance", icon: "fas fa-check-circle", audience: ["STAFF"] }
        ]
      }
    ]
  },

  // ─── VGK4U ────────────────────────────────────────────────────────────
  {
    section_code: "VGK4U",
    section_label: "VGK4U",
    order: 21,
    subSections: [
      {
        sub_section_code: "ZY_PROPERTY_WORKINGS",
        sub_section_label: "ZY Property Workings (16.1)",
        items: [
          { menu_code: "PROPERTY_MARKETPLACE", label: "Property Marketplace", route: "/rvz/real-dreams/marketplace", audience: ["STAFF"] },
          { menu_code: "PROPERTY_AMENITIES", label: "Property Amenities", route: "/rvz/real-dreams", audience: ["STAFF"] },
          { menu_code: "PARTNER_PROFILES", label: "Partner Profiles", route: "/rvz/real-dreams/partners", audience: ["STAFF"] },
          { menu_code: "PROPERTY_HANDLER", label: "Property Handler", route: "/rvz/real-dreams/properties", audience: ["STAFF"] },
          { menu_code: "REAL_DREAMS_DASHBOARD", label: "Real Dreams Dashboard", route: "/rvz/real-dreams-dashboard", audience: ["STAFF"] }
        ]
      },
      {
        sub_section_code: "ZY_MEMBER_EARNINGS",
        sub_section_label: "ZY Member Earnings (16.2)",
        items: [
          { menu_code: "INCENTIVE_APPROVALS", label: "Incentive Approvals", route: "/staff/incentives/approvals", audience: ["STAFF"] },
          { menu_code: "ALL_VGK4U_MEMBERS", label: "All VGK4U Members", route: "/staff/incentives/vgk4u", audience: ["STAFF"] },
          { menu_code: "VGK_REAL_DREAMS", label: "VGK Real Dreams (ZR)", route: "/staff/vgk4u/real-estate", audience: ["STAFF"] },
          { menu_code: "VGK_CARE", label: "VGK Care (ZC)", route: "/staff/vgk4u/insurance", audience: ["STAFF"] }
        ]
      }
    ]
  },
  // ─── HR (DC_CAREERS_001 — Apr 2026) ───────────────────────────────────
  {
    section_code: "HR",
    section_label: "HR",
    sidebar_section: "hr",
    order: 22,
    items: [
      { menu_code: "PERFORMANCE_CONFIG", label: "Performance Config", route: "/staff/performance-config", audience: ["STAFF"] },
      { menu_code: "HR_JOB_POSTINGS", label: "Job Postings", route: "/staff/hr/job-postings", icon: "fas fa-briefcase", audience: ["STAFF"] },
      { menu_code: "HR_CANDIDATES",   label: "Candidates",   route: "/staff/hr/candidates",   icon: "fas fa-user-tie",  audience: ["STAFF"] }
    ]
  },
];

/**
 * Utility: Flatten all menu items for easy lookup
 * @returns {Array} Array of all menu items with section info
 */
function getAllMenuItems() {
  const items = [];
  MENU_MASTER.forEach(section => {
    if (section.items) {
      section.items.forEach(item => {
        items.push({
          ...item,
          section_code: section.section_code,
          section_label: section.section_label,
          section_order: section.order
        });
      });
    }
    if (section.subSections) {
      section.subSections.forEach(subSection => {
        subSection.items.forEach(item => {
          items.push({
            ...item,
            section_code: section.section_code,
            section_label: section.section_label,
            section_order: section.order,
            sub_section_code: subSection.sub_section_code,
            sub_section_label: subSection.sub_section_label
          });
        });
      });
    }
  });
  return items;
}

/**
 * Utility: Find menu item by route
 * @param {string} route - Route path to find
 * @returns {Object|null} Menu item or null
 */
function findMenuByRoute(route) {
  const allItems = getAllMenuItems();
  return allItems.find(item => item.route === route) || null;
}

/**
 * Utility: Find menu item by menu_code
 * @param {string} menuCode - Menu code to find
 * @returns {Object|null} Menu item or null
 */
function findMenuByCode(menuCode) {
  const allItems = getAllMenuItems();
  return allItems.find(item => item.menu_code === menuCode) || null;
}

/**
 * Utility: Get all routes as an array
 * @returns {Array} Array of all route strings
 */
function getAllRoutes() {
  return getAllMenuItems().map(item => item.route);
}

/**
 * Utility: Get section by order number
 * @param {number} order - Section order number
 * @returns {Object|null} Section or null
 */
function getSectionByOrder(order) {
  return MENU_MASTER.find(section => section.order === order) || null;
}

/**
 * Utility: Count total menu items
 * @returns {number} Total count of menu items
 */
function getTotalMenuCount() {
  return getAllMenuItems().length;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MENU_MASTER,
    getAllMenuItems,
    findMenuByRoute,
    findMenuByCode,
    getAllRoutes,
    getSectionByOrder,
    getTotalMenuCount
  };
}
