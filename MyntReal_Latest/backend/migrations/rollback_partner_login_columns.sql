-- Rollback Migration: Remove Partner Login System columns from official_partners table
-- Date: 2025-12-11
-- Description: Removes authentication columns (use only if rollback is required)

-- Drop index first
DROP INDEX IF EXISTS idx_partner_login_status;

-- Remove columns
ALTER TABLE official_partners 
DROP COLUMN IF EXISTS password_hash,
DROP COLUMN IF EXISTS login_status,
DROP COLUMN IF EXISTS last_login,
DROP COLUMN IF EXISTS failed_login_attempts,
DROP COLUMN IF EXISTS password_changed_at;
