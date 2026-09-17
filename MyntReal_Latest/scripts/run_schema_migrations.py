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
_root_dir = Path(__file__).resolve().parent.parent
_backend_dir = _root_dir / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_runner")

def run_migrations():
    logger.info("==================================================")
    logger.info("MyntOS Standalone Schema Migration Runner Starting")
    logger.info("==================================================")
    
    # 1. Check DB connectivity
    from app.core.database import engine, SessionLocal
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connectivity verified")
    except Exception as e:
        logger.error(f"❌ Cannot connect to database: {e}")
        sys.exit(1)
        
    # 2. Run Schema Bootstrap routines
    try:
        from app.core.schema_bootstrap import run_schema_bootstrap
        logger.info("Running schema bootstrap routines...")
        run_schema_bootstrap()
        logger.info("✅ Schema bootstrap complete")
    except Exception as e:
        logger.error(f"❌ Schema bootstrap failed: {e}")
        sys.exit(1)
        
    logger.info("==================================================")
    logger.info("All Migrations Verified / Applied Successfully")
    logger.info("==================================================")

if __name__ == "__main__":
    run_migrations()
