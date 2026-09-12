-- =============================================================================
-- MIGRATION: add_vgk4u_sponsor_override_column_20260912.sql
-- Date: 2026-09-12
-- Scope: Add sponsor_override_pct to vgk4u_category_commission_configs
-- Approved Business Decision: Direct Sponsor Override = 1.00% for Solar
-- Safety: ZERO mutations to historical financial records
-- =============================================================================

BEGIN;

ALTER TABLE vgk4u_category_commission_configs 
ADD COLUMN IF NOT EXISTS sponsor_override_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00;

-- Update Solar category to 1.00% Direct Sponsor Override
UPDATE vgk4u_category_commission_configs
SET sponsor_override_pct = 1.00,
    updated_at = CURRENT_TIMESTAMP
WHERE category_slug = 'solar';

COMMIT;
