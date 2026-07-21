import os
import sys
import logging

# Add backend directory to sys.path
backend_dir = "/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend"
sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, settings
from app.models.crm import CRMLead
from app.services.vgk_solar_advance import check_and_create_advance, check_and_create_dvr_advance
from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
from sqlalchemy.sql import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_dvr_advances")

def backfill():
    print(f"Connecting to database: {settings.DATABASE_URL}")
    db = SessionLocal()
    try:
        # Fetch all solar leads across companies (categories 6, 19, 36, 48 or solar_pipeline_status set)
        leads = db.query(CRMLead).filter(
            text("category_id IN (6, 19, 36, 48) OR solar_pipeline_status IS NOT NULL")
        ).all()
        
        print(f"Found {len(leads)} solar leads to evaluate...")
        
        st1_count = 0
        st2_count = 0
        comm_count = 0
        
        for lead in leads:
            # 1. Stage 1 CIBIL advance check
            res1 = check_and_create_advance(db, lead.id)
            if res1.get('created'):
                st1_count += len(res1.get('entry_numbers', []))
                print(f"  [Lead #{lead.id} - {lead.name}] Created Stage-1 Advance: {res1.get('entry_numbers')}")

            # 2. Stage 2 DVR advance check
            res2 = check_and_create_dvr_advance(db, lead.id)
            if res2.get('created'):
                st2_count += len(res2.get('entry_numbers', []))
                print(f"  [Lead #{lead.id} - {lead.name}] Created Stage-2 DVR Advance: {res2.get('entry_numbers')}")

            # 3. Final Commission drafts check
            c_cnt = generate_vgk_cash_income_drafts(db, lead)
            if c_cnt > 0:
                comm_count += c_cnt
                print(f"  [Lead #{lead.id} - {lead.name}] Generated {c_cnt} Commission Drafts")

        db.commit()
        print("\n==========================================")
        print("BACKFILL COMPLETE!")
        print(f"  - Stage 1 CIBIL Advances Created: {st1_count}")
        print(f"  - Stage 2 DVR Advances Created:   {st2_count}")
        print(f"  - Commission Drafts Generated:    {comm_count}")
        print("==========================================")

    except Exception as e:
        db.rollback()
        print(f"ERROR during backfill: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
