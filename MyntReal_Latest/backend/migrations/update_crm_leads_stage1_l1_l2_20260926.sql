-- ============================================================================
-- Migration: Add independent Stage 1 L1 & L2 tracking columns to crm_leads
-- Date: 2026-09-26
-- Description:
--   Supports dual-level Stage 1 advance recovery (L1 ₹1,000, L2 ₹500)
--   maintaining independent remaining balances per level.
-- ============================================================================

ALTER TABLE crm_leads
  ADD COLUMN IF NOT EXISTS remaining_stage1_advance_l1 NUMERIC(12,2) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS remaining_stage1_advance_l2 NUMERIC(12,2) DEFAULT NULL;

COMMENT ON COLUMN crm_leads.remaining_stage1_advance_l1 IS 'Remaining unadjusted Stage 1 advance balance for L1 Producer (starts at 1000.00)';
COMMENT ON COLUMN crm_leads.remaining_stage1_advance_l2 IS 'Remaining unadjusted Stage 1 advance balance for L2 Direct Sponsor (starts at 500.00)';
