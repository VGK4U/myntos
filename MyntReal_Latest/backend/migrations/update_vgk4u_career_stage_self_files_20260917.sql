-- Migration: update_vgk4u_career_stage_self_files_20260917.sql
-- Date: 2026-09-17
-- Scope: Add stage_own_qualifying_files column and populate stage-wise and cumulative personal qualifying files.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'vgk4u_career_designation_configs' 
          AND column_name = 'stage_own_qualifying_files'
    ) THEN
        ALTER TABLE vgk4u_career_designation_configs
        ADD COLUMN stage_own_qualifying_files INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

-- Update exact stage-wise incremental and cumulative personal qualifying files
UPDATE vgk4u_career_designation_configs
SET stage_own_qualifying_files = CASE hierarchy_order
        WHEN 0 THEN 0
        WHEN 1 THEN 1
        WHEN 2 THEN 3
        WHEN 3 THEN 5
        WHEN 4 THEN 7
        ELSE 0
    END,
    required_own_qualifying_files = CASE hierarchy_order
        WHEN 0 THEN 0
        WHEN 1 THEN 1
        WHEN 2 THEN 4
        WHEN 3 THEN 9
        WHEN 4 THEN 16
        ELSE 0
    END,
    updated_at = NOW()
WHERE hierarchy_order IN (0, 1, 2, 3, 4);
