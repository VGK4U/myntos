-- =============================================================================
-- Migration: update_vgk4u_career_catalog_alignment_20261020.sql
-- Date: 2026-10-20
-- Scope: Align Career Designations & Personal Production configs with Official Catalog (Option A)
--
-- Rules:
-- Track 1 (Personal Direct Sales):
--   Channel Partner (1-4 files): 5.00%
--   Senior (5-9 files): 6.50%
--   Extended (10-15 files): 7.50%
--   Core (16+ files): 8.00%
--
-- Track 2 (Leadership Overrides):
--   Channel Partner: 0 legs, 0.00% overrides
--   Senior: 1 active direct member (>=3 files), +0.50% overrides
--   Extended: 5 active direct members (>=3 files), +1.00% overrides (cum +1.50%)
--   Core: 10 active direct members (>=3 files), +1.50% overrides (cum +3.00%)
-- =============================================================================

BEGIN;

UPDATE vgk4u_career_designation_configs
SET required_own_qualifying_files = CASE hierarchy_order
        WHEN 0 THEN 0
        WHEN 1 THEN 1
        WHEN 2 THEN 5
        WHEN 3 THEN 10
        WHEN 4 THEN 16
        ELSE 0
    END,
    stage_own_qualifying_files = CASE hierarchy_order
        WHEN 0 THEN 0
        WHEN 1 THEN 1
        WHEN 2 THEN 4
        WHEN 3 THEN 5
        WHEN 4 THEN 6
        ELSE 0
    END,
    required_active_team_members = CASE hierarchy_order
        WHEN 0 THEN 0
        WHEN 1 THEN 0
        WHEN 2 THEN 1
        WHEN 3 THEN 5
        WHEN 4 THEN 10
        ELSE 0
    END,
    self_earning_pct = CASE hierarchy_order
        WHEN 0 THEN 0.00
        WHEN 1 THEN 5.00
        WHEN 2 THEN 6.50
        WHEN 3 THEN 7.50
        WHEN 4 THEN 8.00
        ELSE 0.00
    END,
    team_differential_pct = CASE hierarchy_order
        WHEN 0 THEN 0.00
        WHEN 1 THEN 0.00
        WHEN 2 THEN 0.50
        WHEN 3 THEN 1.00
        WHEN 4 THEN 1.50
        ELSE 0.00
    END,
    updated_at = NOW()
WHERE hierarchy_order IN (0, 1, 2, 3, 4);

DELETE FROM vgk4u_personal_prod_configs;
INSERT INTO vgk4u_personal_prod_configs (tier_code, tier_name, min_qualifying_files, commission_rate_pct, is_active)
VALUES
    ('CHANNEL_PARTNER', 'Tier 1 Channel Partner', 1, 5.00, TRUE),
    ('SENIOR', 'Tier 2 Senior', 5, 6.50, TRUE),
    ('EXTENDED', 'Tier 3 Extended', 10, 7.50, TRUE),
    ('CORE', 'Tier 4 Core', 16, 8.00, TRUE);

COMMIT;
