"""
MYNT OS — V18 Database DDL & Seed Migration
Creates incentive_programs & position_rate_configs tables if not present,
adds index optimizations, and seeds Solar V2 position rate configurations.
"""

import sys
sys.path.insert(0, '/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend')

from app.core.database import SessionLocal
from sqlalchemy import text

def run_v18_migration():
    db = SessionLocal()
    try:
        print("[MIGRATION-V18] Creating tables if not existing...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS incentive_programs (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL DEFAULT 1,
                segment_code VARCHAR(30) NOT NULL,
                program_code VARCHAR(50) NOT NULL UNIQUE,
                program_name VARCHAR(200) NOT NULL,
                max_pool_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS position_rate_configs (
                id SERIAL PRIMARY KEY,
                program_id INTEGER NOT NULL REFERENCES incentive_programs(id) ON DELETE CASCADE,
                position_name VARCHAR(40) NOT NULL,
                stars INTEGER NOT NULL DEFAULT 1,
                required_active_team INTEGER NOT NULL DEFAULT 0,
                required_qualifying_files INTEGER NOT NULL DEFAULT 0,
                commission_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
                base_income_amount NUMERIC(12, 2) DEFAULT 0.0,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_crm_leads_partner_status ON crm_leads(associated_partner_id, solar_pipeline_status);
            CREATE INDEX IF NOT EXISTS idx_official_partners_parent ON official_partners(parent_partner_id);
            CREATE INDEX IF NOT EXISTS idx_vci_source_lead ON vgk_cash_income_entries(source_lead_id);
            CREATE INDEX IF NOT EXISTS idx_advances_lead_partner ON vgk_solar_cibil_advances(lead_id, partner_id);
        """))
        db.commit()

        # Seed Solar V2 Program
        prog = db.execute(text("SELECT id FROM incentive_programs WHERE program_code = 'SOLAR_V2_2026'")).fetchone()
        if not prog:
            res = db.execute(text("""
                INSERT INTO incentive_programs (company_id, segment_code, program_code, program_name, max_pool_pct, is_active)
                VALUES (1, 'SOLAR', 'SOLAR_V2_2026', 'Solar V2 Universal Incentive Program 2026', 8.50, TRUE)
                RETURNING id
            """)).fetchone()
            prog_id = res[0]
            
            ranks = [
                {"position": "Channel Partner", "stars": 1, "req_active_team": 0, "req_files": 0, "pct": 5.00, "amount": 10000.00},
                {"position": "Manager", "stars": 2, "req_active_team": 2, "req_files": 0, "pct": 6.50, "amount": 13000.00},
                {"position": "Zonal Manager", "stars": 3, "req_active_team": 10, "req_files": 0, "pct": 7.50, "amount": 15000.00},
                {"position": "Regional Manager", "stars": 4, "req_active_team": 25, "req_files": 0, "pct": 8.25, "amount": 16500.00},
                {"position": "Director", "stars": 5, "req_active_team": 50, "req_files": 0, "pct": 8.50, "amount": 17000.00},
            ]
            for r in ranks:
                db.execute(text("""
                    INSERT INTO position_rate_configs 
                    (program_id, position_name, stars, required_active_team, required_qualifying_files, commission_pct, base_income_amount)
                    VALUES (:pid, :name, :stars, :rat, :rqf, :pct, :amt)
                """), {
                    'pid': prog_id,
                    'name': r['position'],
                    'stars': r['stars'],
                    'rat': r['req_active_team'],
                    'rqf': r['req_files'],
                    'pct': r['pct'],
                    'amt': r['amount']
                })
            db.commit()
            print("[MIGRATION-V18] Successfully seeded Solar V2 position rates into DB.")
        else:
            print("[MIGRATION-V18] Solar V2 program already seeded.")

    except Exception as e:
        db.rollback()
        print(f"[MIGRATION-V18] Error: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_v18_migration()
