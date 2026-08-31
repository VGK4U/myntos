-- ==============================================================================
-- Migration: Create VoIP Call Sessions Table for In-App PSTN Calling & Recordings
-- DC Protocol: multi-company segregation with company_id, unique session constraints,
-- and indexes on operator_id, lead_id, customer phones, and status.
-- Date: Aug 2026
-- ==============================================================================

CREATE TABLE IF NOT EXISTS voip_call_sessions (
    id SERIAL PRIMARY KEY,
    call_session_id VARCHAR(64) NOT NULL,
    company_id INTEGER NOT NULL,
    branch_id INTEGER,
    lead_id INTEGER,
    operator_id INTEGER,
    operator_user_ref VARCHAR(50),
    operator_name VARCHAR(200),
    customer_phone VARCHAR(30) NOT NULL,
    direction VARCHAR(20) NOT NULL DEFAULT 'outbound',
    call_method VARCHAR(30) NOT NULL DEFAULT 'in_app_pstn',
    provider VARCHAR(50) NOT NULL DEFAULT 'mock',
    provider_call_id VARCHAR(128),
    caller_id VARCHAR(30) NOT NULL,
    destination_number VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'created',
    started_at TIMESTAMP WITHOUT TIME ZONE,
    dialing_at TIMESTAMP WITHOUT TIME ZONE,
    ringing_at TIMESTAMP WITHOUT TIME ZONE,
    answered_at TIMESTAMP WITHOUT TIME ZONE,
    ended_at TIMESTAMP WITHOUT TIME ZONE,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    termination_reason VARCHAR(100),
    failure_reason VARCHAR(255),
    recording_status VARCHAR(30) NOT NULL DEFAULT 'not_started',
    recording_id INTEGER,
    recording_storage_key VARCHAR(512),
    recording_mime_type VARCHAR(50),
    recording_file_size BIGINT,
    recording_duration_seconds INTEGER,
    recording_checksum VARCHAR(64),
    operator_call_id INTEGER,
    client_token TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_vcs_session_id UNIQUE (call_session_id)
);

CREATE INDEX IF NOT EXISTS ix_vcs_session_id ON voip_call_sessions(call_session_id);
CREATE INDEX IF NOT EXISTS ix_vcs_company_status ON voip_call_sessions(company_id, status);
CREATE INDEX IF NOT EXISTS ix_vcs_operator_company ON voip_call_sessions(operator_id, company_id);
CREATE INDEX IF NOT EXISTS ix_vcs_lead_company ON voip_call_sessions(lead_id, company_id);
CREATE INDEX IF NOT EXISTS ix_vcs_provider_call_id ON voip_call_sessions(provider, provider_call_id);
CREATE INDEX IF NOT EXISTS ix_vcs_customer_phone ON voip_call_sessions(customer_phone);
CREATE INDEX IF NOT EXISTS ix_vcs_created_at ON voip_call_sessions(created_at);
