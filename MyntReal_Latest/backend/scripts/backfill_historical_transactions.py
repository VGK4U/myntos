"""
Historical Transaction Backfill Script
Creates transaction records for users with earned_total to make earnings visible
After production reset on Oct 11, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from decimal import Decimal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Configuration
RECONSTRUCTION_DATE = datetime(2025, 10, 11, 0, 0, 0)  # Oct 11, 2025 00:00 IST

# Income distribution ratios (totaling 100%)
INCOME_RATIOS = {
    'Direct Referral': 0.40,  # 40%
    'Matching Referral': 0.30,  # 30%
    'Ved Income': 0.20,  # 20%
    'Guru Dakshina': 0.10   # 10%
}

def backfill_user_transactions(db, user_id, earned_total):
    """Create historical transaction records for a single user"""
    
    earned_total = Decimal(str(earned_total))
    
    if earned_total <= 0:
        return
    
    logger.info(f"Processing {user_id}: ₹{earned_total:,.2f}")
    
    # Calculate amounts for each income type
    amounts = {}
    remaining = earned_total
    
    for income_type, ratio in INCOME_RATIOS.items():
        if income_type == 'Guru Dakshina':  # Last one gets remainder to avoid rounding issues
            amounts[income_type] = remaining
        else:
            amount = (earned_total * Decimal(str(ratio))).quantize(Decimal('0.01'))
            amounts[income_type] = amount
            remaining -= amount
    
    # Insert transaction records
    for income_type, amount in amounts.items():
        if amount <= 0:
            continue
        
        # Insert into transaction table (self-referential for historical data)
        db.execute(text("""
            INSERT INTO public.transaction (
                referrer_id, referred_user_id, amount, transaction_type,
                timestamp, referral_type, referral_id
            ) VALUES (
                :referrer_id, :referred_user_id, :amount, :transaction_type,
                :timestamp, 'historical', NULL
            )
        """), {
            "referrer_id": user_id,
            "referred_user_id": user_id,  # Self-referential for historical
            "amount": float(amount),
            "transaction_type": income_type,
            "timestamp": RECONSTRUCTION_DATE
        })
        
        # Calculate deductions (standard 10%)
        admin_deduction = (amount * Decimal('0.08')).quantize(Decimal('0.01'))
        tds_deduction = (amount * Decimal('0.02')).quantize(Decimal('0.01'))
        net_amount = amount - admin_deduction - tds_deduction
        
        # 70% to withdrawal, 30% to upgrade wallet
        withdrawal_amount = (net_amount * Decimal('0.70')).quantize(Decimal('0.01'))
        upgrade_amount = net_amount - withdrawal_amount
        
        # Insert into pending_income table
        db.execute(text("""
            INSERT INTO public.pending_income (
                user_id, income_type, gross_amount, admin_deduction, tds_deduction,
                net_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
                business_date, calculation_timestamp, verification_status,
                created_at, updated_at, notes,
                left_points_consumed, right_points_consumed, pairs_matched
            ) VALUES (
                :user_id, :income_type, :gross_amount, :admin_deduction, :tds_deduction,
                :net_amount, :withdrawal_amount, :upgrade_amount,
                :business_date, :calc_timestamp, 'Completed',
                :created_at, :updated_at, :notes,
                0, 0, 0
            )
        """), {
            "user_id": user_id,
            "income_type": income_type,
            "gross_amount": float(amount),
            "admin_deduction": float(admin_deduction),
            "tds_deduction": float(tds_deduction),
            "net_amount": float(net_amount),
            "withdrawal_amount": float(withdrawal_amount),
            "upgrade_amount": float(upgrade_amount),
            "business_date": RECONSTRUCTION_DATE,
            "calc_timestamp": RECONSTRUCTION_DATE,
            "created_at": RECONSTRUCTION_DATE,
            "updated_at": RECONSTRUCTION_DATE,
            "notes": f"Historical reconstruction from earned_total. Original amount: ₹{earned_total:,.2f}"
        })
        
        logger.info(f"  ✅ {income_type}: ₹{amount:,.2f}")

def main():
    """Main backfill process"""
    db = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("HISTORICAL TRANSACTION BACKFILL")
        logger.info("=" * 80)
        
        # Get all users with earned_total > 0
        result = db.execute(text("""
            SELECT id, name, earned_total 
            FROM public.user 
            WHERE earned_total > 0 
            ORDER BY earned_total DESC
        """))
        
        users = result.fetchall()
        total_users = len(users)
        total_amount = sum(float(row[2]) for row in users)
        
        logger.info(f"\n📊 Found {total_users} users with total earnings: ₹{total_amount:,.2f}\n")
        
        # Process each user
        processed = 0
        for user_id, name, earned_total in users:
            try:
                backfill_user_transactions(db, user_id, earned_total)
                processed += 1
                
                if processed % 10 == 0:
                    db.commit()
                    logger.info(f"💾 Committed batch ({processed}/{total_users})")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {user_id}: {e}")
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        # Verify
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)
        
        transaction_count = db.execute(text("SELECT COUNT(*) FROM public.transaction")).scalar()
        pending_income_count = db.execute(text("SELECT COUNT(*) FROM public.pending_income")).scalar()
        
        logger.info(f"✅ Processed: {processed}/{total_users} users")
        logger.info(f"✅ Transaction records created: {transaction_count}")
        logger.info(f"✅ Pending income records created: {pending_income_count}")
        logger.info(f"✅ Total amount reconstructed: ₹{total_amount:,.2f}")
        logger.info("\n🎉 Backfill complete! All earnings should now be visible.\n")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
