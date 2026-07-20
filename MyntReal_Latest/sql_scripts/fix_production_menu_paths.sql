-- ============================================================
-- PRODUCTION DATABASE FIX: Standardize Menu Route Paths
-- Created: December 19, 2025
-- DC Protocol Compliant - Safe for Multi-Company Environment
-- ============================================================
-- PURPOSE: Align production menu paths with frontend sidebar structure
-- ISSUE: Production has legacy paths that don't match canonical sidebar URLs
-- SAFETY: All updates are idempotent (safe to run multiple times)
-- ============================================================

-- ============================================================
-- SECTION 1: TASK MANAGEMENT MENU FIXES
-- ============================================================

-- Fix Task Tracker: /staff/task-tracker → /staff/tasks/tracker
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/tracker',
    updated_at = NOW()
WHERE menu_name = 'Task Tracker' 
AND route_path = '/staff/task-tracker';

-- Fix Tasks Assigned to Me: /staff/tasks-assigned-to-me → /staff/tasks/assigned-to-me
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/assigned-to-me',
    updated_at = NOW()
WHERE menu_name = 'Tasks Assigned to Me' 
AND route_path = '/staff/tasks-assigned-to-me';

-- Fix Tasks Assigned by Me: /staff/tasks-assigned-by-me → /staff/tasks/assigned-by-me-v2
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/assigned-by-me-v2',
    updated_at = NOW()
WHERE menu_name = 'Tasks Assigned by Me' 
AND route_path = '/staff/tasks-assigned-by-me';

-- Fix Team Activities (if legacy exists)
UPDATE staff_menu_master 
SET route_path = '/staff/tasks/team-activities',
    updated_at = NOW()
WHERE menu_name = 'Team Activities' 
AND route_path != '/staff/tasks/team-activities';

-- ============================================================
-- SECTION 2: CRM/LEADS MENU FIXES (From user screenshot)
-- ============================================================

-- Fix CRM Dashboard: /crm/dashboard → /staff/crm/dashboard
UPDATE staff_menu_master 
SET route_path = '/staff/crm/dashboard',
    updated_at = NOW()
WHERE menu_name = 'CRM Dashboard' 
AND route_path = '/crm/dashboard';

-- Fix CRM Leads (multiple possible legacy paths)
UPDATE staff_menu_master 
SET route_path = '/rvz/crm/leads',
    updated_at = NOW()
WHERE menu_name = 'CRM Leads' 
AND route_path IN ('/crm/leads', '/staff/crm/leads', '/rvz/crm-leads');

-- Fix Lead Sources: /crm/sources → /staff/crm/team-leads
UPDATE staff_menu_master 
SET route_path = '/staff/crm/team-leads',
    updated_at = NOW()
WHERE menu_name = 'Lead Sources' 
AND route_path = '/crm/sources';

-- ============================================================
-- SECTION 3: ATTENDANCE MENU FIXES
-- ============================================================

-- Attendance Sheet fix
UPDATE staff_menu_master 
SET route_path = '/staff/attendance-sheet',
    updated_at = NOW()
WHERE menu_name = 'Attendance Sheet' 
AND route_path NOT IN ('/staff/attendance-sheet');

-- My Attendance fix
UPDATE staff_menu_master 
SET route_path = '/staff/my-attendance',
    updated_at = NOW()
WHERE menu_name = 'My Attendance' 
AND route_path NOT IN ('/staff/my-attendance');

-- ============================================================
-- SECTION 4: JOURNEY TRACKING FIXES
-- ============================================================

UPDATE staff_menu_master 
SET route_path = '/staff/my-journeys',
    updated_at = NOW()
WHERE menu_name = 'My Journeys' 
AND route_path NOT IN ('/staff/my-journeys');

UPDATE staff_menu_master 
SET route_path = '/staff/team-journeys',
    updated_at = NOW()
WHERE menu_name = 'Team Journeys' 
AND route_path NOT IN ('/staff/team-journeys');

