"""
Backfill Missing Ved Income Records

ROOT CAUSE: Ved Team members activated but scheduler failed to create Ved Income records
because ved_team_member records were added AFTER activation dates (timing mismatch).

This script:
1. Uses ved_team_member table as SINGLE SOURCE (DC Protocol)
2. Ensures Ved Team ISOLATION (each ved_owner_id has separate Ved teams)
3. Creates Ved Income records for activated members without existing income
4. Respects Ved breaking (only creates income for period when member was active)
5. Validates against duplicate prevention logic
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
from app.models.ved_team import VedTeamMember
from app.constants import INCOME_RATES, get_earnings_split, get_ved_income
from app.models.base import get_indian_time

def check_ved_owner_prerequisites(db, ved_owner_id: str):
    """
    Check Ved Owner prerequisites #8 and #9 (Conservative Approach - Option 1)
    
    Prerequisite #8: Ved owner must have 1:1 active direct referrals on both sides
    Prerequisite #9: Ved owner must have achieved first matching (referral_bonus_count >= 1)
    
    Returns:
        (passes_check, reason) tuple
    """
    from app.models.placement import Placement
    
    # Get Ved Owner
    ved_owner = db.query(User).filter(User.id == ved_owner_id).first()
    if not ved_owner:
        return (False, "Ved Owner not found")
    
    # Check prerequisite #9: First matching achieved
    if not ved_owner.referral_bonus_count or ved_owner.referral_bonus_count < 1:
        return (False, f"First matching not achieved (referral_bonus_count={ved_owner.referral_bonus_count})")
    
    # Check prerequisite #8: 1:1 active direct referrals on both sides
    left_refs = db.query(User).join(
        Placement, Placement.child_id == User.id
    ).filter(
        User.referrer_id == ved_owner_id,
        Placement.side == 'left',
        User.activation_date.isnot(None),
        User.package_points > 0
    ).count()
    
    right_refs = db.query(User).join(
        Placement, Placement.child_id == User.id
    ).filter(
        User.referrer_id == ved_owner_id,
        Placement.side == 'right',
        User.activation_date.isnot(None),
        User.package_points > 0
    ).count()
    
    if left_refs < 1 or right_refs < 1:
        return (False, f"Missing 1:1 direct referrals (left={left_refs}, right={right_refs})")
    
    return (True, "All prerequisites passed")

def calculate_income_deductions_and_splits(gross_amount: float, package_points: float):
    """Calculate deductions and wallet splits for Ved Income"""
    # Ved Income deductions: 10% (8% Admin + 2% TDS) + 2% Guru Dakshina
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

def check_missing_ved_income(db):
    """
    Find all activated Ved Team members missing Ved Income records
    
    DC PROTOCOL: Uses ved_team_member table as SINGLE SOURCE
    VED TEAM ISOLATION: Groups by ved_owner_id to ensure separation
    
    Returns:
        List of dictionaries with missing Ved Income data
    """
    print("\n🔍 Scanning for missing Ved Income records...")
    print("   Using DC Protocol: ved_team_member table as single source")
    print("   Ensuring Ved Team isolation by ved_owner_id...")
    
    # Get all Ved Team members (both active and removed)
    # DC PROTOCOL: ved_team_member is the single source of truth
    # We'll filter by activation vs removal timeline in the next step
    ved_members_query = db.query(VedTeamMember).all()
    
    missing_records = []
    ved_teams_processed = set()
    ved_owners_blocked = {}
    ved_owners_eligible = set()
    
    for ved_member in ved_members_query:
        ved_owner_id = ved_member.ved_owner_id
        ved_head_id = ved_member.ved_head_id
        member_id = ved_member.member_id
        
        # Track Ved team isolation
        ved_team_key = f"{ved_owner_id}:{ved_head_id}"
        ved_teams_processed.add(ved_team_key)
        
        # CONSERVATIVE APPROACH (Option 1): Check Ved Owner prerequisites
        # Only create income for eligible Ved Owners (respect scheduler business logic)
        if ved_owner_id not in ved_owners_eligible and ved_owner_id not in ved_owners_blocked:
            # Check prerequisites #8 and #9
            prerequisite_pass, reason = check_ved_owner_prerequisites(db, ved_owner_id)
            if prerequisite_pass:
                ved_owners_eligible.add(ved_owner_id)
            else:
                ved_owners_blocked[ved_owner_id] = reason
        
        # Skip if Ved Owner is blocked by prerequisites
        if ved_owner_id in ved_owners_blocked:
            continue
        
        # Get member user details
        member_user = db.query(User).filter(User.id == member_id).first()
        if not member_user:
            continue
        
        # Check if member is activated
        if not member_user.activation_date or member_user.package_points == 0:
            continue
        
        # CRITICAL: Only create income if member was active BEFORE removal
        # Rule: Member must be currently active OR activated before being removed
        if ved_member.removed_date:
            # Member was removed - check if they activated BEFORE removal
            if member_user.activation_date >= ved_member.removed_date:
                # Activated AFTER removal - no income (shouldn't happen normally)
                continue
            # Activated BEFORE removal - eligible for income (they were active when they should have earned)
        # If no removed_date, member is currently active - eligible for income
        
        # Check if Ved Income already exists
        existing_income = db.query(PendingIncome).filter(
            and_(
                PendingIncome.user_id == ved_owner_id,
                PendingIncome.income_type == 'Ved Income',
                PendingIncome.related_user_id == member_id
            )
        ).first()
        
        if not existing_income:
            # Get Ved owner details
            ved_owner = db.query(User).filter(User.id == ved_owner_id).first()
            if not ved_owner:
                continue
            
            # Determine Ved Income amount based on member's package
            ved_income_amount = get_ved_income(member_user.package_points)
            
            if ved_income_amount > 0:
                missing_records.append({
                    'ved_owner_id': ved_owner_id,
                    'ved_owner_name': ved_owner.name,
                    'ved_head_id': ved_head_id,
                    'member_id': member_id,
                    'member_name': member_user.name,
                    'member_activation_date': member_user.activation_date,
                    'member_package_points': member_user.package_points,
                    'expected_income': ved_income_amount,
                    'ved_owner_package_points': ved_owner.package_points
                })
    
    print(f"\n📊 Ved Team Isolation Check:")
    print(f"   Total unique Ved Teams scanned: {len(ved_teams_processed)}")
    print(f"   ✅ Eligible Ved Owners (pass prerequisites): {len(ved_owners_eligible)}")
    print(f"   ❌ Blocked Ved Owners (fail prerequisites): {len(ved_owners_blocked)}")
    
    if ved_owners_blocked:
        print(f"\n⚠️  Blocked Ved Owners (Option 1 - Conservative):")
        for owner_id, reason in sorted(ved_owners_blocked.items())[:10]:
            ved_owner = db.query(User).filter(User.id == owner_id).first()
            owner_name = ved_owner.name if ved_owner else "Unknown"
            print(f"   - {owner_id} ({owner_name}): {reason}")
        if len(ved_owners_blocked) > 10:
            print(f"   ... and {len(ved_owners_blocked) - 10} more blocked Ved Owners")
    
    return missing_records

def create_backfill_record(db, record_data, dry_run=True):
    """
    Create a missing Ved Income record
    
    Args:
        db: Database session
        record_data: Dictionary with ved_owner_id, member_id, activation_date, expected_income
        dry_run: If True, only print what would be created
    
    Returns:
        True if record created successfully, False otherwise
    """
    ved_owner_id = record_data['ved_owner_id']
    ved_owner_name = record_data['ved_owner_name']
    member_id = record_data['member_id']
    member_name = record_data['member_name']
    activation_date = record_data['member_activation_date']
    expected_income = record_data['expected_income']
    ved_owner_package_points = record_data['ved_owner_package_points']
    
    # Calculate deductions
    deductions = calculate_income_deductions_and_splits(expected_income, ved_owner_package_points)
    
    if dry_run:
        print(f"\n📋 [DRY RUN] Would create Ved Income:")
        print(f"   Ved Owner: {ved_owner_id} ({ved_owner_name})")
        print(f"   Member: {member_id} ({member_name})")
        print(f"   Member Activation Date: {activation_date}")
        print(f"   GROSS: ₹{expected_income}")
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
            user_id=ved_owner_id,
            income_type='Ved Income',
            gross_amount=Decimal(str(expected_income)),
            gurudakshina_deduction=Decimal(str(deductions['guru_dakshina_deduction'])),
            admin_deduction=Decimal(str(deductions['admin_deduction'])),
            tds_deduction=Decimal(str(deductions['tds_deduction'])),
            net_amount=Decimal(str(deductions['net_amount'])),
            withdrawal_wallet_amount=Decimal(str(deductions['withdrawal_wallet_amount'])),
            upgraded_wallet_amount=Decimal(str(deductions['upgraded_wallet_amount'])),
            business_date=activation_date,
            calculation_timestamp=activation_date,
            verification_status='Completed',  # Match existing records status
            related_user_id=member_id,
            notes=f"BACKFILL: Ved Income from {member_id} activation in Ved Team"
        )
        
        db.add(pending_income)
        db.flush()
        
        print(f"\n✅ Created Ved Income record (ID: {pending_income.id})")
        print(f"   Ved Owner: {ved_owner_id} ({ved_owner_name})")
        print(f"   Member: {member_id} ({member_name})")
        print(f"   GROSS: ₹{expected_income} → NET: ₹{deductions['net_amount']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating record for {ved_owner_id}/{member_id}: {e}")
        db.rollback()
        return False

def main():
    """Main backfill execution"""
    print("=" * 80)
    print("VED INCOME BACKFILL SCRIPT")
    print("=" * 80)
    print("Purpose: Create missing Ved Income records for activated Ved Team members")
    print("DC Protocol: Uses ved_team_member table as single source of truth")
    print("Ved Isolation: Ensures separation between different Ved owners")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Step 1: Find missing records
        missing_records = check_missing_ved_income(db)
        
        if not missing_records:
            print("\n✅ No missing Ved Income records found!")
            print("All activated Ved Team members have corresponding Ved Income records.")
            return
        
        print(f"\n⚠️  Found {len(missing_records)} missing Ved Income records:")
        print("-" * 80)
        
        # Group by Ved owner for better visibility
        by_ved_owner = {}
        for record in missing_records:
            owner = record['ved_owner_id']
            if owner not in by_ved_owner:
                by_ved_owner[owner] = []
            by_ved_owner[owner].append(record)
        
        for ved_owner_id, records in by_ved_owner.items():
            ved_owner_name = records[0]['ved_owner_name']
            print(f"\n👤 Ved Owner: {ved_owner_id} ({ved_owner_name})")
            print(f"   Missing {len(records)} Ved Income record(s):")
            for rec in records:
                print(f"   - {rec['member_id']} ({rec['member_name']}) - "
                      f"Activated: {rec['member_activation_date'].strftime('%Y-%m-%d')} - "
                      f"Expected: ₹{rec['expected_income']}")
        
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
        print(f"💰 Total income restored: ₹{sum(r['expected_income'] for r in missing_records[:success_count])}")
        print(f"👥 Ved Owners benefited: {len(by_ved_owner)} users")
        print("\n🔄 Next Steps:")
        print("1. Verify records in pending_income table")
        print("2. Check materialized views refresh (if applicable)")
        print("3. Test Ved Income pages to confirm data displays correctly")
        print("4. Verify Ved Team isolation (each owner has separate income records)")
        
    except Exception as e:
        print(f"\n❌ Backfill failed with error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
