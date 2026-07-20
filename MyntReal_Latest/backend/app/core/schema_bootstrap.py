"""
Schema Bootstrap - DC Protocol Columns
Ensures job handler metadata columns exist in all environments
Runs idempotently on application startup

This file ensures production-safe deployments by creating schema columns
if they don't exist, without requiring manual ALTER TABLE execution.
"""

import logging
from sqlalchemy import text
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def bootstrap_background_jobs_schema():
    """
    DC Protocol: Ensure job handler metadata columns exist
    Idempotent - safe to run multiple times
    Runs on application startup to ensure schema is ready in ALL environments
    """
    db = SessionLocal()
    try:
        # Check which columns already exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='background_jobs' 
            AND column_name IN ('job_handler_module', 'job_handler_function', 'scheduler_job_id', 'last_scheduler_attempt')
        """))
        existing = {row[0] for row in result.fetchall()}
        
        columns_to_add = []
        if 'job_handler_module' not in existing:
            columns_to_add.append("ADD COLUMN job_handler_module VARCHAR(255)")
        if 'job_handler_function' not in existing:
            columns_to_add.append("ADD COLUMN job_handler_function VARCHAR(100)")
        if 'scheduler_job_id' not in existing:
            columns_to_add.append("ADD COLUMN scheduler_job_id VARCHAR(150)")
        if 'last_scheduler_attempt' not in existing:
            columns_to_add.append("ADD COLUMN last_scheduler_attempt TIMESTAMP WITH TIME ZONE")
        
        if columns_to_add:
            # DC: Add missing columns (idempotent)
            alter_sql = f"ALTER TABLE background_jobs {', '.join(columns_to_add)}"
            db.execute(text(alter_sql))
            db.commit()
            logger.info(f"[SCHEMA BOOTSTRAP] ✅ Added {len(columns_to_add)} DC Protocol column(s) to background_jobs")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ All DC Protocol columns already exist")
            
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to bootstrap schema: {e}")
        raise
    finally:
        db.close()


def backfill_job_handler_metadata():
    """
    DC Protocol: Backfill handler metadata for existing jobs
    Maps legacy job_type to handler module/function
    Ensures durable retry works for ALL jobs (not just new ones)
    """
    from app.services.background_job_service import BackgroundJobService
    
    db = SessionLocal()
    try:
        # Find jobs missing handler metadata
        result = db.execute(text("""
            SELECT id, job_type 
            FROM background_jobs 
            WHERE job_handler_module IS NULL 
            OR job_handler_function IS NULL
        """))
        jobs_to_backfill = result.fetchall()
        
        if not jobs_to_backfill:
            logger.info("[SCHEMA BOOTSTRAP] ✅ No jobs need handler metadata backfill")
            return
        
        logger.info(f"[SCHEMA BOOTSTRAP] Backfilling handler metadata for {len(jobs_to_backfill)} job(s)")
        
        backfilled_count = 0
        for job_id, job_type in jobs_to_backfill:
            handler_info = BackgroundJobService.JOB_HANDLER_REGISTRY.get(job_type)
            if handler_info:
                db.execute(text("""
                    UPDATE background_jobs 
                    SET job_handler_module = :module, job_handler_function = :function 
                    WHERE id = :job_id
                """), {
                    'module': handler_info['module'],
                    'function': handler_info['function'],
                    'job_id': job_id
                })
                backfilled_count += 1
            else:
                logger.warning(
                    f"[SCHEMA BOOTSTRAP] Job {job_id} has unknown job_type '{job_type}', "
                    f"skipping backfill (add to JOB_HANDLER_REGISTRY if needed)"
                )
        
        db.commit()
        logger.info(f"[SCHEMA BOOTSTRAP] ✅ Backfilled handler metadata for {backfilled_count} job(s)")
        
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to backfill handler metadata: {e}")
        raise
    finally:
        db.close()


def bootstrap_sfms_credit_tables():
    """
    DC Protocol: Create SFMS Credit System tables if they don't exist
    Idempotent - safe to run multiple times
    Creates: accounts_payable_schedule, accounts_receivable_schedule, 
             credit_aging_snapshots, payment_transactions
    """
    db = SessionLocal()
    try:
        tables_created = []
        
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('accounts_payable_schedule', 'accounts_receivable_schedule', 
                              'credit_aging_snapshots', 'payment_transactions')
        """))
        existing_tables = {row[0] for row in result.fetchall()}
        
        if 'accounts_payable_schedule' not in existing_tables:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS accounts_payable_schedule (
                    id SERIAL PRIMARY KEY,
                    schedule_number VARCHAR(30) UNIQUE NOT NULL,
                    transaction_id INTEGER REFERENCES vendor_transaction_header(id),
                    vendor_id INTEGER REFERENCES vendor_master(id),
                    company_id INTEGER REFERENCES associated_companies(id) NOT NULL,
                    scheduled_amount NUMERIC(15, 2) NOT NULL,
                    paid_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    balance_amount NUMERIC(15, 2) NOT NULL,
                    due_date DATE NOT NULL,
                    payment_date DATE,
                    payment_mode VARCHAR(20),
                    payment_reference VARCHAR(100),
                    bank_reference VARCHAR(100),
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                    is_overdue BOOLEAN DEFAULT FALSE,
                    reminder_count INTEGER DEFAULT 0,
                    last_reminder_date DATE,
                    narration TEXT,
                    wvv_hash VARCHAR(64),
                    created_by_id INTEGER REFERENCES staff_employees(id),
                    paid_by_id INTEGER REFERENCES staff_employees(id),
                    ledger_entry_id INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT ap_schedule_status_check CHECK (status IN ('PENDING', 'PARTIAL_PAID', 'FULLY_PAID', 'OVERDUE', 'CANCELLED'))
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ap_schedule_due_date ON accounts_payable_schedule(due_date)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ap_schedule_status ON accounts_payable_schedule(status)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ap_schedule_company ON accounts_payable_schedule(company_id)"))
            tables_created.append('accounts_payable_schedule')
        
        if 'accounts_receivable_schedule' not in existing_tables:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS accounts_receivable_schedule (
                    id SERIAL PRIMARY KEY,
                    schedule_number VARCHAR(30) UNIQUE NOT NULL,
                    invoice_id INTEGER REFERENCES generated_invoices(id),
                    party_type VARCHAR(20) NOT NULL,
                    party_id INTEGER,
                    party_name VARCHAR(200) NOT NULL,
                    company_id INTEGER REFERENCES associated_companies(id) NOT NULL,
                    scheduled_amount NUMERIC(15, 2) NOT NULL,
                    received_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    balance_amount NUMERIC(15, 2) NOT NULL,
                    due_date DATE NOT NULL,
                    receipt_date DATE,
                    payment_mode VARCHAR(20),
                    payment_reference VARCHAR(100),
                    bank_reference VARCHAR(100),
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                    is_overdue BOOLEAN DEFAULT FALSE,
                    reminder_count INTEGER DEFAULT 0,
                    last_reminder_date DATE,
                    narration TEXT,
                    wvv_hash VARCHAR(64),
                    created_by_id INTEGER REFERENCES staff_employees(id),
                    received_by_id INTEGER REFERENCES staff_employees(id),
                    ledger_entry_id INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT ar_schedule_status_check CHECK (status IN ('PENDING', 'PARTIAL_RECEIVED', 'FULLY_RECEIVED', 'OVERDUE', 'CANCELLED')),
                    CONSTRAINT ar_schedule_party_type_check CHECK (party_type IN ('CUSTOMER', 'VENDOR', 'COMPANY', 'MNR_USER', 'OTHER'))
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ar_schedule_due_date ON accounts_receivable_schedule(due_date)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ar_schedule_status ON accounts_receivable_schedule(status)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ar_schedule_company ON accounts_receivable_schedule(company_id)"))
            tables_created.append('accounts_receivable_schedule')
        
        if 'credit_aging_snapshots' not in existing_tables:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS credit_aging_snapshots (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER REFERENCES associated_companies(id) NOT NULL,
                    credit_type VARCHAR(20) NOT NULL,
                    party_type VARCHAR(20),
                    party_id INTEGER,
                    party_name VARCHAR(200),
                    snapshot_date DATE NOT NULL,
                    bucket_current NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    bucket_1_30 NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    bucket_31_60 NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    bucket_61_90 NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    bucket_90_plus NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    total_outstanding NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    total_overdue NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    transaction_count INTEGER DEFAULT 0,
                    overdue_count INTEGER DEFAULT 0,
                    avg_days_outstanding INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT aging_credit_type_check CHECK (credit_type IN ('PAYABLE', 'RECEIVABLE'))
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_aging_company_date ON credit_aging_snapshots(company_id, snapshot_date)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_aging_credit_type ON credit_aging_snapshots(credit_type)"))
            tables_created.append('credit_aging_snapshots')
        
        if 'payment_transactions' not in existing_tables:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id SERIAL PRIMARY KEY,
                    transaction_number VARCHAR(30) UNIQUE NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    company_id INTEGER REFERENCES associated_companies(id) NOT NULL,
                    source_type VARCHAR(30) NOT NULL,
                    source_id INTEGER NOT NULL,
                    schedule_id INTEGER,
                    party_type VARCHAR(20) NOT NULL,
                    party_id INTEGER,
                    party_name VARCHAR(200) NOT NULL,
                    transaction_date DATE NOT NULL,
                    amount NUMERIC(15, 2) NOT NULL,
                    payment_mode VARCHAR(20) NOT NULL,
                    payment_reference VARCHAR(100),
                    bank_name VARCHAR(200),
                    bank_reference VARCHAR(100),
                    cheque_number VARCHAR(20),
                    cheque_date DATE,
                    narration TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
                    created_by_id INTEGER REFERENCES staff_employees(id),
                    ledger_entry_id INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT payment_txn_type_check CHECK (transaction_type IN ('PAYMENT_TO_VENDOR', 'RECEIPT_FROM_CUSTOMER', 'ADVANCE_PAYMENT', 'ADVANCE_RECEIPT', 'REFUND_TO_CUSTOMER', 'REFUND_FROM_VENDOR')),
                    CONSTRAINT payment_source_type_check CHECK (source_type IN ('VENDOR_TRANSACTION', 'INVOICE', 'FUND_ALLOCATION', 'OTHER')),
                    CONSTRAINT payment_party_type_check CHECK (party_type IN ('VENDOR', 'CUSTOMER', 'COMPANY', 'MNR_USER', 'EMPLOYEE', 'OTHER'))
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_payment_txn_date ON payment_transactions(transaction_date)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_payment_txn_company ON payment_transactions(company_id)"))
            tables_created.append('payment_transactions')
        
        if tables_created:
            db.commit()
            logger.info(f"[SCHEMA BOOTSTRAP] ✅ Created SFMS Credit tables: {', '.join(tables_created)}")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ All SFMS Credit tables already exist")
            
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to bootstrap SFMS Credit tables: {e}")
    finally:
        db.close()


def bootstrap_sfms_seed_data():
    """
    DC Protocol: Seed minimal SFMS test data if tables are empty
    Idempotent - only seeds if no data exists
    Creates: companies, vendors, stock items, pricing config
    Each table is committed independently for resilience
    """
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM associated_companies"))
        company_count = result.scalar()
        
        if company_count == 0:
            try:
                db.execute(text("""
                    INSERT INTO associated_companies (company_code, company_name, company_type, address, city, state, pincode, gst_number, pan_number, receipt_prefix, invoice_prefix, receipt_counter, invoice_counter, is_book_keeper, is_active, created_at, updated_at)
                    VALUES 
                    ('MYNT001', 'Mynt Real LLP', 'PARENT', 'Test Address, Bangalore', 'Bangalore', 'Karnataka', '560001', '29AADCM1234A1Z5', 'AADCM1234A', 'RCP', 'INV', 1, 1, false, true, NOW(), NOW()),
                    ('MNR001', 'MNR Energy Pvt Ltd', 'SUBSIDIARY', 'Energy Office, Mumbai', 'Mumbai', 'Maharashtra', '400001', '27AADCM5678B1Z5', 'AADCM5678B', 'RCP', 'INV', 1, 1, false, true, NOW(), NOW())
                """))
                db.commit()
                logger.info("[SCHEMA BOOTSTRAP] ✅ Seeded associated_companies with test data")
            except Exception as e:
                db.rollback()
                logger.error(f"[SCHEMA BOOTSTRAP] ⚠️ Companies seed failed: {e}")
        
        result = db.execute(text("SELECT COUNT(*) FROM vendor_master"))
        vendor_count = result.scalar()
        
        if vendor_count == 0:
            try:
                db.execute(text("""
                    INSERT INTO vendor_master (vendor_code, vendor_name, vendor_type, contact_person, phone, email, address, city, state, pincode, gst_number, pan_number, credit_limit, credit_days, applicable_companies, is_active, created_at, updated_at)
                    VALUES 
                    ('VND001', 'Test Vendor Pvt Ltd', 'PRODUCT', 'John Doe', '9876543210', 'vendor@test.com', 'Vendor Address', 'Bangalore', 'Karnataka', '560001', '29AADCV1234A1Z5', 'AADCV1234A', 100000, 30, '[1, 2]', true, NOW(), NOW()),
                    ('VND002', 'EV Parts Supplier', 'BOTH', 'Jane Smith', '9876543211', 'evparts@test.com', 'EV Park', 'Chennai', 'Tamil Nadu', '600001', '33AADCV5678B1Z5', 'AADCV5678B', 200000, 45, '[1]', true, NOW(), NOW())
                """))
                db.commit()
                logger.info("[SCHEMA BOOTSTRAP] ✅ Seeded vendor_master with test data")
            except Exception as e:
                db.rollback()
                logger.error(f"[SCHEMA BOOTSTRAP] ⚠️ Vendors seed failed: {e}")
        
        result = db.execute(text("SELECT COUNT(*) FROM stock_item_master"))
        stock_count = result.scalar()
        
        if stock_count == 0:
            try:
                db.execute(text("""
                    INSERT INTO stock_item_master (item_code, item_name, item_category, description, unit_of_measure, hsn_code, default_gst_rate, reorder_level, purchase_rate, selling_rate, is_active, created_at, updated_at)
                    VALUES 
                    ('STK001', 'EV Battery Pack', 'PRODUCT', 'Lithium-ion battery pack for EVs', 'UNIT', '8507', 18.00, 10, 40000, 45000, true, NOW(), NOW()),
                    ('STK002', 'EV Motor Assembly', 'SPARE_PART', 'Complete motor assembly unit', 'PCS', '8501', 18.00, 5, 30000, 35000, true, NOW(), NOW()),
                    ('STK003', 'Charging Cable', 'ACCESSORY', 'Type-2 EV charging cable', 'PCS', '8544', 18.00, 20, 2000, 2500, true, NOW(), NOW())
                """))
                db.commit()
                logger.info("[SCHEMA BOOTSTRAP] ✅ Seeded stock_item_master with test data")
            except Exception as e:
                db.rollback()
                logger.error(f"[SCHEMA BOOTSTRAP] ⚠️ Stock items seed failed: {e}")
        
        result = db.execute(text("SELECT id FROM associated_companies LIMIT 1"))
        company_row = result.fetchone()
        company_id = company_row[0] if company_row else None
        
        if company_id:
            result = db.execute(text("SELECT COUNT(*) FROM pricing_configuration"))
            pricing_count = result.scalar()
            
            if pricing_count == 0:
                try:
                    db.execute(text(f"""
                        INSERT INTO pricing_configuration (company_id, config_type, default_markup_pct, incentive_pct, allow_below_cost, min_markup_pct, max_markup_pct, is_active, created_at, updated_at)
                        VALUES 
                        ({company_id}, 'GENERAL', 20.00, 5.00, false, 10.00, 50.00, true, NOW(), NOW())
                    """))
                    db.commit()
                    logger.info("[SCHEMA BOOTSTRAP] ✅ Seeded pricing_configuration with test data")
                except Exception as e:
                    db.rollback()
                    logger.error(f"[SCHEMA BOOTSTRAP] ⚠️ Pricing config seed failed: {e}")
            
            result = db.execute(text("SELECT COUNT(*) FROM income_source_types"))
            income_source_count = result.scalar()
            
            if income_source_count == 0:
                try:
                    db.execute(text(f"""
                        INSERT INTO income_source_types (source_code, source_name, description, is_active, applicable_companies, is_taxable, default_tax_rate, requires_receipt, requires_reference, display_order, created_at, updated_at)
                        VALUES 
                        ('SALES', 'Product Sales', 'Income from product sales', true, '[{company_id}]', true, 18.00, true, false, 1, NOW(), NOW()),
                        ('SERVICE', 'Service Revenue', 'Income from services rendered', true, '[{company_id}]', true, 18.00, true, false, 2, NOW(), NOW()),
                        ('REFERRAL', 'Referral Commission', 'Commission from referrals', true, '[{company_id}]', false, 0, false, false, 3, NOW(), NOW())
                    """))
                    db.commit()
                    logger.info("[SCHEMA BOOTSTRAP] ✅ Seeded income_source_types with test data")
                except Exception as e:
                    db.rollback()
                    logger.error(f"[SCHEMA BOOTSTRAP] ⚠️ Income source types seed failed: {e}")
        
        logger.info("[SCHEMA BOOTSTRAP] ✅ SFMS seed data check complete")
            
    except Exception as e:
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to seed SFMS data: {e}")
    finally:
        db.close()


def bootstrap_accounts_module_schema():
    """
    DC Protocol Accounts Module Schema Bootstrap
    - Adds destination routing columns to income_entries (additive, nullable)
    - Extends employee_fund_ledger CHECK constraints for OPENING_BALANCE
    - Creates company_account_ledger table for company-wise balance tracking
    Idempotent - safe to run multiple times
    """
    db = SessionLocal()
    try:
        # 1. Add destination columns to income_entries
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='income_entries'
            AND column_name IN ('destination_type', 'destination_company_id', 'destination_employee_id')
        """))
        existing_cols = {row[0] for row in result.fetchall()}

        cols_to_add = []
        if 'destination_type' not in existing_cols:
            cols_to_add.append("ADD COLUMN destination_type VARCHAR(20)")
        if 'destination_company_id' not in existing_cols:
            cols_to_add.append("ADD COLUMN destination_company_id INTEGER")
        if 'destination_employee_id' not in existing_cols:
            cols_to_add.append("ADD COLUMN destination_employee_id INTEGER")

        if cols_to_add:
            db.execute(text(f"ALTER TABLE income_entries {', '.join(cols_to_add)}"))
            db.commit()
            logger.info(f"[SCHEMA BOOTSTRAP] ✅ Added destination columns to income_entries")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ income_entries destination columns already exist")

        # 2. Extend employee_fund_ledger CHECK constraints for OPENING_BALANCE
        # pg_get_constraintdef() works on PostgreSQL 12+ (consrc was removed in PG12)
        chk_result = db.execute(text("""
            SELECT pg_get_constraintdef(oid) FROM pg_constraint
            WHERE conname = 'emp_fund_entry_type_check'
        """))
        row = chk_result.fetchone()
        if row and 'OPENING_BALANCE' not in str(row[0]):
            db.execute(text("ALTER TABLE employee_fund_ledger DROP CONSTRAINT IF EXISTS emp_fund_entry_type_check"))
            db.execute(text("""
                ALTER TABLE employee_fund_ledger ADD CONSTRAINT emp_fund_entry_type_check
                CHECK (entry_type IN ('FUND_RECEIVED','EXPENSE_MADE','TRANSFER_SENT','TRANSFER_RECEIVED','REFUND','ADJUSTMENT','OPENING_BALANCE'))
            """))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Extended emp_fund_entry_type_check with OPENING_BALANCE")

        chk_ref = db.execute(text("""
            SELECT pg_get_constraintdef(oid) FROM pg_constraint
            WHERE conname = 'emp_fund_ref_type_check'
        """))
        rrow = chk_ref.fetchone()
        if rrow and 'OPENING_BALANCE' not in str(rrow[0]):
            db.execute(text("ALTER TABLE employee_fund_ledger DROP CONSTRAINT IF EXISTS emp_fund_ref_type_check"))
            db.execute(text("""
                ALTER TABLE employee_fund_ledger ADD CONSTRAINT emp_fund_ref_type_check
                CHECK (reference_type IN ('FUND_ALLOCATION','EXPENSE_ENTRY','FUND_TRANSFER','ADJUSTMENT','OPENING_BALANCE','INCOME_ENTRY'))
            """))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Extended emp_fund_ref_type_check with OPENING_BALANCE, INCOME_ENTRY")

        # 3. Create company_account_ledger table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS company_account_ledger (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES associated_companies(id),
                transaction_date DATE NOT NULL,
                entry_type VARCHAR(20) NOT NULL,
                reference_type VARCHAR(30) NOT NULL,
                reference_id INTEGER,
                reference_number VARCHAR(50),
                debit_amount NUMERIC(15,2) NOT NULL DEFAULT 0,
                credit_amount NUMERIC(15,2) NOT NULL DEFAULT 0,
                balance NUMERIC(15,2) NOT NULL DEFAULT 0,
                narration TEXT,
                created_by_id INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_cal_company_id ON company_account_ledger(company_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_cal_txn_date ON company_account_ledger(transaction_date)"))
        db.commit()
        logger.info("[SCHEMA BOOTSTRAP] ✅ company_account_ledger table ready")

        # 4. Add income_entry_id FK column to employee_fund_ledger if missing
        result2 = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='employee_fund_ledger'
            AND column_name = 'income_entry_id'
        """))
        if not result2.fetchone():
            db.execute(text("ALTER TABLE employee_fund_ledger ADD COLUMN income_entry_id INTEGER"))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Added income_entry_id to employee_fund_ledger")

        # 5. Add REJECTED status to income_entries + rejected audit columns
        rej_col_result = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='income_entries'
            AND column_name IN ('rejected_by_id', 'rejected_at')
        """))
        existing_rej_cols = {row[0] for row in rej_col_result.fetchall()}
        rej_cols = []
        if 'rejected_by_id' not in existing_rej_cols:
            rej_cols.append("ADD COLUMN rejected_by_id INTEGER")
        if 'rejected_at' not in existing_rej_cols:
            rej_cols.append("ADD COLUMN rejected_at TIMESTAMP WITH TIME ZONE")
        if rej_cols:
            db.execute(text(f"ALTER TABLE income_entries {', '.join(rej_cols)}"))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Added rejected_by_id, rejected_at to income_entries")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ income_entries rejection columns already exist")

        income_chk = db.execute(text("""
            SELECT pg_get_constraintdef(oid) FROM pg_constraint
            WHERE conname = 'income_status_check'
        """))
        income_chk_row = income_chk.fetchone()
        if income_chk_row and 'REJECTED' not in str(income_chk_row[0]):
            db.execute(text("ALTER TABLE income_entries DROP CONSTRAINT IF EXISTS income_status_check"))
            db.execute(text("""
                ALTER TABLE income_entries ADD CONSTRAINT income_status_check
                CHECK (status IN ('PENDING', 'CONFIRMED', 'EXCEPTION_TALLY', 'ADJUSTMENT', 'TALLY_DONE', 'REJECTED', 'ESTIMATED'))
            """))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Extended income_status_check to include REJECTED")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ income_status_check already includes REJECTED")

    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ accounts_module_schema bootstrap failed: {e}")
    finally:
        db.close()


def drop_deal_unique_constraint():
    """
    DC Mar 2026: Drop the uq_lead_revenue_category unique constraint on crm_lead_deals.
    Previously, only one deal per lead+category was allowed. Business rule changed:
    multiple deals are allowed as long as only one is 'active' at a time.
    Idempotent - safe to run if constraint does not exist.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'crm_lead_deals'
            AND constraint_name = 'uq_lead_revenue_category'
            AND constraint_type = 'UNIQUE'
        """))
        if result.fetchone():
            db.execute(text("ALTER TABLE crm_lead_deals DROP CONSTRAINT uq_lead_revenue_category"))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Dropped uq_lead_revenue_category constraint — multiple deals per category now allowed")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ uq_lead_revenue_category already removed — no action needed")
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to drop deal unique constraint: {e}")
    finally:
        db.close()


def drop_marketplace_spares_sku_unique():
    """
    DC May 2026: Drop the old plain-sku unique constraint on marketplace_spares.
    Previously only one row per SKU was allowed globally. The business rule changed:
    the same SKU is now allowed across different companies (new composite unique
    uq_marketplace_spares_sku_company covers sku+company_id instead).
    Idempotent — safe to run if constraint is already gone.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'marketplace_spares'
            AND constraint_name = 'marketplace_spares_sku_key'
            AND constraint_type = 'UNIQUE'
            AND table_schema = 'public'
        """))
        if result.fetchone():
            db.execute(text("ALTER TABLE marketplace_spares DROP CONSTRAINT marketplace_spares_sku_key"))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Dropped marketplace_spares_sku_key — sku+company_id composite constraint now in effect")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ marketplace_spares_sku_key already removed — no action needed")
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to drop marketplace_spares_sku_key: {e}")
    finally:
        db.close()


def add_z_guru_id_column():
    """
    DC Mar 2026: Add z_guru_id column to crm_lead table.
    Z Guru = sponsor of the Guru (L2 upline from Ground Source).
    Auto-filled on the frontend when a Ground Source (MNR/VGK) is selected.
    Partners leave this blank. Idempotent.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'crm_leads' AND column_name = 'z_guru_id'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS z_guru_id VARCHAR(12)"))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ Added z_guru_id column to crm_leads")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ z_guru_id already exists — no action needed")
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ Failed to add z_guru_id: {e}")
    finally:
        db.close()


