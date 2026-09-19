-- Rollback Migration: rollback_mobile_device_sessions_20260919.sql
-- Purpose: Drop mobile_device_sessions table safely
-- Created: Sep 19, 2026

DROP TABLE IF EXISTS mobile_device_sessions CASCADE;
