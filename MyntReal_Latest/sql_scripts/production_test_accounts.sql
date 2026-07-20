-- ============================================================================
-- MNR REFERENCE PROGRAM - PRODUCTION TEST ACCOUNTS
-- DC Protocol Compliant | VIEW-ONLY Access | 24-Hour Time-Limited
-- Generated: December 20, 2025 (CORRECTED VERSION)
-- ============================================================================
-- IMPORTANT: Run the DELETE section first if re-running this script
-- ============================================================================

-- ============================================================================
-- SECTION 0: CLEANUP (Run this first if re-running)
-- ============================================================================
-- DELETE FROM staff_employees WHERE emp_code = 'ViewTEST';
-- DELETE FROM "user" WHERE id = 'MNRTEST001';
-- DELETE FROM official_partners WHERE partner_code LIKE 'VENDTEST%';

-- ============================================================================
-- SECTION 1: STAFF TEST ACCOUNT (ViewTEST)
-- ============================================================================
-- Employee ID: ViewTEST
-- Password: CKd65kcemtw3
-- Access: VGK4U Supreme, All Companies, VIEW ONLY

INSERT INTO staff_employees (
    emp_code,
    full_name,
    first_name,
    last_name,
    email,
    phone,
    department_id,
    designation,
    role_id,
    status,
    staff_type,
    date_of_joining,
    password_hash,
    is_deleted,
    requires_password_change,
    kyc_status,
    base_company_id,
    data_companies,
    created_at,
    updated_at
) VALUES (
    'ViewTEST',
    'Test User (VIEW ONLY)',
    'Test',
    'User',
    'viewtest@myntreal.com',
    '9999999901',
    1,
    'Test Account - VIEW ONLY',
    1,
    'active',
    'VGK4U',
    CURRENT_DATE,
    'scrypt:32768:8:1$Py5NMWXy9Wh0EhHU$407a11417df3f4718c1b2d62f6f2fcf52258a7dfd227d5ff55ead4b6ab34718af6b365719b6a21d158bc6a731367b60d2bd7bdbb028b6927a7ec261929e282a0',
    false,
    false,
    'approved',
    16,
    '[16, 17, 20, 21, 22, 31]'::jsonb,
    NOW(),
    NOW()
);

-- ============================================================================
-- SECTION 2: MNR USER TEST ACCOUNT (MNRTEST001)
-- ============================================================================
-- MNR ID: MNRTEST001
-- Password: T6jZH82tVPw0
-- Access: Regular MNR User, VIEW ONLY

INSERT INTO "user" (
    id,
    bev_legacy_id,
    name,
    email,
    password,
    user_type,
    wallet_balance,
    upgrade_wallet_balance,
    kyc_status,
    coupon_status,
    placement_status,
    is_ved,
    ved_paused,
    account_status,
    registration_date,
    referral_bonus_eligible,
    first_referral_bonus_paid,
    first_matching_achieved,
    excluded_from_regular_awards,
    profile_completion_score,
    earned_total,
    released_total,
    phone_number
) VALUES (
    'MNRTEST001',
    'MNRTEST001',
    'Test MNR User (VIEW ONLY)',
    'mnrtest@myntreal.com',
    'scrypt:32768:8:1$Yc2XnCSPzyb6yCYO$e5ad61ce0ca902252588ea84e34e06bfe1be6cae6191685824b9d066a446dc2f501aad01b0178927a31fb0bbbcd62b151abc0f2392c883aa30fca9ea0e6dcd61',
    'USER',
    0.0,
    0.0,
    'APPROVED',
    'PENDING',
    'Approved',
    false,
    false,
    'Active',
    NOW(),
    false,
    false,
    false,
    false,
    0,
    0.0,
    0.0,
    '9999999902'
);

-- ============================================================================
-- SECTION 3: PARTNER TEST ACCOUNTS (All Categories)
-- ============================================================================

-- 3.1 DEALER - Partner Code: VENDTEST_DEALER, Password: xQmz8wLLl@FC
INSERT INTO official_partners (
    partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at
) VALUES (
    'VENDTEST_DEALER', 'Test Dealer (VIEW ONLY)', 'DEALER', 'DEALER', 'Test Contact', '9999999903', 'testdealer@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$6jGjfsnipLbEpN6R$799127e54b00b6918ec21c49a9b4d789d635d49ecfe9bf926edbe7a51b8cc2771fba09911bcba7e6aa7700fd2b2b87ac72c8df505659a05005cf02f744a27a10', NOW(), NOW()
);

-- 3.2 DISTRIBUTOR - Partner Code: VENDTEST_DIST, Password: UyOZC8j13FIb
INSERT INTO official_partners (
    partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at
) VALUES (
    'VENDTEST_DIST', 'Test Distributor (VIEW ONLY)', 'DISTRIBUTOR', 'DISTRIBUTOR', 'Test Contact', '9999999904', 'testdistributor@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$VnQWsdMUh2X1KZNI$42c646239da02d3a73276b3e162cb7d090f173a4b9b6620f2f42372c9a74d9fa40d897b75bd65ce4bffcb1f92814703776af8405878da23a8a1ae3976dd12841', NOW(), NOW()
);