def bootstrap_whatsapp_config_schema():
    """
    Create WhatsApp Config tables and seed default auto-triggers.
    Idempotent — safe to run on every startup.
    """
    from app.core.database import engine, SessionLocal
    from sqlalchemy import text

    with engine.connect() as conn:
        # Create tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                slug VARCHAR(200) UNIQUE NOT NULL,
                segment VARCHAR(50) NOT NULL DEFAULT 'general',
                template_type VARCHAR(50) NOT NULL DEFAULT 'custom',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_system BOOLEAN NOT NULL DEFAULT FALSE,
                header_type VARCHAR(20) DEFAULT 'none',
                header_text VARCHAR(200),
                header_media_url TEXT,
                header_media_path TEXT,
                body_text TEXT NOT NULL,
                footer_text VARCHAR(200),
                buttons JSONB DEFAULT '[]',
                meta_template_name VARCHAR(200),
                meta_template_language VARCHAR(10) DEFAULT 'en',
                is_meta_approved BOOLEAN DEFAULT FALSE,
                created_by_staff_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                updated_by_staff_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_auto_triggers (
                id SERIAL PRIMARY KEY,
                event_key VARCHAR(100) UNIQUE NOT NULL,
                event_label VARCHAR(200) NOT NULL,
                event_category VARCHAR(50) NOT NULL,
                template_id INTEGER REFERENCES whatsapp_templates(id) ON DELETE SET NULL,
                is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                recipient_type VARCHAR(20) DEFAULT 'customer',
                delay_minutes INTEGER DEFAULT 0,
                updated_by_staff_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_campaigns (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                template_id INTEGER REFERENCES whatsapp_templates(id) ON DELETE RESTRICT,
                filters JSONB DEFAULT '{}',
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                total_recipients INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                delivered_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                pending_count INTEGER DEFAULT 0,
                daily_limit INTEGER DEFAULT 1000,
                sends_per_minute INTEGER DEFAULT 50,
                current_batch_day INTEGER DEFAULT 1,
                provider VARCHAR(50) DEFAULT 'META_WHATSAPP',
                notes TEXT,
                created_by_staff_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                paused_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_campaign_logs (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER REFERENCES whatsapp_campaigns(id) ON DELETE CASCADE,
                template_id INTEGER REFERENCES whatsapp_templates(id) ON DELETE SET NULL,
                phone VARCHAR(20) NOT NULL,
                lead_id INTEGER REFERENCES crm_leads(id) ON DELETE SET NULL,
                recipient_name VARCHAR(200),
                status VARCHAR(20) NOT NULL DEFAULT 'queued',
                wamid VARCHAR(200),
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                queued_at TIMESTAMP DEFAULT NOW(),
                sent_at TIMESTAMP,
                delivered_at TIMESTAMP,
                read_at TIMESTAMP,
                failed_at TIMESTAMP
            );
        """))

        # Indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_campaign_logs_campaign ON whatsapp_campaign_logs(campaign_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_campaign_logs_lead ON whatsapp_campaign_logs(lead_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_templates_segment ON whatsapp_templates(segment, is_active);"))
        conn.commit()

    # ── wa_inbox: incoming WhatsApp messages from Meta webhook ───────────────
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS wa_inbox (
                    id              SERIAL PRIMARY KEY,
                    wamid           VARCHAR(100) UNIQUE,
                    from_phone      VARCHAR(30) NOT NULL,
                    from_name       VARCHAR(200),
                    message_type    VARCHAR(30) DEFAULT 'text',
                    body_text       TEXT,
                    media_url       TEXT,
                    media_mime_type VARCHAR(100),
                    lead_id         INTEGER REFERENCES crm_leads(id) ON DELETE SET NULL,
                    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
                    replied         BOOLEAN NOT NULL DEFAULT FALSE,
                    replied_at      TIMESTAMP,
                    replied_by_id   INTEGER,
                    received_at     TIMESTAMP NOT NULL DEFAULT NOW(),
                    raw_payload     TEXT
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_inbox_phone     ON wa_inbox(from_phone);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_inbox_lead      ON wa_inbox(lead_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_inbox_read      ON wa_inbox(is_read);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_inbox_received  ON wa_inbox(received_at DESC);"))
            conn.commit()
            logger.info("[WA-INBOX] ✅ wa_inbox table ready")
    except Exception as e:
        logger.warning("[WA-INBOX] wa_inbox bootstrap error: %s", str(e))

    # ── wa_inbox CRM extension columns (DC Protocol Apr 2026) ─────────────────
    try:
        with engine.connect() as conn:
            for col_sql in [
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS dept_code VARCHAR(50)",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS assigned_to_emp_id INTEGER",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS target_date DATE",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS category_code VARCHAR(50)",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'new'",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS crm_lead_id INTEGER REFERENCES crm_leads(id) ON DELETE SET NULL",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS service_ticket_id INTEGER",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS assigned_notes TEXT",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS auto_replied BOOLEAN DEFAULT FALSE",
                "ALTER TABLE wa_inbox ADD COLUMN IF NOT EXISTS auto_replied_at TIMESTAMP",
            ]:
                conn.execute(text(col_sql))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_inbox_status   ON wa_inbox(status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_inbox_dept     ON wa_inbox(dept_code);"))
            conn.commit()
            logger.info("[WA-INBOX] ✅ wa_inbox CRM extension columns ready")
    except Exception as e:
        logger.warning("[WA-INBOX] wa_inbox CRM extension error: %s", str(e))

    # Add the not_answered status to crm_leads if constraint exists — wrap in try/catch
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name = 'crm_leads' AND constraint_type = 'CHECK'
                        AND constraint_name LIKE '%status%'
                    ) THEN
                        ALTER TABLE crm_leads DROP CONSTRAINT IF EXISTS valid_crm_lead_status;
                    END IF;
                END $$;
            """))
            conn.commit()
    except Exception as e:
        logger.warning("[WA-BOOTSTRAP] crm_leads status constraint update skipped: %s", str(e))

    # Seed default auto-triggers (upsert — safe to re-run)
    db = SessionLocal()
    try:
        from app.models.whatsapp import WhatsAppAutoTrigger
        default_triggers = [
            # CRM Lead events
            ("crm_lead_created",         "New Lead Created",             "crm",     "customer"),
            ("crm_status_contacted",     "Lead Status: Contacted",       "crm",     "customer"),
            ("crm_status_interested",    "Lead Status: Interested",      "crm",     "customer"),
            ("crm_status_qualified",     "Lead Status: Qualified",       "crm",     "customer"),
            ("crm_status_proposal",      "Lead Status: Proposal Sent",   "crm",     "customer"),
            ("crm_status_won",           "Lead Status: Won / Deal Closed","crm",    "customer"),
            ("crm_status_lost",          "Lead Status: Lost",            "crm",     "customer"),
            ("crm_status_not_answered",  "Lead Status: Not Answered",    "crm",     "customer"),
            ("crm_status_loan_process",  "Lead Status: Loan Processing", "crm",     "customer"),
            ("crm_status_on_hold",       "Lead Status: On Hold",         "crm",     "customer"),
            ("crm_status_processing",    "Lead Status: Processing",      "crm",     "customer"),
            ("crm_followup_scheduled",   "Follow-up Scheduled",          "crm",     "customer"),
            ("crm_transaction_created",  "Payment / Transaction Created","crm",     "customer"),
            ("crm_transaction_validated","Payment Validated",            "crm",     "customer"),
            # PO / Marketplace events
            ("po_confirmed",             "Purchase Order Confirmed",     "po",      "customer"),
            ("po_payment_received",      "PO Payment Received",          "po",      "customer"),
            ("po_dispatched",            "Order Dispatched",             "po",      "customer"),
            ("po_completed",             "Order Completed / Delivered",  "po",      "customer"),
            # Service ticket events
            ("ticket_raised",            "Service Ticket Raised",        "ticket",  "customer"),
            ("ticket_acknowledged",      "Ticket Acknowledged",          "ticket",  "customer"),
            ("ticket_resolved",          "Ticket Resolved / Work Done",  "ticket",  "customer"),
            ("ticket_closed",            "Ticket Closed",                "ticket",  "customer"),
            # Partner events
            ("partner_created",          "New Partner Created",          "partner", "customer"),
            # VGK Member events
            ("vgk_member_created",       "New VGK Member Registered",    "vgk",     "customer"),
            # ETC Training events
            ("etc_enrolled",             "ETC Student Enrolled",         "etc",     "customer"),
            ("etc_completed",            "ETC Training Completed",       "etc",     "customer"),
            # Staff events
            ("staff_morning_reminder",       "Staff Morning Reminder (Daily)",        "staff",   "staff"),
            # Lead Welcome messages (auto-sent on new lead creation)
            ("lead_welcome_general",         "Lead Welcome — General/Website/Social", "crm",     "customer"),
            ("lead_welcome_walkin",          "Lead Welcome — Walk-in via Partner",    "crm",     "customer"),
        ]
        _trig_seeded = 0
        _trig_existing = 0
        for event_key, event_label, event_category, recipient_type in default_triggers:
            existing = db.query(WhatsAppAutoTrigger).filter_by(event_key=event_key).first()
            if not existing:
                db.add(WhatsAppAutoTrigger(
                    event_key=event_key,
                    event_label=event_label,
                    event_category=event_category,
                    recipient_type=recipient_type,
                    is_enabled=False,
                    delay_minutes=0,
                ))
                logger.info("[WA-BOOTSTRAP] Seeded trigger: %s", event_key)
                _trig_seeded += 1
            else:
                _trig_existing += 1
        db.commit()
        logger.info("[WA-BOOTSTRAP] Trigger seed complete — %d new, %d already existed", _trig_seeded, _trig_existing)

        # ── Seed lead welcome templates (bilingual EN+TE) ──────────────────────
        from app.models.whatsapp import WhatsAppTemplate
        _COMPANY_NO = "+91 85858 52738"
        _WEBSITE    = "www.myntreal.com"

        _welcome_templates = [
            {
                "slug":       "lead_welcome_general",
                "name":       "Lead Welcome — General",
                "segment":    "general",
                "template_type": "text",
                "body_text":  (
                    "Hello {{name}}! 👋\n\n"
                    "Welcome to *Myntreal* — your trusted partner in Green Energy.\n\n"
                    "We specialize in:\n"
                    "☀️ *Solar Energy* — Rooftop & commercial solar systems\n"
                    "🛵 *Electric Vehicles (EV)* — Smart, eco-friendly mobility\n"
                    "💡 Energy-efficient solutions for homes & businesses\n\n"
                    "Our team will reach out shortly with personalized recommendations.\n\n"
                    "🌐 " + _WEBSITE + "\n"
                    "📞 Contact us: " + _COMPANY_NO + "\n\n"
                    "Thank you for choosing a greener future! 🌱\n"
                    "*— Team Myntreal*\n\n"
                    "———————————————\n"
                    "నమస్కారం {{name}}! 👋\n\n"
                    "*మింట్రియల్*కు స్వాగతం — మీ నమ్మకమైన గ్రీన్ ఎనర్జీ భాగస్వామి.\n\n"
                    "మేము ప్రత్యేకంగా అందించేవి:\n"
                    "☀️ *సోలార్ ఎనర్జీ* — ఇంటి & వాణిజ్య సోలార్ వ్యవస్థలు\n"
                    "🛵 *ఎలక్ట్రిక్ వాహనాలు (EV)* — స్మార్ట్, పర్యావరణహితమైన రవాణా\n"
                    "💡 ఇళ్ళు & వ్యాపారాలకు శక్తి ఆదా పరిష్కారాలు\n\n"
                    "మా బృందం మీకు త్వరలో వ్యక్తిగత సూచనలతో సంప్రదిస్తుంది.\n\n"
                    "🌐 " + _WEBSITE + "\n"
                    "📞 సంప్రదించండి: " + _COMPANY_NO + "\n\n"
                    "గ్రీన్ భవిష్యత్తు ఎంచుకున్నందుకు ధన్యవాదాలు! 🌱\n"
                    "*— టీమ్ మింట్రియల్*"
                ),
                "meta_template_name": "myntreal_lead_welcome_general",
                "meta_template_language": "en",
                "is_meta_approved": False,
            },
            {
                "slug":       "lead_welcome_walkin",
                "name":       "Lead Welcome — Walk-in via Partner",
                "segment":    "general",
                "template_type": "text",
                "body_text":  (
                    "Hello {{name}}! 👋\n\n"
                    "Welcome to *Myntreal* — your trusted partner in Green Energy.\n\n"
                    "We specialize in:\n"
                    "☀️ *Solar Energy* — Rooftop & commercial solar systems\n"
                    "🛵 *Electric Vehicles (EV)* — Smart, eco-friendly mobility\n"
                    "💡 Energy-efficient solutions for homes & businesses\n\n"
                    "Our team will reach out shortly with personalized recommendations.\n\n"
                    "🌐 " + _WEBSITE + "\n"
                    "📍 Showroom Contact: {{partner_phone}}\n"
                    "📞 Myntreal HQ: " + _COMPANY_NO + "\n\n"
                    "Thank you for choosing a greener future! 🌱\n"
                    "*— Team Myntreal*\n\n"
                    "———————————————\n"
                    "నమస్కారం {{name}}! 👋\n\n"
                    "*మింట్రియల్*కు స్వాగతం — మీ నమ్మకమైన గ్రీన్ ఎనర్జీ భాగస్వామి.\n\n"
                    "మేము ప్రత్యేకంగా అందించేవి:\n"
                    "☀️ *సోలార్ ఎనర్జీ* — ఇంటి & వాణిజ్య సోలార్ వ్యవస్థలు\n"
                    "🛵 *ఎలక్ట్రిక్ వాహనాలు (EV)* — స్మార్ట్, పర్యావరణహితమైన రవాణా\n"
                    "💡 ఇళ్ళు & వ్యాపారాలకు శక్తి ఆదా పరిష్కారాలు\n\n"
                    "మా బృందం మీకు త్వరలో వ్యక్తిగత సూచనలతో సంప్రదిస్తుంది.\n\n"
                    "🌐 " + _WEBSITE + "\n"
                    "📍 షోరూమ్ సంప్రదించండి: {{partner_phone}}\n"
                    "📞 మింట్రియల్ HQ: " + _COMPANY_NO + "\n\n"
                    "గ్రీన్ భవిష్యత్తు ఎంచుకున్నందుకు ధన్యవాదాలు! 🌱\n"
                    "*— టీమ్ మింట్రియల్*"
                ),
                "meta_template_name": "myntreal_lead_welcome_walkin",
                "meta_template_language": "en",
                "is_meta_approved": False,
            },
        ]
        for tpl in _welcome_templates:
            ex = db.query(WhatsAppTemplate).filter_by(slug=tpl["slug"]).first()
            if not ex:
                db.add(WhatsAppTemplate(
                    slug=tpl["slug"],
                    name=tpl["name"],
                    segment=tpl["segment"],
                    template_type=tpl["template_type"],
                    body_text=tpl["body_text"],
                    meta_template_name=tpl["meta_template_name"],
                    meta_template_language=tpl["meta_template_language"],
                    is_meta_approved=tpl["is_meta_approved"],
                    is_active=True,
                ))
                logger.info("[WA-BOOTSTRAP] Seeded template: %s", tpl["slug"])
        db.commit()

        # ── Seed VGK Member Welcome template ──────────────────────────────────
        _VGK_CHANNEL_FOOTER = (
            "\n\n📢 *Stay Connected — Join our WhatsApp Channels:*\n"
            "🔷 VGK4U: https://whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m\n"
            "🌐 Myntreal: https://whatsapp.com/channel/0029VbCmSCh2kNFiA0RsHZ2r\n"
            "☀️ Har Ghar Solar: https://whatsapp.com/channel/0029Vb7V0ImFCCoYg891FL3D"
        )
        _VGK_WELCOME_BODY = (
            "Hello {{name}}! 🎉\n\n"
            "Welcome to *VGK4U* — the Loyalty Rewards Platform!\n\n"
            "Your VGK Member ID: *{{member_id}}*\n"
            "💰 Welcome Bonus: *10,000 Discount Credits* Credited!\n\n"
            "You are now part of the VGK4U Loyalty Network across:\n"
            "☀️ Solar Energy  🛵 Electric Vehicles\n"
            "🏠 Real Estate  🛡️ Insurance\n\n"
            "👉 Login here: {{login_url}}\n\n"
            "1 Credit = ₹1 value. Start earning rewards today!\n"
            "*— VGK4U Team*" + _VGK_CHANNEL_FOOTER
        )
        _vgk_welcome_tpl = db.query(WhatsAppTemplate).filter_by(slug="vgk_member_welcome").first()
        if not _vgk_welcome_tpl:
            _vgk_welcome_tpl = WhatsAppTemplate(
                slug="vgk_member_welcome",
                name="VGK Member Welcome",
                segment="vgk",
                template_type="text",
                body_text=_VGK_WELCOME_BODY,
                meta_template_name="vgk_member_welcome",
                meta_template_language="en",
                is_meta_approved=False,
                is_active=True,
            )
            db.add(_vgk_welcome_tpl)
            db.flush()
            logger.info("[WA-BOOTSTRAP] Seeded template: vgk_member_welcome")
        else:
            # [DC-VGK-CHANNEL-001] Always keep channel footer up-to-date in existing template
            if _VGK_CHANNEL_FOOTER not in (_vgk_welcome_tpl.body_text or ""):
                _vgk_welcome_tpl.body_text = _VGK_WELCOME_BODY
                logger.info("[WA-BOOTSTRAP] Updated vgk_member_welcome body with channel footer")

        # Link vgk_member_created trigger to the welcome template
        _vgk_trig = db.query(WhatsAppAutoTrigger).filter_by(event_key="vgk_member_created").first()
        if _vgk_trig and not _vgk_trig.template_id:
            _vgk_trig.template_id = _vgk_welcome_tpl.id
        db.commit()

        # ── Link lead_welcome triggers to their templates ──────────────────────
        for event_key_link, slug_link in [
            ("lead_welcome_general", "lead_welcome_general"),
            ("lead_welcome_walkin",  "lead_welcome_walkin"),
        ]:
            trig = db.query(WhatsAppAutoTrigger).filter_by(event_key=event_key_link).first()
            tmpl = db.query(WhatsAppTemplate).filter_by(slug=slug_link).first()
            if trig and tmpl and not trig.template_id:
                trig.template_id = tmpl.id
        db.commit()

        # ── Seed Partner Agreement Expiry reminder templates ──────────────────
        _PARTNER_EXPIRY_PARTNER_BODY = (
            "Dear *{{partner_name}}*,\n\n"
            "This is a reminder that your partnership agreement (*{{partner_code}}*) is expiring on *{{partner_end_date}}* — that's *{{days_left}} day(s)* from today.\n\n"
            "Please contact your account manager to renew your agreement.\n\n"
            "*— Team Myntreal*"
        )
        _PARTNER_EXPIRY_STAFF_BODY = (
            "📋 *Partnership Expiry Alert*\n\n"
            "Partner: *{{partner_name}}* ({{partner_code}})\n"
            "Expiry Date: *{{partner_end_date}}*\n"
            "Days Left: *{{days_left}} day(s)*\n\n"
            "Please follow up and initiate renewal process.\n\n"
            "*— MyntReal System*"
        )
        for _ptpl in [
            {
                "slug": "partner_agreement_expiry_partner",
                "name": "Partner Agreement Expiry — To Partner",
                "segment": "partner",
                "template_type": "text",
                "body_text": _PARTNER_EXPIRY_PARTNER_BODY,
                "meta_template_name": "partner_agreement_expiry_partner",
                "meta_template_language": "en",
                "is_meta_approved": False,
            },
            {
                "slug": "partner_agreement_expiry_staff",
                "name": "Partner Agreement Expiry — To Staff",
                "segment": "staff",
                "template_type": "text",
                "body_text": _PARTNER_EXPIRY_STAFF_BODY,
                "meta_template_name": "partner_agreement_expiry_staff",
                "meta_template_language": "en",
                "is_meta_approved": False,
            },
        ]:
            if not db.query(WhatsAppTemplate).filter_by(slug=_ptpl["slug"]).first():
                db.add(WhatsAppTemplate(
                    slug=_ptpl["slug"],
                    name=_ptpl["name"],
                    segment=_ptpl["segment"],
                    template_type=_ptpl["template_type"],
                    body_text=_ptpl["body_text"],
                    meta_template_name=_ptpl["meta_template_name"],
                    meta_template_language=_ptpl["meta_template_language"],
                    is_meta_approved=_ptpl["is_meta_approved"],
                    is_active=True,
                ))
                logger.info("[WA-BOOTSTRAP] Seeded template: %s", _ptpl["slug"])
        db.commit()

        logger.info("[WA-BOOTSTRAP] ✅ WhatsApp tables and triggers bootstrapped")
    except Exception as e:
        db.rollback()
        logger.error("[WA-BOOTSTRAP] Seed error: %s", str(e))
    finally:
        db.close()


