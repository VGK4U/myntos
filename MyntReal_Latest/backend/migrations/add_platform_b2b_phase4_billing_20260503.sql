-- Task #42 — B2B SaaS Layer Phase 4 (Billing & Invoicing)
-- Idempotent. Adds invoices, invoice_lines, payments. INR/USD aware.
-- DC: zero impact on existing SFMS sales-invoice tables.

CREATE TABLE IF NOT EXISTS platform_invoices (
    id                  SERIAL PRIMARY KEY,
    invoice_number      VARCHAR(40)  NOT NULL UNIQUE,
    client_id           INT          NOT NULL REFERENCES platform_clients(id),
    subscription_id     INT          REFERENCES platform_subscriptions(id),
    currency            VARCHAR(8)   NOT NULL DEFAULT 'INR',
    period_start        DATE         NOT NULL,
    period_end          DATE         NOT NULL,
    issue_date          DATE         NOT NULL DEFAULT CURRENT_DATE,
    due_date            DATE         NOT NULL,
    subtotal            NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax                 NUMERIC(14,2) NOT NULL DEFAULT 0,
    total               NUMERIC(14,2) NOT NULL DEFAULT 0,
    amount_paid         NUMERIC(14,2) NOT NULL DEFAULT 0,
    status              VARCHAR(20)  NOT NULL DEFAULT 'open',
            -- open | paid | partial | overdue | void
    notes               TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_platform_invoices_client    ON platform_invoices(client_id);
CREATE INDEX IF NOT EXISTS ix_platform_invoices_status    ON platform_invoices(status);
CREATE INDEX IF NOT EXISTS ix_platform_invoices_due_date  ON platform_invoices(due_date);

CREATE TABLE IF NOT EXISTS platform_invoice_lines (
    id              SERIAL PRIMARY KEY,
    invoice_id      INT NOT NULL REFERENCES platform_invoices(id) ON DELETE CASCADE,
    module_id       INT REFERENCES platform_modules(id),
    description     VARCHAR(255) NOT NULL,
    quantity        NUMERIC(12,2) NOT NULL DEFAULT 1,
    unit_price      NUMERIC(14,2) NOT NULL DEFAULT 0,
    line_total      NUMERIC(14,2) NOT NULL DEFAULT 0,
    pricing_unit    VARCHAR(20),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_platform_invoice_lines_invoice ON platform_invoice_lines(invoice_id);

CREATE TABLE IF NOT EXISTS platform_payments (
    id              SERIAL PRIMARY KEY,
    client_id       INT NOT NULL REFERENCES platform_clients(id),
    invoice_id      INT REFERENCES platform_invoices(id),
    amount          NUMERIC(14,2) NOT NULL,
    currency        VARCHAR(8)    NOT NULL DEFAULT 'INR',
    method          VARCHAR(40),  -- bank | upi | stripe | razorpay | cash | manual | …
    reference       VARCHAR(120),
    received_on     DATE          NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    recorded_by     INT,          -- staff_employees.id
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_platform_payments_client  ON platform_payments(client_id);
CREATE INDEX IF NOT EXISTS ix_platform_payments_invoice ON platform_payments(invoice_id);
