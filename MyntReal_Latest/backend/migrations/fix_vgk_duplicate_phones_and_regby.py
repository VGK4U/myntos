"""
Migration: Fix Duplicate VGK Members, Create Phone Unique Index, and Backfill registered_by_emp_code.
DC Protocol Sep 2026.
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Ensure current dir is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.utils.phone_otp import normalize_phone_10

def run_migration(db_url: str = None):
    if not db_url:
        from dotenv import load_dotenv
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
        load_dotenv(env_path)
        db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise RuntimeError("DATABASE_URL not found in environment")

    logger.info(f"Connecting to database: {db_url.split('@')[-1]}")
    engine = create_engine(db_url)

    with engine.begin() as conn:
        # Step 1: Normalize all phones in official_partners for VGK_TEAM
        logger.info("Step 1: Normalizing phone numbers for VGK_TEAM partners...")
        rows = conn.execute(text(
            "SELECT id, phone FROM official_partners WHERE category = 'VGK_TEAM' AND phone IS NOT NULL AND phone != ''"
        )).fetchall()
        
        normalized_count = 0
        for r in rows:
            pid, raw_p = r[0], r[1]
            clean_p = normalize_phone_10(raw_p)
            if clean_p and clean_p != raw_p:
                conn.execute(text(
                    "UPDATE official_partners SET phone = :cp WHERE id = :id"
                ), {"cp": clean_p, "id": pid})
                normalized_count += 1
        logger.info(f"Normalized {normalized_count} phone numbers in official_partners.")

        # Step 2: Merge duplicate S. Ramakrishna (keep 442, remove 443 & 444)
        logger.info("Step 2: Cleaning duplicate accounts for S. Ramakrishna (9440423264)...")
        # Reassign any community registrations from 443 or 444 to 442
        conn.execute(text(
            "UPDATE community_registrations SET user_id = 442 WHERE user_id IN (443, 444)"
        ))
        # Reassign or delete points ledger entries for 443 and 444
        conn.execute(text(
            "DELETE FROM vgk_points_ledger WHERE partner_id IN (443, 444)"
        ))
        # Delete partner rows 443 and 444
        conn.execute(text(
            "DELETE FROM official_partners WHERE id IN (443, 444)"
        ))
        logger.info("Purged duplicate partners 443 and 444. Retained 442 (VGK07107263).")

        # Step 3: Handle test duplicate 336 (Ganesh Utsav Mandal)
        conn.execute(text(
            "UPDATE official_partners SET phone = '9876543211' WHERE id = 336 AND phone = '9876543210'"
        ))
        logger.info("Updated test duplicate partner 336 phone to 9876543211.")

        # Step 4: Create PostgreSQL partial unique index on (phone) for VGK_TEAM
        logger.info("Step 4: Creating unique partial index uq_official_partners_vgk_phone...")
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_official_partners_vgk_phone 
            ON official_partners (phone) 
            WHERE category = 'VGK_TEAM' AND phone IS NOT NULL AND phone != '';
        """))
        logger.info("Unique index uq_official_partners_vgk_phone created successfully.")

        # Step 5: Backfill registered_by_emp_code from staff who created welcome bonus
        logger.info("Step 5: Backfilling registered_by_emp_code from staff creators...")
        staff_backfill = conn.execute(text("""
            UPDATE official_partners op
            SET registered_by_emp_code = se.emp_code
            FROM vgk_points_ledger pl
            JOIN staff_employees se ON se.id = pl.created_by
            WHERE pl.partner_id = op.id 
              AND pl.reason_code = 'WELCOME_BONUS'
              AND op.category = 'VGK_TEAM'
              AND (op.registered_by_emp_code IS NULL OR trim(op.registered_by_emp_code) = '');
        """))
        logger.info(f"Backfilled {staff_backfill.rowcount} members with staff employee codes.")

        # Step 6: For all remaining members with NULL registered_by_emp_code, set to VGK_DEFAULT_ROOT ('VGK07102207')
        logger.info("Step 6: Setting registered_by_emp_code = 'VGK07102207' for self-registered members...")
        default_backfill = conn.execute(text("""
            UPDATE official_partners 
            SET registered_by_emp_code = 'VGK07102207'
            WHERE category = 'VGK_TEAM'
              AND (registered_by_emp_code IS NULL OR trim(registered_by_emp_code) = '');
        """))
        logger.info(f"Set registered_by_emp_code = 'VGK07102207' for {default_backfill.rowcount} self-registered members.")

        # Step 7: For any VGK member where parent_partner_id is NULL, set to 31 (VGK Support root)
        logger.info("Step 7: Setting parent_partner_id = 31 for members without upline...")
        upline_backfill = conn.execute(text("""
            UPDATE official_partners 
            SET parent_partner_id = 31
            WHERE category = 'VGK_TEAM'
              AND parent_partner_id IS NULL
              AND id != 31;
        """))
        logger.info(f"Set parent_partner_id = 31 for {upline_backfill.rowcount} members.")

    logger.info("Migration fix_vgk_duplicate_phones_and_regby completed successfully!")

if __name__ == "__main__":
    run_migration()
