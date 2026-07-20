-- [DC-BANK-DETAILS-001] Apr 2026: Bank details approval flow for VGK members
-- Adds bank_details_status and bank_rejection_reason to official_partners
-- Safe: all columns are nullable / have defaults; zero impact on existing rows.

ALTER TABLE official_partners
  ADD COLUMN IF NOT EXISTS bank_details_status VARCHAR(30) NOT NULL DEFAULT 'Not Submitted',
  ADD COLUMN IF NOT EXISTS bank_rejection_reason TEXT;
