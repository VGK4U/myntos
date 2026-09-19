-- Migration: create_mobile_device_sessions_20260919.sql
-- Purpose: Rotating refresh tokens and persistent device session tracking for MyntOS mobile staff
-- Created: Sep 19, 2026

CREATE TABLE IF NOT EXISTS mobile_device_sessions (
    id SERIAL PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
    device_name VARCHAR(100),
    app_version VARCHAR(30),
    token_version INTEGER NOT NULL DEFAULT 1,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_mds_staff_id ON mobile_device_sessions(staff_id);
CREATE INDEX IF NOT EXISTS ix_mds_device_id ON mobile_device_sessions(device_id);
CREATE INDEX IF NOT EXISTS ix_mds_token_hash ON mobile_device_sessions(refresh_token_hash);
CREATE INDEX IF NOT EXISTS ix_mds_active ON mobile_device_sessions(staff_id, is_revoked, expires_at);
