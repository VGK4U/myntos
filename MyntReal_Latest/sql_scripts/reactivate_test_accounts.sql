-- ============================================================================
-- MNR REFERENCE PROGRAM - REACTIVATE TEST ACCOUNTS FOR ANOTHER 24 HOURS
-- Run this script to re-enable all test accounts for another 24-hour period
-- ============================================================================

-- Reactivate Staff Test Account
UPDATE staff_employees 
SET status = 'active', 
    updated_at = NOW(),
    status_changed_at = NOW(),
    status_change_reason = 'Test account reactivated for 24 hours',
    failed_login_attempts = 0,
    locked_until = NULL
WHERE emp_code = 'ViewTEST';

-- Reactivate MNR Test User
UPDATE "user" 
SET account_status = 'ACTIVE'
WHERE bev_legacy_id = 'MNRTEST001';

-- Reactivate All Partner Test Accounts
UPDATE official_partners 
SET is_active = true, 
    login_status = 'ACTIVE',
    updated_at = NOW(),
    failed_login_attempts = 0
WHERE partner_code LIKE 'VENDTEST%';

-- Verification
SELECT 'REACTIVATED' as action, 'STAFF' as type, emp_code, status 
FROM staff_employees WHERE emp_code = 'ViewTEST'
UNION ALL
SELECT 'REACTIVATED', 'MNR', bev_legacy_id, account_status 
FROM "user" WHERE bev_legacy_id = 'MNRTEST001'
UNION ALL
SELECT 'REACTIVATED', 'PARTNER', partner_code, login_status 
FROM official_partners WHERE partner_code LIKE 'VENDTEST%';

-- ============================================================================
-- REMINDER: Run deactivate_test_accounts.sql after 24 hours
-- ============================================================================
