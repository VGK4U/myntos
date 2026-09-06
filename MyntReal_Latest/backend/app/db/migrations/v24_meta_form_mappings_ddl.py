"""
MYNT OS — V24 Meta Form Mappings Persistent Registry DDL Migration
Creates meta_form_mappings table for configuration-driven multi-tenant form routing.
Enables registering new Meta Lead Forms dynamically without source code changes.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.database import SessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def run_v24_migration():
    print("[MIGRATION-V24] Starting Meta Form Mappings DDL migration...")
    db = SessionLocal()
    try:
        # 1. Create meta_form_mappings table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS meta_form_mappings (
                id SERIAL PRIMARY KEY,
                page_id VARCHAR(50) NOT NULL,
                form_id VARCHAR(50) NOT NULL UNIQUE,
                form_name VARCHAR(200),
                company_id INTEGER NOT NULL,
                category_id INTEGER,
                crm_segment VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
                segment_tag VARCHAR(50),
                looking_for VARCHAR(200),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_meta_form_mappings_page_id ON meta_form_mappings(page_id);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_meta_form_mappings_form_id ON meta_form_mappings(form_id);
            CREATE INDEX IF NOT EXISTS idx_meta_form_mappings_company_id ON meta_form_mappings(company_id);
        """))

        # 2. Seed verified real production Meta Lead Forms
        db.execute(text("""
            INSERT INTO meta_form_mappings 
                (page_id, form_id, form_name, company_id, category_id, crm_segment, segment_tag, looking_for, is_active, updated_at)
            VALUES 
                ('442395068958730', '1596737462160734', 'ETC - EV Career & Trading Leads - Telugu', 2, 16, 'EV_SPARES', 'etc_training', 'ETC Training', TRUE, NOW()),
                ('442395068958730', '629673922859072', 'Royal EV', 2, NULL, 'EV_SPARES', 'ev_spares', 'Royal EV', TRUE, NOW()),
                ('442395068958730', '816990717262052', 'EV Craze Leads Form', 2, NULL, 'EV_SPARES', 'ev_spares', 'EV Craze Dealership', TRUE, NOW()),
                ('894208310452980', '940528145175748', 'Har Ghar Solar Lead Form', 1, NULL, 'SOLAR', 'solar', 'Har Ghar Solar', TRUE, NOW())
            ON CONFLICT (form_id) DO UPDATE SET
                page_id = EXCLUDED.page_id,
                form_name = EXCLUDED.form_name,
                company_id = EXCLUDED.company_id,
                category_id = EXCLUDED.category_id,
                crm_segment = EXCLUDED.crm_segment,
                segment_tag = EXCLUDED.segment_tag,
                looking_for = EXCLUDED.looking_for,
                is_active = EXCLUDED.is_active,
                updated_at = NOW();
        """))

        db.commit()
        print("[MIGRATION-V24] Successfully created meta_form_mappings table and seeded verified live Meta forms.")

    except Exception as e:
        db.rollback()
        print(f"[MIGRATION-V24] Migration FAILED: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_v24_migration()
