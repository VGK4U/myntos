"""
MYNT OS — V23 Meta Lead Ads Idempotency & Database Hardening Migration
Adds UNIQUE constraint/index on meta_leads_attribution(meta_lead_id) to enforce
platform-level database idempotency against concurrent webhook retries & backfills.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.database import SessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def run_v23_migration():
    print("[MIGRATION-V23] Starting Meta Leads Idempotency DDL migration...")
    
    # 1. Pre-migration forensic data validation
    db = SessionLocal()
    try:
        print("[MIGRATION-V23] Validating existing meta_leads_attribution table...")
        total_count = db.execute(text("SELECT COUNT(*) FROM meta_leads_attribution")).scalar()
        print(f"[MIGRATION-V23] Total current attribution records: {total_count}")
        
        # Check for duplicate meta_lead_id
        dups = db.execute(text("""
            SELECT meta_lead_id, COUNT(*) 
            FROM meta_leads_attribution 
            GROUP BY meta_lead_id 
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if dups:
            raise RuntimeError(f"[MIGRATION-V23] Cannot apply UNIQUE constraint: {len(dups)} duplicate meta_lead_id values exist: {dups}")
        
        # Check for NULL / empty meta_lead_id
        null_count = db.execute(text("""
            SELECT COUNT(*) FROM meta_leads_attribution 
            WHERE meta_lead_id IS NULL OR trim(meta_lead_id) = ''
        """)).scalar()
        
        if null_count > 0:
            raise RuntimeError(f"[MIGRATION-V23] Cannot apply UNIQUE constraint: {null_count} NULL or empty meta_lead_id records exist.")

        print("[MIGRATION-V23] Pre-validation PASSED: 0 duplicates, 0 nulls. Applying UNIQUE constraint...")
        
        # 2. Apply Unique Constraint / Index
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_meta_leads_attribution_meta_lead_id 
            ON meta_leads_attribution (meta_lead_id);
        """))
        
        # Performance indexes on foreign keys and search keys
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_meta_leads_attribution_form_id 
            ON meta_leads_attribution (meta_form_id);
            
            CREATE INDEX IF NOT EXISTS idx_meta_leads_attribution_campaign_id 
            ON meta_leads_attribution (meta_campaign_id);
            
            CREATE INDEX IF NOT EXISTS idx_meta_leads_attribution_company_id 
            ON meta_leads_attribution (company_id);
        """))
        
        db.commit()
        print("[MIGRATION-V23] Successfully created uq_meta_leads_attribution_meta_lead_id UNIQUE index and secondary performance indexes.")
        
    except Exception as e:
        db.rollback()
        print(f"[MIGRATION-V23] Migration FAILED: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_v23_migration()
