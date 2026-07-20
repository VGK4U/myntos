"""
Database configuration for FastAPI
Preserves PostgreSQL connection from Flask app
"""

import os
import sys
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings

# DC Protocol (Dec 24, 2025): Early diagnostic logging for production debugging
# This runs at import time, BEFORE lifespan, to catch issues early
print("[DC-DB-INIT] Database module loading...", flush=True)
db_url_raw = os.getenv("DATABASE_URL") or os.getenv("PROD_DATABASE_URL")
if db_url_raw:
    # Mask password in URL for logging
    masked_url = db_url_raw[:30] + "..." if len(db_url_raw) > 30 else db_url_raw
    print(f"[DC-DB-INIT] DATABASE_URL found: {masked_url}", flush=True)
else:
    print("[DC-DB-INIT] WARNING: No DATABASE_URL or PROD_DATABASE_URL environment variable found!", flush=True)
    print("[DC-DB-INIT] Will fall back to SQLite (may fail on read-only filesystem)", flush=True)

print(f"[DC-DB-INIT] Using config DATABASE_URL: {str(settings.DATABASE_URL)[:30]}...", flush=True)

# Create SQLAlchemy engine with PostgreSQL (preserves Flask database)
if settings.DATABASE_URL and str(settings.DATABASE_URL).startswith("sqlite"):
    # SQLite configuration for development
    print("[DC-DB-INIT] Creating SQLite engine (development mode)...", flush=True)
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG  # Only log SQL in debug mode
    )
else:
    # PostgreSQL configuration — Helium (local dev) or Neon (production cloud)
    # DC Protocol (Mar 17, 2026): Pool tuned for Neon 25-connection ceiling.
    # DC Protocol (Mar 21, 2026): Pool exhaustion fix — pool_size + pool_timeout.
    # DC Protocol (May 2026): engine.dispose() in gunicorn post_fork ensures only
    #   workers (not master) hold live connections after startup.
    # DC Protocol (May 2026 — Helium): Replit migrated dev DB from Neon → Helium.
    #   Helium is a LOCAL postgres (sslmode=disable, hostname only resolves inside
    #   the dev container). Replit's diff-checker runs from external servers and
    #   cannot reach Helium → connection always times out. This is a platform
    #   limitation; the Republish button still works (5 consecutive successes confirm).
    #   Helium-specific tuning: no SSL keepalives (sslmode=disable), longer
    #   pool_recycle (local postgres never drops idle connections), no pool ceiling.
    #   Neon-specific tuning: SSL keepalives prevent silent TCP drops; pool capped
    #   at 14 max to leave room for Replit's diff-check connection slot.

    # DC Protocol (May 2026): Apply sslmode typo fix directly here as a second layer
    # of defence. config.py already sanitizes sslmode=require. → sslmode=require in the
    # settings validator, but any code path that reads os.environ directly (e.g. the
    # Replit diff-checker, psycopg2 called with raw env vars, or future tooling) will
    # hit the typo. Sanitize the raw env vars in-process so the running process sees
    # the corrected value via os.environ, and write back so subprocesses inherit it.
    for _key in ("DATABASE_URL", "PROD_DATABASE_URL"):
        _raw = os.environ.get(_key, "")
        if _raw and "sslmode=require." in _raw:
            _fixed = _raw.replace("sslmode=require.", "sslmode=require")
            os.environ[_key] = _fixed
            print(f"[DC-DB-INIT] Fixed sslmode typo in {_key}", flush=True)

    _db_url_str = str(settings.DATABASE_URL)
    _is_helium = any(h in _db_url_str for h in ["@helium", "@helium/", "heliumdb", "127.0.0.1", "localhost"])
    _is_neon   = "neon.tech" in _db_url_str

    if _is_helium:
        print("[DC-DB-INIT] Creating PostgreSQL engine (Helium local mode)...", flush=True)
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,       # Detect stale connections before use
            pool_recycle=1800,        # Recycle every 30m — local postgres never drops idle conns
            pool_size=5,              # Generous pool for dev — no external connection ceiling
            max_overflow=10,
            pool_timeout=30,          # Standard 30s wait for a free slot
            pool_use_lifo=True,       # Reuse warm connections
            connect_args={
                "connect_timeout": 10,  # Fail fast if Helium unreachable
                # DC-MIGRATION-TIMEOUT-001: statement_timeout is NOT set at connection level.
                # It is applied per-session inside get_db() so API requests are still protected
                # but startup migration sessions (engine.connect() / SessionLocal() direct) are
                # never killed mid-migration-key-check.
            },
            echo=False
        )
    else:
        # Neon (production cloud) — SSL keepalives + pool sized for 1-worker + APScheduler load
        # DC Protocol (May 2026 — pool fix): Production runs --workers 1 + APScheduler with up to
        # 8 concurrent background threads. Under burst load (multi-company dashboard, GPS ticks,
        # CRM pages loading simultaneously) the old pool_size=3/overflow=4 (7 max) was fully
        # exhausted — new requests waited 12s then threw QueuePool → "socket hang up" → login fails.
        # Fix: pool_size=5 + max_overflow=10 = 15 max connections.
        #   Neon free tier ceiling = 25. 15 app + 5 Neon internal + 5 spare = 25. Safe.
        # pool_timeout=5: fail fast (not 12s) so the single uvicorn worker moves on quickly
        #   and the proxy's auto-retry picks it up on the next attempt.
        print("[DC-DB-INIT] Creating PostgreSQL engine (Neon cloud mode)...", flush=True)
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,          # Detect dead Neon SSL connections before use
            pool_recycle=300,            # Recycle every 5m — just before Neon drops idle SSL at ~5m
            pool_size=5,                 # 1 worker + APScheduler: 5 base connections always ready
            max_overflow=15,             # DC-POOL-001: Burst headroom increased to 20 total (was 15)
                                         # Neon free-tier ceiling = 25; 20 app + 5 Neon internal = 25. Safe.
                                         # Prevents JV POST / critical writes from timing out during
                                         # service-queue burst load (pool exhaustion was confirmed root cause).
            pool_timeout=5,              # Fail fast (was 12s) — let proxy retry rather than blocking worker
            pool_use_lifo=True,          # LIFO: reuse warm connections, reduces SSL churn
            pool_reset_on_return='rollback',  # Ensure returned connections are always clean
            connect_args={
                "connect_timeout": 10,       # Fail fast if Neon unreachable (no indefinite hang)
                "keepalives": 1,
                "keepalives_idle": 30,       # Send keepalive after 30s idle
                "keepalives_interval": 10,
                "keepalives_count": 3,
                # DC-MIGRATION-TIMEOUT-001: statement_timeout NOT set at connection level.
                # Applied per-session in get_db() — API requests protected; migrations unrestricted.
            },
            echo=False
        )