def bootstrap_vgk_discount_schema_and_points():
    """
    DC Protocol Apr 2026:
    1. Add discount_id column to service_ticket_spare_requests (idempotent)
    2. Initialise mnr_points_balance for all VGK_TEAM members who don't have one yet
       Registered (is_paid_activation=FALSE) → 10,000 pts
       Activated  (is_paid_activation=TRUE)  → 60,000 pts (50K activation + 10K registration)
    """
    db = SessionLocal()
    try:
        # ── 1. discount_id column ─────────────────────────────────────────────
        col_exists = db.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='service_ticket_spare_request' AND column_name='discount_id'
        """)).fetchone()
        if not col_exists:
            db.execute(text(
                "ALTER TABLE service_ticket_spare_request ADD COLUMN IF NOT EXISTS discount_id VARCHAR(50) NULL"
            ))
            db.commit()
            logger.info("[VGK-BOOTSTRAP] ✅ Added discount_id column to service_ticket_spare_request")

        # ── 2. Initialise VGK member points ──────────────────────────────────
        new_members = db.execute(text("""
            SELECT op.id, op.partner_code, op.is_paid_activation
            FROM official_partners op
            WHERE op.category = 'VGK_TEAM'
              AND op.partner_code IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM mnr_points_balance pb WHERE pb.user_id = op.partner_code
              )
        """)).fetchall()

        for m in new_members:
            pts = 60000 if m.is_paid_activation else 10000
            desc = (
                "VGK Activated member — 50,000 activation + 10,000 registration points"
                if m.is_paid_activation
                else "VGK Registered member — 10,000 welcome points"
            )
            db.execute(text("""
                INSERT INTO mnr_points_balance
                    (company_id, user_id, initial_points, current_balance,
                     total_consumed, total_credited, created_at, updated_at)
                VALUES (1, :uid, :pts, :pts, 0, 0, NOW(), NOW())
            """), {'uid': m.partner_code, 'pts': pts})
            db.execute(text("""
                INSERT INTO mnr_points_transactions
                    (company_id, user_id, transaction_type, amount, balance_after,
                     description, created_by_type, created_at)
                VALUES (1, :uid, 'initial_allocation', :pts, :pts, :desc, 'system', NOW())
            """), {'uid': m.partner_code, 'pts': pts, 'desc': desc})

        if new_members:
            db.commit()
            logger.info(f"[VGK-BOOTSTRAP] ✅ Initialised points for {len(new_members)} VGK member(s)")
        else:
            logger.info("[VGK-BOOTSTRAP] ✅ All VGK members already have points records")

    except Exception as e:
        db.rollback()
        logger.error(f"[VGK-BOOTSTRAP] ❌ Failed: {e}")
    finally:
        db.close()


def bootstrap_wa_tracking_tables():
    """
    DC-WA-TRACK-001: Link tracking + CRM WA send log tables.
    wa_link_tracks  — every click on a tracking redirect is logged here.
    crm_wa_sends    — every WhatsApp send from CRM is logged here.
    Idempotent — CREATE TABLE IF NOT EXISTS.
    """
    db = SessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS wa_link_tracks (
                id          SERIAL PRIMARY KEY,
                token       VARCHAR(64) UNIQUE NOT NULL,
                target_url  TEXT NOT NULL,
                title       VARCHAR(200),
                lead_id     INTEGER,
                staff_id    INTEGER,
                source_type VARCHAR(50) DEFAULT 'crm_wa',
                send_id     INTEGER,
                click_count INTEGER DEFAULT 0,
                first_clicked_at TIMESTAMP,
                last_clicked_at  TIMESTAMP,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_link_tracks_token ON wa_link_tracks(token)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_wa_link_tracks_lead ON wa_link_tracks(lead_id)"))

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS crm_wa_sends (
                id          SERIAL PRIMARY KEY,
                lead_id     INTEGER,
                template_id INTEGER,
                staff_id    INTEGER,
                phone_used  VARCHAR(20),
                send_method VARCHAR(20) DEFAULT 'meta',
                body_sent   TEXT,
                status      VARCHAR(20) DEFAULT 'sent',
                wamid       VARCHAR(100),
                sent_at     TIMESTAMP DEFAULT NOW(),
                notes       TEXT
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_wa_sends_lead ON crm_wa_sends(lead_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_wa_sends_staff ON crm_wa_sends(staff_id)"))

        db.commit()
        logger.info("[SCHEMA BOOTSTRAP] ✅ DC-WA-TRACK-001: wa_link_tracks + crm_wa_sends tables ensured")
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ DC-WA-TRACK-001 failed: {e}")
    finally:
        db.close()


def bootstrap_portal_reset_code_columns():
    """
    DC-OTP-RESET-001: Ensure reset_code + reset_code_expires columns exist
    on official_partners (VGK/Dealer) and staff_employees (Staff portal).
    Idempotent — safe to run on every startup across all 4 workers.
    """
    db = SessionLocal()
    try:
        targets = [
            ("official_partners",  ["reset_code VARCHAR(6)", "reset_code_expires TIMESTAMP"]),
            ("staff_employees",    ["reset_code VARCHAR(6)", "reset_code_expires TIMESTAMP"]),
        ]
        for table, col_defs in targets:
            result = db.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name=:tbl
                AND column_name IN ('reset_code','reset_code_expires')
            """), {"tbl": table})
            existing = {row[0] for row in result.fetchall()}
            cols_to_add = []
            if 'reset_code' not in existing:
                cols_to_add.append("ADD COLUMN reset_code VARCHAR(6)")
            if 'reset_code_expires' not in existing:
                cols_to_add.append("ADD COLUMN reset_code_expires TIMESTAMP")
            if cols_to_add:
                db.execute(text(f"ALTER TABLE {table} {', '.join(cols_to_add)}"))
                db.commit()
                logger.info(f"[SCHEMA BOOTSTRAP] ✅ DC-OTP-RESET-001: Added reset_code columns to {table}")
            else:
                logger.info(f"[SCHEMA BOOTSTRAP] ✅ DC-OTP-RESET-001: reset_code columns already exist on {table}")
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ DC-OTP-RESET-001 reset_code bootstrap failed: {e}")
    finally:
        db.close()


