-- =====================================================================
-- Menu Access Control Fix Migration
-- DC Protocol Compliant - Dec 21, 2025
-- =====================================================================
-- This script fixes:
-- 1. Inconsistent route paths for Task pages
-- 2. Missing reimbursement pages in staff_menu_master
-- 3. Syncs all employees/partners with proper menu settings
-- =====================================================================

-- =====================================================================
-- PHASE 1: Fix Task route path inconsistencies
-- =====================================================================

-- Fix Task Tracker route path
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/tracker'
WHERE menu_code = 'staff_task_tracker' 
  AND route_path != '/staff/tasks/tracker';

-- Fix Tasks Assigned to Me route path
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/assigned-to-me'
WHERE menu_code = 'staff_tasks_assigned_to_me' 
  AND route_path != '/staff/tasks/assigned-to-me';

-- Fix Tasks Assigned by Me route path (now uses -v2)
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/assigned-by-me-v2'
WHERE menu_code = 'staff_tasks_assigned_by_me' 
  AND route_path != '/staff/tasks/assigned-by-me-v2';

-- Task Review is already correct (/staff/task-review)

-- =====================================================================
-- PHASE 2: Seed missing reimbursement pages for all companies
-- =====================================================================

-- Get all distinct company_ids that have staff_menu_master entries
-- and insert reimbursement pages for each

-- Insert My Reimbursement Claims for all companies that don't have it
INSERT INTO staff_menu_master (company_id, menu_code, menu_name, menu_category, menu_icon, route_path, display_order, audience_scope, is_active, is_default_visible, is_default_accessible, created_at, updated_at)
SELECT DISTINCT 
    smm.company_id,
    'sfms_my_reimbursements',
    'My Reimbursement Claims',
    'sfms_reimbursements',
    'fas fa-receipt',
    '/staff/accounts/my-reimbursements',
    230,
    'staff',
    true,
    true,
    true,
    NOW(),
    NOW()
FROM staff_menu_master smm
WHERE NOT EXISTS (
    SELECT 1 FROM staff_menu_master 
    WHERE company_id = smm.company_id 
      AND menu_code = 'sfms_my_reimbursements'
);

-- Insert Reimbursement Approvals for all companies that don't have it
INSERT INTO staff_menu_master (company_id, menu_code, menu_name, menu_category, menu_icon, route_path, display_order, audience_scope, is_active, is_default_visible, is_default_accessible, created_at, updated_at)
SELECT DISTINCT 
    smm.company_id,
    'sfms_reimbursement_approvals',
    'Reimbursement Approvals',
    'sfms_reimbursements',
    'fas fa-check-double',
    '/staff/accounts/reimbursement-approvals',
    231,
    'staff',
    true,
    false,
    false,
    NOW(),
    NOW()
FROM staff_menu_master smm
WHERE NOT EXISTS (
    SELECT 1 FROM staff_menu_master 
    WHERE company_id = smm.company_id 
      AND menu_code = 'sfms_reimbursement_approvals'
);

-- =====================================================================
-- PHASE 3: Fix CRM route paths to match sidebar
-- =====================================================================

-- CRM Dashboard should use /staff/crm/dashboard
UPDATE staff_menu_master 
SET route_path = '/staff/crm/dashboard'
WHERE menu_code = 'crm_dashboard' 
  AND route_path NOT IN ('/staff/crm/dashboard', '/crm/dashboard');

-- CRM Leads should use /staff/crm/leads  
UPDATE staff_menu_master 
SET route_path = '/staff/crm/leads'
WHERE menu_code = 'crm_leads' 
  AND route_path NOT IN ('/staff/crm/leads', '/crm/leads', '/rvz/crm/leads');

-- =====================================================================
-- VERIFICATION QUERIES (Run these to verify the fix)
-- =====================================================================

-- Check Task route consistency
-- SELECT DISTINCT route_path, menu_name, COUNT(*) 
-- FROM staff_menu_master 
-- WHERE menu_category = 'staff_tasks' 
-- GROUP BY route_path, menu_name
-- ORDER BY menu_name;

-- Check Reimbursement pages exist
-- SELECT company_id, menu_code, menu_name, route_path 
-- FROM staff_menu_master 
-- WHERE menu_category = 'sfms_reimbursements' AND is_active = true
-- ORDER BY company_id;

-- Check employee settings count per employee
-- SELECT se.emp_code, se.full_name, COUNT(sems.id) as settings_count
-- FROM staff_employees se
-- LEFT JOIN staff_employee_menu_settings sems ON se.id = sems.employee_id
-- WHERE se.status = 'active'
-- GROUP BY se.id, se.emp_code, se.full_name
-- ORDER BY settings_count ASC;
