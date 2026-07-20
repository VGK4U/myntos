-- DC_MIGRATION_001: Vendor Master to Official Partners Migration
-- Date: 2025-12-09
-- Purpose: Migrate vendor_master records to unified official_partners table
-- Rollback: Run rollback_vendors_migration.sql

-- Start transaction for atomic execution
BEGIN;

-- Step 1: Create temporary table to track migrations
CREATE TEMP TABLE vendor_migration_log (
    vendor_id INTEGER PRIMARY KEY,
    partner_id INTEGER,
    action VARCHAR(10), -- 'INSERT' or 'UPDATE'
    migrated_at TIMESTAMP DEFAULT NOW()
);

-- Step 2: Update existing partners where partner_code matches vendor_code
-- This handles VND001, VND002 which already exist
UPDATE official_partners op
SET 
    partner_name = vm.vendor_name,
    partner_type = vm.vendor_type,
    contact_person = vm.contact_person,
    phone = vm.phone,
    email = vm.email,
    gst_number = vm.gst_number,
    pan_number = vm.pan_number,
    address = vm.address,
    city = vm.city,
    state = vm.state,
    pincode = vm.pincode,
    bank_name = vm.bank_name,
    bank_branch = vm.bank_branch,
    account_number = vm.account_number,
    ifsc_code = vm.ifsc_code,
    payment_terms = vm.payment_terms,
    credit_limit = vm.credit_limit,
    credit_days = vm.credit_days,
    is_active = vm.is_active,
    contact_person_1_name = vm.contact_person_1_name,
    contact_person_1_phone = vm.contact_person_1_phone,
    contact_person_1_designation = vm.contact_person_1_designation,
    contact_person_2_name = vm.contact_person_2_name,
    contact_person_2_phone = vm.contact_person_2_phone,
    contact_person_2_designation = vm.contact_person_2_designation,
    map_link_1 = vm.map_link_1,
    map_link_1_label = vm.map_link_1_label,
    map_link_2 = vm.map_link_2,
    map_link_2_label = vm.map_link_2_label,
    payment_scanner_qr_url = vm.payment_scanner_path,
    legacy_vendor_id = vm.id,
    updated_at = NOW()
FROM vendor_master vm
WHERE op.partner_code = vm.vendor_code
  AND op.category = 'VENDOR';

-- Log updated records
INSERT INTO vendor_migration_log (vendor_id, partner_id, action)
SELECT vm.id, op.id, 'UPDATE'
FROM vendor_master vm
JOIN official_partners op ON op.partner_code = vm.vendor_code AND op.category = 'VENDOR';

-- Step 3: Insert new vendors that don't have matching partner_code
INSERT INTO official_partners (
    partner_code, partner_name, category, partner_type,
    contact_person, phone, email,
    gst_number, pan_number,
    address, city, state, pincode,
    bank_name, bank_branch, account_number, ifsc_code,
    payment_terms, credit_limit, credit_days,
    is_active,
    contact_person_1_name, contact_person_1_phone, contact_person_1_designation,
    contact_person_2_name, contact_person_2_phone, contact_person_2_designation,
    map_link_1, map_link_1_label, map_link_2, map_link_2_label,
    payment_scanner_qr_url, legacy_vendor_id,
    created_by_id, created_at, updated_at
)
SELECT 
    vm.vendor_code,
    vm.vendor_name,
    'VENDOR',
    vm.vendor_type,
    vm.contact_person,
    vm.phone,
    vm.email,
    vm.gst_number,
    vm.pan_number,
    vm.address,
    vm.city,
    vm.state,
    vm.pincode,
    vm.bank_name,
    vm.bank_branch,
    vm.account_number,
    vm.ifsc_code,
    vm.payment_terms,
    vm.credit_limit,
    vm.credit_days,
    vm.is_active,
    vm.contact_person_1_name,
    vm.contact_person_1_phone,
    vm.contact_person_1_designation,
    vm.contact_person_2_name,
    vm.contact_person_2_phone,
    vm.contact_person_2_designation,
    vm.map_link_1,
    vm.map_link_1_label,
    vm.map_link_2,
    vm.map_link_2_label,
    vm.payment_scanner_path,
    vm.id,
    vm.created_by_id,
    vm.created_at,
    NOW()
FROM vendor_master vm
WHERE NOT EXISTS (
    SELECT 1 FROM official_partners op 
    WHERE op.partner_code = vm.vendor_code AND op.category = 'VENDOR'
);

-- Log inserted records
INSERT INTO vendor_migration_log (vendor_id, partner_id, action)
SELECT vm.id, op.id, 'INSERT'
FROM vendor_master vm
JOIN official_partners op ON op.legacy_vendor_id = vm.id
WHERE NOT EXISTS (
    SELECT 1 FROM vendor_migration_log vml WHERE vml.vendor_id = vm.id
);

-- Step 4: Create company segment mappings from applicable_companies JSONB
-- Handle both numeric IDs and "ALL" string values
-- DC Protocol: Each partner must be associated with specific companies

-- For vendors with specific company IDs (not "ALL")
INSERT INTO partner_company_segments (partner_id, company_id, segment_id, is_primary, is_active, created_at)
SELECT DISTINCT
    op.id,
    (company_id_elem::text)::integer,
    NULL,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY op.id ORDER BY (company_id_elem::text)::integer) = 1 THEN TRUE ELSE FALSE END,
    TRUE,
    NOW()
FROM vendor_master vm
JOIN official_partners op ON op.legacy_vendor_id = vm.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN vm.applicable_companies IS NULL THEN '[]'::jsonb
        ELSE vm.applicable_companies
    END
) AS company_id_elem
WHERE company_id_elem::text != '"ALL"'
  AND company_id_elem::text ~ '^\d+$'
  AND EXISTS (SELECT 1 FROM associated_companies ac WHERE ac.id = (company_id_elem::text)::integer)
  AND NOT EXISTS (
      SELECT 1 FROM partner_company_segments pcs 
      WHERE pcs.partner_id = op.id AND pcs.company_id = (company_id_elem::text)::integer
  );

-- For vendors with "ALL" - associate with all active companies
INSERT INTO partner_company_segments (partner_id, company_id, segment_id, is_primary, is_active, created_at)
SELECT DISTINCT
    op.id,
    ac.id,
    NULL,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY op.id ORDER BY ac.id) = 1 THEN TRUE ELSE FALSE END,
    TRUE,
    NOW()
FROM vendor_master vm
JOIN official_partners op ON op.legacy_vendor_id = vm.id
CROSS JOIN associated_companies ac
WHERE vm.applicable_companies::text LIKE '%"ALL"%'
  AND ac.is_active = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM partner_company_segments pcs 
      WHERE pcs.partner_id = op.id AND pcs.company_id = ac.id
  );

-- Step 5: Verification queries (output for validation)
-- Count of migrated records
SELECT 'Migration Summary' AS report, COUNT(*) AS total_vendors_migrated FROM vendor_migration_log;
SELECT action, COUNT(*) AS count FROM vendor_migration_log GROUP BY action;

-- Verify all vendors have matching partners
SELECT 'Verification: Unmatched vendors' AS report, vm.id, vm.vendor_code 
FROM vendor_master vm 
WHERE NOT EXISTS (SELECT 1 FROM official_partners op WHERE op.legacy_vendor_id = vm.id);

-- Verify company segment mappings
SELECT 'Company Segments Created' AS report, COUNT(*) AS total_segments 
FROM partner_company_segments pcs 
JOIN official_partners op ON pcs.partner_id = op.id 
WHERE op.legacy_vendor_id IS NOT NULL;

COMMIT;

-- End of migration script
