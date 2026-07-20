-- =============================================================================
-- Task #39 — B2B SaaS Layer Phase 1 (Foundation, Shadow Mode)
-- Date: May 03, 2026
-- Purpose: Add 11 platform_b2b tables + nullable client_id on associated_companies
-- DC: Idempotent, additive-only, zero impact on existing system (shadow mode)
-- =============================================================================

-- 1. platform_clients
CREATE TABLE IF NOT EXISTS platform_clients (
    id                  SERIAL PRIMARY KEY,
    client_code         VARCHAR(64)  NOT NULL UNIQUE,
    client_name         VARCHAR(200) NOT NULL,
    is_internal         BOOLEAN      NOT NULL DEFAULT FALSE,
    status              VARCHAR(16)  NOT NULL DEFAULT 'active',
    contact_name        VARCHAR(200),
    contact_email       VARCHAR(200),
    contact_phone       VARCHAR(40),
    billing_currency    VARCHAR(8)   NOT NULL DEFAULT 'INR',
    billing_address     TEXT,
    notes               TEXT,
    created_at          TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at          TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT platform_client_status_check    CHECK (status IN ('active','suspended','archived','trial')),
    CONSTRAINT platform_client_currency_check  CHECK (billing_currency IN ('INR','USD'))
);
CREATE INDEX IF NOT EXISTS ix_platform_clients_code ON platform_clients(client_code);

-- 2. platform_modules
CREATE TABLE IF NOT EXISTS platform_modules (
    id                  SERIAL PRIMARY KEY,
    module_code         VARCHAR(128) NOT NULL UNIQUE,
    module_name         VARCHAR(200) NOT NULL,
    category            VARCHAR(64),
    description         TEXT,
    menu_code           VARCHAR(128),
    sidebar_section     VARCHAR(64),
    internal_only       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    custom_overrides    JSONB,
    created_at          TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at          TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);
CREATE INDEX IF NOT EXISTS ix_platform_modules_code     ON platform_modules(module_code);
CREATE INDEX IF NOT EXISTS ix_platform_modules_category ON platform_modules(category);
CREATE INDEX IF NOT EXISTS ix_platform_modules_menu     ON platform_modules(menu_code);

-- 3. platform_module_dependencies
CREATE TABLE IF NOT EXISTS platform_module_dependencies (
    id                       SERIAL PRIMARY KEY,
    module_id                INTEGER NOT NULL REFERENCES platform_modules(id) ON DELETE CASCADE,
    depends_on_module_id     INTEGER NOT NULL REFERENCES platform_modules(id) ON DELETE CASCADE,
    created_at               TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_platform_module_dep UNIQUE (module_id, depends_on_module_id),
    CONSTRAINT ck_platform_module_dep_no_self CHECK (module_id <> depends_on_module_id)
);

-- 4. platform_plans
CREATE TABLE IF NOT EXISTS platform_plans (
    id            SERIAL PRIMARY KEY,
    plan_code     VARCHAR(64)  NOT NULL UNIQUE,
    plan_name     VARCHAR(200) NOT NULL,
    description   TEXT,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at    TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
);

-- 5. platform_plan_modules
CREATE TABLE IF NOT EXISTS platform_plan_modules (
    id          SERIAL PRIMARY KEY,
    plan_id     INTEGER NOT NULL REFERENCES platform_plans(id)   ON DELETE CASCADE,
    module_id   INTEGER NOT NULL REFERENCES platform_modules(id) ON DELETE CASCADE,
    created_at  TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_platform_plan_module UNIQUE (plan_id, module_id)
);

-- 6. platform_subscriptions
CREATE TABLE IF NOT EXISTS platform_subscriptions (
    id                   SERIAL PRIMARY KEY,
    client_id            INTEGER NOT NULL REFERENCES platform_clients(id) ON DELETE CASCADE,
    plan_id              INTEGER REFERENCES platform_plans(id) ON DELETE SET NULL,
    display_plan_name    VARCHAR(200),
    billing_currency     VARCHAR(8)  NOT NULL DEFAULT 'INR',
    billing_cycle        VARCHAR(16) NOT NULL DEFAULT 'monthly',
    annual_free_months   INTEGER     NOT NULL DEFAULT 2,
    is_trial             BOOLEAN     NOT NULL DEFAULT FALSE,
    status               VARCHAR(16) NOT NULL DEFAULT 'active',
    starts_on            DATE,
    ends_on              DATE,
    trial_ends_on        DATE,
    created_at           TIMESTAMP   NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at           TIMESTAMP   NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT platform_sub_currency_check CHECK (billing_currency IN ('INR','USD')),
    CONSTRAINT platform_sub_cycle_check    CHECK (billing_cycle    IN ('monthly','annual')),
    CONSTRAINT platform_sub_status_check   CHECK (status           IN ('trial','active','suspended','cancelled'))
);
CREATE INDEX IF NOT EXISTS ix_platform_sub_client ON platform_subscriptions(client_id);

