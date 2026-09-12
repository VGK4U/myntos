import os
import sys
import argparse
import logging
from decimal import Decimal

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile_bonanza_96")

def parse_args():
    parser = argparse.ArgumentParser(description="Reconcile Bonanza #96 Stage 1 Extra Commission entries.")
    parser.add_argument("--prod", action="store_true", help="Run against production RDS database")
    parser.add_argument("--apply", action="store_true", help="Apply mutations (default is dry-run)")
    parser.add_argument("--lead-id", type=int, default=None, help="Filter to specific lead ID")
    return parser.parse_args()

def main():
    args = parse_args()
    is_dry_run = not args.apply

    if args.prod:
        from dotenv import load_dotenv
        env_path = os.path.join(backend_dir, ".env")
        load_dotenv(env_path)
        db_url = os.environ.get("PROD_DATABASE_URL")
        if not db_url:
            logger.error("PROD_DATABASE_URL not found in environment!")
            sys.exit(1)
        logger.info("Connecting to PRODUCTION database...")
    else:
        from app.core.database import settings
        db_url = settings.DATABASE_URL
        logger.info(f"Connecting to DEV database: {db_url}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Fetch Bonanza #96
        bz = db.execute(text("""
            SELECT id, name, start_date, end_date, grace_days, reward_type,
                   ec_l1_amount, ec_l2_amount, ec_l1_trigger, ec_l2_trigger, status
            FROM bonanza
            WHERE id = 96 AND is_deleted = false
        """)).fetchone()

        if not bz:
            logger.error("Bonanza #96 not found or is marked deleted!")
            return

        logger.info(f"Loaded Bonanza #{bz.id}: {bz.name} ({bz.start_date.date()} to {bz.end_date.date()})")
        logger.info(f"  Reward Type: {bz.reward_type} | Status: {bz.status}")
        logger.info(f"  L1 Amount: Rs {bz.ec_l1_amount} (Trigger: {bz.ec_l1_trigger})")
        logger.info(f"  L2 Amount: Rs {bz.ec_l2_amount} (Trigger: {bz.ec_l2_trigger})")

        # 2. Find candidate leads that have a canonical Stage 1 CIBIL advance
        # and whose qualifying date (submit_date or solar_pipeline_status_updated_at) is in window
        query = """
            SELECT l.id, l.name, l.solar_pipeline_status, l.cibil_score, l.submit_date, l.created_at,
                   l.solar_pipeline_status_updated_at, l.associated_partner_id, l.team_senior_partner_id,
                   l.source_ref_id, l.source_ref_type, l.mnr_handler_id, l.company_id
            FROM crm_leads l
            WHERE EXISTS (
                SELECT 1 FROM vgk_solar_cibil_advances vsa
                WHERE vsa.lead_id = l.id AND vsa.kind = 'ADVANCE'
            )
              AND (
                    (l.submit_date BETWEEN :start_d AND :end_d)
                    OR (l.submit_date IS NULL AND l.solar_pipeline_status_updated_at::date BETWEEN :start_d AND :end_d)
              )
        """
        params = {
            "start_d": bz.start_date.date(),
            "end_d": bz.end_date.date(),
        }
        if args.lead_id:
            query += " AND l.id = :lead_id"
            params["lead_id"] = args.lead_id

        query += " ORDER BY l.id"
        candidate_leads = db.execute(text(query), params).fetchall()

        logger.info(f"Found {len(candidate_leads)} candidate lead(s) for Bonanza #96 in window.")

        reconciled_count = 0
        skipped_count = 0

        for lead in candidate_leads:
            logger.info("--------------------------------------------------")
            logger.info(f"Evaluating Lead #{lead.id} ({lead.name}):")
            logger.info(f"  Pipeline: {lead.solar_pipeline_status} | CIBIL: {lead.cibil_score}")
            logger.info(f"  Submit Date: {lead.submit_date} | Created: {lead.created_at}")

            # Resolve L1 and L2 partner IDs
            l1_partner_id = None
            if lead.source_ref_type in ('partner', 'vgk_partner') and lead.source_ref_id and lead.source_ref_id.isdigit():
                l1_partner_id = int(lead.source_ref_id)
            elif lead.mnr_handler_id:
                l1_partner_id = lead.mnr_handler_id
            else:
                l1_partner_id = lead.associated_partner_id

            l2_partner_id = lead.team_senior_partner_id

            logger.info(f"  L1 Partner ID: {l1_partner_id} | L2 Partner ID: {l2_partner_id}")

            levels_to_apply = []
            for lv, pid, amt in [(1, l1_partner_id, bz.ec_l1_amount), (2, l2_partner_id, bz.ec_l2_amount)]:
                if not pid or not amt or float(amt) <= 0:
                    continue

                log_exists = db.execute(text("""
                    SELECT id, vci_entry_id FROM bonanza_extra_commission_log
                    WHERE bonanza_id = :bid AND lead_id = :lid AND level = :lv
                """), {"bid": bz.id, "lid": lead.id, "lv": lv}).fetchone()

                vci_active = db.execute(text("""
                    SELECT id, entry_number, status, commission_amount FROM vgk_cash_income_entries
                    WHERE bonanza_id = :bid AND source_lead_id = :lid AND level = :lv AND status != 'CANCELLED'
                """), {"bid": bz.id, "lid": lead.id, "lv": lv}).fetchone()

                if log_exists or vci_active:
                    logger.info(f"  Level {lv} (Partner {pid}): ALREADY EXISTS (log={bool(log_exists)}, vci={vci_active.entry_number if vci_active else None}) - SKIPPING")
                    skipped_count += 1
                else:
                    logger.info(f"  Level {lv} (Partner {pid}): ELIGIBLE FOR Rs {amt}")
                    levels_to_apply.append((lv, pid, Decimal(str(amt))))

            if not levels_to_apply:
                continue

            if is_dry_run:
                logger.info(f"  [DRY-RUN] Would create {len(levels_to_apply)} entry/entries for Lead #{lead.id}")
                for lv, pid, amt in levels_to_apply:
                    logger.info(f"    -> L{lv} Rs {amt} for Partner {pid}")
            else:
                from app.services.vgk_extra_commission import apply_extra_commission_if_active
                from app.models.crm import CRMLead
                lead_orm = db.query(CRMLead).filter(CRMLead.id == lead.id).first()
                result = apply_extra_commission_if_active(db, lead_orm, 'file_submitted')
                logger.info(f"  [APPLY] Executed apply_extra_commission_if_active for Lead #{lead.id}: {result}")
                db.commit()
                reconciled_count += len(levels_to_apply)

        logger.info("==================================================")
        if is_dry_run:
            logger.info("DRY RUN COMPLETE. No data was mutated.")
            logger.info("To apply changes, re-run with --apply")
        else:
            logger.info(f"RECONCILIATION COMPLETE! Applied entries: {reconciled_count}, Skipped: {skipped_count}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during reconciliation: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    main()