def bootstrap_wa_app_id_column():
    """DC-WA-MEDIA-002: Add facebook_app_id column to whatsapp_api_config for Resumable Upload API."""
    db = SessionLocal()
    try:
        result = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='whatsapp_api_config' AND column_name='facebook_app_id'"
        ))
        if not result.fetchone():
            db.execute(text("ALTER TABLE whatsapp_api_config ADD COLUMN facebook_app_id VARCHAR(64)"))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ DC-WA-MEDIA-002: facebook_app_id column added to whatsapp_api_config")
        else:
            logger.info("[SCHEMA BOOTSTRAP] ✅ DC-WA-MEDIA-002: facebook_app_id column already exists")
    except Exception as e:
        db.rollback()
        logger.error(f"[SCHEMA BOOTSTRAP] ❌ DC-WA-MEDIA-002 facebook_app_id bootstrap failed: {e}")
    finally:
        db.close()


def bootstrap_message_log_columns():
    """
    DC-MSGLOG-001: Widen message_sid to VARCHAR(500) for Meta WAMIDs (were VARCHAR(34)),
    add sent_by_staff_id / sent_by_name / sender_type to message_log,
    and add all missing columns to whatsapp_templates (usage_scope, meta_template_id,
    meta_approval_status, meta_rejected_reason, meta_submitted_at, meta_category, footer_text).
    Fully idempotent — checks existence before each ALTER.
    """
    db = SessionLocal()
    try:
        # ── 1. Widen message_sid ─────────────────────────────────────────────
        try:
            db.execute(text(
                "ALTER TABLE message_log ALTER COLUMN message_sid TYPE VARCHAR(500)"
            ))
            db.commit()
            logger.info("[SCHEMA BOOTSTRAP] ✅ DC-MSGLOG-001: message_sid widened to VARCHAR(500)")
        except Exception:
            db.rollback()

        # ── 2. Add sent_by / sender_type columns to message_log ─────────────
        for col_name, col_def in [
            ("sent_by_staff_id", "INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL"),
            ("sent_by_name",     "VARCHAR(200)"),
            ("sender_type",      "VARCHAR(50)"),
        ]:
            try:
                row = db.execute(text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='message_log' AND column_name=:col"
                ), {"col": col_name}).fetchone()
                if not row:
                    db.execute(text(f"ALTER TABLE message_log ADD COLUMN {col_name} {col_def}"))
                    db.commit()
                    logger.info(f"[SCHEMA BOOTSTRAP] ✅ DC-MSGLOG-001: message_log.{col_name} added")
            except Exception as e:
                db.rollback()
                logger.error(f"[SCHEMA BOOTSTRAP] ❌ message_log.{col_name} failed: {e}")

        # ── 3. Add missing columns to whatsapp_templates ─────────────────────
        tpl_columns = [
            ("usage_scope",           "VARCHAR(20)  NOT NULL DEFAULT 'both'"),
            ("footer_text",           "VARCHAR(200)"),
            ("meta_template_id",      "VARCHAR(100)"),
            ("meta_approval_status",  "VARCHAR(30)"),
            ("meta_submitted_at",     "TIMESTAMP"),
            ("meta_category",         "VARCHAR(30)"),
            ("meta_rejected_reason",  "VARCHAR(500)"),
        ]
        for col_name, col_def in tpl_columns:
            try:
                row = db.execute(text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='whatsapp_templates' AND column_name=:col"
                ), {"col": col_name}).fetchone()
                if not row:
                    db.execute(text(f"ALTER TABLE whatsapp_templates ADD COLUMN {col_name} {col_def}"))
                    db.commit()
                    logger.info(f"[SCHEMA BOOTSTRAP] ✅ DC-MSGLOG-001: whatsapp_templates.{col_name} added")
            except Exception as e:
                db.rollback()
                logger.error(f"[SCHEMA BOOTSTRAP] ❌ whatsapp_templates.{col_name} failed: {e}")

    finally:
        db.close()


