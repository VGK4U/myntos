-- Migration: Add Partner Login System columns to official_partners table
-- Date: 2025-12-11
-- Description: Adds authentication columns required for Partner Login System

-- Add partner authentication columns
ALTER TABLE official_partners 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256),
ADD COLUMN IF NOT EXISTS login_status VARCHAR(20) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;

-- Create index for login status lookups
CREATE INDEX IF NOT EXISTS idx_partner_login_status ON official_partners(login_status);

-- Add comment for documentation
COMMENT ON COLUMN official_partners.password_hash IS 'Hashed password for partner login authentication';
COMMENT ON COLUMN official_partners.login_status IS 'Partner login status: active, suspended, locked';
COMMENT ON COLUMN official_partners.last_login IS 'Timestamp of last successful login';
COMMENT ON COLUMN official_partners.failed_login_attempts IS 'Count of consecutive failed login attempts';
COMMENT ON COLUMN official_partners.password_changed_at IS 'Timestamp when password was last changed';
