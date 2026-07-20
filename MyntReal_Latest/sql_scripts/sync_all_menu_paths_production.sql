-- ============================================================
-- COMPREHENSIVE PRODUCTION SYNC: All Menu Route Paths
-- Created: December 19, 2025
-- Purpose: Sync ALL menu paths to match development/frontend
-- DC Protocol Compliant - Safe for Multi-Company Environment
-- ============================================================
-- This script updates ALL known menu paths to their canonical values
-- Run each section and verify row counts
-- ============================================================

-- ============================================================
-- SECTION 1: TASK MANAGEMENT (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/tasks/tracker'
WHERE menu_name = 'Task Tracker' AND route_path != '/staff/tasks/tracker';

UPDATE staff_menu_master SET route_path = '/staff/tasks/assigned-to-me'
WHERE menu_name = 'Tasks Assigned to Me' AND route_path != '/staff/tasks/assigned-to-me';

UPDATE staff_menu_master SET route_path = '/staff/tasks/assigned-by-me-v2'
WHERE menu_name = 'Tasks Assigned by Me' AND route_path != '/staff/tasks/assigned-by-me-v2';

UPDATE staff_menu_master SET route_path = '/staff/tasks/team-activities'
WHERE menu_name = 'Team Activities' AND route_path != '/staff/tasks/team-activities';

UPDATE staff_menu_master SET route_path = '/staff/task-review'
WHERE menu_name = 'Task Review' AND route_path != '/staff/task-review';

-- ============================================================
-- SECTION 2: CRM & LEADS (Staff/RVZ)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/crm/dashboard'
WHERE menu_name = 'CRM Dashboard' AND route_path != '/staff/crm/dashboard';

UPDATE staff_menu_master SET route_path = '/rvz/crm/leads'
WHERE menu_name = 'CRM Leads' AND route_path != '/rvz/crm/leads';

UPDATE staff_menu_master SET route_path = '/staff/crm/team-leads'
WHERE menu_name = 'Lead Sources' AND route_path != '/staff/crm/team-leads';

-- ============================================================
-- SECTION 3: ATTENDANCE (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/my-attendance'
WHERE menu_name = 'My Attendance' AND route_path != '/staff/my-attendance';

UPDATE staff_menu_master SET route_path = '/staff/attendance-sheet'
WHERE menu_name = 'Attendance Sheet' AND route_path != '/staff/attendance-sheet';

UPDATE staff_menu_master SET route_path = '/staff/team-attendance'
WHERE menu_name = 'Team Attendance' AND route_path != '/staff/team-attendance';

UPDATE staff_menu_master SET route_path = '/staff/team-attendance-summary'
WHERE menu_name = 'Team Attendance Summary' AND route_path != '/staff/team-attendance-summary';

UPDATE staff_menu_master SET route_path = '/staff/attendance-computation'
WHERE menu_name = 'Attendance Computation' AND route_path != '/staff/attendance-computation';

UPDATE staff_menu_master SET route_path = '/staff/attendance-reports'
WHERE menu_name = 'Attendance Reports' AND route_path != '/staff/attendance-reports';

-- ============================================================
-- SECTION 4: TIMESHEET (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/my-timesheet'
WHERE menu_name = 'My Timesheet' AND route_path != '/staff/my-timesheet';

UPDATE staff_menu_master SET route_path = '/staff/timesheet-approval'
WHERE menu_name = 'Timesheet Approval' AND route_path != '/staff/timesheet-approval';

-- ============================================================
-- SECTION 5: JOURNEY TRACKING (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/my-journeys'
WHERE menu_name = 'My Journeys' AND route_path != '/staff/my-journeys';

UPDATE staff_menu_master SET route_path = '/staff/team-journeys'
WHERE menu_name = 'Team Journeys' AND route_path != '/staff/team-journeys';

UPDATE staff_menu_master SET route_path = '/staff/all-journeys'
WHERE menu_name = 'All Journeys' AND route_path != '/staff/all-journeys';

UPDATE staff_menu_master SET route_path = '/staff/vgk4u-journeys'
WHERE menu_name = 'VGK4U Journeys' AND route_path != '/staff/vgk4u-journeys';

-- ============================================================
-- SECTION 6: LOCATION TRACKING (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/team-location-tracker'
WHERE menu_name = 'Team Location Tracker' AND route_path != '/staff/team-location-tracker';

UPDATE staff_menu_master SET route_path = '/staff/my-location-history'
WHERE menu_name = 'My Location History' AND route_path != '/staff/my-location-history';

-- ============================================================
-- SECTION 7: MANAGER REVIEW (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/manager-review'
WHERE menu_name = 'Manager Review' AND route_path != '/staff/manager-review';

UPDATE staff_menu_master SET route_path = '/staff/kra-review'
WHERE menu_name = 'KRA Review' AND route_path != '/staff/kra-review';

-- ============================================================
-- SECTION 8: KRA MANAGEMENT (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/my-kras'
WHERE menu_name = 'My KRAs' AND route_path != '/staff/my-kras';

UPDATE staff_menu_master SET route_path = '/staff/kra-templates'
WHERE menu_name = 'KRA Templates' AND route_path != '/staff/kra-templates';

UPDATE staff_menu_master SET route_path = '/staff/kra-tracking-sheet'
WHERE menu_name = 'KRA Tracking Sheet' AND route_path != '/staff/kra-tracking-sheet';

-- ============================================================
-- SECTION 9: NDA MANAGEMENT (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/nda-versions'
WHERE menu_name = 'NDA Versions' AND route_path != '/staff/nda-versions';

UPDATE staff_menu_master SET route_path = '/staff/nda-acceptance-audit'
WHERE menu_name = 'NDA Acceptance Audit' AND route_path != '/staff/nda-acceptance-audit';

UPDATE staff_menu_master SET route_path = '/staff/nda-pending'
WHERE menu_name = 'NDA Pending' AND route_path != '/staff/nda-pending';

UPDATE staff_menu_master SET route_path = '/staff/nda-editor'
WHERE menu_name = 'NDA Editor' AND route_path != '/staff/nda-editor';

-- ============================================================
-- SECTION 10: FINANCIAL MANAGEMENT / SFMS (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/accounts/balance-sheet'
WHERE menu_name = 'Balance Sheet' AND route_path != '/staff/accounts/balance-sheet';

UPDATE staff_menu_master SET route_path = '/staff/accounts/fund-allocations'
WHERE menu_name = 'Fund Allocations' AND route_path != '/staff/accounts/fund-allocations';

UPDATE staff_menu_master SET route_path = '/staff/accounts/expense-entries'
WHERE menu_name = 'Expense Entries' AND route_path != '/staff/accounts/expense-entries';

UPDATE staff_menu_master SET route_path = '/staff/accounts/my-reimbursements'
WHERE menu_name = 'My Reimbursements' AND route_path != '/staff/accounts/my-reimbursements';

UPDATE staff_menu_master SET route_path = '/staff/accounts/reimbursement-approvals'
WHERE menu_name = 'Reimbursement Approvals' AND route_path != '/staff/accounts/reimbursement-approvals';

UPDATE staff_menu_master SET route_path = '/staff/accounts/income-entries'
WHERE menu_name = 'Income Entries' AND route_path != '/staff/accounts/income-entries';

UPDATE staff_menu_master SET route_path = '/staff/accounts/purchase-invoices'
WHERE menu_name = 'Purchase Invoices' AND route_path != '/staff/accounts/purchase-invoices';

UPDATE staff_menu_master SET route_path = '/staff/accounts/sales-invoices'
WHERE menu_name = 'Sales Invoices' AND route_path != '/staff/accounts/sales-invoices';

UPDATE staff_menu_master SET route_path = '/staff/accounts/reports'
WHERE menu_name = 'Financial Reports' AND route_path != '/staff/accounts/reports';

UPDATE staff_menu_master SET route_path = '/staff/accounts/payables'
WHERE menu_name = 'Payables' AND route_path != '/staff/accounts/payables';

UPDATE staff_menu_master SET route_path = '/staff/accounts/receivables'
WHERE menu_name = 'Receivables' AND route_path != '/staff/accounts/receivables';

UPDATE staff_menu_master SET route_path = '/staff/accounts/party-ledger'
WHERE menu_name = 'Party Ledger' AND route_path != '/staff/accounts/party-ledger';

UPDATE staff_menu_master SET route_path = '/staff/accounts/companies'
WHERE menu_name = 'Companies' AND route_path != '/staff/accounts/companies';

UPDATE staff_menu_master SET route_path = '/staff/accounts/segments'
WHERE menu_name = 'Segments' AND route_path != '/staff/accounts/segments';

UPDATE staff_menu_master SET route_path = '/staff/accounts/pricing'
WHERE menu_name = 'Pricing' AND route_path != '/staff/accounts/pricing';

UPDATE staff_menu_master SET route_path = '/staff/accounts/hsn'
WHERE menu_name = 'HSN Master' AND route_path != '/staff/accounts/hsn';

UPDATE staff_menu_master SET route_path = '/staff/accounts/vendors'
WHERE menu_name = 'Vendors' AND route_path != '/staff/accounts/vendors';

-- ============================================================
-- SECTION 11: INVENTORY & MANUFACTURING (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/inventory/stock-items'
WHERE menu_name = 'Stock Items' AND route_path != '/staff/inventory/stock-items';

UPDATE staff_menu_master SET route_path = '/staff/inventory/stock-ledger'
WHERE menu_name = 'Stock Ledger' AND route_path != '/staff/inventory/stock-ledger';

UPDATE staff_menu_master SET route_path = '/staff/inventory/stock-transfers'
WHERE menu_name = 'Stock Transfers' AND route_path != '/staff/inventory/stock-transfers';

UPDATE staff_menu_master SET route_path = '/staff/inventory/bom'
WHERE menu_name = 'Bill of Materials' AND route_path != '/staff/inventory/bom';

UPDATE staff_menu_master SET route_path = '/staff/inventory/manufacturing'
WHERE menu_name = 'Manufacturing' AND route_path != '/staff/inventory/manufacturing';

UPDATE staff_menu_master SET route_path = '/staff/inventory/procurement'
WHERE menu_name = 'Procurement Planning' AND route_path != '/staff/inventory/procurement';

-- ============================================================
-- SECTION 12: BUSINESS PARTNERS (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/partners/master'
WHERE menu_name = 'Partner Master' AND route_path != '/staff/partners/master';

UPDATE staff_menu_master SET route_path = '/staff/partners/orders'
WHERE menu_name = 'Partner Orders' AND route_path != '/staff/partners/orders';

UPDATE staff_menu_master SET route_path = '/staff/partners/pricing'
WHERE menu_name = 'Partner Pricing' AND route_path != '/staff/partners/pricing';

UPDATE staff_menu_master SET route_path = '/staff/partners/approval'
WHERE menu_name = 'Order Approval' AND route_path != '/staff/partners/approval';

UPDATE staff_menu_master SET route_path = '/staff/partners/routing'
WHERE menu_name = 'Order Routing' AND route_path != '/staff/partners/routing';

UPDATE staff_menu_master SET route_path = '/staff/partners/fulfillment'
WHERE menu_name = 'Order Fulfillment' AND route_path != '/staff/partners/fulfillment';

UPDATE staff_menu_master SET route_path = '/staff/partners/dispatch'
WHERE menu_name = 'Partner Dispatch' AND route_path != '/staff/partners/dispatch';

UPDATE staff_menu_master SET route_path = '/staff/partners/invoices'
WHERE menu_name = 'Partner Invoices' AND route_path != '/staff/partners/invoices';

UPDATE staff_menu_master SET route_path = '/staff/partners/payments'
WHERE menu_name = 'Partner Payments' AND route_path != '/staff/partners/payments';

-- ============================================================
-- SECTION 13: REAL DREAMS (RVZ Staff View)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/rvz/real-dreams/dashboard'
WHERE menu_name = 'Real Dreams Dashboard' AND route_path NOT IN ('/rvz/real-dreams/dashboard', '/partner/real-dreams/dashboard');

UPDATE staff_menu_master SET route_path = '/rvz/real-dreams/partners'
WHERE menu_name = 'Real Dreams Partners' AND route_path != '/rvz/real-dreams/partners';

UPDATE staff_menu_master SET route_path = '/rvz/real-dreams/properties'
WHERE menu_name = 'Real Dreams Properties' AND route_path != '/rvz/real-dreams/properties';

-- ============================================================
-- SECTION 14: ADMINISTRATION (Staff)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/staff/dashboard'
WHERE menu_name = 'Staff Dashboard' AND route_path != '/staff/dashboard';

UPDATE staff_menu_master SET route_path = '/staff/employees'
WHERE menu_name = 'Employees' AND route_path != '/staff/employees';

UPDATE staff_menu_master SET route_path = '/staff/employee-directory'
WHERE menu_name = 'Employee Directory' AND route_path != '/staff/employee-directory';

UPDATE staff_menu_master SET route_path = '/staff/departments'
WHERE menu_name = 'Departments' AND route_path != '/staff/departments';

UPDATE staff_menu_master SET route_path = '/staff/kyc-approvals'
WHERE menu_name = 'KYC Approvals' AND route_path != '/staff/kyc-approvals';

UPDATE staff_menu_master SET route_path = '/staff/signup-categories'
WHERE menu_name = 'Signup Categories' AND route_path != '/staff/signup-categories';

UPDATE staff_menu_master SET route_path = '/staff/settings'
WHERE menu_name = 'Settings' AND route_path != '/staff/settings';

UPDATE staff_menu_master SET route_path = '/staff/audit-logs'
WHERE menu_name = 'Audit Logs' AND route_path != '/staff/audit-logs';

UPDATE staff_menu_master SET route_path = '/staff/change-password'
WHERE menu_name = 'Change Password' AND route_path = '/staff/change-password';

UPDATE staff_menu_master SET route_path = '/staff/2fa-settings'
WHERE menu_name = '2FA Settings' AND route_path != '/staff/2fa-settings';

-- ============================================================
-- SECTION 15: RVZ ADMIN MENUS
-- ============================================================
UPDATE staff_menu_master SET route_path = '/rvz/dashboard'
WHERE menu_name = 'RVZ Dashboard' AND route_path != '/rvz/dashboard';

UPDATE staff_menu_master SET route_path = '/rvz/menu-access-config'
WHERE menu_name = 'Menu Access Control' AND route_path != '/rvz/menu-access-config';

UPDATE staff_menu_master SET route_path = '/rvz/department-management'
WHERE menu_name = 'Department Management' AND route_path != '/rvz/department-management';

UPDATE staff_menu_master SET route_path = '/rvz/banner-oversight'
WHERE menu_name = 'Banner Oversight' AND route_path != '/rvz/banner-oversight';

UPDATE staff_menu_master SET route_path = '/rvz/banners-management'
WHERE menu_name = 'Banners Management' AND route_path = '/rvz/banners-management';

-- ============================================================
-- SECTION 16: PARTNER PORTAL MENUS (for partner_menu_master if exists)
-- ============================================================
UPDATE staff_menu_master SET route_path = '/partner-portal/dashboard'
WHERE menu_name = 'Partner Dashboard' AND route_path != '/partner-portal/dashboard';

UPDATE staff_menu_master SET route_path = '/partner-portal/orders'
WHERE menu_name = 'My Orders' AND route_path != '/partner-portal/orders';

UPDATE staff_menu_master SET route_path = '/partner-portal/invoices'
WHERE menu_name = 'My Invoices' AND route_path != '/partner-portal/invoices';

UPDATE staff_menu_master SET route_path = '/partner-portal/payments'
WHERE menu_name = 'My Payments' AND route_path != '/partner-portal/payments';

UPDATE staff_menu_master SET route_path = '/partner-portal/products'
WHERE menu_name = 'Product Catalog' AND route_path != '/partner-portal/products';

UPDATE staff_menu_master SET route_path = '/partner-portal/profile'
WHERE menu_name = 'My Profile' AND route_path != '/partner-portal/profile';

UPDATE staff_menu_master SET route_path = '/partner-portal/reports'
WHERE menu_name = 'Reports' AND route_path = '/partner-portal/reports';

UPDATE staff_menu_master SET route_path = '/partner-portal/support'
WHERE menu_name = 'Support' AND route_path != '/partner-portal/support';

-- ============================================================
-- SECTION 17: PARTNER REAL DREAMS MENUS
-- ============================================================
UPDATE staff_menu_master SET route_path = '/partner/real-dreams/dashboard'
WHERE menu_name = 'Real Dreams Dashboard' AND route_path = '/partner/real-dreams/dashboard';

UPDATE staff_menu_master SET route_path = '/partner/real-dreams/properties'
WHERE menu_name = 'My Properties' AND route_path != '/partner/real-dreams/properties';

UPDATE staff_menu_master SET route_path = '/partner/real-dreams/leads'
WHERE menu_name = 'My Leads' AND route_path != '/partner/real-dreams/leads';

UPDATE staff_menu_master SET route_path = '/partner/real-dreams/commissions'
WHERE menu_name = 'Commissions' AND route_path != '/partner/real-dreams/commissions';

-- ============================================================
-- VERIFICATION: Check all menu paths
-- ============================================================
SELECT menu_name, route_path, COUNT(*) as count
FROM staff_menu_master 
WHERE is_active = true
GROUP BY menu_name, route_path
ORDER BY menu_name;