def bootstrap_partner_contacts_modules():
    """
    [DC-PARTNER-CONTACTS-001] Add partner contact + module settings + staff-showroom link columns:
    - official_partners.sales_contact_number / sales_contact_name  (dedicated sales POC)
    - official_partners.service_contact_number / service_contact_name (dedicated service POC)
    - official_partners.module_settings JSONB  (per-module on/off control)
    - staff_employees.linked_partner_id  (links a sales/service staff to a showroom for dual portal login)
    - service_ticket.company_support_requested BOOLEAN (partner requests company escalation)
    - service_ticket.service_dept_staff_id INTEGER (notify service dept staff on ticket)
    """
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE official_partners
            ADD COLUMN IF NOT EXISTS sales_contact_number VARCHAR(20),
            ADD COLUMN IF NOT EXISTS sales_contact_name VARCHAR(200),
            ADD COLUMN IF NOT EXISTS service_contact_number VARCHAR(20),
            ADD COLUMN IF NOT EXISTS service_contact_name VARCHAR(200),
            ADD COLUMN IF NOT EXISTS module_settings JSONB DEFAULT '{}'
        """))
        db.execute(text("""
            ALTER TABLE staff_employees
            ADD COLUMN IF NOT EXISTS linked_partner_id INTEGER REFERENCES official_partners(id) ON DELETE SET NULL
        """))
        db.execute(text("""
            ALTER TABLE service_ticket
            ADD COLUMN IF NOT EXISTS company_support_requested BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS service_dept_staff_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL
        """))
        db.commit()
        logger.info("[DC-PARTNER-CONTACTS-001] ✅ Partner contacts + module_settings + staff link + ticket escalation columns ensured")
    except Exception as e:
        logger.warning("[DC-PARTNER-CONTACTS-001] ⚠️ Error (non-fatal): %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_solar_doc_columns():
    """
    [DC-SOLAR-APR2026] Add solar document fix columns:
    - vendor_master.tech_signature_url   (technician/site-engineer signature image for PDF embedding)
    - vendor_master.rep_signature_url    (authorized representative signature for Vendor-Sig-with-Stamp blocks)
    - crm_solar_lead_tech.consumer_category  (HT/LT for Annexure IV)
    """
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE vendor_master
            ADD COLUMN IF NOT EXISTS tech_signature_url VARCHAR(500)
        """))
        db.execute(text("""
            ALTER TABLE vendor_master
            ADD COLUMN IF NOT EXISTS rep_signature_url VARCHAR(500)
        """))
        db.execute(text("""
            ALTER TABLE crm_solar_lead_tech
            ADD COLUMN IF NOT EXISTS consumer_category VARCHAR(30)
        """))
        db.commit()
        logger.info("[DC-SOLAR-APR2026] bootstrap_solar_doc_columns: columns ensured")
    except Exception as e:
        logger.warning("[DC-SOLAR-APR2026] bootstrap_solar_doc_columns error (non-fatal): %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_wa_example_values_column():
    """
    DC-WA-EXAMPLES-001: Add example_values JSONB column to whatsapp_templates.
    DC-WA-EXAMPLES-002: Auto-seed example_values for templates that have none,
    based on segment defaults and variable patterns in the body text.
    This is the single source of truth — segment → variable → default value.
    """
    import re as _re
    import json as _json

    # ── Segment-based variable defaults (single source of truth) ──────────────
    # Key: segment, Value: ordered list of (variable_key_pattern, default_value)
    # Patterns match both named vars ({{name}}) and positional ({{1}})
    SEGMENT_DEFAULTS: dict = {
        "vgk": {
            "1": "Rahul Sharma", "2": "VGK07012345",
            "3": "https://vgk4u.com/vgk/login", "4": "10,000",
            "name": "Rahul Sharma", "member_id": "VGK07012345",
            "login_url": "https://vgk4u.com/vgk/login", "points_balance": "10,000",
        },
        "general": {
            "1": "Rahul Sharma", "2": "VGK07012345",
            "3": "https://vgk4u.com/vgk/login", "4": "10,000",
            "name": "Rahul Kumar", "partner_phone": "+91 98765 43210",
            "otp": "123456",
        },
        "system": {
            "name": "Rahul Kumar", "ticket_id": "TKT2001",
            "status": "In Progress", "po_number": "PO-2025-001",
            "pending_count": "5", "meetings": "3",
            "1": "123456",
        },
        "ev_b2b": {"name": "Business Owner", "1": "Business Owner"},
        "ev_b2c": {"name": "Rahul Kumar", "1": "Rahul Kumar"},
        "real_estate": {"name": "Rahul Kumar", "1": "Rahul Kumar"},
        "etc_training": {"name": "Rahul Kumar", "1": "Rahul Kumar"},
    }

    db = SessionLocal()
    try:
        # 1. Ensure column exists
        db.execute(text(
            "ALTER TABLE whatsapp_templates ADD COLUMN IF NOT EXISTS example_values JSONB"
        ))
        db.commit()

        # 2. Auto-seed example_values for templates that have none
        rows = db.execute(text(
            "SELECT id, segment, body_text FROM whatsapp_templates WHERE example_values IS NULL"
        )).fetchall()

        updated = 0
        for row in rows:
            tpl_id, segment, body = row[0], row[1] or "general", row[2] or ""
            defaults = SEGMENT_DEFAULTS.get(segment, SEGMENT_DEFAULTS.get("general", {}))
            # Extract vars in appearance order (deduped)
            all_vars = []
            seen: set = set()
            for m in _re.finditer(r'\{\{(\w+)\}\}', body):
                v = m.group(1)
                if v not in seen:
                    seen.add(v)
                    all_vars.append(v)
            if not all_vars:
                continue
            examples = [defaults.get(v, f"value_{v}") for v in all_vars]
            db.execute(text(
                "UPDATE whatsapp_templates SET example_values = :val WHERE id = :id"
            ), {"val": _json.dumps(examples), "id": tpl_id})
            updated += 1

        db.commit()
        logger.info("[DC-WA-EXAMPLES-001] ✅ example_values column ensured on whatsapp_templates; seeded %d templates", updated)
    except Exception as e:
        logger.warning("[DC-WA-EXAMPLES-001] ⚠️ Error (non-fatal): %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_vgk_points_refill_schema():
    """
    [DC-POINTS-REFILL] Apr 2026
    Adds auto-refill tracking columns to official_partners and upgrades the
    vgk_points_ledger CHECK constraint to include the AUTO_REFILL reason code.

    New columns on official_partners:
      - vgk_points_refill_count   INTEGER DEFAULT 0   (how many auto-refills fired)
      - vgk_points_last_refill_at TIMESTAMP NULL       (start of current 180-day refill window)

    Constraint change on vgk_points_ledger:
      - Drops old 'vgk_points_reason_check' and recreates it with AUTO_REFILL added.
    """
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE official_partners
            ADD COLUMN IF NOT EXISTS vgk_points_refill_count   INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS vgk_points_last_refill_at TIMESTAMP NULL
        """))
        db.execute(text("""
            ALTER TABLE vgk_points_ledger
            DROP CONSTRAINT IF EXISTS vgk_points_reason_check
        """))
        db.execute(text("""
            ALTER TABLE vgk_points_ledger
            ADD CONSTRAINT vgk_points_reason_check
            CHECK (reason_code IN (
                'WELCOME_BONUS','ACTIVATION_BONUS','LOYAL_BONUS','BONANZA_REWARD',
                'PRODUCT_DISCOUNT','COMMISSION_ADJUSTMENT','MANUAL_ADJUSTMENT',
                'MIGRATION_BALANCE','CAMPAIGN_BONUS','AUTO_REFILL','INCOME_EARNED'
            ))
        """))
        db.commit()
        logger.info("[DC-POINTS-REFILL] ✅ vgk_points_refill columns added and constraint updated")
    except Exception as e:
        logger.warning("[DC-POINTS-REFILL] ⚠️ Non-fatal error: %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_accounts_default_access():
    """
    DC_ACCOUNTS_DEFAULT_ACCESS_001: Grant SFMS accounts page access to all staff
    who belong to the accounts department (ACT or any dept named 'account*').

    Why this is needed:
      - sfms_general_ledger, sfms_ledger_masters, sfms_journal_voucher were
        never added to staff_menu_master (they exist in the registry but not master).
      - Non-VGK4U-Supreme staff (e.g. MR10025) use the my-menus API which reads
        StaffEmployeeMenuSettings.can_view — defaulting to no access.
      - Accounts dept employees should see all SFMS pages automatically.

    Department detection (checks all 3 sources):
      1. staff_employees.department_id  (primary dept)
      2. staff_employee_departments     (ORM additional depts)
      3. staff_employee_additional_departments  (legacy additional depts table)

    Strategy (fully idempotent):
      1. INSERT missing sfms menu records into staff_menu_master for each company.
      2. Find all active employees in the accounts department (across all companies).
      3. INSERT missing staff_employee_menu_settings (can_view=TRUE) for those
         employees, skipping rows already present (preserves manual overrides).
    """
    SFMS_ACCOUNTS = [
        ("sfms_companies",        "Companies",            "fas fa-building",         "/staff/accounts/companies",        200),
        ("sfms_segments",         "Segments",             "fas fa-puzzle-piece",     "/staff/accounts/segments",         201),
        ("sfms_income_entries",   "Income Entries",       "fas fa-arrow-up",         "/staff/accounts/income-entries",   202),
        ("sfms_expense_entries",  "Expense Entries",      "fas fa-arrow-down",       "/staff/accounts/expense-entries",  203),
        ("sfms_party_ledger",     "Party Ledger",         "fas fa-book",             "/staff/accounts/party-ledger",     204),
        ("sfms_general_ledger",   "General Ledger",       "fas fa-book-open",        "/staff/accounts/general-ledger",   205),
        ("sfms_journal_voucher",  "Entries",              "fas fa-file-alt",         "/staff/accounts/journal-voucher",  207),
        ("sfms_receivables",      "Receivables",          "fas fa-hand-holding-usd", "/staff/accounts/receivables",      208),
        ("sfms_payables",         "Payables",             "fas fa-credit-card",      "/staff/accounts/payables",         209),
        ("sfms_capital_account",  "Capital Account",      "fas fa-coins",             "/staff/accounts/capital",          2094),
        ("sfms_cash_in_hand",     "Cash in Hand",         "fas fa-hand-holding-usd",  "/staff/accounts/cash-in-hand",     2093),
        ("sfms_duties_taxes",     "Duties & Taxes",       "fas fa-percent",           "/staff/accounts/duties-taxes",     2095),
        ("sfms_fund_allocations", "Fund Allocations",     "fas fa-piggy-bank",       "/staff/accounts/fund-allocations", 210),
        ("sfms_balance_sheet",    "Balance Sheet",        "fas fa-balance-scale",    "/staff/accounts/balance-sheet",    211),
        ("sfms_reports",          "Financial Reports",    "fas fa-chart-area",       "/staff/accounts/reports",          212),
    ]
    CODES_LIST = "'" + "','".join(m[0] for m in SFMS_ACCOUNTS) + "'"

    db = SessionLocal()
    try:
        # ── Step 1: Get all active company IDs (table: associated_companies) ──
        companies = db.execute(text(
            "SELECT id FROM associated_companies WHERE is_active = TRUE"
        )).fetchall()
        company_ids = [r[0] for r in companies]
        if not company_ids:
            logger.info("[DC_ACCOUNTS_DEFAULT_ACCESS_001] No active companies found, skipping.")
            return

        # ── Step 2: Ensure menu records exist in staff_menu_master ────────────
        inserted_menus = 0
        for cid in company_ids:
            for (code, name, icon, route, order) in SFMS_ACCOUNTS:
                existing = db.execute(text(
                    "SELECT id FROM staff_menu_master WHERE company_id=:c AND menu_code=:mc"
                ), {"c": cid, "mc": code}).fetchone()
                if not existing:
                    db.execute(text("""
                        INSERT INTO staff_menu_master
                            (company_id, menu_code, menu_name, menu_category, menu_icon,
                             route_path, display_order, audience_scope, is_active,
                             is_default_visible, is_default_accessible, created_at, updated_at)
                        VALUES
                            (:c, :mc, :mn, 'sfms', :mi, :rp, :do, 'staff', TRUE,
                             FALSE, FALSE, NOW(), NOW())
                    """), {"c": cid, "mc": code, "mn": name, "mi": icon, "rp": route, "do": order})
                    inserted_menus += 1
        # Rename any existing journal-voucher rows to 'Entries' (menu rename DC fix)
        db.execute(text("""
            UPDATE staff_menu_master
            SET menu_name = 'Entries', updated_at = NOW()
            WHERE route_path = '/staff/accounts/journal-voucher'
              AND menu_name != 'Entries'
        """))
        db.commit()

        # ── Step 3: Find accounts department IDs ─────────────────────────────
        # Match by name: 'ACT', or any name containing 'account' (case-insensitive)
        acct_depts = db.execute(text("""
            SELECT id FROM staff_departments
            WHERE name = 'ACT'
               OR LOWER(name) LIKE '%account%'
        """)).fetchall()
        acct_dept_ids = [r[0] for r in acct_depts]
        if not acct_dept_ids:
            logger.warning("[DC_ACCOUNTS_DEFAULT_ACCESS_001] ⚠️ No accounts department found — skipping employee grants.")
            return

        dept_ids_sql = ", ".join(str(d) for d in acct_dept_ids)
        logger.info(f"[DC_ACCOUNTS_DEFAULT_ACCESS_001] Found accounts dept IDs: {acct_dept_ids}")

        # ── Step 4: Collect accounts dept employee IDs (all 3 sources) ────────
        # Source A: primary department_id
        src_a = db.execute(text(f"""
            SELECT DISTINCT id FROM staff_employees
            WHERE status = 'active'
              AND department_id IN ({dept_ids_sql})
        """)).fetchall()

        # Source B: staff_employee_departments (ORM many-to-many)
        src_b = db.execute(text(f"""
            SELECT DISTINCT employee_id FROM staff_employee_departments
            WHERE department_id IN ({dept_ids_sql})
        """)).fetchall()

        # Source C: staff_employee_additional_departments (legacy additional depts)
        src_c = db.execute(text(f"""
            SELECT DISTINCT employee_id FROM staff_employee_additional_departments
            WHERE department_id IN ({dept_ids_sql})
        """)).fetchall()

        acct_emp_ids_set = {r[0] for r in src_a} | {r[0] for r in src_b} | {r[0] for r in src_c}

        # DC-ACCT-ACCESS-001: Also include MR10001 (VGK4U Mentor) and all MENTOR-designation employees
        mentor_emps = db.execute(text("""
            SELECT DISTINCT id FROM staff_employees
            WHERE status = 'active'
              AND (emp_code = 'MR10001' OR UPPER(COALESCE(designation, '')) LIKE '%MENTOR%')
        """)).fetchall()
        acct_emp_ids_set |= {r[0] for r in mentor_emps}

        acct_emp_ids = list(acct_emp_ids_set)
        if not acct_emp_ids:
            logger.warning("[DC_ACCOUNTS_DEFAULT_ACCESS_001] ⚠️ No accounts dept employees found — skipping grants.")
            return

        logger.info(f"[DC_ACCOUNTS_DEFAULT_ACCESS_001] Accounts dept employees (incl. MR10001/MENTOR): {acct_emp_ids}")

        # ── Step 5: Grant can_view for each employee × company × menu ─────────
        # Employee may access menus from their base_company_id or any data_companies entry.
        # We grant access for the menu record that belongs to ANY company the employee
        # is linked to (base_company_id or appears in data_companies JSONB array).
        emp_ids_sql = ", ".join(str(e) for e in acct_emp_ids)

        # Step 5a: INSERT missing settings rows (new menus like GL/LM/JV) ──────
        result_ins = db.execute(text(f"""
            INSERT INTO staff_employee_menu_settings
                (company_id, employee_id, menu_id, can_view, can_edit,
                 is_overridden, set_by_code, set_by_name, created_at, updated_at)
            SELECT DISTINCT
                smm.company_id,
                se.id            AS employee_id,
                smm.id           AS menu_id,
                TRUE, TRUE,
                FALSE,
                'DC_ACCOUNTS_DEFAULT_001',
                'Accounts Dept Default Access Bootstrap',
                NOW(), NOW()
            FROM staff_menu_master smm
            CROSS JOIN staff_employees se
            WHERE smm.menu_code IN ({CODES_LIST})
              AND se.id IN ({emp_ids_sql})
              AND se.status = 'active'
              AND (
                  smm.company_id = se.base_company_id
                  OR smm.company_id::text = ANY(
                      SELECT jsonb_array_elements_text(se.data_companies)
                  )
              )
              AND NOT EXISTS (
                  SELECT 1 FROM staff_employee_menu_settings sems
                  WHERE sems.company_id = smm.company_id
                    AND sems.employee_id = se.id
                    AND sems.menu_id = smm.id
              )
        """))
        granted = result_ins.rowcount
        db.commit()

        # Step 5b: UPDATE existing rows where can_view=FALSE for accounts employees
        # These were set to False by a previous admin action (MR10001 bulk-set).
        # The accounts dept policy overrides that to ensure visibility.
        result_upd = db.execute(text(f"""
            UPDATE staff_employee_menu_settings sems
            SET can_view = TRUE,
                can_edit = TRUE,
                is_overridden = FALSE,
                set_by_code = 'DC_ACCOUNTS_DEFAULT_001',
                set_by_name = 'Accounts Dept Default Access Bootstrap',
                updated_at = NOW()
            FROM staff_menu_master smm
            WHERE sems.menu_id = smm.id
              AND smm.menu_code IN ({CODES_LIST})
              AND sems.employee_id IN ({emp_ids_sql})
              AND sems.can_view = FALSE
        """))
        updated = result_upd.rowcount
        db.commit()

        print(
            f"[DC_ACCOUNTS_DEFAULT_ACCESS_001] ✅ Bootstrap complete: "
            f"{inserted_menus} menu records inserted, "
            f"{len(acct_emp_ids)} accounts dept employees (ids={acct_emp_ids}), "
            f"{granted} new grants, {updated} existing rows updated to can_view=TRUE",
            flush=True
        )
    except Exception as e:
        db.rollback()
        logger.error(f"[DC_ACCOUNTS_DEFAULT_ACCESS_001] ❌ Failed: {e}", exc_info=True)
    finally:
        db.close()


def bootstrap_wallet_txn_solar_advance_types():
    """
    DC-VGK-PARTNER-SYNC-001: extend vgk_wallet_transactions.txn_type CHECK
    constraint to allow SOLAR_ADVANCE_CREDIT and SOLAR_ADVANCE_RECOVERY,
    used by the auto-released CIBIL advance flow.
    Idempotent: drops + re-adds the constraint each startup.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE vgk_wallet_transactions
                DROP CONSTRAINT IF EXISTS vgk_wallet_transactions_txn_type_check
        """))
        db.execute(text("""
            ALTER TABLE vgk_wallet_transactions
                ADD CONSTRAINT vgk_wallet_transactions_txn_type_check
                CHECK (txn_type IN (
                    'INCOME_CREDIT','INCOME_DEDUCTION','SERVICE_DEBIT',
                    'VENDOR_DEBIT','WITHDRAWAL','ADJUSTMENT',
                    'SOLAR_ADVANCE_CREDIT','SLAB_BONUS_CREDIT','SOLAR_ADVANCE_RECOVERY',
                    'SOLAR_ADV_PAYOUT','SLAB_BONUS_PAYOUT',
                    'COMPANY_PAYOUT','COMPANY_PAYOUT_DEDUCT'
                ))
        """))
        db.commit()
        print("[DC-VGK-PARTNER-SYNC-001] ✅ vgk_wallet_transactions txn_type extended (+SOLAR_ADVANCE_*)", flush=True)
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-VGK-PARTNER-SYNC-001] ❌ Wallet txn_type ALTER failed: {e}")
    finally:
        db.close()


def bootstrap_withdrawal_duplicate_guard():
    """
    DC_WITHDRAW_001: Add a partial unique index on withdrawal_request(user_id)
    covering only in-flight statuses so two active withdrawals for the same user
    can never coexist, regardless of which code path created them.

    Partial index = only rows WHERE status IN (...active...) are indexed,
    so Completed/Rejected rows don't block future withdrawals.

    BLOCKED STATE: If any user has more than one active withdrawal (or if the
    dc_migrations key 'uq_wr_active_per_user_blocked' is present), the handler
    drops the index (ensuring dev/prod parity) and skips creation with a warning.
    Once staff processes the duplicate withdrawals on prod, remove the
    'uq_wr_active_per_user_blocked' key from dc_migrations on both environments
    and restart — the index will be auto-created on the next startup.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        # Check if a manual "blocked" flag is set in dc_migrations
        blocked_key = db.execute(text(
            "SELECT 1 FROM dc_migrations WHERE key = 'uq_wr_active_per_user_blocked' LIMIT 1"
        )).fetchone()

        # Also check for live duplicate active withdrawals in this database
        dup_row = db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT user_id FROM withdrawal_request
                WHERE status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'On Hold')
                GROUP BY user_id HAVING COUNT(*) > 1
            ) x
        """)).fetchone()
        has_duplicates = dup_row and dup_row[0] > 0

        if blocked_key or has_duplicates:
            # Drop the index if it exists so both environments stay in sync
            db.execute(text("DROP INDEX IF EXISTS uq_wr_active_per_user"))
            db.commit()
            reason = "dc_migrations blocked key present" if blocked_key else "duplicate active withdrawals detected"
            print(
                f"[DC_WITHDRAW_001] ⚠️  Skipping uq_wr_active_per_user ({reason}). "
                f"Process duplicate withdrawals and remove 'uq_wr_active_per_user_blocked' "
                f"from dc_migrations on both dev and prod, then restart.",
                flush=True
            )
            return

        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_wr_active_per_user
            ON withdrawal_request (user_id)
            WHERE status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'On Hold')
        """))
        db.commit()
        print("[DC_WITHDRAW_001] ✅ Partial unique index uq_wr_active_per_user ensured", flush=True)
    except Exception as e:
        db.rollback()
        logger.error(f"[DC_WITHDRAW_001] ❌ Failed: {e}")
    finally:
        db.close()


