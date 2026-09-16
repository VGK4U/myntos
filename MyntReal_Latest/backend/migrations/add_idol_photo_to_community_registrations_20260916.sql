-- ============================================================
-- Migration: Add idol_photo to community_registrations
-- Date: 2026-09-16
-- Target Table: community_registrations
-- Description:
-- Adds optional idol_photo column for Ganesh idol photo upload
-- in Section C (Ganesh Idol Location Details).
-- ============================================================

ALTER TABLE community_registrations
    ADD COLUMN IF NOT EXISTS idol_photo TEXT;
