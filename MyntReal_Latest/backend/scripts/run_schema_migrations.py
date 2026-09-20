#!/usr/bin/env python3
"""
MyntOS Standalone Schema Migration Runner
Executes database migrations and schema bootstrap in a controlled, isolated process.
Enforces:
- SET LOCAL lock_timeout = '2s'
- SET LOCAL statement_timeout = '10s'
- information_schema preflights
- Idempotent execution
- Decoupled from web server startup lifecycle
"""

import os
import sys
import logging
from pathlib import Path

# Setup path to backend
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_runner")

def run_migrations():
    # DC Protocol (ARCHITECTURAL FIX - Sep 2026):
    # Standalone runner is the ONLY sanctioned process allowed to run DDL
    os.environ["RUN_EXPLICIT_MIGRATIONS"] = "1"
    logger.info("==================================================")
    logger.info("MyntOS Standalone Schema Migration Runner Starting")
    logger.info("==================================================")
    
    # 1. Check DB connectivity
    from app.core.database import engine, SessionLocal, run_pending_migrations, Base
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SET statement_timeout = 10000"))
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connectivity verified")
    except Exception as e:
        logger.error(f"❌ Cannot connect to database: {e}")
        sys.exit(1)
        
    # 2. Run core database pending migrations
    try:
        logger.info("Running core database pending migrations...")
        run_pending_migrations()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Core database migrations complete")
    except Exception as e:
        logger.error(f"❌ Core migrations failed: {e}")
        sys.exit(1)

    # 3. Run Schema Bootstrap routines
    try:
        from app.core.schema_bootstrap import run_schema_bootstrap
        logger.info("Running schema bootstrap routines...")
        run_schema_bootstrap()
        logger.info("✅ Schema bootstrap complete")
    except Exception as e:
        logger.error(f"❌ Schema bootstrap failed: {e}")
        sys.exit(1)

    # 4. DC Protocol: Explicit Feature Tables & Schema Objects
    # Formerly created at runtime in request handlers / module imports
    try:
        logger.info("Running feature-specific schema migrations...")
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL lock_timeout = '2000'"))
                conn.execute(text("SET LOCAL statement_timeout = '10000'"))

                # 4.1 service_center_given_out (from staff_accounts_service)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS service_center_given_out (
                        id SERIAL PRIMARY KEY,
                        given_out_number VARCHAR(30) UNIQUE NOT NULL,
                        company_id INTEGER NOT NULL REFERENCES associated_companies(id),
                        service_center_id INTEGER NOT NULL REFERENCES official_partners(id),
                        service_ticket_id INTEGER REFERENCES service_ticket(id),
                        recipient_type VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER',
                        recipient_name VARCHAR(200) NOT NULL,
                        recipient_contact VARCHAR(20),
                        recipient_email VARCHAR(200),
                        recipient_partner_id INTEGER REFERENCES official_partners(id),
                        item_id INTEGER REFERENCES stock_item_master(id),
                        item_name VARCHAR(200) NOT NULL,
                        item_code VARCHAR(30),
                        serial_number VARCHAR(100),
                        quantity NUMERIC(15,3) NOT NULL DEFAULT 1,
                        unit_rate NUMERIC(15,2) DEFAULT 0,
                        purpose VARCHAR(20) NOT NULL DEFAULT 'LOAN',
                        notes TEXT,
                        given_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        expected_return_date DATE,
                        status VARCHAR(20) NOT NULL DEFAULT 'GIVEN_OUT',
                        returned_at TIMESTAMP,
                        return_notes TEXT,
                        return_received_by_id INTEGER,
                        created_by_id INTEGER,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """))

                # 4.2 platform_invoice_counters (from platform_b2b_billing)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS platform_invoice_counters (
                        period   VARCHAR(8) PRIMARY KEY,
                        last_seq INTEGER NOT NULL DEFAULT 0
                    )
                """))

                # 4.3 catalog_shares & catalog_hits (from catalog endpoint)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS catalog_shares (
                        id          SERIAL PRIMARY KEY,
                        mnr_id      VARCHAR(20),
                        member_name VARCHAR(200),
                        platform    VARCHAR(30)  NOT NULL DEFAULT 'unknown',
                        language    VARCHAR(10)  DEFAULT 'english',
                        recipient_name    VARCHAR(200),
                        recipient_prefix  VARCHAR(10),
                        share_ref_code    VARCHAR(60) UNIQUE,
                        ip_address  VARCHAR(45),
                        user_agent  TEXT,
                        shared_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS catalog_hits (
                        id              SERIAL PRIMARY KEY,
                        share_ref_code  VARCHAR(60),
                        ip_address      VARCHAR(45),
                        user_agent      TEXT,
                        referrer        VARCHAR(500),
                        viewed_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_catalog_shares_mnr ON catalog_shares (mnr_id)
                """))

                # 4.4 partner_support_requests & partner_stock_items (from partner_auth)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS partner_support_requests (
                        id SERIAL PRIMARY KEY,
                        partner_id INTEGER NOT NULL,
                        partner_code VARCHAR(20),
                        subject VARCHAR(200) NOT NULL,
                        category VARCHAR(50) DEFAULT 'other',
                        description TEXT NOT NULL,
                        status VARCHAR(20) DEFAULT 'OPEN',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        assign_to VARCHAR(20) DEFAULT 'self',
                        service_dept_staff_id INTEGER,
                        company_support_requested BOOLEAN DEFAULT FALSE,
                        customer_name VARCHAR(200),
                        customer_phone VARCHAR(20)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS partner_stock_items (
                        id SERIAL PRIMARY KEY,
                        partner_id INTEGER NOT NULL,
                        item_type VARCHAR(20) NOT NULL DEFAULT 'catalog',
                        stock_item_id INTEGER,
                        item_name VARCHAR(200) NOT NULL,
                        item_code VARCHAR(100),
                        unit_of_measure VARCHAR(20) DEFAULT 'PCS',
                        hsn_code VARCHAR(20),
                        opening_qty NUMERIC(10,2) DEFAULT 0,
                        opening_qty_set_at TIMESTAMP,
                        reorder_level NUMERIC(10,2) DEFAULT 0,
                        selling_price NUMERIC(10,2),
                        is_active BOOLEAN DEFAULT TRUE,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS partner_stock_adjustments (
                        id SERIAL PRIMARY KEY,
                        partner_id INTEGER NOT NULL,
                        partner_stock_item_id INTEGER NOT NULL,
                        adj_type VARCHAR(30) NOT NULL,
                        qty NUMERIC(10,2) NOT NULL,
                        reason VARCHAR(200),
                        notes TEXT,
                        ref_doc_type VARCHAR(50),
                        ref_doc_id INTEGER,
                        ref_doc_number VARCHAR(100),
                        created_by VARCHAR(100),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))

                # 4.5 pdf_canonical_routes (from sidebar_sync_service)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS pdf_canonical_routes (
                        id SERIAL PRIMARY KEY,
                        route_path TEXT NOT NULL UNIQUE,
                        section_id TEXT NOT NULL,
                        section_title TEXT,
                        section_order INTEGER DEFAULT 1,
                        subsection_title TEXT,
                        is_submenu BOOLEAN DEFAULT FALSE,
                        parent_section TEXT,
                        menu_name TEXT,
                        menu_icon TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))

                # 4.6 staff_employees.freelancer_access_mode (from main.py import block)
                _fa_col_exists = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='staff_employees' AND column_name='freelancer_access_mode'
                    )
                """)).scalar()
                if not _fa_col_exists:
                    conn.execute(text("""
                        ALTER TABLE staff_employees 
                        ADD COLUMN freelancer_access_mode VARCHAR(32) DEFAULT 'default'
                    """))

                # 4.7 crm_lead_handlers & members (from main.py import block)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS crm_lead_handlers (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER NOT NULL,
                        department_id INTEGER NOT NULL,
                        category_id INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata') NOT NULL,
                        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata'),
                        created_by_id INTEGER,
                        CONSTRAINT uq_crm_lead_handler_co_dept_cat UNIQUE (company_id, department_id, category_id)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS crm_lead_handler_members (
                        id SERIAL PRIMARY KEY,
                        handler_id INTEGER NOT NULL REFERENCES crm_lead_handlers(id) ON DELETE CASCADE,
                        employee_id INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata') NOT NULL,
                        created_by_id INTEGER,
                        CONSTRAINT uq_crm_lead_handler_member UNIQUE (handler_id, employee_id)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS crm_lead_handler_audits (
                        id SERIAL PRIMARY KEY,
                        handler_id INTEGER,
                        action VARCHAR(50) NOT NULL,
                        details TEXT,
                        performed_by_id INTEGER,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata') NOT NULL
                    )
                """))

                # 4.8 veh_models, veh_model_colors, veh_color_batches, veh_color_in
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS veh_models (
                        id          SERIAL PRIMARY KEY,
                        company_id  INTEGER NOT NULL,
                        name        VARCHAR(100) NOT NULL,
                        is_active   BOOLEAN DEFAULT TRUE,
                        sort_order  INTEGER DEFAULT 0,
                        created_at  TIMESTAMP DEFAULT NOW(),
                        updated_at  TIMESTAMP DEFAULT NOW(),
                        created_by  VARCHAR(20),
                        UNIQUE (company_id, name)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS veh_model_colors (
                        id          SERIAL PRIMARY KEY,
                        model_id    INTEGER NOT NULL REFERENCES veh_models(id) ON DELETE CASCADE,
                        color_name  VARCHAR(50) NOT NULL,
                        is_active   BOOLEAN DEFAULT TRUE,
                        sort_order  INTEGER DEFAULT 0,
                        UNIQUE (model_id, color_name)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS veh_color_batches (
                        id            SERIAL PRIMARY KEY,
                        company_id    INTEGER NOT NULL,
                        batch_label   VARCHAR(100) NOT NULL,
                        batch_date    DATE NOT NULL,
                        batch_type    VARCHAR(20) DEFAULT 'purchase',
                        purchase_qty  INTEGER DEFAULT 0,
                        ref_no        VARCHAR(100),
                        sort_order    INTEGER DEFAULT 0,
                        is_active     BOOLEAN DEFAULT TRUE,
                        created_at    TIMESTAMP DEFAULT NOW(),
                        updated_at    TIMESTAMP DEFAULT NOW(),
                        created_by    VARCHAR(20)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS veh_color_in (
                        id          SERIAL PRIMARY KEY,
                        batch_id    INTEGER NOT NULL REFERENCES veh_color_batches(id) ON DELETE CASCADE,
                        model_id    INTEGER NOT NULL REFERENCES veh_models(id) ON DELETE CASCADE,
                        color_id    INTEGER NOT NULL REFERENCES veh_model_colors(id) ON DELETE CASCADE,
                        qty         INTEGER NOT NULL DEFAULT 0,
                        created_at  TIMESTAMP DEFAULT NOW(),
                        updated_at  TIMESTAMP DEFAULT NOW(),
                        created_by  VARCHAR(20),
                        UNIQUE (batch_id, model_id, color_id)
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS veh_color_out (
                        id           SERIAL PRIMARY KEY,
                        batch_id     INTEGER NOT NULL REFERENCES veh_color_batches(id) ON DELETE CASCADE,
                        model_id     INTEGER NOT NULL REFERENCES veh_models(id) ON DELETE CASCADE,
                        color_id     INTEGER NOT NULL REFERENCES veh_model_colors(id) ON DELETE CASCADE,
                        partner_id   INTEGER REFERENCES official_partners(id) ON DELETE SET NULL,
                        planned_qty  INTEGER DEFAULT 0,
                        sold_qty     INTEGER DEFAULT 0,
                        entry_date   DATE NOT NULL,
                        notes        VARCHAR(200),
                        created_at   TIMESTAMP DEFAULT NOW(),
                        updated_at   TIMESTAMP DEFAULT NOW(),
                        created_by   VARCHAR(20)
                    )
                """))

                # 4.9 crm_leads.first_payment_received_date
                _fpr_col_exists = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='crm_leads' AND column_name='first_payment_received_date'
                    )
                """)).scalar()
                if not _fpr_col_exists:
                    conn.execute(text("""
                        ALTER TABLE crm_leads 
                        ADD COLUMN first_payment_received_date DATE
                    """))

                # 4.10 official_partners Points System V2 columns
                conn.execute(text("""
                    ALTER TABLE official_partners 
                    ADD COLUMN IF NOT EXISTS cumulative_self_business_dvr NUMERIC(14, 2) DEFAULT 0 NOT NULL,
                    ADD COLUMN IF NOT EXISTS points_recovery_liability NUMERIC(12, 2) DEFAULT 0 NOT NULL,
                    ADD COLUMN IF NOT EXISTS is_business_activated BOOLEAN DEFAULT FALSE NOT NULL
                """))

                # 4.11 crm_leads Points System V2 & Direct Team Lead columns
                conn.execute(text("""
                    ALTER TABLE crm_leads 
                    ADD COLUMN IF NOT EXISTS points_evaluated_dvr NUMERIC(12, 2) DEFAULT 0.0 NOT NULL,
                    ADD COLUMN IF NOT EXISTS direct_team_lead_sponsor_id INTEGER,
                    ADD COLUMN IF NOT EXISTS direct_team_lead_points_awarded BOOLEAN DEFAULT FALSE NOT NULL,
                    ADD COLUMN IF NOT EXISTS direct_team_lead_points_awarded_at TIMESTAMP WITHOUT TIME ZONE
                """))

                # 4.12 vgk_self_business_points_accrual_ledger table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS vgk_self_business_points_accrual_ledger (
                        id SERIAL PRIMARY KEY,
                        partner_id INTEGER NOT NULL REFERENCES official_partners(id) ON DELETE CASCADE,
                        lead_id INTEGER NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
                        previous_lead_dvr NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        current_lead_dvr NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        incremental_dvr NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        partner_cumulative_dvr_before NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
                        partner_cumulative_dvr_after NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
                        milestones_crossed INTEGER NOT NULL DEFAULT 0,
                        points_awarded NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        carry_forward_volume NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        ledger_entry_id INTEGER,
                        transaction_type VARCHAR(30) NOT NULL DEFAULT 'ACCRUAL',
                        liability_offset_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_vgk_self_biz_partner ON vgk_self_business_points_accrual_ledger (partner_id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_vgk_self_biz_lead ON vgk_self_business_points_accrual_ledger (lead_id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_vgk_self_biz_created ON vgk_self_business_points_accrual_ledger (created_at)
                """))

                # 4.13 ev & purchase missing columns (safe synchronization)
                conn.execute(text("""
                    ALTER TABLE ev 
                    ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS specifications TEXT,
                    ADD COLUMN IF NOT EXISTS category VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS image_url VARCHAR(500),
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                """))

                conn.execute(text("""
                    ALTER TABLE purchase 
                    ADD COLUMN IF NOT EXISTS delivery_address TEXT,
                    ADD COLUMN IF NOT EXISTS admin_notes TEXT,
                    ADD COLUMN IF NOT EXISTS enhanced_coupon_id INTEGER,
                    ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(30),
                    ADD COLUMN IF NOT EXISTS original_price INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS verified_by_admin_id VARCHAR(20),
                    ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
                    ADD COLUMN IF NOT EXISTS delivery_date TIMESTAMP WITHOUT TIME ZONE,
                    ADD COLUMN IF NOT EXISTS verification_date TIMESTAMP WITHOUT TIME ZONE,
                    ADD COLUMN IF NOT EXISTS discount_amount INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS final_price INTEGER DEFAULT 0
                """))

                # 4.14 SaaS Phase 1 Foundation Migration (Authoritative Integration)
                saas_sql_file = _backend_dir / "migrations" / "add_saas_phase1_foundation_20260914.sql"
                if saas_sql_file.exists():
                    has_saas = conn.execute(text(
                        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'staff_company_memberships'"
                    )).scalar()
                    if has_saas:
                        logger.info("⏭️ SaaS Phase 1 Foundation migration already applied — skipping")
                    else:
                        logger.info(f"Executing SaaS Phase 1 Foundation migration from {saas_sql_file.name}...")
                        with open(saas_sql_file, "r", encoding="utf-8") as f:
                            saas_sql = f.read()
                        conn.execute(text(saas_sql))
                        logger.info("✅ SaaS Phase 1 Foundation migration executed successfully")
                else:
                    logger.warning(f"⚠️ SaaS Phase 1 SQL migration file not found at {saas_sql_file}")

                # 4.15 CRM Phone Identity Association & Provenance Tables (b8c9d0e1f2a3 / c9d0e1f2a3b4)
                logger.info("Executing CRM Phone Identity tables migration...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS crm_lead_phones (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        company_id INTEGER NOT NULL,
                        lead_id INTEGER NOT NULL,
                        phone_norm VARCHAR(15) NOT NULL,
                        phone_role VARCHAR(30) NOT NULL DEFAULT 'PRIMARY',
                        is_primary BOOLEAN NOT NULL DEFAULT TRUE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        verification_status VARCHAR(30) NOT NULL DEFAULT 'UNVERIFIED',
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        
                        CONSTRAINT fk_crm_lead_phones_lead 
                            FOREIGN KEY (lead_id) REFERENCES crm_leads(id) ON DELETE CASCADE,
                        CONSTRAINT fk_crm_lead_phones_tenant_company 
                            FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies(client_id, id) ON DELETE RESTRICT,
                        CONSTRAINT fk_crm_lead_phones_tenant 
                            FOREIGN KEY (tenant_id) REFERENCES platform_clients(id) ON DELETE RESTRICT,
                        CONSTRAINT uq_crm_lead_phones_association 
                            UNIQUE (tenant_id, company_id, lead_id, phone_norm)
                    );

                    CREATE INDEX IF NOT EXISTS idx_crm_lead_phones_lookup 
                    ON crm_lead_phones (tenant_id, company_id, phone_norm) 
                    WHERE (is_active = TRUE);

                    CREATE INDEX IF NOT EXISTS idx_crm_lead_phones_lead_id 
                    ON crm_lead_phones (lead_id);

                    CREATE TABLE IF NOT EXISTS crm_lead_phone_provenances (
                        id BIGSERIAL PRIMARY KEY,
                        phone_association_id BIGINT NOT NULL,
                        tenant_id INTEGER NOT NULL,
                        company_id INTEGER NOT NULL,
                        lead_id INTEGER NOT NULL,
                        source_field VARCHAR(50) NOT NULL,
                        raw_value VARCHAR(100),
                        source_channel VARCHAR(50) NOT NULL DEFAULT 'manual',
                        source_ref TEXT,
                        captured_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                        CONSTRAINT fk_crm_lead_phone_prov_assoc 
                            FOREIGN KEY (phone_association_id) REFERENCES crm_lead_phones(id) ON DELETE CASCADE,
                        CONSTRAINT fk_crm_lead_phone_prov_lead 
                            FOREIGN KEY (lead_id) REFERENCES crm_leads(id) ON DELETE CASCADE,
                        CONSTRAINT fk_crm_lead_phone_prov_company 
                            FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies(client_id, id) ON DELETE RESTRICT
                    );

                    CREATE INDEX IF NOT EXISTS idx_crm_lead_phone_prov_assoc 
                    ON crm_lead_phone_provenances (phone_association_id);

                    CREATE INDEX IF NOT EXISTS idx_crm_lead_phone_prov_lead 
                    ON crm_lead_phone_provenances (lead_id);

                    DO $body$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_crm_leads_tenant_company_id') THEN
                            ALTER TABLE crm_leads ADD CONSTRAINT uq_crm_leads_tenant_company_id UNIQUE (tenant_id, company_id, id);
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_crm_lead_phones_composite_id') THEN
                            ALTER TABLE crm_lead_phones ADD CONSTRAINT uq_crm_lead_phones_composite_id UNIQUE (id, tenant_id, company_id, lead_id);
                        END IF;
                    END $body$;
                """))
                logger.info("✅ CRM Phone Identity tables migration executed successfully")

                # 4.16 CRM Phone Identity Historical Backfill (non-destructive)
                phone_count = conn.execute(text("SELECT count(*) FROM crm_lead_phones")).scalar() or 0
                if phone_count == 0:
                    logger.info("Populating CRM phone identity tables from crm_leads...")
                    conn.execute(text("""
                        INSERT INTO crm_lead_phones (tenant_id, company_id, lead_id, phone_norm, phone_role, is_primary, is_active, verification_status, created_at, updated_at)
                        SELECT 
                            l.tenant_id,
                            l.company_id,
                            l.id,
                            CASE 
                                WHEN length(regexp_replace(l.phone, '\\D', '', 'g')) >= 10 
                                    THEN substring(regexp_replace(l.phone, '\\D', '', 'g') from length(regexp_replace(l.phone, '\\D', '', 'g')) - 9 for 10)
                                WHEN length(regexp_replace(l.phone, '\\D', '', 'g')) IN (8, 9) 
                                    THEN regexp_replace(l.phone, '\\D', '', 'g')
                                ELSE NULL
                            END AS phone_norm,
                            'PRIMARY',
                            TRUE,
                            TRUE,
                            'UNVERIFIED',
                            NOW(),
                            NOW()
                        FROM crm_leads l
                        WHERE l.phone IS NOT NULL 
                          AND length(regexp_replace(l.phone, '\\D', '', 'g')) >= 8
                          AND l.tenant_id IS NOT NULL
                        ON CONFLICT (tenant_id, company_id, lead_id, phone_norm) DO NOTHING;
                    """))

                    conn.execute(text("""
                        INSERT INTO crm_lead_phone_provenances (phone_association_id, tenant_id, company_id, lead_id, source_field, raw_value, source_channel, source_ref, captured_at)
                        SELECT 
                            p.id,
                            p.tenant_id,
                            p.company_id,
                            p.lead_id,
                            'phone',
                            l.phone,
                            COALESCE(l.source, 'crm_leads_backfill'),
                            'Phase 1 Migration Backfill',
                            NOW()
                        FROM crm_lead_phones p
                        JOIN crm_leads l ON p.lead_id = l.id
                        WHERE p.phone_role = 'PRIMARY'
                        ON CONFLICT DO NOTHING;
                    """))

                    conn.execute(text("""
                        INSERT INTO crm_lead_phones (tenant_id, company_id, lead_id, phone_norm, phone_role, is_primary, is_active, verification_status, created_at, updated_at)
                        SELECT 
                            l.tenant_id,
                            l.company_id,
                            l.id,
                            CASE 
                                WHEN length(regexp_replace(l.alternate_phone, '\\D', '', 'g')) >= 10 
                                    THEN substring(regexp_replace(l.alternate_phone, '\\D', '', 'g') from length(regexp_replace(l.alternate_phone, '\\D', '', 'g')) - 9 for 10)
                                WHEN length(regexp_replace(l.alternate_phone, '\\D', '', 'g')) IN (8, 9) 
                                    THEN regexp_replace(l.alternate_phone, '\\D', '', 'g')
                                ELSE NULL
                            END AS phone_norm,
                            'ALTERNATE',
                            FALSE,
                            TRUE,
                            'UNVERIFIED',
                            NOW(),
                            NOW()
                        FROM crm_leads l
                        WHERE l.alternate_phone IS NOT NULL 
                          AND length(regexp_replace(l.alternate_phone, '\\D', '', 'g')) >= 8
                          AND l.tenant_id IS NOT NULL
                        ON CONFLICT (tenant_id, company_id, lead_id, phone_norm) DO NOTHING;
                    """))

                    conn.execute(text("""
                        INSERT INTO crm_lead_phone_provenances (phone_association_id, tenant_id, company_id, lead_id, source_field, raw_value, source_channel, source_ref, captured_at)
                        SELECT 
                            p.id,
                            p.tenant_id,
                            p.company_id,
                            p.lead_id,
                            'alternate_phone',
                            l.alternate_phone,
                            COALESCE(l.source, 'crm_leads_backfill'),
                            'Phase 1 Migration Backfill',
                            NOW()
                        FROM crm_lead_phones p
                        JOIN crm_leads l ON p.lead_id = l.id
                        WHERE p.phone_role = 'ALTERNATE'
                        ON CONFLICT DO NOTHING;
                    """))
                    logger.info("✅ CRM Phone Identity backfill completed")
                else:
                    logger.info(f"⏭️ CRM Phone Identity tables already populated ({phone_count} associations)")

                # 4.14 GUC Committee Fields Migration
                guc_mig_file = _backend_dir / "migrations" / "add_guc_committee_fields_20260915.sql"
                if guc_mig_file.exists():
                    logger.info("Executing GUC committee fields migration (add_guc_committee_fields_20260915.sql)...")
                    sql_content = guc_mig_file.read_text(encoding="utf-8")
                    for statement in sql_content.split(";"):
                        cleaned_lines = [l for l in statement.splitlines() if not l.strip().startswith("--")]
                        stmt = "\n".join(cleaned_lines).strip()
                        if stmt:
                            conn.execute(text(stmt))
                    logger.info("✅ GUC committee fields migration executed successfully")

                # 4.15 GUC Idol Photo Migration
                idol_mig_file = _backend_dir / "migrations" / "add_idol_photo_to_community_registrations_20260916.sql"
                if idol_mig_file.exists():
                    logger.info("Executing GUC idol photo migration (add_idol_photo_to_community_registrations_20260916.sql)...")
                    sql_content = idol_mig_file.read_text(encoding="utf-8")
                    for statement in sql_content.split(";"):
                        cleaned_lines = [l for l in statement.splitlines() if not l.strip().startswith("--")]
                        stmt = "\n".join(cleaned_lines).strip()
                        if stmt:
                            conn.execute(text(stmt))
                    logger.info("✅ GUC idol photo migration executed successfully")

                # 4.16 CRM Lead Document Shares Audit Table (DC-DOC-SHARES-AUDIT-20260916)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS crm_lead_document_shares (
                        id SERIAL PRIMARY KEY,
                        lead_id INTEGER NOT NULL,
                        company_id INTEGER DEFAULT 4,
                        share_mode VARCHAR(50) NOT NULL DEFAULT 'whatsapp_attachments',
                        recipient_phone VARCHAR(50),
                        recipient_name VARCHAR(200),
                        recipient_role VARCHAR(100),
                        shared_by_staff_id INTEGER,
                        shared_by_staff_name VARCHAR(200),
                        doc_group VARCHAR(50),
                        doc_types JSONB,
                        doc_labels JSONB,
                        total_docs INTEGER DEFAULT 0,
                        sent_docs_count INTEGER DEFAULT 0,
                        failed_docs_count INTEGER DEFAULT 0,
                        custom_notes TEXT,
                        share_url TEXT,
                        status VARCHAR(50) DEFAULT 'completed',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS ix_crm_doc_shares_lead ON crm_lead_document_shares (lead_id);
                    CREATE INDEX IF NOT EXISTS ix_crm_doc_shares_staff ON crm_lead_document_shares (shared_by_staff_id);
                """))
                logger.info("✅ CRM lead document shares table verified/created")

                # 4.17 Vendor Master GST Certificate URL
                conn.execute(text("""
                    ALTER TABLE vendor_master ADD COLUMN IF NOT EXISTS gst_certificate_url TEXT;
                """))
                logger.info("✅ vendor_master.gst_certificate_url verified/added")

                # 4.18 VGK4U Career Designation Configs - Stage-Wise Personal Qualifying Files
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'vgk4u_career_designation_configs' 
                              AND column_name = 'stage_own_qualifying_files'
                        ) THEN
                            ALTER TABLE vgk4u_career_designation_configs
                            ADD COLUMN stage_own_qualifying_files INTEGER NOT NULL DEFAULT 0;
                        END IF;
                    END $$;

                    UPDATE vgk4u_career_designation_configs
                    SET stage_own_qualifying_files = CASE hierarchy_order
                            WHEN 0 THEN 0
                            WHEN 1 THEN 1
                            WHEN 2 THEN 3
                            WHEN 3 THEN 5
                            WHEN 4 THEN 7
                            ELSE 0
                        END,
                        required_own_qualifying_files = CASE hierarchy_order
                            WHEN 0 THEN 0
                            WHEN 1 THEN 1
                            WHEN 2 THEN 4
                            WHEN 3 THEN 9
                            WHEN 4 THEN 16
                            ELSE 0
                        END,
                        updated_at = NOW()
                    WHERE hierarchy_order IN (0, 1, 2, 3, 4);
                """))
                logger.info("✅ vgk4u_career_designation_configs.stage_own_qualifying_files verified/updated")

                # 4.19 Default assignment of VGK members & historical data backfill for staff-created members
                # Step 1: Assign unassigned VGK members whose registered_by_emp_code matches a staff employee
                upd1 = conn.execute(text("""
                    UPDATE official_partners op
                    SET assigned_staff_id = se.id,
                        assigned_by_id = se.id,
                        assigned_at = COALESCE(op.created_at, NOW())
                    FROM staff_employees se
                    WHERE op.category = 'VGK_TEAM'
                      AND op.assigned_staff_id IS NULL
                      AND UPPER(TRIM(op.registered_by_emp_code)) = UPPER(TRIM(se.emp_code));
                """))

                # Step 2: Assign unassigned VGK members created by a staff employee in vgk_points_ledger
                upd2 = conn.execute(text("""
                    WITH first_points AS (
                        SELECT DISTINCT ON (partner_id) partner_id, created_by
                        FROM vgk_points_ledger
                        WHERE created_by IS NOT NULL
                        ORDER BY partner_id, id ASC
                    )
                    UPDATE official_partners op
                    SET assigned_staff_id = se.id,
                        assigned_by_id = se.id,
                        assigned_at = COALESCE(op.created_at, NOW()),
                        registered_by_emp_code = COALESCE(NULLIF(TRIM(op.registered_by_emp_code), ''), se.emp_code)
                    FROM first_points fp
                    JOIN staff_employees se ON se.id = fp.created_by
                    WHERE op.category = 'VGK_TEAM'
                      AND op.id = fp.partner_id
                      AND op.assigned_staff_id IS NULL;
                """))
                logger.info(f"✅ VGK member staff assignment backfill complete: {upd1.rowcount} via reg_by code, {upd2.rowcount} via points creator")

                # 4.21 Synchronize Sales Incharge access for MR10036 (Anushka Karri) & MN10009 (Nandana)
                upd_sales_incharges = conn.execute(text("""
                    UPDATE staff_employees
                    SET role_id = (SELECT id FROM staff_roles WHERE role_code = 'sales_incharge'),
                        staff_type = 'SALES_INCHARGE',
                        designation = COALESCE(NULLIF(TRIM(designation), ''), 'Sales Incharge'),
                        data_companies = '[1, 2, 3, 4, 88, 92, 93, 94]'::jsonb,
                        admin_scope = 'SEGMENT_A',
                        updated_at = NOW()
                    WHERE emp_code IN ('MR10036', 'MN10009')
                      AND (role_id != (SELECT id FROM staff_roles WHERE role_code = 'sales_incharge') OR staff_type != 'SALES_INCHARGE');
                """))
                if upd_sales_incharges.rowcount > 0:
                    logger.info("✅ MR10036 (Anushka Karri) & MN10009 (Nandana) synchronized to Sales Incharge")

                # 4.22 Ensure recharge_transactions unified services columns (DTH, FASTag, Electricity, Gas)
                conn.execute(text("""
                    ALTER TABLE recharge_transactions ADD COLUMN IF NOT EXISTS service_type VARCHAR DEFAULT 'Mobile';
                    ALTER TABLE recharge_transactions ADD COLUMN IF NOT EXISTS value1 VARCHAR;
                    ALTER TABLE recharge_transactions ADD COLUMN IF NOT EXISTS value2 VARCHAR;
                """))
                logger.info("✅ recharge_transactions unified services columns ensured (service_type, value1, value2)")

                # 4.23 Ensure meta_capi_logs and system_feature_flags tables
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS meta_capi_logs (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER NOT NULL DEFAULT 1,
                        lead_id INTEGER NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
                        event_name VARCHAR(50) NOT NULL,
                        event_id VARCHAR(150) UNIQUE NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
                        request_payload JSONB,
                        response_payload TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        processed_at TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS system_feature_flags (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER NOT NULL DEFAULT 1,
                        vertical VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
                        feature_key VARCHAR(100) NOT NULL,
                        is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        updated_by_staff_id INTEGER REFERENCES staff_employees(id),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        CONSTRAINT uq_feature_flag UNIQUE (company_id, vertical, feature_key)
                    );
                """))
                logger.info("✅ meta_capi_logs and system_feature_flags tables ensured")

                # 4.24 Ensure digital_catalogs, catalog_sections, catalog_items, and catalog_lead_sends tables
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS digital_catalogs (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER NOT NULL REFERENCES associated_companies(id),
                        tenant_id INTEGER REFERENCES platform_clients(id) ON DELETE SET NULL,
                        category_id INTEGER,
                        segment_code VARCHAR(50) NOT NULL,
                        slug VARCHAR(120) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        subtitle VARCHAR(500),
                        summary TEXT,
                        hero_media_url VARCHAR(500),
                        catalog_type VARCHAR(50) NOT NULL DEFAULT 'SINGLE_PAGE',
                        status VARCHAR(20) NOT NULL DEFAULT 'published',
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_featured BOOLEAN NOT NULL DEFAULT FALSE,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        seo_title VARCHAR(255),
                        seo_description TEXT,
                        seo_keywords TEXT,
                        theme_config JSONB NOT NULL DEFAULT '{}'::jsonb,
                        default_language VARCHAR(10) NOT NULL DEFAULT 'en',
                        active_languages JSONB NOT NULL DEFAULT '["en"]'::jsonb,
                        pdf_brochure_url VARCHAR(500),
                        whatsapp_template_name VARCHAR(100),
                        version INTEGER NOT NULL DEFAULT 1,
                        created_by_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                        updated_by_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                        published_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT uq_digital_catalogs_company_slug UNIQUE (company_id, slug)
                    );
                    CREATE INDEX IF NOT EXISTS ix_digital_catalogs_company_status ON digital_catalogs(company_id, status);
                    CREATE INDEX IF NOT EXISTS ix_digital_catalogs_segment ON digital_catalogs(segment_code);
                    CREATE INDEX IF NOT EXISTS ix_digital_catalogs_category ON digital_catalogs(category_id);
                    CREATE INDEX IF NOT EXISTS ix_digital_catalogs_slug ON digital_catalogs(slug);

                    CREATE TABLE IF NOT EXISTS catalog_sections (
                        id SERIAL PRIMARY KEY,
                        catalog_id INTEGER NOT NULL REFERENCES digital_catalogs(id) ON DELETE CASCADE,
                        section_type VARCHAR(50) NOT NULL,
                        section_key VARCHAR(50) NOT NULL,
                        title VARCHAR(255),
                        subtitle VARCHAR(500),
                        content_variants JSONB NOT NULL DEFAULT '{}'::jsonb,
                        media_gallery JSONB NOT NULL DEFAULT '[]'::jsonb,
                        configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        is_visible BOOLEAN NOT NULL DEFAULT TRUE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS ix_catalog_sections_catalog_order ON catalog_sections(catalog_id, sort_order);

                    CREATE TABLE IF NOT EXISTS catalog_items (
                        id SERIAL PRIMARY KEY,
                        catalog_id INTEGER NOT NULL REFERENCES digital_catalogs(id) ON DELETE CASCADE,
                        item_type VARCHAR(50) NOT NULL DEFAULT 'PRODUCT',
                        source_entity_type VARCHAR(50),
                        source_entity_id INTEGER,
                        item_code VARCHAR(50),
                        title VARCHAR(255) NOT NULL,
                        subtitle VARCHAR(500),
                        specifications JSONB NOT NULL DEFAULT '[]'::jsonb,
                        pricing JSONB NOT NULL DEFAULT '{}'::jsonb,
                        media_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
                        video_url VARCHAR(500),
                        content_variants JSONB NOT NULL DEFAULT '{}'::jsonb,
                        badges JSONB NOT NULL DEFAULT '[]'::jsonb,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        is_featured BOOLEAN NOT NULL DEFAULT FALSE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS ix_catalog_items_catalog_order ON catalog_items(catalog_id, sort_order);

                    CREATE TABLE IF NOT EXISTS catalog_lead_sends (
                        id SERIAL PRIMARY KEY,
                        catalog_id INTEGER NOT NULL REFERENCES digital_catalogs(id) ON DELETE CASCADE,
                        lead_id INTEGER REFERENCES crm_leads(id) ON DELETE SET NULL,
                        company_id INTEGER NOT NULL DEFAULT 4,
                        staff_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                        recipient_phone VARCHAR(20) NOT NULL,
                        recipient_name VARCHAR(200),
                        language_code VARCHAR(10) NOT NULL DEFAULT 'en',
                        delivery_channel VARCHAR(30) NOT NULL DEFAULT 'whatsapp',
                        delivery_method VARCHAR(30) NOT NULL DEFAULT 'web_link',
                        share_ref_code VARCHAR(64) UNIQUE NOT NULL,
                        whatsapp_message_id VARCHAR(255),
                        status VARCHAR(30) NOT NULL DEFAULT 'sent',
                        failure_reason TEXT,
                        view_count INTEGER NOT NULL DEFAULT 0,
                        first_viewed_at TIMESTAMP,
                        last_viewed_at TIMESTAMP,
                        sent_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS ix_catalog_sends_catalog ON catalog_lead_sends(catalog_id);
                    CREATE INDEX IF NOT EXISTS ix_catalog_sends_lead ON catalog_lead_sends(lead_id);
                    CREATE INDEX IF NOT EXISTS ix_catalog_sends_phone ON catalog_lead_sends(recipient_phone);
                    CREATE INDEX IF NOT EXISTS ix_catalog_sends_ref_code ON catalog_lead_sends(share_ref_code);
                """))
                logger.info("✅ digital_catalogs, catalog_sections, catalog_items, catalog_lead_sends tables ensured")

                # 4.25 mobile_device_sessions (Persistent Mobile Sessions & Token Rotation)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS mobile_device_sessions (
                        id SERIAL PRIMARY KEY,
                        staff_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
                        device_id VARCHAR(100) NOT NULL,
                        platform VARCHAR(20) NOT NULL,
                        refresh_token_hash VARCHAR(64) UNIQUE NOT NULL,
                        device_name VARCHAR(100),
                        app_version VARCHAR(30),
                        token_version INTEGER NOT NULL DEFAULT 1,
                        is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
                        expires_at TIMESTAMP NOT NULL,
                        last_used_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS ix_mobile_device_sessions_staff_id ON mobile_device_sessions(staff_id);
                    CREATE INDEX IF NOT EXISTS ix_mobile_device_sessions_device_id ON mobile_device_sessions(device_id);
                    CREATE INDEX IF NOT EXISTS ix_mobile_device_sessions_token_hash ON mobile_device_sessions(refresh_token_hash);
                    CREATE INDEX IF NOT EXISTS ix_mds_staff_active ON mobile_device_sessions(staff_id, is_revoked, expires_at);
                """))
                logger.info("✅ mobile_device_sessions table ensured")

                # 4.26 Direct team lead referral points schema & vgk_points_ledger constraint
                conn.execute(text("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS direct_team_lead_points_awarded BOOLEAN NOT NULL DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS direct_team_lead_points_awarded_at TIMESTAMP NULL;"))
                conn.execute(text("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS direct_team_lead_sponsor_id INTEGER REFERENCES official_partners(id) ON DELETE SET NULL;"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_leads_dtl_points ON crm_leads(direct_team_lead_points_awarded);"))
                conn.execute(text("ALTER TABLE vgk_points_ledger DROP CONSTRAINT IF EXISTS vgk_points_reason_check;"))
                conn.execute(text("""
                    ALTER TABLE vgk_points_ledger ADD CONSTRAINT vgk_points_reason_check CHECK (
                        reason_code IN (
                            'WELCOME_BONUS','ACTIVATION_BONUS','LOYAL_BONUS','BONANZA_REWARD',
                            'PRODUCT_DISCOUNT','COMMISSION_ADJUSTMENT','MANUAL_ADJUSTMENT',
                            'MIGRATION_BALANCE','CAMPAIGN_BONUS','AUTO_REFILL','COMPANY_ROYALTY',
                            'INCOME_EARNED','BONANZA_CASH_CREDIT','REFERRAL_BONUS','SIGNUP_BONUS',
                            'SOLAR_CIBIL_ADVANCE','ROYALTY_PAYOUT','REWARD_POINT_CONVERSION',
                            'BUSINESS_BONUS','BUSINESS_REVERSAL',
                            'ONBOARDING_V2','REGISTRATION_V2','REFERRAL_V2','ACTIVATION_V2',
                            'ACTIVATION_SPONSOR_V2','BUSINESS_V2','PAYOUT_DEBIT_V2',
                            'BUSINESS_REVERSAL_V2','LIABILITY_RECOVERY_V2','V2_ONBOARDING_GRANT',
                            'DIRECT_TEAM_LEAD_V2','DIRECT_TEAM_LEAD_REVERSAL_V2'
                        )
                    );
                """))
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_vgk_pts_direct_team_lead_v2
                    ON vgk_points_ledger (reference_id)
                    WHERE reference_type = 'CRM_LEAD' AND reason_code = 'DIRECT_TEAM_LEAD_V2';
                """))
                logger.info("✅ Direct team lead points schema & vgk_points_ledger constraint ensured")

        logger.info("✅ Feature-specific schema migrations complete")
        
        # 4.20 Staff cash balance zero adjustments as of 16-Sep-2026
        try:
            from scripts.apply_staff_cash_balance_zero_adjustment import apply_zero_balance_adjustments
            apply_zero_balance_adjustments()
            logger.info("✅ Staff cash balance zero adjustments verified/applied")
        except Exception as e:
            logger.warning(f"⚠️ Staff cash balance zero adjustments notice: {e}")

        # 4.24 Seed default digital catalogs for all 8 verticals
        try:
            from scripts.seed_digital_catalogs import seed_default_catalogs
            seed_default_catalogs()
            logger.info("✅ Digital catalog default seed data verified/applied")
        except Exception as e:
            logger.warning(f"⚠️ Digital catalog seed notice: {e}")
    except Exception as e:
        logger.error(f"❌ Feature migrations failed: {e}")
        sys.exit(1)

    # 5. Pre-Deployment Schema Compatibility Gate & Architectural Invariant Check
    try:
        logger.info("Running pre-deployment schema compatibility gate...")
        with engine.connect() as conn:
            # Check 1: staff_employees columns
            staff_cols = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'staff_employees' AND column_name IN ('tenant_id', 'token_version')
            """)).fetchall()
            found_staff_cols = {r[0] for r in staff_cols}
            if 'tenant_id' not in found_staff_cols or 'token_version' not in found_staff_cols:
                raise RuntimeError(f"Gate Failed: staff_employees missing required columns. Found: {found_staff_cols}")

            # Check 2: crm_leads column
            crm_cols = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'crm_leads' AND column_name = 'tenant_id'
            """)).fetchall()
            if not crm_cols:
                raise RuntimeError("Gate Failed: crm_leads missing tenant_id column")

            # Check 3: required tables exist
            required_tables = ['staff_company_memberships', 'crm_lead_phones', 'crm_lead_phone_provenances', 'mobile_device_sessions']
            res_tbls = conn.execute(text(f"""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ({', '.join(repr(t) for t in required_tables)})
            """)).fetchall()
            found_tbls = {r[0] for r in res_tbls}
            missing_tbls = set(required_tables) - found_tbls
            if missing_tbls:
                raise RuntimeError(f"Gate Failed: Missing required tables: {missing_tbls}")

            # Check 4: no unexpected NULLs in tenant_id
            null_staff = conn.execute(text("SELECT count(*) FROM staff_employees WHERE tenant_id IS NULL")).scalar()
            if null_staff > 0:
                raise RuntimeError(f"Gate Failed: Found {null_staff} staff_employees records with NULL tenant_id")

            null_leads = conn.execute(text("SELECT count(*) FROM crm_leads WHERE tenant_id IS NULL")).scalar()
            if null_leads > 0:
                raise RuntimeError(f"Gate Failed: Found {null_leads} crm_leads records with NULL tenant_id")

            logger.info("✅ Pre-deployment schema compatibility gate passed: all invariants satisfied")
    except Exception as e:
        logger.critical(f"❌ Schema compatibility gate failed: {e}")
        sys.exit(1)
        
    logger.info("==================================================")
    logger.info("All Migrations Verified / Applied Successfully")
    logger.info("==================================================")

if __name__ == "__main__":
    run_migrations()
