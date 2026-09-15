"""SaaS Phase 1 Database Foundation

Revision ID: a7b8c9d0e1f2
Revises: 120aa1c00de3
Create Date: 2026-09-14 06:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = '120aa1c00de3'
branch_labels = None
depends_on = None


def upgrade():
    # Step 0: Ensure root parent entities have PRIMARY KEY and UNIQUE constraints in public schema
    op.execute(sa.text("""
        DO $body$
        BEGIN
            -- 0.1 platform_clients PK
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint c
                JOIN pg_namespace n ON c.conrelid = (n.nspname || '.platform_clients')::regclass
                WHERE c.contype = 'p' AND n.nspname = 'public'
            ) THEN
                ALTER TABLE public.platform_clients ADD CONSTRAINT pk_platform_clients PRIMARY KEY (id);
            END IF;

            -- 0.2 associated_companies PK
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint c
                JOIN pg_namespace n ON c.conrelid = (n.nspname || '.associated_companies')::regclass
                WHERE c.contype = 'p' AND n.nspname = 'public'
            ) THEN
                ALTER TABLE public.associated_companies ADD CONSTRAINT pk_associated_companies PRIMARY KEY (id);
            END IF;

            -- 0.3 staff_roles PK
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint c
                JOIN pg_namespace n ON c.conrelid = (n.nspname || '.staff_roles')::regclass
                WHERE c.contype = 'p' AND n.nspname = 'public'
            ) THEN
                ALTER TABLE public.staff_roles ADD CONSTRAINT pk_staff_roles PRIMARY KEY (id);
            END IF;

            -- 0.4 associated_companies UNIQUE (client_id, id)
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_associated_companies_client_id_id'
            ) THEN
                ALTER TABLE public.associated_companies ADD CONSTRAINT uq_associated_companies_client_id_id UNIQUE (client_id, id);
            END IF;
        END $body$;
    """))

    # Step 1: staff_employees columns, authoritative backfill, index
    op.execute(sa.text("""
        ALTER TABLE staff_employees 
            ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id),
            ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;
            
        -- Authoritative backfill from base_company_id -> associated_companies.client_id
        UPDATE staff_employees 
        SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE staff_employees.base_company_id = ac.id AND staff_employees.tenant_id IS NULL;
        
        -- Fallback for staff with NULL base_company_id (e.g. resigned staff id=23)
        UPDATE staff_employees SET tenant_id = 1 WHERE tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_staff_employees_tenant_id ON staff_employees(tenant_id);
    """))

    # Step 2: staff_company_memberships table & backfill
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS staff_company_memberships (
            id SERIAL PRIMARY KEY,
            staff_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
            tenant_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            is_primary BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            role_id INTEGER REFERENCES staff_roles(id),
            segment_access JSONB NOT NULL DEFAULT '["ALL"]',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
            CONSTRAINT uq_staff_tenant_company UNIQUE (staff_id, tenant_id, company_id),
            CONSTRAINT fk_scm_tenant_company FOREIGN KEY (tenant_id, company_id) 
                REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT
        );
        CREATE INDEX IF NOT EXISTS idx_scm_staff_id ON staff_company_memberships (staff_id);
        CREATE INDEX IF NOT EXISTS idx_scm_tenant_company ON staff_company_memberships (tenant_id, company_id);

        -- Primary memberships from base_company_id
        INSERT INTO staff_company_memberships (staff_id, tenant_id, company_id, is_primary, is_active, role_id)
        SELECT s.id, s.tenant_id, s.base_company_id, TRUE, (s.status = 'active'), s.role_id
        FROM staff_employees s
        WHERE s.base_company_id IS NOT NULL AND s.base_company_id IN (SELECT id FROM associated_companies)
        ON CONFLICT (staff_id, tenant_id, company_id) DO NOTHING;

        -- Secondary memberships from data_companies
        INSERT INTO staff_company_memberships (staff_id, tenant_id, company_id, is_primary, is_active, role_id)
        SELECT 
            s.id, 
            s.tenant_id, 
            (elem)::INTEGER, 
            FALSE, 
            (s.status = 'active'), 
            s.role_id
        FROM staff_employees s,
        jsonb_array_elements_text(CASE WHEN jsonb_typeof(s.data_companies::jsonb) = 'array' THEN s.data_companies::jsonb ELSE '[]'::jsonb END) AS elem
        WHERE elem ~ '^[0-9]+$' 
          AND (elem)::INTEGER IN (SELECT id FROM associated_companies)
          AND (s.base_company_id IS NULL OR (elem)::INTEGER != s.base_company_id)
          AND s.tenant_id IS NOT NULL
        ON CONFLICT (staff_id, tenant_id, company_id) DO NOTHING;
    """))

    # Step 3: crm_leads
    op.execute(sa.text("""
        ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE crm_leads SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE crm_leads.company_id = ac.id AND crm_leads.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_crm_leads_tenant_company ON crm_leads(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_leads_tenant_company') THEN
                ALTER TABLE crm_leads ADD CONSTRAINT fk_crm_leads_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 4: service_ticket (preserving 28 legacy NULL company_id rows)
    op.execute(sa.text("""
        ALTER TABLE service_ticket ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE service_ticket SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE service_ticket.company_id = ac.id AND service_ticket.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_service_ticket_tenant_company ON service_ticket(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_service_ticket_tenant_company') THEN
                ALTER TABLE service_ticket ADD CONSTRAINT fk_service_ticket_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 5: whatsapp_api_config
    op.execute(sa.text("""
        ALTER TABLE whatsapp_api_config ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE whatsapp_api_config SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE whatsapp_api_config.company_id = ac.id AND whatsapp_api_config.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_whatsapp_api_config_tenant_company ON whatsapp_api_config(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_whatsapp_api_config_tenant_company') THEN
                ALTER TABLE whatsapp_api_config ADD CONSTRAINT fk_whatsapp_api_config_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 6: meta_campaigns
    op.execute(sa.text("""
        ALTER TABLE meta_campaigns ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE meta_campaigns SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE meta_campaigns.company_id = ac.id AND meta_campaigns.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_meta_campaigns_tenant_company ON meta_campaigns(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_meta_campaigns_tenant_company') THEN
                ALTER TABLE meta_campaigns ADD CONSTRAINT fk_meta_campaigns_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 7: meta_form_mappings
    op.execute(sa.text("""
        ALTER TABLE meta_form_mappings ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE meta_form_mappings SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE meta_form_mappings.company_id = ac.id AND meta_form_mappings.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_meta_form_mappings_tenant_company ON meta_form_mappings(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_meta_form_mappings_tenant_company') THEN
                ALTER TABLE meta_form_mappings ADD CONSTRAINT fk_meta_form_mappings_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 8: facebook_pages
    op.execute(sa.text("""
        ALTER TABLE facebook_pages ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE facebook_pages SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE facebook_pages.company_id = ac.id AND facebook_pages.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_facebook_pages_tenant_company ON facebook_pages(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_facebook_pages_tenant_company') THEN
                ALTER TABLE facebook_pages ADD CONSTRAINT fk_facebook_pages_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 9: staff_call_logs
    op.execute(sa.text("""
        ALTER TABLE staff_call_logs ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE staff_call_logs SET tenant_id = ac.client_id 
        FROM associated_companies ac 
        WHERE staff_call_logs.company_id = ac.id AND staff_call_logs.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_staff_call_logs_tenant_company ON staff_call_logs(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_staff_call_logs_tenant_company') THEN
                ALTER TABLE staff_call_logs ADD CONSTRAINT fk_staff_call_logs_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))

    # Step 10: staff_audit_log (authoritative staff join + preserve unmatched as NULL)
    op.execute(sa.text("""
        ALTER TABLE staff_audit_log ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        UPDATE staff_audit_log SET tenant_id = s.tenant_id 
        FROM staff_employees s 
        WHERE staff_audit_log.employee_id = s.id AND staff_audit_log.tenant_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_staff_audit_log_tenant_id ON staff_audit_log(tenant_id);
    """))

    # Step 11: background_jobs (nullable tenant_id, no fabricated backfill)
    op.execute(sa.text("""
        ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        CREATE INDEX IF NOT EXISTS idx_background_jobs_tenant_id ON background_jobs(tenant_id);
    """))

    # Step 12: crm_lead_sync_configs (nullable columns, zero assumed backfill)
    op.execute(sa.text("""
        ALTER TABLE crm_lead_sync_configs 
            ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES associated_companies(id),
            ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES platform_clients(id);
        
        CREATE INDEX IF NOT EXISTS idx_crm_lead_sync_configs_tenant_company ON crm_lead_sync_configs(tenant_id, company_id);
        
        DO $body$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_lead_sync_configs_tenant_company') THEN
                ALTER TABLE crm_lead_sync_configs ADD CONSTRAINT fk_crm_lead_sync_configs_tenant_company 
                    FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies (client_id, id) ON DELETE RESTRICT;
            END IF;
        END $body$;
    """))


def downgrade():
    # 1. Drop constraints
    op.execute(sa.text("ALTER TABLE crm_lead_sync_configs DROP CONSTRAINT IF EXISTS fk_crm_lead_sync_configs_tenant_company;"))
    op.execute(sa.text("ALTER TABLE staff_call_logs DROP CONSTRAINT IF EXISTS fk_staff_call_logs_tenant_company;"))
    op.execute(sa.text("ALTER TABLE facebook_pages DROP CONSTRAINT IF EXISTS fk_facebook_pages_tenant_company;"))
    op.execute(sa.text("ALTER TABLE meta_form_mappings DROP CONSTRAINT IF EXISTS fk_meta_form_mappings_tenant_company;"))
    op.execute(sa.text("ALTER TABLE meta_campaigns DROP CONSTRAINT IF EXISTS fk_meta_campaigns_tenant_company;"))
    op.execute(sa.text("ALTER TABLE whatsapp_api_config DROP CONSTRAINT IF EXISTS fk_whatsapp_api_config_tenant_company;"))
    op.execute(sa.text("ALTER TABLE service_ticket DROP CONSTRAINT IF EXISTS fk_service_ticket_tenant_company;"))
    op.execute(sa.text("ALTER TABLE crm_leads DROP CONSTRAINT IF EXISTS fk_crm_leads_tenant_company;"))

    # 2. Drop staff_company_memberships table
    op.execute(sa.text("DROP TABLE IF EXISTS staff_company_memberships CASCADE;"))

    # 3. Drop indexes
    op.execute(sa.text("DROP INDEX IF EXISTS idx_crm_lead_sync_configs_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_background_jobs_tenant_id;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_staff_audit_log_tenant_id;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_staff_call_logs_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_facebook_pages_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_meta_form_mappings_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_meta_campaigns_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_whatsapp_api_config_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_service_ticket_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_crm_leads_tenant_company;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_staff_employees_tenant_id;"))

    # 4. Drop added columns
    op.execute(sa.text("ALTER TABLE crm_lead_sync_configs DROP COLUMN IF EXISTS company_id, DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE background_jobs DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE staff_audit_log DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE staff_call_logs DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE facebook_pages DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE meta_form_mappings DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE meta_campaigns DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE whatsapp_api_config DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE service_ticket DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE crm_leads DROP COLUMN IF EXISTS tenant_id;"))
    op.execute(sa.text("ALTER TABLE staff_employees DROP COLUMN IF EXISTS tenant_id, DROP COLUMN IF EXISTS token_version;"))

    # 5. Drop uq_associated_companies_client_id_id
    op.execute(sa.text("ALTER TABLE associated_companies DROP CONSTRAINT IF EXISTS uq_associated_companies_client_id_id;"))
