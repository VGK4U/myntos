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

        logger.info("✅ Feature-specific schema migrations complete")
    except Exception as e:
        logger.error(f"❌ Feature migrations failed: {e}")
        sys.exit(1)
        
    logger.info("==================================================")
    logger.info("All Migrations Verified / Applied Successfully")
    logger.info("==================================================")

if __name__ == "__main__":
    run_migrations()
