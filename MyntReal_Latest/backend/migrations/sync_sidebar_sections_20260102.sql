-- DC Protocol Migration: Sync sidebar_section values for unified menu
-- Date: January 2, 2026
-- Purpose: Update staff_menu_registry with correct sidebar_section, title, order, parent, submenu, and menu_type values
-- This ensures production menu matches development

-- STAFF DASHBOARD Section (Order 5)
UPDATE staff_menu_registry SET sidebar_section='STAFF_DASHBOARD', sidebar_section_title='STAFF DASHBOARD', sidebar_section_order=5, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_dashboard', 'staff_employees', 'staff_employee_directory', 'staff_kyc_approvals', 'staff_my_kyc', 'staff_change_password', 'staff_audit_logs');

-- ATTENDANCE Section (Order 15)
UPDATE staff_menu_registry SET sidebar_section='attendance', sidebar_section_title='ATTENDANCE', sidebar_section_order=15, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_my_attendance', 'staff_team_attendance', 'staff_attendance_sheet', 'staff_attendance_reports', 'staff_attendance_exceptions');

-- CRM Section (Order 16)
UPDATE staff_menu_registry SET sidebar_section='crm', sidebar_section_title='CRM', sidebar_section_order=16, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_crm_dashboard', 'staff_team_leads');

-- SERVICE TICKETS Section (Order 6)
UPDATE staff_menu_registry SET sidebar_section='service-tickets', sidebar_section_title='SERVICE TICKETS', sidebar_section_order=6, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('service_tickets_queue', 'service_tickets_raise', 'service_tickets_procurement', 'staff_service_tickets_dashboard', 'staff_service_tickets_procurement', 'staff_service_tickets_performance', 'staff_service_tickets_reports');

-- KRA MANAGEMENT Section (Order 45)
UPDATE staff_menu_registry SET sidebar_section='kra-management', sidebar_section_title='KRA MANAGEMENT', sidebar_section_order=45, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_my_kras', 'staff_kra_templates', 'staff_kra_review', 'staff_kra_tracking_sheet');

-- TASK MANAGEMENT Section (Order 85)
UPDATE staff_menu_registry SET sidebar_section='task-management', sidebar_section_title='TASK MANAGEMENT', sidebar_section_order=85, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_tasks_assigned_by_me', 'staff_tasks_assigned_to_me', 'staff_task_tracker', 'staff_task_review', 'staff_tasks_team_activities');

-- JOURNEYS Section (Order 1)
UPDATE staff_menu_registry SET sidebar_section='journeys', sidebar_section_title='JOURNEYS', sidebar_section_order=1, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_my_journeys', 'staff_team_journeys', 'staff_all_journeys', 'staff_vgk4u_journeys');

-- TIMESHEET Section (Order 2)
UPDATE staff_menu_registry SET sidebar_section='timesheet', sidebar_section_title='TIMESHEET', sidebar_section_order=2, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_my_timesheet', 'staff_timesheet_approval');

-- ZYNOVA Parent Section - Create ZY Property Workings submenu
UPDATE staff_menu_registry SET sidebar_section='real-dreams', sidebar_section_title='ZY Property Workings', sidebar_section_order=65, parent_section='zynova', is_submenu=true, menu_type='STAFF' WHERE menu_code IN ('rvz_real_dreams_marketplace', 'rvz_real_dreams_dashboard_v2', 'rvz_real_dreams_partners_v2', 'rvz_real_dreams_properties_v2', 'rvz_real_dreams');

-- ZYNOVA Parent Section - Create ZY Member Earnings submenu
UPDATE staff_menu_registry SET sidebar_section='zy-member-earnings', sidebar_section_title='ZY Member Earnings', sidebar_section_order=35, parent_section='zynova', is_submenu=true, menu_type='STAFF' WHERE menu_code IN ('staff_incentives_approvals', 'staff_incentives_zynova', 'staff_zynova_real_estate', 'staff_zynova_insurance');

-- MNR Parent Section - Create MNR Users submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-users', sidebar_section_title='MNR Users', sidebar_section_order=0, parent_section='mnr', is_submenu=true, menu_type='STAFF' WHERE menu_code = 'staff_new_mnr_users';

-- MNR Parent Section - Create MNR Coupons submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-coupons', sidebar_section_title='MNR Coupons', sidebar_section_order=110, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE menu_code IN ('coupon_status', 'admin_coupons_activate');