-- 7. platform_subscription_modules
CREATE TABLE IF NOT EXISTS platform_subscription_modules (
    id               SERIAL PRIMARY KEY,
    subscription_id  INTEGER NOT NULL REFERENCES platform_subscriptions(id) ON DELETE CASCADE,
    module_id        INTEGER NOT NULL REFERENCES platform_modules(id)       ON DELETE CASCADE,
    enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at       TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_platform_sub_module UNIQUE (subscription_id, module_id)
);

-- 8. platform_module_pricing
CREATE TABLE IF NOT EXISTS platform_module_pricing (
    id            SERIAL PRIMARY KEY,
    module_id     INTEGER UNIQUE NOT NULL REFERENCES platform_modules(id) ON DELETE CASCADE,
    price_inr     NUMERIC(14,2) NOT NULL DEFAULT 0,
    price_usd     NUMERIC(14,2) NOT NULL DEFAULT 0,
    pricing_unit  VARCHAR(16)   NOT NULL DEFAULT 'per_company',
    created_at    TIMESTAMP     NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at    TIMESTAMP     NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT platform_pricing_unit_check CHECK (pricing_unit IN ('per_company','per_seat','flat'))
);

-- 9. platform_client_module_pricing_override
CREATE TABLE IF NOT EXISTS platform_client_module_pricing_override (
    id            SERIAL PRIMARY KEY,
    client_id     INTEGER NOT NULL REFERENCES platform_clients(id) ON DELETE CASCADE,
    module_id     INTEGER NOT NULL REFERENCES platform_modules(id) ON DELETE CASCADE,
    price_inr     NUMERIC(14,2),
    price_usd     NUMERIC(14,2),
    pricing_unit  VARCHAR(16),
    notes         TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    updated_at    TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT uq_platform_client_module_override UNIQUE (client_id, module_id)
);

-- 10. platform_audit_log
CREATE TABLE IF NOT EXISTS platform_audit_log (
    id                BIGSERIAL PRIMARY KEY,
    actor_staff_id    INTEGER,
    client_id         INTEGER,
    entity            VARCHAR(32) NOT NULL,
    action            VARCHAR(16) NOT NULL,
    entity_id         INTEGER,
    before_json       JSONB,
    after_json        JSONB,
    created_at        TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT platform_audit_action_check CHECK (action IN ('CREATE','UPDATE','DELETE'))
);
CREATE INDEX IF NOT EXISTS ix_platform_audit_actor    ON platform_audit_log(actor_staff_id);
CREATE INDEX IF NOT EXISTS ix_platform_audit_client   ON platform_audit_log(client_id);
CREATE INDEX IF NOT EXISTS ix_platform_audit_entity   ON platform_audit_log(entity);
CREATE INDEX IF NOT EXISTS ix_platform_audit_at       ON platform_audit_log(created_at);

-- 11. b2b_shadow_log
CREATE TABLE IF NOT EXISTS b2b_shadow_log (
    id           BIGSERIAL PRIMARY KEY,
    client_id    INTEGER,
    user_id      INTEGER,
    user_type    VARCHAR(32),
    module_code  VARCHAR(128),
    route        VARCHAR(512),
    decision     VARCHAR(16) NOT NULL,
    reason       VARCHAR(200),
    created_at   TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
    CONSTRAINT b2b_shadow_decision_check CHECK (decision IN ('ALLOW','WOULD_BLOCK'))
);
CREATE INDEX IF NOT EXISTS ix_b2b_shadow_client_module_at ON b2b_shadow_log(client_id, module_code, created_at);
CREATE INDEX IF NOT EXISTS ix_b2b_shadow_at               ON b2b_shadow_log(created_at);

-- 12. associated_companies.client_id (nullable FK back to platform_clients)
ALTER TABLE associated_companies
    ADD COLUMN IF NOT EXISTS client_id INTEGER NULL REFERENCES platform_clients(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_associated_companies_client_id ON associated_companies(client_id);
