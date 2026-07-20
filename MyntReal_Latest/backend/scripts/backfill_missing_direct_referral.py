"""
Backfill Missing Direct Referral Income Records

ROOT CAUSE: User MNR1800143 has 4 activated direct referrals but only 2 Direct Referral 
income records in pending_income table. Missing 2 records for:
- MNR1800456 (PUDI.DEVI) - Activated: 2025-10-02, Package: Platinum (₹3,000)
- MNR1800186 (K.NOOKU NAIDU) - Activated: 2025-10-02, Package: Platinum (₹3,000)

This script:
1. Identifies ALL users with missing Direct Referral income records
2. Creates backfill records with proper deductions
3. Validates against duplicate prevention logic
4. Logs all actions for audit trail
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, func
from app.core.database import SessionLocal
from app.models.user import User
from app.models.transaction import PendingIncome
from app.constants import INCOME_RATES, get_earnings_split
from app.models.base import get_indian_time

def calculate_income_deductions_and_splits(gross_amount: float, package_points: float):
    """Calculate deductions and wallet splits for Direct Referral income"""
    # Direct Referral deductions: 10% (8% Admin + 2% TDS) + 2% Guru Dakshina
    admin_rate = INCOME_RATES['admin_charge_rate']  # 8%
    tds_rate = INCOME_RATES['tds_rate']  # 2%
    guru_dakshina_rate = 2.0  # 2% Guru Dakshina
    
    admin_deduction = gross_amount * (admin_rate / 100)
    tds_deduction = gross_amount * (tds_rate / 100)
    guru_dakshina_deduction = gross_amount * (guru_dakshina_rate / 100)
    
    # Net after ALL deductions
    net_amount = gross_amount - admin_deduction - tds_deduction - guru_dakshina_deduction
    
    # Wallet split based on package
    split = get_earnings_split(package_points)
    withdrawal_wallet_amount = net_amount * (split['withdrawable'] / 100)
    upgraded_wallet_amount = net_amount * (split['upgraded_wallet'] / 100)
    
    return {
        'admin_deduction': admin_deduction,
        'tds_deduction': tds_deduction,
        'guru_dakshina_deduction': guru_dakshina_deduction,
        'net_amount': net_amount,
        'withdrawal_wallet_amount': withdrawal_wallet_amount,
        'upgraded_wallet_amount': upgraded_wallet_amount
    }

def check_missing_direct_referral_income(db):
    """
    Find all users with activated direct referrals but missing Direct Referral income records
    
    Returns:
        List of tuples: (referrer_id, referred_user_id, activation_date, package_points)
    """
    print("\n🔍 Scanning for missing Direct Referral income records...")
    
    # Get all activated users (activation_date exists and package_points > 0)
    activated_users = db.query(User).filter(
        User.activation_date.isnot(None),
        User.package_points > 0,
        User.referrer_id.isnot(None)
    ).all()
    
    missing_records = []
    
    for user in activated_users:
        # Check if Direct Referral income exists for this activation
        existing_income = db.query(PendingIncome).filter(
            and_(
                PendingIncome.user_id == user.referrer_id,
                PendingIncome.income_type == 'Direct Referral',
                PendingIncome.related_user_id == user.id
            )
        ).first()
        
        if not existing_income:
            # Determine expected bonus amount
            if user.package_points == 1.0:  # Platinum
                expected_bonus = 3000.0
            elif user.package_points == 0.5:  # Diamond
                expected_bonus = 1500.0
            else:  # Blue/Loyal - no bonus
                expected_bonus = 0.0
            
            if expected_bonus > 0:
                missing_records.append({
                    'referrer_id': user.referrer_id,
                    'referred_user_id': user.id,
                    'referred_user_name': user.name,
                    'activation_date': user.activation_date,
                    'package_points': user.package_points,
                    'expected_bonus': expected_bonus
                })
    
    return missing_records

def create_backfill_record(db, record_data, dry_run=True):
    """
    Create a missing Direct Referral income record
    
    Args:
        db: Database session
        record_data: Dictionary with referrer_id, referred_user_id, activation_date, expected_bonus
        dry_run: If True, only print what would be created without actually creating
    
    Returns:
        True if record created successfully, False otherwise
    """
    referrer_id = record_data['referrer_id']
    referred_user_id = record_data['referred_user_id']
    referred_user_name = record_data['referred_user_name']
    activation_date = record_data['activation_date']
    expected_bonus = record_data['expected_bonus']
    
    # Get referrer details
    referrer = db.query(User).filter(User.id == referrer_id).first()
    if not referrer:
        print(f"❌ Referrer {referrer_id} not found - SKIP")
        return False
    
    # Check if referrer was activated (required for earning Direct Referral income)
    if not referrer.package_points or referrer.package_points == 0:
        print(f"⚠️  Referrer {referrer_id} not activated - SKIP")
        return False
    
    # Calculate deductions
    deductions = calculate_income_deductions_and_splits(expected_bonus, referrer.package_points)
    
    if dry_run:
        print(f"\n📋 [DRY RUN] Would create Direct Referral income:")
        print(f"   Referrer: {referrer_id} ({referrer.name})")
        print(f"   Referred User: {referred_user_id} ({referred_user_name})")
        print(f"   Activation Date: {activation_date}")
        print(f"   GROSS: ₹{expected_bonus}")
        print(f"   Admin Deduction: ₹{deductions['admin_deduction']:.2f}")
        print(f"   TDS Deduction: ₹{deductions['tds_deduction']:.2f}")
        print(f"   Guru Dakshina: ₹{deductions['guru_dakshina_deduction']:.2f}")
        print(f"   NET: ₹{deductions['net_amount']:.2f}")
        print(f"   Withdrawable Wallet: ₹{deductions['withdrawal_wallet_amount']:.2f}")
        print(f"   Upgrade Wallet: ₹{deductions['upgraded_wallet_amount']:.2f}")
        return True
    
    try:
        # Create pending_income record
        pending_income = PendingIncome(
            user_id=referrer_id,
            income_type='Direct Referral',
            gross_amount=Decimal(str(expected_bonus)),
            gurudakshina_deduction=Decimal(str(deductions['guru_dakshina_deduction'])),
            admin_deduction=Decimal(str(deductions['admin_deduction'])),
            tds_deduction=Decimal(str(deductions['tds_deduction'])),
            net_amount=Decimal(str(deductions['net_amount'])),
            withdrawal_wallet_amount=Decimal(str(deductions['withdrawal_wallet_amount'])),
            upgraded_wallet_amount=Decimal(str(deductions['upgraded_wallet_amount'])),
            business_date=activation_date,
            calculation_timestamp=activation_date,
            verification_status='Completed',  # Match existing records status
            related_user_id=referred_user_id,
            notes=f"BACKFILL: Direct Referral from {referred_user_id} activation"
        )
        
        db.add(pending_income)
        db.flush()
        
        print(f"\n✅ Created Direct Referral income record (ID: {pending_income.id})")
        print(f"   Referrer: {referrer_id} ({referrer.name})")
        print(f"   Referred User: {referred_user_id} ({referred_user_name})")
        print(f"   GROSS: ₹{expected_bonus} → NET: ₹{deductions['net_amount']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating record for {referrer_id}/{referred_user_id}: {e}")
        db.rollback()
        return False

def main():
    """Main backfill execution"""
    print("=" * 80)
    print("DIRECT REFERRAL INCOME BACKFILL SCRIPT")
    print("=" * 80)
    print("Purpose: Create missing Direct Referral income records for activated referrals")
    print("Status: Identifies and fixes system-wide missing income records")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Step 1: Find missing records
        missing_records = check_missing_direct_referral_income(db)
        
        if not missing_records:
            print("\n✅ No missing Direct Referral income records found!")
            print("All activated users have corresponding Direct Referral income records.")
            return
        
        print(f"\n⚠️  Found {len(missing_records)} missing Direct Referral income records:")
        print("-" * 80)
        
        # Group by referrer for better visibility
        by_referrer = {}
        for record in missing_records:
            referrer = record['referrer_id']
            if referrer not in by_referrer:
                by_referrer[referrer] = []
            by_referrer[referrer].append(record)
        
        for referrer_id, records in by_referrer.items():
            referrer = db.query(User).filter(User.id == referrer_id).first()
            print(f"\n👤 Referrer: {referrer_id} ({referrer.name if referrer else 'Unknown'})")
            print(f"   Missing {len(records)} Direct Referral income record(s):")
            for rec in records:
                print(f"   - {rec['referred_user_id']} ({rec['referred_user_name']}) - "
                      f"Activated: {rec['activation_date'].strftime('%Y-%m-%d')} - "
                      f"Expected: ₹{rec['expected_bonus']}")
        
        # Step 2: Ask for confirmation
        print("\n" + "=" * 80)
        print("DRY RUN MODE - Showing what would be created:")
        print("=" * 80)
        
        for record in missing_records:
            create_backfill_record(db, record, dry_run=True)
        
        print("\n" + "=" * 80)
        response = input("\n⚠️  Create these records in the database? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\n❌ Backfill cancelled by user")
            return
        
        # Step 3: Create records
        print("\n" + "=" * 80)
        print("CREATING BACKFILL RECORDS...")
        print("=" * 80)
        
        success_count = 0
        fail_count = 0
        
        for record in missing_records:
            if create_backfill_record(db, record, dry_run=False):
                success_count += 1
            else:
                fail_count += 1
        
        # Commit all changes
        db.commit()
        
        # Step 4: Summary
        print("\n" + "=" * 80)
        print("BACKFILL COMPLETE")
        print("=" * 80)
        print(f"✅ Successfully created: {success_count} records")
        if fail_count > 0:
            print(f"❌ Failed: {fail_count} records")
        print(f"💰 Total income restored: ₹{sum(r['expected_bonus'] for r in missing_records[:success_count])}")
        print("\n🔄 Next Steps:")
        print("1. Verify records in pending_income table")
        print("2. Check materialized views refresh (mv_user_earning_wallet, mv_user_withdrawable_wallet)")
        print("3. Test user earnings pages to confirm data displays correctly")
        
    except Exception as e:
        print(f"\n❌ Backfill failed with error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
