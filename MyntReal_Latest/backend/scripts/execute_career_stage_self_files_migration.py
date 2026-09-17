"""
Migration Script: Apply Stage-Wise Personal Qualifying Files to Dev and RDS Databases
Date: 2026-09-17
Enforces:
1. Add stage_own_qualifying_files column to vgk4u_career_designation_configs
2. Update hierarchy_order rows:
   Order 0 (Member): stage = 0, cumulative = 0
   Order 1 (Channel Partner): stage = 1, cumulative = 1
   Order 2 (Senior): stage = 3, cumulative = 4
   Order 3 (Extended): stage = 5, cumulative = 9
   Order 4 (Core): stage = 7, cumulative = 16
"""

import os
import sys
from sqlalchemy import create_engine, text

MIGRATION_SQL = """
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
"""

VERIFY_SQL = """
SELECT hierarchy_order, designation_code, designation_name,
       stage_own_qualifying_files, required_own_qualifying_files,
       required_active_team_members, self_earning_pct, team_differential_pct
FROM vgk4u_career_designation_configs
ORDER BY hierarchy_order ASC;
"""

def apply_migration(db_url: str, db_name: str):
    print(f"\n[MIGRATE] Connecting to {db_name} ({db_url[:45]}...)...")
    try:
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text(MIGRATION_SQL))
            print(f"[MIGRATE] ✅ Migration SQL executed successfully on {db_name}")
            
            # Verify results
            rows = conn.execute(text(VERIFY_SQL)).fetchall()
            print(f"[MIGRATE] Verified {len(rows)} configuration rows on {db_name}:")
            for r in rows:
                print(f"  Order {r[0]}: {r[1]} ({r[2]}) -> Stage Files: {r[3]}, Cumulative Files: {r[4]}, Active Legs: {r[5]}, Self%: {r[6]}%, Diff%: {r[7]}%")
        engine.dispose()
    except Exception as e:
        print(f"[MIGRATE] ❌ ERROR migrating {db_name}: {e}")
        raise

if __name__ == '__main__':
    dev_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5433/myntreal_dev')
    rds_url = os.environ.get('PROD_DATABASE_URL', 'postgresql://postgres:MyntRealAdmin2026!@myntreal-database.c5gywaicq6zu.ap-south-2.rds.amazonaws.com:5432/postgres')

    print("=== STARTING STAGE-WISE SELF FILES MIGRATION ===")
    
    # 1. Local Dev DB
    apply_migration(dev_url, "LOCAL DEV DB")
    
    # 2. Production RDS DB
    apply_migration(rds_url, "PRODUCTION RDS DB")
    
    print("\n=== MIGRATION COMPLETED ON ALL ENVIRONMENTS ===")