-- MNR Parent Section - Create MNR Awards & Bonanza submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-awards', sidebar_section_title='MNR Awards & Bonanza', sidebar_section_order=115, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE menu_code LIKE 'admin_awards%' OR menu_code LIKE 'admin_bonanza%';

-- MNR Parent Section - Create MNR Income submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-income', sidebar_section_title='MNR Income', sidebar_section_order=35, parent_section='mnr', is_submenu=true, menu_type='STAFF' WHERE menu_code IN ('staff_incentives_points');

-- MNR Parent Section - Create MNR Withdrawals submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-withdrawals', sidebar_section_title='MNR Withdrawals', sidebar_section_order=145, parent_section='mnr', is_submenu=true, menu_type='MNR' WHERE menu_code LIKE '%withdrawal%';

-- MNR Parent Section - Create MNR CRM submenu
UPDATE staff_menu_registry SET sidebar_section='mnr-crm', sidebar_section_title='MNR CRM', sidebar_section_order=16, parent_section='mnr', is_submenu=true, menu_type='STAFF' WHERE menu_code = 'staff_my_leads';

-- BUSINESS PARTNERS Section (Order 20)
UPDATE staff_menu_registry SET sidebar_section='business-partners', sidebar_section_title='BUSINESS PARTNERS', sidebar_section_order=20, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('order_fulfillment_dashboard', 'staff_partners_orders', 'staff_partners_pricing', 'staff_partners_approval', 'staff_partners_routing', 'staff_partners_fulfillment', 'staff_partners_dispatch', 'staff_partners_invoices', 'staff_partners_payments');

-- CONFIGURATION Section (Order 25)
UPDATE staff_menu_registry SET sidebar_section='configuration', sidebar_section_title='CONFIGURATION', sidebar_section_order=25, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_departments', 'sfms_companies', 'staff_partners_master', 'sfms_segments', 'sfms_pricing', 'sfms_hsn', 'rvz_signup_categories', 'rvz_menu_access', 'sfms_expense_categories', 'staff_settings');

-- LOCATION TRACKING Section (Order 50)
UPDATE staff_menu_registry SET sidebar_section='location-tracking', sidebar_section_title='LOCATION TRACKING', sidebar_section_order=50, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_my_location_history', 'staff_team_location_tracker', 'staff_all_location_tracker', 'staff_team_live_tracker');

-- MANAGER REVIEW Section (Order 55)
UPDATE staff_menu_registry SET sidebar_section='manager-review', sidebar_section_title='MANAGER REVIEW', sidebar_section_order=55, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_manager_review', 'staff_task_review');

-- NDA MANAGEMENT Section (Order 60)
UPDATE staff_menu_registry SET sidebar_section='nda-management', sidebar_section_title='NDA MANAGEMENT', sidebar_section_order=60, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_nda_versions', 'staff_nda_editor', 'staff_nda_acceptance_audit', 'staff_nda_pending');

-- SFMS Section (Order 75)
UPDATE staff_menu_registry SET sidebar_section='sfms', sidebar_section_title='SFMS', sidebar_section_order=75, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_accounts_balance_sheet', 'staff_accounts_fund_allocations', 'staff_accounts_expense_entries', 'staff_accounts_income_entries', 'staff_accounts_purchase_invoices', 'staff_accounts_reports', 'staff_accounts_payables', 'staff_accounts_receivables', 'staff_accounts_party_ledger', 'staff_accounts_vendors');

-- SFMS INVENTORY Section (Order 80)
UPDATE staff_menu_registry SET sidebar_section='sfms-inventory', sidebar_section_title='SFMS INVENTORY', sidebar_section_order=80, parent_section=NULL, is_submenu=false, menu_type='STAFF' WHERE menu_code IN ('staff_inventory_stock_items', 'staff_inventory_stock_ledger', 'staff_inventory_stock_transfers', 'staff_accounts_bom', 'staff_accounts_manufacturing');

-- FINANCE Section (Order 105) - MNR type
UPDATE staff_menu_registry SET sidebar_section='finance', sidebar_section_title='FINANCE', sidebar_section_order=105, parent_section=NULL, is_submenu=false, menu_type='MNR' WHERE menu_code LIKE 'admin_earnings%' OR menu_code LIKE 'admin_income%';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'DC Protocol Migration completed: sidebar_section values synchronized';
END $$;