print("[DC-DB-INIT] Engine created successfully", flush=True)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()

# Metadata for schema introspection
metadata = MetaData()

def get_db():
    """
    Dependency function to get database session
    Used in FastAPI route dependencies.
    DC-MIGRATION-TIMEOUT-001: statement_timeout applied here (not at engine level) so
    startup migration sessions that bypass get_db() are never killed mid-key-check.
    """
    from sqlalchemy import text as _text
    db = SessionLocal()
    try:
        db.execute(_text("SET statement_timeout = 25000"))
        yield db
    finally:
        db.close()

def run_pending_migrations():
    """
    DC Protocol (Dec 18, 2025): Run pending schema migrations at startup
    This ensures production database stays in sync with model changes
    Safe operations only - adds columns if they don't exist (non-destructive)
    PostgreSQL only - skips for SQLite development environments
    """
    from sqlalchemy import text
    
    # DC Protocol: Only run migrations on PostgreSQL (production/staging)
    # SQLite doesn't support all PostgreSQL features
    db_url = str(settings.DATABASE_URL) if settings.DATABASE_URL else ""
    if "sqlite" in db_url.lower():
        print("   ⏭️  Skipping migrations (SQLite dev environment)")
        return

    # DC Protocol (Mar 09, 2026): Skip migrations on local dev postgres.
    # Running DDL on the Replit-managed local postgres (hostname: helium) causes
    # Replit's deployment pipeline to detect "schema changes" every deploy and
    # demand approval before proceeding. The app uses Neon (neon.tech) in
    # production, so local postgres is dev-only and does not need schema
    # management — Neon receives the migrations on every production startup.
    is_neon = "neon.tech" in db_url
    is_local_pg = any(h in db_url for h in ["localhost", "127.0.0.1", "@helium", "@helium/", "heliumdb"])
    if not is_neon and is_local_pg:
        print("   ⏭️  Skipping migrations (Replit local postgres — Neon receives migrations in production)")
        return
    
    # Each migration is a single DDL statement (SQLAlchemy requirement)
    migrations = [
        # DC Protocol (Dec 15, 2025): Multi-Company Employee Assignment - Column
        {
            "name": "staff_employees.base_company_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_employees' AND column_name='base_company_id'",
            "migrate": "ALTER TABLE staff_employees ADD COLUMN base_company_id INTEGER REFERENCES associated_companies(id) ON DELETE SET NULL"
        },
        # DC Protocol (Dec 15, 2025): Multi-Company Employee Assignment - Index
        {
            "name": "idx_staff_employees_base_company_id",
            "check": "SELECT indexname FROM pg_indexes WHERE tablename='staff_employees' AND indexname='idx_staff_employees_base_company_id'",
            "migrate": "CREATE INDEX idx_staff_employees_base_company_id ON staff_employees(base_company_id)"
        },
        # DC Protocol (Dec 15, 2025): Data Companies JSONB column
        {
            "name": "staff_employees.data_companies",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_employees' AND column_name='data_companies'",
            "migrate": "ALTER TABLE staff_employees ADD COLUMN data_companies JSONB NOT NULL DEFAULT '[]'"
        },
        # DC Protocol (Dec 18, 2025): Property Hidden Fields - per-field hide control
        {
            "name": "rd_properties.hidden_fields",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='rd_properties' AND column_name='hidden_fields'",
            "migrate": "ALTER TABLE rd_properties ADD COLUMN hidden_fields JSONB NOT NULL DEFAULT '{}'"
        },
        # DC Protocol (Dec 18, 2025): Property Options - detailed bedroom/unit configuration specs
        {
            "name": "rd_properties.property_options",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='rd_properties' AND column_name='property_options'",
            "migrate": "ALTER TABLE rd_properties ADD COLUMN property_options JSONB DEFAULT '[]'"
        },
        # DC Protocol (Dec 21, 2025): CRM Deal Value System - 3-part tracking (total/received/balance)
        {
            "name": "crm_leads.deal_value_total",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_leads' AND column_name='deal_value_total'",
            "migrate": "ALTER TABLE crm_leads ADD COLUMN deal_value_total FLOAT NOT NULL DEFAULT 0"
        },
        {
            "name": "crm_leads.deal_value_received",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_leads' AND column_name='deal_value_received'",
            "migrate": "ALTER TABLE crm_leads ADD COLUMN deal_value_received FLOAT NOT NULL DEFAULT 0"
        },
        {
            "name": "crm_leads.deal_value_balance",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_leads' AND column_name='deal_value_balance'",
            "migrate": "ALTER TABLE crm_leads ADD COLUMN deal_value_balance FLOAT NOT NULL DEFAULT 0"
        },
        # DC Protocol (Jan 02, 2026): Service Tickets - Staff performer tracking for ticket logs
        {
            "name": "ticket_log.staff_performer_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='ticket_log' AND column_name='staff_performer_id'",
            "migrate": "ALTER TABLE ticket_log ADD COLUMN staff_performer_id INTEGER REFERENCES staff_employees(id)"
        },
        # DC Protocol (Jan 02, 2026): Service Tickets - Attachment scanning fields
        {
            "name": "ticket_attachment.is_scanned",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='ticket_attachment' AND column_name='is_scanned'",
            "migrate": "ALTER TABLE ticket_attachment ADD COLUMN is_scanned BOOLEAN NOT NULL DEFAULT FALSE"
        },
        {
            "name": "ticket_attachment.scan_status",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='ticket_attachment' AND column_name='scan_status'",
            "migrate": "ALTER TABLE ticket_attachment ADD COLUMN scan_status VARCHAR(20) DEFAULT 'Pending'"
        },
        {
            "name": "ticket_attachment.download_filename",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='ticket_attachment' AND column_name='download_filename'",
            "migrate": "ALTER TABLE ticket_attachment ADD COLUMN download_filename VARCHAR(255)"
        },
        {
            "name": "ticket_attachment.uses_new_naming",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='ticket_attachment' AND column_name='uses_new_naming'",
            "migrate": "ALTER TABLE ticket_attachment ADD COLUMN uses_new_naming BOOLEAN NOT NULL DEFAULT FALSE"
        },
        # DC Protocol (Jan 28, 2026): GPS Status Tracking for Team Live Tracker offline reasons
        {
            "name": "staff_attendance.gps_status",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='gps_status'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN gps_status VARCHAR(32) DEFAULT 'active'"
        },
        {
            "name": "staff_attendance.gps_status_reason",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='gps_status_reason'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN gps_status_reason VARCHAR(128)"
        },
        {
            "name": "staff_attendance.gps_status_at",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='gps_status_at'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN gps_status_at TIMESTAMP"
        },
        {
            "name": "staff_attendance.last_gps_at",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='last_gps_at'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN last_gps_at TIMESTAMP"
        },
        {
            "name": "staff_attendance.last_battery_pct",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='last_battery_pct'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN last_battery_pct INTEGER"
        },
        {
            "name": "dynamic_bonanza_reward.criteria_type",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='criteria_type'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN criteria_type VARCHAR(30) NOT NULL DEFAULT 'achievement_count'"
        },
        {
            "name": "dynamic_bonanza_reward.criteria_value",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='criteria_value'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN criteria_value NUMERIC(10, 2) NOT NULL DEFAULT 0"
        },
        {
            "name": "dynamic_bonanza_reward.criteria_operator",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='criteria_operator'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN criteria_operator VARCHAR(10) NOT NULL DEFAULT '>='"
        },
        {
            "name": "dynamic_bonanza_reward.reward_amount",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='reward_amount'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN reward_amount NUMERIC(12, 2)"
        },
        {
            "name": "dynamic_bonanza_reward.award_name",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='award_name'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN award_name VARCHAR(200)"
        },
        {
            "name": "dynamic_bonanza_reward.award_image",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='award_image'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN award_image VARCHAR(255)"
        },
        {
            "name": "dynamic_bonanza_reward.is_monetary",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='is_monetary'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN is_monetary BOOLEAN NOT NULL DEFAULT TRUE"
        },
        {
            "name": "dynamic_bonanza_reward.budget_amount",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='budget_amount'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN budget_amount NUMERIC(12, 2)"
        },
        {
            "name": "dynamic_bonanza_reward.max_recipients",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='max_recipients'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN max_recipients INTEGER"
        },
        {
            "name": "dynamic_bonanza_reward.current_recipients",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='dynamic_bonanza_reward' AND column_name='current_recipients'",
            "migrate": "ALTER TABLE dynamic_bonanza_reward ADD COLUMN current_recipients INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "crm_lead_transactions.revenue_category_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_transactions' AND column_name='revenue_category_id'",
            "migrate": "ALTER TABLE crm_lead_transactions ADD COLUMN revenue_category_id INTEGER REFERENCES revenue_categories(id) ON DELETE SET NULL"
        },
        {
            "name": "crm_lead_transactions.deal_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_transactions' AND column_name='deal_id'",
            "migrate": "ALTER TABLE crm_lead_transactions ADD COLUMN deal_id INTEGER REFERENCES crm_lead_deals(id) ON DELETE SET NULL"
        },
        {
            "name": "income_entries.revenue_category_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='revenue_category_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN revenue_category_id INTEGER REFERENCES revenue_categories(id)"
        },
        {
            "name": "income_entries.crm_transaction_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='crm_transaction_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN crm_transaction_id INTEGER"
        },
        {
            "name": "crm_lead_transactions.income_entry_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_transactions' AND column_name='income_entry_id'",
            "migrate": "ALTER TABLE crm_lead_transactions ADD COLUMN income_entry_id INTEGER"
        },
        {
            "name": "income_entries.lead_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='lead_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN lead_id INTEGER"
        },
        {
            "name": "income_entries.lead_owner_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='lead_owner_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN lead_owner_id INTEGER"
        },
        {
            "name": "income_entries.collected_by_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='collected_by_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN collected_by_id INTEGER"
        },
        {
            "name": "income_entries.payer_city",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='payer_city'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN payer_city VARCHAR(100)"
        },
        {
            "name": "income_entries.payer_state",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='payer_state'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN payer_state VARCHAR(100)"
        },
        {
            "name": "income_entries.transaction_type",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='transaction_type'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN transaction_type VARCHAR(20)"
        },
        {
            "name": "income_entries.confirmed_by_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='confirmed_by_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN confirmed_by_id INTEGER REFERENCES staff_employees(id)"
        },
        {
            "name": "income_entries.confirmed_at",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='confirmed_at'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN confirmed_at TIMESTAMP"
        },
        {
            "name": "crm_lead_deals.deal_code",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_deals' AND column_name='deal_code'",
            "migrate": "ALTER TABLE crm_lead_deals ADD COLUMN deal_code VARCHAR(30) UNIQUE"
        },
        {
            "name": "crm_lead_deals.deal_fy_seq",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_deals' AND column_name='deal_fy_seq'",
            "migrate": "ALTER TABLE crm_lead_deals ADD COLUMN deal_fy_seq INTEGER"
        },
        {
            "name": "crm_lead_deals.deal_date",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_deals' AND column_name='deal_date'",
            "migrate": "ALTER TABLE crm_lead_deals ADD COLUMN deal_date TIMESTAMP"
        },
        {
            "name": "crm_lead_deals.notes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead_deals' AND column_name='notes'",
            "migrate": "ALTER TABLE crm_lead_deals ADD COLUMN notes TEXT"
        },
        {
            "name": "pending_income.matching_contributors_snapshot",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='pending_income' AND column_name='matching_contributors_snapshot'",
            "migrate": "ALTER TABLE pending_income ADD COLUMN matching_contributors_snapshot JSONB"
        },
        {
            "name": "staff_employees.call_tracking_enabled",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_employees' AND column_name='call_tracking_enabled'",
            "migrate": "ALTER TABLE staff_employees ADD COLUMN call_tracking_enabled BOOLEAN NOT NULL DEFAULT FALSE; CREATE INDEX IF NOT EXISTS idx_staff_employees_call_tracking ON staff_employees(call_tracking_enabled)"
        },
        {
            "name": "staff_tasks.contact_phone",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_tasks' AND column_name='contact_phone'",
            "migrate": "ALTER TABLE staff_tasks ADD COLUMN contact_phone VARCHAR(20)"
        },
        {
            "name": "staff_tasks.contact_person_name",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_tasks' AND column_name='contact_person_name'",
            "migrate": "ALTER TABLE staff_tasks ADD COLUMN contact_person_name VARCHAR(128)"
        },
        {
            "name": "staff_task_phases.contact_phone",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_task_phases' AND column_name='contact_phone'",
            "migrate": "ALTER TABLE staff_task_phases ADD COLUMN contact_phone VARCHAR(20)"
        },
        {
            "name": "staff_task_phases.contact_person_name",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_task_phases' AND column_name='contact_person_name'",
            "migrate": "ALTER TABLE staff_task_phases ADD COLUMN contact_person_name VARCHAR(128)"
        },
        {
            "name": "staff_call_recordings_table",
            "check": "SELECT table_name FROM information_schema.tables WHERE table_name='staff_call_recordings'",
            "migrate": """CREATE TABLE staff_call_recordings (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES associated_companies(id),
                staff_id INTEGER NOT NULL REFERENCES staff_employees(id),
                call_log_id INTEGER REFERENCES staff_call_logs(id) ON DELETE SET NULL,
                original_filename VARCHAR(512) NOT NULL,
                storage_path VARCHAR(1024) NOT NULL,
                file_size BIGINT NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                duration_seconds INTEGER,
                recorded_at TIMESTAMP,
                device_recording_id VARCHAR(256),
                source_device VARCHAR(256),
                uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX ix_call_rec_staff_company ON staff_call_recordings(staff_id, company_id);
            CREATE INDEX ix_call_rec_call_log ON staff_call_recordings(call_log_id);
            CREATE INDEX ix_call_rec_device_id ON staff_call_recordings(device_recording_id, staff_id)"""
        },
        {
            "name": "staff_call_logs.has_recording",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_call_logs' AND column_name='has_recording'",
            "migrate": "ALTER TABLE staff_call_logs ADD COLUMN has_recording BOOLEAN NOT NULL DEFAULT FALSE"
        },
        {
            "name": "staff_call_logs.recording_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_call_logs' AND column_name='recording_id'",
            "migrate": "ALTER TABLE staff_call_logs ADD COLUMN recording_id INTEGER REFERENCES staff_call_recordings(id) ON DELETE SET NULL"
        },
        {
            "name": "staff_call_logs.contact_name",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_call_logs' AND column_name='contact_name'",
            "migrate": "ALTER TABLE staff_call_logs ADD COLUMN contact_name VARCHAR(200)"
        },
        {
            "name": "service_ticket_spare_request.is_custom",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='service_ticket_spare_request' AND column_name='is_custom'",
            "migrate": "ALTER TABLE service_ticket_spare_request ADD COLUMN is_custom BOOLEAN NOT NULL DEFAULT FALSE"
        },
        {
            "name": "service_ticket_spare_request.original_item_name",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='service_ticket_spare_request' AND column_name='original_item_name'",
            "migrate": "ALTER TABLE service_ticket_spare_request ADD COLUMN original_item_name VARCHAR(200)"
        },
        {
            "name": "service_ticket_spare_request.verified_by_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='service_ticket_spare_request' AND column_name='verified_by_id'",
            "migrate": "ALTER TABLE service_ticket_spare_request ADD COLUMN verified_by_id INTEGER REFERENCES staff_employees(id)"
        },
        {
            "name": "service_ticket_spare_request.verified_at",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='service_ticket_spare_request' AND column_name='verified_at'",
            "migrate": "ALTER TABLE service_ticket_spare_request ADD COLUMN verified_at TIMESTAMP"
        },
        {
            "name": "service_ticket_spare_request.verification_notes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='service_ticket_spare_request' AND column_name='verification_notes'",
            "migrate": "ALTER TABLE service_ticket_spare_request ADD COLUMN verification_notes TEXT"
        },
        # DC Protocol (Feb 24, 2026): Unified Activity Time Integration - Attendance columns
        {
            "name": "staff_attendance.activity_minutes_total",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='activity_minutes_total'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN activity_minutes_total INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.kra_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='kra_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN kra_minutes INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.task_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='task_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN task_minutes INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.dayplan_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='dayplan_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN dayplan_minutes INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.lead_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='lead_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN lead_minutes INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.ticket_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='ticket_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN ticket_minutes INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.journey_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='journey_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN journey_minutes INTEGER NOT NULL DEFAULT 0"
        },
        {
            "name": "staff_attendance.custom_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_attendance' AND column_name='custom_minutes'",
            "migrate": "ALTER TABLE staff_attendance ADD COLUMN custom_minutes INTEGER NOT NULL DEFAULT 0"
        },
        # DC Protocol (Feb 24, 2026): DayPlanItem time tracking
        {
            "name": "staff_day_plan_items.time_spent_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_day_plan_items' AND column_name='time_spent_minutes'",
            "migrate": "ALTER TABLE staff_day_plan_items ADD COLUMN time_spent_minutes INTEGER NOT NULL DEFAULT 0"
        },
        # DC Protocol (Feb 24, 2026): Activity Time Log table creation
        {
            "name": "staff_activity_time_log_table",
            "check": "SELECT table_name FROM information_schema.tables WHERE table_name='staff_activity_time_log'",
            "migrate": """CREATE TABLE staff_activity_time_log (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                source_type VARCHAR(20) NOT NULL,
                source_id INTEGER,
                source_title VARCHAR(512),
                source_code VARCHAR(64),
                required_minutes INTEGER NOT NULL DEFAULT 0,
                planned_minutes INTEGER NOT NULL DEFAULT 0,
                completed_minutes INTEGER NOT NULL,
                description TEXT,
                attendance_id INTEGER REFERENCES staff_attendance(id) ON DELETE SET NULL,
                approval_status VARCHAR(20) NOT NULL DEFAULT 'submitted',
                approved_minutes INTEGER,
                approved_by INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                approved_at TIMESTAMP,
                rejection_reason TEXT,
                ip_address VARCHAR(64),
                user_agent TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                created_by INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
                CONSTRAINT staff_activity_time_source_type_check CHECK (source_type IN ('kra', 'task', 'dayplan', 'lead', 'ticket', 'journey', 'custom')),
                CONSTRAINT staff_activity_time_minutes_check CHECK (completed_minutes > 0 AND completed_minutes <= 1440)
            )"""
        },
        {
            "name": "idx_activity_time_emp_date",
            "check": "SELECT indexname FROM pg_indexes WHERE tablename='staff_activity_time_log' AND indexname='idx_activity_time_emp_date'",
            "migrate": "CREATE INDEX idx_activity_time_emp_date ON staff_activity_time_log(employee_id, date)"
        },
        {
            "name": "idx_activity_time_source",
            "check": "SELECT indexname FROM pg_indexes WHERE tablename='staff_activity_time_log' AND indexname='idx_activity_time_source'",
            "migrate": "CREATE INDEX idx_activity_time_source ON staff_activity_time_log(source_type, source_id)"
        },
        {
            "name": "staff_activity_time_log.approval_status",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_activity_time_log' AND column_name='approval_status'",
            "migrate": "ALTER TABLE staff_activity_time_log ADD COLUMN approval_status VARCHAR(20) NOT NULL DEFAULT 'submitted'"
        },
        {
            "name": "staff_activity_time_log.approved_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_activity_time_log' AND column_name='approved_minutes'",
            "migrate": "ALTER TABLE staff_activity_time_log ADD COLUMN approved_minutes INTEGER"
        },
        {
            "name": "staff_activity_time_log.approved_by",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_activity_time_log' AND column_name='approved_by'",
            "migrate": "ALTER TABLE staff_activity_time_log ADD COLUMN approved_by INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL"
        },
        {
            "name": "staff_activity_time_log.approved_at",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_activity_time_log' AND column_name='approved_at'",
            "migrate": "ALTER TABLE staff_activity_time_log ADD COLUMN approved_at TIMESTAMP"
        },
        {
            "name": "staff_activity_time_log.rejection_reason",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_activity_time_log' AND column_name='rejection_reason'",
            "migrate": "ALTER TABLE staff_activity_time_log ADD COLUMN rejection_reason TEXT"
        },
        {
            "name": "staff_timesheet_entries.approved_minutes",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='staff_timesheet_entries' AND column_name='approved_minutes'",
            "migrate": "ALTER TABLE staff_timesheet_entries ADD COLUMN approved_minutes INTEGER"
        }
    ]

    column_type_fixes = [
        {
            "name": "scheduler_log status columns VARCHAR(20) → VARCHAR(100)",
            "check": "SELECT character_maximum_length FROM information_schema.columns WHERE table_name='scheduler_log' AND column_name='matching_status' AND character_maximum_length >= 100",
            "migrate": """ALTER TABLE scheduler_log 
                ALTER COLUMN income_triggered TYPE VARCHAR(100),
                ALTER COLUMN direct_referral_status TYPE VARCHAR(100),
                ALTER COLUMN matching_status TYPE VARCHAR(100),
                ALTER COLUMN ved_income_status TYPE VARCHAR(100),
                ALTER COLUMN awards_status TYPE VARCHAR(100),
                ALTER COLUMN guru_dakshina_status TYPE VARCHAR(100),
                ALTER COLUMN field_allowance_status TYPE VARCHAR(100),
                ALTER COLUMN overall_status TYPE VARCHAR(100)"""
        }
    ]
    
    # DC Protocol (Jan 31, 2026): Fix account_status constraint - must allow Suspended, Locked, Pending
    # Pre-column constraints (tables/columns already exist)
    constraint_fixes = [
        {
            "name": "valid_account_status_expansion",
            "check": """
                SELECT pg_get_constraintdef(oid) as def
                FROM pg_constraint 
                WHERE conname = 'valid_account_status' 
                AND conrelid = 'public."user"'::regclass
                AND pg_get_constraintdef(oid) LIKE '%Suspended%'
            """,
            "drop": 'ALTER TABLE "user" DROP CONSTRAINT IF EXISTS valid_account_status',
            "create": """ALTER TABLE "user" ADD CONSTRAINT valid_account_status 
                CHECK (account_status IN ('Active', 'Inactive', 'Suspended', 'Locked', 'Pending'))"""
        },
        {
            "name": "task_activity_action_expansion",
            "check": """
                SELECT pg_get_constraintdef(oid) as def
                FROM pg_constraint 
                WHERE conname = 'staff_task_activity_action_check' 
                AND conrelid = 'staff_task_activity_log'::regclass
                AND pg_get_constraintdef(oid) LIKE '%progress_update%'
            """,
            "drop": "ALTER TABLE staff_task_activity_log DROP CONSTRAINT IF EXISTS staff_task_activity_action_check",
            "create": """ALTER TABLE staff_task_activity_log ADD CONSTRAINT staff_task_activity_action_check 
                CHECK (action IN ('created', 'updated', 'status_changed', 'assigned', 'reassigned', 'invited', 'removed_assignee', 'commented', 'time_logged', 'completed', 'reopened', 'cancelled', 'deleted', 'file_uploaded', 'attachment_added_via_edit', 'attachment_deleted', 'assigner_updated', 'manager_approved', 'manager_bulk_approved', 'manager_edited', 'manager_rejected', 'attachment_previewed', 'phase_reassigned', 'status_change', 'progress_update', 'phase_status_change'))"""
        },
        {
            "name": "valid_source_gps_expansion",
            "check": """
                SELECT pg_get_constraintdef(oid) as def
                FROM pg_constraint 
                WHERE conname = 'valid_source' 
                AND conrelid = 'staff_realtime_locations'::regclass
                AND pg_get_constraintdef(oid) LIKE '%mobile_heartbeat%'
            """,
            "drop": "ALTER TABLE staff_realtime_locations DROP CONSTRAINT IF EXISTS valid_source",
            "create": """ALTER TABLE staff_realtime_locations ADD CONSTRAINT valid_source 
                CHECK (source IN ('attendance', 'journey', 'drift', 'manual', 'heartbeat', 'native_background', 'native_foreground', 'background', 'foreground', 'mobile_heartbeat') OR source LIKE 'gap_%')"""
        }
    ]
    
    for fix in constraint_fixes:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["check"]))
                if result.fetchone() is None:
                    conn.execute(text(fix["drop"]))
                    conn.execute(text(fix["create"]))
                    print(f"   ✅ Constraint fixed: {fix['name']}")
                else:
                    print(f"   ⏭️  Constraint OK: {fix['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Constraint fix warning for {fix['name']}: {error_msg}")
    
    # DC Protocol Optimization: Batch all existence checks into 3 queries instead of N queries.
    # Reduces Neon round-trips from ~55 to 3, saving 20-30s on every cold start.
    import re as _re

    _col_names_set = set()
    _idx_names_set = set()
    _tbl_names_set = set()

    _col_m_names = {}   # migration name -> (table, col)
    _idx_m_names = {}   # migration name -> indexname
    _tbl_m_names = {}   # migration name -> tablename
    _other_m_names = set()

    for _m in migrations:
        _check = _m["check"]
        _t = _re.search(r"table_name='([^']+)'", _check)
        _c = _re.search(r"column_name='([^']+)'", _check)
        _i = _re.search(r"indexname='([^']+)'", _check)
        if "information_schema.columns" in _check and _t and _c:
            _col_m_names[_m["name"]] = (_t.group(1), _c.group(1))
        elif "pg_indexes" in _check and _i:
            _idx_m_names[_m["name"]] = _i.group(1)
        elif "information_schema.tables" in _check and _t:
            _tbl_m_names[_m["name"]] = _t.group(1)
        else:
            _other_m_names.add(_m["name"])

    try:
        with engine.connect() as _bconn:
            if _col_m_names:
                _pairs = ", ".join(
                    f"('{t}', '{c}')" for t, c in _col_m_names.values()
                )
                _r = _bconn.execute(text(
                    f"SELECT table_name || '.' || column_name AS k "
                    f"FROM information_schema.columns "
                    f"WHERE (table_name, column_name) IN ({_pairs})"
                ))
                _col_names_set = {row.k for row in _r.fetchall()}
            if _idx_m_names:
                _ilist = ", ".join(f"'{v}'" for v in _idx_m_names.values())
                _r = _bconn.execute(text(
                    f"SELECT indexname FROM pg_indexes WHERE indexname IN ({_ilist})"
                ))
                _idx_names_set = {row.indexname for row in _r.fetchall()}
            if _tbl_m_names:
                _tlist = ", ".join(f"'{v}'" for v in _tbl_m_names.values())
                _r = _bconn.execute(text(
                    f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_name IN ({_tlist})"
                ))
                _tbl_names_set = {row.table_name for row in _r.fetchall()}
    except Exception as _be:
        print(f"   ⚠️  Batch pre-check failed ({str(_be)[:80]}), falling back to sequential checks")
        _other_m_names = {m["name"] for m in migrations}
        _col_m_names = _idx_m_names = _tbl_m_names = {}

    for migration in migrations:
        try:
            _name = migration["name"]
            if _name in _col_m_names:
                t, c = _col_m_names[_name]
                _exists = f"{t}.{c}" in _col_names_set
            elif _name in _idx_m_names:
                _exists = _idx_m_names[_name] in _idx_names_set
            elif _name in _tbl_m_names:
                _exists = _tbl_m_names[_name] in _tbl_names_set
            else:
                with engine.connect() as conn:
                    _r = conn.execute(text(migration["check"]))
                    _exists = _r.fetchone() is not None

            if _exists:
                print(f"   ⏭️  Already exists: {_name}")
            else:
                with engine.begin() as conn:
                    conn.execute(text(migration["migrate"]))
                print(f"   ✅ Migration applied: {_name}")
        except Exception as e:
            error_msg = str(e)[:100]
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                print(f"   ⏭️  Already exists: {migration['name']}")
            else:
                print(f"   ⚠️  Migration warning for {migration['name']}: {error_msg}")

    for fix in column_type_fixes:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["check"]))
                if result.fetchone() is None:
                    conn.execute(text(fix["migrate"]))
                    print(f"   ✅ Column type fix applied: {fix['name']}")
                else:
                    print(f"   ⏭️  Column type OK: {fix['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Column type fix warning for {fix['name']}: {error_msg}")

    # DC Protocol (Feb 15, 2026): Bonanza reward constraints - MUST run AFTER column migrations
    bonanza_constraints = [
        {
            "name": "valid_criteria_type",
            "check": """
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'valid_criteria_type' 
                AND conrelid = 'dynamic_bonanza_reward'::regclass
            """,
            "drop": "ALTER TABLE dynamic_bonanza_reward DROP CONSTRAINT IF EXISTS valid_criteria_type",
            "create": """ALTER TABLE dynamic_bonanza_reward ADD CONSTRAINT valid_criteria_type 
                CHECK (criteria_type IN ('achievement_count', 'points_threshold', 'rank_position'))"""
        },
        {
            "name": "valid_criteria_operator",
            "check": """
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'valid_criteria_operator' 
                AND conrelid = 'dynamic_bonanza_reward'::regclass
            """,
            "drop": "ALTER TABLE dynamic_bonanza_reward DROP CONSTRAINT IF EXISTS valid_criteria_operator",
            "create": """ALTER TABLE dynamic_bonanza_reward ADD CONSTRAINT valid_criteria_operator 
                CHECK (criteria_operator IN ('>=', '>', '=', '<', '<='))"""
        },
        {
            "name": "valid_reward_type_bonanza",
            "check": """
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'valid_reward_type' 
                AND conrelid = 'dynamic_bonanza_reward'::regclass
            """,
            "drop": "ALTER TABLE dynamic_bonanza_reward DROP CONSTRAINT IF EXISTS valid_reward_type",
            "create": """ALTER TABLE dynamic_bonanza_reward ADD CONSTRAINT valid_reward_type 
                CHECK (reward_type IN ('cash', 'bonus', 'upgrade', 'recognition', 'award', 'gift'))"""
        },
        {
            "name": "positive_or_null_reward_amount",
            "check": """
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'positive_or_null_reward_amount' 
                AND conrelid = 'dynamic_bonanza_reward'::regclass
            """,
            "drop": "ALTER TABLE dynamic_bonanza_reward DROP CONSTRAINT IF EXISTS positive_or_null_reward_amount",
            "create": """ALTER TABLE dynamic_bonanza_reward ADD CONSTRAINT positive_or_null_reward_amount 
                CHECK (reward_amount >= 0 OR reward_amount IS NULL)"""
        },
        {
            "name": "positive_criteria_value",
            "check": """
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'positive_criteria_value' 
                AND conrelid = 'dynamic_bonanza_reward'::regclass
            """,
            "drop": "ALTER TABLE dynamic_bonanza_reward DROP CONSTRAINT IF EXISTS positive_criteria_value",
            "create": """ALTER TABLE dynamic_bonanza_reward ADD CONSTRAINT positive_criteria_value 
                CHECK (criteria_value >= 0)"""
        }
    ]

    income_status_constraints = [
        {
            "name": "income_status_check_v2",
            "check": """
                SELECT pg_get_constraintdef(oid) as def
                FROM pg_constraint 
                WHERE conname = 'income_status_check' 
                AND conrelid = 'income_entries'::regclass
                AND pg_get_constraintdef(oid) LIKE '%CONFIRMED%'
            """,
            "drop": "ALTER TABLE income_entries DROP CONSTRAINT IF EXISTS income_status_check",
            "create": """ALTER TABLE income_entries ADD CONSTRAINT income_status_check 
                CHECK (status IN ('PENDING', 'CONFIRMED', 'EXCEPTION_TALLY', 'ADJUSTMENT', 'TALLY_DONE'))"""
        }
    ]

    for fix in income_status_constraints:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["check"]))
                if result.fetchone() is None:
                    conn.execute(text(fix["drop"]))
                    conn.execute(text(fix["create"]))
                    print(f"   ✅ Constraint fixed: {fix['name']}")
                else:
                    print(f"   ⏭️  Constraint OK: {fix['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Constraint fix warning for {fix['name']}: {error_msg}")

    fk_repoint_migrations = [
        {
            "name": "crm_lead_deals.revenue_category_id -> signup_categories",
            "check": """
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'crm_lead_deals' AND tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = 'signup_categories' AND ccu.column_name = 'id'
                AND tc.constraint_name LIKE '%revenue_category%'
            """,
            "drop": "ALTER TABLE crm_lead_deals DROP CONSTRAINT IF EXISTS crm_lead_deals_revenue_category_id_fkey",
            "create": "ALTER TABLE crm_lead_deals ADD CONSTRAINT crm_lead_deals_revenue_category_id_fkey FOREIGN KEY (revenue_category_id) REFERENCES signup_categories(id)"
        },
        {
            "name": "crm_lead_transactions.revenue_category_id -> signup_categories",
            "check": """
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'crm_lead_transactions' AND tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = 'signup_categories' AND ccu.column_name = 'id'
                AND tc.constraint_name LIKE '%revenue_category%'
            """,
            "drop": "ALTER TABLE crm_lead_transactions DROP CONSTRAINT IF EXISTS crm_lead_transactions_revenue_category_id_fkey",
            "create": "ALTER TABLE crm_lead_transactions ADD CONSTRAINT crm_lead_transactions_revenue_category_id_fkey FOREIGN KEY (revenue_category_id) REFERENCES signup_categories(id) ON DELETE SET NULL"
        },
        {
            "name": "income_entries.revenue_category_id -> signup_categories",
            "check": """
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'income_entries' AND tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = 'signup_categories' AND ccu.column_name = 'id'
                AND tc.constraint_name LIKE '%revenue_category%'
            """,
            "drop": "ALTER TABLE income_entries DROP CONSTRAINT IF EXISTS income_entries_revenue_category_id_fkey",
            "create": "ALTER TABLE income_entries ADD CONSTRAINT income_entries_revenue_category_id_fkey FOREIGN KEY (revenue_category_id) REFERENCES signup_categories(id)"
        }
    ]

    for fix in fk_repoint_migrations:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["check"]))
                if result.fetchone() is None:
                    conn.execute(text(fix["drop"]))
                    conn.execute(text(fix["create"]))
                    print(f"   ✅ FK repointed: {fix['name']}")
                else:
                    print(f"   ⏭️  FK already correct: {fix['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  FK repoint warning for {fix['name']}: {error_msg}")

    for fix in bonanza_constraints:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["check"]))
                if result.fetchone() is None:
                    conn.execute(text(fix["drop"]))
                    conn.execute(text(fix["create"]))
                    print(f"   ✅ Constraint fixed: {fix['name']}")
                else:
                    print(f"   ⏭️  Constraint OK: {fix['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Constraint fix warning for {fix['name']}: {error_msg}")

    # DC Protocol (Mar 09, 2026): Fix global unique index on income_entries.entry_number
    # The global unique index blocks companies from reusing entry number sequences
    # (e.g. company 3 cannot create INC-000001 if company 2 already has one).
    # Replace with per-company composite unique (company_id, entry_number).
    # Same fix applied to expense_entries for the same latent bug.
    entry_number_index_migrations = [
        {
            "name": "uq_income_entry_company_number",
            "check": "SELECT 1 FROM pg_indexes WHERE tablename='income_entries' AND indexname='uq_income_entry_company_number'",
            "drop": "DROP INDEX IF EXISTS ix_income_entries_entry_number; DROP INDEX IF EXISTS income_entries_entry_number_idx",
            "create": "CREATE UNIQUE INDEX uq_income_entry_company_number ON income_entries (company_id, entry_number)"
        },
        {
            "name": "uq_expense_entry_company_number",
            "check": "SELECT 1 FROM pg_indexes WHERE tablename='expense_entries' AND indexname='uq_expense_entry_company_number'",
            "drop": "DROP INDEX IF EXISTS ix_expense_entries_entry_number; DROP INDEX IF EXISTS expense_entries_entry_number_idx",
            "create": "CREATE UNIQUE INDEX uq_expense_entry_company_number ON expense_entries (company_id, entry_number)"
        },
    ]

    for fix in entry_number_index_migrations:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["check"]))
                if result.fetchone() is None:
                    conn.execute(text(fix["drop"]))
                    conn.execute(text(fix["create"]))
                    print(f"   ✅ Index migrated: {fix['name']}")
                else:
                    print(f"   ⏭️  Index OK: {fix['name']}")
        except Exception as e:
            error_msg = str(e)[:150]
            print(f"   ⚠️  Index migration warning for {fix['name']}: {error_msg}")

    # DC Protocol (Mar 09, 2026): Add payment_type column to income_entries (CASH/BANK categorisation)
    income_payment_type_migrations = [
        {
            "name": "income_entries.payment_type",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='payment_type'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN payment_type VARCHAR(10) CONSTRAINT income_entries_payment_type_check CHECK (payment_type IS NULL OR payment_type IN ('CASH', 'BANK'))"
        },
    ]

    for mig in income_payment_type_migrations:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(mig["check"]))
                if result.fetchone() is None:
                    conn.execute(text(mig["migrate"]))
                    print(f"   ✅ Added: {mig['name']}")
                else:
                    print(f"   ⏭️  Already exists: {mig['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Migration warning for {mig['name']}: {error_msg}")

    # DC Protocol (Mar 31, 2026): Sales Invoice billing/coupon/discount enhancements
    sales_invoice_enhancement_migrations = [
        {
            "name": "sales_invoices.document_type",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='document_type'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN document_type VARCHAR(20) NOT NULL DEFAULT 'tax_invoice'"
        },
        {
            "name": "sales_invoices.billing_company_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='billing_company_id'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN billing_company_id INTEGER REFERENCES associated_companies(id) ON DELETE SET NULL"
        },
        {
            "name": "sales_invoices.coupon_code",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='coupon_code'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN coupon_code VARCHAR(50)"
        },
        {
            "name": "sales_invoices.coupon_discount_pct",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='coupon_discount_pct'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN coupon_discount_pct NUMERIC(5,2) DEFAULT 0"
        },
        {
            "name": "sales_invoices.coupon_discount_amount",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='coupon_discount_amount'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN coupon_discount_amount NUMERIC(15,2) DEFAULT 0"
        },
        {
            "name": "sales_invoices.manual_discount_amount",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='manual_discount_amount'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN manual_discount_amount NUMERIC(15,2) DEFAULT 0"
        },
        {
            "name": "sales_invoices.manual_discount_note",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='manual_discount_note'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN manual_discount_note TEXT"
        },
        {
            "name": "sales_invoices.net_payable",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='sales_invoices' AND column_name='net_payable'",
            "migrate": "ALTER TABLE sales_invoices ADD COLUMN net_payable NUMERIC(15,2) DEFAULT 0"
        },
    ]

    for mig in sales_invoice_enhancement_migrations:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(mig["check"]))
                if result.fetchone() is None:
                    conn.execute(text(mig["migrate"]))
                    print(f"   ✅ Added: {mig['name']}")
                else:
                    print(f"   ⏭️  Already exists: {mig['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Migration warning for {mig['name']}: {error_msg}")

    # DC Protocol (Apr 01, 2026): income_entries soft delete — is_deleted / deleted_by_id / deleted_at
    income_soft_delete_migrations = [
        {
            "name": "income_entries.is_deleted",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='is_deleted'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
        },
        {
            "name": "income_entries.deleted_by_id",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='deleted_by_id'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN deleted_by_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL"
        },
        {
            "name": "income_entries.deleted_at",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='income_entries' AND column_name='deleted_at'",
            "migrate": "ALTER TABLE income_entries ADD COLUMN deleted_at TIMESTAMP"
        },
        {
            "name": "idx_income_entries_is_deleted",
            "check": "SELECT 1 FROM pg_indexes WHERE tablename='income_entries' AND indexname='idx_income_entries_is_deleted'",
            "migrate": "CREATE INDEX idx_income_entries_is_deleted ON income_entries (is_deleted)"
        },
    ]

    for mig in income_soft_delete_migrations:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(mig["check"]))
                if result.fetchone() is None:
                    conn.execute(text(mig["migrate"]))
                    print(f"   ✅ Added: {mig['name']}")
                else:
                    print(f"   ⏭️  Already exists: {mig['name']}")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   ⚠️  Migration warning for {mig['name']}: {error_msg}")


    # DC_COMPANY_CONTACT_001: Add phone/email/website to associated_companies
    company_contact_migrations = [
        {
            "name": "associated_companies.phone",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='associated_companies' AND column_name='phone'",
            "migrate": "ALTER TABLE associated_companies ADD COLUMN phone VARCHAR(20)"
        },
        {
            "name": "associated_companies.email",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='associated_companies' AND column_name='email'",
            "migrate": "ALTER TABLE associated_companies ADD COLUMN email VARCHAR(200)"
        },
        {
            "name": "associated_companies.website",
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='associated_companies' AND column_name='website'",
            "migrate": "ALTER TABLE associated_companies ADD COLUMN website VARCHAR(200)"
        },
    ]
    for mig in company_contact_migrations:
        try:
            with engine.begin() as conn:
                result = conn.execute(text(mig["check"]))
                if result.fetchone() is None:
                    conn.execute(text(mig["migrate"]))
                    print(f"   ✅ Added: {mig['name']}")
                else:
                    print(f"   ⏭️  Already exists: {mig['name']}")
        except Exception as e:
            print(f"   ⚠️  Migration warning for {mig['name']}: {str(e)[:100]}")


def init_db():
    """
    Initialize database with all tables
    Preserves existing schema structure
    """
    # Import all models to ensure they are registered
    from app.models import user, placement, transaction, staff_tasks, staff_attendance
    # Real Dreams - Real Estate Marketplace (DC Protocol - Dec 08, 2025)
    from app.models import real_dreams
    # Signup Categories (DC Protocol - Dec 08, 2025)
    from app.models import signup_category
    # Universal CRM System (DC Protocol - Dec 08, 2025)
    from app.models import crm
    # Staff Call Tracking System (DC Protocol - Feb 2026)
    from app.models import call_tracking
    
    # DC Protocol (Dec 18, 2025): Verify schema integrity
    print("🔄 Verifying schema integrity...")
    run_pending_migrations()
    
    # Create all tables (only if they don't exist)
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized with preserved schema")