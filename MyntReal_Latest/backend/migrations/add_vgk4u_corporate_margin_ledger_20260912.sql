-- VGK4U Corporate Retained Margin Ledger Migration
-- Created: 2026-09-12
-- Scope: Dedicated corporate ledger for Apex remainder and corporate retained margin
-- Guarantees:
-- 1. Attributable to source lead/deal
-- 2. Fully auditable with deal value, retained %, amount, deductions (0.00), reason
-- 3. Strictly separated from personal partner income (vgk_cash_income_entries)
-- 4. Idempotent via unique constraint on (company_id, source_lead_id, retained_reason)

CREATE TABLE IF NOT EXISTS vgk4u_corporate_margin_ledger (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    source_lead_id INTEGER NOT NULL,
    category_slug VARCHAR(50) NOT NULL DEFAULT 'solar',
    program_version VARCHAR(50) NOT NULL DEFAULT 'v2_sep2026',
    deal_value NUMERIC(15, 2) NOT NULL,
    retained_pct NUMERIC(5, 2) NOT NULL,
    retained_amount NUMERIC(15, 2) NOT NULL,
    admin_charges NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    tds_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    net_retained_amount NUMERIC(15, 2) NOT NULL,
    retained_reason VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'RECORDED',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_vgk4u_corp_margin_lead_reason UNIQUE (company_id, source_lead_id, retained_reason)
);

CREATE INDEX IF NOT EXISTS idx_vgk4u_cml_lead_id ON vgk4u_corporate_margin_ledger(source_lead_id);
CREATE INDEX IF NOT EXISTS idx_vgk4u_cml_company_id ON vgk4u_corporate_margin_ledger(company_id);
CREATE INDEX IF NOT EXISTS idx_vgk4u_cml_created_at ON vgk4u_corporate_margin_ledger(created_at);
