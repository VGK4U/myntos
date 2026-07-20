-- DC Protocol Migration: Sync sidebar sections by ROUTE PATH (not menu_code)
-- Date: January 2, 2026
-- Purpose: Production has different menu_code values, so we use route_path which is consistent

-- STAFF DASHBOARD Section
UPDATE staff_menu_registry SET sidebar_section='STAFF_DASHBOARD', sidebar_section_title='STAFF DASHBOARD', sidebar_section_order=5, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path IN ('/staff/dashboard', '/staff/employees', '/staff/employee-directory', '/staff/kyc-approvals', '/staff/my-kyc', '/staff/change-password', '/staff/audit-logs');

-- ATTENDANCE Section
UPDATE staff_menu_registry SET sidebar_section='attendance', sidebar_section_title='ATTENDANCE', sidebar_section_order=15, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path IN ('/staff/my-attendance', '/staff/team-attendance', '/staff/attendance-sheet', '/staff/attendance-reports', '/staff/attendance-exceptions');

-- CRM Section
UPDATE staff_menu_registry SET sidebar_section='crm', sidebar_section_title='CRM', sidebar_section_order=16, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path IN ('/staff/crm-dashboard', '/staff/team-leads', '/rvz/crm-leads');

-- SERVICE TICKETS Section
UPDATE staff_menu_registry SET sidebar_section='service-tickets', sidebar_section_title='SERVICE TICKETS', sidebar_section_order=6, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%service-ticket%' OR route_path LIKE '%service_ticket%';

-- KRA MANAGEMENT Section
UPDATE staff_menu_registry SET sidebar_section='kra-management', sidebar_section_title='KRA MANAGEMENT', sidebar_section_order=45, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%kra%';

-- TASK MANAGEMENT Section
UPDATE staff_menu_registry SET sidebar_section='task-management', sidebar_section_title='TASK MANAGEMENT', sidebar_section_order=85, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%task%';

-- JOURNEYS Section
UPDATE staff_menu_registry SET sidebar_section='journeys', sidebar_section_title='JOURNEYS', sidebar_section_order=1, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%journey%';

-- TIMESHEET Section
UPDATE staff_menu_registry SET sidebar_section='timesheet', sidebar_section_title='TIMESHEET', sidebar_section_order=2, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%timesheet%';

-- ZYNOVA - ZY Property Workings submenu
UPDATE staff_menu_registry SET sidebar_section='real-dreams', sidebar_section_title='ZY Property Workings', sidebar_section_order=65, parent_section='zynova', is_submenu=true, menu_type='STAFF' WHERE route_path LIKE '%real-dreams%' OR route_path LIKE '%real_dreams%';

-- ZYNOVA - ZY Member Earnings submenu
UPDATE staff_menu_registry SET sidebar_section='zy-member-earnings', sidebar_section_title='ZY Member Earnings', sidebar_section_order=35, parent_section='zynova', is_submenu=true, menu_type='STAFF' WHERE route_path IN ('/staff/incentives-approvals', '/staff/incentives-zynova', '/staff/zynova-real-estate', '/staff/zynova-insurance', '/rvz/incentive-approvals', '/rvz/zynova-members', '/rvz/vgk-real-dreams', '/rvz/vgk-care');

-- MNR - Users submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-users', sidebar_section_title='MNR Users', sidebar_section_order=0, parent_section='mnr', is_submenu=true, menu_type='STAFF' WHERE route_path IN ('/staff/new-mnr-users', '/admin/all-users', '/admin/password-reset');

-- MNR - Coupons submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-coupons', sidebar_section_title='MNR Coupons', sidebar_section_order=110, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE route_path LIKE '%coupon%';

-- MNR - Awards & Bonanza submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-awards', sidebar_section_title='MNR Awards & Bonanza', sidebar_section_order=115, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE route_path LIKE '%award%' OR route_path LIKE '%bonanza%';

-- MNR - Income submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-income', sidebar_section_title='MNR Income', sidebar_section_order=35, parent_section='mnr', is_submenu=true, menu_type='STAFF' WHERE route_path LIKE '%income%' OR route_path LIKE '%incentives-points%' OR route_path LIKE '%points%';

-- MNR - Withdrawals submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-withdrawals', sidebar_section_title='MNR Withdrawals', sidebar_section_order=145, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE route_path LIKE '%withdrawal%';

