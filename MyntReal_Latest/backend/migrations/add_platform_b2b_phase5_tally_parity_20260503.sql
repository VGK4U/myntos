-- ============================================================================
-- Task #43 — B2B SaaS Phase 3a.0: Tally Parity for SaaS Billing
-- ============================================================================
-- Purpose:
--   Bring platform_invoices / platform_invoice_lines / platform_modules /
--   platform_clients to schema parity with the existing tally-grade
--   sales_invoices table, so SaaS billing follows the SAME tally-like model
--   as customer invoicing — all under one SaaS umbrella.
--
-- DC compliance:
--   * 100% additive. ZERO ALTER on sales_invoices, purchase_invoice_*,
--     associated_companies, or any other production table.
--   * All new columns NULLABLE with safe defaults — existing code paths
--     (which don't reference them yet) continue to work unchanged.
--   * Idempotent: every ALTER uses ADD COLUMN IF NOT EXISTS, every UPDATE
--     guarded by IS NULL.
--   * Single transaction — partial failure rolls back fully.
--   * No DROP, no RENAME, no NOT NULL on existing columns.
--
-- Mapping decision (user-confirmed):
--   platform_clients.MNR-INTERNAL  →  associated_companies.id=4 (MyntReal LLP)
--   = the default legal entity that issues SaaS invoices for MyntReal's own
--     internal SaaS account.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. platform_clients — pointer to default issuing legal entity + GST identity
-- ----------------------------------------------------------------------------
ALTER TABLE platform_clients
  ADD COLUMN IF NOT EXISTS primary_legal_entity_id INT
    REFERENCES associated_companies(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS gstin           VARCHAR(20),
  ADD COLUMN IF NOT EXISTS state_for_gst   VARCHAR(80),
  ADD COLUMN IF NOT EXISTS pan_number      VARCHAR(20);

CREATE INDEX IF NOT EXISTS ix_platform_clients_legal_entity
  ON platform_clients(primary_legal_entity_id);

-- ----------------------------------------------------------------------------
-- 2. platform_modules — HSN/SAC + UoM + default GST rate (Tally line parity)
-- ----------------------------------------------------------------------------
ALTER TABLE platform_modules
  ADD COLUMN IF NOT EXISTS hsn_sac_code         VARCHAR(20),
  ADD COLUMN IF NOT EXISTS unit_of_measure      VARCHAR(20)  DEFAULT 'NOS',
  ADD COLUMN IF NOT EXISTS default_tax_rate_pct NUMERIC(5,2) DEFAULT 18.00;

-- ----------------------------------------------------------------------------
-- 3. platform_invoices — Tally header parity (mirrors sales_invoices)
-- ----------------------------------------------------------------------------
ALTER TABLE platform_invoices
  ADD COLUMN IF NOT EXISTS company_id INT
    REFERENCES associated_companies(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS invoice_date         DATE,
  ADD COLUMN IF NOT EXISTS customer_type        VARCHAR(40)  DEFAULT 'B2B_SAAS_TENANT',
  ADD COLUMN IF NOT EXISTS customer_name        VARCHAR(255),
  ADD COLUMN IF NOT EXISTS customer_address     TEXT,
  ADD COLUMN IF NOT EXISTS customer_gstin       VARCHAR(20),
  ADD COLUMN IF NOT EXISTS customer_state       VARCHAR(80),
  ADD COLUMN IF NOT EXISTS customer_phone       VARCHAR(40),
  ADD COLUMN IF NOT EXISTS customer_email       VARCHAR(120),
  ADD COLUMN IF NOT EXISTS billing_address      TEXT,
  ADD COLUMN IF NOT EXISTS shipping_address     TEXT,
  ADD COLUMN IF NOT EXISTS is_igst              BOOLEAN      DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS seller_state         VARCHAR(80),
  ADD COLUMN IF NOT EXISTS buyer_state          VARCHAR(80),
  ADD COLUMN IF NOT EXISTS taxable_amount       NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cgst_amount          NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS sgst_amount          NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS igst_amount          NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cess_amount          NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_tax            NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS round_off            NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS grand_total          NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS amount_in_words      VARCHAR(255),
  ADD COLUMN IF NOT EXISTS payment_mode         VARCHAR(40),
  ADD COLUMN IF NOT EXISTS amount_received      NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS balance_due          NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_credit_sale       BOOLEAN       DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS credit_days          INT,
  ADD COLUMN IF NOT EXISTS pdf_path             VARCHAR(255),
  ADD COLUMN IF NOT EXISTS irn_number           VARCHAR(64),
  ADD COLUMN IF NOT EXISTS ack_number           VARCHAR(64),
  ADD COLUMN IF NOT EXISTS ack_date             TIMESTAMP,
  ADD COLUMN IF NOT EXISTS e_way_bill_number    VARCHAR(64),
  ADD COLUMN IF NOT EXISTS e_way_bill_date      TIMESTAMP,
  ADD COLUMN IF NOT EXISTS terms_conditions     TEXT,
  ADD COLUMN IF NOT EXISTS remarks              TEXT,
  ADD COLUMN IF NOT EXISTS fy_sequence          INT,
  ADD COLUMN IF NOT EXISTS wvv_hash             VARCHAR(255),
  ADD COLUMN IF NOT EXISTS billing_company_id   INT
    REFERENCES associated_companies(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS so_number            VARCHAR(64);

CREATE INDEX IF NOT EXISTS ix_platform_invoices_company_id
  ON platform_invoices(company_id);
CREATE INDEX IF NOT EXISTS ix_platform_invoices_invoice_date
  ON platform_invoices(invoice_date);
CREATE INDEX IF NOT EXISTS ix_platform_invoices_customer_type
  ON platform_invoices(customer_type);

-- ----------------------------------------------------------------------------
-- 4. platform_invoice_lines — Tally line-level tax parity
-- ----------------------------------------------------------------------------
ALTER TABLE platform_invoice_lines
  ADD COLUMN IF NOT EXISTS hsn_sac_code   VARCHAR(20),
  ADD COLUMN IF NOT EXISTS gst_rate       NUMERIC(5,2)  DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cgst_amount    NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS sgst_amount    NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS igst_amount    NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cess_amount    NUMERIC(14,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS taxable_value  NUMERIC(14,2) DEFAULT 0;

-- ----------------------------------------------------------------------------
-- 5. Backfill — only rows that currently lack the new linkage
-- ----------------------------------------------------------------------------
-- 5a. Link MNR-INTERNAL → MyntReal LLP (associated_companies.id=4)
UPDATE platform_clients
   SET primary_legal_entity_id = 4
 WHERE client_code = 'MNR-INTERNAL'
   AND primary_legal_entity_id IS NULL
   AND EXISTS (SELECT 1 FROM associated_companies WHERE id = 4);

-- 5b. Existing 5 test invoices → company_id = 4 (issued by MyntReal LLP)
--     Mirror legacy columns into new tally-parity columns where empty.
UPDATE platform_invoices pi
   SET company_id      = COALESCE(pi.company_id, 4),
       invoice_date    = COALESCE(pi.invoice_date, pi.issue_date),
       grand_total     = COALESCE(NULLIF(pi.grand_total, 0), pi.total),
       amount_received = COALESCE(NULLIF(pi.amount_received, 0), pi.amount_paid),
       total_tax       = COALESCE(NULLIF(pi.total_tax, 0), pi.tax),
       balance_due     = COALESCE(NULLIF(pi.balance_due, 0),
                                  GREATEST(pi.total - pi.amount_paid, 0)),
       customer_name   = COALESCE(pi.customer_name,
                                  (SELECT client_name FROM platform_clients
                                    WHERE id = pi.client_id)),
       customer_email  = COALESCE(pi.customer_email,
                                  (SELECT contact_email FROM platform_clients
                                    WHERE id = pi.client_id))
 WHERE pi.company_id IS NULL;

COMMIT;

-- ============================================================================
-- Verification queries (run by hand after migration; no destructive effect)
-- ============================================================================
--   SELECT count(*) FROM platform_invoices WHERE company_id IS NOT NULL;     -- expect 5
--   SELECT count(*) FROM platform_clients WHERE primary_legal_entity_id=4;   -- expect 1
--   SELECT count(*) FROM sales_invoices;                                     -- expect 17 (UNCHANGED)
-- ============================================================================
