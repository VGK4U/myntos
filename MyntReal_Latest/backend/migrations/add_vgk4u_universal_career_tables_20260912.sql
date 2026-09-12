-- =============================================================================
-- MIGRATION: VGK4U Universal Career, Personal Production & Commission Architecture
-- Date: 2026-09-12
-- Scope: Additive schema for VGK4U Career, Personal Production, and Differential Commission Engine
-- Safety: ZERO mutations to historical financial ledgers (vgk_cash_income_entries, vgk_solar_cibil_advances)
-- =============================================================================

BEGIN;

-- 1. Career Designation Configurations
CREATE TABLE IF NOT EXISTS vgk4u_career_designation_configs (
    id SERIAL PRIMARY KEY,
    designation_code VARCHAR(30) NOT NULL UNIQUE,
    designation_name VARCHAR(50) NOT NULL,
    hierarchy_order INTEGER NOT NULL UNIQUE,
    required_own_qualifying_files INTEGER NOT NULL DEFAULT 0,
    required_active_team_members INTEGER NOT NULL DEFAULT 0,
    self_earning_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    team_differential_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Personal Production Qualification Configurations
CREATE TABLE IF NOT EXISTS vgk4u_personal_prod_configs (
    id SERIAL PRIMARY KEY,
    tier_code VARCHAR(30) NOT NULL UNIQUE,
    tier_name VARCHAR(50) NOT NULL,
    min_qualifying_files INTEGER NOT NULL,
    commission_rate_pct NUMERIC(5, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Category Commission Configurations (Differential Waterfall)
CREATE TABLE IF NOT EXISTS vgk4u_category_commission_configs (
    id SERIAL PRIMARY KEY,
    version_label VARCHAR(50) NOT NULL DEFAULT 'v2_sep2026',
    effective_from TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT '2026-09-08 00:00:00',
    effective_to TIMESTAMP WITHOUT TIME ZONE NULL,
    category_slug VARCHAR(50) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    max_network_pool_pct NUMERIC(5, 2) NOT NULL,
    producer_base_pct NUMERIC(5, 2) NOT NULL,
    manager_diff_pct NUMERIC(5, 2) NOT NULL,
    gm_diff_pct NUMERIC(5, 2) NOT NULL,
    rm_diff_pct NUMERIC(5, 2) NOT NULL,
    support_journey_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.75,
    support_end_to_end_pct NUMERIC(5, 2) NOT NULL DEFAULT 1.50,
    showroom_pct NUMERIC(5, 2) NOT NULL DEFAULT 3.50,
    unallocated_balance_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    admin_charge_pct NUMERIC(5, 2) NOT NULL DEFAULT 8.00,
    tds_pct NUMERIC(5, 2) NOT NULL DEFAULT 2.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_vgk4u_cat_version UNIQUE (version_label, category_slug)
);

-- 4. Additive Non-Breaking Cache Columns to official_partners
ALTER TABLE official_partners
    ADD COLUMN IF NOT EXISTS vgk4u_current_designation VARCHAR(50) DEFAULT 'Member',
    ADD COLUMN IF NOT EXISTS vgk4u_personal_prod_qualification VARCHAR(50) DEFAULT 'None',
    ADD COLUMN IF NOT EXISTS vgk4u_own_qualifying_files INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS vgk4u_active_team_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS vgk4u_designation_updated_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS is_apex_node BOOLEAN DEFAULT FALSE;

-- 5. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_op_vgk4u_designation ON official_partners (vgk4u_current_designation);
CREATE INDEX IF NOT EXISTS idx_op_vgk4u_prod_qual ON official_partners (vgk4u_personal_prod_qualification);
CREATE INDEX IF NOT EXISTS idx_op_parent_partner_id ON official_partners (parent_partner_id);
CREATE INDEX IF NOT EXISTS idx_crm_leads_partner_status ON crm_leads (associated_partner_id, status, solar_pipeline_status);

-- 6. Seed Career Designation Configurations (Initial Authoritative Ladder)
INSERT INTO vgk4u_career_designation_configs 
    (designation_code, designation_name, hierarchy_order, required_own_qualifying_files, required_active_team_members, self_earning_pct, team_differential_pct, is_active)
VALUES
    ('MEMBER', 'Member', 0, 0, 0, 0.00, 0.00, TRUE),
    ('CHANNEL_PARTNER', 'Channel Partner', 1, 1, 0, 6.00, 0.00, TRUE),
    ('MANAGER', 'Manager', 2, 1, 1, 7.50, 1.50, TRUE),
    ('GENERAL_MANAGER', 'General Manager', 3, 1, 5, 8.50, 1.00, TRUE),
    ('REGIONAL_MANAGER', 'Regional Manager', 4, 1, 10, 9.00, 0.50, TRUE)
ON CONFLICT (designation_code) DO UPDATE SET
    designation_name = EXCLUDED.designation_name,
    hierarchy_order = EXCLUDED.hierarchy_order,
    required_own_qualifying_files = EXCLUDED.required_own_qualifying_files,
    required_active_team_members = EXCLUDED.required_active_team_members,
    self_earning_pct = EXCLUDED.self_earning_pct,
    team_differential_pct = EXCLUDED.team_differential_pct,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 7. Seed Personal Production Qualification Configurations
INSERT INTO vgk4u_personal_prod_configs 
    (tier_code, tier_name, min_qualifying_files, commission_rate_pct, is_active)
VALUES
    ('BASE', 'Base / Channel Partner Qualified', 1, 6.00, TRUE),
    ('GM_QUALIFIED', 'GM Commission Qualified', 5, 8.50, TRUE),
    ('RM_QUALIFIED', 'RM Commission Qualified', 10, 9.00, TRUE)
ON CONFLICT (tier_code) DO UPDATE SET
    tier_name = EXCLUDED.tier_name,
    min_qualifying_files = EXCLUDED.min_qualifying_files,
    commission_rate_pct = EXCLUDED.commission_rate_pct,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 8. Seed Category Commission Configurations (Version 'v2_sep2026')
INSERT INTO vgk4u_category_commission_configs 
    (version_label, effective_from, category_slug, category_name, max_network_pool_pct, producer_base_pct, manager_diff_pct, gm_diff_pct, rm_diff_pct, support_journey_pct, support_end_to_end_pct, showroom_pct, unallocated_balance_pct, admin_charge_pct, tds_pct, is_active)
VALUES
    ('v2_sep2026', '2026-09-08 00:00:00', 'solar', 'Solar Energy Systems', 9.00, 6.00, 1.50, 1.00, 0.50, 0.75, 1.50, 3.50, 0.00, 8.00, 2.00, TRUE),
    ('v2_sep2026', '2026-09-08 00:00:00', 'ev', 'Electric Vehicles (EV)', 22.00, 5.00, 2.50, 1.50, 0.50, 1.50, 3.00, 0.00, 9.50, 8.00, 2.00, TRUE),
    ('v2_sep2026', '2026-09-08 00:00:00', 'etc-training', 'ETC Training & Skills', 11.00, 5.00, 2.50, 2.00, 1.50, 0.00, 0.00, 0.00, 0.00, 8.00, 2.00, TRUE),
    ('v2_sep2026', '2026-09-08 00:00:00', 'real-dreams', 'Real Dreams (Real Estate)', 6.00, 3.00, 1.50, 1.00, 0.50, 0.00, 0.00, 0.00, 0.00, 8.00, 2.00, TRUE),
    ('v2_sep2026', '2026-09-08 00:00:00', 'insurance', 'Insurance Services', 11.00, 5.00, 2.50, 2.00, 1.50, 0.00, 0.00, 0.00, 0.00, 8.00, 2.00, TRUE)
ON CONFLICT (version_label, category_slug) DO UPDATE SET
    effective_from = EXCLUDED.effective_from,
    category_name = EXCLUDED.category_name,
    max_network_pool_pct = EXCLUDED.max_network_pool_pct,
    producer_base_pct = EXCLUDED.producer_base_pct,
    manager_diff_pct = EXCLUDED.manager_diff_pct,
    gm_diff_pct = EXCLUDED.gm_diff_pct,
    rm_diff_pct = EXCLUDED.rm_diff_pct,
    support_journey_pct = EXCLUDED.support_journey_pct,
    support_end_to_end_pct = EXCLUDED.support_end_to_end_pct,
    showroom_pct = EXCLUDED.showroom_pct,
    unallocated_balance_pct = EXCLUDED.unallocated_balance_pct,
    admin_charge_pct = EXCLUDED.admin_charge_pct,
    tds_pct = EXCLUDED.tds_pct,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;
