from decimal import Decimal
from sqlalchemy import text
from app.services.staff_accounts_service import LedgerPostingService


def execute_historical_statutory_backfill(db, company_id: int = 1):
    print("========== INITIATING HISTORICAL STATUTORY GL BACKFILL ==========")

    rows = db.execute(text("""
        SELECT
            id,
            user_id,
            tds_deduction,
            admin_deduction,
            business_date,
            income_type
        FROM pending_income
        WHERE verification_status = 'Completed'
          AND (tds_deduction > 0 OR admin_deduction > 0)
        ORDER BY business_date ASC, id ASC
    """)).fetchall()

    print(f"▶ Found {len(rows)} completed rows to analyse...")

    posted = 0
    failed = 0

    for row in rows:
        try:
            LedgerPostingService.auto_post_statutory_deductions(
                db            = db,
                company_id    = company_id,
                tds_amount    = Decimal(str(row.tds_deduction   or 0)),
                admin_amount  = Decimal(str(row.admin_deduction or 0)),
                txn_date      = row.business_date.date()
                                if hasattr(row.business_date, 'date')
                                else row.business_date,
                ref_type      = 'PENDING_INCOME',
                ref_id        = row.id,
                ref_number    = f'PI-{row.id:08d}',
                narration     = (
                    f'[BACKFILL] {row.income_type} statutory deductions'
                    f' — user {row.user_id}'
                ),
                created_by_id = None,
            )
            posted += 1
        except Exception as e:
            failed += 1
            print(f"  ⚠️  PI#{row.id} failed: {e}")

    db.commit()

    print(f"\n💯 BACKFILL COMPLETE:")
    print(f"   ✅ Posted (or already existed — idempotent):  {posted}")
    print(f"   ❌ Failed:                                    {failed}")
