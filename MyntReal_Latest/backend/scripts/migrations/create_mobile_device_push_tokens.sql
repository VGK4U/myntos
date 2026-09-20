-- Migration: Create mobile_device_push_tokens table
-- Tracks FCM data tokens (Android) and Apple PushKit VoIP tokens (iOS) for incoming call wake-up
-- Created: Sep 2026

CREATE TABLE IF NOT EXISTS mobile_device_push_tokens (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES associated_companies(id) ON DELETE CASCADE,
    staff_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    push_token TEXT NOT NULL,
    token_type VARCHAR(30) NOT NULL DEFAULT 'fcm_data',
    app_version VARCHAR(30),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_staff_device_token_type UNIQUE (staff_id, device_id, token_type)
);

CREATE INDEX IF NOT EXISTS ix_mdpt_staff_active ON mobile_device_push_tokens(staff_id, is_active);
CREATE INDEX IF NOT EXISTS ix_mdpt_company_staff ON mobile_device_push_tokens(company_id, staff_id);