-- 3.3 VENDOR - Partner Code: VENDTEST_VENDOR, Password: OOrTgmzjNJJr
INSERT INTO official_partners (
    partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at
) VALUES (
    'VENDTEST_VENDOR', 'Test Vendor (VIEW ONLY)', 'VENDOR', 'VENDOR', 'Test Contact', '9999999905', 'testvendor@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$AbSWPsUzHgwfAaOM$1f5b4e000c20ed336765b132803c906f66ce64bdd43c35eb1b7ef28a752b26412ee1816c0a8f99d1433f2b96bd7703cd5bef0f49dc6c66fd9d81c6f8fc708fd9', NOW(), NOW()
);

-- 3.4 REAL DREAM PARTNER - Partner Code: VENDTEST_RD, Password: sHnaYHv!RDtM
INSERT INTO official_partners (
    partner_code, partner_name, category, partner_type, contact_person, phone, email, city, state, is_active, login_status, password_hash, created_at, updated_at
) VALUES (
    'VENDTEST_RD', 'Test Real Dream Partner (VIEW ONLY)', 'REAL_DREAM_PARTNER', 'REAL_DREAM_PARTNER', 'Test Contact', '9999999906', 'testrealdream@myntreal.com', 'Test City', 'Test State', true, 'ACTIVE', 'scrypt:32768:8:1$96XfvTheaZYPi8ab$38b52e1d5c00c9a455cf9d4f8f06429456a6bf21e0382a56750debfe3c2e22f8eeb04894c1c0d0b25d46b5248ac483bad6a02917d7b50d83bc43b8d03eab1788', NOW(), NOW()
);

-- ============================================================================
-- SECTION 4: CREATE VIEW-ONLY MENU SETTINGS FOR STAFF
-- ============================================================================

DO $$
DECLARE
    v_employee_id INTEGER;
    v_menu RECORD;
    v_company_id INTEGER;
    v_company_ids INTEGER[] := ARRAY[16, 17, 20, 21, 22, 31];
BEGIN
    SELECT id INTO v_employee_id FROM staff_employees WHERE emp_code = 'ViewTEST';
    
    IF v_employee_id IS NOT NULL THEN
        FOREACH v_company_id IN ARRAY v_company_ids LOOP
            FOR v_menu IN SELECT id FROM staff_menu_master WHERE is_active = true LOOP
                INSERT INTO staff_employee_menu_settings (
                    employee_id, menu_id, company_id, can_view, can_edit, created_at, updated_at
                ) VALUES (
                    v_employee_id, v_menu.id, v_company_id, true, false, NOW(), NOW()
                )
                ON CONFLICT (employee_id, menu_id, company_id) DO UPDATE SET
                    can_view = true, can_edit = false, updated_at = NOW();
            END LOOP;
        END LOOP;
        RAISE NOTICE 'Created VIEW-ONLY menu settings for ViewTEST (ID: %)', v_employee_id;
    END IF;
END $$;

-- ============================================================================
-- SECTION 5: CREATE VIEW-ONLY MENU SETTINGS FOR PARTNERS
-- ============================================================================

DO $$
DECLARE
    v_partner RECORD;
    v_menu RECORD;
    v_company_id INTEGER := 16;
BEGIN
    FOR v_partner IN SELECT id, partner_code FROM official_partners WHERE partner_code LIKE 'VENDTEST%' LOOP
        FOR v_menu IN SELECT id FROM staff_menu_master WHERE is_active = true AND target_audience IN ('partner', 'all') LOOP
            INSERT INTO partner_menu_settings (
                partner_id, menu_id, company_id, can_view, can_edit, created_at, updated_at
            ) VALUES (
                v_partner.id, v_menu.id, v_company_id, true, false, NOW(), NOW()
            )
            ON CONFLICT (partner_id, menu_id, company_id) DO UPDATE SET
                can_view = true, can_edit = false, updated_at = NOW();
        END LOOP;
        RAISE NOTICE 'Created VIEW-ONLY menu settings for partner: %', v_partner.partner_code;
    END LOOP;
END $$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

SELECT 'STAFF' as type, emp_code, full_name, status, staff_type 
FROM staff_employees WHERE emp_code = 'ViewTEST';

SELECT 'MNR' as type, id, name, account_status 
FROM "user" WHERE id = 'MNRTEST001';

SELECT 'PARTNER' as type, partner_code, partner_name, category, is_active, login_status 
FROM official_partners WHERE partner_code LIKE 'VENDTEST%';

-- ============================================================================
-- END OF CREATION SCRIPT
-- ============================================================================
