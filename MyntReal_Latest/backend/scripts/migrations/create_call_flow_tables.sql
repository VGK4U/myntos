-- ========================================================================
-- Migration: Create MyntOS Telephony Call Flow & Routing Engine Tables
-- Normalized schema for Call Flows, Versions, Nodes, Edges, Ring Groups,
-- Business Hours Schedules, Holidays, Plivo Endpoints, and Execution Logs.
-- Created: Sep 2026
-- ========================================================================

-- 1. Call Flows Master Table
CREATE TABLE IF NOT EXISTS telephony_call_flows (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    did_number VARCHAR(50),
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    current_published_version_id INTEGER,
    created_by_staff_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

CREATE INDEX IF NOT EXISTS ix_tcf_company_status ON telephony_call_flows(company_id, status);
CREATE INDEX IF NOT EXISTS ix_tcf_did_number ON telephony_call_flows(did_number);

-- 2. Call Flow Versions Table
CREATE TABLE IF NOT EXISTS telephony_call_flow_versions (
    id SERIAL PRIMARY KEY,
    flow_id INTEGER NOT NULL REFERENCES telephony_call_flows(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    flow_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_at TIMESTAMP WITHOUT TIME ZONE,
    published_by_staff_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_tcf_version_num UNIQUE (flow_id, version_number)
);

CREATE INDEX IF NOT EXISTS ix_tcfv_flow_status ON telephony_call_flow_versions(flow_id, status);
CREATE INDEX IF NOT EXISTS ix_tcfv_company ON telephony_call_flow_versions(company_id);

-- 3. Flow Nodes Table
CREATE TABLE IF NOT EXISTS telephony_flow_nodes (
    id SERIAL PRIMARY KEY,
    flow_version_id INTEGER NOT NULL REFERENCES telephony_call_flow_versions(id) ON DELETE CASCADE,
    node_key VARCHAR(64) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    position_x INTEGER DEFAULT 100,
    position_y INTEGER DEFAULT 100,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

CREATE INDEX IF NOT EXISTS ix_tfn_version_key ON telephony_flow_nodes(flow_version_id, node_key);

-- 4. Flow Edges Table
CREATE TABLE IF NOT EXISTS telephony_flow_edges (
    id SERIAL PRIMARY KEY,
    flow_version_id INTEGER NOT NULL REFERENCES telephony_call_flow_versions(id) ON DELETE CASCADE,
    source_node_key VARCHAR(64) NOT NULL,
    target_node_key VARCHAR(64) NOT NULL,
    condition VARCHAR(100) NOT NULL DEFAULT 'always',
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

CREATE INDEX IF NOT EXISTS ix_tfe_version ON telephony_flow_edges(flow_version_id);

-- 5. Ring Groups Master Table
CREATE TABLE IF NOT EXISTS telephony_ring_groups (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    strategy VARCHAR(30) NOT NULL DEFAULT 'simultaneous',
    timeout_seconds INTEGER NOT NULL DEFAULT 25,
    fallback_action VARCHAR(50) NOT NULL DEFAULT 'voicemail',
    fallback_config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

CREATE INDEX IF NOT EXISTS ix_trg_company ON telephony_ring_groups(company_id);

-- 6. Ring Group Members Table
CREATE TABLE IF NOT EXISTS telephony_ring_group_members (
    id SERIAL PRIMARY KEY,
    ring_group_id INTEGER NOT NULL REFERENCES telephony_ring_groups(id) ON DELETE CASCADE,
    staff_id INTEGER NOT NULL,
    priority_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_trg_member UNIQUE (ring_group_id, staff_id)
);

CREATE INDEX IF NOT EXISTS ix_trgm_group ON telephony_ring_group_members(ring_group_id);
CREATE INDEX IF NOT EXISTS ix_trgm_staff ON telephony_ring_group_members(staff_id);

-- 7. Business Hours Schedules Table
CREATE TABLE IF NOT EXISTS telephony_business_hours (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT 'Standard Business Hours',
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    schedule_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

CREATE INDEX IF NOT EXISTS ix_tbh_company ON telephony_business_hours(company_id);

-- 8. Holidays Table
CREATE TABLE IF NOT EXISTS telephony_holidays (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    holiday_date VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_th_company_date UNIQUE (company_id, holiday_date)
);

CREATE INDEX IF NOT EXISTS ix_th_company_date ON telephony_holidays(company_id, holiday_date);

-- 9. Plivo SIP Endpoint Mappings Table
CREATE TABLE IF NOT EXISTS telephony_plivo_endpoints (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    plivo_endpoint_id VARCHAR(128),
    plivo_username VARCHAR(128) NOT NULL,
    plivo_alias VARCHAR(128),
    plivo_password_hash VARCHAR(255),
    is_registered BOOLEAN NOT NULL DEFAULT FALSE,
    last_registered_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_tpe_company_staff UNIQUE (company_id, staff_id)
);

CREATE INDEX IF NOT EXISTS ix_tpe_company_staff ON telephony_plivo_endpoints(company_id, staff_id);
CREATE INDEX IF NOT EXISTS ix_tpe_username ON telephony_plivo_endpoints(plivo_username);

-- 10. Flow Execution Logs Table
CREATE TABLE IF NOT EXISTS telephony_flow_execution_logs (
    id SERIAL PRIMARY KEY,
    call_session_id VARCHAR(64) NOT NULL,
    company_id INTEGER NOT NULL,
    flow_id INTEGER NOT NULL,
    flow_version_id INTEGER NOT NULL,
    caller_phone VARCHAR(30) NOT NULL,
    did_number VARCHAR(50),
    current_node_key VARCHAR(64) NOT NULL,
    traversed_nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    collected_digits VARCHAR(20),
    selected_destination VARCHAR(150),
    connected_staff_id INTEGER,
    final_outcome VARCHAR(50),
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

CREATE INDEX IF NOT EXISTS ix_tfel_session ON telephony_flow_execution_logs(call_session_id);
CREATE INDEX IF NOT EXISTS ix_tfel_company_flow ON telephony_flow_execution_logs(company_id, flow_id);
