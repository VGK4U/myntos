-- ============================================================================
-- MNR TEST ACCOUNTS - STEP BY STEP (Run each section separately)
-- ============================================================================

-- ============================================================================
-- STEP 1: CLEANUP FIRST (Run this first!)
-- ============================================================================
DELETE FROM staff_employee_menu_settings WHERE employee_id IN (SELECT id FROM staff_employees WHERE emp_code = 'ViewTEST');
DELETE FROM partner_menu_settings WHERE partner_id IN (SELECT id FROM official_partners WHERE partner_code LIKE 'VENDTEST%');
DELETE FROM staff_employees WHERE emp_code = 'ViewTEST';
DELETE FROM "user" WHERE id = 'MNRTEST001';
DELETE FROM official_partners WHERE partner_code LIKE 'VENDTEST%';

-- ============================================================================
-- STEP 2: CREATE STAFF ACCOUNT (Run this next)
-- Employee ID: ViewTEST, Password: CKd65kcemtw3
-- ============================================================================
INSERT INTO staff_employees (emp_code, full_name, first_name, last_name, email, phone, department_id, designation, role_id, status, staff_type, date_of_joining, password_hash, is_deleted, requires_password_change, kyc_status, base_company_id, data_companies, created_at, updated_at)
VALUES ('ViewTEST', 'Test User (VIEW ONLY)', 'Test', 'User', 'viewtest@myntreal.com', '9999999901', 1, 'Test Account', 1, 'active', 'VGK4U', CURRENT_DATE, 'scrypt:32768:8:1$Py5NMWXy9Wh0EhHU$407a11417df3f4718c1b2d62f6f2fcf52258a7dfd227d5ff55ead4b6ab34718af6b365719b6a21d158bc6a731367b60d2bd7bdbb028b6927a7ec261929e282a0', false, false, 'approved', 16, '[16, 17, 20, 21, 22, 31]'::jsonb, NOW(), NOW());

-- Verify:
SELECT 'STAFF CREATED' as result, emp_code, status FROM staff_employees WHERE emp_code = 'ViewTEST';

-- ============================================================================
-- STEP 3: CREATE MNR USER (Run this next)
-- MNR ID: MNRTEST001, Password: T6jZH82tVPw0
-- ============================================================================
INSERT INTO "user" (id, bev_legacy_id, name, email, password, user_type, wallet_balance, upgrade_wallet_balance, kyc_status, coupon_status, placement_status, is_ved, ved_paused, account_status, registration_date, referral_bonus_eligible, first_referral_bonus_paid, first_matching_achieved, excluded_from_regular_awards, profile_completion_score, earned_total, released_total, phone_number)
VALUES ('MNRTEST001', 'MNRTEST001', 'Test MNR User (VIEW ONLY)', 'mnrtest@myntreal.com', 'scrypt:32768:8:1$Yc2XnCSPzyb6yCYO$e5ad61ce0ca902252588ea84e34e06bfe1be6cae6191685824b9d066a446dc2f501aad01b0178927a31fb0bbbcd62b151abc0f2392c883aa30fca9ea0e6dcd61', 'USER', 0.0, 0.0, 'APPROVED', 'PENDING', 'Approved', false, false, 'Active', NOW(), false, false, false, false, 0, 0.0, 0.0, '9999999902');

-- Verify:
SELECT 'MNR CREATED' as result, id, account_status FROM "user" WHERE id = 'MNRTEST001';

-- ============================================================================
-- STEP 4: CREATE DEALER PARTNER
-- Partner Code: VENDTEST_DEALER, Password: xQmz8wLLl@FC
-- ============================================================================
INSERT INTO official_partners (partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at)
VALUES ('VENDTEST_DEALER', 'Test Dealer (VIEW ONLY)', 'DEALER', 'DEALER', 'Test Contact', '9999999903', 'testdealer@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$6jGjfsnipLbEpN6R$799127e54b00b6918ec21c49a9b4d789d635d49ecfe9bf926edbe7a51b8cc2771fba09911bcba7e6aa7700fd2b2b87ac72c8df505659a05005cf02f744a27a10', NOW(), NOW());

-- ============================================================================
-- STEP 5: CREATE DISTRIBUTOR PARTNER
-- Partner Code: VENDTEST_DIST, Password: UyOZC8j13FIb
-- ============================================================================
INSERT INTO official_partners (partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at)
VALUES ('VENDTEST_DIST', 'Test Distributor (VIEW ONLY)', 'DISTRIBUTOR', 'DISTRIBUTOR', 'Test Contact', '9999999904', 'testdistributor@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$VnQWsdMUh2X1KZNI$42c646239da02d3a73276b3e162cb7d090f173a4b9b6620f2f42372c9a74d9fa40d897b75bd65ce4bffcb1f92814703776af8405878da23a8a1ae3976dd12841', NOW(), NOW());

-- ============================================================================
-- STEP 6: CREATE VENDOR PARTNER
-- Partner Code: VENDTEST_VENDOR, Password: OOrTgmzjNJJr
-- ============================================================================
INSERT INTO official_partners (partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at)
VALUES ('VENDTEST_VENDOR', 'Test Vendor (VIEW ONLY)', 'VENDOR', 'VENDOR', 'Test Contact', '9999999905', 'testvendor@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$AbSWPsUzHgwfAaOM$1f5b4e000c20ed336765b132803c906f66ce64bdd43c35eb1b7ef28a752b26412ee1816c0a8f99d1433f2b96bd7703cd5bef0f49dc6c66fd9d81c6f8fc708fd9', NOW(), NOW());

-- ============================================================================
-- STEP 7: CREATE REAL DREAM PARTNER
-- Partner Code: VENDTEST_RD, Password: sHnaYHv!RDtM
-- ============================================================================
INSERT INTO official_partners (partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at)
VALUES ('VENDTEST_RD', 'Test Real Dream Partner (VIEW ONLY)', 'REAL_DREAM_PARTNER', 'REAL_DREAM_PARTNER', 'Test Contact', '9999999906', 'testrealdream@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$96XfvTheaZYPi8ab$38b52e1d5c00c9a455cf9d4f8f06429456a6bf21e0382a56750debfe3c2e22f8eeb04894c1c0d0b25d46b5248ac483bad6a02917d7b50d83bc43b8d03eab1788', NOW(), NOW());

-- Verify Partners:
SELECT 'PARTNERS CREATED' as result, partner_code, category, is_active FROM official_partners WHERE partner_code LIKE 'VENDTEST%';

-- ============================================================================
-- FINAL VERIFICATION
-- ============================================================================
SELECT 'STAFF' as type, emp_code as code, full_name as name, status FROM staff_employees WHERE emp_code = 'ViewTEST'
UNION ALL
SELECT 'MNR', id, name, account_status FROM "user" WHERE id = 'MNRTEST001'
UNION ALL
SELECT 'PARTNER', partner_code, partner_name, login_status FROM official_partners WHERE partner_code LIKE 'VENDTEST%';
