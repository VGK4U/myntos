-- Migration: Add vendor-specific fields to official_partners table
-- DC_PARTNER_002: Unified Business Partner Management
-- Created: Dec 09, 2025

-- Add new columns for vendor-specific fields
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS partner_type VARCHAR(20) DEFAULT 'BOTH';
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS contact_person_1_name VARCHAR(200);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS contact_person_1_phone VARCHAR(20);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS contact_person_1_designation VARCHAR(100);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS contact_person_2_name VARCHAR(200);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS contact_person_2_phone VARCHAR(20);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS contact_person_2_designation VARCHAR(100);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS map_link_1 VARCHAR(500);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS map_link_1_label VARCHAR(100) DEFAULT 'Office';
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS map_link_2 VARCHAR(500);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS map_link_2_label VARCHAR(100) DEFAULT 'Warehouse';
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS payment_scanner_qr_url VARCHAR(500);
ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS legacy_vendor_id INTEGER;

-- Add index for legacy vendor lookup
CREATE INDEX IF NOT EXISTS idx_partner_legacy_vendor ON official_partners(legacy_vendor_id) WHERE legacy_vendor_id IS NOT NULL;
