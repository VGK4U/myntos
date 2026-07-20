#!/usr/bin/env python3
"""
PDF Sidebar Canonical Rebuild Script
Created: Jan 13, 2026
Purpose: Complete transactional rebuild of staff_menu_registry from PDF specification
Source of Truth: PERORMANCE_REPORT_-_Final_Side_bar.pdf (216 pages across 18 sections)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

PDF_SIDEBAR_SPEC = {
    "sections": [
        {
            "order": 1,
            "id": "progress",
            "title": "PROGRESS",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "Progress Dashboard", "route": "/staff/progress", "icon": "fas fa-chart-line"}
            ]
        },
        {
            "order": 2,
            "id": "staff-dashboard",
            "title": "STAFF DASHBOARD",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "Dashboard", "route": "/staff/dashboard", "icon": "fas fa-tachometer-alt"},
                {"name": "Employees", "route": "/staff/employees", "icon": "fas fa-users"},
                {"name": "Employee Directory", "route": "/staff/employee-directory", "icon": "fas fa-address-book"},
                {"name": "My KYC", "route": "/staff/my-kyc", "icon": "fas fa-id-card"},
                {"name": "KYC Approvals", "route": "/staff/kyc-approvals", "icon": "fas fa-check-circle"},
                {"name": "Review Dashboard", "route": "/staff/manager-review", "icon": "fas fa-clipboard-check"}
            ]
        },
        {
            "order": 3,
            "id": "attendance",
            "title": "ATTENDANCE",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "In/Out Time", "route": "/staff/my-attendance", "icon": "fas fa-clock"},
                {"name": "My Leaves", "route": "/staff/my-leaves", "icon": "fas fa-calendar-minus"},
                {"name": "Leave Approvals", "route": "/staff/leave-approvals", "icon": "fas fa-calendar-check"},
                {"name": "In/Out Records - Admin", "route": "/staff/team-attendance", "icon": "fas fa-user-clock"},
                {"name": "Attendance Records", "route": "/staff/attendance-sheet", "icon": "fas fa-table"},
                {"name": "Attendance Dashboard", "route": "/staff/attendance-reports", "icon": "fas fa-chart-bar"},
                {"name": "Exception Approvals", "route": "/staff/attendance-exceptions", "icon": "fas fa-exclamation-circle"},
                {"name": "Attendance Computation", "route": "/staff/attendance-computation", "icon": "fas fa-calculator"}
            ]
        },
        {
            "order": 4,
            "id": "crm",
            "title": "CRM & LEADS",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "My CRM Dashboard", "route": "/staff/crm/dashboard", "icon": "fas fa-funnel-dollar"},
                {"name": "Staff Leads", "route": "/staff/leads", "icon": "fas fa-user-tie"},
                {"name": "Team Leads", "route": "/staff/crm/team-leads", "icon": "fas fa-users-cog"},
                {"name": "My Leads", "route": "/staff/my-leads", "icon": "fas fa-user-plus"},
                {"name": "Lead Sources", "route": "/staff/crm/lead-sources", "icon": "fas fa-sitemap"}
            ]
        },
        {
            "order": 5,
            "id": "task-management",
            "title": "TASK MANAGEMENT",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "Assigned By Me", "route": "/staff/tasks/assigned-by-me-v2", "icon": "fas fa-tasks"},
                {"name": "Assigned To Me", "route": "/staff/tasks/assigned-to-me", "icon": "fas fa-clipboard-list"},
                {"name": "Team Activities", "route": "/staff/tasks/team-activities", "icon": "fas fa-project-diagram"},
                {"name": "Task Tracker", "route": "/staff/tasks/tracker", "icon": "fas fa-chart-gantt"},
                {"name": "Task Reviews", "route": "/staff/task-review", "icon": "fas fa-check-double"}
            ]
        },
        {
            "order": 6,
            "id": "kra-management",
            "title": "KRA MANAGEMENT",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "My KRAs", "route": "/staff/my-kras", "icon": "fas fa-bullseye"},
                {"name": "KRA Templates", "route": "/staff/kra-templates", "icon": "fas fa-file-alt"},
                {"name": "KRA Tracking Sheet", "route": "/staff/kra-tracking-sheet", "icon": "fas fa-table"},
                {"name": "KRA Review", "route": "/staff/kra-review", "icon": "fas fa-star-half-alt"}
            ]
        },
        {
            "order": 7,
            "id": "timesheet",
            "title": "TIMESHEET",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "My Timesheet", "route": "/staff/my-timesheet", "icon": "fas fa-hourglass-half"},
                {"name": "Timesheet Approval", "route": "/staff/timesheet-approval", "icon": "fas fa-check-square"}
            ]
        },
        {
            "order": 8,
            "id": "journey-tracking",
            "title": "JOURNEY TRACKING",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "My Journeys", "route": "/staff/my-journeys", "icon": "fas fa-route"},
                {"name": "Team Journeys", "route": "/staff/team-journeys", "icon": "fas fa-map-marked-alt"},
                {"name": "All Journeys", "route": "/staff/all-journeys", "icon": "fas fa-globe"},
                {"name": "VGK4U Journeys", "route": "/staff/vgk4u-journeys", "icon": "fas fa-car"}
            ]
        },
        {
            "order": 9,
            "id": "location-tracking",
            "title": "LOCATION TRACKING",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "My Location History", "route": "/staff/my-location-history", "icon": "fas fa-map-marker-alt"},
                {"name": "Team Location Tracker", "route": "/staff/team-location-tracker", "icon": "fas fa-map-pin"}
            ]
        },
        {
            "order": 10,
            "id": "reimbursement",
            "title": "REIMBURSEMENT",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "My Reimbursement Claims", "route": "/staff/accounts/my-reimbursements", "icon": "fas fa-receipt"},
                {"name": "Reimbursement Approvals", "route": "/staff/accounts/reimbursement-approvals", "icon": "fas fa-file-invoice-dollar"}
            ]
        },
        {
            "order": 11,
            "id": "service-tickets",
            "title": "SERVICE TICKETS",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "Dashboard", "route": "/staff/service-tickets/dashboard", "icon": "fas fa-ticket-alt"},
                {"name": "Performance", "route": "/staff/service-tickets/performance", "icon": "fas fa-chart-line"},
                {"name": "Procurement", "route": "/staff/service-tickets/procurement", "icon": "fas fa-shopping-cart"},
                {"name": "Procurement Queue", "route": "/staff/service-tickets/procurement-queue", "icon": "fas fa-list-ol"},
                {"name": "Raise Ticket", "route": "/staff/service-tickets/raise", "icon": "fas fa-plus-circle"},
                {"name": "Reports", "route": "/staff/service-tickets/reports", "icon": "fas fa-file-alt"},
                {"name": "Service Queue", "route": "/staff/service-tickets/queue", "icon": "fas fa-stream"},
                {"name": "Service Center Revenue", "route": "/staff/service-center-revenue", "icon": "fas fa-dollar-sign"}
            ]
        },
        {
            "order": 12,
            "id": "accounts",
            "title": "ACCOUNTS",
            "is_submenu": False,
            "parent_section": None,
            "subsections": [
                {
                    "id": "sfms",
                    "title": "SFMS",
                    "pages": [
                        {"name": "Balance Sheet", "route": "/staff/accounts/balance-sheet", "icon": "fas fa-balance-scale"},
                        {"name": "Fund Allocations", "route": "/staff/accounts/fund-allocations", "icon": "fas fa-hand-holding-usd"},
                        {"name": "Expense Entries", "route": "/staff/accounts/expense-entries", "icon": "fas fa-file-invoice"},
                        {"name": "Income Entries", "route": "/staff/accounts/income-entries", "icon": "fas fa-coins"},
                        {"name": "Purchase Invoices", "route": "/staff/accounts/purchase-invoices", "icon": "fas fa-file-alt"},
                        {"name": "Sales Invoices", "route": "/staff/accounts/sales-invoices", "icon": "fas fa-file-invoice-dollar"},
                        {"name": "Invoice Reports", "route": "/staff/accounts/reports", "icon": "fas fa-chart-pie"},
                        {"name": "Accounts Payable", "route": "/staff/accounts/payables", "icon": "fas fa-money-check-alt"},
                        {"name": "Accounts Receivable", "route": "/staff/accounts/receivables", "icon": "fas fa-hand-holding-usd"},
                        {"name": "Sales Team Revenue", "route": "/rvz/sales-revenue", "icon": "fas fa-chart-bar"},
                        {"name": "Party Ledger", "route": "/staff/accounts/party-ledger", "icon": "fas fa-book"}
                    ]
                },
                {
                    "id": "inventory",
                    "title": "Inventory",
                    "pages": [
                        {"name": "Bill of Materials", "route": "/staff/inventory/bom", "icon": "fas fa-clipboard-list"},
                        {"name": "Manufacturing", "route": "/staff/inventory/manufacturing", "icon": "fas fa-industry"},
                        {"name": "Procurement", "route": "/staff/inventory/procurement", "icon": "fas fa-truck-loading"},
                        {"name": "Purchase Intake", "route": "/staff/inventory/intake", "icon": "fas fa-box-open"},
                        {"name": "Stock Items", "route": "/staff/inventory/stock-items", "icon": "fas fa-boxes"},
                        {"name": "Stock Ledger", "route": "/staff/inventory/stock-ledger", "icon": "fas fa-book"},
                        {"name": "Stock Transfers", "route": "/staff/inventory/stock-transfers", "icon": "fas fa-exchange-alt"},
                        {"name": "Stock Validation", "route": "/staff/inventory/stock-validation", "icon": "fas fa-check-circle"},
                        {"name": "Service Center Tracking", "route": "/staff/inventory/service-center-tracking", "icon": "fas fa-map-marked"},
                        {"name": "Vendor Returns", "route": "/staff/inventory/vendor-returns", "icon": "fas fa-undo"}
                    ]
                },
                {
                    "id": "payroll",
                    "title": "Payroll",
                    "pages": [
                        {"name": "Payroll Profiles", "route": "/staff/payroll/profiles", "icon": "fas fa-id-badge"},
                        {"name": "Payroll Cycles", "route": "/staff/payroll/cycles", "icon": "fas fa-sync"},
                        {"name": "Payroll Runs", "route": "/staff/payroll/runs", "icon": "fas fa-play-circle"},
                        {"name": "Approvals", "route": "/staff/payroll/approvals", "icon": "fas fa-check"},
                        {"name": "Consultant Invoices", "route": "/staff/payroll/consultant-invoices", "icon": "fas fa-file-invoice"},
                        {"name": "Allowance Catalog", "route": "/staff/payroll/allowance-catalog", "icon": "fas fa-list"},
                        {"name": "Documents", "route": "/staff/payroll/documents", "icon": "fas fa-folder-open"}
                    ]
                }
            ]
        },
        {
            "order": 13,
            "id": "official-partners",
            "title": "BUSINESS PARTNERS",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "Partner Orders", "route": "/staff/partners/orders", "icon": "fas fa-shopping-bag"},
                {"name": "Partner Pricing", "route": "/staff/partners/pricing", "icon": "fas fa-tags"},
                {"name": "Order Approval", "route": "/staff/partners/approval", "icon": "fas fa-check-circle"},
                {"name": "Order Routing", "route": "/staff/partners/routing", "icon": "fas fa-route"},
                {"name": "Order Fulfillment", "route": "/staff/partners/fulfillment", "icon": "fas fa-truck"},
                {"name": "Dispatch Management", "route": "/staff/partners/dispatch", "icon": "fas fa-shipping-fast"},
                {"name": "Partner Invoices", "route": "/staff/partners/invoices", "icon": "fas fa-file-invoice"},
                {"name": "Payment Verification", "route": "/staff/partners/payments", "icon": "fas fa-credit-card"}
            ]
        },
        {
            "order": 14,
            "id": "nda-management",
            "title": "NDA MANAGEMENT",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "NDA Versions", "route": "/staff/nda-versions", "icon": "fas fa-file-contract"},
                {"name": "Acceptance Audit", "route": "/staff/nda-acceptance-audit", "icon": "fas fa-clipboard-check"},
                {"name": "Pending Acceptances", "route": "/staff/nda-pending", "icon": "fas fa-hourglass-half"},
                {"name": "NDA Editor", "route": "/staff/nda-editor", "icon": "fas fa-edit"}
            ]
        },
        {
            "order": 15,
            "id": "configuration",
            "title": "CONFIGURATION",
            "is_submenu": False,
            "parent_section": None,
            "pages": [
                {"name": "Departments", "route": "/staff/departments", "icon": "fas fa-building"},
                {"name": "Companies", "route": "/staff/accounts/companies", "icon": "fas fa-city"},
                {"name": "Business Partners Config", "route": "/staff/partners/master", "icon": "fas fa-handshake"},
                {"name": "Segments", "route": "/staff/accounts/segments", "icon": "fas fa-layer-group"},
                {"name": "Expense Categories", "route": "/staff/accounts/expense-categories", "icon": "fas fa-folder"},
                {"name": "Pricing Config", "route": "/staff/accounts/pricing", "icon": "fas fa-dollar-sign"},
                {"name": "HSN Master", "route": "/staff/accounts/hsn", "icon": "fas fa-barcode"},
                {"name": "Signup Categories", "route": "/staff/signup-categories", "icon": "fas fa-user-plus"},
                {"name": "Menu Access Control", "route": "/rvz/menu-access-config", "icon": "fas fa-key"},
                {"name": "Sidebar Sync", "route": "/staff/sidebar-sync", "icon": "fas fa-sync-alt"},
                {"name": "Settings", "route": "/staff/settings", "icon": "fas fa-cog"},
                {"name": "Audit Logs", "route": "/staff/audit-logs", "icon": "fas fa-history"}
            ]
        },
        {
            "order": 16,
            "id": "zynova",
            "title": "ZYNOVA",
            "is_submenu": False,
            "parent_section": None,
            "subsections": [
                {
                    "id": "real-dreams",
                    "title": "ZY Property Workings",
                    "pages": [
                        {"name": "Property Marketplace", "route": "/rvz/real-dreams/marketplace", "icon": "fas fa-home"},
                        {"name": "Property Amenities", "route": "/rvz/real-dreams", "icon": "fas fa-swimming-pool"},
                        {"name": "Partner Profiles", "route": "/rvz/real-dreams/partners", "icon": "fas fa-user-tie"},
                        {"name": "Property Handler", "route": "/rvz/real-dreams/properties", "icon": "fas fa-building"},
                        {"name": "Dashboard", "route": "/rvz/real-dreams-dashboard", "icon": "fas fa-tachometer-alt"}
                    ]
                },
                {
                    "id": "zy-member-earnings",
                    "title": "ZY Member Earnings",
                    "pages": [
                        {"name": "MNR Points", "route": "/staff/incentives/points", "icon": "fas fa-coins"},
                        {"name": "Incentive Approvals", "route": "/staff/incentives/approvals", "icon": "fas fa-check-circle"},
                        {"name": "All Zynova Members", "route": "/staff/incentives/zynova", "icon": "fas fa-users"},
                        {"name": "VGK Real Dreams (ZR)", "route": "/staff/zynova/real-estate", "icon": "fas fa-home"},
                        {"name": "VGK Care (ZC)", "route": "/staff/zynova/insurance", "icon": "fas fa-shield-alt"}
                    ]
                }
            ]
        },
        {
            "order": 17,
            "id": "mnr",
            "title": "MNR",
            "is_submenu": False,
            "parent_section": None,
            "subsections": [
                {
                    "id": "mnr-users",
                    "title": "Users",
                    "pages": [
                        {"name": "Dashboard", "route": "/staff/mnr/dashboard", "icon": "fas fa-tachometer-alt"},
                        {"name": "Users", "route": "/staff/mnr/users", "icon": "fas fa-users"},
                        {"name": "User Data Search", "route": "/staff/mnr/user-data-search", "icon": "fas fa-search"},
                        {"name": "User Activation Control", "route": "/staff/mnr/user-activation-control", "icon": "fas fa-toggle-on"},
                        {"name": "Bulk User Edit", "route": "/staff/mnr/bulk-user-edit", "icon": "fas fa-edit"},
                        {"name": "User Update Controls", "route": "/staff/mnr/user-update-controls", "icon": "fas fa-user-edit"},
                        {"name": "Reactivate/Reassign", "route": "/staff/mnr/reactivate-reassign", "icon": "fas fa-redo"},
                        {"name": "User Update Approvals", "route": "/staff/mnr/user-update-approvals", "icon": "fas fa-check"},
                        {"name": "Birthdays", "route": "/staff/mnr/birthdays", "icon": "fas fa-birthday-cake"}
                    ]
                },
                {
                    "id": "mnr-approvals",
                    "title": "Approvals",
                    "pages": [
                        {"name": "KYC Management", "route": "/staff/mnr/kyc-management", "icon": "fas fa-id-card"},
                        {"name": "Bank Pending", "route": "/staff/mnr/bank-pending", "icon": "fas fa-university"},
                        {"name": "Bank All", "route": "/staff/mnr/bank-all", "icon": "fas fa-landmark"}
                    ]
                },
                {
                    "id": "mnr-awards",
                    "title": "Awards",
                    "pages": [
                        {"name": "All Awards", "route": "/staff/mnr/awards-all", "icon": "fas fa-trophy"},
                        {"name": "Awards Approval Queue", "route": "/staff/mnr/awards-approval-queue", "icon": "fas fa-list"},
                        {"name": "Procurement Queue", "route": "/staff/mnr/procurement-queue", "icon": "fas fa-shopping-cart"},
                        {"name": "Gift-wise Status", "route": "/staff/mnr/gift-wise-status", "icon": "fas fa-gift"},
                        {"name": "Award Management", "route": "/staff/mnr/award-management", "icon": "fas fa-medal"},
                        {"name": "Bonanza Management", "route": "/staff/mnr/bonanza-management", "icon": "fas fa-star"},
                        {"name": "Bonanza Claims", "route": "/staff/mnr/bonanza-claims", "icon": "fas fa-hand-holding"}
                    ]
                },
                {
                    "id": "mnr-income",
                    "title": "Income",
                    "pages": [
                        {"name": "Income Records", "route": "/staff/mnr/income-records", "icon": "fas fa-chart-line"},
                        {"name": "Income Supreme", "route": "/staff/mnr/income-supreme", "icon": "fas fa-crown"},
                        {"name": "Finance Complete", "route": "/staff/mnr/income-finance-complete", "icon": "fas fa-check-double"}
                    ]
                },
                {
                    "id": "mnr-withdrawals",
                    "title": "Withdrawals",
                    "pages": [
                        {"name": "Withdrawal Supreme", "route": "/staff/mnr/withdrawal-supreme", "icon": "fas fa-wallet"},
                        {"name": "Withdrawal Approvals", "route": "/staff/mnr/withdrawal/approvals", "icon": "fas fa-check-circle"},
                        {"name": "Withdrawal History", "route": "/staff/mnr/withdrawal/history", "icon": "fas fa-history"}
                    ]
                },
                {
                    "id": "mnr-finance",
                    "title": "Finance & Compliance",
                    "pages": [
                        {"name": "Finance Supreme", "route": "/staff/mnr/finance-supreme", "icon": "fas fa-chart-pie"},
                        {"name": "Compliance", "route": "/staff/mnr/compliance", "icon": "fas fa-clipboard-check"},
                        {"name": "Company Earnings", "route": "/staff/mnr/company-earnings", "icon": "fas fa-building"},
                        {"name": "Revenue Details", "route": "/staff/mnr/revenue-details", "icon": "fas fa-dollar-sign"},
                        {"name": "Payout Details", "route": "/staff/mnr/payout-details", "icon": "fas fa-money-bill-wave"},
                        {"name": "Expense Details", "route": "/staff/mnr/expense-details", "icon": "fas fa-file-invoice-dollar"},
                        {"name": "Expenses Management", "route": "/staff/mnr/expenses-management", "icon": "fas fa-calculator"},
                        {"name": "Expense Overview", "route": "/staff/mnr/expense-overview", "icon": "fas fa-chart-bar"}
                    ]
                },
                {
                    "id": "mnr-communications",
                    "title": "Announcements",
                    "pages": [
                        {"name": "Pending Announcements", "route": "/staff/mnr/feedback/pending", "icon": "fas fa-comment-dots"},
                        {"name": "Announcements View", "route": "/staff/mnr/announcements/view", "icon": "fas fa-bullhorn"},
                        {"name": "Banners Management", "route": "/staff/mnr/banners-management", "icon": "fas fa-image"},
                        {"name": "Banner Analytics", "route": "/staff/mnr/banner-analytics", "icon": "fas fa-chart-area"}
                    ]
                },
                {
                    "id": "mnr-pins",
                    "title": "PINs & Approvals",
                    "pages": [
                        {"name": "PIN Approvals", "route": "/staff/mnr/pin-approvals", "icon": "fas fa-key"},
                        {"name": "Coupon Status", "route": "/staff/mnr/coupon-status", "icon": "fas fa-ticket-alt"},
                        {"name": "PINs", "route": "/staff/mnr/pins", "icon": "fas fa-thumbtack"}
                    ]
                },
                {
                    "id": "mnr-security",
                    "title": "Password & Security",
                    "pages": [
                        {"name": "Change User Password", "route": "/staff/mnr/change-user-password", "icon": "fas fa-key"},
                        {"name": "Password Change", "route": "/staff/mnr/password-change", "icon": "fas fa-lock"},
                        {"name": "Secondary Password Setup", "route": "/staff/mnr/secondary-password-setup", "icon": "fas fa-shield-alt"}
                    ]
                },
                {
                    "id": "mnr-config",
                    "title": "System Configuration",
                    "pages": [
                        {"name": "System Controls", "route": "/staff/mnr/system-controls", "icon": "fas fa-sliders-h"},
                        {"name": "Rate Configuration", "route": "/staff/mnr/rate-configuration", "icon": "fas fa-percentage"},
                        {"name": "Daily Ceiling", "route": "/staff/mnr/daily-ceiling", "icon": "fas fa-chart-line"},
                        {"name": "Emergency Wallet", "route": "/staff/mnr/emergency-wallet", "icon": "fas fa-exclamation-triangle"},
                        {"name": "Role Management", "route": "/staff/mnr/role-management", "icon": "fas fa-user-shield"},
                        {"name": "Add Packages", "route": "/staff/mnr/add-packages", "icon": "fas fa-box"},
                        {"name": "Menu Configuration", "route": "/staff/mnr/menu-configuration", "icon": "fas fa-bars"},
                        {"name": "Menu Access Config", "route": "/staff/mnr/menu-access-config", "icon": "fas fa-key"},
                        {"name": "Scheduler Dashboard", "route": "/staff/mnr/scheduler-dashboard", "icon": "fas fa-clock"}
                    ]
                },
                {
                    "id": "mnr-data",
                    "title": "Data Management",
                    "pages": [
                        {"name": "Delete Management", "route": "/staff/mnr/delete-management", "icon": "fas fa-trash-alt"},
                        {"name": "Data Recovery", "route": "/staff/mnr/data-recovery", "icon": "fas fa-undo"},
                        {"name": "Production Reset Status", "route": "/staff/mnr/production-reset-status", "icon": "fas fa-sync"}
                    ]
                }
            ]
        },
        {
            "order": 18,
            "id": "mnr-user-sidebar",
            "title": "MNR USER SIDEBAR",
            "is_submenu": False,
            "parent_section": None,
            "subsections": [
                {
                    "id": "staff_mnr_user_system",
                    "title": "Audit Log",
                    "pages": [
                        {"name": "Audit Log", "route": "/staff/mnr-user/audit-log", "icon": "fas fa-history"}
                    ]
                },
                {
                    "id": "staff_mnr_user_dashboard",
                    "title": "Dashboard",
                    "pages": [
                        {"name": "Dashboard", "route": "/staff/mnr-user/dashboard", "icon": "fas fa-tachometer-alt"},
                        {"name": "Profile", "route": "/staff/mnr-user/profile", "icon": "fas fa-user"},
                        {"name": "Create Member", "route": "/staff/mnr-user/create-member", "icon": "fas fa-user-plus"}
                    ]
                },
                {
                    "id": "staff_mnr_user_announcements",
                    "title": "Announcements",
                    "pages": [
                        {"name": "Announcements", "route": "/staff/mnr-user/announcements", "icon": "fas fa-bullhorn"},
                        {"name": "Create Announcement", "route": "/staff/mnr-user/announcements/create", "icon": "fas fa-plus"},
                        {"name": "Pending", "route": "/staff/mnr-user/announcements/pending", "icon": "fas fa-hourglass-half"},
                        {"name": "History", "route": "/staff/mnr/announcements/history", "icon": "fas fa-history"},
                        {"name": "Popups", "route": "/staff/mnr-user/popups", "icon": "fas fa-window-restore"}
                    ]
                },
                {
                    "id": "staff_mnr_user_coupons",
                    "title": "Coupons",
                    "pages": [
                        {"name": "Available Coupons", "route": "/staff/mnr-user/coupons/available", "icon": "fas fa-ticket-alt"},
                        {"name": "Red Coupons", "route": "/staff/mnr-user/coupons/red", "icon": "fas fa-circle text-danger"},
                        {"name": "Green Coupons", "route": "/staff/mnr-user/coupons/green", "icon": "fas fa-circle text-success"},
                        {"name": "EV Coupons", "route": "/staff/mnr-user/coupons/ev", "icon": "fas fa-car"},
                        {"name": "Transfer", "route": "/staff/mnr-user/coupons/transfer", "icon": "fas fa-exchange-alt"},
                        {"name": "History", "route": "/staff/mnr-user/coupons/history", "icon": "fas fa-history"}
                    ]
                },
                {
                    "id": "staff_mnr_user_members",
                    "title": "Members",
                    "pages": [
                        {"name": "Members", "route": "/staff/mnr-user/members", "icon": "fas fa-users"},
                        {"name": "All Members", "route": "/staff/mnr-user/members/all", "icon": "fas fa-users"},
                        {"name": "Direct Members", "route": "/staff/mnr-user/members/direct", "icon": "fas fa-user-friends"},
                        {"name": "Downline", "route": "/staff/mnr-user/members/downline", "icon": "fas fa-sitemap"},
                        {"name": "VED Members", "route": "/staff/mnr-user/members/ved", "icon": "fas fa-star"},
                        {"name": "Picture", "route": "/staff/mnr-user/members/picture", "icon": "fas fa-image"}
                    ]
                },
                {
                    "id": "staff_mnr_user_mnr",
                    "title": "Earnings",
                    "pages": [
                        {"name": "Earnings", "route": "/staff/mnr-user/mnr/earnings", "icon": "fas fa-coins"},
                        {"name": "Earnings Summary", "route": "/staff/mnr-user/mnr/earnings-summary", "icon": "fas fa-chart-pie"},
                        {"name": "Direct Referral", "route": "/staff/mnr-user/mnr/direct", "icon": "fas fa-user-plus"},
                        {"name": "Matching", "route": "/staff/mnr-user/mnr/matching", "icon": "fas fa-handshake"},
                        {"name": "VED Income", "route": "/staff/mnr-user/mnr/ved", "icon": "fas fa-star"},
                        {"name": "Guru Dakshina", "route": "/staff/mnr-user/mnr/guru", "icon": "fas fa-pray"},
                        {"name": "Wallet", "route": "/staff/mnr-user/mnr/wallet", "icon": "fas fa-wallet"},
                        {"name": "Withdrawals", "route": "/staff/mnr-user/mnr/withdrawals", "icon": "fas fa-money-bill-wave"},
                        {"name": "Points", "route": "/staff/mnr-user/mnr/points", "icon": "fas fa-coins"},
                        {"name": "Benefits", "route": "/staff/mnr-user/mnr/benefits", "icon": "fas fa-gift"}
                    ]
                },
                {
                    "id": "staff_mnr_user_myntreal",
                    "title": "MyntReal",
                    "pages": [
                        {"name": "Properties", "route": "/staff/mnr-user/myntreal/properties", "icon": "fas fa-home"},
                        {"name": "Leads", "route": "/staff/mnr-user/myntreal/leads", "icon": "fas fa-user-tie"},
                        {"name": "Franchise", "route": "/staff/mnr-user/myntreal/franchise", "icon": "fas fa-store"}
                    ]
                },
                {
                    "id": "staff_mnr_user_zynova",
                    "title": "Zynova",
                    "pages": [
                        {"name": "Dashboard", "route": "/staff/mnr-user/zynova/dashboard", "icon": "fas fa-tachometer-alt"},
                        {"name": "Real Estate", "route": "/staff/mnr-user/zynova/real-estate", "icon": "fas fa-building"},
                        {"name": "Insurance", "route": "/staff/mnr-user/zynova/insurance", "icon": "fas fa-shield-alt"},
                        {"name": "Training", "route": "/staff/mnr-user/zynova/training", "icon": "fas fa-chalkboard-teacher"}
                    ]
                },
                {
                    "id": "staff_mnr_user_awards",
                    "title": "Awards",
                    "pages": [
                        {"name": "All Awards", "route": "/staff/mnr-user/awards/all", "icon": "fas fa-trophy"},
                        {"name": "Bonanza", "route": "/staff/mnr-user/awards/bonanza", "icon": "fas fa-star"}
                    ]
                }
            ]
        }
    ]
}


def rebuild_sidebar():
    """Complete transactional rebuild of sidebar from PDF spec"""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return False
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        logger.info("=" * 60)
        logger.info("STARTING PDF SIDEBAR REBUILD")
        logger.info("=" * 60)
        
        session.execute(text("UPDATE staff_menu_registry SET is_active = false, updated_at = NOW()"))
        logger.info("Step 1: Deactivated all existing entries")
        
        total_pages = 0
        display_order = 0
        
        for section in PDF_SIDEBAR_SPEC["sections"]:
            section_order = section["order"]
            section_id = section["id"]
            section_title = section["title"]
            is_parent_submenu = section.get("is_submenu", False)
            parent_of_section = section.get("parent_section")
            
            if "pages" in section:
                for page in section["pages"]:
                    display_order += 1
                    result = session.execute(text("""
                        UPDATE staff_menu_registry 
                        SET is_active = true,
                            sidebar_section = :section_id,
                            sidebar_section_title = :section_title,
                            sidebar_section_order = :section_order,
                            is_submenu = :is_submenu,
                            parent_section = :parent_section,
                            menu_name = :menu_name,
                            menu_icon = :icon,
                            display_order = :display_order,
                            updated_at = NOW()
                        WHERE route_path = :route
                        RETURNING id
                    """), {
                        "section_id": section_id,
                        "section_title": section_title,
                        "section_order": section_order,
                        "is_submenu": is_parent_submenu,
                        "parent_section": parent_of_section,
                        "menu_name": page["name"],
                        "icon": page["icon"],
                        "display_order": display_order,
                        "route": page["route"]
                    })
                    
                    if result.rowcount > 0:
                        total_pages += 1
                        logger.info(f"  [OK] {page['route']}")
                    else:
                        logger.warning(f"  [MISSING] {page['route']} - not found in DB")
            
            if "subsections" in section:
                for subsection in section["subsections"]:
                    sub_id = subsection["id"]
                    sub_title = subsection["title"]
                    
                    for page in subsection["pages"]:
                        display_order += 1
                        result = session.execute(text("""
                            UPDATE staff_menu_registry 
                            SET is_active = true,
                                sidebar_section = :sub_id,
                                sidebar_section_title = :sub_title,
                                sidebar_section_order = :section_order,
                                is_submenu = true,
                                parent_section = :parent_id,
                                menu_name = :menu_name,
                                menu_icon = :icon,
                                display_order = :display_order,
                                updated_at = NOW()
                            WHERE route_path = :route
                            RETURNING id
                        """), {
                            "sub_id": sub_id,
                            "sub_title": sub_title,
                            "section_order": section_order,
                            "parent_id": section_id,
                            "menu_name": page["name"],
                            "icon": page["icon"],
                            "display_order": display_order,
                            "route": page["route"]
                        })
                        
                        if result.rowcount > 0:
                            total_pages += 1
                            logger.info(f"  [OK] {page['route']} -> {sub_title}")
                        else:
                            logger.warning(f"  [MISSING] {page['route']} - not found in DB")
        
        session.commit()
        
        logger.info("=" * 60)
        logger.info(f"REBUILD COMPLETE: {total_pages} pages activated")
        logger.info("=" * 60)
        
        result = session.execute(text("""
            SELECT sidebar_section_order, sidebar_section_title, COUNT(*) as pages
            FROM staff_menu_registry 
            WHERE is_active = true
            GROUP BY sidebar_section_order, sidebar_section_title
            ORDER BY sidebar_section_order
        """))
        
        logger.info("VERIFICATION:")
        for row in result:
            logger.info(f"  Order {row[0]}: {row[1]} ({row[2]} pages)")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"REBUILD FAILED: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    rebuild_sidebar()
