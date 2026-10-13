"""
DC Protocol Migration: Add T-Shirt Size/Given, Kit Given, and Insurance Record fields to official_partners.
Key: DC_VGK_KIT_INSURANCE_20261013_001
Additive-only changes.
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.database import engine
from sqlalchemy import text


def run_migration():
    migration_key = "DC_VGK_KIT_INSURANCE_20261013_001"
    print(f"[{migration_key}] Starting migration...")
    with engine.begin() as conn:
        # Check if already applied in dc_migrations
        res = conn.execute(text("SELECT 1 FROM dc_migrations WHERE key = :key"), {"key": migration_key}).scalar()
        if res:
            print(f"[{migration_key}] Already applied according to dc_migrations. Checking schema...")
        
        # Add columns additively
        columns = [
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS t_shirt_size VARCHAR(10)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS t_shirt_given BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS t_shirt_given_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS t_shirt_given_by VARCHAR(50)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS kit_given BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS kit_given_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS kit_given_by VARCHAR(50)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_given BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_given_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_policy_number VARCHAR(100)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_provider VARCHAR(100)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_amount NUMERIC(12, 2) DEFAULT 0.00",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_valid_from DATE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_valid_till DATE",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_nominee_name VARCHAR(200)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_nominee_relation VARCHAR(50)",
            "ALTER TABLE official_partners ADD COLUMN IF NOT EXISTS insurance_details TEXT",
            "CREATE INDEX IF NOT EXISTS idx_op_t_shirt_given ON official_partners (t_shirt_given)",
            "CREATE INDEX IF NOT EXISTS idx_op_kit_given ON official_partners (kit_given)",
            "CREATE INDEX IF NOT EXISTS idx_op_insurance_given ON official_partners (insurance_given)",
            "CREATE INDEX IF NOT EXISTS idx_op_t_shirt_size ON official_partners (t_shirt_size)"
        ]

        for stmt in columns:
            conn.execute(text(stmt))
        
        # Record migration key in dc_migrations
        conn.execute(text("INSERT INTO dc_migrations (key) VALUES (:key) ON CONFLICT DO NOTHING"), {"key": migration_key})
        print(f"[{migration_key}] Migration completed and recorded successfully.")


if __name__ == "__main__":
    run_migration()