UPDATE staff_menu_master 
SET route_path = '/staff/all-journeys',
    updated_at = NOW()
WHERE menu_name = 'All Journeys' 
AND route_path NOT IN ('/staff/all-journeys');

-- ============================================================
-- SECTION 5: FINANCIAL MANAGEMENT (SFMS) FIXES
-- ============================================================

UPDATE staff_menu_master 
SET route_path = '/staff/accounts/balance-sheet',
    updated_at = NOW()
WHERE menu_name = 'Balance Sheet' 
AND route_path NOT IN ('/staff/accounts/balance-sheet');

UPDATE staff_menu_master 
SET route_path = '/staff/accounts/my-reimbursements',
    updated_at = NOW()
WHERE menu_name = 'My Reimbursements' 
AND route_path NOT IN ('/staff/accounts/my-reimbursements');

UPDATE staff_menu_master 
SET route_path = '/staff/accounts/reimbursement-approvals',
    updated_at = NOW()
WHERE menu_name = 'Reimbursement Approvals' 
AND route_path NOT IN ('/staff/accounts/reimbursement-approvals');

-- ============================================================
-- SECTION 6: REAL DREAMS FIXES (Staff Sidebar uses /rvz/real-dreams/*)
-- ============================================================

-- Staff Real Dreams Dashboard: Use /rvz/real-dreams/dashboard
UPDATE staff_menu_master 
SET route_path = '/rvz/real-dreams/dashboard',
    updated_at = NOW()
WHERE menu_name = 'Real Dreams Dashboard' 
AND route_path NOT IN ('/rvz/real-dreams/dashboard', '/partner/real-dreams/dashboard');

-- Staff Real Dreams Partners: Use /rvz/real-dreams/partners
UPDATE staff_menu_master 
SET route_path = '/rvz/real-dreams/partners',
    updated_at = NOW()
WHERE menu_name = 'Real Dreams Partners' 
AND route_path NOT IN ('/rvz/real-dreams/partners');

-- Staff Real Dreams Properties: Use /rvz/real-dreams/properties
UPDATE staff_menu_master 
SET route_path = '/rvz/real-dreams/properties',
    updated_at = NOW()
WHERE menu_name = 'Real Dreams Properties' 
AND route_path NOT IN ('/rvz/real-dreams/properties');

-- NOTE: Partner-specific menus (My Properties, My Leads, Commissions) 
-- use /partner/real-dreams/* and are handled in partner_menu_master table

-- ============================================================
-- SECTION 7: VERIFICATION QUERIES
-- Run these AFTER the updates to verify success
-- ============================================================

-- Verify Task Management paths
SELECT id, menu_name, route_path, company_id 
FROM staff_menu_master 
WHERE menu_name ILIKE '%task%' 
ORDER BY menu_name, company_id
LIMIT 30;

-- Verify CRM paths
SELECT id, menu_name, route_path, company_id 
FROM staff_menu_master 
WHERE menu_name ILIKE '%crm%' OR menu_name ILIKE '%lead%'
ORDER BY menu_name, company_id
LIMIT 30;

-- Check for any remaining path mismatches (paths without proper prefixes)
SELECT DISTINCT menu_name, route_path, COUNT(*) as count
FROM staff_menu_master 
WHERE is_active = true
AND route_path NOT LIKE '/staff/%'
AND route_path NOT LIKE '/rvz/%'
AND route_path NOT LIKE '/partner/%'
AND route_path NOT LIKE '/admin/%'
AND route_path NOT LIKE '/user/%'
AND route_path NOT LIKE '/finance/%'
AND route_path NOT LIKE '/superadmin/%'
AND route_path NOT LIKE '/real-dreams/%'
AND route_path NOT LIKE '/partner-portal/%'
GROUP BY menu_name, route_path
ORDER BY menu_name;

-- ============================================================
-- ROLLBACK GUIDANCE (If needed)
-- Save original values BEFORE running updates:
-- SELECT id, menu_name, route_path INTO backup_menu_paths FROM staff_menu_master;
-- ============================================================
