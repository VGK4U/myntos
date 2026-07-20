-- ============================================================================
-- MNR REFERENCE PROGRAM - DEACTIVATE TEST ACCOUNTS
-- Run this script to disable all test accounts after 24 hours or when done
-- ============================================================================

-- Deactivate Staff Test Account
UPDATE staff_employees 
SET status = 'inactive', 
    updated_at = NOW(),
    status_changed_at = NOW(),
    status_change_reason = 'Test account expired - 24 hour limit'
WHERE emp_code = 'ViewTEST';

-- Deactivate MNR Test User
UPDATE "user" 
SET account_status = 'SUSPENDED'
WHERE bev_legacy_id = 'MNRTEST001';

-- Deactivate All Partner Test Accounts
UPDATE official_partners 
SET is_active = false, 
    login_status = 'SUSPENDED',
    updated_at = NOW()
WHERE partner_code LIKE 'VENDTEST%';

-- Verification
SELECT 'DEACTIVATED' as action, 'STAFF' as type, emp_code, status 
FROM staff_employees WHERE emp_code = 'ViewTEST'
UNION ALL
SELECT 'DEACTIVATED', 'MNR', bev_legacy_id, account_status 
FROM "user" WHERE bev_legacy_id = 'MNRTEST001'
UNION ALL
SELECT 'DEACTIVATED', 'PARTNER', partner_code, login_status 
FROM official_partners WHERE partner_code LIKE 'VENDTEST%';

-- ============================================================================
-- END OF DEACTIVATION SCRIPT
-- ============================================================================