def bootstrap_scheduler_log_job_guard():
    """
    DC_WITHDRAW_GUARD_001 (Phase 3): Partial functional unique index on scheduler_log
    so that only one Running-or-Completed row can exist per (job_id, IST calendar day).

    Partial index: only rows WHERE overall_status IN ('Running', 'Completed') are
    covered — Failed rows are excluded so a failed run can always be retried by a
    fresh INSERT without hitting the constraint.

    The guard in generate_automatic_withdrawals() relies on this index: it attempts
    a blind INSERT with status='Running' and catches IntegrityError to exit without
    proceeding, eliminating the SELECT-then-INSERT TOCTOU race.

    Idempotent: deduplicates existing rows first, then creates index with IF NOT EXISTS.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        # Step 1: Remove historical duplicate rows before creating the unique index.
        # Keep only the row with the highest id per (job_id, scheduled_date day)
        # within the covered status set (Running/Completed).
        result = db.execute(text("""
            DELETE FROM scheduler_log
            WHERE overall_status IN ('Running', 'Completed')
              AND id NOT IN (
                SELECT MAX(id)
                FROM scheduler_log
                WHERE overall_status IN ('Running', 'Completed')
                GROUP BY job_id, (scheduled_date::date)
              )
        """))
        deleted = result.rowcount
        if deleted:
            logger.info(f"[DC_WITHDRAW_GUARD_001] 🧹 Removed {deleted} duplicate scheduler_log rows before index creation")
        db.commit()

        # Step 2: Create the unique index now that there are no duplicates.
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_scheduler_log_job_per_day
            ON scheduler_log (job_id, (scheduled_date::date))
            WHERE overall_status IN ('Running', 'Completed')
        """))
        db.commit()
        print("[DC_WITHDRAW_GUARD_001] ✅ Unique index uq_scheduler_log_job_per_day ensured", flush=True)
    except Exception as e:
        db.rollback()
        logger.error(f"[DC_WITHDRAW_GUARD_001] ❌ Failed to create scheduler_log job guard index: {e}")
    finally:
        db.close()