-- MNR - CRM submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-crm', sidebar_section_title='MNR CRM', sidebar_section_order=16, parent_section='mnr', is_submenu=true, menu_type='STAFF' WHERE route_path = '/staff/my-leads';

-- MNR - Communications submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-communications', sidebar_section_title='MNR Communications', sidebar_section_order=120, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE route_path LIKE '%banner%' OR route_path LIKE '%popup%' OR route_path LIKE '%birthday%';

-- MNR - Terms & Conditions submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-terms', sidebar_section_title='MNR Terms & Conditions', sidebar_section_order=125, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE route_path LIKE '%terms%' OR route_path LIKE '%t-c%' OR route_path LIKE '%tc-%';

-- MNR - Approvals submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-approvals', sidebar_section_title='MNR Approvals', sidebar_section_order=130, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE route_path LIKE '%pin-purchase%' OR route_path LIKE '%pin-approval%' OR route_path LIKE '%all-pins%';

-- BUSINESS PARTNERS Section
UPDATE staff_menu_registry SET sidebar_section='business-partners', sidebar_section_title='BUSINESS PARTNERS', sidebar_section_order=20, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%partners%' AND route_path NOT LIKE '%real-dreams%';

-- CONFIGURATION Section
UPDATE staff_menu_registry SET sidebar_section='configuration', sidebar_section_title='CONFIGURATION', sidebar_section_order=25, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path IN ('/staff/departments', '/sfms/companies', '/staff/partners-master', '/sfms/segments', '/sfms/pricing', '/sfms/hsn', '/rvz/signup-categories', '/rvz/menu-access-config', '/sfms/expense-categories', '/staff/settings', '/rvz/department-management');

-- LOCATION TRACKING Section
UPDATE staff_menu_registry SET sidebar_section='location-tracking', sidebar_section_title='LOCATION TRACKING', sidebar_section_order=50, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%location%' OR route_path LIKE '%tracker%' OR route_path LIKE '%live-tracker%';

-- MANAGER REVIEW Section
UPDATE staff_menu_registry SET sidebar_section='manager-review', sidebar_section_title='MANAGER REVIEW', sidebar_section_order=55, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%manager-review%';

-- NDA MANAGEMENT Section
UPDATE staff_menu_registry SET sidebar_section='nda-management', sidebar_section_title='NDA MANAGEMENT', sidebar_section_order=60, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%nda%';

-- SFMS Section
UPDATE staff_menu_registry SET sidebar_section='sfms', sidebar_section_title='SFMS', sidebar_section_order=75, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '/sfms/%' OR route_path LIKE '/staff/accounts-%';

-- SFMS INVENTORY Section
UPDATE staff_menu_registry SET sidebar_section='sfms-inventory', sidebar_section_title='SFMS INVENTORY', sidebar_section_order=80, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '%inventory%' OR route_path LIKE '%stock-%' OR route_path LIKE '%bom%' OR route_path LIKE '%manufacturing%';

-- FINANCE Section (legacy admin)
UPDATE staff_menu_registry SET sidebar_section='finance', sidebar_section_title='FINANCE', sidebar_section_order=105, parent_section=NULL, is_submenu=false, menu_type='MNR' WHERE route_path LIKE '/admin/earning%' OR route_path LIKE '/admin/income%';

-- PARTNER PORTAL Section
UPDATE staff_menu_registry SET sidebar_section='partner-portal', sidebar_section_title='PARTNER PORTAL', sidebar_section_order=90, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '/partner/%';

-- Catch-all for remaining admin/* routes - put in legacy sections
UPDATE staff_menu_registry SET sidebar_section='WORKING_MNR', sidebar_section_title='WORKING MNR', sidebar_section_order=999, parent_section=NULL, is_submenu=false, menu_type='MNR' WHERE route_path LIKE '/admin/%' AND sidebar_section NOT IN ('mnr-users', 'mnr-coupons', 'mnr-awards', 'mnr-income', 'mnr-withdrawals', 'mnr-crm', 'mnr-communications', 'mnr-terms', 'mnr-approvals', 'finance');

-- Catch-all for remaining rvz/* routes  
UPDATE staff_menu_registry SET sidebar_section='WORKING_STAFF', sidebar_section_title='WORKING STAFF', sidebar_section_order=998, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE route_path LIKE '/rvz/%' AND sidebar_section NOT IN ('real-dreams', 'zy-member-earnings', 'configuration', 'crm');
