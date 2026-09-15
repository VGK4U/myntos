-- ============================================================
-- Migration: Add GUC (Ganesh Utsav Committee) Registration Fields
-- Date: 2026-09-15
-- Target Table: community_registrations
-- Description:
-- Adds all fields required to digitally replicate the physical
-- Ganesh Utsav Committee application form (media_1789476344085.png)
-- including office bearers, idol location details, dates, visarjan,
-- mandap volunteers, cultural programs, sound system, signature,
-- coordinates, and Assembly Constituency with default 'Pendurthi'.
-- ============================================================

ALTER TABLE community_registrations
    ADD COLUMN IF NOT EXISTS application_no VARCHAR(100),
    ADD COLUMN IF NOT EXISTS assembly_constituency VARCHAR(100) DEFAULT 'Pendurthi',
    ADD COLUMN IF NOT EXISTS president_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS president_phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS secretary_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS secretary_phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS treasurer_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS treasurer_phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS mandap_location TEXT,
    ADD COLUMN IF NOT EXISTS location_category VARCHAR(50),
    ADD COLUMN IF NOT EXISTS location_owner_details TEXT,
    ADD COLUMN IF NOT EXISTS idol_height VARCHAR(50),
    ADD COLUMN IF NOT EXISTS utsav_start_date DATE,
    ADD COLUMN IF NOT EXISTS utsav_end_date DATE,
    ADD COLUMN IF NOT EXISTS visarjan_date DATE,
    ADD COLUMN IF NOT EXISTS visarjan_time VARCHAR(50),
    ADD COLUMN IF NOT EXISTS visarjan_phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS mandap_volunteers JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS cultural_programs JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS sound_system_details TEXT,
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS formatted_address TEXT,
    ADD COLUMN IF NOT EXISTS applicant_signature TEXT,
    ADD COLUMN IF NOT EXISTS registered_from VARCHAR(100) DEFAULT 'Community Service',
    ADD COLUMN IF NOT EXISTS landmark VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_comm_reg_registered_from ON community_registrations(registered_from);

-- Set default for existing records where assembly_constituency is NULL
UPDATE community_registrations
SET assembly_constituency = 'Pendurthi'
WHERE assembly_constituency IS NULL;
