-- DC_MIGRATION_001: Rollback Script for Vendor Master to Official Partners Migration
-- Date: 2025-12-09
-- Purpose: Rollback the vendor migration if issues are found
-- CAUTION: This will remove all migrated vendor data from official_partners

BEGIN;

-- Step 1: Remove company segment mappings for migrated vendors
DELETE FROM partner_company_segments 
WHERE partner_id IN (
    SELECT id FROM official_partners WHERE legacy_vendor_id IS NOT NULL
);

-- Step 2: Remove partners that were newly inserted (have legacy_vendor_id set)
-- This preserves partners that existed before migration
DELETE FROM official_partners 
WHERE legacy_vendor_id IS NOT NULL;

-- Step 3: Reset legacy_vendor_id for any that were just updated (if any remain)
UPDATE official_partners 
SET legacy_vendor_id = NULL 
WHERE legacy_vendor_id IS NOT NULL;

-- Verification
SELECT 'Rollback Complete' AS status, 
       (SELECT COUNT(*) FROM official_partners WHERE legacy_vendor_id IS NOT NULL) AS remaining_migrated_partners;

COMMIT;
