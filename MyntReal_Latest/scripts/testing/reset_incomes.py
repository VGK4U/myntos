#!/usr/bin/env python3
"""
Income Reset Script
Deletes all income records and resets user wallet balances to 0
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, text
from app.core.config import settings

def reset_all_incomes():
    """Reset all income data to 0"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            print("🔄 Starting income reset...")
            
            # Step 1: Delete all income records
            print("\n📝 Deleting income records...")
            result1 = conn.execute(text("DELETE FROM pending_income"))
            print(f"   ✅ Deleted {result1.rowcount} pending_income records")
            
            result2 = conn.execute(text("DELETE FROM transaction"))
            print(f"   ✅ Deleted {result2.rowcount} transaction records")
            
            result3 = conn.execute(text("DELETE FROM ved_income"))
            print(f"   ✅ Deleted {result3.rowcount} ved_income records")
            
            result4 = conn.execute(text("DELETE FROM field_allowance_progress"))
            print(f"   ✅ Deleted {result4.rowcount} field_allowance_progress records")
            
            result5 = conn.execute(text("DELETE FROM car_allowance_eligibility"))
            print(f"   ✅ Deleted {result5.rowcount} car_allowance_eligibility records")
            
            result6 = conn.execute(text("DELETE FROM bonanza_progress"))
            print(f"   ✅ Deleted {result6.rowcount} bonanza_progress records")
            
            # Step 2: Reset all user wallet balances
            print("\n💰 Resetting user wallets...")
            result7 = conn.execute(text("""
                UPDATE "user" SET 
                    earning_wallet = 0,
                    withdrawable_wallet = 0,
                    wallet_balance = 0,
                    earned_total = 0,
                    released_total = 0,
                    upgrade_wallet_balance = 0
            """))
            print(f"   ✅ Reset wallets for {result7.rowcount} users")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Income reset completed successfully!")
            
            # Verify the reset
            print("\n🔍 Verification:")
            result = conn.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM pending_income) as pending_count,
                    (SELECT COUNT(*) FROM transaction) as transaction_count,
                    (SELECT COUNT(*) FROM ved_income) as ved_count,
                    (SELECT SUM(earning_wallet) FROM "user") as total_earning,
                    (SELECT SUM(wallet_balance) FROM "user") as total_balance,
                    (SELECT SUM(earned_total) FROM "user") as total_earned
            """))
            row = result.fetchone()
            print(f"   - Pending Income Records: {row[0]}")
            print(f"   - Transaction Records: {row[1]}")
            print(f"   - Ved Income Records: {row[2]}")
            print(f"   - Total Earning Wallet: ₹{row[3] or 0}")
            print(f"   - Total Wallet Balance: ₹{row[4] or 0}")
            print(f"   - Total Earned: ₹{row[5] or 0}")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Error: {e}")
            raise

if __name__ == "__main__":
    reset_all_incomes()