def bootstrap_bonanza_slab_wise_cols():
    """
    DC_BONANZA_SLABWISE_001: Add slab_extra_amount + slab_base_reference to the bonanza table.
    Idempotent — safe to run on every startup via IF NOT EXISTS column check.
      slab_extra_amount   NUMERIC(12,2) — bonus actually paid by this campaign (e.g. ₹3000)
      slab_base_reference NUMERIC(12,2) — display-only base reference (e.g. ₹1000 Solar File Advance)
    """
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE bonanza
                ADD COLUMN IF NOT EXISTS slab_extra_amount   NUMERIC(12,2),
                ADD COLUMN IF NOT EXISTS slab_base_reference NUMERIC(12,2)
        """))
        db.commit()
        print("[DC_BONANZA_SLABWISE_001] ✅ slab_extra_amount + slab_base_reference ensured on bonanza table", flush=True)
    except Exception as e:
        db.rollback()
        logger.error(f"[DC_BONANZA_SLABWISE_001] ❌ Failed to add slab columns: {e}")
    finally:
        db.close()


def bootstrap_slab_advance_auto_cols():
    """
    DC_BONANZA_SLABWISE_AUTO_001: Add slab_bonus_paid + slab_bonus_amount to vgk_solar_cibil_advances.
    Idempotent — safe to run on every startup.
      slab_bonus_paid   BOOLEAN DEFAULT FALSE — idempotency guard (never double-credit)
      slab_bonus_amount NUMERIC(12,2)         — slab amount actually credited on this advance
    """
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE vgk_solar_cibil_advances
                ADD COLUMN IF NOT EXISTS slab_bonus_paid   BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS slab_bonus_amount NUMERIC(12,2)
        """))
        db.commit()
        print("[DC_BONANZA_SLABWISE_AUTO_001] ✅ slab_bonus_paid + slab_bonus_amount ensured on vgk_solar_cibil_advances", flush=True)
    except Exception as e:
        db.rollback()
        logger.error(f"[DC_BONANZA_SLABWISE_AUTO_001] ❌ Failed to add slab advance columns: {e}")
    finally:
        db.close()


