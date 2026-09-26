-- =============================================================================
-- MIGRATION: update_vgk4u_solar_commission_model_20260925.sql
-- Date: 2026-09-25
-- Scope: Finalize 9.00% Solar Network Model and Universal Stage 2 Advance Indexing
-- Invariants:
--   1. Total Network Pool: 9.00%
--      - Producer Base: 5.00%
--      - Direct Sponsor Override: 1.00%
--      - Senior Differential: 1.50%
--      - Extended Differential: 1.00%
--      - Core Differential: 0.50%
--   2. Operational Support (0.75% / 1.50%) & Showroom (3.50%) remain outside pool.
--   3. Unique index on vgk_solar_cibil_advances includes partner_id to support
--      multi-layer Stage 2 advances without collision.
-- Safety: ZERO mutations to historical financial records <= 2026-09-24.
-- =============================================================================

BEGIN;

-- 1. Update Solar category commission config to canonical 9.00% model
UPDATE vgk4u_category_commission_configs
SET max_network_pool_pct     = 9.00,
    producer_base_pct        = 5.00,
    sponsor_override_pct     = 1.00,
    manager_diff_pct         = 1.50,
    gm_diff_pct              = 1.00,
    rm_diff_pct              = 0.50,
    unallocated_balance_pct  = 0.00,
    updated_at               = CURRENT_TIMESTAMP
WHERE category_slug = 'solar';

-- 2. Upgrade unique index on vgk_solar_cibil_advances to include partner_id
DROP INDEX IF EXISTS uq_vsca_txn_level_kind;
CREATE UNIQUE INDEX IF NOT EXISTS uq_vsca_txn_partner_level_kind
ON vgk_solar_cibil_advances (source_transaction_id, partner_id, level, kind)
WHERE source_transaction_id IS NOT NULL AND status <> 'RECOVERED';

COMMIT;
