-- =============================================================================
-- MIGRATION: update_vgk4u_universal_9pct_all_categories_20260925.sql
-- Date: 2026-09-25
-- Scope: Universal 9.00% Network Commission Architecture across ALL categories
-- Invariants:
--   1. Common 9.00% Network Distribution Structure:
--      - L1 Producer: 5.00%
--      - L2 Direct Sponsor Override: 1.00%
--      - L3 Senior Differential: 1.50%
--      - L4 Extended Differential: 1.00%
--      - L5 Core Differential: 0.50%
--   2. Distinct Earning Basis:
--      - Model A (MRP/Sale Value): Solar, EV, EV Spares, Training -> PAYMENT_RECEIVED
--      - Model B (Commission Receipt): Insurance, Real Dreams -> COMMISSION_RECEIVED
--   3. Audit ledger columns for earning basis type and amounts.
-- Safety: ZERO mutations to historical financial records <= 2026-09-24.
-- =============================================================================

BEGIN;

-- 1. Add earning_basis_type to category commission configs
ALTER TABLE vgk4u_category_commission_configs
ADD COLUMN IF NOT EXISTS earning_basis_type VARCHAR(50) NOT NULL DEFAULT 'PAYMENT_RECEIVED';

-- 2. Update all categories to universal 9.00% network commission model
UPDATE vgk4u_category_commission_configs
SET max_network_pool_pct     = 9.00,
    producer_base_pct        = 5.00,
    sponsor_override_pct     = 1.00,
    manager_diff_pct         = 1.50,
    gm_diff_pct              = 1.00,
    rm_diff_pct              = 0.50,
    unallocated_balance_pct  = 0.00,
    updated_at               = CURRENT_TIMESTAMP;

-- 3. Set earning basis types according to revenue realization model
UPDATE vgk4u_category_commission_configs
SET earning_basis_type = 'PAYMENT_RECEIVED'
WHERE category_slug IN ('solar', 'ev', 'etc-training', 'ev-spares');

UPDATE vgk4u_category_commission_configs
SET earning_basis_type = 'COMMISSION_RECEIVED'
WHERE category_slug IN ('insurance', 'real-dreams');

-- 4. Ensure EV Spares category row exists with 9% universal structure
INSERT INTO vgk4u_category_commission_configs 
    (version_label, effective_from, category_slug, category_name, max_network_pool_pct, producer_base_pct,
     sponsor_override_pct, manager_diff_pct, gm_diff_pct, rm_diff_pct,
     support_journey_pct, support_end_to_end_pct, showroom_pct,
     unallocated_balance_pct, admin_charge_pct, tds_pct, is_active, earning_basis_type)
SELECT 'v2_sep2026', '2026-09-25 00:00:00', 'ev-spares', 'EV Spares & Components', 9.00, 5.00,
       1.00, 1.50, 1.00, 0.50,
       0.00, 0.00, 0.00,
       0.00, 8.00, 2.00, true, 'PAYMENT_RECEIVED'
WHERE NOT EXISTS (
    SELECT 1 FROM vgk4u_category_commission_configs WHERE category_slug = 'ev-spares'
);

-- 5. Add ledger auditability columns for earning basis tracking
ALTER TABLE vgk_cash_income_entries
ADD COLUMN IF NOT EXISTS earning_basis_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS earning_basis_amount NUMERIC(15, 2);

ALTER TABLE vgk_solar_cibil_advances
ADD COLUMN IF NOT EXISTS earning_basis_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS earning_basis_amount NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS underlying_value NUMERIC(15, 2);

COMMIT;
