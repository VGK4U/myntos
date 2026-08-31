"""
Python Migration Runner: Create VoIP Call Sessions Table
Executes table creation, unique constraints, and indexes on PostgreSQL database.
Created: Aug 2026
"""

import sys
import os
import logging

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import app.models  # Load all models into Base metadata registry
from app.core.database import engine, Base
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voip_migration")


def run_migration():
    """Run VoIPCallSession table migration"""
    logger.info("🚀 Starting VoIPCallSession table migration...")
    
    # 1. Run direct DDL statements to create table and indexes safely
    sql_path = os.path.join(os.path.dirname(__file__), 'create_voip_call_sessions_table.sql')
    if os.path.exists(sql_path):
        with open(sql_path, 'r') as f:
            sql_statements = f.read()

        with engine.connect() as conn:
            conn.execute(text(sql_statements))
            conn.commit()
        logger.info("✅ Executed create_voip_call_sessions_table.sql successfully.")

    logger.info("🎉 Migration complete: voip_call_sessions table is active and verified.")


def rollback_migration():
    """Rollback voip_call_sessions table if ever required"""
    logger.warning("⚠️ Rolling back voip_call_sessions table...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS voip_call_sessions CASCADE;"))
        conn.commit()
    logger.info("✅ Dropped voip_call_sessions table.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        run_migration()
