"""
MYNT OS — V22 Monthly Settlement Idempotency Migration
Creates monthly_settlement_batches table with UNIQUE(partner_id, settlement_period, program_id)
composite index to enforce DB-level atomic idempotency.
"""

import sys
sys.path.insert(0, '/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend')

from app.core.database import SessionLocal
from sqlalchemy import text

def run_v22_migration():
    db = SessionLocal()
    try:
        print("[MIGRATION-V22] Creating monthly_settlement_batches table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS monthly_settlement_batches (
                id SERIAL PRIMARY KEY,
                partner_id INTEGER NOT NULL REFERENCES official_partners(id) ON DELETE RESTRICT,
                settlement_period VARCHAR(7) NOT NULL,
                program_id INTEGER NOT NULL REFERENCES incentive_programs(id) ON DELETE RESTRICT,
                net_payable NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
                status VARCHAR(20) NOT NULL DEFAULT 'PROCESSED',
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_monthly_settlement_partner_period UNIQUE (partner_id, settlement_period, program_id)
            );

            CREATE INDEX IF NOT EXISTS idx_monthly_settlement_partner ON monthly_settlement_batches(partner_id);
            CREATE INDEX IF NOT EXISTS idx_monthly_settlement_period ON monthly_settlement_batches(settlement_period);
            CREATE INDEX IF NOT EXISTS idx_monthly_settlement_program ON monthly_settlement_batches(program_id);
        """))
        db.commit()
        print("[MIGRATION-V22] Successfully created monthly_settlement_batches table with UNIQUE constraint.")
    except Exception as e:
        db.rollback()
        print(f"[MIGRATION-V22] Error creating table: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_v22_migration()