def bootstrap_partner_kyc_agreement():
    """
    [DC-PARTNER-KYC-001 / DC-PARTNER-TERMS-001 / DC-PARTNER-DOCS-001] May 2026
    Add 7 nullable columns to official_partners for KYC, partnership dates, and agreement docs.
    Migration key: partner_kyc_agreement_20260507
    Idempotent — safe to run on every startup via ADD COLUMN IF NOT EXISTS.
    """
    db = SessionLocal()
    try:
        already = db.execute(text(
            "SELECT 1 FROM dc_migrations WHERE key = 'partner_kyc_agreement_20260507' LIMIT 1"
        )).fetchone()
        if already:
            logger.info("[DC-PARTNER-KYC-001] Migration partner_kyc_agreement_20260507 already applied — skipping")
            return
        db.execute(text("""
            ALTER TABLE official_partners
                ADD COLUMN IF NOT EXISTS aadhaar_number          VARCHAR(20),
                ADD COLUMN IF NOT EXISTS partner_start_date      DATE,
                ADD COLUMN IF NOT EXISTS partner_end_date        DATE,
                ADD COLUMN IF NOT EXISTS reminder_days_before    INTEGER DEFAULT 90,
                ADD COLUMN IF NOT EXISTS security_deposit        NUMERIC(15,2) DEFAULT 0,
                ADD COLUMN IF NOT EXISTS agreement_document_path    VARCHAR(500),
                ADD COLUMN IF NOT EXISTS application_document_path  VARCHAR(500)
        """))
        db.execute(text(
            "INSERT INTO dc_migrations (key, applied_at) VALUES ('partner_kyc_agreement_20260507', NOW()) "
            "ON CONFLICT (key) DO NOTHING"
        ))
        db.commit()
        logger.info("[DC-PARTNER-KYC-001] ✅ partner_kyc_agreement_20260507 migration applied — 7 columns added to official_partners")
    except Exception as e:
        logger.warning("[DC-PARTNER-KYC-001] ⚠️ Non-fatal error: %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_spare_procurement_tables():
    """
    [DC-CONSOL-SPARE-001 / DC-PARTNER-SPARE-001] May 2026
    Create 4 tables for consolidated spare parts procurement workbench + partner ordering.
    Migration key: spare_procurement_tables_20260508
    Idempotent — uses CREATE TABLE IF NOT EXISTS.
    """
    db = SessionLocal()
    try:
        already = db.execute(text(
            "SELECT 1 FROM dc_migrations WHERE key = 'spare_procurement_tables_20260508' LIMIT 1"
        )).fetchone()
        if already:
            logger.info("[DC-CONSOL-SPARE-001] spare_procurement_tables_20260508 already applied — skipping")
            return
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS spare_purchase_orders (
                id                    SERIAL PRIMARY KEY,
                order_number          VARCHAR(30) UNIQUE NOT NULL,
                company_id            INTEGER NOT NULL REFERENCES associated_companies(id),
                status                VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                notes                 TEXT,
                created_by_id         INTEGER REFERENCES staff_employees(id),
                submitted_by_id       INTEGER REFERENCES staff_employees(id),
                submitted_at          TIMESTAMP,
                approved_by_id        INTEGER REFERENCES staff_employees(id),
                approved_at           TIMESTAMP,
                approval_notes        TEXT,
                cancelled_by_id       INTEGER REFERENCES staff_employees(id),
                cancelled_at          TIMESTAMP,
                procurement_req_ids   JSONB DEFAULT '[]',
                created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS spare_purchase_order_lines (
                id                    SERIAL PRIMARY KEY,
                order_id              INTEGER NOT NULL REFERENCES spare_purchase_orders(id) ON DELETE CASCADE,
                vendor_id             INTEGER NOT NULL REFERENCES vendor_master(id),
                item_id               INTEGER NOT NULL REFERENCES stock_item_master(id),
                item_code             VARCHAR(30),
                item_name             VARCHAR(200),
                quantity              NUMERIC(15,4) NOT NULL DEFAULT 1,
                unit_of_measure       VARCHAR(20) NOT NULL DEFAULT 'PCS',
                last_purchase_rate    NUMERIC(15,2),
                demand_source         VARCHAR(100),
                demand_qty            NUMERIC(15,4),
                notes                 TEXT,
                created_at            TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS partner_spare_requests (
                id                    SERIAL PRIMARY KEY,
                request_number        VARCHAR(30) UNIQUE NOT NULL,
                partner_id            INTEGER NOT NULL REFERENCES official_partners(id),
                company_id            INTEGER NOT NULL REFERENCES associated_companies(id),
                status                VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
                notes                 TEXT,
                acknowledged_by_id    INTEGER REFERENCES staff_employees(id),
                acknowledged_at       TIMESTAMP,
                fulfilled_by_id       INTEGER REFERENCES staff_employees(id),
                fulfilled_at          TIMESTAMP,
                spare_order_id        INTEGER REFERENCES spare_purchase_orders(id),
                created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS partner_spare_request_lines (
                id                    SERIAL PRIMARY KEY,
                request_id            INTEGER NOT NULL REFERENCES partner_spare_requests(id) ON DELETE CASCADE,
                item_id               INTEGER NOT NULL REFERENCES stock_item_master(id),
                item_code             VARCHAR(30),
                item_name             VARCHAR(200),
                quantity              NUMERIC(15,4) NOT NULL DEFAULT 1,
                unit_of_measure       VARCHAR(20) NOT NULL DEFAULT 'PCS',
                notes                 TEXT,
                created_at            TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_spo_company ON spare_purchase_orders(company_id);
            CREATE INDEX IF NOT EXISTS idx_spo_status ON spare_purchase_orders(status);
            CREATE INDEX IF NOT EXISTS idx_spol_order ON spare_purchase_order_lines(order_id);
            CREATE INDEX IF NOT EXISTS idx_spol_vendor ON spare_purchase_order_lines(vendor_id);
            CREATE INDEX IF NOT EXISTS idx_spol_item ON spare_purchase_order_lines(item_id);
            CREATE INDEX IF NOT EXISTS idx_psr_partner ON partner_spare_requests(partner_id);
            CREATE INDEX IF NOT EXISTS idx_psr_status ON partner_spare_requests(status);
            CREATE INDEX IF NOT EXISTS idx_psrl_request ON partner_spare_request_lines(request_id);
            CREATE INDEX IF NOT EXISTS idx_psrl_item ON partner_spare_request_lines(item_id);
        """))
        db.execute(text(
            "INSERT INTO dc_migrations (key, applied_at) VALUES ('spare_procurement_tables_20260508', NOW()) "
            "ON CONFLICT (key) DO NOTHING"
        ))
        db.commit()
        logger.info("[DC-CONSOL-SPARE-001] ✅ spare_procurement_tables_20260508 applied — 4 tables created")
    except Exception as e:
        logger.warning("[DC-CONSOL-SPARE-001] ⚠️ Non-fatal error: %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_spare_vendor_optional():
    """
    DC-CONSOL-SPARE-002: Make vendor_id nullable on spare_purchase_order_lines.
    Vendor is now optional at draft/submit; mandatory only at approval.
    Migration key: spare_vendor_optional_20260508
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        existing = db.execute(text(
            "SELECT 1 FROM dc_migrations WHERE key = 'spare_vendor_optional_20260508' LIMIT 1"
        )).fetchone()
        if existing:
            logger.info("[DC-CONSOL-SPARE-002] spare_vendor_optional_20260508 already applied — skipping")
            return
        db.execute(text("""
            ALTER TABLE spare_purchase_order_lines
                ALTER COLUMN vendor_id DROP NOT NULL
        """))
        db.execute(text(
            "INSERT INTO dc_migrations (key, applied_at) VALUES ('spare_vendor_optional_20260508', NOW()) "
            "ON CONFLICT (key) DO NOTHING"
        ))
        db.commit()
        logger.info("[DC-CONSOL-SPARE-002] ✅ spare_vendor_optional_20260508 — vendor_id now nullable")
    except Exception as e:
        logger.warning("[DC-CONSOL-SPARE-002] ⚠️ Non-fatal: %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_vgk_company_payouts():
    """
    [DC-COMPANY-PAYOUT-001] May 2026
    Creates vgk_company_payouts table for company-side gross payouts by MR10001/MR10025.
    Migration key: vgk_company_payouts_20260516
    Idempotent — uses CREATE TABLE IF NOT EXISTS.
    """
    db = SessionLocal()
    try:
        already = db.execute(text(
            "SELECT 1 FROM dc_migrations WHERE key = 'vgk_company_payouts_20260516' LIMIT 1"
        )).fetchone()
        if already:
            logger.info("[DC-COMPANY-PAYOUT-001] vgk_company_payouts_20260516 already applied — skipping")
            return
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS vgk_company_payouts (
                id           SERIAL PRIMARY KEY,
                partner_id   INTEGER NOT NULL REFERENCES official_partners(id) ON DELETE CASCADE,
                gross_amount NUMERIC(15,2) NOT NULL,
                tds_pct      NUMERIC(5,2)  NOT NULL DEFAULT 10.00,
                tds_amount   NUMERIC(15,2) NOT NULL,
                net_amount   NUMERIC(15,2) NOT NULL,
                notes        TEXT,
                paid_by      INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                paid_by_code VARCHAR(30),
                created_at   TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_vgk_payout_partner ON vgk_company_payouts(partner_id)"))
        db.execute(text(
            "INSERT INTO dc_migrations (key, applied_at) VALUES ('vgk_company_payouts_20260516', NOW()) "
            "ON CONFLICT (key) DO NOTHING"
        ))
        db.commit()
        logger.info("[DC-COMPANY-PAYOUT-001] ✅ vgk_company_payouts table created")
    except Exception as e:
        logger.warning("[DC-COMPANY-PAYOUT-001] ⚠️ Non-fatal: %s", e)
        db.rollback()
    finally:
        db.close()


def bootstrap_company_royalty_points():
    """
    [DC-COMPANY-ROYALTY-001] May 2026
    Adds COMPANY_ROYALTY to the vgk_points_reason_check constraint.
    Allows MR10001/MR10025 to grant Company Side Royalty Points to any VGK member.
    Migration key: company_royalty_points_20260516
    Idempotent — drops and recreates the CHECK constraint safely.
    """
    db = SessionLocal()
    try:
        already = db.execute(text(
            "SELECT 1 FROM dc_migrations WHERE key = 'company_royalty_points_20260516' LIMIT 1"
        )).fetchone()
        if already:
            logger.info("[DC-COMPANY-ROYALTY-001] company_royalty_points_20260516 already applied — skipping")
            return
        db.execute(text("ALTER TABLE vgk_points_ledger DROP CONSTRAINT IF EXISTS vgk_points_reason_check"))
        db.execute(text(
            "ALTER TABLE vgk_points_ledger ADD CONSTRAINT vgk_points_reason_check "
            "CHECK (reason_code IN ("
            "'WELCOME_BONUS','ACTIVATION_BONUS','LOYAL_BONUS','BONANZA_REWARD',"
            "'PRODUCT_DISCOUNT','COMMISSION_ADJUSTMENT','MANUAL_ADJUSTMENT','MIGRATION_BALANCE',"
            "'CAMPAIGN_BONUS','AUTO_REFILL','COMPANY_ROYALTY','INCOME_EARNED'"
            "))"
        ))
        db.execute(text(
            "INSERT INTO dc_migrations (key, applied_at) VALUES ('company_royalty_points_20260516', NOW()) "
            "ON CONFLICT (key) DO NOTHING"
        ))
        db.commit()
        logger.info("[DC-COMPANY-ROYALTY-001] ✅ company_royalty_points_20260516 — COMPANY_ROYALTY added to vgk_points_reason_check")
    except Exception as e:
        logger.warning("[DC-COMPANY-ROYALTY-001] ⚠️ Non-fatal: %s", e)
        db.rollback()
    finally:
        db.close()


def run_schema_bootstrap():
    """
    Run all schema bootstrap operations
    Called on application startup
    """
    logger.info("[SCHEMA BOOTSTRAP] Starting schema bootstrap...")
    bootstrap_background_jobs_schema()
    backfill_job_handler_metadata()
    bootstrap_sfms_credit_tables()
    bootstrap_sfms_seed_data()
    bootstrap_accounts_module_schema()
    bootstrap_accounts_default_access()
    drop_deal_unique_constraint()
    add_z_guru_id_column()
    bootstrap_whatsapp_config_schema()
    bootstrap_vgk_discount_schema_and_points()
    bootstrap_portal_reset_code_columns()
    bootstrap_wa_tracking_tables()
    bootstrap_wa_app_id_column()
    bootstrap_message_log_columns()
    bootstrap_solar_doc_columns()
    bootstrap_partner_contacts_modules()
    bootstrap_wa_example_values_column()
    bootstrap_vgk_points_refill_schema()
    bootstrap_wallet_txn_solar_advance_types()
    drop_marketplace_spares_sku_unique()
    bootstrap_withdrawal_duplicate_guard()
    bootstrap_scheduler_log_job_guard()
    bootstrap_bonanza_slab_wise_cols()
    bootstrap_slab_advance_auto_cols()
    bootstrap_partner_kyc_agreement()
    bootstrap_spare_procurement_tables()
    bootstrap_spare_vendor_optional()
    bootstrap_company_royalty_points()
    bootstrap_vgk_company_payouts()

    # DC_CAPITAL_ACCOUNT_REGISTRY_001: Ensure Capital Account is in staff_menu_registry
    try:
        _db = SessionLocal()
        try:
            _db.execute(text("""
                INSERT INTO staff_menu_registry
                  (menu_code, menu_name, route_path, menu_category, menu_icon,
                   display_order, audience_scope, source, source_file,
                   is_default_visible, is_default_accessible, is_active, is_system_default,
                   sidebar_section, sidebar_section_title, sidebar_section_order,
                   menu_type, is_submenu, cascade_enabled, item_order,
                   created_at, updated_at, last_discovered_at)
                VALUES
                  ('staff_accounts_capital', 'Capital Account', '/staff/accounts/capital',
                   'sfms', 'fas fa-coins', 1, 'staff', 'manual', 'schema_bootstrap.py',
                   FALSE, FALSE, TRUE, FALSE,
                   'sfms', 'SFMS', 12,
                   'STAFF', FALSE, TRUE, 0,
                   NOW(), NOW(), NOW())
                ON CONFLICT (menu_code) DO UPDATE
                  SET route_path = EXCLUDED.route_path,
                      is_active = TRUE,
                      updated_at = NOW()
            """))
            _db.commit()
            logger.info("[DC_CAPITAL_ACCOUNT_REGISTRY_001] staff_accounts_capital registry entry ensured")
            _db.execute(text("""
                INSERT INTO staff_menu_registry
                  (menu_code, menu_name, route_path, menu_category, menu_icon,
                   display_order, audience_scope, source, source_file,
                   is_default_visible, is_default_accessible, is_active, is_system_default,
                   sidebar_section, sidebar_section_title, sidebar_section_order,
                   menu_type, is_submenu, cascade_enabled, item_order,
                   created_at, updated_at, last_discovered_at)
                VALUES
                  ('staff_accounts_cash_in_hand', 'Cash in Hand', '/staff/accounts/cash-in-hand',
                   'sfms', 'fas fa-hand-holding-usd', 1, 'staff', 'manual', 'schema_bootstrap.py',
                   FALSE, FALSE, TRUE, FALSE,
                   'sfms', 'SFMS', 12,
                   'STAFF', FALSE, TRUE, 0,
                   NOW(), NOW(), NOW())
                ON CONFLICT (menu_code) DO UPDATE
                  SET route_path = EXCLUDED.route_path,
                      is_active = TRUE,
                      updated_at = NOW()
            """))
            _db.commit()
            logger.info("[DC_CAPITAL_ACCOUNT_REGISTRY_001] staff_accounts_cash_in_hand registry entry ensured")
        finally:
            _db.close()
    except Exception as _ce:
        logger.warning(f"[DC_CAPITAL_ACCOUNT_REGISTRY_001] Non-fatal: {_ce}")

    # DC_WA_TEMPLATES_SEED_001: Seed 16 standard WA templates + triggers
    try:
        from app.services.whatsapp_templates_seeder import seed_wa_templates
        from app.core.database import SessionLocal
        seed_wa_templates(SessionLocal)
    except Exception as _wa_seed_err:
        logger.warning(f"[DC_WA_TEMPLATES_SEED_001] Non-fatal seeder error: {_wa_seed_err}")

    # DC_VGK_FIELD_ALLOWANCE_STAGE_20260615: Stage 1/2 approval columns on field_allowance_progress
    # + SENIOR_COMM kind on vgk_cash_income_entries
    try:
        _db = SessionLocal()
        try:
            _exists = _db.execute(text(
                "SELECT 1 FROM dc_migrations WHERE key='vgk_field_allowance_stage_20260615' LIMIT 1"
            )).fetchone()
            if not _exists:
                _db.execute(text("""
                    ALTER TABLE field_allowance_progress
                      ADD COLUMN IF NOT EXISTS stage_1_approved_by VARCHAR(20),
                      ADD COLUMN IF NOT EXISTS stage_1_approved_at TIMESTAMP,
                      ADD COLUMN IF NOT EXISTS stage_2_paid_by     VARCHAR(20),
                      ADD COLUMN IF NOT EXISTS stage_2_paid_at     TIMESTAMP
                """))
                _db.execute(text(
                    "ALTER TABLE vgk_cash_income_entries "
                    "DROP CONSTRAINT IF EXISTS vgk_cash_income_kind_check"
                ))
                _db.execute(text(
                    "ALTER TABLE vgk_cash_income_entries ADD CONSTRAINT vgk_cash_income_kind_check "
                    "CHECK (kind IN ('COMMISSION','ADVANCE','SENIOR_COMM'))"
                ))
                _db.execute(text(
                    "INSERT INTO dc_migrations (key, applied_at) "
                    "VALUES ('vgk_field_allowance_stage_20260615', NOW()) ON CONFLICT DO NOTHING"
                ))
                _db.commit()
                logger.info("[DC_VGK_FIELD_ALLOWANCE_STAGE_20260615] ✅ Stage columns + SENIOR_COMM kind applied")
            else:
                logger.debug("[DC_VGK_FIELD_ALLOWANCE_STAGE_20260615] Already applied — skip")
        finally:
            _db.close()
    except Exception as _fa_err:
        logger.warning(f"[DC_VGK_FIELD_ALLOWANCE_STAGE_20260615] Non-fatal: {_fa_err}")

    # DC_LEDGER_CATEGORY_COLS_20260617: Add main_category_id + sub_category_id to
    # account_ledger and party_ledger for display-only category/sub-category columns.
    # No accounting effect — purely for narration and reporting.
    try:
        _db = SessionLocal()
        try:
            _exists = _db.execute(text(
                "SELECT 1 FROM dc_migrations WHERE key='ledger_category_cols_20260617' LIMIT 1"
            )).fetchone()
            if not _exists:
                _db.execute(text("""
                    ALTER TABLE account_ledger
                      ADD COLUMN IF NOT EXISTS main_category_id INTEGER,
                      ADD COLUMN IF NOT EXISTS sub_category_id  INTEGER
                """))
                _db.execute(text("""
                    ALTER TABLE party_ledger
                      ADD COLUMN IF NOT EXISTS main_category_id INTEGER,
                      ADD COLUMN IF NOT EXISTS sub_category_id  INTEGER
                """))
                # Backfill account_ledger rows from journal_vouchers → expense_sub_category
                _db.execute(text("""
                    UPDATE account_ledger al
                    SET sub_category_id  = jv.category_id,
                        main_category_id = esc.main_category_id
                    FROM journal_vouchers jv
                    JOIN expense_sub_category esc ON esc.id = jv.category_id
                    WHERE al.reference_type = 'JOURNAL'
                      AND al.reference_id   = jv.id
                      AND jv.category_id IS NOT NULL
                      AND al.sub_category_id IS NULL
                """))
                # Backfill party_ledger rows from journal_vouchers → expense_sub_category
                _db.execute(text("""
                    UPDATE party_ledger pl
                    SET sub_category_id  = jv.category_id,
                        main_category_id = esc.main_category_id
                    FROM journal_vouchers jv
                    JOIN expense_sub_category esc ON esc.id = jv.category_id
                    WHERE pl.reference_type = 'JOURNAL'
                      AND pl.reference_id   = jv.id
                      AND jv.category_id IS NOT NULL
                      AND pl.sub_category_id IS NULL
                """))
                _db.execute(text(
                    "INSERT INTO dc_migrations (key, applied_at) "
                    "VALUES ('ledger_category_cols_20260617', NOW()) ON CONFLICT DO NOTHING"
                ))
                _db.commit()
                logger.info("[DC_LEDGER_CATEGORY_COLS_20260617] ✅ main_category_id + sub_category_id added to account_ledger + party_ledger and backfilled")
            else:
                logger.debug("[DC_LEDGER_CATEGORY_COLS_20260617] Already applied — skip")
        finally:
            _db.close()
    except Exception as _cat_col_err:
        logger.warning(f"[DC_LEDGER_CATEGORY_COLS_20260617] Non-fatal: {_cat_col_err}")

    # DC-VOID-001: Add void audit columns to purchase_invoice_uploads.
    # voided_by_id, voided_at, void_reason — set when a CONFIRMED upload is fully reversed.
    # Also drops+recreates status CHECK to include 'VOIDED' for both tables.
    try:
        _db = SessionLocal()
        try:
            _exists = _db.execute(text(
                "SELECT 1 FROM dc_migrations WHERE key='add_void_fields_20260618' LIMIT 1"
            )).fetchone()
            if not _exists:
                _db.execute(text("""
                    ALTER TABLE purchase_invoice_uploads
                      ADD COLUMN IF NOT EXISTS voided_by_id INTEGER REFERENCES staff_employees(id),
                      ADD COLUMN IF NOT EXISTS voided_at    TIMESTAMP,
                      ADD COLUMN IF NOT EXISTS void_reason  TEXT
                """))
                _db.execute(text(
                    "ALTER TABLE purchase_invoice_uploads "
                    "DROP CONSTRAINT IF EXISTS purchase_upload_status_check"
                ))
                _db.execute(text(
                    "ALTER TABLE purchase_invoice_uploads ADD CONSTRAINT purchase_upload_status_check "
                    "CHECK (status IN ('UPLOADED','EXTRACTING','EXTRACTED','REVIEWED','CONFIRMED','PROCESSED','REJECTED','CANCELLED','VOIDED'))"
                ))
                _db.execute(text(
                    "ALTER TABLE sales_invoices "
                    "DROP CONSTRAINT IF EXISTS sales_invoice_status_check"
                ))
                _db.execute(text(
                    "ALTER TABLE sales_invoices ADD CONSTRAINT sales_invoice_status_check "
                    "CHECK (status IN ('DRAFT','CONFIRMED','CANCELLED','RETURNED','VOIDED'))"
                ))
                _db.execute(text(
                    "INSERT INTO dc_migrations (key, applied_at) "
                    "VALUES ('add_void_fields_20260618', NOW()) ON CONFLICT DO NOTHING"
                ))
                _db.commit()
                logger.info("[DC_VOID_FIELDS_20260618] ✅ voided_by_id/voided_at/void_reason added to purchase_invoice_uploads; VOIDED added to both status constraints")
            else:
                logger.debug("[DC_VOID_FIELDS_20260618] Already applied — skip")
        finally:
            _db.close()
    except Exception as _void_err:
        logger.warning(f"[DC_VOID_FIELDS_20260618] Non-fatal: {_void_err}")

    logger.info("[SCHEMA BOOTSTRAP] ✅ Schema bootstrap complete")
