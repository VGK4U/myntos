"""
Fix wallet credits for all users with "Completed" income
This script will:
1. Credit all Finance Paid income to user earning_wallet and upgrade_wallet_balance
2. Create Transaction records for history
3. Sync earning_wallet to withdrawable_wallet (for KYC-approved users)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from decimal import Decimal
from datetime import datetime
from app.core.database import SessionLocal
from app.models.user import User
from app.models.transaction import PendingIncome, Transaction
from app.models.base import get_indian_time

def fix_wallet_credits():
    """Credit all Finance Paid income to user wallets"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 70)
        print("🔧 FIXING WALLET CREDITS FOR ALL USERS")
        print("=" * 70)
        print()
        
        # Get all users with Finance Paid income that hasn't been credited
        query = text("""
            SELECT 
                user_id,
                SUM(withdrawal_wallet_amount) as total_withdrawable,
                SUM(upgraded_wallet_amount) as total_upgrade,
                SUM(net_amount) as total_net,
                COUNT(*) as income_count
            FROM pending_income
            WHERE verification_status = 'Completed'
            GROUP BY user_id
            ORDER BY user_id
        """)
        
        results = db.execute(query).fetchall()
        
        print(f"📊 Found {len(results)} users with Finance Paid income to credit")
        print()
        
        total_users_updated = 0
        total_transactions_created = 0
        total_amount_credited = Decimal('0')
        
        for row in results:
            user_id = row[0]
            total_withdrawable = Decimal(str(row[1] or 0))
            total_upgrade = Decimal(str(row[2] or 0))
            total_net = Decimal(str(row[3] or 0))
            income_count = row[4]
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"❌ User {user_id} not found, skipping...")
                continue
            
            # Get current wallet balances
            current_earning = Decimal(str(user.earning_wallet or 0))
            current_upgrade = Decimal(str(user.upgrade_wallet_balance or 0))
            
            # Calculate new balances
            new_earning = current_earning + total_withdrawable
            new_upgrade = current_upgrade + total_upgrade
            
            # Update user wallets
            user.earning_wallet = float(new_earning)
            user.upgrade_wallet_balance = float(new_upgrade)
            
            # Get all Finance Paid income for this user to create transactions
            incomes = db.query(PendingIncome).filter(
                PendingIncome.user_id == user_id,
                PendingIncome.verification_status == 'Completed'
            ).all()
            
            # Create transaction records for each income
            for income in incomes:
                transaction = Transaction(
                    referrer_id=income.user_id,
                    referred_user_id=income.related_user_id or income.user_id,
                    transaction_type=income.income_type,
                    amount=income.net_amount,
                    timestamp=income.accounts_paid_at or get_indian_time()
                )
                db.add(transaction)
                total_transactions_created += 1
            
            total_users_updated += 1
            total_amount_credited += total_net
            
            print(f"✅ {user_id}: Credited ₹{float(new_earning):.2f} to earning_wallet, "
                  f"₹{float(new_upgrade):.2f} to upgrade_wallet ({income_count} incomes, {len(incomes)} transactions)")
        
        # Commit all changes
        db.commit()
        
        print()
        print("=" * 70)
        print("✅ WALLET CREDIT COMPLETE")
        print("=" * 70)
        print(f"Total Users Updated: {total_users_updated}")
        print(f"Total Transactions Created: {total_transactions_created}")
        print(f"Total Amount Credited: ₹{float(total_amount_credited):,.2f}")
        print()
        
        # Now sync earning_wallet to withdrawable_wallet for KYC-approved users
        print("=" * 70)
        print("🔄 SYNCING EARNING WALLET TO WITHDRAWABLE WALLET")
        print("=" * 70)
        print()
        
        from app.services.wallet_sync_service import WalletSyncService
        
        sync_service = WalletSyncService(db)
        sync_result = sync_service.run_daily_sync()
        
        print(f"✅ Wallet Sync Complete:")
        print(f"   - Eligible Users: {sync_result['total_users_eligible']}")
        print(f"   - Transferred: {sync_result['transferred_count']}")
        print(f"   - Blocked (KYC): {sync_result['blocked_count']}")
        print(f"   - Amount Transferred: ₹{sync_result['total_amount_transferred']:,.2f}")
        print()
        
        return {
            "users_updated": total_users_updated,
            "transactions_created": total_transactions_created,
            "amount_credited": float(total_amount_credited),
            "wallet_sync": sync_result
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    result = fix_wallet_credits()
    if result:
        print("=" * 70)
        print("🎉 ALL WALLETS FIXED SUCCESSFULLY!")
        print("=" * 70)
